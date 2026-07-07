from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage

_QT_APP: QApplication | None = None


def _app() -> QApplication:
    global _QT_APP
    _QT_APP = QApplication.instance() or _QT_APP or QApplication([])
    return _QT_APP


@dataclass(frozen=True)
class ExportDirtyContract:
    name: str
    page_cls: type[Any]
    calculate_method: str
    export_button_names: tuple[str, ...]
    widget_map_name: str
    edit_field_id: str


# BufferEnergyPage keeps a different export button contract (btn_save_report)
# and has curve-import side effects, so it stays under its dedicated tests.
EXPORT_DIRTY_CONTRACTS = (
    ExportDirtyContract(
        name="bolt",
        page_cls=BoltPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="loads.FA_max",
    ),
    ExportDirtyContract(
        name="hertz",
        page_cls=HertzContactPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="loads.normal_force_n",
    ),
    ExportDirtyContract(
        name="interference",
        page_cls=InterferenceFitPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="geometry.shaft_d_mm",
    ),
    ExportDirtyContract(
        name="spline",
        page_cls=SplineFitPage,
        calculate_method="_on_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_widgets",
        edit_field_id="loads.torque_required_nm",
    ),
    ExportDirtyContract(
        name="worm",
        page_cls=WormGearPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="operating.input_torque_nm",
    ),
    ExportDirtyContract(
        name="bolt_tapped_axial",
        page_cls=BoltTappedAxialPage,
        calculate_method="_run_calculation",
        export_button_names=("btn_export_text", "btn_export_pdf"),
        widget_map_name="_field_widgets",
        edit_field_id="fastener.d",
    ),
)


def _make_page(page_cls: type[Any]) -> Any:
    app = _app()
    page = page_cls()
    app.processEvents()
    return page


def _export_buttons(page: Any, button_names: tuple[str, ...]) -> list[Any]:
    return [getattr(page, name) for name in button_names]


def _changed_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return "1"
    try:
        return f"{float(text) + 1:g}"
    except ValueError:
        return f"{text}_edited"


def _edit_line(field: QLineEdit) -> None:
    new_text = _changed_text(field.text())
    field.setText(new_text)
    field.textEdited.emit(new_text)


@pytest.mark.parametrize(
    "contract",
    EXPORT_DIRTY_CONTRACTS,
    ids=[contract.name for contract in EXPORT_DIRTY_CONTRACTS],
)
def test_export_buttons_disable_until_calculate_and_dirty_on_edit(
    contract: ExportDirtyContract,
) -> None:
    page = _make_page(contract.page_cls)
    buttons = _export_buttons(page, contract.export_button_names)

    assert all(not button.isEnabled() for button in buttons)

    getattr(page, contract.calculate_method)()
    _app().processEvents()
    assert all(button.isEnabled() for button in buttons)

    widget_map = getattr(page, contract.widget_map_name)
    field = widget_map[contract.edit_field_id]
    assert isinstance(field, QLineEdit)
    _edit_line(field)
    _app().processEvents()

    assert all(not button.isEnabled() for button in buttons)


def test_spline_export_stays_disabled_after_clear() -> None:
    page = _make_page(SplineFitPage)

    page._on_calculate()
    assert page.btn_save.isEnabled()

    page._clear()
    _app().processEvents()

    assert page._last_payload is None
    assert page._last_result is None
    assert not page.btn_save.isEnabled()
