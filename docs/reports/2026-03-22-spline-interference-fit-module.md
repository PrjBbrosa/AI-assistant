# 花键过盈配合模块开发报告

**Date:** 2026-03-22
**Branch:** `main`
**Commits:** 5 (fb222a9 ~ 1f27f4a)
**Total Lines:** 1052 lines across 8 files

---

## 历史实现说明

本报告记录的是 2026-03-22 首版实现状态，不代表该模块当前已达到正式工程校核级别。

- 场景 A 当时实现的是“花键齿面平均承压”的简化估算。
- 它未建立完整的 DIN 5480 / DIN 6892 风格几何、公差、装配与多失效模式校核链。
- 因此该版本更适合作为方案筛选或简化预校核，不应直接作为正式工程校核结论使用。

---

## 1. Objectives

新建独立模块"花键过盈配合"，支持两种场景的扭矩传递校核：
- **场景 A** — 渐开线花键齿面过盈：基于 Niemann/DIN 5466 简化公式，校核齿面承压安全系数。
- **场景 B** — 花键轴光滑段圆柱过盈：复用现有 DIN 7190 Lame 模型，扣除退刀槽有效长度，校核打滑扭矩与应力。

两场景独立校核、不叠加扭矩能力，在同一 UI 页面中呈现，侧栏注册为独立模块入口。

## 2. Deliverables

### 2.1 Core 计算层

| File | Lines | Description |
|------|-------|-------------|
| `core/spline/__init__.py` | 11 | 模块公共 API 导出 |
| `core/spline/geometry.py` | 50 | 渐开线花键几何推导 (DIN 5480 简化): d, d_a, d_f, h_w, d_m |
| `core/spline/calculator.py` | 212 | 主计算引擎: 场景 A 齿面承压 + 场景 B 委托 DIN 7190 |

### 2.2 UI 层

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/pages/spline_fit_page.py` | 511 | 5 章节式 UI 页面，含模式切换、载荷工况联动、结果展示 |
| `app/ui/main_window.py` | +4/-4 | 侧栏注册：PlaceholderPage -> SplineFitPage |

### 2.3 Tests

| File | Lines | Tests |
|------|-------|-------|
| `tests/core/spline/__init__.py` | 0 | 包标识 |
| `tests/core/spline/test_geometry.py` | 40 | 5 tests: 基础几何、DIN 5480 规格、无效输入、输出键 |
| `tests/core/spline/test_calculator.py` | 185 | 14 tests: 场景 A 公式验证 (7) + 场景 B 委托与联合校核 (7) |
| `tests/ui/test_spline_fit_page.py` | 43 | 4 tests: 页面创建、章节数、默认计算、模式切换显隐 |

**测试总计:** 23 个新增测试，全量 216 测试通过，零回归。

## 3. Commit History

| Commit | Message |
|--------|---------|
| `fb222a9` | feat(spline): add involute spline geometry derivation (DIN 5480) |
| `42d5024` | feat(spline): add scenario A tooth-flank bearing stress calculator |
| `f441f0a` | feat(spline): add scenario B smooth-bore press fit via DIN 7190 delegation |
| `4b027dd` | feat(spline): add spline interference fit UI page |
| `1f27f4a` | test(spline): add UI smoke tests for spline fit page |

## 4. Key Technical Decisions

1. **场景 B 委托而非重写** — 直接调用 `calculate_interference_fit()`，将退刀槽宽度扣除后的有效长度传入 `fit_length_mm`。避免重复实现 Lame 模型，确保 DIN 7190 逻辑单源维护。K_A 在花键侧已乘入，委托时 `application_factor_ka=1.0`。

2. **两场景独立校核，不叠加扭矩** — 根据 Niemann/Winter 工程惯例，花键 form-fit 与光滑段 force-fit 在不同轴向位置时不能简单相加。`overall_pass = A_ok AND B_ok`，各自必须独立满足全部设计扭矩。

3. **花键几何 DIN 5480 简化** — 固定 alpha=30 deg，仅实现 `d=m*z`, `d_a1=m*(z+1)`, `d_f1=m*(z-1.25)`, `d_a2=m*(z-1)` 等基础公式。完整 DIN 5480 包含齿侧间隙、偏差等复杂内容，后续按需扩展。

4. **许用齿面压力查表联动** — UI 提供 4 种典型工况预设 (调质钢/渗碳淬火 x 静载/脉动)，选择后自动填充 p_zul；切到"自定义"可手输任意值。避免用户查手册。

5. **UI 测试用 `isHidden()` 替代 `isVisible()`** — Qt headless (offscreen) 环境下，未 show 的顶层 widget `isVisible()` 始终返回 False，无法区分 `setVisible(True)` 和 `setVisible(False)`。改用 `isHidden()` 精确检测 `setVisible()` 设置的状态。

6. **矩形花键接口预留** — `derive_involute_geometry` 支持 `pressure_angle_deg` 参数，但当前锁定 30 deg。`calculator.py` 的 `_calculate_scenario_a` 仅依赖几何输出字典，后续新增矩形花键只需实现 `derive_rectangular_geometry` 返回相同 key 集。

## 5. Known Limitations

1. **花键几何是 DIN 5480 简化版** — 未考虑齿侧间隙、制造偏差、齿形修正系数。真实 DIN 5480 规格表中的 da/df 可能因偏差略有不同。
2. **载荷分布系数 K_alpha 用户自定** — 未实现 FVA 591 / DIN 5466 的自动计算（取决于齿数、精度等级、配合类型）。当前默认 1.0，适用于过盈配合工况。
3. **场景 B 未集成热装/压装工艺计算** — 现有 `core/interference/assembly.py` 支持 shrink_fit/force_fit 详细计算，但花键模块未传递 assembly 配置。后续可扩展。
4. **无输入条件保存/加载** — 现有过盈配合模块支持 JSON 保存/加载，花键模块尚未接入 `input_condition_store.py`。
5. **无报告导出** — 现有过盈配合模块支持 PDF/文本报告导出，花键模块尚未接入 `report_export.py`。
6. **矩形花键 (DIN 5462/5463)** — 几何推导和校核公式未实现，仅预留接口。

## 6. Reflection

### What went well
- **Subagent-Driven Development 高效** — 5 个 Task 各派独立 subagent，每个 Task 含 TDD + spec review，全程无阻塞。从计划到全量通过约 30 分钟。
- **DIN 7190 委托复用** — 场景 B 只写了 ~70 行胶水代码，零重复逻辑，即刻获得完整的 Lame 模型 + 压入力曲线 + 应力校核。
- **计划先行** — 先写完整 plan（含公式、测试用例、FieldSpec 定义），reviewer 审查后再执行。实现过程中几乎无返工。

### What could be improved
- **UI 页面占 511 行，接近单文件上限** — 如果后续加入输入保存/报告导出/花键截面图，应考虑拆分为 `spline_fit_page.py` (表单) + `spline_fit_result.py` (结果展示)。
- **测试覆盖偏重公式正确性，缺少边界测试** — 例如 relief_groove_width_mm == fit_length_mm（有效长度刚好 0）、极大模数等边界条件未覆盖。

### Recurring Issues
- None identified (首次创建花键模块，无历史问题对比)。

## 7. Next Steps

| Phase | Scope |
|-------|-------|
| 热装/压装工艺 | 场景 B 集成 `assembly.py` 的 shrink_fit/force_fit 计算 |
| 输入保存/加载 | 接入 `input_condition_store.py`，支持 JSON 持久化 |
| 报告导出 | 接入 `report_export.py`，生成 PDF/文本报告 |
| K_alpha 自动估算 | 基于齿数、精度等级、配合类型的简化公式 |
| 矩形花键 | `derive_rectangular_geometry` + 对应校核公式 |
| 花键截面示意图 | 类似 `clamping_diagram.py` 的可视化控件 |
| DIN 5466 完整校核 | 齿根弯曲应力、齿侧间隙、面宽系数 K_beta |
