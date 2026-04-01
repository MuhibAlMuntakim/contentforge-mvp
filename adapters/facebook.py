"""Facebook adapter — brand-friendly social post."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class FacebookAdapter(BaseAdapter):
    platform = Platform.FACEBOOK

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        body_parts: list[str] = []

        # Use long body for Facebook (supports rich posts)
        if package.long_body:
            body_parts.append(self._truncate(package.long_body, 5000))
        elif package.short_caption:
            body_parts.append(package.short_caption)

        if package.cta:
            body_parts.append(f"\n👉 {package.cta}")

        if package.links:
            body_parts.append(f"\n🔗 {package.links[0]}")

        hashtags = self._normalize_hashtags(package.hashtags[:15])
        if hashtags:
            body_parts.append(f"\n\n{' '.join(hashtags)}")

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=package.title,
            body="\n".join(body_parts),
            hashtags=hashtags,
            links=package.links,
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={"tone": "brand-friendly", "format": "social_post"},
        )
