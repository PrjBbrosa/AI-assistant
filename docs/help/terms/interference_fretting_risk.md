# Fretting 风险评估（fretting.mode）

**一句话**：微动腐蚀（fretting corrosion）风险的定性评估开关；本工具按规则打分给出 low / medium / high 分级，但**不改变 DIN 7190 核心通过/不通过主结论**。

**怎么理解**：

过盈配合即使"整体不滑脱"，在循环载荷下接触面仍可能发生**微米量级**相对位移，产生：
- 界面磨损 + 氧化粉末
- 局部摩擦系数降低
- 应力集中加剧
- 端部疲劳裂纹萌生

最终可能从接触端面起裂，走疲劳失效路径。这种现象称为 **fretting**（微动）或 **fretting corrosion**（微动腐蚀）。

Fretting 是**工程经验主导**的领域，没有可靠的闭式判据公式。本工具的 Step 5 评估不是严格的工程校核，只是"值得警觉"的触发提示。

## 三种状态（本工具实现）

```
fretting.mode = "off":
   不评估，不输出 risk_level
   report 不包含 fretting 段

fretting.mode = "on" + 简化条件满足:
   按规则打分，输出 risk_level = low / medium / high
   提供文本建议

fretting.mode = "on" + 简化条件不满足（空心轴、大弯矩、模量差异大、L/d ≤ 0.25）:
   risk_level = not_applicable
   提示"当前工况超出简化模型适用范围，需要手工判断"
```

**注意**：未开启时**不会有任何警告**。默认 off，即使工况危险也不输出风险提示。

## 评分规则（本工具实现）

```
risk_score = torque_reserve_bonus + combined_reserve_bonus
           + spectrum_score + duty_score + surface_score + importance_score
max_score  = 14.0

torque_reserve_bonus (S_torque 越接近 1 越扣分多):
   S_torque ≤ 1.2    : +3
   S_torque ≤ 1.5    : +2
   S_torque ≤ 2.0    : +1
   S_torque > 2.0    : 0

combined_reserve_bonus (S_combined 分开再加一次):
   S_combined ≤ 1.2  : +3
   S_combined ≤ 1.5  : +2
   S_combined ≤ 2.0  : +1
   S_combined > 2.0  : 0

spectrum_score (载荷谱):
   steady    : 0    （稳态单向）
   pulsating : 1    （单向脉动）
   reversing : 2    （双向往复）

duty_score (工况严酷度):
   light     : 0    （循环次数少、冲击小）
   medium    : 1    （中等频率）
   heavy     : 2    （高循环 + 冲击）

surface_score (表面状态):
   coated    : 0    （涂层 / 处理）
   oiled     : 1    （有装配油）
   dry       : 2    （干燥）

importance_score (部件重要度):
   general   : 0    （非关键）
   important : 1    （一般关键）
   critical  : 2    （安全相关）

risk_level 分级（按 score 与 max_score=14 的比例）:
   score ≤ 3         : "low"
   3 < score ≤ 8     : "medium"
   score > 8         : "high"
```

实现对照 `core/interference/fretting.py:148-217`。**扭矩储备与联合作用储备是两项独立的加分项**，不是一个"slip_reserve"——这意味着 S_torque 低且 S_combined 也低的工况会双倍惩罚（各加 3 分，共 6 分），反映两个独立的微滑移路径都在消耗裕度。

**Cannot verify against original DIN standard** —— 上述规则**不是**标准评估方法；DIN 7190 没有规定 fretting 闭式判据。本规则是本工具内部基于若干公开经验指标整理的启发式分级。

## 输出与建议

启用时本工具在 messages 段输出：

```
[Step 5] Fretting 风险等级: low / medium / high / not_applicable
[Step 5 建议] <文本建议列表>
```

建议示例（按风险等级）：
- **low**：维持现状，常规检测即可
- **medium**：建议定期检查接触端面、考虑使用装配油 / 涂层
- **high**：强烈建议增加防 fretting 措施（涂层、表面处理、改连接形式）或走 fretting 专项疲劳评估

## 简化模型的适用条件

本工具的 fretting 评估**仅在以下条件满足时**给出 risk_level：

1. **配合长度比例**：L/d > 0.25（短轴不适用）
2. **实心轴**：空心轴标 not_applicable
3. **模量接近**：|E_shaft - E_hub| / max(E_shaft, E_hub) ≤ 5%
4. **无显著弯矩**：M_b,design = 0

以上任一不满足 → risk_level = "not_applicable"，提示"需要手工判断"。这是**非常严格**的适用条件，大部分工程实际案例会落到 "not_applicable"；这是有意设计的保守策略，避免工具给出过于简化的结论。

## 什么时候特别要启用 fretting 评估

- 循环扭矩 / 反向扭矩（正反转）
- 冲击工况（启停频繁、锻锤、破碎机）
- 高可靠性要求（起重机、升降机、航空、医疗）
- 失效后果严重（人身安全、巨额停产）

## 常见误用

- **把 Fretting 当通过/不通过判据**：只是增强信息，不改变 DIN 7190 主结论。即使 high 也不会把 overall_pass 翻成 False。
- **默认 off 就当没风险**：未启用时**不会告警**；关键件必须手动打开。
- **规则打分当科学结论**：复杂工况（高速、腐蚀介质、润滑中断）必须走专门的 Ruiz / Vingsbo-Söderberg 等专项评估。
- **载荷谱口径不一致**：同一齿轮传动有多层载荷循环（启停 + 齿啮合 + 载荷变化）；应按**最严酷层**填 reversing 或 pulsating。
- **not_applicable 以为是 PASS**：表示"超出简化模型适用范围"，不是"安全"；需要走专项分析。

## 参考文献

- Niemann / Winter 过盈配合 fretting 经验建议
- Ruiz-Chen fretting 疲劳评估方法（进阶参考，本工具**未**实现）
- Vingsbo & Söderberg fretting map（进阶参考，本工具**未**实现）

> Cannot verify against original DIN standard —— 本工具的 fretting 规则打分**不是**标准评估方法；**未查证 DIN 7190-1:2017 原文**涉及 fretting 的约定（标准对 fretting 本身没有闭式判据）。本节仅作为设计评审的触发器，不构成工程合规证明。
