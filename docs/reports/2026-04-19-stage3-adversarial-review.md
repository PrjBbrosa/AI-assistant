# Stage 3 Adversarial Review (bolt_tapped_axial help system)
Date: 2026-04-19
Reviewer: Codex (adversarial mode)
Scope: Stage 3 bolt_tapped_axial 帮助内容、page wiring、guard tests

## 1. 审查概览

- 已读完全部指定文件：`/tmp/stage3-review.diff`、`.claude/lessons/help-content-lessons.md`、`docs/help/GUIDELINES.md`、`core/bolt/tapped_axial_joint.py`、`docs/reports/2026-04-19-stage2-adversarial-review.md`，以及 6 个 section、overview、5 个新 term、page、test。
- 结论计数：**P0 = 4**，**P1 = 3**，**P2 = 1**。
- 已完成专项检查：
  - L1 doc-vs-calc：逐条核对了 section 中所有"本工具实现 / overall_status / skip"相关表述。
  - L4 精确标准引用 grep：`§[0-9]` / `表 [A-Z].[0-9]` / `附录 [A-Z]` 在本批新 `.md` 中 **0 命中**。
  - 模块前缀：5 个新 term 文件均为 `bolt_tapped_axial_*.md`，命名本身 **OK**。

## 2. P0 问题列表

**P0-1**

- **问题**：`Goodman = 0` 时的结论写错了。
- **位置**：`docs/help/modules/bolt_tapped_axial/_section_fatigue_output.md:58-60`
- **证据**：文案原文 `σ_a_allow = 0 → 疲劳必 FAIL（除非 σ_a 也恰为 0）`；代码 `core/bolt/tapped_axial_joint.py:283-286` 明确 `fatigue_ok = (goodman_factor > 0.0) and (sigma_a <= sigma_a_allow)`；只要 `goodman_factor == 0`，即使 `σ_a == 0` 也返回 `False`。Lessons L1 明确要求文档不能与 calculator 实际行为脱节。
- **建议**：删掉"除非 σ_a 也恰为 0"，改成"`goodman_factor <= 0` 时疲劳一律 FAIL"。

**P0-2**

- **问题**：overview 有两处核心行为与实现不符。
- **位置**：`docs/help/modules/bolt_tapped_axial/tapped_axial_overview.md:14`、`:79-80`
- **证据**：原文 1"允许用户覆盖（偏差 1% 抛错）"，但 `core/bolt/tapped_axial_joint.py:104-129` 只校验一致性，计算始终使用 d/p 派生值，不存在"覆盖后参与计算"；原文 2"四项分项校核全 True（或脱扣未启用但其他三项全 True）"，但 `tapped_axial_joint.py:402-414` 规定只要有 `None/not_checked`，`overall_status` 就是 `incomplete`，不是 `pass`。
- **建议**：把"允许覆盖"改成"允许填值做一致性校验，但计算仍使用 d/p 派生值"；把"脱扣未启用也可 pass"改成"脱扣未校核时整体为 incomplete"。

**P0-3**

- **问题**：`prevailing_torque` 的输入约束写反了。
- **位置**：`docs/help/terms/bolt_tapped_axial_prevailing_torque.md:64-66`
- **证据**：原文"不允许负值（_positive 系统强制）"；但 `core/bolt/tapped_axial_joint.py:68-71` 的 `_float_or_none` 只做数值解析，`204-205` 直接接收结果并在空值时置 0，**没有任何 `_positive` 或非负校验**。负值输入会被默默接受并降低 `MA`。
- **建议**：要么文档改成"当前实现允许负值，但不建议"；要么代码补非负校验后再同步文档。

**P0-4**

- **问题**：多处公式块不满足 L6 单位标注硬规则。
- **位置**：`_section_assembly_preload.md:10,18-20,77-78`；`_section_axial_load.md:10-11,34,42-43`；`_section_thread_strip.md:19-25`；`_section_fatigue_output.md:12-24,37-38`；`tapped_axial_overview.md:13-38`；以及 5 个新 term 内的多个公式块。
- **证据**：典型原文如 `F_preload_max = α_A · F_preload_min [N]`、`σ_allow_service = Rp0.2 / yield_safety_operating [MPa]`，overview ASCII 流程图中全部公式无 `[x: unit → y: unit]`。`docs/help/GUIDELINES.md:56-58` 明写：每一个公式都必须显式标注输入/输出单位，缺单位默认判 P0。
- **建议**：按 `[F_preload_min: N, α_A: - → F_preload_max: N]` 格式逐条补全；overview 流程图公式也不能例外。

## 3. P1 问题列表

**P1-1**

- **问题**：多处公式块先上公式、后解释符号，违反 L5。
- **位置**：`_section_assembly_preload.md:17-21`（`k_thread / k_bearing / MA` 在 23-27 行才解释）；`_section_thread_strip.md:18-26`（`A_SB / A_SM / F_strip_B / S_strip` 先出现）；`bolt_tapped_axial_axial_load_range.md:22-25`（`σ_m / σ_a` 在 27-32 行才解释）；`_section_fatigue_output.md:11-25`（`σ_ASV_base / cycle_factor / goodman_raw` 无前置中文释义）。
- **证据**：`.claude/lessons/help-content-lessons.md:36-40` 要求"符号要先解释再写公式"。
- **建议**：每个公式块前先加"其中：…"中文释义表，再放压缩公式。

**P1-2**

- **问题**：fatigue/output 相关文案与实际默认值/行为漂移。
- **位置**：`_section_fatigue_output.md:41-43`；`app/ui/pages/bolt_tapped_axial_page.py:168-179`；`_section_fatigue_output.md:47-52`。
- **证据**：原文写"默认 1.1"，但 page 默认是 `default="1.15"`（diff line 155-156）；字段 hint 写"高周默认 2×10⁶ 保守"，但同行默认值是 `default="1000000.0"`（diff line 142-143）；原文写 `report_mode` "只影响文本 / PDF 导出的详细程度"，但当前 `_build_report_lines` 与 `generate_tapped_axial_report` 都未按 `options.report_mode` 分支。
- **建议**：统一默认值文案；若保留 `report_mode`，就真正实现 `compact/full` 分支，否则删掉该承诺。

**P1-3**

- **问题**：Cannot-verify 覆盖不是"段落级"，仍有裸标准提及。
- **位置**：`_section_fastener_material.md:45-46`；`bolt_tapped_axial_prevailing_torque.md:13`；`tapped_axial_overview.md:54-59`。
- **证据**：这些段落直接写 `ISO 898-1`、`ISO 724 / DIN 13-1`、`ISO 7040/DIN 985`、`VDI 2230 风格`，但段落本身没有 `Cannot verify...`。`docs/help/GUIDELINES.md:70-73` 要求场景 B 的标准引用在对应段落写明 `Cannot verify against original ...`。
- **建议**：把 disclaimer 下沉到具体引用段，而不是只放文件尾部统一声明。

## 4. P2 问题列表

**P2-1**

- **问题**：HelpButton 渲染守护测试仍然偏宽。
- **位置**：`tests/ui/test_bolt_tapped_axial_help_wiring.py:150-155`
- **证据**：原文 `assert len(help_buttons) >= 1`；`app/ui/pages/bolt_tapped_axial_page.py:268-279` 有章节级 `HelpButton`，`:319-332` 还有字段级 `HelpButton`；若字段级按钮回归丢失，只剩章节按钮，此测试仍会通过。Stage 2 review 已记录同类问题：`docs/reports/2026-04-19-stage2-adversarial-review.md:42` 写明 `assert >=1 HelpButton 过宽`。
- **建议**：按 chapter 预期精确断言按钮数量，或逐个 `FieldSpec.help_ref` 验证其标签区域确实渲染了按钮。

## 5. Lessons 违反检查摘要

- **L1 文档不能与 calculator 实际行为脱节**：**VIOLATION** — 证据：P0-1、P0-2、P0-3。
- **L2 公式必须显式带单位**：**VIOLATION** — 证据：P0-4；`docs/help/GUIDELINES.md:56-58`。
- **L3 术语命名默认加模块族前缀**：**OK** — 5 个新 term 均为 `bolt_tapped_axial_*.md`。
- **L4 无法核对标准时必须显式声明**：**VIOLATION** — 精确条款 grep 虽为 0 命中，但 P1-3 显示 paragraph-level disclaimer 仍未完全落实。
- **L5 符号要先解释再写公式**：**VIOLATION** — 证据：P1-1；`.claude/lessons/help-content-lessons.md:36-40`。
- **L6 单篇字数上限要跟内容类型走**：**OK** — 本批 section/term 长度均在可接受范围。
- **L7 adversarial review 必须用不同人格（或不同子代理）**：**OK** — 本次为独立 adversarial review。

## 6. 总体判断

**不能直接 merge，需 Round 2。** 当前阻塞项不是文风，而是几处会直接误导用户理解工具行为的 P0 文档-实现漂移，再叠加大量 L6 公式单位硬违规。至少应先修完 P0-1 到 P0-4，再回头清掉 L5/L4 覆盖和 tests 守护宽度问题。
