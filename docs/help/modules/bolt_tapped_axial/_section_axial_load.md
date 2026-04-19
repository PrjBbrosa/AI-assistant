# 轴向工作载荷

本章节只有两个字段：**FA_min** 和 **FA_max**——一个循环中的最小与最大轴向拉力 [N]。它们共同决定服役 von Mises 校核、疲劳平均应力与应力幅。

## 为什么要填这些

由于本模块**无被夹件**，外部轴向力**直接全部进入螺栓**（没有 Φ_N 分流）：

```
F_bolt,min = F_preload_max + FA_min       [N]
F_bolt,max = F_preload_max + FA_max       [N]
```

从 F_bolt_min/max 进一步推出：

```
σ_ax,service_max = F_bolt_max / As                               [F: N, As: mm² → σ: MPa]
σ_m  = (F_preload_max + 0.5·(FA_min + FA_max)) / As               [MPa]   # 疲劳平均
σ_a  = (FA_max − FA_min) / (2·As)                                 [MPa]   # 疲劳幅
```

（`core/bolt/tapped_axial_joint.py:264-278`）

两者**耦合**——只给一个值不足以完成疲劳校核：
- 给定 FA_max 和 FA_min = FA_max，疲劳 σ_a = 0（纯静载）
- 给定 FA_min = 0、FA_max > 0，σ_a 和 σ_m 都来自 FA_max 单值（脉动循环）
- 给定 FA_min > 0、FA_max > FA_min，完整循环信息（最完整的疲劳输入）

## 方法差异：静载 vs 循环载

**纯静载**（连接只在某次工作状态承受一次恒定拉力）：

```
FA_min = FA_max（相等填同一值）
```

此时 σ_a = 0，疲劳自然通过，`checks.fatigue_ok` 永远 True（除非 σ_m 超过 0.9·Rp0.2 导致 Goodman 因子归零）。

**循环载**（压力循环、振动、机械周期）：

```
FA_min = 循环中最低拉力（压向工况填 0）
FA_max = 循环中最高拉力（含动载放大系数 Kd）
```

本工具**不分段 Miner 累计**——只按**一种幅值**做疲劳评估。如果实际载荷谱有多段（例如温度循环 + 压力循环叠加），需要包络成等效单幅值（保守取最高 FA_max 与最低 FA_min 的组合）。

## 本模块做什么（vs 不做什么）

**本模块做**：

- 严格校验 FA_min ≤ FA_max（否则 `InputError`）
- 用 F_preload_max + FA_max 做服役最大 von Mises 校核
- 用 (FA_max − FA_min)/2 做疲劳应力幅
- 用 F_preload_max + 平均(FA_min, FA_max) 做疲劳平均应力

**本模块不做**：

- **不支持负值（压向）**：`_positive(..., allow_zero=True)` 强制 ≥ 0（`core/bolt/tapped_axial_joint.py:220-221`）。压向工况按 FA_min = 0 保守处理。
- **不自动加动载放大系数**：用户需自行把 Kd 乘入 FA_max。
- **不做载荷谱分解 / Miner 累计**：只按一个幅值评估；多段谱需用户自行包络。
- **不考虑横向力 FQ 与弯矩**：纯轴向力假设，带横向 / 弯矩需另做专项分析。

## 输入 / 产出

**输入**：

| 字段 | 单位 | 允许值 |
|---|---|---|
| FA_min | N | ≥ 0，且 ≤ FA_max |
| FA_max | N | ≥ 0，且 ≥ FA_min |

**产出**：

- F_service_min = F_preload_max + FA_min [N]
- F_service_max = F_preload_max + FA_max [N]
- σ_ax_service_max = F_service_max / As [MPa]
- σ_vm_service_max（含扭矩法残余扭转修正）[MPa]
- σ_m, σ_a（疲劳）[MPa]

## 典型填法

| 工况 | FA_min | FA_max |
|---|---|---|
| 静载：阀盖始终带固定压力 | 10000 | 10000 |
| 脉动：压力容器 0 ↔ 峰值 | 0 | 15000 |
| 循环带预压：管道始终带 5 kN 预张力 | 5000 | 20000 |
| 交变拉-压：外载拉向 15 kN / 压向 −8 kN | **0** | 15000（压向保守舍弃） |

**注意第四行**：本工具不接受压向（负值），严格做法应另用专业动载分析。填 FA_min = 0 保守处理——相当于把压向当作"载荷短暂松开到零"，是**偏保守**的近似。

## 参考标准

- VDI 2230-1:2015（疲劳 σ_a / σ_m 与外载处理相关章节）

> Cannot verify against original VDI standard —— 疲劳公式 σ_a = (FA_max − FA_min)/(2·As) 与 σ_m 定义整理自公开文献；**未查证 VDI 2230-1:2015 原文**。本章实现位于 `core/bolt/tapped_axial_joint.py:264-286`。
