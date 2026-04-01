"""TikTok adapter — short caption + hook orientation."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class TikTokAdapter(BaseAdapter):
    platform = Platform.TIKTOK

    MAX_CAPTION = 2200

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # TikTok: hook-first, short, punchy
        hook = package.short_caption or package.title or ""

        caption_parts: list[str] = []
        caption_parts.append(hook)

        if package.cta:
            caption_parts.append(f"\n{package.cta}")

        hashtags = self._normalize_hashtags(package.hashtags[:10])
        if hashtags:
            caption_parts.append(f"\n{' '.join(hashtags)}")

        # Add trending-style tags
        if package.keywords:
            keyword_tags = self._normalize_hashtags(package.keywords[:5])
            caption_parts.append(" ".join(keyword_tags))

        full_caption = "\n".join(caption_parts)
        full_caption = self._truncate(full_caption, self.MAX_CAPTION)

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title="",  # TikTok doesn't use titles
            body="",
            caption=full_caption,
            hashtags=hashtags,
            links=[],  # TikTok doesn't allow links in captions
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "short_video",
                "media_required": True,
                "hook_text": hook,
            },
        )
