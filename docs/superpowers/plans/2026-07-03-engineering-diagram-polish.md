# Engineering Diagram Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the engineering section diagrams so they match the actual bolt, Hertz contact, and worm-gear calculations while keeping labels readable in offscreen Qt renders.

**Architecture:** Keep computation untouched. Improve only the existing PySide6 drawing widgets: SVG generation remains inside `ClampingDiagramWidget`, while Hertz and worm diagrams remain `QPainter` widgets. Add focused offscreen render/layout tests so diagrams stay nonblank and key dimension logic does not regress.

**Tech Stack:** Python 3.12, PySide6, QPainter, QSvgRenderer, pytest with `QT_QPA_PLATFORM=offscreen`.

---

### Task 1: Render And Layout Regression Tests

**Files:**
- Create: `tests/ui/test_engineering_diagrams.py`
- Modify: none

- [ ] **Step 1: Write failing tests for diagram render contracts**

Create `tests/ui/test_engineering_diagrams.py` with:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from app.ui.theme import apply_theme
from app.ui.widgets.clamping_diagram import ClampingDiagramWidget, ThreadForceTriangleWidget
from app.ui.widgets.hertz_input_diagram import HertzInputDiagramWidget
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget


def _app() -> QApplication:
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    apply_theme(instance)
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
    widget = ThreadForceTriangleWidget()
    widget.set_thread_forces(16000, 3.0, 8.5)

    assert _non_background_ratio(_grab_widget(widget, 760, 280)) > 0.12


def test_hertz_diagram_renders_line_and_point_contact_modes() -> None:
    line = HertzInputDiagramWidget()
    line.set_context("line", 50, 0, 20, 10000, 115000)
    point = HertzInputDiagramWidget()
    point.set_context("point", 25, 50, 0, 10000, 115000)

    assert _non_background_ratio(_grab_widget(line, 920, 420)) > 0.16
    assert _non_background_ratio(_grab_widget(point, 920, 420)) > 0.16


def test_worm_geometry_layout_uses_vertical_center_distance() -> None:
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
```

- [ ] **Step 2: Run tests to verify failures**

Run:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ui/test_engineering_diagrams.py -q
```

Expected: fail because `"load path"` markers and worm layout helper do not exist yet.

### Task 2: Bolt Joint SVG And Thread Force Triangle

**Files:**
- Modify: `app/ui/widgets/clamping_diagram.py`
- Test: `tests/ui/test_engineering_diagrams.py`

- [ ] **Step 1: Rework `ClampingDiagramWidget.paintEvent` layout**

Use a wider central diagram and keep callout boxes out of the SVG body:
- Left zone: compact legend.
- Center zone: sectioned joint SVG.
- Right zone: force stack and numeric force values.
- Use distinct colors for external load `FA`, preload `FM`, residual clamp `FK`.

- [ ] **Step 2: Rebuild through and tapped SVG strings**

Keep public behavior:
- `tapped_svg` contains `"内螺纹"`.
- `through_svg` contains `"Nut"`.

Add engineering content:
- A comment `<!-- load path -->` in both SVGs.
- Bearing head/washer surface.
- Two clamped members with a visible interface.
- Through joint shows full shank plus nut thread engagement below the parts.
- Tapped joint shows thread engagement inside the lower base, with no nut.
- Compression cone/bulb shading in the clamped parts to communicate clamp load spread.

- [ ] **Step 3: Redraw `ThreadForceTriangleWidget`**

Make the triangle read as actual screw-thread force decomposition:
- Draw a baseline `Ft`, vertical `Fa`, and resultant `Fn`.
- Add small angle arcs for `λ` and `ρ'`.
- Put numeric text in a right-side info card instead of near triangle edges.

- [ ] **Step 4: Verify bolt diagram tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ui/test_engineering_diagrams.py::test_clamping_diagram_svg_distinguishes_joint_types_and_renders tests/ui/test_engineering_diagrams.py::test_thread_force_triangle_renders_readable_force_components -q
```

Expected: pass.

### Task 3: Hertz Contact Diagram

**Files:**
- Modify: `app/ui/widgets/hertz_input_diagram.py`
- Test: `tests/ui/test_engineering_diagrams.py`

- [ ] **Step 1: Introduce small drawing helpers**

Add helpers for:
- `_draw_arrow`
- `_draw_dimension`
- `_draw_badge`
- `_draw_text_card`

Keep all labels inside bounded cards or dimension rails.

- [ ] **Step 2: Rework line contact**

Draw:
- Upper cylinder and lower plane/cylinder based on `R2 == 0`.
- Contact strip with highlighted `2b`.
- Length direction `L` shown as a perspective rail below the contact.
- Equivalent curvature badge `R'` and load-per-length `F/L`.

- [ ] **Step 3: Rework point contact**

Draw:
- Sphere-to-plane or sphere-to-sphere contact.
- Elliptical/circular contact patch with radius `a`.
- Load arrow and `R'` badge.
- Do not show `L` as a current input for point contact.

- [ ] **Step 4: Verify Hertz diagram tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ui/test_engineering_diagrams.py::test_hertz_diagram_renders_line_and_point_contact_modes -q
```

Expected: pass.

### Task 4: Worm Geometry Overview

**Files:**
- Modify: `app/ui/widgets/worm_geometry_overview.py`
- Test: `tests/ui/test_engineering_diagrams.py`, `tests/ui/test_worm_page.py`

- [ ] **Step 1: Add layout helpers**

Add:
- `_diagram_rect_for_testing(self) -> QRectF`
- `_compute_geometry_layout(self, diagram: QRectF) -> dict`

The layout helper must compute:
- `worm_rect`
- `wheel_rect`
- `worm_axis`
- `wheel_axis`
- `center_distance` as a vertical dimension line.

- [ ] **Step 2: Fix geometry logic**

Draw a true worm pair:
- Worm axis horizontal below the wheel.
- Wheel center vertically above worm axis by `a`.
- Center distance dimension is vertical, not horizontal.
- `d1` and `d2` dimension rails stay outside the shapes.
- The mesh marker sits between worm crown and wheel pitch circle.

- [ ] **Step 3: Clean up labels**

Move labels away from geometry:
- `a=...` to the center-distance rail.
- `d1=...` below/left of worm.
- `d2=...` right of wheel.
- `gamma=...` near the helix guide line with enough padding.
- Keep the right info card word-wrapped.

- [ ] **Step 4: Verify worm tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ui/test_engineering_diagrams.py::test_worm_geometry_layout_uses_vertical_center_distance tests/ui/test_worm_page.py -q
```

Expected: pass.

### Task 5: Offscreen Visual Review And Full Verification

**Files:**
- Generated only: `tmp/diagram_after/*.png`

- [ ] **Step 1: Render after images**

Run a small offscreen script to save:
- `tmp/diagram_after/bolt_tapped.png`
- `tmp/diagram_after/bolt_through.png`
- `tmp/diagram_after/bolt_thread_triangle.png`
- `tmp/diagram_after/hertz_line.png`
- `tmp/diagram_after/hertz_point.png`
- `tmp/diagram_after/worm_geometry.png`

- [ ] **Step 2: Visually inspect images**

Check:
- no obvious blank widgets,
- no callout text over structural geometry,
- no center-distance or angle label overlap,
- force arrows point to the correct physical relation,
- each diagram still matches warm neutral app styling.

- [ ] **Step 3: Run full tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q
git diff --check
```

Expected: all tests pass and no whitespace errors.
