# Interference Fit DIN 7190 Core Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the current cylindrical interference-fit module to a DIN 7190 core-enhanced version with application factor, radial-force/bending-induced gaping checks, min/mean/max result sets, and aligned UI/report wording.

**Architecture:** Keep the existing page shell and press-force curve widget, extend the calculator result model first, then adapt the UI to the new inputs and outputs. Preserve backward compatibility for saved inputs by mapping legacy `mu_static` into the new torque/axial friction fields.

**Tech Stack:** Python 3.12, PySide6, `unittest`

---

### Task 1: Extend calculator tests for DIN 7190 core fields

**Files:**
- Modify: `tests/core/interference/test_calculator.py`
- Modify: `core/interference/calculator.py`

**Step 1: Write the failing tests**

Add tests for:

```python
def test_application_factor_increases_required_interference(self) -> None:
    base = make_case()
    result_base = calculate_interference_fit(base)
    factored = make_case()
    factored["loads"]["application_factor_ka"] = 1.5
    result_factored = calculate_interference_fit(factored)
    assert result_factored["required"]["delta_required_um"] > result_base["required"]["delta_required_um"]

def test_gaping_check_fails_when_radial_and_bending_loads_are_high(self) -> None:
    data = make_case()
    data["loads"]["radial_force_required_n"] = 18000.0
    data["loads"]["bending_moment_required_nm"] = 450.0
    result = calculate_interference_fit(data)
    assert result["checks"]["gaping_ok"] is False
    assert result["additional_pressure_mpa"]["p_gap"] > result["pressure_mpa"]["p_min"]

def test_legacy_mu_static_is_still_supported(self) -> None:
    data = make_case()
    data["friction"] = {"mu_static": 0.14, "mu_assembly": 0.12}
    result = calculate_interference_fit(data)
    assert result["capacity"]["torque_min_nm"] > 0
    assert result["capacity"]["axial_min_n"] > 0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: FAIL because the new fields and result keys do not exist yet.

**Step 3: Write minimal implementation**

Extend calculator input parsing and result structure to support:

- `loads.application_factor_ka`
- `loads.radial_force_required_n`
- `loads.bending_moment_required_nm`
- legacy `mu_static` fallback
- `checks.gaping_ok`
- `additional_pressure_mpa`
- min/mean/max grouped outputs

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: PASS for the new tests and legacy tests.

**Step 5: Commit**

```bash
git add tests/core/interference/test_calculator.py core/interference/calculator.py
git commit -m "feat: extend interference calculator with DIN 7190 core checks"
```

### Task 2: Refactor calculator outputs to min/mean/max sets

**Files:**
- Modify: `core/interference/calculator.py`
- Modify: `tests/core/interference/test_calculator.py`

**Step 1: Write the failing test**

Add a test like:

```python
def test_result_sets_are_reported_for_min_mean_max_interference(self) -> None:
    result = calculate_interference_fit(make_case())
    pressure = result["pressure_mpa"]
    assert pressure["p_min"] < pressure["p_mean"] < pressure["p_max"]
    capacity = result["capacity"]
    assert capacity["torque_min_nm"] < capacity["torque_mean_nm"] < capacity["torque_max_nm"]
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: FAIL because mean results are not yet emitted consistently.

**Step 3: Write minimal implementation**

Compute and return min/mean/max values for:

- pressure
- torque capacity
- axial capacity
- press force
- shaft stress
- hub stress

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: PASS with monotonic result ordering.

**Step 5: Commit**

```bash
git add tests/core/interference/test_calculator.py core/interference/calculator.py
git commit -m "feat: add mean result set to interference calculator"
```

### Task 3: Update interference-fit UI inputs and badges

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `examples/interference_case_01.json`
- Modify: `examples/interference_case_02.json`

**Step 1: Write the failing test**

If practical, add a focused UI/state test for payload building; otherwise write a calculator-facing regression test that uses the new example schema.

Example assertion target:

```python
payload = page._build_payload()
assert payload["loads"]["application_factor_ka"] == 1.2
assert "process" not in payload
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: FAIL or missing-field behavior until UI defaults/examples are updated.

**Step 3: Write minimal implementation**

Change the chapter structure to:

- 校核目标
- 几何与过盈
- 材料参数
- 载荷与附加载荷
- 摩擦与粗糙度

Remove:

- `process.assembly_method`
- `process.temp_delta_c`

Add:

- `loads.application_factor_ka`
- `loads.radial_force_required_n`
- `loads.bending_moment_required_nm`
- `friction.mu_torque`
- `friction.mu_axial`

Update badges to:

- `torque_ok`
- `axial_ok`
- `gaping_ok`
- `fit_range_ok`
- `shaft_stress_ok`
- `hub_stress_ok`

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: PASS and example files load without calculator input errors.

**Step 5: Commit**

```bash
git add app/ui/pages/interference_fit_page.py examples/interference_case_01.json examples/interference_case_02.json
git commit -m "feat: align interference UI with DIN 7190 core flow"
```

### Task 4: Rewrite results, messages, and export report

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

**Step 1: Write the failing test**

Add a focused assertion around report lines or result rendering helpers if practical, for example:

```python
lines = page._build_report_lines()
assert any("p_r / p_b / p_gap" in line for line in lines)
assert any("最小/平均/最大" in line for line in lines)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: FAIL or report content missing the new values.

**Step 3: Write minimal implementation**

Update result rendering to show:

- min/mean/max pressure, torque, axial capacity, press force
- `p_r`, `p_b`, `p_gap`
- `delta_required`
- gaping warnings first when applicable

Update report text to remove “首版仅记录工艺项” language and replace it with the current supported scope.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.core.interference.test_calculator -v`

Expected: PASS and exported report text matches the new result model.

**Step 5: Commit**

```bash
git add app/ui/pages/interference_fit_page.py
git commit -m "feat: refresh interference results and report wording"
```

### Task 5: Full verification

**Files:**
- Modify: `docs/plans/2026-03-08-interference-fit-din7190-core-design.md`
- Modify: `docs/plans/2026-03-08-interference-fit-din7190-core-plan.md`

**Step 1: Run targeted tests**

Run:

```bash
python3 -m unittest tests.core.interference.test_calculator -v
```

Expected: PASS

**Step 2: Run broader regression tests**

Run:

```bash
python3 -m unittest tests.core.interference.test_calculator tests.core.hertz.test_calculator tests.core.worm.test_calculator tests.ui.test_input_condition_store -v
```

Expected: PASS

**Step 3: Review files for consistency**

Verify:

- no remaining UI references to deleted process-only fields
- legacy `mu_static` compatibility is documented in code comments or messages where needed
- design doc scope matches delivered behavior

**Step 4: Commit**

```bash
git add docs/plans/2026-03-08-interference-fit-din7190-core-design.md docs/plans/2026-03-08-interference-fit-din7190-core-plan.md
git commit -m "docs: capture DIN 7190 interference enhancement plan"
```

