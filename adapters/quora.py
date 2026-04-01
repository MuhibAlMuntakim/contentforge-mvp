"""Quora adapter — answer-style draft, value-first, not promotional."""

from adapters.base import BaseAdapter
from core.models import ContentPackage, Platform, PlatformPayload


class QuoraAdapter(BaseAdapter):
    platform = Platform.QUORA

    def adapt(self, package: ContentPackage) -> PlatformPayload:
        # Quora: answer-style, educational, non-promotional
        # Reframe the content as an expert answer

        body_parts: list[str] = []

        # Lead with value — use long body as the "answer"
        if package.long_body:
            body_parts.append(package.long_body)
        elif package.short_caption:
            body_parts.append(package.short_caption)

        # Add links as citations, not promotions
        if package.links:
            body_parts.append("\n\n**Further reading:**")
            for link in package.links:
                body_parts.append(f"- {link}")

        # Generate a suggested Quora question from the title
        suggested_question = package.title
        if not suggested_question.endswith("?"):
            suggested_question = f"What should you know about {package.title.lower()}?"

        return PlatformPayload(
            platform=self.platform,
            content_id=package.content_id,
            title=suggested_question,  # Quora "question" to answer
            body="\n".join(body_parts),
            caption="",
            hashtags=[],  # Quora uses topics, not hashtags
            tags=package.keywords[:10],  # Use keywords as Quora topics
            links=package.links,
            cta="",  # No CTA — Quora is anti-promotional
            media_paths=package.uploaded_assets,
            metadata={
                "format": "answer",
                "suggested_question": suggested_question,
                "review_required": True,  # Always review Quora posts
                "tone": "educational",
                "note": "Reframed as an expert answer. Review and find an appropriate question.",
            },
        )
