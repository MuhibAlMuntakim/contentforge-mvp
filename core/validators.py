"""
Validation layer for content packages.

Validates content completeness, format correctness, and platform compatibility
before any publishing workflow begins. All issues are returned as structured
ValidationResult objects for display in the Streamlit UI.
"""

from __future__ import annotations

import re
from typing import Optional

from core.models import (
    ContentPackage,
    Platform,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from config.platforms import PLATFORM_INFO, TIER_4_DRAFT_FIRST


# ── URL pattern (simple, intentionally permissive) ───────────────────────────
URL_PATTERN = re.compile(
    r"^https?://"
    r"[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*"
    r"(/[^\s]*)?$"
)


def validate_content_package(
    package: ContentPackage,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate a content package for completeness and publishability.

    Args:
        package: The content package to validate.
        strict: If True, treat warnings as errors.

    Returns:
        ValidationResult with all issues found.
    """
    issues: list[ValidationIssue] = []

    # ── Required fields ──────────────────────────────────────────────────
    if not package.title or not package.title.strip():
        issues.append(ValidationIssue(
            field="title",
            message="Title is required.",
            severity=ValidationSeverity.ERROR,
        ))

    if not package.long_body and not package.short_caption:
        issues.append(ValidationIssue(
            field="long_body",
            message="At least one of long body or short caption is required.",
            severity=ValidationSeverity.ERROR,
        ))

    if not package.target_platforms:
        issues.append(ValidationIssue(
            field="target_platforms",
            message="At least one target platform must be selected.",
            severity=ValidationSeverity.ERROR,
        ))

    # ── Link format validation ───────────────────────────────────────────
    for i, link in enumerate(package.links):
        if not URL_PATTERN.match(link.strip()):
            issues.append(ValidationIssue(
                field=f"links[{i}]",
                message=f"Invalid URL format: '{link}'",
                severity=ValidationSeverity.ERROR,
            ))

    # ── Content length sanity ────────────────────────────────────────────
    if package.title and len(package.title) > 500:
        issues.append(ValidationIssue(
            field="title",
            message=f"Title is unusually long ({len(package.title)} chars). Consider shortening.",
            severity=ValidationSeverity.WARNING,
        ))

    if package.long_body and len(package.long_body) > 200_000:
        issues.append(ValidationIssue(
            field="long_body",
            message="Long body exceeds 200,000 characters. This may cause issues.",
            severity=ValidationSeverity.WARNING,
        ))

    # ── Per-platform compatibility checks ────────────────────────────────
    for platform in package.target_platforms:
        pinfo = PLATFORM_INFO.get(platform)
        if not pinfo:
            issues.append(ValidationIssue(
                field="target_platforms",
                message=f"Unknown platform: {platform.value}",
                severity=ValidationSeverity.ERROR,
                platform=platform,
            ))
            continue

        # Check if media is required but not provided
        if pinfo.get("requires_media") and not package.uploaded_assets:
            issues.append(ValidationIssue(
                field="uploaded_assets",
                message=f"{pinfo['label']} requires media assets, but none were uploaded.",
                severity=ValidationSeverity.WARNING,
                platform=platform,
            ))

        # Check body length limits
        max_len = pinfo.get("max_body_length", 100000)
        body_text = package.short_caption if platform == Platform.TWITTER else package.long_body
        if body_text and len(body_text) > max_len:
            issues.append(ValidationIssue(
                field="long_body" if body_text == package.long_body else "short_caption",
                message=(
                    f"Content exceeds {pinfo['label']} max length "
                    f"({len(body_text)}/{max_len} chars). It will be truncated."
                ),
                severity=ValidationSeverity.WARNING,
                platform=platform,
            ))

    # ── Approval flag checks ────────────────────────────────────────────
    from core.models import PublishMode

    if package.publish_mode == PublishMode.PUBLISH_NOW:
        draft_platforms = [
            p for p in package.target_platforms if p in TIER_4_DRAFT_FIRST
        ]
        if draft_platforms:
            names = ", ".join(PLATFORM_INFO[p]["label"] for p in draft_platforms)
            issues.append(ValidationIssue(
                field="publish_mode",
                message=(
                    f"{names} will be set to draft/review mode even in "
                    f"'Publish Now' mode (Tier 4 safety policy)."
                ),
                severity=ValidationSeverity.INFO,
            ))

    # ── Campaign name suggestion ─────────────────────────────────────────
    if not package.campaign_name:
        issues.append(ValidationIssue(
            field="campaign_name",
            message="No campaign name set. Consider adding one for tracking.",
            severity=ValidationSeverity.INFO,
        ))

    # ── Hashtag format ───────────────────────────────────────────────────
    for i, tag in enumerate(package.hashtags):
        if tag and not tag.startswith("#"):
            issues.append(ValidationIssue(
                field=f"hashtags[{i}]",
                message=f"Hashtag '{tag}' should start with '#'. It will be auto-corrected.",
                severity=ValidationSeverity.INFO,
            ))

    # ── Determine overall validity ───────────────────────────────────────
    if strict:
        is_valid = not any(
            i.severity in (ValidationSeverity.ERROR, ValidationSeverity.WARNING)
            for i in issues
        )
    else:
        is_valid = not any(
            i.severity == ValidationSeverity.ERROR for i in issues
        )

    return ValidationResult(is_valid=is_valid, issues=issues)
