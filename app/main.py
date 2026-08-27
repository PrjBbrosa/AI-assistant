#!/usr/bin/env python3
"""Desktop entry point for local engineering assistant."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from app.ui.icons import app_icon_path, load_app_icon
from app.ui.theme import apply_theme


FATIGUE_PACKAGE_SMOKE_ARG = "--fatigue-package-smoke"


def _run_fatigue_package_smoke(app: QApplication) -> int:
    """Exercise the lazy fatigue UI, SciPy calculation, and PDF stack."""
    from app.ui.pages.fatigue_reliability_page import (  # noqa: PLC0415
        FatigueReliabilityPage,
    )
    from app.ui.report_pdf_fatigue import generate_fatigue_report  # noqa: PLC0415

    page = FatigueReliabilityPage()
    try:
        page.mc_samples_edit.setText("1000")
        page.bootstrap_samples_edit.setText("0")
        payload = page._build_payload()
        result = page._calculate_fatigue(payload)
        if result.get("overall_status") not in {"pass", "fail"}:
            return 2
        with tempfile.TemporaryDirectory(prefix="fatigue-package-smoke-") as folder:
            report_path = Path(folder) / "fatigue-smoke.pdf"
            generate_fatigue_report(report_path, payload, result)
            if not report_path.read_bytes().startswith(b"%PDF"):
                return 3
        app.processEvents()
        return 0
    finally:
        page.deleteLater()


def main() -> int:
    package_smoke = FATIGUE_PACKAGE_SMOKE_ARG in sys.argv
    qt_argv = [arg for arg in sys.argv if arg != FATIGUE_PACKAGE_SMOKE_ARG]
    app = QApplication(qt_argv)
    app.setApplicationName("Local Engineering Assistant")
    app.setOrganizationName("Personal")

    if package_smoke:
        return _run_fatigue_package_smoke(app)

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

    # MainWindow and font helpers are deferred until here so the splash appears
    # before heavier UI modules are imported.
    from app.ui.fonts import make_ui_font  # noqa: PLC0415
    from app.ui.main_window import MainWindow  # noqa: PLC0415

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
