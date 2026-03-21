# Worm Load-Capacity Upgrade Design

## Goal

把当前蜗杆/蜗轮模块从“`DIN 3975` 几何与经验性能占位”升级到“可输出一部分 KISSsoft 风格工程结果”的最小可用版本，至少补齐：

- 几何一致性检查
- 输入/输出功率与扭矩链路闭合
- 齿面应力输出
- 齿根应力输出
- 扭矩波动输出
- 最小安全系数与通过/不通过结论

同时明确边界：

- 本轮不声称完整复现 `DIN 3996` / `ISO/TS 14521`
- 本轮不实现磨损、点蚀寿命、挠度、温升 Method C 等完整标准链路
- 本轮只实现 `Method B` 风格的最小工程子集，并在结果中显式标注简化假设

## Current Problems

## 1. 现有模块的主要问题

### 1.1 功率链路不闭合

当前页面把 `operating.power_kw` 定义为输入功率，但 `core/worm/calculator.py` 中：

- 输出扭矩直接按输入功率换算
- 同时又按效率推导损失功率

这会导致“输出功率仍等于输入功率，但又存在损失功率”的自相矛盾。

### 1.2 几何约束未进入校核

当前把 `z1 / z2 / m / q / gamma / a` 都视为独立输入，只输出：

- 理论中心距
- 中心距偏差

但不会提示这组输入是否构成自洽蜗杆副。现有两个样例都存在明显不一致。

### 1.3 多个字段没有进入主计算

以下字段目前主要用于 UI 保存或展示，没有真正影响结果：

- `geometry.worm_face_width_mm`
- `geometry.wheel_face_width_mm`
- `operating.application_factor`
- `advanced.friction_override`
- `tolerance.*`
- `geometry.handedness`

### 1.4 Load Capacity 只是壳

当前 `Load Capacity` 页面和 `load_capacity.status` 仍是“尚未开始”，没有真实：

- 齿面应力
- 齿根应力
- 载荷系数
- 安全系数
- 波动工况结果

## Scope

### In Scope

- 修复输入功率、效率、输出功率、输出扭矩之间的能量链路
- 增加几何一致性字段、偏差量和 warning
- 把 `worm_face_width_mm`、`wheel_face_width_mm`、`application_factor`、`friction_override` 接入主模型
- 新增 `Method B` 最小工程参数：
  - 弹性模量与泊松比
  - 许用齿面应力
  - 许用齿根应力
  - 横向/纵向载荷系数
  - 扭矩波动幅值
- 输出名义、RMS、峰值三组载荷结果
- 输出齿面/齿根应力及安全系数
- UI、样例、结果摘要、测试同步更新

### Out of Scope

- 完整点蚀寿命计算
- 磨损安全系数
- 挠度安全系数
- 完整热平衡模型
- scuffing 计算
- 多种蜗杆齿形专用修正
- 完整材料数据库与自动寿命因子标定

## Standards and Source Position

本轮实现对齐以下来源的术语和结果结构：

- `ISO/TS 14521:2020` 官方预览页可确认本标准覆盖：
  - 齿面接触应力 `σHm`
  - 齿根剪应力 `τF`
  - pitting / tooth breakage / temperature 等失效模式
- `ISO` 官方标准页确认 `ISO/TS 14521:2020` 是圆柱蜗杆副负载能力计算规范
- 公开研究论文确认：
  - 现代设计流程仍以 mean Hertzian contact stress 作为核心输入/输出量
  - `CuSn12Ni2` 类青铜的接触强度极限可用作工程初始默认值，但不应替代用户显式输入

因此本轮采用的定位是：

- 结果结构、命名和工程语义向 `ISO/TS 14521 / DIN 3996 Method B` 靠拢
- 具体计算公式采用“标准术语 + 经典力学 + 明确简化”的最小闭环
- 所有简化项都在结果中公开，避免把近似结果伪装成完整标准结果

## Recommended Approach

采用“两层模型”：

### Layer 1: Geometry and Power Integrity

负责保证蜗杆副至少在以下层面自洽：

- 传动比
- 理论中心距
- `q-z1-gamma` 一致性偏差
- 输入/输出功率
- 输入/输出扭矩
- 线速度、滑动速度、摩擦与损失功率

### Layer 2: Minimal Load-Capacity Subset

在 Layer 1 自洽的基础上，计算：

- 名义载荷
- 载荷波动后的峰值载荷与 RMS 载荷
- 齿面接触应力
- 齿根应力
- 安全系数

## Proposed Mechanics

### 1. Geometry Consistency

新增并输出：

- `lead_angle_implied_deg = atan(z1 / q)`
- `lead_angle_delta_deg = lead_angle_deg - lead_angle_implied_deg`
- `center_distance_delta_mm = a - a_th`

规则：

- 偏差不直接阻止计算，但进入 `warnings`
- 若偏差超出阈值，`load_capacity` 结论必须标记为“几何不自洽，结果仅供参考”

### 2. Power Chain

定义：

- `P_in = operating.power_kw`
- `n1 = operating.speed_rpm`
- `T1 = 9550 * P_in / n1`
- `eta = f(gamma, mu, KA)` 的经验效率
- `P_out = P_in * eta`
- `P_loss = P_in - P_out`
- `n2 = n1 / i`
- `T2 = 9550 * P_out / n2`

这样保证：

- 输出扭矩来自输出功率，而不是直接复用输入功率
- 损失功率与效率链路一致

### 3. Tooth Force Components

以蜗轮侧切向力作为载荷主量：

- `Ft2 = 2000 * T2 / d2`
- `Fn = Ft2 / (cos(alpha_n) * sin(gamma))`
- `Fa2 = Ft2 / tan(gamma)`
- `Fr2 = Ft2 * tan(alpha_n) / sin(gamma)`

其中：

- `alpha_n` 首版默认 `20 deg`，允许高级参数覆盖
- `KA / Kv / KHalpha / KHbeta` 统一进入设计载荷

### 4. Contact Stress

首版用线接触 Hertz 近似构造 `σHm` 子集：

- `Ered` 由 `E1 / nu1 / E2 / nu2` 计算
- `b_eff = min(b1, b2)`
- `Fn_design = Fn * KA * Kv * KHalpha * KHbeta`
- 以简化等效曲率半径估算接触带宽与平均赫兹应力

输出：

- `sigma_hm_nominal_mpa`
- `sigma_hm_rms_mpa`
- `sigma_hm_peak_mpa`
- `allowable_contact_stress_mpa`
- `safety_factor_contact_nominal`
- `safety_factor_contact_peak`

### 5. Root Stress

首版输出“工程齿根应力”，不伪装成完整标准轮齿局部应力场：

- 采用基于有效齿宽、齿高和等效根截面的简化悬臂模型
- 设计载荷使用与接触应力相同的 `Fn_design`
- 输出名义、RMS、峰值三组结果

输出：

- `sigma_f_nominal_mpa`
- `sigma_f_rms_mpa`
- `sigma_f_peak_mpa`
- `allowable_root_stress_mpa`
- `safety_factor_root_nominal`
- `safety_factor_root_peak`

### 6. Torque Ripple

新增：

- `operating.torque_ripple_percent`

假设波动为绕名义扭矩的正弦波幅值：

- `T_amp = T_nom * r`
- `T_peak = T_nom + T_amp`
- `T_min = max(0, T_nom - T_amp)`
- `T_rms = T_nom * sqrt(1 + 0.5 * r^2)`

应力放大关系：

- 接触应力与载荷平方根相关
- 齿根应力与载荷近似线性相关

## UI Changes

### New Inputs

- `materials.worm_e_mpa`
- `materials.worm_nu`
- `materials.wheel_e_mpa`
- `materials.wheel_nu`
- `operating.torque_ripple_percent`
- `advanced.normal_pressure_angle_deg`
- `load_capacity.allowable_contact_stress_mpa`
- `load_capacity.allowable_root_stress_mpa`
- `load_capacity.dynamic_factor_kv`
- `load_capacity.transverse_load_factor_kha`
- `load_capacity.face_load_factor_khb`
- `load_capacity.required_contact_safety`
- `load_capacity.required_root_safety`

### Results

`Load Capacity` 页面从“尚未开始”改成真实结果卡片，至少展示：

- 几何一致性 warning
- 名义/峰值输出扭矩
- `Ft / Fa / Fr / Fn`
- 齿面应力与安全系数
- 齿根应力与安全系数
- 扭矩波动摘要

## Testing Strategy

### Core

- 旧几何回归不崩
- 功率链路满足 `P_out = P_in * eta`
- `friction_override` 真正影响效率与损失功率
- `application_factor` 与 `KH/KV` 真正进入设计载荷
- 扭矩波动增大时：
  - `T_peak` 增大
  - `sigma_h_peak` 增大
  - `sigma_f_peak` 增大
- 许用值降低时，安全系数下降

### UI

- 页面暴露新字段
- 样例可加载
- 执行计算后 `Load Capacity` 不再是固定占位文案
- 结果摘要中能看到齿面/齿根/波动输出

## Risks

- `DIN 3996 / ISO/TS 14521` 完整公式属于重型标准实现，本轮只做最小工程子集
- 齿根应力首版不是完整局部 FEM 或标准附录法，而是显式声明的工程近似
- 若用户给出不自洽几何，本轮优先给 warning 和结果降级，而不是默默继续当作标准结果
