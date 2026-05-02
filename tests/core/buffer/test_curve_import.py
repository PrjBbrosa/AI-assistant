"""Tests for buffer curve import (CSV / XLSX)."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

from core.buffer.curve_import import InputError, load_buffer_curve


def _write(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.write_text(text, encoding=encoding)


class CSVWideTableTests(unittest.TestCase):
    def test_parses_basic_wide_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "wide.csv"
            _write(
                csv_path,
                "x_mm,loading_force_n,unloading_force_n\n"
                "0,0,0\n5,800,300\n10,1800,900\n",
            )
            result = load_buffer_curve(csv_path)
        self.assertEqual(result["metadata"]["format"], "wide")
        self.assertEqual(len(result["loading"]), 3)
        self.assertEqual(len(result["unloading"]), 3)
        self.assertEqual(result["loading"][2], {"x_mm": 10.0, "force_n": 1800.0})

    def test_supports_chinese_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "wide_cn.csv"
            _write(csv_path, "位移_mm,加载力_n,卸载力_n\n0,0,0\n5,800,300\n")
            result = load_buffer_curve(csv_path)
        self.assertEqual(len(result["loading"]), 2)
        self.assertEqual(result["unloading"][1]["force_n"], 300.0)

    def test_supports_utf8_sig_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bom.csv"
            _write(
                csv_path,
                "\ufeffx_mm,loading_force_n,unloading_force_n\n0,0,0\n5,800,300\n",
                encoding="utf-8-sig",
            )
            result = load_buffer_curve(csv_path)
        self.assertEqual(result["metadata"]["format"], "wide")

    def test_supports_tab_delimited_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "wide.tsv.csv"
            _write(csv_path, "x_mm\tloading_force_n\tunloading_force_n\n0\t0\t0\n5\t800\t300\n")
            result = load_buffer_curve(csv_path)
        self.assertEqual(len(result["loading"]), 2)

    def test_missing_displacement_column_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bad.csv"
            _write(csv_path, "loading_force_n,unloading_force_n\n0,0\n")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(csv_path)
            self.assertIn("位移", str(ctx.exception))

    def test_empty_csv_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "empty.csv"
            _write(csv_path, "")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(csv_path)
            self.assertIn("为空", str(ctx.exception))

    def test_non_numeric_force_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bad_number.csv"
            _write(
                csv_path,
                "x_mm,loading_force_n,unloading_force_n\n0,0,0\n5,abc,300\n",
            )
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(csv_path)
            self.assertIn("不是数字", str(ctx.exception))

    def test_missing_unloading_column_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "missing_unload.csv"
            _write(csv_path, "x_mm,loading_force_n\n0,0\n5,800\n")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(csv_path)
            self.assertIn("卸载", str(ctx.exception))

    def test_unknown_extension_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "data.txt"
            _write(bad, "x_mm,loading_force_n\n0,0\n")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(bad)
            self.assertIn("文件类型", str(ctx.exception))


class CSVLongTableTests(unittest.TestCase):
    def test_parses_basic_long_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.csv"
            _write(
                path,
                "branch,x_mm,force_n\n"
                "loading,0,0\nloading,5,800\nloading,10,1800\n"
                "unloading,10,900\nunloading,5,300\nunloading,0,0\n",
            )
            result = load_buffer_curve(path)
        self.assertEqual(result["metadata"]["format"], "long")
        self.assertEqual(len(result["loading"]), 3)
        self.assertEqual(len(result["unloading"]), 3)

    def test_long_table_chinese_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long_cn.csv"
            _write(
                path,
                "曲线,位移_mm,力_n\n"
                "加载,0,0\n加载,10,1800\n"
                "卸载,10,900\n卸载,0,0\n",
            )
            result = load_buffer_curve(path)
        self.assertEqual(len(result["loading"]), 2)
        self.assertEqual(result["unloading"][0]["force_n"], 900.0)

    def test_unknown_branch_value_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long_bad.csv"
            _write(path, "branch,x_mm,force_n\nbogus,0,0\nloading,10,1800\n")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(path)
            self.assertIn("branch", str(ctx.exception).lower())


class XLSXImportTests(unittest.TestCase):
    def _write_xlsx(self, path: Path, headers: list, rows: list) -> None:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(list(headers))
        for row in rows:
            ws.append(list(row))
        wb.save(path)

    def test_parses_xlsx_wide_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wide.xlsx"
            self._write_xlsx(
                path,
                ["x_mm", "loading_force_n", "unloading_force_n"],
                [(0, 0, 0), (5, 800, 300), (10, 1800, 900)],
            )
            result = load_buffer_curve(path)
        self.assertEqual(result["metadata"]["format"], "wide")
        self.assertEqual(len(result["loading"]), 3)

    def test_parses_xlsx_long_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.xlsx"
            self._write_xlsx(
                path,
                ["branch", "x_mm", "force_n"],
                [
                    ("loading", 0, 0),
                    ("loading", 10, 1800),
                    ("unloading", 10, 900),
                    ("unloading", 0, 0),
                ],
            )
            result = load_buffer_curve(path)
        self.assertEqual(result["metadata"]["format"], "long")

    def test_openpyxl_not_imported_when_loading_csv(self) -> None:
        for mod in list(sys.modules):
            if mod == "openpyxl" or mod.startswith("openpyxl."):
                del sys.modules[mod]
        importlib.reload(importlib.import_module("core.buffer.curve_import"))
        self.assertNotIn("openpyxl", sys.modules)


if __name__ == "__main__":
    unittest.main()
