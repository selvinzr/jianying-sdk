from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jianying.draft import JianyingDraftBuilder
from jianying.presets.subtitle_motion import (
    AnimationMaterialLibrary,
    ComposedSubtitleRef,
    StackedSubtitleComposer,
    StackedSubtitleComposerConfig,
    StackedSubtitleLine,
)


@dataclass(slots=True)
class March18SubtitleLine(StackedSubtitleLine):
    highlight_range: tuple[int, int] | None = None
    use_primary_style: bool | None = None


@dataclass(slots=True)
class March18PresetConfig:
    cover_text: str = "自律"
    cover_start_us: int = 0
    cover_duration_us: int = 5_766_666
    opening_text: str = "自律是人类行为学\n最大的谎言"
    opening_start_us: int = 2_866_666
    opening_duration_us: int = 2_900_000
    subtitle_shift_px: float = 600.0
    subtitle_track_count: int = 3
    chinese_font_path: str | None = None
    latin_font_path: str | None = None


class March18StylePreset:
    """Reusable preset built from the decrypted 3月18日 template draft."""

    def __init__(
        self,
        template_builder: JianyingDraftBuilder,
        *,
        config: March18PresetConfig | None = None,
    ) -> None:
        self.template_builder = template_builder
        self.config = config or March18PresetConfig()
        self.animation_library = AnimationMaterialLibrary.from_builder(template_builder)
        self.subtitle_composer = StackedSubtitleComposer(
            StackedSubtitleComposerConfig(
                max_stack_size=self.config.subtitle_track_count,
                shift_px=self.config.subtitle_shift_px,
                text_track_count=self.config.subtitle_track_count,
                move_lead_us=200_000,
                move_tail_us=200_000,
                first_pair=("左移弹动", "向左模糊"),
                next_pair=("随机上升", "向左模糊 II"),
                first_enter_duration_us=500_000,
                next_enter_duration_us=500_000,
                out_duration_us=300_000,
            )
        )

        self.cover_material = self._find_text_material_by_text("自律")
        self.opening_material = self._find_text_material_by_text("自律是人类行为学\n最大的谎言")
        self.primary_subtitle_material = self._find_text_material_by_text("那些天天让你靠意志力")
        self.secondary_subtitle_material = self._find_text_material_by_text("逆天改命的人")

        self.cover_segment = self._find_first_segment_for_material(self.cover_material["id"])
        self.opening_segment = self._find_first_segment_for_material(self.opening_material["id"])

    @classmethod
    def from_template_directory(
        cls,
        template_dir: str | Path,
        *,
        config: March18PresetConfig | None = None,
    ) -> "March18StylePreset":
        root = Path(template_dir).resolve()
        template_builder = JianyingDraftBuilder.from_template_directory(root, template_dir=root)
        return cls(template_builder, config=config)

    def create_builder(
        self,
        draft_root: str | Path,
        *,
        draft_name: str = "march18_style",
    ) -> JianyingDraftBuilder:
        canvas = self.template_builder.content.get("canvas_config", {})
        return JianyingDraftBuilder(
            draft_root,
            draft_name=draft_name,
            width=int(canvas.get("width", 1080)),
            height=int(canvas.get("height", 1920)),
            ratio=str(canvas.get("ratio", "9:16")),
            version=int(self.template_builder.content.get("version", 360000)),
            new_version=str(self.template_builder.content.get("new_version", "163.0.0")),
        )

    def apply_intro(
        self,
        builder: JianyingDraftBuilder,
        *,
        cover_text: str | None = None,
        opening_text: str | None = None,
    ) -> None:
        self.subtitle_composer.ensure_text_tracks(builder, self.config.subtitle_track_count)
        self._add_cover_text(
            builder,
            text=cover_text or self.config.cover_text,
            start_us=self.config.cover_start_us,
            duration_us=self.config.cover_duration_us,
        )
        self._add_opening_text(
            builder,
            text=opening_text or self.config.opening_text,
            start_us=self.config.opening_start_us,
            duration_us=self.config.opening_duration_us,
        )

    def apply_subtitles(
        self,
        builder: JianyingDraftBuilder,
        lines: list[March18SubtitleLine],
    ) -> list[ComposedSubtitleRef]:
        self.subtitle_composer.ensure_text_tracks(builder, self.config.subtitle_track_count)
        ordered_lines = sorted(lines, key=lambda item: item.start_us)
        details = self.subtitle_composer.compose_detailed(
            builder,
            ordered_lines,
            animation_library=self.animation_library,
        )
        top_track_index = self.config.subtitle_track_count - 1
        for detail, line in zip(details, ordered_lines):
            use_primary = line.use_primary_style
            if use_primary is None:
                use_primary = detail.track_index == top_track_index
            template_material = self.primary_subtitle_material if use_primary else self.secondary_subtitle_material
            current_material = builder.find_material(detail.material_id) or {}
            payload = self._build_text_payload(
                template_material,
                text=line.text,
                words=line.words,
                recognize_task_id=str(current_material.get("recognize_task_id", line.recognize_task_id or "")) or None,
                highlight_range=line.highlight_range if use_primary else None,
                font_size_override=line.font_size_override,
            )
            self._replace_material(builder, detail.material_id, payload)
        return details

    def build_project(
        self,
        draft_root: str | Path,
        *,
        draft_name: str,
        lines: list[March18SubtitleLine],
        cover_text: str | None = None,
        opening_text: str | None = None,
    ) -> JianyingDraftBuilder:
        builder = self.create_builder(draft_root, draft_name=draft_name)
        self.apply_intro(builder, cover_text=cover_text, opening_text=opening_text)
        self.apply_subtitles(builder, lines)
        return builder

    def _add_cover_text(
        self,
        builder: JianyingDraftBuilder,
        *,
        text: str,
        start_us: int,
        duration_us: int,
    ) -> None:
        animation = self.animation_library.clone_pair_to_builder(
            builder,
            enter_name="左移弹动",
            out_name="粒子碎落",
        )
        ref = builder.add_text(
            text=text,
            start_us=start_us,
            duration_us=duration_us,
            track_index=self.config.subtitle_track_count - 1,
        )
        payload = self._build_text_payload(self.cover_material, text=text)
        self._replace_material(builder, ref.material_id, payload)
        segment = self._find_segment_by_material_id(builder, ref.material_id)
        self._apply_segment_pose(segment, self.cover_segment)
        segment.setdefault("extra_material_refs", []).append(animation.material_id)

    def _add_opening_text(
        self,
        builder: JianyingDraftBuilder,
        *,
        text: str,
        start_us: int,
        duration_us: int,
    ) -> None:
        animation = self.animation_library.clone_pair_to_builder(
            builder,
            enter_name="复古打字机",
            out_name="粒子碎落",
        )
        ref = builder.add_text(
            text=text,
            start_us=start_us,
            duration_us=duration_us,
            track_index=max(0, self.config.subtitle_track_count - 2),
        )
        payload = self._build_text_payload(self.opening_material, text=text)
        self._replace_material(builder, ref.material_id, payload)
        segment = self._find_segment_by_material_id(builder, ref.material_id)
        self._apply_segment_pose(segment, self.opening_segment)
        segment.setdefault("extra_material_refs", []).append(animation.material_id)

    def _build_text_payload(
        self,
        template_material: dict[str, Any],
        *,
        text: str,
        words: dict[str, Any] | None = None,
        recognize_task_id: str | None = None,
        highlight_range: tuple[int, int] | None = None,
        font_size_override: float | None = None,
    ) -> dict[str, Any]:
        payload = copy.deepcopy(template_material)
        payload["id"] = str(uuid.uuid4()).upper()

        if "recognize_text" in payload:
            payload["recognize_text"] = text
        if "recognize_task_id" in payload and recognize_task_id is not None:
            payload["recognize_task_id"] = recognize_task_id
        if "words" in payload:
            payload["words"] = copy.deepcopy(words) if words is not None else {"start_time": [], "end_time": [], "text": []}
        if "current_words" in payload:
            payload["current_words"] = {}

        content_payload = json.loads(payload.get("content", "{}") or "{}")
        content_payload["text"] = text
        styles = content_payload.get("styles", [])
        content_styles = self._retime_styles(styles, len(text), highlight_range=highlight_range)
        content_styles = self._override_style_fonts(content_styles, text)
        self._override_style_font_size(content_styles, font_size_override)
        content_payload["styles"] = content_styles
        payload["content"] = json.dumps(content_payload, ensure_ascii=False)

        if "base_content" in payload and payload["base_content"]:
            base_payload = json.loads(payload.get("base_content", "{}") or "{}")
            base_payload["text"] = text
            base_styles = base_payload.get("styles", [])
            if base_styles:
                base_style = copy.deepcopy(base_styles[0])
                base_style["range"] = [0, len(text)]
                expanded_base_styles = self._override_style_fonts([base_style], text)
                self._override_style_font_size(expanded_base_styles, font_size_override)
                base_payload["styles"] = expanded_base_styles
            payload["base_content"] = json.dumps(base_payload, ensure_ascii=False)

        if font_size_override is not None:
            if "font_size" in payload:
                payload["font_size"] = float(font_size_override)
            if "fixed_width" in payload:
                payload["fixed_width"] = float(payload["fixed_width"])

        primary_font_path = self._primary_font_path(text)
        if primary_font_path:
            payload["font_path"] = primary_font_path

        if highlight_range is None:
            payload["is_rich_text"] = False
            if "text_color" in payload:
                payload["text_color"] = "#FFFFFF"
        else:
            payload["is_rich_text"] = True
            if "text_color" in payload:
                payload["text_color"] = "#fe5252"
        return payload

    def _retime_styles(
        self,
        styles: list[dict[str, Any]],
        text_length: int,
        *,
        highlight_range: tuple[int, int] | None,
    ) -> list[dict[str, Any]]:
        if not styles:
            return []
        if highlight_range is None or len(styles) < 2:
            style = copy.deepcopy(styles[0])
            style["range"] = [0, text_length]
            style.pop("useLetterColor", None)
            return [style]

        start, end = highlight_range
        start = max(0, min(start, text_length))
        end = max(start, min(end, text_length))

        base_style = copy.deepcopy(styles[0])
        highlight_style = copy.deepcopy(styles[1])
        rebuilt: list[dict[str, Any]] = []
        if start > 0:
            base_head = copy.deepcopy(base_style)
            base_head["range"] = [0, start]
            rebuilt.append(base_head)
        if end > start:
            highlight_style["range"] = [start, end]
            rebuilt.append(highlight_style)
        if end < text_length:
            base_tail = copy.deepcopy(base_style)
            base_tail["range"] = [end, text_length]
            rebuilt.append(base_tail)
        return rebuilt or [base_style]

    def _override_style_font_size(
        self,
        styles: list[dict[str, Any]],
        font_size_override: float | None,
    ) -> None:
        if font_size_override is None:
            return
        for style in styles:
            if "size" in style:
                style["size"] = float(font_size_override)

    def _override_style_fonts(
        self,
        styles: list[dict[str, Any]],
        text: str,
    ) -> list[dict[str, Any]]:
        if not styles or not text:
            return styles
        rebuilt: list[dict[str, Any]] = []
        for style in styles:
            style_range = style.get("range", [0, len(text)])
            start = max(0, min(int(style_range[0]), len(text)))
            end = max(start, min(int(style_range[1]), len(text)))
            if end <= start:
                continue
            for run_start, run_end, font_path in self._font_runs(text, start, end):
                style_copy = copy.deepcopy(style)
                style_copy["range"] = [run_start, run_end]
                self._set_style_font_path(style_copy, font_path)
                rebuilt.append(style_copy)
        return rebuilt or styles

    def _font_runs(
        self,
        text: str,
        start: int,
        end: int,
    ) -> list[tuple[int, int, str | None]]:
        runs: list[tuple[int, int, str | None]] = []
        run_start = start
        current_font = self._font_path_for_index(text, start, end, start)
        for index in range(start + 1, end):
            font_path = self._font_path_for_index(text, start, end, index)
            if font_path != current_font:
                runs.append((run_start, index, current_font))
                run_start = index
                current_font = font_path
        runs.append((run_start, end, current_font))
        return runs

    def _font_path_for_index(
        self,
        text: str,
        start: int,
        end: int,
        index: int,
    ) -> str | None:
        char = text[index]
        if not char.isspace():
            return self._font_path_for_char(char)
        for probe in range(index - 1, start - 1, -1):
            if not text[probe].isspace():
                return self._font_path_for_char(text[probe])
        for probe in range(index + 1, end):
            if not text[probe].isspace():
                return self._font_path_for_char(text[probe])
        return self.config.chinese_font_path or self.config.latin_font_path

    def _font_path_for_char(self, char: str) -> str | None:
        if self._is_latin_font_char(char):
            return self.config.latin_font_path or self.config.chinese_font_path
        return self.config.chinese_font_path or self.config.latin_font_path

    def _primary_font_path(self, text: str) -> str | None:
        for char in text:
            if char.isspace():
                continue
            return self._font_path_for_char(char)
        return self.config.chinese_font_path or self.config.latin_font_path

    def _set_style_font_path(
        self,
        style: dict[str, Any],
        font_path: str | None,
    ) -> None:
        if not font_path:
            return
        font_payload = style.get("font")
        if not isinstance(font_payload, dict):
            font_payload = {}
            style["font"] = font_payload
        font_payload["path"] = font_path

    def _is_latin_font_char(self, char: str) -> bool:
        if char == "\n":
            return False
        return char.isascii()

    def _replace_material(
        self,
        builder: JianyingDraftBuilder,
        material_id: str,
        payload: dict[str, Any],
    ) -> None:
        bucket = self._find_material_bucket(builder, material_id)
        if bucket is None:
            raise KeyError(f"material not found: {material_id}")
        payload = copy.deepcopy(payload)
        payload["id"] = material_id
        for index, material in enumerate(bucket):
            if material.get("id") == material_id:
                bucket[index] = payload
                return
        raise KeyError(f"material not found: {material_id}")

    def _find_material_bucket(
        self,
        builder: JianyingDraftBuilder,
        material_id: str,
    ) -> list[dict[str, Any]] | None:
        for bucket in builder.content.get("materials", {}).values():
            if not isinstance(bucket, list):
                continue
            for material in bucket:
                if material.get("id") == material_id:
                    return bucket
        return None

    def _find_text_material_by_text(self, text: str) -> dict[str, Any]:
        for material in self.template_builder.get_materials("texts"):
            content_payload = json.loads(material.get("content", "{}") or "{}")
            if content_payload.get("text") == text:
                return copy.deepcopy(material)
        raise KeyError(f"text material not found for text={text!r}")

    def _find_first_segment_for_material(self, material_id: str) -> dict[str, Any]:
        for track in self.template_builder.get_tracks():
            for segment in track.get("segments", []):
                if segment.get("material_id") == material_id:
                    return copy.deepcopy(segment)
        raise KeyError(f"segment not found for material_id={material_id}")

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

    def _apply_segment_pose(
        self,
        target_segment: dict[str, Any],
        source_segment: dict[str, Any],
    ) -> None:
        target_segment["clip"] = copy.deepcopy(source_segment.get("clip", {}))
