from __future__ import annotations

from copy import deepcopy
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.buffer_energy_page import BufferEnergyPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage

_QT_APP: QApplication | None = None


def _app() -> QApplication:
    global _QT_APP
    _QT_APP = QApplication.instance() or _QT_APP or QApplication([])
    return _QT_APP


def _assert_overflow_export_disabled(page: object, *button_names: str) -> None:
    page.show()  # type: ignore[union-attr]
    page.resize(640, 400)  # type: ignore[union-attr]
    _app().processEvents()
    controller = getattr(page, "_action_overflow", None)
    assert controller is not None
    controller.relayout()
    _app().processEvents()
    for name in button_names:
        button = getattr(page, name)
        assert not button.isEnabled()
        action = controller.action_for(button)
        assert action is not None
        controller.sync_button(button)
        assert not action.isEnabled()


def test_interference_render_failure_rolls_back_result_and_disables_export() -> None:
    app = _app()
    page = InterferenceFitPage()
    app.processEvents()

    page._calculate()
    assert page._last_result is not None
    assert page.btn_save.isEnabled()

    bad_result = {
        "overall_pass": True,
        "checks": {"torque_ok": True},
        # Intentionally omit "pressure_mpa", "capacity", "assembly" and other
        # required render fields so _render_result fails after calculation.
    }

    with patch("app.ui.pages.interference_fit_page.calculate_interference_fit", return_value=bad_result), \
            patch("app.ui.pages.interference_fit_page.QMessageBox.critical", return_value=None) as critical:
        page._calculate()

    critical.assert_called_once()
    assert critical.call_args.args[1] == "渲染异常"
    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_save")
    assert "结果渲染失败" in page.info_label.text()
    assert page.result_title.text() == "尚未执行计算"
    assert page.metrics_text.text() == "尚无结果。"
    assert page.message_box.toPlainText() == ""
    assert all(badge.text() == "待计算" for badge in page._check_badges.values())


def test_hertz_render_failure_rolls_back_result_and_disables_export() -> None:
    app = _app()
    page = HertzContactPage()
    app.processEvents()

    page._calculate()
    assert page._last_result is not None
    assert page.btn_save.isEnabled()

    def fail_render(_result: dict) -> None:
        raise RuntimeError("broken hertz render")

    with patch.object(page, "_render_result", side_effect=fail_render), \
            patch("app.ui.pages.hertz_contact_page.QMessageBox.critical", return_value=None) as critical:
        page._calculate()

    critical.assert_called_once()
    assert critical.call_args.args[1] == "渲染异常"
    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_save")
    assert "结果渲染失败" in page.info_label.text()
    assert page.result_title.text() == "尚未执行计算"
    assert page.metrics_text.text() == "尚无结果。"
    assert page.message_box.toPlainText() == ""
    assert all(badge.text() == "待计算" for badge in page._check_badges.values())


def test_worm_render_failure_rolls_back_result_and_disables_export() -> None:
    app = _app()
    page = WormGearPage()
    app.processEvents()

    page._calculate()
    assert page._last_result is not None
    assert page.btn_save.isEnabled()

    bad_result = {
        "geometry": {},
        "performance": {},
        "curve": {},
        "load_capacity": {},
    }

    with patch("app.ui.pages.worm_gear_page.calculate_worm_geometry", return_value=bad_result), \
            patch("app.ui.pages.worm_gear_page.QMessageBox.critical", return_value=None) as critical:
        page._calculate()

    critical.assert_called_once()
    assert critical.call_args.args[1] == "渲染异常"
    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_save")
    assert "结果渲染失败" in page.info_label.text()
    assert page.result_title.text() == "尚未执行计算"
    assert page.result_metrics.toPlainText() == "尚无结果。"
    assert all(badge.text() == "待计算" for _name, badge in page._check_badges.values())


def test_spline_render_failure_rolls_back_result_without_escaping() -> None:
    app = _app()
    page = SplineFitPage()
    app.processEvents()

    assert page._last_result is not None

    def fail_render(_result: dict) -> None:
        raise RuntimeError("broken spline render")

    with patch.object(page, "_display_result", side_effect=fail_render):
        page._run_calculation(strict=True)

    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_save")
    assert "内部错误" in page.info_label.text()
    assert "broken spline render" in page.info_label.text()


def test_bolt_render_failure_rolls_back_result_and_disables_export() -> None:
    app = _app()
    page = BoltPage()
    app.processEvents()

    page._calculate()
    assert page._last_result is not None
    assert page.btn_save.isEnabled()

    def fail_render(_payload: dict, _result: dict) -> None:
        raise RuntimeError("broken bolt render")

    with patch.object(page, "_render_result", side_effect=fail_render), \
            patch("app.ui.pages.bolt_page.QMessageBox.critical", return_value=None) as critical:
        page._calculate()

    critical.assert_called_once()
    assert critical.call_args.args[1] == "渲染异常"
    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_save")
    assert "结果渲染失败" in page.info_label.text()
    assert page.result_title.text() == "尚未执行计算"
    assert all(badge.text() == "待计算" for badge in page._check_badges.values())


def test_bolt_tapped_axial_render_failure_rolls_back_result_and_disables_export() -> None:
    app = _app()
    page = BoltTappedAxialPage()
    app.processEvents()

    page._run_calculation()
    assert page._last_result is not None
    assert page.btn_export_text.isEnabled()
    assert page.btn_export_pdf.isEnabled()

    bad_result = deepcopy(page._last_result)
    bad_result["assembly"]["F_preload_min_N"] = None

    with patch(
        "app.ui.pages.bolt_tapped_axial_page.calculate_tapped_axial_joint",
        return_value=bad_result,
    ), patch(
        "app.ui.pages.bolt_tapped_axial_page.QMessageBox.critical",
        return_value=None,
    ) as critical:
        try:
            page._run_calculation()
        except Exception as exc:  # pragma: no cover - documents the RED failure mode
            pytest.fail(f"_run_calculation 应保护渲染异常，实际抛出：{exc!r}")

    critical.assert_called_once()
    assert critical.call_args.args[1] == "渲染异常"
    assert "结果展示失败" in critical.call_args.args[2]
    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_export_text", "btn_export_pdf")


def test_buffer_render_failure_rolls_back_result_and_disables_export() -> None:
    app = _app()
    page = BufferEnergyPage()
    app.processEvents()
    page._load_sample("buffer_energy_case_01.csv")
    page._on_calculate()
    assert page._last_result is not None
    assert page.btn_save_report.isEnabled()

    def fail_render(_result: dict) -> None:
        raise RuntimeError("broken buffer render")

    with patch.object(page, "_render_result", side_effect=fail_render), patch(
        "app.ui.pages.buffer_energy_page.QMessageBox.warning",
        return_value=None,
    ) as warning:
        page._on_calculate()

    warning.assert_called_once()
    assert page._last_payload is None
    assert page._last_result is None
    _assert_overflow_export_disabled(page, "btn_save_report")
    assert page.overall_verdict_label.text() == "总体结论: 待计算"
    assert all("待计算" in badge.text() for badge in page.check_badges.values())
    assert page.response_widget.response_data()[1] is None
    assert page.compare_table.rowCount() == 0
