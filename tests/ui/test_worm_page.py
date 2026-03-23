import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.pages.worm_gear_page import WormGearPage
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget
from app.ui.widgets.worm_performance_curve import WormPerformanceCurveWidget


class WormPerformanceCurveWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_curve_widget_accepts_three_series_and_current_point(self) -> None:
        widget = WormPerformanceCurveWidget()
        widget.set_curves(
            load_factor=[0.5, 1.0, 1.5],
            efficiency=[0.84, 0.81, 0.76],
            power_loss_kw=[0.3, 0.6, 1.0],
            thermal_capacity_kw=[2.8, 3.4, 4.2],
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
        page._field_widgets["load_capacity.method"].setCurrentText("Niemann")  # type: ignore[attr-defined]

        snapshot = page._capture_input_snapshot()

        self.assertEqual(snapshot["inputs"]["load_capacity"]["method"], "Niemann")

    def test_load_sample_updates_fields_from_example(self) -> None:
        page = WormGearPage()

        page._load_sample("worm_case_01.json")

        self.assertEqual(page._field_widgets["geometry.z1"].text(), "2.0")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["geometry.handedness"].currentText(), "左旋")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["geometry.worm_face_width_mm"].text(), "36.0")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["load_capacity.method"].currentText(), "DIN 3996 Method B")  # type: ignore[attr-defined]

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

        self.assertIn("geometry.handedness", page._field_widgets)
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
        page._field_widgets["materials.wheel_material"].setCurrentText("PA66+GF30")
        self.assertEqual(page._field_widgets["load_capacity.allowable_contact_stress_mpa"].text(), "58.0")
        self.assertEqual(page._field_widgets["load_capacity.allowable_root_stress_mpa"].text(), "70.0")

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


class MainWindowWormModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_mounts_real_worm_page(self) -> None:
        window = MainWindow()

        worm_widget = window.stack.widget(3)
        self.assertIsInstance(worm_widget, WormGearPage)

    def test_main_window_can_open_worm_graphics_step(self) -> None:
        window = MainWindow()
        window.resize(1500, 940)
        window.show()
        window.module_list.setCurrentRow(3)
        self.app.processEvents()

        page = window.stack.widget(3)
        page.set_current_chapter(4)
        self.app.processEvents()
        pixmap = window.grab()

        self.assertIsInstance(page, WormGearPage)
        self.assertGreater(pixmap.size().height(), 0)


if __name__ == "__main__":
    unittest.main()
