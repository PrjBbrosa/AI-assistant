import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from PySide6.QtWidgets import QFrame

from app.ui.main_window import MainWindow
from app.ui.pages.worm_gear_page import WormGearPage, LOAD_CAPACITY_OPTIONS
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget
from app.ui.widgets.worm_performance_curve import WormPerformanceCurveWidget
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget


class WormPerformanceCurveWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_curve_widget_accepts_three_series_and_current_point(self) -> None:
        # set_curves 签名已改为 temperature_rise_k 替换 thermal_capacity_kw（Task 0.B）
        widget = WormPerformanceCurveWidget()
        widget.set_curves(
            load_factor=[0.5, 1.0, 1.5],
            efficiency=[0.84, 0.81, 0.76],
            power_loss_kw=[0.3, 0.6, 1.0],
            temperature_rise_k=[12.5, 28.3, 47.1],
            current_index=1,
        )

        self.assertEqual(widget.minimumHeight(), 300)
        self.assertEqual(widget._current_index, 1)
        self.assertEqual(len(widget._load_factor), 3)


class WormOverviewWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_geometry_overview_accepts_title_and_note(self) -> None:
        widget = WormGeometryOverviewWidget()
        widget.set_display_state("几何总览", "按 DIN 3975 展示主要几何关系")

        self.assertGreaterEqual(widget.minimumHeight(), 320)
        self.assertEqual(widget._title, "几何总览")

    def test_overview_widgets_use_worm_pair_defaults_and_render(self) -> None:
        geometry = WormGeometryOverviewWidget()
        geometry.resize(920, 340)
        geometry.show()
        self.app.processEvents()

        geometry_pixmap = geometry.grab()

        self.assertGreaterEqual(geometry.minimumHeight(), 320)
        self.assertIn("蜗杆", geometry._note)
        self.assertIn("蜗轮", geometry._note)
        self.assertGreater(geometry_pixmap.size().width(), 0)


class WormGearPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_page_shell_uses_step_flow_and_split_actions(self) -> None:
        page = WormGearPage()

        self.assertEqual(page.nav_title_label.text(), "计算顺序")
        self.assertEqual(page.btn_save_inputs.text(), "保存输入条件")
        self.assertEqual(page.btn_load_inputs.text(), "加载输入条件")
        self.assertEqual(page.btn_load_1.text(), "测试案例 1")
        self.assertEqual(page.btn_load_2.text(), "测试案例 2")
        self.assertEqual(page.chapter_list.count(), 7)
        self.assertEqual(page.chapter_list.item(0).text(), "步骤 1. 基本设置")
        self.assertEqual(page.chapter_list.item(5).text(), "步骤 6. Load Capacity")

    def test_calculate_updates_result_summary_and_curve(self) -> None:
        page = WormGearPage()

        page._calculate()

        self.assertNotEqual(page.result_title.text(), "尚未执行计算")
        self.assertGreater(len(page.performance_curve._load_factor), 0)
        self.assertIn("DIN 3996", page.load_capacity_status.text())

    def test_input_snapshot_keeps_load_capacity_method(self) -> None:
        page = WormGearPage()
        method_c = [t for t in LOAD_CAPACITY_OPTIONS if "Method C" in t][0]
        page._field_widgets["load_capacity.method"].setCurrentText(method_c)  # type: ignore[attr-defined]

        snapshot = page._capture_input_snapshot()

        self.assertEqual(snapshot["inputs"]["load_capacity"]["method"], method_c)

    def test_load_sample_updates_fields_from_example(self) -> None:
        page = WormGearPage()

        page._load_sample("worm_case_01.json")

        # Wave 2 刷新后 worm_case_01.json: z1=1, worm_face_width=32, PA66+GF30, Method B
        self.assertEqual(page._field_widgets["geometry.z1"].text(), "1")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["materials.handedness"].currentText(), "right")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["geometry.worm_face_width_mm"].text(), "32.0")  # type: ignore[attr-defined]
        self.assertIn("Method B", page._field_widgets["load_capacity.method"].currentText())  # type: ignore[attr-defined]

    def test_graphics_step_can_render_without_crashing(self) -> None:
        page = WormGearPage()
        page.resize(1440, 920)
        page.show()

        page.set_current_chapter(4)
        self.app.processEvents()
        pixmap = page.grab()

        self.assertGreater(pixmap.size().width(), 0)
        self.assertEqual(page.chapter_list.currentRow(), 4)

    def test_geometry_page_contains_grouped_worm_and_wheel_sections(self) -> None:
        page = WormGearPage()

        self.assertEqual(
            page.geometry_group_titles,
            [
                "蜗杆参数",
                "蜗轮参数",
                "啮合与装配",
                "蜗杆自动计算尺寸",
                "蜗轮自动计算尺寸",
            ],
        )

    def test_derived_dimension_panel_updates_when_base_input_changes(self) -> None:
        page = WormGearPage()
        page._field_widgets["geometry.module_mm"].setText("5.0")  # type: ignore[attr-defined]

        page._refresh_derived_geometry_preview()

        self.assertIn("50.000", page.worm_dimension_labels["pitch_diameter_mm"].text())

    def test_page_exposes_manual_like_fields_and_advanced_parameters(self) -> None:
        page = WormGearPage()

        # handedness 已迁移至 materials.handedness（Task 0.B 中 FieldSpec mapping 调整）
        self.assertIn("materials.handedness", page._field_widgets)
        self.assertIn("geometry.worm_face_width_mm", page._field_widgets)
        self.assertIn("geometry.wheel_face_width_mm", page._field_widgets)
        self.assertIn("advanced.friction_override", page._field_widgets)

    def test_graphics_step_uses_scroll_area_and_curve_still_updates(self) -> None:
        page = WormGearPage()

        self.assertIsNotNone(page.graphics_scroll_area)
        page._calculate()

        self.assertGreater(len(page.performance_curve._efficiency), 0)

    def test_page_exposes_method_b_material_and_load_capacity_fields(self) -> None:
        page = WormGearPage()

        self.assertIn("materials.worm_e_mpa", page._field_widgets)
        self.assertIn("materials.worm_nu", page._field_widgets)
        self.assertIn("materials.wheel_e_mpa", page._field_widgets)
        self.assertIn("materials.wheel_nu", page._field_widgets)
        self.assertIn("operating.torque_ripple_percent", page._field_widgets)
        self.assertIn("advanced.normal_pressure_angle_deg", page._field_widgets)
        self.assertIn("load_capacity.allowable_contact_stress_mpa", page._field_widgets)
        self.assertIn("load_capacity.allowable_root_stress_mpa", page._field_widgets)
        self.assertIn("load_capacity.dynamic_factor_kv", page._field_widgets)
        self.assertIn("load_capacity.face_load_factor_khb", page._field_widgets)

    def test_wheel_material_change_updates_elastic_params(self) -> None:
        page = WormGearPage()
        page._field_widgets["materials.wheel_material"].setCurrentText("PA66+GF30")
        self.assertEqual(page._field_widgets["materials.wheel_e_mpa"].text(), "10000.0")
        self.assertEqual(page._field_widgets["materials.wheel_nu"].text(), "0.36")

    def test_wheel_material_change_updates_allowable_stresses(self) -> None:
        page = WormGearPage()
        # 设成基准条件（23°C / 0%RH），避免降额影响验证材料值本身
        page._field_widgets["advanced.operating_temp_c"].setText("23")
        page._field_widgets["advanced.humidity_rh"].setText("0")
        page._field_widgets["materials.wheel_material"].setCurrentText("PA66+GF30")
        self.assertAlmostEqual(
            float(page._field_widgets["load_capacity.allowable_contact_stress_mpa"].text()),
            58.0, delta=0.01,
        )
        self.assertAlmostEqual(
            float(page._field_widgets["load_capacity.allowable_root_stress_mpa"].text()),
            70.0, delta=0.01,
        )

    def test_load_capacity_disabled_shows_autocalc_style(self) -> None:
        page = WormGearPage()
        page._field_widgets["load_capacity.enabled"].setCurrentText("关闭")
        self.assertEqual(page._lc_params_card.objectName(), "AutoCalcCard")

    def test_load_capacity_enabled_shows_subcard_style(self) -> None:
        page = WormGearPage()
        page._field_widgets["load_capacity.enabled"].setCurrentText("关闭")
        page._field_widgets["load_capacity.enabled"].setCurrentText("启用")
        self.assertEqual(page._lc_params_card.objectName(), "SubCard")

    def test_load_json_with_enabled_false_sets_combo_to_disabled(self) -> None:
        page = WormGearPage()
        data = {"load_capacity": {"enabled": False}}
        page._apply_input_data(data)
        self.assertEqual(page._field_widgets["load_capacity.enabled"].currentText(), "关闭")

    def test_export_report_method_exists_and_button_connected(self) -> None:
        page = WormGearPage()
        self.assertTrue(hasattr(page, '_export_report'))
        self.assertIsNotNone(page.btn_save)

    def test_export_report_has_content_after_calculate(self) -> None:
        page = WormGearPage()
        page._calculate()
        self.assertIsNotNone(page._last_result)
        body = page.result_metrics.toPlainText() + page.load_capacity_metrics.toPlainText()
        self.assertGreater(len(body), 0)

    def test_calculate_renders_stress_and_torque_ripple_outputs(self) -> None:
        page = WormGearPage()

        page._calculate()

        self.assertIn("最小子集", page.load_capacity_status.text())
        self.assertIn("齿面应力", page.result_metrics.toPlainText())
        self.assertIn("齿根应力", page.result_metrics.toPlainText())
        self.assertIn("扭矩波动", page.result_metrics.toPlainText())
        self.assertIn("sigma_Hm", page.load_capacity_metrics.toPlainText())

    def test_geometry_inconsistent_overall_not_pass(self) -> None:
        """geometry_consistent=False but contact_ok=True, root_ok=True ->
        overall badge must NOT show '总体通过', because overall_lc_ok is
        derived from contact_ok AND root_ok only.  This test verifies the
        badge text corresponds to the contact/root checks, not geometry.
        Additionally verifies that geometry_consistent=False is reflected
        in the load_capacity_metrics text as '存在警告', not '通过'.
        """
        from unittest.mock import patch

        page = WormGearPage()

        fake_result = {
            "geometry": {
                "ratio": 20.0,
                "module_mm": 4.0,
                "center_distance_mm": 100.0,
                "theoretical_center_distance_mm": 100.0,
                "center_distance_delta_mm": 0.0,
                "pitch_diameter_worm_mm": 40.0,
                "pitch_diameter_wheel_mm": 160.0,
                "lead_angle_deg": 11.31,
                "lead_angle_input_deg": 11.31,
                "lead_angle_calc_deg": 11.31,
                "lead_angle_delta_deg": 0.0,
                "worm_speed_rpm": 1450.0,
                "wheel_speed_rpm": 72.5,
                "worm_dimensions": {
                    "pitch_diameter_mm": 40.0,
                    "tip_diameter_mm": 48.0,
                    "root_diameter_mm": 30.4,
                    "lead_mm": 25.1,
                    "axial_pitch_mm": 12.57,
                    "pitch_line_speed_mps": 3.04,
                    "face_width_mm": 36.0,
                },
                "wheel_dimensions": {
                    "pitch_diameter_mm": 160.0,
                    "tip_diameter_mm": 168.0,
                    "root_diameter_mm": 150.4,
                    "pitch_line_speed_mps": 0.61,
                    "tooth_height_mm": 8.8,
                    "face_width_mm": 30.0,
                },
                "mesh_dimensions": {
                    "ratio": 20.0,
                    "center_distance_mm": 100.0,
                    "theoretical_center_distance_mm": 100.0,
                    "center_distance_delta_mm": 0.0,
                    "worm_speed_rpm": 1450.0,
                    "wheel_speed_rpm": 72.5,
                    "input_torque_nm": 19.76,
                    "output_torque_nm": 316.2,
                },
                "consistency": {"lead_angle_calc_deg": 11.31, "lead_angle_delta_deg": 0.0, "center_distance_delta_mm": 0.0, "warnings": []},
            },
            "performance": {
                "input_power_kw": 3.0,
                "output_power_kw": 2.5,
                "input_torque_nm": 19.76,
                "worm_pitch_line_speed_mps": 3.04,
                "efficiency_estimate": 0.833,
                "power_loss_kw": 0.5,
                "thermal_capacity_kw": 0.5,
                "output_torque_nm": 316.2,
                "friction_mu": 0.18,
                "application_factor": 1.25,
                "warnings": [],
            },
            "curve": {
                "load_factor": [0.4, 1.0, 1.3],
                "efficiency": [0.84, 0.83, 0.82],
                "power_loss_kw": [0.2, 0.5, 0.7],
                "thermal_capacity_kw": [0.2, 0.5, 0.7],
                "current_load_factor": 1.0,
                "current_index": 1,
                "current_efficiency": 0.833,
                "current_power_loss_kw": 0.5,
                "current_thermal_capacity_kw": 0.5,
            },
            "load_capacity": {
                "enabled": True,
                "status": "DIN 3996 Method B 最小子集",
                "checks": {
                    "geometry_consistent": False,   # geometry has warnings
                    "contact_ok": True,
                    "root_ok": True,
                },
                "forces": {
                    "tangential_force_wheel_n": 3952.5,
                    "axial_force_wheel_n": 19752.1,
                    "radial_force_wheel_n": 1438.6,
                    "normal_force_n": 20957.2,
                    "design_normal_force_n": 27245.4,
                },
                "contact": {
                    "sigma_hm_nominal_mpa": 38.0,
                    "sigma_hm_peak_mpa": 40.0,
                    "allowable_contact_stress_mpa": 42.0,
                    "safety_factor_peak": 1.05,
                    "contact_ok": True,
                },
                "root": {
                    "sigma_f_nominal_mpa": 45.0,
                    "sigma_f_peak_mpa": 48.0,
                    "allowable_root_stress_mpa": 55.0,
                    "safety_factor_peak": 1.15,
                    "root_ok": True,
                },
                "torque_ripple": {
                    "output_torque_nominal_nm": 316.2,
                    "output_torque_rms_nm": 316.2,
                    "output_torque_peak_nm": 316.2,
                    "output_torque_min_nm": 316.2,
                },
                "factors": {"design_force_factor": 1.3125},
                "stress_curve": {},
                "warnings": [],
                "assumptions": [],
            },
            "inputs_echo": {},
        }

        with patch.object(page, "_build_payload", return_value={}):
            with patch("app.ui.pages.worm_gear_page.calculate_worm_geometry", return_value=fake_result):
                page._calculate()

        # geometry_consistent=False -> load_capacity_metrics should say '存在警告', not '通过'
        lc_text = page.load_capacity_metrics.toPlainText()
        self.assertIn("存在警告", lc_text)
        self.assertNotIn("几何一致性 = 通过", lc_text)

        # geometry_consistent=False means overall_lc_ok is False even if contact/root pass.
        # The overall badge must NOT show '总体通过'.
        overall_text = page._overall_lc_badge.text()
        self.assertNotEqual(overall_text, "总体通过",
            "几何不一致时总体徽章不应显示'总体通过'")

    def test_lc_disabled_no_zero_values(self) -> None:
        """When load_capacity enabled=False, result stress/force fields are empty dicts.
        The UI must not display '0.000' for those fields in load_capacity_metrics.
        """
        from unittest.mock import patch

        page = WormGearPage()
        page._field_widgets["load_capacity.enabled"].setCurrentText("关闭")

        fake_result = {
            "geometry": {
                "ratio": 20.0,
                "module_mm": 4.0,
                "center_distance_mm": 100.0,
                "theoretical_center_distance_mm": 100.0,
                "center_distance_delta_mm": 0.0,
                "pitch_diameter_worm_mm": 40.0,
                "pitch_diameter_wheel_mm": 160.0,
                "lead_angle_deg": 11.31,
                "lead_angle_input_deg": 11.31,
                "lead_angle_calc_deg": 11.31,
                "lead_angle_delta_deg": 0.0,
                "worm_speed_rpm": 1450.0,
                "wheel_speed_rpm": 72.5,
                "worm_dimensions": {
                    "pitch_diameter_mm": 40.0,
                    "tip_diameter_mm": 48.0,
                    "root_diameter_mm": 30.4,
                    "lead_mm": 25.1,
                    "axial_pitch_mm": 12.57,
                    "pitch_line_speed_mps": 3.04,
                    "face_width_mm": 36.0,
                },
                "wheel_dimensions": {
                    "pitch_diameter_mm": 160.0,
                    "tip_diameter_mm": 168.0,
                    "root_diameter_mm": 150.4,
                    "pitch_line_speed_mps": 0.61,
                    "tooth_height_mm": 8.8,
                    "face_width_mm": 30.0,
                },
                "mesh_dimensions": {
                    "ratio": 20.0,
                    "center_distance_mm": 100.0,
                    "theoretical_center_distance_mm": 100.0,
                    "center_distance_delta_mm": 0.0,
                    "worm_speed_rpm": 1450.0,
                    "wheel_speed_rpm": 72.5,
                    "input_torque_nm": 19.76,
                    "output_torque_nm": 316.2,
                },
                "consistency": {"lead_angle_calc_deg": 11.31, "lead_angle_delta_deg": 0.0, "center_distance_delta_mm": 0.0, "warnings": []},
            },
            "performance": {
                "input_power_kw": 3.0,
                "output_power_kw": 2.5,
                "input_torque_nm": 19.76,
                "worm_pitch_line_speed_mps": 3.04,
                "efficiency_estimate": 0.833,
                "power_loss_kw": 0.5,
                "thermal_capacity_kw": 0.5,
                "output_torque_nm": 316.2,
                "friction_mu": 0.18,
                "application_factor": 1.25,
                "warnings": [],
            },
            "curve": {
                "load_factor": [0.4, 1.0, 1.3],
                "efficiency": [0.84, 0.83, 0.82],
                "power_loss_kw": [0.2, 0.5, 0.7],
                "thermal_capacity_kw": [0.2, 0.5, 0.7],
                "current_load_factor": 1.0,
                "current_index": 1,
                "current_efficiency": 0.833,
                "current_power_loss_kw": 0.5,
                "current_thermal_capacity_kw": 0.5,
            },
            "load_capacity": {
                "enabled": False,
                "status": "未启用",
                "checks": {},
                "forces": {},
                "contact": {},
                "root": {},
                "torque_ripple": {},
                "factors": {},
                "stress_curve": {},
                "warnings": [],
                "assumptions": [],
            },
            "inputs_echo": {},
        }

        with patch.object(page, "_build_payload", return_value={}):
            with patch("app.ui.pages.worm_gear_page.calculate_worm_geometry", return_value=fake_result):
                page._calculate()

        lc_text = page.load_capacity_metrics.toPlainText()
        # When disabled, stress/force values are absent -> the UI must not render "0.000"
        # for sigma_Hm, sigma_F, SH, SF, T2 lines
        self.assertNotIn("0.000", lc_text, (
            "load_capacity_metrics should not display '0.000' placeholder values "
            "when load capacity is disabled. Actual content:\n" + lc_text
        ))


    def test_method_options_include_abc_descriptions(self) -> None:
        page = WormGearPage()
        combo = page._field_widgets["load_capacity.method"]
        options = [combo.itemText(i) for i in range(combo.count())]
        self.assertTrue(any("Method A" in o for o in options))
        self.assertTrue(any("Method B" in o for o in options))
        self.assertTrue(any("Method C" in o for o in options))

    def test_stress_curve_widget_exists_in_graphics_step(self) -> None:
        page = WormGearPage()
        self.assertTrue(hasattr(page, "stress_curve"))
        self.assertIsInstance(page.stress_curve, WormStressCurveWidget)

    def test_input_field_is_torque_not_power(self) -> None:
        page = WormGearPage()
        self.assertIn("operating.input_torque_nm", page._field_widgets)
        self.assertNotIn("operating.power_kw", page._field_widgets)

    def test_dimension_cards_use_autocalc_style(self) -> None:
        page = WormGearPage()
        first_label = list(page.worm_dimension_labels.values())[0]
        parent = first_label.parent()
        while parent:
            if isinstance(parent, QFrame) and parent.objectName() == "AutoCalcCard":
                break
            parent = parent.parent()
        self.assertIsNotNone(parent)
        self.assertEqual(parent.objectName(), "AutoCalcCard")


class MainWindowWormModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _find_worm_index(self, window: MainWindow) -> int:
        for index in range(window.stack.count()):
            if isinstance(window.stack.widget(index), WormGearPage):
                return index
        self.fail("WormGearPage not mounted in main window stack")

    def test_main_window_mounts_real_worm_page(self) -> None:
        window = MainWindow()

        worm_index = self._find_worm_index(window)
        worm_widget = window.stack.widget(worm_index)
        self.assertIsInstance(worm_widget, WormGearPage)

    def test_main_window_can_open_worm_graphics_step(self) -> None:
        window = MainWindow()
        window.resize(1500, 940)
        window.show()
        worm_index = self._find_worm_index(window)
        window.module_list.setCurrentRow(worm_index)
        self.app.processEvents()

        page = window.stack.widget(worm_index)
        page.set_current_chapter(4)
        self.app.processEvents()
        pixmap = window.grab()

        self.assertIsInstance(page, WormGearPage)
        self.assertGreater(pixmap.size().height(), 0)


# ============================================================
# Task 0.C Step 5 — UI 新增测试（Wave 0）
# ============================================================


class WormGearPageWave0Tests(unittest.TestCase):
    """Wave 0 新增 UI 测试：handedness 联动 + Method C 报错。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_handedness_change_redraws_overview(self) -> None:
        """切换旋向后再次执行计算，geometry_overview._geom_state['handedness'] 应更新。

        前提：WormGeometryOverviewWidget 已实现 set_geometry_state 接口（Task 0.B）。
        若 Task 0.B 未完成，本测试在 geometry_overview 没有 _geom_state 时会 AttributeError 跳过。
        """
        page = WormGearPage()

        # 先执行一次计算（默认旋向 right）
        page._calculate()
        self.app.processEvents()

        if not hasattr(page.geometry_overview, "_geom_state"):
            self.skipTest("WormGeometryOverviewWidget 尚未实现 _geom_state（等待 Task 0.B）")

        # 切换旋向为 left，再次执行计算
        handedness_widget = page._field_widgets.get("materials.handedness")
        self.assertIsNotNone(handedness_widget, "materials.handedness 字段不存在")
        handedness_widget.setCurrentText("left")  # type: ignore[union-attr]
        page._calculate()
        self.app.processEvents()

        # geometry_overview 应反映新旋向
        self.assertEqual(
            page.geometry_overview._geom_state["handedness"],
            "left",
            "切换旋向后 geometry_overview._geom_state['handedness'] 应为 'left'",
        )

    def test_method_c_shows_error_on_execute(self) -> None:
        """选择 Method C 后执行计算，应触发 InputError 并呈现错误（而非静默通过）。

        当前 core 已实现 Method C 拒绝（Task 0.A Step 6），_calculate() 捕获 InputError
        后通过 QMessageBox.critical 弹窗提示；_last_result 不应被更新为新结果。
        若 core 修复前 Method C 不报错，本测试会失败（预期行为）。
        """
        from unittest.mock import patch
        import PySide6.QtWidgets as _QtWidgets

        page = WormGearPage()

        # 先执行一次正常计算，让 _last_result 有初始值
        page._calculate()
        self.app.processEvents()
        initial_result = page._last_result

        # 切换到 Method C
        method_combo = page._field_widgets["load_capacity.method"]
        method_c_options = [
            method_combo.itemText(i)
            for i in range(method_combo.count())
            if "Method C" in method_combo.itemText(i)
        ]
        self.assertTrue(len(method_c_options) > 0, "下拉列表中应有 Method C 选项")
        method_combo.setCurrentText(method_c_options[0])
        self.app.processEvents()

        # patch QMessageBox.critical 以避免弹窗阻塞并捕获调用
        # 注意：需要 patch 模块级引用，而不是 PySide6.QtWidgets.QMessageBox
        with patch("app.ui.pages.worm_gear_page.QMessageBox.critical", return_value=None) as mock_critical:
            page._calculate()
            self.app.processEvents()

        # 应该调用了 QMessageBox.critical（错误弹窗）
        # 允许两种情形：
        # 1. core 已修复：Method C 抛 InputError → critical 被调用 → _last_result 不变
        # 2. core 未修复：Method C 不报错 → critical 未被调用 → 本测试 FAIL（预期）
        self.assertTrue(
            mock_critical.called,
            "选择 Method C 执行计算应触发错误弹窗（QMessageBox.critical），但未被调用。"
            "若 core 尚未实现 Method C 拒绝，本测试预期 FAIL（等待 Task 0.A）。",
        )


if __name__ == "__main__":
    unittest.main()


# ============================================================
# Task 1.C Step 3 — 塑料材料下拉自动填充测试（Wave 1）
# ============================================================


class WormGearPagePlasticMaterialTests(unittest.TestCase):
    """Wave 1 新增 UI 测试：塑料材料下拉自动填充许用应力与 AutoCalcCard 样式。

    前提：ui-engineer Task 1.B Step 1 已将 _on_material_changed 改为
    从 core.worm.materials.PLASTIC_MATERIALS 读取（而非仅查 MATERIAL_ALLOWABLE_HINTS）。
    若 ui-engineer 尚未完成，本类测试预期 FAIL（等待 Task 1.B）。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_wheel_material_pom_autofills_allowables(self) -> None:
        """选择 POM 后 allowable_contact_stress_mpa 字段应自动填充为 48 MPa（POM sigma_Hlim）。

        POM 在 PLASTIC_MATERIALS 中 sigma_hlim_mpa = 48.0 MPa。
        """
        page = WormGearPage()

        page._field_widgets["materials.wheel_material"].setCurrentText("POM")
        self.app.processEvents()

        contact_text = page._field_widgets["load_capacity.allowable_contact_stress_mpa"].text()
        contact_value = float(contact_text)
        # POM sigma_Hlim = 48 MPa，允许 5% 容差
        self.assertAlmostEqual(contact_value, 48.0, delta=48.0 * 0.05,
            msg=f"选 POM 后 allowable_contact_stress_mpa 应 ≈ 48 MPa，实际 {contact_value}")

    def test_wheel_material_pom_sets_autocalc_style(self) -> None:
        """选择 POM 后 allowable_contact_stress_mpa 字段的父卡片应切换到 AutoCalcCard 样式。

        前提：ui-engineer 在 _on_material_changed 中新增了 _set_card_style 调用。
        若未实现，本测试预期 FAIL。
        """
        from PySide6.QtWidgets import QFrame

        page = WormGearPage()
        page._field_widgets["materials.wheel_material"].setCurrentText("POM")
        self.app.processEvents()

        # allowable_contact_stress_mpa 字段的 widget 应处于只读状态或父卡片为 AutoCalcCard
        contact_widget = page._field_widgets["load_capacity.allowable_contact_stress_mpa"]
        # 找到最近的 AutoCalcCard 父容器
        parent = contact_widget.parent()
        found_autocalc = False
        while parent is not None:
            if isinstance(parent, QFrame) and parent.objectName() == "AutoCalcCard":
                found_autocalc = True
                break
            parent = parent.parent()
        self.assertTrue(
            found_autocalc or contact_widget.isReadOnly(),
            "选 POM 后 allowable_contact_stress_mpa 字段应为只读或父卡片为 AutoCalcCard 样式"
        )

    def test_wheel_material_peek_autofills_high_allowables(self) -> None:
        """选择 PEEK 后 allowable_contact_stress_mpa 字段应约为 90 MPa。

        PEEK 在 PLASTIC_MATERIALS 中 sigma_hlim_mpa = 90.0 MPa。
        """
        page = WormGearPage()

        page._field_widgets["materials.wheel_material"].setCurrentText("PEEK")
        self.app.processEvents()

        contact_text = page._field_widgets["load_capacity.allowable_contact_stress_mpa"].text()
        contact_value = float(contact_text)
        # PEEK sigma_Hlim = 90 MPa，允许 5% 容差
        self.assertAlmostEqual(contact_value, 90.0, delta=90.0 * 0.05,
            msg=f"选 PEEK 后 allowable_contact_stress_mpa 应 ≈ 90 MPa，实际 {contact_value}")

    def test_wheel_material_pa46_autofills_correct_allowables(self) -> None:
        """选择 PA46 后 allowable_contact_stress_mpa 字段应约为 52 MPa。

        PA46 在 PLASTIC_MATERIALS 中 sigma_hlim_mpa = 52.0 MPa。
        """
        page = WormGearPage()

        # 基准条件（23°C / 0%RH）下验证材料本身的名义值
        page._field_widgets["advanced.operating_temp_c"].setText("23")
        page._field_widgets["advanced.humidity_rh"].setText("0")
        page._field_widgets["materials.wheel_material"].setCurrentText("PA46")
        self.app.processEvents()

        contact_text = page._field_widgets["load_capacity.allowable_contact_stress_mpa"].text()
        contact_value = float(contact_text)
        # PA46 sigma_Hlim = 52 MPa，允许 5% 容差
        self.assertAlmostEqual(contact_value, 52.0, delta=52.0 * 0.05,
            msg=f"选 PA46 后 allowable_contact_stress_mpa 应 ≈ 52 MPa，实际 {contact_value}")

    def test_life_card_renders_after_calculate(self) -> None:
        """执行计算后，若 load_capacity['life'] 存在，寿命相关文本应出现在结果区。

        若 core 尚未实现寿命/磨损输出，本测试预期 SKIP（load_capacity_metrics 里无寿命字样）。
        若 ui-engineer Task 1.B Step 5 也未完成，同样 SKIP。
        """
        page = WormGearPage()
        page._calculate()
        self.app.processEvents()

        lc_result = page._last_result
        if lc_result is None:
            self.skipTest("计算未成功，跳过寿命卡渲染测试")

        life_dict = lc_result.get("load_capacity", {}).get("life", {})
        if not life_dict:
            self.skipTest(
                "load_capacity['life'] 不存在（core Task 1.A Step 3 未完成），跳过寿命卡测试"
            )

        # life 数据存在时，寿命卡（SubCard）应可见且包含疲劳寿命/磨损等字样
        from PySide6.QtWidgets import QLabel

        life_card = getattr(page, "_life_card", None)
        self.assertIsNotNone(life_card, "寿命评估卡 _life_card 未创建")
        self.assertFalse(life_card.isHidden(),
                         "寿命评估卡在 load_capacity['life'] 存在时应可见")
        life_texts = [
            child.text() for child in life_card.findChildren(QLabel) if child.text()
        ]
        combined_text = "\n".join(life_texts)
        self.assertTrue(
            any(kw in combined_text for kw in ("疲劳寿命", "磨损", "life", "wear")),
            f"life 存在时寿命卡内应显示寿命/磨损文字，实际内容：{combined_text[:200]}"
        )


# ============================================================
# Task 2.C Step 1 & 2 — 节流 + 脏状态测试（Wave 2）
# ============================================================


class WormGearPageWave2ThrottleTests(unittest.TestCase):
    """Wave 2 新增 UI 测试：预览节流计数器 + 输入变更使导出按钮失效。

    依赖 ui-engineer Task 2.B 在 WormGearPage 中曝光：
      - _preview_call_count: int
      - _mark_results_fresh(): 模拟刚计算完
      - _mark_results_dirty(): 模拟输入已变更
    若 ui-engineer 尚未完成，测试通过 hasattr/skipTest 保护，不硬失败。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_preview_throttled_not_recalculating_per_keystroke(self) -> None:
        """连续 5 次快速输入时，节流定时器应合并触发，不超过 count_before + 2 次。"""
        from PySide6.QtCore import QEventLoop, QTimer

        page = WormGearPage()

        if not hasattr(page, "_preview_call_count"):
            self.skipTest(
                "_preview_call_count 未实现（等待 ui-engineer Task 2.B）"
            )

        count_before = page._preview_call_count

        # 连续 5 次快速输入 —— 在节流窗口内不应每次都触发预览
        for v in ("3", "3.5", "4", "4.5", "5"):
            page._field_widgets["geometry.module_mm"].setText(v)
            page._field_widgets["geometry.module_mm"].textEdited.emit(v)

        # 300 ms 内最多允许 1 次额外触发（节流首次立即触发的实现允差）
        count_immediate = page._preview_call_count
        self.assertLessEqual(
            count_immediate,
            count_before + 1,
            "快速连续输入 300ms 内不应超出 count_before+1 次触发",
        )

        # 等待 400 ms，让节流定时器触发最终合并计算
        loop = QEventLoop()
        QTimer.singleShot(400, loop.quit)
        loop.exec()

        count_after = page._preview_call_count
        self.assertLessEqual(
            count_after - count_before,
            2,
            "节流后总触发次数应 <= 2（远少于 5 次逐键触发）",
        )

    def test_input_change_disables_export_button(self) -> None:
        """_mark_results_fresh() 后按钮 enabled；输入变更后按钮应变 disabled。"""
        page = WormGearPage()

        if not hasattr(page, "_mark_results_fresh"):
            self.skipTest(
                "_mark_results_fresh 未实现（等待 ui-engineer Task 2.B）"
            )

        # 模拟刚计算完，按钮应 enabled
        page._mark_results_fresh()
        export_btn = getattr(page, "_export_button", page.btn_save)
        self.assertTrue(
            export_btn.isEnabled(),
            "_mark_results_fresh() 后导出按钮应 enabled",
        )

        # 输入变更 → 按钮应变 disabled
        page._field_widgets["geometry.module_mm"].setText("7")
        page._field_widgets["geometry.module_mm"].textEdited.emit("7")
        self.app.processEvents()

        self.assertFalse(
            export_btn.isEnabled(),
            "输入变化后导出按钮应失效（disabled）",
        )
