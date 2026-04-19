# UI Engineer — 经验教训

> 每次修复错误后，将教训追加到此文件。Agent 启动时必须先读取本文件。

<!-- 格式：
## YYYY-MM-DD 简短标题
- **错误**: 描述犯了什么错
- **正确做法**: 应该怎么做
- **原因**: 为什么这样做是对的
-->

## 2026-04-16 联动回调必须尊重 mode 权威性

- **错误**：`_on_material_changed` 为通过测试，在 material="自定义" 时**无条件**解锁 E/ν/屈服强度三个字段（去掉 `MODE_MAP == "combined"` 判断）。结果：加载 mode=仅花键 + material=自定义 的 JSON 时，三个字段变 SubCard 而其余 smooth_* 仍 AutoCalcCard，视觉不一致。
- **正确做法**：联动回调（material、load_condition 等）解锁字段时**必须按当前 mode 决定锁定状态** —— `self._set_card_disabled(fid, not is_combined)`，把 mode 作为权威状态。测试若强制无条件解锁，需改测试在正确 mode 下运行，而不是改实现。
- **原因**：mode 是页面最上层的状态变量，所有子回调必须遵循 mode。`_sync_state_from_ui` 先 `_on_mode_changed` 再 `_on_material_changed`，后者若不尊重 mode 会覆盖掉前者的锁定结果。

## 2026-04-16 live feedback 要写多个消息通道

- **错误**：`_display_result` 只调 `self.set_info()`（写 header 区），不写结果页的 `message_box`（QPlainTextEdit）。用户在结果页滚动时看不到告警，测试 `page.message_box.toPlainText() != ""` 直接失败。
- **正确做法**：结果展示涉及的所有消息通道（header info_label + 结果页 message_box）都要同步写入。成功路径也应写"校核完成"避免消息框显得"卡住"。
- **原因**：不同视觉位置的消息通道服务不同场景（header 常驻 / message_box 结果页专属），一处缺失就会让用户误判状态未更新。

## 2026-04-16 侧栏/标题命名要与页面头部一致

- **错误**：`main_window.py` 侧栏用"花键过盈配合"，但页面内部头部 + disclaimer 都用"花键连接校核"。导致用户侧栏选一个名字、点进去显示另一个名字，测试 `test_main_window_uses_connection_check_name_for_spline_module` 失败。
- **正确做法**：模块命名在所有入口（main_window 侧栏、页面头部、文档）保持一致；改名时搜索全仓所有字面量。
- **原因**：用户体验一致性 + 命名断言测试会直接失败。

## 2026-04-18 核心新增返回字段后，UI 消费层必须独立走通一次

- **错误**：赫兹模块 H-01 修复时 core 把 `contact_area_mm2` 放在 `result["contact"]` 子字典下（层级对称、合理），UI `_render_result` 与 `_build_report_lines` 却直接写成 `result["contact_area_mm2"]`。核心测试全绿，UI 默认样例点"执行校核"必抛 `KeyError: 'contact_area_mm2'`，模块整整两周不可用。
- **正确做法**：core 返回结构新增/修改字段后，UI 侧必须做两件事：(1) 逐字对照 core 返回层级（`result["<section>"]["<key>"]`），禁止凭印象写顶层 key；(2) 提交前在 `.venv` 下跑一次 `QT_QPA_PLATFORM=offscreen python -c "page=XxxPage(); page._calculate()"` 最小 smoke，确认不抛异常且 `metrics_text` 展示目标字段。涉及报告导出的还要多跑一次 `page._build_report_lines()`。
- **原因**：core 的字段测试只能锁住"字段存在/数值正确"，UI 测试才能锁住"字段被正确访问/被展示"。两者是独立防线，缺一就会出现"核心补了但按钮不能点"的部分闭环。

## 2026-04-18 _calculate 的 try/except 必须包到渲染与报告终点

- **错误**：`hertz_contact_page._calculate()` 只把 `_build_payload` + `calculate_xxx` 放在 try/except 里，`_render_result` 抛的 KeyError 直接冒泡给 Qt 事件循环，用户看到的不是"输入参数错误"弹窗，而是"按钮点击无反应/界面卡住"的静默崩溃。
- **正确做法**：UI 的 execute-handler 必须把"核心计算 + 状态保存 + 渲染结果 + 状态反馈" 整段纳入异常保护，`except Exception` 分支里同时 `QMessageBox.critical` + `self.set_info`，让消费链任何一环断裂都能明确告诉用户。参考螺栓页已有模式。
- **原因**：渲染失败 ≠ 计算失败，但对用户而言都是"按了按钮没反应"；UI 必须对消费链断裂有兜底，否则 bug 会以"模块看起来坏掉"的形式出现，用户无法区分是自己输错了还是程序问题。

## 2026-04-18 输入变更后必须禁用导出按钮直至重新计算（从 CLAUDE.md 迁移）

- **错误**：赫兹/螺栓早期版本里，用户点"执行校核"→"导出报告"后，如果改了任意输入字段再点导出，PDF 写出的是**旧结果** + **新输入字段显示**，两者不一致但用户无法察觉。轴向受力螺纹连接模块已修这个问题（CLAUDE.md"任意输入变更、加载输入、清空页面后，导出报告按钮会立即失效"），但其他模块仍需对齐。
- **正确做法**：所有 input widget（`QLineEdit.textChanged` / `QComboBox.currentTextChanged`）连到通用 slot 执行 `self.btn_save.setEnabled(False)` + `self.btn_save_pdf.setEnabled(False)`；`_calculate` 成功结束时 `setEnabled(True)`；`_clear()` / `_apply_input_data()`（加载条件）也要 disable。模板参考 `bolt_tapped_axial_joint_page.py`。
- **原因**：报告与当前输入的一致性是工程决策的基础。UI 的默认行为（按钮永远可点）在这个场景下是陷阱；显式 disable 是最便宜也最可靠的防线。

## 2026-04-18 QPlainTextEdit Expanding sizePolicy 会压扁同列 SubCard

- **错误**: Load Capacity 章节的 `_lc_params_card`（SubCard）和 `badges_card`（SubCard）在运行时被压缩到几乎不可见；所有 badge 叠在同一 y 坐标。根因是同一 QVBoxLayout 里 `QPlainTextEdit` 默认垂直 sizePolicy 为 `Expanding`，加上 `addStretch(1)`，两者共同吃掉所有剩余高度，把默认 `Preferred` 的 SubCard 挤压到接近零。这个问题多次被用户指出，历次"修复"（改内外 margins / spacing）都没有触及根因。
- **正确做法**: 两步并施：(1) 把 `QPlainTextEdit` 的垂直 sizePolicy 从默认 `Expanding` 改为 `Preferred`（`setSizePolicy(Expanding, Preferred)`）；(2) 把被压缩的卡片（`_lc_params_card`、`badges_card`）的垂直 sizePolicy 改为 `Minimum`（`setSizePolicy(Preferred, Minimum)`），确保它们始终按自身内容高度展示，不被 stretch 挤掉。
- **原因**: `QVBoxLayout` 按 sizePolicy 分配空间；`Expanding` > `Preferred` > `Minimum`。只有把文本框降为 `Preferred` 且把卡片提升为 `Minimum`，布局才会保证卡片完整展示后再把剩余空间给文本框。用 `setMinimumHeight` 只能救文本框自身，不能救同列其他控件。

## 2026-04-18 sizePolicy 补丁不能替代 QScrollArea（viewport 高度不足时的结构性修复）

- **错误**: Load Capacity 章节内容超出 viewport 时，用 `setSizePolicy(Minimum)` + `setSizePolicy(Preferred)` 给卡片和 QPlainTextEdit 打补丁。headless 测试通过（默认窗口较大），真实小窗口（700-800px）下仍失败。原因：`QSizePolicy.Minimum` 的语义是"不能小于 minimumSize"，而默认 minimumSize=0，Qt 仍然允许把它压到 0；补丁不改变 QVBoxLayout 的分配逻辑。
- **正确做法**: 内容丰富、高度超出典型 viewport 的章节页，必须用 QScrollArea 包裹 content widget，并传 scroll area 给 `add_chapter()`。内部 layout 不需要任何 sizePolicy 修改——ScrollArea 内的内容不受 viewport 约束，始终按自身 sizeHint 展示；viewport 不足时用户通过滚动访问剩余内容。
- **原因**: QVBoxLayout 的空间分配只能在"可用高度"范围内进行。可用高度 < 内容 sizeHint 时，布局会按 sizePolicy 优先级压缩各子控件；无论哪个子控件被标为 Minimum，只要 minimumSize=0，它都可能被压到 0。QScrollArea 从根本上把"可用高度"从 viewport 高度解耦，content widget 的可用高度变为无限，各子控件按自然尺寸排列。测试验证策略：必须用小 viewport (800x600) + `page.show()` + `processEvents()` 后检查 sizeHint；仅用大窗口或不 show() 会掩盖问题。

## 2026-04-18 `_build_payload` 必须按 mode 收敛（从 CLAUDE.md 迁移）

- **错误**：花键页有"仅花键"/"组合"两种 mode，早期 `_build_payload` 在"仅花键"模式下仍把 `smooth_*`（光轴过盈段）字段写入 payload；calculator 收到无关字段后或触发 `_require` 异常，或进入错误分支。CLAUDE.md 里明确记录"`_build_payload` 在'仅花键'模式下不再向 calculator 传递 smooth_* 段"正是这条教训的落地。
- **正确做法**：`_build_payload` 顶部先读 mode（`self._mode_field_id` 或 `self._mode`），按 mode 白名单过滤要纳入 payload 的 section key；不属于当前 mode 的字段即使在 UI 上有值也不传。等价原则：UI 上当前 mode 已锁定（AutoCalcCard）/ 已隐藏的字段，其值不应进 payload。
- **原因**：calculator 的输入契约按 mode 分化。UI 不按 mode 裁剪 payload = 把"UI 上不可见的垃圾值"混入计算。这是 mode 权威性（2026-04-16 条）在 payload 构建侧的直接延伸，违反会产生"UI 看起来对、计算走错分支"的隐蔽 bug。


## 2026-04-19 Qt widget 参数必须假定随时可能已销毁（HelpPopover.show_for）

- **错误**: `HelpPopover.show_for(help_ref, anchor)` 直接连续调用 `anchor.window()` / `anchor.rect()` / `anchor.mapToGlobal()` / `anchor.screen()` 来做定位，没有探测 anchor 对应的 C++ 对象是否还在。父页面关闭 / 信号延迟触发 / 快速连点等正常使用路径下，anchor 底层 C++ 对象已被销毁但 Python wrapper 还在，任何属性访问都会抛 `RuntimeError: Internal C++ object already deleted`。codex 对抗评审一把复现。
- **正确做法**: 入口写一个 `_anchor_is_valid(widget) -> bool` 探针，用 `widget.objectName()` 这种无副作用的访问套 `try/except RuntimeError`。valid 走原逻辑，invalid 降级到 `parent=None` + `QCursor.pos()` + `QApplication.primaryScreen().availableGeometry()`（primaryScreen 返回 None 时用 `QRect(0, 0, 1920, 1080)` 兜底），最后统一跑一遍屏幕边界翻转 clamp。同一弹窗单例本来就已经用 try/except 守住 `_current`，就必须把同样的纪律延伸到 anchor。
- **原因**: Qt 的 shiboken 把 C++ QObject 生命周期和 Python wrapper 生命周期解耦——父节点 deleteLater + processEvents 之后，Python 端仍持有"看起来存在"的对象引用，任何进入 C++ 层的方法都会抛。一旦你把一个 widget 参数暴露给 slot / classmethod / 延迟回调，就必须假设它在下一次属性访问前就没了；不探测 = 用户触发一次正常的"关页面后再点帮助"就能崩。测试用 `shiboken6.delete(parent)` 强制立刻销毁才能 offscreen 复现，`deleteLater()` + `processEvents()` 下 wrapper 还可能残留。

## 2026-04-19 新增 kwarg 绝不能偷换既有返回对象的类型契约（add_chapter wrapper）

- **错误**: `BaseChapterPage.add_chapter(page, *, help_ref=None)` 在 help_ref 非空时把用户传进来的 `page` 包进一层 wrapper QWidget 再塞进 `chapter_stack`，让 `chapter_stack.widget(i)` 在"加了 help_ref 后"突然变成返回 wrapper 而不是原 page。仅在 docstring 里写一句"callers 要自己注意"就认为够了——结果 `tests/ui/test_worm_page.py:900` 里 `chapter_stack.widget(5) is QScrollArea` 的断言一旦给 worm 章节加 help_ref 就会直接炸，而且没有任何静态工具能先发现这种字符串类型契约漂移。
- **正确做法**: 为新增行为提供**新的稳定 API**，不要侵蚀旧 API 的语义。做法：
  1. `__init__` 里维护 `self._chapter_pages: list[QWidget]`；
  2. `add_chapter` 两条分支都 append 原始 `page` 到这个 list（wrapper 只进 stack，不进 list）；
  3. 暴露 `chapter_page_at(i)`（始终返回原 page）和 `chapter_container_at(i)`（返回 stack 里那个，可能是 wrapper）；
  4. 立刻把现有直接调用 `chapter_stack.widget(i)` 的地方迁到 `chapter_page_at(i)`。
  docstring 只是提醒，新 API 才是约束。
- **原因**: 公共返回对象的类型 = 公共契约。偷偷换了类型，任何下游断言都是潜伏的定时炸弹，Stage N 加内容时炸、测试改 fixture 时炸、下一个开发者 copy-paste 时炸。"在 docstring 里警告" 只是把责任甩给未来读 docstring 的人——而这个人很可能不存在，或在赶下一个 Stage 时根本不会去读。修复原则：**扩展 API，不污染 API**。

## 2026-04-19 help_ref 重命名时必须同步 test wiring

- **错误**：Stage 1.5 重命名 `terms/pressure_angle` 为 `terms/gear_pressure_angle` 时，若只改 page.py 而忘了 `tests/ui/test_worm_help_wiring.py:EXPECTED_FIELD_HELP_REFS` 字典，测试会失败但错误信息是"断言失败"，不是"引用 md 不存在"，排查很绕。
- **正确做法**：修改 `FieldSpec.help_ref` 时，用 grep `help_ref=.*<old_name>` 找 page 引用，再 grep `<old_name>` 找 test 和 GUIDELINES master list，批量同步。每次重命名至少修 3 处：page.py、test_wiring.py、GUIDELINES §8.1。
- **原因**：help_ref 是"字段 → md 文件"的外键，但没有运行时外键检查（只有弱检查 fixture）。重命名必须当成一次"修数据库迁移"处理，不是纯本地重命名。
