"""Cloud Porcelain main-window shell geometry and lazy-load contract."""

from __future__ import annotations

import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QWidget

from app.ui.design_tokens import cloud_porcelain_spacing
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme, build_style_sheet
from app.ui.widgets.cloud_canvas import CloudCanvas


OFFICIAL_MODULE_NAMES = (
    "螺栓连接",
    "轴向受力螺纹连接",
    "过盈配合",
    "花键连接校核",
    "蜗轮蜗杆设计",
    "赫兹应力",
    "缓冲块吸能仿真",
)


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    yield instance


def _show(app: QApplication, window: MainWindow, width: int, height: int) -> None:
    window.resize(width, height)
    window.show()
    app.processEvents()


def test_central_cloud_canvas_exists(app):
    window = MainWindow()
    try:
        canvas = window.centralWidget()
        assert isinstance(canvas, CloudCanvas)
        assert canvas.objectName() == "CloudCanvas"
        assert not window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        assert not bool(window.windowFlags() & Qt.WindowType.FramelessWindowHint)
    finally:
        window.close()


def test_canvas_margins_and_splitter_gap_at_default_size(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        spacing = cloud_porcelain_spacing()
        canvas = window.centralWidget()
        margins = canvas.layout().contentsMargins()
        assert margins.left() == spacing.canvas_margin
        assert margins.top() == spacing.canvas_margin
        assert margins.right() == spacing.canvas_margin
        assert margins.bottom() == spacing.canvas_margin

        assert window.splitter.handleWidth() == 4
        assert window.splitter.childrenCollapsible() is False

        sidebar = window.findChild(QFrame, "SidebarPanel")
        chrome = window.findChild(QFrame, "WorkspaceChrome")
        assert sidebar is not None and chrome is not None
        sidebar_right = sidebar.mapTo(canvas, QPoint(sidebar.width(), 0)).x()
        chrome_left = chrome.mapTo(canvas, QPoint(0, 0)).x()
        gap = chrome_left - sidebar_right
        assert abs(gap - spacing.sidebar_gap) <= 2, gap
        assert abs(sidebar.width() - spacing.sidebar_width) <= 2, sidebar.width()
    finally:
        window.close()


def test_sidebar_min_max_via_splitter_resize(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        spacing = cloud_porcelain_spacing()
        sidebar = window.findChild(QFrame, "SidebarPanel")
        assert sidebar.minimumWidth() == spacing.sidebar_min
        assert sidebar.maximumWidth() == spacing.sidebar_max

        window.splitter.setSizes([spacing.sidebar_min, 2000])
        app.processEvents()
        assert abs(sidebar.width() - spacing.sidebar_min) <= 2, sidebar.width()

        window.splitter.setSizes([spacing.sidebar_max, 2000])
        app.processEvents()
        assert abs(sidebar.width() - spacing.sidebar_max) <= 2, sidebar.width()

        window.splitter.setSizes([160, 2000])
        app.processEvents()
        assert sidebar.width() >= spacing.sidebar_min
        assert sidebar.width() <= spacing.sidebar_max
    finally:
        window.close()


def test_sidebar_panel_radius_and_brand_tile(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        sidebar = window.findChild(QFrame, "SidebarPanel")
        assert sidebar is not None
        assert sidebar.objectName() == "SidebarPanel"
        match = re.search(
            r"QFrame#SidebarPanel \{(?P<body>.*?)\}",
            build_style_sheet(),
            flags=re.DOTALL,
        )
        assert match is not None
        assert "border-radius: 22px" in match.group("body")

        tile = window.findChild(QLabel, "BrandTile")
        assert tile is not None
        assert tile.width() == 35
        assert tile.height() == 35
        title = window.findChild(QLabel, "BrandTitle")
        subtitle = window.findChild(QLabel, "BrandSubtitle")
        assert title is not None and title.text() == "Engineering Assistant"
        assert subtitle is not None
        assert subtitle.text() == "Local Mechanical Design Workbench"

        info = window.findChild(QFrame, "SidebarInfoCard")
        assert info is not None
        info_title = window.findChild(QLabel, "SidebarInfoTitle")
        info_body = window.findChild(QLabel, "SidebarInfoBody")
        assert info_title is not None and info_title.text() == "本地工程计算"
        assert info_body is not None
        assert "预校核" in info_body.text()
        assert "本地" in info_body.text()
    finally:
        window.close()


def test_no_180px_brand_mark_pixmap(app):
    window = MainWindow()
    try:
        assert window.findChild(QLabel, "SidebarBrandMark") is None
        for label in window.findChildren(QLabel):
            pixmap = label.pixmap()
            if pixmap is None or pixmap.isNull():
                continue
            logical_w = int(round(pixmap.width() / max(pixmap.devicePixelRatio(), 1.0)))
            logical_h = int(round(pixmap.height() / max(pixmap.devicePixelRatio(), 1.0)))
            assert logical_w < 160, (label.objectName(), logical_w, logical_h)
            assert logical_h < 160, (label.objectName(), logical_w, logical_h)
    finally:
        window.close()


def test_module_item_text_format_and_no_status_dots(app):
    window = MainWindow()
    try:
        expected = [f"{index + 1}. {name}" for index, name in enumerate(OFFICIAL_MODULE_NAMES)]
        expected.append("8. 材料与标准库（即将推出）")
        actual = [
            window.module_list.item(index).text()
            for index in range(window.module_list.count())
        ]
        assert actual == expected
        for index in range(window.module_list.count()):
            item = window.module_list.item(index)
            assert item.toolTip() == item.text()

        for widget in window.findChildren(QWidget):
            name = widget.objectName().lower().replace("_", "-")
            assert "status-dot" not in name
            assert "ready-dot" not in name
            assert "statusdot" not in name
            assert "readydot" not in name
    finally:
        window.close()


def test_lazy_pages_only_construct_first_module_at_startup(app):
    window = MainWindow()
    try:
        assert window._pages[0] is not None
        assert all(page is None for page in window._pages[1:])
        window.module_list.setCurrentRow(2)
        app.processEvents()
        assert window._pages[2] is not None
        assert window._pages[1] is None
        assert window._pages[3] is None
    finally:
        window.close()


def test_min_size_shows_bolt_primary_action_without_module_hscroll(app):
    window = MainWindow()
    try:
        _show(app, window, 1180, 720)
        page = window._pages[0]
        assert page is not None
        button = page.btn_calculate
        assert not button.isHidden()
        assert button.width() > 0
        assert button.height() > 0
        top_left = button.mapTo(window, button.rect().topLeft())
        bottom_right = button.mapTo(window, button.rect().bottomRight())
        assert top_left.x() >= 0
        assert top_left.y() >= 0
        assert bottom_right.x() <= window.width()
        assert bottom_right.y() <= window.height()
        assert (
            window.module_list.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        assert window.module_list.horizontalScrollBar().maximum() == 0
    finally:
        window.close()


def test_status_bar_show_message_still_works(app):
    window = MainWindow()
    try:
        window.statusBar().showMessage("probe-status")
        assert window.statusBar().currentMessage() == "probe-status"
        window.statusBar().setStatusTip("probe-tip")
        assert window.statusBar().statusTip() == "probe-tip"
        window.statusBar().showMessage("桌面框架就绪")
        assert "桌面框架就绪" in window.statusBar().currentMessage()
    finally:
        window.close()
