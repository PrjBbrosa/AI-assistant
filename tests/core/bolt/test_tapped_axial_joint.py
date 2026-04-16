"""Tapped axial threaded joint core calculator tests."""

import pytest

import core.bolt as bolt
from core.bolt import InputError


def _base_input() -> dict:
    return {
        "fastener": {
            "d": 12.0,
            "p": 1.75,
            "Rp02": 940.0,
        },
        "assembly": {
            "F_preload_min": 18_000.0,
            "alpha_A": 1.5,
            "mu_thread": 0.10,
            "mu_bearing": 0.12,
            "bearing_d_inner": 13.0,
            "bearing_d_outer": 22.0,
            "prevailing_torque": 0.0,
            "thread_flank_angle_deg": 60.0,
            "tightening_method": "torque",
            "utilization": 0.85,
        },
        "service": {
            "FA_min": 0.0,
            "FA_max": 6_000.0,
        },
        "fatigue": {
            "load_cycles": 2_000_000.0,
            "surface_treatment": "rolled",
        },
        "thread_strip": {
            "tau_BM": 180.0,
            "safety_required": 1.25,
        },
        "checks": {
            "yield_safety_operating": 1.15,
        },
        "options": {
            "report_mode": "full",
        },
    }


def test_returns_stable_result_shape_for_basic_case():
    result = bolt.calculate_tapped_axial_joint(_base_input())

    assert result["model_type"] == "tapped_axial_threaded_joint"
    assert "assembly" in result
    assert "derived_geometry" in result
    assert "forces" in result
    assert "stresses_mpa" in result
    assert "fatigue" in result
    assert "thread_strip" in result
    assert "checks" in result
    assert "trace" in result
    assert "warnings" in result
    assert "recommendations" in result
    assert "scope_note" in result

    assert result["assembly"]["tightening_method"] == "torque"
    assert result["derived_geometry"]["As_mm2"] > 0
    assert "F_preload_max_N" in result["assembly"]
    assert "sigma_vm_service_max" in result["stresses_mpa"]
    assert "thread_strip_ok" in result["checks"]
    assert result["thread_strip"]["active"] is False
    assert result["checks"]["thread_strip_ok"] is True
    assert isinstance(result["warnings"], list)
    assert isinstance(result["recommendations"], list)
    assert "cycle_factor" in result["trace"]["intermediate"]
    assert "无被夹件" in result["scope_note"]


def test_torque_tightening_keeps_residual_torsion_in_service():
    data = _base_input()
    data["assembly"]["tightening_method"] = "torque"

    result = bolt.calculate_tapped_axial_joint(data)

    assert (
        result["stresses_mpa"]["sigma_vm_service_max"]
        >= result["stresses_mpa"]["sigma_ax_service_max"]
    )


def test_non_torque_tightening_releases_service_torsion():
    data = _base_input()
    data["assembly"]["tightening_method"] = "angle"

    result = bolt.calculate_tapped_axial_joint(data)

    assert abs(
        result["stresses_mpa"]["sigma_vm_service_max"]
        - result["stresses_mpa"]["sigma_ax_service_max"]
    ) < 1e-6


def test_fatigue_uses_fa_min_and_fa_max_to_build_mean_and_amplitude():
    data = _base_input()
    data["service"]["FA_min"] = 2_000.0
    data["service"]["FA_max"] = 8_000.0

    result = bolt.calculate_tapped_axial_joint(data)

    assert result["forces"]["F_amplitude_N"] == 3_000.0
    assert result["forces"]["F_mean_N"] == result["assembly"]["F_preload_max_N"] + 5_000.0


def test_thread_strip_uses_service_max_force():
    data = _base_input()
    data["thread_strip"]["m_eff"] = 2.0

    result = bolt.calculate_tapped_axial_joint(data)

    assert result["thread_strip"]["active"] is True
    assert result["thread_strip"]["critical_side"] in {"bolt", "counterpart"}
    assert (
        result["thread_strip"]["F_bolt_max_N"]
        == result["assembly"]["F_preload_max_N"] + data["service"]["FA_max"]
    )


@pytest.mark.parametrize(
    ("fa_min", "fa_max"),
    [
        (-1.0, 6_000.0),
        (7_000.0, 6_000.0),
    ],
)
def test_fa_range_rejects_negative_or_descending_values(fa_min: float, fa_max: float):
    data = _base_input()
    data["service"]["FA_min"] = fa_min
    data["service"]["FA_max"] = fa_max

    with pytest.raises(InputError):
        bolt.calculate_tapped_axial_joint(data)


def test_fatigue_limit_rolled_m12_interpolated():
    """VDI 2230-1 Table A4: d=12mm, rolled -> sigma_ASV = 41 MPa."""
    data = _base_input()
    data["service"]["FA_min"] = 0.0
    data["service"]["FA_max"] = 100.0
    data["fatigue"]["load_cycles"] = 2_000_000.0
    data["fatigue"]["surface_treatment"] = "rolled"
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["fatigue"]["sigma_ASV"] == pytest.approx(41.0, rel=1e-3)


def test_fatigue_limit_cut_m12():
    """VDI 2230-1 Table A4: d=12mm, cut -> sigma_ASV = 41 * 0.65 = 26.65 MPa."""
    data = _base_input()
    data["service"]["FA_min"] = 0.0
    data["service"]["FA_max"] = 100.0
    data["fatigue"]["load_cycles"] = 2_000_000.0
    data["fatigue"]["surface_treatment"] = "cut"
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["fatigue"]["sigma_ASV"] == pytest.approx(26.65, rel=1e-3)


def test_cycle_factor_below_2e6_applies_correction():
    """load_cycles < 2e6 -> cycle_factor = (2e6/N)^0.08 > 1."""
    data = _base_input()
    data["fatigue"]["load_cycles"] = 1_000_000.0
    result = bolt.calculate_tapped_axial_joint(data)
    cf = result["trace"]["intermediate"]["cycle_factor"]
    expected = (2_000_000.0 / 1_000_000.0) ** 0.08
    assert cf == pytest.approx(expected, rel=1e-4)
    assert cf > 1.0


def test_cycle_factor_at_2e6_equals_one():
    """load_cycles >= 2e6 -> cycle_factor = 1.0."""
    data = _base_input()
    data["fatigue"]["load_cycles"] = 2_000_000.0
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["trace"]["intermediate"]["cycle_factor"] == 1.0


def test_static_load_fa_min_equals_fa_max_amplitude_zero():
    """FA_min == FA_max -> F_amplitude = 0 (纯静载)."""
    data = _base_input()
    data["service"]["FA_min"] = 5000.0
    data["service"]["FA_max"] = 5000.0
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["forces"]["F_amplitude_N"] == 0.0
    assert result["stresses_mpa"]["sigma_a_fatigue"] == 0.0
    assert result["checks"]["fatigue_ok"] is True


def test_assembly_failure_high_preload():
    """极高预紧力导致装配不通过."""
    data = _base_input()
    data["assembly"]["F_preload_min"] = 80_000.0
    data["assembly"]["alpha_A"] = 1.8
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["checks"]["assembly_von_mises_ok"] is False
    assert result["overall_pass"] is False
    assert any("装配" in r for r in result["recommendations"])


def test_thread_strip_inactive_returns_fixed_shape():
    """未提供 m_eff 时，脱扣返回固定 shape 且 overall_pass 不受影响."""
    data = _base_input()
    result = bolt.calculate_tapped_axial_joint(data)
    ts = result["thread_strip"]
    assert ts["active"] is False
    assert ts["check_passed"] is True
    assert ts["A_SB_mm2"] == 0.0
    assert ts["critical_side"] == ""
    assert "未提供 m_eff" in ts["note"]
    assert result["checks"]["thread_strip_ok"] is True


def test_high_mean_stress_fails_fatigue_low_goodman():
    """高平均应力场景：原始 Goodman 因子 < 0.1 时疲劳必须按真实许用判定，不能被人为抬高到 0.1。

    复现 Codex 2026-04-16 adversarial review §3.1：此前代码使用
    ``goodman_factor = max(0.1, ...)`` 会在高平均应力下把许用应力幅抬升约 8 倍，
    让本该不通过的疲劳场景被误判为 PASS。

    用例构造：d=10, p=1.5, Rp02=640, F_preload_min=33 kN, angle 法，μ=0.05。
    实际 σ_m/(0.9·Rp02) ≈ 0.988，goodman_factor_raw ≈ 0.012（正但 < 0.1）。
    σ_a 落在 [σ_asv·0.012, σ_asv·0.1] 区间（约 [0.52, 4.4] MPa），
    原代码 PASS，修复后 FAIL。
    """
    data = _base_input()
    data["fastener"].update({"d": 10.0, "p": 1.5, "Rp02": 640.0})
    data["assembly"].update(
        {
            "tightening_method": "angle",
            "mu_thread": 0.05,
            "mu_bearing": 0.05,
            "alpha_A": 1.0,
            "F_preload_min": 33_000.0,
        }
    )
    # FA_max=200 → σ_a ≈ 1.72 MPa，落在新旧许用之间
    data["service"].update({"FA_min": 0.0, "FA_max": 200.0})

    result = bolt.calculate_tapped_axial_joint(data)

    raw = result["fatigue"].get("goodman_factor_raw")
    assert raw is not None, "goodman_factor_raw 必须出现在 result['fatigue'] 中"
    assert 0.0 < raw < 0.1, (
        f"期望 0 < raw < 0.1 以验证旧 max(0.1,...) 下限生效的场景，实际 raw={raw}"
    )
    assert result["fatigue"]["goodman_factor"] == pytest.approx(raw), (
        "正数 raw 应原样保留为 goodman_factor，不应被 clamp。"
    )
    assert result["checks"]["fatigue_ok"] is False, (
        "σ_a 超出真实许用 (σ_asv · raw) 时疲劳必须不通过；"
        "此前 max(0.1, raw) 会把许用抬高到 σ_asv · 0.1 造成非保守 PASS。"
    )
    assert any(
        "Goodman" in w or "疲劳" in w for w in result["warnings"]
    ), f"Expected Goodman/疲劳 warning, got: {result['warnings']}"


def test_mean_stress_beyond_goodman_limit_forces_zero_factor():
    """σ_m >= 0.9·Rp0.2 时 goodman_factor_raw <= 0，clamp 到 0 并直接判疲劳不通过。"""
    data = _base_input()
    data["fastener"].update({"d": 10.0, "p": 1.5, "Rp02": 640.0})
    data["assembly"].update(
        {
            "tightening_method": "angle",
            "mu_thread": 0.05,
            "mu_bearing": 0.05,
            "alpha_A": 1.0,
            "F_preload_min": 40_000.0,  # 让 σ_m > 0.9·Rp02
        }
    )
    data["service"].update({"FA_min": 0.0, "FA_max": 10.0})

    result = bolt.calculate_tapped_axial_joint(data)

    assert result["fatigue"]["goodman_factor_raw"] <= 0.0
    assert result["fatigue"]["goodman_factor"] == 0.0, (
        "raw <= 0 时 goodman_factor 应 clamp 为 0（而非 0.1 或负数）。"
    )
    assert result["checks"]["fatigue_ok"] is False
    assert any(
        "Goodman" in w for w in result["warnings"]
    ), f"Expected Goodman warning, got: {result['warnings']}"
