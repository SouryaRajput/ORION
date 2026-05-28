"""
Lesson Planner — Uses AI to generate structured lesson plans from a topic.
Outputs a validated LessonPlan pydantic model.

Follows the 8-Step Pedagogical Structure:
  1. Hook / Curiosity
  2. Ultra Simple Intuition
  3. Visual Understanding
  4. Formal Definition
  5. Formula Introduction
  6. Multiple Examples
  7. Advanced Intuition
  8. JEE Advanced Level Understanding
"""

from typing import Optional

from study.models.lesson_schema import LessonPlan, DifficultyLevel, ExplanationStyle
from study.core.ai_router import generate_json
from study.core.difficulty_engine import DifficultyEngine
from study.utils.cache import cache_json, load_cached_json
from study.utils.logger import get_logger

log = get_logger("lesson_planner")

LESSON_SYSTEM_PROMPT = """You are an elite educational curriculum designer — like a fusion of 3Blue1Brown, Richard Feynman, and the best JEE coach in India.

Your job is to create a DEEP, INTUITIVE teaching plan that makes a student say "OHHHH… now I FINALLY understand it."

═══════════════════════════════════════════
CRITICAL TEACHING PHILOSOPHY
═══════════════════════════════════════════

DO NOT immediately jump into formulas and textbook language.

FIRST: build intuition → simplify → create mental visuals → connect to real life → remove fear.
ONLY THEN: gradually introduce formulas → equations → derivations → advanced applications.

═══════════════════════════════════════════
8-STEP STRUCTURE (for EACH subconcept)
═══════════════════════════════════════════

Step 1 — HOOK: A surprising fact, practical scenario, or curiosity-sparking question.
   Example: "Why does a heavy truck feel harder to stop than a bicycle?"

Step 2 — INTUITION: Ultra-simple explanation using everyday objects (water flow, rubber bands, pushing objects). ZERO jargon. Like explaining to a curious 10-year-old.

Step 3 — VISUAL DESCRIPTION: Describe what the animation should show to teach this. Be specific about objects, their motion, arrows, labels, color-coding, and what the student should notice.

Step 4 — FORMAL DEFINITION: The proper scientific/mathematical definition. After intuition, this should feel OBVIOUS, not intimidating.

Step 5 — FORMULA BREAKDOWN: For each formula:
   - The LaTeX formula
   - What each variable means in plain English
   - WHY the formula works (physical intuition)
   - Unit interpretation

Step 6 — EXAMPLES: At least 3 examples progressing easy → moderate → advanced.

Step 7 — ADVANCED INTUITION: Deeper insights, edge cases, common misconceptions, limiting cases. "Now let's understand what's REALLY happening."

Step 8 — JEE-LEVEL INSIGHT: Connect to difficult applications, pattern recognition, problem-solving shortcuts, conceptual traps.

═══════════════════════════════════════════
TONE & STYLE
═══════════════════════════════════════════

- Sound like an excited genius friend explaining, NOT a textbook.
- Use contractions (I'm, don't, let's, it's, you'll).
- Build curiosity before revealing answers.
- Use phrases like "Now here's the beautiful part...", "Think of it this way...", "Imagine..."
- Make the student emotionally engaged, not just intellectually informed.
- Each subconcept narration should be 6-12 sentences, not 2-3.

═══════════════════════════════════════════
OUTPUT FORMAT — Return ONLY valid JSON:
═══════════════════════════════════════════
{
  "topic": "string",
  "summary": "One exciting hook sentence",
  "difficulty_progression": ["toddler", "school", "jee_main"],
  "prerequisites": ["topic1"],
  "subconcepts": [
    {
      "name": "Subconcept Name",
      "hook": "Why does X happen? Have you ever noticed...",
      "intuition": "Think of it like water flowing through a pipe...",
      "visual_description": "Show a magnet approaching a coil. As it moves closer, draw field lines increasing in density. Highlight electron movement with small blue dots drifting through the wire. Add an arrow showing current direction.",
      "formal_definition": "The formal definition states that...",
      "formula_breakdowns": [
        {
          "latex": "\\\\mathcal{E} = -\\\\frac{d\\\\Phi_B}{dt}",
          "plain_english": "The induced voltage equals the negative rate of change of magnetic flux",
          "variable_meanings": {"E": "Induced EMF (volts)", "Phi_B": "Magnetic flux (weber)", "t": "Time (seconds)"},
          "why_it_works": "The faster the flux changes, the stronger the push on electrons",
          "unit_check": "Weber/second = Volt ✓"
        }
      ],
      "examples": [
        {"title": "Easy: Flashlight dynamo", "description": "...", "difficulty": "school", "style": "real-world"},
        {"title": "Medium: Generator coil", "description": "...", "difficulty": "jee_main", "style": "mathematical"},
        {"title": "Hard: Self-inductance trap", "description": "...", "difficulty": "jee_advanced", "style": "intuitive"}
      ],
      "advanced_intuition": "Here's what most students miss...",
      "jee_level_insight": "In competitive exams, this concept often appears as...",
      "explanation": "Full narration text combining all the above into a smooth spoken explanation of 6-12 sentences.",
      "required_visuals": ["magnet_approaching_coil", "field_lines", "electron_flow", "current_arrow"],
      "key_equations": ["\\\\mathcal{E} = -\\\\frac{d\\\\Phi_B}{dt}"],
      "difficulty": "school",
      "duration_seconds": 60,
      "alternative_explanations": ["Think of it like a trampoline...", "Imagine a waterfall driving a wheel..."],
      "misconceptions": ["Students often think the magnet needs to touch the coil", "Confusing flux with field strength"]
    }
  ],
  "quiz_questions": [
    {"question": "string", "options": ["A", "B", "C", "D"], "correct_answer": "A", "explanation": "string", "difficulty": "school"}
  ],
  "estimated_duration_minutes": 8,
  "teaching_notes": "optional internal notes"
}"""


class LessonPlanner:
    """Creates structured, AI-generated lesson plans from topics."""

    def __init__(self, difficulty_engine: Optional[DifficultyEngine] = None):
        self.difficulty_engine = difficulty_engine or DifficultyEngine()

    def create_lesson(self, topic: str, target_difficulty: Optional[DifficultyLevel] = None) -> Optional[LessonPlan]:
        """
        Generate a complete lesson plan for a topic.
        Returns a validated LessonPlan or None on failure.
        """
        log.info(f"Creating lesson for: '{topic}'")

        # Check cache
        cache_key = f"lesson_{topic.lower().strip()}"
        cached = load_cached_json("lesson", cache_key)
        if cached:
            try:
                plan = LessonPlan(**cached)
                log.info(f"Loaded lesson from cache: {plan.topic}")
                return plan
            except Exception:
                log.warning("Cached lesson invalid, regenerating.")

        # Build prompt
        difficulty = target_difficulty or self.difficulty_engine.current_level
        levels = self.difficulty_engine.get_levels_up_to_current()
        level_names = [l.value for l in levels]

        user_prompt = f"""Create a complete 8-step lesson plan for the topic: "{topic}"

Target difficulty progression: {level_names}
Current student level: {difficulty.value}

IMPORTANT REQUIREMENTS:
1. Break the topic into 3-5 subconcepts, ordered from foundational to advanced.
2. For EACH subconcept, fill in ALL 8 steps (hook, intuition, visual_description, formal_definition, formula_breakdowns, examples, advanced_intuition, jee_level_insight).
3. The "explanation" field should be a FULL 6-12 sentence narration that weaves together the hook, intuition, and formal definition into a smooth spoken explanation. This is what ORION will say out loud.
4. The "visual_description" should describe EXACTLY what the animation should show — specific objects, their colors, their motion, labels, arrows. Think like a 3Blue1Brown animation director.
5. Include at least 3 examples per subconcept (easy → hard).
6. Include common misconceptions students have.
7. For physics/math, include detailed formula breakdowns with variable meanings and physical intuition.
8. Make the progression feel natural: curiosity → understanding → mastery.

Make this lesson feel like a premium educational experience, NOT a textbook dump."""

        # Call AI with higher token limit for richer content
        raw = generate_json(LESSON_SYSTEM_PROMPT, user_prompt, max_tokens=6000)

        if not raw:
            log.error("AI returned no valid JSON for lesson plan.")
            return None

        # Sanitize AI output before validation (LLMs often exceed constraints)
        raw = self._sanitize_raw_plan(raw)

        # Validate with Pydantic
        try:
            plan = LessonPlan(**raw)
            log.info(f"Lesson plan created: {plan.topic} ({len(plan.subconcepts)} subconcepts)")

            # Cache it
            cache_json("lesson", cache_key, plan.model_dump())
            return plan

        except Exception as e:
            log.error(f"Lesson plan validation failed: {e}")
            log.debug(f"Raw AI output: {raw}")
            return None

    @staticmethod
    def _sanitize_raw_plan(raw: dict) -> dict:
        """
        Fix common AI hallucinations before Pydantic validation.
        Clamps values, normalizes enums, fills missing fields.
        """
        VALID_DIFFICULTIES = {d.value for d in DifficultyLevel}
        VALID_STYLES = {s.value for s in ExplanationStyle}

        def clamp(val, lo, hi):
            try:
                return max(lo, min(hi, int(val)))
            except (ValueError, TypeError):
                return lo

        def fix_difficulty(v):
            return v if v in VALID_DIFFICULTIES else "school"

        def fix_style(v):
            return v if v in VALID_STYLES else "intuitive"

        for sub in raw.get("subconcepts", []):
            # Clamp duration (Pydantic requires 5–120)
            if "duration_seconds" in sub:
                sub["duration_seconds"] = clamp(sub["duration_seconds"], 5, 120)

            # Fix difficulty enum
            if "difficulty" in sub:
                sub["difficulty"] = fix_difficulty(sub["difficulty"])

            # Fix examples
            for ex in sub.get("examples", []):
                if "difficulty" in ex:
                    ex["difficulty"] = fix_difficulty(ex["difficulty"])
                if "style" in ex:
                    ex["style"] = fix_style(ex["style"])

            # Ensure formula_breakdowns is a list of dicts
            if "formula_breakdowns" in sub:
                fb = sub["formula_breakdowns"]
                if isinstance(fb, list):
                    for f in fb:
                        if isinstance(f, str):
                            # LLM returned a string instead of dict — wrap it
                            fb[fb.index(f)] = {"latex": f, "plain_english": "", "variable_meanings": {}, "why_it_works": "", "unit_check": ""}
                        elif isinstance(f, dict):
                            if "variable_meanings" not in f:
                                f["variable_meanings"] = {}
                else:
                    sub["formula_breakdowns"] = []

            # Ensure misconceptions is a list
            if "misconceptions" in sub and not isinstance(sub["misconceptions"], list):
                sub["misconceptions"] = [str(sub["misconceptions"])]

        for q in raw.get("quiz_questions", []):
            if "difficulty" in q:
                q["difficulty"] = fix_difficulty(q["difficulty"])

        # Clamp total duration
        if "estimated_duration_minutes" in raw:
            raw["estimated_duration_minutes"] = clamp(raw["estimated_duration_minutes"], 1, 60)

        # Fix difficulty_progression
        if "difficulty_progression" in raw:
            raw["difficulty_progression"] = [
                fix_difficulty(d) for d in raw["difficulty_progression"]
            ]

        return raw
