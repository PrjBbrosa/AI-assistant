"""Warm neutral theme for PySide6."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.ui.fonts import UI_FONT_FAMILY_CSS


def apply_theme(app: QApplication) -> None:
    """Apply app-wide style sheet."""
    style_sheet = """
        QWidget {
            background-color: #F7F5F2;
            color: #1F1D1A;
            font-family: __UI_FONT_FAMILY_CSS__;
            font-size: 13px;
        }
        QMainWindow {
            background-color: #F7F5F2;
        }
        QFrame#SidebarPanel {
            background-color: #EEE7DE;
            border-right: 1px solid #D9D3CA;
        }
        QLabel#BrandTitle {
            font-size: 18px;
            font-weight: 700;
            color: #1F1D1A;
            background: transparent;
        }
        QLabel#BrandSubtitle {
            color: #6B665E;
            font-size: 12px;
            background: transparent;
        }
        QLabel#SidebarBrandMark {
            background: transparent;
            padding: 6px 0 4px 0;
        }
        QListWidget#ModuleList {
            border: none;
            background: transparent;
            outline: 0;
            padding: 8px;
        }
        QListWidget#ModuleList::item {
            border: 1px solid transparent;
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 4px;
            background: transparent;
        }
        QListWidget#ModuleList::item:hover {
            background: #F7F1E8;
            border: 1px solid #E3D8C8;
        }
        QListWidget#ModuleList::item:selected {
            background: #EED9CF;
            border: 1px solid #D97757;
            color: #1F1D1A;
            font-weight: 600;
        }
        QListWidget#ChapterList {
            border: none;
            background: transparent;
            outline: 0;
            padding: 6px;
        }
        QListWidget#ChapterList::item {
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 8px 10px;
            margin-bottom: 3px;
        }
        QListWidget#ChapterList::item:hover {
            background: #F7F1E8;
            border: 1px solid #E3D8C8;
        }
        QListWidget#ChapterList::item:selected {
            background: #EED9CF;
            border: 1px solid #D97757;
            font-weight: 600;
        }
        QFrame#Card {
            background-color: #FBF8F3;
            border: 1px solid #D9D3CA;
            border-radius: 12px;
        }
        QFrame#SubCard {
            background-color: #F6F1EA;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
        }
        QFrame#WarningCard {
            background-color: #FFF2DE;
            border: 1px solid #E7C590;
            border-left: 4px solid #D97757;
            border-radius: 10px;
        }
        QFrame#DisabledSubCard {
            background-color: #F0EDE8;
            border: 1px dashed #C5BFB5;
            border-radius: 10px;
        }
        QFrame#DisabledSubCard QLabel#SubSectionTitle {
            color: #9B9590;
        }
        QFrame#DisabledSubCard QLineEdit#InputField {
            background-color: #F0EDE8;
            color: #9B9590;
            border: 1px solid #C5BFB5;
        }
        QFrame#DisabledSubCard QLabel#UnitLabel {
            color: #9B9590;
        }
        QFrame#DisabledSubCard QLabel#SectionHint {
            color: #9B9590;
        }
        QFrame#SubCard[selected="true"] {
            border: 2px solid #D97757;
            background-color: #FBF3EE;
        }
        QFrame#AutoCalcCard {
            background-color: #EDF1F5;
            border: 1px solid #C4CDD6;
            border-radius: 10px;
        }
        QFrame#AutoCalcCard QLabel#SubSectionTitle {
            color: #5A6E82;
        }
        QFrame#AutoCalcCard QLineEdit#InputField {
            background-color: #E5EBF2;
            color: #3A4F63;
            border: 1px solid #C4CDD6;
        }
        QFrame#AutoCalcCard QLabel#UnitLabel {
            color: #6B7D8E;
        }
        QFrame#AutoCalcCard QLabel#SectionHint {
            color: #6B7D8E;
        }
        QFrame#AutoCalcCard QComboBox {
            background-color: #E5EBF2;
            color: #3A4F63;
            border: 1px solid #C4CDD6;
        }
        QFrame#ProcessNode {
            background-color: #EDF1F5;
            border: 1px solid #C4CDD6;
            border-left: 3px solid #7E9AB8;
            border-radius: 8px;
        }
        QFrame#ProcessNode[selected="true"] {
            border: 2px solid #7E9AB8;
            border-left: 3px solid #5A7D9E;
            background-color: #E5EBF2;
        }
        QFrame#CheckNode {
            background-color: #FBF7F2;
            border: 1px solid #D9D3CA;
            border-left: 3px solid #D97757;
            border-radius: 8px;
        }
        QFrame#CheckNode[selected="true"] {
            border: 2px solid #D97757;
            border-left: 3px solid #C56649;
            background-color: #FBF3EE;
        }
        QFrame#VerdictNode {
            background-color: #F6F1EA;
            border: 2px dashed #B8B2A8;
            border-radius: 8px;
        }
        QLabel#FlowSectionLabel {
            color: #8A857D;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 0 2px 0;
        }
        QLabel#FlowArrow {
            color: #B8B2A8;
            font-size: 13px;
        }
        QLabel#FlowArrowPass {
            color: #1E5A2F;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#FlowArrowFail {
            color: #7F2D1A;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#SectionTitle {
            font-size: 16px;
            font-weight: 700;
            color: #1F1D1A;
            background: transparent;
        }
        QLabel#SubSectionTitle {
            font-size: 13px;
            font-weight: 700;
            color: #2E2A25;
            background: transparent;
        }
        QLabel#SectionHint {
            color: #6B665E;
            font-size: 12px;
            background: transparent;
        }
        QLabel#WarningTitle {
            color: #7F2D1A;
            font-size: 13px;
            font-weight: 700;
        }
        QLabel#WarningBody {
            color: #5B5147;
            font-size: 12px;
        }
        QLabel#UnitLabel {
            color: #6B665E;
            font-size: 12px;
        }
        QLineEdit#InputField {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 8px;
            padding: 6px 10px;
            min-height: 22px;
            selection-background-color: #EED9CF;
            selection-color: #1F1D1A;
        }
        QLineEdit#InputField:focus {
            border: 1px solid #D97757;
        }
        QLineEdit#InputField:disabled, QLineEdit#InputField:read-only {
            background-color: #F0EDE8;
            color: #6B665E;
            border-color: #E3D8C8;
        }
        QComboBox {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 8px;
            padding: 6px 10px;
            min-height: 22px;
        }
        QComboBox:hover {
            border: 1px solid #CDBFAA;
        }
        QComboBox:focus, QComboBox:on {
            border: 1px solid #D97757;
        }
        QComboBox:disabled {
            background-color: #F0EDE8;
            color: #9B9590;
            border-color: #E3D8C8;
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
            border-top: 5px solid #8A857D;
            margin-right: 8px;
            width: 0;
            height: 0;
        }
        QComboBox::down-arrow:hover {
            border-top-color: #D97757;
        }
        QComboBox::down-arrow:disabled {
            border-top-color: #C5BFB5;
        }
        QComboBox QAbstractItemView {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 4px;
            outline: 0;
            selection-background-color: #EED9CF;
            selection-color: #1F1D1A;
        }
        QComboBox QAbstractItemView::item {
            min-height: 26px;
            padding: 4px 10px;
            border-radius: 6px;
            color: #1F1D1A;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #F7F1E8;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #EED9CF;
            color: #1F1D1A;
        }
        QPlainTextEdit, QTextEdit {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 8px;
            selection-background-color: #EED9CF;
            selection-color: #1F1D1A;
        }
        QPushButton {
            background-color: #EADFD1;
            color: #1F1D1A;
            border: 1px solid #D7CCBE;
            border-radius: 10px;
            padding: 8px 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #E1D2BF;
            border-color: #CDBFAA;
        }
        QPushButton:pressed {
            background-color: #D7CCBE;
        }
        QPushButton:disabled {
            background-color: #EEE7DE;
            color: #9B9590;
            border-color: #E3D8C8;
        }
        QPushButton#PrimaryButton {
            background-color: #D97757;
            color: #FFF9F5;
            border: 1px solid #C56649;
        }
        QPushButton#PrimaryButton:hover {
            background-color: #C56649;
        }
        QPushButton#PrimaryButton:pressed {
            background-color: #B5583E;
        }
        QPushButton#PrimaryButton:disabled {
            background-color: #E8C9B9;
            color: #FFF2EB;
            border-color: #DAB4A0;
        }

        /* ===== Scrollbars ===== */
        QScrollBar:vertical {
            background: transparent;
            width: 12px;
            margin: 0;
            border: none;
        }
        QScrollBar::handle:vertical {
            background: #D9D3CA;
            border-radius: 4px;
            min-height: 28px;
            margin: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: #CDBFAA;
        }
        QScrollBar::handle:vertical:pressed {
            background: #B8B2A8;
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 12px;
            margin: 0;
            border: none;
        }
        QScrollBar::handle:horizontal {
            background: #D9D3CA;
            border-radius: 4px;
            min-width: 28px;
            margin: 2px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #CDBFAA;
        }
        QScrollBar::handle:horizontal:pressed {
            background: #B8B2A8;
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
            border: 1px solid #D9D3CA;
            border-radius: 4px;
            background: #FCFBF8;
        }
        QCheckBox::indicator:hover {
            border-color: #CDBFAA;
        }
        QCheckBox::indicator:checked {
            background: #D97757;
            border-color: #C56649;
            image: none;
        }
        QCheckBox::indicator:disabled {
            background: #F0EDE8;
            border-color: #E3D8C8;
        }
        QRadioButton {
            spacing: 8px;
            background: transparent;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #D9D3CA;
            border-radius: 8px;
            background: #FCFBF8;
        }
        QRadioButton::indicator:hover {
            border-color: #CDBFAA;
        }
        QRadioButton::indicator:checked {
            background: #FCFBF8;
            border: 5px solid #D97757;
        }
        QRadioButton::indicator:disabled {
            background: #F0EDE8;
            border-color: #E3D8C8;
        }

        /* ===== Menu ===== */
        QMenu {
            background: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 16px;
            border-radius: 6px;
            color: #1F1D1A;
        }
        QMenu::item:selected {
            background: #EED9CF;
            color: #1F1D1A;
        }
        QMenu::item:disabled {
            color: #9B9590;
        }
        QMenu::separator {
            height: 1px;
            background: #E3D8C8;
            margin: 4px 8px;
        }
        QMenuBar {
            background: #EFEAE2;
            border-bottom: 1px solid #D9D3CA;
        }
        QMenuBar::item {
            background: transparent;
            padding: 4px 10px;
            border-radius: 6px;
        }
        QMenuBar::item:selected {
            background: #EED9CF;
        }

        /* ===== Tooltip ===== */
        QToolTip {
            background-color: #2F2A22;
            color: #F7F1E8;
            border: 1px solid #2F2A22;
            border-radius: 6px;
            padding: 4px 8px;
        }

        /* ===== MessageBox / Dialog ===== */
        QMessageBox, QDialog {
            background-color: #F7F5F2;
        }
        QMessageBox QLabel {
            background: transparent;
            color: #1F1D1A;
        }

        /* ===== Spin boxes ===== */
        QSpinBox, QDoubleSpinBox {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 8px;
            padding: 6px 8px;
            min-height: 22px;
            selection-background-color: #EED9CF;
            selection-color: #1F1D1A;
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border: 1px solid #D97757;
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
            border-bottom: 5px solid #8A857D;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            width: 0; height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #8A857D;
        }

        /* ===== TabBar (for any future tab widgets) ===== */
        QTabBar::tab {
            background: #EFEAE2;
            color: #5B5147;
            border: 1px solid #D9D3CA;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 6px 14px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #FBF8F3;
            color: #1F1D1A;
        }
        QTabBar::tab:hover:!selected {
            background: #F7F1E8;
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
            background: #E3D8C8;
        }

        /* ===== GroupBox ===== */
        QGroupBox {
            background: transparent;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            margin-top: 14px;
            padding: 12px;
            font-weight: 600;
            color: #2E2A25;
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
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 4px;
        }
        QListView::item {
            padding: 6px 8px;
            border-radius: 6px;
        }
        QListView::item:hover {
            background: #F7F1E8;
        }
        QListView::item:selected {
            background: #EED9CF;
            color: #1F1D1A;
        }
        QLabel#PassBadge {
            background-color: #DCECD9;
            color: #1E5A2F;
            border: 1px solid #A7C6A0;
            border-radius: 10px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#FailBadge {
            background-color: #F5D5CD;
            color: #7F2D1A;
            border: 1px solid #E5A89A;
            border-radius: 10px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 700;
        }
        QLabel#WaitBadge {
            background-color: #E8E3DA;
            color: #6B665E;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
        }
        QLabel#RefBadge {
            background-color: #E8E3DA;
            color: #6B665E;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        }
        QStatusBar {
            border-top: 1px solid #D9D3CA;
            background-color: #EFEAE2;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QToolButton#HelpButton {
            background: #E3E3DE;
            color: #5F5E5B;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            min-width: 16px;
            max-width: 16px;
            min-height: 16px;
            max-height: 16px;
            padding: 0;
            margin-left: 4px;
        }
        QToolButton#HelpButton:hover {
            background: #EED9CF;
            color: #D97757;
        }
        /* ===== HelpPopover ===== */
        QFrame#HelpPopoverRoot {
            background: #FFFFFF;
            border: 1px solid #F0ECE4;
            border-radius: 14px;
        }
        QFrame#HelpPopoverHeader {
            background: #FFFDFB;
            border-bottom: 1px solid #F0ECE4;
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
        }
        QFrame#HelpPopoverFooter {
            background: #FBF8F4;
            border-top: 1px solid #F0ECE4;
            border-bottom-left-radius: 14px;
            border-bottom-right-radius: 14px;
        }
        QLabel#HelpPopoverCategory {
            color: #D97757;
            background: #FAF1EC;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
        }
        QLabel#HelpPopoverTitle {
            color: #2F2E2C;
            font-size: 15px;
            font-weight: 600;
        }
        QLabel#HelpPopoverSource {
            color: #8A8782;
            font-size: 11px;
        }
        QLabel#HelpPopoverSourcePrefix {
            color: #8A8782;
            font-size: 11px;
        }
        QToolButton#HelpPopoverIconBtn {
            background: transparent;
            border: none;
            color: #8A8782;
            padding: 4px;
            border-radius: 6px;
        }
        QToolButton#HelpPopoverIconBtn:hover {
            background: #F0ECE4;
            color: #2F2E2C;
        }
        QToolButton#HelpPopoverIconBtn[pinned="true"] {
            background: #FAF1EC;
            color: #D97757;
        }
        QTextBrowser#HelpPopoverBody {
            background: #FFFFFF;
            border: none;
            padding: 4px 6px;
        }
        """
    app.setStyleSheet(style_sheet.replace("__UI_FONT_FAMILY_CSS__", UI_FONT_FAMILY_CSS))
