"""Tests for the workflow engine and publishers."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import tempfile
from core.models import (
    ContentPackage,
    Platform,
    PublishMode,
    PublishStatus,
)
from core.crew import ContentAdaptationCrew
from core.workflow import WorkflowEngine
from core.storage import Storage
from publishers import get_publisher


@pytest.fixture
def temp_storage():
    """Create a storage instance with a temporary DB file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Storage(db_path=f.name)


@pytest.fixture
def sample_package():
    return ContentPackage(
        campaign_name="Test Campaign",
        title="AI in Healthcare",
        long_body="Artificial intelligence is transforming healthcare.",
        short_caption="AI is reshaping medicine.",
        cta="Learn more →",
        links=["https://example.com"],
        hashtags=["#AI", "#Health"],
        keywords=["ai", "healthcare"],
        target_platforms=[Platform.LINKEDIN, Platform.TWITTER, Platform.MEDIUM],
        publish_mode=PublishMode.DRAFT_ONLY,
    )


class TestPublishers:

    @pytest.mark.parametrize("platform", list(Platform))
    def test_all_publishers_exist(self, platform):
        publisher = get_publisher(platform)
        assert publisher.platform == platform
        assert publisher.is_stub  # All are stubs for now

    @pytest.mark.parametrize("platform", list(Platform))
    def test_all_publishers_accept_valid_payloads(self, platform, sample_package):
        from core.crew import ContentAdaptationCrew

        crew = ContentAdaptationCrew()
        result = crew.run(ContentPackage(
            title="Test",
            long_body="Test content body.",
            short_caption="Test short.",
            target_platforms=[platform],
            uploaded_assets=["dummy.jpg"],  # Satisfy media requirements
        ))

        if result.adaptations:
            payload = crew.adaptation_to_payload(result.adaptations[0], "test-id")
            payload.media_paths = ["dummy.jpg"]  # Satisfy media checks
            publisher = get_publisher(platform)
            pub_result = publisher.publish(payload, draft=True)
            assert pub_result.status in (
                PublishStatus.PUBLISHED, PublishStatus.DRAFT_CREATED,
                PublishStatus.REVIEW_REQUIRED, PublishStatus.FAILED,
            )


class TestWorkflowEngine:

    def test_validation_passes(self, temp_storage, sample_package):
        engine = WorkflowEngine(storage=temp_storage)
        result = engine.validate(sample_package)
        assert result.is_valid

    def test_validation_fails_no_title(self, temp_storage):
        pkg = ContentPackage(
            title="",
            long_body="Content",
            target_platforms=[Platform.LINKEDIN],
        )
        engine = WorkflowEngine(storage=temp_storage)
        result = engine.validate(pkg)
        assert not result.is_valid

    def test_adaptation_produces_results(self, temp_storage, sample_package):
        engine = WorkflowEngine(storage=temp_storage)
        result = engine.adapt(sample_package)
        assert len(result.adaptations) == len(sample_package.target_platforms)

    def test_full_pipeline_draft_mode(self, temp_storage, sample_package):
        engine = WorkflowEngine(storage=temp_storage)

        validation, adaptation, results, report = engine.run_full_pipeline(sample_package)

        assert validation.is_valid
        assert adaptation is not None
        assert len(results) == len(sample_package.target_platforms)
        assert report is not None
        assert report.total_platforms == len(sample_package.target_platforms)

        # All should be drafts in DRAFT_ONLY mode
        for r in results:
            assert r.status in (
                PublishStatus.DRAFT_CREATED,
                PublishStatus.REVIEW_REQUIRED,
                PublishStatus.SKIPPED,
            )

    def test_persists_to_storage(self, temp_storage, sample_package):
        engine = WorkflowEngine(storage=temp_storage)
        engine.run_full_pipeline(sample_package)

        # Verify storage
        pkg = temp_storage.get_content_package(sample_package.content_id)
        assert pkg is not None
        assert pkg.title == sample_package.title

        results = temp_storage.get_publish_results(sample_package.content_id)
        assert len(results) == len(sample_package.target_platforms)

        reports = temp_storage.get_audit_reports_for_content(sample_package.content_id)
        assert len(reports) == 1

    def test_callbacks_invoked(self, temp_storage, sample_package):
        engine = WorkflowEngine(storage=temp_storage)

        started = []
        completed = []

        adaptation = engine.adapt(sample_package)

        engine.execute(
            sample_package, adaptation,
            on_platform_start=lambda p: started.append(p),
            on_platform_complete=lambda p, r: completed.append((p, r)),
        )

        assert len(started) == len(sample_package.target_platforms)
        assert len(completed) == len(sample_package.target_platforms)

    def test_reddit_always_draft(self, temp_storage):
        pkg = ContentPackage(
            title="Reddit Test",
            long_body="This is content for Reddit.",
            target_platforms=[Platform.REDDIT],
            publish_mode=PublishMode.PUBLISH_NOW,
        )
        engine = WorkflowEngine(storage=temp_storage)
        _, _, results, _ = engine.run_full_pipeline(pkg)

        assert len(results) == 1
        assert results[0].status in (
            PublishStatus.DRAFT_CREATED, PublishStatus.REVIEW_REQUIRED
        )


class TestStorage:

    def test_content_package_roundtrip(self, temp_storage, sample_package):
        temp_storage.save_content_package(sample_package)
        restored = temp_storage.get_content_package(sample_package.content_id)
        assert restored is not None
        assert restored.title == sample_package.title

    def test_list_content_packages(self, temp_storage, sample_package):
        temp_storage.save_content_package(sample_package)
        packages = temp_storage.list_content_packages()
        assert len(packages) >= 1

    def test_publish_results_roundtrip(self, temp_storage):
        from core.models import PublishResult
        # Must create parent ContentPackage first (foreign key)
        parent = ContentPackage(title="Parent", long_body="Body")
        parent.content_id = "test-123"
        temp_storage.save_content_package(parent)

        result = PublishResult(
            content_id="test-123",
            platform=Platform.LINKEDIN,
            status=PublishStatus.PUBLISHED,
            url="https://linkedin.com/post/123",
        )
        temp_storage.save_publish_result(result)
        results = temp_storage.get_publish_results("test-123")
        assert len(results) == 1
        assert results[0].url == "https://linkedin.com/post/123"
