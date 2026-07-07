# Mechanical Design Calculator — Coding Standards

## Language Rules
- UI text, error messages, labels: Chinese
- Code, variable names, comments (when explaining formulas): English variable names, Chinese explanations OK
- NO Unicode smart quotes (U+201C `"` / U+201D `"`) — only ASCII `"` and `'`

## Architecture
- `core/` = pure Python, ZERO Qt imports, dict-in dict-out
- `app/ui/pages/` = PySide6 UI, uses FieldSpec pattern
- Never import from `app/` inside `core/`
- Calculator functions: `calculate_xxx(data: dict) -> dict`

## Naming
- Variables follow engineering standard notation: `fm_min`, `phi_n`, `sigma_ax`, `d_a1`, `p_flank`
- MAP constants for dropdown translation: `TIGHTENING_METHOD_MAP`, `SURFACE_CLASS_MAP`, etc.
- Field IDs: `snake_case` matching calculator keys
- Test functions: `test_<what>_<condition>_<expected>`

## Units (internal)
- Force: N
- Length: mm
- Stress: MPa
- Torque: N*m (internal N*mm acceptable)
- Angle: radians (UI displays degrees)

## Input Validation
- Use `_require(data, key, label)` and `_positive(value, label)`
- Raise `InputError` with descriptive Chinese message
- Validate at calculator entry point, not deep inside formulas

## UI Styling
- Manual input: `SubCard` object name
- Auto-filled (lookup/dropdown/material): `AutoCalcCard` object name
  - Field-row card background is transparent under `surfaceRole="inputField"`
  - Visual distinction lives on the inner input controls: read-only QLineEdit warm gray fill with text `#4A4135` and helper `#6B5D4A`
  - Non-input AutoCalcCard containers may keep warm gray `#ECE8DF` and border `#C9BFB0`
  - QLineEdit: `setReadOnly(True)`
  - QComboBox: `setEnabled(False)`
  - Switch via: `setObjectName()` + `unpolish/polish`
- Theme colors: bg `#F7F5F2`, primary `#D97757`, selection `#EED9CF`

## Testing
- Headless: `QT_QPA_PLATFORM=offscreen`
- Visibility: use `isHidden()` not `isVisible()`
- Every `tests/` subdirectory needs `__init__.py`
- Floating point: `pytest.approx(expected, rel=1e-3)`
- Base input pattern: `_base_input()` + override per test
- `data.setdefault("options", {})` when options may be absent
