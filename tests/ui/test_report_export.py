import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QWidget

from app.ui import report_export
from app.ui.pages import bolt_page


def _tmp_leftovers(directory: Path) -> list[Path]:
    return [path for path in directory.iterdir() if ".tmp" in path.name]


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
            self.assertEqual(out_path.read_bytes()[:4], b"%PDF")
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_export_docx_writes_valid_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.docx"

            report_export._export_docx(out_path, ["测试报告", "结论: 通过"])

            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)
            self.assertTrue(zipfile.is_zipfile(out_path))
            with zipfile.ZipFile(out_path, "r") as archive:
                names = archive.namelist()
            self.assertIn("word/document.xml", names)
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_write_text_report_writes_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.txt"

            report_export.write_text_report(out_path, "测试报告\n结论: 通过")

            self.assertEqual(out_path.read_text(encoding="utf-8"), "测试报告\n结论: 通过")
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_export_report_lines_happy_path_txt_docx_pdf(self) -> None:
        parent = QWidget()
        lines = ["测试报告", "结论: 通过"]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cases = (
                (tmp_dir / "report.txt", "Text Files (*.txt)"),
                (tmp_dir / "report.docx", "Word Files (*.docx)"),
                (tmp_dir / "report.pdf", "PDF Files (*.pdf)"),
            )
            for out_path, selected_filter in cases:
                with self.subTest(suffix=out_path.suffix):
                    with patch(
                        "app.ui.report_export.QFileDialog.getSaveFileName",
                        return_value=(str(out_path), selected_filter),
                    ):
                        result = report_export.export_report_lines(
                            parent,
                            "导出报告",
                            out_path,
                            lines,
                        )
                    self.assertEqual(result, out_path)
                    self.assertTrue(out_path.exists())
                    self.assertGreater(out_path.stat().st_size, 0)
                    if out_path.suffix == ".txt":
                        self.assertIn("测试报告", out_path.read_text(encoding="utf-8"))
                    elif out_path.suffix == ".docx":
                        self.assertTrue(zipfile.is_zipfile(out_path))
                    else:
                        self.assertEqual(out_path.read_bytes()[:4], b"%PDF")
                    self.assertEqual(_tmp_leftovers(tmp_dir), [])

    def test_successful_replace_keeps_complete_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            txt_path = tmp_dir / "report.txt"
            txt_path.write_text("OLD TXT", encoding="utf-8")
            report_export.write_text_report(txt_path, "NEW COMPLETE TXT")
            self.assertEqual(txt_path.read_text(encoding="utf-8"), "NEW COMPLETE TXT")

            pdf_path = tmp_dir / "report.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 old incomplete")
            report_export._export_pdf(pdf_path, ["新报告"])
            self.assertEqual(pdf_path.read_bytes()[:4], b"%PDF")
            self.assertGreater(pdf_path.stat().st_size, len(b"%PDF-1.4 old incomplete"))

            docx_path = tmp_dir / "report.docx"
            docx_path.write_bytes(b"PK\x03\x04old")
            report_export._export_docx(docx_path, ["新报告"])
            self.assertTrue(zipfile.is_zipfile(docx_path))
            with zipfile.ZipFile(docx_path, "r") as archive:
                self.assertIn("word/document.xml", archive.namelist())

            self.assertEqual(_tmp_leftovers(tmp_dir), [])

    def test_failed_write_does_not_destroy_existing_or_leave_tmp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.txt"
            out_path.write_text("GOOD CONTENT", encoding="utf-8")

            def boom(path: Path) -> None:
                path.write_text("PARTIAL", encoding="utf-8")
                raise OSError("disk full")

            with self.assertRaises(report_export.ReportExportError) as ctx:
                report_export.write_report_atomically(out_path, boom)

            self.assertIn("导出失败", str(ctx.exception))
            self.assertEqual(out_path.read_text(encoding="utf-8"), "GOOD CONTENT")
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_failed_write_does_not_create_final_file_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.pdf"

            def boom(path: Path) -> None:
                path.write_bytes(b"PARTIAL")
                raise OSError("disk full")

            with self.assertRaises(report_export.ReportExportError):
                report_export.write_report_atomically(out_path, boom)

            self.assertFalse(out_path.exists())
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_invalid_pdf_does_not_replace_existing_good_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.pdf"
            original = b"%PDF-1.4 existing-good"
            out_path.write_bytes(original)

            def bad_pdf(path: Path) -> None:
                path.write_bytes(b"not a pdf but nonempty")

            with self.assertRaises(report_export.ReportExportError) as ctx:
                report_export.write_report_atomically(out_path, bad_pdf)

            self.assertIn("PDF", str(ctx.exception))
            self.assertEqual(out_path.read_bytes(), original)
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_empty_write_is_rejected_and_leaves_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.txt"
            out_path.write_text("GOOD", encoding="utf-8")

            def empty_writer(path: Path) -> None:
                path.write_text("", encoding="utf-8")

            with self.assertRaises(report_export.ReportExportError):
                report_export.write_report_atomically(out_path, empty_writer)

            self.assertEqual(out_path.read_text(encoding="utf-8"), "GOOD")
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

    def test_permission_error_from_writer_preserves_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.docx"
            out_path.write_bytes(b"PK\x03\x04good")

            def occupied(_path: Path) -> None:
                raise PermissionError("Permission denied")

            with self.assertRaises(report_export.ReportExportError) as ctx:
                report_export.write_report_atomically(out_path, occupied)

            self.assertIn("导出失败", str(ctx.exception))
            self.assertIn("占用", str(ctx.exception))
            self.assertEqual(out_path.read_bytes(), b"PK\x03\x04good")
            self.assertEqual(_tmp_leftovers(Path(tmp)), [])

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


class ReportTraceTests(unittest.TestCase):
    def test_payload_hash_is_stable_for_same_payload(self) -> None:
        from app.ui.report_trace import payload_sha256

        payload = {"b": 2, "a": {"z": 1, "y": [3, 4]}}
        shuffled = {"a": {"y": [3, 4], "z": 1}, "b": 2}
        first = payload_sha256(payload)
        second = payload_sha256(shuffled)
        self.assertTrue(first.startswith("sha256:"))
        self.assertEqual(len(first), len("sha256:") + 64)
        self.assertEqual(first, second)
        self.assertEqual(first, payload_sha256(payload))

    def test_payload_hash_changes_when_value_changes(self) -> None:
        from app.ui.report_trace import payload_sha256

        self.assertNotEqual(payload_sha256({"x": 1}), payload_sha256({"x": 2}))

    def test_trace_lines_include_version_time_module_and_hash(self) -> None:
        from app.ui.report_trace import build_report_trace, trace_report_lines

        trace = build_report_trace("bolt_vdi2230", {"fastener": {"d": 12}})
        lines = trace_report_lines(trace)
        joined = "\n".join(lines)
        self.assertIn("软件版本:", joined)
        self.assertNotEqual(trace.software_version, "")
        self.assertIn("生成时间:", joined)
        self.assertRegex(trace.generated_at, r"[+-]\d{4}$")
        self.assertIn("模块: bolt_vdi2230", joined)
        self.assertIn("输入摘要哈希: sha256:", joined)
        self.assertNotIn("模型等级:", joined)

    def test_optional_model_level_is_included_when_provided(self) -> None:
        from app.ui.report_trace import build_report_trace, trace_report_lines

        trace = build_report_trace(
            "interference_fit",
            {"geometry": {"shaft_d_mm": 50}},
            model_level="正式子集",
        )
        self.assertIn("模型等级: 正式子集", trace_report_lines(trace))

    def test_packaged_trace_reads_embedded_build_info_without_git(self) -> None:
        import json

        from app.ui import report_trace

        with tempfile.TemporaryDirectory() as tmp:
            bundle_root = Path(tmp) / "bundle"
            executable_root = Path(tmp) / "release"
            bundle_root.mkdir()
            executable_root.mkdir()
            build_info = {
                "schema_version": 1,
                "version": "2026.08.24.0",
                "build_id": "2026.08.24.0-a1b2c3d-dirty-20260824T010203Z",
                "build_mode": "onedir",
                "built_at": "2026-08-24T01:02:03Z",
                "git_commit": "a1b2c3d",
                "git_dirty": True,
            }
            # utf-8-sig also covers Windows PowerShell 5.1's UTF-8 BOM output.
            (bundle_root / "build-info.json").write_text(
                json.dumps(build_info),
                encoding="utf-8-sig",
            )

            with (
                patch.object(report_trace.sys, "_MEIPASS", str(bundle_root), create=True),
                patch.object(report_trace.sys, "frozen", True, create=True),
                patch.object(
                    report_trace.sys,
                    "executable",
                    str(executable_root / "LocalEngineeringAssistant.exe"),
                ),
                patch.object(
                    report_trace.subprocess,
                    "run",
                    side_effect=AssertionError("packaged metadata must not invoke git"),
                ),
            ):
                version = report_trace.software_version()

        self.assertEqual(
            version,
            "2026.08.24.0 | git:a1b2c3d-dirty | "
            "build:2026.08.24.0-a1b2c3d-dirty-20260824T010203Z",
        )

    def test_packaged_trace_falls_back_to_executable_sidecar(self) -> None:
        import json

        from app.ui import report_trace

        with tempfile.TemporaryDirectory() as tmp:
            release_root = Path(tmp)
            (release_root / "build-info.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "version": "2026.08.24.1",
                        "build_id": "release-sidecar-42",
                        "build_mode": "onefile",
                        "built_at": "2026-08-24T01:02:03Z",
                        "git_commit": "f00ba42",
                        "git_dirty": False,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(report_trace.sys, "_MEIPASS", None, create=True),
                patch.object(report_trace.sys, "frozen", True, create=True),
                patch.object(
                    report_trace.sys,
                    "executable",
                    str(release_root / "LocalEngineeringAssistant.exe"),
                ),
                patch.object(
                    report_trace.subprocess,
                    "run",
                    side_effect=AssertionError("sidecar metadata must not invoke git"),
                ),
            ):
                version = report_trace.software_version()

        self.assertEqual(
            version,
            "2026.08.24.1 | git:f00ba42 | build:release-sidecar-42",
        )

    def test_packaged_trace_fails_closed_when_build_info_is_missing(self) -> None:
        from app.ui import report_trace

        with tempfile.TemporaryDirectory() as tmp:
            release_root = Path(tmp)
            with (
                patch.object(report_trace.sys, "_MEIPASS", str(release_root), create=True),
                patch.object(report_trace.sys, "frozen", True, create=True),
                patch.object(
                    report_trace.sys,
                    "executable",
                    str(release_root / "LocalEngineeringAssistant.exe"),
                ),
                patch.object(
                    report_trace.subprocess,
                    "run",
                    side_effect=AssertionError("broken package must not fall back to git"),
                ),
            ):
                version = report_trace.software_version()

        self.assertEqual(version, "unknown-packaged-build")

    def test_packaged_trace_skips_invalid_embedded_info_and_uses_sidecar(self) -> None:
        import json

        from app.ui import report_trace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle_root = root / "bundle"
            release_root = root / "release"
            bundle_root.mkdir()
            release_root.mkdir()
            (bundle_root / "build-info.json").write_text(
                json.dumps({"schema_version": 0, "version": "stale"}),
                encoding="utf-8",
            )
            (release_root / "build-info.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "version": "2026.08.24.2",
                        "build_id": "valid-sidecar-43",
                        "build_mode": "onedir",
                        "built_at": "2026-08-24T01:02:03Z",
                        "git_commit": "abc1234",
                        "git_dirty": False,
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(report_trace.sys, "_MEIPASS", str(bundle_root), create=True),
                patch.object(report_trace.sys, "frozen", True, create=True),
                patch.object(
                    report_trace.sys,
                    "executable",
                    str(release_root / "LocalEngineeringAssistant.exe"),
                ),
            ):
                version = report_trace.software_version()

        self.assertEqual(
            version,
            "2026.08.24.2 | git:abc1234 | build:valid-sidecar-43",
        )


if __name__ == "__main__":
    unittest.main()
