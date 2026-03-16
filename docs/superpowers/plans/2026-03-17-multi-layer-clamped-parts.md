# Multi-Layer Clamped Parts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable multi-layer clamped parts with independent per-layer thickness, D_A, elastic modulus, and thermal expansion coefficient in the bolt module.

**Architecture:** Three-layer change: (1) calculator adds multi-layer compliance + thermal branches, (2) UI adds layer FieldSpecs with visibility toggling, (3) payload builder constructs `layers` list. Backend `compliance_model.py` already supports multi-layer — no changes needed there.

**Tech Stack:** Python 3.12, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-03-17-multi-layer-clamped-parts-design.md`

---

## Chunk 1: Calculator Multi-Layer Support

### Task 1: Multi-layer auto_compliance test + implementation

**Files:**
- Modify: `tests/core/bolt/test_calculator.py` (add new test class)
- Modify: `core/bolt/calculator.py:69-88` (`_resolve_compliance` in `calculate_vdi2230_core`)

- [ ] **Step 1: Write failing test — multi-layer auto compliance**

Add to `tests/core/bolt/test_calculator.py` at the end of `TestAutoCompliance` class:

```python
    def test_auto_compliance_multi_layer(self):
        """多层被夹件：钢+铝双层，δp = δp_steel + δp_alu。"""
        from core.bolt.compliance_model import calculate_clamped_compliance
        data = _base_input()
        del data["stiffness"]["bolt_compliance"]
        del data["stiffness"]["clamped_compliance"]
        data["stiffness"]["auto_compliance"] = True
        data["stiffness"]["E_bolt"] = 210_000.0
        data["bearing"]["bearing_d_inner"] = 11.0
        data["clamped"] = {
            "total_thickness": 30.0,
            "layers": [
                {"model": "cylinder", "d_h": 11.0, "D_A": 24.0,
                 "l_K": 15.0, "E_clamped": 210_000.0},
                {"model": "cylinder", "d_h": 11.0, "D_A": 24.0,
                 "l_K": 15.0, "E_clamped": 70_000.0},
            ],
        }
        result = calculate_vdi2230_core(data)
        assert result["stiffness_model"]["auto_modeled"] is True
        # 验证 δp 等于各层之和
        dp_steel = calculate_clamped_compliance(
            model="cylinder", d_h=11.0, D_A=24.0,
            l_K=15.0, E_clamped=210_000.0)["delta_p"]
        dp_alu = calculate_clamped_compliance(
            model="cylinder", d_h=11.0, D_A=24.0,
            l_K=15.0, E_clamped=70_000.0)["delta_p"]
        expected_dp = dp_steel + dp_alu
        actual_dp = result["stiffness_model"]["delta_p_mm_per_n"]
        assert abs(actual_dp - expected_dp) / expected_dp < 0.01
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestAutoCompliance::test_auto_compliance_multi_layer -v`

Expected: FAIL (calculator ignores `layers` key, uses single E_clamped fallback)

- [ ] **Step 3: Implement multi-layer branch in `_resolve_compliance`**

In `core/bolt/calculator.py`, replace lines 69-88 (the `elif stiffness.get("auto_compliance"):` block) with:

```python
    elif stiffness.get("auto_compliance"):
        from core.bolt.compliance_model import (
            calculate_bolt_compliance, calculate_clamped_compliance,
        )
        E_bolt = _positive(float(stiffness.get("E_bolt", 210_000)), "stiffness.E_bolt")
        cl = clamped or {}

        if "layers" in cl:
            # ---------- 多层模式 ----------
            layers = cl["layers"]
            if not isinstance(layers, list) or not (1 <= len(layers) <= 10):
                raise InputError("被夹件层数须在 1~10 之间")
            l_K = sum(float(layer["l_K"]) for layer in layers)
            _positive(l_K, "clamped.total_thickness (各层求和)")
            bolt_r = calculate_bolt_compliance(d, p, l_K, E_bolt)
            delta_s = bolt_r["delta_s"]
            d_h = bearing_d_inner
            for layer in layers:
                layer.setdefault("d_h", d_h)
            clamp_r = calculate_clamped_compliance(layers=layers)
            delta_p = clamp_r["delta_p"]
        else:
            # ---------- 单层模式（保持不变）----------
            E_clamped = _positive(float(stiffness.get("E_clamped", 210_000)), "stiffness.E_clamped")
            l_K = _positive(float(cl.get("total_thickness", 0)), "clamped.total_thickness")
            bolt_r = calculate_bolt_compliance(d, p, l_K, E_bolt)
            delta_s = bolt_r["delta_s"]
            solid_type = str(cl.get("basic_solid", "cylinder"))
            D_A = float(cl.get("D_A", bearing_d_outer))
            d_h = bearing_d_inner
            D_w = (bearing_d_inner + bearing_d_outer) / 2.0
            clamp_r = calculate_clamped_compliance(
                model=solid_type, d_h=d_h, D_w=D_w, D_A=D_A,
                l_K=l_K, E_clamped=E_clamped,
            )
            delta_p = clamp_r["delta_p"]
        auto_modeled = True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestAutoCompliance -v`

Expected: ALL PASS (including existing single-layer tests)

- [ ] **Step 5: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): add multi-layer auto_compliance branch in calculator"
```

### Task 2: Multi-layer layer count validation test

**Files:**
- Modify: `tests/core/bolt/test_calculator.py`

- [ ] **Step 1: Write failing test — empty layers raises InputError**

Add a new test class after `TestAutoCompliance`:

```python
class TestMultiLayerValidation:
    def test_empty_layers_raises(self):
        """空 layers 列表应报错。"""
        data = _base_input()
        del data["stiffness"]["bolt_compliance"]
        del data["stiffness"]["clamped_compliance"]
        data["stiffness"]["auto_compliance"] = True
        data["stiffness"]["E_bolt"] = 210_000.0
        data["clamped"] = {"total_thickness": 0, "layers": []}
        with pytest.raises(InputError, match="层数"):
            calculate_vdi2230_core(data)

    def test_too_many_layers_raises(self):
        """超过 10 层应报错。"""
        data = _base_input()
        del data["stiffness"]["bolt_compliance"]
        del data["stiffness"]["clamped_compliance"]
        data["stiffness"]["auto_compliance"] = True
        data["stiffness"]["E_bolt"] = 210_000.0
        layer = {"model": "cylinder", "d_h": 11.0, "D_A": 24.0,
                 "l_K": 5.0, "E_clamped": 210_000.0}
        data["clamped"] = {"total_thickness": 55, "layers": [layer] * 11}
        with pytest.raises(InputError, match="层数"):
            calculate_vdi2230_core(data)
```

- [ ] **Step 2: Run tests to verify they pass** (implementation from Task 1 already handles this)

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestMultiLayerValidation -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/core/bolt/test_calculator.py
git commit -m "test(bolt): add multi-layer validation tests"
```

### Task 3: Multi-layer thermal loss test + implementation

**Files:**
- Modify: `tests/core/bolt/test_calculator.py`
- Modify: `core/bolt/calculator.py:269-311` (thermal section)

- [ ] **Step 1: Write failing test — multi-layer thermal with different alphas**

Add a new test class:

```python
class TestMultiLayerThermal:
    def test_multi_layer_thermal_loss(self):
        """多层不同 alpha：Δl = Σ(alpha_i × l_K_i × ΔT)。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 20.0,
            "alpha_bolt": 11.5e-6,
            "layer_thermals": [
                {"alpha": 11.5e-6, "l_K": 15.0},   # 钢层
                {"alpha": 23.0e-6, "l_K": 15.0},    # 铝层
            ],
        }
        data["clamped"] = {"total_thickness": 30.0}
        result = calculate_vdi2230_core(data)
        thermal = result["thermal"]
        assert thermal["thermal_auto_estimated"] is True
        # 手算验证：
        # delta_l_parts = 11.5e-6*15*60 + 23.0e-6*15*60 = 0.01035 + 0.0207 = 0.03105
        # delta_l_bolt  = 11.5e-6*30*60 = 0.0207
        # F_th = |0.03105 - 0.0207| / (delta_s + delta_p) = 0.01035 / (1.8e-6 + 2.4e-6)
        # F_th = 0.01035 / 4.2e-6 ≈ 2464 N
        delta_s = data["stiffness"]["bolt_compliance"]
        delta_p = data["stiffness"]["clamped_compliance"]
        delta_T = 60.0
        delta_l_parts = 11.5e-6 * 15.0 * delta_T + 23.0e-6 * 15.0 * delta_T
        delta_l_bolt = 11.5e-6 * 30.0 * delta_T
        expected = abs(delta_l_parts - delta_l_bolt) / (delta_s + delta_p)
        assert abs(thermal["thermal_auto_value_N"] - expected) / expected < 0.01

    def test_single_layer_thermal_unchanged(self):
        """单层热损失回归：不带 layer_thermals 时保持原公式。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 23.0e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        thermal = result["thermal"]
        assert thermal["thermal_auto_estimated"] is True
        # 现有公式: |Δα × ΔT × l_K / (δs + δp)|
        delta_s = data["stiffness"]["bolt_compliance"]
        delta_p = data["stiffness"]["clamped_compliance"]
        expected = abs(
            (11.5e-6 - 23.0e-6) * 50.0 * 20.0 / (delta_s + delta_p)
        )
        assert abs(thermal["thermal_auto_value_N"] - expected) / expected < 0.01

    def test_multi_layer_compliance_and_thermal_combined(self):
        """集成测试：auto_compliance + layer_thermals 同时使用。"""
        data = _base_input()
        del data["stiffness"]["bolt_compliance"]
        del data["stiffness"]["clamped_compliance"]
        data["stiffness"]["auto_compliance"] = True
        data["stiffness"]["E_bolt"] = 210_000.0
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["bearing"]["bearing_d_inner"] = 11.0
        data["clamped"] = {
            "total_thickness": 30.0,
            "layers": [
                {"model": "cylinder", "d_h": 11.0, "D_A": 24.0,
                 "l_K": 15.0, "E_clamped": 210_000.0},
                {"model": "cylinder", "d_h": 11.0, "D_A": 24.0,
                 "l_K": 15.0, "E_clamped": 70_000.0},
            ],
        }
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 20.0,
            "alpha_bolt": 11.5e-6,
            "layer_thermals": [
                {"alpha": 11.5e-6, "l_K": 15.0},
                {"alpha": 23.0e-6, "l_K": 15.0},
            ],
        }
        result = calculate_vdi2230_core(data)
        assert result["stiffness_model"]["auto_modeled"] is True
        assert result["thermal"]["thermal_auto_estimated"] is True
        assert result["thermal"]["thermal_auto_value_N"] > 0
```

- [ ] **Step 2: Run tests to verify multi-layer test fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestMultiLayerThermal -v`

Expected: `test_multi_layer_thermal_loss` FAIL (no `layer_thermals` handling), `test_single_layer_thermal_unchanged` PASS

- [ ] **Step 3: Implement multi-layer thermal branch**

In `core/bolt/calculator.py`, modify the thermal section (around lines 277-311). Replace the block starting at `alpha_parts = float(operating.get("alpha_parts", ...))` through the thermal estimation block:

```python
    _ALPHA_STEEL_DEFAULT = 11.5e-6  # 1/K
    alpha_bolt = float(operating.get("alpha_bolt", _ALPHA_STEEL_DEFAULT))
    alpha_parts = float(operating.get("alpha_parts", _ALPHA_STEEL_DEFAULT))

    thermal_auto_estimated = False
    thermal_auto_value = 0.0
    layer_thermals = operating.get("layer_thermals")

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
                    if layer_thermals:
                        # 多层热位移：逐层求和
                        delta_l_parts = sum(
                            float(lt["alpha"]) * float(lt["l_K"]) * delta_T
                            for lt in layer_thermals
                        )
                        delta_l_bolt = alpha_bolt * l_K * delta_T
                        thermal_auto_value = abs(delta_l_parts - delta_l_bolt) / (delta_s + delta_p)
                    else:
                        # 单层热损失：保持原公式
                        c_s = 1.0 / delta_s
                        c_p = 1.0 / delta_p
                        thermal_auto_value = abs(
                            (alpha_bolt - alpha_parts) * delta_T
                            * (c_s * c_p) / (c_s + c_p)
                            * l_K
                        )
                    if thermal_auto_value > 0.0:
                        thermal_force_loss = thermal_auto_value
                        thermal_auto_estimated = True
            except (ValueError, ZeroDivisionError):
                pass
```

- [ ] **Step 4: Run all thermal tests to verify**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestMultiLayerThermal tests/core/bolt/test_calculator.py::TestThermalMaterial tests/core/bolt/test_calculator.py::TestJointTypeThermalIntegration -v`

Expected: ALL PASS

- [ ] **Step 5: Update thermal output dict for multi-layer**

In `core/bolt/calculator.py`, modify the thermal output section (around line 506-514). Replace:

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

with:

```python
        "thermal": {
            "thermal_loss_effective_N": thermal_effective,
            "thermal_loss_ratio": thermal_loss_ratio,
            "thermal_loss_ratio_limit": 0.25,
            "thermal_auto_estimated": thermal_auto_estimated,
            "thermal_auto_value_N": thermal_auto_value,
            "alpha_bolt": alpha_bolt,
            "alpha_parts": alpha_parts,
            **({"layer_thermals": layer_thermals} if layer_thermals else {}),
        },
```

- [ ] **Step 6: Run full test suite to verify nothing is broken**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`

Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): add multi-layer thermal loss calculation"
```

## Chunk 2: UI Multi-Layer Fields + Payload Construction

### Task 4: Add layer FieldSpecs and part_count dropdown

**Files:**
- Modify: `app/ui/pages/bolt_page.py:253-312` (clamped section FieldSpecs)

- [ ] **Step 1: Change `part_count` from numeric to choice**

In `app/ui/pages/bolt_page.py`, replace the `clamped.part_count` FieldSpec (lines 263-270):

```python
            FieldSpec(
                "clamped.part_count",
                "被夹件数量",
                "个",
                "参与夹紧的零件数量。螺纹孔连接常见 1 个，通孔连接常见 2 个。",
                mapping=("clamped", "part_count"),
                default="1",
            ),
```

with:

```python
            FieldSpec(
                "clamped.part_count",
                "被夹件数量",
                "-",
                "参与夹紧的零件数量。选 2 或自定义时可分层输入参数。",
                mapping=None,
                widget_type="choice",
                options=("1", "2", "自定义"),
                default="1",
            ),
            FieldSpec(
                "clamped.custom_count",
                "自定义层数",
                "个",
                "输入被夹件层数（3~5）。",
                mapping=None,
                default="3",
            ),
```

- [ ] **Step 2: Add layer_1 ~ layer_5 FieldSpecs**

After the `clamped.custom_count` FieldSpec and before `clamped.total_thickness`, insert the per-layer fields. Generate them with a helper to keep DRY:

Right before the `CHAPTERS` list definition, add a helper function:

```python
def _make_layer_fields(n: int) -> list[FieldSpec]:
    """生成第 n 层被夹件的 FieldSpec 列表。"""
    return [
        FieldSpec(
            f"clamped.layer_{n}.thickness",
            f"第{n}层厚度",
            "mm",
            f"第{n}层被夹件厚度。",
            mapping=None,
            default="15",
        ),
        FieldSpec(
            f"clamped.layer_{n}.D_A",
            f"第{n}层外径 DA",
            "mm",
            f"第{n}层被夹件外径。",
            mapping=None,
            default="24",
        ),
        FieldSpec(
            f"clamped.layer_{n}.E",
            f"第{n}层弹性模量",
            "MPa",
            f"第{n}层被夹件弹性模量。钢 210000 / 铝 70000。",
            mapping=None,
            default="210000",
        ),
        FieldSpec(
            f"clamped.layer_{n}.material",
            f"第{n}层材料",
            "-",
            f"第{n}层材料选择，用于自动填入热膨胀系数。",
            mapping=None,
            widget_type="choice",
            options=("钢", "铝合金", "铸铁", "不锈钢", "自定义"),
            default="钢",
        ),
        FieldSpec(
            f"clamped.layer_{n}.alpha",
            f"第{n}层热膨胀系数",
            "1/K",
            f"第{n}层热膨胀系数。由材料选择自动填入。",
            mapping=None,
            default="11.5e-6",
        ),
    ]

LAYER_FIELD_IDS: list[list[str]] = [
    [f"clamped.layer_{n}.{f}" for f in ("thickness", "D_A", "E", "material", "alpha")]
    for n in range(1, 6)
]
```

Then in the `clamped` chapter's `"fields"` list, after `clamped.custom_count` and before `clamped.total_thickness`, insert:

```python
            *_make_layer_fields(1),
            *_make_layer_fields(2),
            *_make_layer_fields(3),
            *_make_layer_fields(4),
            *_make_layer_fields(5),
```

- [ ] **Step 3: Run app to verify fields render (visual check)**

Run: `python3 app/main.py`

Verify: All layer fields appear in the clamped section (they'll all be visible initially — visibility logic comes next).

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt): add multi-layer FieldSpecs and part_count dropdown"
```

### Task 5: Implement visibility toggling

**Files:**
- Modify: `app/ui/pages/bolt_page.py` (add visibility method + connect signal)

- [ ] **Step 1: Add `_on_part_count_changed` method**

Add after `_on_clamped_material_changed` (around line 1205):

```python
    # -- 单层字段 ID（多层模式时隐藏）--
    _SINGLE_LAYER_FIELDS: set[str] = {
        "clamped.basic_solid", "clamped.total_thickness", "clamped.D_A",
        "stiffness.E_clamped",
    }
    # -- 单层热材料字段 --
    _SINGLE_THERMAL_FIELDS: set[str] = {
        "operating.clamped_material", "operating.alpha_parts",
    }

    def _get_effective_part_count(self) -> int:
        """从 UI 控件读取有效被夹件数量。"""
        pc_w = self._field_widgets.get("clamped.part_count")
        if not (pc_w and isinstance(pc_w, QComboBox)):
            return 1
        text = pc_w.currentText()
        if text == "1":
            return 1
        if text == "2":
            return 2
        # "自定义"
        cc_w = self._field_widgets.get("clamped.custom_count")
        if cc_w and isinstance(cc_w, QLineEdit):
            try:
                v = int(float(cc_w.text().strip()))
                return max(3, min(v, 5))
            except (ValueError, TypeError):
                return 3
        return 3

    def _on_part_count_changed(self, _text: str = "") -> None:
        """被夹件数量变更时切换单层/多层字段可见性。

        使用 self._field_cards[fid] 获取字段卡片控件（而非 w.parent()），
        这是本代码库中控制字段可见性的标准模式，见 _on_thread_d_changed。
        """
        count = self._get_effective_part_count()
        is_multi = count >= 2

        # 单层字段
        for fid in self._SINGLE_LAYER_FIELDS | self._SINGLE_THERMAL_FIELDS:
            card = self._field_cards.get(fid)
            if card is not None:
                card.setVisible(not is_multi)

        # custom_count 仅在"自定义"时显示
        pc_w = self._field_widgets.get("clamped.part_count")
        is_custom = pc_w and isinstance(pc_w, QComboBox) and pc_w.currentText() == "自定义"
        cc_card = self._field_cards.get("clamped.custom_count")
        if cc_card is not None:
            cc_card.setVisible(bool(is_custom))

        # 各层字段
        for layer_idx in range(5):
            visible = is_multi and layer_idx < count
            for fid in LAYER_FIELD_IDS[layer_idx]:
                card = self._field_cards.get(fid)
                if card is not None:
                    card.setVisible(visible)
```

- [ ] **Step 2: Connect signal in `__init__`**

In the signal connection section (around line 867-870), add after the existing `clamped_mat_widget` connection:

```python
        # 被夹件数量联动
        pc_widget = self._field_widgets.get("clamped.part_count")
        if pc_widget and isinstance(pc_widget, QComboBox):
            pc_widget.currentTextChanged.connect(self._on_part_count_changed)
        cc_widget = self._field_widgets.get("clamped.custom_count")
        if cc_widget and isinstance(cc_widget, QLineEdit):
            cc_widget.textChanged.connect(lambda _: self._on_part_count_changed())
        # 初始化可见性
        self._on_part_count_changed()
```

- [ ] **Step 3: Connect per-layer material dropdowns to auto-fill alpha**

Add after `_on_part_count_changed`:

```python
    def _on_layer_material_changed(self, layer_n: int, text: str) -> None:
        """第 N 层材料变更时自动填入对应热膨胀系数。"""
        alpha_w = self._field_widgets.get(f"clamped.layer_{layer_n}.alpha")
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

And in the signal connection section, add after `cc_widget.textChanged.connect`:

```python
        # 各层材料联动
        for ln in range(1, 6):
            mat_w = self._field_widgets.get(f"clamped.layer_{ln}.material")
            if mat_w and isinstance(mat_w, QComboBox):
                mat_w.currentTextChanged.connect(
                    lambda text, n=ln: self._on_layer_material_changed(n, text)
                )
                self._on_layer_material_changed(ln, mat_w.currentText())
```

- [ ] **Step 4: Add layer alpha fields to `_AUTO_FILLED_FIELDS`**

Update the `_AUTO_FILLED_FIELDS` set to include layer alpha fields:

```python
    _AUTO_FILLED_FIELDS: set[str] = {
        "fastener.d2", "fastener.d3", "fastener.As", "fastener.Rp02",
        "operating.alpha_bolt", "operating.alpha_parts",
        *(f"clamped.layer_{n}.alpha" for n in range(1, 6)),
    }
```

- [ ] **Step 5: Run app to verify visibility toggling**

Run: `python3 app/main.py`

Verify:
- `part_count=1`: only single-layer fields visible
- `part_count=2`: layer_1 + layer_2 visible, single-layer fields hidden
- `part_count=自定义`: custom_count input appears, layer fields match count
- Each layer's material dropdown auto-fills alpha

- [ ] **Step 6: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt): add part_count visibility toggling and layer material linkage"
```

### Task 6: Build multi-layer payload in `_build_payload`

**Files:**
- Modify: `app/ui/pages/bolt_page.py:1640-1695` (`_build_payload` method)

- [ ] **Step 1: Add multi-layer payload construction**

At the end of `_build_payload` (before `return payload`, around line 1695), add:

```python
        # ---------- 多层被夹件 payload 构建 ----------
        part_count = self._get_effective_part_count()
        payload.setdefault("clamped", {})["part_count"] = part_count

        if part_count >= 2:
            layers = []
            layer_thermals = []
            total_thickness = 0.0
            d_h_val = payload.get("bearing", {}).get("bearing_d_inner", 13.0)

            for i in range(1, part_count + 1):
                t_w = self._field_widgets.get(f"clamped.layer_{i}.thickness")
                da_w = self._field_widgets.get(f"clamped.layer_{i}.D_A")
                e_w = self._field_widgets.get(f"clamped.layer_{i}.E")
                alpha_w = self._field_widgets.get(f"clamped.layer_{i}.alpha")
                t_val = float(t_w.text().strip()) if t_w else 15.0
                da_val = float(da_w.text().strip()) if da_w else 24.0
                e_val = float(e_w.text().strip()) if e_w else 210_000.0
                alpha_val = float(alpha_w.text().strip()) if alpha_w else 11.5e-6
                total_thickness += t_val
                layers.append({
                    "model": "cylinder",
                    "d_h": float(d_h_val),
                    "D_A": da_val,
                    "l_K": t_val,
                    "E_clamped": e_val,
                })
                layer_thermals.append({"alpha": alpha_val, "l_K": t_val})

            payload["clamped"]["layers"] = layers
            payload["clamped"]["total_thickness"] = total_thickness
            payload.setdefault("operating", {})["layer_thermals"] = layer_thermals
            # 多层模式移除单层参数
            payload.get("stiffness", {}).pop("E_clamped", None)
            payload.get("operating", {}).pop("alpha_parts", None)
```

Also, ensure the existing `part_count` mapping no longer auto-processes. Since we changed `mapping=None`, the generic loop already skips it. But we need to make sure the single-layer mode also gets `part_count` set. Add before the multi-layer block:

The single-layer case (`part_count == 1`) is already handled: `part_count` is set to `1` by the line above, and the existing `total_thickness`, `D_A`, `E_clamped` fields still have their mappings and flow through normally.

- [ ] **Step 2: Run app — test full single-layer calculation still works**

Run: `python3 app/main.py`

Verify: Load `input_case_01.json`, click calculate → results display correctly (same as before).

- [ ] **Step 3: Run app — test multi-layer calculation**

Run: `python3 app/main.py`

Verify:
1. Set `part_count=2`
2. Layer 1: thickness=15, D_A=24, E=210000, material=钢
3. Layer 2: thickness=15, D_A=24, E=70000, material=铝合金
4. Set `auto_compliance=自动计算`
5. Click calculate → results show without error

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt): build multi-layer payload in _build_payload"
```

### Task 7: Input persistence — save/load multi-layer data

**Files:**
- Modify: `app/ui/pages/bolt_page.py:1490-1568` (`_apply_input_data` method)

- [ ] **Step 1: Add multi-layer restore logic**

**恢复机制说明**：正常保存/加载流程中，`build_form_snapshot` 把所有 `mapping=None` 的字段
存入 `ui_state` 字典（如 `ui_state["clamped.part_count"] = "2"`、`ui_state["clamped.layer_1.thickness"] = "15"`），
`_apply_input_data` 的通用循环已经能按 `field_id` 匹配恢复这些值。`part_count` 的 `setCurrentText` 会触发
`currentTextChanged` 信号 → `_on_part_count_changed()` 自动调用 → 可见性正确。

所以通用循环已经覆盖了正常 save/load round-trip，**无需额外代码**。

但需要处理一个边缘场景：加载原始 calculator payload JSON（如 example 文件或 API 直接产出），
这些文件里只有 `clamped.layers` 结构，没有 `ui_state`。为此添加 fallback 恢复逻辑：

In `_apply_input_data`, after the main field-restore loop and before the `check_level` handling (around line 1542), add:

```python
        # ---------- 多层被夹件 fallback 恢复（用于加载原始 payload JSON）----------
        # 正常 save/load 流程中，通用循环已通过 ui_state 恢复所有层字段。
        # 此处仅处理 inputs 中有 clamped.layers 但 ui_state 中无层字段的情况。
        clamped_data = inputs.get("clamped", {})
        saved_layers = clamped_data.get("layers")
        has_layer_ui_state = any(
            k.startswith("clamped.layer_") for k in ui_state
        )
        if isinstance(saved_layers, list) and len(saved_layers) >= 2 and not has_layer_ui_state:
            n = len(saved_layers)
            pc_w = self._field_widgets.get("clamped.part_count")
            if pc_w and isinstance(pc_w, QComboBox):
                if n == 2:
                    pc_w.setCurrentText("2")
                else:
                    pc_w.setCurrentText("自定义")
                    cc_w = self._field_widgets.get("clamped.custom_count")
                    if cc_w and isinstance(cc_w, QLineEdit):
                        cc_w.setText(str(n))
            # 填充各层参数
            op_data = inputs.get("operating", {})
            saved_thermals = op_data.get("layer_thermals", [])
            for i, layer in enumerate(saved_layers[:5], start=1):
                t_w = self._field_widgets.get(f"clamped.layer_{i}.thickness")
                if t_w and isinstance(t_w, QLineEdit):
                    t_w.setText(str(layer.get("l_K", "")))
                da_w = self._field_widgets.get(f"clamped.layer_{i}.D_A")
                if da_w and isinstance(da_w, QLineEdit):
                    da_w.setText(str(layer.get("D_A", "")))
                e_w = self._field_widgets.get(f"clamped.layer_{i}.E")
                if e_w and isinstance(e_w, QLineEdit):
                    e_w.setText(str(layer.get("E_clamped", "")))
                # 恢复 alpha
                if i - 1 < len(saved_thermals):
                    alpha_val = saved_thermals[i - 1].get("alpha", "")
                    alpha_w = self._field_widgets.get(f"clamped.layer_{i}.alpha")
                    if alpha_w and isinstance(alpha_w, QLineEdit):
                        alpha_w.setText(str(alpha_val))
                        alpha_w.setReadOnly(False)
                    # 尝试从 alpha 反推材料
                    mat_w = self._field_widgets.get(f"clamped.layer_{i}.material")
                    if mat_w and isinstance(mat_w, QComboBox):
                        matched = False
                        for mat_name, preset_val in THERMAL_EXPANSION_PRESETS.items():
                            if str(alpha_val) == preset_val:
                                mat_w.setCurrentText(mat_name)
                                matched = True
                                break
                        if not matched:
                            mat_w.setCurrentText("自定义")
            self._on_part_count_changed()
```

- [ ] **Step 2: Run app — test save/load round-trip**

Run: `python3 app/main.py`

Verify:
1. Set `part_count=2` with 2 layers (different materials)
2. Save input conditions
3. Clear all fields
4. Load saved file → layers restore correctly

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt): add multi-layer input persistence restore"
```

## Chunk 3: Final Verification

### Task 8: Full regression test

**Files:** (no new files)

- [ ] **Step 1: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`

Expected: ALL PASS (including all existing bolt tests + new multi-layer tests)

- [ ] **Step 2: Run app — end-to-end multi-layer scenario**

Run: `python3 app/main.py`

Test the sandwich structure from the original question:
1. M10 bolt, 通孔连接
2. `part_count=2`
3. Layer 1: 钢, thickness=10, D_A=20, E=210000
4. Layer 2: 铝合金, thickness=15, D_A=25, E=70000
5. `auto_compliance=自动计算`
6. Set operating temperatures (bolt=80°C, parts=30°C)
7. Click calculate → verify results make sense

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(bolt): multi-layer clamped parts support — complete"
```
