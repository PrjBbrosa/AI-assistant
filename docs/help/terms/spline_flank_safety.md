# 齿面最小安全系数（S_flank,min）

**一句话**：花键齿面平均承压校核要求的最小安全系数门槛；工具计算出的 `flank_safety = p_zul / p_flank` 必须 ≥ S_flank,min 才判 PASS。

**怎么理解**：

场景 A 的判据很简单：

```
flank_safety = p_zul / p_flank        [MPa / MPa = 无量纲]
flank_ok     = (flank_safety >= flank_safety_min)
```

其中：
- `p_flank`：工具按简化公式 `p_flank = 2·T_design·k_α / (z·h_w·d_m·L)` [MPa] 算出的齿面平均压力。
- `p_zul`：选定载荷工况下的许用齿面压力（MPa）。
- `flank_safety_min`：本字段，默认 1.30。

工具同时给出一个"扭矩视角"的等价指标：`torque_capacity_sf = T_cap / T_design`，其中 `T_cap = p_zul·z·h_w·d_m·L / (2·k_α)`。数学上 `flank_safety ≡ torque_capacity_sf`，只是换算到扭矩单位更直观。UI 结果区标注"S (= T_cap/T_design)"就是为了让用户一眼看出两者等价。

**为什么本工具的 `flank_safety` 不是 DIN 6892 意义上的"齿面承载能力"**：

- 本工具用 `p_flank = 2T·k_α/(z·h_w·d_m·L)` 这种**平均承压**模型，没有把 K_1 / K_2 / K_3 拆开（工具用单一保守的 k_α 合成）。
- 许用 p_zul 按"固定 / 脉动 × 调质 / 渗碳"四档查表，不包含硬度具体数值、表面处理细节、温度修正。
- 不包含齿根弯曲、剪切、胀裂、寿命 / 磨损（见 `calculator.py:102` 的 `not_covered_checks` 列表）。

因此这个 `flank_safety` 不是"DIN 6892 合规的 S_H"，只是"在简化预校核口径下的保守判据"。UI 显示 "PRECHECK PASS"、`overall_verdict_level = simplified_precheck` 就是这个意思。

**典型值 / 场景**：

- **1.2 ~ 1.3**：常规工业连接，载荷谱基本稳定，材料与工艺可控。本工具默认 1.30。
- **1.3 ~ 1.5**：有一定载荷波动 / 冲击，或加工、装配一致性稍差。
- **1.5 ~ 2.0**：高冲击、反复启停、安全关键（人员风险 / 高价值设备）；或材料数据、p_zul 表本身存在不确定性，需要额外裕度。
- **< 1.2**：除非有明确的试验或计算依据，否则偏冒进；尤其在近似几何模式下（h_w 已经取了保守下限）继续压低 SF，剩余裕度不足以覆盖其它未校核项（齿根弯曲、磨损）。

**常见误用**：

- **把 flank_safety 与 torque_capacity_sf 当独立双判据**：两者数学等价，不是两重保险。
- **用 flank_safety = 1.05 来接受 PASS**：近似模式下 h_w 已经打了"保守下限"折扣（让 p_flank 偏高），再把 SF 门槛压到刚过 1.0，其实整体并不保守（未覆盖项没有额外 margin）。
- **混淆 S_flank,min 与 p_zul**：前者是比值门槛（≥ 1），后者是允许应力（MPa）；不能把 p_zul 的单位误当安全系数。

**出处**：本工具判据依 DIN 6892:2012 的 S_H 习惯设计；具体取值参考工程经验。

> Cannot verify against original DIN standard —— DIN 6892 对各工况下 S_H 建议值未逐条比对原文。
