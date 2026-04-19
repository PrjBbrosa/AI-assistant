# 防滑最小安全系数（S_slip,min）

**一句话**：过盈连接**扭矩 / 轴向 / 联合作用**三条滑脱校核共用的最小安全系数门槛；"容量 ÷ 设计载荷" 必须不小于它，校核才算 PASS。

**怎么理解**：

过盈连接的服役失效最怕"整体滑脱"：轴在轮毂里转一个小角度，或向轴向方向窜动几毫米。一旦滑脱，摩擦面发生宏观相对滑动，扭矩容量会瞬间塌陷，并导致 fretting 加速和定位精度丢失。S_slip,min 就是在**最小过盈工况**（加工公差里最不利的一组）下，要求容量仍然比设计载荷大多少倍。

为什么要分开扭矩、轴向、联合作用三条：

1. **扭矩支线**：`T_cap / T_design ≥ S_slip,min`
2. **轴向支线**：`F_cap / F_design ≥ S_slip,min`
3. **联合作用支线**：两者同时作用时用矢量合成，`sqrt((T_design/T_cap)² + (F_design/F_cap)²) ≤ 1/S_slip,min`

联合作用最容易被忽略：两条单独支线都"通过"，但合成后仍不满足门槛。S_slip,min 对三条支线用**同一个值**，确保口径统一。

## 公式（本工具实现）

```
设计载荷:    T_design = KA · T_req              [T: N·m]
             F_design = KA · F_req              [F: N]

最小过盈端容量:
             T_cap_min = μ_T  · p_min · π·d·L · (d/2) / 1000   [T: N·m, p: MPa, d,L: mm]
             F_cap_min = μ_Ax · p_min · π·d·L                  [F: N]

PASS 判据（本工具）：
   扭矩:     T_cap_min ≥ S_slip,min · T_design
   轴向:     F_cap_min ≥ S_slip,min · F_design
   联合:     S_combined ≥ S_slip,min
             S_combined = 1 / sqrt( (T_design/T_cap_min)² + (F_design/F_cap_min)² )

张口缝:      p_min ≥ p_gap       （独立判据，不乘 S_slip,min）
最大过盈覆盖: δ_max ≥ δ_required  [um]

  其中 δ_required = δ_required_eff + subsidence_um
           δ_required_eff = 2 · c_total · p_required · 1000
                    [c_total: mm/N·mm², p_required: MPa → δ: μm]
           subsidence_um = 粗糙度压平量 s（回加进需求过盈）
           p_required = max(p_req,T, p_req,Ax, p_req,comb, p_gap)  [MPa]
              其中 p_req,T    = S_slip,min · p_req,T_service
                   p_req,Ax   = S_slip,min · p_req,Ax_service
                   p_req,comb = S_slip,min · √(p_req,T_service² + p_req,Ax_service²)
                   p_gap      = p_radial + p_bending  (与 S_slip 无关)
```

关键点：**S_slip,min 只进入防滑支线（扭矩 / 轴向 / 联合）放大需求接触压力；张口缝支线 p_gap 独立纳入 p_required 的 max，不乘 S_slip,min**。实现对照 `core/interference/calculator.py:295-311`。

## 典型值

| 工况类型 | S_slip,min 建议 | 说明 |
|---|---|---|
| **稳态传动，人身不临接触** | 1.1 ~ 1.3 | 普通传动轴 / 带轮 / 链轮毂 |
| **变载 / 小冲击** | 1.3 ~ 1.5 | 齿轮副轮毂（非人身相关） |
| **冲击载荷 / 启停频繁** | 1.5 ~ 1.8 | 压力机、冲床主轴、离合器毂 |
| **人身安全相关 / 关键传动** | 1.8 ~ 2.5 | 起重机吊钩、升降机 |
| **航空航天 / 高可靠性** | 2.5 ~ 3.0+ | 按行业规程，不按本工具默认 |

**本工具默认 1.20**，是"普通工业传动"的中值；冲击工况请在此基础上再提。

## 常见误用

- **和 KA 重复计入**：KA 是**需求侧**放大（按工况类型查表），S_slip,min 是**容量侧**门槛（按后果严重度定）。两者互补，不要只用一个顶两个。
- **S_slip,min < 1**：直接失去工程意义（容量低于设计载荷），不允许。
- **只看扭矩支线通过**：扭矩通过但联合作用失败的场景非常常见；必须看三条支线的综合结论。
- **最小过盈口径不含粗糙度**：本工具的 p_min 是 `δ_eff,min = max(0, δ_min − s)` 后算出的；若漏扣 s，S_slip 会虚高 20~40%。

## 出处

- DIN 7190-1 相关章节（防滑安全系数的判据定义与最小过盈量要求）
- Niemann / Winter 过盈配合章节

> Cannot verify against original DIN standard —— 本术语的典型值区间与联合作用矢量合成方法基于公开教科书与工程手册整理；**未查证 DIN 7190-1:2017 原文**，故不给出精确节号 / 表号。
