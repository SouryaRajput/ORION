#!/usr/bin/env python3
"""
ORION Desktop — Entry Point
Launches the unified ORION desktop application.

Usage:
    python -m desktop.run
"""

import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from desktop.main_window import OrionMainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ORION")
    app.setOrganizationName("ORION")

    # Global font
    font = QFont("Inter", 13)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Global tooltip style
    app.setStyleSheet("""
        QToolTip {
            background-color: #1F2937;
            color: #F3F4F6;
            border: 1px solid rgba(71, 85, 105, 0.4);
            border-radius: 6px;
            padding: 6px 10px;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
        }
    """)

    window = OrionMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
