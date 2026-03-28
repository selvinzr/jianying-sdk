from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jianying_draft_sdk.crypto import DraftBundle, DraftFileData, load_draft, save_draft


@dataclass
class DraftResourceRef:
    resource_type: str
    material_id: str
    extra_material_refs: list[str]


class JianyingDraftBuilder:
    """High-level builder for Jianying draft_content/meta structures."""

    def __init__(
        self,
        draft_root: str | Path,
        *,
        draft_name: str = "untitled",
        width: int = 1080,
        height: int = 1920,
        ratio: str = "9:16",
        version: int = 360000,
        new_version: str = "163.0.0",
    ) -> None:
        self.draft_root = Path(draft_root).resolve()
        self.meta = self._build_default_meta(draft_name=draft_name, new_version=new_version)
        self.content = self._build_default_content(
            width=width,
            height=height,
            ratio=ratio,
            version=version,
            new_version=new_version,
        )

    @classmethod
    def from_bundle(cls, draft: DraftBundle) -> "JianyingDraftBuilder":
        meta_file = draft.files.get("draft_meta_info.json")
        content_file = draft.files.get("draft_content.json")
        if meta_file is None or content_file is None:
            raise ValueError("draft bundle must include draft_meta_info.json and draft_content.json")
        builder = cls.__new__(cls)
        builder.draft_root = Path(draft.draft_root).resolve()
        builder.meta = copy.deepcopy(meta_file.data)
        builder.content = copy.deepcopy(content_file.data)
        return builder

    @classmethod
    def from_plaintext_files(
        cls,
        draft_root: str | Path,
        *,
        meta_path: str | Path,
        content_path: str | Path,
    ) -> "JianyingDraftBuilder":
        builder = cls.__new__(cls)
        builder.draft_root = Path(draft_root).resolve()
        builder.meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
        builder.content = json.loads(Path(content_path).read_text(encoding="utf-8"))
        return builder

    @classmethod
    def from_template_directory(
        cls,
        draft_root: str | Path,
        *,
        template_dir: str | Path,
        meta_name: str = "draft_meta_info.plain.json",
        content_name: str = "draft_content.plain.json",
    ) -> "JianyingDraftBuilder":
        template_root = Path(template_dir).resolve()
        return cls.from_plaintext_files(
            draft_root,
            meta_path=template_root / meta_name,
            content_path=template_root / content_name,
        )

    def set_draft_name(self, name: str) -> "JianyingDraftBuilder":
        self.meta["draft_name"] = name
        return self

    def set_duration_us(self, duration_us: int) -> "JianyingDraftBuilder":
        self.meta["tm_duration"] = duration_us
        self.content["duration"] = duration_us
        return self

    def get_tracks(self, track_type: str | None = None) -> list[dict[str, Any]]:
        tracks = self.content.setdefault("tracks", [])
        if track_type is None:
            return tracks
        return [track for track in tracks if track.get("type") == track_type]

    def get_materials(self, bucket_name: str) -> list[dict[str, Any]]:
        return self.ensure_material_bucket(bucket_name)

    def find_material(self, material_id: str) -> dict[str, Any] | None:
        for bucket in self.content.get("materials", {}).values():
            if not isinstance(bucket, list):
                continue
            for material in bucket:
                if material.get("id") == material_id:
                    return material
        return None

    def clone_material(self, bucket_name: str, material_id: str) -> str:
        material = self.find_material(material_id)
        if material is None:
            raise KeyError(f"material not found: {material_id}")
        payload = copy.deepcopy(material)
        payload["id"] = self._uuid()
        return self.add_material(bucket_name, payload)

    def ensure_material_bucket(self, bucket_name: str) -> list[dict[str, Any]]:
        return self.content.setdefault("materials", {}).setdefault(bucket_name, [])

    def add_material(self, bucket_name: str, payload: dict[str, Any]) -> str:
        material = copy.deepcopy(payload)
        material.setdefault("id", self._uuid())
        self.ensure_material_bucket(bucket_name).append(material)
        return str(material["id"])

    def add_speed(self, speed_payload: dict[str, Any] | None = None) -> str:
        payload = copy.deepcopy(speed_payload) if speed_payload else {}
        payload.setdefault("type", "speed")
        return self.add_material("speeds", payload)

    def add_sound_channel_mapping(self, mapping_payload: dict[str, Any] | None = None) -> str:
        payload = copy.deepcopy(mapping_payload) if mapping_payload else {}
        payload.setdefault("type", "")
        return self.add_material("sound_channel_mappings", payload)

    def add_placeholder_info(self, info_payload: dict[str, Any] | None = None) -> str:
        payload = copy.deepcopy(info_payload) if info_payload else {}
        payload.setdefault("type", "placeholder_info")
        payload.setdefault("meta_type", "none")
        return self.add_material("placeholder_infos", payload)

    def add_vocal_separation(self, payload: dict[str, Any] | None = None) -> str:
        material = copy.deepcopy(payload) if payload else {}
        material.setdefault("type", "vocal_separation")
        return self.add_material("vocal_separations", material)

    def add_audio_fade(self, payload: dict[str, Any] | None = None) -> str:
        material = copy.deepcopy(payload) if payload else {}
        material.setdefault("type", "audio_fade")
        return self.add_material("audio_fades", material)

    def add_beat(self, payload: dict[str, Any]) -> str:
        return self.add_material("beats", payload)

    def add_canvas(self, payload: dict[str, Any] | None = None) -> str:
        material = copy.deepcopy(payload) if payload else {}
        material.setdefault("type", "canvas_color")
        return self.add_material("canvases", material)

    def add_material_color(self, payload: dict[str, Any] | None = None) -> str:
        return self.add_material("material_colors", payload or {})

    def add_hsl_material(self, payload: dict[str, Any]) -> str:
        material = copy.deepcopy(payload)
        material.setdefault("type", "hsl")
        return self.add_material("hsl", material)

    def add_text_template_material(self, payload: dict[str, Any]) -> str:
        material = copy.deepcopy(payload)
        material.setdefault("type", "text_template")
        return self.add_material("text_templates", material)

    def add_combination_draft_material(self, payload: dict[str, Any]) -> str:
        material = copy.deepcopy(payload)
        material.setdefault("type", "combination")
        return self.add_material("drafts", material)

    def add_segment(
        self,
        *,
        track_type: str,
        material_id: str,
        start_us: int,
        duration_us: int,
        source_start_us: int | None = None,
        source_duration_us: int | None = None,
        track_index: int | None = None,
        render_index: int | None = None,
        clip: dict[str, Any] | None = None,
        extra_material_refs: Iterable[str] | None = None,
        segment_payload: dict[str, Any] | None = None,
        flag: int | None = None,
    ) -> dict[str, Any]:
        track = self._ensure_track(track_type, track_index=track_index, flag=flag)
        segment = copy.deepcopy(segment_payload) if segment_payload else {}
        segment.setdefault("id", self._uuid())
        segment["material_id"] = material_id
        segment.setdefault("target_timerange", {"start": start_us, "duration": duration_us})
        segment.setdefault("render_timerange", {})
        segment.setdefault("track_render_index", self._track_render_index(track))
        segment.setdefault("responsive_layout", {})
        segment.setdefault("source", "segmentsourcenormal")

        refs = list(extra_material_refs or [])
        if refs:
            segment["extra_material_refs"] = refs

        if source_duration_us is not None or source_start_us is not None:
            segment.setdefault(
                "source_timerange",
                {
                    "start": source_start_us or 0,
                    "duration": source_duration_us if source_duration_us is not None else duration_us,
                },
            )

        if clip is not None:
            segment["clip"] = copy.deepcopy(clip)

        if render_index is not None:
            segment["render_index"] = render_index
        elif track_type in {"text", "sticker", "effect", "filter", "adjust"}:
            segment.setdefault("render_index", self._next_render_index())

        track.setdefault("segments", []).append(segment)
        self._sync_duration()
        return segment

    def add_audio(
        self,
        *,
        path: str | Path,
        duration_us: int,
        start_us: int = 0,
        source_start_us: int = 0,
        name: str | None = None,
        material_type: str = "music",
        track_index: int | None = None,
        extra_material_refs: Iterable[str] | None = None,
        volume: float | None = None,
        meta_material_type: int = 0,
    ) -> DraftResourceRef:
        audio_path = Path(path).resolve()
        material_id = self._uuid()
        track = self._ensure_track("audio", track_index=track_index)
        refs = list(extra_material_refs or [])

        self.content.setdefault("materials", {}).setdefault("audios", []).append(
            {
                "id": material_id,
                "type": material_type,
                "name": name or audio_path.name,
                "duration": duration_us,
                "path": audio_path.as_posix(),
                "category_name": "local",
                "music_id": "",
                "app_id": 0,
                "resource_id": "",
                "category_id": "",
                "music_source": "local",
                "similiar_music_info": {},
                "tts_benefit_info": {"benefit_type": "none"},
            }
        )

        segment = {
            "id": self._uuid(),
            "source_timerange": {"start": source_start_us, "duration": duration_us},
            "target_timerange": {"start": start_us, "duration": duration_us},
            "render_timerange": {},
            "material_id": material_id,
            "extra_material_refs": refs,
            "enable_lut": False,
            "enable_adjust": False,
            "enable_hsl": False,
            "track_render_index": self._track_render_index(track),
            "responsive_layout": {},
            "enable_adjust_mask": False,
            "source": "segmentsourcenormal",
        }
        if volume is not None:
            segment["volume"] = volume
        track.setdefault("segments", []).append(segment)

        self._append_meta_material(
            meta_material_type,
            self._build_meta_material_entry(
                path=audio_path,
                duration=duration_us,
                material_type=meta_material_type,
                metetype=material_type,
                extra_info=name or audio_path.name,
            ),
        )
        self._sync_duration()
        return DraftResourceRef("audio", material_id, refs)

    def add_audio_with_defaults(
        self,
        *,
        path: str | Path,
        duration_us: int,
        start_us: int = 0,
        source_start_us: int = 0,
        name: str | None = None,
        volume: float | None = None,
        with_beat: bool = False,
        beat_payload: dict[str, Any] | None = None,
    ) -> DraftResourceRef:
        refs = [
            self.add_speed(),
            self.add_sound_channel_mapping(),
            self.add_placeholder_info(),
            self.add_vocal_separation(),
        ]
        fade_out = min(duration_us, 500_000)
        refs.append(self.add_audio_fade({"fade_out_duration": fade_out}))
        if with_beat:
            refs.append(self.add_beat(beat_payload or {"type": "beats"}))
        return self.add_audio(
            path=path,
            duration_us=duration_us,
            start_us=start_us,
            source_start_us=source_start_us,
            name=name,
            extra_material_refs=refs,
            volume=volume,
        )

    def add_video(
        self,
        *,
        path: str | Path,
        duration_us: int,
        start_us: int = 0,
        source_start_us: int = 0,
        width: int = 0,
        height: int = 0,
        transform_x: float = 0.0,
        transform_y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        track_index: int | None = None,
        extra_material_refs: Iterable[str] | None = None,
        segment_payload: dict[str, Any] | None = None,
    ) -> DraftResourceRef:
        video_path = Path(path).resolve()
        material_id = self._uuid()
        track = self._ensure_track("video", track_index=track_index)
        refs = list(extra_material_refs or [])

        self.content.setdefault("materials", {}).setdefault("videos", []).append(
            {
                "id": material_id,
                "type": "video",
                "path": video_path.as_posix(),
                "duration": duration_us,
                "width": width,
                "height": height,
                "material_name": video_path.name,
                "local_material_id": "",
            }
        )

        segment = copy.deepcopy(segment_payload) if segment_payload else {}
        segment.update(
            {
                "id": self._uuid(),
                "source_timerange": {"start": source_start_us, "duration": duration_us},
                "target_timerange": {"start": start_us, "duration": duration_us},
                "render_timerange": {},
                "material_id": material_id,
                "extra_material_refs": refs,
                "clip": {
                    "scale": {"x": scale_x, "y": scale_y},
                    "transform": {"x": transform_x, "y": transform_y},
                    "flip": {},
                },
                "enable_lut": False,
                "enable_adjust": False,
                "enable_hsl": False,
                "track_render_index": self._track_render_index(track),
                "responsive_layout": {},
                "enable_adjust_mask": False,
                "source": "segmentsourcenormal",
            }
        )
        track.setdefault("segments", []).append(segment)

        self._append_meta_material(
            1,
            self._build_meta_material_entry(
                path=video_path,
                duration=duration_us,
                material_type=1,
                metetype="video",
                width=width,
                height=height,
                extra_info=video_path.name,
            ),
        )
        self._sync_duration()
        return DraftResourceRef("video", material_id, refs)

    def add_video_with_defaults(
        self,
        *,
        path: str | Path,
        duration_us: int,
        start_us: int = 0,
        source_start_us: int = 0,
        width: int = 0,
        height: int = 0,
        transform_x: float = 0.0,
        transform_y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        with_canvas: bool = True,
        hdr_mode: int | None = 1,
    ) -> DraftResourceRef:
        refs = [
            self.add_speed(),
            self.add_placeholder_info(),
        ]
        if with_canvas:
            refs.append(self.add_canvas())
            refs.append(self.add_material_color())
        segment_payload: dict[str, Any] = {}
        if hdr_mode is not None:
            segment_payload["hdr_settings"] = {"mode": hdr_mode}
        return self.add_video(
            path=path,
            duration_us=duration_us,
            start_us=start_us,
            source_start_us=source_start_us,
            width=width,
            height=height,
            transform_x=transform_x,
            transform_y=transform_y,
            scale_x=scale_x,
            scale_y=scale_y,
            track_index=0 if self.get_tracks("video") else None,
            extra_material_refs=refs,
            segment_payload=segment_payload,
        )

    def add_text(
        self,
        *,
        text: str,
        start_us: int,
        duration_us: int,
        font_path: str = "C:/Windows/Fonts/msyh.ttc",
        font_size: float = 12.0,
        text_color: str = "#FFFFFF",
        alignment: int = 1,
        track_index: int | None = None,
        effect_material_ids: Iterable[str] | None = None,
        words: dict[str, Any] | None = None,
        recognize_task_id: str | None = None,
        transform_x: float = 0.0,
        transform_y: float = 0.72,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> DraftResourceRef:
        material_id = self._uuid()
        track = self._ensure_track("text", track_index=track_index, flag=1)
        refs = list(effect_material_ids or [])
        style_range = [0, len(text)]
        rgb = self._hex_to_rgb(text_color)
        recognize_task = recognize_task_id or f"{self.content['id'].lower()}_subtitle"

        self.content.setdefault("materials", {}).setdefault("texts", []).append(
            {
                "recognize_task_id": recognize_task,
                "id": material_id,
                "recognize_text": text,
                "type": "subtitle",
                "content": json.dumps(
                    {
                        "text": text,
                        "styles": [
                            {
                                "fill": {
                                    "content": {
                                        "render_type": "solid",
                                        "solid": {"color": rgb},
                                    }
                                },
                                "font": {"path": font_path, "id": ""},
                                "size": font_size,
                                "range": style_range,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                "base_content": json.dumps(
                    {
                        "styles": [
                            {
                                "fill": {
                                    "alpha": 1.0,
                                    "content": {
                                        "render_type": "solid",
                                        "solid": {"alpha": 1.0, "color": rgb},
                                    },
                                },
                                "font": {"id": "", "path": font_path},
                                "range": style_range,
                                "size": font_size,
                            }
                        ],
                        "text": text,
                    },
                    ensure_ascii=False,
                ),
                "words": words or {"start_time": [], "end_time": [], "text": []},
                "current_words": {},
                "combo_info": {},
                "caption_template_info": {"resource_id": "", "path": ""},
                "layer_weight": 1,
                "line_spacing": 0.02,
                "shadow_alpha": 0.9,
                "shadow_smoothing": 0.45,
                "shadow_distance": 4.0,
                "shadow_point": {"x": 0.6363961030678928, "y": -0.6363961030678928},
                "shadow_angle": -45.0,
                "border_width": 0.08,
                "text_color": text_color,
                "font_path": font_path,
                "initial_scale": 1.0,
                "alignment": alignment,
                "use_effect_default_color": False,
                "add_type": 1,
                "fixed_width": 780.0,
                "subtitle_keywords": {},
                "lyrics_template": {"resource_id": "", "path": ""},
            }
        )

        track.setdefault("segments", []).append(
            {
                "id": self._uuid(),
                "target_timerange": {"start": start_us, "duration": duration_us},
                "render_timerange": {},
                "clip": {
                    "scale": {"x": scale_x, "y": scale_y},
                    "transform": {"x": transform_x, "y": transform_y},
                    "flip": {},
                },
                "uniform_scale": {},
                "material_id": material_id,
                "extra_material_refs": refs,
                "render_index": self._next_render_index(),
                "enable_lut": False,
                "enable_adjust": False,
                "enable_hsl": False,
                "track_render_index": self._track_render_index(track),
                "responsive_layout": {},
                "enable_adjust_mask": False,
                "source": "segmentsourcenormal",
            }
        )
        self._sync_duration()
        return DraftResourceRef("text", material_id, refs)

    def add_subtitle(
        self,
        *,
        text: str,
        start_us: int,
        duration_us: int,
        words: dict[str, Any] | None = None,
        recognize_task_id: str | None = None,
        track_index: int | None = None,
    ) -> DraftResourceRef:
        ref = self.add_text(
            text=text,
            start_us=start_us,
            duration_us=duration_us,
            words=words,
            recognize_task_id=recognize_task_id,
            track_index=track_index,
        )
        task_id = recognize_task_id or f"{self.content['id'].lower()}_subtitle"
        self._append_subtitle_taskinfo(task_id, text=text, start_us=start_us, duration_us=duration_us, words=words)
        self._append_subtitle_fragment(task_id, text=text, start_us=start_us, duration_us=duration_us, words=words)
        return ref

    def add_text_template_instance(
        self,
        *,
        start_us: int,
        duration_us: int,
        template_payload: dict[str, Any],
        text_material_payloads: list[dict[str, Any]] | None = None,
        non_text_refs: list[dict[str, Any]] | None = None,
    ) -> str:
        payload = copy.deepcopy(template_payload)
        text_infos = payload.setdefault("text_info_resources", [])
        for text_payload in text_material_payloads or []:
            text_material_id = self.add_material("texts", text_payload)
            text_infos.append(
                {
                    "id": self._uuid(),
                    "attach_info": {
                        "duration": duration_us,
                        "clip": {
                            "scale": {"x": 1.0, "y": 1.0},
                            "transform": {"x": 0.0, "y": 0.0},
                            "flip": {},
                        },
                    },
                    "text_material_id": text_material_id,
                    "extra_material_refs": [],
                }
            )
        if non_text_refs:
            payload.setdefault("non_text_info_resources", []).extend(copy.deepcopy(non_text_refs))
        return self.add_text_template_material(payload)

    def add_effect(
        self,
        *,
        effect_type: str = "sticker_animation",
        animations: list[dict[str, Any]] | None = None,
        target_segment_id: str | None = None,
    ) -> DraftResourceRef:
        material_id = self._uuid()
        material = {"id": material_id, "type": effect_type}
        if animations is not None:
            material["animations"] = animations
        self.content.setdefault("materials", {}).setdefault("material_animations", []).append(material)
        refs = [target_segment_id] if target_segment_id else []
        return DraftResourceRef("effect", material_id, refs)

    def add_sticker(
        self,
        *,
        path: str,
        start_us: int,
        duration_us: int,
        name: str = "",
        track_index: int | None = None,
        transform_x: float = 0.0,
        transform_y: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        extra_material_refs: Iterable[str] | None = None,
        material_payload: dict[str, Any] | None = None,
    ) -> DraftResourceRef:
        payload = copy.deepcopy(material_payload) if material_payload else {}
        payload.setdefault("id", self._uuid())
        payload.setdefault("type", "sticker")
        payload.setdefault("path", path)
        payload.setdefault("name", name)
        material_id = self.add_material("stickers", payload)
        refs = list(extra_material_refs or [])
        self.add_segment(
            track_type="sticker",
            material_id=material_id,
            start_us=start_us,
            duration_us=duration_us,
            track_index=track_index,
            clip={
                "scale": {"x": scale_x, "y": scale_y},
                "transform": {"x": transform_x, "y": transform_y},
                "flip": {},
            },
            extra_material_refs=refs,
        )
        return DraftResourceRef("sticker", material_id, refs)

    def add_video_effect(
        self,
        *,
        start_us: int,
        duration_us: int,
        material_payload: dict[str, Any],
        track_index: int | None = None,
    ) -> DraftResourceRef:
        material_id = self.add_material("video_effects", material_payload)
        self.add_segment(
            track_type="effect",
            material_id=material_id,
            start_us=start_us,
            duration_us=duration_us,
            track_index=track_index,
        )
        return DraftResourceRef("video_effect", material_id, [])

    def add_filter(
        self,
        *,
        start_us: int,
        duration_us: int,
        material_payload: dict[str, Any],
        track_index: int | None = None,
    ) -> DraftResourceRef:
        material_id = self.add_material("effects", material_payload)
        self.add_segment(
            track_type="filter",
            material_id=material_id,
            start_us=start_us,
            duration_us=duration_us,
            track_index=track_index,
        )
        return DraftResourceRef("filter", material_id, [])

    def add_adjust(
        self,
        *,
        start_us: int,
        duration_us: int,
        material_payload: dict[str, Any],
        extra_material_refs: Iterable[str] | None = None,
        track_index: int | None = None,
    ) -> DraftResourceRef:
        material_id = self.add_material("placeholders", material_payload)
        refs = list(extra_material_refs or [])
        self.add_segment(
            track_type="adjust",
            material_id=material_id,
            start_us=start_us,
            duration_us=duration_us,
            track_index=track_index,
            extra_material_refs=refs,
        )
        return DraftResourceRef("adjust", material_id, refs)

    def add_transition(self, material_payload: dict[str, Any]) -> str:
        return self.add_material("transitions", material_payload)

    def to_plain_bundle(
        self,
        *,
        meta_key_iv: str = "00000000000000000000000000000000ABCDEFGHIJKLMNOP",
        content_key_iv: str = "11111111111111111111111111111111QRSTUVWXYZABCDEF",
    ) -> DraftBundle:
        return DraftBundle(
            draft_root=str(self.draft_root),
            files={
                "draft_meta_info.json": DraftFileData(
                    file_name="draft_meta_info.json",
                    source_path=str((self.draft_root / "draft_meta_info.json").resolve()),
                    key_iv=meta_key_iv,
                    plaintext_text=json.dumps(self.meta, ensure_ascii=False),
                    data=copy.deepcopy(self.meta),
                ),
                "draft_content.json": DraftFileData(
                    file_name="draft_content.json",
                    source_path=str((self.draft_root / "draft_content.json").resolve()),
                    key_iv=content_key_iv,
                    plaintext_text=json.dumps(self.content, ensure_ascii=False),
                    data=copy.deepcopy(self.content),
                ),
            },
        )

    def save_draft(
        self,
        out_dir: str | Path | None = None,
        *,
        template_draft: DraftBundle | None = None,
        pretty: bool = False,
        ensure_ascii: bool = False,
    ) -> dict[str, Any]:
        if template_draft is not None:
            draft = copy.deepcopy(template_draft)
            if "draft_meta_info.json" not in draft.files or "draft_content.json" not in draft.files:
                raise ValueError("template_draft must include both draft_meta_info.json and draft_content.json")
            draft.files["draft_meta_info.json"].data = copy.deepcopy(self.meta)
            draft.files["draft_content.json"].data = copy.deepcopy(self.content)
        else:
            draft = self.to_plain_bundle()
        return save_draft(draft, out_dir=out_dir, pretty=pretty, ensure_ascii=ensure_ascii)

    def _ensure_track(self, track_type: str, *, track_index: int | None = None, flag: int | None = None) -> dict[str, Any]:
        tracks = self.content.setdefault("tracks", [])
        same_type = [track for track in tracks if track.get("type") == track_type]
        if track_index is not None and track_index < len(same_type):
            return same_type[track_index]
        track: dict[str, Any] = {
            "id": self._uuid(),
            "type": track_type,
            "segments": [],
            "is_default_name": True,
        }
        if flag is not None:
            track["flag"] = flag
        tracks.append(track)
        return track

    def _track_render_index(self, track: dict[str, Any]) -> int:
        tracks = self.content.setdefault("tracks", [])
        for index, item in enumerate(tracks):
            if item is track:
                return index
        return len(tracks)

    def _next_render_index(self) -> int:
        render_indexes = []
        for track in self.content.get("tracks", []):
            for segment in track.get("segments", []):
                if "render_index" in segment:
                    render_indexes.append(int(segment["render_index"]))
        return max(render_indexes, default=9999) + 1

    def _append_meta_material(self, material_type: int, value: dict[str, Any]) -> None:
        materials = self.meta.setdefault("draft_materials", [])
        for item in materials:
            if item.get("type") == material_type:
                item.setdefault("value", []).append(value)
                return
        materials.append({"type": material_type, "value": [value]})

    def _append_subtitle_taskinfo(
        self,
        task_id: str,
        *,
        text: str,
        start_us: int,
        duration_us: int,
        words: dict[str, Any] | None,
    ) -> None:
        config = self.content.setdefault("config", {})
        taskinfo = config.setdefault("subtitle_taskinfo", [])
        utterance = self._subtitle_utterance(text=text, start_us=start_us, duration_us=duration_us, words=words)
        for item in taskinfo:
            if item.get("id") != task_id:
                continue
            payload = json.loads(item.get("content", "{}") or "{}")
            payload.setdefault("attribute", {}).setdefault("extra", {}).setdefault("language", "zh-CN")
            payload.setdefault("utterances", []).append(utterance)
            item["content"] = json.dumps(payload, ensure_ascii=False)
            return
        taskinfo.append(
            {
                "id": task_id,
                "type": 10,
                "language": "zh-CN",
                "content": json.dumps(
                    {
                        "attribute": {"extra": {"language": "zh-CN"}},
                        "utterances": [utterance],
                    },
                    ensure_ascii=False,
                ),
            }
        )

    def _append_subtitle_fragment(
        self,
        task_id: str,
        *,
        text: str,
        start_us: int,
        duration_us: int,
        words: dict[str, Any] | None,
    ) -> None:
        extra_info = self.content.setdefault("extra_info", {})
        fragment_list = extra_info.setdefault("subtitle_fragment_info_list", [])
        utterance = self._subtitle_utterance(text=text, start_us=start_us, duration_us=duration_us, words=words)
        fragment_list.append(
            {
                "start_time": start_us,
                "end_time": start_us + duration_us,
                "subtitle_cache_info": json.dumps(
                    {
                        "sentence_list": [
                            {
                                "attribute": {"event": "speech"},
                                "bilingual_lan": "",
                                "end_time": utterance["end_time"],
                                "language_server_recognize": "zh-CN",
                                "language_user_select": "",
                                "start_time": utterance["start_time"],
                                "task_id": task_id,
                                "text": text,
                                "translation_text": "",
                                "words": utterance["words"],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                "key": uuid.uuid5(uuid.NAMESPACE_URL, f"{task_id}:{start_us}:{text}").hex,
            }
        )

    def _subtitle_utterance(
        self,
        *,
        text: str,
        start_us: int,
        duration_us: int,
        words: dict[str, Any] | None,
    ) -> dict[str, Any]:
        start_ms = int(round(start_us / 1000))
        end_ms = int(round((start_us + duration_us) / 1000))
        raw_words = words or {"start_time": [], "end_time": [], "text": []}
        word_items = []
        for word_text, word_start, word_end in zip(
            raw_words.get("text", []),
            raw_words.get("start_time", []),
            raw_words.get("end_time", []),
        ):
            word_items.append(
                {
                    "start_time": start_ms + int(word_start),
                    "end_time": start_ms + int(word_end),
                    "text": word_text,
                    "attribute": {"extra": {"language": "zh-CN"}},
                }
            )
        return {
            "start_time": start_ms,
            "end_time": end_ms,
            "text": text,
            "words": word_items,
        }

    def _build_meta_material_entry(
        self,
        *,
        path: Path,
        duration: int,
        material_type: int,
        metetype: str,
        extra_info: str,
        width: int = 0,
        height: int = 0,
    ) -> dict[str, Any]:
        now_s = int(path.stat().st_mtime) if path.exists() else 0
        now_us = int(now_s * 1_000_000)
        return {
            "ai_group_type": "",
            "create_time": now_s,
            "duration": duration,
            "enter_from": 0,
            "extra_info": extra_info,
            "file_Path": path.as_posix(),
            "height": height,
            "id": self._uuid(),
            "import_time": now_s,
            "import_time_ms": now_us,
            "item_source": 1,
            "md5": "",
            "metetype": metetype,
            "roughcut_time_range": {"duration": duration, "start": 0},
            "sub_time_range": {"duration": -1, "start": -1},
            "type": material_type,
            "width": width,
        }

    def _sync_duration(self) -> None:
        max_end = 0
        for track in self.content.get("tracks", []):
            for segment in track.get("segments", []):
                timerange = segment.get("target_timerange", {})
                start = int(timerange.get("start", 0))
                duration = int(timerange.get("duration", 0))
                max_end = max(max_end, start + duration)
        self.set_duration_us(max_end)

    def _build_default_meta(self, *, draft_name: str, new_version: str) -> dict[str, Any]:
        return {
            "cloud_draft_cover": False,
            "cloud_draft_sync": False,
            "cloud_package_completed_time": "",
            "draft_cloud_capcut_purchase_info": "",
            "draft_cloud_last_action_download": False,
            "draft_cloud_package_type": "",
            "draft_cloud_purchase_info": "",
            "draft_cloud_template_id": "",
            "draft_cloud_tutorial_info": "",
            "draft_cloud_videocut_purchase_info": "",
            "draft_cover": "draft_cover.jpg",
            "draft_deeplink_url": "",
            "draft_enterprise_info": {
                "draft_enterprise_extra": "",
                "draft_enterprise_id": "",
                "draft_enterprise_name": "",
                "enterprise_material": [],
            },
            "draft_fold_path": self.draft_root.as_posix(),
            "draft_id": self._uuid(),
            "draft_is_ae_produce": False,
            "draft_is_ai_packaging_used": False,
            "draft_is_ai_shorts": False,
            "draft_is_ai_translate": False,
            "draft_is_article_video_draft": False,
            "draft_is_cloud_temp_draft": False,
            "draft_is_from_deeplink": "false",
            "draft_is_invisible": False,
            "draft_is_web_article_video": False,
            "draft_materials": [
                {"type": 0, "value": []},
                {"type": 1, "value": []},
                {"type": 2, "value": []},
                {"type": 3, "value": []},
                {"type": 6, "value": []},
                {"type": 7, "value": []},
                {"type": 8, "value": []},
            ],
            "draft_materials_copied_info": [],
            "draft_name": draft_name,
            "draft_need_rename_folder": False,
            "draft_new_version": new_version,
            "draft_removable_storage_device": "",
            "draft_root_path": self.draft_root.parent.as_posix(),
            "draft_segment_extra_info": [],
            "draft_timeline_materials_size_": 0,
            "draft_type": "",
            "draft_web_article_video_enter_from": "",
            "tm_draft_cloud_completed": "",
            "tm_draft_cloud_entry_id": -1,
            "tm_draft_cloud_modified": 0,
            "tm_draft_cloud_parent_entry_id": -1,
            "tm_draft_cloud_space_id": -1,
            "tm_draft_cloud_user_id": -1,
            "tm_draft_create": 0,
            "tm_draft_modified": 0,
            "tm_draft_removed": 0,
            "tm_duration": 0,
        }

    def _build_default_content(
        self,
        *,
        width: int,
        height: int,
        ratio: str,
        version: int,
        new_version: str,
    ) -> dict[str, Any]:
        draft_id = self.meta["draft_id"]
        return {
            "id": draft_id,
            "version": version,
            "new_version": new_version,
            "duration": 0,
            "color_space": 0,
            "canvas_config": {"ratio": ratio, "width": width, "height": height},
            "config": {"subtitle_taskinfo": []},
            "extra_info": {"subtitle_fragment_info_list": []},
            "function_assistant_info": {"fps": {}},
            "keyframes": {},
            "last_modified_platform": self._default_platform(),
            "materials": {
                "audio_fades": [],
                "audios": [],
                "beats": [],
                "canvases": [],
                "drafts": [],
                "effects": [],
                "hsl": [],
                "images": [],
                "loudnesses": [],
                "material_animations": [],
                "material_colors": [],
                "placeholder_infos": [],
                "placeholders": [],
                "sound_channel_mappings": [],
                "speeds": [],
                "stickers": [],
                "text_templates": [],
                "texts": [],
                "transitions": [],
                "video_effects": [],
                "videos": [],
                "vocal_separations": [],
            },
            "path": "",
            "platform": self._default_platform(),
            "render_index_track_mode_on": True,
            "smart_ads_info": {},
            "tracks": [],
            "uneven_animation_template_info": {},
        }

    def _default_platform(self) -> dict[str, Any]:
        return {
            "os": "windows",
            "os_version": "",
            "app_id": 3704,
            "app_version": "10.3.0",
            "app_source": "lv",
            "device_id": "",
            "hard_disk_id": "",
            "mac_address": "",
        }

    def _hex_to_rgb(self, value: str) -> list[float]:
        raw = value.lstrip("#")
        if len(raw) != 6:
            return [1.0, 1.0, 1.0]
        return [int(raw[index:index + 2], 16) / 255.0 for index in range(0, 6, 2)]

    def _uuid(self) -> str:
        return str(uuid.uuid4()).upper()


class JianyingDraftParser:
    """Parse encrypted/plain Jianying draft JSON into a mutable builder."""

    @staticmethod
    def load_encrypted(draft_root: str | Path) -> JianyingDraftBuilder:
        return JianyingDraftBuilder.from_bundle(load_draft(draft_root))

    @staticmethod
    def load_plain(
        draft_root: str | Path,
        *,
        meta_path: str | Path,
        content_path: str | Path,
    ) -> JianyingDraftBuilder:
        return JianyingDraftBuilder.from_plaintext_files(
            draft_root,
            meta_path=meta_path,
            content_path=content_path,
        )
