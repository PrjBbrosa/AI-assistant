# 载荷工况章节

本章节用于**录入两场景共用的名义扭矩 T 与轴向力 F_ax**。T 会在计算入口乘上工况系数 K_A 变成设计扭矩 T_design，同时被场景 A（花键齿面承压）与场景 B（光滑段过盈）使用；F_ax 只影响场景 B。

## 为什么要填这些

- **名义扭矩 T**（N·m）：两场景共用。场景 A 用 `T_design · k_α` 代入齿面压力公式；场景 B 用 `T_design` 与过盈产生的接触压力、摩擦系数、接触面积对比，给出防滑安全系数。
- **轴向力 F_ax**（N）：**仅场景 B 使用**。花键齿面的轴向载荷分担（齿压力角 × 切向力）本工具未显式校核（属于"未实现"清单）；场景 B 的 F_ax 只进入 DIN 7190 的防滑 / 屈服校核。

`仅花键`模式下 F_ax 字段虽然可见，但不参与 payload（见 `_build_payload` 的 `active_sections` 逻辑，F_ax 属于 `loads` section —— `loads` 始终被激活，但其中只有 `torque_required_nm` 和 `application_factor_ka` 进入场景 A 计算）。

## 输入 / 产出

**输入**：
- `loads.torque_required_nm`（N·m）：名义工作扭矩
- `loads.axial_force_required_n`（N）：名义轴向力，`仅花键`模式下取 0 即可

**产出**：
- `T_design = T_required · K_A`（N·m）—— 在 `calculate_spline_fit` 入口一次性预乘，见 `calculator.py:222`
- `F_ax_design = F_ax_required · K_A`（N）—— 同样在入口一次性预乘（仅联合模式）
- 传给场景 A 的是 `T_design`；传给场景 B 的是 `(T_design, F_ax_design, ka=1.0)` ——**`ka=1.0` 是刻意的**，避免 `calculate_interference_fit` 又一次对 T 乘 K_A。

## 常见坑

- **混淆"名义扭矩"与"峰值扭矩"**：DIN 6892 / DIN 7190 的 K_A 本身就是为了把"名义"放大到"峰值"。这里只填**名义**（平均 / 额定 / 铭牌）扭矩，由 K_A 统一放大。若已经填峰值又选了 K_A > 1，等于双倍放大。
- **单位写错**：T 单位是 **N·m**（不是 N·mm）。场景 A 内部 `T_nmm = T_nm · 1000` 自动换算。填 `5000` 意思是 5000 N·m（大多数机械联轴器已经是很大的扭矩）；若数值写错成 `5000000`（当成 N·mm 直接填），会 PRECHECK FAIL 且数值明显异常。
- **F_ax 填成"扭矩折算的圆周力"**：齿轮 / 蜗轮传动里 F_t = 2·T / d 是切向力，不是轴向力；本字段专指**沿花键轴线方向的压 / 拉力**（例如斜齿推力、装配安装力残余）。
- **`仅花键`模式下 F_ax 填 0 也是安全的**：场景 A 完全不用 F_ax，场景 B 未启用，即便填非零值也不会错。留 0 就行。

## 参考标准

- DIN 6892:2012（花键连接承载能力，K_A 使用约定）
- DIN 7190-1:2017（圆柱过盈配合·F_ax 参与防滑校核）

> Cannot verify against original DIN standard —— 条款号为笼统文献出处，未逐条比对正文。
