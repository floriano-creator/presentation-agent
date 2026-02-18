"""Streamlit web app for the AI Presentation Agent."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from pathlib import Path

import streamlit as st

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from presentation_agent.agent import PresentationAgent, PresentationAgentError
from presentation_agent.config import Config

# Session state keys
KEY_PROGRESS = "progress"
KEY_RESULT_FILES = "result_files"

THEMES = [
    "LIGHT_PROFESSIONAL",
    "DARK_TECH",
    "CORPORATE_BLUE",
    "MINIMAL_CLEAN",
    "BOLD_GRADIENT",
]

LANGUAGES = [
    "Deutsch",
    "Englisch",
    "Französisch",
    "Spanisch",
    "Italienisch",
    "Portugiesisch",
    "Niederländisch",
    "Polnisch",
    "Japanisch",
    "Chinesisch (vereinfacht)",
]

AUDIENCE_PRESETS = [
    "Allgemeines Publikum",
    "Studierende",
    "Schüler/innen",
    "Fachpublikum / Technisch",
    "Führungskräfte",
    "Lehrkräfte",
    "Sonstiges (unten eingeben)",
]


def _ensure_progress_state() -> None:
    if KEY_PROGRESS not in st.session_state:
        st.session_state[KEY_PROGRESS] = {
            "step": "",
            "percent": 0,
            "status": "idle",  # idle | running | done | error
            "error": None,
        }


@st.fragment(run_every=2)
def _progress_ui() -> None:
    """Poll and display progress; no full page reload."""
    _ensure_progress_state()
    progress = st.session_state[KEY_PROGRESS]
    status = progress["status"]

    if status == "idle":
        return

    if status == "running":
        st.markdown("---")
        st.subheader("Präsentation wird erstellt …")
        with st.status("Fortschritt", state="running", expanded=True):
            st.caption(progress["step"] or "Starte …")
            st.progress(min(100, max(0, progress["percent"])) / 100.0)
        return

    if status == "error":
        st.markdown("---")
        st.error("Generierung fehlgeschlagen")
        st.error(progress.get("error") or "Unbekannter Fehler")
        if "Konfiguration" in str(progress.get("error") or ""):
            st.info("Bitte OPENAI_API_KEY und UNSPLASH_ACCESS_KEY in der .env-Datei setzen.")
        if st.button("Erneut versuchen", key="retry_btn"):
            for key in (KEY_PROGRESS, KEY_RESULT_FILES):
                st.session_state.pop(key, None)
            st.rerun()
        return

    if status == "done":
        st.markdown("---")
        files = st.session_state.get(KEY_RESULT_FILES) or {}
        ppt_bytes = files.get("ppt")
        docx_bytes = files.get("docx")
        slide_count = files.get("slide_count", 0)
        images_included = files.get("images_included", 0)

        if ppt_bytes:
            st.success(
                f"Fertig: {slide_count} Folien mit {images_included} Bildern."
            )
            st.download_button(
                label="PowerPoint herunterladen (.pptx)",
                data=ppt_bytes,
                file_name="praesentation.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary",
                key="dl_pptx",
            )
        if docx_bytes:
            st.download_button(
                label="Manuskript herunterladen (.docx)",
                data=docx_bytes,
                file_name="manuskript.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_docx",
            )
        if st.button("Neue Präsentation erstellen", type="secondary", key="new_pres_btn"):
            for key in (KEY_PROGRESS, KEY_RESULT_FILES):
                st.session_state.pop(key, None)
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="KI Präsentations-Generator",
        page_icon="📊",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        .stTextInput input, .stNumberInput input { font-size: 1.05rem !important; }
        .stSelectbox > div { font-size: 1.05rem !important; }
        .stForm { max-width: 42rem; margin: 0 auto; }
        section.main .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 44rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📊 KI Präsentations-Generator")
    st.markdown("Erstelle eine Präsentation zu einem Thema. Wähle unten Design und Optionen.")

    _ensure_progress_state()
    progress = st.session_state[KEY_PROGRESS]

    with st.form("presentation_form", clear_on_submit=False):
        st.subheader("Einstellungen")

        topic = st.text_input(
            "Thema",
            value="Künstliche Intelligenz im Gesundheitswesen",
            placeholder="z. B. Klimawandel und erneuerbare Energien",
            help="Das Hauptthema deiner Präsentation.",
        ).strip()

        col1, col2 = st.columns(2)
        with col1:
            duration_minutes = st.number_input(
                "Dauer (Minuten)",
                min_value=1,
                max_value=120,
                value=5,
                step=1,
                help="Ziel-Länge der Präsentation.",
            )
        with col2:
            audience_preset = st.selectbox(
                "Zielgruppe (Vorgabe)",
                options=AUDIENCE_PRESETS,
                index=0,
                help="Zielgruppe für Ton und Tiefe.",
            )

        audience_custom = st.text_input(
            "Zielgruppe (eigene)",
            placeholder="Leer lassen für Vorgabe",
            help="Eigene Beschreibung der Zielgruppe.",
        ).strip()
        audience = audience_custom if audience_custom else audience_preset

        col3, col4 = st.columns(2)
        with col3:
            language = st.selectbox(
                "Sprache",
                options=LANGUAGES,
                index=0,
                help="Sprache der Präsentation.",
            )
        with col4:
            speaker_age = st.number_input(
                "Alter des Vortragenden (optional)",
                min_value=1,
                max_value=120,
                value=30,
                step=1,
                help="Passt den Manuskript-Stil an. 30 = neutral.",
            )

        theme = st.selectbox(
            "Design-Theme",
            options=THEMES,
            index=0,
            help="Visuelles Theme für die Folien.",
        )

        submitted = st.form_submit_button("Präsentation erstellen")

    if not submitted:
        _progress_ui()
        return

    if not topic:
        st.error("Bitte gib ein Thema ein.")
        _progress_ui()
        return

    # Only start generation if not already running
    if progress["status"] == "running":
        _progress_ui()
        return

    # Persistent output path (kept for the lifetime of the run)
    tmpdir = tempfile.mkdtemp(prefix="presentation_agent_")
    output_pptx = os.path.join(tmpdir, "presentation.pptx")

    speaker_profile = None
    if speaker_age and speaker_age != 30:
        speaker_profile = {"age": int(speaker_age)}

    # Set progress to running and start background thread.
    # Thread only mutates these dicts (no st.session_state access from thread).
    progress["step"] = "Starte …"
    progress["percent"] = 0
    progress["status"] = "running"
    progress["error"] = None
    result_holder = st.session_state.setdefault(KEY_RESULT_FILES, {})
    result_holder.clear()

    def run_agent() -> None:
        try:
            config = Config.from_env()
            agent = PresentationAgent(config)

            def on_progress(step_name: str, percent: int = 0) -> None:
                progress["step"] = step_name
                progress["percent"] = percent

            result = agent.run(
                topic=topic,
                duration_minutes=int(duration_minutes),
                audience=audience,
                language=language,
                output_path=output_pptx,
                theme=theme,
                speaker_profile=speaker_profile,
                progress_callback=on_progress,
            )
            # Persist to shared dicts (same refs as in session_state)
            ppt_path = Path(result.output_path)
            result_holder["ppt"] = ppt_path.read_bytes() if ppt_path.exists() else None
            result_holder["docx"] = None
            if result.script_path and Path(result.script_path).exists():
                result_holder["docx"] = Path(result.script_path).read_bytes()
            result_holder["slide_count"] = result.slide_count
            result_holder["images_included"] = result.images_included
            progress["status"] = "done"
            progress["percent"] = 100
            progress["step"] = "Fertig"
        except ValueError as e:
            progress["status"] = "error"
            progress["error"] = f"Konfigurationsfehler: {e}"
        except PresentationAgentError as e:
            progress["status"] = "error"
            progress["error"] = str(e)
        except Exception as e:
            progress["status"] = "error"
            progress["error"] = f"Erstellung fehlgeschlagen: {e}"

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()

    _progress_ui()


if __name__ == "__main__":
    main()
