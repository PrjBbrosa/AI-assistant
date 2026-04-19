# 花键几何章节

本章节用于**录入渐开线花键（DIN 5480 风格）的几何参数**：选择标准规格或手动输入 m / z / d / d_a1 / d_f1 / d_a2，同时给出啮合长度 L、载荷分布系数 k_α 与许用齿面压力 p_zul。这些是场景 A 齿面平均承压校核的全部输入源头。

## 为什么要填这些

花键齿面压力的简化公式是：

```
p_flank = 2 · T_design · k_α / (z · h_w · d_m · L)   [T: N·mm, 其余 mm → p: MPa]
```

其中：
- `T_design = T_required · K_A`，由载荷工况章节确定。
- `z`：齿数。
- `h_w = (d_a1 - d_a2) / 2`：有效齿高（单侧承载），由齿顶圆派生。
- `d_m = (d_a1 + d_a2) / 2`：接触区平均直径。
- `L`：轴向有效啮合长度。
- `k_α`：齿向 + 齿面载荷分布系数的合成上限。

因此几何章节每一个字段都会直接进入这个公式。任何一项偏离真实值 10% 就可能让 `p_flank` 误差 10~20%，进而让 PASS / FAIL 判据翻转。

## 输入 / 产出

**输入**：
- **标准花键规格**：选择 `W 15x1.25x10` 这类 DIN 5480 条目，自动填充 m / z / d / d_a1 / d_f1 / d_a2（查 `core/spline/din5480_table.py` 的内置 catalog），并把几何输入模式切到`公开/图纸尺寸`。选`自定义`时保持手动输入。
- **几何输入模式**：`公开/图纸尺寸` 或 `近似推导（仅预估）`。
  - `公开/图纸尺寸`：要求 `reference_diameter_mm`、`tip_diameter_shaft_mm`、`root_diameter_shaft_mm`、`tip_diameter_hub_mm` 四个值同时给出；缺一不可（`geometry.py` 会抛 `GeometryError`）。
  - `近似推导`：只给模数 m 与齿数 z，工具按保守下限派生（见下"方法差异"）。
- **模数 m**、**齿数 z**（≥ 6）、**参考直径 d_B**、**d_a1 / d_f1 / d_a2**
- **有效啮合长度 L**（mm）
- **载荷分布系数 k_α**：默认 1.3，可在 1.0~2.0 之间调整。过盈固定连接约 1.0~1.3，滑移连接约 1.5~2.0。**本工具把 DIN 6892 的 K_1 · K_2 · K_3 合成为单一 k_α 保守上限，未做逐一分解**。
- **载荷工况**：下拉选项（固定/脉动 × 调质/渗碳）→ 自动填充 p_zul。选`自定义`时 p_zul 解锁手动输入。
- **许用齿面压力 p_zul**（MPa）

**产出**：
- `geometry` 字典：包含 d、d_a1、d_a2、d_f1、h_w、d_m、`approximation_used` 标志、以及近似模式下附加的 messages（会作为 `场景 A:` 前缀出现在结果消息区）。
- `flank_pressure_mpa`、`torque_capacity_nm`、`flank_safety` 等场景 A 结果。

## 方法差异（本工具实际行为）

两种几何输入模式在 `core/spline/geometry.py:derive_involute_geometry` 里分支处理：

**`公开/图纸尺寸` 模式（`allow_approximation=False` 且四个尺寸全给）**：
1. 校验 `d_f1 < d_a2 < d_a1 < d` 的物理顺序。
2. 如果同时给了 m × z，会与用户输入的 d 比对 —— 相对偏差 > 5% 会在 messages 里追加警告（但不阻断计算）。
3. `geometry_source = "explicit_reference_dimensions"`、`approximation_used = False`。

**`近似推导` 模式（`allow_approximation=True` 且未给四个尺寸）**：
```
d    = m · z
d_a1 = d - 0.5 · m       [外花键齿顶圆]
d_a2 = d - 1.5 · m       [内花键齿顶圆]
d_f1 = d - 2.0 · m       [外花键齿根圆]
h_w  = (d_a1 - d_a2)/2 = 0.5 · m  [取 DIN 5480-2:2015 catalog 最小 h_w/m = 0.5 作保守下限]
```
不同 catalog 条目的实际 h_w/m 在 0.5~1.08 之间，近似模式永远取下限。这样算出的 `p_flank = 2T·k_α/(z·h_w·d_m·L)` 会**不低于**真实值（因为 h_w 被取小了），让 PASS 判据更保守。`geometry_source = "approximation_from_module_and_tooth_count"`、`approximation_used = True`，并在 messages 里追加"近似模式使用 DIN 5480-2 catalog 最小 h_w/m=0.5 作保守下限..."提示。

> **关键差异**：两种模式下算出的 `p_flank` 对同一工况会不同 —— 近似模式永远更悲观。近似模式只适合方案阶段的快速判断；详细设计必须切到`公开/图纸尺寸`并录入图纸或实测的 d_a1 / d_a2 / d_f1。

## 常见坑

- **选了标准规格但没注意几何输入模式**：选完标准规格后 UI 会自动切到`公开/图纸尺寸`并把 m/z/d/d_a1/d_a2/d_f1 六个字段锁成 `AutoCalcCard`。如果再手动切回`近似推导`并手动改值，会进入"混合态"——字段解锁但 catalog 填入的值仍在；对比 catalog 原值与编辑后的值要看字段是否已经是 `SubCard`（解锁态）。
- **h_w 手动计算**：用户经常按 `h_w = m`（渐开线外齿轮经验）估。花键的 h_w 是**单侧**承载齿高，对 DIN 5480 30° 系列平均只有 0.9·m 左右，小齿数大模数条目可低至 0.5·m。不要套齿轮公式。
- **L 填"轴向总长"而不是"有效啮合长度"**：轴向总长可能包含了端部倒角、退刀槽、花键根部不承载段。DIN 6892 的 L 只取"真正传递载荷的那一段"，通常比图纸标注的"花键长度"短 2~5 mm。

## 参考标准

- DIN 5480-1:2006（渐开线花键·一般规则 & 术语）
- DIN 5480-2:2015（30° 压力角 catalog，本工具查表数据来源）
- DIN 6892:2012（花键连接承载能力，k_α / K_1 · K_2 · K_3 合成参考）

> Cannot verify against original DIN standard —— 条款编号为笼统出处，未逐条比对原文。DIN 5480 对非 30° 压力角系列（如 37.5°、45°）的尺寸表本工具未内置。
