from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from core.fatigue.importers import (
    ImportError,
    list_xlsx_sheets,
    load_sn_test_data,
    load_spectrum_data,
)


def test_import_sn_csv_with_chinese_aliases(tmp_path: Path) -> None:
    source = tmp_path / "sn.csv"
    source.write_text(
        "试样编号,应力幅_MPa,平均应力_MPa,循环数,状态,失效模式\n"
        "A1,200,20,100000,断裂,截面\n"
        "A2,150,20,1000000,未断裂,\n",
        encoding="utf-8",
    )
    result = load_sn_test_data(source)
    assert [row["status"] for row in result["specimens"]] == ["failure", "runout"]
    assert result["source"]["file_name"] == "sn.csv"
    assert len(result["source"]["sha256"]) == 64


def test_import_sn_xlsx_uses_selected_sheet_and_records_it(tmp_path: Path) -> None:
    source = tmp_path / "sn.xlsx"
    workbook = Workbook()
    workbook.active.title = "说明"
    sheet = workbook.create_sheet("试验数据")
    sheet.append(["试样编号", "条件组", "应力幅", "循环数", "状态"])
    sheet.append(["A1", "C1", 160, 100_000, "断裂"])
    sheet.append(["A2", "C1", 160, 200_000, "runout"])
    workbook.save(source)

    assert list_xlsx_sheets(source) == ["说明", "试验数据"]
    result = load_sn_test_data(source, sheet_name="试验数据")
    assert len(result["specimens"]) == 2
    assert result["specimens"][0]["condition_group"] == "C1"
    assert result["source"]["sheet_name"] == "试验数据"


def test_import_block_spectrum_from_extrema(tmp_path: Path) -> None:
    source = tmp_path / "blocks.csv"
    source.write_text("最大应力_MPa,最小应力_MPa,循环数\n120,-80,10\n", encoding="utf-8")
    result = load_spectrum_data(source, kind="blocks")
    assert result["blocks"] == [{"amplitude": 100.0, "mean": 20.0, "cycles": 10.0}]


def test_import_rejects_unknown_status(tmp_path: Path) -> None:
    source = tmp_path / "bad.csv"
    source.write_text("应力幅,循环数,状态\n100,1000,maybe\n", encoding="utf-8")
    with pytest.raises(ImportError, match="状态无法识别"):
        load_sn_test_data(source)


def test_import_block_spectrum_accepts_generic_aliases(tmp_path: Path) -> None:
    source = tmp_path / "blocks.csv"
    source.write_text("amplitude,mean,cycles\n100,20,5\n", encoding="utf-8")
    result = load_spectrum_data(source, kind="blocks")
    assert result["blocks"] == [{"amplitude": 100.0, "mean": 20.0, "cycles": 5.0}]


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ("0,0,5", "幅值必须 > 0"),
        ("100,0,0", "循环数必须 > 0"),
    ],
)
def test_import_block_spectrum_rejects_nonpositive_values(
    tmp_path: Path, row: str, message: str
) -> None:
    source = tmp_path / "bad_blocks.csv"
    source.write_text(f"amplitude,mean,cycles\n{row}\n", encoding="utf-8")
    with pytest.raises(ImportError, match=message):
        load_spectrum_data(source, kind="blocks")
