# Batch 1: 连接形式接入计算 + 热膨胀材料参数 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `joint_type`（螺纹孔/通孔）实际影响 R7 支承面压强校核和输出说明，同时将热膨胀系数从硬编码钢升级为用户可选材料。

**Architecture:** Calculator 读取 `options.joint_type`，在 R7 输出中标注连接形式差异（螺纹孔只校核头端、通孔两侧均需满足）。热膨胀系数从 `operating.alpha_bolt` / `operating.alpha_parts` 读取，UI 提供材料下拉预设联动。两项改动均不改变已有公式结构，仅扩展参数来源和输出信息。

**Tech Stack:** Python 3.12, PySide6, pytest

**Existing test runner:** `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`

**Existing test file:** `tests/core/bolt/test_calculator.py` — contains `_base_input()` helper, `TestPhiNHardBlock`, `TestBearingPressureR7`, `TestCalculationMode` classes.

**Key conventions:**
- Calculator signature: `calculate_vdi2230_core(data: dict) -> dict`, pure Python, no Qt
- UI fields: `FieldSpec(field_id, label, unit, hint, mapping, widget_type, options, default, disabled)`
- `mapping=None` → UI-only (saved in snapshot but NOT sent to calculator)
- `mapping=("section", "key")` → included in calculator payload
- Choice fields with `mapping` pass their text value as-is into payload
- `_build_payload()` in bolt_page.py constructs the dict; also manually injects `options.calculation_mode` and `options.check_level`
- Auto-filled fields use `_AUTO_FILLED_FIELDS` set, `AutoCalcCard` ObjectName style, and signal-driven fill methods
- Thermal fields visibility controlled by `THERMAL_FIELD_IDS` set + `_apply_check_level_visibility()`

---

## Chunk 1: Calculator — joint_type 接入

### Task 1: Calculator 读取 joint_type 并在输出中回显

**Files:**
- Modify: `core/bolt/calculator.py:74-92` (options parsing area)
- Modify: `core/bolt/calculator.py:315-370` (return dict)
- Test: `tests/core/bolt/test_calculator.py`

**Context:** Currently `options` dict only has `check_level` and `calculation_mode`. We add `joint_type` with values `"tapped"` (螺纹孔, default) or `"through"` (通孔). The calculator validates the value, stores it, and echoes it in output.

- [ ] **Step 1: Write failing test — joint_type default is tapped**

In `tests/core/bolt/test_calculator.py`, add a new class after `TestCalculationMode`:

```python
class TestJointType:
    def test_default_joint_type_is_tapped(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["joint_type"] == "tapped"

    def test_through_joint_type_echoed(self):
        data = _base_input()
        data.setdefault("options", {})["joint_type"] = "through"
        result = calculate_vdi2230_core(data)
        assert result["joint_type"] == "through"

    def test_invalid_joint_type_raises(self):
        data = _base_input()
        data.setdefault("options", {})["joint_type"] = "invalid"
        with pytest.raises(InputError, match="joint_type"):
            calculate_vdi2230_core(data)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestJointType -v`
Expected: 3 FAILED (KeyError on `result["joint_type"]`)

- [ ] **Step 3: Implement joint_type parsing and echo**

In `core/bolt/calculator.py`, after line 92 (`calculation_mode` validation), add:

```python
    joint_type = str(options.get("joint_type", "tapped"))
    if joint_type not in {"tapped", "through"}:
        raise InputError(f"options.joint_type 无效：{joint_type}，应为 tapped 或 through")
```

In the return dict (after `"calculation_mode": calculation_mode,`), add:

```python
        "joint_type": joint_type,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestJointType -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): read joint_type from options and echo in result"
```

---

### Task 2: R7 输出区分连接形式 — note 字段

**Files:**
- Modify: `core/bolt/calculator.py:275-313` (R7 section + stresses_out)
- Test: `tests/core/bolt/test_calculator.py`

**Context:** R7 bearing pressure check currently calculates `p_bearing = fm_max / a_bearing`. The formula itself is the same for both joint types (we use one set of bearing dimensions). The difference is the **meaning**: for tapped joints, this is only the bolt-head side; for through joints, both sides must satisfy. We add a `r7_note` field to communicate this.

- [ ] **Step 1: Write failing tests**

Add to `TestBearingPressureR7` class:

```python
    def test_r7_tapped_note_says_head_side(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        # default joint_type = tapped
        result = calculate_vdi2230_core(data)
        assert "螺栓头端" in result["r7_note"]
        assert "螺母端" not in result["r7_note"]

    def test_r7_through_note_says_both_sides(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        data.setdefault("options", {})["joint_type"] = "through"
        result = calculate_vdi2230_core(data)
        assert "螺母端" in result["r7_note"]

    def test_r7_note_absent_when_r7_inactive(self):
        data = _base_input()
        # no p_G_allow → r7 inactive
        result = calculate_vdi2230_core(data)
        assert result["r7_note"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestBearingPressureR7::test_r7_tapped_note_says_head_side tests/core/bolt/test_calculator.py::TestBearingPressureR7::test_r7_through_note_says_both_sides tests/core/bolt/test_calculator.py::TestBearingPressureR7::test_r7_note_absent_when_r7_inactive -v`
Expected: 3 FAILED (KeyError on `result["r7_note"]`)

- [ ] **Step 3: Implement r7_note logic**

In `core/bolt/calculator.py`, replace the R7 section (around lines 275-281) with:

```python
    # --- R7 支承面压强校核 ---
    p_g_allow = float(bearing.get("p_G_allow", 0.0))
    r7_active = p_g_allow > 0
    r7_note = ""
    if r7_active:
        a_bearing = math.pi / 4.0 * (bearing_d_outer**2 - bearing_d_inner**2)
        p_bearing = fm_max / a_bearing
        pass_bearing = p_bearing <= p_g_allow
        if joint_type == "through":
            r7_note = "通孔连接：螺栓头端与螺母端均需满足支承面压强要求（当前使用同一组支承面参数校核）"
        else:
            r7_note = "螺纹孔连接：仅校核螺栓头端支承面压强"
```

In the return dict, add (near `"r3_note": r3_note,`):

```python
        "r7_note": r7_note,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestBearingPressureR7 -v`
Expected: 8 PASSED (5 existing + 3 new)

- [ ] **Step 5: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): R7 note distinguishes tapped vs through joint bearing check"
```

---

### Task 3: scope_note 中注明连接形式

**Files:**
- Modify: `core/bolt/calculator.py:366-369` (scope_note)
- Test: `tests/core/bolt/test_calculator.py`

- [ ] **Step 1: Write failing test**

Add to `TestJointType`:

```python
    def test_scope_note_mentions_joint_type(self):
        data = _base_input()
        data.setdefault("options", {})["joint_type"] = "through"
        result = calculate_vdi2230_core(data)
        assert "通孔" in result["scope_note"]

    def test_scope_note_tapped(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert "螺纹孔" in result["scope_note"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestJointType::test_scope_note_mentions_joint_type tests/core/bolt/test_calculator.py::TestJointType::test_scope_note_tapped -v`
Expected: 2 FAILED

- [ ] **Step 3: Implement scope_note with joint_type**

In `core/bolt/calculator.py`, replace the `scope_note` string:

```python
        "scope_note": (
            f"连接形式：{'通孔螺栓连接' if joint_type == 'through' else '螺纹孔连接'}。"
            "本工具覆盖 VDI 2230 核心链路（装配强度、服役强度、残余夹紧力），"
            "并提供温度与疲劳的工程化扩展校核。"
        ),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestJointType -v`
Expected: 5 PASSED

- [ ] **Step 5: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass (50+ tests)

- [ ] **Step 6: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): scope_note includes joint type description"
```

---

## Chunk 2: UI — joint_type 传入 payload + 连接形式说明

### Task 4: bolt_page.py — joint_type 注入 payload

**Files:**
- Modify: `app/ui/pages/bolt_page.py:112-120` (FieldSpec for joint_type)
- Modify: `app/ui/pages/bolt_page.py:1449-1452` (_build_payload options injection)

**Context:** Currently `elements.joint_type` has `mapping=None`. We need to inject it into `options.joint_type` in the payload. The cleanest approach is to keep `mapping=None` (since it doesn't map to a standard section.key pair) and manually inject in `_build_payload`, similar to how `calculation_mode` is already injected. The UI value is Chinese ("螺纹孔连接"/"通孔螺栓连接") but the calculator expects "tapped"/"through", so we need a mapping.

- [ ] **Step 1: Add joint_type mapping constant**

In `app/ui/pages/bolt_page.py`, after `BEARING_MATERIAL_PRESETS` (line 519), add:

```python
JOINT_TYPE_MAP: dict[str, str] = {
    "螺纹孔连接": "tapped",
    "通孔螺栓连接": "through",
}
```

- [ ] **Step 2: Inject joint_type into payload**

In `_build_payload`, after the `calculation_mode` injection (line 1449-1451), add:

```python
        jt_widget = self._field_widgets.get("elements.joint_type")
        if jt_widget and isinstance(jt_widget, QComboBox):
            jt_text = jt_widget.currentText()
            payload.setdefault("options", {})["joint_type"] = JOINT_TYPE_MAP.get(jt_text, "tapped")
```

- [ ] **Step 3: Update joint_type FieldSpec hint**

Change the `elements.joint_type` FieldSpec hint to include comparison info:

```python
            FieldSpec(
                "elements.joint_type",
                "连接形式",
                "-",
                "螺纹孔连接：螺栓拧入基体，仅螺栓头端有支承面。"
                "通孔连接：螺栓穿过被夹件，头端+螺母端均有支承面。",
                widget_type="choice",
                options=("螺纹孔连接", "通孔螺栓连接"),
                default="螺纹孔连接",
            ),
```

- [ ] **Step 4: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): inject joint_type into calculator payload"
```

---

### Task 5: R7 detail page 显示 r7_note，R0 显示连接形式

**Files:**
- Modify: `app/ui/pages/bolt_flowchart.py:34-63` (R_STEP_FIELDS for r0)
- Modify: `app/ui/pages/bolt_flowchart.py:492-500` (_format_calc_text for r7)

**Context:** The flowchart uses `_format_calc_text(result)` to build per-step calculation detail text. For R7, we append `r7_note` to the existing formatted string. For R0, we add `elements.joint_type` to the input echo fields so the connection type is visible in the summary. The `build_input_echo` method handles `R_STEP_FIELDS` entries by looking up `field_specs` and `field_widgets` — `elements.joint_type` already has a FieldSpec and widget, so it works out of the box.

- [ ] **Step 1: Add joint_type to R0 input echo fields**

In `app/ui/pages/bolt_flowchart.py`, update `R_STEP_FIELDS["r0"]` to prepend `"elements.joint_type"`:

```python
    "r0": ["elements.joint_type",
            "fastener.d", "fastener.p", "fastener.As", "fastener.d2",
            "fastener.d3", "fastener.Rp02",
            "tightening.mu_thread", "tightening.mu_bearing",
            "stiffness.bolt_compliance", "stiffness.bolt_stiffness",
            "stiffness.clamped_compliance", "stiffness.clamped_stiffness",
            "stiffness.load_introduction_factor_n",
            "loads.FA_max", "loads.FQ_max",
            "tightening.alpha_A", "tightening.utilization",
            "options.calculation_mode", "options.check_level"],
```

- [ ] **Step 2: Append r7_note in _format_calc_text for r7 step**

In `app/ui/pages/bolt_flowchart.py`, in the `_format_calc_text` method, find the `if step_id == "r7":` block (around line 492). Replace it with:

```python
        if step_id == "r7":
            if "p_bearing" not in stresses:
                return "未设置许用压强 p_G_allow，R7 已跳过。"
            r7_note = result.get("r7_note", "")
            note_line = f"\n{r7_note}" if r7_note else ""
            return (
                f"A_bearing = π/4×(DKo²-DKi²) = {stresses.get('A_bearing_mm2', 0):.1f} mm²\n"
                f"p_B       = FM,max/A_bearing = {stresses.get('p_bearing', 0):.1f} MPa\n"
                f"p_allow   = {stresses.get('p_G_allow', 0):.0f} MPa\n"
                f"判据: p_B ≤ p_allow{note_line}"
            )
```

- [ ] **Step 3: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/bolt_flowchart.py
git commit -m "feat(bolt/ui): show r7_note and joint_type in flowchart detail pages"
```

---

### Task 6: _render_result 中显示连接形式 + r7_note

**Files:**
- Modify: `app/ui/pages/bolt_page.py:1564-1572` (messages section in _render_result)

**Context:** The `_render_result` method builds message lines shown in the "消息与建议" box. We should add the `r7_note` and `joint_type` info there.

- [ ] **Step 1: Add joint_type and r7_note to message output**

In `_render_result`, in the `messages` list building section (around line 1564), add before the existing `messages.append("[说明]...")`:

```python
        jt = result.get("joint_type", "tapped")
        jt_label = "螺纹孔连接" if jt == "tapped" else "通孔螺栓连接"
        messages.append(f"[连接形式] {jt_label}")
        r7_note = result.get("r7_note", "")
        if r7_note:
            messages.append(f"[R7 说明] {r7_note}")
```

- [ ] **Step 2: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): display joint_type and r7_note in result messages"
```

---

## Chunk 3: Calculator — 热膨胀材料参数

### Task 7: Calculator 从 operating 读取 alpha_bolt/alpha_parts，移除硬编码默认值

**Files:**
- Modify: `core/bolt/calculator.py:157-198` (thermal estimation section)
- Test: `tests/core/bolt/test_calculator.py`

**Context:** Currently line 168 hardcodes `_ALPHA_STEEL_DEFAULT = 11.5e-6` and uses it as fallback when `alpha_bolt`/`alpha_parts` not in `operating`. After this change, when alpha values are not provided and thermal estimation is needed, the calculator should raise a warning instead of silently using steel defaults. But for backward compatibility, we keep the fallback — the point is that UI will now always send explicit values.

**Design decision:** Keep the `11.5e-6` default as fallback (backward-compatible for CLI/JSON users), but add a warning when the default is used and temperatures differ. The UI layer will always send explicit alpha values after Phase 3 UI changes.

- [ ] **Step 1: Write failing test — explicit alpha values used in thermal calc**

```python
class TestThermalMaterial:
    def test_steel_bolt_aluminum_clamped_thermal_loss(self):
        """铝壳体+钢螺栓的热损失应显著大于钢+钢。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0  # trigger auto estimation
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 80.0,
            "alpha_bolt": 11.5e-6,   # 钢
            "alpha_parts": 23.0e-6,  # 铝
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        thermal = result["thermal"]
        assert thermal["thermal_auto_estimated"] is True
        assert thermal["thermal_auto_value_N"] > 0

    def test_same_material_no_thermal_loss(self):
        """相同材料、相同温度 → 无热损失。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 80.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 11.5e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        # same alpha → delta_alpha = 0 → no thermal loss despite temp
        assert result["thermal"]["thermal_auto_value_N"] == 0.0
        assert result["thermal"]["thermal_auto_estimated"] is False

    def test_different_temps_same_alpha_no_loss(self):
        """相同材料但不同温度 → 无热损失（Δα=0 使热力为零）。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 100.0,
            "temp_parts": 20.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 11.5e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        # same alpha, different temp → F_th = 0 because (alpha_bolt - alpha_parts) = 0
        assert result["thermal"]["thermal_auto_value_N"] == 0.0

    def test_alpha_values_echoed_in_thermal_output(self):
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0, "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6, "alpha_parts": 23.0e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        assert "alpha_bolt" in result["thermal"]
        assert "alpha_parts" in result["thermal"]
        assert result["thermal"]["alpha_bolt"] == 11.5e-6
        assert result["thermal"]["alpha_parts"] == 23.0e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestThermalMaterial -v`
Expected: FAILED (at least the echo test — `alpha_bolt` not in thermal output)

- [ ] **Step 3: Implement — echo alpha values in thermal output**

In `core/bolt/calculator.py`, in the thermal estimation section (lines 164-198), the `alpha_bolt` and `alpha_parts` variables are already read from `operating`. We just need to echo them in the return dict.

Replace the thermal return dict section (around line 344-350):

```python
        "thermal": {
            "thermal_loss_effective_N": thermal_effective,
            "thermal_loss_ratio": thermal_loss_ratio,
            "thermal_loss_ratio_limit": 0.25,
            "thermal_auto_estimated": thermal_auto_estimated,
            "thermal_auto_value_N": thermal_auto_value,
            "alpha_bolt": alpha_bolt if thermal_auto_estimated else None,
            "alpha_parts": alpha_parts if thermal_auto_estimated else None,
        },
```

But `alpha_bolt`/`alpha_parts` are only defined inside the `if thermal_force_loss == 0.0` block. We need to hoist them to be always available for the echo. Refactor:

```python
    # Thermal expansion coefficients — always read, used for echo even if not estimating
    _ALPHA_STEEL_DEFAULT = 11.5e-6  # 1/K
    alpha_bolt = float(operating.get("alpha_bolt", _ALPHA_STEEL_DEFAULT))
    alpha_parts = float(operating.get("alpha_parts", _ALPHA_STEEL_DEFAULT))

    thermal_auto_estimated = False
    thermal_auto_value = 0.0
    if thermal_force_loss == 0.0:
        temp_bolt = operating.get("temp_bolt")
        temp_parts = operating.get("temp_parts")
        l_K = clamped.get("total_thickness")

        if (
            temp_bolt is not None
            and temp_parts is not None
            and l_K is not None
        ):
            try:
                temp_bolt = float(temp_bolt)
                temp_parts = float(temp_parts)
                l_K = float(l_K)
                delta_T = temp_bolt - temp_parts
                if delta_T != 0.0 and l_K > 0.0:
                    c_s = 1.0 / delta_s
                    c_p = 1.0 / delta_p
                    thermal_auto_value = abs(
                        (alpha_bolt - alpha_parts) * delta_T
                        * (c_s * c_p) / (c_s + c_p)
                        * l_K
                    )
                    thermal_force_loss = thermal_auto_value
                    thermal_auto_estimated = True
            except (ValueError, ZeroDivisionError):
                pass
```

And in the return dict:

```python
        "thermal": {
            "thermal_loss_effective_N": thermal_effective,
            "thermal_loss_ratio": thermal_loss_ratio,
            "thermal_loss_ratio_limit": 0.25,
            "thermal_auto_estimated": thermal_auto_estimated,
            "thermal_auto_value_N": thermal_auto_value,
            "alpha_bolt": alpha_bolt,
            "alpha_parts": alpha_parts,
        },
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestThermalMaterial -v`
Expected: 4 PASSED

- [ ] **Step 5: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): hoist alpha_bolt/alpha_parts, echo in thermal output"
```

---

## Chunk 4: UI — 热膨胀材料选择

### Task 8: bolt_page.py — 材料下拉与热膨胀系数联动

**Files:**
- Modify: `app/ui/pages/bolt_page.py` — CHAPTERS operating section, add fields
- Modify: `app/ui/pages/bolt_page.py` — signal wiring, add handler
- Modify: `app/ui/pages/bolt_page.py` — constants

**Context:** We add two material dropdown fields (`operating.bolt_material`, `operating.clamped_material`) and two alpha fields (`operating.alpha_bolt`, `operating.alpha_parts`). The material dropdowns use `mapping=None` (UI-only preset selectors). The alpha fields have `mapping=("operating", "alpha_bolt")` etc so they feed into the calculator. When a material is selected, the alpha field is auto-filled. "自定义" clears the alpha field and lets user type.

- [ ] **Step 1: Add material table constant**

In `app/ui/pages/bolt_page.py`, after `BEARING_MATERIAL_PRESETS` and `JOINT_TYPE_MAP` (around line 520), add:

```python
THERMAL_EXPANSION_PRESETS: dict[str, str] = {
    "钢": "11.5e-6",
    "不锈钢": "16.0e-6",
    "铝合金": "23.0e-6",
    "铸铁": "10.5e-6",
}
```

- [ ] **Step 2: Add FieldSpecs for material + alpha in operating chapter**

In CHAPTERS, in the `"operating"` chapter `"fields"` list, **before** the `operating.temp_bolt` field, add these four fields:

```python
            FieldSpec(
                "operating.bolt_material",
                "螺栓材料",
                "-",
                "选择螺栓材料以自动填入热膨胀系数。选「自定义」可手动输入。",
                mapping=None,
                widget_type="choice",
                options=("钢", "不锈钢", "自定义"),
                default="钢",
            ),
            FieldSpec(
                "operating.alpha_bolt",
                "螺栓热膨胀系数 α_bolt（自动计算）",
                "1/K",
                "由材料选择自动填入。自定义模式可手动输入。",
                mapping=("operating", "alpha_bolt"),
                default="11.5e-6",
            ),
            FieldSpec(
                "operating.clamped_material",
                "被夹件/基体材料",
                "-",
                "选择被夹件材料以自动填入热膨胀系数。选「自定义」可手动输入。",
                mapping=None,
                widget_type="choice",
                options=("钢", "铝合金", "铸铁", "不锈钢", "自定义"),
                default="钢",
            ),
            FieldSpec(
                "operating.alpha_parts",
                "被夹件热膨胀系数 α_parts（自动计算）",
                "1/K",
                "由材料选择自动填入。自定义模式可手动输入。",
                mapping=("operating", "alpha_parts"),
                default="11.5e-6",
            ),
```

- [ ] **Step 3: Add alpha fields to _AUTO_FILLED_FIELDS and THERMAL_FIELD_IDS**

Inside the `BoltPage` class body, update the class-level `_AUTO_FILLED_FIELDS` set:

```python
    _AUTO_FILLED_FIELDS: set[str] = {
        "fastener.d2", "fastener.d3", "fastener.As", "fastener.Rp02",
        "operating.alpha_bolt", "operating.alpha_parts",
    }
```

At module level, update `THERMAL_FIELD_IDS` to include the material dropdowns and alpha fields:

```python
THERMAL_FIELD_IDS: set[str] = {
    "operating.temp_bolt",
    "operating.temp_parts",
    "loads.thermal_force_loss",
    "operating.bolt_material",
    "operating.alpha_bolt",
    "operating.clamped_material",
    "operating.alpha_parts",
}
```

- [ ] **Step 4: Add _on_bolt_material_changed and _on_clamped_material_changed handlers**

In `app/ui/pages/bolt_page.py`, after `_on_grade_changed` method, add:

```python
    def _on_bolt_material_changed(self, text: str) -> None:
        """螺栓材料下拉变更时自动填入热膨胀系数。"""
        alpha_w = self._field_widgets.get("operating.alpha_bolt")
        if not (alpha_w and isinstance(alpha_w, QLineEdit)):
            return
        preset = THERMAL_EXPANSION_PRESETS.get(text)
        if preset is not None:
            alpha_w.setText(preset)
            alpha_w.setReadOnly(True)
        else:
            alpha_w.setReadOnly(False)
            alpha_w.clear()
            alpha_w.setFocus()

    def _on_clamped_material_changed(self, text: str) -> None:
        """被夹件材料下拉变更时自动填入热膨胀系数。"""
        alpha_w = self._field_widgets.get("operating.alpha_parts")
        if not (alpha_w and isinstance(alpha_w, QLineEdit)):
            return
        preset = THERMAL_EXPANSION_PRESETS.get(text)
        if preset is not None:
            alpha_w.setText(preset)
            alpha_w.setReadOnly(True)
        else:
            alpha_w.setReadOnly(False)
            alpha_w.clear()
            alpha_w.setFocus()
```

- [ ] **Step 5: Wire up signals**

In `__init__`, after the grade signal wiring block, add:

```python
        # 材料热膨胀联动
        bolt_mat_widget = self._field_widgets.get("operating.bolt_material")
        if bolt_mat_widget and isinstance(bolt_mat_widget, QComboBox):
            bolt_mat_widget.currentTextChanged.connect(self._on_bolt_material_changed)
            self._on_bolt_material_changed(bolt_mat_widget.currentText())
        clamped_mat_widget = self._field_widgets.get("operating.clamped_material")
        if clamped_mat_widget and isinstance(clamped_mat_widget, QComboBox):
            clamped_mat_widget.currentTextChanged.connect(self._on_clamped_material_changed)
            self._on_clamped_material_changed(clamped_mat_widget.currentText())
```

- [ ] **Step 6: Update _apply_defaults to re-trigger material auto-fill**

In `_apply_defaults`, after the grade re-trigger, add:

```python
        bm_w = self._field_widgets.get("operating.bolt_material")
        if bm_w and isinstance(bm_w, QComboBox):
            self._on_bolt_material_changed(bm_w.currentText())
        cm_w = self._field_widgets.get("operating.clamped_material")
        if cm_w and isinstance(cm_w, QComboBox):
            self._on_clamped_material_changed(cm_w.currentText())
```

- [ ] **Step 7: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): material dropdowns with thermal expansion auto-fill"
```

---

### Task 9: _render_result 显示热膨胀材料信息

**Files:**
- Modify: `app/ui/pages/bolt_page.py:1553-1556` (thermal metric line area)

**Context:** When thermal check level is active and auto estimation is used, show the alpha values in the metrics output so the user knows which coefficients were used.

- [ ] **Step 1: Enhance thermal metric line**

In `_render_result`, find the thermal metric line (around line 1553-1556) and expand it:

```python
        if level in ("thermal", "fatigue"):
            thermal_line = f"• 热损失占比: {thermal.get('thermal_loss_ratio', 0.0) * 100:.1f}%  /  限值 25.0%"
            if thermal.get("thermal_auto_estimated"):
                a_b = thermal.get("alpha_bolt", 0)
                a_p = thermal.get("alpha_parts", 0)
                thermal_line += f"\n  热膨胀系数: α_bolt={a_b:.1e} /K, α_parts={a_p:.1e} /K（自动估算）"
            metric_lines.append(thermal_line)
```

- [ ] **Step 2: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): show thermal expansion coefficients in result metrics"
```

---

### Task 10: Update example JSON files

**Files:**
- Modify: `examples/input_case_01.json`
- Modify: `examples/input_case_02.json`

**Context:** Add `options.joint_type` and `operating.alpha_bolt`/`alpha_parts` to example files for completeness. Existing tests and UI that load these samples should still work.

- [ ] **Step 1: Update input_case_01.json**

Add to the JSON:
- In `"operating"` section (create if absent): `"alpha_bolt": 11.5e-6, "alpha_parts": 11.5e-6`
- In `"options"` section (create if absent): `"joint_type": "tapped"`

- [ ] **Step 2: Update input_case_02.json**

Same additions as case_01.

- [ ] **Step 3: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add examples/
git commit -m "docs(bolt): add joint_type and thermal alpha to example inputs"
```

---

### Task 11: Final integration test — end-to-end verify

**Files:**
- Test: `tests/core/bolt/test_calculator.py`

**Context:** A comprehensive test that exercises the full new path: tapped joint + aluminum clamped material with thermal check level.

- [ ] **Step 1: Write integration test**

```python
class TestJointTypeThermalIntegration:
    def test_tapped_aluminum_thermal_full_chain(self):
        """螺纹孔连接 + 铝壳体，thermal 层级完整链路。"""
        data = _base_input()
        data["options"] = {
            "check_level": "thermal",
            "joint_type": "tapped",
        }
        data["loads"]["thermal_force_loss"] = 0  # trigger auto estimation
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 23.0e-6,
            "load_cycles": 100000,
        }
        data["clamped"] = {"total_thickness": 20.0}
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        # joint type
        assert result["joint_type"] == "tapped"
        assert "螺纹孔" in result["scope_note"]
        assert "螺栓头端" in result["r7_note"]
        # thermal auto estimation activated
        assert result["thermal"]["thermal_auto_estimated"] is True
        assert result["thermal"]["thermal_auto_value_N"] > 0
        assert result["thermal"]["alpha_bolt"] == 11.5e-6
        assert result["thermal"]["alpha_parts"] == 23.0e-6
        # R7 still works
        assert "bearing_pressure_ok" in result["checks"]
        # all standard checks present
        assert "assembly_von_mises_ok" in result["checks"]
        assert "operating_axial_ok" in result["checks"]
        assert "residual_clamp_ok" in result["checks"]
        assert "thermal_loss_ok" in result["checks"]

    def test_through_joint_steel_basic_level(self):
        """通孔连接 + 钢，basic 层级。"""
        data = _base_input()
        data["options"] = {"joint_type": "through"}
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        assert result["joint_type"] == "through"
        assert "通孔" in result["scope_note"]
        assert "螺母端" in result["r7_note"]
        assert result["overall_pass"] in (True, False)  # just check it runs
```

- [ ] **Step 2: Run the integration tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestJointTypeThermalIntegration -v`
Expected: 2 PASSED

- [ ] **Step 3: Run full test suite one final time**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add tests/core/bolt/test_calculator.py
git commit -m "test(bolt): integration tests for joint_type + thermal material"
```
