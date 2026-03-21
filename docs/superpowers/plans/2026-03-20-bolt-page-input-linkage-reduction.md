# Bolt Page Input Linkage Reduction Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过 3 组低风险联动减少螺栓校核页面的手工输入量，同时保持 payload 语义稳定、手工覆盖能力不丢失。

**Architecture:** 本轮只改 UI 层与 headless UI 测试，不改 VDI 2230 核心公式。具体做法是：`setup_case` 负责相关载荷字段的显隐与 payload 归一化；`μT` 增加“跟随 μK / 单独输入”模式，优先复用 core 现有 fallback；材料选择在保持 `alpha` 联动的基础上，同步带出自动柔度建模依赖的弹性模量 `E`，但一旦用户切到“自定义”就恢复手工控制。

**Tech Stack:** Python 3.12, PySide6, pytest

---

## File Map

- Modify: `app/ui/pages/bolt_page.py`
  - 新增 UI-only 联动状态字段和预设表
  - 扩展 `setup_case` / `slip_mu_mode` / 材料->E 的联动回调
  - 在 `_build_payload()` 中做隐藏字段的归一化注入/剔除
  - 在 `_apply_input_data()` 中补充新 choice 字段的恢复策略
- Modify: `tests/ui/test_bolt_page.py`
  - 为 3 组联动补 headless UI 回归测试
  - 锁定显隐、payload 归一化和自定义值保留行为

---

## Chunk 1: `setup_case` 驱动工况字段显隐与 payload 归一化

### Task 1: 为 `setup_case` 新增失败测试

**Files:**
- Test: `tests/ui/test_bolt_page.py`
- Modify: `app/ui/pages/bolt_page.py:523-571`
- Modify: `app/ui/pages/bolt_page.py:1005-1067`
- Modify: `app/ui/pages/bolt_page.py:2371-2469`

- [ ] **Step 1: 写失败测试，锁定轴向工况时横向字段隐藏且 payload 归零**

```python
    def test_setup_case_axial_hides_transverse_fields_and_builds_zero_fq(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("轴向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.FA_max"].setText("12000")  # type: ignore[attr-defined]
        page._field_widgets["loads.FQ_max"].setText("800")  # type: ignore[attr-defined]
        page._field_widgets["loads.friction_interfaces"].setText("2")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_friction_coefficient"].setText("0.22")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertFalse(page._field_cards["loads.FQ_max"].isVisible())
        self.assertFalse(page._field_cards["loads.friction_interfaces"].isVisible())
        self.assertFalse(page._field_cards["loads.slip_friction_coefficient"].isVisible())
        self.assertEqual(payload["loads"]["FA_max"], 12000.0)
        self.assertEqual(payload["loads"]["FQ_max"], 0.0)
        self.assertNotIn("friction_interfaces", payload["loads"])
        self.assertNotIn("slip_friction_coefficient", payload["loads"])
```

- [ ] **Step 2: 写失败测试，锁定横向工况时轴向外载隐藏但密封力仍保留**

```python
    def test_setup_case_transverse_hides_axial_force_and_builds_zero_fa(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("横向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.FA_max"].setText("15000")  # type: ignore[attr-defined]
        page._field_widgets["loads.FQ_max"].setText("2500")  # type: ignore[attr-defined]
        page._field_widgets["loads.seal_force_required"].setText("3000")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertFalse(page._field_cards["loads.FA_max"].isVisible())
        self.assertTrue(page._field_cards["loads.seal_force_required"].isVisible())
        self.assertEqual(payload["loads"]["FA_max"], 0.0)
        self.assertEqual(payload["loads"]["FQ_max"], 2500.0)
        self.assertEqual(payload["loads"]["seal_force_required"], 3000.0)
```

- [ ] **Step 3: 写失败测试，组合工况与自由输入不应破坏既有手工值**

```python
    def test_setup_case_combined_and_free_input_keep_all_load_fields_visible(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("轴向+横向")  # type: ignore[attr-defined]
        self.assertTrue(page._field_cards["loads.FA_max"].isVisible())
        self.assertTrue(page._field_cards["loads.FQ_max"].isVisible())
        self.assertTrue(page._field_cards["loads.friction_interfaces"].isVisible())
        self.assertTrue(page._field_cards["loads.slip_friction_coefficient"].isVisible())

        page._field_widgets["operating.setup_case"].setCurrentText("自由输入")  # type: ignore[attr-defined]
        self.assertTrue(page._field_cards["loads.FA_max"].isVisible())
        self.assertTrue(page._field_cards["loads.FQ_max"].isVisible())
```

- [ ] **Step 4: 运行测试确认失败**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "setup_case" -v
```

Expected: FAIL，当前 `setup_case` 只用于回显推断，不控制字段显隐或 payload 归一化。

- [ ] **Step 5: 在 `bolt_page.py` 中添加 `setup_case` 联动规则**

在 `app/ui/pages/bolt_page.py` 中：

1. 在 `BEGINNER_GUIDES` 附近新增常量：

```python
SETUP_CASE_RULES: dict[str, dict[str, tuple[str, ...] | dict[str, float]]] = {
    "轴向载荷": {
        "show": ("loads.FA_max", "loads.seal_force_required"),
        "hide": ("loads.FQ_max", "loads.friction_interfaces", "loads.slip_friction_coefficient"),
        "force_zero": {"FQ_max": 0.0},
    },
    "横向载荷": {
        "show": ("loads.FQ_max", "loads.friction_interfaces", "loads.slip_friction_coefficient", "loads.seal_force_required"),
        "hide": ("loads.FA_max",),
        "force_zero": {"FA_max": 0.0},
    },
    "轴向+横向": {
        "show": ("loads.FA_max", "loads.FQ_max", "loads.seal_force_required", "loads.friction_interfaces", "loads.slip_friction_coefficient"),
        "hide": (),
        "force_zero": {},
    },
    "自由输入": {
        "show": ("loads.FA_max", "loads.FQ_max", "loads.seal_force_required", "loads.friction_interfaces", "loads.slip_friction_coefficient"),
        "hide": (),
        "force_zero": {},
    },
}
```

2. 添加回调方法：

```python
    def _on_setup_case_changed(self, text: str) -> None:
        rules = SETUP_CASE_RULES.get(text, SETUP_CASE_RULES["自由输入"])
        for fid in ("loads.FA_max", "loads.FQ_max", "loads.seal_force_required", "loads.friction_interfaces", "loads.slip_friction_coefficient"):
            card = self._field_cards.get(fid)
            if card is None:
                continue
            card.setVisible(fid in rules["show"])
```

3. 在 `__init__()` 中连接 `operating.setup_case.currentTextChanged`，并在初始化和 `_apply_input_data()` 末尾重跑一次回调。

4. 在 `_build_payload()` 末尾读取 `setup_case`，对隐藏载荷做非破坏性归一化：

```python
        setup_widget = self._field_widgets.get("operating.setup_case")
        if isinstance(setup_widget, QComboBox):
            setup_text = setup_widget.currentText()
            setup_rules = SETUP_CASE_RULES.get(setup_text, SETUP_CASE_RULES["自由输入"])
            loads_section = payload.setdefault("loads", {})
            for key, value in setup_rules["force_zero"].items():
                loads_section[key] = value
            if setup_text == "轴向载荷":
                loads_section.pop("friction_interfaces", None)
                loads_section.pop("slip_friction_coefficient", None)
```

重点：不要清空被隐藏控件中的文本，避免用户切回组合工况时丢值。

- [ ] **Step 6: 运行测试确认通过**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "setup_case" -v
```

Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add app/ui/pages/bolt_page.py tests/ui/test_bolt_page.py
git commit -m "feat(bolt): drive load fields from setup case"
```

---

## Chunk 2: `μT` 跟随 `μK`，将防滑摩擦系数改为“默认少填”

### Task 2: 为 `μT` 增加“跟随 / 单独输入”模式

**Files:**
- Modify: `app/ui/pages/bolt_page.py:556-571`
- Modify: `app/ui/pages/bolt_page.py:760-830`
- Modify: `app/ui/pages/bolt_page.py:1005-1067`
- Modify: `app/ui/pages/bolt_page.py:2066-2268`
- Modify: `app/ui/pages/bolt_page.py:2371-2469`
- Test: `tests/ui/test_bolt_page.py`

- [ ] **Step 1: 写失败测试，默认模式下隐藏 `μT` 并走 core fallback**

```python
    def test_slip_mu_follow_mode_hides_mu_t_and_omits_payload_value(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("横向载荷")  # type: ignore[attr-defined]
        page._field_widgets["tightening.mu_bearing"].setText("0.14")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(page._field_widgets["loads.slip_mu_mode"].currentText(), "跟随支承面摩擦 μK")  # type: ignore[attr-defined]
        self.assertFalse(page._field_cards["loads.slip_friction_coefficient"].isVisible())
        self.assertNotIn("slip_friction_coefficient", payload["loads"])
```

- [ ] **Step 2: 写失败测试，切到“单独输入”后显示并保留手工 `μT`**

```python
    def test_slip_mu_custom_mode_shows_mu_t_and_keeps_manual_value(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.setup_case"].setCurrentText("横向载荷")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_mu_mode"].setCurrentText("单独输入 μT")  # type: ignore[attr-defined]
        page._field_widgets["loads.slip_friction_coefficient"].setText("0.08")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertTrue(page._field_cards["loads.slip_friction_coefficient"].isVisible())
        self.assertEqual(payload["loads"]["slip_friction_coefficient"], 0.08)
```

- [ ] **Step 3: 写失败测试，加载 raw payload 时若已有 `μT`，页面应恢复到“单独输入”**

```python
    def test_apply_raw_payload_with_slip_mu_switches_mode_to_custom(self) -> None:
        page = BoltPage()
        raw = _raw_bolt_payload()
        raw["loads"]["FQ_max"] = 1200.0
        raw["loads"]["slip_friction_coefficient"] = 0.16

        page._apply_input_data(raw)

        self.assertEqual(page._field_widgets["loads.slip_mu_mode"].currentText(), "单独输入 μT")  # type: ignore[attr-defined]
        self.assertTrue(page._field_cards["loads.slip_friction_coefficient"].isVisible())
```

- [ ] **Step 4: 运行测试确认失败**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "slip_mu" -v
```

Expected: FAIL，当前不存在 `loads.slip_mu_mode`，`μT` 总是显式采集。

- [ ] **Step 5: 在 `bolt_page.py` 中引入 UI-only 模式字段**

在 `operating` 章节的 `loads.slip_friction_coefficient` 前插入：

```python
            FieldSpec(
                "loads.slip_mu_mode",
                "防滑摩擦系数来源",
                "-",
                "默认跟随支承面摩擦 μK；只有防滑面状态明显不同才单独输入。",
                mapping=None,
                widget_type="choice",
                options=("跟随支承面摩擦 μK", "单独输入 μT"),
                default="跟随支承面摩擦 μK",
            ),
```

- [ ] **Step 6: 添加联动回调并接入初始化 / 回灌流程**

在 `bolt_page.py` 中新增：

```python
    def _on_slip_mu_mode_changed(self, _text: str = "") -> None:
        mode_widget = self._field_widgets.get("loads.slip_mu_mode")
        mu_card = self._field_cards.get("loads.slip_friction_coefficient")
        if not isinstance(mode_widget, QComboBox) or mu_card is None:
            return
        is_custom = mode_widget.currentText() == "单独输入 μT"
        mu_card.setVisible(is_custom and self._field_cards["loads.slip_friction_coefficient"].isVisible())
```

注意：该显隐要与 Chunk 1 的 `setup_case` 联动结果叠加，不要让“轴向载荷”又把 `μT` 显出来。实现时可把 `_on_setup_case_changed()` 作为总入口，在结尾再调用 `_on_slip_mu_mode_changed()`。

- [ ] **Step 7: 在 `_build_payload()` 中让 follow 模式直接复用 core fallback**

```python
        slip_mode_widget = self._field_widgets.get("loads.slip_mu_mode")
        if isinstance(slip_mode_widget, QComboBox):
            if slip_mode_widget.currentText() == "跟随支承面摩擦 μK":
                payload.setdefault("loads", {}).pop("slip_friction_coefficient", None)
```

不要手动把 `μK` 再复制一份到 `μT`，避免产生两套来源。

- [ ] **Step 8: 在 `_apply_input_data()` 中增加恢复规则**

规则：
- 若 `ui_state["loads.slip_mu_mode"]` 存在，按 UI 状态恢复
- 否则若原始 payload 含 `loads.slip_friction_coefficient`，自动切到“单独输入 μT”
- 否则恢复到默认“跟随支承面摩擦 μK”

- [ ] **Step 9: 运行测试确认通过**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "slip_mu" -v
```

Expected: PASS

- [ ] **Step 10: 提交**

```bash
git add app/ui/pages/bolt_page.py tests/ui/test_bolt_page.py
git commit -m "feat(bolt): default slip friction to follow bearing friction"
```

---

## Chunk 3: 材料选择同步带出弹性模量 `E`

### Task 3: 为单层与多层材料联动补 `E` 预设

**Files:**
- Modify: `app/ui/pages/bolt_page.py:140-177`
- Modify: `app/ui/pages/bolt_page.py:393-407`
- Modify: `app/ui/pages/bolt_page.py:590-623`
- Modify: `app/ui/pages/bolt_page.py:784-795`
- Modify: `app/ui/pages/bolt_page.py:1610-1732`
- Test: `tests/ui/test_bolt_page.py`

- [ ] **Step 1: 写失败测试，螺栓材料切换时同步带出 `E_bolt`**

```python
    def test_bolt_material_updates_alpha_and_e_bolt_presets(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.bolt_material"].setCurrentText("不锈钢")  # type: ignore[attr-defined]

        self.assertEqual(page._field_widgets["operating.alpha_bolt"].text(), "16.0e-6")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["stiffness.E_bolt"].text(), "193000")  # type: ignore[attr-defined]
```

- [ ] **Step 2: 写失败测试，单层被夹件材料切换时同步带出 `alpha_parts` 与 `E_clamped`**

```python
    def test_clamped_material_updates_alpha_and_e_clamped_presets(self) -> None:
        page = BoltPage()

        page._set_check_level("thermal")
        page._apply_check_level_visibility()
        page._field_widgets["operating.clamped_material"].setCurrentText("铝合金")  # type: ignore[attr-defined]

        self.assertEqual(page._field_widgets["operating.alpha_parts"].text(), "23.0e-6")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["stiffness.E_clamped"].text(), "70000")  # type: ignore[attr-defined]
```

- [ ] **Step 3: 写失败测试，多层材料切换时同步带出每层 `E`**

```python
    def test_layer_material_updates_alpha_and_layer_e_presets(self) -> None:
        page = BoltPage()

        page._field_widgets["clamped.part_count"].setCurrentText("2")  # type: ignore[attr-defined]
        page._on_part_count_changed()
        page._field_widgets["clamped.layer_2.material"].setCurrentText("铸铁")  # type: ignore[attr-defined]

        self.assertEqual(page._field_widgets["clamped.layer_2.alpha"].text(), "10.5e-6")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["clamped.layer_2.E"].text(), "120000")  # type: ignore[attr-defined]
```

- [ ] **Step 4: 写失败测试，切回“自定义”后恢复手工输入能力**

```python
    def test_custom_material_unlocks_manual_e_fields(self) -> None:
        page = BoltPage()

        page._field_widgets["operating.clamped_material"].setCurrentText("铝合金")  # type: ignore[attr-defined]
        page._field_widgets["operating.clamped_material"].setCurrentText("自定义")  # type: ignore[attr-defined]

        self.assertFalse(page._field_widgets["operating.alpha_parts"].isReadOnly())  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["operating.alpha_parts"].text(), "")  # type: ignore[attr-defined]
        self.assertEqual(page._field_widgets["stiffness.E_clamped"].text(), "")  # type: ignore[attr-defined]
```

- [ ] **Step 5: 运行测试确认失败**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "material_updates or unlocks_manual_e" -v
```

Expected: FAIL，当前材料联动只更新 `alpha`，不更新任何 `E` 字段。

- [ ] **Step 6: 在 `bolt_page.py` 中新增弹性模量预设表**

在 `THERMAL_EXPANSION_PRESETS` 附近新增：

```python
ELASTIC_MODULUS_PRESETS: dict[str, str] = {
    "钢": "210000",
    "不锈钢": "193000",
    "铝合金": "70000",
    "铸铁": "120000",
}
```

这些值使用当前页面已经采用的工程近似口径，避免引入新的材料库设计。

- [ ] **Step 7: 扩展 3 个现有联动回调，使其同时更新 `E` 字段**

目标行为：
- `_on_bolt_material_changed()` 同时更新 `operating.alpha_bolt` 和 `stiffness.E_bolt`
- `_on_clamped_material_changed()` 同时更新 `operating.alpha_parts` 和 `stiffness.E_clamped`
- `_on_layer_material_changed()` 同时更新 `clamped.layer_n.alpha` 和 `clamped.layer_n.E`

实现骨架：

```python
    def _apply_material_preset(
        self,
        material_text: str,
        alpha_field_id: str,
        e_field_id: str,
    ) -> None:
        alpha_widget = self._field_widgets.get(alpha_field_id)
        e_widget = self._field_widgets.get(e_field_id)
        alpha_preset = THERMAL_EXPANSION_PRESETS.get(material_text)
        e_preset = ELASTIC_MODULUS_PRESETS.get(material_text)
        if isinstance(alpha_widget, QLineEdit):
            if alpha_preset is not None:
                alpha_widget.setText(alpha_preset)
                alpha_widget.setReadOnly(True)
            else:
                alpha_widget.setReadOnly(False)
                alpha_widget.clear()
        if isinstance(e_widget, QLineEdit):
            if e_preset is not None:
                e_widget.setText(e_preset)
            else:
                e_widget.clear()
```

`E` 字段无需强制 `readOnly=True`，因为工程师可能在预设基础上手调；但切到“自定义”时必须清空预设值，避免误把旧值当自定义值带入。

- [ ] **Step 8: 确认 `_apply_defaults()` 与 `_apply_input_data()` 的重放顺序不会覆盖恢复值**

需要检查两点：
- 默认页初始化后，材料联动会把默认 `E` 重新带出
- raw payload / snapshot 回灌时，先恢复 choice，再允许具体数值覆盖预设；不能让联动把 JSON 中的明确 `E` 值二次抹掉

如果发现恢复顺序冲突，采用与 layer alpha 回灌相同的模式：先触发 material choice，再在 `_apply_input_data()` 中用 payload 中的数值覆盖一次。

- [ ] **Step 9: 运行测试确认通过**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -k "material_updates or unlocks_manual_e" -v
```

Expected: PASS

- [ ] **Step 10: 提交**

```bash
git add app/ui/pages/bolt_page.py tests/ui/test_bolt_page.py
git commit -m "feat(bolt): sync elastic modulus presets from material choices"
```

---

## Chunk 4: 组合验证与收尾

### Task 4: 跑整组 UI 回归并人工核对联动叠加行为

**Files:**
- Verify: `tests/ui/test_bolt_page.py`
- Verify: `app/ui/pages/bolt_page.py`

- [ ] **Step 1: 跑 bolt 页完整 UI 测试**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_page.py -v
```

Expected: 全部 PASS，包括既有回灌、热参数校验、R5 展示语义、详情页去重等回归。

- [ ] **Step 2: 跑 bolt core + UI 相关回归**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
  tests/core/bolt/test_calculator.py \
  tests/core/bolt/test_compliance_model.py \
  tests/ui/test_bolt_page.py -q
```

Expected: 全部 PASS

- [ ] **Step 3: 人工走查 4 个重点场景**

1. `轴向载荷`：确认横向参数隐藏，计算不再强迫填写 `μT`
2. `横向载荷 + 跟随 μK`：确认只填 `μK` 即可跑通
3. `横向载荷 + 单独输入 μT`：确认能覆盖 `μK`
4. `自动柔度 + 材料切换`：确认 `E_bolt / E_clamped / layer.E` 会跟着刷新

- [ ] **Step 4: 提交验证完成的收尾 commit**

```bash
git add app/ui/pages/bolt_page.py tests/ui/test_bolt_page.py
git commit -m "test(bolt): cover input linkage reduction flows"
```

---

## Notes / Guardrails

- `setup_case` 只能影响 UI 显隐和 payload 归一化，不能修改核心公式解释。
- 对被隐藏字段，优先“构建 payload 时归零/剔除”，不要直接清空控件文本。
- `μT` 跟随 `μK` 要复用 core 现有 fallback：`slip_friction_coefficient` 缺省时回退 `mu_bearing`。
- 材料->`E` 联动必须允许手工覆盖；“预设”不等于“锁死”。
- 新增 UI-only choice 字段后，必须补 `_apply_input_data()` 的 raw payload fallback，否则加载旧 JSON 时会出现模式错位。

Plan complete and saved to `docs/superpowers/plans/2026-03-20-bolt-page-input-linkage-reduction.md`. Ready to execute?
