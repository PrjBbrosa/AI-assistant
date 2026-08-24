# Local Engineering Assistant「云瓷」悬浮毛玻璃视觉系统 Spec

- 日期：2026-08-25
- 状态：Approved direction / implementation not started
- 选定方案：A「云瓷 / Cloud Porcelain」
- 目标原型：`docs/ui-mockups/claude-glass-theme-options.html` 的 `data-theme="cloud"`
- 配套计划：`docs/superpowers/plans/2026-08-25-cloud-porcelain-visual-system-plan.md`
- 依赖质量合同：`docs/superpowers/specs/2026-08-23-software-quality-optimization-spec.md`

## 1. 决策与目标

本次确定使用 A「云瓷」作为 Local Engineering Assistant 的唯一新视觉方向。

最终产品必须达到 HTML 原型中应用窗口主体的视觉效果：低饱和暖灰画布、珊瑚强调色、半透明浅色表面、清晰的悬浮层级、克制的应力云谱背景、精确的圆角与留白，以及完整的 hover/focus/pressed/disabled/error/read-only/auto-filled/result 状态。

“达到原型效果”不等于把 CSS 粗略翻译成 QSS，也不等于只替换 `theme.py` 中的色值。实现必须覆盖：

1. 主窗口壳层和侧栏。
2. 共享章节页面骨架。
3. 输入、自动填充、禁用、警告和结果卡。
4. 自绘工程图、QPainter 曲线和 matplotlib 曲线。
5. 帮助按钮、帮助浮窗、新手指南、菜单、组合框和消息框。
6. 正常、失败、校核不完整、未校核、仅参考、输入已变更和渲染失败状态。
7. macOS 与 Windows 的真实前景表现。

## 2. 事实基线

### 2.1 当前代码事实

- 当前主窗口默认尺寸为 `1400×860`，最小尺寸为 `1180×720`，以 `app/ui/main_window.py` 为准。
- 当前页面骨架是 `BaseChapterPage`：头部卡、动作条、章节导航、章节 stack 和 footer。
- 主题主入口是 `app/ui/theme.py::apply_theme()`。
- 当前通用 objectName 至少包括 `Card`、`SubCard`、`AutoCalcCard`、`DisabledSubCard`、`WarningCard`、`InputField`、`PassBadge`、`FailBadge`、`WaitBadge`、`RefBadge`、`SidebarPanel`、`ModuleList`、`ChapterList`、`HelpPopover*`。
- 多个 QPainter/matplotlib/SVG 组件仍硬编码旧暖米色，包括 `press_force_curve.py`、`worm_*`、`buffer_*`、`hertz_input_diagram.py`、`clamping_diagram.py`。
- 当前工作区已有帮助按钮与质量文档的未提交改动；视觉实现不得覆盖或回退这些改动。

### 2.2 已知历史风险

以下问题必须作为本 spec 的硬约束，而不是实施后的补救项：

- QSS token 或 offscreen 测试不能证明真实圆角像素和前景观感。
- 调 margin/spacing 不能修复错误的 sizePolicy；内容超高必须使用 QScrollArea。
- 新 wrapper 不能偷换 `chapter_stack.widget()` 的对象类型合同。
- mode 是字段显隐、锁定和 payload 的权威状态；视觉层不得重新解释 mode。
- core 新字段、UI 渲染和报告消费是三条独立链路。
- 输入变更后旧结果和导出必须立即失效。
- 渲染失败必须清理所有用户可见结果面，不能只清内部变量。
- `not_checked/incomplete/reference_only` 不能被重新涂成 PASS 或普通 FAIL。
- 帮助浮窗、frameless 圆角面和 Qt widget 生命周期必须在真实 Qt 路径验证。

## 3. 范围与非目标

### 3.1 本次范围

- 新增集中式视觉 token 与调色板 API。
- 重做应用画布、侧栏、共享页面骨架和通用控件视觉。
- 让七个正式模块使用统一云瓷表面和语义状态。
- 统一自绘图和 matplotlib 图表的视觉色板，但不改变坐标、数据、判据或工作点。
- 建立可重复的 render probe、几何检查、功能回归和前景验收矩阵。
- 必要时增加只负责呈现的 delegate/widget/helper。

### 3.2 非目标

- 不修改 `core/` 中任何公式、阈值、默认值、输入验证或结果结构。
- 不新增工程计算项，不删减现有结果信息。
- 不重写 FieldSchema、ResultViewModel、报告架构或 calculator adapter。
- 不改变保存文件格式、输入 JSON schema、payload key 或 mode 枚举。
- 不在同一变更中重做 TXT/PDF/DOCX 报告视觉；只验证报告内容与状态不变。
- 不实现暗色主题。
- 不把主窗口改成 frameless 自绘标题栏。
- 不强制 Qt 自绘 `QFileDialog/QFontDialog/QColorDialog` 等 OS 级对话框。
- 不引入 WebView、QML 或第三方毛玻璃库。
- 不使用持续动画、噪声视频或动态模糊制造“高级感”。

## 4. 原型的权威边界

### 4.1 必须还原

HTML 原型中下列内容属于产品视觉合同：

- 云瓷色板、玻璃面板、高光边、柔和阴影和应力云谱。
- 12–16 px 外部呼吸空间与悬浮面板之间的空隙。
- 顶部品牌区、侧栏选中态、章节选中态、输入表面和结果卡层级。
- 珊瑚主操作、蓝灰自动派生、低饱和绿色 PASS。
- 10–22 px 的分级圆角。
- 数字、单位、变量符号的等宽辅助字体。
- 轻量 hover、focus、pressed 和计算完成反馈。

### 4.2 不得照搬

下列内容仅为 HTML 展示素材，不得作为真实功能进入产品：

- `CASE-024`、虚构项目路径和虚构同步状态。
- 每个模块右侧的绿色“就绪”点。
- 原型中简化后的三个结果数字，不能替代真实结果页。
- 浏览器页面的方案切换器、设计说明卡和 94% 评分。
- 浏览器模拟的窗口三色点；真实产品保留原生标题栏。

需要同位置的信息时，只能使用当前软件已拥有的真实状态，例如当前模块名、本地运行状态、输入是否变更、结果是否可导出。

## 5. 视觉原则

### V-01 空灵来自层级，不来自低对比度

正文、字段值和状态必须清晰；轻盈感由背景、空隙、高光边、半透明表面和少量阴影产生。禁止通过把文本和边框整体变淡来伪造毛玻璃。

### V-02 只在三层表面使用阴影

阴影等级：

1. Shell surface：侧栏、页面头部、主内容容器。
2. Raised control：主按钮、popup、菜单。
3. Inline surface：输入框、SubCard、badge 不使用独立大阴影，只使用边框和内高光。

禁止给每个字段卡或每个列表项添加 `QGraphicsDropShadowEffect`。

### V-03 语义优先于品牌色

珊瑚色表示选择、focus 和主操作，不能被复用为 FAIL。PASS/FAIL/incomplete/not_checked/reference_only 使用独立语义色，并同时提供文字/图标/形状差异。

### V-04 工程内容不为视觉让路

不能为了让页面像原型而隐藏、合并或重新计算工程结果。密集结果允许折叠追溯区，但默认关键结论、关键指标、未校核项和警告必须可见。

### V-05 静态拟态毛玻璃优先

跨平台实现使用“拟态毛玻璃”：不透明画布 + 半透明浅色面板 + 高光边 + 受控阴影。首版不做实时 backdrop blur；HTML 的 `backdrop-filter` 只是视觉参考。

## 6. 云瓷 token 合同

颜色值源自 HTML 的 cloud 主题。Qt 实现应集中在一个 token 模块中，页面与自绘 widget 不得复制十六进制色值。

### 6.1 基础色

| Token | 值 | 用途 |
|---|---:|---|
| `canvas_outer` | `#DFE3E5` | 窗口外部/截图基底参考 |
| `canvas_base` | `#EFF0EF` | 主应用画布 |
| `surface_glass` | `rgba(252,252,250,0.68)` | 通用玻璃面 |
| `surface_glass_strong` | `rgba(253,252,249,0.88)` | header、popup、按钮 |
| `surface_glass_soft` | `rgba(249,249,247,0.50)` | hover/轻层 |
| `surface_field` | `rgba(255,255,253,0.76)` | 输入框、combo、text edit |
| `ink_primary` | `#282624` | 主文字 |
| `ink_muted` | `#716D68` | 正文说明 |
| `ink_quiet` | `#96908A` | 微标签、辅助信息 |
| `line_highlight` | `rgba(255,255,255,0.86)` | 玻璃高光边 |
| `line_structural` | `rgba(91,82,74,0.16)` | 结构边和控件边 |

### 6.2 品牌与辅助色

| Token | 值 | 用途 |
|---|---:|---|
| `accent` | `#C76C4D` | 主操作、选中编号、曲线主色 |
| `accent_action` | `#B75D40` | 带白色小字号文字的主按钮（对比度 ≥4.5:1） |
| `accent_hover` | `#A95338` | 主操作 hover/pressed |
| `accent_soft` | `#F2D8CF` | 选中背景 |
| `accent_ink` | `#733C2B` | accent-soft 上文字 |
| `secondary` | `#71868A` | 自动派生/第二曲线 |
| `secondary_soft` | `#DCE7E8` | 自动填充表面 |
| `focus_ring` | `rgba(199,108,77,0.18)` | 3 px 外焦点环 |

### 6.3 状态色

| 状态 | 前景 | 背景 | 文案合同 |
|---|---:|---:|---|
| pass | `#2B715C` | `#D8EBE4` | 通过/预校核通过 |
| fail | `#9D4939` | `#F2D9D3` | 不通过/预校核不通过 |
| incomplete | `#946525` | `#F3E5C9` | 校核不完整 |
| not_checked | `#6F716E` | `#E5E6E3` | 未校核 |
| reference_only | `#566B72` | `#DEE7E9` | 仅参考 |
| warning | `#9B672F` | `#F2E3CF` | 警告/适用范围 |
| input_error | `#A33F35` | `#F5DEDA` | 输入错误 |

状态 badge 必须包含中文文本；fail 与 pass 不得只用红绿区分。建议图形分别使用 `✓`、`×`、`!`、`—`、`i`。

### 6.4 应力云谱

主画布右上角绘制静态同心圆应力场：

- 中心约为 `(viewport_width - 90, 70)`。
- 半径从 64 px 到 340 px，间隔约 36 px。
- 线宽 1 px，白色 alpha 35–55。
- 圆心下方叠加暖珊瑚径向渐变，最大 alpha 32。
- 左下可使用蓝灰径向渐变，最大 alpha 24。
- 不得滚动、呼吸或跟随鼠标。

### 6.5 圆角

| Token | 值 |
|---|---:|
| `radius_window_reference` | 30 px（仅 HTML/截图外框参考） |
| `radius_sidebar` | 22 px |
| `radius_primary` | 19–20 px |
| `radius_panel` | 14–15 px |
| `radius_control` | 10 px |
| `radius_badge` | 999 px |
| `radius_small` | 7–8 px |

### 6.6 spacing 与尺寸

- 基础网格：4 px；主要间距只使用 4/8/12/16/20/24/32。
- 主画布外边距：12 px。
- 侧栏与 workspace 间距：12 px。
- 侧栏目标宽度：228 px；允许用户通过 splitter 调整到 212–280 px。
- 模块项高度：40 px。
- 页面头部最小高度：78 px。
- 标准按钮高度：32 px；主按钮可为 34 px。
- 输入控件高度：36 px。
- icon-only hit area：至少 28×28 px，推荐 32×32 px。
- 内容卡 padding：16 px；SubCard padding：12–16 px。

### 6.7 字体

- 继续使用 `app/ui/fonts.py` 的平台字体栈，不下载 Web 字体。
- 主界面正文：10 pt。
- 页面标题：15–16 pt，DemiBold。
- 区块标题：11–12 pt，DemiBold。
- 微标签：8–9 pt，DemiBold，字距仅用于大写英文。
- 数字/变量/单位：`make_mono_font()`，不得在页面写死 Menlo/Consolas。
- 不以极细字重制造空灵感；Windows 下正文不得低于 Normal。

## 7. 主窗口结构合同

### SHELL-01 原生窗口

- 保留 QMainWindow 原生标题栏、拖动、缩放、最小化和系统菜单。
- 中央画布使用 `canvas_base` 与应力云谱。
- 不设置整个窗口 `WA_TranslucentBackground`，避免 Windows 黑边、输入法和 resize 回归。

### SHELL-02 悬浮侧栏

- 侧栏离窗口四边 12 px，圆角 22 px，使用一级玻璃表面。
- 品牌图标移到顶部 35×35 的 accent tile；复用现有 app icon，不新增未经确认的品牌图形。
- 标题与副标题保持真实名称。
- 移除/收起当前底部 180 px 大图，替换为紧凑的“本地工程计算”信息卡。
- 模块列表通过 delegate 绘制编号与标签；不添加虚构就绪点。
- 模块名称、tooltip 和页面标题必须继续一致。

### SHELL-03 workspace 顶部信息行

- 可增加 36–40 px 的轻量 workspace chrome，但只能显示真实信息。
- 推荐内容：`本地机械设计工作台 / 当前模块` 与 `本地运行`。
- 不显示假项目、假同步、假保存成功或假 CASE 编号。

### SHELL-04 状态栏

- 继续保留现有 `statusBar().showMessage()` API。
- 状态栏视觉应与右侧 workspace 对齐，显示运行、导航、保存、错误信息。
- 状态栏不得显示或复制总体 PASS/FAIL。

## 8. BaseChapterPage 合同

### PAGE-01 组合式页面头部

页面标题、subtitle 与动作按钮合并在同一一级玻璃头部，视觉对应 HTML 原型的 module header。

必须保留：

- `add_action_button()` 返回真实 QPushButton 的合同。
- `add_guide_button()` 行为。
- 所有页面对按钮属性和 enabled 状态的引用。
- `chapter_page_at()` 与 `chapter_container_at()` 语义。

不得通过临时 wrapper 改变既有 page/container 对象身份。

### PAGE-02 动作优先级与 overflow

- 每页只能有一个 primary action。
- `执行校核/执行仿真` 始终可见。
- 保存、加载和指南优先可见。
- 清空、测试案例、次级导出在宽度不足时进入 overflow。
- overflow QAction 只是既有 QPushButton 的代理：trigger 调用原按钮 `click()`，enabled/visible/text/tooltip 状态双向同步。
- disabled 的导出不能因进入 overflow 而被错误启用。

### PAGE-03 章节导航

- 使用 paint-only delegate 绘制步骤编号 tile 和标题，不给每项创建 QWidget。
- `QListWidgetItem.text()` 保持完整原文本，避免测试、tooltip 和可访问性合同漂移。
- 选中态为 accent-soft + accent 编号块；hover 只使用 soft glass。
- 章节列表不出现水平滚动条。

### PAGE-04 内容与滚动

- 主 stack 的页面对象、QScrollArea 和 sizePolicy 保持现有行为。
- 内容超高时只能通过 QScrollArea 解决，不能通过压缩卡片或硬设小字号解决。
- Card/SubCard 视觉改变不得改变页面的 payload、signal、slot 或父子生命周期。

## 9. 控件状态合同

### CONTROL-01 输入控件

必须覆盖：normal、hover、focus、disabled、read-only、error、auto-filled、selection。

- normal：field surface + structural line。
- focus：accent border + 3 px focus ring，不能只变边框颜色。
- error：input_error border + 可见错误文本；focus 后仍保持错误语义。
- read-only：比 disabled 更清晰，文字仍可读/可复制。
- auto-filled：secondary-soft 表面 + 来源文案，不等同 disabled。
- disabled：降低对比但仍可辨认标签和当前值。

### CONTROL-02 按钮

- Primary：accent 实色、白字、轻阴影。
- 带白色小字号文字的 Primary 实际使用 `accent_action`；`accent` 保留给选中块、图标和曲线，以兼顾原型观感与 4.5:1 对比度。
- Secondary：strong glass、structural line。
- Link：透明，无独立卡片背景。
- disabled：保留轮廓，不能消失在玻璃面上。
- pressed 必须比 hover 更深，不能只向下移动。

### CONTROL-03 popup 与对话框

- AppComboBox popup、QMenu、帮助浮窗和新手指南使用云瓷表面。
- HelpPopover 外层使用透明背景与自绘/可靠圆角，角落不得出现矩形底色。
- popup 首次打开位置、屏幕翻转、focus 和关闭行为在 macOS/Windows 前景验证。
- OS 级文件、字体和颜色对话框保持原生。

## 10. 工程状态与结果合同

### RESULT-01 结论层级

结果页面保持：总体结论 → 关键指标 → 分项检查 → 追溯/公式/消息。

视觉改造不能：

- 把 `incomplete` 显示为 fail 或 pass。
- 把 `not_checked` 计入 PASS。
- 把 reference_only 与正式失败同权。
- 隐藏未覆盖模型范围。
- 复制总体状态到 footer。

### RESULT-02 stale 状态

输入改变、加载条件、清空页面后：

- 旧结果面全部进入待重新计算/空状态。
- 导出按钮与 overflow 中的导出 QAction 同步禁用。
- 旧 PASS 不能继续以绿色卡片存在。
- 图表不得继续暗示是当前输入的结果。

### RESULT-03 render failure

计算成功但结果、图表或报告预览渲染失败时：

- 清空所有已写入的指标、badge、结果文本、图表、预览和工作台摘要。
- 禁用导出。
- 显示明确错误状态。
- 不改变 core 返回，不吞掉诊断信息。

## 11. 自绘图与图表合同

### CHART-01 集中取色

- QPainter、matplotlib 和 SVG 颜色必须从 token/palette adapter 获取。
- 页面和 widget 不再硬编码旧主题十六进制值。
- 报告 PDF 的颜色暂不迁移，不纳入 UI token 静态扫描。

### CHART-02 数值不可变

视觉迁移前后必须满足：

- 曲线 x/y 数据完全一致。
- 工作点、限值线、marker 位置完全一致。
- 坐标范围、单位、插值和判据完全一致。
- 只允许颜色、线宽、网格透明度、字体和背景改变。

任何 widget 在 UI 层重新推导工作点或安全值都属于 blocker。

### CHART-03 云瓷图表色

- 背景：透明或 `surface_glass_soft`，由父卡片透出。
- 网格：`line_structural`，alpha 0.45–0.65。
- 主曲线：accent。
- 第二曲线：secondary。
- 安全/目标：success 或 secondary，必须配图例。
- 失败/超限：fail。
- 文本：ink_primary/ink_muted。

## 12. 计算与数据不可回归合同

这是视觉项目的发布阻断条件。

### SAFE-01 文件边界

- 实施阶段默认禁止修改 `core/**`。
- 若视觉实现暴露 core bug，停止视觉任务，另开诊断/修复任务，不得在本分支顺手修公式。
- `app/ui/report_pdf*.py` 和报告内容默认不改。

### SAFE-02 payload

七个模块的默认、样例和主要 mode 在实施前后 `_build_payload()` 深度相等；允许差异仅限明确批准的非计算 UI metadata，且 calculator 不消费。

### SAFE-03 结果

对同一 payload，calculator JSON 结果做规范化深比较：

- 数值、状态、messages、warnings、model scope 不变。
- 不因视觉层改变浮点格式或单位换算。
- 不新增 UI 派生的判据字段。

### SAFE-04 报告

同一结果的 `_build_report_lines()` 逐行一致；PDF/DOCX/TXT 的总体状态、分项状态、关键数值、警告和未校核项一致。

### SAFE-05 行为

必须保持：

- 页面懒加载。
- mode 驱动字段锁定/显隐/payload。
- 输入变化使结果与导出失效。
- 保存/加载输入。
- 默认/测试案例加载。
- 计算异常与渲染异常保护。
- native dialog 行为。

## 13. 性能、DPI 与可访问性

### PERF-01 预算

- `apply_theme()` P95 不高于 15 ms。
- MainWindow 构造 P95 `<350 ms`，且相对冻结基线退化不超过 15%。
- 普通页面首次导航 P95 `<150 ms`。
- 云谱只在 resize/theme change 重绘，不使用 timer。
- 滚动页面时不对每个字段做 blur/shadow offscreen composition。

### DPI-01 支持矩阵

- 尺寸：`1180×720`、`1400×860`、`1600×1000`。
- Windows：100%、125%、150%、200%。
- macOS：标准 Retina 与缩放显示。
- 所有尺寸下无关键截字、非内容水平滚动、隐藏主操作或裁切 popup。

### A11Y-01

- 所有交互控件有 visible focus。
- icon-only hit area ≥28 px。
- 状态有文字/图形，不只靠颜色。
- 对比度：正文目标 ≥4.5:1，大字/非文本关键轮廓 ≥3:1。
- `ink_quiet` 只用于非关键装饰或同时有更清晰主标签的辅助信息；任何独立承载含义的文字至少使用 `ink_muted`。
- Tab 顺序与阅读顺序一致。
- 200% 缩放下能通过滚动访问全部内容。

## 14. 视觉一致性验收

### 14.1 对比对象

权威目标为 HTML 中 `.window` 区域的 cloud 主题，不包括浏览器 review header 和下方说明卡。

Qt 截图对比需裁掉 OS 原生标题栏，以 central widget 为统一边界。

### 14.2 容差

- 主 token 实色：与 spec 色值完全一致。
- 合成玻璃色：取 5 个固定采样点，目标与 Qt 截图 ΔE2000 ≤3；抗锯齿边缘 ≤5。
- 主要几何：1400×860 下边距/间距/圆角/控件高度误差 ≤2 px。
- 1180×720 与高 DPI 下误差可按缩放后 ≤3 device-independent px。
- 文本基线和 icon optical center：标注截图偏差 ≤2 px。
- 阴影和云谱由人工前景 review 判定，不使用不稳定的整图二进制 golden 作为唯一 gate。

### 14.3 必拍截图

1. 主窗口空/初始状态，1180×720、1400×860。
2. 七个模块输入页，1400×860。
3. 七个模块结果页，至少覆盖 pass/fail/incomplete/reference_only。
4. 输入 normal/focus/error/read-only/auto-filled/disabled 组件板。
5. 主/次/disabled 按钮和 overflow。
6. Combo popup、QMenu、HelpPopover、BeginnerGuideDialog、QMessageBox。
7. 自绘图、buffer 曲线、worm matplotlib 曲线。
8. macOS Retina 前景；Windows 100/125/150% 前景。

## 15. 验收矩阵

| 证据 | 自动 | macOS 前景 | Windows 前景 |
|---|---:|---:|---:|
| token/QSS 结构 | 必须 | - | - |
| 圆角角点/背景漏色 | 像素预检 | 必须 | 必须 |
| 1180×720 几何 | 必须 | 必须 | 必须 |
| hover/focus/pressed | 状态测试 | 必须 | 必须 |
| popup/菜单/对话框 | smoke | 必须 | 必须 |
| 七模块 calculate | 必须 | 必须 | smoke 必须 |
| payload/result/report equality | 必须 | - | - |
| stale/export disable | 必须 | 必须 | smoke 必须 |
| render failure cleanup | 必须 | smoke | - |
| 自绘图数据位置 | 必须 | 必须 | smoke |
| 性能预算 | 必须 | 观察 | 必须 |

## 16. Definition of Done

只有同时满足以下条件，才可声称“达到云瓷 HTML 渲染效果”：

1. 用户确认 1400×860 的 shell、输入页、结果页和 popup 前景截图。
2. 云瓷 token、几何和主要状态满足本 spec 容差。
3. 七个模块都完成输入页与结果页检查，不以首个螺栓页面代表全软件。
4. macOS 前景通过；Windows 100/125/150% 至少完成正式 smoke。
5. 所有 payload、calculator result、report lines 保持冻结基线一致。
6. pass/fail/incomplete/not_checked/reference_only/stale/render-error 均有独立正确视觉。
7. 输入变化、渲染失败和加载/清空不会留下旧成功结果或可导出状态。
8. 自绘图和 matplotlib 只改变视觉，不改变数据、限值、工作点或判定。
9. 相关测试和全量测试通过，没有放宽旧断言来迁就视觉改动。
10. MainWindow、页面导航和滚动满足性能预算。
11. 无未经批准的 `core/`、报告内容、帮助工程结论或保存格式改动。
12. 最终 diff 只包含批准的视觉系统范围，并保留工作区原有无关改动。

任何仅有 HTML 截图、QSS 色值、offscreen 测试或单页演示的结果，都只能标记为 `PARTIAL / NEEDS FOREGROUND ACCEPTANCE`，不得标记完成。
