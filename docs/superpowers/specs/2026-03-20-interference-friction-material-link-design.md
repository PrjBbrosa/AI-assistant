# 过盈配合摩擦系数与材料联动设计

## 概述

在过盈配合模块中，根据轴/轮毂材料配对和表面状态，自动推荐 DIN 7190-1 经验摩擦系数。
推荐值可编辑，字段旁显示内联标签标明来源；用户修改后标签更新为"已修改"。

## 需求

1. 新增"表面状态"下拉（干摩擦 / 轻油润滑 / MoS2 润滑脂 / 自定义）
2. 材料配对 + 表面状态 → 查 DIN 7190-1 表 3 → 自动填入 mu_torque、mu_axial、mu_assembly
3. 摩擦字段保持可编辑（推荐值而非强制值）
4. 每个摩擦字段旁显示 RefBadge 标明值来源，用户修改后变为"已修改（参考值 X）"
5. calculator 层不改动，纯 UI 便利功能

## 数据模型

### 材料类别映射

将 MATERIAL_LIBRARY 中的材料归为三类：

| 类别 | 材料 |
|------|------|
| steel | 45钢、40Cr、42CrMo |
| cast_iron | QT500-7、灰铸铁 HT250 |
| aluminum | 铝合金 6061-T6 |

"自定义"材料不属于任何类别，不触发联动。

```python
MATERIAL_CATEGORY: dict[str, str] = {
    "45钢": "steel",
    "40Cr": "steel",
    "42CrMo": "steel",
    "QT500-7": "cast_iron",
    "灰铸铁 HT250": "cast_iron",
    "铝合金 6061-T6": "aluminum",
}
```

### 表面状态选项

```python
SURFACE_CONDITIONS: tuple[str, ...] = ("干摩擦", "轻油润滑", "MoS2 润滑脂", "自定义")
```

### 摩擦系数查找表

key = (frozenset({category_shaft, category_hub}), surface_condition)
value = {"mu_torque": float, "mu_axial": float, "mu_assembly": float}

查找键使用 frozenset，因此轴/轮毂顺序无关——steel/cast_iron 同时匹配"钢轴+铸铁毂"和"铸铁轴+钢毂"。

DIN 7190-1:2017 表 3 中值，通用经验值，不区分纵压/横装：

| 配对 | 表面状态 | mu_torque | mu_axial | mu_assembly |
|------|----------|-----------|----------|-------------|
| steel/steel | 干摩擦 | 0.15 | 0.12 | 0.12 |
| steel/steel | 轻油润滑 | 0.11 | 0.08 | 0.08 |
| steel/steel | MoS2 润滑脂 | 0.08 | 0.06 | 0.06 |
| steel/cast_iron | 干摩擦 | 0.12 | 0.10 | 0.10 |
| steel/cast_iron | 轻油润滑 | 0.09 | 0.07 | 0.07 |
| steel/cast_iron | MoS2 润滑脂 | 0.07 | 0.05 | 0.05 |
| steel/aluminum | 干摩擦 | 0.12 | 0.10 | 0.10 |
| steel/aluminum | 轻油润滑 | 0.08 | 0.06 | 0.06 |
| steel/aluminum | MoS2 润滑脂 | 0.06 | 0.04 | 0.04 |
| cast_iron/cast_iron | 干摩擦 | 0.12 | 0.10 | 0.10 |
| cast_iron/cast_iron | 轻油润滑 | 0.08 | 0.06 | 0.06 |
| cast_iron/cast_iron | MoS2 润滑脂 | 0.06 | 0.04 | 0.04 |
| cast_iron/aluminum | 干摩擦 | 0.10 | 0.08 | 0.08 |
| cast_iron/aluminum | 轻油润滑 | 0.07 | 0.05 | 0.05 |
| cast_iron/aluminum | MoS2 润滑脂 | 0.05 | 0.04 | 0.04 |
| aluminum/aluminum | 干摩擦 | 0.10 | 0.08 | 0.08 |
| aluminum/aluminum | 轻油润滑 | 0.07 | 0.05 | 0.05 |
| aluminum/aluminum | MoS2 润滑脂 | 0.05 | 0.04 | 0.04 |

## UI 变更

### 新增 FieldSpec

在"摩擦与粗糙度"章节最前面（三个摩擦系数字段之前）插入：

```python
FieldSpec(
    "friction.surface_condition",
    "表面状态",
    "-",
    "配合面润滑状态，与材料配对共同决定推荐摩擦系数。",
    mapping=None,  # 不参与计算 payload
    widget_type="choice",
    options=SURFACE_CONDITIONS,
    default="干摩擦",
)
```

### RefBadge 内联标签

在 mu_torque、mu_axial、mu_assembly 三个字段卡片中，hint 行下方新增一个 QLabel：

- ObjectName: "RefBadge"
- 样式: 复用 WaitBadge 暖灰配色（#E8E3DA bg, #6B665E text），与 WaitBadge 一致的 border-radius 和 font-weight
- 查表命中时: 显示 `DIN 7190-1 参考 · 钢/钢 · 干摩擦`
- 用户手改后: 显示 `已修改（参考值 0.15）`
- 无法查表时: 隐藏
- 存储: `_ref_badges: dict[str, QLabel]`，key 为 field_id（mu_torque/mu_axial/mu_assembly），在章节页构建时创建
- 布局: 在字段卡片 QGridLayout 的 row 2, column 0-2（hint 行下方），`row.addWidget(ref_badge, 2, 0, 1, 3)`

### RefBadge QSS（theme.py 新增）

```css
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

## 联动逻辑

### 触发条件

以下任一变化都触发 `_sync_friction_from_material()`:
- 轴材料下拉变化 (`materials.shaft_material`)
- 轮毂材料下拉变化 (`materials.hub_material`)
- 表面状态下拉变化 (`friction.surface_condition`)

### 触发行为

1. 读取轴材料名 → 查 MATERIAL_CATEGORY → cat_shaft（未命中则 None）
2. 读取轮毂材料名 → 查 MATERIAL_CATEGORY → cat_hub（未命中则 None）
3. 读取表面状态文本
4. 若 cat_shaft is None 或 cat_hub is None 或表面状态为"自定义" → 隐藏所有 RefBadge，不动字段值，return
5. 用 (frozenset({cat_shaft, cat_hub}), surface_condition) 查 FRICTION_TABLE
6. 命中 → 填入三个摩擦字段，记录 `_friction_ref_values`，更新 RefBadge 显示来源
7. 未命中 → 隐藏 RefBadge，不动字段值

### 信号注册

在 `_register_material_bindings()` 末尾追加三条 `currentTextChanged` 连接：
- `materials.shaft_material` → `_sync_friction_from_material`
- `materials.hub_material` → `_sync_friction_from_material`
- `friction.surface_condition` → `_sync_friction_from_material`

（轴/轮毂材料的 currentTextChanged 已连接 `_apply_material_selection`，再追加一条连接到新方法即可，Qt 允许同一信号连接多个槽。）

### "已修改"检测

- `__init__` 中初始化 `_friction_ref_values: dict[str, float] = {}`
- 查表填入后更新 `_friction_ref_values`
- 三个摩擦字段的 textChanged 连接 `_check_friction_modified` 检查函数
- 比较方式：将字段文本 parse 为 float，与参考值做数值比较（epsilon=1e-9），避免 "0.150" vs "0.15" 的字符串误判
- 当前值 ≠ 参考值 → RefBadge 文本变为 `已修改（参考值 X）`
- 当前值 = 参考值 → RefBadge 恢复 DIN 来源文本
- parse 失败（非法输入）→ 视为"已修改"

### 材料类别中文标签

RefBadge 显示时需要把类别翻译为中文：

```python
CATEGORY_DISPLAY: dict[str, str] = {
    "steel": "钢",
    "cast_iron": "铸铁",
    "aluminum": "铝",
}
```

## 清除行为

调用 `_clear()` 时：
- `friction.surface_condition` 随 `_apply_defaults()` 重置为 "干摩擦"
- `_friction_ref_values` 清空为 `{}`
- 所有 RefBadge 隐藏
- `_apply_defaults()` 完成后，材料下拉也会恢复默认值，由 `currentTextChanged` 触发 `_sync_friction_from_material()`，自动重新查表填入

## 加载兼容性

### 保存

`friction.surface_condition` 的 `mapping=None`，因此通过 `build_form_snapshot` 自动持久化到 `ui_state` 区段（与 `roughness.profile`、`fit.mode` 等 mapping=None 字段一致）。

### 加载输入条件 / 测试案例

- JSON 中有 `friction.surface_condition` → 直接恢复下拉选择
- JSON 中没有 → 默认设为"自定义"，不触发自动填充，保留 JSON 中的原始摩擦值
- 旧 JSON 文件完全兼容

## 不变部分

- `core/interference/calculator.py` 不做任何改动
- calculator 接收的 payload 格式不变：friction.mu_torque、friction.mu_axial、friction.mu_assembly
- 表面状态不进入计算 payload

## 涉及文件

| 文件 | 改动 |
|------|------|
| `app/ui/pages/interference_fit_page.py` | 新增常量表（MATERIAL_CATEGORY, SURFACE_CONDITIONS, FRICTION_TABLE, CATEGORY_DISPLAY）、新增 FieldSpec、联动注册与同步逻辑、RefBadge 创建与管理 |
| `app/ui/theme.py` | 新增 RefBadge QSS 样式 |
| `tests/ui/test_interference_page.py` | 新增：材料联动填充测试、手改后"已修改"标签测试、"自定义"不触发测试、加载兼容性测试 |

## 测试计划

1. 选择 45钢/45钢 + 干摩擦 → 验证三个摩擦字段自动填入 0.15/0.12/0.12，RefBadge 显示正确来源
2. 手改 mu_torque 为 0.16 → RefBadge 变为"已修改（参考值 0.15）"
3. 切换表面状态到轻油润滑 → 字段更新，RefBadge 恢复来源文本
4. 切换轴材料到"自定义" → RefBadge 隐藏，摩擦字段值不变
5. 加载不含 surface_condition 的旧 JSON → 表面状态默认"自定义"，摩擦值保持 JSON 原值
6. 加载含 surface_condition 的新 JSON → 下拉恢复，联动正确触发，验证最终摩擦值与查表结果一致
7. 铝合金/铝合金 + 干摩擦 → 验证 frozenset 相同材料配对正确查表
8. 清除参数 → RefBadge 隐藏后重新出现（因为默认材料+干摩擦会重新触发联动）
