"""Targeted fact-checking: identify and patch only incorrect or doubtful statements."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from presentation_agent.llm_client import LLMClient
from presentation_agent.models import (
    ManuscriptSection,
    PresentationManuscript,
)


IssueType = Literal["incorrect", "misleading", "outdated", "unverifiable"]


class FactCheckIssue(BaseModel):
    """A single factual issue with minimal correction."""

    original_text: str = Field(
        ...,
        description="Exact verbatim quote from the manuscript to replace",
    )
    issue_type: IssueType = Field(
        ...,
        description="incorrect | misleading | outdated | unverifiable",
    )
    explanation: str = Field(default="", description="Brief explanation of the issue")
    corrected_text: str = Field(
        ...,
        description="Minimal replacement preserving tone and style",
    )


class FactCheckReport(BaseModel):
    """Structured report from fact-check analysis."""

    issues: list[FactCheckIssue] = Field(default_factory=list)


class FactChecker:
    """
    Reviews manuscript for factual issues and applies minimal patches only.

    Does NOT rewrite the full script. Replaces only problematic segments.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: Optional[str] = None,
    ) -> None:
        self._llm = llm_client
        self._model = model

    def _manuscript_text(self, manuscript: PresentationManuscript) -> str:
        """Full manuscript as single text for analysis."""
        return "\n\n".join(
            f"## {s.name}\n{s.content}" for s in manuscript.sections
        )

    async def fact_check(
        self,
        manuscript: PresentationManuscript,
        topic: str,
        audience: str,
    ) -> FactCheckReport:
        """
        Analyze manuscript and return structured list of factual issues.

        Returns report with empty issues list if nothing to correct.
        """
        full_text = self._manuscript_text(manuscript)
        system_prompt = (
            "You are a careful fact-checker for presentation scripts. "
            "Analyze the manuscript sentence by sentence. "
            "Identify ONLY: factually incorrect statements, potentially misleading claims, "
            "outdated information, or unverifiable claims presented as facts. "
            "Output valid JSON. "
            "For each issue, original_text MUST be an exact verbatim copy of the problematic "
            "phrase or sentence as it appears in the manuscript (so it can be replaced). "
            "corrected_text must be a minimal replacement that fixes the issue while preserving "
            "tone, style, and length as much as possible. "
            "Prefer widely accepted general knowledge. If unsure, rephrase more cautiously "
            "rather than fabricate. Do not invent precise statistics unless certain."
        )
        prompt = f"""
Topic: {topic}
Audience: {audience}

Manuscript to analyze:

{full_text}

Identify factual issues only. For each issue provide:
- "original_text": exact verbatim quote from the manuscript (required for replacement)
- "issue_type": one of "incorrect" | "misleading" | "outdated" | "unverifiable"
- "explanation": brief explanation
- "corrected_text": minimal replacement, same tone and style

If no issues are found, return: {{ "issues": [] }}

Output a JSON object with "issues": array of the above objects.
"""

        result = await self._llm.generate_structured(
            prompt=prompt,
            response_model=FactCheckReport,
            system_prompt=system_prompt,
            model=self._model,
        )
        return result

    def apply_patches(
        self,
        manuscript: PresentationManuscript,
        report: FactCheckReport,
    ) -> PresentationManuscript:
        """
        Create a new manuscript with only the problematic segments replaced.

        Keeps surrounding text, tone, style, and structure unchanged.
        Replaces at most one occurrence per (section, issue) to avoid over-replace.
        """
        if not report.issues:
            return manuscript

        new_sections: list[ManuscriptSection] = []
        for section in manuscript.sections:
            content = section.content
            for issue in report.issues:
                if not issue.original_text or issue.original_text not in content:
                    continue
                content = content.replace(
                    issue.original_text,
                    issue.corrected_text,
                    1,
                )
            new_sections.append(
                ManuscriptSection(name=section.name, content=content)
            )

        return PresentationManuscript(
            title=manuscript.title,
            sections=new_sections,
        )

    async def fact_check_and_patch(
        self,
        manuscript: PresentationManuscript,
        topic: str,
        audience: str,
    ) -> PresentationManuscript:
        """
        Fact-check the manuscript and apply minimal corrections only.

        If no issues: return original manuscript unchanged.
        On any failure: return original manuscript (robust).
        """
        try:
            report = await self.fact_check(manuscript, topic, audience)
            if not report.issues:
                return manuscript
            return self.apply_patches(manuscript, report)
        except Exception:
            return manuscript
