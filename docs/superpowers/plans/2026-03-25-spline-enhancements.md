# 花键模块三项增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为花键模块添加压入力曲线、DIN 5480 标准尺寸查表、AutoCalcCard 蓝色样式一致性。

**Architecture:** 新增 `core/spline/din5480_table.py` 查表数据层；UI 层复用 `PressForceCurveWidget`；所有自动填充字段统一切换 `AutoCalcCard` 样式。

**Tech Stack:** Python 3.12, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-03-25-spline-enhancements-design.md`

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `core/spline/din5480_table.py` | 新增 | DIN 5480 标准花键目录数据 + 查找函数 |
| `tests/core/spline/test_din5480_table.py` | 新增 | 目录数据完整性和查找函数测试 |
| `app/ui/pages/spline_fit_page.py` | 修改 | 查表联动、曲线展示、AutoCalcCard 样式 |
| `tests/ui/test_spline_fit_page.py` | 修改 | UI 联动行为测试 |

---

### Task 1: DIN 5480 查表数据层

**Files:**
- Create: `core/spline/din5480_table.py`
- Create: `tests/core/spline/test_din5480_table.py`

- [ ] **Step 1: 编写 6 个测试**

```python
# tests/core/spline/test_din5480_table.py
import pytest
from core.spline.din5480_table import (
    DIN5480_CATALOG,
    all_designations,
    lookup_by_designation,
)

REQUIRED_KEYS = {
    "designation", "module_mm", "tooth_count", "reference_diameter_mm",
    "tip_diameter_shaft_mm", "root_diameter_shaft_mm", "tip_diameter_hub_mm",
}


class TestDin5480Table:
    def test_catalog_not_empty(self):
        assert len(DIN5480_CATALOG) >= 15

    def test_lookup_known_designation(self):
        result = lookup_by_designation("W 25x1.25x18")
        assert result is not None
        assert result["module_mm"] == 1.25
        assert result["tooth_count"] == 18
        assert result["reference_diameter_mm"] == 25.0

    def test_lookup_unknown_returns_none(self):
        assert lookup_by_designation("W 999x99x99") is None

    def test_all_designations_matches_catalog(self):
        assert len(all_designations()) == len(DIN5480_CATALOG)

    def test_catalog_entries_have_required_keys(self):
        for entry in DIN5480_CATALOG:
            missing = REQUIRED_KEYS - set(entry.keys())
            assert not missing, f"{entry.get('designation', '?')} missing keys: {missing}"

    def test_geometric_consistency(self):
        for entry in DIN5480_CATALOG:
            d = entry["designation"]
            assert entry["root_diameter_shaft_mm"] < entry["tip_diameter_hub_mm"], f"{d}: d_f1 >= d_a2"
            assert entry["tip_diameter_hub_mm"] < entry["tip_diameter_shaft_mm"], f"{d}: d_a2 >= d_a1"
            assert entry["tip_diameter_shaft_mm"] < entry["reference_diameter_mm"], f"{d}: d_a1 >= d_B"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_din5480_table.py -v`
Expected: FAIL (ImportError - module not found)

- [ ] **Step 3: 实现 `core/spline/din5480_table.py`**

```python
"""DIN 5480 involute spline catalog — common W 15~50 sizes.

数据来源：DIN 5480-2:2015 表 1/2 公差带 7H/7e，
d_a1 = d_B - 0.1*m (公差带 e 偏移近似), d_f1 按标准齿根间隙，
d_a2 = d_B - m (内花键齿顶)。实际工程应以采购件实测或目录值为准。
"""

from __future__ import annotations

DIN5480_CATALOG: list[dict] = [
    # 模数 0.8
    {"designation": "W 15x0.8x17", "module_mm": 0.8, "tooth_count": 17,
     "reference_diameter_mm": 15.0, "tip_diameter_shaft_mm": 14.36,
     "root_diameter_shaft_mm": 12.56, "tip_diameter_hub_mm": 12.84},
    {"designation": "W 20x0.8x23", "module_mm": 0.8, "tooth_count": 23,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 19.36,
     "root_diameter_shaft_mm": 17.56, "tip_diameter_hub_mm": 17.84},
    {"designation": "W 25x0.8x30", "module_mm": 0.8, "tooth_count": 30,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 24.56,
     "root_diameter_shaft_mm": 22.56, "tip_diameter_hub_mm": 22.84},
    # 模数 1.0
    {"designation": "W 15x1x13", "module_mm": 1.0, "tooth_count": 13,
     "reference_diameter_mm": 15.0, "tip_diameter_shaft_mm": 14.2,
     "root_diameter_shaft_mm": 12.15, "tip_diameter_hub_mm": 12.5},
    {"designation": "W 20x1x18", "module_mm": 1.0, "tooth_count": 18,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 19.2,
     "root_diameter_shaft_mm": 17.15, "tip_diameter_hub_mm": 17.5},
    {"designation": "W 25x1x23", "module_mm": 1.0, "tooth_count": 23,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 24.2,
     "root_diameter_shaft_mm": 22.15, "tip_diameter_hub_mm": 22.5},
    {"designation": "W 30x1x28", "module_mm": 1.0, "tooth_count": 28,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 29.2,
     "root_diameter_shaft_mm": 27.15, "tip_diameter_hub_mm": 27.5},
    {"designation": "W 35x1x33", "module_mm": 1.0, "tooth_count": 33,
     "reference_diameter_mm": 35.0, "tip_diameter_shaft_mm": 34.2,
     "root_diameter_shaft_mm": 32.15, "tip_diameter_hub_mm": 32.5},
    # 模数 1.25
    {"designation": "W 15x1.25x10", "module_mm": 1.25, "tooth_count": 10,
     "reference_diameter_mm": 15.0, "tip_diameter_shaft_mm": 14.75,
     "root_diameter_shaft_mm": 12.1, "tip_diameter_hub_mm": 12.5},
    {"designation": "W 20x1.25x14", "module_mm": 1.25, "tooth_count": 14,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 19.75,
     "root_diameter_shaft_mm": 17.1, "tip_diameter_hub_mm": 17.5},
    {"designation": "W 25x1.25x18", "module_mm": 1.25, "tooth_count": 18,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 24.75,
     "root_diameter_shaft_mm": 22.1, "tip_diameter_hub_mm": 22.5},
    {"designation": "W 30x1.25x22", "module_mm": 1.25, "tooth_count": 22,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 29.75,
     "root_diameter_shaft_mm": 27.1, "tip_diameter_hub_mm": 27.5},
    {"designation": "W 35x1.25x26", "module_mm": 1.25, "tooth_count": 26,
     "reference_diameter_mm": 35.0, "tip_diameter_shaft_mm": 34.75,
     "root_diameter_shaft_mm": 32.1, "tip_diameter_hub_mm": 32.5},
    {"designation": "W 40x1.25x30", "module_mm": 1.25, "tooth_count": 30,
     "reference_diameter_mm": 40.0, "tip_diameter_shaft_mm": 39.75,
     "root_diameter_shaft_mm": 37.1, "tip_diameter_hub_mm": 37.5},
    {"designation": "W 45x1.25x34", "module_mm": 1.25, "tooth_count": 34,
     "reference_diameter_mm": 45.0, "tip_diameter_shaft_mm": 44.75,
     "root_diameter_shaft_mm": 42.1, "tip_diameter_hub_mm": 42.5},
    {"designation": "W 50x1.25x38", "module_mm": 1.25, "tooth_count": 38,
     "reference_diameter_mm": 50.0, "tip_diameter_shaft_mm": 49.75,
     "root_diameter_shaft_mm": 47.1, "tip_diameter_hub_mm": 47.5},
    # 模数 1.75
    {"designation": "W 20x1.75x9", "module_mm": 1.75, "tooth_count": 9,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 18.9,
     "root_diameter_shaft_mm": 16.35, "tip_diameter_hub_mm": 16.85},
    {"designation": "W 25x1.75x12", "module_mm": 1.75, "tooth_count": 12,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 23.9,
     "root_diameter_shaft_mm": 21.35, "tip_diameter_hub_mm": 21.85},
    {"designation": "W 30x1.75x15", "module_mm": 1.75, "tooth_count": 15,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 28.9,
     "root_diameter_shaft_mm": 26.35, "tip_diameter_hub_mm": 26.85},
    {"designation": "W 35x1.75x18", "module_mm": 1.75, "tooth_count": 18,
     "reference_diameter_mm": 35.0, "tip_diameter_shaft_mm": 33.9,
     "root_diameter_shaft_mm": 31.35, "tip_diameter_hub_mm": 31.85},
    {"designation": "W 45x1.75x24", "module_mm": 1.75, "tooth_count": 24,
     "reference_diameter_mm": 45.0, "tip_diameter_shaft_mm": 43.9,
     "root_diameter_shaft_mm": 41.35, "tip_diameter_hub_mm": 41.85},
    # 模数 2.0
    {"designation": "W 20x2x8", "module_mm": 2.0, "tooth_count": 8,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 18.6,
     "root_diameter_shaft_mm": 16.1, "tip_diameter_hub_mm": 16.5},
    {"designation": "W 25x2x11", "module_mm": 2.0, "tooth_count": 11,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 23.6,
     "root_diameter_shaft_mm": 21.1, "tip_diameter_hub_mm": 21.5},
    {"designation": "W 30x2x13", "module_mm": 2.0, "tooth_count": 13,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 28.6,
     "root_diameter_shaft_mm": 26.1, "tip_diameter_hub_mm": 26.5},
    {"designation": "W 40x2x18", "module_mm": 2.0, "tooth_count": 18,
     "reference_diameter_mm": 40.0, "tip_diameter_shaft_mm": 38.6,
     "root_diameter_shaft_mm": 36.1, "tip_diameter_hub_mm": 36.5},
    {"designation": "W 50x2x23", "module_mm": 2.0, "tooth_count": 23,
     "reference_diameter_mm": 50.0, "tip_diameter_shaft_mm": 48.6,
     "root_diameter_shaft_mm": 46.1, "tip_diameter_hub_mm": 46.5},
    # 模数 2.5
    {"designation": "W 25x2.5x8", "module_mm": 2.5, "tooth_count": 8,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 23.25,
     "root_diameter_shaft_mm": 20.12, "tip_diameter_hub_mm": 20.75},
    {"designation": "W 30x2.5x10", "module_mm": 2.5, "tooth_count": 10,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 28.25,
     "root_diameter_shaft_mm": 25.12, "tip_diameter_hub_mm": 25.75},
    {"designation": "W 40x2.5x14", "module_mm": 2.5, "tooth_count": 14,
     "reference_diameter_mm": 40.0, "tip_diameter_shaft_mm": 38.25,
     "root_diameter_shaft_mm": 35.12, "tip_diameter_hub_mm": 35.75},
    {"designation": "W 50x2.5x18", "module_mm": 2.5, "tooth_count": 18,
     "reference_diameter_mm": 50.0, "tip_diameter_shaft_mm": 48.25,
     "root_diameter_shaft_mm": 45.12, "tip_diameter_hub_mm": 45.75},
]

_LOOKUP: dict[str, dict] = {entry["designation"]: entry for entry in DIN5480_CATALOG}


def lookup_by_designation(designation: str) -> dict | None:
    """返回匹配的记录，未找到返回 None。"""
    return _LOOKUP.get(designation)


def all_designations() -> list[str]:
    """返回所有标准标记名列表，用于 UI 下拉框。"""
    return [entry["designation"] for entry in DIN5480_CATALOG]
```

- [ ] **Step 4: 运行测试确认全绿**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_din5480_table.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add core/spline/din5480_table.py tests/core/spline/test_din5480_table.py
git commit -m "feat(spline): add DIN 5480 standard spline lookup table (W 15-50)"
```

---

### Task 2: 标准花键下拉框 UI 联动

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py`
- Modify: `tests/ui/test_spline_fit_page.py`

- [ ] **Step 1: 在 `spline_fit_page.py` 顶部添加 import**

```python
# 在 from core.spline.calculator import ... 之后添加:
from core.spline.din5480_table import all_designations, lookup_by_designation
```

- [ ] **Step 2: 在花键几何章节 CHAPTERS 中 geometry_mode 之前插入 FieldSpec**

在 `CHAPTERS` 列表的 "花键几何" 章节（第二个 dict）的 `fields` 列表最前面插入：

```python
FieldSpec(
    "spline.standard_designation", "标准花键规格", "-",
    "选择 DIN 5480 标准规格后自动填充几何尺寸；选'自定义'手动输入。",
    widget_type="choice",
    options=tuple(all_designations()) + ("自定义",),
    default="自定义",
),
```

- [ ] **Step 3: 新增 `_on_standard_designation_changed` 方法**

添加模块级常量（与 `SMOOTH_FIT_FIELD_IDS` 同级，放在其后）：

```python
_STANDARD_GEOMETRY_FIELD_IDS: list[str] = [
    "spline.module_mm", "spline.tooth_count", "spline.reference_diameter_mm",
    "spline.tip_diameter_shaft_mm", "spline.root_diameter_shaft_mm",
    "spline.tip_diameter_hub_mm",
]
```

在 `SplineFitPage` 类的 `_on_mode_changed` 方法之后添加方法：

```python
def _on_standard_designation_changed(self, text: str) -> None:
    is_standard = (text != "自定义")
    if is_standard:
        record = lookup_by_designation(text)
        if record is None:
            return
        field_map = {
            "spline.module_mm": str(record["module_mm"]),
            "spline.tooth_count": str(record["tooth_count"]),
            "spline.reference_diameter_mm": str(record["reference_diameter_mm"]),
            "spline.tip_diameter_shaft_mm": str(record["tip_diameter_shaft_mm"]),
            "spline.root_diameter_shaft_mm": str(record["root_diameter_shaft_mm"]),
            "spline.tip_diameter_hub_mm": str(record["tip_diameter_hub_mm"]),
        }
        for fid, value in field_map.items():
            w = self._widgets.get(fid)
            if isinstance(w, QLineEdit):
                w.setText(value)
        # 切换 geometry_mode 到"公开/图纸尺寸"
        geo_combo = self._widgets.get("spline.geometry_mode")
        if isinstance(geo_combo, QComboBox):
            idx = geo_combo.findText("公开/图纸尺寸")
            if idx >= 0:
                geo_combo.setCurrentIndex(idx)
    # AutoCalcCard 样式
    for fid in _STANDARD_GEOMETRY_FIELD_IDS:
        self._set_card_disabled(fid, is_standard)
    self._set_card_disabled("spline.geometry_mode", is_standard)
```

- [ ] **Step 4: 在 `__init__` 中连接信号**

在 `__init__` 中 `lc_combo` 信号连接块之前添加（行号会因 Step 2 插入 FieldSpec 而偏移，以代码上下文定位）：

```python
std_combo = self._widgets.get("spline.standard_designation")
if isinstance(std_combo, QComboBox):
    std_combo.currentTextChanged.connect(self._on_standard_designation_changed)
```

- [ ] **Step 5: 在 `tests/ui/test_spline_fit_page.py` 添加联动测试**

```python
def test_standard_designation_autofills_geometry(self, app):
    page = SplineFitPage()
    combo = page._widgets["spline.standard_designation"]
    combo.setCurrentText("W 25x1.25x18")
    assert page._widgets["spline.module_mm"].text() == "1.25"
    assert page._widgets["spline.tooth_count"].text() == "18"
    assert page._widgets["spline.reference_diameter_mm"].text() == "25.0"

def test_standard_designation_custom_restores_editable(self, app):
    page = SplineFitPage()
    combo = page._widgets["spline.standard_designation"]
    combo.setCurrentText("W 25x1.25x18")
    combo.setCurrentText("自定义")
    card = page._field_cards.get("spline.module_mm")
    assert card.objectName() == "SubCard"
```

- [ ] **Step 6: 运行全量测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/spline_fit_page.py tests/ui/test_spline_fit_page.py
git commit -m "feat(spline): add DIN 5480 standard designation dropdown with auto-fill"
```

---

### Task 3: 压入力曲线展示

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py`

- [ ] **Step 1: 添加 import**

```python
from app.ui.widgets.press_force_curve import PressForceCurveWidget
```

- [ ] **Step 2: 在 `__init__` 中初始化 `self.curve_widget = None`**

在 `self._last_payload: dict | None = None` 行之后添加：

```python
self.curve_widget: PressForceCurveWidget | None = None
```

- [ ] **Step 3: 在 `_build_result_chapter` 末尾（`layout.addWidget(card)` 循环之后）添加曲线 widget**

```python
# 在 _build_result_chapter 方法末尾（for 循环之后、方法结束前）添加:
self.curve_widget = PressForceCurveWidget()
self.curve_widget.setVisible(False)
layout.addWidget(self.curve_widget)
```

- [ ] **Step 4: 在 `_display_result` 中填充曲线数据**

在 `_display_result` 方法中，场景 B 显示逻辑之后（`b_detail.setText(...)` 之后），添加：

```python
# 在 scenario_b 存在的分支中:
curve = b["press_force_curve"]
self.curve_widget.set_curve(
    curve["interference_um"],
    curve["force_n"],
    curve["delta_min_um"],
    curve["delta_max_um"],
    curve.get("delta_required_um", 0.0),
)
self.curve_widget.setVisible(True)
```

在 `else` 分支（"未启用"）中：

```python
self.curve_widget.setVisible(False)
```

- [ ] **Step 5: 在 `_on_mode_changed` 末尾隐藏曲线**

```python
# 在 _on_mode_changed 方法末尾追加:
if self.curve_widget is not None:
    self.curve_widget.setVisible(False)
```

- [ ] **Step 6: 运行全量测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/spline_fit_page.py
git commit -m "feat(spline): display press force curve for scenario B"
```

---

### Task 4: AutoCalcCard 蓝色样式一致性

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py`
- Modify: `tests/ui/test_spline_fit_page.py`

- [ ] **Step 1: 重构 `_on_load_condition_changed`**

```python
def _on_load_condition_changed(self, text: str) -> None:
    p_zul = LOAD_CONDITION_P_ZUL.get(text)
    if p_zul is not None:
        w = self._widgets.get("spline.p_allowable_mpa")
        if isinstance(w, QLineEdit):
            w.setText(str(p_zul))
        self._set_card_disabled("spline.p_allowable_mpa", True)
    else:
        # "自定义"
        self._set_card_disabled("spline.p_allowable_mpa", False)
```

- [ ] **Step 2: 重构 `_on_material_changed`**

```python
def _on_material_changed(self, field_prefix: str, material_name: str) -> None:
    material = MATERIAL_LIBRARY.get(material_name)
    e_fid = f"{field_prefix}_e_mpa"
    nu_fid = f"{field_prefix}_nu"
    if material is None:
        # "自定义"：恢复可编辑（仅联合模式下生效）
        if MODE_MAP.get(self._get_value("mode")) == "combined":
            self._set_card_disabled(e_fid, False)
            self._set_card_disabled(nu_fid, False)
        return
    # 非自定义：自动填充 + 蓝色样式
    e_widget = self._widgets.get(e_fid)
    nu_widget = self._widgets.get(nu_fid)
    if isinstance(e_widget, QLineEdit):
        e_widget.setText(str(material["e_mpa"]))
    if isinstance(nu_widget, QLineEdit):
        nu_widget.setText(str(material["nu"]))
    self._set_card_disabled(e_fid, True)
    self._set_card_disabled(nu_fid, True)
```

- [ ] **Step 3: 在 `_on_mode_changed` 末尾重新触发联动**

在 `_on_mode_changed` 末尾追加（在 curve_widget 隐藏之前）：

```python
# 模式切换后重新触发材料/工况联动以刷新 AutoCalcCard 样式
if is_combined:
    shaft_mat = self._widgets.get("smooth_materials.shaft_material")
    if isinstance(shaft_mat, QComboBox):
        self._on_material_changed("smooth_materials.shaft", shaft_mat.currentText())
    hub_mat = self._widgets.get("smooth_materials.hub_material")
    if isinstance(hub_mat, QComboBox):
        self._on_material_changed("smooth_materials.hub", hub_mat.currentText())
```

- [ ] **Step 4: 在 `__init__` 中初始触发 p_zul 样式**

在已有的 `lc_combo` 信号连接块中，**在 `connect` 调用之后追加一行**初始触发（不要重复 connect）：

```python
# 已有代码:
# lc_combo.currentTextChanged.connect(self._on_load_condition_changed)
# 追加这一行:
self._on_load_condition_changed(lc_combo.currentText())
```

- [ ] **Step 5: 添加 AutoCalcCard 样式测试**

在 `tests/ui/test_spline_fit_page.py` 追加：

```python
def test_load_condition_autofills_with_blue_style(self, app):
    page = SplineFitPage()
    lc = page._widgets["spline.load_condition"]
    lc.setCurrentText("固定连接，静载，调质钢")
    card = page._field_cards.get("spline.p_allowable_mpa")
    assert card.objectName() == "AutoCalcCard"
    # 切自定义恢复
    lc.setCurrentText("自定义")
    assert card.objectName() == "SubCard"

def test_material_autofills_with_blue_style(self, app):
    page = SplineFitPage()
    shaft_mat = page._widgets["smooth_materials.shaft_material"]
    shaft_mat.setCurrentText("40Cr")
    e_card = page._field_cards.get("smooth_materials.shaft_e_mpa")
    nu_card = page._field_cards.get("smooth_materials.shaft_nu")
    assert e_card.objectName() == "AutoCalcCard"
    assert nu_card.objectName() == "AutoCalcCard"
    # 切自定义恢复
    shaft_mat.setCurrentText("自定义")
    assert e_card.objectName() == "SubCard"
    assert nu_card.objectName() == "SubCard"

def test_standard_designation_autofills_geometry_with_blue_style(self, app):
    page = SplineFitPage()
    combo = page._widgets["spline.standard_designation"]
    combo.setCurrentText("W 25x1.25x18")
    for fid in ["spline.module_mm", "spline.tooth_count", "spline.reference_diameter_mm"]:
        card = page._field_cards.get(fid)
        assert card.objectName() == "AutoCalcCard", f"{fid} should be AutoCalcCard"
    # 切自定义恢复
    combo.setCurrentText("自定义")
    for fid in ["spline.module_mm", "spline.tooth_count", "spline.reference_diameter_mm"]:
        card = page._field_cards.get(fid)
        assert card.objectName() == "SubCard", f"{fid} should be SubCard"
```

- [ ] **Step 6: 运行全量测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/spline_fit_page.py tests/ui/test_spline_fit_page.py
git commit -m "fix(spline): apply AutoCalcCard blue style to all auto-filled fields"
```
