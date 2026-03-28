from jianying_draft_sdk import JianyingDraftBuilder, load_draft
from jianying_draft_sdk.project_exporter import March18ProjectExporter


def test_sdk_imports() -> None:
    assert JianyingDraftBuilder is not None
    assert load_draft is not None
    assert March18ProjectExporter is not None
