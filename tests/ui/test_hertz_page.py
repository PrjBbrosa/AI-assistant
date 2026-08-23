"""UI smoke and contract tests for HertzContactPage.

Covers:
- HR-01/02 smoke: default sample + _calculate() does not raise; metrics_text contains
  contact area; badge state is updated.
- HR-01/02 contract: bad result structure causes _render_result to be swallowed by the
  outer try/except, leaving _last_result as None.
- HR-05 contract: _build_report_lines contains "接触面积" and, when warnings exist,
  a "提示:" section with the warning text.
"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app.ui.pages.hertz_contact_page import HertzContactPage
from core.hertz.calculator import OUTER_CONTACT_SCOPE_NOTE


class HertzPageSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _make_page(self) -> HertzContactPage:
        page = HertzContactPage()
        cls_app = self.__class__.app
        cls_app.processEvents()
        return page

    # ------------------------------------------------------------------
    # P0-3 smoke: default sample loads (hertz_case_01.json is loaded in
    # __init__), then _calculate() must not raise.
    # ------------------------------------------------------------------
    def test_default_sample_calculate_not_raising(self) -> None:
        page = self._make_page()
        # Should not raise — if it does, the test will fail via exception.
        page._calculate()
        self.__class__.app.processEvents()

    # ------------------------------------------------------------------
    # HR-01 UI consumption: after calculate, metrics_text must show contact
    # area (two-level path result["contact"]["contact_area_mm2"] is correct).
    # ------------------------------------------------------------------
    def test_metrics_text_contains_contact_area(self) -> None:
        page = self._make_page()
        page._calculate()
        self.__class__.app.processEvents()
        text = page.metrics_text.text()
        self.assertIn("接触面积", text)

    # ------------------------------------------------------------------
    # Badge state: after calculate the badge must be "通过" or "不通过",
    # not the initial "待计算".
    # ------------------------------------------------------------------
    def test_badges_updated_after_calculate(self) -> None:
        page = self._make_page()
        page._calculate()
        self.__class__.app.processEvents()
        badge = page._check_badges["contact_stress_ok"]
        self.assertIn(badge.text(), ("通过", "不通过"))

    # ------------------------------------------------------------------
    # HR-02 guard: when calculate_hertz_contact returns a structure that
    # makes _render_result raise (missing "contact" key), the outer
    # try/except must swallow it — _last_result stays None and no
    # exception escapes to the caller.
    # QMessageBox is patched to prevent headless blocking.
    # ------------------------------------------------------------------
    def test_render_failure_leaves_last_result_none(self) -> None:
        page = self._make_page()

        # Return a result missing the "contact" sub-dict — this would have
        # raised KeyError before HR-02's expanded try/except.
        bad_result = {
            "mode": "line",
            "derived": {"e_eq_mpa": 1.0, "r_eq_mm": 1.0, "inv_r1_per_mm": 0.0, "inv_r2_per_mm": 0.0},
            # intentionally omit "contact"
            "check": {"allowable_p0_mpa": 1500.0, "safety_factor": 1.5},
            "checks": {"contact_stress_ok": True},
            "curve": {"force_n": [], "p0_mpa": [], "force_design_n": 0.0, "p0_design_mpa": 0.0},
            "overall_pass": True,
            "warnings": [],
            "options": {"curve_points": 41, "curve_force_scale": 1.3},
            "inputs_echo": {},
        }
        with patch("app.ui.pages.hertz_contact_page.calculate_hertz_contact", return_value=bad_result), \
             patch("app.ui.pages.hertz_contact_page.QMessageBox") as mock_msgbox:
            mock_msgbox.critical.return_value = None
            # Must not propagate any exception.
            page._calculate()

        self.__class__.app.processEvents()
        # Because _render_result raised, the result should not have been saved.
        self.assertIsNone(page._last_result)

    # ------------------------------------------------------------------
    # HR-01 report consumption: _build_report_lines must contain a line
    # with "接触面积".
    # ------------------------------------------------------------------
    def test_build_report_lines_contains_contact_area(self) -> None:
        page = self._make_page()
        page._calculate()
        self.__class__.app.processEvents()
        lines = page._build_report_lines()
        self.assertTrue(
            any("接触面积" in line for line in lines),
            msg=f"Expected '接触面积' in report lines, got:\n{lines}",
        )

    # ------------------------------------------------------------------
    # HR-05 report: when warnings exist, _build_report_lines includes a
    # "提示:" section with the warning text.
    # Use line contact with length_mm=3.0, which triggers the short-length
    # warning inside calculate_hertz_contact.
    # ------------------------------------------------------------------
    def test_build_report_lines_contains_warnings_section_for_short_length(self) -> None:
        page = self._make_page()

        # Switch to line contact and set length to 3.0 (< 5.0 triggers warning).
        from PySide6.QtWidgets import QComboBox, QLineEdit
        mode_widget = page._field_widgets.get("geometry.contact_mode")
        if isinstance(mode_widget, QComboBox):
            idx = mode_widget.findText("线接触")
            if idx >= 0:
                mode_widget.setCurrentIndex(idx)

        length_widget = page._field_widgets.get("geometry.length_mm")
        if isinstance(length_widget, QLineEdit):
            length_widget.setText("3.0")

        page._calculate()
        self.__class__.app.processEvents()

        # Confirm a warning was actually generated.
        result = page._last_result
        self.assertIsNotNone(result)
        self.assertTrue(len(result["warnings"]) > 0, "Expected at least one warning for length_mm=3.0")

        lines = page._build_report_lines()
        self.assertTrue(
            any("提示:" in line for line in lines),
            msg=f"Expected '提示:' section in report lines, got:\n{lines}",
        )
        # At least one warning body line must appear.
        warning_text = result["warnings"][0]
        self.assertTrue(
            any(warning_text in line for line in lines),
            msg=f"Expected warning '{warning_text}' in report lines, got:\n{lines}",
        )

    def test_outer_contact_scope_visible_on_page_and_report(self) -> None:
        page = self._make_page()
        labels = [widget.text() for widget in page.findChildren(QLabel)]
        self.assertTrue(
            any(OUTER_CONTACT_SCOPE_NOTE in text for text in labels),
            msg="Expected outer-contact scope note on Hertz page labels",
        )

        page._calculate()
        self.__class__.app.processEvents()
        self.assertIsNotNone(page._last_result)
        self.assertIn(OUTER_CONTACT_SCOPE_NOTE, page._last_result["warnings"])
        self.assertIn(OUTER_CONTACT_SCOPE_NOTE, page.message_box.toPlainText())
        lines = page._build_report_lines()
        self.assertTrue(
            any(OUTER_CONTACT_SCOPE_NOTE in line for line in lines),
            msg=f"Expected outer-contact scope note in report lines, got:\n{lines}",
        )


if __name__ == "__main__":
    unittest.main()
