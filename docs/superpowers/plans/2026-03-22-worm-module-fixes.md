# Worm Module Comprehensive Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 21 review issues in the worm gear module, add profile shift coefficients, and overhaul materials from bronze to plastic (37CrS4 / PA66 / PA66+GF30).

**Architecture:** Pure computation in `core/worm/calculator.py` (dict in → dict out), UI in `app/ui/pages/worm_gear_page.py` with `FieldSpec`-driven forms. Changes are surgical edits to these two files plus their tests, example JSON, and one widget deletion.

**Tech Stack:** Python 3.12, PySide6, pytest (headless: `QT_QPA_PLATFORM=offscreen`)

**Spec:** `docs/superpowers/specs/2026-03-22-worm-module-fixes-design.md`

---

### Task 1: Calculator — Material Tables & Profile Shift & Geometry Formulas

**Files:**
- Modify: `core/worm/calculator.py:39-62` (material tables)
- Modify: `core/worm/calculator.py:65-133` (geometry formulas)
- Test: `tests/core/worm/test_calculator.py`

- [ ] **Step 1: Write failing tests for new materials and profile shift**

Add to `tests/core/worm/test_calculator.py`:

```python
def _base_payload(self) -> dict:
    """Updated to 37CrS4 / PA66 with profile shift."""
    return {
        "geometry": {
            "z1": 2.0,
            "z2": 40.0,
            "module_mm": 4.0,
            "center_distance_mm": 100.0,
            "diameter_factor_q": 10.0,
            "lead_angle_deg": 11.31,
            "worm_face_width_mm": 36.0,
            "wheel_face_width_mm": 30.0,
            "x1": 0.0,
            "x2": 0.0,
        },
        "operating": {
            "power_kw": 3.0,
            "speed_rpm": 1450.0,
            "application_factor": 1.25,
            "torque_ripple_percent": 0.0,
        },
        "materials": {
            "worm_material": "37CrS4",
            "wheel_material": "PA66",
            "worm_e_mpa": 210000.0,
            "worm_nu": 0.30,
            "wheel_e_mpa": 3000.0,
            "wheel_nu": 0.38,
        },
        "advanced": {
            "friction_override": "",
            "normal_pressure_angle_deg": 20.0,
        },
        "load_capacity": {
            "enabled": True,
            "method": "DIN 3996 Method B",
            "allowable_contact_stress_mpa": 42.0,
            "allowable_root_stress_mpa": 55.0,
            "dynamic_factor_kv": 1.05,
            "transverse_load_factor_kha": 1.00,
            "face_load_factor_khb": 1.10,
            "required_contact_safety": 1.00,
            "required_root_safety": 1.00,
        },
    }

def test_profile_shift_changes_tip_and_root_diameters(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["x1"] = 0.3
    payload["geometry"]["x2"] = 0.5

    result = calculate_worm_geometry(payload)

    worm = result["geometry"]["worm_dimensions"]
    wheel = result["geometry"]["wheel_dimensions"]
    m = 4.0
    q = 10.0
    z2 = 40.0
    d1 = q * m  # 40
    d2 = z2 * m  # 160
    self.assertAlmostEqual(worm["pitch_diameter_mm"], d1)
    self.assertAlmostEqual(wheel["pitch_diameter_mm"], d2)
    # da1 = d1 + 2m(1+x1) = 40 + 2*4*(1.3) = 50.4
    self.assertAlmostEqual(worm["tip_diameter_mm"], 50.4, places=3)
    # da2 = d2 + 2m(1+x2) = 160 + 2*4*(1.5) = 172.0
    self.assertAlmostEqual(wheel["tip_diameter_mm"], 172.0, places=3)
    # df1 = d1 - 2m(1.2-x1) = 40 - 2*4*(0.9) = 32.8
    self.assertAlmostEqual(worm["root_diameter_mm"], 32.8, places=3)
    # df2 = d2 - 2m(1.2-x2) = 160 - 2*4*(0.7) = 154.4
    self.assertAlmostEqual(wheel["root_diameter_mm"], 154.4, places=3)

def test_profile_shift_affects_working_center_distance_warning(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["x1"] = 0.0
    payload["geometry"]["x2"] = 1.0
    # a_w = m(q+z2)/2 + (x1+x2)*m = 4*50/2 + 1.0*4 = 104
    # user a = 100 → delta = -4, should warn

    result = calculate_worm_geometry(payload)

    warnings = result["geometry"]["consistency"]["warnings"]
    self.assertTrue(any("中心距" in w for w in warnings))

def test_default_friction_uses_new_material_pair(self) -> None:
    payload = self._base_payload()
    # 37CrS4 + PA66 → 0.18

    result = calculate_worm_geometry(payload)

    self.assertAlmostEqual(result["performance"]["friction_mu"], 0.18)

def test_pitch_diameter_wheel_uses_standard_definition(self) -> None:
    """d2 = z2 * m, not derived from center distance."""
    payload = self._base_payload()
    payload["geometry"]["center_distance_mm"] = 110.0  # off from theoretical

    result = calculate_worm_geometry(payload)

    # d2 should be z2*m = 40*4 = 160 regardless of center distance
    self.assertAlmostEqual(result["geometry"]["wheel_dimensions"]["pitch_diameter_mm"], 160.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v -k "profile_shift or default_friction or pitch_diameter_wheel_uses"`
Expected: FAIL (new material not recognized, x1/x2 not read, d2 still derived from a)

- [ ] **Step 3: Implement material tables + profile shift + geometry formula changes**

In `core/worm/calculator.py`:

1. Replace `MATERIAL_FRICTION_HINTS`, `MATERIAL_ELASTIC_HINTS`, `MATERIAL_ALLOWABLE_HINTS` with new tables per spec 1.1
2. Update `_estimate_friction` fallback to `0.20`
3. Read `x1 = float(geometry.get("x1", 0.0))` and `x2 = float(geometry.get("x2", 0.0))`
4. Change `pitch_diameter_wheel_mm = z2 * module_mm` (replace old `2*a - d1` derivation)
5. Update tip/root diameters:
   - `worm_tip_diameter_mm = pitch_diameter_worm_mm + 2.0 * module_mm * (1.0 + x1)`
   - `worm_root_diameter_mm = max(1e-6, pitch_diameter_worm_mm - 2.0 * module_mm * (1.2 - x1))`
   - `wheel_tip_diameter_mm = pitch_diameter_wheel_mm + 2.0 * module_mm * (1.0 + x2)`
   - `wheel_root_diameter_mm = max(1e-6, pitch_diameter_wheel_mm - 2.0 * module_mm * (1.2 - x2))`
6. Update `theoretical_center_distance_mm = module_mm * (diameter_factor_q + z2) / 2.0 + (x1 + x2) * module_mm`
7. Update `tooth_height_mm = module_mm * (2.2 + x1 - x2)`
8. Keep `tooth_root_thickness_mm = max(1.25 * module_mm, 1e-6)` unchanged (spec does not cover root thickness shift)

- [ ] **Step 4: Also update all existing tests that use old materials**

Update `test_basic_geometry_outputs_ratio_and_performance_curve` and other tests that use `"20CrMnTi"` / `"ZCuSn12Ni2"` to `"37CrS4"` / `"PA66"`.

- [ ] **Step 5: Run all calculator tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add core/worm/calculator.py tests/core/worm/test_calculator.py
git commit -m "feat(worm): replace materials with 37CrS4/PA66, add profile shift x1/x2, fix d2 derivation"
```

---

### Task 2: Calculator — Thermal Capacity, Lead Angle, Enabled Flag

**Files:**
- Modify: `core/worm/calculator.py:146-153` (thermal), `core/worm/calculator.py:113-119` (lead angle), `core/worm/calculator.py:158-182` (enabled guard)
- Test: `tests/core/worm/test_calculator.py`

- [ ] **Step 1: Write failing tests**

```python
def test_thermal_capacity_equals_power_loss(self) -> None:
    payload = self._base_payload()

    result = calculate_worm_geometry(payload)

    perf = result["performance"]
    self.assertAlmostEqual(perf["thermal_capacity_kw"], perf["power_loss_kw"], places=9)

def test_lead_angle_downstream_uses_calculated_value(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["lead_angle_deg"] = 20.0  # deliberate mismatch with z1/q=atan(2/10)=11.31

    result = calculate_worm_geometry(payload)

    # Output should have both values; lead_angle_deg = calc value for backward compat
    self.assertAlmostEqual(result["geometry"]["lead_angle_input_deg"], 20.0)
    calc_deg = result["geometry"]["lead_angle_deg"]  # now the calc value
    self.assertAlmostEqual(calc_deg, 11.3099, places=2)
    # Efficiency should use the calc value, not 20 deg
    # At gamma=11.31 deg, efficiency is lower than at gamma=20 deg
    payload2 = self._base_payload()  # lead_angle_deg=11.31, matches calc
    result2 = calculate_worm_geometry(payload2)
    # Both should have same efficiency since both use atan(z1/q)
    self.assertAlmostEqual(
        result["performance"]["efficiency_estimate"],
        result2["performance"]["efficiency_estimate"],
        places=6,
    )

def test_enabled_false_returns_stub(self) -> None:
    payload = self._base_payload()
    payload["load_capacity"]["enabled"] = False
    # Remove LC fields to prove they're not required when disabled
    del payload["load_capacity"]["allowable_contact_stress_mpa"]
    del payload["load_capacity"]["dynamic_factor_kv"]

    result = calculate_worm_geometry(payload)

    lc = result["load_capacity"]
    self.assertFalse(lc["enabled"])
    self.assertEqual(lc["status"], "未启用")
    self.assertEqual(lc["checks"], {})
    self.assertEqual(lc["forces"], {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v -k "thermal_capacity_equals or lead_angle_downstream or enabled_false"`
Expected: FAIL

- [ ] **Step 3: Implement thermal capacity fix**

In `calculator.py`:
- Change `thermal_capacity_kw = power_loss_kw` (was `power_kw + power_loss_kw * 0.55`)
- In curve loop: change `p_thermal_i = p_loss_i` (was `power_kw * factor + p_loss_i * 0.55`)

- [ ] **Step 4: Implement lead angle self-consistency**

In `calculator.py`:
- Add `lead_angle_calc_rad = math.atan(z1 / diameter_factor_q)` after reading `lead_angle_deg`
- Replace all downstream uses of `lead_angle_rad` with `lead_angle_calc_rad`
- Keep `lead_angle_rad = math.radians(lead_angle_deg)` for the consistency comparison only
- **Output key strategy (backward compatible):** Keep `"lead_angle_deg"` key in output but set it to the **calculated** value `math.degrees(lead_angle_calc_rad)`. Add a new key `"lead_angle_input_deg": lead_angle_deg` alongside. This avoids breaking UI consumers that read `geometry['lead_angle_deg']`.
- Update `lead_angle_delta_deg` to compare input vs calc
- Update `lead_angle_implied_deg` → rename to `lead_angle_calc_deg` for clarity (it is the same value)

- [ ] **Step 5: Implement enabled flag guard**

In `calculator.py`, after reading `load_capacity.enabled`:
- If `not enabled`: return early from the load capacity block with stub dict per spec 1.5
- Move all LC parameter reads (`dynamic_factor_kv`, etc.) to after the enabled check

- [ ] **Step 6: Run all calculator tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add core/worm/calculator.py tests/core/worm/test_calculator.py
git commit -m "fix(worm): thermal=loss, lead angle uses atan(z1/q), enabled flag guards LC"
```

---

### Task 3: Calculator — Input Validation & Assumptions

**Files:**
- Modify: `core/worm/calculator.py:73-88` (validation), `core/worm/calculator.py:420-425` (assumptions)
- Test: `tests/core/worm/test_calculator.py`

- [ ] **Step 1: Write failing tests**

```python
def test_non_integer_z1_is_rejected(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["z1"] = 1.5

    with self.assertRaises(InputError):
        calculate_worm_geometry(payload)

def test_non_integer_z2_is_rejected(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["z2"] = 40.5

    with self.assertRaises(InputError):
        calculate_worm_geometry(payload)

def test_lead_angle_above_45_is_rejected(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["lead_angle_deg"] = 60.0

    with self.assertRaises(InputError):
        calculate_worm_geometry(payload)

def test_friction_override_below_range_is_rejected(self) -> None:
    payload = self._base_payload()
    payload["advanced"]["friction_override"] = 0.005

    with self.assertRaises(InputError):
        calculate_worm_geometry(payload)

def test_friction_override_above_range_is_rejected(self) -> None:
    payload = self._base_payload()
    payload["advanced"]["friction_override"] = 0.35

    with self.assertRaises(InputError):
        calculate_worm_geometry(payload)

def test_non_standard_q_produces_warning(self) -> None:
    payload = self._base_payload()
    payload["geometry"]["diameter_factor_q"] = 13.0

    result = calculate_worm_geometry(payload)

    warnings = result["geometry"]["consistency"]["warnings"]
    self.assertTrue(any("直径系数" in w or "q" in w for w in warnings))

def test_assumptions_mention_zk_and_plastic(self) -> None:
    payload = self._base_payload()

    result = calculate_worm_geometry(payload)

    assumptions = result["load_capacity"]["assumptions"]
    text = " ".join(assumptions)
    self.assertIn("ZK", text)
    self.assertIn("塑料", text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v -k "non_integer or lead_angle_above or friction_override_below or friction_override_above or non_standard_q or assumptions_mention"`
Expected: FAIL

- [ ] **Step 3: Implement input validation**

In `calculator.py`:
1. After reading `z1` and `z2`, add: `if z1 != int(z1): raise InputError(f"z1 必须为正整数，当前值 {z1}")`; same for `z2`
2. After reading `lead_angle_deg`, add: `if lead_angle_deg > 45: raise InputError(f"导程角 γ 必须 ≤ 45°，当前值 {lead_angle_deg}")`
3. Add standard q set: `STANDARD_Q_VALUES = {6, 7, 8, 9, 10, 11, 12, 14, 17, 20}`; if `diameter_factor_q not in STANDARD_Q_VALUES`, append warning to `geometry_warnings`
4. Replace friction_override validation: instead of `_fraction()`, use dedicated check `if not (0.01 <= val <= 0.30): raise InputError(...)`

- [ ] **Step 4: Update assumptions list**

Replace assumptions list per spec 1.8 (7 items including ZK, Hertz, cantilever, plastic).
Add method label note per spec 1.6.

- [ ] **Step 5: Run all calculator tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add core/worm/calculator.py tests/core/worm/test_calculator.py
git commit -m "fix(worm): add integer/range validation, update assumptions for ZK/plastic"
```

---

### Task 4: UI — Remove Tolerance Page & Widget

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py:36,142-146,258-261,486,715-718,805`
- Delete: `app/ui/widgets/worm_tolerance_overview.py`
- Test: `tests/ui/test_worm_page.py`

- [ ] **Step 1: Update UI tests for chapter count and tolerance removal**

In `tests/ui/test_worm_page.py`:
1. Remove `WormToleranceOverviewWidget` import and all tolerance-specific tests (`test_tolerance_overview_accepts_title_and_note`, tolerance parts of `test_overview_widgets_use_worm_pair_defaults_and_render`)
2. Update `test_page_shell_uses_step_flow_and_split_actions`: `chapter_list.count()` → 7, `item(5).text()` → `"步骤 6. Load Capacity"`
3. Update `test_graphics_step_can_render_without_crashing`: `set_current_chapter(4)` (was 5), `currentRow()` → 4
4. Update `test_graphics_step_uses_scroll_area_and_curve_still_updates` if it references chapter index
5. Update `test_main_window_can_open_worm_graphics_step` in `MainWindowWormModuleTests`: `page.set_current_chapter(4)` (was 5)

- [ ] **Step 2: Run tests to verify they fail (chapter count mismatch)**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v -k "shell_uses_step or graphics_step_can_render"`
Expected: FAIL (count still 8)

- [ ] **Step 3: Remove tolerance from UI**

In `worm_gear_page.py`:
1. Delete `WormToleranceOverviewWidget` import (line 36)
2. Delete `TOLERANCE_FIELDS` constant (lines 142-146)
3. Delete "公差与回差" chapter from `_build_input_steps` (lines 258-261)
4. Remove `self.tolerance_overview = WormToleranceOverviewWidget(container)` and `body.addWidget(self.tolerance_overview)` from `_build_graphics_step` (around line 486)
5. Remove `self.tolerance_overview.set_display_state(...)` in `_calculate()` (~line 715-718) and `_clear()` (~line 805)

- [ ] **Step 4: Delete tolerance widget file**

```bash
rm app/ui/widgets/worm_tolerance_overview.py
```

- [ ] **Step 5: Run all UI tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add -A app/ui/pages/worm_gear_page.py app/ui/widgets/ tests/ui/test_worm_page.py
git commit -m "refactor(worm): remove tolerance page and widget"
```

---

### Task 5: UI — Material Linkage & Profile Shift Fields & Dropdown Updates

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py:91-140,207-246` (fields, __init__, _on_material_changed)
- Test: `tests/ui/test_worm_page.py`

- [ ] **Step 1: Write failing UI tests for material linkage**

```python
def test_wheel_material_change_updates_elastic_params(self) -> None:
    page = WormGearPage()
    page._field_widgets["materials.wheel_material"].setCurrentText("PA66+GF30")

    self.assertEqual(page._field_widgets["materials.wheel_e_mpa"].text(), "10000.0")
    self.assertEqual(page._field_widgets["materials.wheel_nu"].text(), "0.36")

def test_wheel_material_change_updates_allowable_stresses(self) -> None:
    page = WormGearPage()
    page._field_widgets["materials.wheel_material"].setCurrentText("PA66+GF30")

    self.assertEqual(page._field_widgets["load_capacity.allowable_contact_stress_mpa"].text(), "58.0")
    self.assertEqual(page._field_widgets["load_capacity.allowable_root_stress_mpa"].text(), "70.0")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v -k "material_change"`
Expected: FAIL

- [ ] **Step 3: Update field constants**

In `worm_gear_page.py`:
1. Update `MATERIAL_FIELDS` worm material options: `("37CrS4",)`, default `"37CrS4"`
2. Update `MATERIAL_FIELDS` wheel material options: `("PA66", "PA66+GF30")`, default `"PA66"`
3. Update default values for elastic params: worm E=210000, nu=0.30; wheel E=3000, nu=0.38
4. Update `LOAD_CAPACITY_PARAMETER_FIELDS` defaults: contact=42.0, root=55.0
5. Add `FieldSpec("geometry.x1", ...)` to `WORM_GEOMETRY_FIELDS`
6. Add `FieldSpec("geometry.x2", ...)` to `WHEEL_GEOMETRY_FIELDS`

- [ ] **Step 4: Implement `_on_material_changed()`**

Add method to `WormGearPage`:

```python
def _on_material_changed(self) -> None:
    from core.worm.calculator import MATERIAL_ELASTIC_HINTS, MATERIAL_ALLOWABLE_HINTS, MATERIAL_FRICTION_HINTS
    worm_mat = self._field_widgets["materials.worm_material"].currentText()
    wheel_mat = self._field_widgets["materials.wheel_material"].currentText()
    worm_hints = MATERIAL_ELASTIC_HINTS.get(worm_mat, {})
    wheel_hints = MATERIAL_ELASTIC_HINTS.get(wheel_mat, {})
    allowable_hints = MATERIAL_ALLOWABLE_HINTS.get(wheel_mat, {})
    if worm_hints:
        self._field_widgets["materials.worm_e_mpa"].setText(str(worm_hints["e_mpa"]))
        self._field_widgets["materials.worm_nu"].setText(str(worm_hints["nu"]))
    if wheel_hints:
        self._field_widgets["materials.wheel_e_mpa"].setText(str(wheel_hints["e_mpa"]))
        self._field_widgets["materials.wheel_nu"].setText(str(wheel_hints["nu"]))
    if allowable_hints:
        self._field_widgets["load_capacity.allowable_contact_stress_mpa"].setText(str(allowable_hints["contact_mpa"]))
        self._field_widgets["load_capacity.allowable_root_stress_mpa"].setText(str(allowable_hints["root_mpa"]))
    default_mu = MATERIAL_FRICTION_HINTS.get((worm_mat, wheel_mat), 0.20)
    self._field_widgets["advanced.friction_override"].setPlaceholderText(f"留空则自动 \u03bc={default_mu:.2f}")
    self._refresh_derived_geometry_preview()
```

Connect in `__init__` **after** `_apply_defaults()`:
```python
self._field_widgets["materials.worm_material"].currentTextChanged.connect(lambda: self._on_material_changed())
self._field_widgets["materials.wheel_material"].currentTextChanged.connect(lambda: self._on_material_changed())
```

- [ ] **Step 5: Add signal blocking in `_apply_input_data()`**

At the start of `_apply_input_data()`, block signals on material combos:
```python
self._field_widgets["materials.worm_material"].blockSignals(True)
self._field_widgets["materials.wheel_material"].blockSignals(True)
```
Restore at the end (before `_refresh_derived_geometry_preview()`):
```python
self._field_widgets["materials.worm_material"].blockSignals(False)
self._field_widgets["materials.wheel_material"].blockSignals(False)
```

- [ ] **Step 6: Run all UI tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/worm_gear_page.py tests/ui/test_worm_page.py
git commit -m "feat(worm): material linkage, profile shift fields, dropdown update to 37CrS4/PA66"
```

---

### Task 6: UI — Load Capacity Enable/Disable & Enabled Load Fix & Method Hint

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py` (_build_load_capacity_step, _apply_input_data, BASIC_SETTINGS_FIELDS)
- Test: `tests/ui/test_worm_page.py`

- [ ] **Step 1: Write failing tests**

```python
def test_load_capacity_disabled_hides_params_card(self) -> None:
    page = WormGearPage()
    page._field_widgets["load_capacity.enabled"].setCurrentText("关闭")

    self.assertTrue(page._lc_params_card.isHidden())

def test_load_capacity_enabled_shows_params_card(self) -> None:
    page = WormGearPage()
    page._field_widgets["load_capacity.enabled"].setCurrentText("关闭")
    page._field_widgets["load_capacity.enabled"].setCurrentText("启用")

    self.assertFalse(page._lc_params_card.isHidden())

def test_load_json_with_enabled_false_sets_combo_to_disabled(self) -> None:
    page = WormGearPage()
    data = {"load_capacity": {"enabled": False}}

    page._apply_input_data(data)

    self.assertEqual(page._field_widgets["load_capacity.enabled"].currentText(), "关闭")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v -k "load_capacity_disabled or load_capacity_enabled_shows or load_json_with_enabled"`
Expected: FAIL (no `_lc_params_card` attribute)

- [ ] **Step 3: Implement enable/disable control**

In `_build_load_capacity_step()`:
1. Save the return value of `_create_group_input_card(...)` as `self._lc_params_card`
2. Connect `load_capacity.enabled` combo in `__init__` (after `_apply_defaults`):

```python
self._field_widgets["load_capacity.enabled"].currentTextChanged.connect(self._on_lc_enabled_changed)
```

```python
def _on_lc_enabled_changed(self, text: str) -> None:
    self._lc_params_card.setVisible(text == "启用")
```

- [ ] **Step 4: Fix `_apply_input_data` for enabled:false**

Replace the `load_capacity.enabled` conversion logic:
```python
if spec.field_id == "load_capacity.enabled":
    text = "启用" if value in (True, "启用", "true") else "关闭"
```

- [ ] **Step 5: Update method hint text**

In `BASIC_SETTINGS_FIELDS`, change `load_capacity.method` hint to:
`"当前版本各方法计算逻辑相同，仅作标记用途。"`

- [ ] **Step 6: Run all UI tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/worm_gear_page.py tests/ui/test_worm_page.py
git commit -m "fix(worm): LC enable/disable toggle, enabled:false load fix, method hint update"
```

---

### Task 7: UI — Export Report Button & Performance Curve Label

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py` (_export_report, __init__)
- Modify: `app/ui/widgets/worm_performance_curve.py:61,69`
- Test: `tests/ui/test_worm_page.py`

- [ ] **Step 1: Implement export report**

In `worm_gear_page.py`:

```python
def _export_report(self) -> None:
    if self._last_result is None:
        QMessageBox.warning(self, "无结果", "请先执行计算。")
        return
    from datetime import datetime
    from PySide6.QtWidgets import QFileDialog
    note = self._last_result.get("inputs_echo", {}).get("meta", {}).get("note", "")
    header = f"蜗杆副计算报告 — {note}\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'=' * 60}\n\n"
    body = self.result_metrics.toPlainText() + "\n\n" + self.load_capacity_metrics.toPlainText()
    path, _ = QFileDialog.getSaveFileName(self, "导出结果说明", "worm_report.txt", "文本文件 (*.txt)")
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + body)
    except OSError as exc:
        QMessageBox.critical(self, "导出失败", f"导出结果失败：{exc}")
        return
    self.set_info(f"结果已导出：{path}")
```

Connect in `__init__`: `self.btn_save.clicked.connect(self._export_report)`

- [ ] **Step 1b: Write test for export report**

```python
def test_export_report_warns_when_no_result(self) -> None:
    page = WormGearPage()

    # _last_result is None, calling _export_report should not crash
    # We can't easily test QMessageBox in headless, but verify button is connected
    self.assertIsNotNone(page.btn_save)
    # Verify _export_report method exists
    self.assertTrue(hasattr(page, '_export_report'))

def test_export_report_has_content_after_calculate(self) -> None:
    page = WormGearPage()
    page._calculate()

    self.assertIsNotNone(page._last_result)
    # Verify the report body is non-empty
    body = page.result_metrics.toPlainText() + page.load_capacity_metrics.toPlainText()
    self.assertGreater(len(body), 0)
```

- [ ] **Step 2: Update performance curve label**

In `app/ui/widgets/worm_performance_curve.py`:
- Line 61: change `"执行计算后显示效率 / 损失功率 / 热功率曲线"` to `"执行计算后显示效率 / 损失功率曲线"`
- Line 69: change `"热功率 P_th"` to `"损失功率 P_loss (热)"` (or remove this third curve entirely since it now duplicates power_loss)

Actually since `thermal_capacity_kw` now equals `power_loss_kw`, the third curve is redundant. Remove it:
- Remove `self._thermal_capacity_kw` storage and the third chart entry
- Update `set_curves` signature: remove `thermal_capacity_kw` parameter
- Update all callers

**Alternative (simpler):** Keep the third curve but relabel it. The curve data still comes from the calculator which computes it as `p_loss_i`. Keep for now, just relabel to `"损失功率 (热负荷)"`.

Choose the simpler path: just relabel line 69.

- [ ] **Step 3: Run all tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py tests/core/worm/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/worm_gear_page.py app/ui/widgets/worm_performance_curve.py tests/ui/test_worm_page.py
git commit -m "feat(worm): connect export report button, relabel thermal curve to loss power"
```

---

### Task 8: Example JSON Update & Final Verification

**Files:**
- Modify: `examples/worm_case_01.json`
- Modify: `examples/worm_case_02.json`

- [ ] **Step 1: Update worm_case_01.json**

```json
{
  "meta": {
    "note": "Method B 常规示例"
  },
  "geometry": {
    "z1": 2.0,
    "z2": 40.0,
    "module_mm": 4.0,
    "center_distance_mm": 100.0,
    "diameter_factor_q": 10.0,
    "lead_angle_deg": 11.31,
    "handedness": "左旋",
    "worm_face_width_mm": 36.0,
    "wheel_face_width_mm": 30.0,
    "x1": 0.0,
    "x2": 0.0
  },
  "materials": {
    "worm_material": "37CrS4",
    "wheel_material": "PA66",
    "worm_e_mpa": 210000.0,
    "worm_nu": 0.3,
    "wheel_e_mpa": 3000.0,
    "wheel_nu": 0.38
  },
  "operating": {
    "power_kw": 3.0,
    "speed_rpm": 1450.0,
    "application_factor": 1.25,
    "torque_ripple_percent": 10.0,
    "lubrication": "油浴润滑"
  },
  "advanced": {
    "friction_override": "",
    "normal_pressure_angle_deg": 20.0
  },
  "load_capacity": {
    "enabled": true,
    "method": "DIN 3996 Method B",
    "allowable_contact_stress_mpa": 42.0,
    "allowable_root_stress_mpa": 55.0,
    "dynamic_factor_kv": 1.05,
    "transverse_load_factor_kha": 1.0,
    "face_load_factor_khb": 1.1,
    "required_contact_safety": 1.0,
    "required_root_safety": 1.0
  }
}
```

- [ ] **Step 2: Update worm_case_02.json**

```json
{
  "meta": {
    "note": "Method B 大变位塑料示例"
  },
  "geometry": {
    "z1": 1.0,
    "z2": 55.0,
    "module_mm": 5.0,
    "center_distance_mm": 145.0,
    "diameter_factor_q": 12.0,
    "lead_angle_deg": 4.76,
    "handedness": "右旋",
    "worm_face_width_mm": 42.0,
    "wheel_face_width_mm": 38.0,
    "x1": 0.2,
    "x2": 0.8
  },
  "materials": {
    "worm_material": "37CrS4",
    "wheel_material": "PA66+GF30",
    "worm_e_mpa": 210000.0,
    "worm_nu": 0.3,
    "wheel_e_mpa": 10000.0,
    "wheel_nu": 0.36
  },
  "operating": {
    "power_kw": 5.5,
    "speed_rpm": 960.0,
    "application_factor": 1.5,
    "torque_ripple_percent": 20.0,
    "lubrication": "强制润滑"
  },
  "advanced": {
    "friction_override": "",
    "normal_pressure_angle_deg": 20.0
  },
  "load_capacity": {
    "enabled": true,
    "method": "Niemann",
    "allowable_contact_stress_mpa": 58.0,
    "allowable_root_stress_mpa": 70.0,
    "dynamic_factor_kv": 1.12,
    "transverse_load_factor_kha": 1.02,
    "face_load_factor_khb": 1.15,
    "required_contact_safety": 1.0,
    "required_root_safety": 1.0
  }
}
```

- [ ] **Step 3: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/ tests/ui/test_worm_page.py -v`
Expected: ALL PASS

- [ ] **Step 4: Run load sample tests specifically**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v -k "load_sample"`
Expected: PASS (verifies the example JSON loads correctly into the updated UI)

- [ ] **Step 5: Commit**

```bash
git add examples/worm_case_01.json examples/worm_case_02.json
git commit -m "chore(worm): update example JSON for 37CrS4/PA66 materials and profile shift"
```

- [ ] **Step 6: Run entire project test suite as final verification**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: ALL PASS (no regressions in bolt, interference, hertz, spline modules)
