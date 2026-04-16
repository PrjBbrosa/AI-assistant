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
        }
        QLabel#BrandSubtitle {
            color: #6B665E;
            font-size: 12px;
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
        }
        QLabel#SubSectionTitle {
            font-size: 13px;
            font-weight: 700;
            color: #2E2A25;
        }
        QLabel#SectionHint {
            color: #6B665E;
            font-size: 12px;
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
            padding: 6px 8px;
            selection-background-color: #EED9CF;
            selection-color: #1F1D1A;
        }
        QLineEdit#InputField:focus {
            border: 1px solid #D97757;
        }
        QComboBox {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            border-radius: 8px;
            padding: 6px 8px;
        }
        QComboBox:hover {
            border: 1px solid #CDBFAA;
        }
        QComboBox:focus {
            border: 1px solid #D97757;
        }
        QComboBox QAbstractItemView {
            background-color: #FCFBF8;
            border: 1px solid #D9D3CA;
            selection-background-color: #EED9CF;
            selection-color: #1F1D1A;
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
        QPushButton#PrimaryButton {
            background-color: #D97757;
            color: #FFF9F5;
            border: 1px solid #C56649;
        }
        QPushButton#PrimaryButton:hover {
            background-color: #C56649;
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
        """
    app.setStyleSheet(style_sheet.replace("__UI_FONT_FAMILY_CSS__", UI_FONT_FAMILY_CSS))
