import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui import report_export
from app.ui.pages import bolt_page


class ReportExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_export_pdf_writes_non_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.pdf"

            report_export._export_pdf(out_path, ["测试报告", "结论: 通过"])

            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)

    def test_report_export_error_is_public_exception(self) -> None:
        self.assertTrue(issubclass(report_export.ReportExportError, RuntimeError))

    def test_bolt_save_report_shows_chinese_error_when_export_fails(self) -> None:
        page = bolt_page.BoltPage()
        page._last_payload = {"inputs": {}}
        page._last_result = {"result": {}}

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "bolt_report.pdf"
            with (
                patch(
                    "app.ui.pages.bolt_page.QFileDialog.getSaveFileName",
                    return_value=(str(out_path), "PDF Files (*.pdf)"),
                ),
                patch.object(page, "_build_report_lines", return_value=["螺栓报告"]),
                patch(
                    "app.ui.pages.bolt_page._export_bolt_pdf_report",
                    side_effect=OSError("disk is read-only"),
                ),
                patch("app.ui.pages.bolt_page.QMessageBox.critical", return_value=None) as critical,
                patch("app.ui.pages.bolt_page.QMessageBox.information", return_value=None) as information,
            ):
                page._save_report()

        critical.assert_called_once()
        self.assertEqual(critical.call_args.args[1], "导出失败")
        self.assertIn("导出失败", critical.call_args.args[2])
        information.assert_not_called()


if __name__ == "__main__":
    unittest.main()
