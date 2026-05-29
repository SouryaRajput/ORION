"""
ORION Desktop — Main Window
============================
Premium AI assistant interface with a soft pastel living gradient
atmosphere, frosted glass panels, iridescent orb, floating particles,
and smooth animated transitions.

Aesthetic: Apple Intelligence × OpenAI Voice Mode × Arc Browser
           Soft pinks, peaches, lavenders, and cyans on a warm light base.
"""

import math
import time
import random

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, pyqtSlot, QSize,
    QPropertyAnimation, QEasingCurve, QPoint, QRect,
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCursor, QPainter, QLinearGradient,
    QBrush, QRadialGradient, QPen,
)

from desktop.orb_widget import OrbWidget
from desktop.ipc import JsonUDPListener, JsonUDPSender, UI_PORT, ENGINE_PORT


# ═══════════════════════════════════════════════
# Animated Mute Button — soft glass on light bg
# ═══════════════════════════════════════════════

class MuteButton(QPushButton):
    """Circular mute/unmute toggle with soft pastel glow."""

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
                    background: rgba(255, 120, 120, 0.2);
                    border: 1.5px solid rgba(255, 120, 120, 0.35);
                    border-radius: 28px;
                    font-size: 22px;
                }
                QPushButton:hover {
                    background: rgba(255, 120, 120, 0.3);
                    border-color: rgba(255, 120, 120, 0.5);
                }
            """)
        else:
            self.setText("🎙️")
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(179, 136, 255, 0.18);
                    border: 1.5px solid rgba(179, 136, 255, 0.3);
                    border-radius: 28px;
                    font-size: 22px;
                }
                QPushButton:hover {
                    background: rgba(179, 136, 255, 0.3);
                    border-color: rgba(179, 136, 255, 0.5);
                }
            """)

    @property
    def is_muted(self):
        return self._muted


# ═══════════════════════════════════════════════
# Living Pastel Background — soft aurora blobs
# ═══════════════════════════════════════════════

class LivingBackground(QWidget):
    """Animated warm pastel atmosphere with drifting color blobs,
    aurora-like movement, and subtle floating particles.
    Light base — pinks, peaches, lavenders, sky blues."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0

        # Large pastel aurora blobs — high opacity on light bg
        self._blobs = []
        blob_colors = [
            (255, 170, 210, 85),   # soft pink
            (195, 160, 255, 80),   # lavender
            (150, 240, 252, 75),   # ice cyan
            (255, 220, 170, 80),   # warm peach
            (255, 130, 195, 65),   # rose
            (170, 205, 255, 70),   # sky blue
            (255, 195, 150, 70),   # apricot
            (205, 170, 255, 75),   # light violet
        ]
        for r, g, b, a in blob_colors:
            self._blobs.append({
                "color": (r, g, b, a),
                "cx": random.uniform(0.1, 0.9),
                "cy": random.uniform(0.1, 0.9),
                "radius": random.uniform(0.3, 0.55),
                "speed_x": random.uniform(0.015, 0.05) * random.choice([-1, 1]),
                "speed_y": random.uniform(0.01, 0.04) * random.choice([-1, 1]),
                "phase": random.uniform(0, math.tau),
            })

        # Soft floating particles (sparkles)
        self._particles = []
        for _ in range(35):
            self._particles.append({
                "x": random.uniform(0, 1),
                "y": random.uniform(0, 1),
                "size": random.uniform(1.5, 3.0),
                "alpha": random.uniform(0.08, 0.25),
                "speed_y": random.uniform(-0.002, -0.0005),
                "drift_x": random.uniform(-0.001, 0.001),
                "phase": random.uniform(0, math.tau),
                "color": random.choice([
                    (255, 255, 255),
                    (255, 200, 230),
                    (200, 190, 255),
                    (180, 230, 255),
                ]),
            })

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _tick(self):
        self._t += 0.033
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        # ── Soft warm pastel base gradient ──
        base = QLinearGradient(0, 0, w, h)
        shift = math.sin(self._t * 0.04) * 8

        # Light pastel base that gently shifts
        base.setColorAt(0.0, QColor(255, 230 + int(shift), 240))       # warm pink-white
        base.setColorAt(0.25, QColor(240, 225 + int(shift * 0.5), 250))  # soft lavender
        base.setColorAt(0.5, QColor(235 + int(shift), 240, 255))       # pale sky
        base.setColorAt(0.75, QColor(255, 235, 225 + int(shift * 0.7)))  # peach cream
        base.setColorAt(1.0, QColor(250, 228 + int(shift * 0.3), 245))  # rose mist
        painter.fillRect(self.rect(), QBrush(base))

        # ── Drifting aurora blobs ──
        for blob in self._blobs:
            bx = blob["cx"] + math.sin(self._t * blob["speed_x"] + blob["phase"]) * 0.15
            by = blob["cy"] + math.cos(self._t * blob["speed_y"] + blob["phase"]) * 0.12
            br = blob["radius"]
            r, g, b, a = blob["color"]

            # Gentle pulsing alpha
            pulse = 0.7 + 0.3 * math.sin(self._t * 0.3 + blob["phase"])
            alpha = int(a * pulse)

            grad = QRadialGradient(bx * w, by * h, br * max(w, h))
            grad.setColorAt(0.0, QColor(r, g, b, alpha))
            grad.setColorAt(0.35, QColor(r, g, b, int(alpha * 0.65)))
            grad.setColorAt(0.7, QColor(r, g, b, int(alpha * 0.25)))
            grad.setColorAt(1.0, QColor(r, g, b, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            radius = br * max(w, h)
            painter.drawEllipse(
                int(bx * w - radius), int(by * h - radius),
                int(radius * 2), int(radius * 2),
            )

        # ── Floating particles / sparkles ──
        for p in self._particles:
            px = (p["x"] + math.sin(self._t * 0.25 + p["phase"]) * 0.012 + p["drift_x"] * self._t) % 1.0
            py = (p["y"] + p["speed_y"] * self._t * 0.4) % 1.0
            flicker = 0.4 + 0.6 * math.sin(self._t * 0.6 + p["phase"])
            alpha = int(p["alpha"] * 255 * flicker)

            if alpha > 3:
                cr, cg, cb = p["color"]
                painter.setBrush(QColor(cr, cg, cb, alpha))
                painter.setPen(Qt.PenStyle.NoPen)
                size = p["size"]
                painter.drawEllipse(int(px * w), int(py * h), int(size), int(size))

        painter.end()


# ═══════════════════════════════════════════════
# Glassmorphic Transcript Panel — frosted glass on light bg
# ═══════════════════════════════════════════════

class TranscriptView(QTextEdit):
    """Frosted glass transcript panel with soft pink/violet borders,
    designed to sit beautifully on a pastel background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QTextEdit {
                background: rgba(255, 255, 255, 0.45);
                color: rgba(60, 40, 80, 0.9);
                border: 1px solid rgba(200, 170, 255, 0.3);
                border-radius: 24px;
                padding: 22px 24px;
                font-family: 'Inter', 'SF Pro Text', system-ui, sans-serif;
                font-size: 14px;
                line-height: 1.7;
                selection-background-color: rgba(179, 136, 255, 0.2);
            }
            QScrollBar:vertical {
                background: transparent;
                width: 5px;
                margin: 14px 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(179, 136, 255, 0.25);
                border-radius: 2px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(179, 136, 255, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def add_bot_message(self, text: str):
        self.append(
            f'<p style="margin:12px 0; font-size:14px;">'
            f'<span style="color:#7C3AED; font-weight:700;">ORION</span> '
            f'<span style="color:rgba(140,120,170,0.45); font-size:10px;">{time.strftime("%H:%M")}</span>'
            f'<br/><span style="color:#4C3570;">{text}</span></p>'
        )
        self._scroll()

    def add_user_message(self, text: str):
        self.append(
            f'<p style="margin:12px 0; font-size:14px;">'
            f'<span style="color:#0D9488; font-weight:700;">You</span> '
            f'<span style="color:rgba(140,120,170,0.45); font-size:10px;">{time.strftime("%H:%M")}</span>'
            f'<br/><span style="color:#1F4D48;">{text}</span></p>'
        )
        self._scroll()

    def add_system_message(self, text: str):
        self.append(
            f'<p style="color:rgba(120,100,150,0.45); margin:4px 0; font-size:11px; font-style:italic;">{text}</p>'
        )
        self._scroll()

    def _scroll(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)


# ═══════════════════════════════════════════════
# Main Window
# ═══════════════════════════════════════════════

class OrionMainWindow(QMainWindow):
    """Premium ORION Desktop — soft pastel living atmosphere with glass panels."""

    _state_signal = pyqtSignal(str)
    _transcript_signal = pyqtSignal(str, str)
    _amplitude_signal = pyqtSignal(float)

    # State label colors — visible on pastel light bg
    STATE_COLORS = {
        "sleeping":   "rgba(140, 100, 180, 0.5)",
        "listening":  "rgba(14, 165, 180, 0.85)",
        "processing": "rgba(200, 140, 40, 0.85)",
        "speaking":   "rgba(124, 58, 237, 0.85)",
    }

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

        self._transcript_visible = True
        self._slide_anim = None  # Will hold the QPropertyAnimation

        self._build_ui()

        # Amplitude decay timer
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
        # ── Root: Living pastel gradient background ──
        self._bg = LivingBackground()
        self.setCentralWidget(self._bg)
        self._bg.setStyleSheet("font-family: 'Inter', 'SF Pro Display', system-ui, sans-serif;")

        root = QHBoxLayout(self._bg)
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

        # State label — dark text on light bg
        self.state_label = QLabel("SLEEPING")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state_label.setStyleSheet("""
            QLabel {
                color: rgba(140, 100, 180, 0.5);
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 5px;
                padding-bottom: 20px;
            }
        """)
        orb_layout.addWidget(self.state_label)

        # Orb
        self.orb = OrbWidget()
        self.orb.setFixedSize(360, 360)
        orb_h = QHBoxLayout()
        orb_h.addStretch()
        orb_h.addWidget(self.orb)
        orb_h.addStretch()
        orb_layout.addLayout(orb_h)

        # Bot speech label (below orb) — dark text on light bg
        self.bot_speech_label = QLabel("")
        self.bot_speech_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bot_speech_label.setWordWrap(True)
        self.bot_speech_label.setMaximumWidth(500)
        self.bot_speech_label.setStyleSheet("""
            QLabel {
                color: rgba(60, 40, 80, 0.75);
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

        # ── Bottom bar ──
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)

        self.mute_btn = MuteButton()
        self.mute_btn.clicked.connect(self._on_mute_clicked)
        bottom.addWidget(self.mute_btn)

        bottom.addStretch()

        # Toggle Transcript button
        self.toggle_transcript_btn = QPushButton("💬")
        self.toggle_transcript_btn.setFixedSize(44, 44)
        self.toggle_transcript_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_transcript_btn.setStyleSheet("""
            QPushButton {
                background: rgba(179, 136, 255, 0.15);
                color: #7C3AED;
                border: 1px solid rgba(179, 136, 255, 0.25);
                border-radius: 22px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(179, 136, 255, 0.25);
                border-color: rgba(179, 136, 255, 0.45);
            }
        """)
        self.toggle_transcript_btn.clicked.connect(self._toggle_transcript)
        bottom.addWidget(self.toggle_transcript_btn)

        bottom.addSpacing(10)

        # Study button
        self.study_btn = QPushButton("📚  Study")
        self.study_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.study_btn.setStyleSheet("""
            QPushButton {
                background: rgba(179, 136, 255, 0.12);
                color: rgba(100, 60, 160, 0.8);
                border: 1px solid rgba(179, 136, 255, 0.22);
                border-radius: 14px;
                padding: 11px 22px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(179, 136, 255, 0.22);
                border-color: rgba(179, 136, 255, 0.45);
                color: rgba(100, 60, 160, 0.95);
            }
        """)
        bottom.addWidget(self.study_btn)

        orb_layout.addLayout(bottom)

        root.addWidget(orb_panel, stretch=6)

        # ── Subtle divider ──
        self.divider = QFrame()
        self.divider.setFixedWidth(1)
        self.divider.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop:0 transparent, "
            "stop:0.2 rgba(200,170,255,0.2), "
            "stop:0.5 rgba(255,160,210,0.18), "
            "stop:0.8 rgba(165,243,252,0.12), "
            "stop:1 transparent);"
        )
        root.addWidget(self.divider)

        # ════════════════════════════════════════
        # RIGHT PANEL: Transcript
        # ════════════════════════════════════════
        self.right_panel = QWidget()
        self.right_panel.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(24, 36, 40, 36)
        right_layout.setSpacing(16)

        # Header row
        header_layout = QHBoxLayout()

        header = QLabel("Conversation")
        header.setStyleSheet("""
            QLabel {
                color: rgba(80, 55, 120, 0.8);
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.8px;
            }
        """)
        header_layout.addWidget(header)
        header_layout.addStretch()

        # New conversation button
        self.new_chat_btn = QPushButton("✨ New")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.12);
                color: rgba(13, 148, 136, 0.8);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 12px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.2);
                color: rgba(13, 148, 136, 0.95);
                border-color: rgba(16, 185, 129, 0.45);
            }
        """)
        self.new_chat_btn.clicked.connect(self._clear_conversation)
        header_layout.addWidget(self.new_chat_btn)

        right_layout.addLayout(header_layout)

        # Transcript
        self.transcript = TranscriptView()
        right_layout.addWidget(self.transcript, stretch=1)

        # Connection status
        self.connection_label = QLabel("● Connected to Voice Engine")
        self.connection_label.setStyleSheet("""
            QLabel {
                color: rgba(13, 148, 136, 0.45);
                font-size: 10px;
                padding-top: 6px;
                letter-spacing: 0.3px;
            }
        """)
        right_layout.addWidget(self.connection_label)

        root.addWidget(self.right_panel, stretch=4)

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

        c = self.STATE_COLORS.get(sl, "rgba(140, 100, 180, 0.5)")
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

    def _toggle_transcript(self):
        if self._slide_anim and self._slide_anim.state() == QPropertyAnimation.State.Running:
            return  # Don't interrupt a running animation

        if self._transcript_visible:
            # Slide out: animate maxWidth from current width to 0
            self._slide_anim = QPropertyAnimation(self.right_panel, b"maximumWidth")
            self._slide_anim.setDuration(350)
            self._slide_anim.setStartValue(self.right_panel.width())
            self._slide_anim.setEndValue(0)
            self._slide_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._slide_anim.finished.connect(lambda: self.right_panel.setVisible(False))
            self._slide_anim.start()
            self.divider.setVisible(False)
            self._transcript_visible = False
        else:
            # Slide in: show widget at 0 width and animate to full
            self.right_panel.setMaximumWidth(0)
            self.right_panel.setVisible(True)
            self.divider.setVisible(True)
            target_width = int(self.width() * 0.38)  # ~4/10 stretch ratio
            self._slide_anim = QPropertyAnimation(self.right_panel, b"maximumWidth")
            self._slide_anim.setDuration(400)
            self._slide_anim.setStartValue(0)
            self._slide_anim.setEndValue(target_width)
            self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._slide_anim.finished.connect(lambda: self.right_panel.setMaximumWidth(16777215))
            self._slide_anim.start()
            self._transcript_visible = True

    def _clear_conversation(self):
        self.transcript.clear()
        self.bot_speech_label.setText("")
        self.transcript.add_system_message("Conversation cleared.")

    def closeEvent(self, event):
        self._listener.stop()
        super().closeEvent(event)
