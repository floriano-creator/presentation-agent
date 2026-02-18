"""Unsplash image search with multimodal vision-based selection."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from presentation_agent.models import ImageEvaluation, SlideContent, SlideWithImage


class ImageServiceError(Exception):
    """Raised when image fetch fails."""

    pass


_MIN_WIDTH = 800


@dataclass
class _Candidate:
    """Image candidate with URL and metadata."""

    url: str
    width: int
    height: int
    raw: dict[str, Any]


def _metadata_select_best(results: list[dict[str, Any]]) -> Optional[str]:
    """Fallback: select by metadata when vision fails."""
    for r in results:
        urls = r.get("urls", {})
        width = r.get("width", 0)
        height = r.get("height", 0)
        if width and height and width < height:
            continue
        if width < _MIN_WIDTH:
            continue
        url = urls.get("regular") or urls.get("small")
        if url:
            return url
    for r in results:
        url = r.get("urls", {}).get("regular") or r.get("urls", {}).get("small")
        if url:
            return url
    return None


def _parse_candidates(results: list[dict[str, Any]]) -> list[_Candidate]:
    """Parse Unsplash results into candidates."""
    candidates: list[_Candidate] = []
    for r in results:
        urls = r.get("urls", {})
        url = urls.get("regular") or urls.get("small")
        if not url:
            continue
        width = r.get("width", 0) or 0
        height = r.get("height", 0) or 0
        if width < height:
            continue
        candidates.append(_Candidate(url=url, width=width, height=height, raw=r))
    if not candidates:
        for r in results:
            url = r.get("urls", {}).get("regular") or r.get("urls", {}).get("small")
            if url:
                candidates.append(
                    _Candidate(
                        url=url,
                        width=r.get("width", 0),
                        height=r.get("height", 0),
                        raw=r,
                    )
                )
    return candidates


class ImageService:
    """Fetches images from Unsplash and selects best via vision analysis."""

    def __init__(
        self,
        access_key: str,
        base_url: str = "https://api.unsplash.com",
        candidates_per_query: int = 3,
        llm_client: Optional[Any] = None,
        vision_model: Optional[str] = None,
    ) -> None:
        self._access_key = access_key
        self._base_url = base_url.rstrip("/")
        self._candidates_per_query = candidates_per_query
        self._llm = llm_client
        self._vision_model = vision_model

    async def _evaluate_candidate(
        self,
        candidate: _Candidate,
        slide_topic: str,
        slide_context: str,
    ) -> Optional[ImageEvaluation]:
        """Evaluate single candidate with vision. Returns None on failure."""
        if not self._llm:
            return None
        try:
            return await self._llm.evaluate_image_vision(
                image_url=candidate.url,
                slide_topic=slide_topic,
                slide_context=slide_context,
                response_model=ImageEvaluation,
                model=self._vision_model,
            )
        except Exception:
            return None

    def _select_best_by_vision(
        self,
        candidates: list[_Candidate],
        evaluations: list[tuple[_Candidate, ImageEvaluation]],
        prefer_background: bool,
    ) -> Optional[str]:
        """Select best image from vision evaluations."""
        if not evaluations:
            return None

        def key(item: tuple[_Candidate, ImageEvaluation]) -> tuple:
            ev = item[1]
            score = ev.score
            bg_bonus = 1 if (prefer_background and ev.suitable_as_background) else 0
            return (score + bg_bonus * 2, score)

        best = max(evaluations, key=key)
        return best[0].url

    async def fetch_image_for_query(
        self,
        query: str,
        slide_topic: str = "",
        slide_context: str = "",
        prefer_background: bool = False,
    ) -> Optional[str]:
        """
        Fetch candidates and select best via vision evaluation.

        Args:
            query: Unsplash search query.
            slide_topic: Slide title for context.
            slide_context: Bullets/notes for context.
            prefer_background: Prefer suitable_as_background images.

        Returns:
            Best image URL or None.
        """
        url = f"{self._base_url}/search/photos"
        params = {
            "query": query,
            "per_page": self._candidates_per_query,
            "orientation": "landscape",
        }
        headers = {"Authorization": f"Client-ID {self._access_key}"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise ImageServiceError(f"Unsplash API error: {e}") from e

        data = response.json()
        results = data.get("results", [])[:3]
        if not results:
            return None

        candidates = _parse_candidates(results)
        if not candidates:
            return None

        topic = slide_topic or query
        context = slide_context or f"Search: {query}"

        if self._llm and candidates:
            ev_results = await asyncio.gather(
                *[self._evaluate_candidate(c, topic, context) for c in candidates],
                return_exceptions=True,
            )
            evaluations: list[tuple[_Candidate, ImageEvaluation]] = []
            for c, ev in zip(candidates, ev_results):
                if isinstance(ev, ImageEvaluation):
                    evaluations.append((c, ev))

            if evaluations:
                return self._select_best_by_vision(
                    candidates, evaluations, prefer_background
                )

        return _metadata_select_best(results)

    async def enrich_slides_with_images(
        self,
        slides: list[SlideContent],
    ) -> list[SlideWithImage]:
        """
        Fetch and select images for slides with image_query.

        Uses vision evaluation when available. First slide prefers
        suitable_as_background for hero layouts.
        """
        async def process_slide(i: int, slide: SlideContent) -> SlideWithImage:
            image_url: Optional[str] = None
            if slide.image_query and slide.image_query.strip():
                try:
                    topic = slide.title
                    context = " | ".join(slide.bullet_points[:3]) if slide.bullet_points else ""
                    prefer_bg = i == 0

                    image_url = await self.fetch_image_for_query(
                        query=slide.image_query.strip(),
                        slide_topic=topic,
                        slide_context=context,
                        prefer_background=prefer_bg,
                    )
                except Exception:
                    image_url = None

            return SlideWithImage(
                slide_number=slide.slide_number,
                title=slide.title,
                bullet_points=slide.bullet_points,
                speaker_notes=slide.speaker_notes,
                image_url=image_url,
                image_query=slide.image_query,
            )

        results = await asyncio.gather(
            *[process_slide(i, s) for i, s in enumerate(slides)],
            return_exceptions=True,
        )

        enriched: list[SlideWithImage] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                slide = slides[i]
                enriched.append(
                    SlideWithImage(
                        slide_number=slide.slide_number,
                        title=slide.title,
                        bullet_points=slide.bullet_points,
                        speaker_notes=slide.speaker_notes,
                        image_url=None,
                        image_query=slide.image_query,
                    )
                )
            else:
                enriched.append(r)

        return enriched
