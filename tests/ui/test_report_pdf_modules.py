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
