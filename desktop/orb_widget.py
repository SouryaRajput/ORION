"""
ORION — Iridescent Glass Orb Widget
====================================
A translucent, living glass orb with iridescent multi-color reflections,
internal liquid gradients, specular highlights, glow halos, reactive audio
rings, and floating caustic light effects.

Inspired by: Apple Intelligence orb, soap bubble optics, aurora borealis.

States:
  SLEEPING   → small gentle glow, slow breathing, muted pastel palette
  LISTENING  → orb expands, gradient shifts faster, outer rings pulse
  PROCESSING → internal swirls rotate, energy waves ripple through sphere
  SPEAKING   → orb vibrates with amplitude, color waves sync to voice
"""

import math
import random

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QRadialGradient, QColor, QPen, QPainterPath,
    QConicalGradient, QBrush, QLinearGradient
)


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp_color(c1, c2, t):
    return tuple(int(_lerp(c1[i], c2[i], t)) for i in range(3))


class OrbWidget(QWidget):
    """Premium iridescent glass orb with multi-state animations."""

    SLEEPING = "sleeping"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

    # ── Iridescent color palettes ──
    # Each state uses 6 color zones that blend together for a rainbow-glass look.
    PALETTES = {
        SLEEPING: {
            "c1": (255, 122, 217),   # pink
            "c2": (179, 136, 255),   # violet
            "c3": (165, 243, 252),   # ice cyan
            "c4": (255, 226, 154),   # warm gold
            "c5": (255, 182, 182),   # soft peach
            "c6": (200, 170, 255),   # lavender
            "glow": (200, 160, 255), # ambient glow
            "ring": (180, 140, 255), # ring color
        },
        LISTENING: {
            "c1": (110, 231, 255),   # bright cyan
            "c2": (139, 162, 255),   # periwinkle
            "c3": (255, 122, 217),   # pink
            "c4": (165, 243, 252),   # ice
            "c5": (120, 220, 255),   # sky
            "c6": (180, 200, 255),   # light blue
            "glow": (110, 200, 255), # cyan glow
            "ring": (100, 210, 255), # ring
        },
        PROCESSING: {
            "c1": (255, 226, 154),   # gold
            "c2": (255, 182, 182),   # peach
            "c3": (255, 122, 217),   # pink
            "c4": (179, 136, 255),   # violet
            "c5": (255, 200, 120),   # amber
            "c6": (255, 160, 200),   # rose
            "glow": (255, 200, 140), # warm glow
            "ring": (255, 180, 120), # ring
        },
        SPEAKING: {
            "c1": (179, 136, 255),   # violet
            "c2": (110, 231, 255),   # cyan
            "c3": (255, 122, 217),   # pink
            "c4": (165, 243, 252),   # ice
            "c5": (200, 120, 255),   # purple
            "c6": (120, 180, 255),   # blue
            "glow": (160, 140, 255), # purple glow
            "ring": (140, 170, 255), # ring
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(340, 340)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._state = self.SLEEPING
        self._t = 0.0
        self._amplitude = 0.0
        self._target_amplitude = 0.0
        self._phase_offsets = [random.uniform(0, math.tau) for _ in range(16)]

        # Particle system for floating caustics
        self._particles = []
        for _ in range(24):
            self._particles.append({
                "angle": random.uniform(0, math.tau),
                "dist": random.uniform(0.4, 1.3),
                "speed": random.uniform(0.15, 0.6),
                "size": random.uniform(1.5, 4.0),
                "alpha": random.uniform(0.15, 0.5),
                "phase": random.uniform(0, math.tau),
            })

        # Smooth color lerp storage
        self._colors = {k: v for k, v in self.PALETTES[self.SLEEPING].items()}
        self._target_colors = {k: v for k, v in self.PALETTES[self.SLEEPING].items()}

        # 60fps render loop
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
        speed = {
            "sleeping": 0.3,
            "listening": 0.65,
            "processing": 1.2,
            "speaking": 0.85,
        }.get(self._state, 0.5)
        self._t += 0.016 * speed

        # Smooth amplitude interpolation
        self._amplitude += (self._target_amplitude - self._amplitude) * 0.08

        # Smooth color transitions
        for key in self._colors:
            c = self._colors[key]
            t = self._target_colors[key]
            self._colors[key] = tuple(
                int(c[j] + (t[j] - c[j]) * 0.04) for j in range(3)
            )

        self.update()

    def _qc(self, key, alpha=255):
        """Get QColor from current interpolated palette."""
        c = self._colors[key]
        return QColor(c[0], c[1], c[2], alpha)

    def _shifted(self, key, hue_shift=0, alpha=255):
        """Get a hue-shifted variant of a palette color for iridescence."""
        c = self._colors[key]
        qc = QColor(c[0], c[1], c[2])
        h, s, l, _ = qc.getHslF()
        h = (h + hue_shift) % 1.0
        out = QColor.fromHslF(h, min(1.0, s * 1.1), min(1.0, l * 1.05))
        out.setAlpha(alpha)
        return out

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_r = min(w, h) * 0.29

        # Scale orb slightly based on state
        state_scale = {
            "sleeping": 0.92,
            "listening": 1.04,
            "processing": 0.98,
            "speaking": 1.0 + self._amplitude * 0.06,
        }.get(self._state, 1.0)
        base_r *= state_scale

        self._draw_ambient_glow(painter, cx, cy, base_r)
        self._draw_reactive_rings(painter, cx, cy, base_r)
        self._draw_orb_body(painter, cx, cy, base_r)
        self._draw_iridescent_overlay(painter, cx, cy, base_r)
        self._draw_specular_highlights(painter, cx, cy, base_r)
        self._draw_caustic_particles(painter, cx, cy, base_r)
        self._draw_processing_arcs(painter, cx, cy, base_r)

        painter.end()

    # ───────────────────────────────────────────
    # Layer 1: Deep ambient glow
    # ───────────────────────────────────────────
    def _draw_ambient_glow(self, painter, cx, cy, base_r):
        # Multiple overlapping soft glow layers — vibrant
        glow_configs = [
            ("c1", 0.0, base_r * 2.4, 65),
            ("c3", 0.3, base_r * 2.0, 50),
            ("c5", 0.6, base_r * 2.1, 40),
            ("glow", 0.0, base_r * 2.8, 70),
        ]

        for key, time_offset, radius, max_alpha in glow_configs:
            pulse = 0.6 + 0.4 * math.sin(self._t * 0.5 + time_offset * math.tau)
            alpha = int(max_alpha * pulse)

            grad = QRadialGradient(QPointF(cx, cy), radius)
            grad.setColorAt(0.0, self._qc(key, alpha))
            grad.setColorAt(0.3, self._qc(key, int(alpha * 0.7)))
            grad.setColorAt(0.6, self._qc(key, alpha // 3))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), radius, radius)

    # ───────────────────────────────────────────
    # Layer 2: Reactive audio rings
    # ───────────────────────────────────────────
    def _draw_reactive_rings(self, painter, cx, cy, base_r):
        num_rings = 4
        for i in range(num_rings):
            # Rings expand outward from orb
            ring_phase = self._t * 1.5 - i * 0.5
            ring_expansion = (math.sin(ring_phase) + 1.0) / 2.0

            if self._state == self.LISTENING:
                ring_r = base_r + 22 + i * 20 + ring_expansion * 15
                ring_alpha = int((60 - i * 10) * (0.6 + self._amplitude * 0.8))
                ring_width = 2.5 + ring_expansion * 2.0
            elif self._state == self.SPEAKING:
                ring_r = base_r + 18 + i * 16 + self._amplitude * 25
                ring_alpha = int((55 - i * 8) * (0.5 + self._amplitude))
                ring_width = 2.0 + self._amplitude * 4.0
            else:
                ring_r = base_r + 14 + i * 12
                ring_alpha = max(0, 25 - i * 5)
                ring_width = 1.5

            if ring_alpha <= 0:
                continue

            # Alternate ring colors for iridescent feel
            color_key = ["c1", "c2", "c3", "c5"][i % 4]
            pen = QPen(self._qc(color_key, ring_alpha), ring_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

    # ───────────────────────────────────────────
    # Layer 3: Morphed orb body with liquid gradient
    # ───────────────────────────────────────────
    def _draw_orb_body(self, painter, cx, cy, base_r):
        # Build morphed path
        path = QPainterPath()
        num_pts = 128
        morph = 2.0 + self._amplitude * 14.0
        if self._state == self.SLEEPING:
            morph = 0.8 + math.sin(self._t * 0.3) * 0.5
        elif self._state == self.PROCESSING:
            morph = 3.0 + math.sin(self._t * 2.0) * 2.0

        points = []
        for i in range(num_pts):
            angle = (i / num_pts) * math.tau
            noise = 0.0
            for k in range(6):
                freq = (k + 2) * 0.8
                noise += math.sin(
                    angle * freq + self._t * (0.4 + k * 0.2) + self._phase_offsets[k]
                ) / (k + 2.0)

            r = base_r + noise * morph

            # Breathing
            b_speed = {"sleeping": 0.4, "listening": 0.8, "processing": 1.5, "speaking": 1.0}.get(self._state, 0.6)
            b_amp = {"sleeping": 2.5, "listening": 4.0, "processing": 2.0, "speaking": 5.0 + self._amplitude * 10.0}.get(self._state, 2.5)
            r += math.sin(self._t * b_speed) * b_amp

            points.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))

        # Smooth cubic bezier
        if points:
            path.moveTo(points[0])
            n = len(points)
            for i in range(n):
                p0 = points[i]
                p1 = points[(i + 1) % n]
                p2 = points[(i + 2) % n]
                pm = points[(i - 1) % n]
                ctrl1 = QPointF(
                    p0.x() + (p1.x() - pm.x()) / 4,
                    p0.y() + (p1.y() - pm.y()) / 4,
                )
                ctrl2 = QPointF(
                    p1.x() - (p2.x() - p0.x()) / 4,
                    p1.y() - (p2.y() - p0.y()) / 4,
                )
                path.cubicTo(ctrl1, ctrl2, p1)
            path.closeSubpath()

        # ── Multi-color iridescent radial fill ──
        # The light source moves slowly to create the soap-bubble refraction effect
        light_angle = self._t * 0.25
        light_x = cx + math.sin(light_angle) * base_r * 0.2
        light_y = cy - base_r * 0.25 + math.cos(light_angle * 0.7) * base_r * 0.1

        fill = QRadialGradient(QPointF(light_x, light_y), base_r * 1.8)
        a = 245 if self._state != self.SLEEPING else 210

        # Cycle through colors for living iridescence — vibrant fills
        fill.setColorAt(0.0, self._qc("c1", a))
        fill.setColorAt(0.15, self._qc("c2", a))
        fill.setColorAt(0.35, self._qc("c3", int(a * 0.95)))
        fill.setColorAt(0.55, self._qc("c4", int(a * 0.9)))
        fill.setColorAt(0.75, self._qc("c5", int(a * 0.85)))
        fill.setColorAt(1.0, self._qc("c6", int(a * 0.6)))

        painter.setBrush(QBrush(fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # ── Glass inner shadow (depth) ──
        inner_shadow = QRadialGradient(QPointF(cx, cy + base_r * 0.15), base_r * 1.1)
        inner_shadow.setColorAt(0.0, QColor(0, 0, 0, 0))
        inner_shadow.setColorAt(0.6, QColor(0, 0, 0, 0))
        inner_shadow.setColorAt(0.85, QColor(20, 10, 40, 35))
        inner_shadow.setColorAt(1.0, QColor(10, 5, 25, 55))
        painter.setBrush(QBrush(inner_shadow))
        painter.drawPath(path)

    # ───────────────────────────────────────────
    # Layer 4: Iridescent conical overlay (rotating rainbow)
    # ───────────────────────────────────────────
    def _draw_iridescent_overlay(self, painter, cx, cy, base_r):
        shimmer_r = base_r * 0.92

        # Slowly rotating conical gradient with rainbow stops — vibrant
        rotation = (self._t * 20) % 360
        shimmer = QConicalGradient(QPointF(cx, cy), rotation)

        shimmer_alpha = 50 if self._state != self.SLEEPING else 30
        shimmer.setColorAt(0.0, self._qc("c1", shimmer_alpha))
        shimmer.setColorAt(0.17, self._qc("c2", shimmer_alpha + 10))
        shimmer.setColorAt(0.33, self._qc("c3", shimmer_alpha))
        shimmer.setColorAt(0.5, self._qc("c4", shimmer_alpha + 10))
        shimmer.setColorAt(0.67, self._qc("c5", shimmer_alpha))
        shimmer.setColorAt(0.83, self._qc("c6", shimmer_alpha + 10))
        shimmer.setColorAt(1.0, self._qc("c1", shimmer_alpha))

        painter.setBrush(QBrush(shimmer))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), shimmer_r, shimmer_r)

        # Second layer, counter-rotating for depth
        rotation2 = (360 - self._t * 12) % 360
        shimmer2 = QConicalGradient(QPointF(cx, cy), rotation2)
        s2a = shimmer_alpha // 2
        shimmer2.setColorAt(0.0, QColor(255, 255, 255, s2a))
        shimmer2.setColorAt(0.25, self._qc("c3", s2a + 5))
        shimmer2.setColorAt(0.5, QColor(255, 255, 255, 0))
        shimmer2.setColorAt(0.75, self._qc("c1", s2a + 5))
        shimmer2.setColorAt(1.0, QColor(255, 255, 255, s2a))

        painter.setBrush(QBrush(shimmer2))
        painter.drawEllipse(QPointF(cx, cy), shimmer_r * 0.85, shimmer_r * 0.85)

    # ───────────────────────────────────────────
    # Layer 5: Specular glass highlights
    # ───────────────────────────────────────────
    def _draw_specular_highlights(self, painter, cx, cy, base_r):
        # Primary specular (top-left, moving)
        spec_r = base_r * 0.4
        sx = cx - base_r * 0.18 + math.sin(self._t * 0.35) * 4
        sy = cy - base_r * 0.22 + math.cos(self._t * 0.25) * 3
        spec_alpha = 90 + int(self._amplitude * 40)

        spec = QRadialGradient(QPointF(sx, sy), spec_r)
        spec.setColorAt(0.0, QColor(255, 255, 255, spec_alpha))
        spec.setColorAt(0.3, QColor(255, 255, 255, spec_alpha // 2))
        spec.setColorAt(0.7, QColor(255, 255, 255, spec_alpha // 6))
        spec.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(spec))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(sx, sy), spec_r, spec_r * 0.65)

        # Secondary specular (bottom-right, subtle color tint)
        spec2_r = base_r * 0.28
        s2x = cx + base_r * 0.2 + math.cos(self._t * 0.2) * 2
        s2y = cy + base_r * 0.18 + math.sin(self._t * 0.3) * 2
        s2a = 25 + int(self._amplitude * 15)

        spec2 = QRadialGradient(QPointF(s2x, s2y), spec2_r)
        spec2.setColorAt(0.0, self._qc("c3", s2a))
        spec2.setColorAt(0.5, self._qc("c1", s2a // 3))
        spec2.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(spec2))
        painter.drawEllipse(QPointF(s2x, s2y), spec2_r, spec2_r * 0.7)

        # Tiny sharp glint
        glint_r = 3 + math.sin(self._t * 0.5) * 1
        gx = cx - base_r * 0.12
        gy = cy - base_r * 0.28
        glint = QRadialGradient(QPointF(gx, gy), glint_r * 3)
        glint.setColorAt(0.0, QColor(255, 255, 255, 80))
        glint.setColorAt(0.3, QColor(255, 255, 255, 30))
        glint.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(glint))
        painter.drawEllipse(QPointF(gx, gy), glint_r * 3, glint_r * 2)

    # ───────────────────────────────────────────
    # Layer 6: Floating caustic particles
    # ───────────────────────────────────────────
    def _draw_caustic_particles(self, painter, cx, cy, base_r):
        for p in self._particles:
            angle = p["angle"] + self._t * p["speed"]
            dist = base_r * p["dist"] + math.sin(self._t * 0.5 + p["phase"]) * 8
            px = cx + math.cos(angle) * dist
            py = cy + math.sin(angle) * dist

            # Fade particles based on distance from center
            fade = max(0.0, 1.0 - (dist / (base_r * 1.8)))
            alpha = int(p["alpha"] * 255 * fade)
            if alpha <= 0:
                continue

            size = p["size"] * (0.8 + 0.4 * math.sin(self._t + p["phase"]))

            # Use iridescent colors
            color_idx = int(p["phase"] * 3) % 6
            color_key = ["c1", "c2", "c3", "c4", "c5", "c6"][color_idx]

            grad = QRadialGradient(QPointF(px, py), size * 2)
            grad.setColorAt(0.0, self._qc(color_key, alpha))
            grad.setColorAt(0.5, self._qc(color_key, alpha // 3))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px, py), size * 2, size * 2)

    # ───────────────────────────────────────────
    # Layer 7: Processing state arcs
    # ───────────────────────────────────────────
    def _draw_processing_arcs(self, painter, cx, cy, base_r):
        if self._state != self.PROCESSING:
            return

        painter.save()
        painter.translate(cx, cy)

        for i in range(3):
            painter.save()
            speed = 60 + i * 30
            painter.rotate((self._t * speed + i * 120) % 360)

            arc_r = base_r + 18 + i * 8
            alpha = 70 - i * 15
            width = 2.5 - i * 0.5

            color_key = ["c1", "c4", "c3"][i]
            pen = QPen(self._qc(color_key, alpha), width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            span = (90 - i * 15) * 16
            painter.drawArc(
                QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2),
                0, span,
            )
            painter.restore()

        painter.restore()
