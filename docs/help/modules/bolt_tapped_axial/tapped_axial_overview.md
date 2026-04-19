# 轴向受力螺纹连接方法总览（ISO 898-1 + VDI 2230 风格简化）

## 解决什么问题

专门校核**螺栓直接拧入螺纹对手件（无被夹件）、承受纯轴向拉载荷**的连接：发动机缸体螺栓、阀盖螺栓、法兰螺栓（入壳工况）、直接入铝/铸铁壳体的螺栓等。

**与 VDI 2230 夹紧连接（`bolt_page.py`）的根本区别**：没有被夹件，没有载荷系数 Φ_N，外载直接全部进螺栓——不能用夹紧连接的公式链简化到"残余夹紧力"概念。

## 一图总览

```
┌──────────────────────────────────────────────────────┐
│ Step 1: 截面派生（d, p → As, d2, d3）                 │
│         核心: ISO 898-1 公式，用户可填值做一致性校验    │
│         （偏差 >1% 抛错），计算始终用 d/p 派生值        │
├──────────────────────────────────────────────────────┤
│ Step 2: 装配计算                                      │
│         F_preload_max = α_A · F_preload_min            │
│         MA = F_preload · (k_thread + k_bearing) / 1000 │
│             + prevailing_torque                         │
│         σ_vm_assembly 校核 ≤ ν · Rp0.2                 │
├──────────────────────────────────────────────────────┤
│ Step 3: 服役 von Mises                                │
│         F_bolt_max = F_preload_max + FA_max            │
│         σ_ax_service_max = F_bolt_max / As             │
│         σ_vm_service_max = √(σ_ax² + 3·(k_τ·τ_asm)²)   │
│         校核 ≤ Rp0.2 / S_yield                         │
├──────────────────────────────────────────────────────┤
│ Step 4: 疲劳 Goodman                                   │
│         σ_a = (FA_max − FA_min) / (2·As)               │
│         σ_m = (F_preload_max + avg(FA))/As             │
│         σ_ASV_eff = σ_ASV[d] · surface · cycle         │
│         σ_a_allow = σ_ASV_eff · (1 − σ_m/(0.9·Rp0.2))  │
│         校核 σ_a ≤ σ_a_allow 且 Goodman > 0             │
├──────────────────────────────────────────────────────┤
│ Step 5: 螺纹脱扣（可选）                               │
│         A_SB = π·d3·m_eff·C1、A_SM = π·d·m_eff·C3       │
│         S_strip = min(F_strip_B, F_strip_M) / F_bolt_max│
│         留空 m_eff → overall_status = "incomplete"       │
└──────────────────────────────────────────────────────┘

综合：overall_status ∈ {pass, fail, incomplete}
```

## 核心流程

1. **派生截面**（`_derive_thread_geometry`）：用户给 d、p；工具按 ISO 724 派生 As/d2/d3。如用户手填，1% 偏差内接受，超出抛 `InputError`。
2. **装配**（Step 2 计算块）：F_preload_max = α_A·F_preload_min；配合摩擦系数、支承几何、牙型角算出装配扭矩 MA。同时做装配 von Mises 校核。
3. **服役 von Mises**：叠加 FA_max 到 F_preload_max；扭矩法工艺保留 50% 装配扭转进入服役（其他工艺假设扭转已消除）；与 Rp0.2 / S_yield 比较。
4. **疲劳 Goodman**：按 σ_ASV 表 + 寿命修正（0.08 幂律）+ 表面修正（0.65 for cut）得出许用幅基准，再按 Goodman 折减（σ_m/(0.9·Rp0.2)）得最终许用。
5. **螺纹脱扣（R8 风格）**：如填 m_eff，校核剪切承载；未填则记为 `not_checked` → overall = `incomplete`。

## 本模块实现的范围

- ISO 公制螺纹几何派生（DIN 13-1 / ISO 724）
- 装配扭矩 / 装配 von Mises（VDI 2230 风格）
- 服役 von Mises（含扭矩法残余 50% 扭转）
- 疲劳 Goodman（含表面、寿命修正）
- 脱扣 R8 风格（C1 = 0.75 / C3 = 0.58 近似）
- 四种拧紧工艺的 α_A 建议区间 warning

## 本模块**不**做的范围

- **横向力 / 剪切 / 弯矩**：纯轴向假设
- **多螺栓并联 / 群螺栓**：单螺栓模型
- **带被夹件的夹紧连接**：请用 `bolt_page.py`（VDI 2230）
- **FA 压向（负值）**：严格拒绝；压向需另做动载分析
- **Miner 累计疲劳 / 多段载荷谱**：单幅值评估
- **Haigh / Smith 图完整疲劳分析**：只用 Goodman 折线
- **材料温度效应**：室温 Rp0.2，需用户自行修正
- **支承面压溃（R6）**：支承面几何仅用于算 k_bearing，未校核 p_bearing ≤ p_allow——是已知不足
- **英制 UNC / UNF 螺纹**：公式按 ISO 724 公制

## 结果三态详解

`overall_status` 的三种可能值，分别对应不同用户操作：

### `pass` —— 全部通过（且脱扣已校核）

- 四项分项校核全 True，**且**脱扣校核已启用并通过
- `core/bolt/tapped_axial_joint.py:402-414`：脱扣未校核时一律返回 `incomplete`，不会因"其他三项通过"降级为 pass
- 建议：可作为设计基线进入审阅
- 注意：仍可能有 warning（如 α_A 超建议区间、利用系数偏高），请读 warning 面板

### `fail` —— 存在不通过

- 至少一项分项为 False
- 建议面板会给出方向性建议（加大规格、降预紧力、提强度等级、加深 m_eff 等）
- 不要降低安全系数阈值硬让它过——应检查物理参数是否合理

### `incomplete` —— 有校核未执行

- 常见原因：螺纹脱扣未填 m_eff
- 工具会追加 warning 提示
- **与 `pass` 区别**：UI 徽章是橙色"等待"，不是绿色"通过"
- 补齐输入后重新计算才能给明确结论

## 常见误用

- **把夹紧连接硬塞入本模块**：带被夹件 / 法兰的连接不适用——会少算被夹件对外载的吸收，严重高估螺栓应力，也无法校核密封所需残余夹紧力。
- **留空 m_eff 但以为通过**：不可以。工具强制 overall = `incomplete`，UI 显示橙色。
- **把压向载荷填负数**：抛 `InputError`；压向保守用 FA_min = 0 处理。
- **改 Rp0.2 让校核通过**：填错 Rp0.2 会影响所有校核方向；必须按 ISO 898-1 强度等级填正确值。
- **把低周 < 10³ 循环硬用 0.08 幂律**：低周需用 Manson-Coffin 专项分析，本工具不保证低周准确性。
- **不填 τ_BM 填 m_eff**：直接抛 `InputError`。两者必须一起填（启用 R8）。

## 报告输出

- **文本报告**（`_export_text_report`）：包含输入摘要、分项结论、关键数值、trace、warning、建议、标准引用
- **PDF 报告**（`_export_pdf_report`）：需要 reportlab 依赖；通过 `app.ui.report_pdf_tapped_axial.generate_tapped_axial_report` 生成

**重要**：任何输入变更、加载输入、清空参数后，导出按钮会**立即禁用**；必须重新点"开始计算"刷新缓存后才能导出。实现见 `core/bolt/tapped_axial_joint.py` 及 UI 的 `_invalidate_cache`。

## 参考标准

- VDI 2230-1:2015（螺栓连接预紧、装配应力、疲劳 σ_ASV、R8 脱扣相关章节）
- ISO 898-1:2013（螺栓强度等级、应力截面积、疲劳）
- ISO 898-2（螺母剪切强度）
- DIN 13-1 / ISO 724（ISO 公制螺纹尺寸）
- ISO 4032 / DIN 934（标准螺母尺寸）
- DIN 743（动载放大系数）

> Cannot verify against original VDI / ISO / DIN standard —— 本模块为上述标准的**工程简化子集**，采用公开教科书和标准摘录整理；**未查证原始标准正文**，精确公式、条款号、系数取值请以各自标准原文为准。不应将本工具输出作为标准合规性依据。
