"""
Manim Renderer — Translates Scene DSL into actual Manim scenes and renders them.
This is the safe bridge: the AI never writes raw Manim code.
The DSL is mapped to validated Manim primitives.
"""

import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

from study.models.scene_schema import (
    ScenePlan, SceneObject, SceneAnimation, ObjectType, AnimationType
)
from study.utils.cache import get_render_path, is_render_cached, RENDERS_DIR
from study.utils.logger import get_logger

log = get_logger("manim_renderer")


# --------------------------------------------------
# DSL → MANIM CODE GENERATOR
# --------------------------------------------------

def _obj_to_manim(obj: SceneObject) -> str:
    """Convert a SceneObject to a Manim constructor call."""
    p = obj.params
    pos = f".move_to([{obj.position.x}, {obj.position.y}, {obj.position.z}])"
    color = f'color="{obj.color}"'

    match obj.type:
        case ObjectType.BLOCK | ObjectType.RECTANGLE:
            w = p.get("width", 1.5)
            h = p.get("height", 1.0)
            code = f'Rectangle(width={w}, height={h}, {color}, fill_opacity=0.8, stroke_width=2){pos}'

        case ObjectType.CIRCLE:
            r = p.get("radius", 0.5) * obj.size
            code = f'Circle(radius={r}, {color}, fill_opacity=0.3, stroke_width=2){pos}'

        case ObjectType.ARROW | ObjectType.VECTOR:
            sx, sy = p.get("start", [obj.position.x - 1, obj.position.y])
            ex, ey = p.get("end", [obj.position.x + 1, obj.position.y])
            code = f'Arrow(start=[{sx}, {sy}, 0], end=[{ex}, {ey}, 0], {color}, buff=0, stroke_width=3)'

        case ObjectType.LINE:
            sx, sy = p.get("start", [-3, 0])
            ex, ey = p.get("end", [3, 0])
            code = f'Line(start=[{sx}, {sy}, 0], end=[{ex}, {ey}, 0], {color}, stroke_width=2)'

        case ObjectType.TEXT:
            txt = obj.label or p.get("text", "")
            fs = p.get("font_size", 32)
            code = f'Text("{txt}", font_size={fs}, {color}){pos}'

        case ObjectType.LATEX:
            eq = p.get("equation", obj.label or "x")
            eq_escaped = eq.replace("\\", "\\\\").replace('"', '\\"')
            code = f'MathTex(r"{eq_escaped}", {color}, font_size=36){pos}'

        case ObjectType.DOT | ObjectType.PARTICLE:
            r = p.get("radius", 0.12)
            code = f'Dot(point=[{obj.position.x}, {obj.position.y}, 0], radius={r}, {color})'

        case ObjectType.AXES:
            xr = p.get("x_range", [-4, 4, 1])
            yr = p.get("y_range", [-3, 3, 1])
            code = f'Axes(x_range={xr}, y_range={yr}, x_length=7, y_length=5, tips=True){pos}'

        case ObjectType.GRAPH_CURVE:
            # Requires axes to exist; use a lambda function string
            func_str = p.get("function", "lambda x: x**2")
            axes_id = p.get("axes_id", "axes")
            code = f'{axes_id}.plot({func_str}, {color}, stroke_width=3)'

        case ObjectType.WAVE:
            amp = p.get("amplitude", 1)
            freq = p.get("frequency", 2)
            code = (
                f'FunctionGraph(lambda x: {amp} * np.sin({freq} * PI * x), '
                f'x_range=[-4, 4], {color}, stroke_width=2){pos}'
            )

        case ObjectType.SPRING:
            code = f'Line(start=[-1, 0, 0], end=[1, 0, 0], {color}, stroke_width=2){pos}'

        case ObjectType.ARC:
            angle = p.get("angle", 3.14)
            r = p.get("radius", 1.0)
            code = f'Arc(radius={r}, angle={angle}, {color}){pos}'

        case ObjectType.BRACE:
            direction = p.get("direction", "DOWN")
            code = f'BraceBetweenPoints([{obj.position.x - 1}, {obj.position.y}, 0], [{obj.position.x + 1}, {obj.position.y}, 0], direction={direction}, {color})'

        case _:
            # Fallback: render as a labeled dot
            label = obj.label or obj.type.value
            code = f'Dot(point=[{obj.position.x}, {obj.position.y}, 0], {color}).scale({obj.size})'
            log.warning(f"Using fallback renderer for object type: {obj.type}")

    # Add label if present (and not already a text/latex object)
    if obj.label and obj.type not in (ObjectType.TEXT, ObjectType.LATEX):
        label_var = f"{obj.id}_label"
        line1 = f"{obj.id} = {code}"
        line2 = f'{label_var} = Text("{obj.label}", font_size=22, color="{obj.color}").next_to({obj.id}, UP, buff=0.2)'
        return line1 + "\n" + line2

    return f"{obj.id} = {code}"


def _anim_to_manim(anim: SceneAnimation) -> str:
    """Convert a SceneAnimation to a Manim play() call."""
    p = anim.params
    dur = anim.duration
    tid = anim.target_id

    match anim.type:
        case AnimationType.FADE_IN:
            return f"self.play(FadeIn({tid}), run_time={dur})"
        case AnimationType.FADE_OUT:
            return f"self.play(FadeOut({tid}), run_time={dur})"
        case AnimationType.WRITE:
            return f"self.play(Write({tid}), run_time={dur})"
        case AnimationType.CREATE:
            return f"self.play(Create({tid}), run_time={dur})"
        case AnimationType.GROW:
            return f"self.play(GrowFromCenter({tid}), run_time={dur})"
        case AnimationType.SHIFT:
            dx = p.get("dx", 0)
            dy = p.get("dy", 0)
            return f"self.play({tid}.animate.shift([{dx}, {dy}, 0]), run_time={dur})"
        case AnimationType.MOVE_TO:
            x = p.get("x", 0)
            y = p.get("y", 0)
            return f"self.play({tid}.animate.move_to([{x}, {y}, 0]), run_time={dur})"
        case AnimationType.ROTATE:
            angle = p.get("angle", 3.14159)
            return f"self.play(Rotate({tid}, angle={angle}), run_time={dur})"
        case AnimationType.SCALE:
            factor = p.get("factor", 1.5)
            return f"self.play({tid}.animate.scale({factor}), run_time={dur})"
        case AnimationType.INDICATE:
            return f"self.play(Indicate({tid}), run_time={dur})"
        case AnimationType.FLASH:
            return f"self.play(Flash({tid}), run_time={dur})"
        case AnimationType.WIGGLE:
            return f"self.play(Wiggle({tid}), run_time={dur})"
        case AnimationType.TRANSFORM:
            target = p.get("target_object", tid)
            return f"self.play(Transform({tid}, {target}), run_time={dur})"
        case AnimationType.UNCREATE:
            return f"self.play(Uncreate({tid}), run_time={dur})"
        case AnimationType.WAIT:
            return f"self.wait({dur})"
        case _:
            return f"self.wait({dur})  # Unknown animation: {anim.type}"


def generate_manim_script(scene: ScenePlan) -> str:
    """Generate a complete, runnable Manim Python script from a ScenePlan."""
    class_name = "".join(word.capitalize() for word in scene.scene_id.split("_")) + "Scene"

    # Build object creation lines
    obj_lines = []
    add_lines = []  # Lines to add objects to the scene
    for obj in scene.objects:
        obj_code = _obj_to_manim(obj)
        obj_lines.append(obj_code)
        # Don't auto-add graph curves (they need axes)
        if obj.type != ObjectType.GRAPH_CURVE:
            add_lines.append(f"self.add({obj.id})")
            if obj.label and obj.type not in (ObjectType.TEXT, ObjectType.LATEX):
                add_lines.append(f"self.add({obj.id}_label)")

    # Build animation lines
    anim_lines = [_anim_to_manim(a) for a in scene.animations]

    # Assemble the script
    script = f'''from manim import *
import numpy as np

class {class_name}(Scene):
    def construct(self):
        # Background
        self.camera.background_color = "{scene.background_color}"

        # --- CREATE OBJECTS ---
{textwrap.indent(chr(10).join(obj_lines), "        ")}

        # --- ANIMATIONS ---
{textwrap.indent(chr(10).join(anim_lines) if anim_lines else "self.wait(1)", "        ")}

        # Final hold
        self.wait(1)
'''
    return script


# --------------------------------------------------
# RENDER TO VIDEO
# --------------------------------------------------

def render_scene(scene: ScenePlan, quality: str = "low") -> Optional[Path]:
    """
    Render a ScenePlan to an MP4 video file using Manim CLI.
    Returns the path to the rendered video, or None on failure.
    """
    # Check cache
    output_path = get_render_path(scene.scene_id, ".mp4")
    if output_path.exists():
        log.info(f"Render cached: {output_path}")
        return output_path

    # Generate Manim script
    script = generate_manim_script(scene)
    class_name = "".join(word.capitalize() for word in scene.scene_id.split("_")) + "Scene"

    log.info(f"Rendering scene: {scene.scene_id} (quality={quality})")
    log.debug(f"Generated script:\n{script}")

    # Write script to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, prefix="manim_") as f:
        f.write(script)
        script_path = f.name

    # Quality flags
    quality_flags = {
        "low": "-ql",
        "medium": "-qm",
        "high": "-qh",
        "production": "-qp",
    }
    qflag = quality_flags.get(quality, "-ql")

    try:
        result = subprocess.run(
            [
                "python3", "-m", "manim", "render", qflag,
                "--format", "mp4",
                "--media_dir", str(RENDERS_DIR),
                script_path, class_name,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            log.error(f"Manim render failed:\n{result.stderr}")
            return None

        # Find the output file (Manim puts it in a nested directory)
        for mp4 in RENDERS_DIR.rglob(f"{class_name}.mp4"):
            # Move to our expected location
            mp4.rename(output_path)
            log.info(f"Render complete: {output_path}")
            return output_path

        log.error("Render succeeded but output file not found.")
        return None

    except subprocess.TimeoutExpired:
        log.error("Manim render timed out (120s).")
        return None
    except FileNotFoundError:
        log.error("Python 3 or Manim not found. Ensure 'python3 -m manim' works.")
        return None
    except Exception as e:
        log.error(f"Render error: {e}")
        return None
    finally:
        Path(script_path).unlink(missing_ok=True)
