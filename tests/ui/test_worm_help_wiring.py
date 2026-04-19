"""蜗杆页 help_ref 接入的守护测试 [Task 1.5]。"""
import os

import pytest
from PySide6.QtWidgets import QApplication

# Note: the module-level list is named LOAD_CAPACITY_PARAMETER_FIELDS (not LOAD_CAPACITY_FIELDS)
from app.ui.pages.worm_gear_page import (
    ADVANCED_FIELDS,
    BASIC_SETTINGS_FIELDS,
    LOAD_CAPACITY_PARAMETER_FIELDS,
    MATERIAL_FIELDS,
    MESH_GEOMETRY_FIELDS,
    OPERATING_FIELDS,
    WHEEL_GEOMETRY_FIELDS,
    WORM_GEOMETRY_FIELDS,
    WormGearPage,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXPECTED_FIELD_HELP_REFS = {
    "load_capacity.method": "modules/worm/din3996_method_b",
    "geometry.module_mm": "terms/module",
    "geometry.diameter_factor_q": "terms/diameter_factor_q",
    "geometry.lead_angle_deg": "terms/lead_angle",
    "geometry.x1": "terms/gear_profile_shift",
    "geometry.x2": "terms/gear_profile_shift",
    "materials.lubrication": "terms/worm_lubrication_mode",
    "materials.worm_e_mpa": "terms/elastic_modulus",
    "materials.worm_nu": "terms/poisson_ratio",
    "materials.wheel_e_mpa": "terms/elastic_modulus",
    "materials.wheel_nu": "terms/poisson_ratio",
    "operating.application_factor": "terms/gear_application_factor_ka",
    "advanced.normal_pressure_angle_deg": "terms/gear_pressure_angle",
    "load_capacity.allowable_contact_stress_mpa": "terms/allowable_contact_stress",
    "load_capacity.allowable_root_stress_mpa": "terms/allowable_root_stress",
    "load_capacity.dynamic_factor_kv": "terms/kv_factor",
    "load_capacity.transverse_load_factor_kha": "terms/kh_alpha",
    "load_capacity.face_load_factor_khb": "terms/kh_beta",
}


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _all_specs():
    return (
        BASIC_SETTINGS_FIELDS
        + WORM_GEOMETRY_FIELDS
        + WHEEL_GEOMETRY_FIELDS
        + MESH_GEOMETRY_FIELDS
        + MATERIAL_FIELDS
        + OPERATING_FIELDS
        + ADVANCED_FIELDS
        + LOAD_CAPACITY_PARAMETER_FIELDS
    )


@pytest.mark.parametrize("field_id,expected_ref", EXPECTED_FIELD_HELP_REFS.items())
def test_field_has_expected_help_ref(field_id, expected_ref):
    specs = {s.field_id: s for s in _all_specs()}
    assert field_id in specs, f"FieldSpec {field_id} not found in module"
    assert specs[field_id].help_ref == expected_ref, (
        f"field {field_id}: expected help_ref={expected_ref!r}, "
        f"got {specs[field_id].help_ref!r}"
    )


def test_non_help_fields_have_empty_help_ref():
    """All fields not in the explicit mapping should have help_ref == ''."""
    for s in _all_specs():
        if s.field_id in EXPECTED_FIELD_HELP_REFS:
            continue
        assert s.help_ref == "", (
            f"field {s.field_id} has unexpected help_ref={s.help_ref!r}"
        )


def test_chapter_titles_with_help_ref(qapp):
    """Instantiate page; verify chapters that should have help_ref produce a wrapper."""
    page = WormGearPage()
    expected_with_help = {
        "基本设置": "modules/worm/_section_basic",
        "几何参数": "modules/worm/_section_geometry",
        "材料与配对": "modules/worm/_section_material",
        "工况与润滑": "modules/worm/_section_operating",
        "Load Capacity": "modules/worm/_section_load_capacity",
    }
    # Collect (index, stripped_title) pairs from the chapter list
    titles_in_order = []
    for i in range(page.chapter_list.count()):
        text = page.chapter_list.item(i).text()
        # Strip "步骤 N. " prefix
        stripped = text.split(". ", 1)[1] if ". " in text else text
        titles_in_order.append((i, stripped))

    # For each chapter that expects a help_ref wrapper, confirm container != page
    for i, t in titles_in_order:
        if t in expected_with_help:
            original_page = page.chapter_page_at(i)
            container = page.chapter_container_at(i)
            assert container is not original_page, (
                f"chapter '{t}' at index {i} should be wrapped by help_ref "
                f"but container is the same object as the page"
            )
        elif t in ("图形与曲线", "结果与报告"):
            # These chapters have no help_ref; container == page
            original_page = page.chapter_page_at(i)
            container = page.chapter_container_at(i)
            assert container is original_page, (
                f"chapter '{t}' at index {i} should NOT be wrapped "
                f"but container differs from page"
            )
