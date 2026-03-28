# Internal Methods Guide

This document lists the important internal modules and the methods you are expected to use when you need more control than the `Jianying` facade provides.

## Module: `jianying.crypto`

Purpose:

- Read encrypted Jianying draft files
- Write encrypted Jianying draft files
- Convert between encrypted and plaintext representations

Main functions:

- `load_draft(draft_root)`
  Loads `draft_content.json` and `draft_meta_info.json` into a `DraftBundle`.
- `save_draft(draft, out_dir=None, pretty=False, ensure_ascii=False)`
  Saves a `DraftBundle` back to encrypted Jianying files.
- `decrypt_jianying_file(input_path, output_path, pretty=False)`
  Decrypts one Jianying JSON file.
- `encrypt_jianying_file(input_path, output_path, keyiv=..., keyiv_path=...)`
  Encrypts one plaintext JSON file back into Jianying format.
- `decrypt_draft_directory(draft_root, out_dir, pretty=True)`
  Decrypts supported draft files in a directory.
- `reencrypt_draft_directory(plain_dir, out_dir)`
  Re-encrypts plaintext draft files previously produced by `decrypt_draft_directory`.
- `roundtrip_file(input_path, out_dir)`
  Decrypts and re-encrypts one file for verification.
- `inspect_file(input_path)`
  Checks whether a file looks like a supported Jianying encrypted file.

## Module: `jianying.draft`

Purpose:

- Create and mutate `draft_content` and `draft_meta_info`
- Add tracks, materials, and segments
- Save the current builder state as encrypted draft output

Main classes:

### `JianyingDraftBuilder`

Creation methods:

- `JianyingDraftBuilder(draft_root, draft_name=..., width=..., height=..., ratio=...)`
- `JianyingDraftBuilder.from_bundle(draft)`
- `JianyingDraftBuilder.from_plaintext_files(draft_root, meta_path=..., content_path=...)`
- `JianyingDraftBuilder.from_template_directory(draft_root, template_dir=...)`

Frequently used methods:

- `set_draft_name(name)`
- `set_duration_us(duration_us)`
- `get_tracks(track_type=None)`
- `get_materials(bucket_name)`
- `find_material(material_id)`
- `add_audio(...)`
- `add_audio_with_defaults(...)`
- `add_video(...)`
- `add_video_with_defaults(...)`
- `add_text(...)`
- `add_subtitle(...)`
- `add_sticker(...)`
- `add_effect(...)`
- `add_video_effect(...)`
- `add_filter(...)`
- `add_adjust(...)`
- `add_transition(...)`
- `save_draft(out_dir=None, pretty=False, ensure_ascii=False)`

### `JianyingDraftParser`

- `load_encrypted(draft_root)`
- `load_plain(draft_root, meta_path=..., content_path=...)`

## Module: `jianying.project_exporter`

Purpose:

- Build complete Jianying drafts from planned subtitle timelines and template presets

Main classes:

- `March18ProjectExporterConfig`
- `March18ProjectExporter`

Main method:

- `March18ProjectExporter.export(planned_timeline, output_dir, audio_path=..., draft_name=...)`

## Module: `jianying.presets.subtitle_motion`

Purpose:

- Clone animation materials from template drafts
- Compose stacked subtitle tracks with motion behavior

Main classes:

- `AnimationMaterialLibrary`
- `StackedSubtitleComposer`
- `StackedSubtitleComposerConfig`
- `StackedSubtitleLine`
- `ComposedSubtitleRef`

## Module: `jianying.presets.march18`

Purpose:

- Reusable preset built from a template draft
- Applies intro text and subtitle layout onto a builder

Main classes:

- `March18PresetConfig`
- `March18StylePreset`
- `March18SubtitleLine`

## Module: `jianying.models`

Purpose:

- Provide the timeline-style models needed by the exporter and preset layers

Included types:

- `TimelineWord`
- `TimelineLine`
- `TimelineShot`
- `TimelineDocument`
- `StyleSpan`
- `LineLayout`
- `LineMotion`
- `PlannedTimelineLine`
- `PlannedTimelineShot`
- `PlannedTimelineDocument`
