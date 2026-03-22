# 花键模块工程化整改 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前“花键过盈配合”模块从“可运行的简化估算”整改为“边界清晰的安全预校核工具”，并为后续升级到可追溯的 DIN 5480 / DIN 6892 风格工程校核链建立基础。

**Architecture:** 本计划分两层推进。第 1 层先做“立即去风险”整改：修正文案、暴露模型边界、补齐 UI/trace/输入校验，避免当前模块被误当成正式工程校核工具。第 2 层再做“标准化重构”：把场景 A 从 `m + z` 简化模型升级为基于参考直径/变位/标准尺寸的花键几何与强度链，并加入 benchmark 闭环。

**Tech Stack:** Python 3.12, PySide6, pytest, 现有 `core/spline` / `app/ui/pages/spline_fit_page.py` / `core/interference`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `core/spline/calculator.py` | 场景 A/B trace、warning 合并、输入验证、结果语义修正 |
| Modify | `core/spline/geometry.py` | 从“简化几何”过渡到“受控输入的标准几何”，或拆出新几何 helper |
| Modify | `core/spline/__init__.py` | 对外导出调整 |
| Modify | `app/ui/pages/spline_fit_page.py` | 模块命名、字段文案、材料联动、错误提示、结果展示 |
| Modify | `tests/core/spline/test_geometry.py` | 从自洽测试升级到标准样例/边界测试 |
| Modify | `tests/core/spline/test_calculator.py` | trace、warning、输入验证、benchmark fixture |
| Modify | `tests/ui/test_spline_fit_page.py` | 文案、联动、结果解释、模式显隐回归 |
| Modify | `docs/reports/2026-03-22-spline-interference-fit-module.md` | 标记为历史开发报告并补充“不适合作为正式校核”的结论 |
| Create | `docs/references/2026-03-22-spline-fit-sources.md` | 记录 DIN 5480 / DIN 6892 / 第三方工具 benchmark 来源 |
| Optional Create | `examples/spline_case_*.json` | benchmark / smoke cases |

## Execution Strategy

### Stage A: 立即去风险（推荐先执行）

目标：不改变模块大方向，但立刻消除“名称/文案/trace 过度承诺”问题，让当前版本最多只能被当作“简化预校核”使用。

### Stage B: 标准化重构（达到工程校核前的必经阶段）

目标：重建场景 A 的输入与几何链，逐步引入标准尺寸、载荷分布、更多失效模式和 benchmark 对齐。

---

## Chunk 1: Stage A — 安全边界与审计性修正

### Task 1: 先把错误承诺降下来

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py`
- Modify: `tests/ui/test_spline_fit_page.py`
- Modify: `docs/reports/2026-03-22-spline-interference-fit-module.md`

- [ ] **Step 1: 写失败测试，锁定新的模块语义**

  目标断言：
  - 页面标题/副标题不再把场景 A 叫作“过盈配合”
  - 场景 A 结果卡片明确写成“齿面平均承压（简化）”
  - 页面存在显式 disclaimer，说明“当前不用于 DIN 5480 正式工程校核”

- [ ] **Step 2: 运行测试确认当前实现失败**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 3: 修改 UI 文案与结果标题**

  具体要求：
  - 模块总标题改成“花键连接校核”
  - 场景 A 改成“花键齿面承压（简化）”
  - 场景 B 保持“光滑段圆柱过盈”
  - 在页面显眼位置加入 disclaimer：当前花键部分仅为简化平均承压估算，不替代 DIN 5480 / DIN 6892 工程校核

- [ ] **Step 4: 同步历史开发报告**

  具体要求：
  - 在开发报告头部补充“历史实现说明”
  - 明确注明场景 A 当前不能作为正式工程校核

- [ ] **Step 5: 回归测试**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 6: Commit**

  ```bash
  git add app/ui/pages/spline_fit_page.py tests/ui/test_spline_fit_page.py docs/reports/2026-03-22-spline-interference-fit-module.md
  git commit -m "fix(spline): clarify simplified scope and disclaim engineering limits"
  ```

### Task 2: 补齐 UI 真实行为与结果解释

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py`
- Modify: `core/spline/calculator.py`
- Modify: `tests/core/spline/test_calculator.py`
- Modify: `tests/ui/test_spline_fit_page.py`

- [ ] **Step 1: 写失败测试，覆盖当前 review 中确认的问题**

  目标断言：
  - `scenario_b.messages` 会并入顶层 `messages`
  - 选择轴/轮毂材料后，`E` 和 `nu` 会自动更新
  - `tooth_count` 非整数输入会报 `InputError`，不能静默截断
  - 如果继续保留 `KA` 先乘后委托，则结果 trace 不能显示成 `KA=1.0`

- [ ] **Step 2: 运行定向测试确认失败**

  Run: `python3 -m pytest tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 3: 实现计算层与 UI 修正**

  具体要求：
  - `calculate_spline_fit()` 合并场景 A/B warning，并保留来源标识
  - 对 `tooth_count` 做整数性校验
  - 为材料下拉添加 signal handler，真正填充 `E` 与 `nu`
  - 在 `scenario_b.trace` 中保留真实设计载荷或真实外层 `KA`

- [ ] **Step 4: 运行回归**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 5: Commit**

  ```bash
  git add core/spline/calculator.py app/ui/pages/spline_fit_page.py tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py
  git commit -m "fix(spline): restore traceability and tighten UI validation"
  ```

---

## Chunk 2: Stage B — DIN 5480 几何基础重建

### Task 3: 把几何输入从“m + z 自推”改成“标准尺寸/标准参数”

**Files:**
- Modify: `core/spline/geometry.py`
- Modify: `core/spline/__init__.py`
- Modify: `tests/core/spline/test_geometry.py`
- Modify: `app/ui/pages/spline_fit_page.py`
- Create: `docs/references/2026-03-22-spline-fit-sources.md`

- [ ] **Step 1: 写参考样例测试**

  至少包含：
  - 一个 DIN 5480 公开规格样例（例如 `W30x1.25x22`）
  - 一个非法组合样例（参考直径/模数/齿数不自洽）
  - 一个“缺少关键标准参数”的失败样例

- [ ] **Step 2: 运行测试确认当前几何实现失败**

  Run: `python3 -m pytest tests/core/spline/test_geometry.py -q`

- [ ] **Step 3: 设计新的几何 API**

  推荐方案：
  - UI 不再默认“只填 `m`、`z`”
  - 最少补入：`reference_diameter_mm`、`module_mm`、`tooth_count`、`profile_shift_coeff`
  - 如果公开标准尺寸不足以稳定推导，则允许“标准规格表选择器 + 手工覆盖”

- [ ] **Step 4: 实现新的几何推导与 trace**

  具体要求：
  - 输出中保留“几何来源”：标准规格 / 手工输入 / 近似补全
  - 不允许把“近似补全”默默当成“标准几何”
  - 旧的 `m*z` 近似如需保留，只能放到明确命名的 fallback helper 中，并带强 warning

- [ ] **Step 5: 更新 UI 字段与 hints**

  具体要求：
  - 新字段与旧字段的映射清晰
  - 对“近似模式”做显式开关，而不是默认启用

- [ ] **Step 6: 记录来源**

  在 `docs/references/2026-03-22-spline-fit-sources.md` 中写清：
  - 参考尺寸样例出处
  - benchmark 对齐规则
  - 哪些公开资料只能用于几何，不能直接用于强度

- [ ] **Step 7: 回归测试**

  Run: `python3 -m pytest tests/core/spline/test_geometry.py tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 8: Commit**

  ```bash
  git add core/spline/geometry.py core/spline/__init__.py app/ui/pages/spline_fit_page.py tests/core/spline/test_geometry.py tests/ui/test_spline_fit_page.py docs/references/2026-03-22-spline-fit-sources.md
  git commit -m "refactor(spline): rebuild DIN 5480 geometry inputs and trace"
  ```

---

## Chunk 3: Stage B — 强度链扩展与结论边界

### Task 4: 场景 A 从单一承压式升级为“最小工程子集”

**Files:**
- Modify: `core/spline/calculator.py`
- Modify: `tests/core/spline/test_calculator.py`
- Modify: `app/ui/pages/spline_fit_page.py`

- [ ] **Step 1: 写失败测试，先定义“最小工程子集”的输出结构**

  最少包含：
  - `flank_pressure_mpa`
  - `load_distribution` trace（不要只留一个模糊的 `k_alpha`）
  - `model_assumptions`
  - `not_covered_checks`
  - 明确的 `overall_verdict_level`（例如 `simplified_precheck`）

- [ ] **Step 2: 运行测试确认失败**

  Run: `python3 -m pytest tests/core/spline/test_calculator.py -q`

- [ ] **Step 3: 扩展计算链**

  推荐最小范围：
  - 把“周向/轴向载荷分布”拆成独立 trace 字段，而不是一个统称 `k_alpha`
  - 明确 `p_allowable` 来源：手工 / 预设 / benchmark 映射
  - 在结果中显式列出未覆盖项：齿根弯曲、剪切、胀裂、磨损、寿命

- [ ] **Step 4: 如果本轮不实现更多失效模式，则把 verdict 降级**

  规则：
  - 缺少关键失效模式时，禁止输出“工程校核通过”
  - 只能输出“简化预校核通过/不通过”

- [ ] **Step 5: 回归**

  Run: `python3 -m pytest tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 6: Commit**

  ```bash
  git add core/spline/calculator.py app/ui/pages/spline_fit_page.py tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py
  git commit -m "feat(spline): expand scenario A trace and downgrade verdict semantics"
  ```

### Task 5: benchmark 闭环，不再只做“自洽测试”

**Files:**
- Modify: `tests/core/spline/test_geometry.py`
- Modify: `tests/core/spline/test_calculator.py`
- Create: `examples/spline_case_01.json`
- Create: `examples/spline_case_02.json`
- Modify: `docs/references/2026-03-22-spline-fit-sources.md`

- [ ] **Step 1: 准备至少 3 类样例**

  至少包括：
  - 标准尺寸几何样例
  - 一个简化承压可通过样例
  - 一个需要因 trace / warning 被降级的样例

- [ ] **Step 2: 把样例转成 fixture / example**

- [ ] **Step 3: 测试结果必须带来源注释**

  要求：
  - 每个 benchmark 写清“对齐什么”
  - 明确容差范围
  - 如果只是公开规格近似，不得称为“标准认证算例”

- [ ] **Step 4: 运行 spline 全量回归**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline tests/ui/test_spline_fit_page.py -q`

- [ ] **Step 5: Commit**

  ```bash
  git add tests/core/spline/test_geometry.py tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py examples/spline_case_01.json examples/spline_case_02.json docs/references/2026-03-22-spline-fit-sources.md
  git commit -m "test(spline): add benchmark-backed geometry and calculator coverage"
  ```

---

## Review / 校核 Gate

执行每个 chunk 后都必须满足以下 gate，未满足不得进入下一 chunk：

- [ ] 相关 `pytest` 定向测试通过
- [ ] UI 文案与计算结论语义一致
- [ ] 没有把“简化预校核”说成“正式工程校核”
- [ ] 新增 trace 能解释失败原因和参数来源
- [ ] `task_plan.md` / `findings.md` / `progress.md` 已同步

## Final Verification

在宣称“整改完成”之前，必须至少运行：

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline tests/ui/test_spline_fit_page.py -q
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

并人工核对：

- [ ] 默认页面不会再暗示“可直接用于正式 DIN 5480 工程校核”
- [ ] 场景 B fail 时，UI 能显示具体失败原因
- [ ] 几何样例不再把 `30x1.25x22` 这类规格误判成 `m*z`
- [ ] 结果页面能区分“简化预校核”与“正式工程校核”

## Recommended Execution Order

1. 先执行 Stage A，两次 commit，先把“错误承诺”和“trace 缺失”止血。
2. Stage A 验证通过后，再决定是否进入 Stage B。
3. 如果目标只是“内部预筛选工具”，Stage A + Task 5 benchmark 已足够。
4. 如果目标是“可用于工程校核”，Stage B 不能跳过，而且还需要额外补一轮标准/商业工具对标审查。

## Exit Criteria

- 达到“安全预校核工具”标准：
  - Stage A 全部完成
  - benchmark 基线建立
  - verdict 全部降级到真实边界

- 达到“可作为工程校核候选”标准：
  - Stage B 全部完成
  - 几何和强度链对公开样例/工具结果的偏差已知且受控
  - 新一轮深度 review 明确通过
