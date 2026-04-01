"""Reddit adapter — community-safe draft, avoid spam tone."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class RedditAdapter(BaseAdapter):
    platform = Platform.REDDIT

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Reddit: value-first, conversational, NO spam tone
        # Strip promotional language and make it community-appropriate

        body_parts: list[str] = []

        if package.long_body:
            body_parts.append(package.long_body)
        elif package.short_caption:
            body_parts.append(package.short_caption)

        # Add links as references, not promotions
        if package.links:
            body_parts.append("\n\n---\n")
            body_parts.append("**Resources:**")
            for link in package.links:
                body_parts.append(f"- {link}")

        # Explicitly NO CTA in Reddit (anti-spam)
        # No hashtags either (Reddit doesn't use them)

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=package.title,
            body="\n".join(body_parts),
            caption="",
            hashtags=[],  # Reddit doesn't use hashtags
            tags=[],
            links=package.links,
            cta="",  # Intentionally stripped — spam prevention
            media_paths=package.uploaded_assets,
            metadata={
                "format": "text_post",
                "subreddit": "",  # To be configured per campaign
                "flair": "",
                "review_required": True,  # Always review Reddit posts
                "tone": "community-safe",
                "note": "CTA removed to avoid spam flagging. Review before posting.",
            },
        )
