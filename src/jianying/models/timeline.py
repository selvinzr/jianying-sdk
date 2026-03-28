from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class StyleSpan:
    start: int
    end: int
    color: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "color": self.color,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
        }


@dataclass(slots=True)
class TimelineWord:
    text: str
    start: float
    end: float
    start_char_index: int
    end_char_index: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "start_char_index": self.start_char_index,
            "end_char_index": self.end_char_index,
        }


@dataclass(slots=True)
class TimelineLine:
    text: str
    start: float
    end: float
    words: List[TimelineWord] = field(default_factory=list)
    style_spans: List[StyleSpan] = field(default_factory=list)
    line_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "words": [word.to_dict() for word in self.words],
            "style_spans": [span.to_dict() if hasattr(span, "to_dict") else dict(span) for span in self.style_spans],
            "line_index": self.line_index,
        }


@dataclass(slots=True)
class TimelineShot:
    start: float
    end: float
    lines: List[TimelineLine] = field(default_factory=list)
    shot_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_index": self.shot_index,
            "start": self.start,
            "end": self.end,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass(slots=True)
class TimelineDocument:
    shots: List[TimelineShot] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shots": [shot.to_dict() for shot in self.shots],
            "metadata": self.metadata,
        }
