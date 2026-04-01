"""Twitter/X adapter — short-form or thread-capable structure."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class TwitterAdapter(BaseAdapter):
    platform = Platform.TWITTER

    MAX_TWEET_LENGTH = 280

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Prefer short caption for tweets; fall back to title
        raw_text = package.short_caption or package.title or ""

        hashtags = self._normalize_hashtags(package.hashtags[:5])
        hashtag_str = " ".join(hashtags)

        # Calculate available space for text
        link_part = f" {package.links[0]}" if package.links else ""
        reserved = len(hashtag_str) + len(link_part) + 2  # spacing
        available = self.MAX_TWEET_LENGTH - reserved

        tweet_text = self._truncate(raw_text, max(available, 50))

        parts = [tweet_text]
        if link_part:
            parts.append(link_part.strip())
        if hashtag_str:
            parts.append(hashtag_str)

        full_tweet = " ".join(parts)

        # If content is long enough, generate thread metadata
        is_thread = len(package.long_body or "") > 500
        thread_parts = []
        if is_thread and package.long_body:
            words = package.long_body.split()
            chunk: list[str] = []
            chunk_len = 0
            for word in words:
                if chunk_len + len(word) + 1 > 270:
                    thread_parts.append(" ".join(chunk))
                    chunk = [word]
                    chunk_len = len(word)
                else:
                    chunk.append(word)
                    chunk_len += len(word) + 1
            if chunk:
                thread_parts.append(" ".join(chunk))

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title="",  # tweets don't have titles
            body=full_tweet,
            caption=tweet_text,
            hashtags=hashtags,
            links=package.links[:1],
            cta=package.cta,
            media_paths=package.uploaded_assets,
            metadata={
                "format": "thread" if is_thread else "single_tweet",
                "thread_parts": thread_parts if is_thread else [],
                "character_count": len(full_tweet),
            },
        )
