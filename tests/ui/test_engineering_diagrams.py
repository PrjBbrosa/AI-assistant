import inspect
import os
import re
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.theme import apply_theme
from app.ui.widgets.clamping_diagram import ClampingDiagramWidget, ThreadForceTriangleWidget
from app.ui.widgets.hertz_input_diagram import HertzInputDiagramWidget
from app.ui.widgets.press_force_curve import GRID_ALPHA, PressForceCurveWidget
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget

ROOT = Path(__file__).resolve().parents[2]
OLD_BEIGE_HEXES = ("#FBF8F3", "#EEE7DE", "#D97757")

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


def test_hertz_diagram_geometry_survives_paint() -> None:
    _app()
    widget = HertzInputDiagramWidget()
    widget.set_context("line", 50, 0, 20, 10000, 115000)
    before = widget.geometry_context()
    _grab_widget(widget, 920, 420)
    assert widget.geometry_context() == before
    assert before == ("line", 50.0, 0.0, 20.0, 10000.0, 115000.0)

    widget.set_context("point", 25, 50, 0, 10000, 115000)
    before_point = widget.geometry_context()
    _grab_widget(widget, 920, 420)
    assert widget.geometry_context() == before_point
    assert before_point == ("point", 25.0, 50.0, 0.0, 10000.0, 115000.0)


def test_hertz_paint_event_does_not_call_calculators() -> None:
    sources = [
        inspect.getsource(HertzInputDiagramWidget.paintEvent),
        inspect.getsource(HertzInputDiagramWidget._draw_line_contact),
        inspect.getsource(HertzInputDiagramWidget._draw_point_contact),
    ]
    joined = "\n".join(sources)
    assert "calculate_" not in joined
    assert "allowable" not in joined
    assert "safety_factor" not in joined
    assert "overall_pass" not in joined
    assert "overall_status" not in joined


def test_hertz_diagram_source_has_no_old_beige_hex() -> None:
    text = (ROOT / "app" / "ui" / "widgets" / "hertz_input_diagram.py").read_text(encoding="utf-8")
    assert "from app.ui.design_tokens import" in text
    assert "qcolor" in text or "qpen" in text
    for hex_value in OLD_BEIGE_HEXES:
        assert hex_value not in text
    assert re.search(r'QColor\("#', text) is None
    assert re.search(r"QColor\('#", text) is None


def test_hertz_page_sample_keeps_diagram_geometry_and_paint_exception_is_isolated() -> None:
    app = _app()
    page = HertzContactPage()
    app.processEvents()
    page._load_sample("hertz_case_01.json")
    app.processEvents()
    page._calculate()
    app.processEvents()

    diagram = page.diagram_widget
    before_ctx = diagram.geometry_context()
    assert before_ctx[0] == "line"
    assert before_ctx[1] == 30.0
    assert before_ctx[2] == 0.0
    assert before_ctx[3] == 20.0
    assert before_ctx[4] == 12000.0
    _grab_widget(diagram, 920, 420)
    assert diagram.geometry_context() == before_ctx

    before_result = deepcopy(page._last_result)
    assert isinstance(before_result, dict)

    def boom(_self, _event) -> None:
        raise RuntimeError("hertz paint boom")

    with patch.object(HertzInputDiagramWidget, "paintEvent", boom):
        try:
            diagram.repaint()
        except RuntimeError:
            pass
        app.processEvents()

    assert page._last_result == before_result
    assert page._last_result is not None
    assert page._last_result["checks"]["contact_stress_ok"] is True


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


def test_press_force_curve_data_survives_paint() -> None:
    _app()
    xs = [0.0, 10.0, 20.0, 30.0]
    ys = [0.0, 1000.0, 2500.0, 4000.0]
    widget = PressForceCurveWidget()
    widget.set_curve(xs, ys, 8.0, 22.0, 15.0)
    before = widget.curve_data()
    assert before == (xs, ys, 8.0, 22.0, 15.0)
    assert _non_background_ratio(_grab_widget(widget, 760, 300)) > 0.12
    assert widget.curve_data() == before
    assert widget._interp_force(10.0) == 1000.0
    assert widget._interp_force(15.0) == 1750.0


def test_press_force_paint_event_does_not_call_calculators() -> None:
    sources = [
        inspect.getsource(PressForceCurveWidget.paintEvent),
        inspect.getsource(PressForceCurveWidget._interp_force),
        inspect.getsource(PressForceCurveWidget._draw_marker),
    ]
    joined = "\n".join(sources)
    assert "calculate_" not in joined
    assert "allowable" not in joined
    assert "safety_factor" not in joined
    assert "overall_pass" not in joined
    assert 0.45 <= GRID_ALPHA <= 0.65


def test_press_force_curve_source_has_no_old_beige_hex() -> None:
    text = (ROOT / "app" / "ui" / "widgets" / "press_force_curve.py").read_text(encoding="utf-8")
    assert "from app.ui.design_tokens import" in text
    for hex_value in OLD_BEIGE_HEXES:
        assert hex_value not in text
    assert re.search(r'QColor\("#', text) is None
    assert re.search(r"QColor\('#", text) is None


def test_interference_page_curve_reads_result_keys_and_paint_exception_is_isolated() -> None:
    app = _app()
    page = InterferenceFitPage()
    app.processEvents()
    page._load_sample("interference_case_01.json")
    app.processEvents()
    page._calculate()
    app.processEvents()

    result = page._last_result
    assert isinstance(result, dict)
    curve = result["press_force_curve"]
    stored_x, stored_y, dmin, dmax, dreq = page.curve_widget.curve_data()
    assert stored_x == [float(v) for v in curve["interference_um"]]
    assert stored_y == [float(v) for v in curve["force_n"]]
    assert dmin == float(curve["delta_min_um"])
    assert dmax == float(curve["delta_max_um"])
    assert dreq == float(curve["delta_required_um"])

    before_result = deepcopy(result)
    _grab_widget(page.curve_widget, 760, 300)
    assert page.curve_widget.curve_data() == (stored_x, stored_y, dmin, dmax, dreq)
    assert page._last_result == before_result

    def boom(_self, _event) -> None:
        raise RuntimeError("press-force paint boom")

    with patch.object(PressForceCurveWidget, "paintEvent", boom):
        try:
            page.curve_widget.repaint()
        except RuntimeError:
            pass
        app.processEvents()

    assert page._last_result == before_result
    assert page._last_result["press_force_curve"]["interference_um"] == curve["interference_um"]
