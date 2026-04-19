# Code Reviewer — 经验教训

> 每次修复错误后，将教训追加到此文件。Agent 启动时必须先读取本文件。

<!-- 格式：
## YYYY-MM-DD 简短标题
- **错误**: 描述犯了什么错
- **正确做法**: 应该怎么做
- **原因**: 为什么这样做是对的
-->

## 2026-04-16 近似公式审查必须遍历全部样本

- **错误**：review 花键近似几何时若只看"test_approximation_aligns_with_catalog_w25x125 通过"就放行，会漏过对 m=1.75/2.0/2.5 的非保守事故。
- **正确做法**：工程公式 review 时亲手算一遍"在参数边界/极值的表现"——比如 catalog 里 h_w/m 最小/最大的条目。准备一份"边界样本表"作为 review checklist。
- **原因**：测试绿是自证样本满足，不等于全域正确。reviewer 必须带有"找反例"的姿态。

## 2026-04-16 数学等价字段在 UI 同时展示是 review 可拦截的误导

- **错误**：`torque_capacity_sf = T_cap/T_design` 在数学上恒等于 `flank_safety = p_zul/p_flank`，review 时若没深究两者代入公式会错过这一等价性，放任 UI 展示 "S=3.27, S_T=3.27" 两个看似独立的"安全系数"。
- **正确做法**：review 新增字段时，代入公式看它是否可化简为既有字段；若等价，要求只保留一个或明确标注 "≡" 等价关系。
- **原因**：工程结果的"数量" = 决策维度；两个数值同义却并列展示，会让工程师误判存在两个独立校核余量。

## 2026-04-16 测试断言放宽时 reviewer 要追问原因

- **错误**：PR 里把 `MATERIAL_AUTO_FILLED` 白名单从 4 项扩到 6 项，review 时若只看"测试 passed"就放行，掩盖了实现层面的 mode 权威性 bug。
- **正确做法**：review diff 里看到**测试断言放宽**（白名单扩张、阈值放宽、期望值更新）要立即追问 commit message："这是契约变化？还是掩盖缺陷？"。若 commit message 没说清，应要求补充。
- **原因**：测试是契约冻结态；review 最重要的防线之一是阻止"改测试让 bug 绿化"。

## 2026-04-16 独立 review 必不可少

- **错误**：本次 Round 1 完成后自我验证 394 tests all green 并声称完成，若未经独立 reviewer 介入会直接合并含 Critical 级非保守几何的代码。
- **正确做法**：重要修改（计算公式、API 契约、默认值）在合并前必须经过与实现者**独立**的 reviewer（其他 agent / 其他人），并按 Critical / Important / Nice-to-have 分级输出。
- **原因**：自验证天然有"测试是实现者写的 → 同时包含同一盲区"的盲点问题。独立 reviewer 提供正交视角。

## 2026-04-18 review 报告的修复建议必须挂进 plan/todo 跟踪

- **错误**：2026-04-03-hertz-worm-review.md 的 C-01 明确列出"新增 Hertz UI 测试 / 报告测试包含接触面积 / 结果页边界展示测试"三条建议，但 2026-04-03-three-module-fix-plan.md 只承接了 "H1：calculator 添加 contact_area_mm2；UI 结果页展示" 这一条，其余建议被默默丢弃。后续修复只做了 core 层，UI/报告从未闭环，导致两周后默认样例"点击即崩"。
- **正确做法**：review 报告生成后立即把每条修复建议映射成 plan 条目（一条发现 → 一条任务），每条任务的"验收标准"必须包含"最小复现脚本跑一次"。plan 关闭前逐条勾验收，拒绝"核心补了就算完"的部分闭环。review 报告末尾应附"Agent 派遣计划"段落，明确每项由哪个 subagent 承接。
- **原因**：review 的价值等于 plan 的承接力。没挂进 plan/todo 的建议 = 没发现；挂了但没验收标准 = 执行者会自裁剪为"最小可交付"。

## 2026-04-18 模块级 review 必须跑一次端到端 smoke path

- **错误**：2026-04-03 对 Hertz 模块的 review 偏重静态审查 + core spot-check，没有执行"加载默认样例 → 点击执行校核 → 查看结果 → 导出报告" 5 秒级端到端路径。结果 H-01 遗留的 UI 字段路径错误（`result['contact_area_mm2']` 而非 `result['contact']['contact_area_mm2']`）潜伏至今，点击即 KeyError。
- **正确做法**：任何模块级 review 必须包含一次 headless 端到端 smoke：
  ```bash
  QT_QPA_PLATFORM=offscreen .venv/bin/python -c "
  from PySide6.QtWidgets import QApplication; import sys
  from app.ui.pages.<module>_page import <Module>Page
  app = QApplication.instance() or QApplication(sys.argv)
  page = <Module>Page(); page._calculate()
  print('ok:', page.metrics_text.text()[-200:])
  print('report:', page._build_report_lines()[-5:])
  "
  ```
  跑通=通过；抛异常=Critical 级发现，无论静态审查多干净都要立即拦下。
- **原因**：静态审查会漏掉"字段名拼错 / 层级写错 / 属性名换了但调用点没改"等只在运行态暴露的缺陷。这类 bug 在 Qt 应用里会表现为"按钮点了没反应"，用户无法判断是自己输错还是程序问题。5 秒 smoke 是最便宜的屏障，比补任何测试都快。


## 2026-04-19 "docstring 警告" 不是修复——要看新 API 是否真正替换了旧调用（add_chapter wrapper）

- **错误**: review `add_chapter(*, help_ref=None)` 时只看到"新增了 help_ref，docstring 里警告了 `chapter_stack.widget(i)` 返回 wrapper 而非 page"，就判定"已说明"放行。实际这是一个公共 API 类型契约漂移：下游任何 `chapter_stack.widget(i) is <Page>` 断言都会在下游加 help_ref 的当下炸掉，docstring 永远拦不住未来读者。codex 对抗评审立刻识别 `tests/ui/test_worm_page.py:900` 会被 Stage 1 破坏。
- **正确做法**: 凡遇到"新增 kwarg / 新行为分支 悄悄改变既有公共返回对象或返回类型"的 diff，必须强制作者提供**新稳定 API**并**迁移所有既有直接调用**，仅更新 docstring 不接受。review 里要主动跑：
  ```bash
  Grep chapter_stack\.widget  # 或等价的"旧 API 直接用法"
  ```
  把命中清单贴进反馈；如果作者只留 docstring 没改命中点，就标 P0 blocker。判例：公共属性 / 返回对象类型 / 对象身份（`is` 断言会用到的） 属于契约；只加 docstring = P0 未修。
- **原因**: docstring 是软约束，类型/身份契约是硬约束。评审拿软约束代替硬约束，相当于把未来的回归风险贴在条款外壳上说"已告知"，用户实际体验是"某个 Stage 突然一堆测试炸"。评审的职责是**现在拦下契约漂移**，不是**备案未来的爆点**。一次 grep + 一次 blocker 标记的成本，远低于下游一个 Stage 踩坑后回滚。

## 2026-04-19 Qt widget 参数的生命周期风险要作为必检项（show_for 的 anchor）

- **错误**: review `HelpPopover.show_for(help_ref, anchor)` 时注意到作者已经用 try/except 守住了 `_current` 单例的野引用，就默认作者"已经想过销毁路径"，没追问同一个 classmethod 里对 `anchor.window() / rect() / mapToGlobal() / screen()` 这几行是否也有保护。结果 anchor 被销毁后任一访问都抛 `RuntimeError: Internal C++ object already deleted`，正常使用路径（关页面后再点帮助）直接崩。
- **正确做法**: 看到任何 Qt classmethod / slot / 延迟回调接收 `QWidget` 参数，review checklist 固定一条：**该 widget 参数的每一次属性/方法访问，是否对 `RuntimeError` 免疫，或在入口处做过有效性探测？** 如果不是，标 P0。建议作者统一用 `_widget_is_valid(w)` 探针 + 无效时降级到 `QCursor.pos()` + `QApplication.primaryScreen()`，而不是在多个访问点都套 try/except。探针写法：
  ```python
  def _widget_is_valid(w: QWidget) -> bool:
      try:
          _ = w.objectName()   # 无副作用
          return True
      except RuntimeError:
          return False
  ```
- **原因**: Qt 的 shiboken 生命周期机制使"Python wrapper 存在但 C++ 对象已销毁"成为正常态，不是罕见角落。作者如果对 `_current` 这类局部成员写了 try/except，却没对参数 widget 写，就是"防了内部、没防入参"的不对称防御——逻辑上等于漏防。review 必须主动识别这种不对称，否则 P0 crash 会滑过静态审查（spec 对、质量审查都不触发运行态）。

## 2026-04-19 二次 review 不是形式，会抓修复时新弄出的 P0

- **错误**：Stage 1.5 修 P0-D（降低 DIN 3996 合规口径）时，加了 "Cannot verify against original DIN standard"，但文末参考文献里保留了 `DIN 3996:2019 §5（Method B）及附录...` 的精确条号，Cannot verify 与精确引用共存自相矛盾。主会话修完没发现。
- **正确做法**：plan §1.5.3 要求"P0 > 3 条触发二次 review"不是形式主义。每修一条 P0 都有可能顺手违反另一条规则；二次 review 的职责就是抓这种"修这个又弄坏那个"。二次 review 时对 round 1 每条 P0 必须给 PASS / PARTIAL / FAIL 判定而不是笼统说"看起来 ok"。
- **原因**：修复 P0 的过程本质是"改变文档约束"，任何约束改变都可能触发其他文档的一致性问题；只有真正交叉核对每一条修复的 side effect 才能发现。单轮 review 无法覆盖。

## 2026-04-19 review 子代理回传内容必须主会话落盘

- **错误**：Stage 1.5 第一次调用 `codex:codex-rescue` 时，子代理在完成后因工作区权限问题无法写 `docs/reports/*.md`，只在返回消息里给了 200 字摘要，导致完整报告差点丢失。
- **正确做法**：review 类 agent 调用时，**主会话** 负责落盘报告文件；子代理 prompt 里要求"把完整报告原文贴回到返回消息中"，主会话拿到后用 Write 工具写入 `docs/reports/*.md`。不要相信子代理能写入共享工作区。
- **原因**：子代理的工作目录 / 权限上下文可能与主会话不同，文件系统写入的成功不是子代理能保证的契约。主会话才是唯一对 repo 有"稳定可写权限"的一方。
