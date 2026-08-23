"""Smoke and contract tests for the buffer-energy UI."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.widgets.buffer_energy_curve import BufferEnergyCurveWidget
from app.ui.widgets.buffer_response_curve import BufferResponseCurveWidget


def _sample_curve() -> dict:
    loading = [
        {"x_mm": 0.0, "force_n": 0.0},
        {"x_mm": 10.0, "force_n": 1800.0},
        {"x_mm": 20.0, "force_n": 4200.0},
    ]
    unloading = [
        {"x_mm": 0.0, "force_n": 0.0},
        {"x_mm": 10.0, "force_n": 800.0},
        {"x_mm": 20.0, "force_n": 2100.0},
    ]
    return {
        "loading": loading,
        "unloading": unloading,
        "metadata": {
            "format": "wide",
            "rows": 3,
            "loading_count": len(loading),
            "unloading_count": len(unloading),
            "warnings": [],
        },
    }


def _sample_result(*, bottom_out: bool = False) -> dict:
    peak_force = None if bottom_out else 1650.0
    peak_status = "bottom_out_unknown" if bottom_out else "ok"
    peak_ok = None if bottom_out else True
    return {
        "inputs_echo": {
            "impact": {
                "mass_kg": 12.0,
                "initial_velocity_m_s": 1.5,
                "available_stroke_mm": 30.0,
                "allowable_peak_force_n": 9000.0,
            },
            "options": {
                "force_scale": 1.0,
                "stroke_scale": 1.0,
                "noise_tolerance_n": 5.0,
                "time_samples": 80,
            },
        },
        "curve_summary": {
            "max_stroke_mm": 20.0,
            "peak_loading_force_n": 4200.0,
            "loading_energy_j": 48.0,
            "unloading_energy_j": 22.0,
            "curve_hysteresis_energy_j": 26.0,
            "energy_absorption_ratio": 0.5417,
            "equivalent_stiffness_n_per_mm": 210.0,
            "tangent_stiffness_min_n_per_mm": 180.0,
            "tangent_stiffness_max_n_per_mm": 240.0,
        },
        "impact": {
            "initial_energy_j": 13.5,
            "available_energy_capacity_j": 48.0,
            "max_compression_mm": 8.25 if not bottom_out else 20.0,
            "peak_force_n": peak_force,
            "peak_force_status": peak_status,
            "average_force_n": 1636.4,
            "absorbed_energy_j": 13.5,
            "rebound_energy_j": 5.4,
            "impact_dissipated_energy_j": 8.1,
            "estimated_rebound_velocity_m_s": 0.95,
            "bottom_out": bottom_out,
        },
        "checks": {
            "stroke_ok": not bottom_out,
            "peak_force_ok": peak_ok,
            "energy_capacity_ok": not bottom_out,
        },
        "overall_pass": not bottom_out,
        "curves": {
            "loading_x_mm": [0.0, 10.0, 20.0],
            "loading_force_n": [0.0, 1800.0, 4200.0],
            "unloading_x_mm": [0.0, 10.0, 20.0],
            "unloading_force_n": [0.0, 800.0, 2100.0],
            "loading_energy_x_mm": [0.0, 10.0, 20.0],
            "loading_energy_j": [0.0, 9.0, 48.0],
        },
        "time_response": {
            "duration_s": 0.018,
            "compression_duration_s": 0.010,
            "rebound_duration_s": 0.008 if not bottom_out else 0.0,
            "time_s": [0.0, 0.006, 0.010, 0.014, 0.018],
            "displacement_mm": [0.0, 5.0, 8.25, 4.0, 0.0],
            "velocity_m_s": [1.5, 0.8, 0.0, -0.5, -0.95],
            "acceleration_m_s2": [0.0, 120.0, 140.0, -70.0, 0.0],
            "force_n": [0.0, 900.0, 1650.0, 350.0, 0.0],
        },
        "warnings": ["示例 warning"] if bottom_out else [],
        "assumptions": [
            "本工具基于加载 / 卸载 F-x 曲线的单次冲击能量法。",
            "未使用时间域数据，不能唯一识别真实粘性阻尼系数 c。",
            "回弹速度为基于卸载曲线能量的估算值。",
            "时域响应曲线为由能量守恒反推的近似映射，不含应变率效应。",
            "假设水平冲击或重力做功相对动能可忽略。",
            "卸载段简化假设：测试卸载曲线形状只与位移有关。",
        ],
    }


class BufferEnergyCurveWidgetSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_constructs_with_no_data(self) -> None:
        widget = BufferEnergyCurveWidget()
        widget.resize(420, 280)
        widget.repaint()

    def test_set_curves_repaints(self) -> None:
        widget = BufferEnergyCurveWidget()
        widget.set_curves(
            loading=[(0.0, 0.0), (10.0, 1800.0)],
            unloading=[(0.0, 0.0), (10.0, 900.0)],
            x_max_mm=4.0,
            available_stroke_mm=10.0,
            allowable_peak_n=2000.0,
            bottom_out=False,
        )
        widget.resize(420, 280)
        widget.repaint()

    def test_bottom_out_repaints(self) -> None:
        widget = BufferEnergyCurveWidget()
        widget.set_curves(
            loading=[(0.0, 0.0), (10.0, 1800.0)],
            unloading=[(0.0, 0.0), (10.0, 900.0)],
            x_max_mm=10.0,
            available_stroke_mm=12.0,
            allowable_peak_n=2000.0,
            bottom_out=True,
        )
        widget.resize(420, 280)
        widget.repaint()


class BufferResponseCurveWidgetSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_constructs_empty(self) -> None:
        widget = BufferResponseCurveWidget()
        widget.resize(420, 280)
        widget.repaint()

    def test_switches_all_variables(self) -> None:
        widget = BufferResponseCurveWidget()
        widget.set_response(_sample_result()["time_response"])
        for variable in ("x", "v", "a", "F"):
            widget.set_variable(variable)
            self.assertEqual(widget.variable(), variable)
            widget.repaint()

    def test_invalid_variable_raises(self) -> None:
        widget = BufferResponseCurveWidget()
        with self.assertRaises(ValueError):
            widget.set_variable("energy")


class BufferEnergyPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _make_page(self):
        from app.ui.pages.buffer_energy_page import BufferEnergyPage

        return BufferEnergyPage()

    def test_page_skeleton_and_scheme_a_widgets(self) -> None:
        page = self._make_page()
        self.assertEqual(page.chapter_list.count(), 7)
        self.assertFalse(page.disclaimer_label.isHidden())
        self.assertIn("能量法", page.disclaimer_label.text())
        self.assertIn("应变率", page.disclaimer_label.text())
        for attr in (
            "btn_import_curve",
            "btn_save_inputs",
            "btn_load_inputs",
            "btn_calculate",
            "btn_clear",
            "btn_save_report",
            "btn_load_1",
            "btn_load_2",
            "metric_labels",
            "overview_curve_widget",
            "energy_strip_label",
            "overall_verdict_label",
            "model_boundary_label",
            "workbench_status_label",
            "compare_preview_table",
            "results_label",
        ):
            self.assertTrue(hasattr(page, attr), f"missing {attr}")
        self.assertIn("initial_energy", page.metric_labels)
        self.assertEqual(page.compare_preview_table.columnCount(), 4)
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertFalse(page.btn_calculate.isEnabled())

    def test_open_curve_path_uses_loader_and_updates_summary(self) -> None:
        page = self._make_page()
        page._load_buffer_curve = lambda _path: _sample_curve()
        page._open_curve_path(Path("curve.csv"))
        self.assertIsNotNone(page._curve_data)
        self.assertIn("最大行程", page.curve_summary_label.text())
        self.assertIn("加载 3 点", page.curve_summary_label.text())
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertTrue(page.btn_calculate.isEnabled())

    def test_load_sample_enables_calculate_button(self) -> None:
        page = self._make_page()
        page._load_buffer_curve = lambda _path: _sample_curve()

        page._load_sample("buffer_energy_case_01.csv")

        self.assertTrue(page.btn_calculate.isEnabled())

    def test_open_curve_error_warns(self) -> None:
        page = self._make_page()

        def fail(_path):
            raise ValueError("bad curve")

        page._load_buffer_curve = fail
        with patch.object(QMessageBox, "warning") as mock_warn:
            page._open_curve_path(Path("bad.csv"))
        self.assertTrue(mock_warn.called)
        self.assertIsNone(page._curve_data)
        self.assertFalse(page.btn_calculate.isEnabled())

    def test_build_payload_matches_core_contract(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        payload = page._build_payload()
        self.assertEqual(set(payload), {"curve", "impact", "options"})
        self.assertEqual(payload["impact"]["mass_kg"], 12.0)
        self.assertEqual(payload["options"]["time_samples"], 200)
        self.assertEqual(len(payload["curve"]["loading"]), 3)

    def test_calculate_renders_results_and_enables_report(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page._curve_source = Path("curve.csv")
        page._calculate_buffer_energy = lambda _payload: _sample_result()
        page._on_calculate()
        self.assertIsNotNone(page._last_result)
        text = page.results_label.toPlainText()
        for keyword in ("最大压缩", "峰值", "吸收能量", "回弹", "接触时长"):
            self.assertIn(keyword, text)
        self.assertNotIn("--", page.metric_labels["initial_energy"].text())
        self.assertIn("总体结论", page.overall_verdict_label.text())
        self.assertIn("加载能量", page.energy_strip_label.text())
        self.assertIsNotNone(page.response_widget._response)
        self.assertTrue(page.btn_save_report.isEnabled())

    def test_render_tail_failure_resets_partial_ui(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page._calculate_buffer_energy = lambda _payload: _sample_result()

        def fail_report():
            raise KeyError("late render failure")

        page._build_report_lines = fail_report
        with patch.object(QMessageBox, "warning") as mock_warn:
            page._on_calculate()
        self.assertTrue(mock_warn.called)
        self.assertIsNone(page._last_result)
        self.assertIsNone(page._last_payload)
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertEqual(page.metric_labels["initial_energy"].text(), "--")
        self.assertEqual(page.overall_verdict_label.text(), "总体结论: 待计算")
        self.assertIn("计算未完成", page.results_label.toPlainText())
        self.assertIn("状态: 待仿真", page.workbench_status_label.text())
        self.assertNotIn("最大压缩:", page.workbench_status_label.text())

    def test_real_sample_calculates_end_to_end(self) -> None:
        page = self._make_page()
        page._load_sample("buffer_energy_case_01.csv")
        page._on_calculate()
        self.assertIsNotNone(page._last_result)
        self.assertIn("最大压缩", page.results_label.toPlainText())
        self.assertIn("曲线文件", page.workbench_status_label.text())
        self.assertIsNotNone(page._last_result["time_response"])

    def test_bottom_out_marks_peak_unjudgeable(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page._calculate_buffer_energy = lambda _payload: _sample_result(bottom_out=True)
        page._on_calculate()
        self.assertIn("不可判定", page.check_badges["peak_force_ok"].text())
        self.assertIn("触底", page.metric_labels["peak_force"].text())

    def test_input_change_disables_export_after_success(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page._calculate_buffer_energy = lambda _payload: _sample_result()
        page._on_calculate()
        self.assertTrue(page.btn_save_report.isEnabled())
        page._field_widgets["impact.mass_kg"].setText("13")
        self.app.processEvents()
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertEqual(page.metric_labels["initial_energy"].text(), "--")
        self.assertIn("状态: 待仿真", page.workbench_status_label.text())

    def test_response_combo_switches_widget_variable(self) -> None:
        page = self._make_page()
        page.response_widget.set_response(_sample_result()["time_response"])
        idx = page.response_var_combo.findData("F")
        page.response_var_combo.setCurrentIndex(idx)
        self.app.processEvents()
        self.assertEqual(page.response_widget.variable(), "F")

    def test_parameter_compare_and_clear(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page._calculate_buffer_energy = lambda _payload: _sample_result()
        page._on_calculate()
        self.assertEqual(page.compare_table.rowCount(), 9)
        self.assertGreaterEqual(page.compare_preview_table.rowCount(), 3)
        page._on_clear()
        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertFalse(page.btn_calculate.isEnabled())
        self.assertEqual(page.compare_preview_table.rowCount(), 0)
        self.assertTrue(page.results_label.toPlainText().startswith("执行计算后"))

    def test_report_lines_contain_required_disclaimers(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page._curve_source = Path("curve.csv")
        page._calculate_buffer_energy = lambda _payload: _sample_result()
        page._on_calculate()
        text = "\n".join(page._build_report_lines())
        for keyword in ("能量法", "应变率", "重力", "回弹", "卸载段简化假设"):
            self.assertIn(keyword, text)
        self.assertIn("缓冲块吸能仿真", page.report_preview.toPlainText())

    def test_save_load_input_conditions_roundtrip(self) -> None:
        page = self._make_page()
        page._field_widgets["impact.mass_kg"].setText("99.5")
        page._field_widgets["impact.initial_velocity_m_s"].setText("3.21")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "buffer.json"
            page._write_input_conditions(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["module"], "buffer_energy")
            self.assertEqual(data["version"], 1)
            self.assertIn("inputs", data)
            self.assertIn("ui_state", data)
            self.assertNotIn("fields", data)
            page._field_widgets["impact.mass_kg"].setText("0")
            page._field_widgets["impact.initial_velocity_m_s"].setText("0")
            page._read_input_conditions(path)
        self.assertEqual(page._field_widgets["impact.mass_kg"].text(), "99.5")
        self.assertEqual(page._field_widgets["impact.initial_velocity_m_s"].text(), "3.21")
        self.assertFalse(page.btn_save_report.isEnabled())

    def test_example_input_conditions_use_current_snapshot_format(self) -> None:
        data = json.loads(
            Path("examples/buffer_energy_input_conditions.json").read_text(encoding="utf-8")
        )

        self.assertEqual(data["module"], "buffer_energy")
        self.assertEqual(data["version"], 1)
        self.assertIn("inputs", data)
        self.assertIn("ui_state", data)
        self.assertNotIn("fields", data)
        self.assertEqual(data["inputs"]["impact"]["mass_kg"], "12.0")
        self.assertEqual(data["inputs"]["options"]["time_samples"], "200")

    def test_apply_input_data_uses_inputs_not_removed_flat_fields(self) -> None:
        page = self._make_page()
        snapshot = {
            "module": "buffer_energy",
            "version": 1,
            "fields": {
                "impact.mass_kg": "1.0",
                "impact.initial_velocity_m_s": "1.0",
            },
            "inputs": {
                "impact": {
                    "mass_kg": "22.5",
                    "initial_velocity_m_s": "4.2",
                },
                "options": {
                    "time_samples": "120",
                },
            },
            "ui_state": {
                "curve_source": "",
            },
        }

        page._apply_input_data(snapshot)

        self.assertEqual(page._field_widgets["impact.mass_kg"].text(), "22.5")
        self.assertEqual(page._field_widgets["impact.initial_velocity_m_s"].text(), "4.2")
        self.assertEqual(page._field_widgets["options.time_samples"].text(), "120")

    def _assert_live_error_for_invalid_numeric(self, field_id: str) -> None:
        page = self._make_page()
        widget = page._field_widgets[field_id]
        error = page._field_error_labels[field_id]
        self.assertTrue(error.isHidden())
        page._curve_data = _sample_curve()
        page.btn_calculate.setEnabled(True)

        widget.setText("inf")
        self.assertFalse(error.isHidden())
        self.assertTrue(error.text())
        self.assertIn(widget.property("fieldError"), (True, "true"))
        self.assertTrue(page.btn_calculate.isEnabled())

        widget.setText("nan")
        self.assertFalse(error.isHidden())
        self.assertIn("有效数字", error.text())
        self.assertIn(widget.property("fieldError"), (True, "true"))
        self.assertTrue(page.btn_calculate.isEnabled())

        widget.setText("abc")
        self.assertFalse(error.isHidden())
        self.assertIn("有效数字", error.text())
        self.assertIn(widget.property("fieldError"), (True, "true"))
        self.assertTrue(page.btn_calculate.isEnabled())

        widget.setText("1e999")
        self.assertFalse(error.isHidden())
        self.assertIn("有限", error.text())
        self.assertIn(widget.property("fieldError"), (True, "true"))
        self.assertTrue(page.btn_calculate.isEnabled())

        widget.setText("0")
        self.assertFalse(error.isHidden())
        self.assertIn(">", error.text())
        self.assertTrue(page.btn_calculate.isEnabled())

        widget.setText(page._field_specs[field_id].default)
        self.assertTrue(error.isHidden())
        self.assertIn(widget.property("fieldError"), (False, "false", None))
        self.assertTrue(page.btn_calculate.isEnabled())

    def test_available_stroke_live_rejects_inf_nan_and_non_numeric(self) -> None:
        self._assert_live_error_for_invalid_numeric("impact.available_stroke_mm")

    def test_allowable_peak_live_rejects_inf_nan_and_non_numeric(self) -> None:
        self._assert_live_error_for_invalid_numeric("impact.allowable_peak_force_n")

    def test_calculate_with_invalid_stroke_focuses_field_and_keeps_button(self) -> None:
        page = self._make_page()
        page._curve_data = _sample_curve()
        page.btn_calculate.setEnabled(True)
        page._field_widgets["impact.available_stroke_mm"].setText("inf")
        page._field_widgets["impact.allowable_peak_force_n"].setText("abc")

        with patch.object(QMessageBox, "warning", side_effect=AssertionError("no dialog")):
            page._on_calculate()

        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertTrue(page.btn_calculate.isEnabled())
        stroke_error = page._field_error_labels["impact.available_stroke_mm"]
        peak_error = page._field_error_labels["impact.allowable_peak_force_n"]
        self.assertFalse(stroke_error.isHidden())
        self.assertFalse(peak_error.isHidden())
        self.assertEqual(page.chapter_list.currentRow(), 2)
        self.assertIn("字段需要修正", page.info_label.text())


class BufferEnergyMainWindowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_module_registered_in_mainwindow(self) -> None:
        from app.ui.main_window import MainWindow

        win = MainWindow()
        names = [name for name, _factory in win._page_factories]
        self.assertIn("缓冲块吸能仿真", names)

    def test_lazy_construct_buffer_page(self) -> None:
        from app.ui.main_window import MainWindow

        win = MainWindow()
        index = next(
            i for i, (name, _factory) in enumerate(win._page_factories)
            if name == "缓冲块吸能仿真"
        )
        self.assertIsNone(win._pages[index])
        win.module_list.setCurrentRow(index)
        self.app.processEvents()
        self.assertEqual(win.stack.currentIndex(), index)
        page = win._ensure_page(index)
        self.assertIsNotNone(page)
        self.assertEqual(page.__class__.__name__, "BufferEnergyPage")


if __name__ == "__main__":
    unittest.main()
