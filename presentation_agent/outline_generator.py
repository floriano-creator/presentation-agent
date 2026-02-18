"""Generate presentation outline from user input."""

from __future__ import annotations

from presentation_agent.llm_client import LLMClient
from presentation_agent.models import PresentationOutline, UserInput
from presentation_agent.presentation_targets import compute_presentation_targets


class OutlineGenerator:
    """Generates a structured presentation outline with professional narrative structure."""

    def __init__(self, llm_client: LLMClient, model: str | None = None) -> None:
        self._llm = llm_client
        self._model = model

    async def generate(self, user_input: UserInput) -> PresentationOutline:
        """
        Generate a presentation outline from user input.

        Structure: title → introduction → main sections → conclusion.
        Duration and audience drive section count and depth.

        Args:
            user_input: Topic, duration, audience, and language.

        Returns:
            Structured outline with title and typed sections.
        """
        try:
            return await self._generate_with_retry(user_input)
        except ValueError:
            return await self._generate_with_retry(user_input, strict=True)

    async def _generate_with_retry(
        self,
        user_input: UserInput,
        strict: bool = False,
    ) -> PresentationOutline:
        """Generate outline, with optional stricter prompt on retry."""
        system_prompt = self._build_system_prompt(strict)
        prompt = self._build_prompt(user_input, strict)
        return await self._llm.generate_structured(
            prompt=prompt,
            response_model=PresentationOutline,
            system_prompt=system_prompt,
            model=self._model,
        )

    def _build_system_prompt(self, strict: bool) -> str:
        base = (
            "You are an expert presentation designer. "
            "Generate a clear, professional outline with logical narrative structure. "
            "Output valid JSON matching the exact schema. "
        )
        if strict:
            base += (
                "CRITICAL: Include exactly 'type', 'title', and 'points' for each section. "
                "Type must be one of: introduction, main, conclusion. "
            )
        return base

    def _build_prompt(self, user_input: UserInput, strict: bool) -> str:
        targets = compute_presentation_targets(
            user_input.duration_minutes, user_input.audience
        )
        min_slides = targets["min_slides"]
        max_slides = targets["max_slides"]
        target_slides = (min_slides + max_slides) // 2
        # Enough main sections so content can map to target slide count (intro ~10-15%, main 70-80%, conclusion ~10-15%)
        main_section_count = max(2, min(8, (target_slides * 3) // 4))

        structure_notes = ""
        if strict:
            structure_notes = """
STRICT SCHEMA - each section MUST have:
- "type": exactly "introduction" OR "main" OR "conclusion"
- "title": string
- "points": array of 2-4 strings (subpoints)
"""

        return f"""
Create a presentation outline with this structure:

1. INTRODUCTION (type: "introduction") — ~10-15% of content
   - Hook / attention grabber
   - Context / background
   - Purpose of the presentation
   - Optional: agenda

2. MAIN CONTENT (type: "main") — {main_section_count} sections, ~70-80% of content
   - Each section: one core idea, 2-4 subpoints
   - Logical progression
   - Provide enough subpoints so the presentation can yield {min_slides}-{max_slides} slides total

3. CONCLUSION (type: "conclusion") — ~10-15% of content
   - Summary of key points
   - Final takeaway / message
   - Optional: call to action

Parameters:
- Topic: {user_input.topic}
- Duration: {user_input.duration_minutes} minutes
- Target slide count: {min_slides}-{max_slides} slides (1-2 slides per minute)
- Audience: {user_input.audience}
- Language: {user_input.language}

AUDIENCE ADAPTATION: Adjust terminology complexity, depth for "{user_input.audience}".

DURATION: Outline must support a {user_input.duration_minutes}-minute presentation with {min_slides}-{max_slides} slides. Ensure enough substance in main sections.
{structure_notes}

Output a JSON object:
```json
{{
  "title": "string (presentation title)",
  "sections": [
    {{ "type": "introduction", "title": "...", "points": ["...", "..."] }},
    {{ "type": "main", "title": "...", "points": ["...", "..."] }},
    {{ "type": "main", "title": "...", "points": ["...", "..."] }},
    {{ "type": "conclusion", "title": "...", "points": ["...", "..."] }}
  ]
}}
```
"""
