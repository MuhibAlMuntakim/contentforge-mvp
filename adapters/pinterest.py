"""Pinterest adapter — title + pin description + image association."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class PinterestAdapter(BaseAdapter):
    platform = Platform.PINTEREST

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Pin description: concise, keyword-rich
        desc_parts: list[str] = []

        if package.short_caption:
            desc_parts.append(package.short_caption)
        elif package.long_body:
            desc_parts.append(self._truncate(package.long_body, 400))

        if package.cta:
            desc_parts.append(f"| {package.cta}")

        hashtags = self._normalize_hashtags(package.hashtags[:20])
        if hashtags:
            desc_parts.append(f"\n{' '.join(hashtags)}")

        pin_description = " ".join(desc_parts)
        pin_description = self._truncate(pin_description, 500)

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=self._truncate(package.title, 100),
            body=pin_description,
            caption=pin_description,
            hashtags=hashtags,
            links=package.links[:1],  # Pin has one destination link
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "pin",
                "media_required": True,
                "board_name": "",  # To be set by user or config
                "destination_link": package.links[0] if package.links else "",
            },
        )
