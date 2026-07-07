import os
from collections import Counter

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QWidget

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.theme import apply_theme

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_THEME_APPLIED_PROPERTY = "_ai_assistant_test_theme_applied_once"


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def _ensure_theme(app: QApplication) -> None:
    if not app.property(_THEME_APPLIED_PROPERTY) or not app.styleSheet():
        apply_theme(app)
        app.setProperty(_THEME_APPLIED_PROPERTY, True)


@pytest.mark.parametrize(
    "page_cls",
    [
        BoltPage,
        BoltTappedAxialPage,
        HertzContactPage,
        InterferenceFitPage,
        SplineFitPage,
    ],
)
def test_input_field_cards_are_marked_for_transparent_surface(app, page_cls):
    page = page_cls()

    assert page._field_cards  # type: ignore[attr-defined]
    for field_id, card in page._field_cards.items():  # type: ignore[attr-defined]
        assert card.property("surfaceRole") == "inputField", field_id


def test_theme_makes_only_input_field_cards_transparent(app):
    _ensure_theme(app)
    stylesheet = app.styleSheet()

    assert 'QFrame#SubCard[surfaceRole="inputField"]' in stylesheet
    assert 'QFrame#AutoCalcCard[surfaceRole="inputField"]' in stylesheet
    assert 'QFrame#DisabledSubCard[surfaceRole="inputField"]' in stylesheet
    assert 'QFrame#SubCard[surfaceRole="inputField"] QWidget#InputFieldLabelWrap' in stylesheet
    assert "background-color: transparent;" in stylesheet


def test_input_field_label_wrapper_renders_without_extra_background(app):
    _ensure_theme(app)
    page = BoltTappedAxialPage()
    page.resize(1270, 920)
    page.chapter_stack.setCurrentIndex(1)
    page.chapter_list.setCurrentRow(1)
    page.show()
    app.processEvents()

    card = page._field_cards["fastener.d"]  # type: ignore[attr-defined]
    label_wrap = card.findChild(QWidget, "InputFieldLabelWrap")
    assert label_wrap is not None
    image = page.grab().toImage()

    def region_mode(widget: QWidget, x0: int, y0: int, width: int, height: int):
        colors: Counter[tuple[int, int, int]] = Counter()
        for x in range(max(0, x0), min(widget.width(), x0 + width)):
            for y in range(max(0, y0), min(widget.height(), y0 + height)):
                point = widget.mapTo(page, QPoint(x, y))
                color = image.pixelColor(point)
                colors[(color.red(), color.green(), color.blue())] += 1
        return colors.most_common(1)[0][0]

    label_bg = region_mode(label_wrap, 0, 0, label_wrap.width(), label_wrap.height())
    row_bg = region_mode(
        card,
        2,
        label_wrap.geometry().bottom() + 4,
        max(1, label_wrap.width()),
        12,
    )
    assert label_bg == row_bg
