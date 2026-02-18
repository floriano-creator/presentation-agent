"""Generate full speech manuscript from outline."""

from __future__ import annotations

from presentation_agent.llm_client import LLMClient
from presentation_agent.models import (
    PresentationManuscript,
    PresentationOutline,
    SpeakerProfile,
    UserInput,
)
from presentation_agent.presentation_targets import compute_presentation_targets


def _speaker_instruction(user_input: UserInput) -> str:
    """Build prompt block for speaker profile. Style only; content stays accurate."""
    profile = user_input.speaker_profile
    if not profile:
        return (
            "SPEAKER: No specific profile; use a neutral adult tone, "
            "clear and professional."
        )

    age = profile.age
    role = profile.role or ""
    experience = profile.experience_level or ""

    if age < 18:
        style = (
            "Use simpler sentences and everyday vocabulary. "
            "More explanatory tone, less jargon. "
            "Write as if spoken by a younger speaker—clear and accessible."
        )
    elif age < 30:
        style = (
            "Use a natural, modern tone. Moderate complexity. "
            "Write as if spoken by a young adult."
        )
    elif age < 50:
        style = (
            "Use professional, clear language. Moderate formality. "
            "Write as if spoken by an adult professional."
        )
    else:
        style = (
            "Use precise terminology and concise phrasing where appropriate. "
            "Write as if spoken by an experienced speaker."
        )

    parts = [f"SPEAKER PROFILE: age {age}.", style]
    if role:
        parts.append(f"Role/context: {role}.")
    if experience:
        parts.append(f"Experience level: {experience}.")
    parts.append(
        "Write as if spoken by a person of this age and background. "
        "Adapt ONLY language, tone, and complexity—do NOT change factual content."
    )
    return " ".join(parts)


class ScriptGeneratorError(Exception):
    """Raised when script generation fails."""

    pass


class ScriptGenerator:
    """Expands an outline into a true speech manuscript for reading aloud."""

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model

    async def generate(
        self,
        outline: PresentationOutline,
        user_input: UserInput,
    ) -> PresentationManuscript:
        """
        Generate a full speech manuscript from the outline.

        Args:
            outline: The presentation outline.
            user_input: Original user parameters for context.

        Returns:
            PresentationManuscript with continuous prose suitable for reading aloud.

        Raises:
            ScriptGeneratorError: On generation failure.
        """
        system_prompt = (
            "You are an expert presentation writer specializing in spoken manuscripts. "
            "LAYER 1 — MANUSCRIPT: This is the full speech script for Word export. "
            "Slides and speaker notes are derived separately. "
            "Write as if the presenter will read this aloud. "
            "Full sentences, natural paragraphs, transitions. "
            "NO bullet-point style. Output valid JSON. "
            "When adapting to speaker profile: change only language, tone, and complexity—never alter or stereotype factual content."
        )

        sections_str = "\n".join(
            f"- {s.title}: {', '.join(s.key_points)}"
            for s in outline.sections
        )

        targets = compute_presentation_targets(
            user_input.duration_minutes,
            user_input.audience,
            user_input.speaker_profile,
        )
        target_words = targets["target_word_count"]
        wpm = targets["wpm"]

        prompt = f"""
Create a TRUE SPEECH MANUSCRIPT from this outline. The presenter will READ THIS ALOUD.

Title: {outline.title}
Outline sections:
{sections_str}

Context:
- Topic: {user_input.topic}
- Audience: {user_input.audience}
- Duration: {user_input.duration_minutes} minutes
- Language: {user_input.language}

{_speaker_instruction(user_input)}

LENGTH (guidance):
- Aim for roughly {target_words} words (based on {wpm} words per minute for this audience); slightly shorter or longer is fine
- Adjust depth and pacing so a {user_input.duration_minutes}-minute presentation feels natural—no padding, no abrupt cuts
- Distribute content naturally: introduction ~10-15%, main body ~70-80%, conclusion ~10-15%

CRITICAL REQUIREMENTS:
- Write in full sentences and paragraphs
- Sound natural when spoken aloud
- Include smooth transitions between sections
- Tailor language and examples to the audience
- Maintain consistent, professional tone
- NO bullet points, NO slide-style phrasing
- Structure: Introduction, Main Part (with subsections from outline), Conclusion

Output a JSON object with:
- "title": string (presentation title)
- "sections": array of objects, each with:
  - "name": string (e.g. "Introduction", "Main Part", "Conclusion" or section title)
  - "content": string (full prose paragraph(s) to be read aloud—continuous text, not bullets)
"""

        try:
            return await self._llm.generate_structured(
                prompt=prompt,
                response_model=PresentationManuscript,
                system_prompt=system_prompt,
                model=self._model,
            )
        except ValueError as e:
            raise ScriptGeneratorError(f"Script generation failed: {e}") from e
