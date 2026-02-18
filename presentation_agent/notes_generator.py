"""Derive Layer 2 (speaker notes) from manuscript."""

from __future__ import annotations

from pydantic import BaseModel, Field

from presentation_agent.llm_client import LLMClient
from presentation_agent.models import PresentationManuscript, SlideContent


class SlideNotesOutput(BaseModel):
    """Speaker notes per slide."""

    slide_number: int = Field(..., ge=1)
    speaker_notes: str = Field(..., description="2-5 concise notes for the presenter")


class NotesListOutput(BaseModel):
    """Wrapper for notes list from LLM."""

    notes: list[SlideNotesOutput] = Field(default_factory=list)


class NotesGenerator:
    """
    Derives Layer 2 — speaker notes from manuscript.

    Notes are for the SPEAKER. Slides are for the AUDIENCE.
    Output: 2-5 concise reminders per slide, derived from manuscript.
    """

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model

    async def generate(
        self,
        manuscript: PresentationManuscript,
        slides: list[SlideContent],
    ) -> list[SlideContent]:
        """
        Add speaker notes to each slide, derived from the manuscript.

        Notes: concise summaries, key arguments, presenter reminders.
        NOT full paragraphs. NOT identical to slide bullets.

        Args:
            manuscript: The speech manuscript (Layer 1).
            slides: Slide structure with title, bullets (notes empty).

        Returns:
            Slides with speaker_notes filled in.
        """
        system_prompt = (
            "You are an expert at creating presenter support materials. "
            "SPEAKER NOTES ARE FOR THE PRESENTER. Slides are for the audience. "
            "Generate 2-5 concise notes per slide: key arguments, reminders. "
            "Short sentences or phrases. NOT full paragraphs. "
            "NOT identical to slide bullets. Output valid JSON."
        )

        content_str = "\n\n---\n\n".join(
            f"{s.name}:\n{s.content}" for s in manuscript.sections
        )

        slides_str = "\n".join(
            f"- Slide {s.slide_number}: {s.title} | bullets: {s.bullet_points}"
            for s in slides
        )

        prompt = f"""
Generate SPEAKER NOTES for each slide. Notes are for the presenter, not the audience.

LAYER 2 — SPEAKER NOTES:
- 2-5 concise notes per slide
- Key arguments only
- Helpful reminders for the presenter
- Short sentences or phrases allowed
- NOT full paragraphs
- NOT identical to slide bullets (slides are separate, for audience)

Manuscript:
{content_str}

Slide structure (bullets already defined for audience):
{slides_str}

For each slide, output:
- "slide_number": int
- "speaker_notes": string with 2-5 concise notes, newline-separated or as bullet points

Output a JSON object with "notes": array of these objects.
Match notes to the manuscript content relevant to each slide.
"""

        try:
            result = await self._llm.generate_structured(
                prompt=prompt,
                response_model=NotesListOutput,
                system_prompt=system_prompt,
                model=self._model,
            )
        except Exception:
            return slides  # Continue with slides only if notes fail

        # Merge notes into slides
        notes_by_slide = {n.slide_number: n.speaker_notes for n in result.notes}
        enriched: list[SlideContent] = []
        for s in slides:
            notes = notes_by_slide.get(s.slide_number, "")
            enriched.append(
                SlideContent(
                    slide_number=s.slide_number,
                    title=s.title,
                    bullet_points=s.bullet_points,
                    speaker_notes=notes,
                    image_query=s.image_query,
                )
            )
        return enriched
