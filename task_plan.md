# Task Plan: 本地桌面框架搭建（含螺栓模块）

## Goal
在保留 VDI 2230 螺栓计算核心的基础上，搭建本地 PySide6 桌面框架并预留多模块入口，支持后续打包为 `.exe`。

## Current Phase
Phase 12 (Phase 10 in_progress, Phase 11 complete, fretting planning added)

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
- [ ] Define the scope of Step 5 fretting enhancement inside the interference-fit module
- [ ] Compare lightweight vs engineering-grade implementation approaches and complexity
- [ ] Write a design spec for the approved approach
- [ ] Write an implementation plan after the spec is approved
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
