"""Packaged-entry fatigue probe contract."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.main import _run_fatigue_package_smoke


def test_fatigue_package_smoke_exercises_scipy_and_pdf() -> None:
    app = QApplication.instance() or QApplication([])
    assert _run_fatigue_package_smoke(app) == 0
