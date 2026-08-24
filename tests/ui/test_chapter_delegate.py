"""Chapter list paint-only delegate contracts."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListWidget,
    QStyle,
    QStyleOptionViewItem,
    QWidget,
)

from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.theme import apply_theme
from app.ui.widgets.chapter_delegate import (
    ChapterNavigationDelegate,
    parse_chapter_item_text,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    yield app


def _assert_list_has_no_hidden_horizontal_overflow(app: QApplication, widget: QListWidget) -> None:
    original_policy = widget.horizontalScrollBarPolicy()
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    app.processEvents()
    try:
        assert widget.horizontalScrollBar().maximum() == 0
        assert not widget.horizontalScrollBar().isVisible()
    finally:
        widget.setHorizontalScrollBarPolicy(original_policy)
        app.processEvents()


def test_parse_chapter_item_text_keeps_title() -> None:
    tile, title = parse_chapter_item_text("步骤 3. 光滑段过盈（当前跳过）")
    assert tile == "03"
    assert title == "光滑段过盈（当前跳过）"


def test_item_text_and_tooltip_remain_full_step_label(qapp):
    page = BaseChapterPage("t", "s")
    first = QWidget()
    second = QWidget()
    page.add_chapter("连接件参数", first)
    page.add_chapter("校核结果与消息", second)
    assert page.chapter_list.item(0).text() == "步骤 1. 连接件参数"
    assert page.chapter_list.item(1).text() == "步骤 2. 校核结果与消息"
    assert page.chapter_list.item(0).toolTip() == page.chapter_list.item(0).text()
    assert page.chapter_list.item(1).toolTip() == page.chapter_list.item(1).text()
    page.chapter_list.item(1).setText("步骤 2. 校核结果与消息（已更新）")
    qapp.processEvents()
    assert page.chapter_list.item(1).toolTip() == "步骤 2. 校核结果与消息（已更新）"


def test_current_row_changed_drives_chapter_stack(qapp):
    page = BaseChapterPage("t", "s")
    first = QWidget()
    second = QWidget()
    page.add_chapter("A", first)
    page.add_chapter("B", second)
    page.set_current_chapter(0)
    assert page.chapter_stack.currentIndex() == 0
    assert page.chapter_page_at(0) is first
    page.chapter_list.setCurrentRow(1)
    qapp.processEvents()
    assert page.chapter_stack.currentIndex() == 1
    assert page.chapter_stack.currentWidget() is second
    assert isinstance(page.chapter_list.itemDelegate(), ChapterNavigationDelegate)


def test_no_horizontal_scroll_at_1180(qapp):
    host = QWidget()
    host.resize(1180, 720)
    layout = QHBoxLayout(host)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(12)
    sidebar = QWidget(host)
    sidebar.setFixedWidth(228)
    layout.addWidget(sidebar)
    page = HertzContactPage()
    layout.addWidget(page, 1)
    host.show()
    qapp.processEvents()
    try:
        chapter_list = page.chapter_list
        assert (
            chapter_list.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        assert chapter_list.horizontalScrollBar().maximum() == 0
        _assert_list_has_no_hidden_horizontal_overflow(qapp, chapter_list)
        for index in range(chapter_list.count()):
            item = chapter_list.item(index)
            assert item.toolTip() == item.text()
            assert item.text().startswith("步骤 ")
            assert (
                chapter_list.visualItemRect(item).width()
                <= chapter_list.viewport().width()
            )
        delegate = chapter_list.itemDelegate()
        assert isinstance(delegate, ChapterNavigationDelegate)
        option = QStyleOptionViewItem()
        model_index = chapter_list.model().index(0, 0)
        delegate.initStyleOption(option, model_index)
        option.rect = chapter_list.visualItemRect(chapter_list.item(0))
        option.state |= QStyle.StateFlag.State_Selected
        painted = delegate.elided_label(option, model_index)
        assert painted
        _tile, name = parse_chapter_item_text(chapter_list.item(0).text())
        assert painted == name or painted.startswith(name[:2])
    finally:
        host.close()
        page.deleteLater()
        qapp.processEvents()
