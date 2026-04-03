import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage


class BoltTappedAxialPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_page_builds_expected_chapters(self) -> None:
        page = BoltTappedAxialPage()

        titles = [page.chapter_list.item(i).text() for i in range(page.chapter_list.count())]

        self.assertTrue(any("适用范围" in title for title in titles))
        self.assertTrue(any("交变轴向疲劳" in title for title in titles))

    def test_page_exposes_spec_fields_without_clamped_or_stiffness(self) -> None:
        page = BoltTappedAxialPage()

        self.assertIn("fastener.d", page._field_widgets)  # type: ignore[attr-defined]
        self.assertIn("assembly.F_preload_min", page._field_widgets)  # type: ignore[attr-defined]
        self.assertIn("service.FA_min", page._field_widgets)  # type: ignore[attr-defined]
        self.assertIn("fatigue.surface_treatment", page._field_widgets)  # type: ignore[attr-defined]
        self.assertNotIn("clamped.parts", page._field_widgets)  # type: ignore[attr-defined]
        self.assertNotIn("stiffness.delta_p", page._field_widgets)  # type: ignore[attr-defined]

    def test_build_payload_matches_new_schema(self) -> None:
        page = BoltTappedAxialPage()

        payload = page._build_payload()

        self.assertIn("fastener", payload)
        self.assertIn("assembly", payload)
        self.assertIn("service", payload)
        self.assertIn("fatigue", payload)
        self.assertIn("thread_strip", payload)
        self.assertIn("checks", payload)
        self.assertIn("options", payload)
        self.assertNotIn("clamped", payload)
        self.assertNotIn("stiffness", payload)
        self.assertEqual(payload["assembly"]["tightening_method"], "torque")
        self.assertEqual(payload["fatigue"]["surface_treatment"], "rolled")
        self.assertEqual(payload["options"]["report_mode"], "full")

    def test_snapshot_round_trip_preserves_service_range_and_surface_treatment(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_min"].setText("2000")  # type: ignore[attr-defined]
        page._field_widgets["service.FA_max"].setText("8000")  # type: ignore[attr-defined]
        page._field_widgets["fatigue.surface_treatment"].setCurrentText("cut")  # type: ignore[attr-defined]

        snapshot = page._capture_input_snapshot()

        clone = BoltTappedAxialPage()
        clone._apply_input_data(snapshot)

        self.assertEqual(clone._field_widgets["service.FA_min"].text(), "2000")  # type: ignore[attr-defined]
        self.assertEqual(clone._field_widgets["service.FA_max"].text(), "8000")  # type: ignore[attr-defined]
        self.assertEqual(clone._field_widgets["fatigue.surface_treatment"].currentText(), "cut")  # type: ignore[attr-defined]


    def test_run_calculation_sets_result_title_pass(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        self.assertIn(page.result_title.text(), ("校核通过", "校核不通过"))

    def test_run_calculation_populates_check_badges(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        for key, badge in page._check_badges.items():
            self.assertIn(badge.text(), ("通过", "不通过"))

    def test_run_calculation_populates_metrics_text(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        text = page.metrics_text.text()
        self.assertIn("预紧力范围", text)
        self.assertIn("装配 von Mises", text)
        self.assertIn("疲劳应力幅", text)

    def test_build_report_lines_contains_scope_note(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        lines = page._build_report_lines()
        report_text = "\n".join(lines)
        self.assertIn("轴向受力螺纹连接校核报告", report_text)
        self.assertIn("适用范围", report_text)
        self.assertIn("螺纹脱扣", report_text)
        self.assertNotIn("FK_residual", report_text)


if __name__ == "__main__":
    unittest.main()
