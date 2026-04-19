"""bolt_tapped_axial_page help_ref 接入的守护测试 [Stage 3 Step E+G]。"""
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_tapped_axial_page import (
    CHAPTERS,
    BoltTappedAxialPage,
    FieldSpec,
)
from app.ui.widgets.help_button import HelpButton

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELP_ROOT = PROJECT_ROOT / "docs" / "help"


EXPECTED_FIELD_HELP_REFS = {
    # fastener_material 章节
    "fastener.d": "terms/bolt_thread_nominal",
    "fastener.p": "terms/bolt_thread_pitch",
    "fastener.d2": "terms/bolt_stress_area",
    "fastener.d3": "terms/bolt_stress_area",
    "fastener.As": "terms/bolt_stress_area",
    "fastener.Rp02": "terms/bolt_yield_strength",
    "fastener.E_bolt": "terms/elastic_modulus",
    "fastener.grade": "terms/bolt_grade",
    # assembly_preload 章节
    "assembly.F_preload_min": "terms/bolt_preload_fm",
    "assembly.alpha_A": "terms/bolt_tightening_factor_alpha_a",
    "assembly.mu_thread": "terms/bolt_friction_thread",
    "assembly.mu_bearing": "terms/bolt_friction_bearing",
    "assembly.prevailing_torque": "terms/bolt_tapped_axial_prevailing_torque",
    "assembly.tightening_method": "terms/bolt_tightening_method",
    "assembly.utilization": "terms/bolt_utilization_nu",
    # axial_load 章节
    "service.FA_min": "terms/bolt_tapped_axial_axial_load_range",
    "service.FA_max": "terms/bolt_tapped_axial_axial_load_range",
    # thread_strip 章节
    "thread_strip.m_eff": "terms/bolt_thread_engagement",
    "thread_strip.tau_BM": "terms/bolt_thread_strip_tau",
    "thread_strip.tau_BS": "terms/bolt_thread_strip_tau",
    "thread_strip.safety_required": "terms/bolt_tapped_axial_strip_safety_required",
    # fatigue_output 章节
    "fatigue.load_cycles": "terms/bolt_tapped_axial_load_cycles",
    "fatigue.surface_treatment": "terms/bolt_tapped_axial_surface_treatment",
    "checks.yield_safety_operating": "terms/bolt_yield_safety",
}

EXPECTED_CHAPTER_HELP_REFS = {
    "scope": "modules/bolt_tapped_axial/_section_scope",
    "fastener_material": "modules/bolt_tapped_axial/_section_fastener_material",
    "assembly_preload": "modules/bolt_tapped_axial/_section_assembly_preload",
    "axial_load": "modules/bolt_tapped_axial/_section_axial_load",
    "thread_strip": "modules/bolt_tapped_axial/_section_thread_strip",
    "fatigue_output": "modules/bolt_tapped_axial/_section_fatigue_output",
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


def test_no_orphan_bolt_tapped_axial_term_files():
    """每个 terms/bolt_tapped_axial_*.md 至少要被一个 FieldSpec / CHAPTER 引用；孤岛术语一律视为失败。"""
    module_term_files = sorted(HELP_ROOT.glob("terms/bolt_tapped_axial_*.md"))
    assert module_term_files, "期望至少一篇 terms/bolt_tapped_axial_*.md 存在"

    all_refs: set[str] = set()
    for spec in _all_field_specs():
        if spec.help_ref:
            all_refs.add(spec.help_ref)
    for chapter in CHAPTERS:
        if chapter.get("help_ref"):
            all_refs.add(chapter["help_ref"])

    orphans: list[str] = []
    for md in module_term_files:
        ref = f"terms/{md.stem}"
        if ref not in all_refs:
            orphans.append(ref)

    assert not orphans, (
        f"发现孤岛 bolt_tapped_axial 术语（写了文章但没有字段指向）：{orphans}\n"
        "请在 bolt_tapped_axial_page.py 的对应 FieldSpec 加 help_ref，或删除未用术语。"
    )


def test_page_renders_with_help_buttons(qapp):
    """实例化 tapped_axial 页面并确认每个带 help_ref 的章节页都渲染了至少一个 HelpButton。"""
    page = BoltTappedAxialPage()
    # add_chapter 顺序和 CHAPTERS 一致；最后还有一个"校核结果"章节（不算 help_ref）
    for offset, chapter in enumerate(CHAPTERS):
        chapter_widget = page.chapter_stack.widget(offset)
        assert chapter_widget is not None, f"chapter {chapter['id']} widget 未找到"
        help_buttons = chapter_widget.findChildren(HelpButton)
        if chapter.get("help_ref"):
            assert len(help_buttons) >= 1, (
                f"chapter {chapter['id']} 期望至少 1 个 HelpButton（章节级），"
                f"实际 {len(help_buttons)} 个"
            )
