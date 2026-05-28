"""
Scene Executor — Orchestrates the full rendering pipeline.
Takes a list of ScenePlans, renders them, and manages the output video files.
"""

import time
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from study.models.scene_schema import ScenePlan
from study.rendering.manim_renderer import render_scene, generate_manim_script
from study.utils.cache import is_render_cached, get_render_path
from study.utils.logger import get_logger

log = get_logger("scene_executor")


class SceneExecutor:
    """Manages the rendering pipeline for lesson scenes."""

    def __init__(self, quality: str = "low", max_workers: int = 2):
        self.quality = quality
        self.max_workers = max_workers
        self.rendered_paths: list[Path] = []

    def render_single(self, scene: ScenePlan) -> Optional[Path]:
        """Render a single scene and return the video path."""
        t0 = time.perf_counter()

        if is_render_cached(scene.scene_id):
            path = get_render_path(scene.scene_id)
            log.info(f"Using cached render: {scene.scene_id}")
            return path

        log.info(f"Rendering: {scene.title} ({scene.scene_id})")
        path = render_scene(scene, quality=self.quality)

        if path:
            elapsed = time.perf_counter() - t0
            log.info(f"Rendered '{scene.scene_id}' in {elapsed:.1f}s → {path}")
            self.rendered_paths.append(path)
        else:
            log.error(f"Failed to render: {scene.scene_id}")

        return path

    def render_all(self, scenes: list[ScenePlan]) -> list[tuple[ScenePlan, Optional[Path]]]:
        """Render all scenes. Returns list of (scene, video_path) tuples."""
        log.info(f"Rendering {len(scenes)} scenes (quality={self.quality})")
        t0 = time.perf_counter()

        results = []
        # Render sequentially for now (Manim can be resource-intensive)
        for scene in scenes:
            path = self.render_single(scene)
            results.append((scene, path))

        elapsed = time.perf_counter() - t0
        success = sum(1 for _, p in results if p is not None)
        log.info(f"Rendering complete: {success}/{len(scenes)} scenes in {elapsed:.1f}s")

        return results

    def get_script_preview(self, scene: ScenePlan) -> str:
        """Get the generated Manim script for debugging/preview."""
        return generate_manim_script(scene)
