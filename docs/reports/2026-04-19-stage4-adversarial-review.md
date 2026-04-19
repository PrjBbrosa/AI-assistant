# Stage 4 Adversarial Review (interference DIN 7190 过盈配合)
Date: 2026-04-19
Reviewer: Codex (adversarial mode)
Scope: Stage 4 interference 帮助内容、page wiring、guard tests

## P0 缺陷（阻塞合并）

**P0-1 | [docs/help/terms/interference_slip_safety.md:33-35; core/interference/calculator.py:301-312]**
问题描述：`δ_required / p_required` 回算公式与 calculator 不一致，会把张口缝需求错误地乘上 `S_slip,min`，且漏掉粗糙度压平量回加。
证据：文档写 `p_required = S_slip,min · max(..., p_gap)`；代码实际是 `p_required = max(p_req_torque, p_req_axial, p_req_combined, p_gap)`，随后 `delta_required_um = delta_required_eff_um + subsidence_um`。
建议修复：把回算拆成"防滑支线乘 `S_slip,min`、张口缝支线不乘"，并补写 `δ_required = 2·c_total·p_required·1000 + s`（含粗糙度压平量 `s`）。

**P0-2 | [docs/help/terms/interference_assembly_method.md:38-45; docs/help/modules/interference/_section_assembly.md:27-31; docs/help/modules/interference/din7190_overview.md:72-74; core/interference/assembly.py:100-124]**
问题描述：热装公式写错/写漏：`diameter_rule` 单位表达会把装配间隙读小 1000 倍，且所需轮毂温度公式漏掉轴预冷修正项。
证据：三处文档写 `clearance = 0.001 · d [um, d: mm]`，且 `T_hub_required = T_amb + required_expansion_um / hub_growth_per_c`；代码实际是 `clearance_um = shaft_d_mm`，并叠加 `(alpha_shaft / alpha_hub) * (shaft_temperature_c - room_temperature_c)`。
建议修复：三处帮助文统一改成与 `assembly.py` 完全一致的实现公式，并在公式行明确 `alpha_*: 10^-6/°C, d: mm, clearance/delta: um`。

**P0-3 | [docs/help/modules/interference/_section_fretting.md:14-25; docs/help/terms/interference_fretting_risk.md:38-69; core/interference/fretting.py:28,148-161,218-229]**
问题描述：Fretting 评分规则与实现漂移：文档写成单个 `slip_reserve_bonus`，代码实际对 `torque_sf` 和 `combined_sf` 各加一次分，最大分也不是文档暗示的 11。
证据：文档写 `slip_reserve_bonus ∈ {0..3}`；代码先算 `torque_score`，再算 `combined_score`，并定义 `_MAX_SCORE = 14.0`。
建议修复：把帮助文改成"双储备项"版本，明确 `torque_reserve_bonus + combined_reserve_bonus`，并把最大分/分级口径写成与代码一致。

**P0-4 | [docs/help/modules/interference/_section_friction.md:24; docs/help/modules/interference/_section_checks.md:33; docs/help/terms/interference_stress_safety.md:21-26; docs/help/terms/interference_yield_strength.md:23-24; docs/help/GUIDELINES.md:57-58]**
问题描述：L6 仍未吸收：核心公式族仍有缺单位或单位不完整的公式行。
证据：`_section_friction.md:24` 只写 `[p: MPa]`；`_section_checks.md:33` 写成 `[T,d,L: N·m/mm]`；`interference_stress_safety.md:21-26` 的 `K_hub/K_shaft/VM_*` 无单位标注；`interference_yield_strength.md:23-24` 的 `S_shaft/S_hub` 未标 `[无量纲]`。
建议修复：按 GUIDELINES §5 把输入/输出单位补齐到每一条公式行，尤其是接触压、Lamé/VM 系数、安全系数与回算公式。

---

## P1 缺陷（合并前应修）

**P1-1 | [docs/help/modules/interference/_section_checks.md:9; core/interference/calculator.py:325-326]**
问题描述：章节摘要把 `S_slip,min` 说成"直接进…张口缝校核"，会误导读者。
证据：文档写"直接进扭矩、轴向力、联合作用、张口缝校核"；代码 `gaping_ok = p_min >= p_gap`，`pressure_ok = p_min >= p_required`，张口缝判据本身不乘 `S_slip,min`。
建议修复：改成"`S_slip,min` 进入防滑支线与需求过盈回算；张口缝单独比较 `p_min` 与 `p_gap`"。

**P1-2 | [docs/help/terms/interference_fretting_risk.md:28,95-97; docs/help/modules/interference/_section_fretting.md:37; core/interference/fretting.py:101-103]**
问题描述：Fretting 适用条件把"有弯矩"写成"显著/大弯矩"，比代码宽。
证据：文档写"大弯矩/显著弯矩"；代码只要 `has_bending` 为真就返回 `not_applicable`。
建议修复：把文案收紧为"存在任何非零弯矩时，本简化 Step 5 不适用"。

**P1-3 | [docs/help/terms/interference_fretting_risk.md:20-22; app/ui/pages/interference_fit_page.py:1759-1766,2048-2050]**
问题描述：文档说 `fretting.mode="off"` 时报告不包含 fretting 段，但页面导出的 report 仍固定输出 Step 5 段。
证据：术语文写"report 不包含 fretting 段"；页面导出固定写入 `Step 5 Fretting 风险评估:`，并追加 `enabled=False` 等 trace。
建议修复：二选一，要么隐藏 off 状态的 Step 5 报告段，要么把帮助文改成"off 时不做风险判定，但报告仍保留 trace"。

**P1-4 | [docs/help/modules/interference/_section_assembly.md:54-57,63-67; app/ui/pages/interference_fit_page.py:1610,1734-1740]**
问题描述：`shrink_fit` 的输出描述自相矛盾，且与 UI 不完全一致。
证据：同一节先写 `manual_only / shrink_fit：通用压入力（用 μ_Assy）`，后面的表又写 `shrink_fit` "替换为 T_hub 需求"；页面实际同时显示压入力和 `required_hub_temperature` trace。
建议修复：把 shrink-fit 输出统一描述为"保留通用压入力显示，并额外给出所需轮毂温度"。

---

## P2 建议

**P2-1 | [tests/ui/test_interference_help_wiring.py:154-166]**
渲染守卫只断言"每章至少 1 个 HelpButton"，抓不到字段级按钮缺失。
建议：增加"每个带 `help_ref` 的 FieldSpec 都能在对应 chapter widget 渲染出按钮"的 DOM 级断言。

**P2-2 | [docs/help/modules/interference/_section_checks.md:20; docs/help/terms/interference_application_factor_ka.md:14-25]**
`checks` 章节仍用"DIN 3990 风格"描述 KA，容易把已分开的 gear/interference 语义重新混在一起。
建议：把章节文案改成"过盈配合场景下的工况放大系数"，避免再借 gear 语境做类比。

---

## 专项审查

### A. Lessons 违反（L1/L4/L5/L6/命名前缀）
- L1 违反：至少 3 处实锤（interference_slip_safety.md:33-35、热装公式三处文档、fretting 评分规则两处文档）
- L4 通过：grep 结果 `§ = 0`、`表 [A-Z].[0-9] = 0`、`附录 [A-Z] = 0`
- L5 基本吸收：`interference_delta_min.md:3-9`、`interference_delta_max.md:3-8`、`interference_stress_safety.md:3-14`、`interference_slip_safety.md:3-15` 均先中文解释符号再给公式
- L6 违反：见 P0-4
- 命名前缀通过：24/24 新术语文件均为 `docs/help/terms/interference_*.md`；`test_interference_help_wiring.py:129-151` 还加了反向孤岛守卫

### B. 过盈工程正确性
- Lamé/几何因子主干公式与 `calculator.py:200-205,232-246` 主体一致；问题主要在单位标注不全
- δ 方向：都明确写成直径方向，且与 `fit_selection.py:74-75` 一致
- 温度装配：帮助文存在 P0-2 漂移；但 `din7190_overview.md:91` 已诚实写出"装配温差对服役过盈的影响未实现"
- 典型值 sanity：H7/p6-s6-u6 子集与文档数值量级基本一致，未见离谱的 δ/d 量级错误
- fretting：适用条件大框架与 `fretting.py:95-103` 基本一致，但评分组成和弯矩适用条件描述已漂移

### C. 内容可懂性（抽查3篇）
- 几何术语 `interference_hub_outer_diameter.md`：先给一句话、再给 D/d 表，读者进入成本低；但第 10 行的 `K_hub` 公式缺 `[无量纲]`
- 材料术语 `interference_yield_strength.md`：材料表和热处理段实用；但 `23-24` 安全系数公式没标 `[无量纲]`
- 安全系数术语 `interference_slip_safety.md`：`3-15` 解释清楚，但 `33-35` 公式与代码不一致（P0-1）

### D. 命名冲突前瞻
- `interference_application_factor_ka` vs `gear_application_factor_ka`：已明确声明两者不同；当前命名独立是对的
- `interference_stress_safety` vs `bolt_yield_safety`：两者语义不同，不建议合并
- 过度前缀化：本批 24 篇无"本可复用却被硬加前缀"的反例

---

## 总体判断

- 状态: **NEEDS ROUND 2**
- P0 / P1 / P2 数量: **4 / 4 / 2**
- Round 2 必须修复：
  1. `interference_slip_safety.md` 回算公式（张口缝支线不乘 `S_slip,min` + 补粗糙度压平量）
  2. 热装公式三处文档（`assembly_method.md` + `_section_assembly.md` + `din7190_overview.md`）与 `assembly.py` 对齐
  3. Fretting 评分文档改成双储备项版本，`_MAX_SCORE = 14`
  4. 核心公式族补全单位（接触压、Lamé/VM 系数、安全系数行）
