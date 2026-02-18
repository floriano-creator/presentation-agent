"""Iterative quality review loop for presentation manuscripts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from presentation_agent.llm_client import LLMClient
from presentation_agent.models import PresentationManuscript


class ScriptReviewEvaluation(BaseModel):
    """Structured evaluation result from the LLM."""

    score: int = Field(..., ge=0, le=10, description="Quality score 0-10")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class ScriptReviewer:
    """
    Evaluates and improves presentation manuscripts before slide generation.

    Process:
    A) Evaluate manuscript on structure, clarity, audience fit, depth, engagement, duration
    B) If score >= 8: approve as-is. If score < 8: rewrite
    C) Return improved manuscript (or original on approval/failure)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        evaluate_model: str | None = None,
        rewrite_model: str | None = None,
    ) -> None:
        self._llm = llm_client
        self._evaluate_model = evaluate_model
        self._rewrite_model = rewrite_model

    async def review_and_improve(
        self,
        manuscript: PresentationManuscript,
        topic: str,
        audience: str,
        duration_minutes: int,
        language: str,
    ) -> tuple[PresentationManuscript, int]:
        """
        Evaluate the manuscript and improve it if score < 8.

        Args:
            manuscript: The generated speech manuscript.
            topic: Presentation topic.
            audience: Target audience.
            duration_minutes: Duration in minutes.
            language: Presentation language.

        Returns:
            Tuple of (final manuscript, evaluation score).
            On failure, returns (original manuscript, 0).
        """
        try:
            evaluation = await self._evaluate(
                manuscript, topic, audience, duration_minutes, language
            )
            if evaluation.score >= 8:
                return manuscript, evaluation.score
            print("Improving script...")
            improved = await self._rewrite(
                manuscript, evaluation, topic, audience, duration_minutes, language
            )
            return improved, evaluation.score
        except Exception:
            return manuscript, 0

    async def _evaluate(
        self,
        manuscript: PresentationManuscript,
        topic: str,
        audience: str,
        duration_minutes: int,
        language: str,
    ) -> ScriptReviewEvaluation:
        """Step A: Evaluate manuscript and return structured JSON."""
        content_str = "\n\n---\n\n".join(
            f"{s.name}:\n{s.content}" for s in manuscript.sections
        )

        system_prompt = (
            "You are an expert presentation reviewer. "
            "Evaluate this as a SPOKEN MANUSCRIPT—text to be read aloud. "
            "Output valid JSON only."
        )

        prompt = f"""
Evaluate this presentation manuscript (speech script to be read aloud):

Topic: {topic}
Audience: {audience}
Duration: {duration_minutes} minutes
Language: {language}

Title: {manuscript.title}

Manuscript content:
{content_str}

Evaluate on:
- Structure and logical flow (does it read naturally?)
- Clarity and understandability when spoken
- Audience appropriateness
- Depth of explanation
- Engagement / rhetorical quality
- Fit to time duration
- Natural transitions between sections
- Avoidance of robotic or outline-like phrasing

Output a JSON object with:
- "score": int (0-10, 10 = excellent spoken manuscript)
- "strengths": array of strings
- "weaknesses": array of strings
- "missing_topics": array of strings
- "improvement_suggestions": array of strings
"""

        return await self._llm.generate_structured(
            prompt=prompt,
            response_model=ScriptReviewEvaluation,
            system_prompt=system_prompt,
            model=self._evaluate_model,
        )

    async def _rewrite(
        self,
        manuscript: PresentationManuscript,
        evaluation: ScriptReviewEvaluation,
        topic: str,
        audience: str,
        duration_minutes: int,
        language: str,
    ) -> PresentationManuscript:
        """Step C: Generate improved manuscript based on evaluation."""
        system_prompt = (
            "You are an expert presentation writer. "
            "Improve this SPOKEN MANUSCRIPT based on the feedback. "
            "Write as if the presenter will read it aloud. "
            "Output valid JSON matching the PresentationManuscript schema. "
            "Keep continuous prose—no bullet points."
        )

        feedback = (
            f"Weaknesses: {', '.join(evaluation.weaknesses)}\n"
            f"Missing topics: {', '.join(evaluation.missing_topics)}\n"
            f"Suggestions: {', '.join(evaluation.improvement_suggestions)}"
        )

        content_preview = "\n".join(
            f"{s.name}: {s.content[:150]}..." for s in manuscript.sections
        )

        prompt = f"""
Improve this presentation manuscript based on the evaluation feedback.

Original manuscript:
Title: {manuscript.title}
Sections: {content_preview}

Evaluation feedback:
{feedback}

Context: topic={topic}, audience={audience}, duration={duration_minutes} min, language={language}

Requirements:
- Fix weaknesses
- Incorporate missing content where relevant
- Improve clarity and flow for spoken delivery
- Keep same topic and duration
- Maintain consistent style and language
- Preserve section structure (Introduction, Main Part, Conclusion)
- Output full prose in each section—no bullet points

Output a JSON object with:
- "title": string
- "sections": array of objects with "name" (string) and "content" (string, full prose)
"""

        return await self._llm.generate_structured(
            prompt=prompt,
            response_model=PresentationManuscript,
            system_prompt=system_prompt,
            model=self._rewrite_model,
        )
