"""TikTok publisher — Tier 3: stubbed with realistic responses."""

from publishers.base import BasePublisher
from core.models import Platform, PlatformPayload, PublishResult


class TikTokPublisher(BasePublisher):
    platform = Platform.TIKTOK
    is_stub = True

    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        if not payload.caption:
            return False, "TikTok post requires a caption."
        if not payload.media_paths:
            return False, "TikTok requires a video file."
        return True, ""

    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        valid, err = self.validate_payload(payload)
        if not valid:
            return self._make_stub_result(payload, error=err)
        return self._make_stub_result(payload, draft=draft)
