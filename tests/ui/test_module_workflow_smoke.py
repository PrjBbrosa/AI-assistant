"""Offscreen 7-module workflow smoke (QT_QPA_PLATFORM=offscreen).

This is not Windows packaged-exe smoke. Packaged Windows smoke remains a
manual checklist in scripts/windows_smoke.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.buffer_energy_page import BufferEnergyPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage


_QT_APP: QApplication | None = None

_REPORT_TOKENS = ("总体", "预校核", "校核")
_INPUT_HASH_LABEL = "输入摘要哈希"


@dataclass(frozen=True)
class WorkflowCase:
    name: str
    page_cls: type[Any]
    sample: str
    calculate_method: str
    export_button_names: tuple[str, ...]
    traces_input_hash: bool


WORKFLOW_CASES: tuple[WorkflowCase, ...] = (
    WorkflowCase(
        name="bolt",
        page_cls=BoltPage,
        sample="input_case_01.json",
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        traces_input_hash=True,
    ),
    WorkflowCase(
        name="bolt_tapped_axial",
        page_cls=BoltTappedAxialPage,
        sample="tapped_axial_joint_case_01.json",
        calculate_method="_run_calculation",
        export_button_names=("btn_export_text", "btn_export_pdf"),
        traces_input_hash=True,
    ),
    WorkflowCase(
        name="interference",
        page_cls=InterferenceFitPage,
        sample="interference_case_01.json",
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        traces_input_hash=True,
    ),
    WorkflowCase(
        name="hertz",
        page_cls=HertzContactPage,
        sample="hertz_case_01.json",
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        traces_input_hash=True,
    ),
    WorkflowCase(
        name="worm",
        page_cls=WormGearPage,
        sample="worm_case_01.json",
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        traces_input_hash=True,
    ),
    WorkflowCase(
        name="spline",
        page_cls=SplineFitPage,
        sample="spline_case_01.json",
        calculate_method="_on_calculate",
        export_button_names=("btn_save",),
        traces_input_hash=True,
    ),
    WorkflowCase(
        name="buffer",
        page_cls=BufferEnergyPage,
        sample="buffer_energy_case_01.csv",
        calculate_method="_on_calculate",
        export_button_names=("btn_save_report",),
        traces_input_hash=True,
    ),
)


def _app() -> QApplication:
    global _QT_APP
    _QT_APP = QApplication.instance() or _QT_APP or QApplication([])
    return _QT_APP


def _export_buttons(page: Any, names: tuple[str, ...]) -> list[Any]:
    return [getattr(page, name) for name in names]


def _report_and_equivalent_text(page: Any) -> str:
    chunks = ["\n".join(page._build_report_lines())]
    for attr in ("result_title", "result_summary", "overall_verdict_label"):
        widget = getattr(page, attr, None)
        if widget is None:
            continue
        text_fn = getattr(widget, "text", None)
        if callable(text_fn):
            chunks.append(str(text_fn()))
    return "\n".join(chunks)


@pytest.fixture(scope="module")
def app() -> QApplication:
    return _app()


@pytest.fixture(autouse=True)
def fail_on_message_box(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*args: Any, **kwargs: Any) -> None:
        raise AssertionError(f"unexpected QMessageBox during workflow smoke: {args!r} {kwargs!r}")

    monkeypatch.setattr(QMessageBox, "critical", _fail)
    monkeypatch.setattr(QMessageBox, "warning", _fail)
    monkeypatch.setattr(QMessageBox, "information", _fail)


@pytest.mark.parametrize(
    "case",
    WORKFLOW_CASES,
    ids=[case.name for case in WORKFLOW_CASES],
)
def test_module_workflow_smoke_loads_sample_calculates_and_reports(
    app: QApplication,
    case: WorkflowCase,
) -> None:
    page = case.page_cls()
    app.processEvents()
    buttons = _export_buttons(page, case.export_button_names)

    assert all(not button.isEnabled() for button in buttons)

    page._load_sample(case.sample)
    app.processEvents()

    getattr(page, case.calculate_method)()
    app.processEvents()

    assert isinstance(page._last_result, dict)
    assert page._last_result
    assert all(button.isEnabled() for button in buttons)

    report_lines = page._build_report_lines()
    report_text = "\n".join(report_lines)
    visible = _report_and_equivalent_text(page)
    assert any(token in visible for token in _REPORT_TOKENS), visible
    if case.traces_input_hash:
        assert _INPUT_HASH_LABEL in report_text
        assert "sha256:" in report_text
