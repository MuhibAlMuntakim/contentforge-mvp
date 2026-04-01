"""
Workflow orchestration engine.

Controls the order of execution for the content publishing pipeline:
  1. Validate content package
  2. Run CrewAI ContentAdaptationCrew for content intelligence
  3. Respect publish mode (draft / review / publish now)
  4. Execute publishing in platform order
  5. Handle failures gracefully (per-platform isolation)
  6. Generate audit report

One failed platform never crashes the entire run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from core.crew import ContentAdaptationCrew, ContentAdaptationResult, ContentStatus
from core.models import (
    AuditReport,
    ContentPackage,
    Platform,
    PlatformPayload,
    PublishMode,
    PublishResult,
    PublishStatus,
    ValidationResult,
)
from core.reporting import generate_audit_report
from core.storage import Storage
from core.validators import validate_content_package
from config.platforms import (
    DEFAULT_PUBLISH_ORDER,
    TIER_4_DRAFT_FIRST,
    get_ordered_platforms,
)
from publishers import get_publisher

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Orchestrates the full content publishing workflow.

    Sequence:
      validate → adapt (CrewAI) → approval gate → publish → audit report
    """

    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self.crew = ContentAdaptationCrew()

    def validate(self, package: ContentPackage) -> ValidationResult:
        """Step 1: Validate the content package."""
        logger.info(f"Validating content package {package.content_id}")
        result = validate_content_package(package)
        logger.info(f"Validation complete: valid={result.is_valid}, issues={len(result.issues)}")
        return result

    def adapt(self, package: ContentPackage) -> ContentAdaptationResult:
        """Step 2: Run CrewAI content intelligence pipeline."""
        logger.info(f"Running content adaptation for {package.content_id}")
        result = self.crew.run(package)
        logger.info(
            f"Adaptation complete: {len(result.adaptations)} platforms, "
            f"overall_status={result.overall_status.value}"
        )
        return result

    def _should_publish(
        self,
        platform: Platform,
        publish_mode: PublishMode,
        content_status: ContentStatus,
    ) -> tuple[bool, bool]:
        """
        Determine whether to publish or draft for a given platform.

        Returns:
            (should_execute, is_draft) — whether to proceed and whether it's a draft.
        """
        # Blocked content is never published
        if content_status == ContentStatus.BLOCKED:
            return False, False

        # Tier 4 platforms always draft, regardless of mode
        if platform in TIER_4_DRAFT_FIRST:
            return True, True

        if publish_mode == PublishMode.DRAFT_ONLY:
            return True, True

        if publish_mode == PublishMode.REVIEW_REQUIRED:
            # In review mode, content that needs review stays as draft
            if content_status == ContentStatus.NEEDS_REVIEW:
                return True, True
            return True, True  # All drafts in review mode

        if publish_mode == PublishMode.PUBLISH_NOW:
            if content_status == ContentStatus.NEEDS_REVIEW:
                return True, True  # Needs review → still draft
            return True, False  # Approved → publish

        return True, True  # Default to draft

    def execute(
        self,
        package: ContentPackage,
        adaptation_result: ContentAdaptationResult,
        on_platform_start: Optional[callable] = None,
        on_platform_complete: Optional[callable] = None,
    ) -> list[PublishResult]:
        """
        Step 3: Execute publishing for all selected platforms.

        Args:
            package: The validated content package.
            adaptation_result: Output from the CrewAI content intelligence pipeline.
            on_platform_start: Callback(platform) when a platform begins processing.
            on_platform_complete: Callback(platform, result) when complete.

        Returns:
            List of PublishResult, one per platform.
        """
        results: list[PublishResult] = []

        # Save content package
        self.storage.save_content_package(package)

        # Get platforms in publish order
        ordered = get_ordered_platforms(package.target_platforms)

        # Build lookup: platform_name → adaptation
        adaptation_map = {a.platform: a for a in adaptation_result.adaptations}

        for platform in ordered:
            if on_platform_start:
                on_platform_start(platform)

            try:
                adaptation = adaptation_map.get(platform.value)
                if not adaptation:
                    result = PublishResult(
                        content_id=package.content_id,
                        platform=platform,
                        status=PublishStatus.SKIPPED,
                        notes="No adaptation generated for this platform",
                    )
                    results.append(result)
                    if on_platform_complete:
                        on_platform_complete(platform, result)
                    continue

                # Convert CrewAI adaptation to PlatformPayload
                payload = self.crew.adaptation_to_payload(adaptation, package.content_id)
                # Attach media from original package
                payload.media_paths = package.uploaded_assets

                # Save the payload
                self.storage.save_platform_payload(payload)

                # Determine publish vs draft
                should_execute, is_draft = self._should_publish(
                    platform, package.publish_mode, adaptation.status
                )

                if not should_execute:
                    result = PublishResult(
                        content_id=package.content_id,
                        platform=platform,
                        status=PublishStatus.SKIPPED,
                        notes=f"Blocked by compliance: {adaptation.status_reason}",
                    )
                else:
                    # Get publisher and execute
                    publisher = get_publisher(platform)
                    result = publisher.publish(payload, draft=is_draft)
                    result.variant_summary = payload.summary()

            except Exception as e:
                logger.error(f"Publishing failed for {platform.value}: {e}", exc_info=True)
                result = PublishResult(
                    content_id=package.content_id,
                    platform=platform,
                    status=PublishStatus.FAILED,
                    error_message=str(e),
                    retryable=True,
                    notes=f"Unexpected error during publishing: {type(e).__name__}",
                )

            # Save result and notify
            self.storage.save_publish_result(result)
            results.append(result)

            if on_platform_complete:
                on_platform_complete(platform, result)

        return results

    def run_full_pipeline(
        self,
        package: ContentPackage,
        on_platform_start: Optional[callable] = None,
        on_platform_complete: Optional[callable] = None,
    ) -> tuple[ValidationResult, Optional[ContentAdaptationResult], list[PublishResult], Optional[AuditReport]]:
        """
        Run the complete pipeline: validate → adapt → execute → report.

        Returns:
            (validation_result, adaptation_result, publish_results, audit_report)
        """
        # Step 1: Validate
        validation = self.validate(package)
        if not validation.is_valid:
            return validation, None, [], None

        # Step 2: Adapt via CrewAI
        adaptation = self.adapt(package)

        # Step 3: Execute publishing
        publish_results = self.execute(
            package, adaptation,
            on_platform_start=on_platform_start,
            on_platform_complete=on_platform_complete,
        )

        # Step 4: Generate audit report
        report = generate_audit_report(package, publish_results)
        self.storage.save_audit_report(report)

        return validation, adaptation, publish_results, report
