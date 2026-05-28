"""
Controls Widget — Redesigned with soft gradients and glassmorphism.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QLabel, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal

from study.models.lesson_schema import DifficultyLevel


# Shared button styles
_BTN_BASE = """
    QPushButton {
        background: rgba(30, 41, 59, 0.6);
        color: rgba(226, 232, 240, 0.9);
        border: 1px solid rgba(71, 85, 105, 0.3);
        border-radius: 10px;
        padding: 8px 18px;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 500;
    }
    QPushButton:hover {
        background: rgba(51, 65, 85, 0.7);
        border-color: rgba(100, 116, 139, 0.4);
    }
    QPushButton:pressed {
        background: rgba(71, 85, 105, 0.6);
    }
    QPushButton:disabled {
        color: rgba(100, 116, 139, 0.4);
        border-color: rgba(30, 41, 59, 0.3);
    }
"""

_BTN_ACCENT = """
    QPushButton {
        background: rgba(59, 130, 246, 0.2);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.35);
        border-radius: 10px;
        padding: 8px 18px;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: rgba(59, 130, 246, 0.35);
        border-color: rgba(59, 130, 246, 0.6);
    }
    QPushButton:pressed {
        background: rgba(59, 130, 246, 0.5);
    }
"""


class ControlsPanel(QWidget):
    """Bottom control bar for the study GUI."""

    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    replay_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    difficulty_changed = pyqtSignal(str)
    explain_again_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Playback controls
        self.btn_prev = QPushButton("⏮ Prev")
        self.btn_prev.setStyleSheet(_BTN_BASE)
        self.btn_prev.clicked.connect(self.prev_clicked.emit)
        layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setStyleSheet(_BTN_ACCENT)
        self.btn_play.clicked.connect(self._toggle_play)
        layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("Next ⏭")
        self.btn_next.setStyleSheet(_BTN_BASE)
        self.btn_next.clicked.connect(self.next_clicked.emit)
        layout.addWidget(self.btn_next)

        layout.addSpacing(20)

        # Replay & alternative explanation
        self.btn_replay = QPushButton("🔄 Replay")
        self.btn_replay.setStyleSheet(_BTN_BASE)
        self.btn_replay.clicked.connect(self.replay_clicked.emit)
        layout.addWidget(self.btn_replay)

        self.btn_explain = QPushButton("💡 Explain Differently")
        self.btn_explain.setStyleSheet(_BTN_BASE)
        self.btn_explain.clicked.connect(self.explain_again_clicked.emit)
        layout.addWidget(self.btn_explain)

        layout.addStretch()

        # Difficulty selector
        diff_label = QLabel("Level:")
        diff_label.setStyleSheet("""
            color: rgba(148, 163, 184, 0.6);
            font-family: 'Inter', sans-serif;
            font-size: 12px;
        """)
        layout.addWidget(diff_label)

        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems([level.value for level in DifficultyLevel])
        self.difficulty_combo.setCurrentText(DifficultyLevel.SCHOOL.value)
        self.difficulty_combo.setStyleSheet("""
            QComboBox {
                background: rgba(30, 41, 59, 0.6);
                color: rgba(226, 232, 240, 0.9);
                border: 1px solid rgba(71, 85, 105, 0.3);
                border-radius: 8px;
                padding: 6px 14px;
                font-family: 'Inter', sans-serif;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1E293B;
                color: #E2E8F0;
                selection-background-color: rgba(59, 130, 246, 0.4);
                border: 1px solid rgba(71, 85, 105, 0.3);
                border-radius: 6px;
            }
        """)
        self.difficulty_combo.currentTextChanged.connect(self.difficulty_changed.emit)
        layout.addWidget(self.difficulty_combo)

        # Stop
        self.btn_stop = QPushButton("⬛ Stop")
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.12);
                color: rgba(252, 165, 165, 0.9);
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 10px;
                padding: 8px 18px;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.25);
                border-color: rgba(239, 68, 68, 0.5);
            }
        """)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.btn_stop)

        self._is_playing = False

    def _toggle_play(self):
        if self._is_playing:
            self.btn_play.setText("▶ Play")
            self._is_playing = False
            self.pause_clicked.emit()
        else:
            self.btn_play.setText("⏸ Pause")
            self._is_playing = True
            self.play_clicked.emit()

    def set_playing(self, playing: bool):
        self._is_playing = playing
        self.btn_play.setText("⏸ Pause" if playing else "▶ Play")

    def set_progress(self, current: int, total: int):
        """Update which subconcept we're on."""
        self.btn_prev.setEnabled(current > 0)
        self.btn_next.setEnabled(current < total - 1)
