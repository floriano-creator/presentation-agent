"""Theme selection system — five predefined visual themes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# RGB tuples (0-255)
# Hex reference: #RRGGBB


@dataclass(frozen=True)
class ThemeStyle:
    """Complete theme definition for slide styling."""

    name: str
    background: tuple[int, int, int]
    primary: tuple[int, int, int]  # Title/body text
    secondary: tuple[int, int, int]  # Caption/muted
    accent: tuple[int, int, int]
    card_bg: tuple[int, int, int]
    overlay_dark: tuple[int, int, int]
    section_bg: tuple[int, int, int]  # Section divider background
    section_text: tuple[int, int, int]
    use_gradient: bool = False
    gradient_start: Optional[tuple[int, int, int]] = None
    gradient_end: Optional[tuple[int, int, int]] = None
    font_family: str = "Calibri"
    title_size: int = 48
    body_size: int = 22
    caption_size: int = 18


class Theme(str, Enum):
    """Available theme identifiers."""

    LIGHT_PROFESSIONAL = "LIGHT_PROFESSIONAL"
    DARK_TECH = "DARK_TECH"
    CORPORATE_BLUE = "CORPORATE_BLUE"
    MINIMAL_CLEAN = "MINIMAL_CLEAN"
    BOLD_GRADIENT = "BOLD_GRADIENT"


THEMES: dict[str, ThemeStyle] = {
    Theme.LIGHT_PROFESSIONAL.value: ThemeStyle(
        name="Light Professional",
        background=(247, 249, 252),  # #F7F9FC
        primary=(15, 23, 42),        # #0F172A
        secondary=(100, 116, 139),    # #64748B
        accent=(37, 99, 235),         # #2563EB
        card_bg=(255, 255, 255),
        overlay_dark=(15, 23, 42),
        section_bg=(37, 99, 235),
        section_text=(255, 255, 255),
    ),
    Theme.DARK_TECH.value: ThemeStyle(
        name="Dark Tech",
        background=(15, 23, 42),      # #0F172A
        primary=(248, 250, 252),      # #F8FAFC
        secondary=(148, 163, 184),    # #94A3B8
        accent=(56, 189, 248),        # #38BDF8
        card_bg=(30, 41, 59),
        overlay_dark=(15, 23, 42),
        section_bg=(56, 189, 248),
        section_text=(15, 23, 42),
    ),
    Theme.CORPORATE_BLUE.value: ThemeStyle(
        name="Corporate Blue",
        background=(255, 255, 255),
        primary=(1, 47, 105),         # #012F69
        secondary=(70, 98, 132),
        accent=(0, 84, 159),          # #00549F
        card_bg=(245, 248, 252),
        overlay_dark=(1, 47, 105),
        section_bg=(0, 84, 159),
        section_text=(255, 255, 255),
    ),
    Theme.MINIMAL_CLEAN.value: ThemeStyle(
        name="Minimal Clean",
        background=(255, 255, 255),
        primary=(23, 23, 23),
        secondary=(115, 115, 115),
        accent=(163, 163, 163),       # Very subtle
        card_bg=(250, 250, 250),
        overlay_dark=(23, 23, 23),
        section_bg=(245, 245, 245),
        section_text=(23, 23, 23),
    ),
    Theme.BOLD_GRADIENT.value: ThemeStyle(
        name="Bold Gradient",
        background=(250, 250, 255),
        primary=(15, 23, 42),
        secondary=(71, 85, 105),
        accent=(99, 102, 241),        # #6366F1
        card_bg=(255, 255, 255),
        overlay_dark=(30, 27, 75),
        section_bg=(99, 102, 241),
        section_text=(255, 255, 255),
        use_gradient=True,
        gradient_start=(99, 102, 241),
        gradient_end=(168, 85, 247),  # #A855F7
    ),
}

DEFAULT_THEME = Theme.LIGHT_PROFESSIONAL.value


def get_theme(theme_name: Optional[str] = None) -> ThemeStyle:
    """
    Get theme by name. Fallback to default if unknown.

    Args:
        theme_name: Theme identifier (e.g. LIGHT_PROFESSIONAL).

    Returns:
        ThemeStyle for the theme.
    """
    if not theme_name:
        return THEMES[DEFAULT_THEME]
    key = str(theme_name).upper().strip()
    return THEMES.get(key, THEMES[DEFAULT_THEME])


def list_themes() -> list[str]:
    """Return list of available theme names."""
    return list(THEMES.keys())
