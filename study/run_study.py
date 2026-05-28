#!/usr/bin/env python3
"""
ORION Study Mode — Entry Point
Launch the AI Study Mode desktop application.

Usage:
    python -m study.run_study
    python study/run_study.py
    python study/run_study.py --topic "Newton's Laws of Motion"
"""

import sys
import argparse
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from study.gui.main_window import StudyMainWindow
from study.utils.logger import get_logger

log = get_logger("main")


def create_tts_function():
    """
    Attempts to import the existing ORION TTS engine.
    Falls back to console output if not available.
    """
    try:
        from voice.tts import speak_eleven
        log.info("Using ORION ElevenLabs TTS engine.")
        return speak_eleven
    except ImportError:
        log.info("ORION TTS not available. Using console fallback.")
        return None


def main():
    parser = argparse.ArgumentParser(description="ORION Study Mode")
    parser.add_argument("--topic", type=str, default=None, help="Auto-start with this topic")
    parser.add_argument("--quality", type=str, default="low", choices=["low", "medium", "high"], help="Manim render quality")
    args = parser.parse_args()

    # Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("ORION Study Mode")
    app.setOrganizationName("ORION")

    # Global stylesheet
    app.setStyleSheet("""
        QToolTip {
            background-color: #1F2937;
            color: #F3F4F6;
            border: 1px solid #374151;
            border-radius: 4px;
            padding: 4px 8px;
            font-family: 'Inter', sans-serif;
        }
    """)

    # Try to set a nice font
    font = QFont("Inter", 13)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Create TTS function
    tts_fn = create_tts_function()

    # Create main window
    window = StudyMainWindow(tts_function=tts_fn)
    # Auto-start with topic if provided, else keep hidden in background
    if args.topic:
        window.show()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: window.start_lesson_from_voice(args.topic))
    else:
        log.info("ORION Study Mode running in background. Waiting for voice trigger...")

    log.info("ORION Study Mode launched.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
