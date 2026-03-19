# Interference-Fit Fretting Step Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在过盈配合模块内新增正式的“Step 5: Fretting 风险评估”增强模块，输出适用性、风险等级、驱动因素和建议，并保持其不进入基础 `overall_pass` verdict。

**Architecture:** 以现有 `core/interference/calculator.py` 中的 `repeated_load` 逻辑为基础，拆出职责单一的 fretting helper，避免继续把启发式规则堆在主求解器里。UI 层将把当前“高级校核”升级为正式 Step 5 章节，并在结果区/报告区新增独立 fretting 卡片，强调“增强结果，不改变基础 DIN 结论”。

**Tech Stack:** Python 3、PySide6、`pytest`/`unittest`、项目内 Markdown 文档。

---

## 范围边界

- 本轮纳入范围：
  - fretting Step 5 输入章节
  - fretting core helper
  - fretting 风险等级与建议
  - UI 结果展示与导出报告
  - legacy `advanced.repeated_load_mode` 到 `fretting.mode` 的兼容映射
- 本轮不纳入范围：
  - 独立通用 fretting 页面
  - 磨损寿命/累计损伤模型
  - 服役温度、离心力、空心轴等更大范围建模
  - fretting 进入 `overall_pass`

## 文件结构映射

- Create: `core/interference/fretting.py`
  - 承载 Step 5 的适用性判断、评分、风险等级、驱动因素和建议生成。
- Modify: `core/interference/calculator.py`
  - 解析 `fretting.*` 输入，调用 helper，输出新的 `fretting` 结果块；保留或瘦身旧 `repeated_load` 结构用于兼容。
- Modify: `core/interference/__init__.py`
  - 导出新的 fretting helper（如果 tests/UI 需要直接引用）。
- Modify: `app/ui/pages/interference_fit_page.py`
  - 新增 Step 5 章节、payload 映射、legacy load 映射、结果卡片和报告段落。
- Create: `tests/core/interference/test_fretting.py`
  - 纯 fretting helper 的规则与等级回归。
- Modify: `tests/core/interference/test_calculator.py`
  - 验证 fretting 集成结果、legacy 兼容和 `overall_pass` 不受影响。
- Modify: `tests/ui/test_interference_page.py`
  - 验证 fretting 字段、payload、结果、报告和 legacy UI 行为。
- Modify: `examples/interference_case_01.json`
  - 视需要加一个 fretting-enabled 示例。
- Modify: `README.md`
  - 补充 Step 5 fretting 的范围说明。
- Modify: `docs/review/2026-03-18-interference-fit-deep-review.md`
  - 只在需要交叉引用新计划时微调，否则可不改。

## Chunk 1: 先搭好 fretting core

### Task 1: 为 fretting helper 建立独立测试与输出 schema

**Files:**
- Create: `tests/core/interference/test_fretting.py`
- Reference: `docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md`

- [ ] **Step 1: 写第一个失败测试，锁定适用工况的最小输出结构**

  新增测试，传入一个满足当前简化假设的 context，断言 helper 至少返回：
  - `enabled`
  - `applicable`
  - `risk_level`
  - `drivers`
  - `recommendations`
  - `confidence`

  示例断言：

  ```python
  def test_fretting_assessment_returns_structured_result_for_applicable_case() -> None:
      result = assess_fretting_risk(inputs, context)
      assert result["enabled"] is True
      assert result["applicable"] is True
      assert result["risk_level"] in {"low", "medium", "high"}
      assert isinstance(result["drivers"], list)
  ```

- [ ] **Step 2: 写第二个失败测试，锁定不适用工况返回 `not_applicable`**

  构造 `l_fit / d <= 0.25` 或存在弯矩的 case，断言：

  ```python
  assert result["applicable"] is False
  assert result["risk_level"] == "not_applicable"
  ```

- [ ] **Step 3: 写第三个失败测试，锁定风险等级随工况恶化单调上升**

  至少比较两组输入：
  - `steady + light + coated`
  - `reversing + heavy + dry`

  断言后者风险分更高，且风险等级不低于前者。

- [ ] **Step 4: 运行 fretting 定向测试并确认先失败**

  Run: `python3 -m pytest tests/core/interference/test_fretting.py -q`

  Expected:
  - 新测试失败
  - 错误集中在 helper 尚未实现

### Task 2: 实现 fretting helper

**Files:**
- Create: `core/interference/fretting.py`
- Modify: `core/interference/__init__.py`
- Test: `tests/core/interference/test_fretting.py`

- [ ] **Step 1: 创建 fretting helper 的输入/输出边界**

  在 `core/interference/fretting.py` 中定义单一入口，例如：

  ```python
  def assess_fretting_risk(
      fretting_input: dict[str, Any],
      context: dict[str, float | bool | str | None],
  ) -> dict[str, Any]:
      ...
  ```

  `context` 应只接收 Step 5 真正需要的值，避免直接把整个 calculator result 丢进去。

- [ ] **Step 2: 先实现 applicability gate**

  首版直接重用现有规则：
  - `l_fit / d > 0.25`
  - 模量差在允许范围内
  - 无 rotating bending

  不适用时：
  - `risk_level = "not_applicable"`
  - `confidence = "low"`
  - `notes` 里写明原因

- [ ] **Step 3: 实现规则评分与 risk level 映射**

  评分项至少覆盖：
  - torque/slip reserve
  - combined margin
  - load spectrum
  - duty severity
  - surface condition
  - importance level

  结果必须能稳定映射到：
  - `low`
  - `medium`
  - `high`

- [ ] **Step 4: 实现 drivers 与 recommendations 生成**

  让 helper 直接返回面向工程的原因和建议，而不是把这些逻辑塞回 UI。

- [ ] **Step 5: 导出 helper 并跑测试**

  Run: `python3 -m pytest tests/core/interference/test_fretting.py -q`

  Expected:
  - `test_fretting.py` 全部通过

## Chunk 2: 把 fretting 接回主 calculator

### Task 3: 在主 calculator 中集成 fretting，不改变基础 verdict

**Files:**
- Modify: `core/interference/calculator.py`
- Modify: `tests/core/interference/test_calculator.py`
- Reference: `core/interference/fretting.py`

- [ ] **Step 1: 写失败测试，锁定 fretting 结果会出现在 calculator 输出中**

  在 `tests/core/interference/test_calculator.py` 中新增断言：

  ```python
  result = calculate_interference_fit(data)
  assert "fretting" in result
  assert result["fretting"]["enabled"] is True
  ```

- [ ] **Step 2: 写失败测试，锁定 fretting 不影响 `overall_pass`**

  构造一个基础 verdict 通过、但 fretting 风险高的工况，断言：
  - `result["overall_pass"]` 保持原有语义
  - `result["fretting"]["risk_level"] == "high"`

- [ ] **Step 3: 写失败测试，锁定 legacy `advanced.repeated_load_mode` 仍可触发 fretting**

  兼容断言至少覆盖：
  - 新输入 `fretting.mode=on`
  - 旧输入 `advanced.repeated_load_mode=on`

  两者都能得到启用结果。

- [ ] **Step 4: 修改 calculator，接入 fretting helper**

  在 `core/interference/calculator.py`：
  - 读取新的 `fretting` section
  - 组装 helper 所需 context
  - 输出 `result["fretting"]`
  - 保持 `overall_pass` 不引用 fretting

  兼容策略：
  - 若显式给出 `fretting.mode`，优先用它
  - 否则回退读取 legacy `advanced.repeated_load_mode`

- [ ] **Step 5: 决定旧 `repeated_load` block 的兼容方式**

  首版推荐保留旧 block，但让它变成兼容别名/摘要，而不是继续承载主要语义。
  若保留：
  - 在注释中说明其为 legacy compatibility block
  - 让 UI 新逻辑优先读取 `fretting`

- [ ] **Step 6: 跑 interference core 测试**

  Run:
  - `python3 -m pytest tests/core/interference/test_fretting.py tests/core/interference/test_calculator.py -q`

  Expected:
  - 所有相关 core 测试通过

## Chunk 3: 升级页面与报告

### Task 4: 把“高级校核”升级成正式 Step 5 章节

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 写失败测试，锁定 Step 5 fretting 字段会出现在页面**

  至少覆盖：
  - `fretting.mode`
  - `fretting.load_spectrum`
  - `fretting.duty_severity`
  - `fretting.surface_condition`
  - `fretting.importance_level`

- [ ] **Step 2: 写失败测试，锁定 payload 使用新的 `fretting.*` section**

  断言 `_build_payload()` 会生成：

  ```python
  payload["fretting"] = {...}
  ```

- [ ] **Step 3: 更新页面章节定义**

  在 `CHAPTERS` 中：
  - 用正式的 `Fretting 风险评估` Step 5 替换旧“高级校核”
  - 为所有新字段提供 hint / tooltip / beginner guide

- [ ] **Step 4: 更新 payload 和 legacy load 映射**

  在 `_build_payload()` / `_apply_input_data()` 中：
  - 生成新 `fretting` section
  - 支持 legacy `advanced.repeated_load_mode` -> `fretting.mode`
  - 不要破坏既有 saved input 的加载

- [ ] **Step 5: 跑页面定向测试**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -q`

  Expected:
  - fretting 字段与 payload 测试通过

### Task 5: 在结果区和报告里新增 fretting 卡片

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 写失败测试，锁定报告中会出现 fretting 章节**

  至少断言报告 lines 中包含：
  - `Step 5 Fretting 风险评估`
  - risk level
  - applicability

- [ ] **Step 2: 写失败测试，锁定 fretting 不会伪装成基础 verdict**

  断言报告或页面文本中明确说明：
  - 这是增强结果
  - 不改变基础 pass/fail 结论

- [ ] **Step 3: 更新结果渲染**

  在 `_render_result()` 中增加 fretting card / text block，至少显示：
  - applicability
  - risk level
  - top drivers
  - recommendations
  - confidence / notes

- [ ] **Step 4: 更新 `_build_report_lines()`**

  在报告中新增独立段落：
  - `Step 5 Fretting 风险评估`
  - applicability
  - risk level
  - reasons
  - recommendations
  - note that it does not change `overall_pass`

- [ ] **Step 5: 跑 UI 测试**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -q`

  Expected:
  - 所有 UI tests 通过

## Chunk 4: 文档、示例与回归

### Task 6: 更新示例和 README

**Files:**
- Modify: `examples/interference_case_01.json`
- Modify: `README.md`

- [ ] **Step 1: 决定是否启用一个 fretting 示例**

  推荐：
  - `interference_case_01.json` 开启 fretting
  - 使用一组能输出清晰风险等级的输入

- [ ] **Step 2: 更新 README**

  明确写出：
  - fretting 是 Step 5 enhancement
  - 输出风险等级与建议
  - 不并入基础 DIN verdict

- [ ] **Step 3: 若示例变更，人工加载检查字段回显**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -q`

  Expected:
  - 示例加载相关用例仍通过

### Task 7: 做最终 interference 回归

**Files:**
- Test only

- [ ] **Step 1: 跑 interference 全量相关测试**

  Run:

  ```bash
  QT_QPA_PLATFORM=offscreen python3 -m pytest \
    tests/core/interference/test_fretting.py \
    tests/core/interference/test_calculator.py \
    tests/core/interference/test_fit_selection.py \
    tests/core/interference/test_assembly.py \
    tests/ui/test_interference_page.py -q
  ```

  Expected:
  - 全部通过

- [ ] **Step 2: 做一次针对 fretting 的人工 smoke 复核**

  人工检查至少 3 类工况：
  - disabled
  - applicable + low risk
  - applicable + high risk
  - not applicable

  确认：
  - risk level 符合预期
  - recommendations 不空泛
  - `overall_pass` 没被 fretting 改写

- [ ] **Step 3: 更新进度与审查文档**

  更新：
  - `progress.md`
  - `findings.md`
  - 如有必要，补充 `docs/review/2026-03-18-interference-fit-deep-review.md` 的 follow-up note

- [ ] **Step 4: Commit**

  ```bash
  git add core/interference app/ui/pages/interference_fit_page.py tests/core/interference tests/ui/test_interference_page.py README.md examples/interference_case_01.json progress.md findings.md task_plan.md docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md docs/superpowers/plans/2026-03-19-interference-fit-fretting-step.md
  git commit -m "feat: add interference-fit fretting risk step"
  ```

## Execution Notes

- 优先保持 fretting helper 的独立性，不要把评分和建议生成逻辑塞回 UI。
- 不要在首版里扩展到 service temperature / centrifugal / hollow-shaft；这些是后续阶段。
- 若 implementation 中发现当前 `repeated_load` block 过于混乱，可先抽 helper 再集成，但不要顺手做大规模无关重构。
- 所有用户可见文案保持中文；核心代码命名保持英文。

Plan complete and saved to `docs/superpowers/plans/2026-03-19-interference-fit-fretting-step.md`. Ready to execute?
