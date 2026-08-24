"""AppComboBox owns popup polish; QComboBox is no longer monkeypatched."""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox

from app.ui.theme import apply_theme
from app.ui.widgets.app_combo_box import AppComboBox

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_theme(instance)
    return instance


def test_app_combo_box_uses_adjust_to_contents(app):
    combo = AppComboBox()
    assert combo.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToContents


def test_apply_theme_does_not_patch_qcombobox(app):
    original_init = QComboBox.__init__
    original_show = QComboBox.showPopup
    apply_theme(app)

    assert QComboBox.__init__ is original_init
    assert QComboBox.showPopup is original_show
    assert getattr(QComboBox.__init__, "__name__", "") != "patched_init"
    assert getattr(QComboBox.__init__, "__module__", "") != "app.ui.theme"
    assert getattr(QComboBox.showPopup, "__module__", "") != "app.ui.theme"

    raw = QComboBox()
    assert not isinstance(raw, AppComboBox)
    assert raw.sizeAdjustPolicy() != QComboBox.SizeAdjustPolicy.AdjustToContents


def test_page_choice_editors_are_app_combo_boxes(app):
    from app.ui.pages.bolt_page import BoltPage

    page = BoltPage()
    combos = page.findChildren(QComboBox)
    assert combos
    for combo in combos:
        assert isinstance(combo, AppComboBox)
        assert combo.sizeAdjustPolicy() == QComboBox.SizeAdjustPolicy.AdjustToContents


def test_app_combo_box_show_popup_widens_view(app):
    combo = AppComboBox()
    combo.addItems(["短", "圆柱体夹紧件非常长的选项文字"])
    combo.show()
    app.processEvents()
    combo.showPopup()
    app.processEvents()
    try:
        view = combo.view()
        assert view is not None
        longest = max(
            view.fontMetrics().horizontalAdvance(combo.itemText(i))
            for i in range(combo.count())
        )
        assert view.minimumWidth() >= combo.width()
        assert view.minimumWidth() >= longest + 56
        container = view.window()
        assert container is not combo.window()
        assert container.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert bool(container.windowFlags() & Qt.WindowType.FramelessWindowHint)
    finally:
        combo.hidePopup()
