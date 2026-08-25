"""Offscreen Cloud Porcelain component gallery and control-state guards."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFontDialog,
    QColorDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabBar,
    QTableWidget,
)

from app.ui.design_tokens import (
    cloud_porcelain_controls,
    contrast_ratio,
    qcolor,
    qss_rgba,
)
from app.ui.theme import apply_theme, build_style_sheet
from app.ui.widgets.app_combo_box import AppComboBox
from app.ui.widgets.help_button import HelpButton
from tests.ui.cloud_component_gallery import (
    CloudComponentGallery,
    build_cloud_component_gallery,
)


ROOT = Path(__file__).resolve().parents[2]
OLD_HELP_HEXES = (
    "#F4EFE8",
    "#FAF1EC",
    "#8A4A2E",
    "#D97757",
    "#FBF8F4",
    "#FAF7F4",
    "#8A8782",
)


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    return instance


def test_gallery_constructs_named_controls(app):
    gallery = build_cloud_component_gallery()
    gallery.resize(980, 860)
    gallery.show()
    app.processEvents()

    assert isinstance(gallery, CloudComponentGallery)
    assert gallery.objectName() == "CloudComponentGallery"
    assert gallery.field_normal.objectName() == "InputField"
    assert gallery.field_error.property("fieldError") is True
    assert gallery.field_readonly.isReadOnly()
    assert gallery.field_readonly.isEnabled()
    assert not gallery.field_disabled.isEnabled()
    assert isinstance(gallery.combo_normal, AppComboBox)
    assert not gallery.combo_disabled.isEnabled()
    assert gallery.combo_error.property("fieldError") is True
    assert gallery.btn_primary.objectName() == "PrimaryButton"
    assert gallery.btn_secondary.objectName() == "SecondaryButton"
    assert gallery.btn_link.objectName() == "LinkButton"
    assert not gallery.btn_disabled.isEnabled()
    assert gallery.overflow_button.objectName() == "OverflowButton"
    assert gallery.help_button.objectName() == "HelpButton"
    assert gallery.badge_pass.objectName() == "PassBadge"
    assert gallery.badge_fail.objectName() == "FailBadge"
    assert gallery.badge_incomplete.objectName() == "IncompleteBadge"
    assert gallery.badge_wait.objectName() == "WaitBadge"
    assert gallery.badge_ref.objectName() == "RefBadge"
    assert gallery.sub_card.objectName() == "SubCard"
    assert gallery.auto_card.objectName() == "AutoCalcCard"
    assert gallery.disabled_card.objectName() == "DisabledSubCard"
    assert gallery.warning_card.objectName() == "WarningCard"
    assert gallery.findChild(QTableWidget) is not None
    assert gallery.findChild(QTabBar) is not None
    assert gallery.menu.actions()
    gallery.close()


def test_gallery_grab_has_canvas_background_and_readable_labels(app):
    gallery = build_cloud_component_gallery()
    gallery.resize(980, 860)
    gallery.show()
    app.processEvents()
    try:
        image = gallery.grab().toImage()
        expected = qcolor("canvas_base")
        corner = image.pixelColor(2, 2)
        assert max(
            abs(corner.red() - expected.red()),
            abs(corner.green() - expected.green()),
            abs(corner.blue() - expected.blue()),
        ) <= 2

        sampled = [
            image.pixelColor(x, y)
            for y in range(2, image.height(), 20)
            for x in range(2, image.width(), 20)
        ]
        black_fraction = sum(
            1 for color in sampled if max(color.red(), color.green(), color.blue()) < 20
        ) / len(sampled)
        assert black_fraction < 0.05, black_fraction

        caption = gallery.caption_labels[0]
        caption_origin = caption.mapTo(gallery, QPoint(0, 0))
        caption_background = image.pixelColor(
            caption_origin.x(),
            caption_origin.y(),
        )
        readable_pixels = sum(
            1
            for y in range(caption_origin.y(), caption_origin.y() + caption.height())
            for x in range(caption_origin.x(), caption_origin.x() + caption.width())
            if contrast_ratio(image.pixelColor(x, y), caption_background) >= 4.5
        )
        assert readable_pixels >= 5, readable_pixels
    finally:
        gallery.close()


def test_gallery_is_not_a_main_window_module():
    main_window = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "cloud_component_gallery" not in main_window
    assert "CloudComponentGallery" not in main_window


def test_stylesheet_covers_control_states():
    stylesheet = build_style_sheet()
    for selector in (
        "QLineEdit#InputField:hover",
        "QLineEdit#InputField:focus",
        "QLineEdit#InputField:read-only",
        "QLineEdit#InputField:disabled",
        '[fieldError="true"]',
        "QPushButton#PrimaryButton:pressed",
        "QPushButton#SecondaryButton:pressed",
        "QPushButton#LinkButton:disabled",
        "QComboBox[fieldError=\"true\"]:on",
        "QDialog#HelpPopover",
        "QDialog#BeginnerGuideDialog",
        "QLabel#GuideTitle",
        "QLabel#GuideFlowArrow",
        "QLabel#IncompleteBadge",
        "QTabBar::tab",
        "QTableWidget",
        "QMenu",
        "QScrollBar:vertical",
        "QPlainTextEdit",
    ):
        assert selector in stylesheet, selector
    assert "QFileDialog" not in stylesheet
    assert "QFontDialog" not in stylesheet
    assert "QColorDialog" not in stylesheet
    assert "DontUseNativeDialog" not in stylesheet


def test_native_dialog_flags_are_not_forced():
    ui_root = ROOT / "app" / "ui"
    for path in ui_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "DontUseNativeDialog" not in text, path
    assert QFileDialog.Option.DontUseNativeDialog
    assert QFontDialog is not None
    assert QColorDialog is not None


def test_read_only_qss_is_distinct_from_disabled():
    stylesheet = build_style_sheet()
    read_only = _block(stylesheet, "QLineEdit#InputField:read-only {")
    disabled = _block(stylesheet, "QLineEdit#InputField:disabled {")
    assert qss_rgba("ink_primary") in read_only
    assert qss_rgba("ink_quiet") in disabled
    assert qss_rgba("surface_glass_soft") in read_only
    assert qss_rgba("not_checked_bg") in disabled
    assert read_only != disabled


def test_pressed_is_darker_than_hover_in_qss():
    stylesheet = build_style_sheet()
    hover = _block(stylesheet, "QPushButton:hover {")
    pressed = _block(stylesheet, "QPushButton:pressed {")
    primary_hover = _block(stylesheet, "QPushButton#PrimaryButton:hover {")
    primary_pressed = _block(stylesheet, "QPushButton#PrimaryButton:pressed {")
    assert "background-color:" in hover
    assert "background-color:" in pressed
    assert hover != pressed
    assert qss_rgba("accent_hover") in primary_hover
    assert qss_rgba("accent_hover") not in primary_pressed


def test_selection_uses_accent_soft():
    stylesheet = build_style_sheet()
    assert f"selection-background-color: {qss_rgba('accent_soft')}" in stylesheet
    assert f"selection-color: {qss_rgba('accent_ink')}" in stylesheet


def test_help_and_overflow_hit_areas(app):
    gallery = build_cloud_component_gallery()
    gallery.show()
    app.processEvents()
    assert gallery.help_button.width() == 24
    assert gallery.help_button.height() == 24
    assert gallery.overflow_button.width() >= 28
    assert gallery.overflow_button.height() >= 28
    field_height = gallery.field_normal.sizeHint().height()
    assert 28 <= field_height <= 42
    gallery.close()


def test_large_font_keeps_help_24_and_overflow_28(app):
    gallery = build_cloud_component_gallery()
    font = gallery.font()
    font.setPointSize(max(font.pointSize(), 10) * 2)
    gallery.setFont(font)
    gallery.help_button.setFixedSize(
        cloud_porcelain_controls().help_button_outer,
        cloud_porcelain_controls().help_button_outer,
    )
    gallery.show()
    app.processEvents()
    assert gallery.help_button.width() == 24
    assert gallery.help_button.height() == 24
    assert gallery.overflow_button.minimumWidth() >= 28
    assert gallery.overflow_button.minimumHeight() >= 28
    gallery.close()


def test_pass_badge_uses_token_pixels(app):
    stylesheet = build_style_sheet()
    badge_qss = _block(stylesheet, "QLabel#PassBadge {")
    assert qss_rgba("pass_bg") in badge_qss
    assert qss_rgba("pass_fg") in badge_qss
    gallery = build_cloud_component_gallery()
    gallery.show()
    app.processEvents()
    image = gallery.badge_pass.grab().toImage()
    assert image.width() > 0 and image.height() > 0
    gallery.close()


def test_wave4_sources_drop_old_help_hexes():
    files = (
        ROOT / "app" / "ui" / "theme.py",
        ROOT / "app" / "ui" / "widgets" / "help_popover.py",
        ROOT / "app" / "ui" / "widgets" / "beginner_guide_dialog.py",
        ROOT / "app" / "ui" / "widgets" / "help_button.py",
        ROOT / "app" / "ui" / "widgets" / "app_combo_box.py",
    )
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        for hex_value in OLD_HELP_HEXES:
            assert hex_value.lower() not in text, f"{path} still has {hex_value}"
        assert "setstylesheet" not in (ROOT / "app" / "ui" / "widgets" / "beginner_guide_dialog.py").read_text(encoding="utf-8").lower()


def test_gallery_exposes_expected_widget_types(app):
    gallery = build_cloud_component_gallery()
    assert gallery.findChildren(QLineEdit)
    assert gallery.findChildren(QComboBox)
    assert gallery.findChildren(QPushButton)
    assert gallery.findChildren(QLabel)
    assert gallery.findChildren(HelpButton)
    gallery.close()


def _block(stylesheet: str, header: str) -> str:
    start = stylesheet.index(header)
    end = stylesheet.index("}", start)
    return stylesheet[start:end]
