from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from jianying.models.timeline import TimelineWord


LayoutSlot = Literal["center", "top", "bottom"]
LayoutAlign = Literal["left"]
EnterPreset = Literal["slide_bounce_left", "blur_left", "random_rise"]
ExitPreset = Literal["fade_out", "move_left_fade", "soft_blur_out"]
ReflowPreset = Literal["move_up", "none"]


@dataclass(slots=True)
class LineLayout:
    slot: LayoutSlot
    align: LayoutAlign = "left"
    x: Optional[float] = None
    y: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "align": self.align,
            "x": self.x,
            "y": self.y,
        }


@dataclass(slots=True)
class LineMotion:
    enter_preset: EnterPreset
    exit_preset: ExitPreset
    reflow_preset: ReflowPreset
    enter_duration: float
    exit_duration: float
    reflow_duration: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enter_preset": self.enter_preset,
            "exit_preset": self.exit_preset,
            "reflow_preset": self.reflow_preset,
            "enter_duration": self.enter_duration,
            "exit_duration": self.exit_duration,
            "reflow_duration": self.reflow_duration,
        }


@dataclass(slots=True)
class PlannedTimelineLine:
    text: str
    start: float
    end: float
    words: List[TimelineWord] = field(default_factory=list)
    style_spans: List[Dict[str, Any]] = field(default_factory=list)
    line_index: int = 0
    layout: LineLayout = field(default_factory=lambda: LineLayout(slot="center"))
    motion: LineMotion = field(
        default_factory=lambda: LineMotion(
            enter_preset="slide_bounce_left",
            exit_preset="fade_out",
            reflow_preset="none",
            enter_duration=0.35,
            exit_duration=0.25,
            reflow_duration=0.25,
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "words": [word.to_dict() for word in self.words],
            "style_spans": list(self.style_spans),
            "line_index": self.line_index,
            "layout": self.layout.to_dict(),
            "motion": self.motion.to_dict(),
        }


@dataclass(slots=True)
class PlannedTimelineShot:
    shot_index: int
    start: float
    end: float
    lines: List[PlannedTimelineLine] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_index": self.shot_index,
            "start": self.start,
            "end": self.end,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass(slots=True)
class PlannedTimelineDocument:
    shots: List[PlannedTimelineShot] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shots": [shot.to_dict() for shot in self.shots],
            "metadata": self.metadata,
        }
