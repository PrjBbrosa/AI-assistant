# Interference-Fit Hollow-Shaft Support Design

## Goal

在现有过盈配合模块中增加空心轴支持，使 `geometry.shaft_inner_d_mm` 能进入主计算链路，并影响：

- 接触压力
- 扭矩/轴向承载能力
- 过盈需求
- 应力与安全系数
- UI / 报告 / trace

同时保持以下边界不扩散：

- 不顺带实现服役温度耦合
- 不顺带实现离心力 / 转速耦合
- 不顺带实现阶梯轴 / 阶梯轮毂
- 不把 repeated-load 的实心轴简化公式硬套到空心轴

## Current Problem

当前实现只接受：

- `geometry.shaft_d_mm`
- `geometry.hub_outer_d_mm`
- `geometry.fit_length_mm`

并在 core 中把轴侧柔度写成固定“实心轴”形式。这样会带来两个问题：

1. 无法与包含 `inner diameter shaft` 的经典 DIN / eAssistant 案例直接对齐边界。
2. 对真实空心轴工况会高估轴刚度，从而高估接触压力和传递能力。

## Scope

### In Scope

- 新增几何输入 `geometry.shaft_inner_d_mm`
- `0` 代表实心轴，保持现有输入兼容
- 主模型根据轴内径修正轴侧径向柔度
- 更新结果 `model.type`、`derived`、UI 文案和报告说明
- 空心轴下让 `repeated_load` 输出 `not applicable`
- 增加 core / UI 回归测试

### Out of Scope

- 服役温度、转速、离心力
- 阶梯空心轴
- 空心轴专用 fretting 寿命模型
- 空心轴下更复杂的径向/弯矩局部接触模型

## Design Approach

### Recommended Approach

采用“兼容现有实心轴基线”的增量扩展：

- 保持当前实心轴结果不变
- 当 `shaft_inner_d_mm > 0` 时，引入空心轴柔度放大因子
- 放大因子使用厚壁圆筒外压下的经典变形比值，对当前实心轴基线进行修正

这样做的原因：

- 不会破坏现有已验证的实心轴输出
- 能体现“内孔越大，轴越柔，接触压力越低”的正确趋势
- 可以在后续需要时再替换成更完整的统一公式，而不影响 UI/数据结构

## Proposed Mechanics

### Geometry

- `d = geometry.shaft_d_mm`
- `d_inner = geometry.shaft_inner_d_mm`
- `D = geometry.hub_outer_d_mm`
- 必须满足：`0 <= d_inner < d < D`

### Shaft Compliance

保留当前实心轴基线：

- `c_shaft_solid = r / E_s * (1 - nu_s^2)`

当 `d_inner > 0` 时，引入空心轴放大因子：

- `k = d_inner / d`
- `factor_hollow = (((1 + k^2) / (1 - k^2)) - nu_s) / (1 - nu_s)`
- `c_shaft = c_shaft_solid * factor_hollow`

当 `d_inner = 0` 时：

- `factor_hollow = 1`
- 自动退化为当前实心轴结果

### Hub Compliance

轮毂侧保持现有厚壁轮毂模型不变。

### Stress / Capacity Chain

主模型仍沿用当前压力 -> 能力 -> 应力的链路，但全部使用新的：

- `c_total = c_shaft + c_hub`

因此空心轴会自动影响：

- `p_min / p_mean / p_max`
- `torque_* / axial_*`
- `delta_required_*`
- `press_force_*`
- 安全系数与总判定

## Repeated-Load / Fretting Handling

当前 `repeated_load` 文案和简化式明确针对实心轴。

因此首版处理为：

- `shaft_inner_d_mm = 0`：保持现有逻辑
- `shaft_inner_d_mm > 0`：`repeated_load.applicable = False`
- `notes` 中明确说明：当前简化 repeated-load 估算仅支持实心轴

`fretting` Step 5 仍然可以保留风险评估入口，但如果因 repeated-load 适用性受限导致不适用，应明确给出低可信度说明。

## UI / Report Changes

- 页面标题副标题从“实心轴 + 厚壁轮毂”改成“实心轴/空心轴 + 厚壁轮毂”
- “几何与过盈”章节新增：
  - `轴内径 d_i`
- beginner guide / hint 明确：
  - `0` 表示实心轴
  - 非零表示空心轴
- 报告中增加：
  - `shaft inner diameter`
  - `shaft type`
- `model.type` 改成：
  - `cylindrical_interference_solid_shaft`
  - `cylindrical_interference_hollow_shaft`

## Testing Strategy

### Core

- `shaft_inner_d_mm = 0` 时结果与当前实心轴兼容
- `shaft_inner_d_mm > 0` 时：
  - `c_shaft` 增大
  - `p_min` 降低
  - `torque_min_nm` 降低
- 非法几何 `d_inner >= d` 必须报错
- 空心轴时 repeated-load 必须变成 `not applicable`

### UI

- 新字段出现在页面中
- payload 正确包含 `geometry.shaft_inner_d_mm`
- 报告中能看到空心轴几何与模型类型

## Risks

- 首版采用“兼容当前实心轴基线 + 空心轴放大因子”的折中方案，不是完全统一的厚壁圆筒全公式。
- 因此它更适合作为当前仓库的工程增强版，而不是最终的 DIN 7190 完整空心轴解算器。
- 这比继续把空心轴完全排除在模型外更有工程价值，也更适合当前迭代节奏。
