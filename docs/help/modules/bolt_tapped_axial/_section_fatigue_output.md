# 交变轴向疲劳与输出选项

本章节确定**疲劳校核参数**（循环次数、螺纹成形工艺）、**服役屈服安全系数**，以及**报告输出模式**。

## 为什么要填这些

### 疲劳校核输入

本工具用 σ_ASV 疲劳极限表 + 寿命修正 + Goodman 折减：

```
σ_ASV_base    = interpolate(d, ASV_table)       [d: mm → σ_ASV_base: MPa]
cycle_factor  = (2×10⁶ / N_L) ** 0.08  if N_L < 2×10⁶  [N_L: 无量纲 → cycle_factor: 无量纲]
              = 1.0                    if N_L ≥ 2×10⁶
surface_fac   = 0.65 if cut else 1.0             [无量纲]
σ_ASV_eff     = σ_ASV_base · cycle_factor · surface_fac   [MPa · 无量纲 · 无量纲 → MPa]

σ_m           = (F_preload_max + 0.5·(FA_min + FA_max)) / As    [F: N, As: mm² → σ_m: MPa]
goodman_raw   = 1 − σ_m / (0.9 · Rp0.2)                    [σ_m: MPa, Rp0.2: MPa → 无量纲]
goodman       = goodman_raw if goodman_raw > 0 else 0      [无量纲]
σ_a_allow     = σ_ASV_eff · goodman                        [MPa · 无量纲 → MPa]

σ_a           = (FA_max − FA_min) / (2 · As)              [F: N, As: mm² → σ_a: MPa]
通过条件      = goodman > 0  AND  σ_a ≤ σ_a_allow        [两侧均 MPa]
```

实现见 `core/bolt/tapped_axial_joint.py:275-286`。

两个关键字段在本章：

- **load_cycles（N_L）**：寿命修正的分母；详见 `terms/bolt_tapped_axial_load_cycles`
- **surface_treatment**：rolled / cut 选择；详见 `terms/bolt_tapped_axial_surface_treatment`

### 服役屈服安全系数

```
σ_allow_service = Rp0.2 / yield_safety_operating     [Rp0.2: MPa, S: 无量纲 → σ_allow: MPa]
σ_vm_service_max ≤ σ_allow_service                   [两侧均 MPa]
```

- **默认 1.1**：满足 VDI 风格"屈服前保留 10% 余量"
- **重要连接可用 1.15 – 1.25**：更保守
- **必须 ≥ 1.0**（`core/bolt/tapped_axial_joint.py:234-237` 强制）

详见 `terms/bolt_yield_safety`（Stage 2 已写）。

### 报告模式

- **full**：完整报告（含 trace、intermediate、references）
- **compact**：精简报告（只含结论 + 关键数值）

该选项**不影响计算**，只影响文本 / PDF 导出的详细程度。

## Goodman 因子为 0 时的行为

如果平均应力 σ_m ≥ 0.9·Rp0.2，Goodman 原始因子 `goodman_raw ≤ 0`：

- 工具取 `goodman_factor = 0`（不设人为下限，`core/bolt/tapped_axial_joint.py:283-284`）
- σ_a_allow = 0 → **疲劳一律 FAIL**；代码 `fatigue_ok = (goodman_factor > 0) and (σ_a ≤ σ_a_allow)`，即便 σ_a = 0 也按失败处理
- 追加 warning：「平均应力已超出 Goodman 折减范围（σ_m >= 0.9·Rp0.2），疲劳许用幅为 0，疲劳不通过。」

**这是主动的工程提醒**：σ_m 接近屈服时，疲劳折减几乎无剩余，应**降低 F_preload、降低 FA 或加大规格**。本工具**不给虚假通过**——即使 goodman_raw 为负也不会钳到小正值。

## Goodman 因子 < 0.1 的 warning

`core/bolt/tapped_axial_joint.py:375-379`：

```
if goodman_factor_raw < 0.1:
    warning: "Goodman 因子偏低（{factor:.3f} < 0.1），疲劳裕度极小..."
```

即使通过了疲劳校核，若 Goodman 因子低于 0.1，意味着 σ_m 已逼近 0.9·Rp0.2，任何 σ_m 的扰动都可能让疲劳失败。**此警告是工程预警**，建议设计阶段把 Goodman 因子维持在 0.3+。

## 本模块做什么（vs 不做什么）

**本模块做**：

- σ_ASV 按直径 ×  寿命修正 × 成形折减 × Goodman 折减 多层级修正
- 疲劳失败时给明确方向建议（降 σ_m、降 σ_a、改表面、加大规格）
- Goodman 因子低于阈值时追加工程预警

**本模块不做**：

- **不做 Miner 累计**：单幅值评估；多段谱需用户包络
- **不做 Haigh 图 / Smith 图分析**：只用 Goodman 折线近似
- **不做散差疲劳分布（Weibull 等）**：确定性评估
- **不考虑切口敏感系数 Kt / Kf**：σ_ASV 表已隐含"螺纹自身切口"，但不考虑螺栓其他几何切口（例如过渡圆角应力集中）
- **不自动判断 load_cycles 是否为低周范围**：N_L < 10³ 仍按 0.08 幂律外推；低周需用户自觉改用专项分析

## 输入 / 产出

**输入**：

| 字段 | 单位 | 典型值 |
|---|---|---|
| load_cycles | 次 | 10⁶（默认）/ 2×10⁶（保守高周）/ 10⁴（有限寿命） |
| surface_treatment | 字符串 | rolled（标准螺栓）/ cut（后加工螺纹） |
| yield_safety_operating | - | 1.1（默认）/ 1.15（重要连接） |
| report_mode | 字符串 | full / compact |

**产出**：

- σ_ASV_eff（修正后许用幅基准）[MPa]
- goodman_factor（可能为 0）
- σ_a_allow = σ_ASV_eff · goodman [MPa]
- σ_a 实际值 [MPa]
- fatigue_ok（通过 / 不通过）
- 服役 σ_vm_service_max 与许用 [MPa]

## 参考标准

- VDI 2230-1:2015（σ_ASV、Goodman 折减、寿命修正相关章节）
- ISO 898-1:2013（螺栓疲劳）

> Cannot verify against original VDI / ISO standard —— σ_ASV 数值、0.08 幂律、0.65 切削折减、Goodman 折线整理自公开文献；**未查证 VDI 2230-1:2015 原文**。本章实现位于 `core/bolt/tapped_axial_joint.py:263-286`（疲劳）、`228-237`（服役屈服）、`230-280`（surface / cycle 修正）。
