"""
Animated Orb Widget — Vibrant, colorful orb with layered radial gradients,
vivid glows, and organic morphing. Designed to feel premium and alive.

States & Behaviours:
  SLEEPING  → soft violet-indigo, slow dreamy pulse
  LISTENING → vivid cyan-teal, bright attentive glow
  PROCESSING → golden-amber shimmer with rotating ring
  SPEAKING  → electric blue-magenta with amplitude-driven morph
"""

import math
import random

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QRadialGradient, QColor, QPen, QPainterPath,
    QConicalGradient, QBrush
)


class OrbWidget(QWidget):
    """Animated orb that reacts to the agent's state."""

    SLEEPING = "sleeping"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

    # Rich color palettes: (inner_bright, core, mid, outer_glow, accent)
    PALETTES = {
        SLEEPING: {
            "inner":  (180, 160, 255),
            "core":   (110, 80, 200),
            "mid":    (70, 50, 160),
            "glow":   (90, 60, 180),
            "accent": (140, 100, 240),
            "ring":   (160, 130, 255),
        },
        LISTENING: {
            "inner":  (120, 255, 255),
            "core":   (40, 200, 220),
            "mid":    (20, 150, 180),
            "glow":   (30, 180, 210),
            "accent": (80, 240, 255),
            "ring":   (60, 220, 240),
        },
        PROCESSING: {
            "inner":  (255, 220, 100),
            "core":   (240, 180, 60),
            "mid":    (200, 140, 30),
            "glow":   (220, 160, 40),
            "accent": (255, 200, 80),
            "ring":   (255, 190, 60),
        },
        SPEAKING: {
            "inner":  (180, 160, 255),
            "core":   (120, 100, 255),
            "mid":    (160, 60, 220),
            "glow":   (140, 80, 240),
            "accent": (200, 120, 255),
            "ring":   (100, 140, 255),
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._state = self.SLEEPING
        self._t = 0.0
        self._amplitude = 0.0
        self._target_amplitude = 0.0
        self._phase_offsets = [random.uniform(0, math.tau) for _ in range(16)]

        # Smooth colour lerp
        self._colors = {k: v for k, v in self.PALETTES[self.SLEEPING].items()}
        self._target_colors = {k: v for k, v in self.PALETTES[self.SLEEPING].items()}

        # 60fps timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_state(self, state: str):
        state = state.lower()
        if state in self.PALETTES:
            self._state = state
            self._target_colors = {k: v for k, v in self.PALETTES[state].items()}

    def set_amplitude(self, amp: float):
        self._target_amplitude = max(0.0, min(1.0, amp))

    def _tick(self):
        speed = {"sleeping": 0.35, "listening": 0.7, "processing": 1.5, "speaking": 1.0}.get(self._state, 0.6)
        self._t += 0.016 * speed

        # Lerp amplitude
        self._amplitude += (self._target_amplitude - self._amplitude) * 0.1

        # Lerp all colors
        for key in self._colors:
            c = self._colors[key]
            t = self._target_colors[key]
            self._colors[key] = tuple(int(c[j] + (t[j] - c[j]) * 0.05) for j in range(3))

        self.update()

    def _make_color(self, key, alpha=255):
        c = self._colors[key]
        return QColor(c[0], c[1], c[2], alpha)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_r = min(w, h) * 0.30

        # ── Layer 1: Deep ambient glow (very wide, soft) ──
        for i in range(5):
            r = base_r + 55 + i * 22
            a = max(0, 28 - i * 5)
            grad = QRadialGradient(QPointF(cx, cy), r)
            grad.setColorAt(0.0, self._make_color("glow", a))
            grad.setColorAt(0.6, self._make_color("mid", a // 2))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # ── Layer 2: Vibrant halo ring ──
        halo_r = base_r + 30
        halo_width = 12 + math.sin(self._t * 1.2) * 4
        halo_alpha = 40 + int(math.sin(self._t * 0.8) * 15)
        halo_pen = QPen(self._make_color("accent", halo_alpha), halo_width)
        halo_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(halo_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), halo_r, halo_r)

        # ── Layer 3: Build morphed orb path ──
        path = QPainterPath()
        num_pts = 128
        morph = 2.5 + self._amplitude * 16.0
        if self._state == self.SLEEPING:
            morph = 1.2 + math.sin(self._t * 0.4) * 0.8

        points = []
        for i in range(num_pts):
            angle = (i / num_pts) * math.tau
            noise = 0.0
            for k in range(8):
                freq = (k + 2) * 0.7
                noise += math.sin(angle * freq + self._t * (0.5 + k * 0.25) + self._phase_offsets[k]) / (k + 1.8)

            r = base_r + noise * morph

            # Breathing pulse
            b_speed = {"sleeping": 0.5, "listening": 0.9, "processing": 1.8, "speaking": 1.2}.get(self._state, 0.8)
            b_amp = {"sleeping": 3.0, "listening": 5.0, "processing": 2.5, "speaking": 7.0 + self._amplitude * 12.0}.get(self._state, 3.0)
            r += math.sin(self._t * b_speed) * b_amp

            points.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))

        # Smooth cubic bezier path
        if points:
            path.moveTo(points[0])
            n = len(points)
            for i in range(n):
                p0 = points[i]
                p1 = points[(i + 1) % n]
                p2 = points[(i + 2) % n]
                pm = points[(i - 1) % n]
                ctrl1 = QPointF(p0.x() + (p1.x() - pm.x()) / 4, p0.y() + (p1.y() - pm.y()) / 4)
                ctrl2 = QPointF(p1.x() - (p2.x() - p0.x()) / 4, p1.y() - (p2.y() - p0.y()) / 4)
                path.cubicTo(ctrl1, ctrl2, p1)
            path.closeSubpath()

        # ── Layer 4: Multi-stop radial gradient fill ──
        light_x = cx + math.sin(self._t * 0.3) * base_r * 0.15
        light_y = cy - base_r * 0.25 + math.cos(self._t * 0.2) * base_r * 0.08
        fill_grad = QRadialGradient(QPointF(light_x, light_y), base_r * 1.6)
        alpha_main = 240 if self._state != self.SLEEPING else 180
        fill_grad.setColorAt(0.0, self._make_color("inner", alpha_main))
        fill_grad.setColorAt(0.35, self._make_color("core", alpha_main))
        fill_grad.setColorAt(0.7, self._make_color("mid", int(alpha_main * 0.8)))
        fill_grad.setColorAt(1.0, self._make_color("glow", int(alpha_main * 0.4)))

        painter.setBrush(QBrush(fill_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # ── Layer 5: Bright specular highlight ──
        spec_r = base_r * 0.38
        sx = cx - base_r * 0.16 + math.sin(self._t * 0.4) * 3
        sy = cy - base_r * 0.2 + math.cos(self._t * 0.3) * 2
        spec_alpha = 55 + int(self._amplitude * 35)
        spec = QRadialGradient(QPointF(sx, sy), spec_r)
        spec.setColorAt(0.0, QColor(255, 255, 255, spec_alpha))
        spec.setColorAt(0.5, QColor(255, 255, 255, spec_alpha // 3))
        spec.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(spec))
        painter.drawEllipse(QPointF(sx, sy), spec_r, spec_r)

        # ── Layer 6: Secondary color bloom (bottom-right) ──
        bloom_r = base_r * 0.5
        bx = cx + base_r * 0.2
        by = cy + base_r * 0.15
        bloom = QRadialGradient(QPointF(bx, by), bloom_r)
        bloom.setColorAt(0.0, self._make_color("accent", 40))
        bloom.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(bloom))
        painter.drawEllipse(QPointF(bx, by), bloom_r, bloom_r)

        # ── Layer 7: Rotating accent arc (processing) ──
        if self._state == self.PROCESSING:
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._t * 90 % 360)
            arc_r = base_r + 22
            arc_pen = QPen(self._make_color("ring", 100), 2.5)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2), 0, 100 * 16)
            # Second arc opposite side
            painter.rotate(180)
            painter.drawArc(QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2), 0, 60 * 16)
            painter.restore()

        # ── Layer 8: Subtle conical shimmer overlay ──
        shimmer_r = base_r * 0.85
        shimmer = QConicalGradient(QPointF(cx, cy), (self._t * 30) % 360)
        shimmer.setColorAt(0.0, QColor(255, 255, 255, 0))
        shimmer.setColorAt(0.25, QColor(255, 255, 255, 8))
        shimmer.setColorAt(0.5, QColor(255, 255, 255, 0))
        shimmer.setColorAt(0.75, QColor(255, 255, 255, 6))
        shimmer.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(shimmer))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), shimmer_r, shimmer_r)

        painter.end()
