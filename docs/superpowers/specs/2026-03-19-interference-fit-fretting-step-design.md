# Interference-Fit Fretting Step Design Spec

## Goal
Add a formal "Step 5: Fretting Risk Assessment" enhancement inside the interference-fit module. The feature should assess fretting risk for shaft-hub interference fits, present a risk level and engineering recommendations, and remain separate from the base DIN 7190 pass/fail verdict.

## Problem Statement
The current interference-fit module already contains a lightweight `repeated_load` block, but it is not yet a real chapter-level step:

- It is exposed as an advanced toggle instead of a named workflow step.
- It returns only a narrow set of fields (`applicable`, `max_transferable_torque_nm`, `fretting_risk`).
- It does not explain *why* risk is high or low in an engineering-friendly way.
- It does not provide a formal risk level (`low/medium/high/not_applicable`).
- It does not feel like a traceable, reportable "Step 5" result.

We want to promote fretting from a hidden advanced hint into a first-class interference-fit enhancement while keeping scope controlled.

## Scope

### In Scope
- Add a dedicated fretting assessment step within the existing interference-fit page.
- Reuse current interference-fit calculation results as primary inputs.
- Add a small number of user-controlled fretting inputs.
- Compute:
  - applicability
  - risk level
  - main drivers
  - recommendations
  - confidence / assumption notes
- Show the fretting result in the UI and exported report.
- Keep fretting outside the base `overall_pass` verdict.

### Out of Scope
- Independent, reusable fretting module for bolts/splines/keys/other joints.
- Wear life prediction or accumulated damage model.
- Full thermomechanical operating-temperature coupling.
- Centrifugal-force / speed coupling.
- Stepped shaft / stepped hub geometry.
- Full hollow-shaft model expansion in this spec.
- Directly making fretting a mandatory pass/fail gate for the DIN 7190 base result.

## Design Principles
- **Controlled scope:** This is a Step 5 enhancement, not a new multiphysics solver.
- **Engineer-readable output:** The user should understand the risk level and the main causes immediately.
- **Traceable assumptions:** If the method is not applicable, the tool must say so clearly.
- **No hidden verdict coupling:** Fretting remains informative and prominent, but not part of `overall_pass`.
- **Progressive enhancement:** The design should reuse and evolve the existing `repeated_load` logic rather than replace it wholesale.

## Recommended Approach
Use an **enhanced rule-based fretting assessment** built on top of the current `repeated_load` block.

### Why this approach
- Faster and safer than implementing a heavy new analytical model.
- Reuses existing core outputs:
  - `torque_design_nm`
  - `torque_min_nm`
  - `combined_sf`
  - `p_min`
  - `l_fit / d`
  - modulus match
  - bending applicability gate
- Produces much more useful output than the current boolean-like warning.
- Fits the user's priority: fretting matters, but temperature/speed can stay lower priority.

## User Experience

### Page Placement
Inside `InterferenceFitPage`, introduce a formal step/chapter:

1. 校核目标
2. 几何与过盈
3. 材料参数
4. 载荷与附加载荷
5. 摩擦与粗糙度
6. 装配流程
7. **Fretting 风险评估**
8. 压入力曲线图
9. 校核结果与消息

This new chapter should replace the vague "高级校核" framing with a more explicit engineering purpose.

### User-Facing Behavior
The Step 5 chapter should let the user:
- enable/disable fretting assessment
- select a simple load spectrum
- select duty severity
- select surface condition
- select component importance

Then the result page should show:
- applicability
- risk level
- driver breakdown
- recommendations
- assumptions note

## Inputs

### Reused Inputs / Derived Values
The fretting step should reuse existing interference-fit result/context:
- `loads.torque_required_nm`
- `loads.axial_force_required_n`
- `loads.bending_moment_required_nm`
- `loads.application_factor_ka`
- `geometry.shaft_d_mm`
- `geometry.fit_length_mm`
- `friction.mu_torque`
- `roughness.*`
- `pressure_mpa.p_min`
- `capacity.torque_min_nm`
- `safety.combined_sf`
- repeated-load applicability gate values:
  - `length_ratio_l_over_d`
  - `modulus_ratio`
  - bending presence

### New User Inputs
Add a new `fretting` section to the payload with these first-pass fields:

- `fretting.mode`
  - values: `off`, `on`
  - default: `off`
- `fretting.load_spectrum`
  - values: `steady`, `pulsating`, `reversing`
  - default: `pulsating`
- `fretting.duty_severity`
  - values: `light`, `medium`, `heavy`
  - default: `medium`
- `fretting.surface_condition`
  - values: `dry`, `oiled`, `coated`
  - default: `dry`
- `fretting.importance_level`
  - values: `general`, `important`, `critical`
  - default: `important`

These are intentionally categorical inputs to keep the first implementation understandable and controllable.

## Output Model
Add a top-level result block:

```python
"fretting": {
    "enabled": bool,
    "applicable": bool,
    "risk_level": "low" | "medium" | "high" | "not_applicable",
    "risk_score": float,
    "max_score": float,
    "drivers": [
        {"key": str, "label": str, "severity": "low|medium|high", "detail": str}
    ],
    "recommendations": [str],
    "confidence": "low" | "medium" | "high",
    "notes": [str],
}
```

### Semantics
- `risk_level` is the primary user-visible outcome.
- `risk_score` is an internal traceable score used to derive the level.
- `drivers` explain *why* the level was assigned.
- `recommendations` are short engineering actions.
- `confidence` reflects how well the current assumptions fit the simplified method.
- `notes` record applicability and assumption warnings.

## Risk Logic

### Applicability Gate
The fretting step should first evaluate whether the simplified method is applicable.

The first-pass rules should reuse the current gate:
- `l_fit / d > 0.25`
- elastic modulus mismatch small enough
- no rotating bending in the simplified method

If the method is not applicable:
- `risk_level = "not_applicable"`
- `applicable = False`
- no misleading "safe" verdict should be shown
- the UI should show the reason clearly

### Scoring Model
Use a rule-based additive score. This is simpler and more maintainable than a pseudo-precise formula.

Suggested score contributors:

1. **Slip reserve / torque reserve**
- Lower reserve -> higher score
- Primary indicator

2. **Combined loading margin**
- Lower `combined_sf` -> higher score

3. **Load spectrum**
- `steady` < `pulsating` < `reversing`

4. **Duty severity**
- `light` < `medium` < `heavy`

5. **Surface condition**
- `coated` < `oiled` < `dry`

6. **Importance level**
- `general` < `important` < `critical`

### Risk Levels
Map score to levels:
- `low`
- `medium`
- `high`

Exact thresholds should be chosen during implementation, but the model must satisfy:
- worsening load spectrum increases risk
- lower reserve increases risk
- harsher surface condition increases risk
- higher importance level increases recommended conservatism

## Driver Breakdown
Each non-trivial result should list the main drivers in plain language, such as:

- "扭矩储备偏低，循环微滑移风险升高"
- "载荷谱为 reversing，较 steady/pulsating 更易触发 fretting"
- "当前表面状态为 dry，接触副保护能力较弱"
- "本结果基于简化适用条件，可信度受限"

This should make the step useful for engineering action, not just display.

## Recommendations
Recommendations should be generated from the driver set, for example:

- increase minimum interference
- increase fit length
- improve surface condition / lubrication
- improve coating / anti-fretting surface treatment
- reduce cyclic torque fluctuation
- reduce combined loading
- treat result as low-confidence when assumptions are violated

The recommendation engine should be deterministic and easy to test.

## Interaction with Existing Repeated-Load Block

### Core Strategy
Do **not** build a second unrelated algorithm.

Instead:
- preserve the useful parts of the current `repeated_load` block
- refactor them into a fretting-oriented core helper
- let Step 5 consume that helper and produce richer output

### UI Strategy
Replace the current "高级校核" wording with a proper Step 5 chapter.

Possible migration:
- old internal field: `advanced.repeated_load_mode`
- new user-facing field: `fretting.mode`

Compatibility may be preserved by reading legacy saved input and mapping it to the new field during load.

## Verdict Relationship
Fretting must remain **outside** the base DIN verdict:

- `overall_pass` remains unchanged
- fretting result must be visually prominent but separate
- report text must explicitly say:
  - "Fretting risk assessment is an enhancement result"
  - "It does not change the base pass/fail result"

This is a hard requirement from the approved design direction.

## UI Design Details

### Step 5 Input Chapter
Add a new chapter with:
- fretting enable/disable
- load spectrum
- duty severity
- surface condition
- importance level

Each field should have:
- hint
- tooltip
- beginner guidance

### Result Presentation
In the result chapter:
- add a dedicated fretting card
- show:
  - applicability badge
  - risk-level badge
  - driver list
  - recommendations
  - confidence note

The visual hierarchy should ensure users do not miss high fretting risk even though it is not part of `overall_pass`.

### Report Presentation
Add a dedicated report section:
- `Step 5 Fretting 风险评估`
- applicability
- risk level
- reasons
- recommendations
- assumption note

## Data Compatibility

### Backward Compatibility
- Existing saved inputs without fretting fields must still load.
- Existing `advanced.repeated_load_mode` data should map cleanly to the new fretting enable state if present.

### Forward Compatibility
Structure the output so future versions can add:
- more contact geometries
- hollow-shaft support
- service-temperature coupling
- richer surface-treatment logic

without breaking the first-pass shape too much.

## Files Likely Affected

### Core
- `core/interference/calculator.py`
  - integrate fretting input parsing and output block
  - refactor current repeated-load logic into richer Step 5 result

### UI
- `app/ui/pages/interference_fit_page.py`
  - replace/add chapter
  - payload mapping
  - result rendering
  - report rendering
  - saved input compatibility handling

### Tests
- `tests/core/interference/test_calculator.py`
- `tests/ui/test_interference_page.py`

### Docs / Examples
- update interference-fit review / design docs as needed
- update sample files if we want one fretting-enabled example

## Testing Strategy

### Core Tests
- fretting disabled -> no misleading active result
- applicable case -> produces `low/medium/high`
- non-applicable case -> produces `not_applicable`
- worse load spectrum raises risk
- lower reserve raises risk
- harsher surface condition raises risk
- fretting does not alter `overall_pass`

### UI Tests
- Step 5 fields appear in the page
- payload includes `fretting.*`
- results and report include fretting section
- legacy saved input with old advanced flag can still load

## Complexity Assessment

### Recommended Complexity Label
**Medium**

### Why it is not low
- Requires both core and UI restructuring
- Needs a new result model, not just a warning string
- Needs migration from the current advanced repeated-load block

### Why it is not high
- Reuses current interference-fit model and current repeated-load logic
- Avoids life-prediction and full multiphysics coupling
- Uses a rule-based risk engine rather than a heavy analytical model

Expected implementation effort: roughly **1.5 to 3 focused engineering days**, depending on how much report/UI polish we include.

## Open Questions Resolved
- Scope: inside interference-fit only
- Result type: risk level + recommendations
- Verdict coupling: not part of `overall_pass`

## Non-Goals to Re-emphasize
- No fretting life model
- No standalone fretting module
- No mandatory fail gate
- No full service-temperature / centrifugal coupling in this step
