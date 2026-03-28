from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jianying.draft import JianyingDraftBuilder, JianyingDraftParser


class Jianying:
    """Simple facade for building, loading, and saving Jianying drafts."""

    def __init__(
        self,
        draft_name: str = "untitled",
        *,
        draft_root: str | Path | None = None,
        width: int = 1080,
        height: int = 1920,
        ratio: str = "9:16",
        version: int = 360000,
        new_version: str = "163.0.0",
        builder: JianyingDraftBuilder | None = None,
    ) -> None:
        self._builder = builder or JianyingDraftBuilder(
            draft_root or Path('.'),
            draft_name=draft_name,
            width=width,
            height=height,
            ratio=ratio,
            version=version,
            new_version=new_version,
        )

    @property
    def builder(self) -> JianyingDraftBuilder:
        return self._builder

    @property
    def draft_root(self) -> Path:
        return self._builder.draft_root

    @property
    def meta(self) -> dict[str, Any]:
        return self._builder.meta

    @property
    def content(self) -> dict[str, Any]:
        return self._builder.content

    @classmethod
    def load(cls, draft_root: str | Path) -> 'Jianying':
        return cls(builder=JianyingDraftParser.load_encrypted(draft_root))

    @classmethod
    def load_json(
        cls,
        path: str | Path,
        *,
        meta_name: str = 'draft_meta_info.plain.json',
        content_name: str = 'draft_content.plain.json',
    ) -> 'Jianying':
        root = Path(path)
        meta_path = root / meta_name if root.is_dir() else Path(path)
        if root.is_dir():
            content_path = root / content_name
            draft_root = root
        else:
            content_path = root.parent / content_name
            draft_root = root.parent
        builder = JianyingDraftParser.load_plain(
            draft_root,
            meta_path=meta_path,
            content_path=content_path,
        )
        return cls(builder=builder)

    @classmethod
    def from_template(
        cls,
        template_dir: str | Path,
        *,
        draft_root: str | Path | None = None,
        meta_name: str = 'draft_meta_info.plain.json',
        content_name: str = 'draft_content.plain.json',
    ) -> 'Jianying':
        builder = JianyingDraftBuilder.from_template_directory(
            draft_root or template_dir,
            template_dir=template_dir,
            meta_name=meta_name,
            content_name=content_name,
        )
        return cls(builder=builder)

    def set_draft_name(self, name: str) -> 'Jianying':
        self._builder.set_draft_name(name)
        return self

    def setDraftName(self, name: str) -> 'Jianying':
        return self.set_draft_name(name)

    def set_duration_us(self, duration_us: int) -> 'Jianying':
        self._builder.set_duration_us(duration_us)
        return self

    def setDurationUs(self, duration_us: int) -> 'Jianying':
        return self.set_duration_us(duration_us)

    def add_text(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_text(**kwargs)
        return self

    def addText(self, **kwargs: Any) -> 'Jianying':
        return self.add_text(**kwargs)

    def add_subtitle(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_subtitle(**kwargs)
        return self

    def addSubtitle(self, **kwargs: Any) -> 'Jianying':
        return self.add_subtitle(**kwargs)

    def add_audio(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_audio(**kwargs)
        return self

    def addAudio(self, **kwargs: Any) -> 'Jianying':
        return self.add_audio(**kwargs)

    def add_audio_with_defaults(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_audio_with_defaults(**kwargs)
        return self

    def addAudioWithDefaults(self, **kwargs: Any) -> 'Jianying':
        return self.add_audio_with_defaults(**kwargs)

    def add_video(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_video(**kwargs)
        return self

    def addVideo(self, **kwargs: Any) -> 'Jianying':
        return self.add_video(**kwargs)

    def add_video_with_defaults(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_video_with_defaults(**kwargs)
        return self

    def addVideoWithDefaults(self, **kwargs: Any) -> 'Jianying':
        return self.add_video_with_defaults(**kwargs)

    def add_sticker(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_sticker(**kwargs)
        return self

    def addSticker(self, **kwargs: Any) -> 'Jianying':
        return self.add_sticker(**kwargs)

    def add_effect(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_effect(**kwargs)
        return self

    def addEffect(self, **kwargs: Any) -> 'Jianying':
        return self.add_effect(**kwargs)

    def add_filter(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_filter(**kwargs)
        return self

    def addFilter(self, **kwargs: Any) -> 'Jianying':
        return self.add_filter(**kwargs)

    def add_adjust(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_adjust(**kwargs)
        return self

    def addAdjust(self, **kwargs: Any) -> 'Jianying':
        return self.add_adjust(**kwargs)

    def add_video_effect(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_video_effect(**kwargs)
        return self

    def addVideoEffect(self, **kwargs: Any) -> 'Jianying':
        return self.add_video_effect(**kwargs)

    def add_transition(self, **kwargs: Any) -> 'Jianying':
        self._builder.add_transition(**kwargs)
        return self

    def addTransition(self, **kwargs: Any) -> 'Jianying':
        return self.add_transition(**kwargs)

    def save(self, path: str | Path, *, pretty: bool = False, ensure_ascii: bool = False) -> dict[str, Any]:
        return self._builder.save_draft(path, pretty=pretty, ensure_ascii=ensure_ascii)

    def save_json(
        self,
        path: str | Path,
        *,
        meta_name: str = 'draft_meta_info.plain.json',
        content_name: str = 'draft_content.plain.json',
        ensure_ascii: bool = False,
        indent: int = 2,
    ) -> dict[str, str]:
        output_root = Path(path).resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        meta_path = output_root / meta_name
        content_path = output_root / content_name
        meta_path.write_text(json.dumps(self.meta, ensure_ascii=ensure_ascii, indent=indent), encoding='utf-8')
        content_path.write_text(json.dumps(self.content, ensure_ascii=ensure_ascii, indent=indent), encoding='utf-8')
        return {
            'draft_root': str(output_root),
            'draft_meta_info': str(meta_path),
            'draft_content': str(content_path),
        }

    def saveJson(self, path: str | Path, **kwargs: Any) -> dict[str, str]:
        return self.save_json(path, **kwargs)
