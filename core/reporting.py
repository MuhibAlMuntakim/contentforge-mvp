"""
Audit report generation.

Produces structured AuditReport from publishing results.
Reports are persisted to SQLite and displayed in the Streamlit UI.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.models import (
    AuditReport,
    ContentPackage,
    PublishResult,
    PublishStatus,
)

logger = logging.getLogger(__name__)


def generate_audit_report(
    package: ContentPackage,
    results: list[PublishResult],
) -> AuditReport:
    """
    Generate a structured audit report from publishing results.

    Args:
        package: The original content package.
        results: List of per-platform publish results.

    Returns:
        A complete AuditReport.
    """
    succeeded = sum(1 for r in results if r.status == PublishStatus.PUBLISHED)
    failed = sum(1 for r in results if r.status == PublishStatus.FAILED)
    drafts = sum(1 for r in results if r.status in (
        PublishStatus.DRAFT_CREATED, PublishStatus.REVIEW_REQUIRED
    ))
    skipped = sum(1 for r in results if r.status == PublishStatus.SKIPPED)

    # Build summary notes
    notes_parts: list[str] = []
    if failed > 0:
        failed_platforms = [r.platform.value for r in results if r.status == PublishStatus.FAILED]
        notes_parts.append(f"Failed platforms: {', '.join(failed_platforms)}")
    if drafts > 0:
        draft_platforms = [
            r.platform.value for r in results
            if r.status in (PublishStatus.DRAFT_CREATED, PublishStatus.REVIEW_REQUIRED)
        ]
        notes_parts.append(f"Drafts/review: {', '.join(draft_platforms)}")

    report = AuditReport(
        content_id=package.content_id,
        campaign_name=package.campaign_name,
        publish_mode=package.publish_mode,
        total_platforms=len(results),
        succeeded=succeeded,
        failed=failed,
        drafts=drafts,
        skipped=skipped,
        results=results,
        completed_at=datetime.now(timezone.utc),
        notes="; ".join(notes_parts) if notes_parts else "All operations completed successfully",
    )

    logger.info(
        f"Audit report generated: {report.report_id} | "
        f"success={succeeded} fail={failed} draft={drafts} skip={skipped}"
    )

    return report
