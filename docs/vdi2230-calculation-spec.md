# 基于 VDI 2230 的螺栓校核计算说明（首版实现）

## 1. 文档目的
本文给出本仓库螺栓校核工具的计算逻辑、变量定义、单位约定、校核准则与实现范围。  
目标是实现 VDI 2230 的核心工程链路，保证可复核与可扩展。

## 2. 参考依据
- VDI 2230 Part 1 官方说明（高负荷单螺栓系统计算）
- eAssistant 对 VDI 2230 的公开摘要（`FMmax = alpha_A * FMmin` 及 `FMmin` 约束来源）
- PCB 白皮书（VDI 2230 R1-R10 计算与校核流程概述）

说明：VDI 2230 原文标准为版权文档，本实现依据公开可引用资料构建核心计算链路，并在文末列出未覆盖项。

## 3. 单位约定
- 力：`N`
- 长度：`mm`
- 应力/弹性模量：`MPa`（即 `N/mm^2`）
- 扭矩：`N·m`（内部中间量可用 `N·mm`）
- 角度：内部计算用弧度

## 4. 输入参数定义（核心）

### 4.1 紧固件与材料
- `d`：公称直径（mm）
- `p`：螺距（mm）
- `As`：螺纹应力截面积（mm²，可选；缺省由 `d,p` 估算）
- `d2`：螺纹中径（mm，可选；缺省由 `d,p` 估算）
- `d3`：螺纹小径（mm，可选；缺省由 `d,p` 估算）
- `Rp02`：螺栓 0.2% 屈服强度（MPa）

### 4.2 装配参数
- `alpha_A`：拧紧系数（`FMmax/FMmin`）
- `mu_thread`：螺纹摩擦系数
- `mu_bearing`：支承面摩擦系数
- `utilization`：装配屈服利用系数（常用 `0.8~0.95`）
- `thread_flank_angle_deg`：螺纹牙型角（公制默认 `60`）
- `prevailing_torque`：附加防松扭矩（N·m，可选）

### 4.3 接触与载荷
- `FA_max`：最大轴向工作外载（N）
- `FQ_max`：最大横向剪切载荷（N，可选）
- `seal_force_required`：密封/压紧需要的最小残余夹紧力（N，可选）
- `embed_loss`：嵌入导致的预紧力损失（N）
- `thermal_force_loss`：热效应导致的等效预紧力损失（N，可选）
- `slip_friction_coefficient`：防滑面摩擦系数（可与 `mu_bearing` 不同）
- `friction_interfaces`：受力摩擦面数（默认 `1`）

### 4.4 刚度/顺从度
- 二选一输入：
  - `bolt_compliance` 与 `clamped_compliance`（单位 `mm/N`）
  - 或 `bolt_stiffness` 与 `clamped_stiffness`（单位 `N/mm`）
- `load_introduction_factor_n`：载荷导入系数 `n`（默认 `1.0`）

### 4.5 支承面几何
- `bearing_d_inner`：有效内径（mm）
- `bearing_d_outer`：有效外径（mm）

## 5. 几何推导（缺省计算）
若未提供 `As, d2, d3`，按 ISO 公制近似：

- `As = pi/4 * (d - 0.9382*p)^2`
- `d2 = d - 0.64952*p`
- `d3 = d - 1.22687*p`

## 6. VDI 2230 核心计算链路（本实现）

### 6.1 载荷分配系数
定义螺栓与被夹件顺从度分别为 `delta_s`、`delta_p`：

- `phi = delta_p / (delta_s + delta_p)`
- `phi_n = n * phi`

对应最大轴向载荷下：
- 螺栓附加载荷：`DeltaF_b = phi_n * FA_max`
- 夹紧力衰减：`DeltaF_k = (1 - phi_n) * FA_max`

### 6.2 防滑/密封所需最小残余夹紧力
- 防滑需求：
  - `F_slip_required = FQ_max / (slip_friction_coefficient * friction_interfaces)`（若 `FQ_max = 0` 则为 0）
- 总需求：
  - `F_K_required = max(seal_force_required, F_slip_required)`

### 6.3 最小装配预紧力 `FMmin`
考虑外载导致夹紧力下降、嵌入损失、热损失：

- `FMmin = F_K_required + (1 - phi_n)*FA_max + embed_loss + thermal_force_loss`

### 6.4 最大装配预紧力 `FMmax`
- `FMmax = alpha_A * FMmin`

### 6.5 扭矩模型
螺纹升角与等效摩擦角：
- `lambda = atan(p / (pi*d2))`
- `rho = atan(mu_thread / cos(thread_flank_angle_deg/2))`

螺纹扭矩系数与支承面扭矩系数（单位 mm）：
- `k_thread = (d2/2) * tan(lambda + rho)`
- `Dkm = (bearing_d_inner + bearing_d_outer)/2`
- `k_bearing = mu_bearing * Dkm/2`

总拧紧扭矩：
- `MA(F) = F*(k_thread + k_bearing)/1000 + prevailing_torque`  （N·m）

故：
- `MA_min = MA(FMmin)`
- `MA_max = MA(FMmax)`

### 6.6 装配阶段等效应力校核
在 `FMmax` 下：
- 轴向应力：`sigma_ax = FMmax / As`
- 螺纹扭转载荷（N·mm）：`M_thread = FMmax * k_thread`
- 扭转切应力：`tau = 16*M_thread / (pi*d3^3)`
- 装配当量应力：`sigma_vm_assembly = sqrt(sigma_ax^2 + 3*tau^2)`
- 允许值：`sigma_allow_assembly = utilization * Rp02`

判定：
- `sigma_vm_assembly <= sigma_allow_assembly` 为通过

### 6.7 服役阶段应力校核（简化）
- `F_bolt_work_max = FMmax + phi_n*FA_max`
- `sigma_ax_work = F_bolt_work_max / As`
- `sigma_allow_work = Rp02 / yield_safety_operating`

判定：
- `sigma_ax_work <= sigma_allow_work` 为通过

### 6.8 残余夹紧力校核
- `F_K_residual = FMmin - embed_loss - thermal_force_loss - (1 - phi_n)*FA_max`

判定：
- `F_K_residual >= F_K_required` 为通过

### 6.9 最大允许附加载荷（VDI 常用判据）
- `FA_perm = (0.1 * Rp02 * As) / phi_n`（当 `phi_n > 0`）

判定：
- `FA_max <= FA_perm` 为通过

## 7. 输出内容
工具输出以下结果（JSON）：
- 关键中间量：`As,d2,d3,phi,phi_n,FMmin,FMmax,MA_min,MA_max`
- 装配/服役应力：`sigma_vm_assembly,sigma_ax_work`
- 夹紧力：`F_K_required,F_K_residual`
- 附加载荷能力：`FA_perm`
- 各项判定布尔值与总体 `overall_pass`

## 8. 实现边界与限制
- 本实现为 VDI 2230 核心流程的工程化首版，不等同于标准全文全场景求解器。
- 未覆盖项（后续可扩展）：
  - 多螺栓群耦合
  - 详细锥台压缩体几何自动建模
  - 完整疲劳强度谱和安全系数体系
  - 偏心载荷与复杂边界条件

## 9. 使用建议
- 项目初期可先用本工具做快速方案筛选。
- 关键安全件应结合企业规范、实测摩擦系数、以及完整 VDI 2230 标准校核。
