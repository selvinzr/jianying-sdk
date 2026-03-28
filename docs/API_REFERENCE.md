# API Reference

## Facade: `from jianying import Jianying`

### Create a new draft

```python
from jianying import Jianying

draft = Jianying(draft_name="demo")
```

Constructor parameters:

- `draft_name`: draft display name
- `draft_root`: logical root path for the builder
- `width`, `height`, `ratio`: canvas settings
- `version`, `new_version`: Jianying version fields

### Load encrypted draft

```python
from jianying import Jianying

draft = Jianying.load("path/to/draft")
```

Expected files under the directory:

- `draft_content.json`
- `draft_meta_info.json`

### Load plaintext draft JSON

```python
from jianying import Jianying

draft = Jianying.load_json("path/to/plain_dir")
```

Expected files by default:

- `draft_content.plain.json`
- `draft_meta_info.plain.json`

### Save encrypted draft

```python
result = draft.save("output/draft")
```

Writes encrypted Jianying files and returns generated file metadata.

### Save plaintext JSON

```python
result = draft.saveJson("output/plain")
```

Writes:

- `draft_meta_info.plain.json`
- `draft_content.plain.json`

### Add text

```python
(
    Jianying(draft_name="demo")
    .addText(text="hello", start_us=0, duration_us=1_000_000)
    .save("output/draft")
)
```

Common arguments:

- `text`
- `start_us`
- `duration_us`
- `font_path`
- `font_size`
- `text_color`
- `track_index`
- `transform_x`
- `transform_y`
- `scale_x`
- `scale_y`

### Add audio

```python
(
    Jianying(draft_name="demo")
    .addAudio(path="audio.wav", duration_us=3_000_000)
    .save("output/draft")
)
```

### Add video

```python
(
    Jianying(draft_name="demo")
    .addVideo(path="video.mp4", duration_us=3_000_000, width=1080, height=1920)
    .save("output/draft")
)
```

### Add sticker

```python
(
    Jianying(draft_name="demo")
    .addSticker(path="assets/sticker.png", start_us=0, duration_us=1_500_000)
    .save("output/draft")
)
```

### Add effect material

```python
draft = Jianying(draft_name="demo")
draft.addEffect(effect_type="sticker_animation", animations=[{"type": "in", "name": "fade_in"}])
```

### Add video effect

```python
draft = Jianying(draft_name="demo")
draft.addVideoEffect(start_us=0, duration_us=1_000_000, effect_payload={"name": "glow"})
```

### Add filter

```python
draft = Jianying(draft_name="demo")
draft.addFilter(start_us=0, duration_us=2_000_000, filter_payload={"name": "warm"})
```

### Add adjust

```python
draft = Jianying(draft_name="demo")
draft.addAdjust(start_us=0, duration_us=2_000_000, adjust_payload={"name": "contrast"})
```

### Add transition

```python
draft = Jianying(draft_name="demo")
draft.addTransition(material_payload={"name": "crossfade"})
```

### Facade aliases

Both snake_case and camelCase are supported for the common facade methods:

- `set_draft_name` / `setDraftName`
- `set_duration_us` / `setDurationUs`
- `add_text` / `addText`
- `add_subtitle` / `addSubtitle`
- `add_audio` / `addAudio`
- `add_audio_with_defaults` / `addAudioWithDefaults`
- `add_video` / `addVideo`
- `add_video_with_defaults` / `addVideoWithDefaults`
- `add_sticker` / `addSticker`
- `add_effect` / `addEffect`
- `add_video_effect` / `addVideoEffect`
- `add_filter` / `addFilter`
- `add_adjust` / `addAdjust`
- `add_transition` / `addTransition`
- `save_json` / `saveJson`

## Low-level modules

### `jianying.crypto`

Use this module when you want direct control over encrypted/plaintext draft files.

Key functions:

- `load_draft(draft_root)`
- `save_draft(draft, out_dir)`
- `decrypt_jianying_file(input_path, output_path)`
- `encrypt_jianying_file(input_path, output_path, keyiv=...)`
- `decrypt_draft_directory(draft_root, out_dir)`
- `reencrypt_draft_directory(plain_dir, out_dir)`
- `roundtrip_file(input_path, out_dir)`
- `inspect_file(input_path)`

### `jianying.draft`

Use this module when the facade is too simple and you need material-level editing.

Core classes:

- `JianyingDraftBuilder`
- `JianyingDraftParser`
- `DraftResourceRef`

### `jianying.project_exporter`

Template-driven exporter for subtitle and project assembly.

### `jianying.presets`

Animation and subtitle composition helpers for reusable template workflows.
