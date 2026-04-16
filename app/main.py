#!/usr/bin/env python3
"""Desktop entry point for local engineering assistant."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

from app.ui.fonts import make_ui_font
from app.ui.icons import load_app_icon
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Local Engineering Assistant")
    app.setOrganizationName("Personal")

    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setFont(make_ui_font(10))
    apply_theme(app)

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

