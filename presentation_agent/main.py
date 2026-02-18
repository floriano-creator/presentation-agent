"""Entry point for running the presentation agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from presentation_agent.agent import PresentationAgent, PresentationAgentError
from presentation_agent.config import Config


def main() -> None:
    """Runnable entry point with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="AI Presentation Agent – Erstelle Präsentationen aus wenigen Angaben"
    )
    parser.add_argument(
        "--topic", "-t",
        default="Artificial Intelligence in Healthcare",
        help="Thema der Präsentation (default: Artificial Intelligence in Healthcare)",
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=10,
        help="Dauer in Minuten (default: 10)",
    )
    parser.add_argument(
        "--audience", "-a",
        default="University students",
        help="Zielgruppe (default: University students)",
    )
    parser.add_argument(
        "--language", "-l",
        default="English",
        help="Sprache der Präsentation (default: English)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Ausgabepfad für .pptx (default: presentation.pptx im aktuellen Ordner)",
    )
    parser.add_argument(
        "--theme",
        default="LIGHT_PROFESSIONAL",
        choices=["LIGHT_PROFESSIONAL", "DARK_TECH", "CORPORATE_BLUE", "MINIMAL_CLEAN", "BOLD_GRADIENT"],
        help="Design-Theme (default: LIGHT_PROFESSIONAL)",
    )
    parser.add_argument(
        "--speaker-age",
        type=int,
        default=None,
        metavar="N",
        help="Speaker age (adapts manuscript style; e.g. 14, 22, 45). Optional.",
    )
    parser.add_argument(
        "--speaker-role",
        default=None,
        help="Speaker role (e.g. student, professional, teacher). Optional.",
    )
    parser.add_argument(
        "--speaker-experience",
        default=None,
        choices=["beginner", "intermediate", "expert"],
        help="Speaker experience level. Optional.",
    )

    args = parser.parse_args()

    try:
        config = Config.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    agent = PresentationAgent(config)

    output_path = args.output or str(Path.cwd() / "presentation.pptx")

    speaker_profile = None
    if args.speaker_age is not None:
        speaker_profile = {"age": args.speaker_age}
        if args.speaker_role is not None:
            speaker_profile["role"] = args.speaker_role
        if args.speaker_experience is not None:
            speaker_profile["experience_level"] = args.speaker_experience

    try:
        result = agent.run(
            topic=args.topic,
            duration_minutes=args.duration,
            audience=args.audience,
            language=args.language,
            output_path=output_path,
            theme=args.theme,
            speaker_profile=speaker_profile,
        )
        print(f"\nSuccess! Presentation saved to: {result.output_path}")
        if result.script_path:
            print(f"Script saved to: {result.script_path}")
    except PresentationAgentError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
