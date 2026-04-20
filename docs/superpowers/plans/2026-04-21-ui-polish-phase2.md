# UI 统一性加固 Phase 2 — 实施 Plan

**Spec**：`docs/superpowers/specs/2026-04-21-ui-polish-phase2-design.md`
**PR**：接续 #6（theme-widget-polish），增补 commits
**前置条件**：本地 branch `theme-widget-polish`（HEAD `861424f`），tests 707 全过。

## 波次图

```
Wave 0  ── 主会话：写 spec + plan + 任务拆分（本步骤）
           │
Wave 1  ── 并行派 3 个 ui-engineer agent ─────────────────────┐
           │                                                   │
           ├─ Agent A：theme.py 状态与对比度（#4 + #5）        │
           ├─ Agent B：spline_fit_page objectName（#2）        │ 全部完成 → Wave 2
           └─ Agent C：worm 结果滚动 + 图表主题（#6 + #7）     │
           │                                                   │
Wave 2  ── 主会话：CLAUDE.md 追加原生对话框约定（#3）
           │
Wave 3  ── ui-engineer Agent D：BoltPage 视觉对齐（#1 简化版）
           │
Wave 4  ── Codex 二轮 review → 若 blocker/major 则回到对应 wave 修复 → 直到 OK
           │
Wave 5  ── 主会话：写结题报告 + commit + push
```

## Wave 1 agent 任务模板

### Agent A（ui-engineer）— theme.py 状态与对比度

**Prompt**：
> 你拿到 `app/ui/theme.py`。按 `docs/superpowers/specs/2026-04-21-ui-polish-phase2-design.md` §"#4 AutoCalcCard" 和 §"#5 缺失交互状态"落实：
>
> 1. AutoCalcCard：背景 `#EDF1F5` → `#ECE8DF`；正文 `#3A4F63` → `#4A4135`；辅助 `#6B7D8E` → `#6B5D4A`；边框 `#C4CDD6` → `#C9BFB0`。所有 AutoCalcCard 相关选择器统一。
> 2. `QPlainTextEdit, QTextEdit`：加 `:focus { border: 1px solid #D97757 }` 和 `:disabled { background: #F0EDE8; color: #9B9590 }`。
> 3. `QToolButton#HelpButton`：加 `:pressed { background: #D97757; color: #FFF9F5 }` 和 `:focus { border: 1px solid #D97757 }`、`:disabled { background: #F0EDE8; color: #C5BFB5 }`。
> 4. `QToolButton#HelpPopoverIconBtn`：加 `:pressed` 和 `:focus`。
>
> 验证：
> - `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q` → 707 passed
> - 不碰 theme.py 外的任何文件
> - 不引入新 QSS 规则以外的逻辑改动

### Agent B（ui-engineer）— spline 裸 Label 审计

**Prompt**：
> 你拿到 `app/ui/pages/spline_fit_page.py`。按 `docs/superpowers/specs/...` §"#2" 落实：
>
> 1. 扫描整个文件的 `QLabel(...)` 调用，每一个都必须在下一行 `setObjectName(...)` 设置为：
>    - "SectionTitle"（章节大标题）
>    - "SubSectionTitle"（子块/字段标题）
>    - "UnitLabel"（单位）
>    - "SectionHint"（辅助/描述文字）
>    之一。根据上下文选择。
> 2. 如果某些 QLabel 已经通过父容器继承了样式（如 SubCard 里的辅助），仍需显式 objectName 以便测试与未来维护。
>
> 验证：
> - `grep -n "QLabel(" app/ui/pages/spline_fit_page.py | grep -v setObjectName` 应该为空（所有 QLabel 下紧跟 setObjectName）
> - `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ui/test_spline_fit_page.py -v` 全过
> - 不改任何 layout 或 logic，**只加 setObjectName 调用**

### Agent C（ui-engineer）— worm 结果滚动 + 图表主题

**Prompt**：
> 你拿到 `app/ui/pages/worm_gear_page.py` 以及 `app/ui/widgets/worm_stress_curve.py` + `app/ui/widgets/worm_performance_curve.py`。按 §"#6" 和 §"#7" 落实：
>
> **#6 WormGearPage 结果区滚动**：
> `worm_gear_page.py:673-749` 的 `_build_results_step` 返回的 page 外层包装 `QScrollArea(widgetResizable=True)`，`setFrameShape(QFrame.Shape.NoFrame)`。
>
> **#7 Matplotlib 主题**：
> 两份 widget 文件统一（对每个 Figure/Axes）：
> - `figure.patch.set_facecolor("#FBF8F3")`
> - `ax.set_facecolor("#FBF8F3")`
> - 主线色 `#D97757`
> - 次线色 `#5A7D9E`（替换现有饱和蓝）
> - 标题/刻度/图例文字色 `#2E2A25`
> - spine/grid 色 `#D9D3CA`
> - 字体由已有 `configure_matplotlib_fonts()` 设置，不要再手动设 rcParams
>
> 验证：
> - `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q` → 707 passed
> - `tests/ui/test_worm_page.py` 必过
> - 不改计算逻辑

## Wave 2（主会话）

在 `CLAUDE.md` 的"项目约定"段追加：

```markdown
## 跨平台对话框
- QFileDialog 等 OS 级对话框**保留原生**，不强制 Qt 自绘。
  理由：原生对话框的 Finder/Explorer 侧栏、最近访问、OS 快捷键
  （Mac Command+Shift+G）等集成收益大于主题一致性。
  偶发的"系统 chrome 穿帮"是已知、可接受的取舍。
```

## Wave 3 — BoltPage 视觉对齐（简化版）

**Prompt（派给 ui-engineer Agent D）**：
> 你拿到 `app/ui/pages/bolt_page.py`。按 §"#1 BoltPage 视觉对齐（简化版）" 落实：
>
> 1. 打开任一继承 `BaseChapterPage` 的模块（如 `interference_fit_page.py`），对照 `base_chapter_page.py` 的 `__init__`：
>    - header Card 的 contentsMargins、spacing、title/hint objectName
>    - actions 行的 left/right 分组 + stretch
>    - footer badge 与 info_label 的 padding
> 2. 把 `bolt_page.py:945-996, 1245-1256` 自建的部分做成与 BaseChapterPage 渲染效果**视觉上一致**：contentsMargins、spacing、objectName、padding 完全对齐。
> 3. 不要真的改成继承 BaseChapterPage（因 BoltPage 有独特的"校核链路"tab 导航）。
> 4. 保留：tab bar（输入步骤/校核链路）、flowchart_nav、校核指南按钮、所有测试案例按钮。
>
> 验证：
> - `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ui/test_bolt_page.py -v` 必过
> - 全量测试 707 过
> - 提交前手动 grab 截图保存到 `/tmp/bolt_after.png`，与 `/tmp/interference_after.png` 对比（主会话核查）

## Wave 4 — Codex 二轮 review

主会话派 `codex:codex-rescue` agent，提示词参考 Phase 1 的 prompt 但明确：
- 本轮目标：验收 spec 中 7 项的验收标准
- 期望输出：每项标记 ✅ / ⚠️ / ❌ 三态
- 若有 ❌，指出具体 file:line 与建议方向
- ✅ 后可直接进入结题报告

若 codex 发现 ❌，回到对应 Wave 修复，再派 codex 审。最多 3 轮；若 3 轮仍不 OK，主会话介入拆解。

## Wave 5 — 结题报告

`docs/reports/2026-04-21-ui-phase2-completion.md`：
- 每项 finding 状态（fixed / deferred / not-applicable）
- 关键文件 diff 摘要
- 全量测试与冒烟结果
- 遗留项与下一步建议
- 同内容追加到 PR #6 的 description（gh pr edit）

最后：`git commit + git push`。

## 回退计划

- 任一 wave 测试失败 → 该 wave agent 自行修复（有 budget）或回退 commit。
- theme.py 改动导致其它模块视觉回归 → 回退 AutoCalcCard 色值到原值，逐条重提。
- Matplotlib 主题导致图表不可读 → 临时还原 `worm_stress_curve.py`。
- Codex 3 轮仍 ❌ → 主会话评估是否缩小本轮 scope 到"只做确定通过的项"，其余单独 PR。
