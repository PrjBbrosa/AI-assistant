# Worm Module Comprehensive Fix — Design Spec

**Date**: 2026-03-22
**Scope**: 21 review issues + profile shift + material overhaul
**Approach**: Method B (targeted refactor + fix)

## Background

Code review of the worm gear module (DIN 3975) identified 21 issues across calculator logic,
UI linkage, input validation, and documentation. Additionally, user requirements clarified:

- Tooth profile: ZK only (conical grinding wheel generation)
- Worm material: 37CrS4 only (remove 20CrMnTi, 16MnCr5, 42CrMo)
- Wheel material: PA66 and PA66+GF30 only (remove all bronze/aluminum)
- Profile shift coefficients x1/x2 are used in practice (large shift for plastic wheels)

## Decisions Log

| # | Topic | Decision |
|---|-------|----------|
| D1 | Fix scope | All 21 issues |
| D2 | Method options (#10) | Keep 3 options, label as "calculation logic identical, tag only" |
| D3 | Thermal capacity (#1) | `thermal_capacity_kw = power_loss_kw` |
| D4 | Lead angle (#17) | Downstream uses `atan(z1/q)`, user input for comparison only |
| D5 | Tolerance fields (#21) | Remove tolerance page entirely |
| D6 | Profile shift | Add x1/x2 inputs, update all geometry formulas |
| D7 | Materials | 37CrS4 (worm), PA66/PA66+GF30 (wheel) |

---

## Section 1: Calculator Logic (`core/worm/calculator.py`)

### 1.1 Material Tables

Replace all material lookup tables:

```python
MATERIAL_ELASTIC_HINTS = {
    "37CrS4":     {"e_mpa": 210000.0, "nu": 0.30},
    "PA66":       {"e_mpa":   3000.0, "nu": 0.38},
    "PA66+GF30":  {"e_mpa":  10000.0, "nu": 0.36},
}

MATERIAL_ALLOWABLE_HINTS = {
    "PA66":       {"contact_mpa": 42.0, "root_mpa": 55.0},
    "PA66+GF30":  {"contact_mpa": 58.0, "root_mpa": 70.0},
}

MATERIAL_FRICTION_HINTS = {
    ("37CrS4", "PA66"):      0.18,
    ("37CrS4", "PA66+GF30"): 0.22,
}
```

Default friction fallback: `0.20`.
Allowable stress defaults are room-temperature dry-state engineering estimates.

### 1.2 Profile Shift Coefficients

New geometry inputs:
- `geometry.x1` (worm profile shift, default 0.0)
- `geometry.x2` (wheel profile shift, default 0.0)

Formula changes:
- **Reference pitch diameters** (standard definition): `d1 = q * m`, `d2 = z2 * m`.
  **Replaces** the existing `pitch_diameter_wheel_mm = 2*a - d1` derivation (line 115). The old center-distance-based derivation is no longer used.
- Tip diameters: `da1 = d1 + 2m(1 + x1)`, `da2 = d2 + 2m(1 + x2)`
- Root diameters: `df1 = d1 - 2m(1.2 - x1)`, `df2 = d2 - 2m(1.2 - x2)`
- Theoretical working center distance: `a_w = m(q + z2)/2 + (x1 + x2) * m`
- User's `center_distance_mm` compared against `a_w` for consistency warning
- **Force/stress calculations use reference pitch diameters** `d1`, `d2` (not working pitch diameters).
  This is consistent with DIN 3975 convention where tangential force `Ft2 = 2000*T2/d2` references the standard pitch circle.
  The profile shift changes the tooth geometry (tip/root/height) but the reference circle remains `z*m`.
- Tooth height for root stress bending lever arm: `h = m * (2.2 + x1 - x2)`.
  This represents the depth of the worm tooth penetrating into the wheel:
  worm addendum `ha1 = m(1+x1)` + wheel dedendum `hf2 = m(1.2-x2)` = `m(2.2 + x1 - x2)`.
  A larger worm addendum (positive x1) or smaller wheel dedendum (negative x2) increases the lever arm.

### 1.3 Thermal Capacity Fix (#1)

```python
# Before
thermal_capacity_kw = power_kw + power_loss_kw * 0.55
# After
thermal_capacity_kw = power_loss_kw
```

Performance curve: `p_thermal_i = p_loss_i` (was `power_kw * factor + p_loss_i * 0.55`).

`WormPerformanceCurveWidget` curve label should be updated from "热容量" to "损失功率"
if applicable, since the semantic meaning has changed.

### 1.4 Lead Angle Self-Consistency (#17)

```python
lead_angle_calc_rad = math.atan(z1 / diameter_factor_q)
```

All downstream calculations (lead, efficiency, forces) use `lead_angle_calc_rad`.
User input `lead_angle_deg` is retained for comparison only.
Output includes both `lead_angle_input_deg` and `lead_angle_calc_deg`.

### 1.5 `enabled` Flag (#5)

The `enabled` guard must be placed *before* parsing load capacity parameter fields
(`dynamic_factor_kv`, `allowable_contact_stress_mpa`, etc.), so that disabled mode
does not require those fields to be present or valid.

When `load_capacity.enabled == False`:
- Skip all load capacity calculations (early return from that code block)
- Return `{"enabled": false, "status": "未启用", "checks": {}, "forces": {}, "contact": {}, "root": {}, "torque_ripple": {}, "factors": {}, "warnings": [], "assumptions": []}`

### 1.6 Method Label (#10)

Status string appends `"（当前版本各方法计算逻辑相同，仅作标记）"`.
Add to assumptions list.

### 1.7 Input Validation (#11-14)

| Field | Validation | Error type |
|-------|-----------|------------|
| `z1`, `z2` | Must be positive integer (`z != int(z)` → reject) | InputError |
| `lead_angle_deg` | `0 < γ ≤ 45` | InputError |
| `diameter_factor_q` | Not in `{6,7,8,9,10,11,12,14,17,20}` → warning (non-blocking) | geometry_warnings |
| `friction_override` | `0.01 ≤ μ ≤ 0.30` (new dedicated range check) | InputError |

Note: `_fraction()` helper is retained for efficiency clamping (line 147) where it is still correct.

### 1.8 Assumptions Documentation (#2, #3, #4, #15, #16, #18)

Update `assumptions` list to:

```python
[
    "当前结果为 Method B 风格最小工程子集，不是完整 DIN 3996 / ISO/TS 14521。",
    "齿形假设：ZK 型（锥面砂轮展成）。",
    "齿面应力采用线接触 Hertz 近似，等效曲率半径基于分度圆简化（未考虑蜗轮凹面修正）。",
    "接触长度取 min(b1, b2)，未考虑包角影响。",
    "齿根应力采用等效悬臂梁近似。",
    "蜗轮齿顶/齿根高系数与蜗杆相同（含变位修正），未单独处理间隙系数。",
    "钢-塑料配对，许用应力为常温干态工程经验值。",
]
```

### 1.9 Remove Tolerance Reading (#21)

Calculator already does not read `tolerance` section — no change needed.

---

## Section 2: UI Page (`app/ui/pages/worm_gear_page.py`)

### 2.1 Material Linkage (#6, #7, #8)

New method `_on_material_changed()`:
- Connected to `currentTextChanged` of both material combo boxes
- On worm material change: update `worm_e_mpa`, `worm_nu` from HINTS
- On wheel material change: update `wheel_e_mpa`, `wheel_nu`, `allowable_contact_stress_mpa`, `allowable_root_stress_mpa` from HINTS
- Update `friction_override` placeholder to show current pair's default mu (e.g. `"留空则自动 μ=0.18"`)
- Also triggers `_refresh_derived_geometry_preview()`

Material combo always overwrites elastic/allowable fields on change (material switch = new physical object).

**Signal connection timing**: `_on_material_changed()` must be connected *after* `_apply_defaults()` completes,
to avoid cascading updates during initialization. In `_apply_input_data()`, block signals on material combos
(or use a guard flag) while restoring saved values, so that user-customized elastic/allowable values from
saved inputs are not overwritten by the material-change handler.

### 2.2 Load Capacity Enable/Disable (#9)

Connect `load_capacity.enabled` combo's `currentTextChanged`:
- "关闭" → `self._lc_params_card.setVisible(False)`
- "启用" → `self._lc_params_card.setVisible(True)`

Save reference to the Load Capacity parameter card widget as `self._lc_params_card`.

### 2.3 `enabled: false` Load Fix (#20)

Replace current logic in `_apply_input_data`:
```python
if spec.field_id == "load_capacity.enabled":
    text = "启用" if value in (True, "启用", "true") else "关闭"
```

### 2.4 Export Report Button (#19)

Connect `btn_save.clicked` → `_export_report()`:
- If `_last_result is None`: show warning "请先执行计算"
- Otherwise: format result as readable text, save via `QFileDialog.getSaveFileName` as `.txt`
- Report format: reuse the same text as `result_metrics` + `load_capacity_metrics` combined,
  prefixed with a header line containing project note and timestamp

### 2.5 Remove Tolerance Page (#21)

- Delete `TOLERANCE_FIELDS` constant
- Delete "公差与回差" chapter from `_build_input_steps`
- Remove `self.tolerance_overview` (WormToleranceOverviewWidget) from graphics page
- Remove `self.tolerance_overview.set_display_state(...)` calls in `_calculate()` (~line 715) and `_clear()` (~line 805)
- Remove `WormToleranceOverviewWidget` import
- Chapter count: 8 → 7
- Chapter indices shift: graphics page 5→4, Load Capacity 6→5, results 7→6

### 2.6 Profile Shift Fields

Add to geometry field lists:
- `WORM_GEOMETRY_FIELDS`: `FieldSpec("geometry.x1", "蜗杆变位系数 x1", "-", "蜗杆齿形变位系数。", default="0.0")`
- `WHEEL_GEOMETRY_FIELDS`: `FieldSpec("geometry.x2", "蜗轮变位系数 x2", "-", "蜗轮齿形变位系数。塑料蜗轮常用大正变位。", default="0.0")`

Both connected to `_refresh_derived_geometry_preview()` via `textChanged`.

### 2.7 Material Dropdown Options

```python
# Worm material
options=("37CrS4",)
default="37CrS4"

# Wheel material
options=("PA66", "PA66+GF30")
default="PA66"
```

Update default values for elastic params and allowable stresses to match new materials.

### 2.8 Method Hint Update (#10)

`load_capacity.method` hint → `"当前版本各方法计算逻辑相同，仅作标记用途。"`

---

## Section 3: Tests & Examples

### 3.1 Calculator Tests

Update `_base_payload()` to new materials (37CrS4 / PA66) and params.

New test cases:
- Profile shift x1/x2 ≠ 0 → correct tip/root diameters
- Profile shift affects working center distance warning
- `enabled: false` → load_capacity output is stub
- `z1=1.5` → InputError (integer check)
- `lead_angle_deg=60` → InputError (range check)
- `friction_override=0.005` and `0.35` → InputError (range tightened)
- Lead angle: downstream forces use `atan(z1/q)`, not user input
- Thermal capacity equals power loss

### 3.2 UI Tests

- `chapter_list.count()` → 7 (was 8)
- Chapter indices adjusted
- New tests:
  - Wheel material change → `wheel_e_mpa` auto-updates
  - Wheel material change → `allowable_contact_stress_mpa` auto-updates
  - `load_capacity.enabled` = "关闭" → parameter card hidden
  - Load JSON with `enabled: false` → combo shows "关闭"

### 3.3 Example JSON

Both `worm_case_01.json` and `worm_case_02.json`:
- Materials → 37CrS4 / PA66 or PA66+GF30
- Elastic params, allowable stresses, friction updated
- Add `x1`, `x2` fields
- Remove `tolerance` section
- case_02: PA66+GF30 with larger profile shift

### 3.4 Widget Cleanup

- Delete `app/ui/widgets/worm_tolerance_overview.py`
- Remove tolerance widget tests from `test_worm_page.py`

---

## Files Changed

| File | Action |
|------|--------|
| `core/worm/calculator.py` | Major: materials, profile shift, thermal, lead angle, validation, enabled, assumptions |
| `app/ui/pages/worm_gear_page.py` | Major: material linkage, enable/disable, export, tolerance removal, profile shift fields |
| `app/ui/widgets/worm_tolerance_overview.py` | Delete |
| `tests/core/worm/test_calculator.py` | Major: new payload, ~8 new tests |
| `tests/ui/test_worm_page.py` | Major: chapter count, indices, ~4 new tests, tolerance tests removed |
| `examples/worm_case_01.json` | Update: materials, x1/x2, remove tolerance |
| `examples/worm_case_02.json` | Update: materials, x1/x2, remove tolerance |
