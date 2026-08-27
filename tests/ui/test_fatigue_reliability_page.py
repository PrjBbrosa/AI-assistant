"""UI and report contracts for the fatigue reliability module."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem

from app.ui.pages.fatigue_reliability_page import FatigueReliabilityPage
from app.ui.report_export import _export_docx, write_text_report
from app.ui.report_pdf_fatigue import generate_fatigue_report
from app.ui.result_contract import FATIGUE_CHECK_LABELS, from_fatigue


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _fast_page() -> FatigueReliabilityPage:
    page = FatigueReliabilityPage()
    page.mc_samples_edit.setText("1000")
    page.bootstrap_samples_edit.setText("0")
    return page


def test_page_has_seven_steps_and_embedded_sample(qapp) -> None:
    page = _fast_page()
    assert page.chapter_list.count() == 7
    assert page.sn_table.rowCount() == 16
    assert page.spectrum_table.rowCount() == 2
    assert not page.btn_export.isEnabled()


def test_plastic_ui_locks_cross_r_correction(qapp) -> None:
    page = _fast_page()
    page.mean_stress_combo.setCurrentIndex(1)
    page.material_type_combo.setCurrentText("工程塑料")
    assert page.mean_stress_combo.currentIndex() == 0
    assert not page.mean_stress_combo.isEnabled()
    assert not page.ultimate_edit.isEnabled()


def test_calculation_populates_five_badges_and_enables_export(qapp) -> None:
    page = _fast_page()
    page._on_calculate()
    assert page._last_result is not None
    assert page._last_result["overall_status"] in {"pass", "fail"}
    assert set(page.check_badges) == set(FATIGUE_CHECK_LABELS)
    assert all("待计算" not in badge.text() for badge in page.check_badges.values())
    assert page.btn_export.isEnabled()
    assert page.damage_chart._rows
    assert page.reliability_chart._data.get("life_quantiles_blocks")


def test_any_input_change_invalidates_all_visible_results(qapp) -> None:
    page = _fast_page()
    page._on_calculate()
    page.target_blocks_edit.setText("11")
    assert page._last_result is None
    assert not page.btn_export.isEnabled()
    assert page.overall_label.text() == "总体结论：待计算"
    assert not page.sn_chart._specimens
    assert not page.damage_chart._rows
    assert not page.reliability_chart._data
    assert all("待计算" in badge.text() for badge in page.check_badges.values())


def test_render_failure_clears_partial_result_and_disables_export(qapp) -> None:
    page = _fast_page()
    with (
        patch.object(page, "_build_report_lines", side_effect=RuntimeError("paint")),
        patch.object(QMessageBox, "critical") as critical,
    ):
        page._on_calculate()
    assert critical.called
    assert page._last_result is None
    assert page._last_payload is None
    assert not page.btn_export.isEnabled()
    assert page.overall_label.text() == "总体结论：待计算"
    assert not page.sn_chart._specimens
    assert all("待计算" in badge.text() for badge in page.check_badges.values())


def test_all_runout_renders_incomplete_not_pass(qapp) -> None:
    page = _fast_page()
    for row in range(page.sn_table.rowCount()):
        page.sn_table.setItem(row, 6, QTableWidgetItem("runout"))
    page._on_calculate()
    assert page._last_result is not None
    assert page._last_result["overall_status"] == "incomplete"
    assert "不完整" in page.overall_label.text()
    assert "通过" not in page.overall_label.text()


def test_snapshot_embeds_normalized_data_and_source_hash(qapp) -> None:
    page = _fast_page()
    snapshot = page._snapshot()
    encoded = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
    assert "内置测试案例 1" in encoded
    assert snapshot["inputs"]["test_data"]["source"]["sha256"] == "embedded"
    restored = _fast_page()
    restored._apply_payload(snapshot["inputs"])
    assert restored._build_payload() == snapshot["inputs"]


def test_csv_imports_update_tables_and_keep_sha256(qapp) -> None:
    page = _fast_page()
    root = Path(__file__).resolve().parents[2]
    sn_path = root / "examples" / "fatigue_sn_case_01.csv"
    spectrum_path = root / "examples" / "fatigue_spectrum_case_01.csv"
    with patch(
        "app.ui.pages.fatigue_reliability_page.QFileDialog.getOpenFileName",
        side_effect=[(str(sn_path), "CSV"), (str(spectrum_path), "CSV")],
    ):
        page._on_import_sn()
        page._on_import_spectrum()
    assert page.sn_table.rowCount() == 16
    assert page.spectrum_table.rowCount() == 2
    assert len(page._sn_source["sha256"]) == 64
    assert len(page._spectrum_source["sha256"]) == 64
    assert not page.btn_export.isEnabled()


def test_result_contract_and_three_report_formats(qapp, tmp_path: Path) -> None:
    page = _fast_page()
    payload = page._build_payload()
    result = page._calculate_fatigue(payload)
    view = from_fatigue(result, payload)
    assert len(view.checks) == 5
    assert any(metric.label == "目标寿命前失效概率 Pf" for metric in view.metrics)
    assert not any("N90" in metric.label for metric in view.metrics)

    pdf_path = tmp_path / "fatigue.pdf"
    docx_path = tmp_path / "fatigue.docx"
    txt_path = tmp_path / "fatigue.txt"
    page._render_result(payload, result)
    lines = page._build_report_lines()
    generate_fatigue_report(pdf_path, payload, result)
    _export_docx(docx_path, lines)
    write_text_report(txt_path, "\n".join(lines))

    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert pdf_path.stat().st_size > 10_000
    assert zipfile.is_zipfile(docx_path)
    assert "目标寿命前失效概率 Pf" in txt_path.read_text(encoding="utf-8")
    assert "存活率 Ps=90% 对应寿命" in txt_path.read_text(encoding="utf-8")
