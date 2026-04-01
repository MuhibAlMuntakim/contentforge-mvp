"""
Environment-based configuration.
All secrets and API keys are loaded from environment variables.
No credentials are hardcoded anywhere in the codebase.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file from project root ─────────────────────────────────────────
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
ASSETS_DIR = PROJECT_ROOT / "assets"
DB_PATH = PROJECT_ROOT / "content_publisher.db"

LOGS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# ── App Settings ─────────────────────────────────────────────────────────────
APP_NAME = "ContentForge"
APP_VERSION = "0.1.0"
DEBUG = os.getenv("CONTENTFORGE_DEBUG", "false").lower() == "true"

# ── Platform API Keys (loaded from env, never hardcoded) ─────────────────────
# When real integrations are built, these will be required.
PLATFORM_CREDENTIALS = {
    "linkedin": {
        "client_id": os.getenv("LINKEDIN_CLIENT_ID", ""),
        "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET", ""),
        "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN", ""),
    },
    "twitter": {
        "api_key": os.getenv("TWITTER_API_KEY", ""),
        "api_secret": os.getenv("TWITTER_API_SECRET", ""),
        "access_token": os.getenv("TWITTER_ACCESS_TOKEN", ""),
        "access_secret": os.getenv("TWITTER_ACCESS_SECRET", ""),
    },
    "facebook": {
        "app_id": os.getenv("FACEBOOK_APP_ID", ""),
        "app_secret": os.getenv("FACEBOOK_APP_SECRET", ""),
        "page_token": os.getenv("FACEBOOK_PAGE_TOKEN", ""),
    },
    "medium": {
        "integration_token": os.getenv("MEDIUM_INTEGRATION_TOKEN", ""),
    },
    "blogger": {
        "api_key": os.getenv("BLOGGER_API_KEY", ""),
        "blog_id": os.getenv("BLOGGER_BLOG_ID", ""),
    },
    "youtube": {
        "api_key": os.getenv("YOUTUBE_API_KEY", ""),
        "client_id": os.getenv("YOUTUBE_CLIENT_ID", ""),
        "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", ""),
    },
    "instagram": {
        "access_token": os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
        "business_account_id": os.getenv("INSTAGRAM_BUSINESS_ID", ""),
    },
    "pinterest": {
        "access_token": os.getenv("PINTEREST_ACCESS_TOKEN", ""),
    },
    "tiktok": {
        "access_token": os.getenv("TIKTOK_ACCESS_TOKEN", ""),
    },
    "snapchat": {
        "access_token": os.getenv("SNAPCHAT_ACCESS_TOKEN", ""),
    },
    "reddit": {
        "client_id": os.getenv("REDDIT_CLIENT_ID", ""),
        "client_secret": os.getenv("REDDIT_CLIENT_SECRET", ""),
        "username": os.getenv("REDDIT_USERNAME", ""),
        "password": os.getenv("REDDIT_PASSWORD", ""),
    },
    "quora": {
        # Quora has no public API; drafts are generated locally.
        "session_cookie": os.getenv("QUORA_SESSION_COOKIE", ""),
    },
}


def has_credentials(platform: str) -> bool:
    """Check if real credentials are configured for a platform."""
    creds = PLATFORM_CREDENTIALS.get(platform, {})
    return any(v for v in creds.values())


# ── Publishing Defaults ──────────────────────────────────────────────────────
MAX_RETRY_ATTEMPTS = 3
PUBLISH_TIMEOUT_SECONDS = 30
