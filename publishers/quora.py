"""Quora publisher — Tier 4: always draft-first, review-required."""

from publishers.base import BasePublisher
from core.models import Platform, PlatformPayload, PublishResult, PublishStatus


class QuoraPublisher(BasePublisher):
    platform = Platform.QUORA
    is_stub = True

    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        if not payload.body:
            return False, "Quora answer requires body content."
        return True, ""

    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        valid, err = self.validate_payload(payload)
        if not valid:
            return self._make_stub_result(payload, error=err)
        # Quora ALWAYS creates drafts regardless of mode (Tier 4 policy)
        result = self._make_stub_result(payload, draft=True)
        result.notes = "[STUB] Quora always creates drafts per Tier 4 safety policy. " + result.notes
        result.status = PublishStatus.REVIEW_REQUIRED
        return result
