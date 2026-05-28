"""
ORION Study Mode — Redesigned Main Window
Matches the Desktop UI's soft gradient, minimal aesthetic.
"""

import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QProgressBar, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt6.QtGui import QFont

from study.gui.animation_player import AnimationPlayer
from study.gui.transcript_panel import TranscriptPanel
from study.gui.controls import ControlsPanel
from study.core.lesson_planner import LessonPlanner
from study.core.scene_planner import ScenePlanner
from study.core.explanation_engine import ExplanationEngine
from study.core.difficulty_engine import DifficultyEngine
from study.rendering.scene_executor import SceneExecutor
from study.voice.narration_sync import NarrationSyncEngine
from study.models.lesson_schema import LessonPlan, DifficultyLevel, ExplanationStyle
from study.models.scene_schema import ScenePlan
from study.utils.logger import get_logger

log = get_logger("main_window")


class StudyMainWindow(QMainWindow):
    """Main application window for ORION Study Mode."""

    # Thread-safe signals for UI updates from background threads
    _narration_signal = pyqtSignal(str)
    _status_signal = pyqtSignal(str)
    _progress_signal = pyqtSignal(int, int)
    _scene_ready_signal = pyqtSignal(str)  # video path
    _lesson_ready_signal = pyqtSignal()
    _voice_trigger_signal = pyqtSignal(str) # topic

    def __init__(self, tts_function=None):
        super().__init__()

        # Core engines
        self.difficulty_engine = DifficultyEngine()
        self.lesson_planner = LessonPlanner(self.difficulty_engine)
        self.scene_planner = ScenePlanner()
        self.explanation_engine = ExplanationEngine(self.difficulty_engine)
        self.scene_executor = SceneExecutor(quality="low")
        self.narration_engine = NarrationSyncEngine(tts_function=tts_function)

        # State
        self.current_lesson: Optional[LessonPlan] = None
        self.current_scenes: list[tuple[ScenePlan, Optional[Path]]] = []
        self.current_scene_index: int = 0
        self.current_style = ExplanationStyle.INTUITIVE

        # UI
        self._setup_ui()
        self._connect_signals()

        # Start background UDP listener for Voice Engine integration
        threading.Thread(target=self._listen_for_voice_commands, daemon=True).start()

    def _listen_for_voice_commands(self):
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", 5005))
            log.info("Listening on UDP 5005 for voice study commands...")
            while True:
                data, _ = sock.recvfrom(1024)
                topic = data.decode("utf-8").strip()
                if topic:
                    log.info(f"Received topic from voice engine: {topic}")
                    self._voice_trigger_signal.emit(topic)
        except Exception as e:
            log.error(f"UDP listener failed: {e}")

    def _setup_ui(self):
        self.setWindowTitle("ORION · Study Mode")
        self.setMinimumSize(1200, 700)

        # ── Global Stylesheet ──
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #06080F,
                    stop:0.5 #0B1120,
                    stop:1 #0F172A
                );
            }
            QWidget {
                font-family: 'Inter', 'SF Pro Display', system-ui, sans-serif;
            }
            QSplitter::handle {
                background: rgba(71, 85, 105, 0.2);
                width: 1px;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # ── TOP BAR ──
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)

        self.topic_label = QLabel("ORION · Study Mode")
        self.topic_label.setStyleSheet("""
            color: rgba(243, 244, 246, 0.9);
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        top_layout.addWidget(self.topic_label)

        top_layout.addStretch()

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: rgba(148, 163, 184, 0.6); font-size: 12px;")
        top_layout.addWidget(self.progress_label)

        root_layout.addWidget(top_bar)

        # ── PROGRESS BAR ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(30, 41, 59, 0.5);
                border: none;
                border-radius: 1px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6,
                    stop:1 #8B5CF6
                );
                border-radius: 1px;
            }
        """)
        root_layout.addWidget(self.progress_bar)

        # ── MAIN CONTENT (Splitter) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Transcript
        self.transcript = TranscriptPanel()
        self.transcript.setMinimumWidth(280)
        self.transcript.setMaximumWidth(400)
        splitter.addWidget(self.transcript)

        # Center: Animation player
        self.player = AnimationPlayer()
        splitter.addWidget(self.player)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        root_layout.addWidget(splitter, stretch=1)

        # ── BOTTOM CONTROLS ──
        self.controls = ControlsPanel()
        root_layout.addWidget(self.controls)

        # ── STATUS BAR ──
        self.status_label = QLabel("Ready. Waiting for voice request from ORION...")
        self.status_label.setStyleSheet("""
            color: rgba(100, 116, 139, 0.7);
            font-size: 11px;
            padding: 4px 8px;
        """)
        root_layout.addWidget(self.status_label)

    def _connect_signals(self):
        # Thread-safe signal connections
        self._narration_signal.connect(self.transcript.add_narration)
        self._status_signal.connect(self._update_status)
        self._progress_signal.connect(self._update_progress)
        self._scene_ready_signal.connect(self._on_scene_rendered)
        self._lesson_ready_signal.connect(self._on_lesson_ready)
        self._voice_trigger_signal.connect(self.start_lesson_from_voice)

        # Controls
        self.controls.play_clicked.connect(self._play_current)
        self.controls.pause_clicked.connect(self._pause_current)
        self.controls.replay_clicked.connect(self._replay_current)
        self.controls.next_clicked.connect(self._next_scene)
        self.controls.prev_clicked.connect(self._prev_scene)
        self.controls.explain_again_clicked.connect(self._explain_differently)
        self.controls.stop_clicked.connect(self._stop_all)
        self.controls.difficulty_changed.connect(self._on_difficulty_changed)

    # --------------------------------------------------
    # TOPIC SUBMISSION & LESSON PIPELINE
    # --------------------------------------------------

    def _on_topic_submitted(self, topic: str):
        if not topic:
            return

        self.transcript.clear()
        self.transcript.add_system_message(f"Starting lesson on: {topic}")
        self._status_signal.emit("🧠 AI is creating your lesson plan...")

        # Run lesson planning in background thread
        threading.Thread(
            target=self._build_lesson_pipeline,
            args=(topic,),
            daemon=True,
            name="lesson-pipeline"
        ).start()

    def _build_lesson_pipeline(self, topic: str):
        """Background thread: plan lesson → plan scenes → render → notify UI."""
        try:
            # Step 1: Create lesson plan
            self._status_signal.emit("🧠 Step 1/3: Planning lesson structure...")
            self._progress_signal.emit(10, 100)

            lesson = self.lesson_planner.create_lesson(topic)
            if not lesson:
                self._status_signal.emit("❌ Failed to create lesson plan. Try again.")
                return

            self.current_lesson = lesson
            log.info(f"Lesson: {lesson.topic} ({len(lesson.subconcepts)} subconcepts)")

            # Step 2: Plan scenes for each subconcept
            self._status_signal.emit(f"🎨 Step 2/3: Designing {len(lesson.subconcepts)} visual scenes...")
            self._progress_signal.emit(30, 100)

            scenes = self.scene_planner.plan_all_scenes(lesson)

            # Step 3: Render scenes
            self._status_signal.emit(f"🎬 Step 3/3: Rendering {len(scenes)} animations...")
            self._progress_signal.emit(50, 100)

            rendered = self.scene_executor.render_all(scenes)
            self.current_scenes = rendered
            self.current_scene_index = 0

            self._progress_signal.emit(100, 100)
            self._lesson_ready_signal.emit()

        except Exception as e:
            log.error(f"Lesson pipeline error: {e}")
            self._status_signal.emit(f"❌ Error: {e}")

    # --------------------------------------------------
    # UI SLOT HANDLERS
    # --------------------------------------------------

    @pyqtSlot()
    def _on_lesson_ready(self):
        """Called when the lesson pipeline completes."""
        if not self.current_lesson or not self.current_scenes:
            self._update_status("⚠️ Lesson created but no scenes were rendered.")
            return

        lesson = self.current_lesson
        self.topic_label.setText(f"📖 {lesson.topic}")
        self.transcript.add_system_message(f"Lesson ready! {len(lesson.subconcepts)} subconcepts to cover.")
        self.transcript.add_system_message(lesson.summary)

        # Load first scene
        self._load_scene(0)
        self.controls.set_progress(0, len(self.current_scenes))
        self._update_status(f"✅ Lesson ready. Press Play to begin!")

    @pyqtSlot(str)
    def _on_scene_rendered(self, video_path: str):
        """Load a rendered video into the player."""
        path = Path(video_path)
        if path.exists():
            self.player.load_video(path)

    @pyqtSlot(str)
    def _update_status(self, text: str):
        self.status_label.setText(text)

    @pyqtSlot(int, int)
    def _update_progress(self, value: int, maximum: int):
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    # --------------------------------------------------
    # PLAYBACK CONTROLS
    # --------------------------------------------------

    def _load_scene(self, index: int):
        """Load a specific scene by index and display rich pedagogical content."""
        if index < 0 or index >= len(self.current_scenes):
            return

        self.current_scene_index = index
        scene, video_path = self.current_scenes[index]

        # Update UI
        self.controls.set_progress(index, len(self.current_scenes))
        self.progress_label.setText(f"Scene {index + 1}/{len(self.current_scenes)}")

        if self.current_lesson and index < len(self.current_lesson.subconcepts):
            sub = self.current_lesson.subconcepts[index]
            self.transcript.add_subconcept_header(sub.name, sub.difficulty.value)

            # Display the 8-step pedagogical content
            if sub.hook:
                self.transcript.add_hook(sub.hook)

            if sub.intuition:
                self.transcript.add_intuition(sub.intuition)

            if sub.formal_definition:
                self.transcript.add_definition(sub.formal_definition)

            # Show formula breakdowns
            for fb in getattr(sub, 'formula_breakdowns', []):
                formula_text = fb.latex
                if fb.plain_english:
                    formula_text += f" — {fb.plain_english}"
                self.transcript.add_formula(formula_text)

            # Show misconceptions
            for mc in getattr(sub, 'misconceptions', []):
                self.transcript.add_misconception(mc)

        if video_path and video_path.exists():
            self.player.load_video(video_path)
            self._update_status(f"📽 Loaded: {scene.title}")
        else:
            self.player.show_placeholder(f"⚠️ Animation not available:\n{scene.title}")
            self._update_status(f"⚠️ Scene '{scene.title}' failed to render.")

    def _play_current(self):
        """Play the current scene with narration."""
        if not self.current_scenes:
            return

        scene, video_path = self.current_scenes[self.current_scene_index]

        # Play video
        if video_path:
            self.player.play()

        # Start narration, piping text to the transcript exactly when it's spoken
        self.narration_engine.play_narration(
            scene, 
            on_complete=self._on_narration_done,
            on_text=lambda text: self._narration_signal.emit(text)
        )

        self.controls.set_playing(True)
        self._update_status(f"▶ Playing: {scene.title}")

    def _stream_explanation(self, subconcept, topic):
        """Stream AI explanation to the transcript."""
        full_text = ""
        for token in self.explanation_engine.explain_stream(subconcept, topic, self.current_style):
            full_text += token
        if full_text.strip():
            self._narration_signal.emit(full_text.strip())

    def _on_narration_done(self):
        """Called when narration for a scene finishes."""
        self.controls.set_playing(False)

    def _pause_current(self):
        self.player.pause()
        self.narration_engine.pause()
        self.controls.set_playing(False)
        self._update_status("⏸ Paused")

    def _replay_current(self):
        self._stop_all()
        self._load_scene(self.current_scene_index)
        self._play_current()

    def _next_scene(self):
        if self.current_scene_index < len(self.current_scenes) - 1:
            self._stop_all()
            self._load_scene(self.current_scene_index + 1)
            self._play_current()

    def _prev_scene(self):
        if self.current_scene_index > 0:
            self._stop_all()
            self._load_scene(self.current_scene_index - 1)
            self._play_current()

    def _stop_all(self):
        self.player.stop()
        self.narration_engine.stop()
        self.controls.set_playing(False)
        self._update_status("⬛ Stopped")

    def _explain_differently(self):
        """Cycle to a different explanation style and re-explain."""
        styles = list(ExplanationStyle)
        idx = styles.index(self.current_style)
        self.current_style = styles[(idx + 1) % len(styles)]

        if self.current_lesson and self.current_scene_index < len(self.current_lesson.subconcepts):
            sub = self.current_lesson.subconcepts[self.current_scene_index]
            self.transcript.add_system_message(f"Trying {self.current_style.value} explanation style...")
            threading.Thread(
                target=self._stream_explanation,
                args=(sub, self.current_lesson.topic),
                daemon=True
            ).start()

    def _on_difficulty_changed(self, level_str: str):
        try:
            level = DifficultyLevel(level_str)
            self.difficulty_engine.set_level(level)
            self.transcript.add_system_message(f"Difficulty set to: {level.value}")
        except ValueError:
            pass

    # --------------------------------------------------
    # EXTERNAL API: Voice integration
    # --------------------------------------------------

    def start_lesson_from_voice(self, topic: str):
        """Called by ORION voice pipeline to start a lesson."""
        self.show()
        self.raise_()
        self.activateWindow()
        self._on_topic_submitted(topic)
