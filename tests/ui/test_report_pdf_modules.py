"""Tests for module-specific PDF report generators."""

import pytest
from pathlib import Path


def _interference_payload():
    return {
        "geometry": {"shaft_d_mm": 50, "hub_D_mm": 80, "fit_length_mm": 40, "shaft_inner_d_mm": 0},
        "materials": {"shaft_E_mpa": 210000, "shaft_Rp02_mpa": 350, "shaft_nu": 0.3,
                      "hub_E_mpa": 210000, "hub_Rp02_mpa": 250, "hub_nu": 0.3},
        "fit": {"delta_min_um": 30, "delta_max_um": 60},
        "roughness": {"shaft_rz_um": 6.3, "hub_rz_um": 6.3},
        "friction": {"mu_longitudinal": 0.12, "mu_circumferential": 0.15},
        "loads": {"torque_nm": 500, "axial_force_n": 5000, "application_factor_ka": 1.25},
    }


def _interference_result():
    return {
        "overall_pass": True,
        "checks": {"torque_ok": True, "axial_ok": True, "combined_ok": True,
                    "gaping_ok": True, "fit_range_ok": True, "shaft_stress_ok": True, "hub_stress_ok": True},
        "pressure_mpa": {"p_min": 30.0, "p_mean": 45.0, "p_max": 60.0, "p_required": 25.0, "p_required_total": 28.0},
        "capacity": {"torque_min_nm": 800, "torque_mean_nm": 1200, "torque_max_nm": 1600,
                     "axial_min_n": 12000, "axial_mean_n": 18000, "axial_max_n": 24000},
        "assembly": {"press_force_min_n": 45000, "press_force_mean_n": 67000, "press_force_max_n": 90000},
        "stress_mpa": {"shaft_vm_min": 50, "shaft_vm_mean": 75, "shaft_vm_max": 100,
                       "hub_vm_min": 60, "hub_vm_mean": 90, "hub_vm_max": 120,
                       "hub_hoop_inner_min": 40, "hub_hoop_inner_mean": 60, "hub_hoop_inner_max": 80},
        "safety": {"torque_sf": 1.6, "axial_sf": 2.4, "combined_sf": 1.4,
                   "shaft_sf": 3.5, "hub_sf": 2.1, "slip_safety_min": 1.4,
                   "stress_safety_min": 2.1, "combined_usage": 0.71,
                   "application_factor_ka": 1.25, "gaping_margin_mpa": 5.0},
        "required": {"p_required_torque_mpa": 15.0, "p_required_axial_mpa": 10.0,
                     "p_required_combined_mpa": 20.0, "p_required_gap_mpa": 5.0,
                     "p_required_mpa": 25.0, "p_required_total_mpa": 28.0,
                     "delta_required_um": 22.0, "delta_required_effective_um": 18.0},
        "roughness": {"shaft_rz_um": 6.3, "hub_rz_um": 6.3, "smoothing_factor": 0.4,
                      "subsidence_um": 5.04, "delta_input_min_um": 30, "delta_input_max_um": 60,
                      "delta_input_mean_um": 45, "delta_effective_min_um": 24.96,
                      "delta_effective_mean_um": 39.96, "delta_effective_max_um": 54.96},
        "additional_pressure_mpa": {"p_radial": 0, "p_bending": 0, "p_gap": 3.0},
        "model": {"type": "cylindrical_interference_solid_shaft", "shaft_type": "solid_shaft"},
        "derived": {"shaft_inner_d_mm": 0},
        "messages": [],
    }


class TestInterferencePdfReport:
    def test_creates_nonempty_pdf(self, tmp_path):
        from app.ui.report_pdf_interference import generate_interference_report
        out = tmp_path / "interference_report.pdf"
        generate_interference_report(out, _interference_payload(), _interference_result())
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_fail_report(self, tmp_path):
        from app.ui.report_pdf_interference import generate_interference_report
        result = _interference_result()
        result["overall_pass"] = False
        result["checks"]["torque_ok"] = False
        result["checks"]["hub_stress_ok"] = False
        out = tmp_path / "interference_fail.pdf"
        generate_interference_report(out, _interference_payload(), result)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_hollow_shaft(self, tmp_path):
        from app.ui.report_pdf_interference import generate_interference_report
        payload = _interference_payload()
        payload["geometry"]["shaft_inner_d_mm"] = 20
        result = _interference_result()
        result["model"]["shaft_type"] = "hollow_shaft"
        result["derived"]["shaft_inner_d_mm"] = 20
        out = tmp_path / "interference_hollow.pdf"
        generate_interference_report(out, payload, result)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_with_messages(self, tmp_path):
        from app.ui.report_pdf_interference import generate_interference_report
        result = _interference_result()
        result["messages"] = ["过盈量接近材料屈服极限", "建议复核轮毂外径"]
        out = tmp_path / "interference_warnings.pdf"
        generate_interference_report(out, _interference_payload(), result)
        assert out.exists()
        assert out.stat().st_size > 1000


class TestInterferenceRecommendations:
    def test_all_pass(self):
        from app.ui.report_pdf_interference import build_interference_recommendations
        result = _interference_result()
        recs = build_interference_recommendations(result)
        assert len(recs) == 1
        assert "通过" in recs[0]

    def test_failures_generate_recommendations(self):
        from app.ui.report_pdf_interference import build_interference_recommendations
        result = _interference_result()
        result["checks"]["torque_ok"] = False
        result["checks"]["hub_stress_ok"] = False
        recs = build_interference_recommendations(result)
        assert len(recs) == 2


# ---------------------------------------------------------------------------
# Spline PDF report tests
# ---------------------------------------------------------------------------

def _spline_only_payload():
    return {
        "spline": {"module_mm": 2.0, "tooth_count": 26, "engagement_length_mm": 30,
                    "k_alpha": 1.0, "p_allowable_mpa": 100},
        "loads": {"torque_nm": 200, "application_factor_ka": 1.25},
    }


def _spline_only_result():
    return {
        "mode": "spline_only", "overall_pass": True,
        "overall_verdict_level": "simplified_precheck",
        "loads": {"torque_required_nm": 200, "torque_design_nm": 250,
                  "application_factor_ka": 1.25},
        "scenario_a": {
            "geometry": {"reference_diameter_mm": 52.0, "effective_tooth_height_mm": 1.8,
                         "mean_diameter_mm": 51.1, "messages": []},
            "geometry_mode": "approximate", "engagement_length_mm": 30, "k_alpha": 1.0,
            "p_allowable_mpa": 100, "flank_pressure_mpa": 45.2, "torque_capacity_nm": 553,
            "torque_design_nm": 250, "flank_safety": 2.21, "flank_safety_min": 1.0,
            "flank_ok": True, "messages": [], "model_assumptions": ["simplified precheck"],
            "not_covered_checks": ["fatigue"],
            "overall_verdict_level": "simplified_precheck",
        },
        "messages": [],
    }


def _combined_result():
    return {
        "mode": "combined", "overall_pass": True,
        "overall_verdict_level": "simplified_precheck",
        "loads": {"torque_required_nm": 200, "torque_design_nm": 250,
                  "application_factor_ka": 1.25},
        "scenario_a": {
            "geometry": {"reference_diameter_mm": 52.0, "effective_tooth_height_mm": 1.8,
                         "mean_diameter_mm": 51.1, "messages": []},
            "geometry_mode": "approximate", "engagement_length_mm": 30, "k_alpha": 1.0,
            "p_allowable_mpa": 100, "flank_pressure_mpa": 45.2, "torque_capacity_nm": 553,
            "torque_design_nm": 250, "flank_safety": 2.21, "flank_safety_min": 1.0,
            "flank_ok": True, "messages": [], "model_assumptions": [],
            "not_covered_checks": [],
            "overall_verdict_level": "simplified_precheck",
        },
        "scenario_b": {
            "nominal_fit_length_mm": 35, "relief_groove_width_mm": 5,
            "effective_fit_length_mm": 30,
            "pressure_mpa": {"p_min": 20.0, "p_mean": 30.0, "p_max": 40.0,
                             "p_required": 15.0, "p_required_total": 18.0},
            "capacity": {"torque_min_nm": 600, "torque_mean_nm": 900,
                         "torque_max_nm": 1200, "axial_min_n": 8000,
                         "axial_mean_n": 12000, "axial_max_n": 16000},
            "assembly": {"press_force_min_n": 30000, "press_force_mean_n": 45000,
                         "press_force_max_n": 60000},
            "stress_mpa": {"shaft_vm_min": 30, "shaft_vm_mean": 45, "shaft_vm_max": 60,
                           "hub_vm_min": 40, "hub_vm_mean": 60, "hub_vm_max": 80},
            "safety": {"torque_sf": 2.4, "axial_sf": 3.2, "combined_sf": 2.0,
                       "shaft_sf": 5.8, "hub_sf": 3.1, "slip_safety_min": 2.0,
                       "stress_safety_min": 3.1},
            "checks": {"torque_ok": True, "axial_ok": True, "combined_ok": True,
                       "gaping_ok": True, "fit_range_ok": True,
                       "shaft_stress_ok": True, "hub_stress_ok": True},
            "overall_pass": True,
            "messages": [],
        },
        "messages": [],
    }


class TestSplinePdfReport:
    def test_spline_only_report(self, tmp_path):
        from app.ui.report_pdf_spline import generate_spline_report
        out = tmp_path / "spline_only.pdf"
        generate_spline_report(out, _spline_only_payload(), _spline_only_result())
        assert out.exists() and out.stat().st_size > 1000

    def test_combined_report(self, tmp_path):
        from app.ui.report_pdf_spline import generate_spline_report
        payload = _spline_only_payload()
        payload["smooth_fit"] = {"delta_min_um": 20, "delta_max_um": 40}
        generate_spline_report(out := tmp_path / "spline_combined.pdf",
                               payload, _combined_result())
        assert out.exists() and out.stat().st_size > 1000

    def test_with_messages(self, tmp_path):
        from app.ui.report_pdf_spline import generate_spline_report
        result = _spline_only_result()
        result["messages"] = ["齿面压力接近许用值", "建议复核啮合长度"]
        out = tmp_path / "spline_warnings.pdf"
        generate_spline_report(out, _spline_only_payload(), result)
        assert out.exists() and out.stat().st_size > 1000

    def test_fail_report(self, tmp_path):
        from app.ui.report_pdf_spline import generate_spline_report
        result = _spline_only_result()
        result["overall_pass"] = False
        result["scenario_a"]["flank_ok"] = False
        out = tmp_path / "spline_fail.pdf"
        generate_spline_report(out, _spline_only_payload(), result)
        assert out.exists() and out.stat().st_size > 1000


class TestSplineRecommendations:
    def test_all_pass(self):
        from app.ui.report_pdf_spline import build_spline_recommendations
        result = _spline_only_result()
        recs = build_spline_recommendations(result)
        assert len(recs) == 1
        assert "通过" in recs[0]

    def test_flank_fail(self):
        from app.ui.report_pdf_spline import build_spline_recommendations
        result = _spline_only_result()
        result["scenario_a"]["flank_ok"] = False
        recs = build_spline_recommendations(result)
        assert len(recs) == 1
        assert "齿面" in recs[0]

    def test_combined_failures(self):
        from app.ui.report_pdf_spline import build_spline_recommendations
        result = _combined_result()
        result["scenario_b"]["checks"]["torque_ok"] = False
        result["scenario_b"]["checks"]["hub_stress_ok"] = False
        recs = build_spline_recommendations(result)
        assert len(recs) == 2


# ---------------------------------------------------------------------------
# Worm gear PDF report tests
# ---------------------------------------------------------------------------

class TestWormPdfReport:
    def test_geometry_only(self, tmp_path):
        from app.ui.report_pdf_worm import generate_worm_report
        payload = {"geometry": {"module_mm": 4, "tooth_count_worm": 2, "tooth_count_wheel": 41},
                   "operating": {"worm_speed_rpm": 1500, "input_power_kw": 1.5}}
        result = {
            "geometry": {
                "ratio": 20.5, "module_mm": 4, "center_distance_mm": 86,
                "theoretical_center_distance_mm": 86, "lead_angle_deg": 5.6,
                "worm_dimensions": {"pitch_diameter_mm": 32, "tip_diameter_mm": 40,
                    "root_diameter_mm": 22.4, "lead_mm": 25.1, "axial_pitch_mm": 12.6,
                    "pitch_line_speed_mps": 2.51, "face_width_mm": 50},
                "wheel_dimensions": {"pitch_diameter_mm": 164, "tip_diameter_mm": 172,
                    "root_diameter_mm": 154.4, "pitch_line_speed_mps": 0.63,
                    "tooth_height_mm": 8.8, "face_width_mm": 35},
                "mesh_dimensions": {"ratio": 20.5, "center_distance_mm": 86,
                    "worm_speed_rpm": 1500, "wheel_speed_rpm": 73.2,
                    "input_torque_nm": 9.55, "output_torque_nm": 156.3},
                "consistency": {"warnings": []},
            },
            "performance": {"input_power_kw": 1.5, "output_power_kw": 1.2,
                "input_torque_nm": 9.55, "worm_pitch_line_speed_mps": 2.51,
                "efficiency_estimate": 0.80, "power_loss_kw": 0.3,
                "thermal_capacity_kw": 0.5, "output_torque_nm": 156.3,
                "friction_mu": 0.08, "application_factor": 1.0},
            "load_capacity": {"enabled": False, "status": "未启用", "checks": {},
                "forces": {}, "contact": {}, "root": {}, "factors": {},
                "torque_ripple": {}, "warnings": [], "assumptions": []},
        }
        out = tmp_path / "worm_geom.pdf"
        generate_worm_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000

    def test_with_load_capacity(self, tmp_path):
        from app.ui.report_pdf_worm import generate_worm_report
        payload = {"geometry": {"module_mm": 4, "tooth_count_worm": 2, "tooth_count_wheel": 41},
                   "operating": {"worm_speed_rpm": 1500, "input_power_kw": 1.5}}
        result = {
            "geometry": {
                "ratio": 20.5, "module_mm": 4, "center_distance_mm": 86,
                "theoretical_center_distance_mm": 86, "lead_angle_deg": 5.6,
                "worm_dimensions": {"pitch_diameter_mm": 32, "tip_diameter_mm": 40,
                    "root_diameter_mm": 22.4, "lead_mm": 25.1, "axial_pitch_mm": 12.6,
                    "pitch_line_speed_mps": 2.51, "face_width_mm": 50},
                "wheel_dimensions": {"pitch_diameter_mm": 164, "tip_diameter_mm": 172,
                    "root_diameter_mm": 154.4, "pitch_line_speed_mps": 0.63,
                    "tooth_height_mm": 8.8, "face_width_mm": 35},
                "mesh_dimensions": {"ratio": 20.5, "center_distance_mm": 86,
                    "worm_speed_rpm": 1500, "wheel_speed_rpm": 73.2,
                    "input_torque_nm": 9.55, "output_torque_nm": 156.3},
                "consistency": {"warnings": []},
            },
            "performance": {"input_power_kw": 1.5, "output_power_kw": 1.2,
                "input_torque_nm": 9.55, "worm_pitch_line_speed_mps": 2.51,
                "efficiency_estimate": 0.80, "power_loss_kw": 0.3,
                "thermal_capacity_kw": 0.5, "output_torque_nm": 156.3,
                "friction_mu": 0.08, "application_factor": 1.0},
            "load_capacity": {
                "enabled": True, "method": "DIN 3996 Method B", "status": "通过",
                "checks": {"geometry_consistent": True, "contact_ok": True, "root_ok": True},
                "forces": {"tangential_force_wheel_n": 1905, "axial_force_wheel_n": 597,
                    "radial_force_wheel_n": 693, "normal_force_n": 2150,
                    "design_normal_force_n": 2150},
                "contact": {"sigma_hm_nominal_mpa": 450, "allowable_contact_stress_mpa": 600,
                    "safety_factor_nominal": 1.33, "safety_factor_peak": 1.1},
                "root": {"sigma_f_nominal_mpa": 25, "allowable_root_stress_mpa": 50,
                    "safety_factor_nominal": 2.0, "safety_factor_peak": 1.6},
                "factors": {"application_factor": 1.0, "dynamic_factor_kv": 1.05,
                    "transverse_load_factor_kha": 1.0, "face_load_factor_khb": 1.0},
                "torque_ripple": {"percent": 10, "output_torque_nominal_nm": 156.3,
                    "output_torque_peak_nm": 171.9},
                "warnings": [], "assumptions": ["ZK tooth form", "Steel-plastic pairing"],
            },
        }
        out = tmp_path / "worm_lc.pdf"
        generate_worm_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000
