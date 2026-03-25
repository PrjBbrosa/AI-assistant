import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_page import BoltPage
from core.bolt.calculator import InputError, calculate_vdi2230_core


def _raw_bolt_payload() -> dict:
    return {
        "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
        "tightening": {
            "alpha_A": 1.5,
            "mu_thread": 0.1,
            "mu_bearing": 0.12,
            "utilization": 0.85,
            "thread_flank_angle_deg": 60.0,
        },
        "loads": {
            "FA_max": 6000.0,
            "FQ_max": 600.0,
            "embed_loss": 600.0,
            "thermal_force_loss": 300.0,
            "slip_friction_coefficient": 0.2,
            "friction_interfaces": 1.0,
            "FM_min_input": 12000.0,
        },
        "stiffness": {
            "auto_compliance": True,
            "E_bolt": 210000.0,
            "E_clamped": 210000.0,
            "load_introduction_factor_n": 1.0,
        },
        "bearing": {
            "bearing_d_inner": 13.0,
            "bearing_d_outer": 22.0,
            "p_G_allow": 700.0,
        },
        "clamped": {
            "basic_solid": "cone",
            "surface_class": "fine",
            "total_thickness": 20.0,
            "D_A": 24.0,
        },
        "options": {
            "joint_type": "through",
            "check_level": "fatigue",
            "calculation_mode": "verify",
            "tightening_method": "angle",
            "surface_treatment": "cut",
        },
        "checks": {"yield_safety_operating": 1.15},
    }


def _vm_governing_payload() -> dict:
    data = _raw_bolt_payload()
    data["tightening"]["alpha_A"] = 1.8
    data["tightening"]["mu_thread"] = 0.4
    data["loads"]["FA_max"] = 40000.0
    data["loads"]["FQ_max"] = 0.0
    data["loads"]["FM_min_input"] = 24000.0
    data["options"] = {
        "calculation_mode": "verify",
        "tightening_method": "torque",
    }
    return data


class BoltPageStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_snapshot_round_trip_supports_standard_thread_labels(self) -> None:
        page = BoltPage()
        snapshot = page._capture_input_snapshot()

        clone = BoltPage()
        clone._apply_input_data(snapshot)

        self.assertEqual(clone._field_widgets["fastener.d"].currentText(), "M10")  # type: ignore[attr-defined]
        self.assertTrue(clone._field_widgets["fastener.p"].currentText().startswith("1.5"))  # type: ignore[attr-defined]

    def test_snapshot_persists_calculation_mode(self) -> None:
        page = BoltPage()
        page.calc_mode_combo.setCurrentIndex(1)
        snapshot = page._capture_input_snapshot()

        clone = BoltPage()
        clone._apply_input_data(snapshot)

        self.assertEqual(clone.calc_mode_combo.currentData(), "verify")

    def test_apply_raw_payload_restores_choice_selectors(self) -> None:
        page = BoltPage()

        page._apply_input_data(_raw_bolt_payload())

        self.assertEqual(page._field_widgets["elements.joint_type"].currentText(), "通孔螺栓连接")  # type: ignore[attr-defined]
        self.assertEqual(page.check_level_combo.currentData(), "fatigue")
        self.assertEqual(page.calc_mode_combo.currentData(), "verify")
        self.assertEqual(page._field_widgets["clamped.basic_solid"].currentText(), "锥体")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["clamped.surface_class"].currentText(), "精细 (Ra≈1.6μm)")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["assembly.tightening_method"].currentText(), "转角法")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["options.surface_treatment"].currentText(), "切削")  # type: ignore[attr-defined]

    def test_single_layer_custom_material_requires_alpha(self) -> None:
        page = BoltPage()
        page._set_check_level("thermal")
        page._apply_check_level_visibility()
        page._field_widgets["operating.bolt_material"].setCurrentText("自定义")  # type: ignore[attr-defined]
        page._field_widgets["operating.clamped_material"].setCurrentText("自定义")  # type: ignore[attr-defined]

        with self.assertRaisesRegex(InputError, "热膨胀系数"):
            page._build_payload()

    def test_multi_layer_custom_material_requires_alpha(self) -> None:
        page = BoltPage()
        page._field_widgets["clamped.part_count"].setCurrentText("2")  # type: ignore[attr-defined]
        page._on_part_count_changed()
        page._set_check_level("thermal")
        page._apply_check_level_visibility()
        page._field_widgets["clamped.layer_1.material"].setCurrentText("自定义")  # type: ignore[attr-defined]

        with self.assertRaisesRegex(InputError, "第1层热膨胀系数"):
            page._build_payload()

    def test_result_summary_and_report_use_sigma_vm_work_for_r5(self) -> None:
        page = BoltPage()
        payload = _vm_governing_payload()
        result = calculate_vdi2230_core(payload)
        stresses = result["stresses_mpa"]

        self.assertGreater(stresses["sigma_vm_work"], stresses["sigma_allow_work"])
        self.assertLess(stresses["sigma_ax_work"], stresses["sigma_allow_work"])

        page._last_payload = payload
        page._last_result = result
        page._render_result(payload, result)
        report_lines = page._build_report_lines()

        self.assertIn(f"{stresses['sigma_vm_work']:.1f}", page.metrics_text.text())
        self.assertNotIn(f"{stresses['sigma_ax_work']:.1f} MPa  /  允许", page.metrics_text.text())
        self.assertTrue(
            any(
                "sigma_vm_work" in line and f"{stresses['sigma_vm_work']:.2f}" in line
                for line in report_lines
            )
        )

    def test_r5_flowchart_detail_uses_sigma_vm_work_as_governing_metric(self) -> None:
        page = BoltPage()
        payload = _vm_governing_payload()
        result = calculate_vdi2230_core(payload)
        r5_page = page._r_pages[5]

        r5_page.build_input_echo(page._field_specs, page._field_widgets, result)
        r5_page.update_from_result(result, page._field_widgets)

        calc_text = r5_page._calc_text.text()  # type: ignore[attr-defined]
        self.assertIn("σ_vm_work", calc_text)
        self.assertIn("判据: σ_vm_work ≤ σ_allow", calc_text)

    def test_r7_failure_generates_specific_recommendation(self) -> None:
        page = BoltPage()
        payload = {
            "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
            "tightening": {
                "alpha_A": 1.5,
                "mu_thread": 0.1,
                "mu_bearing": 0.12,
                "utilization": 0.85,
                "thread_flank_angle_deg": 60.0,
            },
            "loads": {
                "FA_max": 6000.0,
                "FQ_max": 600.0,
                "embed_loss": 600.0,
                "thermal_force_loss": 300.0,
                "slip_friction_coefficient": 0.2,
                "friction_interfaces": 1.0,
            },
            "stiffness": {
                "bolt_compliance": 1.8e-06,
                "clamped_compliance": 2.4e-06,
                "load_introduction_factor_n": 1.0,
            },
            "bearing": {
                "bearing_d_inner": 13.0,
                "bearing_d_outer": 22.0,
                "p_G_allow": 1.0,
            },
            "checks": {"yield_safety_operating": 1.15},
        }
        result = calculate_vdi2230_core(payload)

        recs = page._build_recommendations(result)

        self.assertFalse(any("满足全部校核" in rec for rec in recs))
        self.assertTrue(any("支承面" in rec for rec in recs))

    def test_report_lines_mark_skipped_optional_checks_as_skipped(self) -> None:
        page = BoltPage()
        payload = {
            "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
            "tightening": {
                "alpha_A": 1.5,
                "mu_thread": 0.1,
                "mu_bearing": 0.12,
                "utilization": 0.85,
                "thread_flank_angle_deg": 60.0,
            },
            "loads": {
                "FA_max": 6000.0,
                "FQ_max": 600.0,
                "embed_loss": 600.0,
                "thermal_force_loss": 300.0,
                "slip_friction_coefficient": 0.2,
                "friction_interfaces": 1.0,
            },
            "stiffness": {
                "bolt_compliance": 1.8e-06,
                "clamped_compliance": 2.4e-06,
                "load_introduction_factor_n": 1.0,
            },
            "bearing": {"bearing_d_inner": 13.0, "bearing_d_outer": 22.0},
            "checks": {"yield_safety_operating": 1.15},
        }
        result = calculate_vdi2230_core(payload)
        page._last_payload = payload
        page._last_result = result

        report_lines = page._build_report_lines()

        self.assertIn("- 支承面压强校核（R7）: 已跳过", report_lines)
        self.assertIn("- 螺纹脱扣校核: 已跳过", report_lines)

    def test_flowchart_includes_optional_r8_thread_strip_step(self) -> None:
        page = BoltPage()

        titles = [node.title_label.text() for node in page.flowchart_nav._nodes]  # type: ignore[attr-defined]

        self.assertIn("R8 螺纹脱扣", titles)

    def test_repeated_calculation_does_not_duplicate_r_step_input_echo(self) -> None:
        page = BoltPage()
        r_page = page._r_pages[0]

        page._calculate()
        first_count = r_page._input_layout.count()
        page._calculate()
        second_count = r_page._input_layout.count()

        self.assertGreater(first_count, 0)
        self.assertEqual(second_count, first_count)

    def test_dynamic_hints_update_tooltip_and_footer_cache(self) -> None:
        page = BoltPage()
        alpha_widget = page._field_widgets["tightening.alpha_A"]
        method_widget = page._field_widgets["assembly.tightening_method"]
        n_widget = page._field_widgets["stiffness.load_introduction_factor_n"]
        position_widget = page._field_widgets["introduction.position"]

        method_widget.setCurrentText("液压拉伸法")  # type: ignore[attr-defined]
        position_widget.setCurrentText("螺母端")  # type: ignore[attr-defined]

        self.assertIn("1.05~1.15", alpha_widget.toolTip())  # type: ignore[attr-defined]
        self.assertIn("1.05~1.15", page._widget_hints[alpha_widget])  # type: ignore[index]
        self.assertIn("0.5~0.7", n_widget.toolTip())  # type: ignore[attr-defined]
        self.assertIn("0.5~0.7", page._widget_hints[n_widget])  # type: ignore[index]

    def test_assembly_guide_expands_into_a_readable_card(self) -> None:
        page = BoltPage()
        for i in range(page.chapter_list.count()):
            if "装配属性" in page.chapter_list.item(i).text():
                page.chapter_list.setCurrentRow(i)
                break

        page.resize(1400, 900)
        page.show()
        self.app.processEvents()

        guide_button = next(
            widget
            for widget in page.findChildren(type(page.btn_help_guide))
            if "新手指南" in widget.text()
        )
        guide_card = guide_button.parentWidget()
        guide_text = next(
            widget
            for widget in guide_card.findChildren(type(page.info_label))
            if widget.objectName() == "SectionHint" and "拧紧方式" in widget.text()
        )

        collapsed_height = guide_card.height()
        guide_button.click()
        self.app.processEvents()

        self.assertFalse(guide_text.isHidden())
        self.assertGreater(guide_card.height(), collapsed_height + 100)
        self.assertGreater(guide_text.width(), 400)
        self.assertGreater(guide_text.height(), 200)

    def test_manual_stiffness_overrides_default_compliance_values(self) -> None:
        page = BoltPage()

        page._field_widgets["stiffness.bolt_stiffness"].setText("1000000")  # type: ignore[attr-defined]
        page._field_widgets["stiffness.clamped_stiffness"].setText("2000000")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertNotIn("bolt_compliance", payload["stiffness"])
        self.assertNotIn("clamped_compliance", payload["stiffness"])
        self.assertEqual(payload["stiffness"]["bolt_stiffness"], 1000000.0)
        self.assertEqual(payload["stiffness"]["clamped_stiffness"], 2000000.0)

    def test_diagram_switches_with_joint_type(self) -> None:
        page = BoltPage()

        page._field_widgets["elements.joint_type"].setCurrentText("螺纹孔连接")  # type: ignore[attr-defined]
        page._sync_joint_diagram_from_ui()
        tapped_svg = page.diagram_widget._build_svg()  # type: ignore[attr-defined]

        page._field_widgets["elements.joint_type"].setCurrentText("通孔螺栓连接")  # type: ignore[attr-defined]
        page._sync_joint_diagram_from_ui()
        through_svg = page.diagram_widget._build_svg()  # type: ignore[attr-defined]

        self.assertIn("内螺纹", tapped_svg)
        self.assertNotIn("Nut", tapped_svg)
        self.assertIn("Nut", through_svg)

    def test_diagram_help_explains_compliance(self) -> None:
        page = BoltPage()

        help_text = page.diagram_help_label.text()  # type: ignore[attr-defined]

        self.assertIn("柔度", help_text)
        self.assertIn("δ = Δl / F", help_text)
        self.assertIn("phi", help_text)


if __name__ == "__main__":
    unittest.main()
