"""Pydantic models for the presentation pipeline."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# --- User Input ---


class SpeakerProfile(BaseModel):
    """Profile of the person delivering the presentation (adapts style, not content)."""

    age: int = Field(..., ge=1, le=120, description="Speaker age (e.g. 14, 22, 45)")
    role: Optional[str] = Field(
        default=None,
        description="Optional: student, professional, teacher, etc.",
    )
    experience_level: Optional[str] = Field(
        default=None,
        description="Optional: beginner, intermediate, expert",
    )


class UserInput(BaseModel):
    """Minimal user input to generate a presentation."""

    topic: str = Field(..., min_length=1, description="Presentation topic")
    duration_minutes: int = Field(..., ge=1, le=120, description="Duration in minutes")
    audience: str = Field(..., min_length=1, description="Target audience")
    language: str = Field(..., min_length=1, description="Presentation language")
    theme: str = Field(
        default="LIGHT_PROFESSIONAL",
        description="Visual theme: LIGHT_PROFESSIONAL, DARK_TECH, CORPORATE_BLUE, MINIMAL_CLEAN, BOLD_GRADIENT",
    )
    speaker_profile: Optional[SpeakerProfile] = Field(
        default=None,
        description="Optional speaker profile (age, role, experience) to adapt manuscript style.",
    )


# --- Outline ---


class OutlineSection(BaseModel):
    """A section in the presentation outline."""

    type: str = Field(
        ...,
        description="Section type: introduction, main, or conclusion",
    )
    title: str = Field(..., description="Section title")
    points: list[str] = Field(default_factory=list, description="Subpoints for this section")

    @property
    def key_points(self) -> list[str]:
        """Backward compatibility with key_points."""
        return self.points

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        return str(v).lower().strip() if v else v

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_format(cls, data: dict) -> dict:
        """Accept key_points as alias for points; infer type from position if missing."""
        if not isinstance(data, dict):
            return data
        if "key_points" in data and "points" not in data:
            data = {**data, "points": data["key_points"]}
        if "type" not in data or not data["type"]:
            data = {**data, "type": "main"}  # Default for legacy outlines
        return data


class PresentationOutline(BaseModel):
    """Structured outline for the presentation."""

    title: str = Field(..., description="Overall presentation title")
    sections: list[OutlineSection] = Field(
        default_factory=list,
        description="Outline sections",
    )


# --- Script ---


class ScriptSlide(BaseModel):
    """Script content for a single slide (for PPT generation)."""

    slide_number: int = Field(..., ge=1)
    title: str = Field(...)
    bullet_points: list[str] = Field(default_factory=list)
    speaker_notes: str = Field(default="")


class PresentationScript(BaseModel):
    """Full presentation script with slide-level content (legacy/PPT)."""

    title: str = Field(...)
    slides: list[ScriptSlide] = Field(default_factory=list)


# --- Manuscript (spoken script) ---


class ManuscriptSection(BaseModel):
    """A section of the spoken manuscript."""

    name: str = Field(..., description="Section name, e.g. Introduction, Main Part, Conclusion")
    content: str = Field(..., description="Full prose content to be read aloud")


class PresentationManuscript(BaseModel):
    """True speech manuscript: continuous prose suitable for reading aloud."""

    title: str = Field(..., description="Presentation title")
    sections: list[ManuscriptSection] = Field(
        default_factory=list,
        description="Sections with full prose content",
    )

    def full_text(self) -> str:
        """Return the complete manuscript as continuous text."""
        return "\n\n".join(s.content for s in self.sections)


# --- Slide Structure ---


class SlideContent(BaseModel):
    """Content for a single slide in the final structure."""

    slide_number: int = Field(..., ge=1)
    title: str = Field(...)
    bullet_points: list[str] = Field(default_factory=list)
    speaker_notes: str = Field(default="")
    image_query: Optional[str] = Field(default=None, description="Query for image search")


# --- Image Search ---


class SlideWithImage(BaseModel):
    """Slide content with an optional image URL."""

    slide_number: int = Field(..., ge=1)
    title: str = Field(...)
    bullet_points: list[str] = Field(default_factory=list)
    speaker_notes: str = Field(default="")
    image_url: Optional[str] = Field(default=None)
    image_query: Optional[str] = Field(default=None)


# --- Export Result ---


class SlideListOutput(BaseModel):
    """Wrapper for slide list from LLM."""

    slides: list[SlideContent] = Field(default_factory=list)


class ImageEvaluation(BaseModel):
    """Vision-based image evaluation result."""

    score: int = Field(..., ge=0, le=10)
    reason: str = Field(default="")
    suitable_as_background: bool = Field(default=False)


class ExportResult(BaseModel):
    """Result of the presentation export."""

    output_path: str = Field(..., description="Path to the generated PowerPoint file")
    script_path: Optional[str] = Field(default=None, description="Path to the exported script .docx")
    slide_count: int = Field(..., ge=0)
    images_included: int = Field(..., ge=0)
