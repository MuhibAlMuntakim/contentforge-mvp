"""Pinterest publisher — Tier 1: stubbed with realistic responses."""

from publishers.base import BasePublisher
from core.models import Platform, PlatformPayload, PublishResult


class PinterestPublisher(BasePublisher):
    platform = Platform.PINTEREST
    is_stub = True

    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        if not payload.title and not payload.body:
            return False, "Pinterest pin requires a title or description."
        return True, ""

    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        valid, err = self.validate_payload(payload)
        if not valid:
            return self._make_stub_result(payload, error=err)
        return self._make_stub_result(payload, draft=draft)
