# Bolt Page Review Follow-up Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the high-risk bolt page issues found in the 2026-03-17 deep review: broken input-condition round-trip, thermal custom-parameter validation gaps, R5 result semantics mismatch, and flowchart/detail-page duplication.

**Architecture:** Four coordinated change sets: (1) normalize bolt-page persistence and restore logic, (2) harden thermal/custom input validation in UI and core, (3) align result/report rendering with actual calculator checks, and (4) add headless UI regression coverage for `bolt_page.py` and `bolt_flowchart.py`. The calculator core formulas remain mostly intact; the main risk is UI/core state drift.

**Tech Stack:** Python 3.12, PySide6, pytest

**Spec:** `docs/review/2026-03-17-bolt-page-deep-review.md`

---

## Chunk 1: Save/Load Round-Trip Hardening

### Task 1: Add failing tests for bolt-page snapshot round-trip

**Files:**
- Create: `tests/ui/test_bolt_page.py`
- Modify: `app/ui/pages/bolt_page.py:1660-1712`
- Modify: `app/ui/input_condition_store.py:21-45`

- [ ] **Step 1: Write the failing test for standard thread snapshot round-trip**

Add a new file `tests/ui/test_bolt_page.py` with a helper that creates a `QApplication` and `BoltPage`, then add:

```python
def test_snapshot_round_trip_supports_standard_thread_labels():
    page = BoltPage()
    snapshot = page._capture_input_snapshot()

    clone = BoltPage()
    clone._apply_input_data(snapshot)

    assert clone._field_widgets["fastener.d"].currentText() == "M10"
    assert clone._field_widgets["fastener.p"].currentText().startswith("1.5")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py::test_snapshot_round_trip_supports_standard_thread_labels -v`

Expected: FAIL with `ValueError: could not convert string to float: '1.5（粗牙）'`

- [ ] **Step 3: Normalize bolt-page snapshot values before persistence**

In `app/ui/pages/bolt_page.py`, replace `_capture_input_snapshot()` with bolt-specific normalization for thread selectors:

```python
def _capture_input_snapshot(self) -> dict[str, Any]:
    snapshot = build_form_snapshot(
        self._field_specs.values(),
        self._read_widget_value,
        extra_state={
            "check_level": self._current_check_level(),
            "calculation_mode": self.calc_mode_combo.currentData() or "design",
        },
    )
    fastener = snapshot.setdefault("inputs", {}).setdefault("fastener", {})
    d_raw = self._resolve_thread_d()
    p_raw = self._resolve_thread_p()
    if d_raw:
        fastener["d"] = d_raw
    if p_raw:
        fastener["p"] = p_raw
    return snapshot
```

Do not rely on the display text `M10` / `1.5（粗牙）` as persisted values.

- [ ] **Step 4: Make `_apply_input_data()` tolerate either canonical values or label text**

Update the `fastener.p` restore branch so it handles:
- canonical numeric strings like `"1.5"`
- already-labeled strings like `"1.5（粗牙）"`

Use a small helper inside `_apply_input_data()`:

```python
def _parse_pitch_text(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        try:
            return float(text.split("（")[0].strip())
        except ValueError:
            return None
```

Then compare parsed values safely instead of raw `float(text)`.

- [ ] **Step 5: Re-run the test and confirm it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py::test_snapshot_round_trip_supports_standard_thread_labels -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/ui/test_bolt_page.py app/ui/pages/bolt_page.py app/ui/input_condition_store.py
git commit -m "fix(bolt): normalize input-condition round-trip for thread selectors"
```

### Task 2: Persist and restore key bolt-page UI state

**Files:**
- Modify: `tests/ui/test_bolt_page.py`
- Modify: `app/ui/pages/bolt_page.py:1660-1800`

- [ ] **Step 1: Write failing tests for `calculation_mode` persistence and raw payload selector restore**

Add:

```python
def test_snapshot_persists_calculation_mode():
    page = BoltPage()
    page.calc_mode_combo.setCurrentIndex(1)  # verify
    snapshot = page._capture_input_snapshot()

    clone = BoltPage()
    clone._apply_input_data(snapshot)

    assert clone.calc_mode_combo.currentData() == "verify"


def test_apply_raw_payload_restores_choice_selectors():
    page = BoltPage()
    raw = {
        "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
        "tightening": {
            "alpha_A": 1.5, "mu_thread": 0.1, "mu_bearing": 0.12,
            "utilization": 0.85, "thread_flank_angle_deg": 60.0,
        },
        "loads": {
            "FA_max": 6000.0, "FQ_max": 600.0, "embed_loss": 600.0,
            "thermal_force_loss": 300.0, "slip_friction_coefficient": 0.2,
            "friction_interfaces": 1.0, "FM_min_input": 12000.0,
        },
        "stiffness": {
            "auto_compliance": True, "E_bolt": 210000.0,
            "E_clamped": 210000.0, "load_introduction_factor_n": 1.0,
        },
        "bearing": {"bearing_d_inner": 13.0, "bearing_d_outer": 22.0, "p_G_allow": 700.0},
        "clamped": {"basic_solid": "cone", "surface_class": "fine", "total_thickness": 20.0, "D_A": 24.0},
        "options": {
            "joint_type": "through", "check_level": "fatigue",
            "calculation_mode": "verify", "tightening_method": "angle",
            "surface_treatment": "cut",
        },
        "checks": {"yield_safety_operating": 1.15},
    }
    page._apply_input_data(raw)
    assert page._field_widgets["elements.joint_type"].currentText() == "通孔螺栓连接"
    assert page.calc_mode_combo.currentData() == "verify"
    assert page._field_widgets["clamped.basic_solid"].currentText() == "锥体"
    assert page._field_widgets["clamped.surface_class"].currentText() == "精细 (Ra≈1.6μm)"
    assert page._field_widgets["assembly.tightening_method"].currentText() == "转角法"
    assert page._field_widgets["options.surface_treatment"].currentText() == "切削"
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "calculation_mode or raw_payload" -v`

Expected: FAIL

- [ ] **Step 3: Implement explicit restore mappings in `_apply_input_data()`**

Add reverse-restore branches for:
- `ui_state["calculation_mode"]`
- `options.joint_type`
- `clamped.basic_solid`
- `clamped.surface_class`
- `options.tightening_method`
- `options.surface_treatment`
- `stiffness.auto_compliance`

Recommended pattern:

```python
if "calculation_mode" in ui_state:
    self.calc_mode_combo.setCurrentIndex(
        self.calc_mode_combo.findData(ui_state["calculation_mode"])
    )
elif isinstance(options, dict) and "calculation_mode" in options:
    ...
```

For choice selectors that are stored in English/raw form, map them back through the inverse dictionaries before calling `setCurrentText()`.

- [ ] **Step 4: Re-run the targeted tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "calculation_mode or raw_payload" -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ui/test_bolt_page.py app/ui/pages/bolt_page.py
git commit -m "fix(bolt): persist calculation mode and restore choice selectors"
```

---

## Chunk 2: Thermal and Custom Input Validation

### Task 3: Remove silent steel fallback for custom thermal inputs

**Files:**
- Modify: `tests/ui/test_bolt_page.py`
- Modify: `tests/core/bolt/test_calculator.py`
- Modify: `app/ui/pages/bolt_page.py:1273-1299, 1930-1960`
- Modify: `core/bolt/calculator.py:294-340`

- [ ] **Step 1: Add failing UI tests for custom-material alpha requirements**

Add:

```python
def test_single_layer_custom_material_requires_alpha():
    page = BoltPage()
    page._set_check_level("thermal")
    page._apply_check_level_visibility()
    page._field_widgets["operating.bolt_material"].setCurrentText("自定义")
    page._field_widgets["operating.clamped_material"].setCurrentText("自定义")

    with pytest.raises(InputError, match="热膨胀系数"):
        page._build_payload()


def test_multi_layer_custom_material_requires_alpha():
    page = BoltPage()
    page._field_widgets["clamped.part_count"].setCurrentText("2")
    page._on_part_count_changed()
    page._set_check_level("thermal")
    page._apply_check_level_visibility()
    page._field_widgets["clamped.layer_1.material"].setCurrentText("自定义")

    with pytest.raises(InputError, match="第1层.*热膨胀系数"):
        page._build_payload()
```

- [ ] **Step 2: Add a failing core test proving missing alpha must not silently become steel**

Add to `tests/core/bolt/test_calculator.py`:

```python
def test_missing_alpha_values_do_not_silently_fall_back_to_steel_for_thermal_estimation():
    data = _base_input()
    data["options"] = {"check_level": "thermal"}
    data["loads"]["thermal_force_loss"] = 0
    data["operating"] = {"temp_bolt": 120.0, "temp_parts": 20.0}
    data["clamped"] = {"total_thickness": 20.0}
    result = calculate_vdi2230_core(data)
    assert result["thermal"]["thermal_auto_estimated"] is False
    assert result["thermal"]["thermal_auto_value_N"] == 0.0
```

- [ ] **Step 3: Run the targeted tests and verify failure**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "requires_alpha" -v`

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py -k "missing_alpha_values" -v`

Expected: FAIL

- [ ] **Step 4: Add explicit UI-level validation in `_build_payload()`**

When a thermal field is visible:
- if `operating.bolt_material == "自定义"` and `operating.alpha_bolt` is blank, raise `InputError`
- if single-layer `operating.clamped_material == "自定义"` and `operating.alpha_parts` is blank, raise `InputError`
- if multi-layer `clamped.layer_n.material == "自定义"` and `clamped.layer_n.alpha` is blank, raise `InputError`

Use the same `InputError` style already used elsewhere in the page:

```python
raise InputError("字段 [螺栓热膨胀系数 α_bolt] 不能为空。")
```

- [ ] **Step 5: Remove `_ALPHA_STEEL_DEFAULT` fallback from the thermal auto-estimation branch**

In `core/bolt/calculator.py`, replace:

```python
_ALPHA_STEEL_DEFAULT = 11.5e-6
alpha_bolt = float(operating.get("alpha_bolt", _ALPHA_STEEL_DEFAULT))
alpha_parts = float(operating.get("alpha_parts", _ALPHA_STEEL_DEFAULT))
```

with a safer approach:

```python
alpha_bolt_raw = operating.get("alpha_bolt")
alpha_parts_raw = operating.get("alpha_parts")
alpha_bolt = float(alpha_bolt_raw) if alpha_bolt_raw is not None else None
alpha_parts = float(alpha_parts_raw) if alpha_parts_raw is not None else None
```

Then only run single-layer thermal auto-estimation when both values are present.

- [ ] **Step 6: Convert multi-layer raw `ValueError` paths to `InputError`**

Wrap the `float()` conversions in the multi-layer payload builder and surface layer-specific messages instead of raw conversion errors.

- [ ] **Step 7: Re-run the targeted tests**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "requires_alpha" -v
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py -k "missing_alpha_values" -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add tests/ui/test_bolt_page.py tests/core/bolt/test_calculator.py app/ui/pages/bolt_page.py core/bolt/calculator.py
git commit -m "fix(bolt): require custom thermal coefficients and remove silent steel fallback"
```

---

## Chunk 3: Result Semantics and Flowchart Rendering

### Task 4: Align R5 page/report summaries with actual `sigma_vm_work` check

**Files:**
- Modify: `tests/ui/test_bolt_page.py`
- Modify: `app/ui/pages/bolt_page.py:2014-2203`

- [ ] **Step 1: Add a failing UI test for the R5 summary mismatch**

Add:

```python
def test_r5_summary_uses_sigma_vm_work_when_torque_method_controls():
    page = BoltPage()
    payload = {
        "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
        "tightening": {
            "alpha_A": 1.8, "mu_thread": 0.4, "mu_bearing": 0.12,
            "utilization": 0.85, "thread_flank_angle_deg": 60.0,
        },
        "loads": {
            "FA_max": 40000.0, "FQ_max": 600.0, "embed_loss": 600.0,
            "thermal_force_loss": 300.0, "slip_friction_coefficient": 0.2,
            "friction_interfaces": 1.0,
        },
        "stiffness": {
            "bolt_compliance": 1.8e-06, "clamped_compliance": 2.4e-06,
            "load_introduction_factor_n": 1.0,
        },
        "bearing": {"bearing_d_inner": 13.0, "bearing_d_outer": 22.0, "p_G_allow": 700.0},
        "checks": {"yield_safety_operating": 1.15},
        "options": {"tightening_method": "torque", "check_level": "basic"},
    }
    result = calculate_vdi2230_core(payload)
    page._render_result(payload, result)
    assert "867.1" in page.metrics_text.text()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py::test_r5_summary_uses_sigma_vm_work_when_torque_method_controls -v`

Expected: FAIL (current text shows `714.3`)

- [ ] **Step 3: Update page metrics and report lines**

In `app/ui/pages/bolt_page.py`:
- change the R5 metric line to use `sigma_vm_work`
- optionally append `sigma_ax_work` as a secondary detail in the message box or flowchart only
- change report output from `sigma_ax_work` to `sigma_vm_work`

Recommended wording:

```python
f"• 服役等效应力: {stresses['sigma_vm_work']:.1f} MPa / 允许 {stresses['sigma_allow_work']:.1f} MPa"
```

- [ ] **Step 4: Re-run the test**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py::test_r5_summary_uses_sigma_vm_work_when_torque_method_controls -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ui/test_bolt_page.py app/ui/pages/bolt_page.py
git commit -m "fix(bolt): align R5 page and report summaries with sigma_vm_work"
```

### Task 5: Prevent flowchart detail-page input echo duplication

**Files:**
- Modify: `tests/ui/test_bolt_page.py`
- Modify: `app/ui/pages/bolt_flowchart.py:364-431`
- Modify: `app/ui/pages/bolt_page.py:2004-2010`

- [ ] **Step 1: Add a failing UI test for duplicate input echo growth**

Add:

```python
def test_r_step_input_echo_does_not_duplicate_on_recalculate():
    page = BoltPage()
    r_page = page._r_pages[0]
    page._calculate()
    first = r_page._input_layout.count()
    page._calculate()
    second = r_page._input_layout.count()
    assert second == first
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py::test_r_step_input_echo_does_not_duplicate_on_recalculate -v`

Expected: FAIL (`54 != 108`)

- [ ] **Step 3: Fix `build_input_echo()` to be idempotent**

Recommended approach:
- if `_input_labels` is already populated, do not create new widgets again
- only build once, then let `update_from_result()` refresh values

Minimal guard:

```python
if self._input_labels:
    return
```

If layout rebuilding is preferred, clear the grid first before adding widgets again.

- [ ] **Step 4: Re-run the test**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py::test_r_step_input_echo_does_not_duplicate_on_recalculate -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ui/test_bolt_page.py app/ui/pages/bolt_flowchart.py app/ui/pages/bolt_page.py
git commit -m "fix(bolt): make R-step input echo idempotent across recalculations"
```

### Task 6: Clean stale hint cache and dead config

**Files:**
- Modify: `tests/ui/test_bolt_page.py`
- Modify: `app/ui/pages/bolt_page.py:1383-1393`
- Modify: `app/ui/pages/bolt_flowchart.py:13-30`

- [ ] **Step 1: Add tests proving the bottom help cache updates with the selector**

Add:

```python
def test_alpha_hint_cache_updates_with_tightening_method():
    page = BoltPage()
    alpha = page._field_widgets["tightening.alpha_A"]
    page._field_widgets["assembly.tightening_method"].setCurrentText("液压拉伸法")
    assert "1.05~1.15" in page._widget_hints[alpha]


def test_n_hint_cache_updates_with_position():
    page = BoltPage()
    n_widget = page._field_widgets["stiffness.load_introduction_factor_n"]
    page._field_widgets["introduction.position"].setCurrentText("中间")
    assert "0.3~0.5" in page._widget_hints[n_widget]
```

- [ ] **Step 2: Run the tests to verify failure**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "hint_cache_updates" -v`

Expected: FAIL

- [ ] **Step 3: Update both `tooltip` and `_widget_hints` together**

Refactor `_on_tightening_method_changed()` and `_on_position_changed()` so the cached help text used by the footer stays in sync with the tooltip.

Also either:
- remove unused `summary_key` from `R_STEPS`, or
- wire it into actual rendering if there is a real use case

- [ ] **Step 4: Re-run the tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "hint_cache_updates" -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ui/test_bolt_page.py app/ui/pages/bolt_page.py app/ui/pages/bolt_flowchart.py
git commit -m "refactor(bolt): sync footer hints with tooltips and remove dead flowchart config"
```

---

## Chunk 4: Verification and Close-Out

### Task 7: Run targeted and full verification, then sync docs

**Files:**
- Modify: `docs/review/2026-03-17-bolt-page-deep-review.md`
- Modify: `progress.md`
- Modify: `findings.md`

- [ ] **Step 1: Run the full targeted bolt/UI suite**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
  tests/core/bolt/test_calculator.py \
  tests/core/bolt/test_compliance_model.py \
  tests/ui/test_bolt_page.py \
  tests/ui/test_input_condition_store.py -q
```

Expected: all tests pass

- [ ] **Step 2: Run the full repository suite**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q
```

Expected: all tests pass

- [ ] **Step 3: Update the review doc with fix status**

Add a short “Resolved in follow-up” section to `docs/review/2026-03-17-bolt-page-deep-review.md` once the remediation lands.

- [ ] **Step 4: Update planning files**

Record:
- what changed
- what tests ran
- any remaining limitations

- [ ] **Step 5: Commit**

```bash
git add docs/review/2026-03-17-bolt-page-deep-review.md findings.md progress.md
git commit -m "docs(bolt): record bolt page remediation verification results"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-17-bolt-page-review-followup.md`. Ready to execute.
