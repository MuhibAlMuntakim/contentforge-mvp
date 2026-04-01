"""
Abstract base class for platform publishers.

Every publisher must implement a consistent interface:
  1. validate_payload — check the payload is publishable
  2. publish — execute the publish or create a draft
  3. Each method returns structured results, never raw exceptions

The publisher is ONLY responsible for publishing — never content adaptation.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from core.models import Platform, PlatformPayload, PublishResult, PublishStatus


class BasePublisher(ABC):
    """Abstract base for all platform publishers."""

    platform: Platform
    is_stub: bool = True  # True until real API integration is built

    @abstractmethod
    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        """
        Validate that the payload is ready to publish.

        Returns:
            (is_valid, error_message) — error_message is empty if valid.
        """
        ...

    @abstractmethod
    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        """
        Publish or create a draft for the given payload.

        Args:
            payload: The platform-specific content payload.
            draft: If True, create a draft instead of publishing.

        Returns:
            A PublishResult with status, URL, error info, etc.
        """
        ...

    def _make_stub_result(
        self,
        payload: PlatformPayload,
        draft: bool = False,
        error: Optional[str] = None,
    ) -> PublishResult:
        """
        Generate a realistic stub result for mocked publishers.
        Used until real API integrations are built.
        """
        fake_id = uuid.uuid4().hex[:12]
        platform_name = self.platform.value

        if error:
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                draft_or_published="failed",
                error_message=error,
                retryable=True,
                notes=f"[STUB] Simulated failure for {platform_name}",
            )

        status = PublishStatus.DRAFT_CREATED if draft else PublishStatus.PUBLISHED
        mode = "draft" if draft else "published"

        return PublishResult(
            content_id=payload.content_id,
            platform=self.platform,
            status=status,
            draft_or_published=mode,
            timestamp=datetime.now(timezone.utc),
            variant_summary=payload.summary(),
            url=f"https://{platform_name}.example.com/post/{fake_id}",
            notes=f"[STUB] Simulated {mode} on {platform_name}",
            raw_response={
                "stub": True,
                "platform": platform_name,
                "post_id": fake_id,
                "mode": mode,
            },
        )
