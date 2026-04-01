# Publishers package
from publishers.linkedin import LinkedInPublisher
from publishers.twitter import TwitterPublisher
from publishers.facebook import FacebookPublisher
from publishers.medium import MediumPublisher
from publishers.blogger import BloggerPublisher
from publishers.youtube import YouTubePublisher
from publishers.instagram import InstagramPublisher
from publishers.pinterest import PinterestPublisher
from publishers.tiktok import TikTokPublisher
from publishers.snapchat import SnapchatPublisher
from publishers.reddit import RedditPublisher
from publishers.quora import QuoraPublisher
from core.models import Platform

PUBLISHER_REGISTRY: dict[Platform, type] = {
    Platform.LINKEDIN: LinkedInPublisher,
    Platform.TWITTER: TwitterPublisher,
    Platform.FACEBOOK: FacebookPublisher,
    Platform.MEDIUM: MediumPublisher,
    Platform.BLOGGER: BloggerPublisher,
    Platform.YOUTUBE: YouTubePublisher,
    Platform.INSTAGRAM: InstagramPublisher,
    Platform.PINTEREST: PinterestPublisher,
    Platform.TIKTOK: TikTokPublisher,
    Platform.SNAPCHAT: SnapchatPublisher,
    Platform.REDDIT: RedditPublisher,
    Platform.QUORA: QuoraPublisher,
}


def get_publisher(platform: Platform):
    """Get a publisher instance for the given platform."""
    publisher_cls = PUBLISHER_REGISTRY.get(platform)
    if not publisher_cls:
        raise ValueError(f"No publisher registered for platform: {platform}")
    return publisher_cls()
