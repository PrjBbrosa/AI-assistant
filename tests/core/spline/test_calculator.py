"""Tests for spline scenario A: tooth-flank bearing stress check."""
import math
import pytest
from core.spline.calculator import (
    InputError,
    calculate_spline_fit,
)


def make_scenario_a_case() -> dict:
    """Scenario A: involute spline tooth flank interference only."""
    return {
        "mode": "spline_only",
        "spline": {
            "module_mm": 2.0,
            "tooth_count": 20,
            "engagement_length_mm": 30.0,
            "k_alpha": 1.0,
            "p_allowable_mpa": 100.0,
        },
        "loads": {
            "torque_required_nm": 500.0,
            "application_factor_ka": 1.25,
        },
        "checks": {
            "flank_safety_min": 1.3,
        },
    }


class TestScenarioA:
    def test_nominal_case_passes(self):
        result = calculate_spline_fit(make_scenario_a_case())
        assert result["scenario_a"]["flank_pressure_mpa"] > 0
        assert result["scenario_a"]["torque_capacity_nm"] > 0
        assert result["scenario_a"]["flank_safety"] >= 1.3
        assert result["scenario_a"]["flank_ok"] is True
        assert result["overall_pass"] is True

    def test_geometry_auto_derived(self):
        result = calculate_spline_fit(make_scenario_a_case())
        geo = result["scenario_a"]["geometry"]
        assert geo["reference_diameter_mm"] == pytest.approx(40.0)
        assert geo["effective_tooth_height_mm"] == pytest.approx(2.0)

    def test_high_torque_fails(self):
        case = make_scenario_a_case()
        case["loads"]["torque_required_nm"] = 50000.0
        result = calculate_spline_fit(case)
        assert result["scenario_a"]["flank_ok"] is False
        assert result["overall_pass"] is False

    def test_flank_pressure_formula(self):
        """Verify: p = 2*T*K_A*K_alpha / (z*h_w*d_m*L)"""
        case = make_scenario_a_case()
        result = calculate_spline_fit(case)
        T = 500.0 * 1000  # N·mm
        K_A = 1.25
        K_alpha = 1.0
        z = 20
        h_w = 2.0
        d_m = 39.75
        L = 30.0
        p_expected = (2 * T * K_A * K_alpha) / (z * h_w * d_m * L)
        assert result["scenario_a"]["flank_pressure_mpa"] == pytest.approx(
            p_expected, rel=1e-3
        )

    def test_torque_capacity_formula(self):
        """Verify: T_form = p_zul * z * h_w * d_m * L / (2 * K_alpha)"""
        case = make_scenario_a_case()
        result = calculate_spline_fit(case)
        p_zul = 100.0
        z = 20
        h_w = 2.0
        d_m = 39.75
        L = 30.0
        K_alpha = 1.0
        T_expected_nmm = p_zul * z * h_w * d_m * L / (2 * K_alpha)
        T_expected_nm = T_expected_nmm / 1000.0
        assert result["scenario_a"]["torque_capacity_nm"] == pytest.approx(
            T_expected_nm, rel=1e-3
        )

    def test_missing_module_raises(self):
        case = make_scenario_a_case()
        del case["spline"]["module_mm"]
        with pytest.raises(InputError, match="module_mm"):
            calculate_spline_fit(case)

    def test_missing_torque_raises(self):
        case = make_scenario_a_case()
        del case["loads"]["torque_required_nm"]
        with pytest.raises(InputError, match="torque_required_nm"):
            calculate_spline_fit(case)
