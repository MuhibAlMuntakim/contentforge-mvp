"""YouTube adapter — title, description, tags, optional CTA placement."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class YouTubeAdapter(BaseAdapter):
    platform = Platform.YOUTUBE

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Build YouTube description
        desc_parts: list[str] = []

        if package.long_body:
            desc_parts.append(self._truncate(package.long_body, 4500))
        elif package.short_caption:
            desc_parts.append(package.short_caption)

        if package.cta:
            desc_parts.append(f"\n🎯 {package.cta}")

        # Timestamps placeholder
        desc_parts.append("\n⏱️ Timestamps:")
        desc_parts.append("0:00 - Intro")

        if package.links:
            desc_parts.append("\n📎 Links:")
            for link in package.links:
                desc_parts.append(f"  {link}")

        hashtags = self._normalize_hashtags(package.hashtags[:15])
        if hashtags:
            desc_parts.append(f"\n{' '.join(hashtags)}")

        # YouTube uses tags (not hashtags) for SEO
        tags = list(set(package.keywords + [t.lstrip("#") for t in package.hashtags]))[:30]

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=self._truncate(package.title, 100),
            body="\n".join(desc_parts),
            tags=tags,
            hashtags=hashtags,
            links=package.links,
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "video",
                "privacy": "private",  # Safe default
                "category": "22",  # People & Blogs
                "made_for_kids": False,
            },
        )
