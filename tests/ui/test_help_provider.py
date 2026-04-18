import pytest
from pathlib import Path
from app.ui.help_provider import HelpProvider, HelpEntry


@pytest.fixture
def provider():
    root = Path(__file__).resolve().parents[2] / "docs" / "help"
    return HelpProvider(root=root)


def test_provider_loads_existing_term(provider):
    entry = provider.get("terms/_sample")
    assert isinstance(entry, HelpEntry)
    assert entry.title == "示例术语（S）"
    assert "仅供自测" in entry.body_md


def test_provider_missing_ref_returns_placeholder(provider):
    entry = provider.get("terms/does_not_exist")
    assert entry.title.startswith("帮助内容缺失")
    assert "does_not_exist" in entry.body_md


def test_provider_cache_returns_same_entry(provider):
    first = provider.get("terms/_sample")
    second = provider.get("terms/_sample")
    assert first is second  # 同对象即命中缓存
