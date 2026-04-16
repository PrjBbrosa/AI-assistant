# 花键连接校核修复工作总结

- 日期：2026-04-16
- 分支：`fix/spline-blocking`（已合并到 main，已 push origin）
- Plan：`docs/plans/2026-04-16-spline-fit-fixes.md`
- 执行回顾：`docs/reports/2026-04-16-spline-fix-followup.md`
- 最终测试：**396 passed / 0 failed**（main 前为 391 passed + 3 spline UI failed）
- 合并方式：fast-forward，12 个 commit 线性历史

## 工作范围

按 plan 8 步执行 + 3 个 main 既有 UI 测试失败 + code review 后追加 3 次关键修复。涉及 11 个文件，+298 / −45 行。

## 核心成果

### 1. Calculator / 几何层（core/）
- **近似公式重写**：旧版 `d_a1=m(z+1)` 等违反 DIN 5480 拓扑（`d_a1 > d_B`）；先改为 catalog m=1.25 反推的 `h_w=0.9m`，但 review 发现对 m≥1.75 非保守（m=2/z=8 实测 h_w/m=0.525，近似高估 71% → 假 PASS 风险）。**最终采用 h_w=0.5m 保守下限**（catalog 最苛刻条目 W 25x2.5x8），对全部 33 条 catalog 记录断言 `h_w_approx ≤ h_w_ref`。
- **k_alpha 默认值 1.0→1.3**：与 UI FieldSpec.default 对齐，注释补 K_A 预乘来源。
- **扭矩容量比 `torque_capacity_sf`**：新增字段 = T_cap/T_design（数学上等价于 flank_safety）。
- **DIN 5480 catalog docstring 纠正**：原来"±10% 波动"实际范围为 0.5m~1.08m。

### 2. UI 层（app/）
- **材料下拉联动屈服强度**：45钢 355 / 40Cr 785 / 42CrMo 930 MPa（GB/T 699 / 3077 下限）。
- **mode 权威性守护**：`_on_material_changed` 按当前 mode 决定锁定状态，联合解锁 SubCard、仅花键保留 AutoCalcCard。
- **payload mode 过滤**：仅花键模式下不向 calculator 传 smooth_* 段。
- **侧栏改名**：`花键过盈配合` → `花键连接校核`，与模块头部一致。
- **live feedback 消息同步**：`_display_result` 把 messages 同步到 `message_box`。

### 3. 报告/文档
- PDF 报告新增"扭矩容量比 T_cap/T_d (与 S 等价)"行，避免重复展示两个等价"安全系数"。
- CLAUDE.md 花键模块限制段补全近似公式、k_alpha、材料联动、payload 过滤 4 条。
- follow-up 报告完整记录 Round 1 + Round 2 决策偏离。

## Commit 历史（main → HEAD 时序）

| # | 标题 | 类型 |
|---|------|------|
| 1 | fix(spline-geom): correct DIN 5480 approximation to satisfy tip/root ordering | Plan Step 1（Round 1） |
| 2 | feat(spline-ui): auto-fill yield strength when choosing preset material | Plan Step 2 |
| 3 | fix(spline-core): align k_alpha default with UI and clarify docstring | Plan Step 3 |
| 4 | feat(spline-core): expose torque_capacity_sf in scenario A result | Plan Step 4 |
| 5 | docs(spline): normalize din5480_table docstring | Plan Step 5 |
| 6 | feat(spline-ui): filter smooth_* sections from payload | Plan Step 6 |
| 7 | fix(spline-ui): rename sidebar entry to 花键连接校核 and mirror messages | 附加 UI 修复 |
| 8 | docs(spline): update CLAUDE.md limits and add follow-up report | Plan Step 8 |
| 9 | fix(spline-geom): use conservative h_w=0.5m lower bound | **Review C1** |
| 10 | fix(spline-ui): material autofill respects mode as authoritative | **Review I1** |
| 11 | refactor(spline-ui): clarify S_T ≡ flank_safety in display and PDF | **Review I2/I3** |
| 12 | docs(spline): append Round 2 review fixes to follow-up report | 报告追加 |

## 与 Plan 的偏离决策

1. **近似系数**：Plan 建议 `h_w=0.4m`，Round 1 误采 `0.9m`（单点 catalog 偏差），Round 2 最终定在 `0.5m` 保守下限——偏离原因是 Plan 的验收测试 `test_approximation_aligns_with_catalog_w25x125` 只挑 m=1.25 有利样本。
2. **Step 6.1** standard→custom 恢复 FieldSpec default：**不做**，保留用户输入值更符合 UX 直觉。
3. **Step 6.3** 催生的 `test_din5480_table.py`：基线已存在，无需新增。
4. **Step 6.2** 补 hint 文案：跳过，低优先级。

## Review 处理

启动 Codex rescue review 失败（companion 脚本 bug），改用 `superpowers:code-reviewer` agent 做独立审查。结论："需改动后再合并"。核心 3 项已全部修复：

- **C1（Critical）**：近似公式在 m≥1.75 非保守 → 改保守下限 + 全 catalog 断言
- **I1（Important）**：material autofill 无条件解锁破坏 mode 权威 → 按 mode 决定 + 新测试
- **I2/I3（Important）**：S_T/S_flank 重复展示误导 + 近似告警缺失 → UI/PDF 措辞修正 + messages 加非保守提示

## 关键数据变化（examples/spline_case_02.json）

| 指标 | main 原值 | Round 1 | Round 2（最终） |
|------|-----------|---------|-----------------|
| h_w (mm) | 2.0 | 1.8 | 1.0 |
| d_m (mm) | 40.0 | 37.8 | 38.0 |
| p_flank (MPa) | 26.04 | 30.62 | 54.82 |
| flank_safety | 3.84 | 3.27 | 1.82 |
| flank_ok | True | True | True |

即使采用保守下限，示例案例仍通过 1.3 安全阈值，无需调整载荷。

## 方法论反思

1. **Plan 里"验收测试不能只挑有利样本"**：这次直接把 test_approximation_aligns_with_catalog_w25x125 作为判定依据，导致公式 Round 1 在非目标样本下失真。未来验收测试应覆盖参数全域。
2. **独立 code review 价值高**：自我实现 + 自我验证盲点明显。独立 reviewer 抓到的 C1 是真正可能造成工程事故的问题，仅靠 "396 绿" 无法发现。
3. **TDD 先写测试 ≠ 测试质量好**：本次 TDD 流程严格（先失败后通过），但测试本身的样本选择有盲区；"测试通过"是必要条件，不是充分条件。
