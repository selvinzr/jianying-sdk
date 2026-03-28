from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from jianying.draft import JianyingDraftBuilder

AnimationSelection = Literal["first", "longest_enter", "shortest_enter"]


@dataclass(slots=True)
class StackedSubtitleLine:
    text: str
    start_us: int
    duration_us: int
    words: dict[str, Any] | None = None
    recognize_task_id: str | None = None
    font_size_override: float | None = None
    occupied_height_px: float | None = None


@dataclass(slots=True)
class StackedSubtitleComposerConfig:
    max_stack_size: int = 3
    shift_px: float = 600.0
    move_lead_us: int = 200_000
    move_tail_us: int = 200_000
    text_track_count: int = 3
    center_y: float = 0.0
    first_pair: tuple[str, str] = ("左移弹动", "向左模糊")
    next_pair: tuple[str, str] = ("随机上升", "向左模糊")
    first_pair_selection: AnimationSelection = "first"
    next_pair_selection: AnimationSelection = "first"
    fallback_enter_duration_us: int = 500_000
    first_enter_duration_us: int | None = 400_000
    next_enter_duration_us: int | None = 400_000
    out_duration_us: int | None = 300_000
    prefer_descending_track_order: bool = True


@dataclass(slots=True)
class AnimationCloneResult:
    material_id: str
    enter_name: str
    out_name: str
    enter_duration_us: int
    out_duration_us: int
    source_payload: dict[str, Any]


@dataclass(slots=True)
class ComposedSubtitleRef:
    line: StackedSubtitleLine
    material_id: str
    segment_id: str
    track_index: int
    animation: AnimationCloneResult


@dataclass(slots=True)
class _ActiveSegment:
    material_id: str
    track_index: int
    start_us: int
    end_us: int
    y_units: float = 0.0


class AnimationMaterialLibrary:
    """Resolve and clone material_animations from a template draft."""

    def __init__(self, animation_materials: list[dict[str, Any]]) -> None:
        self.animation_materials = [copy.deepcopy(item) for item in animation_materials]

    @classmethod
    def from_builder(cls, builder: JianyingDraftBuilder) -> "AnimationMaterialLibrary":
        return cls(builder.get_materials("material_animations"))

    def clone_pair_to_builder(
        self,
        builder: JianyingDraftBuilder,
        *,
        enter_name: str,
        out_name: str,
        selection: AnimationSelection = "first",
        enter_duration_us: int | None = None,
        out_duration_us: int | None = None,
    ) -> AnimationCloneResult:
        source = self._select_pair(
            enter_name=enter_name,
            out_name=out_name,
            selection=selection,
        )
        if source is None:
            raise KeyError(f"animation pair not found: in={enter_name}, out={out_name}")
        payload = copy.deepcopy(source)
        payload["id"] = str(uuid.uuid4()).upper()
        self._override_animation_duration(payload, "in", enter_duration_us)
        self._override_animation_duration(payload, "out", out_duration_us)
        material_id = builder.add_material("material_animations", payload)
        return AnimationCloneResult(
            material_id=material_id,
            enter_name=enter_name,
            out_name=out_name,
            enter_duration_us=self._animation_duration(payload, "in"),
            out_duration_us=self._animation_duration(payload, "out"),
            source_payload=payload,
        )

    def _select_pair(
        self,
        *,
        enter_name: str,
        out_name: str,
        selection: AnimationSelection,
    ) -> dict[str, Any] | None:
        matches = [
            item
            for item in self.animation_materials
            if self._pair_matches(item, enter_name=enter_name, out_name=out_name)
        ]
        if not matches:
            return None
        if selection == "first":
            return matches[0]
        reverse = selection == "longest_enter"
        return sorted(
            matches,
            key=lambda item: self._animation_duration(item, "in"),
            reverse=reverse,
        )[0]

    def _pair_matches(self, item: dict[str, Any], *, enter_name: str, out_name: str) -> bool:
        animations = item.get("animations", [])
        in_names = [anim.get("name") for anim in animations if anim.get("type") == "in"]
        out_names = [anim.get("name") for anim in animations if anim.get("type") == "out"]
        return enter_name in in_names and out_name in out_names

    def _animation_duration(self, item: dict[str, Any], animation_type: str) -> int:
        for animation in item.get("animations", []):
            if animation.get("type") != animation_type:
                continue
            return int(animation.get("duration") or 0)
        return 0

    def _override_animation_duration(
        self,
        item: dict[str, Any],
        animation_type: str,
        duration_us: int | None,
    ) -> None:
        if duration_us is None:
            return
        for animation in item.get("animations", []):
            if animation.get("type") != animation_type:
                continue
            animation["duration"] = int(duration_us)


class StackedSubtitleComposer:
    """Compose multi-line subtitles using animation materials plus position keyframes."""

    def __init__(self, config: StackedSubtitleComposerConfig | None = None) -> None:
        self.config = config or StackedSubtitleComposerConfig()

    def compose(
        self,
        builder: JianyingDraftBuilder,
        lines: list[StackedSubtitleLine],
        *,
        animation_library: AnimationMaterialLibrary,
    ) -> list[str]:
        return [
            item.material_id
            for item in self.compose_detailed(
                builder,
                lines,
                animation_library=animation_library,
            )
        ]

    def compose_detailed(
        self,
        builder: JianyingDraftBuilder,
        lines: list[StackedSubtitleLine],
        *,
        animation_library: AnimationMaterialLibrary,
    ) -> list[ComposedSubtitleRef]:
        self._ensure_text_tracks(builder, self.config.text_track_count)
        active: list[_ActiveSegment] = []
        created: list[ComposedSubtitleRef] = []
        for line in sorted(lines, key=lambda item: item.start_us):
            active = [item for item in active if item.end_us > line.start_us]
            while len(active) >= self.config.max_stack_size:
                active.pop(0)

            pair, selection = self._select_animation_config(active)
            animation = animation_library.clone_pair_to_builder(
                builder,
                enter_name=pair[0],
                out_name=pair[1],
                selection=selection,
                enter_duration_us=self._enter_duration_override(active),
                out_duration_us=self.config.out_duration_us,
            )

            self._push_existing_lines_up(
                builder,
                active_segments=active,
                next_line_start_us=line.start_us,
                next_line_enter_duration_us=animation.enter_duration_us or self.config.fallback_enter_duration_us,
                shift_units=self._shift_units(
                    builder,
                    line.occupied_height_px if line.occupied_height_px is not None else self.config.shift_px,
                ),
            )

            track_index = self._pick_track_index(active)
            ref = builder.add_subtitle(
                text=line.text,
                start_us=line.start_us,
                duration_us=line.duration_us,
                words=line.words,
                recognize_task_id=line.recognize_task_id,
                track_index=track_index,
            )
            segment = self._find_segment_by_material_id(builder, ref.material_id)
            segment.setdefault("extra_material_refs", []).append(animation.material_id)
            segment.setdefault("clip", {}).setdefault("transform", {})
            segment["clip"]["transform"]["y"] = self.config.center_y
            segment.setdefault("clip", {}).setdefault("scale", {"x": 1.0, "y": 1.0})

            active.append(
                _ActiveSegment(
                    material_id=ref.material_id,
                    track_index=track_index,
                    start_us=line.start_us,
                    end_us=line.start_us + line.duration_us,
                    y_units=0.0,
                )
            )
            created.append(
                ComposedSubtitleRef(
                    line=line,
                    material_id=ref.material_id,
                    segment_id=str(segment.get("id", "")),
                    track_index=track_index,
                    animation=animation,
                )
            )

        return created

    def ensure_text_tracks(self, builder: JianyingDraftBuilder, count: int | None = None) -> None:
        self._ensure_text_tracks(builder, count or self.config.text_track_count)

    def _select_animation_config(
        self,
        active_segments: list[_ActiveSegment],
    ) -> tuple[tuple[str, str], AnimationSelection]:
        if not active_segments:
            return self.config.first_pair, self.config.first_pair_selection
        return self.config.next_pair, self.config.next_pair_selection

    def _enter_duration_override(self, active_segments: list[_ActiveSegment]) -> int | None:
        if not active_segments:
            return self.config.first_enter_duration_us
        return self.config.next_enter_duration_us

    def _push_existing_lines_up(
        self,
        builder: JianyingDraftBuilder,
        *,
        active_segments: list[_ActiveSegment],
        next_line_start_us: int,
        next_line_enter_duration_us: int,
        shift_units: float,
    ) -> None:
        if not active_segments:
            return

        move_start = next_line_start_us - self.config.move_lead_us
        move_end = next_line_start_us + next_line_enter_duration_us - self.config.move_tail_us
        if move_end <= move_start:
            move_end = move_start + max(1, next_line_enter_duration_us)

        for item in active_segments:
            segment = self._find_segment_by_material_id(builder, item.material_id)
            start_value = item.y_units
            end_value = item.y_units + shift_units
            relative_move_start = max(0, move_start - item.start_us)
            relative_move_end = max(relative_move_start + 1, move_end - item.start_us)
            self._append_hold_and_move_keyframes(
                segment,
                move_start_us=relative_move_start,
                move_end_us=relative_move_end,
                start_y=start_value,
                end_y=end_value,
            )
            item.y_units = end_value

    def _append_hold_and_move_keyframes(
        self,
        segment: dict[str, Any],
        *,
        move_start_us: int,
        move_end_us: int,
        start_y: float,
        end_y: float,
    ) -> None:
        common_keyframes = segment.setdefault("common_keyframes", [])
        easing_span = float(max(0, min(490_000, move_end_us - move_start_us - 1)))

        self._append_property_keyframes(
            common_keyframes,
            property_type="KFTypePositionX",
            values=[
                {"time_offset": move_start_us, "value": 0.0, "curveType": "FreeCurveIn"},
                {"time_offset": move_end_us, "value": 0.0, "curveType": "FreeCurveOut"},
            ],
            easing_span=easing_span,
        )
        self._append_property_keyframes(
            common_keyframes,
            property_type="KFTypeScaleX",
            values=[
                {"time_offset": move_start_us, "value": 1.0},
                {"time_offset": move_end_us, "value": 1.0},
            ],
            easing_span=easing_span,
        )
        self._append_property_keyframes(
            common_keyframes,
            property_type="KFTypePositionY",
            values=[
                {"time_offset": move_start_us, "value": start_y, "curveType": "FreeCurveIn"},
                {"time_offset": move_end_us, "value": end_y, "curveType": "FreeCurveOut"},
            ],
            easing_span=easing_span,
        )

    def _append_property_keyframes(
        self,
        common_keyframes: list[dict[str, Any]],
        *,
        property_type: str,
        values: list[dict[str, Any]],
        easing_span: float,
    ) -> None:
        prop = self._find_property_block(common_keyframes, property_type)
        if prop is None:
            prop = {
                "id": str(uuid.uuid4()).upper(),
                "material_id": "",
                "property_type": property_type,
                "keyframe_list": [],
            }
            common_keyframes.append(prop)

        for entry in values:
            keyframe = {
                "id": str(uuid.uuid4()).upper(),
                "time_offset": int(entry["time_offset"]),
                "left_control": {"x": 0.0, "y": 0.0},
                "right_control": {"x": 0.0, "y": 0.0},
                "values": [entry["value"]],
            }
            curve_type = entry.get("curveType")
            if curve_type:
                keyframe["curveType"] = curve_type
                if curve_type == "FreeCurveIn":
                    keyframe["right_control"] = {"x": easing_span, "y": 0.0}
                if curve_type == "FreeCurveOut":
                    keyframe["left_control"] = {"x": -easing_span - 1.0, "y": 0.0}
            prop["keyframe_list"].append(keyframe)
        prop["keyframe_list"].sort(key=lambda item: item["time_offset"])

    def _find_property_block(
        self,
        common_keyframes: list[dict[str, Any]],
        property_type: str,
    ) -> dict[str, Any] | None:
        for item in common_keyframes:
            if item.get("property_type") == property_type:
                return item
        return None

    def _find_segment_by_material_id(
        self,
        builder: JianyingDraftBuilder,
        material_id: str,
    ) -> dict[str, Any]:
        for track in builder.get_tracks():
            for segment in track.get("segments", []):
                if segment.get("material_id") == material_id:
                    return segment
        raise KeyError(f"segment not found for material_id={material_id}")

    def _pick_track_index(self, active_segments: list[_ActiveSegment]) -> int:
        used = {item.track_index for item in active_segments}
        indexes = range(self.config.text_track_count - 1, -1, -1)
        if not self.config.prefer_descending_track_order:
            indexes = range(self.config.text_track_count)
        for index in indexes:
            if index not in used:
                return index
        return 0 if self.config.prefer_descending_track_order else max(0, self.config.text_track_count - 1)

    def _ensure_text_tracks(self, builder: JianyingDraftBuilder, count: int) -> None:
        tracks = builder.get_tracks()
        while len(builder.get_tracks("text")) < count:
            tracks.append(
                {
                    "id": str(uuid.uuid4()).upper(),
                    "type": "text",
                    "segments": [],
                    "flag": 1,
                    "is_default_name": True,
                }
            )

    def _shift_units(self, builder: JianyingDraftBuilder, shift_px: float) -> float:
        canvas_height = float(builder.content.get("canvas_config", {}).get("height", 1920))
        if canvas_height <= 0:
            canvas_height = 1920.0
        return shift_px / canvas_height
