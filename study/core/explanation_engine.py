"""
Explanation Engine — Generates rich, multi-style spoken explanations.
Supports streaming for real-time voice narration.
"""

from typing import Generator, Optional

from study.models.lesson_schema import SubConcept, DifficultyLevel, ExplanationStyle
from study.core.ai_router import generate_stream, generate_text
from study.core.difficulty_engine import DifficultyEngine
from study.utils.logger import get_logger

log = get_logger("explanation")

EXPLANATION_SYSTEM_PROMPT = """You are an extraordinary AI tutor — warm, brilliant, and deeply passionate about teaching.

VOICE RULES (critical — you are SPEAKING, not writing):
- Use contractions naturally (I'm, don't, let's, you'll, it's).
- Keep sentences short. 1-2 sentences per thought.
- Sound like an excited friend explaining something cool, NOT a textbook.
- NEVER use bullet points, markdown, headers, or lists.
- NEVER say "Here's" or "Here are" followed by a list.
- Pause between ideas naturally.
- Use phrases like "Now here's the cool part...", "Think of it this way...", "Imagine..."
- Build INTUITION first. Formulas come after understanding.
- Use real-world analogies that resonate emotionally.
- If the concept is abstract, anchor it to something concrete and familiar.
- Match the difficulty level the student is at.
- Be genuinely enthusiastic. Make the student FEEL the beauty of the concept."""


class ExplanationEngine:
    """Generates rich spoken explanations for subconcepts."""

    def __init__(self, difficulty_engine: Optional[DifficultyEngine] = None):
        self.difficulty_engine = difficulty_engine or DifficultyEngine()

    def explain_stream(
        self,
        subconcept: SubConcept,
        topic: str,
        style: ExplanationStyle = ExplanationStyle.INTUITIVE,
    ) -> Generator[str, None, None]:
        """Stream an explanation for real-time voice narration."""
        log.info(f"Streaming explanation: '{subconcept.name}' ({style.value})")

        difficulty = self.difficulty_engine.current_level

        user_prompt = f"""Explain this concept as if speaking to a student:

TOPIC: {topic}
SUBCONCEPT: {subconcept.name}
CORE IDEA: {subconcept.explanation}
DIFFICULTY LEVEL: {difficulty.value}
STYLE: {style.value}
KEY EQUATIONS: {', '.join(subconcept.key_equations) if subconcept.key_equations else 'None'}

{'Use a concrete real-world ANALOGY to explain this.' if style == ExplanationStyle.ANALOGY else ''}
{'Focus on VISUAL descriptions — describe what the student should picture in their mind.' if style == ExplanationStyle.VISUAL else ''}
{'Derive the mathematics step by step, explaining each step intuitively.' if style == ExplanationStyle.MATHEMATICAL else ''}
{'Build pure INTUITION — no formulas, just deep understanding.' if style == ExplanationStyle.INTUITIVE else ''}

Keep it under 5 sentences. Be concise but deeply insightful."""

        yield from generate_stream(EXPLANATION_SYSTEM_PROMPT, user_prompt, max_tokens=300)

    def explain_full(
        self,
        subconcept: SubConcept,
        topic: str,
        style: ExplanationStyle = ExplanationStyle.INTUITIVE,
    ) -> str:
        """Get a complete explanation (non-streaming)."""
        log.info(f"Generating full explanation: '{subconcept.name}' ({style.value})")

        difficulty = self.difficulty_engine.current_level

        user_prompt = f"""Explain this concept as if speaking to a student:

TOPIC: {topic}
SUBCONCEPT: {subconcept.name}
CORE IDEA: {subconcept.explanation}
DIFFICULTY LEVEL: {difficulty.value}
STYLE: {style.value}

Keep it under 5 sentences. Be concise but deeply insightful."""

        return generate_text(EXPLANATION_SYSTEM_PROMPT, user_prompt, max_tokens=300)

    def get_alternative_explanation(self, subconcept: SubConcept, topic: str, previous_style: ExplanationStyle) -> Generator[str, None, None]:
        """Generate a different explanation style when the student is confused."""
        # Cycle through styles
        style_order = [
            ExplanationStyle.ANALOGY,
            ExplanationStyle.VISUAL,
            ExplanationStyle.INTUITIVE,
            ExplanationStyle.MATHEMATICAL,
        ]
        idx = style_order.index(previous_style) if previous_style in style_order else 0
        next_style = style_order[(idx + 1) % len(style_order)]

        log.info(f"Switching explanation style: {previous_style.value} → {next_style.value}")
        yield from self.explain_stream(subconcept, topic, style=next_style)
