"""Derive Layer 3 (ultra-concise slide content) from manuscript."""

from __future__ import annotations

from typing import Optional

from presentation_agent.llm_client import LLMClient
from presentation_agent.models import PresentationManuscript, SlideContent, SlideListOutput
from presentation_agent.presentation_targets import compute_presentation_targets


class SlideGenerator:
    """
    Derives Layer 3 — audience-facing slide content from manuscript.

    Slides are for the AUDIENCE. Notes are for the SPEAKER.
    Output: title + minimal bullets only. Speaker notes added separately.
    """

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model

    async def generate(
        self,
        manuscript: PresentationManuscript,
        duration_minutes: Optional[int] = None,
        audience: Optional[str] = None,
        strict_slide_count_retry: bool = False,
    ) -> list[SlideContent]:
        """
        Extract ultra-concise slide content from manuscript.

        Each slide: one core message, minimal text, audience-facing.
        Speaker notes are NOT included here (see NotesGenerator).

        Args:
            manuscript: The speech manuscript (Layer 1).
            duration_minutes: If set (with audience), enforces slide count in 1-2/min range.
            audience: Used with duration_minutes to compute min/max slides.

        Returns:
            Slide content with title, bullet_points, image_query. speaker_notes empty.
        """
        system_prompt = (
            "You are an expert at creating visual presentations. "
            "SLIDES ARE FOR THE AUDIENCE. Create minimal, impactful content. "
            "One core message per slide. Avoid full sentences. "
            "Do NOT write speaker notes—those are generated separately. "
            "Output valid JSON matching the expected schema."
        )

        content_str = "\n\n---\n\n".join(
            f"{s.name}:\n{s.content}" for s in manuscript.sections
        )

        slide_count_instruction = ""
        if duration_minutes is not None and audience:
            targets = compute_presentation_targets(duration_minutes, audience)
            min_slides = targets["min_slides"]
            max_slides = targets["max_slides"]
            strict_note = " STRICT: You MUST produce exactly between " + str(min_slides) + " and " + str(max_slides) + " slides." if strict_slide_count_retry else ""
            slide_count_instruction = f"""
SLIDE COUNT (required): Produce between {min_slides} and {max_slides} slides total (1-2 slides per minute for a {duration_minutes}-minute presentation).{strict_note}
- Introduction: ~10-15% of slides (e.g. 1-2 slides for short, 2-3 for longer)
- Main content: ~70-80% of slides
- Conclusion: ~10-15% of slides (e.g. 1-2 slides)
Split or merge content as needed to stay within this range while keeping one core message per slide.
"""

        prompt = f"""
Convert this speech manuscript into ULTRA-CONCISE slide content.

LAYER 3 — SLIDES (audience-facing):
- Extremely concise bullet points only
- One core message per slide
- Minimal text—audience reads this
- NO full sentences where possible
- NO speaker notes (handled separately)
{slide_count_instruction}

Title: {manuscript.title}

Manuscript:
{content_str}

For each slide, output:
- "slide_number": int (1-based)
- "title": string (concise slide title)
- "bullet_points": array of 2-4 SHORT phrases (key ideas only, not full sentences)
- "speaker_notes": empty string "" (notes are generated separately)
- "image_query": string or null — precise Unsplash search query

IMAGE QUERY RULES:
- Use null for: first slide (intro), last slide (conclusion), agenda/overview slides, text-heavy analytical slides
- Use CONCRETE visual concepts: "robot surgery operating room" NOT "artificial intelligence"
- Combine title + bullets into 2-4 word search: e.g. "sustainable factory solar panels"
- Avoid abstract terms. Prefer scenes, objects, actions that can be photographed.

Output a JSON object with "slides": array of these objects.
Map manuscript sections to slides. Keep slides clean and scannable.
"""

        result = await self._llm.generate_structured(
            prompt=prompt,
            response_model=SlideListOutput,
            system_prompt=system_prompt,
            model=self._model,
        )
        # Ensure speaker_notes are empty (Layer 2 added by NotesGenerator)
        slides = [
            SlideContent(
                slide_number=s.slide_number,
                title=s.title,
                bullet_points=s.bullet_points,
                speaker_notes="",
                image_query=s.image_query,
            )
            for s in result.slides
        ]
        return slides
