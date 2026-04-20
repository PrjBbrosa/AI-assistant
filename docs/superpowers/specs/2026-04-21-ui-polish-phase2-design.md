# UI 统一性加固 Phase 2 — 设计 Spec

**日期**：2026-04-21
**作者**：主会话
**背景**：PR #6（theme-widget-polish）已完成默认组件（scrollbar / combobox popup / checkbox / menu / spinbox / ...）的 Claude 暖中性主题覆盖。Codex 对此分支做了一轮 review，产出 7 项发现。本 spec 定义这 7 项的验收标准与取舍决策。

## Review 原始发现

引用自 2026-04-21 Codex review 报告：

| # | 严重度 | 问题 | 位置 |
|---|---|---|---|
| 1 | Major | BoltPage 骨架不一致，自建 header/actions/footer，没走 `BaseChapterPage` | `bolt_page.py:945-996, 1245-1256` |
| 2 | Major | SplineFitPage 裸 QLabel 无 objectName；结果页版式偏离共版式 | `spline_fit_page.py:519-569, 571-614` |
| 3 | Major | QFileDialog 走 macOS 原生面板 | `input_condition_store.py:65-85` |
| 4 | Minor | AutoCalcCard 对比度 3.74:1 不达 WCAG AA；冷蓝嵌暖中性割裂 | `theme.py:198-215` |
| 5 | Minor | QPlainTextEdit/QTextEdit 缺 `:focus`/`:disabled`；HelpButton 缺 `:pressed`/`:focus`/`:disabled` | `theme.py:378-385, 717-733` |
| 6 | Polish | WormGearPage 结果区竖堆无滚动兜底 | `worm_gear_page.py:673-749` |
| 7 | Polish | Matplotlib 图表（worm_stress_curve）默认蓝线灰底 DejaVu | `worm_stress_curve.py:26-33, 70-97` |

## 验收标准（按项）

### #4 — AutoCalcCard 对比度与色调
- **当前**：背景 `#EDF1F5`（冷蓝灰），正文 `#3A4F63`，辅助 `#6B7D8E`。冷色与整体暖中性冲突；辅助文字对比 3.74:1 < WCAG AA 4.5:1。
- **目标**：
  - 背景改暖灰如 `#ECE8DF`（与 Sidebar `#EEE7DE` 同色系，略浅）
  - 正文改 `#4A4135`（warm ink）
  - 辅助改 `#6B5D4A`，对背景对比 ≥ 4.5:1
  - 保持"auto-filled"视觉标识（边框仍略深：`#C9BFB0` 实线）
- **验证**：用工具或手算 WCAG，所有文字对比 ≥ 4.5:1。

### #5 — 缺失交互状态
- `QPlainTextEdit, QTextEdit`：补 `:focus`（border `#D97757`）、`:disabled`（bg `#F0EDE8`、文字 `#9B9590`）。
- `QToolButton#HelpButton`：补 `:pressed`（bg `#D97757`, color `#FFF9F5`）、`:focus`（border 1px `#D97757`）、`:disabled`（bg `#F0EDE8`, color `#C5BFB5`）。
- `QToolButton#HelpPopoverIconBtn`：补 `:pressed`、`:focus`。
- **验证**：手动点击每种按钮验证状态切换；或跑测试触发 focus/press 快照（视现有测试支持情况）。

### #2 — SplineFitPage 裸 QLabel
- **目标**：spline_fit_page.py 里所有 `QLabel(...)` 调用均需 `setObjectName("SectionTitle" / "SubSectionTitle" / "UnitLabel" / "SectionHint")` 之一，或外部 SubCard 自带样式。
- **验证**：grep `QLabel(` 的裸实例数量前后对比；`tests/ui/test_spline_fit_page.py` 全过。
- **范围外**：结果页"版式对齐其他模块"重构不在本轮——只做 objectName 补齐这一步低风险动作。

### #3 — QFileDialog 原生 vs 自绘
- **决定**：**保留 macOS 原生对话框**。理由：
  1. 原生对话框对用户（尤其 Mac 用户）更熟悉，Finder 侧栏、iCloud、最近访问等系统集成无法替代
  2. Qt 自绘的 QFileDialog 样式补全工作量大，且在 Mac 上会失去 Command+Shift+G 等快捷键
  3. 保存/加载输入条件是低频操作，界面一致性收益 < 原生用户体验
- **spec 记录**：该取舍写入 `CLAUDE.md` 的"跨平台 UI 约定"段（追加于下一次 CLAUDE.md 修订）。
- **代码改动**：无。

### #6 — WormGearPage 结果区滚动兜底
- **目标**：`_build_results_step` 返回的 page 外层包 `QScrollArea(widgetResizable=True, frame=NoFrame)`。
- **验证**：窗口缩到 `resize(900, 600)` 时，结果区出现滚动条而非截断。
- **兼容**：现有测试 `tests/ui/test_worm_page.py` 断言结果 label/字段可被 findChild 找到，QScrollArea 包装不影响 findChild 递归。

### #7 — Matplotlib 图表主题
- **worm_stress_curve.py** + **worm_performance_curve.py** 统一：
  - `figure.patch.set_facecolor("#FBF8F3")` （Card 色）
  - `ax.set_facecolor("#FBF8F3")`
  - 主线色 `#D97757`（已部分用）
  - 次线色 `#5A7D9E`（暖中性友好的蓝灰，替代 `#2563EB` 那种饱和蓝）
  - 图例/标题/刻度文字色 `#2E2A25`
  - spine + grid 色 `#D9D3CA` 淡化
  - 字体经由 `configure_matplotlib_fonts()` 统一（已有）
- **验证**：手动执行测试案例 1/2 后查看图表，线条/背景/字体均属暖中性调色板。

### #1 — BoltPage 骨架一致（简化版）
- **讨论**：BoltPage 有独特的"校核链路"flowchart 导航，`BaseChapterPage` 不支持 tab 切换导航栈。全量继承需要：
  - 把 flowchart nav 改造成插件式（BaseChapterPage 加 nav 扩展点）
  - 或保留 BoltPage 不继承，只做视觉对齐
- **决定**：**本轮只做视觉对齐**，不做类继承重构。
  - 核查 bolt_page.py 的 header Card、action bar、footer badge 的 objectName、字号、padding、间距与 BaseChapterPage 生成的一致
  - 不一致处修齐
- **后续 PR**（非本轮）：把 flowchart nav 抽成 BaseChapterPage 的可插拔组件，再让 BoltPage 继承。用独立 spec/plan 推进。
- **验证**：截图 bolt 模块与任一继承 BaseChapterPage 的模块（如 interference）并排对比，header/action bar 视觉一致。

## 范围外（Deferred）

- BoltPage 全量继承 `BaseChapterPage` 重构 → 独立 PR
- SplineFitPage 结果页版式重构为 summary/check/metrics 分块 → 独立 PR
- 自绘 QFileDialog 替代原生 → 永久决定不做
- 批量自动化对比度检测工具（axe 类） → 独立基础设施

## Agent 分配与并行可行性

| 任务 | 文件范围 | 冲突风险 | 建议 agent |
|---|---|---|---|
| #4+#5 (theme) | `app/ui/theme.py` | 与其它任务无 | `ui-engineer` #A |
| #2 (spline) | `app/ui/pages/spline_fit_page.py` | 无 | `ui-engineer` #B |
| #6+#7 (worm) | `app/ui/pages/worm_gear_page.py` + `app/ui/widgets/worm_stress_curve.py` + `app/ui/widgets/worm_performance_curve.py` | 无 | `ui-engineer` #C |
| #3 (filedialog) | 无代码改动 | 无 | 主会话自己处理 |
| #1 (bolt align) | `app/ui/pages/bolt_page.py` | 可能与 #4/#5 有 theme interaction | `ui-engineer` #D（串行在 theme 之后）|

A/B/C 可并行（Wave 1），D 串在 A 后（Wave 2），全部完成后跑 Codex review（Wave 3）。

## 测试要求
- 每个 wave 完成后跑 `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q`，必须 707 全过。
- 手动冒烟：启动 app，切换每个模块，打开至少一个 combobox 下拉，观察视觉。
