import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidget, QStyle, QStyleOptionViewItem

from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    yield instance


def test_main_window_minimum_supported_size(app):
    window = MainWindow()
    try:
        assert window.minimumWidth() == 1180
        assert window.minimumHeight() == 720
    finally:
        window.close()


def _assert_list_labels_are_not_elided(widget: QListWidget) -> None:
    """Verify the delegate's real text rect fits every complete label."""
    for item_index in range(widget.count()):
        item = widget.item(item_index)
        option = QStyleOptionViewItem()
        model_index = widget.model().index(item_index, 0)
        widget.itemDelegate().initStyleOption(option, model_index)
        option.rect = widget.visualItemRect(item)
        text_rect = widget.style().subElementRect(
            QStyle.SubElement.SE_ItemViewItemText,
            option,
            widget,
        )
        rendered_text = option.fontMetrics.elidedText(
            item.text(),
            widget.textElideMode(),
            text_rect.width(),
        )
        assert rendered_text == item.text(), (
            f"{item.text()!r} would render as {rendered_text!r} "
            f"inside {text_rect.width()} px"
        )


def _assert_list_has_no_hidden_horizontal_overflow(
    app: QApplication,
    widget: QListWidget,
) -> None:
    """Temporarily restore AsNeeded so AlwaysOff cannot make this test green."""
    original_policy = widget.horizontalScrollBarPolicy()
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    app.processEvents()
    try:
        assert widget.horizontalScrollBar().maximum() == 0
        assert not widget.horizontalScrollBar().isVisible()
    finally:
        widget.setHorizontalScrollBarPolicy(original_policy)
        app.processEvents()


def test_supported_size_navigation_has_no_horizontal_overflow(app):
    window = MainWindow()
    try:
        window.resize(1180, 720)
        window.show()
        app.processEvents()

        assert window.module_list.horizontalScrollBar().maximum() == 0
        assert (
            window.module_list.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # Exercise the longest module label in its selected (bold) state.
        window.module_list.setCurrentRow(window.module_list.count() - 1)
        app.processEvents()
        _assert_list_has_no_hidden_horizontal_overflow(app, window.module_list)
        _assert_list_labels_are_not_elided(window.module_list)

        # These modules contain the longest current chapter labels. Exercise
        # their actual rendered geometry rather than only minimumSize().
        for module_index in (1, 3):
            window.module_list.setCurrentRow(module_index)
            app.processEvents()
            chapter_list = window.stack.currentWidget().chapter_list

            assert chapter_list.horizontalScrollBar().maximum() == 0
            assert (
                chapter_list.horizontalScrollBarPolicy()
                == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            assert chapter_list.viewport().width() >= 220
            _assert_list_has_no_hidden_horizontal_overflow(app, chapter_list)
            _assert_list_labels_are_not_elided(chapter_list)

            for item_index in range(chapter_list.count()):
                item = chapter_list.item(item_index)
                assert (
                    chapter_list.visualItemRect(item).width()
                    <= chapter_list.viewport().width()
                )
                assert item.toolTip() == item.text()
    finally:
        window.close()


def test_materials_library_sidebar_is_marked_unfinished(app):
    window = MainWindow()
    try:
        items = [
            window.module_list.item(i).text()
            for i in range(window.module_list.count())
        ]
        assert any("材料与标准库" in text and "即将推出" in text for text in items)
    finally:
        window.close()
