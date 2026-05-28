"""
Caching system for lessons, rendered scenes, and API responses.
Uses a local disk cache with hash-based keys.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Any

from study.utils.logger import get_logger

log = get_logger("cache")

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache" / "study"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

LESSONS_DIR = CACHE_DIR / "lessons"
SCENES_DIR = CACHE_DIR / "scenes"
RENDERS_DIR = CACHE_DIR / "renders"
API_DIR = CACHE_DIR / "api_responses"

for d in [LESSONS_DIR, SCENES_DIR, RENDERS_DIR, API_DIR]:
    d.mkdir(exist_ok=True)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def cache_json(category: str, key: str, data: dict) -> Path:
    """Store a JSON-serializable dict to disk cache."""
    dirs = {"lesson": LESSONS_DIR, "scene": SCENES_DIR, "api": API_DIR}
    target_dir = dirs.get(category, CACHE_DIR)
    file_path = target_dir / f"{_hash_key(key)}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.debug(f"Cached {category}: {key[:60]}... → {file_path.name}")
    return file_path


def load_cached_json(category: str, key: str) -> Optional[dict]:
    """Load a cached JSON file if it exists."""
    dirs = {"lesson": LESSONS_DIR, "scene": SCENES_DIR, "api": API_DIR}
    target_dir = dirs.get(category, CACHE_DIR)
    file_path = target_dir / f"{_hash_key(key)}.json"

    if file_path.exists():
        log.debug(f"Cache HIT for {category}: {key[:60]}...")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    log.debug(f"Cache MISS for {category}: {key[:60]}...")
    return None


def get_render_path(scene_id: str, extension: str = ".mp4") -> Path:
    """Get the path where a rendered scene video should be stored."""
    return RENDERS_DIR / f"{scene_id}{extension}"


def is_render_cached(scene_id: str, extension: str = ".mp4") -> bool:
    """Check if a rendered video already exists."""
    return get_render_path(scene_id, extension).exists()


def clear_cache(category: Optional[str] = None) -> int:
    """Clear cache files. Returns count of files deleted."""
    dirs = {"lesson": LESSONS_DIR, "scene": SCENES_DIR, "api": API_DIR, "render": RENDERS_DIR}
    count = 0

    targets = [dirs[category]] if category and category in dirs else dirs.values()

    for d in targets:
        for f in d.iterdir():
            if f.is_file():
                f.unlink()
                count += 1

    log.info(f"Cleared {count} cached files.")
    return count
