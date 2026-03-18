# 过盈配合缺口收敛实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正当前 `DIN 7190` 过盈配合模块在结论可信度上的缺口，并补上本轮仍在范围内、且最有工程价值的 `eAssistant` 对齐能力：配合/公差选择、装配流程、重复载荷/微动腐蚀校核，以及报告可追溯性。

**Architecture:** 继续以现有 `core/interference/calculator.py` 作为圆柱面过盈的主求解器，但把它的通过/不通过语义收紧并提升可追溯性。围绕它新增职责单一的辅助模块来承载配合搜索和装配计算，避免把更多隐性逻辑继续堆进页面类中。维持当前模型边界：`solid shaft + thick-walled hub + linear elastic + constant friction`。

**Tech Stack:** Python 3、PySide6、`unittest`、项目内 Markdown 文档。

---

## 范围边界

- 本轮纳入范围：
  - 防滑安全系数 / 需求过盈量语义修正
  - 扭矩 + 轴向力联合作用评估
  - UI 中“虚参数”和纯绘图参数的语义清理
  - ISO 286 配合/公差流程
  - `shrink-fit` / `force-fit` 装配流程
  - 带适用性前提的 repeated-load / fretting-corrosion 校核
  - 报告与输入来源追溯
- 本轮不纳入范围：
  - `centrifugal force`
  - `stepped hub geometry`
  - 基于 FEM 的局部边缘应力细化

## 文件映射

- Modify: `core/interference/calculator.py`
  - 保持其作为 `DIN 7190` 圆柱面过盈主求解器的角色，并继续输出统一结果 schema。
- Create: `core/interference/fit_selection.py`
  - 封装 ISO 286 配合/公差搜索，以及人工偏差到 `delta_min/delta_max` 的换算。
- Create: `core/interference/assembly.py`
  - 封装 `shrink-fit` / `force-fit` 的装配计算与来源表格。
- Modify: `core/interference/__init__.py`
  - 重新导出 UI / tests 需要共享的新 helper。
- Modify: `app/ui/pages/interference_fit_page.py`
  - 新增工作流章节、显式展示真实语义，并清理误导性标签。
- Modify: `app/ui/report_export.py`
  - 仅在共享报告布局需要扩展追溯区块时修改。
- Modify: `examples/interference_case_01.json`
- Modify: `examples/interference_case_02.json`
- Create or modify: 其他需要补充的 interference-fit 示例文件。
- Modify: `tests/core/interference/test_calculator.py`
- Create: `tests/core/interference/test_fit_selection.py`
- Create: `tests/core/interference/test_assembly.py`
- Modify: `tests/ui/test_interference_page.py`
- Modify: `README.md`
- Modify: `docs/references/2026-03-05-interference-roughness-sources.md`
  - 补充或交叉引用新增、且有来源依据的假设说明。

## Chunk 1: 先修正确性

### Task 1: 修正需求过盈语义和联合作用判定

**Files:**
- Modify: `core/interference/calculator.py`
- Modify: `tests/core/interference/test_calculator.py`

- [ ] **Step 1: 先补会失败的测试，覆盖缺失的防滑安全系数耦合**

  新增针对性测试，证明 `checks.slip_safety_min` 增大时会同步提高：
  - required pressure
  - required interference
  - fit-window verdict

  至少加入一个类似这样的回归用例：

  ```python
  def test_slip_safety_factor_increases_delta_required() -> None:
      ...
      assert result_high["required"]["delta_required_um"] > result_low["required"]["delta_required_um"]
  ```

- [ ] **Step 2: 再补一个会失败的测试，覆盖扭矩 + 轴向力联合作用**

  构造一个工况，使得：
  - `torque_ok is True`
  - `axial_ok is True`
  - 但联合作用利用率必须失败

  然后断言：一旦 combined slip 超限，`overall_pass` 也必须失败。

- [ ] **Step 3: 运行定向 calculator 测试并确认它们先失败**

  Run: `python3 -m unittest tests.core.interference.test_calculator -v`

  Expected:
  - 新增测试失败
  - 现有 interference 测试仍然能跑完

- [ ] **Step 4: 更新 calculator 语义**

  在 `core/interference/calculator.py` 中：
  - 把 `slip_safety_min` 正式折算进 demand-side pressure / interference derivation
  - 把 combined torque + axial evaluation 明确体现在 `checks` 中
  - 把 combined check 纳入 `overall_pass`
  - 避免保留会与主结论相矛盾、且偏乐观的辅助结果

- [ ] **Step 5: 收紧结果 schema 的命名**

  重命名或拆分有歧义的结果字段，让输出能明确区分：
  - transmission requirement
  - gaping requirement
  - final required interference
  - fit-window coverage status

  如果一次性重命名会让 UI 改动过大，本任务先保留一轮 backward-compatible aliases，后续再移除。

- [ ] **Step 6: 重新运行 calculator 测试**

  Run: `python3 -m unittest tests.core.interference.test_calculator -v`

  Expected:
  - 所有 interference calculator 测试通过

### Task 2: 让 UI 语义与真实求解器保持一致

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 先补会失败的 UI / report 测试，锁定新的结果语义**

  新增断言，覆盖：
  - combined-load status 必须可见
  - fit-window / result semantics 的文案必须更准确
  - 纯绘图参数 / 自动填充参数必须被更诚实地标识

- [ ] **Step 2: 更新页面 badge 集合和结论摘要**

  让结果区显式展示：
  - combined slip verdict
  - demand-side breakdown
  - material/profile selectors 是 preset helpers 的说明

- [ ] **Step 3: 移动或重命名纯绘图控制项**

  `options.curve_points` 必须看起来是 plotting option，而不是 safety input。

- [ ] **Step 4: 重新运行 interference page 测试**

  Run: `python3 -m unittest tests.ui.test_interference_page -v`

  Expected:
  - 所有 UI 测试通过

## Chunk 2: 配合选择与装配流程

### Task 3: 增加 ISO 286 配合/公差流程

**Files:**
- Create: `core/interference/fit_selection.py`
- Create: `tests/core/interference/test_fit_selection.py`
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `tests/ui/test_interference_page.py`
- Modify: `examples/interference_case_01.json`
- Modify: `examples/interference_case_02.json`

- [ ] **Step 1: 先定义最小可行的 tolerance workflow**

  支持两种模式：
  - manual `delta_min/delta_max`
  - tolerance-derived `delta_min/delta_max`

  不要一开始就做一个很重的通用 dialog。先落一个稳定、可测试的核心：
  - nominal diameter
  - hub tolerance field 或 user-defined deviations
  - shaft tolerance field 或 user-defined deviations
  - 计算后的 `delta_min/delta_max`

- [ ] **Step 2: 先写会失败的核心测试，覆盖偏差到过盈量的换算**

  覆盖以下场景：
  - 直接输入 user-defined deviations
  - 一个有代表性的 ISO 286 preferred fit 示例
  - 无法形成 interference fit 的非法组合

- [ ] **Step 3: 实现核心 helper**

  在 `core/interference/fit_selection.py` 中：
  - 保持换算逻辑与 UI 解耦
  - 返回一个带追溯信息的结构，至少包含：
    - selected mode
    - tolerance names 或 manual deviations
    - `delta_min_um`
    - `delta_max_um`
    - warning text（如果有）

- [ ] **Step 4: 把 helper 接进页面**

  更新页面，让用户可选择：
  - `"manual interference"`
  - `"fit/tolerance selection"`

  但 calculator 最终仍只接收 `delta_min_um` 和 `delta_max_um`。

- [ ] **Step 5: 在报告里补上 fit source trace**

  报告 / 结果区必须能说清楚当前 interference range 来自：
  - manual entry
  - selected fit
  - user-defined deviations

- [ ] **Step 6: 运行测试**

  Run:
  - `python3 -m unittest tests.core.interference.test_fit_selection -v`
  - `python3 -m unittest tests.ui.test_interference_page -v`

### Task 4: 增加 `shrink-fit` / `force-fit` 装配流程

**Files:**
- Create: `core/interference/assembly.py`
- Create: `tests/core/interference/test_assembly.py`
- Modify: `core/interference/calculator.py`
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `tests/ui/test_interference_page.py`
- Modify: `README.md`

- [ ] **Step 1: 先定义 assembly inputs 和显式模式**

  增加一个 assembly 章节，至少包含：
  - `assembly.method`: `manual_only`, `shrink_fit`, `force_fit`
  - 共用的 source-trace fields

  对于 `shrink_fit`：
  - room temperature
  - shaft temperature
  - mating clearance rule 或 direct value
  - linear thermal expansion coefficients
  - maximum permissible hub joining temperature（如果可得）

  对于 `force_fit`：
  - press-in friction
  - press-out friction
  - 可选的 edge-length / bevel guidance text

- [ ] **Step 2: 先写会失败的 assembly helper 测试**

  覆盖：
  - shrink-fit required joining temperature 会随 required clearance 上升
  - force-fit pressing force 使用 max-pressure 侧
  - mode-specific report fields

- [ ] **Step 3: 实现 `core/interference/assembly.py`**

  让数学逻辑与页面解耦，至少包含：
  - shrink-fit joining temperature / cooling requirement
  - force-fit press-in / extraction force estimates
  - structured assumptions and warnings

- [ ] **Step 4: 把 assembly results 接到主结果 payload**

  主 calculator 结果里应新增 `assembly_detail` 区块，但不要把与 assembly mode 无关的 safety verdict 硬耦合进去。

- [ ] **Step 5: 更新 UI 和报告**

  页面 / 报告必须清楚展示：
  - shrink fits 的 required joining temperature
  - force fits 的 required pressing force
  - 哪个 friction coefficient 属于 service，哪个属于 assembly

- [ ] **Step 6: 运行测试**

  Run:
  - `python3 -m unittest tests.core.interference.test_assembly -v`
  - `python3 -m unittest tests.ui.test_interference_page -v`

## Chunk 3: 重复载荷、追溯与收尾

### Task 5: 增加带适用性保护的 repeated-load / fretting-corrosion 校核

**Files:**
- Modify: `core/interference/calculator.py`
- Modify: `tests/core/interference/test_calculator.py`
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 先补一个明确的 repeated-load input gate**

  不要默认假装这个校核永远适用。增加一个 switch 或 sub-mode，把它需要的适用性输入显式收进来。

- [ ] **Step 2: 先写会失败的适用性处理测试**

  覆盖：
  - 一个有效 repeated-load case，结果可确定
  - 一个不支持的 geometry / condition，返回 warning 而不是 fake pass

- [ ] **Step 3: 实现 repeated-load result block**

  输出必须区分：
  - 该校核是否 applicable
  - repeated load 下计算得到的 maximum transferable torque
  - 是否存在 fretting risk

- [ ] **Step 4: 在 UI / messages 中反映这个结果**

  把它展示为一个带 applicability notes 的 advanced result，而不是无条件并入基础 `DIN` verdict。

- [ ] **Step 5: 运行测试**

  Run:
  - `python3 -m unittest tests.core.interference.test_calculator -v`
  - `python3 -m unittest tests.ui.test_interference_page -v`

### Task 6: 让报告和保存输入具备可追溯性

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `app/ui/input_condition_store.py`
- Modify: `README.md`
- Modify: `examples/interference_case_01.json`
- Modify: `examples/interference_case_02.json`

- [ ] **Step 1: 在保存输入中保留 selection metadata**

  Saved inputs 需要保留：
  - material preset names
  - roughness profile source
  - fit-selection mode 与 chosen tolerance fields
  - assembly mode 与来源值

- [ ] **Step 2: 扩展报告章节**

  新增报告区块，覆盖：
  - input-source traceability
  - explicit model assumptions
  - explicit exclusions（`centrifugal force`, `stepped hub geometry`）

- [ ] **Step 3: 更新 examples**

  刷新示例，至少保证一个 sample 覆盖：
  - tolerance-derived interference
  - 一种 assembly mode
  - 一条可追溯的 preset path

- [ ] **Step 4: 重新运行 save/load 与报告相关 UI 测试**

  Run: `python3 -m unittest tests.ui.test_interference_page tests.ui.test_input_condition_store -v`

### Task 7: 最终验证与交接

**Files:**
- Modify only as needed based on failures

- [ ] **Step 1: 运行聚焦后的 interference suite**

  Run:
  - `python3 -m unittest tests.core.interference.test_calculator tests.core.interference.test_fit_selection tests.core.interference.test_assembly tests.ui.test_interference_page tests.ui.test_input_condition_store -v`

- [ ] **Step 2: 运行相邻模块回归**

  Run:
  - `python3 -m unittest tests.core.bolt.test_calculator tests.core.hertz.test_calculator tests.core.worm.test_calculator tests.ui.test_worm_page -v`

  Goal:
  - 确认 interference 相关改动没有破坏相邻模块

- [ ] **Step 3: 更新 planning files**

  Update:
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

  Record:
  - 最终交付了什么
  - 哪些项是有意 deferred 的
  - 还剩下哪些 residual risks

- [ ] **Step 4: 请求 code review**

  在实现整体变绿之后，使用 `superpowers:requesting-code-review`。

- [ ] **Step 5: 在宣称完成前做最终验证**

  在汇报成功前，使用 `superpowers:verification-before-completion`。
