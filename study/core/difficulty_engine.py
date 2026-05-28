"""
Difficulty Engine — Manages progressive difficulty levels and adaptation.
Tracks student understanding and adjusts the teaching depth dynamically.
"""

from study.models.lesson_schema import DifficultyLevel
from study.utils.logger import get_logger

log = get_logger("difficulty")

# Ordered progression
DIFFICULTY_ORDER = [
    DifficultyLevel.TODDLER,
    DifficultyLevel.SCHOOL,
    DifficultyLevel.JEE_MAIN,
    DifficultyLevel.JEE_ADVANCED,
    DifficultyLevel.OLYMPIAD,
]


class DifficultyEngine:
    """Tracks and adapts the teaching difficulty level."""

    def __init__(self, start_level: DifficultyLevel = DifficultyLevel.SCHOOL):
        self.current_level: DifficultyLevel = start_level
        self.history: list[DifficultyLevel] = [start_level]
        self.confusion_count: int = 0
        self.correct_streak: int = 0

    @property
    def current_index(self) -> int:
        return DIFFICULTY_ORDER.index(self.current_level)

    def increase_difficulty(self) -> DifficultyLevel:
        """Move up one level if possible."""
        idx = self.current_index
        if idx < len(DIFFICULTY_ORDER) - 1:
            self.current_level = DIFFICULTY_ORDER[idx + 1]
            self.history.append(self.current_level)
            log.info(f"Difficulty ↑ → {self.current_level.value}")
        return self.current_level

    def decrease_difficulty(self) -> DifficultyLevel:
        """Move down one level if possible."""
        idx = self.current_index
        if idx > 0:
            self.current_level = DIFFICULTY_ORDER[idx - 1]
            self.history.append(self.current_level)
            log.info(f"Difficulty ↓ → {self.current_level.value}")
        return self.current_level

    def set_level(self, level: DifficultyLevel) -> None:
        """Directly set the difficulty level."""
        self.current_level = level
        self.history.append(level)
        log.info(f"Difficulty set → {level.value}")

    def record_quiz_result(self, correct: bool) -> DifficultyLevel:
        """Adapt difficulty based on quiz performance."""
        if correct:
            self.correct_streak += 1
            self.confusion_count = max(0, self.confusion_count - 1)
            if self.correct_streak >= 2:
                self.correct_streak = 0
                return self.increase_difficulty()
        else:
            self.correct_streak = 0
            self.confusion_count += 1
            if self.confusion_count >= 2:
                self.confusion_count = 0
                return self.decrease_difficulty()

        return self.current_level

    def record_confusion(self) -> DifficultyLevel:
        """Called when the system detects student confusion."""
        self.confusion_count += 1
        log.info(f"Confusion detected (count={self.confusion_count})")
        if self.confusion_count >= 2:
            self.confusion_count = 0
            return self.decrease_difficulty()
        return self.current_level

    def get_levels_up_to_current(self) -> list[DifficultyLevel]:
        """Get all difficulty levels from toddler up to current level."""
        idx = self.current_index
        return DIFFICULTY_ORDER[: idx + 1]

    def should_show_alternative_explanation(self) -> bool:
        """Whether to offer a different explanation style."""
        return self.confusion_count >= 1
