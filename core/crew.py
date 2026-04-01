"""
ContentAdaptationCrew — CrewAI-powered content intelligence layer.

This crew handles ONLY content intelligence:
  - Content analysis (themes, audience, key messages)
  - Platform-specific adaptation (tone, format, length)
  - Tone transformation (professional, casual, community-safe, etc.)
  - Compliance / risk checks (spam detection, guideline adherence)

This crew does NOT:
  - Call external APIs
  - Handle publishing
  - Manage workflow execution

When LLM credentials are not available, the crew falls back to a deterministic
rule-based adapter that produces structured output without AI calls.

Design decision: The crew returns a single ContentAdaptationResult Pydantic model
containing per-platform adapted content + status flags (approved / needs_review / blocked).
"""

from __future__ import annotations

import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from core.models import ContentPackage, Platform, PlatformPayload

# Load .env before any credential checks
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)


# ── Output schemas ───────────────────────────────────────────────────────────

class ContentStatus(str, Enum):
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class PlatformAdaptation(BaseModel):
    """Adapted content for a single platform, output by the crew."""
    platform: str
    title: str = ""
    body: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    cta: str = ""
    tone: str = ""
    format_type: str = ""
    status: ContentStatus = ContentStatus.APPROVED
    status_reason: str = ""
    compliance_notes: list[str] = Field(default_factory=list)
    risk_score: float = 0.0  # 0.0 = safe, 1.0 = high risk


class ContentAnalysis(BaseModel):
    """Analysis of the master content."""
    key_themes: list[str] = Field(default_factory=list)
    target_audience: str = ""
    primary_message: str = ""
    content_type: str = ""  # article, announcement, tutorial, etc.
    sentiment: str = ""  # positive, neutral, negative
    word_count: int = 0


class ContentAdaptationResult(BaseModel):
    """Complete output from the ContentAdaptationCrew."""
    content_id: str
    analysis: ContentAnalysis
    adaptations: list[PlatformAdaptation] = Field(default_factory=list)
    overall_status: ContentStatus = ContentStatus.APPROVED
    overall_notes: str = ""


# ── Platform tone/format configuration ───────────────────────────────────────

PLATFORM_TONE_CONFIG: dict[str, dict[str, str]] = {
    "linkedin": {"tone": "professional", "format": "post", "style": "concise but informative"},
    "twitter": {"tone": "conversational", "format": "short_form", "style": "punchy and engaging"},
    "facebook": {"tone": "brand-friendly", "format": "social_post", "style": "warm and approachable"},
    "medium": {"tone": "authoritative", "format": "article", "style": "long-form educational"},
    "blogger": {"tone": "informative", "format": "blog_post", "style": "structured article with headers"},
    "youtube": {"tone": "engaging", "format": "video_description", "style": "SEO-optimized with timestamps"},
    "instagram": {"tone": "casual", "format": "caption", "style": "hook-first, hashtag-rich"},
    "pinterest": {"tone": "inspirational", "format": "pin", "style": "keyword-rich, visual-first"},
    "tiktok": {"tone": "trendy", "format": "short_video_caption", "style": "hook-oriented, casual"},
    "snapchat": {"tone": "ephemeral", "format": "snap", "style": "ultra-short, media-first"},
    "reddit": {"tone": "community-safe", "format": "text_post", "style": "value-first, non-promotional"},
    "quora": {"tone": "educational", "format": "answer", "style": "expert answer, non-promotional"},
}

# Platforms that always require human review
REVIEW_REQUIRED_PLATFORMS = {"reddit", "quora"}

# Content risk keywords (basic heuristic for fallback mode)
RISK_KEYWORDS = [
    "guaranteed", "act now", "limited time", "buy now", "free money",
    "click here", "urgent", "congratulations", "winner", "100% free",
]


# ── CrewAI-powered crew ─────────────────────────────────────────────────────

def _has_llm_credentials() -> bool:
    """Check if any LLM API key is configured."""
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )


def _get_llm_model() -> str:
    """
    Determine the LLM model string for CrewAI based on available credentials.
    CrewAI uses LiteLLM under the hood, so we use the LiteLLM model format.
    """
    if os.getenv("GEMINI_API_KEY"):
        return "gemini/gemini-2.5-flash"
    elif os.getenv("GOOGLE_API_KEY"):
        return "gemini/gemini-2.5-flash"
    elif os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o"
    elif os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic/claude-sonnet-4-20250514"
    return "gemini/gemini-2.5-flash"  # default


def _build_crewai_crew(
    master_content: dict,
    target_platforms: list[str],
) -> ContentAdaptationResult:
    """
    Run the actual CrewAI crew with LLM agents.
    Only called when LLM credentials are available.
    """
    from crewai import Agent, Crew, Process, Task

    platform_list = ", ".join(target_platforms)
    platform_configs = json.dumps(
        {p: PLATFORM_TONE_CONFIG.get(p, {}) for p in target_platforms},
        indent=2,
    )

    llm_model = _get_llm_model()
    logger.info(f"Using LLM model: {llm_model}")

    # ── Agent 1: Content Analyst ─────────────────────────────────────────
    content_analyst = Agent(
        role="Content Analyst",
        goal=(
            "Analyze the master content to extract key themes, target audience, "
            "primary message, content type, and sentiment."
        ),
        backstory=(
            "You are a senior content strategist with expertise in analyzing "
            "content for multi-platform distribution. You identify the core "
            "message, target audience, and emotional tone of any content."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm_model,
    )

    # ── Agent 2: Platform Adapter ────────────────────────────────────────
    platform_adapter = Agent(
        role="Platform Content Adapter",
        goal=(
            f"Transform the master content into optimized variants for each "
            f"target platform: {platform_list}. Each variant must match the "
            f"platform's tone, format, and character limits."
        ),
        backstory=(
            "You are an expert social media and content manager who has "
            "managed publishing across all major platforms. You know the "
            "exact tone, format, character limits, and best practices for "
            "LinkedIn, Twitter/X, Facebook, Medium, Blogger, YouTube, "
            "Instagram, Pinterest, TikTok, Snapchat, Reddit, and Quora."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm_model,
    )

    # ── Agent 3: Tone Specialist ─────────────────────────────────────────
    tone_specialist = Agent(
        role="Tone & Voice Specialist",
        goal=(
            "Review and refine each platform variant to ensure the tone "
            "matches the platform's culture and audience expectations."
        ),
        backstory=(
            "You are a brand voice consultant who ensures every piece of "
            "content matches the intended platform culture. You adjust "
            "formality, emoji usage, hashtag density, CTA style, and "
            "promotional intensity per platform."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm_model,
    )

    # ── Agent 4: Compliance Checker ──────────────────────────────────────
    compliance_checker = Agent(
        role="Content Compliance & Risk Analyst",
        goal=(
            "Review all platform variants for compliance risks, spam "
            "signals, guideline violations, and community safety issues. "
            "Flag content that needs review or should be blocked."
        ),
        backstory=(
            "You are a content moderation expert who reviews content for "
            "platform guideline compliance, spam risk, and community safety. "
            "You identify promotional overreach, misleading claims, and "
            "content that could get flagged or banned on specific platforms. "
            "Reddit and Quora content should always be flagged as needs_review."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm_model,
    )

    # ── Task 1: Analyze content ──────────────────────────────────────────
    analysis_task = Task(
        description=(
            f"Analyze the following master content and produce a content analysis:\n\n"
            f"Title: {master_content.get('title', '')}\n"
            f"Body: {master_content.get('long_body', '')[:2000]}\n"
            f"Caption: {master_content.get('short_caption', '')}\n"
            f"CTA: {master_content.get('cta', '')}\n"
            f"Keywords: {', '.join(master_content.get('keywords', []))}\n\n"
            f"Extract: key themes, target audience, primary message, content type, sentiment, word count."
        ),
        expected_output=(
            "A JSON object with fields: key_themes (list), target_audience (string), "
            "primary_message (string), content_type (string), sentiment (string), word_count (int)."
        ),
        agent=content_analyst,
        output_json=ContentAnalysis,
    )

    # ── Task 2: Adapt for platforms ──────────────────────────────────────
    adaptation_task = Task(
        description=(
            f"Using the content analysis, create optimized content variants for "
            f"these platforms: {platform_list}.\n\n"
            f"Platform-specific configuration:\n{platform_configs}\n\n"
            f"Master content:\n"
            f"Title: {master_content.get('title', '')}\n"
            f"Body: {master_content.get('long_body', '')[:3000]}\n"
            f"Caption: {master_content.get('short_caption', '')}\n"
            f"CTA: {master_content.get('cta', '')}\n"
            f"Links: {json.dumps(master_content.get('links', []))}\n"
            f"Hashtags: {json.dumps(master_content.get('hashtags', []))}\n\n"
            f"For each platform produce: title, body, caption, hashtags, tags, "
            f"links, cta, tone, format_type. Respect character limits."
        ),
        expected_output=(
            f"A JSON array of objects, one per platform ({platform_list}). "
            f"Each object has: platform, title, body, caption, hashtags, tags, "
            f"links, cta, tone, format_type."
        ),
        agent=platform_adapter,
        context=[analysis_task],
    )

    # ── Task 3: Refine tone ──────────────────────────────────────────────
    tone_task = Task(
        description=(
            "Review each platform variant from the previous task and refine the "
            "tone to perfectly match platform culture:\n"
            "- LinkedIn: professional, no excessive emojis\n"
            "- Twitter/X: punchy, conversational\n"
            "- Facebook: warm, brand-friendly\n"
            "- Medium/Blogger: authoritative, long-form\n"
            "- YouTube: engaging, SEO keywords in description\n"
            "- Instagram: hook-first, emoji-friendly, hashtag-rich\n"
            "- Pinterest: inspirational, keyword-dense\n"
            "- TikTok: trendy, hook-oriented\n"
            "- Snapchat: ultra-brief, media-first\n"
            "- Reddit: conversational, NO promotional tone, no CTAs\n"
            "- Quora: educational, answer-style, value-first\n\n"
            "Return the refined variants with the same structure."
        ),
        expected_output=(
            "A JSON array of refined platform content objects with same structure as input."
        ),
        agent=tone_specialist,
        context=[adaptation_task],
    )

    # ── Task 4: Compliance check ─────────────────────────────────────────
    compliance_task = Task(
        description=(
            "Review ALL platform variants for compliance and risk:\n"
            "1. Check for spam signals (excessive CTAs, clickbait, misleading claims)\n"
            "2. Check for platform guideline violations\n"
            "3. Check hashtag appropriateness\n"
            "4. Reddit and Quora must ALWAYS be marked as 'needs_review'\n"
            "5. Any content with risk score > 0.7 should be 'blocked'\n"
            "6. Any content with risk score > 0.3 should be 'needs_review'\n\n"
            "For each platform variant, set:\n"
            "- status: 'approved', 'needs_review', or 'blocked'\n"
            "- status_reason: explanation\n"
            "- compliance_notes: list of specific findings\n"
            "- risk_score: 0.0 to 1.0\n\n"
            f"Content ID: {master_content.get('content_id', 'unknown')}"
        ),
        expected_output=(
            "A JSON object with: content_id, analysis (from task 1), "
            "adaptations (array of platform objects with status flags), "
            "overall_status, overall_notes."
        ),
        agent=compliance_checker,
        context=[analysis_task, tone_task],
        output_json=ContentAdaptationResult,
    )

    # ── Build and run the crew ───────────────────────────────────────────
    crew = Crew(
        agents=[content_analyst, platform_adapter, tone_specialist, compliance_checker],
        tasks=[analysis_task, adaptation_task, tone_task, compliance_task],
        process=Process.sequential,
        verbose=False,
    )

    logger.info("Running ContentAdaptationCrew with LLM agents...")
    result = crew.kickoff()

    # Parse the structured output
    if hasattr(result, "json_dict") and result.json_dict:
        return ContentAdaptationResult.model_validate(result.json_dict)
    elif hasattr(result, "raw"):
        try:
            parsed = json.loads(result.raw)
            return ContentAdaptationResult.model_validate(parsed)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse CrewAI output, falling back: {e}")
            return _fallback_adaptation(master_content, target_platforms)
    else:
        logger.warning("No structured output from CrewAI, using fallback")
        return _fallback_adaptation(master_content, target_platforms)


# ── Deterministic fallback (no LLM required) ────────────────────────────────

def _analyze_content(content: dict) -> ContentAnalysis:
    """Rule-based content analysis when no LLM is available."""
    body = content.get("long_body", "")
    title = content.get("title", "")
    caption = content.get("short_caption", "")
    keywords = content.get("keywords", [])
    all_text = f"{title} {body} {caption}"

    # Simple keyword extraction
    themes = keywords[:5] if keywords else []
    if not themes and title:
        themes = [w for w in title.split() if len(w) > 4][:3]

    word_count = len(all_text.split())

    # Determine content type from length
    if word_count > 500:
        content_type = "article"
    elif word_count > 100:
        content_type = "post"
    else:
        content_type = "short_update"

    return ContentAnalysis(
        key_themes=themes,
        target_audience="general",
        primary_message=title or caption or "",
        content_type=content_type,
        sentiment="neutral",
        word_count=word_count,
    )


def _compute_risk_score(text: str, platform: str) -> tuple[float, list[str]]:
    """Simple heuristic risk scoring."""
    notes: list[str] = []
    score = 0.0

    text_lower = text.lower()
    for keyword in RISK_KEYWORDS:
        if keyword in text_lower:
            score += 0.15
            notes.append(f"Contains risk keyword: '{keyword}'")

    # Over-promotion check
    if text_lower.count("!") > 5:
        score += 0.1
        notes.append("Excessive exclamation marks")
    if text_lower.count("http") > 3:
        score += 0.1
        notes.append("Multiple URLs may appear spammy")

    # Platform-specific
    if platform in REVIEW_REQUIRED_PLATFORMS:
        score = max(score, 0.5)  # Always elevated for Reddit/Quora
        notes.append(f"{platform} requires human review per policy")

    return min(score, 1.0), notes


def _adapt_for_platform(
    content: dict,
    platform: str,
    analysis: ContentAnalysis,
) -> PlatformAdaptation:
    """Rule-based adaptation for a single platform."""
    config = PLATFORM_TONE_CONFIG.get(platform, {})
    title = content.get("title", "")
    body = content.get("long_body", "")
    caption = content.get("short_caption", "")
    cta = content.get("cta", "")
    links = content.get("links", [])
    hashtags = content.get("hashtags", [])
    keywords = content.get("keywords", [])

    # Normalize hashtags
    norm_hashtags = [t if t.startswith("#") else f"#{t}" for t in hashtags if t.strip()]

    adapted = PlatformAdaptation(
        platform=platform,
        tone=config.get("tone", "neutral"),
        format_type=config.get("format", "post"),
    )

    # ── Platform-specific formatting ─────────────────────────────────────
    if platform == "linkedin":
        adapted.title = title
        text = body[:2800] if body else caption
        if cta:
            text += f"\n\n{cta}"
        if links:
            text += f"\n\n🔗 {links[0]}"
        if norm_hashtags:
            text += f"\n\n{' '.join(norm_hashtags[:10])}"
        adapted.body = text
        adapted.hashtags = norm_hashtags[:10]

    elif platform == "twitter":
        text = caption or title or ""
        hashtag_str = " ".join(norm_hashtags[:5])
        link_part = f" {links[0]}" if links else ""
        available = 280 - len(hashtag_str) - len(link_part) - 2
        if len(text) > available:
            text = text[:max(available - 3, 20)] + "..."
        full = text
        if link_part:
            full += link_part
        if hashtag_str:
            full += f" {hashtag_str}"
        adapted.body = full[:280]
        adapted.caption = text
        adapted.hashtags = norm_hashtags[:5]

    elif platform == "facebook":
        text = body[:5000] if body else caption
        if cta:
            text += f"\n\n👉 {cta}"
        if links:
            text += f"\n\n🔗 {links[0]}"
        if norm_hashtags:
            text += f"\n\n{' '.join(norm_hashtags[:15])}"
        adapted.title = title
        adapted.body = text
        adapted.hashtags = norm_hashtags[:15]

    elif platform == "medium":
        text = body or caption or ""
        if cta:
            text += f"\n\n---\n\n**{cta}**"
        if links:
            text += "\n\n### Links\n" + "\n".join(f"- {l}" for l in links)
        adapted.title = title
        adapted.body = text
        adapted.tags = keywords[:5]

    elif platform == "blogger":
        text = body or caption or ""
        html = f"<p>{text.replace(chr(10)+chr(10), '</p><p>').replace(chr(10), '<br/>')}</p>"
        if cta:
            html += f"\n<p><strong>{cta}</strong></p>"
        if links:
            html += "\n<h3>Links</h3><ul>" + "".join(f'<li><a href="{l}">{l}</a></li>' for l in links) + "</ul>"
        adapted.title = title
        adapted.body = html
        adapted.tags = keywords[:10]

    elif platform == "youtube":
        desc = body[:4500] if body else caption
        if cta:
            desc += f"\n\n🎯 {cta}"
        desc += "\n\n⏱️ Timestamps:\n0:00 - Intro"
        if links:
            desc += "\n\n📎 Links:\n" + "\n".join(f"  {l}" for l in links)
        if norm_hashtags:
            desc += f"\n\n{' '.join(norm_hashtags[:15])}"
        adapted.title = title[:100]
        adapted.body = desc
        adapted.tags = list(set(keywords + [t.lstrip("#") for t in hashtags]))[:30]
        adapted.hashtags = norm_hashtags[:15]

    elif platform == "instagram":
        hook = caption or title or ""
        parts = [hook]
        if body:
            parts.append(f"\n\n{body[:800]}")
        if cta:
            parts.append(f"\n\n👉 {cta}")
        if links:
            parts.append("\n🔗 Link in bio")
        if norm_hashtags:
            parts.append(f"\n.\n.\n.\n{' '.join(norm_hashtags[:30])}")
        adapted.caption = "\n".join(parts)[:2200]
        adapted.hashtags = norm_hashtags[:30]

    elif platform == "pinterest":
        desc = caption or (body[:400] if body else "")
        if cta:
            desc += f" | {cta}"
        if norm_hashtags:
            desc += f"\n{' '.join(norm_hashtags[:20])}"
        adapted.title = title[:100]
        adapted.body = desc[:500]
        adapted.caption = desc[:500]
        adapted.hashtags = norm_hashtags[:20]
        adapted.links = links[:1]

    elif platform == "tiktok":
        hook = caption or title or ""
        parts = [hook]
        if cta:
            parts.append(cta)
        if norm_hashtags:
            parts.append(" ".join(norm_hashtags[:10]))
        if keywords:
            parts.append(" ".join(f"#{k}" for k in keywords[:5]))
        adapted.caption = "\n".join(parts)[:2200]
        adapted.hashtags = norm_hashtags[:10]

    elif platform == "snapchat":
        text = caption or title or ""
        if len(text) > 200:
            text = text[:197] + "..."
        if cta:
            text += f" | {cta[:40]}"
        adapted.caption = text[:250]
        adapted.links = links[:1]

    elif platform == "reddit":
        parts = []
        if body:
            parts.append(body)
        elif caption:
            parts.append(caption)
        if links:
            parts.append("\n\n---\n\n**Resources:**")
            parts.extend(f"- {l}" for l in links)
        # NO CTA, NO hashtags for Reddit
        adapted.title = title
        adapted.body = "\n".join(parts)
        adapted.cta = ""  # Intentionally stripped

    elif platform == "quora":
        parts = []
        if body:
            parts.append(body)
        elif caption:
            parts.append(caption)
        if links:
            parts.append("\n\n**Further reading:**")
            parts.extend(f"- {l}" for l in links)
        question = title
        if not question.endswith("?"):
            question = f"What should you know about {title.lower()}?"
        adapted.title = question
        adapted.body = "\n".join(parts)
        adapted.tags = keywords[:10]
        adapted.cta = ""  # Intentionally stripped

    else:
        adapted.title = title
        adapted.body = body or caption
        adapted.hashtags = norm_hashtags

    # ── Compliance / risk check ──────────────────────────────────────────
    all_text = f"{adapted.title} {adapted.body} {adapted.caption} {adapted.cta}"
    risk_score, compliance_notes = _compute_risk_score(all_text, platform)
    adapted.risk_score = risk_score
    adapted.compliance_notes = compliance_notes

    if platform in REVIEW_REQUIRED_PLATFORMS:
        adapted.status = ContentStatus.NEEDS_REVIEW
        adapted.status_reason = f"{platform} always requires human review per Tier 4 policy"
    elif risk_score >= 0.7:
        adapted.status = ContentStatus.BLOCKED
        adapted.status_reason = f"High risk score ({risk_score:.2f}): {'; '.join(compliance_notes)}"
    elif risk_score >= 0.3:
        adapted.status = ContentStatus.NEEDS_REVIEW
        adapted.status_reason = f"Moderate risk score ({risk_score:.2f}): {'; '.join(compliance_notes)}"
    else:
        adapted.status = ContentStatus.APPROVED
        adapted.status_reason = "Content passed compliance checks"

    adapted.links = links

    return adapted


def _fallback_adaptation(
    master_content: dict,
    target_platforms: list[str],
) -> ContentAdaptationResult:
    """Deterministic rule-based adaptation — no LLM needed."""
    analysis = _analyze_content(master_content)

    adaptations = [
        _adapt_for_platform(master_content, p, analysis)
        for p in target_platforms
    ]

    # Overall status: worst-case of all platforms
    statuses = [a.status for a in adaptations]
    if ContentStatus.BLOCKED in statuses:
        overall = ContentStatus.BLOCKED
    elif ContentStatus.NEEDS_REVIEW in statuses:
        overall = ContentStatus.NEEDS_REVIEW
    else:
        overall = ContentStatus.APPROVED

    return ContentAdaptationResult(
        content_id=master_content.get("content_id", "unknown"),
        analysis=analysis,
        adaptations=adaptations,
        overall_status=overall,
        overall_notes="Processed via rule-based fallback (no LLM configured)"
        if not _has_llm_credentials()
        else "",
    )


# ── Public API ───────────────────────────────────────────────────────────────

class ContentAdaptationCrew:
    """
    Main entry point for content intelligence.

    Accepts a ContentPackage, runs analysis + adaptation + compliance,
    and returns structured ContentAdaptationResult with per-platform
    content and status flags.

    Uses CrewAI with LLM when credentials are available; falls back to
    deterministic rule-based processing otherwise.
    """

    def run(
        self,
        package: ContentPackage,
        target_platforms: Optional[list[Platform]] = None,
    ) -> ContentAdaptationResult:
        """
        Process a content package through the content intelligence pipeline.

        Args:
            package: The master content package.
            target_platforms: Override target platforms (defaults to package.target_platforms).

        Returns:
            ContentAdaptationResult with per-platform content + status flags.
        """
        platforms = target_platforms or package.target_platforms
        platform_names = [p.value for p in platforms]

        master_content = package.model_dump()
        master_content["content_id"] = package.content_id

        if _has_llm_credentials():
            logger.info("LLM credentials detected — running CrewAI agents")
            try:
                return _build_crewai_crew(master_content, platform_names)
            except Exception as e:
                logger.error(f"CrewAI execution failed, falling back to rules: {e}")
                return _fallback_adaptation(master_content, platform_names)
        else:
            logger.info("No LLM credentials — using deterministic rule-based adaptation")
            return _fallback_adaptation(master_content, platform_names)

    def adaptation_to_payload(
        self,
        adaptation: PlatformAdaptation,
        content_id: str,
    ) -> PlatformPayload:
        """Convert a CrewAI PlatformAdaptation to a PlatformPayload for publishing."""
        return PlatformPayload(
            platform=Platform(adaptation.platform),
            content_id=content_id,
            title=adaptation.title,
            body=adaptation.body,
            caption=adaptation.caption,
            hashtags=adaptation.hashtags,
            tags=adaptation.tags,
            links=adaptation.links,
            cta=adaptation.cta,
            media_paths=[],  # Media paths come from the original package
            metadata={
                "tone": adaptation.tone,
                "format_type": adaptation.format_type,
                "status": adaptation.status.value,
                "status_reason": adaptation.status_reason,
                "risk_score": adaptation.risk_score,
                "compliance_notes": adaptation.compliance_notes,
                "source": "crewai" if _has_llm_credentials() else "rule_based",
            },
        )
