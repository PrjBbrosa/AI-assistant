import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

from app.ui.help_provider import HelpEntry, HelpProvider, _parse, infer_category


def test_help_entry_defaults_category_source_to_none():
    entry = HelpEntry(title="T", body_md="B")
    assert entry.category is None
    assert entry.source is None


def test_parse_extracts_source_from_trailing_line():
    md = (
        "# 示例\n\n"
        "**一句话**：测试。\n\n"
        "正文。\n\n"
        "**出处**：GB/T 228.1-2010\n"
    )
    entry = _parse(md, "terms/x")
    assert entry.title == "示例"
    assert entry.source == "GB/T 228.1-2010"
    assert "**出处**" not in entry.body_md
    assert entry.body_md.endswith("正文。")


def test_parse_source_missing_leaves_none():
    md = "# 示例\n\n正文，没有出处。\n"
    entry = _parse(md, "terms/x")
    assert entry.source is None
    assert "正文" in entry.body_md


def test_parse_source_variants_cn_and_en():
    for line in ("**出处**：A", "出处：A", "**Source**: A", "Source: A"):
        md = f"# T\n\n正文。\n\n{line}\n"
        entry = _parse(md, "ref")
        assert entry.source == "A", f"failed for: {line}"


def test_infer_category_from_ref_prefixes():
    cases = {
        "terms/bolt_yield_strength": "螺栓 · 术语",
        "terms/interference_fit": "过盈 · 术语",
        "terms/hertz_pressure": "赫兹 · 术语",
        "terms/spline_pitch": "花键 · 术语",
        "terms/worm_lead_angle": "蜗轮 · 术语",
        "terms/unknown_topic": "通用 · 术语",
        "modules/bolt_vdi/chapter1": "螺栓 · 章节",
        "modules/bolt_tapped_axial/chapter1": "螺纹连接 · 章节",
        "modules/hertz/chapter1": "赫兹 · 章节",
        "modules/interference/chapter1": "过盈 · 章节",
        "modules/spline/chapter1": "花键 · 章节",
        "modules/worm/chapter1": "蜗轮 · 章节",
    }
    for ref, expected in cases.items():
        assert infer_category(ref) == expected, f"failed for ref={ref}"


def test_provider_get_populates_category_from_ref(tmp_path):
    (tmp_path / "terms").mkdir()
    (tmp_path / "terms" / "bolt_xx.md").write_text(
        "# 示例\n\n正文。\n\n**出处**：internal\n", encoding="utf-8"
    )
    provider = HelpProvider(root=tmp_path)
    entry = provider.get("terms/bolt_xx")
    assert entry.category == "螺栓 · 术语"
    assert entry.source == "internal"
