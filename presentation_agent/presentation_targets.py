"""Duration-aware presentation targets: word count and slide count."""

from __future__ import annotations

from typing import Optional

# Evidence-based speaking rate: 120–150 WPM typical
DEFAULT_WPM = 135
WPM_SLOW_MIN = 120
WPM_SLOW_MAX = 130
WPM_FAST_MIN = 140
WPM_FAST_MAX = 150

# Slide pacing: 1–2 slides per minute
SLIDES_PER_MINUTE_MIN = 1
SLIDES_PER_MINUTE_MAX = 2

# Manuscript length tolerance ±10%
WORD_COUNT_TOLERANCE_LOW = 0.9
WORD_COUNT_TOLERANCE_HIGH = 1.1


def get_wpm_for_audience(audience: str) -> int:
    """
    Return words-per-minute assumption based on audience.

    - Students / general / non-expert → slower (120–130 WPM)
    - Experts / technical → faster (140–150 WPM)
    - Default → 135 WPM
    """
    if not audience or not audience.strip():
        return DEFAULT_WPM
    lower = audience.lower().strip()
    if any(
        term in lower
        for term in (
            "student",
            "general",
            "public",
            "beginner",
            "overview",
            "introductory",
            "everyone",
        )
    ):
        return (WPM_SLOW_MIN + WPM_SLOW_MAX) // 2  # 125
    if any(
        term in lower
        for term in (
            "expert",
            "technical",
            "engineer",
            "developer",
            "specialist",
            "professional",
        )
    ):
        return (WPM_FAST_MIN + WPM_FAST_MAX) // 2  # 145
    return DEFAULT_WPM


def compute_presentation_targets(
    duration_minutes: int,
    audience: str,
    speaker_profile: Optional[object] = None,
) -> dict[str, int]:
    """
    Compute target word count and slide count for the given duration and audience.

    Optionally adjust WPM by speaker age (e.g. younger speakers slightly slower).

    Returns:
        {
            "target_word_count": int,
            "min_slides": int,
            "max_slides": int,
            "wpm": int,
        }
    """
    wpm = get_wpm_for_audience(audience)
    if speaker_profile is not None and hasattr(speaker_profile, "age"):
        age = getattr(speaker_profile, "age", 30)
        if age < 18:
            wpm = min(wpm, WPM_SLOW_MAX)
        elif age >= 50 and getattr(speaker_profile, "experience_level", ""):
            if str(getattr(speaker_profile, "experience_level", "")).lower() == "expert":
                wpm = max(wpm, WPM_FAST_MIN)
    target_word_count = duration_minutes * wpm
    min_slides = max(3, duration_minutes * SLIDES_PER_MINUTE_MIN)
    max_slides = max(min_slides, duration_minutes * SLIDES_PER_MINUTE_MAX)
    return {
        "target_word_count": target_word_count,
        "min_slides": min_slides,
        "max_slides": max_slides,
        "wpm": wpm,
    }


def word_count(text: str) -> int:
    """Count words in text (whitespace-separated)."""
    if not text or not text.strip():
        return 0
    return len(text.split())


def manuscript_word_count(manuscript) -> int:
    """Count words in a PresentationManuscript (full_text)."""
    return word_count(manuscript.full_text())


def is_manuscript_length_acceptable(
    manuscript,
    target_word_count: int,
    tolerance_low: float = WORD_COUNT_TOLERANCE_LOW,
    tolerance_high: float = WORD_COUNT_TOLERANCE_HIGH,
) -> bool:
    """True if manuscript word count is within ±tolerance of target."""
    count = manuscript_word_count(manuscript)
    low = int(target_word_count * tolerance_low)
    high = int(target_word_count * tolerance_high)
    return low <= count <= high


def is_slide_count_acceptable(
    slides: list,
    min_slides: int,
    max_slides: int,
) -> bool:
    """True if number of slides is within [min_slides, max_slides]."""
    n = len(slides)
    return min_slides <= n <= max_slides
