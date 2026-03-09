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

    def test_report_lines_include_gaping_and_mean_results(self) -> None:
        page = InterferenceFitPage()

        page._calculate()
        report_lines = page._build_report_lines()

        self.assertTrue(any("p_r / p_b / p_gap" in line for line in report_lines))
        self.assertTrue(any("p_min / p_mean / p_max" in line for line in report_lines))
        self.assertIn("gaping_ok", page._check_badges)


if __name__ == "__main__":
    unittest.main()
