#!/usr/bin/env python3
"""Desktop entry point for local engineering assistant."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from app.ui.icons import app_icon_path, load_app_icon
from app.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Local Engineering Assistant")
    app.setOrganizationName("Personal")

    # Show splash as early as possible — before any heavy imports.
    splash_pixmap = QPixmap(str(app_icon_path()))
    if not splash_pixmap.isNull():
        splash = QSplashScreen(splash_pixmap)
        splash.show()
        app.processEvents()
    else:
        splash = None

    # Apply theme before the main window, but after splash is visible.
    apply_theme(app)

    # configure_matplotlib_fonts and MainWindow are deferred until here so
    # that matplotlib is not imported before the splash screen appears.
    from app.ui.fonts import configure_matplotlib_fonts, make_ui_font  # noqa: PLC0415
    from app.ui.main_window import MainWindow  # noqa: PLC0415

    configure_matplotlib_fonts()

    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    app.setFont(make_ui_font(10))

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)

    if splash is not None:
        splash.finish(window)

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

