# Fretting 风险评估章节

本章节用于**开启或关闭微动腐蚀（fretting）风险的定性评估**，并填写载荷谱、工况严酷度、表面状态、部件重要度四个等级化输入。Fretting 评估属于**增强结果**，不改变前面章节的 DIN 7190 通过 / 不通过主结论（overall_pass）。

## 为什么要填这些

过盈配合的失效模式除了"整体滑脱 / 屈服 / 张口缝"之外，还有一个常被忽视的**微动疲劳**：即使整体不滑脱，循环载荷会让接触面发生**微米量级的相对位移**，磨掉表面、生成氧化粉末、加剧应力集中，最终从接触端萌生疲劳裂纹。

Fretting 是**工程经验主导**的领域，没有可靠的闭式公式。本工具按**规则打分** + 分级判定（low / medium / high / not_applicable），仅作为设计评审时的"值得警觉"提示。

## 本工具的简化评估（规则打分）

```
risk_score = spectrum_score + duty_score + surface_score + importance_score + slip_reserve_bonus

spectrum_score   ∈ {0 (steady), 1 (pulsating), 2 (reversing)}
duty_score       ∈ {0 (light),  1 (medium),    2 (heavy)}
surface_score    ∈ {0 (coated), 1 (oiled),     2 (dry)}
importance_score ∈ {0 (general),1 (important), 2 (critical)}
slip_reserve_bonus ∈ {0..3}   （扭矩或联合作用安全系数越接近 1，越加分）

risk_level:
   score ≤ 3  → low
   3 < score ≤ 8 → medium
   score > 8  → high
```

Cannot verify against original DIN standard —— 上述规则**不是**标准规定的评估方法，而是本工具内部基于若干公开经验指标整理的简化分级，主要目的是给新手"何时需要进一步查 fretting 专项"的提示。

## 开关与适用条件

```
fretting.mode = "off"  → 不计算，不输出 risk_level
fretting.mode = "on"   → 按规则打分，输出 low / medium / high 或 not_applicable
```

`not_applicable` 意味着当前过盈配合的某些前置条件不满足简化模型（例如存在显著弯矩、空心轴组合、模量差异过大）；此时 Fretting 评估被视为"超出简化范围"，需要手工判断。

## 输入字段说明

| 字段 | 选项 | 建议选择 |
|---|---|---|
| **载荷谱** | steady / pulsating / reversing | 稳态工况 steady；有方向但不过零 pulsating；正反转或双向扭矩 reversing |
| **工况严酷度** | light / medium / heavy | 按循环次数 × 载荷幅值综合判断 |
| **表面状态** | coated（涂层 / 处理） / oiled（有润滑） / dry（干） | 按实际装配状态 |
| **部件重要度** | general / important / critical | 一旦失效的后果（停机损失、安全事故） |

## 输入 / 产出

**输入**：
- 开关 on / off
- 载荷谱、工况严酷度、表面状态、部件重要度四项等级输入

**产出给结果**：
- risk_level（low / medium / high / not_applicable）
- risk_score 与最大可能分数
- 文本建议列表（提醒检查的具体方向）

## 常见坑

- **把 Fretting 当通过/不通过判据**：Fretting 评估只是**增强信息**；即使 risk=high，主 verdict 仍可能 PASS。对关键件应把 risk=medium 及以上视为"必须进一步分析"。
- **不设开关就忘了**：默认 off；若没打开，**不会**得到任何 fretting 反馈，也不会在报告中提到。关键件建议默认 on。
- **规则打分当科学结论**：本工具打分规则是简化启发式；复杂工况（高速、润滑中断、带腐蚀介质）应走专门的 fretting 疲劳试验或 Ruiz / Vingsbo-Söderberg 等专项评估。
- **载荷谱口径不一致**：同一颗齿轮传动有"启停脉动 + 稳态齿啮合脉动"两层；应按最严酷层选 reversing 或 pulsating。

## 参考文献

- Niemann / Winter 过盈配合 fretting 经验建议章节
- Ruiz-Chen fretting 疲劳评估方法（作为进阶参考，非本工具实现）
- Vingsbo & Söderberg fretting map（作为理论背景，非本工具实现）

> Cannot verify against original DIN standard —— 本模块的 fretting 规则打分方案**不是**标准规定的评估方法；DIN 7190 没有规定 fretting 闭式判据。本节内容仅供设计评审时作为"何时需要深入查 fretting 专项"的触发器使用。
