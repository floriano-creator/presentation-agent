"""Central orchestrator for the presentation generation pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional

from presentation_agent.config import Config
from presentation_agent.image_service import ImageService, ImageServiceError
from presentation_agent.llm_client import LLMClient
from presentation_agent.models import ExportResult, SpeakerProfile, SlideWithImage, UserInput
from presentation_agent.outline_generator import OutlineGenerator
from presentation_agent.presentation_targets import (
    compute_presentation_targets,
    is_slide_count_acceptable,
)
from presentation_agent.ppt_exporter import PPTExporter, PPTExporterError
from presentation_agent.script_exporter import ScriptExporter
from presentation_agent.script_generator import ScriptGenerator, ScriptGeneratorError
from presentation_agent.script_reviewer import ScriptReviewer
from presentation_agent.fact_checker import FactChecker
from presentation_agent.notes_generator import NotesGenerator
from presentation_agent.slide_generator import SlideGenerator


class PresentationAgentError(Exception):
    """Base exception for presentation agent failures."""

    pass


class PresentationAgent:
    """
    Orchestrates the full presentation generation pipeline.

    Multi-layer content system:
    - Layer 1: Manuscript (Word) — full speech script
    - Layer 2: Speaker notes (PPT notes) — concise presenter reminders
    - Layer 3: Slides (PPT) — ultra-concise audience-facing content

    Pipeline: outline → manuscript → review → fact_check → slides → notes → export
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._llm = LLMClient(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )
        self._outline_gen = OutlineGenerator(self._llm, model=config.outline_model)
        self._script_gen = ScriptGenerator(self._llm, model=config.manuscript_model)
        self._script_reviewer = ScriptReviewer(
            self._llm,
            evaluate_model=config.script_review_evaluate_model,
            rewrite_model=config.script_review_rewrite_model,
        )
        self._fact_checker = FactChecker(
            self._llm,
            model=config.script_review_evaluate_model,
        )
        self._slide_gen = SlideGenerator(self._llm, model=config.slide_model)
        self._notes_gen = NotesGenerator(self._llm, model=config.notes_model)
        self._image_svc = ImageService(
            access_key=config.unsplash_access_key,
            base_url=config.unsplash_base_url,
            candidates_per_query=3,
            llm_client=self._llm,
            vision_model=config.image_vision_model,
        )
        self._exporter = PPTExporter()
        self._script_exporter = ScriptExporter()

    def run(
        self,
        topic: str,
        duration_minutes: int,
        audience: str,
        language: str,
        output_path: Optional[Path | str] = None,
        theme: Optional[str] = None,
        speaker_profile: Optional[dict] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> ExportResult:
        """
        Run the full pipeline and produce a PowerPoint file and script.

        Args:
            topic: Presentation topic.
            duration_minutes: Duration in minutes.
            audience: Target audience.
            language: Presentation language.
            output_path: Optional path for .pptx file. If None, uses temp file.
            theme: Visual theme.
            speaker_profile: Optional {"age": int, "role": str?, "experience_level": str?}.

        Returns:
            ExportResult with output_path, script_path, slide_count, images_included.

        Raises:
            PresentationAgentError: On pipeline failure.
        """
        profile = None
        if speaker_profile and isinstance(speaker_profile, dict) and "age" in speaker_profile:
            profile = SpeakerProfile(
                age=speaker_profile["age"],
                role=speaker_profile.get("role"),
                experience_level=speaker_profile.get("experience_level"),
            )
        user_input = UserInput(
            topic=topic,
            duration_minutes=duration_minutes,
            audience=audience,
            language=language,
            theme=theme or "LIGHT_PROFESSIONAL",
            speaker_profile=profile,
        )
        return asyncio.run(
            self._run_async(user_input, output_path, progress_callback)
        )

    def _report(
        self,
        progress_callback: Optional[Callable[[str, int], None]],
        step: str,
        percent: int,
    ) -> None:
        if progress_callback:
            progress_callback(step, percent)
        print(f"[{percent}%] {step}")

    async def _run_async(
        self,
        user_input: UserInput,
        output_path: Optional[Path | str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> ExportResult:
        """Internal async pipeline implementation."""
        try:
            self._report(progress_callback, "Planning structure", 5)
            outline = await self._outline_gen.generate(user_input)

            self._report(progress_callback, "Writing manuscript", 15)
            try:
                manuscript = await self._script_gen.generate(outline, user_input)
            except ScriptGeneratorError as e:
                raise PresentationAgentError(f"Script generation failed: {e}") from e

            self._report(progress_callback, "Reviewing manuscript", 25)
            manuscript, score = await self._script_reviewer.review_and_improve(
                manuscript,
                topic=user_input.topic,
                audience=user_input.audience,
                duration_minutes=user_input.duration_minutes,
                language=user_input.language,
            )
            self._report(progress_callback, f"Manuscript approved ({score}/10)", 35)
            self._report(progress_callback, "Fact-checking", 40)
            manuscript = await self._fact_checker.fact_check_and_patch(
                manuscript,
                topic=user_input.topic,
                audience=user_input.audience,
            )

            self._report(progress_callback, "Creating slides", 55)
            targets = compute_presentation_targets(
                user_input.duration_minutes, user_input.audience
            )
            slides = await self._slide_gen.generate(
                manuscript,
                duration_minutes=user_input.duration_minutes,
                audience=user_input.audience,
            )
            if not is_slide_count_acceptable(
                slides, targets["min_slides"], targets["max_slides"]
            ):
                self._report(progress_callback, "Adjusting slide count, retrying", 60)
                slides = await self._slide_gen.generate(
                    manuscript,
                    duration_minutes=user_input.duration_minutes,
                    audience=user_input.audience,
                    strict_slide_count_retry=True,
                )
            self._report(progress_callback, "Adding speaker notes", 70)
            slides = await self._notes_gen.generate(manuscript, slides)

            self._report(progress_callback, "Selecting images", 80)
            slides_with_images = await self._image_svc.enrich_slides_with_images(
                slides
            )

            self._report(progress_callback, "Exporting files", 92)
            try:
                result = self._exporter.export(
                    slides=slides_with_images,
                    title=manuscript.title,
                    output_path=output_path,
                    theme=user_input.theme,
                )
            except PPTExporterError as e:
                raise PresentationAgentError(f"Export failed: {e}") from e

            # Export manuscript to Word (derive path from ppt output)
            ppt_path = Path(result.output_path)
            script_path = ppt_path.parent / f"{ppt_path.stem}_script.docx"
            try:
                script_file = self._script_exporter.export(
                    manuscript,
                    str(script_path),
                    topic=user_input.topic,
                    duration_minutes=user_input.duration_minutes,
                    audience=user_input.audience,
                )
                result = ExportResult(
                    output_path=result.output_path,
                    script_path=script_file,
                    slide_count=result.slide_count,
                    images_included=result.images_included,
                )
            except Exception:
                pass  # Continue without script export on failure

            self._report(progress_callback, "Done", 100)
            return result

        except ValueError as e:
            raise PresentationAgentError(f"LLM response error: {e}") from e

    async def generate(
        self,
        user_input: UserInput,
        output_path: Optional[Path | str] = None,
    ) -> ExportResult:
        """
        Run the full pipeline and produce a PowerPoint file (async).

        Args:
            user_input: Topic, duration, audience, language.
            output_path: Optional path for the .pptx file. If None, uses temp file.

        Returns:
            ExportResult with output path and counts.

        Raises:
            PresentationAgentError: On pipeline failure.
        """
        return await self._run_async(user_input, output_path)
