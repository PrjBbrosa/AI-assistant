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
        self.assertIn("advanced.repeated_load_mode", page._field_widgets)
        self.assertIn("friction.mu_torque", page._field_widgets)
        self.assertIn("friction.mu_axial", page._field_widgets)
        self.assertNotIn("process.assembly_method", page._field_widgets)
        self.assertNotIn("process.temp_delta_c", page._field_widgets)

    def test_build_payload_uses_new_friction_fields(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["loads.application_factor_ka"].setText("1.35")  # type: ignore[attr-defined]
        page._field_widgets["friction.mu_torque"].setText("0.16")  # type: ignore[attr-defined]
        page._field_widgets["friction.mu_axial"].setText("0.12")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["loads"]["application_factor_ka"], 1.35)
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

    def test_report_lines_include_repeated_load_trace(self) -> None:
        page = InterferenceFitPage()
        page._field_widgets["advanced.repeated_load_mode"].setCurrentText("on")  # type: ignore[attr-defined]

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("repeated load" in line for line in report_lines))
        self.assertTrue(any("max_transferable_torque" in line for line in report_lines))

    def test_report_lines_include_material_and_profile_source_trace(self) -> None:
        page = InterferenceFitPage()

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("shaft material preset" in line for line in report_lines))
        self.assertTrue(any("roughness profile source" in line for line in report_lines))


if __name__ == "__main__":
    unittest.main()
