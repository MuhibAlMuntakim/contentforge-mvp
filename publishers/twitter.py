"""Twitter/X publisher — Tier 1: stubbed with realistic responses."""

import os
try:
    import tweepy
except ImportError:
    tweepy = None

from publishers.base import BasePublisher
from core.models import Platform, PlatformPayload, PublishResult, PublishStatus


class TwitterPublisher(BasePublisher):
    platform = Platform.TWITTER
    is_stub = False

    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        text = payload.body or payload.caption
        if not text:
            return False, "Tweet requires text content."
        # Note: Twitter API allows 280 chars. 
        if len(text) > 280 and payload.metadata.get("format") != "thread":
            return False, f"Tweet exceeds 280 chars ({len(text)}). Use thread format."
        return True, ""

    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        valid, err = self.validate_payload(payload)
        if not valid:
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                error_message=err
            )

        if draft:
            return self._make_stub_result(payload, draft=draft)

        if not tweepy:
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                error_message="tweepy library is not installed."
            )

        api_key = os.getenv("TWITTER_API_KEY")
        api_secret = os.getenv("TWITTER_API_SECRET")
        access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        access_secret = os.getenv("TWITTER_ACCESS_SECRET")

        if not all([api_key, api_secret, access_token, access_secret]):
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                error_message="Twitter credentials missing from .env."
            )

        try:
            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret
            )
            text = payload.body or payload.caption
            
            response = client.create_tweet(text=text)
            
            # The API returns the new tweet's ID in response.data
            tweet_id = response.data['id']
            url = f"https://x.com/user/status/{tweet_id}"
            
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.PUBLISHED,
                url=url
            )
            
        except Exception as e:
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                error_message=str(e),
                retryable=True
            )
