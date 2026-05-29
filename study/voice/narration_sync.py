"""
Narration Sync — Synchronizes voice narration with animation playback.
Uses the existing ORION TTS infrastructure for speech generation.
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable

from study.models.scene_schema import ScenePlan
from study.utils.logger import get_logger

log = get_logger("narration_sync")


class NarrationSyncEngine:
    """
    Manages timed narration cues synchronized with animation playback.
    Calls a TTS function at the right timestamps.
    """

    def __init__(self, tts_function: Optional[Callable[[str], None]] = None):
        """
        Args:
            tts_function: A callable that speaks text. If None, uses print fallback.
                          Expected signature: speak(text: str) -> None
        """
        self.tts_fn = tts_function or self._fallback_tts
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.is_playing: bool = False

    @staticmethod
    def _fallback_tts(text: str) -> None:
        """Fallback: print narration to console."""
        log.info(f"🗣️ {text}")

    def play_narration(self, scene: ScenePlan, on_complete: Optional[Callable] = None, on_text: Optional[Callable[[str], None]] = None) -> None:
        """Start narration for a scene in a background thread."""
        if not scene.actions:
            log.info("No narration cues for this scene.")
            if on_complete:
                on_complete()
            return

        self._stop_event.clear()
        self.is_playing = True

        def _worker():
            try:
                # The video has audio baked in! We just print the text to the UI as it plays.
                # Estimate timings roughly based on text length since we don't have exact timestamps.
                for action in scene.actions:
                    if self._stop_event.is_set():
                        break

                    text = action.narration
                    if not text:
                        continue

                    log.debug(f"Narrating to UI: {text[:50]}...")
                    if on_text:
                        on_text(text)
                    
                    # Estimate wait time based on reading speed (approx 2.5 words per sec)
                    wait_time = max(1.0, len(text.split()) / 2.5)
                    self._stop_event.wait(timeout=wait_time)

                log.info("Narration transcript complete.")
            except Exception as e:
                log.error(f"Narration error: {e}")
            finally:
                self.is_playing = False
                if on_complete and not self._stop_event.is_set():
                    on_complete()

        self._thread = threading.Thread(target=_worker, daemon=True, name="narration-sync")
        self._thread.start()

    def stop(self) -> None:
        """Stop narration immediately."""
        self._stop_event.set()
        self.is_playing = False
        log.info("Narration stopped.")

    def pause(self) -> None:
        """Pause narration (sets stop event but doesn't reset)."""
        self._stop_event.set()
        self.is_playing = False

    def wait_for_completion(self, timeout: float = 60.0) -> None:
        """Block until narration finishes."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
