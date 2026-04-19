"""interference_fit_page help_ref 接入的守护测试 [Stage 4 Step E+G]."""
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.interference_fit_page import CHAPTERS, FieldSpec, InterferenceFitPage
from app.ui.widgets.help_button import HelpButton

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HELP_ROOT = PROJECT_ROOT / "docs" / "help"


EXPECTED_FIELD_HELP_REFS = {
    # checks 章节
    "checks.slip_safety_min": "terms/interference_slip_safety",
    "checks.stress_safety_min": "terms/interference_stress_safety",
    "loads.application_factor_ka": "terms/interference_application_factor_ka",
    # geometry 章节
    "geometry.shaft_d_mm": "terms/interference_fit_diameter",
    "geometry.shaft_inner_d_mm": "terms/interference_hollow_shaft_bore",
    "geometry.hub_outer_d_mm": "terms/interference_hub_outer_diameter",
    "geometry.fit_length_mm": "terms/interference_fit_length",
    "fit.mode": "terms/interference_fit_mode",
    "fit.preferred_fit_name": "terms/interference_preferred_fit",
    "fit.shaft_upper_deviation_um": "terms/interference_iso286_deviations",
    "fit.shaft_lower_deviation_um": "terms/interference_iso286_deviations",
    "fit.hub_upper_deviation_um": "terms/interference_iso286_deviations",
    "fit.hub_lower_deviation_um": "terms/interference_iso286_deviations",
    "fit.delta_min_um": "terms/interference_delta_min",
    "fit.delta_max_um": "terms/interference_delta_max",
    # materials 章节（E / ν 复用 Stage 1 通用术语）
    "materials.shaft_e_mpa": "terms/elastic_modulus",
    "materials.shaft_nu": "terms/poisson_ratio",
    "materials.shaft_yield_mpa": "terms/interference_yield_strength",
    "materials.hub_e_mpa": "terms/elastic_modulus",
    "materials.hub_nu": "terms/poisson_ratio",
    "materials.hub_yield_mpa": "terms/interference_yield_strength",
    # loads 章节
    "loads.torque_required_nm": "terms/interference_torque_required",
    "loads.axial_force_required_n": "terms/interference_axial_force_required",
    "loads.radial_force_required_n": "terms/interference_radial_force",
    "loads.bending_moment_required_nm": "terms/interference_bending_moment",
    # friction 章节（μ_T / μ_Ax 共享术语）
    "friction.mu_torque": "terms/interference_friction_coefficient",
    "friction.mu_axial": "terms/interference_friction_coefficient",
    "friction.mu_assembly": "terms/interference_assembly_mu",
    "roughness.profile": "terms/interference_roughness_profile",
    "roughness.smoothing_factor": "terms/interference_smoothing_factor_k",
    "roughness.shaft_rz_um": "terms/interference_surface_roughness_rz",
    "roughness.hub_rz_um": "terms/interference_surface_roughness_rz",
    # assembly 章节
    "assembly.method": "terms/interference_assembly_method",
    "assembly.mu_press_in": "terms/interference_assembly_mu",
    "assembly.mu_press_out": "terms/interference_assembly_mu",
    # fretting 章节
    "fretting.mode": "terms/interference_fretting_risk",
}

EXPECTED_CHAPTER_HELP_REFS = {
    "checks": "modules/interference/_section_checks",
    "geometry": "modules/interference/_section_geometry",
    "materials": "modules/interference/_section_materials",
    "loads": "modules/interference/_section_loads",
    "friction": "modules/interference/_section_friction",
    "assembly": "modules/interference/_section_assembly",
    "fretting": "modules/interference/_section_fretting",
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


def test_no_orphan_interference_term_files():
    """每个 terms/interference_*.md 至少要被一个 FieldSpec / CHAPTER 引用；孤岛术语一律视为失败。"""
    interference_term_files = sorted(HELP_ROOT.glob("terms/interference_*.md"))
    assert interference_term_files, "期望至少一篇 terms/interference_*.md 存在"

    all_refs: set[str] = set()
    for spec in _all_field_specs():
        if spec.help_ref:
            all_refs.add(spec.help_ref)
    for chapter in CHAPTERS:
        if chapter.get("help_ref"):
            all_refs.add(chapter["help_ref"])

    orphans: list[str] = []
    for md in interference_term_files:
        ref = f"terms/{md.stem}"
        if ref not in all_refs:
            orphans.append(ref)

    assert not orphans, (
        f"发现孤岛 interference 术语（写了文章但没有字段指向）：{orphans}\n"
        "请在 interference_fit_page.py 的对应 FieldSpec 加 help_ref，或删除未用术语。"
    )


def test_page_renders_with_help_buttons(qapp):
    """实例化 interference 页面并确认每个带 help_ref 的章节页都渲染了至少一个 HelpButton。"""
    page = InterferenceFitPage()
    # 每个输入章节对应 chapter_stack 的一个 widget；前面没有额外的层级页
    for offset, chapter in enumerate(CHAPTERS):
        chapter_widget = page.chapter_stack.widget(offset)
        assert chapter_widget is not None, f"chapter {chapter['id']} widget 未找到"
        help_buttons = chapter_widget.findChildren(HelpButton)
        if chapter.get("help_ref"):
            # 带 help_ref 的章节至少有 1 个 HelpButton（章节级 + 字段级）
            assert len(help_buttons) >= 1, (
                f"chapter {chapter['id']} 期望至少 1 个 HelpButton（章节级），"
                f"实际 {len(help_buttons)} 个"
            )
