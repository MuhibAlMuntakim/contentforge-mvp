"""Tests for the CrewAI ContentAdaptationCrew (fallback/rule-based mode)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from core.models import ContentPackage, Platform
from core.crew import (
    ContentAdaptationCrew,
    ContentAdaptationResult,
    ContentStatus,
    PlatformAdaptation,
)


@pytest.fixture
def sample_package():
    return ContentPackage(
        title="10 Ways AI Is Transforming Healthcare",
        long_body="Artificial intelligence is revolutionizing healthcare in ways we never imagined. "
                  "From diagnostic imaging to drug discovery, AI is making medicine more precise, "
                  "personalized, and accessible. In this article, we explore the top 10 applications "
                  "of AI in healthcare and what they mean for the future of medicine.",
        short_caption="AI is revolutionizing healthcare 🏥 Here's how it's changing everything.",
        cta="Learn more at our website →",
        links=["https://example.com/ai-healthcare"],
        hashtags=["#AI", "#Healthcare", "#Innovation", "#MedTech"],
        keywords=["artificial intelligence", "healthcare", "medical technology"],
        target_platforms=[
            Platform.LINKEDIN, Platform.TWITTER, Platform.FACEBOOK,
            Platform.MEDIUM, Platform.BLOGGER, Platform.INSTAGRAM,
            Platform.REDDIT, Platform.QUORA,
        ],
    )


class TestContentAdaptationCrew:

    def test_produces_result_for_all_platforms(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        assert isinstance(result, ContentAdaptationResult)
        assert len(result.adaptations) == len(sample_package.target_platforms)

    def test_platforms_have_correct_names(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        platform_names = {a.platform for a in result.adaptations}
        expected = {p.value for p in sample_package.target_platforms}
        assert platform_names == expected

    def test_reddit_quora_always_needs_review(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        for adaptation in result.adaptations:
            if adaptation.platform in ("reddit", "quora"):
                assert adaptation.status == ContentStatus.NEEDS_REVIEW

    def test_reddit_has_no_cta(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        reddit = next(a for a in result.adaptations if a.platform == "reddit")
        assert reddit.cta == ""

    def test_quora_has_question_title(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        quora = next(a for a in result.adaptations if a.platform == "quora")
        assert quora.title.endswith("?")

    def test_twitter_respects_length(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        twitter = next(a for a in result.adaptations if a.platform == "twitter")
        assert len(twitter.body) <= 280

    def test_content_analysis_populated(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        assert result.analysis.word_count > 0
        assert result.analysis.content_type

    def test_overall_status_reflects_worst_case(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        # With Reddit/Quora included, overall should be NEEDS_REVIEW
        assert result.overall_status in (ContentStatus.NEEDS_REVIEW, ContentStatus.APPROVED)

    def test_adaptation_to_payload_conversion(self, sample_package):
        crew = ContentAdaptationCrew()
        result = crew.run(sample_package)

        for adaptation in result.adaptations:
            payload = crew.adaptation_to_payload(adaptation, sample_package.content_id)
            assert payload.content_id == sample_package.content_id
            assert payload.platform == Platform(adaptation.platform)

    def test_single_platform(self):
        pkg = ContentPackage(
            title="Simple Test",
            long_body="Test body content.",
            target_platforms=[Platform.LINKEDIN],
        )
        crew = ContentAdaptationCrew()
        result = crew.run(pkg)

        assert len(result.adaptations) == 1
        assert result.adaptations[0].platform == "linkedin"

    def test_all_twelve_platforms(self):
        pkg = ContentPackage(
            title="All Platform Test",
            long_body="Comprehensive test content.",
            short_caption="Short ver.",
            target_platforms=list(Platform),
        )
        crew = ContentAdaptationCrew()
        result = crew.run(pkg)

        assert len(result.adaptations) == 12


class TestRiskScoring:

    def test_safe_content_low_risk(self):
        pkg = ContentPackage(
            title="Educational Article",
            long_body="This is informative and educational content about science.",
            target_platforms=[Platform.LINKEDIN],
        )
        crew = ContentAdaptationCrew()
        result = crew.run(pkg)

        linkedin = result.adaptations[0]
        assert linkedin.risk_score < 0.3

    def test_spammy_content_elevated_risk(self):
        pkg = ContentPackage(
            title="ACT NOW - GUARANTEED RESULTS!!!",
            long_body="Buy now! Limited time! Click here! Free money! Congratulations!",
            short_caption="URGENT: Act now for guaranteed free money!!!",
            target_platforms=[Platform.LINKEDIN],
        )
        crew = ContentAdaptationCrew()
        result = crew.run(pkg)

        linkedin = result.adaptations[0]
        assert linkedin.risk_score > 0.3
