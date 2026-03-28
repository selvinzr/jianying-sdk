# jianying-sdk

Python SDK for Jianying draft creation, editing, encryption, decryption, and template-based export.

## Install

```bash
pip install -e .
```

Published package name recommendation:

```bash
pip install jianying-sdk
```

Import name:

```python
from jianying import Jianying
```

## Quick Start

### 1. Create a new encrypted draft

```python
from jianying import Jianying

builder = Jianying(draft_name="demo")
builder.addText(
    text="hello world",
    start_us=0,
    duration_us=2_000_000,
    font_size=14.0,
    text_color="#FFFFFF",
)
builder.save("output/draft")
```

### 2. Load an existing encrypted draft

```python
from jianying import Jianying

draft = Jianying.load("existing_draft")
draft.saveJson("output/plain")
draft.save("output/reencrypted")
```

### 3. Load plaintext JSON draft files

```python
from jianying import Jianying

draft = Jianying.load_json("plain_draft")
draft.save("output/encrypted")
```

## Main API

- `Jianying()`: create a new draft builder
- `Jianying.load(path)`: load encrypted Jianying draft directory
- `Jianying.load_json(path)`: load plaintext `draft_meta_info.plain.json` and `draft_content.plain.json`
- `draft.addText(...)`: add a text segment
- `draft.addSubtitle(...)`: add a subtitle segment with subtitle task metadata
- `draft.addAudio(...)`: add an audio segment
- `draft.addAudioWithDefaults(...)`: add an audio segment with default refs like fade/speed/mapping
- `draft.addVideo(...)`: add a video segment
- `draft.addVideoWithDefaults(...)`: add a video segment with default refs
- `draft.addSticker(...)`: add a sticker segment
- `draft.addEffect(...)`: add an animation/effect material
- `draft.addVideoEffect(...)`: add a video effect segment
- `draft.addFilter(...)`: add a filter segment
- `draft.addAdjust(...)`: add an adjust segment
- `draft.addTransition(...)`: add a transition material
- `draft.save(path)`: save encrypted Jianying draft files
- `draft.saveJson(path)`: save plaintext JSON files

## Advanced Modules

- `jianying.crypto`: low-level encryption/decryption helpers
- `jianying.draft`: high-level draft builder and parser
- `jianying.project_exporter`: template-based exporter
- `jianying.presets`: preset animation and subtitle helpers
- `jianying.models`: timeline and exporter data models

## Docs

- `docs/API_REFERENCE.md`: facade and low-level API usage
- `docs/INTERNAL_METHODS.md`: internal module and method guide
