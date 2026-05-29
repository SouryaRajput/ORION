"""
Scene Schema — Pydantic models for the Teaching Scene DSL.
These models define WHAT to render, not HOW to render it.
The renderer translates these into actual Manim/VPython calls.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Union
from enum import Enum


# --------------------------------------------------
# ENUMS
# --------------------------------------------------

class SceneType(str, Enum):
    """Categories of scene types the renderer supports."""
    ANIMATION = "animation"
    SIMULATION = "simulation"
    DIAGRAM = "diagram"
    GRAPH = "graph"
    EQUATION_WALKTHROUGH = "equation_walkthrough"


class ObjectType(str, Enum):
    """Primitive object types the renderer can draw."""
    VECTOR = "vector"
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    LINE = "line"
    TEXT = "text"
    LATEX = "latex"
    AXES = "axes"
    GRAPH_CURVE = "graph_curve"
    PARTICLE = "particle"
    SPRING = "spring"
    BLOCK = "block"
    ARROW = "arrow"
    WAVE = "wave"
    FIELD_LINE = "field_line"
    COIL = "coil"
    MAGNET = "magnet"
    PENDULUM = "pendulum"
    SURFACE = "surface"
    DOT = "dot"
    ARC = "arc"
    BRACE = "brace"
    GROUP = "group"


class AnimationType(str, Enum):
    """Types of animations that can be applied to objects."""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    MOVE_TO = "move_to"
    SHIFT = "shift"
    ROTATE = "rotate"
    SCALE = "scale"
    GROW = "grow"
    WRITE = "write"
    TRANSFORM = "transform"
    INDICATE = "indicate"
    FLASH = "flash"
    WIGGLE = "wiggle"
    TRACE_PATH = "trace_path"
    CREATE = "create"
    UNCREATE = "uncreate"
    WAIT = "wait"


class Color(str, Enum):
    """Standard color palette for educational visuals."""
    BLUE = "#3B82F6"
    RED = "#EF4444"
    GREEN = "#22C55E"
    YELLOW = "#EAB308"
    PURPLE = "#A855F7"
    ORANGE = "#F97316"
    CYAN = "#06B6D4"
    WHITE = "#FFFFFF"
    GRAY = "#9CA3AF"
    DARK = "#1F2937"


# --------------------------------------------------
# SCENE OBJECTS
# --------------------------------------------------

class Position(BaseModel):
    """2D or 3D position."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class SceneObject(BaseModel):
    """A single drawable object in the scene."""
    id: str = Field(..., description="Unique identifier for this object")
    type: ObjectType
    position: Position = Field(default_factory=Position)
    label: Optional[str] = Field(default=None, description="Text label to display")
    color: str = Color.BLUE
    size: float = Field(default=1.0, ge=0.1, le=10.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)

    # Type-specific parameters
    params: dict = Field(
        default_factory=dict,
        description="Type-specific parameters (e.g., start/end for vector, equation for latex)"
    )


class SceneAnimation(BaseModel):
    """A single animation step applied to one or more objects."""
    target_id: str = Field(default="none", description="ID of the object to animate (or 'none' for wait)")
    type: AnimationType
    duration: float = Field(default=1.0, ge=0.1, le=10.0)
    params: dict = Field(
        default_factory=dict,
        description="Animation parameters (e.g., destination for move_to)"
    )


class SceneAction(BaseModel):
    """A synchronized block of narration and visual animations."""
    narration: str = Field(..., description="The explanation spoken by the tutor")
    animations: list[SceneAnimation] = Field(default_factory=list, description="Animations to execute while speaking")

# --------------------------------------------------
# TOP-LEVEL SCENE
# --------------------------------------------------

class ScenePlan(BaseModel):
    """
    Complete scene definition in the Teaching DSL.
    This is the contract between the AI planner and the renderer.
    """
    scene_id: str = Field(..., description="Unique scene identifier")
    title: str = Field(..., description="Scene title for the GUI")
    scene_type: SceneType = SceneType.ANIMATION
    background_color: str = Color.DARK
    duration_seconds: float = Field(default=10.0, ge=1.0, le=120.0)

    # Scene content
    objects: list[SceneObject] = Field(default_factory=list)
    actions: list[SceneAction] = Field(default_factory=list, description="Sequential actions combining speech and visuals")

    # Metadata
    subconcept_name: str = Field(default="", description="Which subconcept this scene illustrates")
    difficulty: str = "school"

    class Config:
        json_schema_extra = {
            "example": {
                "scene_id": "newtons_first_law_01",
                "title": "Objects at Rest",
                "scene_type": "animation",
                "objects": [
                    {
                        "id": "block",
                        "type": "block",
                        "position": {"x": -3, "y": 0, "z": 0},
                        "label": "Block",
                        "color": "#3B82F6",
                        "size": 1.0,
                        "params": {"width": 1.5, "height": 1.0}
                    }
                ],
                "actions": [
                    {
                        "narration": "Look at this block sitting on a surface. Without any force, it stays perfectly still.",
                        "animations": [
                            {"target_id": "block", "type": "fade_in", "duration": 1.0}
                        ]
                    },
                    {
                        "narration": "But if we apply a push, it starts to move.",
                        "animations": [
                            {"target_id": "block", "type": "shift", "duration": 2.0, "params": {"dx": 4, "dy": 0}}
                        ]
                    }
                ]
            }
        }
