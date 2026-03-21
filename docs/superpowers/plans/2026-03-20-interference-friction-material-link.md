# 过盈配合摩擦系数-材料联动 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据轴/轮毂材料配对和表面状态，自动推荐 DIN 7190-1 经验摩擦系数，并在字段旁显示来源标签。

**Architecture:** 纯 UI 层功能。新增常量表（MATERIAL_CATEGORY, FRICTION_TABLE 等）和 FieldSpec 到 interference_fit_page.py，在 `_create_chapter_page` 中为摩擦字段创建 RefBadge，在 `_register_material_bindings` 末尾追加联动信号。theme.py 新增 RefBadge 样式。calculator 层不改动。

**Tech Stack:** Python 3.12, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-03-20-interference-friction-material-link-design.md`

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `app/ui/theme.py:293` | Modify | 新增 RefBadge QSS 样式 |
| `app/ui/pages/interference_fit_page.py:47-73` | Modify | 新增常量 MATERIAL_CATEGORY, SURFACE_CONDITIONS, FRICTION_TABLE, CATEGORY_DISPLAY |
| `app/ui/pages/interference_fit_page.py:362-428` | Modify | 在"摩擦与粗糙度"章节 fields 列表最前面插入 surface_condition FieldSpec |
| `app/ui/pages/interference_fit_page.py:636-720` | Modify | __init__ 新增 `_ref_badges`, `_friction_ref_values`；信号注册追加 |
| `app/ui/pages/interference_fit_page.py:732-786` | Modify | `_create_chapter_page` 中为摩擦字段创建 RefBadge |
| `app/ui/pages/interference_fit_page.py:966-973` | Modify | `_register_material_bindings` 末尾追加三条 friction 联动信号 |
| `app/ui/pages/interference_fit_page.py` (new methods) | Modify | 新增 `_sync_friction_from_material`, `_check_friction_modified`, `_update_ref_badge` |
| `tests/ui/test_interference_page.py` | Modify | 新增 6 个测试 |

---

### Task 1: RefBadge QSS 样式

**Files:**
- Modify: `app/ui/theme.py:293` (在 WaitBadge 后追加)
- Test: 目视 / 已有测试不回归

- [ ] **Step 1: 在 theme.py WaitBadge 样式块之后追加 RefBadge 样式**

在 `QLabel#WaitBadge { ... }` 块（line 285-293）之后，`QStatusBar` 块之前，追加：

```python
        QLabel#RefBadge {
            background-color: #E8E3DA;
            color: #6B665E;
            border: 1px solid #D9D3CA;
            border-radius: 10px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: 600;
        }
```

- [ ] **Step 2: 运行现有测试确认不回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -v`
Expected: 所有现有测试 PASS

- [ ] **Step 3: Commit**

```bash
git add app/ui/theme.py
git commit -m "style: add RefBadge QSS for friction reference labels"
```

---

### Task 2: 常量表与 FieldSpec

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] **Step 1: 在 MATERIAL_LIBRARY 块之后（line 56 附近）新增四个常量**

```python
MATERIAL_CATEGORY: dict[str, str] = {
    "45钢": "steel",
    "40Cr": "steel",
    "42CrMo": "steel",
    "QT500-7": "cast_iron",
    "灰铸铁 HT250": "cast_iron",
    "铝合金 6061-T6": "aluminum",
}

SURFACE_CONDITIONS: tuple[str, ...] = ("干摩擦", "轻油润滑", "MoS2 润滑脂", "自定义")

FRICTION_TABLE: dict[tuple[frozenset[str], str], dict[str, float]] = {
    (frozenset({"steel", "steel"}), "干摩擦"): {"mu_torque": 0.15, "mu_axial": 0.12, "mu_assembly": 0.12},
    (frozenset({"steel", "steel"}), "轻油润滑"): {"mu_torque": 0.11, "mu_axial": 0.08, "mu_assembly": 0.08},
    (frozenset({"steel", "steel"}), "MoS2 润滑脂"): {"mu_torque": 0.08, "mu_axial": 0.06, "mu_assembly": 0.06},
    (frozenset({"steel", "cast_iron"}), "干摩擦"): {"mu_torque": 0.12, "mu_axial": 0.10, "mu_assembly": 0.10},
    (frozenset({"steel", "cast_iron"}), "轻油润滑"): {"mu_torque": 0.09, "mu_axial": 0.07, "mu_assembly": 0.07},
    (frozenset({"steel", "cast_iron"}), "MoS2 润滑脂"): {"mu_torque": 0.07, "mu_axial": 0.05, "mu_assembly": 0.05},
    (frozenset({"steel", "aluminum"}), "干摩擦"): {"mu_torque": 0.12, "mu_axial": 0.10, "mu_assembly": 0.10},
    (frozenset({"steel", "aluminum"}), "轻油润滑"): {"mu_torque": 0.08, "mu_axial": 0.06, "mu_assembly": 0.06},
    (frozenset({"steel", "aluminum"}), "MoS2 润滑脂"): {"mu_torque": 0.06, "mu_axial": 0.04, "mu_assembly": 0.04},
    (frozenset({"cast_iron", "cast_iron"}), "干摩擦"): {"mu_torque": 0.12, "mu_axial": 0.10, "mu_assembly": 0.10},
    (frozenset({"cast_iron", "cast_iron"}), "轻油润滑"): {"mu_torque": 0.08, "mu_axial": 0.06, "mu_assembly": 0.06},
    (frozenset({"cast_iron", "cast_iron"}), "MoS2 润滑脂"): {"mu_torque": 0.06, "mu_axial": 0.04, "mu_assembly": 0.04},
    (frozenset({"cast_iron", "aluminum"}), "干摩擦"): {"mu_torque": 0.10, "mu_axial": 0.08, "mu_assembly": 0.08},
    (frozenset({"cast_iron", "aluminum"}), "轻油润滑"): {"mu_torque": 0.07, "mu_axial": 0.05, "mu_assembly": 0.05},
    (frozenset({"cast_iron", "aluminum"}), "MoS2 润滑脂"): {"mu_torque": 0.05, "mu_axial": 0.04, "mu_assembly": 0.04},
    (frozenset({"aluminum", "aluminum"}), "干摩擦"): {"mu_torque": 0.10, "mu_axial": 0.08, "mu_assembly": 0.08},
    (frozenset({"aluminum", "aluminum"}), "轻油润滑"): {"mu_torque": 0.07, "mu_axial": 0.05, "mu_assembly": 0.05},
    (frozenset({"aluminum", "aluminum"}), "MoS2 润滑脂"): {"mu_torque": 0.05, "mu_axial": 0.04, "mu_assembly": 0.04},
}

CATEGORY_DISPLAY: dict[str, str] = {
    "steel": "钢",
    "cast_iron": "铸铁",
    "aluminum": "铝",
}

_FRICTION_MU_FIELDS: tuple[str, ...] = (
    "friction.mu_torque",
    "friction.mu_axial",
    "friction.mu_assembly",
)
```

- [ ] **Step 2: 在 CHAPTERS 的"摩擦与粗糙度"章节 fields 列表最前面插入 surface_condition FieldSpec**

在 `interference_fit_page.py` 的 CHAPTERS 列表中，`"title": "摩擦与粗糙度"` 章节的 `"fields"` 列表开头（在 `friction.mu_torque` FieldSpec 之前）插入：

```python
            FieldSpec(
                "friction.surface_condition",
                "表面状态",
                "-",
                "配合面润滑状态，与材料配对共同决定推荐摩擦系数。",
                widget_type="choice",
                options=SURFACE_CONDITIONS,
                default="干摩擦",
            ),
```

- [ ] **Step 3: 运行现有测试确认不回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -v`
Expected: 所有现有测试 PASS

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/interference_fit_page.py
git commit -m "feat: add friction lookup constants and surface_condition FieldSpec"
```

---

### Task 3: RefBadge 创建与实例变量

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] **Step 1: 在 `__init__` 中新增实例变量**

在 `self.roughness_warning_text: QLabel | None = None`（line 650 附近）之后追加：

```python
        self._ref_badges: dict[str, QLabel] = {}
        self._friction_ref_values: dict[str, float] = {}
```

- [ ] **Step 2: 在 `_create_chapter_page` 的字段循环中，为 _FRICTION_MU_FIELDS 创建 RefBadge**

在 `_create_chapter_page` 方法中，`row.addWidget(hint, 1, 0, 1, 3)` 之后、`form_layout.addWidget(field_card)` 之前，追加：

```python
            if spec.field_id in _FRICTION_MU_FIELDS:
                ref_badge = QLabel("", field_card)
                ref_badge.setObjectName("RefBadge")
                ref_badge.setVisible(False)
                row.addWidget(ref_badge, 2, 0, 1, 3)
                self._ref_badges[spec.field_id] = ref_badge
```

- [ ] **Step 3: 运行现有测试确认不回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -v`
Expected: 所有现有测试 PASS

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/interference_fit_page.py
git commit -m "feat: create RefBadge widgets for friction fields"
```

---

### Task 4: 联动方法 + 信号注册

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] **Step 1: 在 `_register_material_bindings` 末尾追加联动信号**

在 `_register_material_bindings` 方法的最后（现有 for 循环之后）追加：

```python
        # Friction coefficient auto-fill from material pair + surface condition
        for fid in ("materials.shaft_material", "materials.hub_material", "friction.surface_condition"):
            combo = self._field_widgets.get(fid)
            if isinstance(combo, QComboBox):
                combo.currentTextChanged.connect(lambda _t: self._sync_friction_from_material())
```

- [ ] **Step 2: 新增 `_sync_friction_from_material` 方法**

在 `_apply_material_selection` 方法之后追加：

```python
    def _sync_friction_from_material(self) -> None:
        shaft_combo = self._field_widgets.get("materials.shaft_material")
        hub_combo = self._field_widgets.get("materials.hub_material")
        surface_combo = self._field_widgets.get("friction.surface_condition")
        if not all(isinstance(c, QComboBox) for c in (shaft_combo, hub_combo, surface_combo)):
            return

        cat_shaft = MATERIAL_CATEGORY.get(shaft_combo.currentText().strip())
        cat_hub = MATERIAL_CATEGORY.get(hub_combo.currentText().strip())
        surface = surface_combo.currentText().strip()

        if cat_shaft is None or cat_hub is None or surface == "自定义":
            for fid in _FRICTION_MU_FIELDS:
                badge = self._ref_badges.get(fid)
                if badge is not None:
                    badge.setVisible(False)
            return

        key = (frozenset({cat_shaft, cat_hub}), surface)
        entry = FRICTION_TABLE.get(key)
        if entry is None:
            for fid in _FRICTION_MU_FIELDS:
                badge = self._ref_badges.get(fid)
                if badge is not None:
                    badge.setVisible(False)
            return

        cat_a = CATEGORY_DISPLAY.get(cat_shaft, cat_shaft)
        cat_b = CATEGORY_DISPLAY.get(cat_hub, cat_hub)
        source_text = f"DIN 7190-1 参考 \u00b7 {cat_a}/{cat_b} \u00b7 {surface}"

        self._friction_ref_values.clear()
        for fid in _FRICTION_MU_FIELDS:
            mu_key = fid.split(".")[-1]  # mu_torque / mu_axial / mu_assembly
            value = entry[mu_key]
            self._friction_ref_values[fid] = value

        # Block textChanged signals during batch fill to avoid intermediate badge churn
        mu_widgets = []
        for fid in _FRICTION_MU_FIELDS:
            w = self._field_widgets.get(fid)
            if isinstance(w, QLineEdit):
                w.blockSignals(True)
                mu_widgets.append(w)

        for fid in _FRICTION_MU_FIELDS:
            mu_key = fid.split(".")[-1]
            value = self._friction_ref_values[fid]
            widget = self._field_widgets.get(fid)
            if isinstance(widget, QLineEdit):
                widget.setText(f"{value:.2f}")
            badge = self._ref_badges.get(fid)
            if badge is not None:
                badge.setText(source_text)
                badge.setVisible(True)

        for w in mu_widgets:
            w.blockSignals(False)
```

- [ ] **Step 3: 新增 `_check_friction_modified` 方法**

在 `_sync_friction_from_material` 之后追加：

```python
    def _check_friction_modified(self) -> None:
        if not self._friction_ref_values:
            return
        shaft_combo = self._field_widgets.get("materials.shaft_material")
        hub_combo = self._field_widgets.get("materials.hub_material")
        surface_combo = self._field_widgets.get("friction.surface_condition")
        if not all(isinstance(c, QComboBox) for c in (shaft_combo, hub_combo, surface_combo)):
            return
        cat_shaft = MATERIAL_CATEGORY.get(shaft_combo.currentText().strip())
        cat_hub = MATERIAL_CATEGORY.get(hub_combo.currentText().strip())
        surface = surface_combo.currentText().strip()
        if cat_shaft is None or cat_hub is None or surface == "自定义":
            return
        cat_a = CATEGORY_DISPLAY.get(cat_shaft, cat_shaft)
        cat_b = CATEGORY_DISPLAY.get(cat_hub, cat_hub)
        source_text = f"DIN 7190-1 参考 \u00b7 {cat_a}/{cat_b} \u00b7 {surface}"

        for fid in _FRICTION_MU_FIELDS:
            ref = self._friction_ref_values.get(fid)
            if ref is None:
                continue
            widget = self._field_widgets.get(fid)
            badge = self._ref_badges.get(fid)
            if badge is None or not isinstance(widget, QLineEdit):
                continue
            try:
                current = float(widget.text())
            except (ValueError, TypeError):
                badge.setText(f"已修改（参考值 {ref}）")
                continue
            if abs(current - ref) < 1e-9:
                badge.setText(source_text)
            else:
                badge.setText(f"已修改（参考值 {ref}）")
```

- [ ] **Step 4: 在 `_register_material_bindings` 末尾为三个摩擦 QLineEdit 连接 textChanged 信号**

在 Step 1 追加的信号之后继续追加：

```python
        # Detect manual edits to friction fields
        for fid in _FRICTION_MU_FIELDS:
            widget = self._field_widgets.get(fid)
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _t: self._check_friction_modified())
```

- [ ] **Step 5: 在 `__init__` 中 `_apply_defaults()` 之后追加一行调用**

在 `self._apply_defaults()`（line 715 附近）之后、`self._load_sample(...)` 之前，追加：

```python
        self._sync_friction_from_material()
```

注意：实际上 `_load_sample` 会调用 `_apply_input_data` 然后 `_sync_material_inputs` 等，最终 `currentTextChanged` 信号会自动触发 `_sync_friction_from_material`，所以这行实际上是保险。

- [ ] **Step 6: 运行现有测试确认不回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -v`
Expected: 所有现有测试 PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/interference_fit_page.py
git commit -m "feat: wire friction-material linkage and modified detection"
```

---

### Task 5: _clear 中清理 RefBadge 状态

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] **Step 1: 在 `_clear` 方法中 `_apply_defaults()` 之前追加 RefBadge 清理**

在 `self._apply_defaults()` **之前**追加：

```python
        self._friction_ref_values.clear()
        for badge in self._ref_badges.values():
            badge.setVisible(False)
```

顺序很重要：先清空旧状态，再让 `_apply_defaults()` 重置下拉默认值（"45钢"+"干摩擦"），其 `currentTextChanged` 信号会自动触发 `_sync_friction_from_material()` 重新查表填入并显示 RefBadge。若放在 `_apply_defaults()` 之后，会把信号刚填充的状态又清掉。

- [ ] **Step 2: 运行测试确认**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/interference_fit_page.py
git commit -m "fix: clear RefBadge state on parameter reset"
```

---

### Task 6: 加载兼容 — surface_condition 缺失时默认"自定义"

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] **Step 1: 在 `_apply_input_data` 中处理缺失 surface_condition**

找到 `_apply_input_data` 方法（line 1518）。该方法先调用 `self._clear()`（line 1525），再遍历 field specs 恢复字段值。`_clear()` 会把 surface_condition 重置为"干摩擦"（默认值），导致 45钢+干摩擦 联动自动填入摩擦值。

对于不含 surface_condition 的旧 JSON，需要在 `_clear()` 之后、for 循环之前，将 surface_condition 设为"自定义"以禁止联动覆盖。如果 JSON 中有 `ui_state["friction.surface_condition"]`，for 循环会将其覆盖回正确值。

在 `self._clear()`（line 1525）和 `legacy_repeated_mode = None`（line 1526）之间插入：

```python
        # Default surface condition to "自定义" before restoring fields;
        # will be overwritten if present in ui_state during the for-loop.
        sc_widget = self._field_widgets.get("friction.surface_condition")
        if isinstance(sc_widget, QComboBox):
            sc_widget.setCurrentText("自定义")
```

- [ ] **Step 2: 运行测试确认**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/interference_fit_page.py
git commit -m "fix: default surface_condition to custom when loading legacy JSON"
```

---

### Task 7: 测试 — 材料联动填充

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_friction_sync_steel_steel_dry**

```python
    def test_friction_sync_steel_steel_dry(self) -> None:
        """45钢/45钢 + 干摩擦 → 自动填入 0.15/0.12/0.12，RefBadge 可见且含来源文本。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.12")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.12")

        badge = page._ref_badges["friction.mu_torque"]
        self.assertTrue(badge.isVisible())
        self.assertIn("DIN 7190-1", badge.text())
        self.assertIn("钢/钢", badge.text())
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_friction_sync_steel_steel_dry -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: friction sync steel/steel dry"
```

---

### Task 8: 测试 — 手改后 RefBadge 变"已修改"

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_friction_ref_badge_modified_on_manual_edit**

```python
    def test_friction_ref_badge_modified_on_manual_edit(self) -> None:
        """手改 mu_torque 后 RefBadge 显示"已修改（参考值 0.15）"。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        page._field_widgets["friction.mu_torque"].setText("0.16")

        badge = page._ref_badges["friction.mu_torque"]
        self.assertTrue(badge.isVisible())
        self.assertIn("已修改", badge.text())
        self.assertIn("0.15", badge.text())
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_friction_ref_badge_modified_on_manual_edit -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: RefBadge shows modified after manual edit"
```

---

### Task 9: 测试 — 自定义材料不触发

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_friction_sync_custom_material_no_autofill**

```python
    def test_friction_sync_custom_material_no_autofill(self) -> None:
        """轴材料切到"自定义"→ RefBadge 隐藏，摩擦字段值不变。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")
        # Now values are 0.15/0.12/0.12

        page._field_widgets["materials.shaft_material"].setCurrentText("自定义")

        # Values should NOT be changed
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")
        # RefBadge should be hidden
        badge = page._ref_badges["friction.mu_torque"]
        self.assertFalse(badge.isVisible())
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_friction_sync_custom_material_no_autofill -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: custom material hides RefBadge without changing values"
```

---

### Task 10: 测试 — 切换表面状态更新值

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_friction_sync_surface_condition_change**

```python
    def test_friction_sync_surface_condition_change(self) -> None:
        """切换表面状态从干摩擦到轻油润滑 → 值更新。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("45钢")
        page._field_widgets["materials.hub_material"].setCurrentText("45钢")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")

        page._field_widgets["friction.surface_condition"].setCurrentText("轻油润滑")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.11")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.08")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.08")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertIn("DIN 7190-1", badge.text())
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_friction_sync_surface_condition_change -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: surface condition change updates friction values"
```

---

### Task 11: 测试 — frozenset 对称性 + 铝/铝配对

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_friction_sync_aluminum_aluminum**

```python
    def test_friction_sync_aluminum_aluminum(self) -> None:
        """铝合金/铝合金 + 干摩擦 → frozenset 相同材料正确查表。"""
        page = InterferenceFitPage()
        page._field_widgets["materials.shaft_material"].setCurrentText("铝合金 6061-T6")
        page._field_widgets["materials.hub_material"].setCurrentText("铝合金 6061-T6")
        page._field_widgets["friction.surface_condition"].setCurrentText("干摩擦")

        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.10")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.08")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.08")
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_friction_sync_aluminum_aluminum -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: aluminum/aluminum frozenset lookup"
```

---

### Task 12: 测试 — 加载旧 JSON 兼容

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_load_legacy_json_no_surface_condition**

```python
    def test_load_legacy_json_no_surface_condition(self) -> None:
        """加载不含 surface_condition 的旧 JSON → 表面状态默认"自定义"，保留原始摩擦值。"""
        page = InterferenceFitPage()

        page._apply_input_data(
            {
                "inputs": {
                    "geometry": {"shaft_d_mm": "40", "hub_outer_d_mm": "80", "fit_length_mm": "45"},
                    "fit": {"delta_min_um": "20", "delta_max_um": "45"},
                    "materials": {
                        "shaft_e_mpa": "210000", "shaft_nu": "0.30", "shaft_yield_mpa": "600",
                        "hub_e_mpa": "210000", "hub_nu": "0.30", "hub_yield_mpa": "320",
                    },
                    "friction": {"mu_torque": "0.18", "mu_axial": "0.16", "mu_assembly": "0.14"},
                    "loads": {
                        "torque_required_nm": "350", "axial_force_required_n": "0",
                        "radial_force_required_n": "0", "bending_moment_required_nm": "0",
                        "application_factor_ka": "1.0",
                    },
                }
            }
        )

        self.assertEqual(
            page._field_widgets["friction.surface_condition"].currentText(),
            "自定义",
        )
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.18")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.16")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.14")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertFalse(badge.isVisible())
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_load_legacy_json_no_surface_condition -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: legacy JSON load preserves friction values"
```

---

### Task 13: 测试 — 清除后 RefBadge 重新出现

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_clear_resets_friction_and_shows_ref_badge**

```python
    def test_clear_resets_friction_and_shows_ref_badge(self) -> None:
        """清除参数 → 默认材料+干摩擦触发联动，RefBadge 重新出现。"""
        page = InterferenceFitPage()
        # Set to custom state first
        page._field_widgets["materials.shaft_material"].setCurrentText("自定义")
        page._field_widgets["friction.mu_torque"].setText("0.99")

        page._clear()

        # After clear, defaults (45钢/45钢/干摩擦) should trigger linkage
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.15")
        badge = page._ref_badges["friction.mu_torque"]
        self.assertTrue(badge.isVisible())
        self.assertIn("DIN 7190-1", badge.text())
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_clear_resets_friction_and_shows_ref_badge -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: clear resets friction and shows RefBadge"
```

---

### Task 14: 测试 — 加载含 surface_condition 的 JSON

**Files:**
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 编写测试 test_load_json_with_surface_condition**

```python
    def test_load_json_with_surface_condition(self) -> None:
        """加载含 surface_condition 的 JSON → 下拉恢复，摩擦值与查表一致。"""
        page = InterferenceFitPage()

        page._apply_input_data(
            {
                "inputs": {
                    "geometry": {"shaft_d_mm": "40", "hub_outer_d_mm": "80", "fit_length_mm": "45"},
                    "fit": {"delta_min_um": "20", "delta_max_um": "45"},
                    "materials": {
                        "shaft_e_mpa": "210000", "shaft_nu": "0.30", "shaft_yield_mpa": "600",
                        "hub_e_mpa": "210000", "hub_nu": "0.30", "hub_yield_mpa": "320",
                    },
                    "friction": {"mu_torque": "0.11", "mu_axial": "0.08", "mu_assembly": "0.08"},
                    "loads": {
                        "torque_required_nm": "350", "axial_force_required_n": "0",
                        "radial_force_required_n": "0", "bending_moment_required_nm": "0",
                        "application_factor_ka": "1.0",
                    },
                },
                "ui_state": {
                    "friction.surface_condition": "轻油润滑",
                    "materials.shaft_material": "45钢",
                    "materials.hub_material": "45钢",
                },
            }
        )

        self.assertEqual(
            page._field_widgets["friction.surface_condition"].currentText(),
            "轻油润滑",
        )
        self.assertEqual(page._field_widgets["friction.mu_torque"].text(), "0.11")
        self.assertEqual(page._field_widgets["friction.mu_axial"].text(), "0.08")
        self.assertEqual(page._field_widgets["friction.mu_assembly"].text(), "0.08")
```

- [ ] **Step 2: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_load_json_with_surface_condition -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/ui/test_interference_page.py
git commit -m "test: load JSON with surface_condition restores linkage"
```

---

### Task 15: 全量测试通过

- [ ] **Step 1: 运行完整测试套件**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: 所有测试 PASS

- [ ] **Step 2: 手动启动应用验证 UI**

Run: `python3 app/main.py`（可选，根据环境决定）
- 切换到过盈配合模块
- "摩擦与粗糙度"章节第一个字段为"表面状态"下拉
- 选择 45钢/45钢 + 干摩擦，验证三个摩擦字段自动填入、RefBadge 可见
- 手改 mu_torque → RefBadge 变为"已修改"
- 切到"自定义"材料 → RefBadge 隐藏

- [ ] **Step 3: Final commit (if any remaining changes)**

```bash
git add -A
git commit -m "feat: friction-material linkage with DIN 7190-1 reference badges"
```
