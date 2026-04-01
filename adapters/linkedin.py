"""LinkedIn adapter — professional tone, concise but informative."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class LinkedInAdapter(BaseAdapter):
    platform = Platform.LINKEDIN

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Build a professional-tone post
        body_parts: list[str] = []

        if package.long_body:
            body_parts.append(self._truncate(package.long_body, 2800))
        elif package.short_caption:
            body_parts.append(package.short_caption)

        if package.cta:
            body_parts.append(f"\n{package.cta}")

        if package.links:
            body_parts.append(f"\n🔗 {package.links[0]}")

        hashtag_str = " ".join(self._normalize_hashtags(package.hashtags[:10]))
        if hashtag_str:
            body_parts.append(f"\n\n{hashtag_str}")

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=package.title,
            body="\n".join(body_parts),
            hashtags=self._normalize_hashtags(package.hashtags[:10]),
            links=package.links,
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={"tone": "professional", "format": "post"},
        )
