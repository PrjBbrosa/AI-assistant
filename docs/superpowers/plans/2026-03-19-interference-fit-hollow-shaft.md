# Interference-Fit Hollow-Shaft Support Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在过盈配合模块中新增空心轴支持，并把轴内径输入接入主校核链路与 UI/报告。

**Architecture:** 保持当前实心轴基线不变；新增 `geometry.shaft_inner_d_mm` 并通过空心轴柔度放大因子修正轴侧柔度。`repeated_load` 对空心轴降级为 `not applicable`，避免超出当前简化公式边界。

**Tech Stack:** Python, PySide6, pytest, unittest-style tests

---

### Task 1: Planning Context

**Files:**
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

- [ ] 记录本轮“空心轴支持”进入执行阶段
- [ ] 标明本轮仍不扩展 temperature / speed / stepped geometry

### Task 2: Core RED Tests

**Files:**
- Modify: `tests/core/interference/test_calculator.py`

- [ ] 新增失败测试：空心轴输入应降低接触压力与扭矩能力
- [ ] 运行单测，确认 RED
- [ ] 新增失败测试：`shaft_inner_d_mm >= shaft_d_mm` 报错
- [ ] 运行单测，确认 RED
- [ ] 新增失败测试：空心轴下 repeated-load 不适用
- [ ] 运行单测，确认 RED

### Task 3: UI RED Tests

**Files:**
- Modify: `tests/ui/test_interference_page.py`

- [ ] 新增失败测试：页面暴露 `geometry.shaft_inner_d_mm`
- [ ] 新增失败测试：payload 包含 `shaft_inner_d_mm`
- [ ] 新增失败测试：报告能看到空心轴几何/模型语义
- [ ] 运行 UI 定向测试，确认 RED

### Task 4: Core Implementation

**Files:**
- Modify: `core/interference/calculator.py`

- [ ] 解析 `geometry.shaft_inner_d_mm`，默认 `0`
- [ ] 校验 `0 <= d_inner < d`
- [ ] 实现空心轴柔度放大因子
- [ ] 将 `c_shaft` / `c_total` / 主结果链路切换到新几何
- [ ] 更新 `model.type` 与 `derived` 输出
- [ ] 空心轴下将 repeated-load 标记为不适用

### Task 5: UI / Report Implementation

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`

- [ ] 在“几何与过盈”章节新增 `geometry.shaft_inner_d_mm`
- [ ] 更新标题、副标题、hint、beginner guide
- [ ] 确保 payload / load / report 路径正确传递该字段
- [ ] 在结果/报告中明确实心轴或空心轴语义

### Task 6: Docs and Example Text

**Files:**
- Modify: `README.md`
- Modify: `docs/references/2026-03-19-interference-public-benchmark-notes.md`

- [ ] README 说明当前已支持空心轴主模型，但 speed / service temperature 仍未耦合
- [ ] benchmark 说明改成“空心轴已支持，但公开 benchmark 仍非一对一复现”

### Task 7: Verification and Closeout

**Files:**
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`
- Create: `docs/reports/2026-03-19-summary-2.md`

- [ ] 运行 interference 子集回归
- [ ] 运行全量 `pytest -q`
- [ ] 更新 planning 文件与日报
