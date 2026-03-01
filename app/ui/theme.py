"""Claude-inspired warm neutral theme for PySide6."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    """Apply app-wide style sheet."""
    app.setStyleSheet(
        """
        QWidget {
            background-color: #F7F5F2;
            color: #1F1D1A;
            font-family: "Avenir Next", "SF Pro Text", "Segoe UI", sans-serif;
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
            padding: 5px 10px;
            font-weight: 700;
        }
        QLabel#FailBadge {
            background-color: #F5D5CD;
            color: #7F2D1A;
            border: 1px solid #E5A89A;
            border-radius: 10px;
            padding: 5px 10px;
            font-weight: 700;
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
    )
