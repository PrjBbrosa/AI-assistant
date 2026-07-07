from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage

_QT_APP: QApplication | None = None


def _app() -> QApplication:
    global _QT_APP
    _QT_APP = QApplication.instance() or _QT_APP or QApplication([])
    return _QT_APP


def _interference_page() -> InterferenceFitPage:
    app = _app()
    page = InterferenceFitPage()
    app.processEvents()
    return page


def _hertz_page() -> HertzContactPage:
    app = _app()
    page = HertzContactPage()
    app.processEvents()
    return page


def _bolt_page() -> BoltPage:
    app = _app()
    page = BoltPage()
    app.processEvents()
    return page


def _spline_page() -> SplineFitPage:
    app = _app()
    page = SplineFitPage()
    app.processEvents()
    return page


def test_interference_export_starts_disabled_and_only_reenables_after_calculate() -> None:
    page = _interference_page()

    assert not page.btn_save.isEnabled()

    page._calculate()
    _app().processEvents()
    assert page.btn_save.isEnabled()

    field = page._field_widgets["geometry.shaft_d_mm"]
    assert isinstance(field, QLineEdit)
    field.textEdited.emit(field.text())

    assert not page.btn_save.isEnabled()


def test_hertz_export_starts_disabled_and_only_reenables_after_calculate() -> None:
    page = _hertz_page()

    assert not page.btn_save.isEnabled()

    page._calculate()
    _app().processEvents()
    assert page.btn_save.isEnabled()

    field = page._field_widgets["loads.normal_force_n"]
    assert isinstance(field, QLineEdit)
    field.textEdited.emit(field.text())

    assert not page.btn_save.isEnabled()


def test_bolt_export_starts_disabled_and_only_reenables_after_calculate() -> None:
    page = _bolt_page()

    assert not page.btn_save.isEnabled()

    page._calculate()
    _app().processEvents()
    assert page.btn_save.isEnabled()

    field = page._field_widgets["loads.FA_max"]
    assert isinstance(field, QLineEdit)
    field.textEdited.emit(field.text())

    assert not page.btn_save.isEnabled()


def test_spline_export_disabled_immediately_on_edit() -> None:
    page = _spline_page()

    assert not page.btn_save.isEnabled()

    page._on_calculate()
    assert page.btn_save.isEnabled()

    field = page._widgets["loads.torque_required_nm"]
    assert isinstance(field, QLineEdit)
    field.setText("100000")

    assert not page.btn_save.isEnabled()


def test_spline_export_stays_disabled_after_clear() -> None:
    page = _spline_page()

    page._on_calculate()
    assert page.btn_save.isEnabled()

    page._clear()
    _app().processEvents()

    assert page._last_payload is None
    assert page._last_result is None
    assert not page.btn_save.isEnabled()
