# jianying-draft-sdk

Python SDK for Jianying draft editing, encryption/decryption, and template-based export.

## Included capabilities

- Load encrypted `draft_content.json` and `draft_meta_info.json`
- Save modified drafts back to Jianying encrypted format
- Decrypt and re-encrypt complete draft directories
- Build and edit draft structures with `JianyingDraftBuilder`
- Apply reusable subtitle presets and export project drafts

## Install

```bash
pip install -e .
```

## Quick start

```python
from pathlib import Path
from jianying_draft_sdk import JianyingDraftParser

builder = JianyingDraftParser.load_encrypted(Path("path/to/draft"))
print(builder.content.keys())
```

## Package layout

- `jianying_draft_sdk.crypto`: encrypted draft file load/save and offline crypto helpers
- `jianying_draft_sdk.draft`: high-level draft builder and parser
- `jianying_draft_sdk.project_exporter`: template-based project exporter
- `jianying_draft_sdk.presets`: subtitle preset and animation helpers
- `jianying_draft_sdk.models`: draft-adjacent timeline models used by the exporter
