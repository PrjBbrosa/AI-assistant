"""Stable Cloud Porcelain render/geometry contract (spec §14).

Asserts device-independent geometry, hit areas, scrollbar policy, and
token sample points. Does not use full PNG binary equality as a gate.
"""

from __future__ import annotations

import math
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QListWidget, QPushButton

from app.ui.design_tokens import (
    cloud_porcelain_controls,
    cloud_porcelain_palette,
    cloud_porcelain_radii,
    cloud_porcelain_spacing,
    qcolor,
)
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme, build_style_sheet
from app.ui.widgets.cloud_canvas import CloudCanvas
from app.ui.widgets.help_button import HelpButton
from tests.ui.cloud_component_gallery import build_cloud_component_gallery
from tools.render_cloud_porcelain_matrix import (
    delta_e2000,
    logical_pixel,
    rgb_distance,
    rgb_tuple,
)


SUPPORTED_SIZES = ((1024, 640), (1400, 860))
OLD_SIDEBAR_BEIGE = QColor("#EEE7DE")
INSUFFICIENT_ACCENT = QColor("#C76C4D")
GREEN_READY = QColor("#2B715C")


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    return instance


def _show(app: QApplication, window: MainWindow, width: int, height: int) -> None:
    window.resize(width, height)
    window.show()
    app.processEvents()
    app.processEvents()


def _map_px(image, widget, x: int, y: int) -> tuple[int, int, int]:
    return logical_pixel(image, widget, x, y)


def test_supported_window_sizes(app):
    window = MainWindow()
    try:
        assert window.minimumWidth() == 1024
        assert window.minimumHeight() == 640
        _show(app, window, 1400, 860)
        assert window.width() == 1400
        assert window.height() == 860
        _show(app, window, 1024, 640)
        assert window.width() == 1024
        assert window.height() == 640
    finally:
        window.close()


def test_sidebar_width_and_limits_at_default_size(app):
    window = MainWindow()
    spacing = cloud_porcelain_spacing()
    try:
        _show(app, window, 1400, 860)
        sidebar = window.findChild(QFrame, "SidebarPanel")
        assert sidebar is not None
        assert abs(sidebar.width() - 228) <= 2, sidebar.width()
        assert sidebar.minimumWidth() == 212
        assert sidebar.maximumWidth() == 280
        assert spacing.sidebar_width == 228
        assert spacing.sidebar_min == 212
        assert spacing.sidebar_max == 280

        window.splitter.setSizes([spacing.sidebar_min, 2000])
        app.processEvents()
        assert abs(sidebar.width() - 212) <= 2, sidebar.width()
        window.splitter.setSizes([spacing.sidebar_max, 2000])
        app.processEvents()
        assert abs(sidebar.width() - 280) <= 2, sidebar.width()
    finally:
        window.close()


def test_canvas_margin_and_gap_at_1400(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        spacing = cloud_porcelain_spacing()
        canvas = window.centralWidget()
        assert isinstance(canvas, CloudCanvas)
        margins = canvas.layout().contentsMargins()
        for value in (margins.left(), margins.top(), margins.right(), margins.bottom()):
            assert abs(value - 12) <= 2, value
        assert spacing.canvas_margin == 12
        assert spacing.sidebar_gap == 12

        sidebar = window.findChild(QFrame, "SidebarPanel")
        chrome = window.findChild(QFrame, "WorkspaceChrome")
        assert sidebar is not None and chrome is not None
        sidebar_right = sidebar.mapTo(canvas, QPoint(sidebar.width(), 0)).x()
        chrome_left = chrome.mapTo(canvas, QPoint(0, 0)).x()
        gap = chrome_left - sidebar_right
        assert abs(gap - 12) <= 2, gap
    finally:
        window.close()


def test_help_overflow_and_standard_button_hit_areas(app):
    controls = cloud_porcelain_controls()
    gallery = build_cloud_component_gallery()
    window = MainWindow()
    try:
        gallery.show()
        app.processEvents()
        assert gallery.help_button.width() == 24
        assert gallery.help_button.height() == 24
        assert gallery.help_button.width() == controls.help_button_outer
        assert gallery.overflow_button.width() >= 28
        assert gallery.overflow_button.height() >= 28
        assert 28 <= gallery.btn_primary.height() <= 42
        assert 28 <= gallery.btn_secondary.height() <= 42

        _show(app, window, 1400, 860)
        page = window._pages[0]
        assert page is not None
        help_btn = page.findChild(HelpButton)
        if help_btn is not None:
            assert help_btn.width() == 24
            assert help_btn.height() == 24
        overflow = page.findChild(QPushButton, "OverflowButton")
        assert overflow is not None
        assert overflow.minimumWidth() >= 28
        assert overflow.minimumHeight() >= 28
        primary = page.findChild(QPushButton, "PrimaryButton")
        assert primary is not None
        assert not primary.isHidden()
        assert 28 <= primary.height() <= 42
        assert primary.height() >= controls.primary_button_height - 2
    finally:
        gallery.close()
        window.close()


def test_module_and_chapter_lists_have_no_horizontal_scroll(app):
    window = MainWindow()
    try:
        for width, height in SUPPORTED_SIZES:
            _show(app, window, width, height)
            assert window.module_list.horizontalScrollBar().maximum() == 0
            assert (
                window.module_list.horizontalScrollBarPolicy()
                == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            for row in range(7):
                window.module_list.setCurrentRow(row)
                app.processEvents()
                page = window._pages[row]
                assert page is not None
                chapter_list = getattr(page, "chapter_list", None)
                assert isinstance(chapter_list, QListWidget)
                assert chapter_list.horizontalScrollBar().maximum() == 0, (
                    width,
                    height,
                    row,
                    chapter_list.horizontalScrollBar().maximum(),
                )
    finally:
        window.close()


def test_canvas_corner_token_sample_not_old_beige(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        canvas = window.centralWidget()
        assert isinstance(canvas, CloudCanvas)
        image = canvas.grab().toImage()
        sample = _map_px(image, canvas, 2, 2)
        expected = rgb_tuple(qcolor("canvas_base"))
        assert expected == (0xEF, 0xF0, 0xEF)
        assert rgb_distance(sample, expected) <= 12
        assert delta_e2000(sample, expected) <= 5.0
        old = rgb_tuple(OLD_SIDEBAR_BEIGE)
        assert rgb_distance(sample, expected) < rgb_distance(sample, old)
    finally:
        window.close()


def test_sidebar_panel_is_not_old_beige(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        sidebar = window.findChild(QFrame, "SidebarPanel")
        canvas = window.centralWidget()
        assert sidebar is not None
        image = canvas.grab().toImage()
        origin = sidebar.mapTo(canvas, QPoint(0, 0))
        inside = _map_px(
            image,
            canvas,
            origin.x() + min(40, sidebar.width() // 3),
            origin.y() + min(40, sidebar.height() // 4),
        )
        old = rgb_tuple(OLD_SIDEBAR_BEIGE)
        canvas_base = rgb_tuple(qcolor("canvas_base"))
        assert rgb_distance(inside, old) > 12, inside
        # Interior should be a glass surface, not the old opaque beige.
        assert rgb_distance(inside, old) > rgb_distance(inside, canvas_base) or rgb_distance(
            inside, old
        ) > 20
    finally:
        window.close()


def test_sidebar_rounded_corner_shows_canvas_not_opaque_panel(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        canvas = window.centralWidget()
        sidebar = window.findChild(QFrame, "SidebarPanel")
        assert isinstance(canvas, CloudCanvas) and sidebar is not None
        assert cloud_porcelain_radii().radius_sidebar == 22
        match = re.search(
            r"QFrame#SidebarPanel \{(?P<body>.*?)\}",
            build_style_sheet(),
            flags=re.DOTALL,
        )
        assert match is not None
        assert "border-radius: 22px" in match.group("body")

        image = canvas.grab().toImage()
        origin = sidebar.mapTo(canvas, QPoint(0, 0))
        # Bounding-box corner sits outside the 22 px quarter-circle.
        corner = _map_px(image, canvas, origin.x() + 1, origin.y() + 1)
        inside = _map_px(
            image,
            canvas,
            origin.x() + min(40, sidebar.width() // 3),
            origin.y() + min(40, sidebar.height() // 4),
        )
        canvas_ref = _map_px(image, canvas, 2, 2)
        dist_canvas = rgb_distance(corner, canvas_ref)
        dist_inside = rgb_distance(corner, inside)
        dist_beige = rgb_distance(corner, rgb_tuple(OLD_SIDEBAR_BEIGE))
        assert dist_canvas < dist_inside, (corner, inside, canvas_ref)
        assert dist_beige > dist_canvas
    finally:
        window.close()


def test_primary_button_fill_uses_accent_action_not_accent(app):
    window = MainWindow()
    gallery = build_cloud_component_gallery()
    try:
        _show(app, window, 1400, 860)
        gallery.show()
        app.processEvents()
        palette = cloud_porcelain_palette()
        expected = rgb_tuple(qcolor(palette.accent_action))
        assert expected == (0xB7, 0x5D, 0x40)
        insufficient = rgb_tuple(INSUFFICIENT_ACCENT)
        assert insufficient == (0xC7, 0x6C, 0x4D)

        for button in (window.findChild(QPushButton, "PrimaryButton"), gallery.btn_primary):
            assert button is not None
            image = button.grab().toImage()
            sample = _map_px(image, button, max(8, button.width() // 2), 6)
            dist_action = rgb_distance(sample, expected)
            dist_accent = rgb_distance(sample, insufficient)
            assert dist_action < dist_accent, (sample, dist_action, dist_accent)
            assert dist_action <= 24 or delta_e2000(sample, expected) <= 5.0
    finally:
        gallery.close()
        window.close()


def test_selected_module_uses_accent_soft_not_green_ready_dot(app):
    window = MainWindow()
    try:
        _show(app, window, 1400, 860)
        module_list = window.module_list
        module_list.setCurrentRow(0)
        app.processEvents()
        item = module_list.item(0)
        rect = module_list.visualItemRect(item)
        image = module_list.grab().toImage()
        fill = _map_px(
            image,
            module_list,
            rect.right() - 20,
            rect.center().y(),
        )
        accent_soft = rgb_tuple(qcolor("accent_soft"))
        green = rgb_tuple(GREEN_READY)
        assert rgb_distance(fill, accent_soft) < rgb_distance(fill, green), fill
        # Right edge must not be a green ready-dot cluster.
        right = _map_px(
            image,
            module_list,
            rect.right() - 6,
            rect.center().y(),
        )
        assert rgb_distance(right, green) > 40

        for widget in window.findChildren(QFrame) + window.findChildren(QLabel):
            name = widget.objectName().lower().replace("_", "-")
            assert "status-dot" not in name
            assert "ready-dot" not in name
    finally:
        window.close()


def test_delta_e2000_identity_and_black_white():
    assert delta_e2000((255, 0, 0), (255, 0, 0)) == 0.0
    assert math.isclose(delta_e2000((0, 0, 0), (0, 0, 0)), 0.0)
    contrast = delta_e2000((255, 255, 255), (0, 0, 0))
    assert contrast > 50.0
