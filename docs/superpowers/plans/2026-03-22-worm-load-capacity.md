# Worm Load-Capacity Upgrade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复蜗杆模块的几何/功率逻辑漏洞，并实现 `DIN 3996 Method B` 风格的最小负载能力闭环，输出齿面应力、齿根应力和扭矩波动结果。

**Architecture:** 保留 `core/worm/calculator.py` 作为单一计算入口，但把返回值分成 geometry/performance/load_capacity 三个稳定层级。先用 TDD 修复功率与几何一致性，再增量接入最小负载能力子集和 UI 结果展示，避免一次性重写页面。

**Tech Stack:** Python, PySide6, pytest, unittest-style tests

---

### Task 1: Planning Context

**Files:**
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`
- Create: `docs/superpowers/specs/2026-03-22-worm-load-capacity-design.md`

- [ ] 记录蜗杆模块进入执行阶段
- [ ] 记录本轮范围是 `Method B` 风格最小子集，不是完整标准实现
- [ ] 记录关键问题：功率链路、几何一致性、参数未入模、Load Capacity 占位

### Task 2: Core RED Tests for Integrity Gaps

**Files:**
- Modify: `tests/core/worm/test_calculator.py`

- [ ] **Step 1: Write the failing test for power-chain consistency**
- [ ] **Step 2: Run `python3 -m pytest tests/core/worm/test_calculator.py -q` and confirm RED**
- [ ] **Step 3: Write the failing test for `friction_override` affecting efficiency**
- [ ] **Step 4: Re-run the same test file and confirm RED**
- [ ] **Step 5: Write the failing test for `application_factor` affecting design load**
- [ ] **Step 6: Re-run the same test file and confirm RED**

### Task 3: Core Implementation for Geometry and Power Chain

**Files:**
- Modify: `core/worm/calculator.py`

- [ ] 修正 `input power -> output power -> output torque` 链路
- [ ] 接入 `advanced.friction_override`
- [ ] 输出 `lead_angle_implied_deg` 和 `lead_angle_delta_deg`
- [ ] 保留 `center_distance_delta_mm`，并追加几何 warning
- [ ] 接入 `application_factor`
- [ ] 运行 `python3 -m pytest tests/core/worm/test_calculator.py -q`，确认 GREEN

### Task 4: Core RED Tests for Load Capacity Subset

**Files:**
- Modify: `tests/core/worm/test_calculator.py`

- [ ] **Step 1: Write the failing test for tooth-force outputs**
- [ ] **Step 2: Write the failing test for contact-stress outputs and safety factor**
- [ ] **Step 3: Write the failing test for root-stress outputs and safety factor**
- [ ] **Step 4: Write the failing test for torque-ripple peak/RMS outputs**
- [ ] **Step 5: Run `python3 -m pytest tests/core/worm/test_calculator.py -q` and confirm RED**

### Task 5: Core Implementation for Minimal Method-B Subset

**Files:**
- Modify: `core/worm/calculator.py`

- [ ] 新增材料弹性参数和许用应力解析
- [ ] 新增 `Ft/Fa/Fr/Fn`
- [ ] 新增名义、RMS、峰值扭矩
- [ ] 新增齿面应力与安全系数
- [ ] 新增齿根应力与安全系数
- [ ] 把 `load_capacity.status` 从固定文案升级为真实状态摘要
- [ ] 运行 `python3 -m pytest tests/core/worm/test_calculator.py -q`，确认 GREEN

### Task 6: UI RED Tests

**Files:**
- Modify: `tests/ui/test_worm_page.py`

- [ ] **Step 1: Write the failing test for new load-capacity input fields**
- [ ] **Step 2: Write the failing test for `Load Capacity` page rendering real stress outputs**
- [ ] **Step 3: Write the failing test for result summary exposing torque ripple / stress data**
- [ ] **Step 4: Run `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -q` and confirm RED**

### Task 7: UI / Sample Implementation

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `examples/worm_case_01.json`
- Modify: `examples/worm_case_02.json`

- [ ] 增加新输入字段与默认值
- [ ] 让 `Load Capacity` 页面展示真实结果
- [ ] 更新结果摘要与导出文本
- [ ] 同步两个样例为几何更自洽、参数更完整的工况
- [ ] 运行 `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -q`，确认 GREEN

### Task 8: Closeout Verification

**Files:**
- Modify: `README.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

- [ ] README 说明蜗杆模块已具备最小负载能力子集，但不是完整 `DIN 3996 / ISO/TS 14521`
- [ ] 运行 `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py tests/ui/test_worm_page.py -q`
- [ ] 如无异常，再运行 `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py tests/ui/test_worm_page.py tests/core/hertz/test_calculator.py -q`
- [ ] 更新 planning 文件的阶段状态、发现和验证记录
