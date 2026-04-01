"""Instagram adapter — caption-first, hashtag-aware, media-first."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class InstagramAdapter(BaseAdapter):
    platform = Platform.INSTAGRAM

    MAX_CAPTION_LENGTH = 2200
    MAX_HASHTAGS = 30

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Instagram is caption + hashtags; body is secondary
        caption_parts: list[str] = []

        # Hook line from title or short caption
        hook = package.short_caption or package.title or ""
        if hook:
            caption_parts.append(hook)

        # Supporting text (condensed from long body)
        if package.long_body:
            condensed = self._truncate(package.long_body, 800)
            caption_parts.append(f"\n\n{condensed}")

        if package.cta:
            caption_parts.append(f"\n\n👉 {package.cta}")

        if package.links:
            caption_parts.append(f"\n🔗 Link in bio")

        # Hashtags block at the end
        hashtags = self._normalize_hashtags(package.hashtags[:self.MAX_HASHTAGS])
        if hashtags:
            caption_parts.append(f"\n.\n.\n.\n{' '.join(hashtags)}")

        full_caption = "\n".join(caption_parts)
        full_caption = self._truncate(full_caption, self.MAX_CAPTION_LENGTH)

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title="",  # Instagram doesn't have titles
            body="",
            caption=full_caption,
            hashtags=hashtags,
            links=package.links,
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "post",
                "media_required": True,
                "link_in_bio": bool(package.links),
            },
        )
