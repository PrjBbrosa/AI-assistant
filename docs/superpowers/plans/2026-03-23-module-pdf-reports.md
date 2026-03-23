# Multi-Module PDF Report Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add professional PDF export (matching bolt report style) to interference fit, spline fit, and worm gear modules.

**Architecture:** Extract common PDF primitives (colors, fonts, styles, building blocks) from `report_pdf.py` into `report_pdf_common.py`. Create per-module report generators that reuse these primitives. Wire each UI page to use the new generator with reportlab-optional fallback.

**Tech Stack:** reportlab (optional), PySide6 (fallback PDF), existing `report_export.py` for DOCX/TXT.

---

## File Structure

| File | Role |
|------|------|
| `app/ui/report_pdf_common.py` (create) | Shared colors, fonts, styles, building block functions |
| `app/ui/report_pdf.py` (modify) | Bolt report — import from common instead of defining locally |
| `app/ui/report_pdf_interference.py` (create) | Interference fit report generator |
| `app/ui/report_pdf_spline.py` (create) | Spline fit report generator |
| `app/ui/report_pdf_worm.py` (create) | Worm gear report generator |
| `app/ui/pages/interference_fit_page.py` (modify) | Wire PDF export with reportlab fallback |
| `app/ui/pages/spline_fit_page.py` (modify) | Add `_last_result`/`_last_payload`, wire PDF export |
| `app/ui/pages/worm_gear_page.py` (modify) | Wire PDF export, store `_last_payload` |
| `tests/ui/test_report_pdf_modules.py` (create) | Tests for all 3 new report generators |

---

### Task 1: Extract Common PDF Primitives

**Files:**
- Create: `app/ui/report_pdf_common.py`
- Modify: `app/ui/report_pdf.py`

- [ ] **Step 1: Create `report_pdf_common.py`**

Extract from `report_pdf.py` into the new file:
- Color constants: `C_PRIMARY`, `C_BG`, `C_PASS`, `C_FAIL`, `C_TEXT`, `C_MUTED`, `C_WHITE`, `C_LIGHT_PASS`, `C_LIGHT_FAIL`
- Page constants: `PAGE_W`, `PAGE_H`, `MARGIN_L`, `MARGIN_R`, `MARGIN_T`, `MARGIN_B`, `CONTENT_W`
- Font setup: `FONT_CN`, `FONT_CN_BOLD`, `_FONT_CANDIDATES`, `_register_fonts()`
- Styles: `_build_styles()`
- Helpers: `_fmt()`, `_pass_text()`
- Building blocks: `_header_bar()`, `_verdict_block()`, `_metric_cards()`, `_check_pills()`, `_section_title()`, `_input_table()`, `_rstep_card()`, `_kv_table()`
- Footer factory: `make_footer(tool_name: str)` → returns a footer function with custom tool name
- Doc builder: `build_pdf(path, elements, tool_name)` → creates `BaseDocTemplate` + builds

The `_header_bar` should accept a `title` parameter (currently hardcoded "VDI 2230 螺栓连接校核报告").

- [ ] **Step 2: Update `report_pdf.py` to import from common**

Replace local definitions with imports:
```python
from app.ui.report_pdf_common import (
    C_PRIMARY, C_BG, C_PASS, C_FAIL, C_TEXT, C_MUTED, C_WHITE,
    C_LIGHT_PASS, C_LIGHT_FAIL, CONTENT_W, FONT_CN, FONT_CN_BOLD,
    _register_fonts, _build_styles, _fmt, _pass_text,
    _header_bar, _verdict_block, _metric_cards, _check_pills,
    _section_title, _input_table, _rstep_card, _kv_table, build_pdf,
)
```

Update `generate_bolt_report` to use `build_pdf(path, elements, "VDI 2230 螺栓校核工具")` instead of manually creating `BaseDocTemplate`.

Update `_header_bar` call to pass title string.

- [ ] **Step 3: Run existing bolt PDF tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_report_pdf.py -v`
Expected: All existing tests PASS (no regression).

- [ ] **Step 4: Commit**

```bash
git add app/ui/report_pdf_common.py app/ui/report_pdf.py
git commit -m "refactor: extract common PDF primitives to report_pdf_common.py"
```

---

### Task 2: Interference Fit PDF Report

**Files:**
- Create: `app/ui/report_pdf_interference.py`
- Create: `tests/ui/test_report_pdf_modules.py`
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] **Step 1: Write test for interference fit PDF**

```python
# tests/ui/test_report_pdf_modules.py
import pytest
from pathlib import Path

def _interference_payload():
    return {
        "geometry": {"shaft_d_mm": 50, "hub_D_mm": 80, "fit_length_mm": 40, "shaft_inner_d_mm": 0},
        "materials": {"shaft_E_mpa": 210000, "shaft_Rp02_mpa": 350, "shaft_nu": 0.3,
                      "hub_E_mpa": 210000, "hub_Rp02_mpa": 250, "hub_nu": 0.3},
        "fit": {"delta_min_um": 30, "delta_max_um": 60},
        "roughness": {"shaft_rz_um": 6.3, "hub_rz_um": 6.3},
        "friction": {"mu_longitudinal": 0.12, "mu_circumferential": 0.15},
        "loads": {"torque_nm": 500, "axial_force_n": 5000, "application_factor_ka": 1.25},
    }

def _interference_result():
    return {
        "overall_pass": True,
        "checks": {"torque_ok": True, "axial_ok": True, "combined_ok": True,
                    "gaping_ok": True, "fit_range_ok": True, "shaft_stress_ok": True, "hub_stress_ok": True},
        "pressure_mpa": {"p_min": 30.0, "p_mean": 45.0, "p_max": 60.0, "p_required": 25.0, "p_required_total": 28.0},
        "capacity": {"torque_min_nm": 800, "torque_mean_nm": 1200, "torque_max_nm": 1600,
                     "axial_min_n": 12000, "axial_mean_n": 18000, "axial_max_n": 24000},
        "assembly": {"press_force_min_n": 45000, "press_force_mean_n": 67000, "press_force_max_n": 90000},
        "stress_mpa": {"shaft_vm_min": 50, "shaft_vm_mean": 75, "shaft_vm_max": 100,
                       "hub_vm_min": 60, "hub_vm_mean": 90, "hub_vm_max": 120,
                       "hub_hoop_inner_min": 40, "hub_hoop_inner_mean": 60, "hub_hoop_inner_max": 80},
        "safety": {"torque_sf": 1.6, "axial_sf": 2.4, "combined_sf": 1.4,
                   "shaft_sf": 3.5, "hub_sf": 2.1, "slip_safety_min": 1.4,
                   "stress_safety_min": 2.1, "combined_usage": 0.71,
                   "application_factor_ka": 1.25, "gaping_margin_mpa": 5.0},
        "required": {"p_required_torque_mpa": 15.0, "p_required_axial_mpa": 10.0,
                     "p_required_combined_mpa": 20.0, "p_required_gap_mpa": 5.0,
                     "p_required_mpa": 25.0, "p_required_total_mpa": 28.0,
                     "delta_required_um": 22.0, "delta_required_effective_um": 18.0},
        "roughness": {"shaft_rz_um": 6.3, "hub_rz_um": 6.3, "smoothing_factor": 0.4,
                      "subsidence_um": 5.04, "delta_input_min_um": 30, "delta_input_max_um": 60,
                      "delta_input_mean_um": 45, "delta_effective_min_um": 24.96,
                      "delta_effective_mean_um": 39.96, "delta_effective_max_um": 54.96},
        "additional_pressure_mpa": {"p_radial": 0, "p_bending": 0, "p_gap": 3.0},
        "model": {"type": "cylindrical_interference_solid_shaft", "shaft_type": "solid_shaft"},
        "derived": {"shaft_inner_d_mm": 0},
        "messages": [],
    }

class TestInterferencePdfReport:
    def test_creates_nonempty_pdf(self, tmp_path):
        from app.ui.report_pdf_interference import generate_interference_report
        out = tmp_path / "interference_report.pdf"
        generate_interference_report(out, _interference_payload(), _interference_result())
        assert out.exists()
        assert out.stat().st_size > 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_report_pdf_modules.py::TestInterferencePdfReport -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement `report_pdf_interference.py`**

Create `app/ui/report_pdf_interference.py` with `generate_interference_report(path, payload, result)`.

Report structure:
1. **Header bar**: "DIN 7190 过盈配合校核报告"
2. **Verdict block**: overall_pass + subtitle (shaft_type + model)
3. **Metric cards**: p_min/p_max, T_capacity_min, S_combined
4. **Check pills**: all 7 checks from CHECK_LABELS
5. **Input summary**: geometry, materials, fit tolerances, friction, loads
6. **Pressure section**: p_min/mean/max, p_required, roughness subsidence
7. **Capacity cards**: torque capacity, axial capacity, press force
8. **Safety cards**: slip safety, stress safety (shaft/hub), combined usage
9. **Stress section**: shaft VM, hub VM, hub hoop
10. **Warnings**: from messages list
11. **Recommendations**: built from checks

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_report_pdf_modules.py::TestInterferencePdfReport -v`
Expected: PASS

- [ ] **Step 5: Wire UI page**

Modify `interference_fit_page.py`:
- Change `_save_report` to use rich PDF export pattern (same as bolt_page):
  - `.pdf` → try `report_pdf_interference.generate_interference_report`, fallback to `export_report_lines`
  - `.docx` / `.txt` → use existing `_build_report_lines()` path
- Update file dialog filter to include PDF/DOCX/TXT

- [ ] **Step 6: Run all tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/report_pdf_interference.py app/ui/pages/interference_fit_page.py tests/ui/test_report_pdf_modules.py
git commit -m "feat: add professional PDF report for interference fit module"
```

---

### Task 3: Spline Fit PDF Report

**Files:**
- Create: `app/ui/report_pdf_spline.py`
- Modify: `app/ui/pages/spline_fit_page.py`
- Modify: `tests/ui/test_report_pdf_modules.py`

- [ ] **Step 1: Write test for spline fit PDF**

Add to `tests/ui/test_report_pdf_modules.py`:
```python
class TestSplinePdfReport:
    def test_spline_only_report(self, tmp_path):
        from app.ui.report_pdf_spline import generate_spline_report
        # ... spline_only mode payload + result
        out = tmp_path / "spline_report.pdf"
        generate_spline_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000

    def test_combined_mode_report(self, tmp_path):
        from app.ui.report_pdf_spline import generate_spline_report
        # ... combined mode payload + result (with scenario_b)
        out = tmp_path / "spline_combined_report.pdf"
        generate_spline_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement `report_pdf_spline.py`**

Create `app/ui/report_pdf_spline.py` with `generate_spline_report(path, payload, result)`.

Report structure:
1. **Header bar**: "花键连接校核报告"
2. **Verdict block**: overall_pass + mode (spline_only / combined) + verdict_level
3. **Metric cards**: flank_pressure, flank_safety, (if combined: p_min)
4. **Scenario A section**: geometry, flank pressure vs allowable, safety factor card
5. **Scenario B section** (if combined): pressure, capacity, safety — reuse interference building blocks
6. **Input summary**: spline geometry, loads, (smooth fit params if combined)
7. **Warnings/messages**
8. **Recommendations**

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Wire UI page**

Modify `spline_fit_page.py`:
- Add `self._last_result` and `self._last_payload` storage in `_on_calculate`
- Add export button in `__init__` (similar to other pages)
- Add `_save_report` method with rich PDF / fallback
- Add `_build_report_lines` for text fallback

- [ ] **Step 6: Run all tests**

- [ ] **Step 7: Commit**

```bash
git add app/ui/report_pdf_spline.py app/ui/pages/spline_fit_page.py tests/ui/test_report_pdf_modules.py
git commit -m "feat: add professional PDF report for spline fit module"
```

---

### Task 4: Worm Gear PDF Report

**Files:**
- Create: `app/ui/report_pdf_worm.py`
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `tests/ui/test_report_pdf_modules.py`

- [ ] **Step 1: Write test for worm gear PDF**

Add to `tests/ui/test_report_pdf_modules.py`:
```python
class TestWormPdfReport:
    def test_geometry_only_report(self, tmp_path):
        from app.ui.report_pdf_worm import generate_worm_report
        # ... result without load_capacity enabled
        out = tmp_path / "worm_report.pdf"
        generate_worm_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000

    def test_with_load_capacity_report(self, tmp_path):
        from app.ui.report_pdf_worm import generate_worm_report
        # ... result with load_capacity enabled
        out = tmp_path / "worm_lc_report.pdf"
        generate_worm_report(out, payload, result)
        assert out.exists() and out.stat().st_size > 1000
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement `report_pdf_worm.py`**

Create `app/ui/report_pdf_worm.py` with `generate_worm_report(path, payload, result)`.

Report structure:
1. **Header bar**: "DIN 3975 蜗杆副设计报告"
2. **Verdict block**: if load_capacity enabled → overall pass/fail; else → "几何设计" info badge
3. **Metric cards**: ratio, center_distance, efficiency, output_torque
4. **Geometry section**: worm dimensions table, wheel dimensions table, mesh dimensions
5. **Performance section**: power, torque, efficiency, friction, thermal capacity
6. **Load capacity section** (if enabled):
   - Check pills: geometry_consistent, contact_ok, root_ok
   - Forces card: tangential, axial, radial, normal
   - Contact stress card: sigma_hm vs allowable, safety
   - Root stress card: sigma_f vs allowable, safety
   - Factors table: KA, KV, KHα, KHβ
7. **Warnings**: from load_capacity.warnings + geometry.consistency.warnings
8. **Assumptions**: from load_capacity.assumptions

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Wire UI page**

Modify `worm_gear_page.py`:
- Store `self._last_payload = payload` in `_calculate`
- Update `_export_report` to support PDF/DOCX/TXT with rich PDF:
  - Change file dialog filter from txt-only to PDF/DOCX/TXT
  - `.pdf` → try `report_pdf_worm.generate_worm_report`, fallback to text PDF
  - `.docx` / `.txt` → existing text export logic
- Add `_build_report_lines` for text fallback

- [ ] **Step 6: Run all tests**

- [ ] **Step 7: Commit**

```bash
git add app/ui/report_pdf_worm.py app/ui/pages/worm_gear_page.py tests/ui/test_report_pdf_modules.py
git commit -m "feat: add professional PDF report for worm gear module"
```

---

### Task 5: Final Verification & Cleanup

- [ ] **Step 1: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All PASS including bolt regression tests

- [ ] **Step 2: Manual smoke test**

Run: `python3 app/main.py`
- Open each module, run a calculation, export PDF
- Verify PDF has correct styling, Chinese fonts, page layout

- [ ] **Step 3: Final commit if needed**
