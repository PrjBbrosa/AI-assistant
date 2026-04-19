"""spline_fit_page help_ref 接入的守护测试 [Stage 6 Step G]。

按 Stage 2 bolt 的双向守护测试模式：
1. EXPECTED_FIELD_HELP_REFS / EXPECTED_CHAPTER_HELP_REFS —— 正向断言
2. test_all_*_help_refs_point_to_existing_markdown —— 每个 help_ref 指向的 md 必须存在
3. test_no_orphan_spline_term_files —— 反向守卫：每个 terms/spline_*.md 必须被某字段/章节引用
"""

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.spline_fit_page import CHAPTERS, FieldSpec, SplineFitPage
from app.ui.widgets.help_button import HelpButton

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELP_ROOT = PROJECT_ROOT / "docs" / "help"


# 字段级 help_ref 正向断言（覆盖所有带 help_ref 的 FieldSpec）
EXPECTED_FIELD_HELP_REFS = {
    # 校核目标章节
    "mode": "terms/spline_mode",
    "checks.flank_safety_min": "terms/spline_flank_safety",
    "checks.slip_safety_min": "terms/spline_slip_safety",
    "checks.stress_safety_min": "terms/spline_stress_safety",
    "loads.application_factor_ka": "terms/spline_application_factor_ka",
    # 花键几何章节
    "spline.standard_designation": "terms/spline_din5480_spec",
    "spline.geometry_mode": "terms/spline_geometry_mode",
    "spline.module_mm": "terms/module",
    "spline.tooth_count": "terms/spline_tooth_count",
    "spline.reference_diameter_mm": "terms/spline_reference_diameter",
    "spline.tip_diameter_shaft_mm": "terms/spline_tip_root_diameter",
    "spline.root_diameter_shaft_mm": "terms/spline_tip_root_diameter",
    "spline.tip_diameter_hub_mm": "terms/spline_tip_root_diameter",
    "spline.engagement_length_mm": "terms/spline_engagement_length",
    "spline.k_alpha": "terms/spline_k_alpha",
    "spline.load_condition": "terms/spline_load_condition",
    "spline.p_allowable_mpa": "terms/spline_allowable_flank_pressure",
    # 光滑段过盈章节
    "smooth_fit.relief_groove_width_mm": "terms/spline_relief_groove",
    "smooth_fit.delta_min_um": "terms/spline_smooth_interference",
    "smooth_fit.delta_max_um": "terms/spline_smooth_interference",
    "smooth_materials.shaft_e_mpa": "terms/elastic_modulus",
    "smooth_materials.shaft_nu": "terms/poisson_ratio",
    "smooth_materials.shaft_yield_mpa": "terms/spline_smooth_yield_strength",
    "smooth_materials.hub_e_mpa": "terms/elastic_modulus",
    "smooth_materials.hub_nu": "terms/poisson_ratio",
    "smooth_materials.hub_yield_mpa": "terms/spline_smooth_yield_strength",
    "smooth_friction.mu_torque": "terms/spline_smooth_friction",
    "smooth_friction.mu_axial": "terms/spline_smooth_friction",
    "smooth_friction.mu_assembly": "terms/spline_smooth_friction",
}

EXPECTED_CHAPTER_HELP_REFS = {
    "targets": "modules/spline/_section_targets",
    "geometry": "modules/spline/_section_geometry",
    "smooth": "modules/spline/_section_smooth",
    "loads": "modules/spline/_section_loads",
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
    chapters_by_id = {c["id"]: c for c in CHAPTERS if "id" in c}
    assert chapter_id in chapters_by_id, f"chapter {chapter_id} not found"
    assert chapters_by_id[chapter_id].get("help_ref") == expected_ref, (
        f"chapter {chapter_id}: expected help_ref={expected_ref!r}, "
        f"got {chapters_by_id[chapter_id].get('help_ref')!r}"
    )


def test_all_field_help_refs_point_to_existing_markdown():
    """每个 FieldSpec.help_ref 指向的 md 必须真实存在。"""
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
            f"chapter {chapter.get('id', chapter['title'])} 指向 help_ref={ref!r}，"
            f"但 {target} 不存在"
        )


def test_no_orphan_spline_term_files():
    """每个 terms/spline_*.md 至少要被一个 FieldSpec / CHAPTER 引用；孤岛术语一律视为失败。"""
    spline_term_files = sorted(HELP_ROOT.glob("terms/spline_*.md"))
    assert spline_term_files, "期望至少一篇 terms/spline_*.md 存在"

    all_refs: set[str] = set()
    for spec in _all_field_specs():
        if spec.help_ref:
            all_refs.add(spec.help_ref)
    for chapter in CHAPTERS:
        if chapter.get("help_ref"):
            all_refs.add(chapter["help_ref"])

    orphans: list[str] = []
    for md in spline_term_files:
        ref = f"terms/{md.stem}"
        if ref not in all_refs:
            orphans.append(ref)

    assert not orphans, (
        f"发现孤岛 spline 术语（写了文章但没有字段指向）：{orphans}\n"
        "请在 spline_fit_page.py 的对应 FieldSpec 加 help_ref，或删除未用术语。"
    )


def test_page_renders_with_help_buttons(qapp):
    """实例化 spline 页面并确认每个带 help_ref 的章节页都渲染了至少一个 HelpButton。"""
    page = SplineFitPage()
    # 每个章节对应 chapter_stack 的一个 widget
    for idx, chapter in enumerate(CHAPTERS):
        chapter_widget = page.chapter_stack.widget(idx)
        assert chapter_widget is not None, (
            f"chapter {chapter.get('id', chapter['title'])} widget 未找到"
        )
        help_buttons = chapter_widget.findChildren(HelpButton)
        if chapter.get("help_ref"):
            # 带章节级 help_ref 的章节至少有 1 个 HelpButton（章节级）；字段级另计
            assert len(help_buttons) >= 1, (
                f"chapter {chapter.get('id', chapter['title'])} "
                f"期望至少 1 个 HelpButton（章节级），实际 {len(help_buttons)} 个"
            )
