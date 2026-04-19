"""bolt_page help_ref 接入的守护测试 [Stage 2 Step E+G]。"""
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_page import CHAPTERS, BoltPage, FieldSpec
from app.ui.widgets.help_button import HelpButton

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELP_ROOT = PROJECT_ROOT / "docs" / "help"


EXPECTED_FIELD_HELP_REFS = {
    # elements 章节
    "fastener.d": "terms/bolt_thread_nominal",
    "fastener.d_custom": "terms/bolt_thread_nominal",
    "fastener.p": "terms/bolt_thread_pitch",
    "fastener.p_custom": "terms/bolt_thread_pitch",
    "fastener.As": "terms/bolt_stress_area",
    "fastener.grade": "terms/bolt_grade",
    "fastener.Rp02": "terms/bolt_yield_strength",
    "tightening.mu_thread": "terms/bolt_friction_thread",
    "tightening.mu_bearing": "terms/bolt_friction_bearing",
    "bearing.p_G_allow": "terms/bolt_bearing_pressure_allowable",
    # clamped 章节
    "stiffness.E_bolt": "terms/elastic_modulus",
    "stiffness.E_clamped": "terms/elastic_modulus",
    "stiffness.auto_compliance": "terms/bolt_compliance",
    "stiffness.bolt_compliance": "terms/bolt_compliance",
    "stiffness.clamped_compliance": "terms/bolt_compliance",
    "stiffness.bolt_stiffness": "terms/bolt_compliance",
    "stiffness.clamped_stiffness": "terms/bolt_compliance",
    # assembly 章节
    "assembly.tightening_method": "terms/bolt_tightening_method",
    "tightening.alpha_A": "terms/bolt_tightening_factor_alpha_a",
    "tightening.utilization": "terms/bolt_utilization_nu",
    "loads.embed_loss": "terms/bolt_embed_loss",
    "loads.thermal_force_loss": "terms/bolt_thermal_loss",
    "loads.FM_min_input": "terms/bolt_preload_fm",
    # operating 章节
    "loads.FA_max": "terms/bolt_axial_load_fa",
    "loads.seal_force_required": "terms/bolt_seal_clamp_force",
    # introduction 章节
    "stiffness.load_introduction_factor_n": "terms/bolt_load_intro_factor",
    "checks.yield_safety_operating": "terms/bolt_yield_safety",
    # thread_strip 章节
    "thread_strip.m_eff": "terms/bolt_thread_engagement",
    "thread_strip.tau_BM": "terms/bolt_thread_strip_tau",
    "thread_strip.tau_BS": "terms/bolt_thread_strip_tau",
}

EXPECTED_CHAPTER_HELP_REFS = {
    "elements": "modules/bolt_vdi/_section_elements",
    "clamped": "modules/bolt_vdi/_section_clamped",
    "assembly": "modules/bolt_vdi/_section_assembly",
    "operating": "modules/bolt_vdi/_section_operating",
    "introduction": "modules/bolt_vdi/_section_introduction",
    "thread_strip": "modules/bolt_vdi/_section_thread_strip",
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


def test_no_orphan_bolt_vdi_term_files():
    """每个 bolt VDI 2230 术语至少要被 bolt_page.py 的 FieldSpec / CHAPTER 引用。
    注意：`bolt_tapped_axial_*.md` 不在本测试范围内 —— 它们归 bolt_tapped_axial
    模块管，由 test_bolt_tapped_axial_help_wiring 的孤岛测试保护。"""
    # 只检查真正属于 VDI 2230 模块的 bolt_* 术语（前缀是 bolt_ 但不是 bolt_tapped_axial_）
    bolt_vdi_term_files = [
        p for p in sorted(HELP_ROOT.glob("terms/bolt_*.md"))
        if not p.name.startswith("bolt_tapped_axial_")
    ]
    assert bolt_vdi_term_files, "期望至少一篇 terms/bolt_*.md 存在（非 tapped_axial）"

    all_refs: set[str] = set()
    for spec in _all_field_specs():
        if spec.help_ref:
            all_refs.add(spec.help_ref)
    for chapter in CHAPTERS:
        if chapter.get("help_ref"):
            all_refs.add(chapter["help_ref"])

    orphans: list[str] = []
    for md in bolt_vdi_term_files:
        ref = f"terms/{md.stem}"
        if ref not in all_refs:
            orphans.append(ref)

    assert not orphans, (
        f"发现孤岛 bolt VDI 2230 术语（写了文章但没有 bolt_page FieldSpec 指向）：{orphans}\n"
        "请在 bolt_page.py 的对应 FieldSpec 加 help_ref，或删除未用术语。"
    )


def test_page_renders_with_help_buttons(qapp):
    """实例化 bolt 页面并确认每个带 help_ref 的章节页都渲染了至少一个 HelpButton。"""
    page = BoltPage()
    # 每个章节对应 chapter_stack 的一个 widget（前面 1 个是校核层级页）
    for offset, chapter in enumerate(CHAPTERS, start=1):
        chapter_widget = page.chapter_stack.widget(offset)
        assert chapter_widget is not None, f"chapter {chapter['id']} widget 未找到"
        help_buttons = chapter_widget.findChildren(HelpButton)
        # 带 help_ref 的章节至少有 1 个 HelpButton（章节级）；字段级另算
        if chapter.get("help_ref"):
            assert len(help_buttons) >= 1, (
                f"chapter {chapter['id']} 期望至少 1 个 HelpButton（章节级），"
                f"实际 {len(help_buttons)} 个"
            )
