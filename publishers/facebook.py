"""Facebook publisher — Tier 1: real API integration using Graph API."""

import os
import logging
from typing import Optional
import requests
from dotenv import load_dotenv
from pathlib import Path

from publishers.base import BasePublisher
from core.models import Platform, PlatformPayload, PublishResult, PublishStatus

load_dotenv()

logger = logging.getLogger(__name__)


class FacebookPublisher(BasePublisher):
    platform = Platform.FACEBOOK
    is_stub = True

    # Facebook Graph API endpoint
    GRAPH_API_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        super().__init__()
        self.page_token = os.getenv("FACEBOOK_PAGE_TOKEN", "")
        # Page ID should be explicitly configured (more reliable than auto-extraction)
        self.page_id = os.getenv("FACEBOOK_PAGE_ID", "")
        
        if not self.page_id:
            logger.warning("FACEBOOK_PAGE_ID not configured in .env")
        if not self.page_token:
            logger.warning("FACEBOOK_PAGE_TOKEN not configured in .env")

    def validate_payload(self, payload: PlatformPayload) -> tuple[bool, str]:
        """Validate Facebook payload."""
        if not self.page_token:
            return False, "Facebook Page Token not configured."

        title = (payload.title or "").strip()
        body = (payload.body or "").strip()
        caption = (payload.caption or "").strip()

        # Accept title-only/caption-only submissions and normalize to body.
        if not body:
            body = caption or title
            payload.body = body

        if not body and not title:
            return False, "Facebook post requires content (title or body)."

        if not self.page_id:
            return False, "Unable to resolve Facebook Page ID from access token."

        return True, ""

    def publish(self, payload: PlatformPayload, draft: bool = False) -> PublishResult:
        """Publish content to Facebook Page using Graph API."""
        valid, err = self.validate_payload(payload)
        if not valid:
            return self._make_stub_result(payload, error=err)

        # If draft mode, don't actually post
        if draft:
            logger.info(f"Draft mode: Skipping live Facebook publish for {payload.content_id}")
            return self._make_stub_result(payload, draft=True)

        try:
            # Prepare post content
            post_message = (payload.body or "").strip()

            if payload.cta:
                post_message += f"\n\n👉 {payload.cta}"

            valid_links = [l for l in payload.links if isinstance(l, str) and l.strip().startswith(("http://", "https://"))]
            if valid_links:
                post_message += f"\n🔗 {valid_links[0].strip()}"

            if payload.hashtags:
                normalized_tags = [
                    tag if str(tag).startswith("#") else f"#{tag}"
                    for tag in payload.hashtags
                    if str(tag).strip()
                ]
                if normalized_tags:
                    post_message += f"\n\n{' '.join(normalized_tags[:30])}"

            # The page_id can be numeric or a page username.
            page_identifier = self.page_id or "me"

            # If media is provided, publish media first (single-file support).
            response = None
            if payload.media_paths:
                media_path = Path(payload.media_paths[0])
                ext = media_path.suffix.lower()
                if media_path.exists() and ext in {".mp4", ".mov", ".m4v", ".avi", ".webm"}:
                    api_endpoint = f"{self.GRAPH_API_URL}/{page_identifier}/videos"
                    post_data = {
                        "description": post_message,
                        "access_token": self.page_token,
                    }
                    logger.info(f"Publishing Facebook video: {payload.content_id} via {page_identifier}")
                    with media_path.open("rb") as video_file:
                        response = requests.post(
                            api_endpoint,
                            data=post_data,
                            files={"source": video_file},
                            timeout=90,
                        )
                elif media_path.exists() and ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                    api_endpoint = f"{self.GRAPH_API_URL}/{page_identifier}/photos"
                    post_data = {
                        "caption": post_message,
                        "access_token": self.page_token,
                    }
                    logger.info(f"Publishing Facebook image: {payload.content_id} via {page_identifier}")
                    with media_path.open("rb") as image_file:
                        response = requests.post(
                            api_endpoint,
                            data=post_data,
                            files={"source": image_file},
                            timeout=90,
                        )

            # Fallback to text feed post.
            if response is None:
                api_endpoint = f"{self.GRAPH_API_URL}/{page_identifier}/feed"
                post_data = {
                    "message": post_message,
                    "access_token": self.page_token,
                }
                logger.info(f"Publishing Facebook text post: {payload.content_id} via {page_identifier}")
                response = requests.post(api_endpoint, data=post_data, timeout=30)

            response.raise_for_status()

            result_data = response.json()
            post_id = result_data.get("id")

            logger.info(f"Successfully published to Facebook. Post ID: {post_id}")

            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.PUBLISHED,
                draft_or_published="published",
                variant_summary=payload.summary(),
                url=f"https://facebook.com/{post_id}",
                notes=f"Published successfully to Facebook. Post ID: {post_id}",
                raw_response=result_data,
            )

        except requests.exceptions.RequestException as e:
            details = ""
            if getattr(e, "response", None) is not None:
                try:
                    details = f" | Response: {e.response.text}"
                except Exception:
                    details = ""
            error_msg = f"Facebook API error: {str(e)}{details}"
            logger.error(error_msg)
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                draft_or_published="failed",
                error_message=error_msg,
                retryable=True,
                notes="Facebook Graph API request failed",
            )
        except Exception as e:
            error_msg = f"Unexpected error publishing to Facebook: {str(e)}"
            logger.error(error_msg)
            return PublishResult(
                content_id=payload.content_id,
                platform=self.platform,
                status=PublishStatus.FAILED,
                draft_or_published="failed",
                error_message=error_msg,
                retryable=True,
                notes="Unexpected error in Facebook publisher",
            )
