# Task Plan: 本地桌面框架搭建（含螺栓模块）

## Goal
在保留 VDI 2230 螺栓计算核心的基础上，搭建本地 PySide6 桌面框架并预留多模块入口，支持后续打包为 `.exe`。

## Current Phase
Phase 8

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

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- 优先保证公式来源和单位一致性
- 在文档中明确“实现范围”和“未覆盖项”
