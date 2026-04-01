"""Blogger adapter — article formatting with title/body."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class BloggerAdapter(BaseAdapter):
    platform = Platform.BLOGGER

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Blogger expects HTML-ish content; we produce clean markup
        body = package.long_body or package.short_caption or ""

        # Wrap in basic HTML structure for Blogger
        html_body = f"<p>{body.replace(chr(10) + chr(10), '</p><p>').replace(chr(10), '<br/>')}</p>"

        if package.cta:
            html_body += f"\n<p><strong>{package.cta}</strong></p>"

        if package.links:
            html_body += "\n<h3>Links</h3>\n<ul>"
            for link in package.links:
                html_body += f'\n<li><a href="{link}">{link}</a></li>'
            html_body += "\n</ul>"

        labels = package.keywords[:10] if package.keywords else []

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=package.title,
            body=html_body,
            tags=labels,
            hashtags=self._normalize_hashtags(package.hashtags[:10]),
            links=package.links,
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "blog_post",
                "content_format": "html",
                "labels": labels,
            },
        )
