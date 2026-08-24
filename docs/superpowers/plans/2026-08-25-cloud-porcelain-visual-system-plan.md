# Local Engineering Assistant「云瓷」视觉系统实施 Plan

- 日期：2026-08-25
- 状态：Ready for implementation after user approval
- 依赖 spec：`docs/superpowers/specs/2026-08-25-cloud-porcelain-visual-system-spec.md`
- 目标原型：`docs/ui-mockups/claude-glass-theme-options.html`，方案 A「云瓷」
- 预计工期：8–12 个工程日（含 macOS/Windows 前景验收，不含等待用户 review 的时间）

## 0. 执行结论

本项目不是一次“换主题色”任务，而是一次有计算安全护栏的视觉系统迁移。

执行顺序固定为：

1. 冻结计算/UI/报告基线。
2. 先搭 token 与玻璃表面，不动七个页面业务逻辑。
3. 完成主 shell 并获得第一次真实前景批准。
4. 迁移共享 BaseChapterPage 和通用控件。
5. 逐模块迁移自绘图和页面特例，每个模块独立过门。
6. 跑状态矩阵、全量回归、macOS/Windows 前景矩阵。
7. 只有用户确认最终截图并且计算合同无差异，才标记完成。

禁止先全局替换 `theme.py` 数百个颜色，再靠测试和截图追着修。该方式会同时污染所有页面、popup、自绘图和异常状态，无法定位回归来源。

## 1. 工作区与变更纪律

### 1.1 开始前

执行者必须先记录：

```bash
pwd
git status --short --branch
git log -5 --oneline --decorate
git diff -- app/ui/theme.py app/ui/widgets/help_button.py \
  docs/superpowers/specs/2026-08-23-software-quality-optimization-spec.md \
  docs/superpowers/plans/2026-08-23-software-quality-optimization-plan.md
```

当前已知工作区包含用户/其他任务的未提交改动，尤其是：

- `app/ui/theme.py`
- `app/ui/widgets/help_button.py`
- 帮助浮窗测试和质量 review/spec/plan
- 被删除但仍在 HEAD 中的 `.claude/lessons/*`
- 多个未跟踪 docs、配置和虚拟环境目录

这些内容一律不得回退、删除、重命名或顺手清理。若实施需要编辑同一文件，先基于当前工作区内容合并，不用 `git checkout`、`git reset` 或复制 HEAD 覆盖。

### 1.2 分支与提交

- 建议分支：`codex/cloud-porcelain-visual-system`。
- 每个 wave 独立提交；不在 visual commit 中混入 core、报告内容或帮助工程结论。
- 每次 stage 前使用明确文件列表，不使用 `git add .`。
- 未经用户要求不 push。

### 1.3 硬停线条件

出现任意一项立即停止当前 wave，先诊断：

1. `core/**` 出现 diff。
2. 同一输入的 payload、calculator result 或 report lines 不一致。
3. PASS/FAIL/incomplete/not_checked/reference_only 语义改变。
4. 输入变化后旧结果/导出仍有效。
5. 渲染失败后任何成功指标、badge、图表或预览残留。
6. 页面对象身份、`chapter_page_at()`、`chapter_container_at()` 或按钮属性合同变化。
7. native dialog 被替换为自绘 dialog。
8. 1180×720 出现关键截字、非内容水平滚动或主操作不可见。
9. MainWindow 构造或页面导航超过 spec 预算。
10. 为让测试变绿而放宽既有断言、白名单或数值阈值。

## 2. Wave 0：冻结基线（0.5–1 天）

### 2.1 读取与清单

完整读取/核对：

- `app/ui/theme.py`
- `app/ui/main_window.py`
- `app/ui/pages/base_chapter_page.py`
- `app/ui/fonts.py`
- `app/ui/icons.py`
- `app/ui/widgets/app_combo_box.py`
- `app/ui/widgets/help_popover.py`
- `app/ui/widgets/beginner_guide_dialog.py`
- 七个 module page 的构造、`_build_payload`、calculate/render/report/dirty-state 路径
- 所有 QPainter/matplotlib/SVG widget
- `tests/ui/test_module_workflow_smoke.py`
- `tests/ui/test_render_exception_guard.py`
- `tests/ui/test_export_dirty_tracking.py`
- `tests/ui/test_field_mapping_contract.py`
- `tests/ui/test_result_source_contract.py`

使用 grep 生成两份临时清单：

```bash
rg -n 'setObjectName|setProperty|setStyleSheet' app/ui --glob '*.py'
rg -n 'QColor\(|#[0-9A-Fa-f]{6}' app/ui --glob '*.py'
```

### 2.2 当前 UI 截图基线

使用当前 `.venv` 和当前工作区代码生成：

- 1180×720：主窗口、螺栓首屏。
- 1400×860：七模块输入页。
- 1400×860：七模块默认/样例结果页。
- HelpPopover、BeginnerGuideDialog、QComboBox popup、QMenu、QMessageBox。
- worm stress curve、buffer 曲线、Hertz/bolt 自绘示意图。

offscreen 只用于结构基线；另拍一组 macOS 前景基线。图片先放 `/tmp/cloud-porcelain-baseline/`，不自动提交。

### 2.3 计算/报告冻结基线

为每个正式模块至少捕获：

- 页面默认 payload。
- 测试案例/代表样例 payload。
- 主要 mode 的 payload。
- calculator canonical JSON。
- `ResultViewModel` 的总体/分项状态。
- `_build_report_lines()`。
- 输入变化前后 export enabled 状态。

输出为 canonical UTF-8 JSON，排序 key，拒绝 NaN；保存到 `/tmp/cloud-porcelain-baseline/contracts/`。

不得把当前 calculator 结果当作“公式正确性 golden”；该文件只证明视觉迁移前后不变。

### 2.4 测试基线

```bash
TMPDIR=/tmp QT_QPA_PLATFORM=offscreen PYTHONPATH=. \
  .venv/bin/python -m pytest \
  tests/ui/test_theme.py \
  tests/ui/test_main_window.py \
  tests/ui/test_base_chapter_page.py \
  tests/ui/test_module_workflow_smoke.py \
  tests/ui/test_render_exception_guard.py \
  tests/ui/test_export_dirty_tracking.py -q
```

再跑全量测试并记录真实通过/失败/跳过数。若基线已有失败，先记录为 pre-existing，不在视觉分支顺手修复。

### Gate W0

- [ ] Git/环境/尺寸事实已记录。
- [ ] 七模块 UI 与 contract 基线齐全。
- [ ] macOS 前景基线齐全。
- [ ] 既有失败与本任务无关项已单独记录。
- [ ] 尚未修改产品源码。

## 3. Wave 1：视觉 token 与渲染基础（1–1.5 天）

### 3.1 新增集中 token

建议新增：

- `app/ui/design_tokens.py`
- `tests/ui/test_design_tokens.py`

`design_tokens.py` 至少提供：

- `CloudPorcelainPalette` frozen dataclass。
- spacing、radius、control height、shadow spec。
- `QColor`/QBrush/QPen 获取 helper。
- QSS rgba 序列化 helper。
- matplotlib 色板 dict。
- SVG 色板 dict。

禁止页面 import 一组散乱全局常量后再自行拼色；统一从 `cloud_porcelain_palette()` 或等价只读入口取值。

### 3.2 重构 theme 生成

修改 `app/ui/theme.py`：

- 保留 `apply_theme(app)` 公共入口。
- 将 QSS 构建拆为纯函数，例如 `build_style_sheet(palette) -> str`。
- 全局 `QWidget` 只负责字体和文字颜色；背景只赋给明确 root/surface，防止透明卡片内部出现不透明矩形。
- 保留 `mark_input_field_surface()` 与 `mark_input_field_label_wrap()` 合同。
- 合并当前工作区中的 24 px HelpButton 修正，不回退。

### 3.3 云谱画布与玻璃 primitive

建议新增：

- `app/ui/widgets/cloud_canvas.py`
- `app/ui/widgets/glass_surface.py`（只有确有需要时）
- `tests/ui/test_cloud_canvas.py`

要求：

- QPainter 静态画布，device-independent geometry。
- resize/theme change 才重绘，无 timer。
- 圆角表面优先通过明确 QFrame objectName + QSS；只有 QSS 角点无法可靠达到目标时才用 `GlassSurface(QFrame)` 自绘。
- 不给 inline 字段/列表项加独立 `QGraphicsDropShadowEffect`。
- 任何新 surface subclass 必须保持 QFrame 公共行为，不改变下游对象类型预期。

### 3.4 自动检查

`test_design_tokens.py` 覆盖：

- spec 中所有 token 值。
- QSS 包含必需 selector 和状态。
- 页面/通用 widget 不新增散落的旧主题 hex。
- 报告 PDF、资源生成工具和明确豁免的 SVG fixture 不进入该扫描。
- alpha、对比度和语义色不被 accent 误用。
- 白字主按钮使用 `accent_action`，不能因追求 HTML 原始色值退回对比度不足的 `accent`。

### Gate W1

- [ ] token 单一事实源完成。
- [ ] theme 构建可单测。
- [ ] 云谱静态渲染无 timer/持续 repaint。
- [ ] 仅在测试 probe 中展示 primitive，不迁移七模块。
- [ ] apply_theme/MainWindow 性能未超预算。

## 4. Wave 2：主窗口 shell（1–1.5 天）

### 4.1 修改范围

- `app/ui/main_window.py`
- `app/ui/icons.py`（只做现有资源适配，不重做品牌）
- `app/ui/theme.py`
- 可新增 `app/ui/widgets/navigation_delegate.py`
- `tests/ui/test_main_window.py`
- 新增 `tests/ui/test_cloud_shell_geometry.py`

### 4.2 布局改造

1. central root 改为/包含 `CloudCanvas`，objectName 明确。
2. 根布局 12 px margin，sidebar/workspace 间隔 12 px。
3. QSplitter 保留，目标 sidebar 228 px，可调范围 212–280 px。
4. SidebarPanel 使用 22 px 圆角玻璃面。
5. 品牌区改为顶部横向：35 px accent icon tile + 标题/副标题。
6. 大型底部 brand mark 改为紧凑的“本地工程计算”信息卡。
7. ModuleList 使用 paint-only delegate 显示编号 tile；item.text/tooltip 不变。
8. 不绘制虚构绿色状态点。
9. 如增加 workspace 顶部信息行，只显示当前模块和本地运行事实。
10. statusBar API 保持有效，视觉与右侧 workspace 对齐。

### 4.3 Shell 视觉验收

先只渲染第一个螺栓页面，生成：

- 1180×720 offscreen。
- 1400×860 offscreen。
- 1400×860 macOS 前景。
- sidebar 最窄/最宽。
- module selected/hover/focus。

此处必须暂停，交给用户确认 shell 的材质、颜色、侧栏宽度和背景云谱。用户未通过不得进入 Wave 3。

### Gate W2

- [ ] 与 HTML shell 主几何误差在 spec 容差内。
- [ ] 1180×720 无品牌/模块/主内容关键截字。
- [ ] splitter resize 正常，无阴影裁切。
- [ ] 页面懒加载仍有效。
- [ ] macOS 前景角点无矩形底色。
- [ ] 用户批准 shell 截图。

## 5. Wave 3：共享页面骨架与动作系统（1.5–2 天）

### 5.1 修改范围

- `app/ui/pages/base_chapter_page.py`
- `app/ui/theme.py`
- 可新增：
  - `app/ui/widgets/chapter_delegate.py`
  - `app/ui/widgets/action_overflow.py`
- `tests/ui/test_base_chapter_page.py`
- 新增 `tests/ui/test_action_overflow.py`
- 新增 `tests/ui/test_chapter_delegate.py`

### 5.2 组合 header

- 把标题/subtitle 和 action layout 放入同一个 primary glass header。
- 保持 `add_action_button()` 返回 QPushButton。
- 保持 `left_actions_layout/right_actions_layout` 的兼容性，除非先 grep 并迁移所有消费者。
- 不用 wrapper 替换 page 本体。
- `chapter_page_at()` 与 `chapter_container_at()` 分别继续返回原 page 与实际 container。

### 5.3 动作 overflow

先 grep 七页面动作按钮及测试引用，再定义优先级：

- P0：执行校核/仿真，始终显示。
- P1：保存、加载、指南，空间允许时显示。
- P2：清空、测试案例、次级导出，空间不足时进入 overflow。

代理 QAction 必须：

- 触发原 QPushButton.click()。
- 同步 enabled/visible/text/tooltip。
- 原按钮被输入变更禁用后，菜单 action 同步禁用。
- 原按钮销毁后 action 不访问 deleted wrapper。
- 键盘和 screen reader 可访问。

### 5.4 ChapterList delegate

- QListWidgetItem 仍保存完整 `步骤 N. 标题` 文本。
- delegate 解析/读取 role 绘制编号 tile 与标题。
- currentRowChanged 行为不变。
- tooltip 不变。
- 1180×720 不出现水平滚动。

### Gate W3

- [ ] BaseChapterPage 全部旧测试通过。
- [ ] 七页面构造不抛异常。
- [ ] action/overflow enabled 状态一致。
- [ ] chapter page/container identity 合同通过。
- [ ] 1180×720 和 1400×860 header 截图通过。
- [ ] 不修改任何 `_build_payload/calculate/render/report`。

## 6. Wave 4：通用控件、popup 与状态组件（1–1.5 天）

### 6.1 修改范围

- `app/ui/theme.py`
- `app/ui/widgets/app_combo_box.py`
- `app/ui/widgets/help_button.py`
- `app/ui/widgets/help_popover.py`
- `app/ui/widgets/beginner_guide_dialog.py`
- `app/ui/model_scope.py`（只改 presentation helper 时）
- 对应 UI tests

### 6.2 组件状态板

建立测试/开发用 component gallery（优先测试 helper，不必加入正式导航），至少渲染：

- QLineEdit normal/hover/focus/error/read-only/disabled。
- AppComboBox normal/open/selected/disabled/error。
- primary/secondary/link/disabled button。
- Pass/Fail/Incomplete/NotChecked/Reference badge。
- SubCard/AutoCalcCard/DisabledSubCard/WarningCard。
- QPlainTextEdit、QTableWidget、QScrollBar、QTabBar、QMenu。

### 6.3 HelpPopover 与 Guide

- 保留 anchor 有效性探测和 deleted QWidget 防护。
- 保留 pin/close/resize/失焦行为。
- 外层 frameless popup 必须 `WA_TranslucentBackground`，仅用于该 popup。
- QTextBrowser 的 Qt rich-text CSS 子集按当前可靠方式处理；不把浏览器 CSS 直接复制进去。
- BeginnerGuide 中现有 inline stylesheet 改为 token/objectName，避免旧橙色残留。

### 6.4 popup 前景 gate

macOS 与 Windows 至少验证：

- 首次 combo popup 宽度和位置。
- 贴屏幕右/下边时翻转/clamp。
- HelpPopover pin、close、resize、失焦。
- 销毁 anchor 后再次 show 不崩溃。
- native QFileDialog 仍为原生。

### Gate W4

- [ ] component gallery 状态完整。
- [ ] 帮助/指南内容未改写工程结论。
- [ ] popup 无角点漏底、z-order、focus 或 deleted-wrapper 回归。
- [ ] 200% 缩放下 hit area 和文本可用。

## 7. Wave 5：七模块逐个迁移（2.5–4 天）

每个模块是独立小 gate。一个模块未通过，不得以“其他模块都用了同一 QSS”为由跳过。

### 7.1 迁移顺序

1. 赫兹应力：页面 + `hertz_input_diagram.py`。
2. 轴向受力螺纹连接：输入/结果状态。
3. 花键连接校核：mode、auto/disabled、not_checked/reference。
4. 过盈配合：密集字段、结果层级、表格。
5. 蜗轮蜗杆：geometry/performance/stress curve、matplotlib。
6. 缓冲块：导入态、工作台、energy/response/press-force 曲线、table。
7. 主螺栓：最多动作、flowchart、clamping diagram、完整结果链。

将主螺栓放最后是为了先稳定共享组件；不代表它可以少验收。

### 7.2 页面规则

- 页面业务构造尽量不改，只删除/替换确实覆盖全局 token 的 inline `setStyleSheet`。
- `FieldSpec`、mapping、help_ref、signal 和 mode handler 不改。
- Card/SubCard 通过 objectName 获得新视觉。
- 内容密度过高通过 QScrollArea/布局处理，不缩小关键字号。
- 原型中简化结果卡不能替代真实结果控件。

### 7.3 自绘图迁移

对下列文件逐一迁移硬编码色：

- `app/ui/widgets/hertz_input_diagram.py`
- `app/ui/widgets/clamping_diagram.py`
- `app/ui/widgets/press_force_curve.py`
- `app/ui/widgets/worm_geometry_overview.py`
- `app/ui/widgets/worm_performance_curve.py`
- `app/ui/widgets/worm_stress_curve.py`
- `app/ui/widgets/buffer_energy_curve.py`
- `app/ui/widgets/buffer_response_curve.py`

每个图表增加“数据路径未变”断言：

- 原 x/y 数组或几何参数与迁移前相等。
- marker/limit/working point 使用原结果字段。
- 不在 paintEvent 中重新计算工程判据。
- paintEvent 异常不修改 page 的计算状态。

`clamping_diagram.py` 内嵌 SVG 通过 palette format 参数替换颜色，不能用全局字符串 replace 误改路径、变量或文字。

### 7.4 每模块固定验证

每完成一个模块执行：

1. 目标 module UI tests。
2. `test_field_mapping_contract.py` / 对应 payload contract。
3. `test_render_exception_guard.py` 相关案例。
4. `test_export_dirty_tracking.py` 相关案例。
5. 默认/样例 `_calculate()` smoke。
6. `_build_report_lines()` 与 W0 baseline 比较。
7. 输入页 + pass/fail/incomplete（适用时）结果页截图。
8. macOS 前景点击：导航、输入、计算、修改输入、导出状态。

### Gate W5

- [ ] 七模块逐个完成，证据不互相替代。
- [ ] 无 payload/result/report diff。
- [ ] 无页面旧米色/旧橙色孤岛。
- [ ] 自绘图数据和 marker 位置未变。
- [ ] pass/fail/incomplete/not_checked/reference_only 语义正确。

## 8. Wave 6：异常、stale 与跨出口可信度复核（1 天）

### 8.1 状态场景

逐模块或按能力覆盖：

- 初始未计算。
- 合法输入计算成功。
- 正式 fail。
- incomplete。
- not_checked。
- reference_only 超限。
- 输入错误。
- core exception。
- render exception。
- report preview exception。
- 计算后修改输入。
- 加载输入条件。
- 清空页面。

### 8.2 可见面清理检查

对每个异常/失效路径逐项检查：

- 总体 badge。
- 指标卡。
- 分项 badge。
- 文本结果。
- QTableWidget。
- QPainter/matplotlib 图表。
- report preview。
- workbench/status summary。
- 页面 footer。
- 原按钮和 overflow action 的导出 enabled 状态。

### 8.3 跨出口对照

对每个总体状态对照：

```text
core result
  == ResultViewModel
  == UI badge/title
  == text report lines
  == PDF/DOCX verdict/status
```

本 wave 不改变报告样式；任何内容差异都是 blocker。

### Gate W6

- [ ] stale/异常后无成功视觉残留。
- [ ] UI 与导出状态一致。
- [ ] 未校核和参考项没有伪绿/伪红。
- [ ] 结果失败不影响下一次合法计算恢复。

## 9. Wave 7：视觉对标与跨平台前景（1–2 天）

### 9.1 自动 render probe

建议新增：

- `tools/render_cloud_porcelain_matrix.py`
- `tests/ui/test_cloud_porcelain_render_contract.py`

工具输出到显式临时目录，不污染仓库。覆盖 spec §14 的截图矩阵。

自动断言只检查稳定事实：

- 支持尺寸。
- 控件 geometry/hit area。
- scrollbar policy。
- token 采样点。
- 圆角角点没有错误底色。
- primary/selected/focus/error 状态色。

不把完整 PNG 二进制相等作为跨平台 gate。

### 9.2 HTML 对标

在 1400×860 central-widget crop 上制作 A/B overlay（A=HTML cloud window，B=Qt）：

- shell 外边距。
- sidebar 宽度与圆角。
- header 高度。
- chapter/content gap。
- surface 明度。
- accent/secondary/status 色。
- 字体基线和按钮视觉中心。
- 云谱位置和强度。

按 spec 容差记录 PASS/FAIL，不使用“看起来差不多”。

### 9.3 macOS 前景

真实运行：

```bash
./.venv/bin/python app/main.py
```

检查：

- Retina 圆角、阴影和云谱。
- 七模块 navigation/input/result。
- splitter resize。
- hover/focus/pressed。
- combo/menu/help/guide/messagebox/native file dialog。
- 输入变更与导出失效。
- 长内容滚动与 popup z-order。

### 9.4 Windows 前景

至少在 100%、125%、150% DPI 检查：

- 启动和最小尺寸。
- 字体回退。
- titlebar/resize。
- combo/menu/help popup。
- 七模块切换。
- 每模块至少一个样例计算。
- 输入修改后导出禁用。
- PDF/TXT/DOCX smoke（内容一致，不审本次报告视觉）。

### Gate W7

- [ ] HTML/Qt 几何与颜色容差通过。
- [ ] macOS 前景完整通过。
- [ ] Windows 100/125/150% 通过。
- [ ] 用户确认最终 1400×860 shell、输入、结果、popup 四类截图。

## 10. Wave 8：全量验证、review 与收口（0.5–1 天）

### 10.1 静态与 focused tests

```bash
git diff --check
rg -n 'QColor\(|#[0-9A-Fa-f]{6}' app/ui/pages app/ui/widgets --glob '*.py'

TMPDIR=/tmp QT_QPA_PLATFORM=offscreen PYTHONPATH=. \
  .venv/bin/python -m pytest \
  tests/ui/test_design_tokens.py \
  tests/ui/test_cloud_canvas.py \
  tests/ui/test_cloud_shell_geometry.py \
  tests/ui/test_cloud_porcelain_render_contract.py \
  tests/ui/test_theme.py \
  tests/ui/test_main_window.py \
  tests/ui/test_base_chapter_page.py \
  tests/ui/test_module_workflow_smoke.py \
  tests/ui/test_render_exception_guard.py \
  tests/ui/test_export_dirty_tracking.py \
  tests/ui/test_field_mapping_contract.py \
  tests/ui/test_result_source_contract.py -q
```

文件名以实际落地为准，但能力项不可省略。

### 10.2 七模块 UI 套件

```bash
TMPDIR=/tmp QT_QPA_PLATFORM=offscreen PYTHONPATH=. \
  .venv/bin/python -m pytest \
  tests/ui/test_bolt_page.py \
  tests/ui/test_bolt_tapped_axial_page.py \
  tests/ui/test_bolt_tapped_axial_results.py \
  tests/ui/test_interference_page.py \
  tests/ui/test_spline_fit_page.py \
  tests/ui/test_worm_page.py \
  tests/ui/test_worm_stress_curve.py \
  tests/ui/test_hertz_page.py \
  tests/ui/test_buffer_energy_page.py -q
```

### 10.3 全量回归

```bash
TMPDIR=/tmp QT_QPA_PLATFORM=offscreen PYTHONPATH=. \
  .venv/bin/python -m pytest tests/ -q
```

全量失败时不直接归因主题；先单独复现第一个失败并区分 pre-existing、环境、时序或本次回归。

### 10.4 计算合同复核

- 重新生成 W0 canonical JSON。
- 对 payload/result/report 做结构化 diff。
- `git diff --name-only -- core` 必须为空。
- grep UI 是否新增工程公式、阈值、工作点推导。
- 报告状态与结果 view model 再做一次跨出口 smoke。

### 10.5 独立 review

最终 review 先列发现并逐条给状态：

- P0：计算/状态/导出可信度回归。
- P1：原型差距、支持尺寸、popup、信息丢失。
- P2：像素、性能、重复 token、跨平台差异。

reviewer 必须检查真实 diff、target HTML、macOS/Windows 前景截图和计算 contract diff；不能只看测试报告。

### Gate W8

- [ ] `git diff --check` 通过。
- [ ] focused 与全量测试通过；无放宽断言。
- [ ] core diff 为空。
- [ ] canonical contract diff 为空。
- [ ] 独立 review 的 P0/P1 清零。
- [ ] 用户最终视觉验收通过。

## 11. 推荐提交切分

1. `test: freeze cloud-porcelain visual and data contracts`
2. `refactor: centralize cloud-porcelain design tokens`
3. `feat: add static cloud canvas and glass surfaces`
4. `feat: restyle main shell with floating sidebar`
5. `feat: unify chapter header navigation and action overflow`
6. `feat: apply cloud controls and popup chrome`
7. `style: migrate hertz tapped spline and interference surfaces`
8. `style: migrate worm buffer and bolt diagrams`
9. `test: cover stale error dpi and render parity states`
10. `docs: record cloud-porcelain foreground acceptance`

每个提交都先检查 changed-file scope；如果当前工作区同文件包含其他任务改动，提交时只 stage 本任务 hunk 或等待用户决定。

## 12. 交付物

### 必须交付

- 云瓷 token 与 theme 构建代码。
- 主 shell、BaseChapterPage、通用控件和七模块视觉迁移。
- 自绘图与 matplotlib palette 迁移。
- 自动 render/geometry/state tests。
- 计算/payload/report 前后对照证据。
- macOS 与 Windows 前景截图矩阵。
- 最终验收报告，逐条对应 spec Definition of Done。

### 最终报告必须分开写

- 实现状态。
- focused tests。
- 全量 tests。
- macOS 前景。
- Windows 前景。
- HTML parity。
- 计算/报告 contract diff。
- Git commit/push 状态。

任何一项未完成都必须写 `未验证` 或 `PARTIAL`，不能用其他证据代替。

## 13. 最终验收清单

- [ ] 用户已确认方案 A 云瓷，不再保留 B/C 产品实现分支。
- [ ] 1400×860 达到 HTML cloud window 的材质与层级。
- [ ] 1180×720 完整可用。
- [ ] 七模块输入页和结果页全部完成，不只验证螺栓首屏。
- [ ] normal/hover/focus/pressed/disabled/error/read-only/auto-filled 完整。
- [ ] pass/fail/incomplete/not_checked/reference_only/stale/render-error 完整。
- [ ] combo/menu/help/guide/messagebox/native dialog 正常。
- [ ] 所有自绘图数据、marker、limit、工作点不变。
- [ ] payload/calculator result/report lines 前后无差异。
- [ ] 输入变更、加载、清空、渲染失败不会留下旧结果或可导出状态。
- [ ] macOS 前景通过。
- [ ] Windows 100/125/150% 前景通过。
- [ ] 性能预算通过。
- [ ] focused/full tests 通过，无放宽断言。
- [ ] `core/**` 无 diff。
- [ ] 用户批准最终截图。
- [ ] 只提交批准范围，未覆盖其他工作区改动。

完成定义不是“主题已应用”，而是“云瓷视觉在真实七模块、全部关键状态和两个桌面平台上成立，同时计算与报告合同零变化”。
