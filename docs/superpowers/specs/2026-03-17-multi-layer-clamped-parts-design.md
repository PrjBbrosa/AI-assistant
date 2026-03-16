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
5. UI 不显示 total_thickness 汇总

## 设计方案：FieldSpec 静态定义 + 动态显隐

### 1. UI 字段结构 (`bolt_page.py`)

#### part_count 下拉改造

- 从 numeric 改为 `widget_type="choice"`
- 选项：`"1"`, `"2"`, `"自定义"`
- 选"自定义"时显示数字输入框 `clamped.custom_count`（范围 3~5）
- `mapping=None`（不参与自动 payload 构建，由 `_build_payload` 手动解析为整数）

#### `_build_payload` 中 part_count 的解析

`part_count` 下拉值为中文字符串，必须在 `_build_payload` 中转换为整数后再放入 payload：
- 选 "1" → `part_count = 1`
- 选 "2" → `part_count = 2`
- 选 "自定义" → 读取 `clamped.custom_count` 控件的值，转为整数

最终 payload 中 `clamped.part_count` 始终为整数，无论哪种模式。

#### 字段显隐逻辑

| part_count 值 | 可见字段 |
|---|---|
| **1** | 现有单层字段：`total_thickness`、`D_A`、`stiffness.E_clamped`；隐藏 `custom_count` 和所有 layer 字段 |
| **2** | 隐藏单层字段（`total_thickness`、`D_A`、`stiffness.E_clamped`）和 `custom_count`，显示 layer_1 和 layer_2 |
| **自定义** | 隐藏单层字段，显示 `custom_count` 输入 + 对应层数的 layer 字段 |

同时，多层模式下隐藏工况章节的 `operating.clamped_material` 和 `operating.alpha_parts`（单层材料/alpha），因为每层已有独立的材料和 alpha。

#### 每层 FieldSpec 定义

预定义 layer_1 ~ layer_5，默认全部隐藏，`mapping=None`（由 `_build_payload` 手动处理）。

以 layer_1 为例：
- `clamped.layer_1.thickness` — "第1层厚度"，mm
- `clamped.layer_1.D_A` — "第1层外径 DA"，mm
- `clamped.layer_1.E` — "第1层弹性模量"，MPa
- `clamped.layer_1.material` — "第1层材料"，choice（钢/铝合金/铸铁/不锈钢/自定义）→ 选材料自动填充 alpha
- `clamped.layer_1.alpha` — "第1层热膨胀系数"，1/K

layer_2 ~ layer_5 结构相同，仅 id 和 label 中的序号递增。

### 2. Payload 构建 (`_build_payload`)

#### 单层模式 (part_count == 1)

与现有逻辑完全一致，不做任何改动。`stiffness.E_clamped`、`clamped.total_thickness`、`clamped.D_A` 正常发送。`operating.alpha_parts` 正常发送。

#### 多层模式 (part_count >= 2)

- 不发送 `stiffness.E_clamped`（单层弹性模量）
- 不发送 `operating.alpha_parts`（单层热膨胀系数）
- **必须**计算并注入 `clamped.total_thickness = sum(各层厚度)`，这是热损失和嵌入损失计算的关键输入
- 构建 `clamped.layers` 列表（柔度用），每层**硬编码** `"model": "cylinder"`（不从 UI 读取，多层统一圆柱体）：

```python
# _build_payload 多层构建伪码
total_thickness = 0
layers = []
layer_thermals = []
for i in range(1, part_count + 1):
    t = float(widget(f"clamped.layer_{i}.thickness"))
    da = float(widget(f"clamped.layer_{i}.D_A"))
    e = float(widget(f"clamped.layer_{i}.E"))
    alpha = float(widget(f"clamped.layer_{i}.alpha"))
    total_thickness += t
    layers.append({
        "model": "cylinder",   # 硬编码，非 UI 字段
        "d_h": bearing_d_inner,  # 所有层共用，从螺栓参数推导
        "D_A": da,
        "l_K": t,
        "E_clamped": e,
    })
    layer_thermals.append({"alpha": alpha, "l_K": t})

clamped["layers"] = layers
clamped["total_thickness"] = total_thickness  # 关键：热损失 + 嵌入损失需要
operating["layer_thermals"] = layer_thermals
```

### 3. Calculator 改造 (`calculator.py`)

#### `_resolve_compliance()` 多层分支

完整的重构后 `auto_compliance` 分支：

```python
elif stiffness.get("auto_compliance"):
    from core.bolt.compliance_model import (
        calculate_bolt_compliance, calculate_clamped_compliance,
    )
    E_bolt = _positive(float(stiffness.get("E_bolt", 210_000)), "stiffness.E_bolt")
    cl = clamped or {}

    if "layers" in cl:
        # 多层模式
        layers = cl["layers"]
        if not (1 <= len(layers) <= 10):
            raise InputError("被夹件层数须在 1~10 之间")
        l_K = sum(float(layer["l_K"]) for layer in layers)
        _positive(l_K, "clamped.total_thickness (sum of layers)")
        bolt_r = calculate_bolt_compliance(d, p, l_K, E_bolt)
        delta_s = bolt_r["delta_s"]
        d_h = bearing_d_inner
        for layer in layers:
            layer.setdefault("d_h", d_h)
        clamp_r = calculate_clamped_compliance(layers=layers)
        delta_p = clamp_r["delta_p"]
    else:
        # 单层模式：保持现有逻辑
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

关键点：`E_clamped` 仅在单层 else 分支中读取，多层分支从 `layers` 中各层的 `E_clamped` 获取。

#### 热损失逐层计算

其中 `l_K` = `clamped.total_thickness`（单层为直接输入值，多层为各层厚度之和）。`delta_T = temp_bolt - temp_parts`。

```python
layer_thermals = operating.get("layer_thermals")
l_K = clamped.get("total_thickness")  # 单层直接值 / 多层由 _build_payload 注入求和值

if layer_thermals:
    # 多层热位移：各层分别计算再求和
    # 所有被夹件层共享同一温度 temp_parts（本迭代不支持逐层温度）
    delta_l_parts = sum(
        float(lt["alpha"]) * float(lt["l_K"]) * delta_T
        for lt in layer_thermals
    )
else:
    # 单层模式：保持现有公式完全不变
    # 即 F_th = |(alpha_bolt - alpha_parts) * delta_T * l_K / (delta_s + delta_p)|
    delta_l_parts = alpha_parts * l_K * delta_T

# 螺栓热位移，l_K 同上（夹紧长度，非 l_eff）
delta_l_bolt = alpha_bolt * l_K * delta_T
F_V_thermal = abs(delta_l_parts - delta_l_bolt) / (delta_s + delta_p)
```

**温度假设**：所有被夹件层共享同一操作温度 `temp_parts`。本迭代不引入逐层温度。
**公式等价性**：单层 else 分支展开后为 `|(alpha_parts - alpha_bolt) * delta_T * l_K / (delta_s + delta_p)|`，与现有代码 `|(alpha_bolt - alpha_parts) * delta_T * c_s*c_p/(c_s+c_p) * l_K|` 数学等价（因 `1/(delta_s+delta_p) = c_s*c_p/(c_s+c_p)`，abs 消除符号差异）。

#### 输出字典

- 单层模式：`thermal.alpha_parts` 保持为标量，不变
- 多层模式：`thermal.layer_thermals` 为列表（同输入），`thermal.alpha_parts` 不输出

### 4. 嵌入损失

无需改动。`part_count` 在 payload 中始终为整数（见第 1 节 payload 解析），正确用于接口数计算（通孔 `n = part_count + 2`，螺纹孔 `n = part_count + 1`）。

### 5. 输入持久化

存储层 (`input_condition_store.py`) 无需改动，JSON 序列化天然支持嵌套列表。

**保存**：`_build_payload` 输出的 dict 直接存为 JSON，包含 `clamped.layers` 和 `operating.layer_thermals`。

**加载恢复流程**：
1. 读取 JSON，检查 `clamped.layers` 是否存在
2. 若存在：
   - 根据 `len(layers)` 设置 `part_count` 下拉（2 → "2"，其他 → "自定义" + 设 `custom_count`）
   - 触发显隐逻辑
   - 遍历 layers，填充 `layer_N.thickness`、`layer_N.D_A`、`layer_N.E` 控件
   - 从 `operating.layer_thermals` 填充 `layer_N.material`（按 alpha 反推）和 `layer_N.alpha`
3. 若不存在：走现有单层恢复逻辑

### 6. 不做的事

- UI 限制最多 5 层（`custom_count` 范围 3~5 + 固定选项 1/2），calculator 校验上限 10 层（防御性，供未来 API/JSON 直接调用）
- 不改动 `compliance_model.py`（多层逻辑已完整）
- 不改动锥体/套筒模型（多层统一用圆柱体）
- 不新增 `total_thickness` UI 汇总展示
- 不做加权平均 alpha 自动计算
- 不引入逐层温度（所有层共享 temp_parts）

## 测试策略

### 新增测试 (`tests/test_calculator.py`)

- **多层柔度**：2 层不同材料（钢 E=210000 + 铝 E=70000），auto_compliance 路径，验证 δp = δp_1 + δp_2
- **多层热损失**：2 层不同 alpha，验证 Δl = Σ(alpha_i × l_K_i × ΔT)
- **多层 layers 校验**：空列表、超过上限层数，验证 InputError
- **单层回归**：确保现有单层逻辑不受影响

### 已有覆盖

- `tests/test_compliance_model.py` 已有多层测试（钢+铝双层），无需新增

## 改动范围

| 文件 | 改动 |
|---|---|
| `app/ui/pages/bolt_page.py` | `part_count` 改下拉 + 预定义 layer_1~5 FieldSpec + 显隐联动 + `_build_payload` 构建 layers/layer_thermals + 加载恢复逻辑 |
| `core/bolt/calculator.py` | `_resolve_compliance()` 加多层分支 + 热损失逐层求和 + 层数校验 |
| `tests/test_calculator.py` | 新增多层柔度、热损失、边界校验测试 |
