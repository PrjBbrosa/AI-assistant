from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


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


def _hertz_payload():
    return {
        "geometry": {
            "contact_mode": "line",
            "r1_mm": 30.0,
            "r2_mm": 0.0,
            "length_mm": 20.0,
        },
        "materials": {
            "e1_mpa": 210000.0,
            "nu1": 0.29,
            "e2_mpa": 210000.0,
            "nu2": 0.30,
        },
        "loads": {"normal_force_n": 12000.0},
        "checks": {"allowable_p0_mpa": 1500.0},
        "options": {"curve_points": 41, "curve_force_scale": 1.30},
    }


def _hertz_result(payload=None):
    from core.hertz.calculator import calculate_hertz_contact

    return calculate_hertz_contact(payload or _hertz_payload())


def _buffer_payload():
    return {
        "curve": {
            "loading": [
                {"x_mm": 0.0, "force_n": 0.0},
                {"x_mm": 10.0, "force_n": 4000.0},
                {"x_mm": 20.0, "force_n": 8000.0},
            ],
            "unloading": [
                {"x_mm": 0.0, "force_n": 0.0},
                {"x_mm": 10.0, "force_n": 1600.0},
                {"x_mm": 20.0, "force_n": 3200.0},
            ],
        },
        "impact": {
            "mass_kg": 10.0,
            "initial_velocity_m_s": 1.0,
            "available_stroke_mm": 20.0,
            "allowable_peak_force_n": 9000.0,
        },
        "options": {
            "force_scale": 1.0,
            "stroke_scale": 1.0,
            "noise_tolerance_n": 5.0,
            "time_samples": 80,
        },
    }


def _buffer_result(payload=None):
    from core.buffer.calculator import calculate_buffer_energy

    return calculate_buffer_energy(payload or _buffer_payload())


class TestHertzPdfReport:
    def test_creates_nonempty_pdf(self, tmp_path):
        from app.ui.report_pdf_hertz import generate_hertz_report

        out = tmp_path / "hertz_report.pdf"
        generate_hertz_report(out, _hertz_payload(), _hertz_result())
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_missing_optional_contact_fields_do_not_crash(self, tmp_path):
        from app.ui.report_pdf_hertz import generate_hertz_report

        result = _hertz_result()
        result["contact"].pop("contact_area_mm2")
        result["contact"].pop("semi_width_mm")
        out = tmp_path / "hertz_sparse.pdf"
        generate_hertz_report(out, _hertz_payload(), result)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_page_pdf_export_uses_reportlab_module(self, qapp, tmp_path):
        from app.ui.pages.hertz_contact_page import HertzContactPage

        page = HertzContactPage()
        page._last_payload = _hertz_payload()
        page._last_result = _hertz_result()
        out = tmp_path / "hertz_page.pdf"

        from unittest.mock import patch

        with (
            patch(
                "app.ui.pages.hertz_contact_page.QFileDialog.getSaveFileName",
                return_value=(str(out), "PDF Files (*.pdf)"),
            ),
            patch(
                "app.ui.report_pdf_hertz.generate_hertz_report",
                side_effect=lambda path, payload, result: path.write_bytes(b"%PDF hertz"),
            ) as generate,
        ):
            page._save_report()

        generate.assert_called_once()

    def test_pdf_includes_report_trace(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_hertz
        from app.ui.model_scope import HERTZ_SCOPE
        from app.ui.report_pdf_hertz import generate_hertz_report

        captured: list[list[tuple[str, str]]] = []
        original = report_pdf_hertz._trace_block

        def capture_trace(styles, rows):
            captured.append(list(rows))
            return original(styles, rows)

        monkeypatch.setattr(report_pdf_hertz, "_trace_block", capture_trace)
        payload = _hertz_payload()
        generate_hertz_report(tmp_path / "hertz_trace.pdf", payload, _hertz_result(payload))

        assert captured
        kv = dict(captured[0])
        assert "软件版本" in kv
        assert kv["软件版本"]
        assert kv.get("模块") == HERTZ_SCOPE.module_id
        assert kv.get("模型等级") == HERTZ_SCOPE.model_level
        assert str(kv.get("输入摘要哈希", "")).startswith("sha256:")

    def test_pdf_includes_model_level(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_hertz
        from app.ui.model_scope import MODEL_LEVEL_QUICK
        from app.ui.report_pdf_hertz import generate_hertz_report

        subtitles: list[str] = []
        titles: list[str] = []
        original_verdict = report_pdf_hertz._verdict_block
        original_title = report_pdf_hertz._section_title

        def capture_verdict(styles, overall, subtitle):
            subtitles.append(subtitle)
            return original_verdict(styles, overall, subtitle)

        def capture_title(styles, title):
            titles.append(title)
            return original_title(styles, title)

        monkeypatch.setattr(report_pdf_hertz, "_verdict_block", capture_verdict)
        monkeypatch.setattr(report_pdf_hertz, "_section_title", capture_title)

        out = tmp_path / "hertz_model_level.pdf"
        payload = _hertz_payload()
        result = _hertz_result(payload)
        generate_hertz_report(out, payload, result)
        assert any(MODEL_LEVEL_QUICK in text for text in subtitles)
        assert "模型范围" in titles

    def test_pdf_verdict_matches_result_view_model(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_hertz
        from app.ui.report_pdf_hertz import generate_hertz_report
        from app.ui.result_contract import from_hertz

        overalls: list[object] = []
        original_verdict = report_pdf_hertz._verdict_block

        def capture_verdict(styles, overall, subtitle):
            overalls.append(overall)
            return original_verdict(styles, overall, subtitle)

        monkeypatch.setattr(report_pdf_hertz, "_verdict_block", capture_verdict)
        payload = _hertz_payload()
        result = _hertz_result(payload)
        view = from_hertz(result, payload)
        generate_hertz_report(tmp_path / "hertz_verdict.pdf", payload, result)

        assert overalls
        assert overalls[0] == view.overall_status
        assert view.overall_status in ("pass", "fail")
        assert view.title_zh.startswith("校核通过" if view.overall_status == "pass" else "校核不通过")


class TestBufferPdfReport:
    def test_creates_nonempty_pdf(self, tmp_path):
        from app.ui.report_pdf_buffer import generate_buffer_report

        out = tmp_path / "buffer_report.pdf"
        generate_buffer_report(out, _buffer_payload(), _buffer_result())
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_missing_optional_impact_fields_do_not_crash(self, tmp_path):
        from app.ui.report_pdf_buffer import generate_buffer_report

        result = _buffer_result()
        result["impact"].pop("peak_force_n")
        result.pop("time_response", None)
        out = tmp_path / "buffer_sparse.pdf"
        generate_buffer_report(out, _buffer_payload(), result)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_page_pdf_export_uses_reportlab_module(self, qapp, tmp_path):
        from app.ui.pages.buffer_energy_page import BufferEnergyPage

        page = BufferEnergyPage()
        page._last_payload = _buffer_payload()
        page._last_result = _buffer_result()
        out = tmp_path / "buffer_page.pdf"

        from unittest.mock import patch

        with (
            patch(
                "app.ui.pages.buffer_energy_page.QFileDialog.getSaveFileName",
                return_value=(str(out), "PDF Files (*.pdf)"),
            ),
            patch(
                "app.ui.report_pdf_buffer.generate_buffer_report",
                side_effect=lambda path, payload, result: path.write_bytes(b"%PDF buffer"),
            ) as generate,
        ):
            page._on_save_report()

        generate.assert_called_once()


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

    def test_pdf_includes_report_trace(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_interference
        from app.ui.model_scope import INTERFERENCE_SCOPE
        from app.ui.report_pdf_interference import generate_interference_report

        captured: list[list[tuple[str, str]]] = []
        original = report_pdf_interference._trace_block

        def capture_trace(styles, rows):
            captured.append(list(rows))
            return original(styles, rows)

        monkeypatch.setattr(report_pdf_interference, "_trace_block", capture_trace)
        payload = _interference_payload()
        generate_interference_report(
            tmp_path / "interference_trace.pdf", payload, _interference_result()
        )

        assert captured
        kv = dict(captured[0])
        assert "软件版本" in kv
        assert kv["软件版本"]
        assert kv.get("模块") == INTERFERENCE_SCOPE.module_id
        assert kv.get("模型等级") == INTERFERENCE_SCOPE.model_level
        assert str(kv.get("输入摘要哈希", "")).startswith("sha256:")

    def test_pdf_includes_model_level(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_interference
        from app.ui.model_scope import MODEL_LEVEL_FORMAL_SUBSET
        from app.ui.report_pdf_interference import generate_interference_report

        subtitles: list[str] = []
        titles: list[str] = []
        original_verdict = report_pdf_interference._verdict_block
        original_title = report_pdf_interference._section_title

        def capture_verdict(styles, overall, subtitle):
            subtitles.append(subtitle)
            return original_verdict(styles, overall, subtitle)

        def capture_title(styles, title):
            titles.append(title)
            return original_title(styles, title)

        monkeypatch.setattr(report_pdf_interference, "_verdict_block", capture_verdict)
        monkeypatch.setattr(report_pdf_interference, "_section_title", capture_title)

        out = tmp_path / "interference_model_level.pdf"
        generate_interference_report(out, _interference_payload(), _interference_result())
        assert any(MODEL_LEVEL_FORMAL_SUBSET in text for text in subtitles)
        assert "模型范围" in titles

    def test_pdf_verdict_matches_result_view_model(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_interference
        from app.ui.report_pdf_interference import generate_interference_report
        from app.ui.result_contract import from_interference

        overalls: list[object] = []
        original_verdict = report_pdf_interference._verdict_block

        def capture_verdict(styles, overall, subtitle):
            overalls.append(overall)
            return original_verdict(styles, overall, subtitle)

        monkeypatch.setattr(report_pdf_interference, "_verdict_block", capture_verdict)
        payload = _interference_payload()
        result = _interference_result()
        view = from_interference(result, payload)
        generate_interference_report(tmp_path / "interference_verdict.pdf", payload, result)

        assert overalls
        assert overalls[0] == view.overall_status
        assert view.overall_status in ("pass", "fail")
        assert view.title_zh.startswith(
            "校核通过" if view.overall_status == "pass" else "校核不通过"
        )
        check_ids = {item.id for item in view.checks}
        assert "torque_ok" in check_ids or "combined_ok" in check_ids
        assert "shaft_stress_ok" in check_ids or "hub_stress_ok" in check_ids


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

    def test_pdf_includes_model_level(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_spline
        from app.ui.model_scope import MODEL_LEVEL_PRECHECK
        from app.ui.report_pdf_spline import generate_spline_report

        subtitles: list[str] = []
        titles: list[str] = []
        original_verdict = report_pdf_spline._verdict_block
        original_title = report_pdf_spline._section_title

        def capture_verdict(styles, overall, subtitle):
            subtitles.append(subtitle)
            return original_verdict(styles, overall, subtitle)

        def capture_title(styles, title):
            titles.append(title)
            return original_title(styles, title)

        monkeypatch.setattr(report_pdf_spline, "_verdict_block", capture_verdict)
        monkeypatch.setattr(report_pdf_spline, "_section_title", capture_title)

        out = tmp_path / "spline_model_level.pdf"
        generate_spline_report(out, _spline_only_payload(), _spline_only_result())
        assert any(MODEL_LEVEL_PRECHECK in text for text in subtitles)
        assert "模型范围" in titles

    def test_pdf_verdict_matches_result_view_model(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_spline
        from app.ui.report_pdf_spline import generate_spline_report
        from app.ui.result_contract import from_spline

        overalls: list[object] = []
        original_verdict = report_pdf_spline._verdict_block

        def capture_verdict(styles, overall, subtitle):
            overalls.append(overall)
            return original_verdict(styles, overall, subtitle)

        monkeypatch.setattr(report_pdf_spline, "_verdict_block", capture_verdict)
        payload = _spline_only_payload()
        result = _spline_only_result()
        view = from_spline(result, payload)
        generate_spline_report(tmp_path / "spline_verdict.pdf", payload, result)

        assert overalls
        assert overalls[0] == view.overall_status
        assert view.overall_status in ("pass", "fail")
        assert "预校核通过" in view.title_zh or "预校核不通过" in view.title_zh
        assert view.checks[0].label_zh == "齿面承压校核"

    def test_pdf_includes_report_trace(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_spline
        from app.ui.model_scope import MODEL_LEVEL_PRECHECK
        from app.ui.report_pdf_spline import generate_spline_report

        traces: list[list[tuple[str, str]]] = []
        original_trace = report_pdf_spline._trace_block

        def capture_trace(styles, rows):
            traces.append(list(rows))
            return original_trace(styles, rows)

        monkeypatch.setattr(report_pdf_spline, "_trace_block", capture_trace)
        generate_spline_report(
            tmp_path / "spline_trace.pdf",
            _spline_only_payload(),
            _spline_only_result(),
        )
        assert traces
        labels = [row[0] for row in traces[0]]
        values = " ".join(row[1] for row in traces[0])
        assert "软件版本" in labels
        assert "输入摘要哈希" in labels
        assert "模型等级" in labels
        assert MODEL_LEVEL_PRECHECK in values
        assert any(row[1].startswith("sha256:") for row in traces[0])


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

    def test_pdf_includes_report_trace(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_worm
        from app.ui.model_scope import WORM_SCOPE
        from app.ui.report_pdf_worm import generate_worm_report

        captured: list[list[tuple[str, str]]] = []
        original = report_pdf_worm._trace_block

        def capture_trace(styles, rows):
            captured.append(list(rows))
            return original(styles, rows)

        monkeypatch.setattr(report_pdf_worm, "_trace_block", capture_trace)
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
        generate_worm_report(tmp_path / "worm_trace.pdf", payload, result)

        assert captured
        kv = dict(captured[0])
        assert "软件版本" in kv
        assert kv["软件版本"]
        assert kv.get("模块") == WORM_SCOPE.module_id
        assert kv.get("模型等级") == WORM_SCOPE.model_level
        assert str(kv.get("输入摘要哈希", "")).startswith("sha256:")

    def test_pdf_includes_model_level(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_worm
        from app.ui.model_scope import MODEL_LEVEL_FORMAL_SUBSET
        from app.ui.report_pdf_worm import generate_worm_report

        subtitles: list[str] = []
        titles: list[str] = []
        original_verdict = report_pdf_worm._verdict_block
        original_title = report_pdf_worm._section_title

        def capture_verdict(styles, overall, subtitle):
            subtitles.append(subtitle)
            return original_verdict(styles, overall, subtitle)

        def capture_title(styles, title):
            titles.append(title)
            return original_title(styles, title)

        monkeypatch.setattr(report_pdf_worm, "_verdict_block", capture_verdict)
        monkeypatch.setattr(report_pdf_worm, "_section_title", capture_title)

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
                "overall_pass": True,
                "checks": {"geometry_consistent": True, "contact_ok": True, "root_ok": True},
                "forces": {}, "contact": {}, "root": {}, "factors": {},
                "torque_ripple": {}, "warnings": [], "assumptions": [],
            },
        }
        out = tmp_path / "worm_model_level.pdf"
        generate_worm_report(out, payload, result)
        assert any(MODEL_LEVEL_FORMAL_SUBSET in text for text in subtitles)
        assert "模型范围" in titles

    def test_pdf_verdict_matches_result_view_model(self, tmp_path, monkeypatch):
        from app.ui import report_pdf_worm
        from app.ui.report_pdf_worm import generate_worm_report
        from app.ui.result_contract import from_worm

        overalls: list[object] = []
        original_verdict = report_pdf_worm._verdict_block

        def capture_verdict(styles, overall, subtitle):
            overalls.append(overall)
            return original_verdict(styles, overall, subtitle)

        monkeypatch.setattr(report_pdf_worm, "_verdict_block", capture_verdict)
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
                "overall_pass": True,
                "checks": {"geometry_consistent": True, "contact_ok": True, "root_ok": True},
                "contact": {"sigma_hm_peak_mpa": 450, "allowable_contact_stress_mpa": 600},
                "root": {"sigma_f_peak_mpa": 25, "allowable_root_stress_mpa": 50},
                "forces": {}, "factors": {}, "torque_ripple": {},
                "warnings": [], "assumptions": [],
            },
        }
        view = from_worm(result, payload)
        generate_worm_report(tmp_path / "worm_verdict.pdf", payload, result)

        assert overalls
        assert overalls[0] == view.overall_status
        assert view.overall_status in ("pass", "fail", "incomplete")
        assert view.title_zh.startswith(
            "校核通过" if view.overall_status == "pass" else (
                "校核不完整" if view.overall_status == "incomplete" else "校核不通过"
            )
        )
        assert view.checks[0].id == "geometry_consistent"
        assert view.checks[1].label_zh == "齿面接触应力"
        assert view.checks[2].label_zh == "齿根弯曲应力"
        assert "Load Capacity" in view.verdict_subtitle_zh

    def test_missing_overall_pass_does_not_fallback_to_checks_pass(self, tmp_path, monkeypatch):
        from reportlab.platypus import Spacer

        from app.ui import report_pdf_worm

        verdict_values = []

        def fake_verdict_block(styles, passed, subtitle):
            verdict_values.append(passed)
            return Spacer(1, 1)

        monkeypatch.setattr(report_pdf_worm, "_verdict_block", fake_verdict_block)
        monkeypatch.setattr(report_pdf_worm, "build_pdf", lambda path, elems, title: path.write_bytes(b"%PDF"))

        payload = {"geometry": {}, "operating": {}}
        result = {
            "geometry": {
                "ratio": 20.0,
                "center_distance_mm": 100.0,
                "worm_dimensions": {},
                "wheel_dimensions": {},
                "consistency": {},
            },
            "performance": {
                "efficiency_estimate": 0.80,
                "output_torque_nm": 100.0,
            },
            "load_capacity": {
                "enabled": True,
                "status": "legacy result without authoritative overall_pass",
                "checks": {
                    "geometry_consistent": True,
                    "contact_ok": True,
                    "root_ok": True,
                },
                "warnings": [],
                "assumptions": [],
            },
        }

        from app.ui.result_contract import from_worm

        report_pdf_worm.generate_worm_report(tmp_path / "worm_missing_overall.pdf", payload, result)

        view = from_worm(result, payload)
        assert verdict_values == [view.overall_status]
        assert view.overall_status == "fail"


# ---------------------------------------------------------------------------
# Bolt rich PDF tri-state (CRIT-1 regression)
# ---------------------------------------------------------------------------
def _bolt_incomplete_result():
    """缺 R7/R8 输入的 payload -> overall_status=incomplete。"""
    from core.bolt.calculator import calculate_vdi2230_core
    base = {
        "fastener": {"d": 12, "p": 1.75, "Rp02": 900},
        "tightening": {"alpha_A": 1.4, "mu_thread": 0.12, "mu_bearing": 0.12, "utilization": 0.9},
        "loads": {"FA_max": 5000, "seal_force_required": 1000},
        "stiffness": {"bolt_stiffness": 300000, "clamped_stiffness": 900000},
        "bearing": {"bearing_d_inner": 13, "bearing_d_outer": 20},
    }
    return base, calculate_vdi2230_core(base)


class TestBoltTriStatePdf:
    def test_incomplete_recommendations_no_false_green(self):
        from app.ui.report_pdf import build_bolt_recommendations
        _, result = _bolt_incomplete_result()
        assert result["overall_status"] == "incomplete"
        recs = build_bolt_recommendations(result)
        # incomplete 时不得输出"满足全部校核"绿灯结论
        assert not any("满足全部校核" in x for x in recs), recs
        # 应提示存在未校核项
        assert any("未校核" in x or "不完整" in x for x in recs), recs

    def test_incomplete_pdf_nonempty(self, tmp_path):
        from app.ui.report_pdf import generate_bolt_report
        payload, result = _bolt_incomplete_result()
        out = tmp_path / "bolt_incomplete.pdf"
        generate_bolt_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000

    def test_incomplete_pdf_not_rendered_as_fail(self, tmp_path):
        import shutil
        import subprocess
        from app.ui.report_pdf import generate_bolt_report
        payload, result = _bolt_incomplete_result()
        out = tmp_path / "bolt_incomplete_text.pdf"
        generate_bolt_report(out, payload, result)
        pdftotext = shutil.which("pdftotext")
        if pdftotext is None:
            pytest.skip("pdftotext 不可用，跳过文本断言")
        txt = subprocess.run(
            [pdftotext, str(out), "-"], capture_output=True, text=True, check=True
        ).stdout
        # incomplete 应渲染为"校核不完整"，而非 FAIL
        # pdftotext 可能在徽章文字中插入换行，先去除所有空白再断言
        compact = "".join(txt.split())
        assert "FAIL" not in compact, txt
        assert "校核不完整" in compact, txt
