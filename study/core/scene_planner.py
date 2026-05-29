"""
Scene Planner — Converts a LessonPlan's subconcepts into renderable ScenePlan DSL.
The AI decides WHAT to visualize; the renderer decides HOW to draw it.

Designed to produce educational animations in the style of 3Blue1Brown:
  - ONE major idea per scene
  - Progressive visual reveals
  - Synchronized narration
  - Meaningful color coding
  - Focus-guiding animations
"""

from typing import Optional

from study.models.lesson_schema import SubConcept, LessonPlan
from study.models.scene_schema import ScenePlan
from study.core.ai_router import generate_json
from study.utils.cache import cache_json, load_cached_json
from study.utils.logger import get_logger

log = get_logger("scene_planner")

SCENE_SYSTEM_PROMPT = """You are a world-class educational animation director — think 3Blue1Brown meets Physics Wallah.

Your job is to create animation scene plans that TEACH, not just look pretty.

═══════════════════════════════════════════
CRITICAL RULE: EVERY ANIMATION MUST ANSWER
═══════════════════════════════════════════

"What understanding should the student gain from THIS scene?"

NOT: "What motion looks cool?"

═══════════════════════════════════════════
ANIMATION STYLE RULES
═══════════════════════════════════════════

1. ONE major idea per scene. Don't cram everything together.
2. Build visuals PROGRESSIVELY — start simple, add complexity step by step.
3. Fade in objects ONE AT A TIME as the narration mentions them.
4. Use consistent, meaningful colors:
   - Blue (#3B82F6) = primary concept / main object
   - Red (#EF4444) = forces / important highlights / warnings
   - Green (#22C55E) = positive quantities / correct answers
   - Yellow (#EAB308) = labels / annotations / attention
   - Purple (#A855F7) = secondary concepts / derived quantities
   - Cyan (#06B6D4) = velocity / flow / motion
   - Gray (#9CA3AF) = background elements / surfaces
5. Pause (wait animation) after revealing important insights.
6. Use arrows to show direction, force, flow, cause-effect.
7. Use text labels to name every important object.
8. Use LaTeX for equations — reveal them AFTER the visual intuition.
9. Show BEFORE and AFTER states for transformations.
10. Keep total scene to 15-30 seconds. Quality over quantity.

═══════════════════════════════════════════
SYNC RULES (The "Action" System)
═══════════════════════════════════════════

- You must structure the scene as a sequence of "actions".
- Each action has a `narration` (what the tutor says) and a list of `animations` (what happens while they say it).
- First write the explanation (narration), then add visual animations to match it perfectly.
- If a step requires the student to just look, use an empty narration "" and a "wait" animation.
- Keep the narration conversational and engaging.

═══════════════════════════════════════════
OBJECT PLACEMENT RULES
═══════════════════════════════════════════

- Center the main concept object at (0, 0).
- Labels above objects (y + 1.5).
- Equations at the bottom of the screen (y = -2.5).
- Arrows between objects to show relationships.
- Don't place objects off-screen (keep x in [-5, 5], y in [-3, 3]).

═══════════════════════════════════════════
AVAILABLE OBJECT TYPES
═══════════════════════════════════════════
vector, circle, rectangle, line, text, latex, axes, graph_curve, particle, spring, block, arrow, wave, field_line, coil, magnet, pendulum, surface, dot, arc, brace, group

═══════════════════════════════════════════
AVAILABLE ANIMATION TYPES
═══════════════════════════════════════════
fade_in, fade_out, move_to, shift, rotate, scale, grow, write, transform, indicate, flash, wiggle, trace_path, create, uncreate, wait

═══════════════════════════════════════════
OUTPUT FORMAT — Return ONLY valid JSON:
═══════════════════════════════════════════
{
  "scene_id": "unique_snake_case_id",
  "title": "What the student will learn",
  "scene_type": "animation",
  "background_color": "#1F2937",
  "duration_seconds": 20.0,
  "objects": [
    {
      "id": "obj_id",
      "type": "block",
      "position": {"x": 0, "y": 0, "z": 0},
      "label": "Descriptive Label",
      "color": "#3B82F6",
      "size": 1.0,
      "opacity": 1.0,
      "params": {"width": 1.5, "height": 1.0}
    }
  ],
  "actions": [
    {
      "narration": "Let's start by imagining...",
      "animations": [
        {"target_id": "obj_id", "type": "fade_in", "duration": 1.0, "params": {}}
      ]
    },
    {
      "narration": "Notice how this block shifts over here.",
      "animations": [
        {"target_id": "obj_id", "type": "shift", "duration": 2.0, "params": {"dx": 3, "dy": 0}}
      ]
    }
  ],
  "subconcept_name": "Name of subconcept",
  "difficulty": "school"
}"""


class ScenePlanner:
    """Converts lesson subconcepts into renderable scene DSL."""

    def plan_scene(self, subconcept: SubConcept, topic: str, scene_index: int = 0) -> Optional[ScenePlan]:
        """Generate a ScenePlan for a single subconcept."""
        log.info(f"Planning scene for subconcept: '{subconcept.name}'")

        # Check cache
        cache_key = f"scene_{topic}_{subconcept.name}".lower().replace(" ", "_")
        cached = load_cached_json("scene", cache_key)
        if cached:
            try:
                scene = ScenePlan(**cached)
                log.info(f"Loaded scene from cache: {scene.scene_id}")
                return scene
            except Exception:
                log.warning("Cached scene invalid, regenerating.")

        # Build a rich prompt from the 8-step subconcept data
        visuals_hint = ", ".join(subconcept.required_visuals) if subconcept.required_visuals else "use your best judgment"
        equations_hint = ", ".join(subconcept.key_equations) if subconcept.key_equations else "none"

        # Use the new visual_description field if available
        visual_direction = subconcept.visual_description if subconcept.visual_description else "Create visuals that teach the core concept step by step."

        # Use the hook and intuition to guide narration
        hook_text = subconcept.hook if subconcept.hook else ""
        intuition_text = subconcept.intuition if subconcept.intuition else ""
        formal_def_text = subconcept.formal_definition if subconcept.formal_definition else ""

        user_prompt = f"""Create an educational animation scene for this subconcept:

═══════════════════════════════════════════
CONTEXT
═══════════════════════════════════════════
TOPIC: {topic}
SUBCONCEPT: {subconcept.name}
DIFFICULTY: {subconcept.difficulty.value}
TARGET DURATION: {min(subconcept.duration_seconds, 30)} seconds

═══════════════════════════════════════════
WHAT TO TEACH (use this to guide the animation)
═══════════════════════════════════════════
HOOK: {hook_text or subconcept.explanation[:100]}
INTUITION: {intuition_text or subconcept.explanation}
FORMAL DEFINITION: {formal_def_text}

═══════════════════════════════════════════
ANIMATION DIRECTION
═══════════════════════════════════════════
{visual_direction}

SUGGESTED VISUAL ELEMENTS: {visuals_hint}
KEY EQUATIONS TO SHOW: {equations_hint}

═══════════════════════════════════════════
REQUIREMENTS
═══════════════════════════════════════════
1. Start the narration with the HOOK to spark curiosity.
2. Then visually BUILD the intuition step by step.
3. Fade in objects ONE at a time, narrating each as it appears.
4. Add a WAIT animation (1-2 sec) after key insights so the student can absorb.
5. If there's a formula, show it as a LaTeX object AFTER the visual intuition is clear.
6. Use arrows to show cause → effect relationships.
7. Use 6-10 narration cues, each 1-2 sentences, spaced 2-3 seconds apart.
8. Keep total scene under 30 seconds.
9. Make the narration sound like an excited tutor, not a textbook."""

        raw = generate_json(SCENE_SYSTEM_PROMPT, user_prompt, max_tokens=8000)

        if not raw:
            log.error(f"AI returned no valid JSON for scene: {subconcept.name}")
            return None

        # Sanitize
        raw = self._sanitize_scene(raw, topic, scene_index)

        try:
            scene = ScenePlan(**raw)
            log.info(f"Scene planned: {scene.scene_id} ({len(scene.objects)} objects, {len(scene.actions)} actions)")
            cache_json("scene", cache_key, scene.model_dump())
            return scene

        except Exception as e:
            log.error(f"Scene validation failed: {e}")
            return None

    @staticmethod
    def _sanitize_scene(raw: dict, topic: str, scene_index: int) -> dict:
        """Fix common AI issues in scene JSON."""
        from study.models.scene_schema import ObjectType, AnimationType

        VALID_OBJ_TYPES = {t.value for t in ObjectType}
        VALID_ANIM_TYPES = {t.value for t in AnimationType}

        # Ensure scene_id
        if "scene_id" not in raw or not raw["scene_id"]:
            raw["scene_id"] = f"{topic.lower().replace(' ', '_')}_{scene_index:03d}"

        # Clamp duration
        if "duration_seconds" in raw:
            try:
                raw["duration_seconds"] = max(1.0, min(120.0, float(raw["duration_seconds"])))
            except (ValueError, TypeError):
                raw["duration_seconds"] = 20.0

        # Fix object types
        for obj in raw.get("objects", []):
            if obj.get("type") not in VALID_OBJ_TYPES:
                obj["type"] = "dot"  # safe fallback
            # Clamp positions
            pos = obj.get("position", {})
            if isinstance(pos, dict):
                pos["x"] = max(-6, min(6, pos.get("x", 0)))
                pos["y"] = max(-4, min(4, pos.get("y", 0)))

        # Sanitize actions
        actions = raw.get("actions", [])
        if not actions:
            # Fallback action
            actions = [{
                "narration": raw.get("title", "Let's explore this concept."),
                "animations": [{"target_id": "none", "type": "wait", "duration": 2.0}]
            }]
            raw["actions"] = actions

        for action in actions:
            if not isinstance(action.get("narration"), str):
                action["narration"] = ""
            
            # Fix animation types inside actions
            for anim in action.get("animations", []):
                if anim.get("type") not in VALID_ANIM_TYPES:
                    anim["type"] = "fade_in"
                # Clamp duration
                try:
                    anim["duration"] = max(0.1, min(10.0, float(anim.get("duration", 1.0))))
                except (ValueError, TypeError):
                    anim["duration"] = 1.0

        return raw

    def plan_all_scenes(self, lesson: LessonPlan) -> list[ScenePlan]:
        """Generate ScenePlans for every subconcept in a lesson."""
        scenes = []
        for i, subconcept in enumerate(lesson.subconcepts):
            scene = self.plan_scene(subconcept, lesson.topic, scene_index=i)
            if scene:
                scenes.append(scene)
            else:
                log.warning(f"Skipping scene for: {subconcept.name}")
        log.info(f"Planned {len(scenes)}/{len(lesson.subconcepts)} scenes for '{lesson.topic}'")
        return scenes
