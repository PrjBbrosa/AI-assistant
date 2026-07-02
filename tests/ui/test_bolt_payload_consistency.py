"""bolt 原始 JSON 载入后下拉、锁定状态与 payload 必须一致（spec 2026-07-02 D12）。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EXAMPLES = Path("examples")


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _page(qapp: QApplication):
    from app.ui.pages.bolt_page import BoltPage

    return BoltPage()


def test_grade_dropdown_syncs_with_raw_rp02_not_in_table(qapp: QApplication) -> None:
    """Rp02=940 不在等级表：grade 不得停留默认 8.8，Rp02 应解锁可编辑。"""
    page = _page(qapp)
    data = json.loads((EXAMPLES / "input_case_02.json").read_text(encoding="utf-8"))
    assert float(data["fastener"]["Rp02"]) == 940.0

    page._apply_input_data(data)

    grade = page._field_widgets["fastener.grade"]
    rp02 = page._field_widgets["fastener.Rp02"]
    assert isinstance(grade, QComboBox)
    assert isinstance(rp02, QLineEdit)
    assert grade.currentText() != "8.8", "grade 下拉与 Rp02=940 自相矛盾"
    assert not rp02.isReadOnly(), "非表内 Rp02 必须解锁为手动值"


def test_grade_dropdown_reverse_lookup_hits_table(qapp: QApplication) -> None:
    """Rp02=640 命中表：grade 应选中 8.8 且 Rp02 锁定。"""
    page = _page(qapp)
    data = json.loads((EXAMPLES / "input_case_01.json").read_text(encoding="utf-8"))
    data["fastener"]["Rp02"] = 640.0

    page._apply_input_data(data)

    assert page._field_widgets["fastener.grade"].currentText() == "8.8"
    assert page._field_widgets["fastener.Rp02"].isReadOnly()


def test_surface_class_mapping_no_double_write(qapp: QApplication) -> None:
    """basic_solid/surface_class 的 FieldSpec.mapping 为 None，payload 仍写英文枚举。"""
    from app.ui.pages.bolt_page import CHAPTERS

    by_id = {
        spec.field_id: spec
        for chapter in CHAPTERS
        for spec in chapter["fields"]
    }
    assert by_id["clamped.basic_solid"].mapping is None
    assert by_id["clamped.surface_class"].mapping is None

    page = _page(qapp)
    payload = page._build_payload()
    assert payload["clamped"]["surface_class"] in {"fine", "medium", "rough"}
    assert payload["clamped"]["basic_solid"] in {"cylinder", "cone", "sleeve"}


def test_raw_choice_fallbacks_restore_mappingless_clamped_selectors(
    qapp: QApplication,
) -> None:
    """mapping=None 后，原始 payload 仍能反查 basic_solid/surface_class 到 UI 下拉。"""
    page = _page(qapp)
    data = json.loads((EXAMPLES / "input_case_01.json").read_text(encoding="utf-8"))
    data["clamped"]["basic_solid"] = "cone"
    data["clamped"]["surface_class"] = "fine"

    page._apply_input_data(data)

    assert page._field_widgets["clamped.basic_solid"].currentText() == "锥体"
    assert page._field_widgets["clamped.surface_class"].currentText() == "精细 (Ra≈1.6μm)"


def test_fine_pitch_payload_roundtrip(qapp: QApplication) -> None:
    """细牙 M10x1.0 载入后 payload 的 p 必须是 1.0，不被默认粗牙覆盖。"""
    page = _page(qapp)
    data = json.loads((EXAMPLES / "input_case_01.json").read_text(encoding="utf-8"))
    data["fastener"]["d"] = 10
    data["fastener"]["p"] = 1.0
    for key in ("As", "d2", "d3"):
        data["fastener"].pop(key, None)

    page._apply_input_data(data)

    payload = page._build_payload()
    assert payload["fastener"]["p"] == pytest.approx(1.0)
