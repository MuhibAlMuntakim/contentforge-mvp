"""
Reusable Streamlit UI components for ContentForge.

These helper functions keep the main streamlit_app.py clean by encapsulating
repeated UI patterns and formatting logic.
"""

from __future__ import annotations

import streamlit as st
from core.models import Platform, PublishStatus, ValidationSeverity
from core.crew import ContentStatus
from config.platforms import PLATFORM_INFO


# ── Status badges ────────────────────────────────────────────────────────────

STATUS_COLORS = {
    PublishStatus.PUBLISHED: "🟢",
    PublishStatus.DRAFT_CREATED: "🟡",
    PublishStatus.REVIEW_REQUIRED: "🟠",
    PublishStatus.FAILED: "🔴",
    PublishStatus.SKIPPED: "⚪",
    PublishStatus.PENDING: "⏳",
    PublishStatus.IN_PROGRESS: "🔵",
}

CONTENT_STATUS_COLORS = {
    ContentStatus.APPROVED: "✅",
    ContentStatus.NEEDS_REVIEW: "⚠️",
    ContentStatus.BLOCKED: "🚫",
}

SEVERITY_ICONS = {
    ValidationSeverity.ERROR: "❌",
    ValidationSeverity.WARNING: "⚠️",
    ValidationSeverity.INFO: "ℹ️",
}


def status_badge(status: PublishStatus) -> str:
    """Return an emoji + label for a publish status."""
    icon = STATUS_COLORS.get(status, "❓")
    return f"{icon} {status.value.replace('_', ' ').title()}"


def content_status_badge(status: ContentStatus) -> str:
    """Return an emoji + label for a content status."""
    icon = CONTENT_STATUS_COLORS.get(status, "❓")
    return f"{icon} {status.value.replace('_', ' ').title()}"


def platform_label(platform: Platform) -> str:
    """Return a formatted label with icon for a platform."""
    info = PLATFORM_INFO.get(platform, {})
    icon = info.get("icon", "📱")
    label = info.get("label", platform.value.title())
    tier = info.get("tier", "?")
    return f"{icon} {label} (T{tier})"


def show_validation_issues(issues: list, title: str = "Validation Results"):
    """Display validation issues with appropriate styling."""
    if not issues:
        st.success("✅ All validation checks passed!")
        return

    for issue in issues:
        icon = SEVERITY_ICONS.get(issue.severity, "❓")
        platform_tag = f" [{issue.platform.value}]" if issue.platform else ""
        if issue.severity == ValidationSeverity.ERROR:
            st.error(f"{icon} **{issue.field}**{platform_tag}: {issue.message}")
        elif issue.severity == ValidationSeverity.WARNING:
            st.warning(f"{icon} **{issue.field}**{platform_tag}: {issue.message}")
        else:
            st.info(f"{icon} **{issue.field}**{platform_tag}: {issue.message}")
