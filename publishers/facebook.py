"""Facebook publisher — Tier 1: stubbed with realistic responses."""

from publishers.base import BasePublisher
from core.models import Platform, PlatformPayload, PublishResult


class FacebookPublisher(BasePublisher):
    platform = Platform.FACEBOOK
    is_stub = True

    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        if not payload.body and not payload.title:
            return False, "Facebook post requires content."
        return True, ""

    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        valid, err = self.validate_payload(payload)
        if not valid:
            return self._make_stub_result(payload, error=err)
        return self._make_stub_result(payload, draft=draft)
