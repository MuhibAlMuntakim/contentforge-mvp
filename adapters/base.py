"""
Abstract base class for platform adapters.

Every platform adapter must implement the `adapt` method, which transforms
a master ContentPackage into a platform-specific PlatformPayload.

The adapter is ONLY responsible for content transformation — never publishing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import ContentPackage, PlatformPayload, Platform


class BaseAdapter(ABC):
    """Abstract base for all platform content adapters."""

    platform: Platform

    @abstractmethod
    def adapt(self, package: ContentPackage) -> PlatformPayload:
        """
        Transform a master content package into a platform-specific payload.

        Args:
            package: The master content package.

        Returns:
            A PlatformPayload tailored for this adapter's platform.
        """
        ...

    def _normalize_hashtags(self, tags: list[str]) -> list[str]:
        """Ensure all hashtags start with '#'."""
        return [t if t.startswith("#") else f"#{t}" for t in tags if t.strip()]

    def _truncate(self, text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max_length, appending suffix if truncated."""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix
