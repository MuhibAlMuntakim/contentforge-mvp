"""
Platform metadata, tiers, and default publishing order.

Design decision: Publishing order is long-form reference first, then professional/brand,
then visual/short-form, then community. This ensures reference URLs exist before
they're shared on social platforms.
"""

from core.models import Platform


# ── Platform Tiers ───────────────────────────────────────────────────────────
# Determines automation level and default publish behavior.

TIER_1_FULL_AUTO = {
    Platform.BLOGGER, Platform.MEDIUM, Platform.LINKEDIN,
    Platform.FACEBOOK, Platform.TWITTER, Platform.PINTEREST,
}

TIER_2_SEMI_AUTO = {
    Platform.YOUTUBE, Platform.INSTAGRAM,
}

TIER_3_CAUTIOUS = {
    Platform.TIKTOK, Platform.SNAPCHAT,
}

TIER_4_DRAFT_FIRST = {
    Platform.REDDIT, Platform.QUORA,
}


def get_tier(platform: Platform) -> int:
    """Return the tier number for a given platform."""
    if platform in TIER_1_FULL_AUTO:
        return 1
    elif platform in TIER_2_SEMI_AUTO:
        return 2
    elif platform in TIER_3_CAUTIOUS:
        return 3
    elif platform in TIER_4_DRAFT_FIRST:
        return 4
    return 99


# ── Default Publishing Order ─────────────────────────────────────────────────
# Ordered list of platforms in the recommended publish sequence.
DEFAULT_PUBLISH_ORDER: list[Platform] = [
    # Phase 1: Long-form reference platforms
    Platform.BLOGGER,
    Platform.MEDIUM,
    Platform.YOUTUBE,
    # Phase 2: Brand / professional platforms
    Platform.LINKEDIN,
    Platform.FACEBOOK,
    Platform.TWITTER,
    # Phase 3: Visual / short-form platforms
    Platform.INSTAGRAM,
    Platform.PINTEREST,
    Platform.TIKTOK,
    Platform.SNAPCHAT,
    # Phase 4: Community platforms (always draft-first)
    Platform.REDDIT,
    Platform.QUORA,
]

# ── Platform Display Metadata ────────────────────────────────────────────────
PLATFORM_INFO: dict[str, dict] = {
    Platform.LINKEDIN: {
        "label": "LinkedIn",
        "icon": "🔗",
        "tier": 1,
        "description": "Professional networking — concise & informative tone",
        "max_body_length": 3000,
        "supports_media": True,
        "requires_media": False,
    },
    Platform.TWITTER: {
        "label": "Twitter / X",
        "icon": "🐦",
        "tier": 1,
        "description": "Short-form or thread-capable structure",
        "max_body_length": 280,
        "supports_media": True,
        "requires_media": False,
    },
    Platform.FACEBOOK: {
        "label": "Facebook",
        "icon": "📘",
        "tier": 1,
        "description": "Brand-friendly social post",
        "max_body_length": 63206,
        "supports_media": True,
        "requires_media": False,
    },
    Platform.MEDIUM: {
        "label": "Medium",
        "icon": "📝",
        "tier": 1,
        "description": "Long-form article formatting",
        "max_body_length": 100000,
        "supports_media": True,
        "requires_media": False,
    },
    Platform.BLOGGER: {
        "label": "Blogger",
        "icon": "📰",
        "tier": 1,
        "description": "Article formatting with title/body",
        "max_body_length": 500000,
        "supports_media": True,
        "requires_media": False,
    },
    Platform.YOUTUBE: {
        "label": "YouTube",
        "icon": "🎬",
        "tier": 2,
        "description": "Title, description, tags, CTA placement",
        "max_body_length": 5000,
        "supports_media": True,
        "requires_media": True,
    },
    Platform.INSTAGRAM: {
        "label": "Instagram",
        "icon": "📸",
        "tier": 2,
        "description": "Caption-first, hashtag-aware, media-first",
        "max_body_length": 2200,
        "supports_media": True,
        "requires_media": True,
    },
    Platform.PINTEREST: {
        "label": "Pinterest",
        "icon": "📌",
        "tier": 1,
        "description": "Title + pin description + image association",
        "max_body_length": 500,
        "supports_media": True,
        "requires_media": True,
    },
    Platform.TIKTOK: {
        "label": "TikTok",
        "icon": "🎵",
        "tier": 3,
        "description": "Short caption + hook orientation",
        "max_body_length": 2200,
        "supports_media": True,
        "requires_media": True,
    },
    Platform.SNAPCHAT: {
        "label": "Snapchat",
        "icon": "👻",
        "tier": 3,
        "description": "Short media-first copy",
        "max_body_length": 250,
        "supports_media": True,
        "requires_media": True,
    },
    Platform.REDDIT: {
        "label": "Reddit",
        "icon": "🤖",
        "tier": 4,
        "description": "Community-safe draft, avoid spam tone",
        "max_body_length": 40000,
        "supports_media": True,
        "requires_media": False,
    },
    Platform.QUORA: {
        "label": "Quora",
        "icon": "❓",
        "tier": 4,
        "description": "Answer-style draft, value-first, not promotional",
        "max_body_length": 10000,
        "supports_media": True,
        "requires_media": False,
    },
}


def get_ordered_platforms(selected: list[Platform]) -> list[Platform]:
    """Return selected platforms in the recommended publish order."""
    return [p for p in DEFAULT_PUBLISH_ORDER if p in selected]
