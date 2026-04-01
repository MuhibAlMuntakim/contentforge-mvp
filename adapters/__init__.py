# Adapters package
from adapters.linkedin import LinkedInAdapter
from adapters.twitter import TwitterAdapter
from adapters.facebook import FacebookAdapter
from adapters.medium import MediumAdapter
from adapters.blogger import BloggerAdapter
from adapters.youtube import YouTubeAdapter
from adapters.instagram import InstagramAdapter
from adapters.pinterest import PinterestAdapter
from adapters.tiktok import TikTokAdapter
from adapters.snapchat import SnapchatAdapter
from adapters.reddit import RedditAdapter
from adapters.quora import QuoraAdapter
from core.models import Platform

ADAPTER_REGISTRY: dict[Platform, type] = {
    Platform.LINKEDIN: LinkedInAdapter,
    Platform.TWITTER: TwitterAdapter,
    Platform.FACEBOOK: FacebookAdapter,
    Platform.MEDIUM: MediumAdapter,
    Platform.BLOGGER: BloggerAdapter,
    Platform.YOUTUBE: YouTubeAdapter,
    Platform.INSTAGRAM: InstagramAdapter,
    Platform.PINTEREST: PinterestAdapter,
    Platform.TIKTOK: TikTokAdapter,
    Platform.SNAPCHAT: SnapchatAdapter,
    Platform.REDDIT: RedditAdapter,
    Platform.QUORA: QuoraAdapter,
}


def get_adapter(platform: Platform):
    """Get an adapter instance for the given platform."""
    adapter_cls = ADAPTER_REGISTRY.get(platform)
    if not adapter_cls:
        raise ValueError(f"No adapter registered for platform: {platform}")
    return adapter_cls()
