from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage

_QT_APP: QApplication | None = None


def _app() -> QApplication:
    global _QT_APP
    _QT_APP = QApplication.instance() or _QT_APP or QApplication([])
    return _QT_APP


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
    assert not page.btn_save.isEnabled()
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
    assert not page.btn_save.isEnabled()
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
    assert not page.btn_save.isEnabled()
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
    assert "内部错误" in page.overall_badge.text()
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
    assert not page.btn_save.isEnabled()
    assert "结果渲染失败" in page.info_label.text()
