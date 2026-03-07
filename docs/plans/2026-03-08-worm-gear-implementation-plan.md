# Worm Gear Module Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the worm module to separate required inputs from derived dimensions, present worm and wheel dimensions in two columns, fix the graphics-page crash, and improve worm-specific engineering illustrations while keeping DIN 3996 deferred.

**Architecture:** Keep `core/worm/calculator.py` as the source of DIN 3975 geometry and basic performance values, but add a lightweight derived-dimensions pathway that can refresh read-only size cards immediately from base inputs. Refactor `WormGearPage` into a more manual-like layout with grouped worm/wheel sections, read-only derived-dimension panels, and a scrollable graphics page whose custom-painted widgets are safe in real paint execution.

**Tech Stack:** Python 3, PySide6, unittest

---

### Task 1: Lock the graphics crash with failing UI tests

**Files:**
- Modify: `tests/ui/test_worm_page.py`
- Test: `app/ui/pages/worm_gear_page.py`
- Test: `app/ui/main_window.py`

**Step 1: Write the failing test**

Add UI tests that render the graphics path for real instead of only instantiating widgets.

```python
def test_graphics_step_can_render_without_crashing(self) -> None:
    page = WormGearPage()
    page.resize(1440, 920)
    page.show()
    page.set_current_chapter(5)
    self.app.processEvents()
    pixmap = page.grab()
    self.assertGreater(pixmap.size().width(), 0)


def test_main_window_can_open_worm_graphics_step(self) -> None:
    window = MainWindow()
    window.resize(1500, 940)
    window.show()
    window.module_list.setCurrentRow(3)
    self.app.processEvents()
    page = window.stack.widget(3)
    page.set_current_chapter(5)
    self.app.processEvents()
    pixmap = window.grab()
    self.assertGreater(pixmap.size().height(), 0)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_worm_page.WormGearPageTests.test_graphics_step_can_render_without_crashing tests.ui.test_worm_page.MainWindowWormModuleTests.test_main_window_can_open_worm_graphics_step -v`
Expected: FAIL with `AttributeError` from `Qt.AlignmentFlag.TextWordWrap`

**Step 3: Write minimal implementation**

Fix the invalid Qt flag usage and ensure custom-painted widgets can render through `show()` / `grab()` without leaving an active painter.

**Step 4: Run test to verify it passes**

Run the same unittest command.
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_worm_page.py app/ui/widgets/worm_geometry_overview.py app/ui/widgets/worm_tolerance_overview.py app/ui/widgets/worm_performance_curve.py
 git commit -m "fix: stop worm graphics page from crashing"
```

### Task 2: Define derived-dimension outputs with test-first geometry coverage

**Files:**
- Modify: `tests/core/worm/test_calculator.py`
- Modify: `core/worm/calculator.py`

**Step 1: Write the failing test**

Add a test that asserts the calculator returns separate derived-dimension groups for worm and wheel.

```python
def test_geometry_returns_separate_worm_and_wheel_dimensions(self) -> None:
    result = calculate_worm_geometry(sample_payload)
    self.assertIn("worm_dimensions", result["geometry"])
    self.assertIn("wheel_dimensions", result["geometry"])
    self.assertIn("pitch_diameter_mm", result["geometry"]["worm_dimensions"])
    self.assertIn("pitch_diameter_mm", result["geometry"]["wheel_dimensions"])
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.core.worm.test_calculator.WormCalculatorTests.test_geometry_returns_separate_worm_and_wheel_dimensions -v`
Expected: FAIL because the grouped fields do not exist yet

**Step 3: Write minimal implementation**

Extend the calculator to return grouped derived dimensions, including worm diameters, wheel diameters, ratio, center-distance outputs, and speed outputs required by the read-only UI cards.

**Step 4: Run test to verify it passes**

Run the same unittest command.
Expected: PASS

**Step 5: Commit**

```bash
git add tests/core/worm/test_calculator.py core/worm/calculator.py
 git commit -m "feat: group worm derived dimensions for UI"
```

### Task 3: Add failing page tests for grouped input sections and live derived-size panels

**Files:**
- Modify: `tests/ui/test_worm_page.py`
- Test: `app/ui/pages/worm_gear_page.py`

**Step 1: Write the failing test**

Add tests that require the page to expose grouped sections and update read-only derived values after base-input edits.

```python
def test_geometry_page_contains_grouped_worm_and_wheel_sections(self) -> None:
    page = WormGearPage()
    self.assertEqual(page.geometry_group_titles, [
        "蜗杆参数",
        "蜗轮参数",
        "啮合与装配",
        "蜗杆自动计算尺寸",
        "蜗轮自动计算尺寸",
    ])


def test_derived_dimension_panel_updates_when_base_input_changes(self) -> None:
    page = WormGearPage()
    page._field_widgets["geometry.module_mm"].setText("5.0")
    page._refresh_derived_geometry_preview()
    self.assertIn("50.000", page.worm_dimension_labels["pitch_diameter_mm"].text())
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_worm_page.WormGearPageTests.test_geometry_page_contains_grouped_worm_and_wheel_sections tests.ui.test_worm_page.WormGearPageTests.test_derived_dimension_panel_updates_when_base_input_changes -v`
Expected: FAIL because the grouped layout and preview labels are not implemented yet

**Step 3: Write minimal implementation**

Refactor the geometry step to:
- separate worm and wheel inputs into two columns
- add a meshing/assembly group
- add two read-only derived-dimension panels
- refresh derived dimensions from current base inputs without requiring full calculation

**Step 4: Run test to verify it passes**

Run the same unittest command.
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_worm_page.py app/ui/pages/worm_gear_page.py
 git commit -m "feat: split worm geometry inputs and derived size panels"
```

### Task 4: Expand manual-like inputs and advanced parameters without reintroducing ambiguity

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `tests/ui/test_worm_page.py`
- Modify: `examples/worm_case_01.json`
- Modify: `examples/worm_case_02.json`

**Step 1: Write the failing test**

Add tests covering the new visible fields and advanced-parameter defaults.

```python
def test_page_exposes_manual_like_fields_and_advanced_parameters(self) -> None:
    page = WormGearPage()
    self.assertIn("geometry.handedness", page._field_widgets)
    self.assertIn("geometry.worm_face_width_mm", page._field_widgets)
    self.assertIn("geometry.wheel_face_width_mm", page._field_widgets)
    self.assertIn("advanced.friction_override", page._field_widgets)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_worm_page.WormGearPageTests.test_page_exposes_manual_like_fields_and_advanced_parameters -v`
Expected: FAIL because the additional fields do not exist yet

**Step 3: Write minimal implementation**

Add the new grouped fields, keep advanced inputs collapsed or visually secondary, and update sample payloads to include the new structure.

**Step 4: Run test to verify it passes**

Run the same unittest command.
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_worm_page.py app/ui/pages/worm_gear_page.py examples/worm_case_01.json examples/worm_case_02.json
 git commit -m "feat: add manual-like worm geometry and advanced fields"
```

### Task 5: Replace placeholder graphics with worm-specific engineering illustrations

**Files:**
- Modify: `app/ui/widgets/worm_geometry_overview.py`
- Modify: `app/ui/widgets/worm_tolerance_overview.py`
- Modify: `tests/ui/test_worm_page.py`

**Step 1: Write the failing test**

Add smoke tests that require the widgets to expose updated worm-specific titles or notes and to survive real rendering.

```python
def test_geometry_overview_renders_worm_specific_note(self) -> None:
    widget = WormGeometryOverviewWidget()
    widget.set_display_state("几何总览", "蜗杆螺旋与蜗轮啮合示意")
    widget.resize(900, 320)
    widget.show()
    self.app.processEvents()
    pixmap = widget.grab()
    self.assertEqual(widget._title, "几何总览")
    self.assertGreater(pixmap.size().width(), 0)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_worm_page.WormOverviewWidgetTests -v`
Expected: FAIL if widgets still crash or cannot render through `grab()`

**Step 3: Write minimal implementation**

Redraw both widgets so they clearly depict worm/wheel geometry and worm-pair tolerance concepts, while keeping them as high-quality placeholders rather than live-geometry renderers.

**Step 4: Run test to verify it passes**

Run the same unittest command.
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_worm_page.py app/ui/widgets/worm_geometry_overview.py app/ui/widgets/worm_tolerance_overview.py
 git commit -m "feat: improve worm engineering overview graphics"
```

### Task 6: Make the graphics page scrollable and preserve performance-curve behavior

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `tests/ui/test_worm_page.py`
- Test: `app/ui/widgets/worm_performance_curve.py`

**Step 1: Write the failing test**

Add a page test that checks the graphics step is hosted in a scrollable container and still updates the performance curve after calculation.

```python
def test_graphics_step_uses_scroll_area_and_curve_still_updates(self) -> None:
    page = WormGearPage()
    self.assertIsNotNone(page.graphics_scroll_area)
    page._calculate()
    self.assertGreater(len(page.performance_curve._efficiency), 0)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_worm_page.WormGearPageTests.test_graphics_step_uses_scroll_area_and_curve_still_updates -v`
Expected: FAIL because the scroll area handle does not exist yet

**Step 3: Write minimal implementation**

Wrap the graphics page in a `QScrollArea`, keep geometry/tolerance/performance cards stacked vertically, and ensure calculation still populates the curve widget.

**Step 4: Run test to verify it passes**

Run the same unittest command.
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_worm_page.py app/ui/pages/worm_gear_page.py
 git commit -m "feat: make worm graphics step scrollable"
```

### Task 7: Verify examples, docs, and module-level smoke coverage

**Files:**
- Modify: `README.md`
- Modify: `tests/ui/test_worm_page.py`
- Modify: `tests/core/worm/test_calculator.py`
- Modify: `docs/plans/2026-03-08-worm-gear-design.md`
- Modify: `docs/plans/2026-03-08-worm-gear-implementation-plan.md`

**Step 1: Write the failing test**

If needed, add or update smoke assertions to reflect the new grouped layout and example loading behavior.

**Step 2: Run test to verify it fails**

Run the targeted tests impacted by doc/example changes.
Expected: FAIL only if example structures are stale

**Step 3: Write minimal implementation**

Update docs and example payloads so the current worm-module behavior is accurately documented.

**Step 4: Run test to verify it passes**

Run:
`python3 -m unittest tests.core.worm.test_calculator tests.ui.test_worm_page -v`
Expected: PASS

Then run:
`python3 -m py_compile app/ui/pages/worm_gear_page.py app/ui/widgets/worm_performance_curve.py app/ui/widgets/worm_geometry_overview.py app/ui/widgets/worm_tolerance_overview.py core/worm/calculator.py app/ui/main_window.py`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md tests/core/worm/test_calculator.py tests/ui/test_worm_page.py docs/plans/2026-03-08-worm-gear-design.md docs/plans/2026-03-08-worm-gear-implementation-plan.md
 git commit -m "docs: capture worm module polish behavior"
```
