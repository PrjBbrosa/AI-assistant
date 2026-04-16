# Task Plan: 本地桌面框架搭建（含螺栓模块）

## Goal
在保留 VDI 2230 螺栓计算核心的基础上，搭建本地 PySide6 桌面框架并预留多模块入口，支持后续打包为 `.exe`。

## Current Phase
Phase 20: Spline Workflow Alignment

## Phases
### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify initial constraints and requirements
- [x] Gather authoritative VDI 2230 logic references
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Define technical approach for formulas and workflow
- [x] Define project structure and input/output schema
- [x] Confirm assumptions and limitations
- **Status:** complete

### Phase 3: Implementation
- [x] Write calculation specification document
- [x] Implement bolt verification tool
- [x] Add sample cases and usage instructions
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Run example calculations end-to-end
- [x] Check intermediate values and constraints
- [x] Record test results in progress.md
- **Status:** complete

### Phase 5: Delivery
- [x] Review generated files and explain output
- [x] Summarize assumptions, risks, and next steps
- [x] Deliver to user
- **Status:** complete

### Phase 6: Desktop Framework Implementation
- [x] Create PySide6 desktop shell with module navigation
- [x] Apply Claude-style warm neutral theme
- [x] Integrate bolt calculation module into GUI
- [x] Add packaging prerequisites (`requirements.txt`, build script)
- [x] Verify CLI compatibility and run code checks
- **Status:** complete

### Phase 7: Bolt Form UX Upgrade
- [x] Replace JSON input editor with full structured form
- [x] Keep all bolt parameters visible in UI
- [x] Preserve sample loading / calculation / output save flow
- [x] Run regression checks (CLI + GUI smoke)
- **Status:** complete

### Phase 8: eAssistant Chapter-Style UI Alignment
- [x] Reorganize bolt UI by Chapter 14 sections (14.2~14.10)
- [x] Add per-parameter explanation text and tooltip
- [x] Add bolt clamping schematic diagram (FM/FA/FK)
- [x] Replace JSON result view with human-readable result panels
- [x] Add plain-language report export
- **Status:** complete

### Phase 9: Interference-Fit DIN 7190 Gap Closure
- [x] Review the current interference-fit module against DIN 7190 and the eAssistant handbook
- [x] Identify P0/P1 correctness issues, virtual parameters, and weak result semantics
- [x] Confirm scope exclusions for this round (`centrifugal force`, `stepped hub geometry`)
- [x] Write a superpowers execution checklist covering correctness, fit selection, assembly workflow, fretting, and traceability
- [x] Execute the implementation plan (Chunk 1-3, Task 1-7 all complete)
- **Status:** complete

### Phase 10: Bolt Page Deep Review & Remediation Planning
- [x] Review the bolt page UI/core/flowchart chain end-to-end
- [x] Reproduce page-state, parameter-reference, and result-semantics issues with fresh evidence
- [x] Write a formal review report under `docs/review/`
- [x] Write a superpowers execution plan under `docs/superpowers/plans/`
- [ ] Execute the remediation plan in an isolated workspace
- **Status:** in_progress

### Phase 11: Interference-Fit Chapter Deep Review
- [x] Audit the interference-fit chapter UI/core/tests/docs end-to-end
- [x] Cross-check formulas and result semantics against DIN 7190-style references and tool manuals
- [x] Re-run local examples and targeted edge cases
- [x] Write a formal review summary with findings, omissions, and comparison notes
- **Status:** complete

### Phase 12: Interference-Fit Fretting Step Planning
- [x] Define the scope of Step 5 fretting enhancement inside the interference-fit module
- [x] Compare lightweight vs engineering-grade implementation approaches and complexity
- [x] Write a design spec for the approved approach
- [x] Write an implementation plan after the spec is approved
- **Status:** complete

### Phase 13: Interference-Fit Fretting Step Implementation
- [x] Add fretting core helper with structured risk output
- [x] Integrate fretting into interference calculator without changing base verdict
- [x] Upgrade interference page Step 5 fields, report lines, and legacy compatibility
- [x] Update examples / README and run interference regression
- **Status:** complete

### Phase 14: Interference-Fit Closeout
- [x] Fix raw payload -> UI restore semantics for custom materials/profile/assembly/fretting
- [x] Add fit-selection boundary regression coverage
- [x] Add public benchmark disclaimer and sync historical design/review docs
- [x] Re-run repository verification before final closeout
- **Status:** complete

### Phase 15: Interference-Fit Hollow-Shaft Support
- [x] Write hollow-shaft design spec and implementation plan
- [x] Add RED tests for hollow-shaft core and UI behavior
- [x] Implement hollow-shaft geometry in calculator and page/report
- [x] Run verification and write closeout notes
- **Status:** complete

### Phase 16: Worm Load-Capacity Upgrade
- [x] Audit the worm page/core/tests and identify logic gaps
- [x] Write a worm-load-capacity design spec
- [x] Write a TDD implementation plan for the upgrade
- [x] Execute the plan in an isolated workspace
- [x] Verify worm core/UI regressions and sync docs
- **Status:** complete

### Phase 17: Spline Fit Deep Review & Remediation Planning
- [x] Audit the spline page/core/tests/docs end-to-end
- [x] Cross-check current geometry and strength assumptions against DIN 5480 / Niemann / DIN 6892 style references
- [x] Re-run local spline/UI tests and identify engineering-use blockers
- [x] Write a superpowers remediation plan under `docs/superpowers/plans/`
- **Status:** complete

### Phase 18: Spline Fit Engineering Hardening Execution
- [x] Execute Stage A immediate risk-removal tasks
- [x] Rebuild scenario A geometry inputs and trace toward DIN 5480-style semantics
- [x] Add benchmark-backed spline tests and rerun repository verification
- [x] Re-review whether the module may be used only for precheck or can graduate to engineering-check candidate
- [x] Merge the hardened spline worktree back to `main`
- **Status:** complete

### Phase 19: Alternating Axial Bolt Tool Planning
- [ ] Audit the current bolt / interference-fit architecture and identify reusable chapter patterns
- [ ] Clarify the intended engineering boundary for the new "preloaded + alternating axial load" scenario
- [ ] Propose tool rules, data model, chapter layout, and calculator/report integration plan
- [ ] Write or update the planning artifact after user confirms the direction
- [ ] Write the design spec and detailed implementation plan for the parallel section
- [ ] Define the multi-agent execution map and file ownership
- **Status:** in_progress

### Phase 20: Spline Workflow Alignment
- [x] Re-review current spline page state design and compare it against the current eAssistant-style workflow
- [x] Write a focused design spec for state closure, boundary clarity, message window, and live preview
- [x] Write a TDD implementation plan for the selected approach
- [ ] Execute the plan in the current workspace
- [ ] Re-run spline UI/core verification and sync handoff docs
- **Status:** in_progress

## Key Questions
1. 交付形态是 Web 还是本地桌面？（已选本地桌面）
2. 模块范围是只做螺栓还是全量？（已选“螺栓先做，其余占位”）

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 默认先做可复核的 CLI 工具 | 空仓库起步，CLI 更快验证计算正确性 |
| 先实现核心可工程落地项，再扩展 | VDI 2230 完整范围很大，分层实现更可控 |
| 首版文档与代码同时交付 | 保证公式与实现一一对应，便于审查 |
| 桌面 UI 采用 PySide6 | 满足 PyCharm 本地运行和 exe 打包需求 |
| 保留 `src/vdi2230_tool.py` 命令兼容 | 避免既有使用方式中断 |
| 过盈配合下一轮优先修正“安全系数/联合作用/结论语义” | 这些问题会直接影响通过/不通过结论，优先级高于新功能扩展 |
| 本轮暂不实现 `centrifugal force` 与 `stepped hub geometry` | 用户已明确排除，避免范围蔓延 |
| 过盈配合后续扩展按“正确性 → 配合选择 → 装配 → 重复载荷/报告追溯”推进 | 先修可信度，再补齐 eAssistant 中最有工程价值的能力 |
| 螺栓页后续修复优先级定为“展示语义/输入持久化/热参数校验/UI 回归测试” | 当前最大风险不在主公式，而在 UI 与实际 payload / checks 脱节 |
| 本轮新增一次“过盈配合章节深度审查”，先审查再决定是否进入修复 | 用户当前目标是确认 bug / 遗漏 / 逻辑风险，并对照 DIN 案例与同类工具结果 |
| fretting 下一步按“过盈配合第 5 步增强模块”规划，而不是独立通用页面 | 用户已明确希望 fretting 服务于过盈配合场景，并且首版先给风险等级与建议，不并入主 verdict |
| 空心轴支持本轮按“兼容当前实心轴基线”的增量方式接入 | 先补齐主模型几何边界，同时避免把 speed / temperature / stepped geometry 一起引入导致范围失控 |
| 蜗杆模块本轮按“先修逻辑漏洞，再做 Method-B 风格最小负载能力子集”推进 | 用户要求的不只是设计校核，而是要输出齿面应力、齿根应力和扭矩波动等工程结果 |
| 花键模块整改按“Stage A 立即去风险 → Stage B 标准化重构”推进 | 先消除错误承诺和 trace 缺口，再决定是否投入更重的 DIN 5480 / DIN 6892 重建成本 |
| 本轮“预紧后承受交变轴向力”按现有螺栓章节和过盈配合增强模式来规划 | 用户要求新工具的规则、架构、撰写方式尽量复用已验证的章节式组织和渐进增强方法 |
| 本轮花键 UI 收敛按“单页双场景继续保留，但状态闭环、导航语义和实时反馈先做齐”推进 | 先收敛当前页的可用性和心智模型，再决定是否值得拆成两个独立模块 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- 优先保证公式来源和单位一致性
- 在文档中明确“实现范围”和“未覆盖项”
- 螺栓页 2026-03-17 深度审查结果已落到 `docs/review/2026-03-17-bolt-page-deep-review.md`
- 螺栓页后续修复计划已落到 `docs/superpowers/plans/2026-03-17-bolt-page-review-followup.md`
- 本轮将补充一份过盈配合章节深度审查记录，重点覆盖 DIN 7190 公式链、UI 章节语义、案例对比与测试盲区
- 过盈配合章节 2026-03-18 深度审查结果已落到 `docs/review/2026-03-18-interference-fit-deep-review.md`
- fretting 第 5 步本轮先完成方案与计划文档，不直接进入实现
- fretting 第 5 步设计 spec 已写入 `docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md`
- fretting 第 5 步 implementation plan 已写入 `docs/superpowers/plans/2026-03-19-interference-fit-fretting-step.md`
- fretting 第 5 步实现已完成，核心 helper/UI/报告/样例与测试均已接入
- 过盈配合 closeout 已补齐：raw payload 回灌修复、fit band 边界测试、benchmark 差异说明与历史文档同步
- 空心轴支持 design spec 已写入 `docs/superpowers/specs/2026-03-19-interference-fit-hollow-shaft-design.md`
- 空心轴支持 implementation plan 已写入 `docs/superpowers/plans/2026-03-19-interference-fit-hollow-shaft.md`
- 空心轴支持已完成：主模型、UI、报告、repeated-load 适用性和测试均已接入
- 蜗杆模块 2026-03-22 审查结果显示：当前仅有 `DIN 3975` 几何与基础性能壳，`DIN 3996` 负载能力仍未实现
- 蜗杆模块本轮 design spec 已写入 `docs/superpowers/specs/2026-03-22-worm-load-capacity-design.md`
- 蜗杆模块本轮 implementation plan 已写入 `docs/superpowers/plans/2026-03-22-worm-load-capacity.md`
- 蜗杆模块本轮已完成：功率链路修正、最小 Method B 子集、UI 新参数、样例与回归测试同步
- 花键模块 2026-03-22 深度审查结论：当前场景 A 仅能作为“齿面平均承压简化预校核”，不能直接作为正式工程校核
- 花键模块后续整改计划已写入 `docs/superpowers/plans/2026-03-22-spline-fit-engineering-hardening.md`
- 花键模块本轮已完成：语义降级、trace/warning 修复、参考直径几何输入、公开 benchmark 与回归验证，并已合回 `main`
- 本轮新任务聚焦“预紧后承受交变轴向力”的螺栓计算工具规划，目标是沿用现有螺栓章节式 UI、flowchart、报告和过盈配合的增强型规则组织方式
- 新 section 的 design spec 已写入 `docs/superpowers/specs/2026-03-25-tapped-axial-threaded-joint-design.md`
- 新 section 的 implementation plan 已写入 `docs/superpowers/plans/2026-03-25-tapped-axial-threaded-joint.md`
- 花键模块本轮新 design spec 已写入 `docs/superpowers/specs/2026-03-29-spline-workflow-alignment-design.md`
- 花键模块本轮新 implementation plan 已写入 `docs/superpowers/plans/2026-03-29-spline-workflow-alignment.md`
