# 预紧与装配参数

本章节确定**装配过程**：预紧力上下限、摩擦系数、支承几何、拧紧工艺。装配参数决定装配扭矩 MA、装配 von Mises 校核（R5 风格）、以及服役计算中使用的 F_preload_max。

## 为什么要填这些

装配过程的核心不等式：

```
F_preload_min  ≤  实际装配预紧力  ≤  F_preload_max = α_A · F_preload_min    [N]
```

**F_preload_min** 是设计承诺的下限（工艺质保能达到）。**α_A** 是散差系数——反映"同一扭矩目标下，实际预紧力的最大/最小比值"。**F_preload_max** 是装配 von Mises 校核使用的上限值（最坏装配应力在这里）。

装配扭矩 MA（给扭矩扳手的目标值）由预紧力 + 摩擦系数 + 支承几何推导：

```
k_thread  = (d2/2) · tan(lead_angle + friction_angle)             [mm]
k_bearing = μ_bearing · (d_inner + d_outer) / 4                   [mm]
MA = F_preload · (k_thread + k_bearing) / 1000 + prevailing_torque    [F: N, k: mm → MA: N·m]
```

其中：
- **lead_angle = atan(p / (π·d2))** —— 螺纹导程角 [rad]
- **friction_angle = atan(μ_thread / cos(flank/2))** —— 当量摩擦角 [rad]
- **flank = 60°** 公制螺纹牙型角（工具默认，可覆盖）
- **prevailing_torque** —— 锁紧件附加扭矩（见 `terms/bolt_tapped_axial_prevailing_torque`）

`core/bolt/tapped_axial_joint.py:242-253` 实现。

## 输入 / 产出

**必填**：

| 字段 | 单位 | 作用 |
|---|---|---|
| F_preload_min | N | 装配预紧力下限 |
| α_A | - | 预紧力上下限比值（散差） |
| μ_thread | - | 螺纹副摩擦系数 |
| μ_bearing | - | 支承面摩擦系数 |
| bearing_d_inner | mm | 支承面内径（通常 = 通孔直径） |
| bearing_d_outer | mm | 支承面外径（垫圈外径或螺栓头接触面外径） |
| tightening_method | 字符串 | torque / angle / hydraulic / thermal |
| utilization | - | 装配利用系数 ≤ 1 |

**可选（有默认）**：

- `prevailing_torque` 默认 0（无防松件）
- `thread_flank_angle_deg` 默认 60°（公制螺纹）

**产出**：

- MA_min, MA_max（装配扭矩范围 [N·m]）
- 装配 von Mises 应力 σ_vm,assembly [MPa]
- F_preload_max = α_A · F_preload_min [N]（给后续服役校核用）

## α_A 与 tightening_method 的耦合校验

`_ALPHA_A_RANGES`（`core/bolt/tapped_axial_joint.py:10-15`）为每种拧紧工艺设定建议区间：

| tightening_method | α_A 建议区间 |
|---|---|
| torque（扭矩法） | 1.4 – 1.8 |
| angle（转角法） | 1.1 – 1.3 |
| hydraulic（液压拉伸法） | 1.05 – 1.15 |
| thermal（热装法） | 1.05 – 1.15 |

用户填的 α_A 偏离建议区间**不抛错**，但会**追加 warning**——提示装配工艺能力与散差假设不匹配。工艺越先进（angle → hydraulic → thermal），α_A 越接近 1，预紧力波动越小。

**扭矩法的特殊处理**：`core/bolt/tapped_axial_joint.py:267` 给服役 von Mises 保留 `k_tau = 0.5`（50% 装配扭转应力进入服役）；其他三种工艺 `k_tau = 0`（**假设装配扭矩在服役前已基本消除**）。如果你用转角/液压/热装但担心装配扭矩残留，此假设可能不保守——需自行评估。

## utilization 做什么

利用系数 ν（`assembly.utilization`）决定装配许用应力：

```
σ_allow_assembly = ν · Rp0.2     [MPa]
装配通过条件: σ_vm_assembly ≤ σ_allow_assembly
```

典型值：

| ν | 场景 |
|---|---|
| 0.9 | 通用（本工具默认） |
| 0.95 | 工艺控制严，工件质量高 |
| 0.8 | 装配环境差、工艺散差大 |
| > 0.95 | 工具追加 warning（装配进入屈服边缘） |

utilization = 1.0 意味着"装配直接允许到屈服点"——物理上不合理，工具接受但会 warning。**不允许 > 1.0**（`core/bolt/tapped_axial_joint.py:217-218` 强制）。

## 本模块做什么（vs 不做什么）

**本模块做**：

- 按 lead angle + friction angle 公式严格计算装配扭矩
- 区分扭矩法（保留 50% 残余扭转）vs 其他工艺（无残余扭转）
- 校核装配 von Mises（F_preload_max 下）≤ ν·Rp0.2

**本模块不做**：

- **不从拧紧方式自动选 α_A**：用户必须自己填 α_A；拧紧方式只作为 warning 比对依据
- **不自动求 F_preload_min**：本模块不是"设计反推"，需要用户**直接提供** F_preload_min（常由外部 FA_max + 疲劳要求反推，再手动填入）
- **不校核 R1 防滑 / R6 支承压溃**：支承直径输入只用于 k_bearing，未校核 p_bearing ≤ p_allow——这是本模块的**已知不足**，关键工况需另做支承压溃评估

## 典型填法

对标准钢-钢连接（M10, 8.8, 通用工况）：

```
F_preload_min   = 0.6 · As · Rp0.2 ≈ 22 300 N    （利用系数 0.6 起步）
α_A             = 1.6（扭矩法）
μ_thread        = 0.12（钢-钢干/轻油）
μ_bearing       = 0.14（钢-钢干）
bearing_d_inner = 11 mm（M10 通孔）
bearing_d_outer = 18 mm（垫圈外径）
utilization     = 0.9
```

## 常见坑

- **F_preload_min 填成 F_preload_max**：装配 von Mises 会用 α_A·F_min 作为上限应力；填错会让 von Mises 许用校核**过于激进**。
- **α_A 填 < 1**：直接抛 `InputError`（`core/bolt/tapped_axial_joint.py:178-179`）。
- **摩擦系数超过 1.0**：直接抛 `InputError`（`core/bolt/tapped_axial_joint.py:186-189`）。
- **bearing_d_outer ≤ bearing_d_inner**：直接抛 `InputError`（`core/bolt/tapped_axial_joint.py:199-202`）。
- **支承内/外径颠倒**：工具严格要求 outer > inner，填反会抛错。
- **忘记填 prevailing_torque**：多数工况留 0 即可；使用防松件必须填产品规格值（否则 MA 低于实际需求）。

## 参考标准

- VDI 2230-1:2015（α_A、装配扭矩、装配应力校核相关章节）
- ISO 898-1:2013（预紧力与屈服）

> Cannot verify against original VDI / ISO standard —— α_A 区间与扭矩 / 摩擦公式整理自公开文献；**未查证 VDI 2230-1:2015 原文**。本章实现位于 `core/bolt/tapped_axial_joint.py:173-262`。
