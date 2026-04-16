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
            "geometry_mode": "approximate",
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
        # DIN 5480-2 近似：h_w = 0.9 m = 1.8
        assert geo["effective_tooth_height_mm"] == pytest.approx(1.8)
        assert geo["geometry_source"] == "approximation_from_module_and_tooth_count"

    def test_public_catalog_geometry_can_be_used_for_precheck(self):
        case = {
            "mode": "spline_only",
            "spline": {
                "geometry_mode": "reference_dimensions",
                "module_mm": 1.25,
                "tooth_count": 10,
                "reference_diameter_mm": 15.0,
                "tip_diameter_shaft_mm": 14.75,
                "root_diameter_shaft_mm": 12.1,
                "tip_diameter_hub_mm": 12.5,
                "engagement_length_mm": 40.0,
                "k_alpha": 1.3,
                "p_allowable_mpa": 100.0,
            },
            "loads": {
                "torque_required_nm": 50.0,
                "application_factor_ka": 1.25,
            },
            "checks": {
                "flank_safety_min": 1.3,
            },
        }
        result = calculate_spline_fit(case)
        assert result["scenario_a"]["geometry"]["reference_diameter_mm"] == pytest.approx(15.0)
        assert result["scenario_a"]["geometry"]["geometry_source"] == "explicit_reference_dimensions"
        assert result["scenario_a"]["overall_verdict_level"] == "simplified_precheck"

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
        # DIN 5480-2 近似（m=2, z=20）：d=40, d_a1=39.6, d_a2=36.0 → h_w=1.8, d_m=37.8
        h_w = 1.8
        d_m = 37.8
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
        h_w = 1.8
        d_m = 37.8
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

    def test_non_integer_tooth_count_raises(self):
        case = make_scenario_a_case()
        case["spline"]["tooth_count"] = 20.5
        with pytest.raises(InputError, match="tooth_count"):
            calculate_spline_fit(case)

    def test_invalid_geometry_mode_raises(self):
        case = make_scenario_a_case()
        case["spline"]["geometry_mode"] = "invalid"
        with pytest.raises(InputError, match="geometry_mode"):
            calculate_spline_fit(case)

    def test_zero_torque_raises(self):
        case = make_scenario_a_case()
        case["loads"]["torque_required_nm"] = 0.0
        with pytest.raises(InputError, match="torque_required_nm"):
            calculate_spline_fit(case)


def make_combined_case() -> dict:
    """Combined mode: scenario A + scenario B."""
    return {
        "mode": "combined",
        "spline": {
            "geometry_mode": "approximate",
            "module_mm": 2.0,
            "tooth_count": 20,
            "engagement_length_mm": 30.0,
            "k_alpha": 1.0,
            "p_allowable_mpa": 100.0,
        },
        "smooth_fit": {
            "shaft_d_mm": 40.0,
            "shaft_inner_d_mm": 0.0,
            "hub_outer_d_mm": 80.0,
            "fit_length_mm": 45.0,
            "relief_groove_width_mm": 3.0,
            "delta_min_um": 20.0,
            "delta_max_um": 45.0,
        },
        "smooth_materials": {
            "shaft_e_mpa": 210000.0,
            "shaft_nu": 0.30,
            "shaft_yield_mpa": 600.0,
            "hub_e_mpa": 210000.0,
            "hub_nu": 0.30,
            "hub_yield_mpa": 320.0,
        },
        "smooth_roughness": {
            "shaft_rz_um": 6.3,
            "hub_rz_um": 6.3,
        },
        "smooth_friction": {
            "mu_torque": 0.14,
            "mu_axial": 0.14,
            "mu_assembly": 0.12,
        },
        "loads": {
            "torque_required_nm": 500.0,
            "axial_force_required_n": 0.0,
            "application_factor_ka": 1.25,
        },
        "checks": {
            "flank_safety_min": 1.3,
            "slip_safety_min": 1.5,
            "stress_safety_min": 1.2,
        },
    }


class TestScenarioB:
    def test_combined_mode_has_both_scenarios(self):
        result = calculate_spline_fit(make_combined_case())
        assert "scenario_a" in result
        assert "scenario_b" in result

    def test_scenario_b_pressure_positive(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert b["pressure_mpa"]["p_min"] > 0
        assert b["pressure_mpa"]["p_max"] > b["pressure_mpa"]["p_min"]

    def test_relief_groove_reduces_effective_length(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert b["effective_fit_length_mm"] == pytest.approx(42.0)

    def test_scenario_b_torque_capacity(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert b["capacity"]["torque_min_nm"] > 0

    def test_scenario_b_slip_safety(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert "torque_sf" in b["safety"]

    def test_overall_pass_requires_both(self):
        case = make_combined_case()
        case["loads"]["torque_required_nm"] = 50000.0
        result = calculate_spline_fit(case)
        assert result["overall_pass"] is False

    def test_spline_only_mode_no_scenario_b(self):
        case = make_combined_case()
        case["mode"] = "spline_only"
        result = calculate_spline_fit(case)
        assert "scenario_b" not in result

    def test_scenario_b_messages_are_promoted_to_top_level(self):
        result = calculate_spline_fit(make_combined_case())
        assert any("扭矩与轴向力联合作用超出当前最小过盈能力" in msg for msg in result["messages"])

    def test_scenario_b_keeps_outer_design_load_trace(self):
        result = calculate_spline_fit(make_combined_case())
        trace = result["scenario_b"]["design_loads"]
        assert trace["application_factor_ka"] == pytest.approx(1.25)
        assert trace["torque_design_nm"] == pytest.approx(625.0)
        assert trace["delegated_application_factor_ka"] == pytest.approx(1.0)

    def test_negative_relief_groove_raises(self):
        case = make_combined_case()
        case["smooth_fit"]["relief_groove_width_mm"] = -1.0
        with pytest.raises(InputError, match="不能为负数"):
            calculate_spline_fit(case)

    def test_relief_groove_exceeds_length_raises(self):
        case = make_combined_case()
        case["smooth_fit"]["relief_groove_width_mm"] = 50.0  # >= fit_length_mm (45.0)
        with pytest.raises(InputError, match="有效配合长度"):
            calculate_spline_fit(case)

    def test_scenario_b_ka_comment_in_design_loads(self):
        """Verify design_loads contains both real ka and delegated ka=1.0."""
        result = calculate_spline_fit(make_combined_case())
        dl = result["scenario_b"]["design_loads"]
        # Real ka from outer loads
        assert dl["application_factor_ka"] == pytest.approx(1.25)
        # Delegated ka must be 1.0 because loads are pre-multiplied
        assert dl["delegated_application_factor_ka"] == pytest.approx(1.0)
        # Design torque = required * ka
        assert dl["torque_design_nm"] == pytest.approx(500.0 * 1.25)

    def test_combined_mode_both_scenarios_present(self):
        """Combined mode must produce both scenario_a and scenario_b results."""
        result = calculate_spline_fit(make_combined_case())
        assert "scenario_a" in result
        assert "scenario_b" in result
        # scenario_a has flank check fields
        assert "flank_pressure_mpa" in result["scenario_a"]
        assert "flank_safety" in result["scenario_a"]
        # scenario_b has DIN 7190 delegation fields
        assert "pressure_mpa" in result["scenario_b"]
        assert "safety" in result["scenario_b"]
        assert "design_loads" in result["scenario_b"]
        # overall_pass reflects both
        assert isinstance(result["overall_pass"], bool)
