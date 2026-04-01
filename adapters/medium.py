"""Medium adapter — long-form article formatting."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class MediumAdapter(BaseAdapter):
    platform = Platform.MEDIUM

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Medium expects full article content
        body = package.long_body or package.short_caption or ""

        # Add CTA at the bottom
        if package.cta:
            body += f"\n\n---\n\n**{package.cta}**"

        # Add reference links
        if package.links:
            body += "\n\n### Links\n"
            for link in package.links:
                body += f"- {link}\n"

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=package.title,
            body=body,
            tags=package.keywords[:5],  # Medium uses tags, not hashtags
            hashtags=self._normalize_hashtags(package.hashtags[:5]),
            links=package.links,
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "article",
                "content_format": "markdown",
                "publish_status": "draft",
            },
        )
