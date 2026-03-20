import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.interference_fit_page import InterferenceFitPage


class InterferenceFitPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_page_exposes_din7190_core_fields_and_removes_process_only_fields(self) -> None:
        page = InterferenceFitPage()

        self.assertIn("loads.application_factor_ka", page._field_widgets)
        self.assertIn("loads.radial_force_required_n", page._field_widgets)
        self.assertIn("loads.bending_moment_required_nm", page._field_widgets)
        self.assertIn("geometry.shaft_inner_d_mm", page._field_widgets)
        self.assertIn("fit.mode", page._field_widgets)
        self.assertIn("fit.preferred_fit_name", page._field_widgets)
        self.assertIn("fit.shaft_upper_deviation_um", page._field_widgets)
        self.assertIn("fit.shaft_lower_deviation_um", page._field_widgets)
        self.assertIn("fit.hub_upper_deviation_um", page._field_widgets)
        self.assertIn("fit.hub_lower_deviation_um", page._field_widgets)
        self.assertIn("assembly.method", page._field_widgets)
        self.assertIn("assembly.room_temperature_c", page._field_widgets)
        self.assertIn("assembly.mu_press_in", page._field_widgets)
        self.assertIn("assembly.mu_press_out", page._field_widgets)
        self.assertIn("fretting.mode", page._field_widgets)
        self.assertIn("fretting.load_spectrum", page._field_widgets)
        self.assertIn("fretting.duty_severity", page._field_widgets)
        self.assertIn("fretting.surface_condition", page._field_widgets)
        self.assertIn("fretting.importance_level", page._field_widgets)
        self.assertIn("friction.mu_torque", page._field_widgets)
        self.assertIn("friction.mu_axial", page._field_widgets)
        self.assertNotIn("process.assembly_method", page._field_widgets)
        self.assertNotIn("process.temp_delta_c", page._field_widgets)
        self.assertNotIn("advanced.repeated_load_mode", page._field_widgets)

    def test_build_payload_uses_new_friction_fields(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["loads.application_factor_ka"].setText("1.35")  # type: ignore[attr-defined]
        page._field_widgets["geometry.shaft_inner_d_mm"].setText("12")  # type: ignore[attr-defined]
        page._field_widgets["friction.mu_torque"].setText("0.16")  # type: ignore[attr-defined]
        page._field_widgets["friction.mu_axial"].setText("0.12")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["loads"]["application_factor_ka"], 1.35)
        self.assertEqual(payload["geometry"]["shaft_inner_d_mm"], 12.0)
        self.assertEqual(payload["friction"]["mu_torque"], 0.16)
        self.assertEqual(payload["friction"]["mu_axial"], 0.12)
        self.assertNotIn("process", payload)

    def test_build_payload_includes_force_fit_assembly_fields(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["assembly.method"].setCurrentText("force_fit")  # type: ignore[attr-defined]
        page._field_widgets["assembly.mu_press_in"].setText("0.08")  # type: ignore[attr-defined]
        page._field_widgets["assembly.mu_press_out"].setText("0.06")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["assembly"]["method"], "force_fit")
        self.assertEqual(payload["assembly"]["mu_press_in"], 0.08)
        self.assertEqual(payload["assembly"]["mu_press_out"], 0.06)

    def test_build_payload_can_derive_interference_from_user_defined_deviations(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["fit.mode"].setCurrentText("偏差换算")  # type: ignore[attr-defined]
        page._field_widgets["fit.shaft_upper_deviation_um"].setText("35")  # type: ignore[attr-defined]
        page._field_widgets["fit.shaft_lower_deviation_um"].setText("20")  # type: ignore[attr-defined]
        page._field_widgets["fit.hub_upper_deviation_um"].setText("-10")  # type: ignore[attr-defined]
        page._field_widgets["fit.hub_lower_deviation_um"].setText("-20")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["fit"]["delta_min_um"], 30.0)
        self.assertEqual(payload["fit"]["delta_max_um"], 55.0)

    def test_build_payload_can_derive_interference_from_preferred_fit(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["geometry.shaft_d_mm"].setText("50")  # type: ignore[attr-defined]
        page._field_widgets["fit.mode"].setCurrentText("优选配合")  # type: ignore[attr-defined]
        page._field_widgets["fit.preferred_fit_name"].setCurrentText("H7/s6")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["fit"]["delta_min_um"], 18.0)
        self.assertEqual(payload["fit"]["delta_max_um"], 59.0)
        self.assertEqual(payload["fit_selection"]["mode"], "preferred_fit")
        self.assertEqual(payload["fit_selection"]["fit_name"], "H7/s6")

    def test_report_lines_include_gaping_and_mean_results(self) -> None:
        page = InterferenceFitPage()

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("p_r / p_b / p_gap" in line for line in report_lines))
        self.assertTrue(any("p_min / p_mean / p_max" in line for line in report_lines))
        self.assertIn("gaping_ok", page._check_badges)

    def test_report_lines_surface_combined_check_and_demand_breakdown(self) -> None:
        page = InterferenceFitPage()

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertIn("combined_ok", page._check_badges)
        self.assertTrue(any("p_req,T / p_req,Ax / p_req,comb / p_gap" in line for line in report_lines))

    def test_curve_points_help_marks_it_as_plotting_only_option(self) -> None:
        page = InterferenceFitPage()

        curve_points_widget = page._field_widgets["options.curve_points"]
        hint = page._widget_hints[curve_points_widget]

        self.assertIn("仅影响曲线显示", hint)

    def test_report_lines_include_fit_source_trace(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["fit.mode"].setCurrentText("偏差换算")  # type: ignore[attr-defined]
        page._field_widgets["fit.shaft_upper_deviation_um"].setText("35")  # type: ignore[attr-defined]
        page._field_widgets["fit.shaft_lower_deviation_um"].setText("20")  # type: ignore[attr-defined]
        page._field_widgets["fit.hub_upper_deviation_um"].setText("-10")  # type: ignore[attr-defined]
        page._field_widgets["fit.hub_lower_deviation_um"].setText("-20")  # type: ignore[attr-defined]

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("fit source" in line for line in report_lines))
        self.assertTrue(any("user_defined_deviations" in line for line in report_lines))

    def test_report_lines_include_selected_fit_trace(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["geometry.shaft_d_mm"].setText("50")  # type: ignore[attr-defined]
        page._field_widgets["fit.mode"].setCurrentText("优选配合")  # type: ignore[attr-defined]
        page._field_widgets["fit.preferred_fit_name"].setCurrentText("H7/s6")  # type: ignore[attr-defined]

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("preferred_fit" in line for line in report_lines))
        self.assertTrue(any("H7/s6" in line for line in report_lines))

    def test_report_lines_include_force_fit_assembly_trace(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["assembly.method"].setCurrentText("force_fit")  # type: ignore[attr-defined]
        page._field_widgets["assembly.mu_press_in"].setText("0.08")  # type: ignore[attr-defined]
        page._field_widgets["assembly.mu_press_out"].setText("0.06")  # type: ignore[attr-defined]

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("assembly method" in line for line in report_lines))
        self.assertTrue(any("press_in_force" in line for line in report_lines))

    def test_report_lines_include_fretting_section(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["fretting.mode"].setCurrentText("on")  # type: ignore[attr-defined]
        page._field_widgets["fretting.load_spectrum"].setCurrentText("reversing")  # type: ignore[attr-defined]
        page._field_widgets["fretting.duty_severity"].setCurrentText("heavy")  # type: ignore[attr-defined]
        page._field_widgets["fretting.surface_condition"].setCurrentText("dry")  # type: ignore[attr-defined]
        page._field_widgets["fretting.importance_level"].setCurrentText("critical")  # type: ignore[attr-defined]

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("Step 5 Fretting 风险评估" in line for line in report_lines))
        self.assertTrue(any("risk level" in line.lower() for line in report_lines))
        self.assertTrue(any("enhancement result" in line.lower() or "does not change" in line.lower() for line in report_lines))

    def test_report_lines_include_material_and_profile_source_trace(self) -> None:
        page = InterferenceFitPage()

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("shaft material preset" in line for line in report_lines))
        self.assertTrue(any("roughness profile source" in line for line in report_lines))

    def test_report_lines_include_hollow_shaft_geometry_and_model_semantics(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["geometry.shaft_inner_d_mm"].setText("18")  # type: ignore[attr-defined]

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("shaft inner diameter" in line.lower() for line in report_lines))
        self.assertTrue(any("hollow shaft" in line.lower() for line in report_lines))

    def test_build_payload_includes_fretting_fields(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["fretting.mode"].setCurrentText("on")  # type: ignore[attr-defined]
        page._field_widgets["fretting.load_spectrum"].setCurrentText("reversing")  # type: ignore[attr-defined]
        page._field_widgets["fretting.duty_severity"].setCurrentText("heavy")  # type: ignore[attr-defined]
        page._field_widgets["fretting.surface_condition"].setCurrentText("dry")  # type: ignore[attr-defined]
        page._field_widgets["fretting.importance_level"].setCurrentText("critical")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["fretting"]["mode"], "on")
        self.assertEqual(payload["fretting"]["load_spectrum"], "reversing")
        self.assertEqual(payload["fretting"]["duty_severity"], "heavy")
        self.assertEqual(payload["fretting"]["surface_condition"], "dry")
        self.assertEqual(payload["fretting"]["importance_level"], "critical")

    def test_apply_input_data_maps_legacy_repeated_load_switch_to_fretting_mode(self) -> None:
        page = InterferenceFitPage()

        page._apply_input_data(
            {
                "inputs": {
                    "geometry": {
                        "shaft_d_mm": "40",
                        "hub_outer_d_mm": "80",
                        "fit_length_mm": "45",
                    },
                    "fit": {
                        "delta_min_um": "20",
                        "delta_max_um": "45",
                    },
                    "materials": {
                        "shaft_e_mpa": "210000",
                        "shaft_nu": "0.30",
                        "shaft_yield_mpa": "600",
                        "hub_e_mpa": "210000",
                        "hub_nu": "0.30",
                        "hub_yield_mpa": "320",
                    },
                    "friction": {
                        "mu_torque": "0.14",
                        "mu_axial": "0.14",
                        "mu_assembly": "0.12",
                    },
                    "loads": {
                        "torque_required_nm": "350",
                        "axial_force_required_n": "0",
                        "radial_force_required_n": "0",
                        "bending_moment_required_nm": "0",
                        "application_factor_ka": "1.0",
                    },
                    "advanced": {
                        "repeated_load_mode": "on",
                    },
                }
            }
        )

        self.assertEqual(page._field_widgets["fretting.mode"].currentText(), "on")  # type: ignore[attr-defined]

    def test_apply_input_data_preserves_custom_raw_inputs_without_ui_state(self) -> None:
        page = InterferenceFitPage()

        page._apply_input_data(
            {
                "geometry": {
                    "shaft_d_mm": 40,
                    "hub_outer_d_mm": 80,
                    "fit_length_mm": 45,
                },
                "fit": {
                    "delta_min_um": 20,
                    "delta_max_um": 45,
                },
                "materials": {
                    "shaft_e_mpa": 199999,
                    "shaft_nu": 0.271,
                    "shaft_yield_mpa": 700,
                    "hub_e_mpa": 188888,
                    "hub_nu": 0.255,
                    "hub_yield_mpa": 333,
                },
                "roughness": {
                    "smoothing_factor": 0.67,
                    "shaft_rz_um": 9.0,
                    "hub_rz_um": 11.0,
                },
                "friction": {
                    "mu_torque": 0.14,
                    "mu_axial": 0.13,
                    "mu_assembly": 0.12,
                },
                "loads": {
                    "torque_required_nm": 350,
                    "axial_force_required_n": 1200,
                    "radial_force_required_n": 0,
                    "bending_moment_required_nm": 0,
                    "application_factor_ka": 1.2,
                },
                "assembly": {
                    "method": "force_fit",
                    "mu_press_in": 0.09,
                    "mu_press_out": 0.07,
                },
                "fretting": {
                    "mode": "on",
                },
            }
        )

        self.assertEqual(page._field_widgets["materials.shaft_material"].currentText(), "自定义")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["materials.hub_material"].currentText(), "自定义")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["materials.shaft_e_mpa"].text(), "199999")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["materials.hub_e_mpa"].text(), "188888")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["roughness.profile"].currentText(), "自定义k")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["roughness.smoothing_factor"].text(), "0.67")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["assembly.method"].currentText(), "force_fit")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["fretting.mode"].currentText(), "on")  # type: ignore[attr-defined]

    def test_roughness_chapter_has_dedicated_batch_warning_box(self) -> None:
        page = InterferenceFitPage()

        self.assertEqual(page.roughness_warning_box.objectName(), "WarningCard")  # type: ignore[attr-defined]

    def test_roughness_warning_box_mentions_batch_scatter_and_analysis_directions(self) -> None:
        page = InterferenceFitPage()

        warning_text = page.roughness_warning_text.text()  # type: ignore[attr-defined]

        self.assertIn("批量生产", warning_text)
        self.assertIn("压入散差", warning_text)
        self.assertIn("有效过盈", warning_text)
        self.assertIn("波纹度", warning_text)
        self.assertIn("润滑", warning_text)

    # ------------------------------------------------------------------
    # Tasks 7-14: friction-material linkage tests
    # ------------------------------------------------------------------

    def test_friction_sync_steel_steel_dry(self) -> None:
        """45钢/45钢 + 干摩擦 → 自动填入 0.15/0.12/0.12，RefBadge 可见且含来源文本。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.12")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.12")

        badge = page._ref_badges["friction.mu_torque"]
        self.assertFalse(badge.isHidden())
        self.assertIn("DIN 7190-1", badge.text())
        self.assertIn("钢/钢", badge.text())

    def test_friction_ref_badge_modified_on_manual_edit(self) -> None:
        """手改 mu_torque 后 RefBadge 显示"已修改（参考值 0.15）"。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        page._field_widgets["friction.mu_torque"].setText("0.16")

        badge = page._ref_badges["friction.mu_torque"]
        self.assertFalse(badge.isHidden())
        self.assertIn("已修改", badge.text())
        self.assertIn("0.15", badge.text())

    def test_friction_sync_custom_material_no_autofill(self) -> None:
        """轴材料切到"自定义"→ RefBadge 隐藏，摩擦字段值不变。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        page._field_widgets["materials.shaft_material"].setCurrentText("自定义")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertTrue(badge.isHidden())

    def test_friction_sync_surface_condition_change(self) -> None:
        """切换表面状态从干摩擦到轻油润滑 → 值更新。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")

        page._field_widgets["friction.surface_condition"].setCurrentText("轻油润滑")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.11")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.08")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.08")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertIn("DIN 7190-1", badge.text())

    def test_friction_sync_aluminum_aluminum(self) -> None:
        """铝合金/铝合金 + 干摩擦 → frozenset 相同材料正确查表。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("铝合金 6061-T6")
        page._field_widgets["materials.hub_material"].setCurrentText("铝合金 6061-T6")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.10")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.08")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.08")

    def test_load_legacy_json_no_surface_condition(self) -> None:
        """加载不含 surface_condition 的旧 JSON → 表面状态默认"自定义"，保留原始摩擦值。"""
        page = InterferenceFitPage()

        page._apply_input_data(
            {
                "inputs": {
                    "geometry": {"shaft_d_mm": "40", "hub_outer_d_mm": "80", "fit_length_mm": "45"},
                    "fit": {"delta_min_um": "20", "delta_max_um": "45"},
                    "materials": {
                        "shaft_e_mpa": "210000", "shaft_nu": "0.30", "shaft_yield_mpa": "600",
                        "hub_e_mpa": "210000", "hub_nu": "0.30", "hub_yield_mpa": "320",
                    },
                    "friction": {"mu_torque": "0.18", "mu_axial": "0.16", "mu_assembly": "0.14"},
                    "loads": {
                        "torque_required_nm": "350", "axial_force_required_n": "0",
                        "radial_force_required_n": "0", "bending_moment_required_nm": "0",
                        "application_factor_ka": "1.0",
                    },
                }
            }
        )

        self.assertEqual(
            page._field_widgets["friction.surface_condition"].currentText(),
            "自定义",
        )
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.18")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.16")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.14")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertTrue(badge.isHidden())

    def test_clear_resets_friction_and_shows_ref_badge(self) -> None:
        """清除参数 → 默认材料+干摩擦触发联动，RefBadge 重新出现。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("自定义")
        page._field_widgets["friction.mu_torque"].setText("0.99")

        page._clear()

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertFalse(badge.isHidden())
        self.assertIn("DIN 7190-1", badge.text())

    def test_load_json_with_surface_condition(self) -> None:
        """加载含 surface_condition 的 JSON → 下拉恢复，摩擦值与查表一致。"""
        page = InterferenceFitPage()

        page._apply_input_data(
            {
                "inputs": {
                    "geometry": {"shaft_d_mm": "40", "hub_outer_d_mm": "80", "fit_length_mm": "45"},
                    "fit": {"delta_min_um": "20", "delta_max_um": "45"},
                    "materials": {
                        "shaft_e_mpa": "210000", "shaft_nu": "0.30", "shaft_yield_mpa": "600",
                        "hub_e_mpa": "210000", "hub_nu": "0.30", "hub_yield_mpa": "320",
                    },
                    "friction": {"mu_torque": "0.11", "mu_axial": "0.08", "mu_assembly": "0.08"},
                    "loads": {
                        "torque_required_nm": "350", "axial_force_required_n": "0",
                        "radial_force_required_n": "0", "bending_moment_required_nm": "0",
                        "application_factor_ka": "1.0",
                    },
                },
                "ui_state": {
                    "friction.surface_condition": "轻油润滑",
                    "materials.shaft_material": "45钢",
                    "materials.hub_material": "45钢",
                },
            }
        )

        self.assertEqual(
            page._field_widgets["friction.surface_condition"].currentText(),
            "轻油润滑",
        )
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.11")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.08")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.08")


if __name__ == "__main__":
    unittest.main()
