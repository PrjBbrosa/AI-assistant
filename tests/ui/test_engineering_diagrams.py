import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from app.ui.theme import apply_theme
from app.ui.widgets.clamping_diagram import ClampingDiagramWidget, ThreadForceTriangleWidget
from app.ui.widgets.hertz_input_diagram import HertzInputDiagramWidget
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget

_THEME_APPLIED_PROPERTY = "_ai_assistant_test_theme_applied_once"


def _app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    if not instance.property(_THEME_APPLIED_PROPERTY) or not instance.styleSheet():
        apply_theme(instance)
        instance.setProperty(_THEME_APPLIED_PROPERTY, True)
    return instance


def _grab_widget(widget, width: int, height: int):
    app = _app()
    widget.resize(width, height)
    widget.show()
    app.processEvents()
    pixmap = widget.grab()
    widget.hide()
    return pixmap


def _non_background_ratio(pixmap, background: QColor = QColor("#F7F5F2")) -> float:
    image = pixmap.toImage()
    total = max(1, image.width() * image.height())
    changed = 0
    for x in range(0, image.width(), 4):
        for y in range(0, image.height(), 4):
            color = image.pixelColor(x, y)
            if color != background:
                changed += 16
    return changed / total


def test_clamping_diagram_svg_distinguishes_joint_types_and_renders() -> None:
    _app()
    tapped = ClampingDiagramWidget()
    tapped.set_joint_type("tapped")
    tapped.set_forces(12000, 3500, 8500)
    through = ClampingDiagramWidget()
    through.set_joint_type("through")
    through.set_forces(12000, 3500, 8500)

    tapped_svg = tapped._build_svg()
    through_svg = through._build_svg()

    assert "内螺纹" in tapped_svg
    assert "Nut" not in tapped_svg
    assert "Nut" in through_svg
    assert "load path" in tapped_svg
    assert "load path" in through_svg
    assert _non_background_ratio(_grab_widget(tapped, 980, 400)) > 0.15
    assert _non_background_ratio(_grab_widget(through, 980, 400)) > 0.15


def test_thread_force_triangle_renders_readable_force_components() -> None:
    _app()
    widget = ThreadForceTriangleWidget()
    widget.set_thread_forces(16000, 3.0, 8.5)

    assert _non_background_ratio(_grab_widget(widget, 760, 280)) > 0.12


def test_hertz_diagram_renders_line_and_point_contact_modes() -> None:
    _app()
    line = HertzInputDiagramWidget()
    line.set_context("line", 50, 0, 20, 10000, 115000)
    point = HertzInputDiagramWidget()
    point.set_context("point", 25, 50, 0, 10000, 115000)

    assert _non_background_ratio(_grab_widget(line, 920, 420)) > 0.16
    assert _non_background_ratio(_grab_widget(point, 920, 420)) > 0.16


def test_worm_geometry_layout_uses_vertical_center_distance() -> None:
    _app()
    widget = WormGeometryOverviewWidget()
    widget.resize(920, 360)
    widget.set_geometry_state(
        d1_mm=40,
        d2_mm=160,
        a_mm=100,
        gamma_deg=11.31,
        z1=2,
        z2=40,
        handedness="right",
    )

    layout = widget._compute_geometry_layout(widget._diagram_rect_for_testing())
    center_distance = layout["center_distance"]

    assert abs(center_distance["p0"].x() - center_distance["p1"].x()) < 1.0
    assert center_distance["p1"].y() - center_distance["p0"].y() > 60.0
    assert layout["wheel_rect"].bottom() <= layout["worm_rect"].top() + 12.0
    assert _non_background_ratio(_grab_widget(widget, 920, 360)) > 0.18
