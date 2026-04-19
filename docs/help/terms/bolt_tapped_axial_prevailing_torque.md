# 附加防松扭矩（prevailing_torque）

**一句话**：锁紧件（尼龙圈螺母、变形螺母、螺纹胶等）在拧紧过程中产生的**不参与预紧、仅克服防松阻力**的附加扭矩 [N·m]；直接累加到装配扭矩 MA 的结果里。

**怎么理解**：

普通螺栓拧紧时，施加扭矩 MA 换来预紧力 F_preload 和克服支承 / 螺纹摩擦的损耗：

```
MA = F_preload · (k_thread + k_bearing) / 1000     [F: N, k: mm → MA: N·m]
```

但使用防松件（如 ISO 7040/DIN 985 尼龙嵌圈螺母、DIN 6927 全金属防松螺母、Nord-Lock 垫圈、螺纹胶 Loctite 等）时，**还有一部分扭矩纯粹用来克服"防松阻力"**，不贡献预紧力。本工具把它累加进 MA：

```
MA = F_preload · (k_thread + k_bearing) / 1000 + prevailing_torque    [N·m]
```

其中 `prevailing_torque` 是锁紧件自身的防松扭矩（产品规格中给出），**不影响 F_preload、应力、疲劳、脱扣等任一校核结果**，只改变 MA 的数值。`core/bolt/tapped_axial_joint.py:249-253` 实现。

## 什么时候填 0

多数常规工况填 0：

- 普通六角螺母、螺栓自锁结构依靠预紧摩擦防松
- 只用弹簧垫圈 / 碟形垫圈（防松效果有限但不产生显著 prevailing torque）
- 工具链默认无防松件

## 什么时候要填

使用了有明确 prevailing torque 规格的锁紧件：

| 防松件类型 | 典型 prevailing_torque（M10 参考） |
|---|---|
| ISO 7040 全金属压扁螺母（Stover） | 8 – 15 N·m |
| DIN 985 尼龙圈螺母（Nyloc） | 3 – 6 N·m |
| DIN 6927 全金属法兰防松 | 10 – 18 N·m |
| Nord-Lock 楔形垫圈 + 普通螺母 | 0（靠预紧力维持，不产生 prevailing） |
| Loctite 243（中强度螺纹胶） | 5 – 10 N·m（固化后） |
| Loctite 271（高强度螺纹胶） | 20 – 35 N·m |

**精确值请查产品数据表**——同规格 M10 在不同品牌、批次、温度、润滑条件下可差一倍。工程估算先填类别典型值，最终以实测为准。

## 为什么只改 MA、不改 F_preload

物理上 prevailing_torque 被螺纹 / 垫圈的"弹性变形 + 塑性变形"吸收，**不转化为螺栓伸长**。所以：

- 扭矩扳手读数 = MA（含 prevailing）；操作者按此标定
- 螺栓实际预紧力 = 正常公式（不含 prevailing）
- 若扭矩扳手设定值漏算 prevailing，实际得到的 F_preload **低于预期**（因为一部分扭矩被锁紧件"吃掉"了）

这是使用防松件时最常见的装配错误：扭矩目标没把 prevailing 加进去，结果预紧力不足。

## 典型填法建议

| 场景 | 填法 |
|---|---|
| 普通螺栓 + 六角螺母 | 0 |
| 尼龙嵌圈螺母 | 产品规格值（通常 3–6 N·m for M10） |
| 全金属防松螺母 | 产品规格值（通常 8–15 N·m for M10） |
| 螺纹胶 | 产品规格最大值（保守估算，取胶未完全固化前的阻力） |
| 不确定 | 先填 0 做基础校核，再查防松件规格做扭矩上修 |

## 边界检查

`core/bolt/tapped_axial_joint.py:204-205` 用 `_float_or_none` 允许空值和 0；不允许负值（_positive 系统强制），但**也不限制上限**。填了过大值（例如写错单位，把 N·cm 当 N·m）时工具不会报错，但输出的 MA 会显著偏高，应自查。

## 常见误用

- **误把 prevailing_torque 当成增强预紧力的"加分项"**：它**不增加 F_preload**，完全是扭矩扳手读数的附加项。
- **单位填错 N·cm 或 kN·mm**：务必用 N·m，与其他扭矩输出（MA_min、MA_max）统一。
- **螺纹胶工况忘记填**：螺纹胶固化后防松扭矩可达 20–35 N·m，扭矩扳手不含这部分值会导致预紧力 30%–50% 不足。
- **以为它会改变疲劳 / 脱扣结果**：不会。它只改装配扭矩数值，不进任何应力链。

## 相关

- 装配扭矩 MA_min / MA_max → 结果界面显示
- 摩擦系数 μ_thread / μ_bearing → `terms/bolt_friction_thread` / `terms/bolt_friction_bearing`
- 拧紧方式 → `terms/bolt_tightening_method`

**出处**：ISO 2320（全金属防松螺母）、ISO 7040（尼龙嵌圈螺母）；VDI 2230-1:2015 装配扭矩计算相关章节

> Cannot verify against original ISO / VDI standard —— prevailing torque 的典型值来自公开产品数据表整理；**未查证 ISO 2320 / 7040 / VDI 2230 原文**，精确值请以具体产品数据表（Stover / Nyloc / Loctite TDS 等）为准。本工具实现位于 `core/bolt/tapped_axial_joint.py:204-253`。
