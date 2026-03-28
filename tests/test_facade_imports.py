from jianying import Jianying


def test_facade_imports() -> None:
    draft = Jianying(draft_name='demo')
    assert draft.meta['draft_name'] == 'demo'
