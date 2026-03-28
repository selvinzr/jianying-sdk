from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jianying_draft_sdk.presets.march18 import March18PresetConfig, March18StylePreset, March18SubtitleLine
from jianying_draft_sdk.models.motion import PlannedTimelineDocument, PlannedTimelineLine, PlannedTimelineShot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECT_FONTS_DIR = PROJECT_ROOT / "fonts"


@dataclass(slots=True)
class March18ProjectExporterConfig:
    template_dir: Path = Path("data/outputs/inspect_3_18")
    include_intro: bool = True
    consume_intro_source_lines: bool = True
    max_cover_chars: int = 6
    subtitle_min_font_size: float = 10.0
    subtitle_base_font_size: float = 15.0
    subtitle_line_height_px: float = 600.0
    subtitle_line_gap_px: float = 120.0
    subtitle_fit_safety: float = 0.88
    chinese_font_source_path: Path = Path("fonts/SourceHanSansSC-Regular.otf")
    latin_font_source_path: Path = Path("fonts/SF-Pro.ttf")
    chinese_font_output_name: str = "SourceHanSansJP-Normal.otf"
    latin_font_output_name: str = "latin-fallback.ttf"


class March18ProjectExporter:
    """Build an encrypted Jianying draft from the planned subtitle timeline."""

    PUNCTUATION_RE = re.compile(
        r"[\u3000\u3001\u3002\uff01\uff1f\uff1b\uff1a\uff0c\uff08\uff09\u3010\u3011\u300a\u300b"
        r"\u201c\u201d\u2018\u2019\u2026\u00b7,.!?;:()\"'<>[\]\-—]"
    )
    COVER_SPLIT_RE = re.compile(r"[\s\u3000\u3001\u3002\uff01\uff1f\uff1b\uff1a\uff0c,.!?;:]+")

    def __init__(self, config: March18ProjectExporterConfig | None = None) -> None:
        self.config = config or March18ProjectExporterConfig()

    def export(
        self,
        planned_timeline: PlannedTimelineDocument,
        output_dir: str | Path,
        *,
        audio_path: str | Path,
        draft_name: str = "human-demo",
    ) -> dict[str, Any]:
        output_root = Path(output_dir).resolve()
        intro_lines = self._intro_source_lines(self._iter_lines(planned_timeline)) if self.config.include_intro else []
        embedded_fonts = self._embed_fonts(output_root)
        preset = March18StylePreset.from_template_directory(
            self.config.template_dir,
            config=March18PresetConfig(
                chinese_font_path=embedded_fonts["chinese"],
                latin_font_path=embedded_fonts["latin"],
                subtitle_track_count=self._required_track_count(
                    planned_timeline,
                    skip_intro_lines=intro_lines if self.config.consume_intro_source_lines else [],
                ),
            ),
        )
        builder = preset.create_builder(output_root, draft_name=draft_name)

        cover_text = self._derive_cover_text(intro_lines[0].text) if intro_lines else None
        opening_text = self._derive_opening_text(intro_lines) if intro_lines else None

        if self.config.include_intro and intro_lines:
            preset.apply_intro(builder, cover_text=cover_text, opening_text=opening_text)

        subtitle_lines = self._build_subtitle_lines(
            planned_timeline.shots,
            skip_intro_lines=intro_lines if self.config.consume_intro_source_lines else [],
        )
        if subtitle_lines:
            preset.apply_subtitles(builder, subtitle_lines)

        duration_us = self._timeline_duration_us(planned_timeline)
        builder.add_audio_with_defaults(
            path=audio_path,
            duration_us=duration_us,
            start_us=0,
        )
        builder.set_duration_us(duration_us)
        return builder.save_draft(out_dir=output_root, pretty=False, ensure_ascii=False)

    def _embed_fonts(self, output_root: Path) -> dict[str, str]:
        fonts_dir = output_root / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        chinese_font_path = self._copy_font(
            self._resolve_font_source(
                preferred=self.config.chinese_font_source_path,
                fallback_candidates=[
                    Path("C:/Windows/Fonts/SourceHanSansSC-Regular.otf"),
                    Path("C:/Windows/Fonts/SourceHanSansJP-Normal.otf"),
                    Path("C:/Windows/Fonts/msyh.ttc"),
                ],
            ),
            fonts_dir / self.config.chinese_font_output_name,
        )
        latin_font_path = self._copy_font(
            self._resolve_font_source(
                preferred=self.config.latin_font_source_path,
                fallback_candidates=[
                    Path("C:/Windows/Fonts/SF-Pro.ttf"),
                    Path("C:/Windows/Fonts/SFNS.ttf"),
                    Path("C:/Windows/Fonts/arial.ttf"),
                ],
            ),
            fonts_dir / self.config.latin_font_output_name,
        )
        return {
            "chinese": chinese_font_path.as_posix(),
            "latin": latin_font_path.as_posix(),
        }

    def _resolve_font_source(
        self,
        *,
        preferred: Path,
        fallback_candidates: list[Path],
    ) -> Path:
        candidates = [preferred, *fallback_candidates]
        checked: list[Path] = []
        for candidate in candidates:
            resolved = self._resolve_candidate_path(candidate)
            if resolved in checked:
                continue
            checked.append(resolved)
            if resolved.exists():
                return resolved
        checked_text = ", ".join(str(path) for path in checked)
        raise FileNotFoundError(f"no usable font file found; checked: {checked_text}")

    def _resolve_candidate_path(self, candidate: Path) -> Path:
        candidate = Path(candidate)
        if candidate.is_absolute():
            return candidate.resolve()
        return (PROJECT_ROOT / candidate).resolve()

    def _copy_font(self, source: Path, destination: Path) -> Path:
        resolved_source = Path(source).resolve()
        if not resolved_source.exists():
            raise FileNotFoundError(f"font file not found: {resolved_source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_source, destination)
        return destination.resolve()

    def _build_subtitle_lines(
        self,
        shots: list[PlannedTimelineShot],
        *,
        skip_intro_lines: list[PlannedTimelineLine],
    ) -> list[March18SubtitleLine]:
        skip_ids = {id(item) for item in skip_intro_lines}
        results: list[March18SubtitleLine] = []
        for index, shot in enumerate(shots):
            shot_end = self._effective_shot_end(shots, index)
            shot_lines = [line for line in shot.lines if id(line) not in skip_ids and self._sanitize_text(line.text).strip()]
            shot_font_size = self._pick_shot_font_size(shot_lines)
            for line in shot.lines:
                if id(line) in skip_ids:
                    continue
                sanitized_text, index_map = self._sanitize_text_with_index_map(line.text)
                if not sanitized_text.strip():
                    continue
                highlight_range = self._remap_range(self._highlight_range(line), index_map)
                wrapped_text, visual_line_count, wrapped_highlight_range = self._layout_text(
                    sanitized_text,
                    shot_font_size,
                    highlight_range,
                )
                results.append(
                    March18SubtitleLine(
                        text=wrapped_text,
                        start_us=self._to_us(line.start),
                        duration_us=max(1, self._to_us(shot_end - line.start)),
                        words=self._words_payload(line),
                        highlight_range=wrapped_highlight_range,
                        use_primary_style=line.motion.enter_preset == "slide_bounce_left",
                        font_size_override=shot_font_size,
                        occupied_height_px=self._occupied_height_px(shot_font_size, visual_line_count),
                    )
                )
        return results

    def _intro_source_lines(self, lines: list[PlannedTimelineLine]) -> list[PlannedTimelineLine]:
        return [line for line in lines[:2] if self._sanitize_text(line.text).strip()]

    def _derive_cover_text(self, text: str) -> str:
        stripped = self._sanitize_text(text).strip()
        first_chunk = self.COVER_SPLIT_RE.split(stripped, maxsplit=1)[0]
        candidate = first_chunk or stripped
        return candidate[: self.config.max_cover_chars] or stripped[: self.config.max_cover_chars]

    def _derive_opening_text(self, lines: list[PlannedTimelineLine]) -> str:
        parts = [self._sanitize_text(line.text).strip() for line in lines]
        parts = [part for part in parts if part]
        return "\n".join(parts[:2])

    def _highlight_range(self, line: PlannedTimelineLine) -> tuple[int, int] | None:
        for span in line.style_spans:
            color = str(span.get("color") or "").lower()
            if color and color not in {"#ffffff", "white"}:
                start = int(span.get("start", 0))
                end = int(span.get("end", start))
                return (start, end)
        return None

    def _words_payload(self, line: PlannedTimelineLine) -> dict[str, list[Any]]:
        start_times: list[int] = []
        end_times: list[int] = []
        texts: list[str] = []
        for word in line.words:
            cleaned = self._sanitize_text(word.text)
            if not cleaned:
                continue
            start_times.append(self._to_ms(word.start - line.start))
            end_times.append(self._to_ms(word.end - line.start))
            texts.append(cleaned)
        return {
            "start_time": start_times,
            "end_time": end_times,
            "text": texts,
        }

    def _iter_lines(self, planned_timeline: PlannedTimelineDocument) -> list[PlannedTimelineLine]:
        return [line for shot in planned_timeline.shots for line in shot.lines]

    def _effective_shot_end(self, shots: list[PlannedTimelineShot], index: int) -> float:
        current = shots[index]
        if index + 1 < len(shots):
            return max(current.end, shots[index + 1].start)
        return current.end

    def _required_track_count(
        self,
        planned_timeline: PlannedTimelineDocument,
        *,
        skip_intro_lines: list[PlannedTimelineLine],
    ) -> int:
        skip_ids = {id(item) for item in skip_intro_lines}
        count = 1
        for shot in planned_timeline.shots:
            visible = sum(
                1
                for line in shot.lines
                if id(line) not in skip_ids and self._sanitize_text(line.text).strip()
            )
            count = max(count, visible)
        return count

    def _timeline_duration_us(self, planned_timeline: PlannedTimelineDocument) -> int:
        if not planned_timeline.shots:
            return 0
        return max(self._to_us(shot.end) for shot in planned_timeline.shots)

    def _pick_shot_font_size(self, lines: list[PlannedTimelineLine]) -> float:
        if not lines:
            return self.config.subtitle_base_font_size
        candidate = self.config.subtitle_base_font_size
        for line in lines:
            candidate = min(candidate, self._fit_font_size_for_single_line(self._sanitize_text(line.text)))
        return max(self.config.subtitle_min_font_size, round(candidate, 2))

    def _fit_font_size_for_single_line(self, text: str) -> float:
        fixed_width = self._subtitle_fixed_width()
        weight = max(1.0, self._text_visual_weight(text))
        estimated_size = (fixed_width * self.config.subtitle_fit_safety) / weight
        return min(self.config.subtitle_base_font_size, estimated_size)

    def _estimate_visual_line_count(self, text: str, font_size: float) -> int:
        fixed_width = self._subtitle_fixed_width()
        line_capacity = (fixed_width * self.config.subtitle_fit_safety) / max(font_size, 1.0)
        return max(1, int((self._text_visual_weight(text) + line_capacity - 1) // line_capacity))

    def _layout_text(
        self,
        text: str,
        font_size: float,
        highlight_range: tuple[int, int] | None,
    ) -> tuple[str, int, tuple[int, int] | None]:
        if self._estimate_visual_line_count(text, font_size) <= 1:
            return text, 1, highlight_range

        capacity = max(
            1.0,
            (self._subtitle_fixed_width() * self.config.subtitle_fit_safety) / max(font_size, 1.0),
        )
        parts = self._wrap_text_balanced(text, capacity)
        inserted_before_index = self._build_inserted_index_map(parts)

        wrapped_text = "\n".join(parts)
        if highlight_range is None:
            return wrapped_text, len(parts), None

        start, end = highlight_range
        wrapped_start = start + inserted_before_index[start]
        wrapped_end = end + inserted_before_index[end]
        return wrapped_text, len(parts), (wrapped_start, wrapped_end)

    def _occupied_height_px(self, font_size: float, visual_line_count: int) -> float:
        scale = font_size / max(self.config.subtitle_base_font_size, 1.0)
        line_count = max(1, visual_line_count)
        return (
            self.config.subtitle_line_height_px * line_count
            + self.config.subtitle_line_gap_px * max(0, line_count - 1)
        ) * scale

    def _subtitle_fixed_width(self) -> float:
        preset = March18StylePreset.from_template_directory(self.config.template_dir)
        return float(preset.primary_subtitle_material.get("fixed_width", 662.5426626205443))

    def _text_visual_weight(self, text: str) -> float:
        return sum(self._char_visual_weight(char) for char in text)

    def _sanitize_text(self, text: str) -> str:
        return self.PUNCTUATION_RE.sub("", text)

    def _sanitize_text_with_index_map(self, text: str) -> tuple[str, list[int]]:
        cleaned_chars: list[str] = []
        index_map = [0]
        for char in text:
            if not self.PUNCTUATION_RE.fullmatch(char):
                cleaned_chars.append(char)
            index_map.append(len(cleaned_chars))
        return "".join(cleaned_chars), index_map

    def _remap_range(
        self,
        source_range: tuple[int, int] | None,
        index_map: list[int],
    ) -> tuple[int, int] | None:
        if source_range is None:
            return None
        start, end = source_range
        start = max(0, min(start, len(index_map) - 1))
        end = max(start, min(end, len(index_map) - 1))
        mapped = (index_map[start], index_map[end])
        return mapped if mapped[0] < mapped[1] else None

    def _wrap_text_balanced(self, text: str, capacity: float) -> list[str]:
        if not text:
            return [text]

        total_weight = self._text_visual_weight(text)
        target_lines = max(1, int((total_weight + capacity - 1) // capacity))
        if target_lines <= 1:
            return [text]

        prefix_weights = [0.0]
        for char in text:
            prefix_weights.append(prefix_weights[-1] + self._char_visual_weight(char))

        parts: list[str] = []
        cursor = 0
        for remaining_lines in range(target_lines, 0, -1):
            if remaining_lines == 1:
                parts.append(text[cursor:])
                break
            next_index = self._choose_wrap_index(
                text=text,
                start=cursor,
                prefix_weights=prefix_weights,
                capacity=capacity,
                target_weight=(prefix_weights[-1] - prefix_weights[cursor]) / remaining_lines,
            )
            parts.append(text[cursor:next_index])
            cursor = next_index
        return parts

    def _choose_wrap_index(
        self,
        *,
        text: str,
        start: int,
        prefix_weights: list[float],
        capacity: float,
        target_weight: float,
    ) -> int:
        best_index = start + 1
        best_score = float("inf")

        for index in range(start + 1, len(text) + 1):
            current_weight = prefix_weights[index] - prefix_weights[start]
            if current_weight > capacity:
                break
            score = abs(current_weight - target_weight) + self._split_penalty(text, index)
            if score < best_score:
                best_score = score
                best_index = index

        return min(best_index, len(text))

    def _split_penalty(self, text: str, index: int) -> float:
        if index <= 0 or index >= len(text):
            return 0.0
        left = text[index - 1]
        right = text[index]
        if left.isspace() or right.isspace():
            return -0.15
        if left.isascii() and right.isascii() and left.isalnum() and right.isalnum():
            return 0.45
        return 0.0

    def _build_inserted_index_map(self, parts: list[str]) -> list[int]:
        inserted_before_index = [0]
        inserted = 0
        for part_index, part in enumerate(parts):
            for _ in part:
                inserted_before_index.append(inserted)
            if part_index < len(parts) - 1:
                inserted += 1
        return inserted_before_index

    def _char_visual_weight(self, char: str) -> float:
        if char in {" ", "\t"}:
            return 0.35
        if self.PUNCTUATION_RE.fullmatch(char):
            return 0.55
        if self._is_ascii(char):
            return 0.6
        return 1.0

    def _is_ascii(self, char: str) -> bool:
        return ord(char) < 128

    def _to_us(self, seconds: float) -> int:
        return int(round(seconds * 1_000_000))

    def _to_ms(self, seconds: float) -> int:
        return int(round(seconds * 1_000))
