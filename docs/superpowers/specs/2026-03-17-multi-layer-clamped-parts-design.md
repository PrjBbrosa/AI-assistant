# 多层被夹件支持设计文档

日期: 2026-03-17
模块: 螺栓连接 (VDI 2230)

## 背景

当前螺栓模块仅支持单层被夹件（单一弹性模量、单一厚度）。实际工程中常见三明治结构，如最后一层螺纹孔、中间两层通孔且材料不同（钢+铝合金）。后端 `compliance_model.py` 已实现多层 δp 串联求和，但 UI 和 calculator 入口未接通。

## 需求

1. `part_count` 改为下拉选项：`1`、`2`、`自定义`
2. 多层模式下每层独立指定：厚度、外径 D_A、弹性模量、材料/热膨胀系数
3. 多层统一使用圆柱体模型
4. 热损失按各层逐层计算再求和，不做加权平均
5. 不显示 total_thickness 汇总

## 设计方案：FieldSpec 静态定义 + 动态显隐

### 1. UI 字段结构 (`bolt_page.py`)

#### part_count 下拉改造

- 从 numeric 改为 `widget_type="choice"`
- 选项：`"1"`, `"2"`, `"自定义"`
- 选"自定义"时显示数字输入框 `clamped.custom_count`（范围 3~5）

#### 字段显隐逻辑

| part_count 值 | 可见字段 |
|---|---|
| **1** | 现有单层字段：`total_thickness`、`D_A`、`stiffness.E_clamped` |
| **2** | 隐藏单层字段，显示 layer_1 和 layer_2 |
| **自定义** | 显示 `custom_count` 输入 + 对应层数的 layer 字段 |

#### 每层 FieldSpec 定义

预定义 layer_1 ~ layer_5，默认全部隐藏，`mapping=None`（由 `_build_payload` 手动处理）。

以 layer_1 为例：
- `clamped.layer_1.thickness` — "第1层厚度"，mm
- `clamped.layer_1.D_A` — "第1层外径 DA"，mm
- `clamped.layer_1.E` — "第1层弹性模量"，MPa
- `clamped.layer_1.material` — "第1层材料"，choice（钢/铝合金/铸铁/不锈钢/自定义）
- `clamped.layer_1.alpha` — "第1层热膨胀系数"，1/K

layer_2 ~ layer_5 结构相同，仅 id 和 label 中的序号递增。

### 2. Payload 构建 (`_build_payload`)

当 `part_count >= 2` 时：
- 不发送 `stiffness.E_clamped`（单层弹性模量）
- 构建 `clamped.layers` 列表：

```python
clamped["layers"] = [
    {
        "model": "cylinder",
        "d_h": bearing_d_inner,   # 所有层共用
        "D_A": layer_i_D_A,
        "l_K": layer_i_thickness,
        "E_clamped": layer_i_E,
    },
    ...
]
```

- `clamped.total_thickness` 由各层厚度求和自动填入（仅供 calculator 内部计算螺栓柔度和嵌入损失使用）
- 各层的 `alpha` 和 `l_K` 组成列表传入 `operating.layer_alphas`

### 3. Calculator 改造 (`calculator.py`)

#### `_resolve_compliance()` 多层分支

```python
elif stiffness.get("auto_compliance"):
    ...
    cl = clamped or {}
    if "layers" in cl:
        # 多层模式：δp 串联求和
        l_K = sum(layer["l_K"] for layer in cl["layers"])
        bolt_r = calculate_bolt_compliance(d, p, l_K, E_bolt)
        delta_s = bolt_r["delta_s"]
        for layer in cl["layers"]:
            layer.setdefault("d_h", d_h)
        clamp_r = calculate_clamped_compliance(layers=cl["layers"])
        delta_p = clamp_r["delta_p"]
    else:
        # 单层模式：保持现有逻辑不变
        ...
```

改动仅在 `auto_compliance` 分支内加 if/else，不影响手动输入路径。

#### 热损失逐层计算

当 `operating.layer_alphas` 存在时：

```python
# 多层热位移
delta_l_parts = sum(
    alpha_i * l_K_i * delta_T
    for alpha_i, l_K_i in zip(layer_alphas, layer_thicknesses)
)
delta_l_bolt = alpha_bolt * l_K_total * delta_T
F_V_thermal = (delta_l_parts - delta_l_bolt) / (delta_s + delta_p)
```

单层模式保持不变。

### 4. 嵌入损失

无需改动。`part_count` 已正确用于接口数计算（通孔 `n = part_count + 2`，螺纹孔 `n = part_count + 1`）。多层模式下 `part_count` 直接从下拉选项或自定义值获取。

### 5. 输入持久化

无需改动存储层。多层数据作为 `clamped.layers` 列表存入 JSON。加载时根据 `layers` 长度恢复 `part_count` 和各层字段。

### 6. 不做的事

- 不改动 `compliance_model.py`（多层逻辑已完整）
- 不改动锥体/套筒模型（多层统一用圆柱体）
- 不新增 `total_thickness` 汇总展示
- 不做加权平均 alpha 自动计算

## 测试策略

### 新增测试 (`tests/test_calculator.py`)

- **多层柔度**：2 层不同材料（钢 E=210000 + 铝 E=70000），验证 δp = δp_1 + δp_2
- **多层热损失**：2 层不同 alpha，验证 Δl = Σ(alpha_i × l_K_i × ΔT)
- **单层回归**：确保现有单层逻辑不受影响

### 已有覆盖

- `tests/test_compliance_model.py` 已有多层测试（钢+铝双层），无需新增

## 改动范围

| 文件 | 改动 |
|---|---|
| `app/ui/pages/bolt_page.py` | `part_count` 改下拉 + 预定义 layer_1~5 FieldSpec + 显隐联动 + `_build_payload` 构建 layers |
| `core/bolt/calculator.py` | `_resolve_compliance()` 加多层分支 + 热损失逐层求和 |
| `tests/test_calculator.py` | 新增多层柔度和热损失测试 |
