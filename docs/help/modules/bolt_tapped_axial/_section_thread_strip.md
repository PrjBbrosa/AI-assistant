# 螺纹脱扣

本章节校核**螺栓在服役最大拉力下，内外螺纹是否会被剪断（脱扣 / 滑牙）**。对**拧入螺纹对手件**的场景（尤其是铝 / 铸铁壳体上的螺纹孔）尤其重要。

## 为什么要填这些

螺栓拉断之前，**螺纹牙可能先被剪断**。特别是当内螺纹材料（壳体）比螺栓材料软时，内螺纹先失效——这种失效从外观不可见，却是致命模式。

本章节提供三个关键输入让工具判别：

- **m_eff**：有效啮合长度（螺栓实际旋入内螺纹的承载长度）
- **τ_BM**：内螺纹（螺母 / 壳体）材料的剪切强度
- **τ_BS**：外螺纹（螺栓）材料的剪切强度（留空自动取 0.6·Rp0.2）
- **safety_required**：设计要求的脱扣安全系数（典型 1.25 – 1.5）

## 公式（本工具实现）

```
A_SB      = π · d3 · m_eff · C1        [d3, m_eff: mm → A: mm²]   # 外螺纹剪切面积
A_SM      = π · d  · m_eff · C3        [d, m_eff: mm  → A: mm²]   # 内螺纹剪切面积
F_strip_B = A_SB · τ_BS                [A: mm², τ: MPa → F: N]    # 外螺纹剪切承载力
F_strip_M = A_SM · τ_BM                [A: mm², τ: MPa → F: N]    # 内螺纹剪切承载力
F_bolt_max = F_preload_max + FA_max    [F_preload_max: N, FA_max: N → F_bolt_max: N]
S_strip   = min(F_strip_B, F_strip_M) / F_bolt_max   [F: N → S_strip: 无量纲]
通过条件：S_strip ≥ safety_required                   [两侧均无量纲]
```

其中：
- **C1 = 0.75**（外螺纹有效承载系数）
- **C3 = 0.58**（内螺纹有效承载系数）

这两个系数可通过 `thread_strip.C1`、`thread_strip.C3` 覆盖；默认值见 `core/bolt/tapped_axial_joint.py:291-294`。**UI 不暴露这两个字段**——一般默认值对公制 ISO 螺纹足够。

**临界侧**：`F_strip_B <= F_strip_M` → "螺栓侧（外螺纹）"；反之 "壳体侧（内螺纹）"。建议针对性加深或换材料。

## 重要：未填 m_eff 的语义

这是**本模块与 VDI 2230 夹紧连接模块 `bolt_page.py` 行为最关键的差异**，务必理解。

当 `m_eff` 留空（未填）：

1. `checks.thread_strip_ok` 设为 **None**（不是 True 也不是 False）
2. `thread_strip.status = "not_checked"`，`active = False`
3. **强制 `overall_status = "incomplete"`**（`core/bolt/tapped_axial_joint.py:396-414`）
4. 工具自动追加 warning：「螺纹脱扣未校核：未提供 thread_strip.m_eff 等必要输入；请填写啮合长度与对手件材料剪切强度后再判定总体结论。」

结果界面：

- 分项校核那一行显示「未校核」灰徽章
- 总体结论显示「校核不完整」橙色等待徽章
- 消息面板显示上述 warning

**这意味着跳过 R8 不会给虚假绿灯**——UI 会明确告诉你"你漏校了一项"。与 Stage 2 bolt_page.py（VDI 2230 夹紧连接）里的"默默跳过"行为**不同**，后者可能整体返 `pass` 而不警告用户。

### 什么时候可以接受 `incomplete`

**只有在你确认 R8 不会成为瓶颈时**，才可接受 `incomplete`：

- 使用 ISO 4032 / DIN 934 标准螺母（螺母强度等级 ≥ 螺栓）
- 已有上游评审或产品认证覆盖 R8
- 螺栓旋入钢基体，m_eff ≫ 1.5d 且内螺纹孔质量受控

即便如此，**建议补全 m_eff 让工具给出明确 PASS**，避免日后审阅报告时误判。

### 什么时候**必须填**

- 螺栓旋入铝 / 铸铁 / 镁 / 塑料基体
- m_eff ≤ 1.0d 或接近该下限
- 重要连接需完整校核记录
- 设计依赖于脱扣校核通过

## 启用 R8 必须同时填 m_eff + τ_BM

`core/bolt/tapped_axial_joint.py:316-321`：只填 m_eff 不填 τ_BM 会抛 `InputError("thread_strip.tau_BM（内螺纹材料剪切强度）必须 > 0")`。τ_BS 有默认值（0.6·Rp0.2），可不填。

## 输入 / 产出

**输入**：

| 字段 | 单位 | 说明 |
|---|---|---|
| m_eff | mm | 有效旋合深度；留空 → 跳过 R8，overall = incomplete |
| τ_BM | MPa | 内螺纹材料剪切强度；启用 R8 必填 |
| τ_BS | MPa | 外螺纹材料剪切强度；留空默认 0.6·Rp0.2 |
| safety_required | - | 设计要求安全系数，典型 1.25 – 1.5 |

**产出**（R8 启用时）：

- A_SB, A_SM [mm²]
- F_strip_B, F_strip_M [N]
- S_strip（实际安全系数）
- critical_side（bolt / counterpart）
- 失败建议（指向"加深 m_eff" 或 "提高对手件材料强度"）

## 典型值速查

| 场景 | m_eff 典型 | τ_BM 典型 [MPa] |
|---|---|---|
| M10 × 钢螺母（8 级螺母） | 0.8d = 8 mm | ≈ 380 |
| M10 × 钢螺纹孔（基础设计） | 1.0d = 10 mm | 取螺栓同材料或基体实测 |
| M10 × 铝 6061 壳体 | 1.5 – 2.0d = 15 – 20 mm | ≈ 180 |
| M10 × 铸铁 HT200 壳体 | 1.5d = 15 mm | ≈ 200 |

## 常见误用

- **只填 m_eff 不填 τ_BM**：直接抛 `InputError`。两个必须一起填（若启用 R8）。
- **m_eff 填螺母全高**：实际有效承载按 0.8–1.0 倍螺母高度取。
- **τ_BM 填 Rp0.2 而非 0.6·Rp0.2**：高估承载 67%。
- **铝壳体未加深 m_eff**：M10 在 Al 6061 需 ≥ 1.5d，留默认 0.8–1.0d 会判 FAIL。
- **降低 safety_required 让 R8 勉强过**：这是错误做法；应检查 m_eff、τ_BM、螺栓强度是否真合理。

## 参考标准

- VDI 2230-1:2015（R8 螺纹剪切相关章节）
- ISO 898-2（螺母剪切强度）
- ISO 4032 / DIN 934（标准螺母尺寸）

> Cannot verify against original VDI / ISO standard —— C1 = 0.75、C3 = 0.58 与 τ ≈ 0.6·Rp0.2 是 ISO 公制螺纹常用近似；**未查证 VDI 2230-1:2015 / ISO 898-2 原文**。本章实现位于 `core/bolt/tapped_axial_joint.py:288-356` 与 `396-420`。
