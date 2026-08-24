"""Static CloudCanvas primitive tests. Not a MainWindow migration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMainWindow

from app.ui.design_tokens import cloud_porcelain_palette, qcolor
from app.ui.theme import apply_theme
from app.ui.widgets.cloud_canvas import CloudCanvas


_CANVAS_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "ui"
    / "widgets"
    / "cloud_canvas.py"
)


def _app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_theme(instance)
    return instance


def test_cloud_canvas_object_name_and_no_timer() -> None:
    _app()
    canvas = CloudCanvas()
    assert canvas.objectName() == "CloudCanvas"
    assert canvas.findChildren(QTimer) == []


def test_paint_event_does_not_raise() -> None:
    _app()
    canvas = CloudCanvas()
    canvas.resize(400, 300)
    canvas.show()
    QApplication.processEvents()
    image = canvas.grab().toImage()
    assert image.width() > 0
    assert image.height() > 0
    canvas.close()


def test_corner_pixel_is_canvas_base_not_old_beige() -> None:
    _app()
    palette = cloud_porcelain_palette()
    expected = qcolor(palette.canvas_base)
    old_beige = QColor("#F7F5F2")

    for width, height in ((400, 300), (800, 520)):
        canvas = CloudCanvas()
        canvas.resize(width, height)
        canvas.show()
        QApplication.processEvents()
        image = canvas.grab().toImage()
        sample = image.pixelColor(2, 2)
        assert abs(sample.red() - expected.red()) <= 8
        assert abs(sample.green() - expected.green()) <= 8
        assert abs(sample.blue() - expected.blue()) <= 8
        old_distance = (
            abs(sample.red() - old_beige.red())
            + abs(sample.green() - old_beige.green())
            + abs(sample.blue() - old_beige.blue())
        )
        new_distance = (
            abs(sample.red() - expected.red())
            + abs(sample.green() - expected.green())
            + abs(sample.blue() - expected.blue())
        )
        assert new_distance < old_distance
        canvas.close()


def test_stress_rings_are_not_animated() -> None:
    _app()
    canvas = CloudCanvas()
    assert canvas.findChildren(QTimer) == []
    source = _CANVAS_SOURCE.read_text(encoding="utf-8")
    assert "QTimer" not in source
    assert "startTimer" not in source
    canvas.close()


def test_constructing_cloud_canvas_does_not_import_core_calculators() -> None:
    _app()
    before = {name for name in sys.modules if name.startswith("core")}
    canvas = CloudCanvas()
    canvas.resize(200, 160)
    canvas.show()
    QApplication.instance().processEvents()
    canvas.grab()
    canvas.close()
    after = {name for name in sys.modules if name.startswith("core")}
    assert after == before


def test_cloud_canvas_probe_in_throwaway_main_window() -> None:
    app = _app()
    window = QMainWindow()
    canvas = CloudCanvas()
    window.setCentralWidget(canvas)
    window.resize(480, 320)
    window.show()
    app.processEvents()
    assert window.centralWidget() is canvas
    assert canvas.objectName() == "CloudCanvas"
    assert canvas.findChildren(QTimer) == []
    image = canvas.grab().toImage()
    assert not image.isNull()
    window.close()
