"""Cloud Porcelain application stylesheet for PySide6."""

from __future__ import annotations

import re

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from app.ui.design_tokens import (
    CloudPorcelainPalette,
    cloud_porcelain_controls,
    cloud_porcelain_palette,
    cloud_porcelain_radii,
    qcolor,
    qss_rgba,
)
from app.ui.fonts import UI_FONT_FAMILIES, UI_FONT_FAMILY_CSS


INPUT_FIELD_SURFACE_ROLE = "inputField"
INPUT_FIELD_LABEL_WRAP_OBJECT_NAME = "InputFieldLabelWrap"

_PLACEHOLDER_RE = re.compile(r"\$\{(\w+)\}")


def mark_input_field_surface(frame: QFrame) -> None:
    """Mark a frame as an input field row for theme-level surface styling."""
    frame.setProperty("surfaceRole", INPUT_FIELD_SURFACE_ROLE)
    frame.style().unpolish(frame)
    frame.style().polish(frame)


def mark_input_field_label_wrap(widget: QWidget) -> None:
    """Mark a label/help wrapper inside an input field row as transparent."""
    widget.setObjectName(INPUT_FIELD_LABEL_WRAP_OBJECT_NAME)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _darken_qss(token_or_spec: str, factor: int = 125) -> str:
    """Return a QSS color darker than hover; used for pressed states."""
    return qss_rgba(qcolor(token_or_spec).darker(factor))


def _interpolate(template: str, values: dict[str, str | int]) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(f"missing stylesheet token: {key}")
        return str(values[key])

    return _PLACEHOLDER_RE.sub(_replace, template)


def build_style_sheet(palette: CloudPorcelainPalette | None = None) -> str:
    """Build the application QSS from Cloud Porcelain tokens. No QApplication."""
    pal = palette or cloud_porcelain_palette()
    radii = cloud_porcelain_radii()
    controls = cloud_porcelain_controls()
    white = QColor(255, 255, 255)

    values: dict[str, str | int] = {
        "font_family": UI_FONT_FAMILY_CSS,
        "canvas_outer": qss_rgba(pal.canvas_outer),
        "canvas_base": qss_rgba(pal.canvas_base),
        "surface_glass": qss_rgba(pal.surface_glass),
        "surface_glass_strong": qss_rgba(pal.surface_glass_strong),
        "surface_glass_soft": qss_rgba(pal.surface_glass_soft),
        "surface_field": qss_rgba(pal.surface_field),
        "ink_primary": qss_rgba(pal.ink_primary),
        "ink_muted": qss_rgba(pal.ink_muted),
        "ink_quiet": qss_rgba(pal.ink_quiet),
        "line_highlight": qss_rgba(pal.line_highlight),
        "line_structural": qss_rgba(pal.line_structural),
        "accent": qss_rgba(pal.accent),
        "accent_action": qss_rgba(pal.accent_action),
        "accent_hover": qss_rgba(pal.accent_hover),
        "accent_pressed": _darken_qss(pal.accent_hover, 125),
        "accent_soft": qss_rgba(pal.accent_soft),
        "accent_ink": qss_rgba(pal.accent_ink),
        "secondary": qss_rgba(pal.secondary),
        "secondary_soft": qss_rgba(pal.secondary_soft),
        "focus_ring": qss_rgba(pal.focus_ring),
        "surface_pressed": _darken_qss(pal.surface_glass_strong, 118),
        "pass_fg": qss_rgba(pal.pass_fg),
        "pass_bg": qss_rgba(pal.pass_bg),
        "fail_fg": qss_rgba(pal.fail_fg),
        "fail_bg": qss_rgba(pal.fail_bg),
        "incomplete_fg": qss_rgba(pal.incomplete_fg),
        "incomplete_bg": qss_rgba(pal.incomplete_bg),
        "not_checked_fg": qss_rgba(pal.not_checked_fg),
        "not_checked_bg": qss_rgba(pal.not_checked_bg),
        "reference_only_fg": qss_rgba(pal.reference_only_fg),
        "reference_only_bg": qss_rgba(pal.reference_only_bg),
        "warning_fg": qss_rgba(pal.warning_fg),
        "warning_bg": qss_rgba(pal.warning_bg),
        "input_error_fg": qss_rgba(pal.input_error_fg),
        "input_error_bg": qss_rgba(pal.input_error_bg),
        "white": qss_rgba(white),
        "radius_sidebar": radii.radius_sidebar,
        "radius_primary": radii.radius_primary,
        "radius_panel": radii.radius_panel,
        "radius_control": radii.radius_control,
        "radius_badge": radii.radius_badge,
        "radius_small": radii.radius_small,
        "help_button_inner": controls.help_button_inner,
        "header_min_height": controls.header_min_height,
        "button_height": controls.button_height,
        "primary_button_height": controls.primary_button_height,
        "icon_hit_min": controls.icon_hit_min,
    }

    return _interpolate(_STYLE_TEMPLATE, values)


def apply_theme(app: QApplication) -> None:
    """Apply app-wide style sheet."""
    app_font = app.font()
    if app_font.families() != UI_FONT_FAMILIES:
        app_font.setFamilies(UI_FONT_FAMILIES)
        app.setFont(app_font)
    resolved_style_sheet = build_style_sheet(cloud_porcelain_palette())
    # Re-applying an identical application stylesheet makes Qt unpolish and
    # polish every existing widget.  Besides being unnecessary in production,
    # that turns late UI tests into multi-second operations as their widget
    # population grows.  Keep the operation idempotent while still allowing a
    # genuinely changed theme to be applied.
    if app.styleSheet() == resolved_style_sheet:
        return
    app.setStyleSheet(resolved_style_sheet)


_STYLE_TEMPLATE = """
        QWidget {
            background-color: transparent;
            color: ${ink_primary};
            font-family: ${font_family};
            font-size: 10pt;
        }
        QMainWindow {
            background-color: ${canvas_base};
        }
        QWidget#CloudCanvas, QFrame#CloudCanvas {
            background-color: ${canvas_base};
            border: none;
        }
        QFrame#SidebarPanel {
            background-color: ${surface_glass};
            border: 1px solid ${line_structural};
            border-top-color: ${line_highlight};
            border-radius: ${radius_sidebar}px;
        }
        QWidget#BrandRow {
            background: transparent;
        }
        QLabel#BrandTile {
            border-radius: 12px;
            background-color: ${accent};
            border: none;
            padding: 0px;
        }
        QLabel#BrandTitle {
            font-size: 13px;
            font-weight: 700;
            color: ${ink_primary};
            background: transparent;
        }
        QLabel#BrandSubtitle {
            color: ${ink_muted};
            font-size: 10px;
            background: transparent;
        }
        QLabel#NavLabel {
            color: ${ink_quiet};
            font-size: 9px;
            font-weight: 700;
            background: transparent;
            padding: 2px 2px 0px 2px;
        }
        QFrame#SidebarInfoCard {
            background-color: ${surface_glass_soft};
            border: 1px solid ${line_structural};
            border-radius: ${radius_panel}px;
        }
        QLabel#SidebarInfoTitle {
            font-size: 11px;
            font-weight: 700;
            color: ${ink_primary};
            background: transparent;
        }
        QLabel#SidebarInfoBody {
            font-size: 10px;
            color: ${ink_muted};
            background: transparent;
        }
        QWidget#WorkspaceColumn {
            background: transparent;
        }
        QFrame#WorkspaceChrome {
            background: transparent;
            min-height: 36px;
            max-height: 40px;
        }
        QLabel#WorkspaceBreadcrumb {
            color: ${ink_muted};
            font-size: 11px;
            background: transparent;
        }
        QLabel#WorkspaceRunState {
            color: ${ink_muted};
            font-size: 10px;
            background-color: ${surface_glass_soft};
            border: 1px solid ${line_structural};
            border-radius: ${radius_badge}px;
            padding: 4px 10px;
        }
        QListWidget#ModuleList {
            border: none;
            background: transparent;
            outline: 0;
            padding: 4px 0px;
        }
        QListWidget#ModuleList::item {
            border: none;
            border-radius: ${radius_control}px;
            padding: 0px;
            margin-bottom: 3px;
            min-height: 40px;
            background: transparent;
        }
        QListWidget#ModuleList::item:hover {
            background: transparent;
        }
        QListWidget#ModuleList::item:selected {
            background: transparent;
            color: ${accent_ink};
        }
        QListWidget#ChapterList {
            border: none;
            background: transparent;
            outline: 0;
            padding: 4px 0px;
        }
        QListWidget#ChapterList::item {
            border: none;
            border-radius: ${radius_control}px;
            padding: 0px;
            margin-bottom: 3px;
            min-height: 36px;
            background: transparent;
        }
        QListWidget#ChapterList::item:hover {
            background: transparent;
        }
        QListWidget#ChapterList::item:selected {
            background: transparent;
            color: ${accent_ink};
        }
        QFrame#ChapterHeader {
            background-color: ${surface_glass_strong};
            border: 1px solid ${line_structural};
            border-top-color: ${line_highlight};
            border-radius: ${radius_primary}px;
            min-height: ${header_min_height}px;
        }
        QWidget#ChapterActions {
            background: transparent;
        }
        QLabel#ChapterTitle {
            font-size: 15pt;
            font-weight: 600;
            color: ${ink_primary};
            background: transparent;
        }
        QPushButton#OverflowButton {
            min-height: ${button_height}px;
            min-width: ${icon_hit_min}px;
        }
        QFrame#Card {
            background-color: ${surface_glass_strong};
            border: 1px solid ${line_structural};
            border-radius: ${radius_panel}px;
        }
        QFrame#SubCard {
            background-color: ${surface_glass};
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
        }
        QFrame#WarningCard {
            background-color: ${warning_bg};
            border: 1px solid ${warning_fg};
            border-left: 4px solid ${warning_fg};
            border-radius: ${radius_control}px;
        }
        QFrame#DisabledSubCard {
            background-color: ${not_checked_bg};
            border: 1px dashed ${line_structural};
            border-radius: ${radius_control}px;
        }
        QFrame#DisabledSubCard QLabel#SubSectionTitle {
            color: ${ink_quiet};
        }
        QFrame#DisabledSubCard QLineEdit#InputField {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border: 1px solid ${line_structural};
        }
        QFrame#DisabledSubCard QLabel#UnitLabel {
            color: ${ink_quiet};
        }
        QFrame#DisabledSubCard QLabel#SectionHint {
            color: ${ink_quiet};
        }
        QFrame#SubCard[selected="true"] {
            border: 2px solid ${accent};
            background-color: ${accent_soft};
        }
        QFrame#AutoCalcCard {
            background-color: ${secondary_soft};
            border: 1px solid ${secondary};
            border-radius: ${radius_control}px;
        }
        QFrame#AutoCalcCard QLabel#SubSectionTitle {
            color: ${ink_primary};
        }
        QFrame#AutoCalcCard QLineEdit#InputField {
            background-color: ${secondary_soft};
            color: ${ink_primary};
            border: 1px solid ${secondary};
        }
        QFrame#AutoCalcCard QLabel#UnitLabel {
            color: ${secondary};
        }
        QFrame#AutoCalcCard QLabel#SectionHint {
            color: ${secondary};
        }
        QFrame#AutoCalcCard QComboBox {
            background-color: ${secondary_soft};
            color: ${ink_primary};
            border: 1px solid ${secondary};
        }
        QFrame#SubCard[surfaceRole="inputField"],
        QFrame#AutoCalcCard[surfaceRole="inputField"],
        QFrame#DisabledSubCard[surfaceRole="inputField"] {
            background-color: transparent;
            border: none;
            border-radius: 0px;
        }
        QFrame#SubCard[surfaceRole="inputField"] QWidget#InputFieldLabelWrap,
        QFrame#AutoCalcCard[surfaceRole="inputField"] QWidget#InputFieldLabelWrap,
        QFrame#DisabledSubCard[surfaceRole="inputField"] QWidget#InputFieldLabelWrap {
            background-color: transparent;
        }
        QFrame#ProcessNode {
            background-color: ${surface_glass};
            border: 1px solid ${line_structural};
            border-left: 3px solid ${secondary};
            border-radius: ${radius_small}px;
        }
        QFrame#ProcessNode[selected="true"] {
            border: 2px solid ${secondary};
            border-left: 3px solid ${secondary};
            background-color: ${secondary_soft};
        }
        QFrame#CheckNode {
            background-color: ${surface_glass_strong};
            border: 1px solid ${line_structural};
            border-left: 3px solid ${accent};
            border-radius: ${radius_small}px;
        }
        QFrame#CheckNode[selected="true"] {
            border: 2px solid ${accent};
            border-left: 3px solid ${accent_hover};
            background-color: ${accent_soft};
        }
        QFrame#VerdictNode {
            background-color: ${surface_glass};
            border: 2px dashed ${line_structural};
            border-radius: ${radius_small}px;
        }
        QLabel#FlowSectionLabel {
            color: ${ink_quiet};
            font-size: 11px;
            font-weight: 700;
            padding: 4px 0 2px 0;
        }
        QLabel#FlowArrow {
            color: ${ink_quiet};
            font-size: 13px;
        }
        QLabel#FlowArrowPass {
            color: ${pass_fg};
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#FlowArrowFail {
            color: ${fail_fg};
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#SectionTitle {
            font-size: 16px;
            font-weight: 700;
            color: ${ink_primary};
            background: transparent;
        }
        QLabel#GuideTitle {
            font-size: 16pt;
            font-weight: 600;
            color: ${ink_primary};
            background: transparent;
        }
        QLabel#GuideFlowArrow {
            color: ${accent};
            font-size: 18px;
            font-weight: 700;
            background: transparent;
        }
        QLabel#GuideSectionTitle {
            font-size: 14px;
            font-weight: 700;
            color: ${ink_primary};
            background: transparent;
        }
        QLabel#SubSectionTitle {
            font-size: 13px;
            font-weight: 700;
            color: ${ink_primary};
            background: transparent;
        }
        QLabel#SectionHint {
            color: ${ink_muted};
            font-size: 12px;
            background: transparent;
        }
        QLabel#WarningTitle {
            color: ${warning_fg};
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#WarningBody {
            color: ${ink_muted};
            font-size: 12px;
        }
        QLabel#UnitLabel {
            color: ${ink_muted};
            font-size: 12px;
        }
        QLineEdit#InputField {
            /* 6+22+6 padding plus 1px borders = 36px input_height token.
               Do not set min-height to the full token or padding doubles it. */
            background-color: ${surface_field};
            border: 1px solid ${line_structural};
            border-radius: ${radius_small}px;
            padding: 6px 10px;
            min-height: 22px;
            selection-background-color: ${accent_soft};
            selection-color: ${accent_ink};
        }
        QLineEdit#InputField:hover {
            border: 1px solid ${secondary};
        }
        QLineEdit#InputField:focus {
            /* WHY: Qt Style Sheets do not implement CSS box-shadow. A 4px
               focus_ring border is the 3px outer ring plus the inner 1px
               accent edge (focus_ring is accent at 18% alpha, so the inner
               pixels read as a tinted accent line against the field fill).
               Padding shrinks by 3px so outer geometry does not jump versus
               the 1px rest border. Do not replace this with a 1px accent-only
               border-color change. */
            border: 4px solid ${focus_ring};
            padding: 3px 7px;
        }
        QLineEdit#InputField[fieldError="true"] {
            border: 1px solid ${input_error_fg};
            background-color: ${input_error_bg};
        }
        QLineEdit#InputField[fieldError="true"]:hover {
            border: 1px solid ${input_error_fg};
            background-color: ${input_error_bg};
        }
        QLineEdit#InputField[fieldError="true"]:focus {
            border: 4px solid ${input_error_fg};
            padding: 3px 7px;
            background-color: ${input_error_bg};
        }
        QLineEdit#InputField:read-only {
            background-color: ${surface_glass_soft};
            color: ${ink_primary};
            border-color: ${line_structural};
        }
        QLineEdit#InputField:read-only:hover {
            border: 1px solid ${line_structural};
            background-color: ${surface_glass_soft};
            color: ${ink_primary};
        }
        QLineEdit#InputField:read-only:focus {
            border: 4px solid ${focus_ring};
            padding: 3px 7px;
            background-color: ${surface_glass_soft};
            color: ${ink_primary};
        }
        QLineEdit#InputField:disabled {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border-color: ${line_structural};
        }
        QLabel#FieldErrorLabel {
            color: ${input_error_fg};
            font-size: 12px;
            background: transparent;
        }
        QComboBox {
            background-color: ${surface_field};
            border: 1px solid ${line_structural};
            border-radius: ${radius_small}px;
            padding: 6px 10px;
            min-height: 22px;
        }
        QComboBox:hover {
            border: 1px solid ${secondary};
        }
        QComboBox:focus, QComboBox:on {
            /* Same Qt-capable focus ring as InputField; see comment there. */
            border: 4px solid ${focus_ring};
            padding: 3px 7px;
        }
        QComboBox[fieldError="true"] {
            border: 1px solid ${input_error_fg};
            background-color: ${input_error_bg};
        }
        QComboBox[fieldError="true"]:focus, QComboBox[fieldError="true"]:on {
            border: 4px solid ${input_error_fg};
            padding: 3px 7px;
            background-color: ${input_error_bg};
        }
        QComboBox:disabled {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border-color: ${line_structural};
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: center right;
            width: 22px;
            border: none;
            background: transparent;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid ${ink_muted};
            margin-right: 8px;
            width: 0;
            height: 0;
        }
        QComboBox::down-arrow:hover {
            border-top-color: ${accent};
        }
        QComboBox::down-arrow:disabled {
            border-top-color: ${ink_quiet};
        }
        QComboBox QAbstractItemView {
            background-color: ${surface_glass_strong};
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
            padding: 4px;
            outline: 0;
            selection-background-color: ${accent_soft};
            selection-color: ${accent_ink};
        }
        QComboBox QAbstractItemView::item {
            min-height: 26px;
            padding: 4px 10px;
            border-radius: 6px;
            color: ${ink_primary};
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: ${surface_glass_soft};
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: ${accent_soft};
            color: ${accent_ink};
        }
        QPlainTextEdit, QTextEdit {
            background-color: ${surface_field};
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
            padding: 8px;
            selection-background-color: ${accent_soft};
            selection-color: ${accent_ink};
        }
        QPlainTextEdit:focus, QTextEdit:focus {
            border: 4px solid ${focus_ring};
            padding: 5px;
        }
        QPlainTextEdit:disabled, QTextEdit:disabled {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border-color: ${line_structural};
        }
        QPushButton {
            background-color: ${surface_glass_strong};
            color: ${ink_primary};
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
            padding: 8px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: ${surface_glass};
            border-color: ${secondary};
        }
        QPushButton:pressed {
            background-color: ${surface_pressed};
            border-color: ${secondary};
        }
        QPushButton:focus {
            border-color: ${accent};
        }
        QPushButton:disabled {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border: 1px solid ${line_structural};
        }
        QPushButton#SecondaryButton {
            background-color: ${surface_glass_strong};
            color: ${ink_primary};
            border: 1px solid ${line_structural};
        }
        QPushButton#SecondaryButton:hover {
            background-color: ${surface_glass};
            border-color: ${secondary};
        }
        QPushButton#SecondaryButton:pressed {
            background-color: ${surface_pressed};
            border-color: ${secondary};
        }
        QPushButton#SecondaryButton:disabled {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border: 1px solid ${line_structural};
        }
        QPushButton#LinkButton {
            background: transparent;
            border: none;
            color: ${accent};
        }
        QPushButton#LinkButton:hover {
            background: transparent;
            border: none;
            color: ${accent_hover};
            text-decoration: underline;
        }
        QPushButton#LinkButton:pressed {
            background: transparent;
            border: none;
            color: ${accent_pressed};
        }
        QPushButton#LinkButton:disabled {
            background: transparent;
            color: ${ink_quiet};
            border: 1px solid ${line_structural};
        }
        QPushButton#PrimaryButton {
            background-color: ${accent_action};
            color: ${white};
            border: 1px solid ${accent_action};
        }
        QPushButton#PrimaryButton:hover {
            background-color: ${accent_hover};
            border-color: ${accent_hover};
        }
        QPushButton#PrimaryButton:pressed {
            background-color: ${accent_pressed};
            border-color: ${accent_pressed};
        }
        QPushButton#PrimaryButton:focus {
            border-color: ${accent_hover};
        }
        QPushButton#PrimaryButton:disabled {
            background-color: ${not_checked_bg};
            color: ${ink_quiet};
            border: 1px solid ${line_structural};
        }

        /* ===== Scrollbars ===== */
        QScrollBar:vertical {
            background: transparent;
            width: 12px;
            margin: 0;
            border: none;
        }
        QScrollBar::handle:vertical {
            background: ${line_structural};
            border-radius: 4px;
            min-height: 28px;
            margin: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: ${secondary};
        }
        QScrollBar::handle:vertical:pressed {
            background: ${ink_muted};
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 12px;
            margin: 0;
            border: none;
        }
        QScrollBar::handle:horizontal {
            background: ${line_structural};
            border-radius: 4px;
            min-width: 28px;
            margin: 2px;
        }
        QScrollBar::handle:horizontal:hover {
            background: ${secondary};
        }
        QScrollBar::handle:horizontal:pressed {
            background: ${ink_muted};
        }
        QScrollBar::add-line, QScrollBar::sub-line {
            width: 0;
            height: 0;
            background: transparent;
            border: none;
        }
        QScrollBar::add-page, QScrollBar::sub-page {
            background: transparent;
        }

        /* ===== CheckBox / RadioButton ===== */
        QCheckBox {
            spacing: 8px;
            background: transparent;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid ${line_structural};
            border-radius: 4px;
            background: ${surface_field};
        }
        QCheckBox::indicator:hover {
            border-color: ${accent};
        }
        QCheckBox::indicator:checked {
            background: ${accent};
            border-color: ${accent_hover};
            image: none;
        }
        QCheckBox::indicator:disabled {
            background: ${not_checked_bg};
            border-color: ${line_structural};
        }
        QRadioButton {
            spacing: 8px;
            background: transparent;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid ${line_structural};
            border-radius: 8px;
            background: ${surface_field};
        }
        QRadioButton::indicator:hover {
            border-color: ${accent};
        }
        QRadioButton::indicator:checked {
            background: ${surface_field};
            border: 5px solid ${accent};
        }
        QRadioButton::indicator:disabled {
            background: ${not_checked_bg};
            border-color: ${line_structural};
        }

        /* ===== Menu ===== */
        QMenu {
            background: ${surface_glass_strong};
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 16px;
            border-radius: 6px;
            color: ${ink_primary};
        }
        QMenu::item:selected {
            background: ${accent_soft};
            color: ${accent_ink};
        }
        QMenu::item:disabled {
            color: ${ink_quiet};
        }
        QMenu::separator {
            height: 1px;
            background: ${line_structural};
            margin: 4px 8px;
        }
        QMenuBar {
            background: ${canvas_base};
            border-bottom: 1px solid ${line_structural};
        }
        QMenuBar::item {
            background: transparent;
            padding: 4px 10px;
            border-radius: 6px;
        }
        QMenuBar::item:selected {
            background: ${accent_soft};
        }

        /* ===== Tooltip ===== */
        QToolTip {
            background-color: ${ink_primary};
            color: ${canvas_base};
            border: 1px solid ${ink_primary};
            border-radius: 6px;
            padding: 4px 8px;
        }

        /* ===== MessageBox / Dialog =====
           App dialogs inherit canvas_base. HelpPopover is frameless +
           translucent so its rounded root is the only opaque surface.
           Native OS file/font/color dialogs are not styled here. */
        QMessageBox, QDialog#BeginnerGuideDialog {
            background-color: ${canvas_base};
        }
        QDialog#HelpPopover {
            background-color: transparent;
            border: none;
        }
        QMessageBox QLabel {
            background: transparent;
            color: ${ink_primary};
        }
        QComboBoxPrivateContainer {
            background-color: transparent;
            border: none;
        }

        /* ===== Spin boxes ===== */
        QSpinBox, QDoubleSpinBox {
            background-color: ${surface_field};
            border: 1px solid ${line_structural};
            border-radius: ${radius_small}px;
            padding: 6px 8px;
            min-height: 22px;
            selection-background-color: ${accent_soft};
            selection-color: ${accent_ink};
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border: 4px solid ${focus_ring};
            padding: 3px 5px;
        }
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            background: transparent;
            border: none;
            width: 16px;
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid ${ink_muted};
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid ${ink_muted};
        }

        /* ===== TabBar (for any future tab widgets) ===== */
        QTabWidget::pane {
            background: ${surface_glass};
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
        }
        QTabBar::tab {
            background: ${surface_glass};
            color: ${ink_muted};
            border: 1px solid ${line_structural};
            border-bottom: none;
            border-top-left-radius: ${radius_small}px;
            border-top-right-radius: ${radius_small}px;
            padding: 6px 14px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: ${surface_glass_strong};
            color: ${ink_primary};
        }
        QTabBar::tab:hover:!selected {
            background: ${surface_glass_soft};
        }

        /* ===== Splitter handle ===== */
        QSplitter::handle {
            background: transparent;
        }
        QSplitter::handle:horizontal {
            width: 4px;
        }
        QSplitter::handle:vertical {
            height: 4px;
        }
        QSplitter::handle:hover {
            background: ${line_structural};
        }

        /* ===== GroupBox ===== */
        QGroupBox {
            background: transparent;
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
            margin-top: 14px;
            padding: 12px;
            font-weight: 600;
            color: ${ink_primary};
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            background: transparent;
        }

        /* ===== ListView (generic) ===== */
        QListView {
            background: transparent;
            outline: 0;
            border: 1px solid ${line_structural};
            border-radius: ${radius_control}px;
            padding: 4px;
        }
        QListView::item {
            padding: 6px 8px;
            border-radius: 6px;
        }
        QListView::item:hover {
            background: ${surface_glass_soft};
        }
        QListView::item:selected {
            background: ${accent_soft};
            color: ${accent_ink};
        }
        QTableWidget, QTableView {
            background-color: ${surface_field};
            border: 1px solid ${line_structural};
            border-radius: ${radius_small}px;
            gridline-color: ${line_structural};
            selection-background-color: ${accent_soft};
            selection-color: ${accent_ink};
        }
        QHeaderView::section {
            background-color: ${surface_glass_strong};
            color: ${ink_muted};
            border: none;
            border-right: 1px solid ${line_structural};
            border-bottom: 1px solid ${line_structural};
            padding: 6px 8px;
        }
        QLabel#PassBadge {
            background-color: ${pass_bg};
            color: ${pass_fg};
            border: 1px solid ${pass_fg};
            border-radius: ${radius_badge}px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#FailBadge {
            background-color: ${fail_bg};
            color: ${fail_fg};
            border: 1px solid ${fail_fg};
            border-radius: ${radius_badge}px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#WaitBadge {
            background-color: ${not_checked_bg};
            color: ${not_checked_fg};
            border: 1px solid ${not_checked_fg};
            border-radius: ${radius_badge}px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
        }
        QLabel#RefBadge {
            background-color: ${reference_only_bg};
            color: ${reference_only_fg};
            border: 1px solid ${reference_only_fg};
            border-radius: ${radius_badge}px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        }
        QLabel#IncompleteBadge {
            background-color: ${incomplete_bg};
            color: ${incomplete_fg};
            border: 1px solid ${incomplete_fg};
            border-radius: ${radius_badge}px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        }
        QStatusBar {
            border-top: 1px solid ${line_structural};
            background-color: ${canvas_base};
            color: ${ink_muted};
        }
        QStatusBar::item {
            border: none;
            background: transparent;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QStackedWidget {
            background: transparent;
        }
        QToolButton#HelpButton {
            background: ${not_checked_bg};
            color: ${ink_muted};
            border: 1px solid transparent;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
            /* QSS width excludes the 1px border; outer geometry remains 24px. */
            min-width: ${help_button_inner}px;
            max-width: ${help_button_inner}px;
            min-height: ${help_button_inner}px;
            max-height: ${help_button_inner}px;
            padding: 0;
        }
        QToolButton#HelpButton:hover {
            background: ${accent_soft};
            color: ${accent};
        }
        QToolButton#HelpButton:pressed {
            background: ${accent_action};
            color: ${white};
        }
        QToolButton#HelpButton:focus {
            border: 1px solid ${accent};
        }
        QToolButton#HelpButton:disabled {
            background: ${not_checked_bg};
            color: ${ink_quiet};
        }
        /* ===== HelpPopover ===== */
        QFrame#HelpPopoverRoot {
            background: ${surface_glass_strong};
            border: 1px solid ${line_structural};
            border-radius: ${radius_panel}px;
        }
        QFrame#HelpPopoverHeader {
            background: ${surface_glass};
            border-bottom: 1px solid ${line_structural};
            border-top-left-radius: ${radius_panel}px;
            border-top-right-radius: ${radius_panel}px;
        }
        QFrame#HelpPopoverFooter {
            background: ${surface_glass_soft};
            border-top: 1px solid ${line_structural};
            border-bottom-left-radius: ${radius_panel}px;
            border-bottom-right-radius: ${radius_panel}px;
        }
        QLabel#HelpPopoverCategory {
            color: ${accent_ink};
            background: ${accent_soft};
            padding: 2px 8px;
            border-radius: ${radius_control}px;
            font-size: 11px;
        }
        QLabel#HelpPopoverTitle {
            color: ${ink_primary};
            font-size: 15px;
            font-weight: 600;
        }
        QLabel#HelpPopoverSource {
            color: ${ink_quiet};
            font-size: 11px;
        }
        QLabel#HelpPopoverSourcePrefix {
            color: ${ink_quiet};
            font-size: 11px;
        }
        QToolButton#HelpPopoverIconBtn {
            background: transparent;
            border: none;
            color: ${ink_muted};
            padding: 4px;
            border-radius: 6px;
        }
        QToolButton#HelpPopoverIconBtn:hover {
            background: ${surface_glass_soft};
            color: ${ink_primary};
        }
        QToolButton#HelpPopoverIconBtn:pressed {
            background: ${accent_soft};
        }
        QToolButton#HelpPopoverIconBtn:focus {
            background: ${surface_glass_soft};
        }
        QToolButton#HelpPopoverIconBtn[pinned="true"] {
            background: ${accent_soft};
            color: ${accent};
        }
        QTextBrowser#HelpPopoverBody {
            background: ${surface_glass_strong};
            border: none;
            padding: 4px 6px;
        }
        """
