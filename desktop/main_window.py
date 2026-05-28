"""
ORION Desktop — Main Window
Unified control centre with animated orb, state indicator,
live transcript, mute button, and navigation to Study Mode.
Rich gradient design with depth and premium feel.
"""

import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor, QTextCursor, QPainter, QLinearGradient, QBrush

from desktop.orb_widget import OrbWidget
from desktop.ipc import JsonUDPListener, JsonUDPSender, UI_PORT, ENGINE_PORT


class MuteButton(QPushButton):
    """Animated circular mute/unmute toggle with glow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._muted = False
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle)
        self._apply_style()

    def _toggle(self):
        self._muted = not self._muted
        self._apply_style()

    def _apply_style(self):
        if self._muted:
            self.setText("🔇")
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 rgba(239, 68, 68, 0.35),
                        stop:1 rgba(239, 68, 68, 0.12)
                    );
                    border: 1.5px solid rgba(239, 68, 68, 0.5);
                    border-radius: 28px;
                    font-size: 22px;
                }
                QPushButton:hover {
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 rgba(239, 68, 68, 0.5),
                        stop:1 rgba(239, 68, 68, 0.2)
                    );
                }
            """)
        else:
            self.setText("🎙️")
            self.setStyleSheet("""
                QPushButton {
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 rgba(99, 102, 241, 0.3),
                        stop:1 rgba(99, 102, 241, 0.08)
                    );
                    border: 1.5px solid rgba(99, 102, 241, 0.35);
                    border-radius: 28px;
                    font-size: 22px;
                }
                QPushButton:hover {
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 rgba(99, 102, 241, 0.45),
                        stop:1 rgba(99, 102, 241, 0.15)
                    );
                }
            """)

    @property
    def is_muted(self):
        return self._muted


class GradientPanel(QWidget):
    """A widget with a custom painted gradient background."""

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self._colors = colors  # list of (position, QColor) tuples

    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        for pos, color in self._colors:
            grad.setColorAt(pos, color)
        painter.fillRect(self.rect(), QBrush(grad))
        painter.end()


class TranscriptView(QTextEdit):
    """Sleek, read-only transcript with glassmorphic styling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QTextEdit {
                background: qlineargradient(
                    x1:0, y1:0, x2:0.3, y2:1,
                    stop:0 rgba(15, 20, 40, 0.92),
                    stop:0.5 rgba(20, 25, 50, 0.95),
                    stop:1 rgba(10, 14, 35, 0.97)
                );
                color: rgba(203, 213, 225, 0.9);
                border: 1px solid rgba(99, 102, 241, 0.15);
                border-radius: 16px;
                padding: 20px 22px;
                font-family: 'Inter', 'SF Pro Text', system-ui, sans-serif;
                font-size: 14px;
                line-height: 1.7;
                selection-background-color: rgba(99, 102, 241, 0.3);
            }
            QScrollBar:vertical {
                background: transparent;
                width: 5px;
                margin: 10px 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(139, 92, 246, 0.3);
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(139, 92, 246, 0.55);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def add_bot_message(self, text: str):
        self.append(
            f'<p style="color:#A5B4FC; margin:10px 0; font-size:14px;">'
            f'<span style="color:#818CF8; font-weight:700;">ORION</span> '
            f'<span style="color:rgba(100,116,139,0.5); font-size:10px;">{time.strftime("%H:%M")}</span>'
            f'<br/><span style="color:#C7D2FE;">{text}</span></p>'
        )
        self._scroll()

    def add_user_message(self, text: str):
        self.append(
            f'<p style="color:#A7F3D0; margin:10px 0; font-size:14px;">'
            f'<span style="color:#6EE7B7; font-weight:700;">You</span> '
            f'<span style="color:rgba(100,116,139,0.5); font-size:10px;">{time.strftime("%H:%M")}</span>'
            f'<br/><span style="color:#D1FAE5;">{text}</span></p>'
        )
        self._scroll()

    def add_system_message(self, text: str):
        self.append(
            f'<p style="color:rgba(100,116,139,0.5); margin:4px 0; font-size:11px; font-style:italic;">{text}</p>'
        )
        self._scroll()

    def _scroll(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)


class OrionMainWindow(QMainWindow):
    """Unified ORION Desktop Application with rich gradient design."""

    _state_signal = pyqtSignal(str)
    _transcript_signal = pyqtSignal(str, str)
    _amplitude_signal = pyqtSignal(float)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ORION")
        self.setMinimumSize(960, 640)
        self.resize(1140, 740)

        # IPC
        self._sender = JsonUDPSender(ENGINE_PORT)
        self._listener = JsonUDPListener(UI_PORT, self._handle_ipc)
        self._listener.start()

        # Signals
        self._state_signal.connect(self._on_state_changed)
        self._transcript_signal.connect(self._on_transcript)
        self._amplitude_signal.connect(self._on_amplitude)

        self._build_ui()

        # Decay timer
        self._decay_timer = QTimer(self)
        self._decay_timer.timeout.connect(self._decay_amplitude)
        self._decay_timer.start(100)

    def _handle_ipc(self, msg: dict):
        t = msg.get("type", "")
        if t == "state":
            self._state_signal.emit(msg.get("state", "sleeping"))
        elif t == "transcript":
            self._transcript_signal.emit(msg.get("role", "bot"), msg.get("text", ""))
        elif t == "amplitude":
            self._amplitude_signal.emit(msg.get("value", 0.0))

    def _build_ui(self):
        # ── Root: gradient painted background ──
        central = GradientPanel([
            (0.0,  QColor(6, 8, 18)),
            (0.3,  QColor(12, 16, 38)),
            (0.6,  QColor(18, 12, 42)),
            (0.85, QColor(10, 18, 35)),
            (1.0,  QColor(6, 10, 22)),
        ])
        self.setCentralWidget(central)
        central.setStyleSheet("font-family: 'Inter', 'SF Pro Display', system-ui, sans-serif;")

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ════════════════════════════════════════
        # LEFT PANEL: Orb + State + Speech
        # ════════════════════════════════════════
        orb_panel = QWidget()
        orb_panel.setStyleSheet("background: transparent;")
        orb_layout = QVBoxLayout(orb_panel)
        orb_layout.setContentsMargins(48, 36, 24, 36)
        orb_layout.setSpacing(0)

        orb_layout.addStretch(3)

        # State label
        self.state_label = QLabel("SLEEPING")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("""
            QLabel {
                color: rgba(139, 92, 246, 0.6);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 5px;
                padding-bottom: 20px;
            }
        """)
        orb_layout.addWidget(self.state_label)

        # Orb
        self.orb = OrbWidget()
        self.orb.setFixedSize(340, 340)
        orb_h = QHBoxLayout()
        orb_h.addStretch()
        orb_h.addWidget(self.orb)
        orb_h.addStretch()
        orb_layout.addLayout(orb_h)

        # Bot speech (below orb)
        self.bot_speech_label = QLabel("")
        self.bot_speech_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bot_speech_label.setWordWrap(True)
        self.bot_speech_label.setMaximumWidth(480)
        self.bot_speech_label.setStyleSheet("""
            QLabel {
                color: rgba(199, 210, 254, 0.8);
                font-size: 15px;
                font-weight: 400;
                padding: 24px 20px 0 20px;
                line-height: 1.55;
            }
        """)
        speech_h = QHBoxLayout()
        speech_h.addStretch()
        speech_h.addWidget(self.bot_speech_label)
        speech_h.addStretch()
        orb_layout.addLayout(speech_h)

        orb_layout.addStretch(3)

        # Bottom bar
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)

        self.mute_btn = MuteButton()
        self.mute_btn.clicked.connect(self._on_mute_clicked)
        bottom.addWidget(self.mute_btn)

        bottom.addStretch()

        # Study button
        self.study_btn = QPushButton("📚  Study Mode")
        self.study_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.study_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(99, 102, 241, 0.15),
                    stop:1 rgba(139, 92, 246, 0.1)
                );
                color: #A5B4FC;
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 14px;
                padding: 11px 26px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(99, 102, 241, 0.3),
                    stop:1 rgba(139, 92, 246, 0.2)
                );
                border-color: rgba(99, 102, 241, 0.5);
                color: #C7D2FE;
            }
        """)
        bottom.addWidget(self.study_btn)

        orb_layout.addLayout(bottom)

        root.addWidget(orb_panel, stretch=6)

        # ── Subtle divider line ──
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet("background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 transparent, stop:0.3 rgba(99,102,241,0.2), stop:0.7 rgba(139,92,246,0.15), stop:1 transparent);")
        root.addWidget(divider)

        # ════════════════════════════════════════
        # RIGHT PANEL: Transcript
        # ════════════════════════════════════════
        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(24, 36, 40, 36)
        right_layout.setSpacing(16)

        header = QLabel("Conversation")
        header.setStyleSheet("""
            QLabel {
                color: rgba(199, 210, 254, 0.85);
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.8px;
            }
        """)
        right_layout.addWidget(header)

        self.transcript = TranscriptView()
        right_layout.addWidget(self.transcript, stretch=1)

        self.connection_label = QLabel("● Connected to Voice Engine")
        self.connection_label.setStyleSheet("""
            QLabel {
                color: rgba(110, 231, 183, 0.55);
                font-size: 10px;
                padding-top: 6px;
                letter-spacing: 0.3px;
            }
        """)
        right_layout.addWidget(self.connection_label)

        root.addWidget(right, stretch=4)

    # ── Slots ──

    @pyqtSlot(str)
    def _on_state_changed(self, state: str):
        sl = state.lower()
        self.orb.set_state(sl)

        label_map = {
            "sleeping":   "SLEEPING",
            "listening":  "LISTENING",
            "processing": "THINKING",
            "speaking":   "SPEAKING",
        }
        self.state_label.setText(label_map.get(sl, state.upper()))

        color_map = {
            "sleeping":   "rgba(139, 92, 246, 0.5)",
            "listening":  "rgba(56, 189, 248, 0.85)",
            "processing": "rgba(251, 191, 36, 0.85)",
            "speaking":   "rgba(129, 140, 248, 0.85)",
        }
        c = color_map.get(sl, "rgba(139, 92, 246, 0.5)")
        self.state_label.setStyleSheet(f"""
            QLabel {{
                color: {c};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 5px;
                padding-bottom: 20px;
            }}
        """)

        if sl == "sleeping":
            self.bot_speech_label.setText("")

    @pyqtSlot(str, str)
    def _on_transcript(self, role: str, text: str):
        if role == "bot":
            self.transcript.add_bot_message(text)
            self.bot_speech_label.setText(text)
        elif role == "user":
            self.transcript.add_user_message(text)
        else:
            self.transcript.add_system_message(text)

    @pyqtSlot(float)
    def _on_amplitude(self, value: float):
        self.orb.set_amplitude(value)

    def _decay_amplitude(self):
        self.orb.set_amplitude(max(0, self.orb._target_amplitude - 0.03))

    def _on_mute_clicked(self):
        self._sender.send("mute", muted=self.mute_btn.is_muted)

    def closeEvent(self, event):
        self._listener.stop()
        super().closeEvent(event)
