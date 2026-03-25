# 花键模块三项增强设计

**日期**: 2026-03-25
**范围**: core/spline/, app/ui/pages/spline_fit_page.py, app/ui/widgets/

## 背景

花键模块完成 review 修复后，增加三项功能增强：
1. 场景 B 压入力曲线展示
2. DIN 5480 标准花键尺寸查表
3. 自动填充字段统一使用 AutoCalcCard 蓝色样式

## 增强 1: 压入力曲线

### 现状
场景 B 委托 DIN 7190 计算后，返回值中已包含 `press_force_curve`（`calculator.py:185`），数据格式与过盈模块完全一致。`PressForceCurveWidget`（`app/ui/widgets/press_force_curve.py`）已存在可直接复用。UI 未展示。

### 改动

**文件**: `app/ui/pages/spline_fit_page.py`

1. **import**: 添加 `from app.ui.widgets.press_force_curve import PressForceCurveWidget`

2. **`_build_result_chapter`**: 在场景 B 卡片**之后**（同一 layout 中的独立 sibling widget，非嵌套在 B 卡片内部）添加 `PressForceCurveWidget` 实例，存入 `self.curve_widget`。初始 `setVisible(False)`。

3. **`_display_result`**: 当 `scenario_b` 存在时：
   - `self.curve_widget.set_curve(...)` 填入 `result["scenario_b"]["press_force_curve"]` 数据
   - `self.curve_widget.setVisible(True)`
   - 仅花键模式时 `self.curve_widget.setVisible(False)`

4. **`_on_mode_changed`**: 追加 `self.curve_widget.setVisible(False)`，防止切换到"仅花键"模式后残留上次计算的曲线。

**数据流**: `result["scenario_b"]["press_force_curve"]` → `set_curve(interference_um, force_n, delta_min_um, delta_max_um, delta_required_um)`

## 增强 2: DIN 5480 标准花键尺寸查表

### 新增文件: `core/spline/din5480_table.py`

常量 `DIN5480_CATALOG: list[dict]`，覆盖 W 15~50 常用规格（模数 0.8~2.5，约 20~30 条记录）。每条记录：
```python
{
    "designation": "W 25x1.25x18",    # 标准标记
    "module_mm": 1.25,
    "tooth_count": 18,
    "reference_diameter_mm": 25.0,
    "tip_diameter_shaft_mm": ...,      # d_a1
    "root_diameter_shaft_mm": ...,     # d_f1
    "tip_diameter_hub_mm": ...,        # d_a2
}
```

查找函数:
```python
def lookup_by_designation(designation: str) -> dict | None:
    """返回匹配的记录，未找到返回 None。"""
```

辅助函数:
```python
def all_designations() -> list[str]:
    """返回所有标准标记名列表，用于 UI 下拉框。"""
```

### UI 改动: `app/ui/pages/spline_fit_page.py`

1. 在花键几何章节顶部（geometry_mode 之前）新增一个 FieldSpec:
   - field_id: `"spline.standard_designation"`
   - widget_type: `"choice"`
   - options: `all_designations() + ("自定义",)`
   - default: `"自定义"`
   - mapping: `None`（不参与 payload，纯 UI 联动）

2. 新增 `_on_standard_designation_changed(text: str)`:
   - 若非"自定义"：调用 `lookup_by_designation` 获取记录，自动填充 6 个字段：
     `spline.module_mm`, `spline.tooth_count`, `spline.reference_diameter_mm`,
     `spline.tip_diameter_shaft_mm`, `spline.root_diameter_shaft_mm`, `spline.tip_diameter_hub_mm`
     并将 `spline.geometry_mode` 切为"公开/图纸尺寸"
   - 被填充的 6 个字段 + `spline.geometry_mode` → `_set_card_disabled(fid, True)`（AutoCalcCard 蓝色）
   - 若"自定义"：7 个字段恢复 `_set_card_disabled(fid, False)`

3. 连接信号: `standard_combo.currentTextChanged.connect(self._on_standard_designation_changed)`

### 测试: `tests/core/spline/test_din5480_table.py`

- `test_catalog_not_empty`: 目录非空
- `test_lookup_known_designation`: 已知标记可查到
- `test_lookup_unknown_returns_none`: 未知标记返回 None
- `test_all_designations_matches_catalog`: 列表长度与目录一致
- `test_catalog_entries_have_required_keys`: 每条记录包含所有必需字段
- `test_geometric_consistency`: 每条记录满足 `root_diameter_shaft_mm < tip_diameter_hub_mm < tip_diameter_shaft_mm < reference_diameter_mm`

## 增强 3: AutoCalcCard 蓝色样式一致性

### 3.1 载荷工况联动 → p_zul

**现状**: `_on_load_condition_changed` 填充 p_zul 值，但字段保持普通 SubCard。

**改动**: 在 `_on_load_condition_changed` 中：
- 非"自定义"时：`_set_card_disabled("spline.p_allowable_mpa", True)`
- "自定义"时：`_set_card_disabled("spline.p_allowable_mpa", False)`

### 3.2 材料下拉联动 → E / nu

**现状**: `_on_material_changed` 填充 E 和 nu，但字段保持普通样式。

**改动**: 重构 `_on_material_changed` 方法。当前实现在 `material is None`（自定义）时直接 `return`，新逻辑需在 return 之前先恢复样式：

```python
def _on_material_changed(self, field_prefix: str, material_name: str) -> None:
    material = MATERIAL_LIBRARY.get(material_name)
    e_fid = f"{field_prefix}_e_mpa"
    nu_fid = f"{field_prefix}_nu"
    if material is None:
        # "自定义"：恢复可编辑
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

**优先级规则**: 模式级禁用（`_on_mode_changed` 对 smooth 字段的禁用）优先于自动填充级禁用。`_on_material_changed` 中的 `_set_card_disabled(fid, False)` 仅在当前模式为"联合"时生效。实现方式：在 `_set_card_disabled(fid, False)` 之前检查 `if MODE_MAP.get(self._get_value("mode")) != "combined": return`，或更简洁地：在 `_on_mode_changed` 最后重新触发材料/工况联动以刷新样式。

受影响字段:
- `smooth_materials.shaft_e_mpa`, `smooth_materials.shaft_nu`
- `smooth_materials.hub_e_mpa`, `smooth_materials.hub_nu`

### 3.3 标准花键查表联动（增强 2 新增）

已在增强 2 中描述。选择标准规格时 6+1 个几何字段切为 AutoCalcCard，选"自定义"恢复。

### UI 测试追加

- `test_load_condition_autofills_with_blue_style`: 选择非自定义工况 → p_zul 字段为 AutoCalcCard
- `test_material_autofills_with_blue_style`: 选择非自定义材料 → E/nu 字段为 AutoCalcCard
- `test_standard_designation_autofills_geometry_with_blue_style`: 选择标准规格 → 几何字段为 AutoCalcCard

## 执行顺序

增强 2（查表数据+UI）→ 增强 1（曲线展示）→ 增强 3（AutoCalcCard 样式）

原因：增强 2 新增了标准花键下拉框，增强 3 需要对其设置 AutoCalcCard；增强 1 独立但放中间避免在增强 2/3 之间插入无关改动。

## 不在此次范围内

- DIN 5480 完整规格表（模数 3~10 的大规格）
- 内花键 N 系列的独立查表
- 花键齿根弯曲/剪切校核
- 输入条件持久化
