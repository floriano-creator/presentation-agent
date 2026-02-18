"""High-end slide design library — keynote/tech conference style."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from pptx.util import Inches, Pt

if TYPE_CHECKING:
    from presentation_agent.models import SlideWithImage


# --- 16:9 Dimensions ---
SLIDE_WIDTH_INCH = 13.333
SLIDE_HEIGHT_INCH = 7.5
SLIDE_WIDTH = Inches(SLIDE_WIDTH_INCH)
SLIDE_HEIGHT = Inches(SLIDE_HEIGHT_INCH)

# --- Grid System ---
MARGIN_LEFT = Inches(0.59)
MARGIN_RIGHT = Inches(0.59)
MARGIN_TOP = Inches(0.47)
MARGIN_BOTTOM = Inches(0.47)
CONTENT_WIDTH = SLIDE_WIDTH_INCH - 0.59 - 0.59
CONTENT_HEIGHT = SLIDE_HEIGHT_INCH - 0.47 - 0.47

# --- Accent & Shape Dimensions ---
ACCENT_BAR_WIDTH = 0.08  # inches
ACCENT_LINE_HEIGHT = 0.04
CORNER_RADIUS = 0.15  # normalized for rounded rect
CARD_PADDING = 0.2


# --- Design Tokens (fallback; use theme_library for active theme) ---

LINE_SPACING = 1.4
SUBTITLE_SIZE = 26

# --- Layout safe zones (inches) ---
TITLE_AREA_MAX_HEIGHT = 1.2
TITLE_BODY_GAP = 0.15
MAX_BULLETS_DISPLAY = 6
BODY_MIN_FONT_SIZE = 10
BODY_FONT_REDUCE_IF_BULLETS_ABOVE = 4
IMAGE_TEXT_GAP = 0.1


# --- Layout Types ---


class LayoutType(str, Enum):
    """Available slide layout types."""

    TITLE_SLIDE = "title_slide"
    BOLD_SECTION_DIVIDER = "bold_section_divider"
    TITLE_AND_BULLETS = "title_and_bullets"
    ACCENT_LEFT_LAYOUT = "accent_left_layout"
    CARD_LAYOUT = "card_layout"
    HERO_RIGHT = "hero_right"
    HERO_BACKGROUND = "hero_background"
    IMAGE_FOCUS = "image_focus"
    TWO_COLUMN = "two_column"
    MINIMAL_TEXT = "minimal_text"
    CONCLUSION = "conclusion"


@dataclass
class PlaceholderBox:
    """Content area with position and size (inches)."""

    left: float
    top: float
    width: float
    height: float

    @property
    def inches(self) -> tuple:
        return (Inches(self.left), Inches(self.top), Inches(self.width), Inches(self.height))


@dataclass
class LayoutTemplate:
    """Slide template definition."""

    name: LayoutType
    title_area: Optional[PlaceholderBox] = None
    body_area: Optional[PlaceholderBox] = None
    image_area: Optional[PlaceholderBox] = None
    subtitle_area: Optional[PlaceholderBox] = None
    caption_area: Optional[PlaceholderBox] = None
    accent_left: bool = False
    accent_top: bool = False
    card_style: bool = False
    hero_full_image: bool = False


# Template definitions
TEMPLATES = {
    LayoutType.TITLE_SLIDE: LayoutTemplate(
        name=LayoutType.TITLE_SLIDE,
        title_area=PlaceholderBox(0.59, 2.6, 12.15, 1.6),
        subtitle_area=PlaceholderBox(0.59, 4.4, 12.15, 1.0),
        accent_top=True,
    ),
    LayoutType.BOLD_SECTION_DIVIDER: LayoutTemplate(
        name=LayoutType.BOLD_SECTION_DIVIDER,
        title_area=PlaceholderBox(0.59, 2.4, 12.15, 2.0),
        body_area=PlaceholderBox(0.59, 4.6, 12.15, 1.2),
    ),
    LayoutType.TITLE_AND_BULLETS: LayoutTemplate(
        name=LayoutType.TITLE_AND_BULLETS,
        title_area=PlaceholderBox(0.59, 0.47, 12.15, 0.95),
        body_area=PlaceholderBox(0.59, 1.6, 12.15, 5.2),
    ),
    LayoutType.ACCENT_LEFT_LAYOUT: LayoutTemplate(
        name=LayoutType.ACCENT_LEFT_LAYOUT,
        title_area=PlaceholderBox(0.85, 0.47, 11.4, 0.95),
        body_area=PlaceholderBox(0.85, 1.6, 11.4, 5.2),
        accent_left=True,
    ),
    LayoutType.CARD_LAYOUT: LayoutTemplate(
        name=LayoutType.CARD_LAYOUT,
        title_area=PlaceholderBox(0.59, 0.47, 12.15, 0.95),
        body_area=PlaceholderBox(0.79, 1.7, 11.75, 4.9),
        card_style=True,
    ),
    LayoutType.HERO_RIGHT: LayoutTemplate(
        name=LayoutType.HERO_RIGHT,
        title_area=PlaceholderBox(0.59, 0.47, 5.5, 0.95),
        body_area=PlaceholderBox(0.59, 1.6, 5.5, 5.0),
        image_area=PlaceholderBox(6.3, 0, 7.0, 7.5),
    ),
    LayoutType.HERO_BACKGROUND: LayoutTemplate(
        name=LayoutType.HERO_BACKGROUND,
        title_area=PlaceholderBox(0.59, 2.2, 12.15, 1.4),
        body_area=PlaceholderBox(0.59, 3.8, 12.15, 2.5),
        hero_full_image=True,
    ),
    LayoutType.IMAGE_FOCUS: LayoutTemplate(
        name=LayoutType.IMAGE_FOCUS,
        image_area=PlaceholderBox(0.59, 0.47, 12.15, 5.2),
        caption_area=PlaceholderBox(0.59, 5.9, 12.15, 0.9),
    ),
    LayoutType.TWO_COLUMN: LayoutTemplate(
        name=LayoutType.TWO_COLUMN,
        title_area=PlaceholderBox(0.59, 0.47, 12.15, 0.95),
        body_area=PlaceholderBox(0.59, 1.6, 5.8, 5.0),
        image_area=PlaceholderBox(6.6, 1.6, 5.9, 4.0),
    ),
    LayoutType.MINIMAL_TEXT: LayoutTemplate(
        name=LayoutType.MINIMAL_TEXT,
        title_area=PlaceholderBox(0.59, 2.8, 12.15, 1.2),
        body_area=PlaceholderBox(0.59, 4.2, 12.15, 1.5),
    ),
    LayoutType.CONCLUSION: LayoutTemplate(
        name=LayoutType.CONCLUSION,
        title_area=PlaceholderBox(0.59, 0.47, 12.15, 0.95),
        body_area=PlaceholderBox(0.59, 1.6, 12.15, 5.2),
        accent_left=True,
    ),
}


# --- Layout Selection ---


def select_layout(
    slide: "SlideWithImage",
    slide_index: int,
    total_slides: int,
) -> LayoutType:
    """
    Select layout based on content.
    - Section start → BOLD_SECTION_DIVIDER
    - Image + few bullets → HERO_RIGHT or IMAGE_FOCUS
    - Dense bullets (4+) → CARD_LAYOUT
    - First slide (intro) → BOLD_SECTION_DIVIDER
    - Last slide → CONCLUSION (ACCENT_LEFT)
    - Standard → TITLE_AND_BULLETS or ACCENT_LEFT_LAYOUT
    """
    try:
        is_first = slide_index == 0
        is_last = slide_index == total_slides - 1
        has_image = bool(slide.image_url)
        bullet_count = len(slide.bullet_points) if slide.bullet_points else 0

        if is_first:
            if has_image:
                return LayoutType.HERO_BACKGROUND
            return LayoutType.BOLD_SECTION_DIVIDER
        if is_last:
            return LayoutType.CONCLUSION
        if has_image and bullet_count <= 2:
            return LayoutType.HERO_RIGHT
        if has_image and bullet_count <= 1:
            return LayoutType.IMAGE_FOCUS
        if has_image:
            return LayoutType.TWO_COLUMN
        if bullet_count >= 4:
            return LayoutType.CARD_LAYOUT
        if bullet_count <= 2:
            return LayoutType.MINIMAL_TEXT

        return LayoutType.ACCENT_LEFT_LAYOUT
    except Exception:
        return LayoutType.TITLE_AND_BULLETS


def get_template(layout: LayoutType) -> LayoutTemplate:
    """Get template for layout type."""
    return TEMPLATES.get(layout, TEMPLATES[LayoutType.TITLE_AND_BULLETS])
