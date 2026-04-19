# Stage 2 Round 2 Adversarial Review
Date: 2026-04-19
Reviewer: codex-rescue (adversarial mode, round 2)
Scope: 验证 Round 1 的 5 条 P0 + 2 条 P1 修复是否落地，并检查批量替换死角

## 1. Round 1 对账

- **P0-1 PARTIAL**：多数精确条号/表号已删，但 `docs/help/modules/bolt_vdi/vdi2230_overview.md:82` 仍写"VDI 2230 表 A1"，同文件 `:107` 仍有 `Cannot verify`；`docs/help/terms/bolt_bearing_pressure_allowable.md:44` 仍写"VDI 2230 表 B.5"，同文件 `:60` 仍有 `Cannot verify`。问题规模下降，但未清零。

- **P0-2 PASS**：`docs/help/terms/bolt_axial_load_fa.md:53-57` 已改成"本工具只接受非负 FA"；与 `core/bolt/calculator.py:260` 的 `_positive(..., allow_zero=True)` 一致。

- **P0-3 PASS**：`docs/help/terms/bolt_thermal_loss.md:11-16,20-24,51-54` 明写"取绝对值，仅计损失 / 同升同降且 ΔT=0 时返回 0"；与 `core/bolt/calculator.py:337-391` 一致。

- **P0-4 PARTIAL**：`docs/help/modules/bolt_vdi/_section_thread_strip.md:32-36`、`docs/help/terms/bolt_thread_engagement.md:31-33` 已改对，并与 `core/bolt/calculator.py:620-621,703`、`app/ui/pages/bolt_page.py:2613-2633` 一致；但 `docs/help/modules/bolt_vdi/vdi2230_overview.md:55,98` 仍写"incomplete"，同类误导还在用户面。

- **P0-5 PASS**：`docs/help/terms/bolt_embed_loss.md:20-45` 已明确"单一常数 × 界面数"的简化实现，并列出 `3.0/2.5/1.0 μm`；与 `core/bolt/calculator.py:178-214` 一致。

- **P1-1 PASS**：`app/ui/pages/bolt_page.py:579-585` 已补 `help_ref`，`tests/ui/test_bolt_help_wiring.py:45-46,79-85` 也已守护。

- **P1-4 PASS**：`app/ui/pages/bolt_page.py:519-526` 默认值已改 `"0"`，hint 明写"填 0 自动估算"。

## 2. Round 2 专属检查

- **死角 grep：FAIL**。`docs/help/` 仍非零。bolt 范围至少剩 `vdi2230_overview.md:82`、`bolt_bearing_pressure_allowable.md:44`；仓库范围还命中 `docs/help/modules/worm/din3975_geometry_overview.md:46`、`docs/help/modules/worm/_section_advanced.md:25`、`docs/help/GUIDELINES.md:67`。

- **新 P0：未确认新增**。基于 `/tmp/stage2-round2-review.diff` 与当前正文，未见证据表明 Round 2 批量替换新造了独立 P0；当前高风险更像旧 P0 漏改/漏扫。

- **lessons 写入：PARTIAL**。`.claude/lessons/help-content-lessons.md:60-65,85-89` 已补 P0-1/L4 检查清单与批量替换回归教训；但未见针对"R8 跳过时 `overall_pass` 仍可为真、不能写成 `incomplete`"的专门 lesson，P0-4 吸收不完整。

- **P1/P2 前瞻**：
  - `docs/help/terms/bolt_friction_thread.md:18-19` 仍漏 `prevailing_torque`，而 `core/bolt/calculator.py:446-449` 明确把它加进扭矩（**P1-2 未解**）。
  - `tests/ui/test_bolt_help_wiring.py:121-134` 仅断言章节页 `>=1` 个 `HelpButton`，未实现 lessons 要求的反向孤岛测试（**P1-3 未解**）。
  - `app/ui/pages/bolt_page.py:879` 仍写"未知时可先用 500~2000 N"，与已修正的默认 0 说法并存（**P2 级残留**）。

## 3. Stage 3 结论

**不可进**。P0-1 仍有 dead spot（`vdi2230_overview.md:82`, `bolt_bearing_pressure_allowable.md:44`），P0-4 在 overview 级别仍有错误说法。至少须先：

1. 清掉 `docs/help/modules/bolt_vdi/vdi2230_overview.md:55,82,98` 的旧条号与误导性 incomplete 说法；
2. 清掉 `docs/help/terms/bolt_bearing_pressure_allowable.md:44,60` 的精确表号+Cannot verify 共存；
3. 补写 P0-4 专门 lesson 并加反向守卫测试；

上述三项完成后可重做 Round 3 confirm，再决定是否开 Stage 3。
