# Bolt Report PDF Redesign Spec

## Goal
Replace the current plain-text PDF export with a professionally designed, modern PDF report using reportlab. The report should clearly present inputs, calculation chain, and verdicts in a visually appealing format.

## Technical Approach
- **Library**: reportlab (new dependency, add to `requirements.txt`)
- **New file**: `app/ui/report_pdf.py` — standalone PDF builder, receives `(payload, result)` dicts
- **Integration**: `bolt_page.py:_save_report()` calls `report_pdf.generate_bolt_report(path, payload, result)`
- **Existing**: `report_export.py` unchanged (still handles DOCX/TXT plain-text fallback)

## Color Palette
| Role | Hex | Usage |
|------|-----|-------|
| Primary | `#D97757` | Title bar, section headers, accent lines |
| Background | `#F7F5F2` | Card backgrounds, alternating table rows |
| Pass | `#4CAF50` | Check pass badges and left-border accents |
| Fail | `#E53935` | Check fail badges and left-border accents |
| Text | `#2D2D2D` | Body text |
| Muted | `#888888` | Secondary text, units, footnotes |
| White | `#FFFFFF` | Page background, table even rows |

## Typography
- **Chinese font**: Detect OS — macOS: PingFang SC (.ttc, need subfontIndex); Windows: Microsoft YaHei; fallback: SimSun
  - reportlab requires explicit TTF/TTC file path via `TTFont`. For `.ttc` files use `subfontIndex` param.
- Title: 18pt bold
- Section header: 12pt bold
- Body/table: 9pt regular
- Values: 9pt monospace (Courier) for numeric alignment

## Page Layout (A4 portrait)
- Margins: left=25mm, right=20mm, top=20mm, bottom=20mm
- Page footer on every page: tool name + "仅供工程参考" + page number

## Report Structure

### Page 1: Overview + Inputs

**Header bar** (full width colored rectangle):
- Title: "VDI 2230 螺栓连接校核报告"
- Right-aligned: generation date

**Overall verdict block**:
- Large pass/fail badge (colored rounded rect with white text)
- Subtitle line: calculation_mode + joint_type + check_level + tightening_method

**Key metrics row** (3 mini cards side by side, implemented as single-row Table):
- FM,min (N) | MA,min ~ MA,max (N-m) | FK,residual (N)

**Check summary strip** (single-row Table with colored cells):
- Horizontal row of compact pass/fail pills for each active check key in `result["checks"]`
- Includes: residual_clamp_ok, assembly_von_mises_ok, operating_axial_ok, thermal_loss_ok (if active), fatigue_ok (if active), bearing_pressure_ok (if active), thread_strip_ok (if active)
- `additional_load_ok` shown separately with muted "参考" tag (from `result["references"]`)

**Input summary table** (grouped by category, compact):
| Category | Content |
|----------|---------|
| Fastener | Thread spec (d x p) + grade + Rp0.2 + E_bolt + derived As/d2/d3 |
| Loads | FA_max, FQ_max, FK_seal (if any) |
| Assembly | Tightening method, alpha_A, v, mu_thread, mu_bearing |
| Clamped parts | Part count, total thickness, model type, D_A, materials |
| Stiffness | auto/manual (from `result.stiffness_model.auto_modeled`), delta_s, delta_p (or bolt_stiffness, clamped_stiffness) |

Each category = one row with label cell + value cell. Values concatenated inline, not one-field-per-row.

### Page 2: Calculation Chain (R-steps)

**Stiffness & force ratio** (compact table):
- delta_s, delta_p, phi, phi_n, n

**R1 — Preload**:
- FK_req, FZ (embed loss), F_thermal, FM_min, FM_max
- Left-border color: primary (#D97757)

**R2 — Tightening torque**:
- MA_min, MA_max

**R3 — Residual clamping force** + verdict badge:
- FK_res vs FK_req, pass/fail

**R4 — Assembly stress** + verdict badge:
- sigma_vm_assembly vs nu * Rp0.2

**R5 — Operating stress** + verdict badge:
- sigma_vm_work vs sigma_allow_work

**R7 — Bearing pressure** (if active) + verdict badge:
- p_bearing vs p_G_allow

**R8 — Thread stripping** (if active) + verdict badge:
- strip_safety vs strip_safety_required, critical_side, F_strip_bolt, F_strip_nut

Note: Each R-step card should include the corresponding note string if present (r3_note, r7_note, r8_note).

Each R-step rendered as a mini card: light background rect, left color accent bar (pass=green, fail=red), title line, 1~3 value lines, verdict pill top-right. Implemented as Table with custom TableStyle (BACKGROUND, LINEBEFOREE for left accent).

Page breaks: content flows naturally; use `KeepTogether` to avoid splitting a single R-step card across pages. No hard page breaks.

### Page 3 (conditional): Extended Checks + Recommendations

Only generated when thermal/fatigue checks are active or warnings exist.

**Thermal impact** (if check_level in thermal/fatigue):
- Thermal loss, loss ratio, layer thermals if multi-layer

**R6 — Fatigue** (if check_level == fatigue):
- sigma_a, sigma_a_allow, Goodman factor, surface treatment

**Warnings** (if any):
- Bullet list of warning messages

**Recommendations**:
- Recommendation logic extracted to standalone function `build_bolt_recommendations(result) -> list[str]` in `report_pdf.py` (duplicated from bolt_page logic, operates on result dict only, no UI dependency)

**Scope note**:
- scope_note text in muted color

## Implementation Plan

### Files to create/modify:
1. `app/ui/report_pdf.py` (NEW) — all reportlab PDF generation logic
   - `generate_bolt_report(path: Path, payload: dict, result: dict) -> None`
   - Internal helper functions for header, cards, tables, R-step blocks
   - Font detection utility
2. `app/ui/pages/bolt_page.py` (MODIFY) — in `_save_report()`, intercept `.pdf` suffix BEFORE calling `export_report_lines()` and call `report_pdf.generate_bolt_report()` directly; other suffixes still go through `export_report_lines()`
3. `app/ui/report_export.py` (MODIFY) — minor: default filter to PDF first
4. `requirements.txt` (MODIFY) — add `reportlab`

### Files NOT changed:
- `core/bolt/calculator.py` — no changes to calculation logic
- Other module pages — future work to adopt same template

## Testing Strategy
- Unit test: `tests/ui/test_report_pdf.py` — call `generate_bolt_report()` with example payload/result, verify PDF file created and non-empty
- Manual visual QA: generate PDF from app, inspect layout

## Out of Scope
- Other module reports (interference, hertz, worm) — future work
- DOCX/TXT visual upgrade — keep plain text for now
- Custom logo/company info fields — future enhancement
