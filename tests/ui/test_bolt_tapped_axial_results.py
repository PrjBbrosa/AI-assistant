import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage


class BoltTappedAxialResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_run_calculation_renders_result_and_inactive_thread_strip(self) -> None:
        """未填 m_eff 的默认场景：结果渲染正常，总体结论为"校核不完整"（Codex §3.3）."""
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        self.assertEqual(page.result_title.text(), "校核不完整")
        self.assertIn("预紧力范围", page.metrics_text.text())
        self.assertIn("未提供 m_eff", page.metrics_text.text())
        self.assertNotIn("FK_residual", page.metrics_text.text())

    def test_report_lines_include_scope_and_new_sections(self) -> None:
        page = BoltTappedAxialPage()
        page._run_calculation()
        lines = page._build_report_lines()
        report_text = "\n".join(lines)
        self.assertIn("轴向受力螺纹连接校核报告", report_text)
        self.assertIn("适用范围", report_text)
        self.assertIn("trace", report_text.lower())
        self.assertIn("螺纹脱扣", report_text)
        self.assertNotIn("clamped", report_text.lower())
        self.assertNotIn("FK_residual", report_text)
        self.assertNotIn("R3", report_text)

    def test_main_window_registers_tapped_axial_module_entry(self) -> None:
        window = MainWindow()
        module_names = [name for name, _ in window.modules]
        self.assertIn("轴向受力螺纹连接", module_names)

    def test_calculation_failure_shows_error_not_crash(self) -> None:
        from unittest.mock import patch
        page = BoltTappedAxialPage()
        page._field_widgets["fastener.d"].setText("")
        with patch("app.ui.pages.bolt_tapped_axial_page.QMessageBox"):
            page._run_calculation()
        self.assertIsNone(page._last_result)


if __name__ == "__main__":
    unittest.main()
