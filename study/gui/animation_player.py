"""
Animation Player Widget — Plays rendered MP4 animations in the PyQt6 GUI.
"""

from pathlib import Path
from typing import Optional

# pyrefly: ignore [missing-import]
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, pyqtSignal


class AnimationPlayer(QWidget):
    """Video player widget for Manim-rendered animations."""

    playback_finished = pyqtSignal()
    position_changed = pyqtSignal(int)  # milliseconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_path: Optional[Path] = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_widget.setMinimumSize(640, 360)
        self.video_widget.setStyleSheet("background-color: #1F2937; border-radius: 12px;")
        layout.addWidget(self.video_widget)

        # Placeholder label (shown when no video is loaded)
        self.placeholder = QLabel("🎬 Animation will appear here")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #6B7280;
                font-size: 18px;
                font-family: 'Inter', sans-serif;
                background-color: #1F2937;
                border-radius: 12px;
                padding: 40px;
            }
        """)
        layout.addWidget(self.placeholder)

        # Media player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0)  # Animations are silent; voice is separate
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # Signals
        self.player.mediaStatusChanged.connect(self._on_status_changed)
        self.player.positionChanged.connect(lambda pos: self.position_changed.emit(pos))

        # Initially show placeholder
        self.video_widget.hide()

    def load_video(self, path: Path) -> bool:
        """Load a video file for playback."""
        if not path.exists():
            return False

        self._current_path = path
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.placeholder.hide()
        self.video_widget.show()
        return True

    def play(self):
        """Start or resume playback."""
        if self._current_path:
            self.player.play()

    def pause(self):
        """Pause playback."""
        self.player.pause()

    def stop(self):
        """Stop playback and reset to beginning."""
        self.player.stop()

    def seek(self, position_ms: int):
        """Seek to a position in milliseconds."""
        self.player.setPosition(position_ms)

    def get_duration(self) -> int:
        """Get video duration in milliseconds."""
        return self.player.duration()

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.playback_finished.emit()

    def show_placeholder(self, text: str = "🎬 Animation will appear here"):
        """Show the placeholder text instead of video."""
        self.placeholder.setText(text)
        self.placeholder.show()
        self.video_widget.hide()
        self.player.stop()
