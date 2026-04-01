"""Snapchat adapter — short media-first copy."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class SnapchatAdapter(BaseAdapter):
    platform = Platform.SNAPCHAT

    MAX_CAPTION = 250

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Snapchat: ultra-short, media-forward
        text = package.short_caption or package.title or ""
        text = self._truncate(text, 200)

        if package.cta:
            text += f" | {self._truncate(package.cta, 40)}"

        text = self._truncate(text, self.MAX_CAPTION)

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title="",
            body="",
            caption=text,
            hashtags=[],  # Snapchat doesn't use hashtags
            links=package.links[:1],
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "snap",
                "media_required": True,
                "swipe_up_link": package.links[0] if package.links else "",
            },
        )
