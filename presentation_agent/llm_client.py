"""OpenAI LLM client with structured output and vision support."""

from __future__ import annotations

import json
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Async OpenAI client for structured JSON outputs."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> T:
        """
        Generate a structured response from the LLM, parsed into a Pydantic model.

        Args:
            prompt: User prompt.
            response_model: Pydantic model class for the expected JSON structure.
            system_prompt: Optional system message.
            model: Override model for this call (default: client default).

        Returns:
            Parsed instance of response_model.

        Raises:
            ValueError: If the response cannot be parsed into the model.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=model or self._model,
            messages=messages,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}") from e

        return response_model.model_validate(data)

    async def evaluate_image_vision(
        self,
        image_url: str,
        slide_topic: str,
        slide_context: str,
        response_model: type[T],
        model: str | None = None,
    ) -> T:
        """
        Evaluate an image using vision model for presentation suitability.

        Args:
            image_url: URL of the image to evaluate.
            slide_topic: Slide title/topic.
            slide_context: Additional context (bullets, etc.).
            response_model: Pydantic model for structured response.
            model: Override model for this call (must be vision-capable).

        Returns:
            Parsed evaluation result.
        """
        prompt = f"""
Evaluate this image for use in a professional presentation slide.

Slide topic: {slide_topic}
Context: {slide_context}

Assess:
- Relevance to the topic (does it match the subject?)
- Clarity of subject (is the main subject clear?)
- Visual quality (sharpness, composition)
- Presentation suitability (professional, not distracting)
- Background usability (could work as slide background?)
- Absence of distracting elements (text, logos, clutter)

Output JSON with:
- "score": int 0-10 (10 = perfect for presentation)
- "reason": string (brief explanation)
- "suitable_as_background": bool (true if image could work as full-slide background)
"""

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
        ]

        response = await self._client.chat.completions.create(
            model=model or self._model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        if not raw:
            raise ValueError("Empty vision response")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from vision: {e}") from e

        return response_model.model_validate(data)
