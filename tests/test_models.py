"""Tests for Pydantic data models."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from datetime import datetime, timezone

from core.models import (
    ContentPackage,
    Platform,
    PlatformPayload,
    PublishMode,
    PublishResult,
    PublishStatus,
    ApprovalStatus,
    AuditReport,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class TestContentPackage:

    def test_creates_with_defaults(self):
        pkg = ContentPackage(title="Test Title")
        assert pkg.title == "Test Title"
        assert pkg.content_id  # auto-generated
        assert pkg.publish_mode == PublishMode.DRAFT_ONLY
        assert pkg.approval_status == ApprovalStatus.PENDING
        assert isinstance(pkg.created_at, datetime)

    def test_all_fields(self):
        pkg = ContentPackage(
            campaign_name="Test Campaign",
            title="Title",
            long_body="Long body text",
            short_caption="Short caption",
            cta="Sign up now",
            links=["https://example.com"],
            hashtags=["#test", "#content"],
            keywords=["content", "marketing"],
            target_platforms=[Platform.LINKEDIN, Platform.TWITTER],
            publish_mode=PublishMode.PUBLISH_NOW,
            owner="test_user",
            notes="Test notes",
        )
        assert pkg.campaign_name == "Test Campaign"
        assert len(pkg.target_platforms) == 2
        assert Platform.LINKEDIN in pkg.target_platforms

    def test_serialization_roundtrip(self):
        pkg = ContentPackage(
            title="Roundtrip Test",
            target_platforms=[Platform.MEDIUM],
        )
        json_str = pkg.model_dump_json()
        restored = ContentPackage.model_validate_json(json_str)
        assert restored.title == "Roundtrip Test"
        assert restored.content_id == pkg.content_id

    def test_unique_content_ids(self):
        pkg1 = ContentPackage(title="A")
        pkg2 = ContentPackage(title="B")
        assert pkg1.content_id != pkg2.content_id


class TestPlatformPayload:

    def test_creates_with_platform(self):
        payload = PlatformPayload(
            platform=Platform.LINKEDIN,
            content_id="test-123",
            title="LinkedIn post",
            body="Professional content",
        )
        assert payload.platform == Platform.LINKEDIN
        assert payload.title == "LinkedIn post"

    def test_summary(self):
        payload = PlatformPayload(
            platform=Platform.TWITTER,
            content_id="test-123",
            body="Tweet body content",
            hashtags=["#tech"],
        )
        summary = payload.summary()
        assert "Body:" in summary
        assert "#tech" in summary

    def test_empty_summary(self):
        payload = PlatformPayload(
            platform=Platform.SNAPCHAT,
            content_id="test-123",
        )
        assert payload.summary() == "(empty payload)"


class TestPublishResult:

    def test_creates_with_status(self):
        result = PublishResult(
            content_id="test-123",
            platform=Platform.MEDIUM,
            status=PublishStatus.PUBLISHED,
        )
        assert result.status == PublishStatus.PUBLISHED
        assert result.timestamp

    def test_failed_result(self):
        result = PublishResult(
            content_id="test-123",
            platform=Platform.FACEBOOK,
            status=PublishStatus.FAILED,
            error_message="API error",
            retryable=True,
        )
        assert result.error_message == "API error"
        assert result.retryable


class TestValidationResult:

    def test_valid_result(self):
        result = ValidationResult(is_valid=True, issues=[])
        assert result.is_valid
        assert len(result.errors) == 0

    def test_with_issues(self):
        result = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    field="title",
                    message="Required",
                    severity=ValidationSeverity.ERROR,
                ),
                ValidationIssue(
                    field="links",
                    message="Consider adding",
                    severity=ValidationSeverity.WARNING,
                ),
            ],
        )
        assert not result.is_valid
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestAuditReport:

    def test_creates_with_defaults(self):
        report = AuditReport(
            content_id="test-123",
            publish_mode=PublishMode.DRAFT_ONLY,
        )
        assert report.report_id
        assert report.content_id == "test-123"
        assert report.succeeded == 0
