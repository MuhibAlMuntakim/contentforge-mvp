"""Tests for the validation layer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from core.models import ContentPackage, Platform, PublishMode, ValidationSeverity
from core.validators import validate_content_package


class TestValidation:

    def test_valid_package(self):
        pkg = ContentPackage(
            title="Valid Title",
            long_body="This is a valid body with enough content.",
            target_platforms=[Platform.LINKEDIN],
        )
        result = validate_content_package(pkg)
        assert result.is_valid

    def test_missing_title(self):
        pkg = ContentPackage(
            title="",
            long_body="Some content",
            target_platforms=[Platform.LINKEDIN],
        )
        result = validate_content_package(pkg)
        assert not result.is_valid
        assert any(i.field == "title" for i in result.errors)

    def test_missing_body_and_caption(self):
        pkg = ContentPackage(
            title="Title",
            long_body="",
            short_caption="",
            target_platforms=[Platform.TWITTER],
        )
        result = validate_content_package(pkg)
        assert not result.is_valid
        assert any("body" in i.field or "caption" in i.field for i in result.errors)

    def test_no_platforms_selected(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[],
        )
        result = validate_content_package(pkg)
        assert not result.is_valid
        assert any(i.field == "target_platforms" for i in result.errors)

    def test_invalid_url_format(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[Platform.LINKEDIN],
            links=["not-a-url", "https://valid.com"],
        )
        result = validate_content_package(pkg)
        assert any(
            i.field.startswith("links") and i.severity == ValidationSeverity.ERROR
            for i in result.issues
        )

    def test_valid_url_passes(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[Platform.LINKEDIN],
            links=["https://example.com/page?q=1"],
        )
        result = validate_content_package(pkg)
        assert not any(
            i.field.startswith("links") and i.severity == ValidationSeverity.ERROR
            for i in result.issues
        )

    def test_media_required_warning(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[Platform.INSTAGRAM],
            uploaded_assets=[],
        )
        result = validate_content_package(pkg)
        assert any(
            i.platform == Platform.INSTAGRAM and i.severity == ValidationSeverity.WARNING
            for i in result.issues
        )

    def test_publish_now_with_tier4_info(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[Platform.REDDIT, Platform.LINKEDIN],
            publish_mode=PublishMode.PUBLISH_NOW,
        )
        result = validate_content_package(pkg)
        assert any(
            i.field == "publish_mode" and i.severity == ValidationSeverity.INFO
            for i in result.issues
        )

    def test_hashtag_format_info(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[Platform.LINKEDIN],
            hashtags=["notag", "#valid"],
        )
        result = validate_content_package(pkg)
        assert any(
            i.field.startswith("hashtags") and i.severity == ValidationSeverity.INFO
            for i in result.issues
        )

    def test_campaign_name_info(self):
        pkg = ContentPackage(
            title="Title",
            long_body="Content",
            target_platforms=[Platform.TWITTER],
            campaign_name="",
        )
        result = validate_content_package(pkg)
        assert any(
            i.field == "campaign_name" and i.severity == ValidationSeverity.INFO
            for i in result.issues
        )

    def test_long_title_warning(self):
        pkg = ContentPackage(
            title="x" * 600,
            long_body="Content",
            target_platforms=[Platform.MEDIUM],
        )
        result = validate_content_package(pkg)
        assert any(
            i.field == "title" and i.severity == ValidationSeverity.WARNING
            for i in result.issues
        )
