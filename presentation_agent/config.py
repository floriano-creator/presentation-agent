"""Configuration management with environment variable support."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _model_env(key: str, default: str) -> str:
    """Read model from env; fallback to OPENAI_MODEL then default."""
    return os.getenv(key) or os.getenv("OPENAI_MODEL", default)


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    openai_api_key: str
    unsplash_access_key: str
    openai_model: str = "gpt-5"
    unsplash_base_url: str = "https://api.unsplash.com"
    # Per-task models (speed/cost optimization)
    outline_model: str = "gpt-4o"
    manuscript_model: str = "gpt-5"
    script_review_evaluate_model: str = "gpt-5-mini"
    script_review_rewrite_model: str = "gpt-5"
    slide_model: str = "gpt-4o"
    notes_model: str = "gpt-5-mini"
    image_vision_model: str = "gpt-4o"

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        openai_key = os.getenv("OPENAI_API_KEY")
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")

        if not openai_key:
            raise ValueError(
                "OPENAI_API_KEY is required. Set it in .env or export it."
            )
        if not unsplash_key:
            raise ValueError(
                "UNSPLASH_ACCESS_KEY is required. Set it in .env or export it."
            )

        return cls(
            openai_api_key=openai_key,
            unsplash_access_key=unsplash_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5"),
            unsplash_base_url=os.getenv(
                "UNSPLASH_BASE_URL", "https://api.unsplash.com"
            ),
            outline_model=_model_env("OPENAI_MODEL_OUTLINE", "gpt-4o"),
            manuscript_model=_model_env("OPENAI_MODEL_MANUSCRIPT", "gpt-5"),
            script_review_evaluate_model=_model_env(
                "OPENAI_MODEL_SCRIPT_REVIEW_EVALUATE", "gpt-5-mini"
            ),
            script_review_rewrite_model=_model_env(
                "OPENAI_MODEL_SCRIPT_REVIEW_REWRITE", "gpt-5"
            ),
            slide_model=_model_env("OPENAI_MODEL_SLIDES", "gpt-4o"),
            notes_model=_model_env("OPENAI_MODEL_NOTES", "gpt-5-mini"),
            image_vision_model=_model_env("OPENAI_MODEL_IMAGE_VISION", "gpt-4o"),
        )
