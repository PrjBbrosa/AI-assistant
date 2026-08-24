"""Source-origin contract for normalized engineering verdict rows."""

from __future__ import annotations

import pytest

from app.ui.result_contract import (
    from_buffer,
    from_interference,
    from_tapped_axial,
    from_worm,
)


def _checks_by_id(view):
    return {check.id: check for check in view.checks}


def test_worm_uses_effective_derived_stress_limits_and_reference_life() -> None:
    result = {
        "overall_status": "pass",
        "geometry": {},
        "performance": {},
        "load_capacity": {
            "enabled": True,
            "checks": {
                "geometry_consistent": True,
                "contact_ok": True,
                "root_ok": True,
            },
            "contact": {
                "sigma_hm_peak_mpa": 70.0,
                "allowable_contact_stress_mpa": 100.0,
                "required_contact_safety": 1.25,
            },
            "root": {
                "sigma_f_peak_mpa": 35.0,
                "allowable_root_stress_mpa": 60.0,
                "required_root_safety": 1.5,
            },
            "life": {
                "fatigue_life_hours": 20_000.0,
                "wear_life_hours_until_0p3mm": 12_000.0,
            },
        },
    }

    payload = {
        "materials": {"wheel_material": "PA66"},
        "advanced": {"operating_temp_c": 23.0, "humidity_rh": 0.0},
        "load_capacity": {
            "allowable_contact_stress_mpa": 100.0,
            "allowable_root_stress_mpa": 60.0,
        },
    }
    view = from_worm(result, payload)
    checks = _checks_by_id(view)

    assert checks["geometry_consistent"].source_kind == "derived"
    assert checks["contact_ok"].actual == pytest.approx(70.0)
    assert checks["contact_ok"].limit == pytest.approx(80.0)
    assert checks["contact_ok"].source_kind == "derived"
    assert checks["root_ok"].limit == pytest.approx(40.0)
    assert checks["root_ok"].source_kind == "derived"
    assert checks["fatigue_life"].source_kind == "reference"
    assert checks["wear_life"].source_kind == "reference"
    assert any("显式覆盖值" in note and "用户输入" in note for note in view.source_notes)


def test_worm_source_notes_recognize_material_temperature_humidity_derivation() -> None:
    result = {
        "geometry": {},
        "performance": {},
        "load_capacity": {
            "enabled": True,
            "overall_status": "pass",
            "overall_pass": True,
            "checks": {},
            "contact": {"allowable_contact_stress_mpa": 42.0},
            "root": {"allowable_root_stress_mpa": 55.0},
        },
    }
    payload = {
        "materials": {"wheel_material": "PA66"},
        "advanced": {"operating_temp_c": 23.0, "humidity_rh": 0.0},
        "load_capacity": {
            "allowable_contact_stress_mpa": 42.0,
            "allowable_root_stress_mpa": 55.0,
        },
    }

    view = from_worm(result, payload)

    assert any(
        "材料预设 PA66" in note and "温度/湿度派生" in note
        for note in view.source_notes
    )


def test_worm_source_notes_recognize_nonplastic_allowable_hint(monkeypatch) -> None:
    from core.worm.calculator import MATERIAL_ALLOWABLE_HINTS

    monkeypatch.setitem(
        MATERIAL_ALLOWABLE_HINTS,
        "锡青铜",
        {"contact_mpa": 135.0, "root_mpa": 72.0},
    )
    result = {
        "geometry": {},
        "performance": {},
        "load_capacity": {
            "enabled": True,
            "overall_status": "pass",
            "overall_pass": True,
            "checks": {},
            "contact": {"allowable_contact_stress_mpa": 135.0},
            "root": {"allowable_root_stress_mpa": 72.0},
        },
    }
    payload = {
        "materials": {"wheel_material": "锡青铜"},
        "advanced": {"operating_temp_c": 80.0, "humidity_rh": 80.0},
        "load_capacity": {
            "allowable_contact_stress_mpa": 135.0,
            "allowable_root_stress_mpa": 72.0,
        },
    }

    view = from_worm(result, payload)

    assert any("来自材料预设 锡青铜" in note for note in view.source_notes)
    assert not any("显式覆盖值" in note for note in view.source_notes)


def test_worm_load_capacity_incomplete_status_overrides_legacy_boolean() -> None:
    result = {
        "geometry": {},
        "performance": {},
        "load_capacity": {
            "enabled": True,
            "overall_status": "incomplete",
            "overall_pass": False,
            "checks": {"geometry_consistent": True, "contact_ok": True, "root_ok": True},
        },
    }

    view = from_worm(result)

    assert view.overall_status == "incomplete"
    assert view.title_zh.startswith("校核不完整")
    assert "超出可信域" in view.summary_zh
    assert "满足" not in view.summary_zh


def test_interference_distinguishes_user_thresholds_from_derived_criteria() -> None:
    result = {
        "overall_pass": True,
        "checks": {
            "torque_ok": True,
            "axial_ok": True,
            "combined_ok": True,
            "gaping_ok": True,
            "fit_range_ok": True,
            "shaft_stress_ok": True,
            "hub_stress_ok": True,
        },
        "model": {"shaft_type": "solid_shaft"},
        "safety": {
            "torque_sf": 1.6,
            "axial_sf": 2.0,
            "combined_sf": 1.4,
            "gaping_margin_mpa": 5.0,
            "shaft_sf": 2.3,
            "hub_sf": 2.1,
            "slip_safety_min": 1.2,
            "stress_safety_min": 1.2,
        },
        "required": {"delta_required_um": 22.0},
    }
    payload = {
        "checks": {"slip_safety_min": 1.3, "stress_safety_min": 1.4},
        "fit": {"delta_max_um": 60.0},
    }

    view = from_interference(result, payload)
    checks = _checks_by_id(view)

    assert checks["torque_ok"].limit == pytest.approx(1.3)
    assert checks["torque_ok"].source_kind == "user"
    assert checks["gaping_ok"].actual == pytest.approx(5.0)
    assert checks["gaping_ok"].limit == pytest.approx(0.0)
    assert checks["gaping_ok"].source_kind == "derived"
    assert checks["fit_range_ok"].actual == pytest.approx(60.0)
    assert checks["fit_range_ok"].limit == pytest.approx(22.0)
    assert checks["fit_range_ok"].unit == "um"
    assert checks["fit_range_ok"].source_kind == "derived"
    assert any("K_A" in note and "模型派生" in note for note in view.source_notes)


def test_interference_fit_range_failure_recommends_more_available_interference() -> None:
    result = {
        "overall_pass": False,
        "checks": {
            "torque_ok": True,
            "axial_ok": True,
            "combined_ok": True,
            "gaping_ok": True,
            "fit_range_ok": False,
            "shaft_stress_ok": True,
            "hub_stress_ok": True,
        },
        "model": {},
        "safety": {},
        "required": {"delta_required_um": 80.0},
    }
    payload = {"fit": {"delta_max_um": 60.0}}

    view = from_interference(result, payload)

    recommendation = next(item for item in view.recommendations if "过盈覆盖需求" in item)
    assert "最大可用过盈小于" in recommendation
    assert "增大最大可用过盈" in recommendation
    assert "缩小过盈公差带" not in recommendation


def test_tapped_axial_marks_strength_limits_derived_and_user_gate_explicitly() -> None:
    result = {
        "overall_status": "pass",
        "checks": {
            "assembly_von_mises_ok": True,
            "service_von_mises_ok": True,
            "fatigue_ok": True,
            "thread_strip_ok": True,
        },
        "stresses_mpa": {
            "sigma_vm_assembly": 500.0,
            "sigma_vm_service_max": 520.0,
            "sigma_a_fatigue": 30.0,
        },
        "fatigue": {"sigma_a_allow": 45.0},
        "trace": {
            "intermediate": {
                "sigma_allow_assembly": 576.0,
                "sigma_allow_service": 581.8,
            }
        },
        "thread_strip": {
            "active": True,
            "strip_safety": 1.7,
            "strip_safety_required": 1.25,
        },
    }
    payload = {"fastener": {"grade": "8.8", "Rp02": 640.0}}

    view = from_tapped_axial(result, payload)
    checks = _checks_by_id(view)

    for check_id in (
        "assembly_von_mises_ok",
        "service_von_mises_ok",
        "fatigue_ok",
    ):
        assert checks[check_id].source_kind == "derived"
    assert checks["thread_strip_ok"].source_kind == "user"
    assert any("预设强度等级 8.8" in note for note in view.source_notes)
    assert any("模型公式派生" in note for note in view.source_notes)


def test_buffer_exposes_user_limits_and_curve_derived_energy_capacity() -> None:
    result = {
        "overall_pass": True,
        "checks": {
            "stroke_ok": True,
            "peak_force_ok": True,
            "energy_capacity_ok": True,
        },
        "impact": {
            "max_compression_mm": 18.0,
            "peak_force_n": 7_500.0,
            "initial_energy_j": 120.0,
            "available_energy_capacity_j": 150.0,
            "bottom_out": False,
        },
        "curve_summary": {},
    }
    payload = {
        "impact": {
            "available_stroke_mm": 20.0,
            "allowable_peak_force_n": 8_000.0,
        }
    }

    view = from_buffer(result, payload)
    checks = _checks_by_id(view)

    assert checks["stroke_ok"].actual == pytest.approx(18.0)
    assert checks["stroke_ok"].limit == pytest.approx(20.0)
    assert checks["stroke_ok"].source_kind == "user"
    assert checks["peak_force_ok"].actual == pytest.approx(7_500.0)
    assert checks["peak_force_ok"].limit == pytest.approx(8_000.0)
    assert checks["peak_force_ok"].source_kind == "user"
    assert checks["energy_capacity_ok"].actual == pytest.approx(120.0)
    assert checks["energy_capacity_ok"].limit == pytest.approx(150.0)
    assert checks["energy_capacity_ok"].source_kind == "derived"
    assert any("导入测试曲线" in note for note in view.source_notes)
