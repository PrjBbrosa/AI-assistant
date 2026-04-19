# 装配流程章节

本章节用于**选择装配模式并填写工艺参数**：manual_only（仅压入力估算）、shrink_fit（热装）、force_fit（压装）。装配模式不影响 DIN 7190 核心校核（通过/不通过由前面章节决定），但会改变压入力估算、所需加热温度与装配摩擦追溯。

## 为什么要填这些

装配模式决定**服役摩擦 vs 装配摩擦**的分离：
- 压装：μ_in / μ_out 通常低于静摩擦（滑动动态、有装配油）；用它估压入/压出力
- 热装：装配阶段瞬间几乎无摩擦（有装配间隙），校核重点转为"轮毂加热到什么温度才装得进去"
- 仅压入力估算：不区分工艺，按摩擦章节的 μ_Assy 做通用压入力估算

## 三种装配模式（本工具实现）

### `manual_only`
- 仅做通用压入力估算：`F_press = μ_Assy · p · π·d·L`
- μ_Assy 来自"摩擦与粗糙度"章节
- UI 会把本章节里的其他字段锁定为灰色

### `shrink_fit`（热装）
需要解决两个问题：**轮毂加热到多少度才能刚好滑入**，以及**这个温度是否超出材料限制**。

```
装配间隙 clearance_um（本工具实现）：
   diameter_rule  → clearance_um = d_shaft   [d_shaft: mm → clearance_um: μm]
                                  （每 1 mm 直径预留 1 μm，即 d/1000 mm；数值上等于 d 的毫米数）
   direct_value   → 直接输入 clearance_um                          [μm]

所需加热温度（本工具实现，对照 core/interference/assembly.py:116-124）：
   required_expansion_um = δ_max + clearance_um               [δ: μm, clearance: μm → μm]
   hub_growth_per_c      = α_h · d_shaft / 1000               [α_h: 10⁻⁶/°C, d: mm → μm/°C]
   T_hub_required = T_amb
                  + required_expansion_um / hub_growth_per_c
                  + (α_shaft / α_hub) · (T_shaft − T_amb)       [μm/(μm/°C) = °C]
```

若 T_hub_required > `hub_temp_limit_c`（材料热处理允许上限），本工具会发出警告。典型限制：调质钢 250~300°C（再高回火性能退化）、铝合金 150~180°C（过时效）。

**轴预冷修正（第三项）**：若轴用液氮或干冰冷却到低于环境温度，`shaft_temperature_c` 输入冷却后的温度，第三项 `(α_shaft/α_hub)·(T_shaft-T_amb)` 按两种材料膨胀系数的比值折算等效到"所需轮毂额外温度"，避免冷却轴的几何变化被漏算。

### `force_fit`（压装）

```
F_in  = μ_in  · p · π·d·L                                [F: N, p: MPa, d,L: mm]
F_out = μ_out · p · π·d·L                                [F: N]
```

μ_in（压入摩擦）一般取 0.06~0.10；μ_out（压出摩擦）常略低于 μ_in（表面已被抚平，残余油膜持续存在），取 0.05~0.08。压装工艺会给表面带来轻微塑性变形，首次压入后再拆装的摩擦行为会改变。

## 输入 / 产出

**输入**：
- 装配模式（manual_only / shrink_fit / force_fit）
- shrink_fit：装配间隙模式与数值、环境温度、轴装配温度、轮毂与轴的线膨胀系数、轮毂允许最高装配温度
- force_fit：μ_press_in、μ_press_out

**产出给下一步**：
- manual_only / shrink_fit：通用压入力（用 μ_Assy）
- force_fit：专属压入力 F_in、压出力 F_out
- shrink_fit：所需加热温度 T_hub、超限警告

## 装配模式切换的字段联动

UI 会根据装配模式锁定 / 解锁字段卡：

| 字段 | manual_only | shrink_fit | force_fit |
|---|---|---|---|
| 热装温度 / 间隙相关 | 锁定 | **解锁** | 锁定 |
| μ_press_in / μ_press_out | 锁定 | 锁定 | **解锁** |
| 通用压入力 | 仍按 μ_Assy 显示 | 替换为 T_hub 需求 | 替换为 F_in / F_out |

## 工艺选择建议

| 连接场景 | 推荐装配模式 | 理由 |
|---|---|---|
| 齿轮 / 传动轴套 / 轴承内圈 | shrink_fit | 大批量、温差可控、不留装配伤 |
| 锥孔联轴器、小尺寸销套 | force_fit | 无需加热设备，成本低 |
| 图纸约束或首件试制 | manual_only | 工艺待定阶段先通过校核 |
| 精密主轴 / 高精度轴承 | shrink_fit（优先） | 压装会擦伤精密配合面 |

## 常见坑

- **热装温度算出 400°C 仍硬压**：一次性把轮毂加热超过回火温度会让材料性能退化；应优先减小 δ_max 或改成阶梯过盈。
- **液氮冷轴时没填 T_shaft**：默认两温度都等于 T_amb，会低估预冷效果；液氮 −196°C、干冰 −78°C 是常用数值。
- **线膨胀系数取反侧材料**：α_h 是**轮毂**材料的，α_s 是**轴**材料的；若轴是钢、轮毂是铝，α_h 要取 23·10⁻⁶/°C 不是 11·10⁻⁶/°C。
- **直接用 diameter_rule 的装配间隙校核精密配合**：diameter_rule = 1·d(mm) 是通用粗略值；精密场合应按工艺规范给 direct_value。
- **force_fit 的 μ_in 取服役摩擦**：服役摩擦默认 0.12~0.15，用到压入会让压入力估得偏高；设备选型如此易超裕量，浪费投入。

## 参考标准

- DIN 7190-1 装配工艺（热装 / 压装）相关章节
- 工艺经验手册（如 Roloff/Matek 机械设计）关于装配温度与装配间隙的推荐

> Cannot verify against original DIN standard —— 本章节所述的装配间隙经验规则（diameter_rule = 0.001·d）、热装温度公式基于公开教科书与代码注释整理；**未查证 DIN 7190-1 原文**，故不给出精确节号 / 表号。
