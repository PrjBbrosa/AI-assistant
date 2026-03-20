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

    def test_setup_case_axial_hides_transverse_fields_and_builds_zero_fq(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("轴向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.FA_max"].setText("12000")  # type: ignore[attr-defined]
        page._field_widgets["loads.FQ_max"].setText("800")  # type: ignore[attr-defined]
        page._field_widgets["loads.friction_interfaces"].setText("2")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_friction_coefficient"].setText("0.22")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertTrue(page._field_cards["loads.FQ_max"].isHidden())
        self.assertTrue(page._field_cards["loads.friction_interfaces"].isHidden())
        self.assertTrue(page._field_cards["loads.slip_friction_coefficient"].isHidden())
        self.assertEqual(payload["loads"]["FA_max"], 12000.0)
        self.assertEqual(payload["loads"]["FQ_max"], 0.0)
        self.assertNotIn("friction_interfaces", payload["loads"])
        self.assertNotIn("slip_friction_coefficient", payload["loads"])

    def test_setup_case_transverse_hides_axial_force_and_builds_zero_fa(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("横向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.FA_max"].setText("15000")  # type: ignore[attr-defined]
        page._field_widgets["loads.FQ_max"].setText("2500")  # type: ignore[attr-defined]
        page._field_widgets["loads.seal_force_required"].setText("3000")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertTrue(page._field_cards["loads.FA_max"].isHidden())
        self.assertFalse(page._field_cards["loads.seal_force_required"].isHidden())
        self.assertEqual(payload["loads"]["FA_max"], 0.0)
        self.assertEqual(payload["loads"]["FQ_max"], 2500.0)
        self.assertEqual(payload["loads"]["seal_force_required"], 3000.0)

    def test_setup_case_combined_and_free_input_keep_all_load_fields_visible(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("轴向+横向")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_mu_mode"].setCurrentText("跟随支承面摩擦 μK")  # type: ignore[attr-defined]
        self.assertFalse(page._field_cards["loads.FA_max"].isHidden())
        self.assertFalse(page._field_cards["loads.FQ_max"].isHidden())
        self.assertFalse(page._field_cards["loads.friction_interfaces"].isHidden())
        self.assertFalse(page._field_cards["loads.slip_mu_mode"].isHidden())
        self.assertTrue(page._field_cards["loads.slip_friction_coefficient"].isHidden())

        page._field_widgets["operating.setup_case"].setCurrentText("自由输入")  # type: ignore[attr-defined]
        self.assertFalse(page._field_cards["loads.FA_max"].isHidden())
        self.assertFalse(page._field_cards["loads.FQ_max"].isHidden())

    def test_slip_mu_follow_mode_hides_mu_t_and_omits_payload_value(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("横向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_mu_mode"].setCurrentText("跟随支承面摩擦 μK")  # type: ignore[attr-defined]
        page._field_widgets["tightening.mu_bearing"].setText("0.14")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(page._field_widgets["loads.slip_mu_mode"].currentText(), "跟随支承面摩擦 μK")  # type: ignore[attr-defined]
        self.assertFalse(page._field_cards["loads.slip_mu_mode"].isHidden())
        self.assertTrue(page._field_cards["loads.slip_friction_coefficient"].isHidden())
        self.assertNotIn("slip_friction_coefficient", payload["loads"])

    def test_slip_mu_custom_mode_shows_mu_t_and_keeps_manual_value(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("横向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_mu_mode"].setCurrentText("单独输入 μT")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_friction_coefficient"].setText("0.08")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertFalse(page._field_cards["loads.slip_friction_coefficient"].isHidden())
        self.assertEqual(payload["loads"]["slip_friction_coefficient"], 0.08)

    def test_apply_raw_payload_with_slip_mu_switches_mode_to_custom(self) -> None:
        page = BoltPage()
        raw = _raw_bolt_payload()
        raw["loads"]["FQ_max"] = 1200.0
        raw["loads"]["slip_friction_coefficient"] = 0.16

        page._apply_input_data(raw)

        self.assertEqual(page._field_widgets["loads.slip_mu_mode"].currentText(), "单独输入 μT")  # type: ignore[attr-defined]
        self.assertFalse(page._field_cards["loads.slip_friction_coefficient"].isHidden())

    def test_bolt_material_updates_alpha_and_e_bolt_presets(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.bolt_material"].setCurrentText("不锈钢")  # type: ignore[attr-defined]

        self.assertEqual(page._field_widgets["operating.alpha_bolt"].text(), "16.0e-6")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["stiffness.E_bolt"].text(), "193000")  # type: ignore[attr-defined]

    def test_clamped_material_updates_alpha_and_e_clamped_presets(self) -> None:
        page = BoltPage()

        page._set_check_level("thermal")
        page._apply_check_level_visibility()
        page._field_widgets["operating.clamped_material"].setCurrentText("铝合金")  # type: ignore[attr-defined]

        self.assertEqual(page._field_widgets["operating.alpha_parts"].text(), "23.0e-6")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["stiffness.E_clamped"].text(), "70000")  # type: ignore[attr-defined]

    def test_layer_material_updates_alpha_and_layer_e_presets(self) -> None:
        page = BoltPage()

        page._field_widgets["clamped.part_count"].setCurrentText("2")  # type: ignore[attr-defined]
        page._on_part_count_changed()
        page._field_widgets["clamped.layer_2.material"].setCurrentText("铸铁")  # type: ignore[attr-defined]

        self.assertEqual(page._field_widgets["clamped.layer_2.alpha"].text(), "10.5e-6")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["clamped.layer_2.E"].text(), "120000")  # type: ignore[attr-defined]

    def test_custom_material_unlocks_manual_e_fields(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.clamped_material"].setCurrentText("铝合金")  # type: ignore[attr-defined]
        page._field_widgets["operating.clamped_material"].setCurrentText("自定义")  # type: ignore[attr-defined]

        self.assertFalse(page._field_widgets["operating.alpha_parts"].isReadOnly())  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["operating.alpha_parts"].text(), "")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["stiffness.E_clamped"].text(), "70000")  # type: ignore[attr-defined]

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
