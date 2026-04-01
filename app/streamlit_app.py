"""
ContentForge — Multi-Platform Content Publishing System

Streamlit entrypoint. This file handles ONLY UI interactions.
All business logic is delegated to the core modules.

Run with: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
import os
import logging
from pathlib import Path

# ── Path setup (so imports work from project root) ───────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from core.models import (
    ContentPackage,
    Platform,
    PublishMode,
    PublishResult,
    PublishStatus,
)
from core.validators import validate_content_package
from core.crew import ContentAdaptationCrew, ContentAdaptationResult, ContentStatus
from core.workflow import WorkflowEngine
from core.storage import Storage
from app.components.ui_helpers import (
    content_status_badge,
    platform_label,
    show_validation_issues,
    status_badge,
)
from config.platforms import PLATFORM_INFO, get_tier

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ContentForge — Multi-Platform Publisher",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialize session state ─────────────────────────────────────────────────
if "storage" not in st.session_state:
    st.session_state.storage = Storage()

# Always refresh workflow so code/env edits are picked up without stale instances.
st.session_state.workflow = WorkflowEngine(st.session_state.storage)

if "content_package" not in st.session_state:
    st.session_state.content_package = None
if "validation_result" not in st.session_state:
    st.session_state.validation_result = None
if "adaptation_result" not in st.session_state:
    st.session_state.adaptation_result = None
if "publish_results" not in st.session_state:
    st.session_state.publish_results = None
if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 1


# ── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.title("🚀 ContentForge")
        st.caption("Multi-Platform Content Publisher v0.1")
        st.divider()

        # Pipeline steps
        steps = {
            1: "📝 Content Intake",
            2: "🎯 Platform Selection",
            3: "✅ Validation",
            4: "👁️ Content Preview",
            5: "🚀 Execute Publishing",
            6: "📊 Audit Report",
        }

        for num, label in steps.items():
            if num == st.session_state.current_step:
                st.markdown(f"**→ {label}**")
            elif num < st.session_state.current_step:
                st.markdown(f"~~{label}~~ ✓")
            else:
                st.markdown(f"  {label}")

        st.divider()

        # Quick stats
        if st.session_state.content_package:
            pkg = st.session_state.content_package
            st.metric("Content ID", pkg.content_id[:8] + "...")
            st.metric("Platforms", len(pkg.target_platforms))
            st.metric("Mode", pkg.publish_mode.value.replace("_", " ").title())

        st.divider()

        # History
        st.subheader("📜 Recent Runs")
        reports = st.session_state.storage.list_audit_reports(limit=5)
        if reports:
            for r in reports:
                with st.expander(f"{r.campaign_name or r.content_id[:8]}"):
                    st.write(f"✅ {r.succeeded} | ❌ {r.failed} | 📝 {r.drafts}")
                    st.caption(r.started_at.strftime("%Y-%m-%d %H:%M"))
        else:
            st.caption("No previous runs yet.")


# ── Step 1: Content Intake ───────────────────────────────────────────────────

def render_content_intake():
    st.header("📝 Content Intake")
    st.markdown("Enter your master content package below. This will be adapted for each selected platform.")

    col1, col2 = st.columns([2, 1])

    with col1:
        campaign_name = st.text_input(
            "Campaign Name",
            placeholder="e.g., Q2 Product Launch",
            help="Optional but recommended for tracking.",
        )
        title = st.text_input(
            "Title *",
            placeholder="e.g., Introducing Our Revolutionary New Feature",
            help="Required. Used as the primary heading across platforms.",
        )
        long_body = st.text_area(
            "Long-Form Body",
            height=250,
            placeholder="Write the full content here. This will be adapted per platform...",
            help="Main content body. Used for articles (Medium, Blogger) and condensed for social.",
        )
        short_caption = st.text_input(
            "Short Caption",
            placeholder="A punchy one-liner for social platforms...",
            help="Used for Twitter, Instagram, TikTok. Falls back to title if empty.",
        )

    with col2:
        cta = st.text_input(
            "Call to Action (CTA)",
            placeholder="e.g., Sign up for free →",
            help="CTA text. Stripped from Reddit/Quora for compliance.",
        )
        owner = st.text_input(
            "Owner / Author",
            placeholder="Your name",
        )
        notes = st.text_area(
            "Internal Notes",
            height=80,
            placeholder="Any internal notes about this content...",
            help="Not published. For internal tracking only.",
        )

    # Links
    st.subheader("🔗 Links")
    links_text = st.text_area(
        "Links (one per line)",
        height=80,
        placeholder="https://example.com/product\nhttps://example.com/signup",
    )
    links = [l.strip() for l in links_text.strip().split("\n") if l.strip()]

    # Hashtags & Keywords
    col3, col4 = st.columns(2)
    with col3:
        hashtags_text = st.text_input(
            "Hashtags",
            placeholder="#tech #innovation #product",
            help="Space-separated. '#' prefix auto-added if missing.",
        )
        hashtags = [h.strip() for h in hashtags_text.split() if h.strip()]

    with col4:
        keywords_text = st.text_input(
            "Keywords / Tags",
            placeholder="artificial intelligence, machine learning, SaaS",
            help="Comma-separated. Used for SEO tags on Medium, Blogger, YouTube.",
        )
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]

    # Media upload
    st.subheader("📎 Media Assets")
    uploaded_files = st.file_uploader(
        "Upload images, videos, or other media",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg", "gif", "mp4", "mov", "webp"],
    )

    # Save uploaded files to assets dir
    asset_paths: list[str] = []
    if uploaded_files:
        assets_dir = PROJECT_ROOT / "assets"
        assets_dir.mkdir(exist_ok=True)
        for f in uploaded_files:
            file_path = assets_dir / f.name
            file_path.write_bytes(f.read())
            asset_paths.append(str(file_path))
        st.success(f"✅ {len(asset_paths)} file(s) uploaded.")

    # Proceed button
    st.divider()
    if st.button("Next → Platform Selection", type="primary", use_container_width=True):
        if not title.strip():
            st.error("❌ Title is required.")
            return

        package = ContentPackage(
            campaign_name=campaign_name,
            title=title,
            long_body=long_body,
            short_caption=short_caption,
            cta=cta,
            links=links,
            hashtags=hashtags,
            keywords=keywords,
            uploaded_assets=asset_paths,
            owner=owner,
            notes=notes,
        )
        st.session_state.content_package = package
        st.session_state.current_step = 2
        st.rerun()


# ── Step 2: Platform Selection & Mode ────────────────────────────────────────

def render_platform_selection():
    st.header("🎯 Platform Selection & Publish Mode")

    package = st.session_state.content_package
    if not package:
        st.warning("Please complete content intake first.")
        return

    # Publish mode
    st.subheader("Publishing Mode")
    mode = st.radio(
        "Select publish mode:",
        options=[PublishMode.DRAFT_ONLY, PublishMode.REVIEW_REQUIRED, PublishMode.PUBLISH_NOW],
        format_func=lambda m: {
            PublishMode.DRAFT_ONLY: "📝 Draft Only — Generate variants, do not publish",
            PublishMode.REVIEW_REQUIRED: "👁️ Review Required — Generate, review, then publish",
            PublishMode.PUBLISH_NOW: "🚀 Publish Now — Publish immediately (Tier 4 still drafts)",
        }[m],
        horizontal=True,
    )

    st.divider()

    # Platform selection by tier
    st.subheader("Target Platforms")

    selected_platforms: list[Platform] = []

    # Quick select buttons
    col_all, col_none, col_t1, col_text = st.columns(4)
    select_all = col_all.button("Select All")
    select_none = col_none.button("Clear All")
    select_t1 = col_t1.button("Tier 1 Only")
    select_text = col_text.button("Text Platforms")

    tiers = {
        "Tier 1 — Full Automation": [Platform.BLOGGER, Platform.MEDIUM, Platform.LINKEDIN,
                                      Platform.FACEBOOK, Platform.TWITTER, Platform.PINTEREST],
        "Tier 2 — Semi-Automated": [Platform.YOUTUBE, Platform.INSTAGRAM],
        "Tier 3 — Cautious Rollout": [Platform.TIKTOK, Platform.SNAPCHAT],
        "Tier 4 — Draft/Review First": [Platform.REDDIT, Platform.QUORA],
    }

    for tier_label, platforms in tiers.items():
        st.markdown(f"**{tier_label}**")
        cols = st.columns(len(platforms))
        for i, plat in enumerate(platforms):
            info = PLATFORM_INFO.get(plat, {})
            icon = info.get("icon", "📱")
            label = info.get("label", plat.value)

            # Determine default checked state
            if select_all:
                default = True
            elif select_none:
                default = False
            elif select_t1:
                default = plat in tiers["Tier 1 — Full Automation"]
            elif select_text:
                default = plat in {Platform.BLOGGER, Platform.MEDIUM, Platform.LINKEDIN,
                                    Platform.FACEBOOK, Platform.TWITTER, Platform.REDDIT, Platform.QUORA}
            else:
                default = plat in (package.target_platforms or [])

            if cols[i].checkbox(f"{icon} {label}", value=default, key=f"plat_{plat.value}"):
                selected_platforms.append(plat)

    if not selected_platforms:
        st.warning("Select at least one platform to continue.")

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)

    if col_back.button("← Back to Content"):
        st.session_state.current_step = 1
        st.rerun()

    if col_next.button("Next → Validate", type="primary", disabled=not selected_platforms):
        package.target_platforms = selected_platforms
        package.publish_mode = mode
        st.session_state.content_package = package
        st.session_state.current_step = 3
        st.rerun()


# ── Step 3: Validation ───────────────────────────────────────────────────────

def render_validation():
    st.header("✅ Validation")

    package = st.session_state.content_package
    if not package:
        st.warning("Please complete previous steps first.")
        return

    # Show content summary
    with st.expander("📋 Content Summary", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Title", package.title[:40] + ("..." if len(package.title) > 40 else ""))
        col2.metric("Platforms", len(package.target_platforms))
        col3.metric("Mode", package.publish_mode.value.replace("_", " ").title())

        if package.long_body:
            st.text(f"Body: {len(package.long_body)} chars")
        if package.links:
            st.text(f"Links: {len(package.links)}")
        if package.uploaded_assets:
            st.text(f"Assets: {len(package.uploaded_assets)} files")

    # Run validation
    if st.button("🔍 Run Validation", type="primary", use_container_width=True):
        with st.spinner("Validating content package..."):
            result = st.session_state.workflow.validate(package)
            st.session_state.validation_result = result

    # Display results
    if st.session_state.validation_result:
        result = st.session_state.validation_result
        st.divider()

        if result.is_valid:
            st.success("✅ Content package is valid and ready for adaptation!")
        else:
            st.error("❌ Validation failed. Fix the errors below before proceeding.")

        show_validation_issues(result.issues)

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)

    if col_back.button("← Back to Platforms"):
        st.session_state.current_step = 2
        st.rerun()

    can_proceed = (
        st.session_state.validation_result
        and st.session_state.validation_result.is_valid
    )
    if col_next.button("Next → Generate Previews", type="primary", disabled=not can_proceed):
        st.session_state.current_step = 4
        st.rerun()


# ── Step 4: Content Preview (CrewAI Adaptation) ─────────────────────────────

def render_preview():
    st.header("👁️ Platform Content Preview")

    package = st.session_state.content_package
    if not package:
        st.warning("Please complete previous steps first.")
        return

    # Run adaptation
    if st.button("🤖 Generate Platform Variants", type="primary", use_container_width=True):
        with st.spinner("Running content intelligence pipeline (CrewAI)..."):
            crew = ContentAdaptationCrew()
            result = crew.run(package)
            st.session_state.adaptation_result = result

    # Display adaptations
    if st.session_state.adaptation_result:
        result = st.session_state.adaptation_result

        # Overall status
        st.divider()
        overall_badge = content_status_badge(result.overall_status)
        st.subheader(f"Overall Status: {overall_badge}")

        if result.overall_notes:
            st.info(result.overall_notes)

        # Content analysis
        with st.expander("📊 Content Analysis", expanded=False):
            analysis = result.analysis
            col1, col2, col3 = st.columns(3)
            col1.metric("Content Type", analysis.content_type.title())
            col2.metric("Sentiment", analysis.sentiment.title())
            col3.metric("Word Count", analysis.word_count)

            if analysis.key_themes:
                st.write("**Key Themes:**", ", ".join(analysis.key_themes))
            if analysis.target_audience:
                st.write("**Target Audience:**", analysis.target_audience)
            if analysis.primary_message:
                st.write("**Primary Message:**", analysis.primary_message)

        # Per-platform previews
        st.divider()
        st.subheader("Per-Platform Content")

        for adaptation in result.adaptations:
            plat = adaptation.platform
            info = PLATFORM_INFO.get(Platform(plat), {})
            icon = info.get("icon", "📱")
            label = info.get("label", plat.title())
            badge = content_status_badge(adaptation.status)

            with st.expander(f"{icon} {label} — {badge}", expanded=False):
                # Status info
                if adaptation.status != ContentStatus.APPROVED:
                    if adaptation.status == ContentStatus.BLOCKED:
                        st.error(f"🚫 {adaptation.status_reason}")
                    else:
                        st.warning(f"⚠️ {adaptation.status_reason}")

                # Content preview
                if adaptation.title:
                    st.markdown(f"**Title:** {adaptation.title}")
                if adaptation.body:
                    st.text_area(
                        "Body",
                        value=adaptation.body,
                        height=150,
                        key=f"preview_body_{plat}",
                        disabled=True,
                    )
                if adaptation.caption and adaptation.caption != adaptation.body:
                    st.text_area(
                        "Caption",
                        value=adaptation.caption,
                        height=80,
                        key=f"preview_caption_{plat}",
                        disabled=True,
                    )

                # Metadata
                col1, col2 = st.columns(2)
                with col1:
                    if adaptation.hashtags:
                        st.write("**Hashtags:**", " ".join(adaptation.hashtags[:10]))
                    if adaptation.tags:
                        st.write("**Tags:**", ", ".join(adaptation.tags[:10]))
                with col2:
                    st.write(f"**Tone:** {adaptation.tone}")
                    st.write(f"**Format:** {adaptation.format_type}")
                    st.write(f"**Risk Score:** {adaptation.risk_score:.2f}")

                # Compliance notes
                if adaptation.compliance_notes:
                    st.caption("Compliance: " + "; ".join(adaptation.compliance_notes))

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)

    if col_back.button("← Back to Validation"):
        st.session_state.current_step = 3
        st.rerun()

    can_proceed = st.session_state.adaptation_result is not None
    if col_next.button("Next → Execute Publishing", type="primary", disabled=not can_proceed):
        st.session_state.current_step = 5
        st.rerun()


# ── Step 5: Execute Publishing ───────────────────────────────────────────────

def render_execution():
    st.header("🚀 Execute Publishing")

    package = st.session_state.content_package
    adaptation = st.session_state.adaptation_result
    if not package or not adaptation:
        st.warning("Please complete previous steps first.")
        return

    # Summary before execution
    mode_label = package.publish_mode.value.replace("_", " ").title()
    st.info(
        f"**Mode:** {mode_label} | "
        f"**Platforms:** {len(package.target_platforms)} | "
        f"**Content ID:** {package.content_id[:12]}..."
    )

    # Confirm execution
    if package.publish_mode == PublishMode.PUBLISH_NOW:
        st.warning(
            "⚠️ **Publish Now** mode is active. Content will be published immediately "
            "(except Tier 4 platforms which always create drafts)."
        )

    if st.button("🚀 Execute Publishing Workflow", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_container = st.container()
        platform_statuses: dict[str, str] = {}

        total = len(package.target_platforms)

        def on_start(platform: Platform):
            platform_statuses[platform.value] = "🔵 In Progress..."
            _update_status_display(status_container, platform_statuses)

        def on_complete(platform: Platform, result: PublishResult):
            platform_statuses[platform.value] = status_badge(result.status)
            completed = sum(1 for v in platform_statuses.values() if "In Progress" not in v)
            progress_bar.progress(completed / total)
            _update_status_display(status_container, platform_statuses)

        with st.spinner("Publishing in progress..."):
            results = st.session_state.workflow.execute(
                package, adaptation,
                on_platform_start=on_start,
                on_platform_complete=on_complete,
            )

            # Generate audit report
            from core.reporting import generate_audit_report
            report = generate_audit_report(package, results)
            st.session_state.storage.save_audit_report(report)

            st.session_state.publish_results = results
            st.session_state.audit_report = report

        progress_bar.progress(1.0)
        st.success("✅ Publishing workflow complete!")

        # Quick summary
        succeeded = sum(1 for r in results if r.status == PublishStatus.PUBLISHED)
        failed = sum(1 for r in results if r.status == PublishStatus.FAILED)
        drafts = sum(1 for r in results if r.status in (
            PublishStatus.DRAFT_CREATED, PublishStatus.REVIEW_REQUIRED
        ))

        col1, col2, col3 = st.columns(3)
        col1.metric("Published", succeeded, delta=None)
        col2.metric("Drafts/Review", drafts, delta=None)
        col3.metric("Failed", failed, delta=None if failed == 0 else f"-{failed}")

    # Navigation
    st.divider()
    col_back, col_next = st.columns(2)

    if col_back.button("← Back to Preview"):
        st.session_state.current_step = 4
        st.rerun()

    if col_next.button("Next → View Audit Report", type="primary",
                        disabled=st.session_state.audit_report is None):
        st.session_state.current_step = 6
        st.rerun()


def _update_status_display(container, statuses: dict[str, str]):
    """Render the platform status list inside a container."""
    with container:
        for plat_name, stat in statuses.items():
            info = PLATFORM_INFO.get(Platform(plat_name), {})
            icon = info.get("icon", "📱")
            label = info.get("label", plat_name.title())
            st.write(f"{icon} **{label}**: {stat}")


# ── Step 6: Audit Report ────────────────────────────────────────────────────

def render_audit_report():
    st.header("📊 Audit Report")

    report = st.session_state.audit_report
    if not report:
        # Try loading from storage
        package = st.session_state.content_package
        if package:
            reports = st.session_state.storage.get_audit_reports_for_content(package.content_id)
            if reports:
                report = reports[0]
                st.session_state.audit_report = report

    if not report:
        st.warning("No audit report available. Run the publishing workflow first.")
        if st.button("← Back to Start"):
            st.session_state.current_step = 1
            st.rerun()
        return

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Platforms", report.total_platforms)
    col2.metric("Published", report.succeeded)
    col3.metric("Drafts/Review", report.drafts)
    col4.metric("Failed", report.failed)

    st.divider()

    # Report metadata
    with st.expander("📋 Report Details", expanded=False):
        st.write(f"**Report ID:** `{report.report_id}`")
        st.write(f"**Content ID:** `{report.content_id}`")
        st.write(f"**Campaign:** {report.campaign_name or 'N/A'}")
        st.write(f"**Publish Mode:** {report.publish_mode.value.replace('_', ' ').title()}")
        st.write(f"**Started:** {report.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if report.completed_at:
            st.write(f"**Completed:** {report.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if report.notes:
            st.info(report.notes)

    # Per-platform results table
    st.subheader("Per-Platform Results")

    for result in report.results:
        info = PLATFORM_INFO.get(result.platform, {})
        icon = info.get("icon", "📱")
        label = info.get("label", result.platform.value.title())
        badge = status_badge(result.status)

        with st.expander(f"{icon} {label} — {badge}"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Status:** {badge}")
                st.write(f"**Mode:** {result.draft_or_published}")
                st.write(f"**Timestamp:** {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

                if result.url:
                    st.write(f"**URL:** [{result.url}]({result.url})")
                if result.retryable:
                    st.write("**Retryable:** Yes ♻️")

            with col2:
                if result.variant_summary:
                    st.write(f"**Content Summary:** {result.variant_summary[:200]}")
                if result.error_message:
                    st.error(f"Error: {result.error_message}")
                if result.notes:
                    st.caption(result.notes)

    # Export
    st.divider()
    st.subheader("Export")

    report_json = report.model_dump_json(indent=2)
    st.download_button(
        "📥 Download Report (JSON)",
        data=report_json,
        file_name=f"audit_report_{report.report_id[:8]}.json",
        mime="application/json",
    )

    # Navigation
    st.divider()
    if st.button("🔄 Start New Content Run", type="primary", use_container_width=True):
        # Reset state for new run
        st.session_state.content_package = None
        st.session_state.validation_result = None
        st.session_state.adaptation_result = None
        st.session_state.publish_results = None
        st.session_state.audit_report = None
        st.session_state.current_step = 1
        st.rerun()


# ── Main routing ─────────────────────────────────────────────────────────────

def main():
    render_sidebar()

    step = st.session_state.current_step

    if step == 1:
        render_content_intake()
    elif step == 2:
        render_platform_selection()
    elif step == 3:
        render_validation()
    elif step == 4:
        render_preview()
    elif step == 5:
        render_execution()
    elif step == 6:
        render_audit_report()
    else:
        st.session_state.current_step = 1
        st.rerun()


if __name__ == "__main__":
    main()
