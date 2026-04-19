# Stage 2 Adversarial Review (bolt_vdi / VDI 2230)
Date: 2026-04-19
Reviewer: codex-rescue (adversarial mode)
Scope: bolt 模块帮助内容、page 集成、Stage 1 lessons 吸收度

## Stage 1 Lessons Audit（7 条对账）

**L1. Docs must not drift from calculator behavior**
Verdict: **VIOLATED**
- `docs/help/terms/bolt_axial_load_fa.md:53` 称"`FA 填负值代表压力`"，但 `core/bolt/calculator.py:260` 用 `_positive(..., allow_zero=True)` 拒绝任何负值的 `FA_max`。
- `docs/help/terms/bolt_thermal_loss.md:21-37` 描述了基于 `T_bolt/T_parts` 的有向热损失模型，但代码 `core/bolt/calculator.py:337-393` 实际使用 `abs(temp_bolt - temp_parts)`，两者温差为零时代码输出 0，即使 α 系数不同也是如此。
- `_section_thread_strip.md:32-33` 等多处声称空 `m_eff` 导致结果"不完整"，但代码只是跳过 `thread_strip_ok`，`app/ui/pages/bolt_page.py:2616-2633` 依然呈现正常的 pass/fail。

**L2. 公式必须带单位** — ABSORBED
**L3. 模块族前缀** — ABSORBED
**L4. 无法核对的标准引用必须写 Cannot verify，且不得精确到条款** — **VIOLATED**
- Stage 2 在 `_section_elements.md:48-50`、`_section_introduction.md:66-68`、`_section_operating.md:82-84`、`bolt_tightening_factor_alpha_a.md:69-71`、`bolt_yield_safety.md:74-76` 仍然把精确的 `§` 条款号与 `Cannot verify against original VDI standard` 并排写出。

**L5. 符号先解释再压缩公式** — ABSORBED
**L6. 字数上限按内容类型适度放宽** — ABSORBED
**L7. Adversarial review 由独立角色** — PARTIAL（本次即首次执行）

## New P0 Issues

**P0-1**: 精确 VDI 条款号 + Cannot verify 并排（5 处）
- `_section_elements.md:48`、`_section_introduction.md:66-68`、`_section_operating.md:82-84`、`bolt_tightening_factor_alpha_a.md:69-71`、`bolt_yield_safety.md:74-76`

**P0-2**: `bolt_axial_load_fa.md:53` 负值说明与 calculator `_positive` 检查矛盾

**P0-3**: `bolt_thermal_loss.md` 描述有向热损失模型，代码 `abs(delta_T)` 单向取损失

**P0-4**: `_section_thread_strip.md:32` 说空 `m_eff` 导致结果"incomplete"，但 UI/calculator 仍给 pass/fail

**P0-5**: `bolt_embed_loss.md` 展示逐接触面差异化嵌入量（10.5 μm 算例），但 calculator 用单一常数 3.0/2.5/1.0 μm

## P1 Issues

**P1-1**: `app/ui/pages/bolt_page.py:579` `loads.seal_force_required` 未 wiring `bolt_seal_clamp_force`

**P1-2**: `bolt_friction_thread.md` MA 公式遗漏 `prevailing_torque` 项

**P1-3**: `test_bolt_help_wiring.py:120` 断言 >=1 HelpButton 过宽

**P1-4**: `bolt_page.py:579` `loads.embed_loss` 默认 `"1000"` 而非 `"0"`，新手不知道填 0 才触发自动估算

## 术语命名前瞻（Stage 3 prep）

**Stage 3 可直接复用的 14 个**：bolt_axial_load_fa / bolt_friction_bearing / bolt_friction_thread / bolt_grade / bolt_preload_fm / bolt_seal_clamp_force / bolt_stress_area / bolt_thread_engagement / bolt_thread_nominal / bolt_thread_pitch / bolt_thread_strip_tau / bolt_tightening_factor_alpha_a / bolt_tightening_method / bolt_yield_strength

**VDI 2230 专属的 7 个**：bolt_bearing_pressure_allowable / bolt_compliance / bolt_embed_loss / bolt_load_intro_factor / bolt_thermal_loss / bolt_utilization_nu / bolt_yield_safety

命名规范错误：无。

## 公式正确性抽查

- `As = π/4·(d − 0.9382·p)²`：正确
- MA 扭矩公式：文档遗漏代码 `prevailing_torque` 项（P1-2）
- R8 `C1=0.75, C3=0.58`：标注为近似 + Cannot verify，一致
- Fth 方向：文档有向 vs 代码 `abs()`（P0-3）

## 结论

Stage 2 在教学质量（单位标注、前缀命名、符号先行解释）明显优于 Stage 1 初版；但 L1 与 L4 两条 Stage 1 已要求纠正的教训在 Stage 2 **再次违反**（精确条款号 + doc/code 行为不一致）。最低修复集：P0-1 到 P0-5 全部修复后方可启动 Stage 3。
