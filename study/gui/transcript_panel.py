"""
Transcript Panel — Redesigned with soft gradients and minimal aesthetic.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor


class TranscriptPanel(QWidget):
    """Scrollable transcript/chat panel for the study session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QLabel("📝 Lesson Transcript")
        header.setStyleSheet("""
            QLabel {
                color: rgba(226, 232, 240, 0.85);
                font-size: 14px;
                font-weight: 600;
                font-family: 'Inter', sans-serif;
                padding: 4px 0;
                letter-spacing: 0.3px;
            }
        """)
        layout.addWidget(header)

        # Transcript area
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setFont(QFont("Inter", 14))
        self.transcript.setStyleSheet("""
            QTextEdit {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(17, 24, 39, 0.9),
                    stop:1 rgba(10, 15, 30, 0.95)
                );
                color: rgba(226, 232, 240, 0.85);
                font-size: 14px;
                border: 1px solid rgba(71, 85, 105, 0.25);
                border-radius: 12px;
                padding: 14px;
                selection-background-color: rgba(59, 130, 246, 0.3);
            }
            QScrollBar:vertical {
                background: transparent;
                width: 5px;
                margin: 8px 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(148, 163, 184, 0.25);
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(148, 163, 184, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        layout.addWidget(self.transcript)

    @pyqtSlot(str)
    def add_narration(self, text: str):
        """Add a narration line from ORION (spoken text)."""
        self.transcript.append(f'<p style="color:#93C5FD; margin:6px 0; font-size:14px;">🗣️ {text}</p>')
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_hook(self, text: str):
        """Add a curiosity hook."""
        self.transcript.append(f'<p style="color:#F59E0B; margin:8px 0; font-size:14px; font-weight:bold;">💡 {text}</p>')
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_intuition(self, text: str):
        """Add an intuition block."""
        self.transcript.append(f'<p style="color:#34D399; margin:6px 0; font-size:14px;">🧠 {text}</p>')
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_formula(self, text: str):
        """Add a formula / equation."""
        self.transcript.append(f'<p style="color:#A78BFA; margin:6px 0; font-size:14px; font-family:monospace;">📐 {text}</p>')
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_definition(self, text: str):
        """Add a formal definition."""
        self.transcript.append(
            f'<div style="background-color:rgba(30,41,59,0.5); border-left:3px solid rgba(59,130,246,0.5); padding:8px 12px; margin:8px 0; border-radius:6px;">'
            f'<p style="color:#E2E8F0; font-size:14px;">📖 {text}</p></div>'
        )
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_misconception(self, text: str):
        """Add a misconception warning."""
        self.transcript.append(
            f'<div style="background-color:rgba(45,27,27,0.5); border-left:3px solid rgba(239,68,68,0.5); padding:8px 12px; margin:8px 0; border-radius:6px;">'
            f'<p style="color:#FCA5A5; font-size:13px;">⚠️ Common Misconception: {text}</p></div>'
        )
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_user_message(self, text: str):
        """Add a message from the student."""
        self.transcript.append(f'<p style="color:#A7F3D0; margin:4px 0;">👤 {text}</p>')
        self._scroll_to_bottom()

    @pyqtSlot(str)
    def add_system_message(self, text: str):
        """Add a system/status message."""
        self.transcript.append(f'<p style="color:rgba(107,114,128,0.7); margin:4px 0; font-style:italic;">{text}</p>')
        self._scroll_to_bottom()

    @pyqtSlot(str, str)
    def add_subconcept_header(self, name: str, difficulty: str):
        """Add a visual header when starting a new subconcept."""
        self.transcript.append(
            f'<hr style="border-color:rgba(71,85,105,0.2);">'
            f'<p style="color:#F59E0B; font-weight:bold; font-size:15px; margin:10px 0;">📌 {name} '
            f'<span style="color:rgba(107,114,128,0.6); font-weight:normal; font-size:12px;">({difficulty})</span></p>'
        )
        self._scroll_to_bottom()

    def clear(self):
        """Clear the transcript."""
        self.transcript.clear()

    def _scroll_to_bottom(self):
        cursor = self.transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.transcript.setTextCursor(cursor)
