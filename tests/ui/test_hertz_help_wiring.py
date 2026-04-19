"""hertz_contact_page help_ref 接入的守护测试 [Stage 5 Step E+G]。"""
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.hertz_contact_page import CHAPTERS, FieldSpec, HertzContactPage
from app.ui.widgets.help_button import HelpButton

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELP_ROOT = PROJECT_ROOT / "docs" / "help"


EXPECTED_FIELD_HELP_REFS = {
    # checks 章节
    "checks.allowable_p0_mpa": "terms/hertz_allowable_pressure",
    "options.curve_points": "terms/hertz_curve_sampling",
    "options.curve_force_scale": "terms/hertz_curve_sampling",
    # geometry 章节
    "geometry.contact_mode": "terms/hertz_contact_mode",
    "geometry.r1_mm": "terms/hertz_curvature_radius",
    "geometry.r2_mm": "terms/hertz_curvature_radius",
    "geometry.length_mm": "terms/hertz_contact_length",
    # materials 章节（复用 elastic_modulus / poisson_ratio）
    "materials.e1_mpa": "terms/elastic_modulus",
    "materials.nu1": "terms/poisson_ratio",
    "materials.e2_mpa": "terms/elastic_modulus",
    "materials.nu2": "terms/poisson_ratio",
}

EXPECTED_CHAPTER_HELP_REFS = {
    "checks": "modules/hertz/_section_checks",
    "geometry": "modules/hertz/_section_geometry",
    "materials": "modules/hertz/_section_materials",
    "loads": "modules/hertz/_section_loads",
}


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _all_field_specs() -> list[FieldSpec]:
    result: list[FieldSpec] = []
    for chapter in CHAPTERS:
        result.extend(chapter["fields"])
    return result


@pytest.mark.parametrize("field_id,expected_ref", EXPECTED_FIELD_HELP_REFS.items())
def test_field_has_expected_help_ref(field_id, expected_ref):
    specs = {s.field_id: s for s in _all_field_specs()}
    assert field_id in specs, f"FieldSpec {field_id} not found in CHAPTERS"
    assert specs[field_id].help_ref == expected_ref, (
        f"field {field_id}: expected help_ref={expected_ref!r}, "
        f"got {specs[field_id].help_ref!r}"
    )


@pytest.mark.parametrize("chapter_id,expected_ref", EXPECTED_CHAPTER_HELP_REFS.items())
def test_chapter_has_expected_help_ref(chapter_id, expected_ref):
    chapters_by_id = {c["id"]: c for c in CHAPTERS}
    assert chapter_id in chapters_by_id, f"chapter {chapter_id} not found"
    assert chapters_by_id[chapter_id].get("help_ref") == expected_ref, (
        f"chapter {chapter_id}: expected help_ref={expected_ref!r}, "
        f"got {chapters_by_id[chapter_id].get('help_ref')!r}"
    )


def test_all_field_help_refs_point_to_existing_markdown():
    """每个 help_ref 指向的 md 文件必须真实存在。"""
    for spec in _all_field_specs():
        if not spec.help_ref:
            continue
        target = HELP_ROOT / f"{spec.help_ref}.md"
        assert target.exists(), (
            f"field {spec.field_id} 指向 help_ref={spec.help_ref!r}，"
            f"但 {target} 不存在"
        )


def test_all_chapter_help_refs_point_to_existing_markdown():
    for chapter in CHAPTERS:
        ref = chapter.get("help_ref", "")
        if not ref:
            continue
        target = HELP_ROOT / f"{ref}.md"
        assert target.exists(), (
            f"chapter {chapter['id']} 指向 help_ref={ref!r}，但 {target} 不存在"
        )


def test_no_orphan_hertz_term_files():
    """每个 terms/hertz_*.md 至少要被一个 FieldSpec / CHAPTER / 其他帮助 md 引用；孤岛术语视为失败。

    对 hertz 模块，derived-value 术语（E' / R' / p0 / S）没有对应输入字段，只在
    section / overview md 里以 "进一步阅读" 或公式说明形式出现。允许这类交叉引用抵
    消孤岛，避免为"只存在于派生结果"的术语被迫新增假字段。
    """
    hertz_term_files = sorted(HELP_ROOT.glob("terms/hertz_*.md"))
    assert hertz_term_files, "期望至少一篇 terms/hertz_*.md 存在"

    all_refs: set[str] = set()
    for spec in _all_field_specs():
        if spec.help_ref:
            all_refs.add(spec.help_ref)
    for chapter in CHAPTERS:
        if chapter.get("help_ref"):
            all_refs.add(chapter["help_ref"])

    # 额外：从所有非自身的 help md 文件内容里提取 `terms/xxx` 引用
    cross_refs: set[str] = set()
    for md in HELP_ROOT.rglob("*.md"):
        if md.name.startswith("hertz_") and md.parent.name == "terms":
            # 允许 hertz 术语之间互相引用；但不允许术语只被自己引用
            continue
        text = md.read_text(encoding="utf-8")
        # 简单匹配 `terms/hertz_xxx` 形式
        import re
        for m in re.finditer(r"terms/(hertz_[a-z_]+)", text):
            cross_refs.add(f"terms/{m.group(1)}")

    orphans: list[str] = []
    for md in hertz_term_files:
        ref = f"terms/{md.stem}"
        if ref not in all_refs and ref not in cross_refs:
            orphans.append(ref)

    assert not orphans, (
        f"发现孤岛 hertz 术语（写了文章但没有字段 / 章节 / 其他 md 指向）：{orphans}\n"
        "请在 hertz_contact_page.py 的对应 FieldSpec 加 help_ref，"
        "或在 section / overview md 中添加交叉引用，或删除未用术语。"
    )


def test_page_renders_with_help_buttons(qapp):
    """实例化 hertz 页面并确认每个带 help_ref 的输入章节都渲染了至少一个 HelpButton。"""
    page = HertzContactPage()
    # chapter_stack 的索引：0..len(CHAPTERS)-1 是 4 个输入章节；之后是图示章节 + 结果章节
    for idx, chapter in enumerate(CHAPTERS):
        chapter_widget = page.chapter_stack.widget(idx)
        assert chapter_widget is not None, f"chapter {chapter['id']} widget 未找到"
        help_buttons = chapter_widget.findChildren(HelpButton)
        if chapter.get("help_ref"):
            # 章节级 HelpButton (1) + 该章节所有带 help_ref 的字段
            field_help_count = sum(1 for f in chapter["fields"] if f.help_ref)
            expected_min = 1 + field_help_count
            assert len(help_buttons) >= expected_min, (
                f"chapter {chapter['id']} 期望至少 {expected_min} 个 HelpButton "
                f"（章节 1 + 字段 {field_help_count}），实际 {len(help_buttons)} 个"
            )
