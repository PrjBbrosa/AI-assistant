# 缓冲块吸能仿真 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增缓冲块吸能仿真模块（独立 section），导入加载/卸载 F-x 曲线，按能量法求解单次冲击响应（最大压缩、峰值力、吸收/耗散/回弹能量），并由能量守恒反推近似时域响应曲线 `x(t)/v(t)/a(t)/F(t)`。

**Architecture:** Core 层纯 Python（dict-in dict-out），分三个文件：`calculator.py`（能量法主流程）、`time_response.py`（能量守恒时域反推）、`curve_import.py`（CSV/XLSX 解析，`openpyxl` 懒加载）。UI 层走 `BaseChapterPage`，但第 4 章 `吸能结果` 必须采用方案 A 工作台总览：中央关键指标 + F-x 曲线 + 能量条，右侧总体结论 / 模型边界 / 参数对比摘要；响应时程和完整参数对比仍保留为详细章节。新增两个 QPainter 自绘 widget：`BufferEnergyCurveWidget`（F-x）和 `BufferResponseCurveWidget`（时域响应，可在 x/v/a/F 间切换）。`MainWindow` 通过现有 `_page_factories` 列表懒加载注册新模块。

**Tech Stack:** Python 3.12、PySide6 (Qt6)、unittest（pytest 运行）、`openpyxl>=3.1`（仅 XLSX 路径懒加载）、`QT_QPA_PLATFORM=offscreen` headless 测试。

---

## Spec Reference

参考 `docs/superpowers/specs/2026-05-02-buffer-energy-simulation-design.md`。所有公式、字段命名、断言阈值、免责声明文案以 spec 为准；本 plan 中所有代码示例与该 spec 完全对齐。

## File Structure

**新增 core 文件**

- `core/buffer/__init__.py` — 模块标记，re-export 主入口
- `core/buffer/calculator.py` — `InputError`、`_require`/`_positive`、曲线 normalization、能量积分、impact solve、checks、`calculate_buffer_energy(data) -> dict` 主入口
- `core/buffer/curve_import.py` — CSV/XLSX 解析；`load_buffer_curve(path) -> dict` 返回 `{"loading": [...], "unloading": [...], "metadata": {...}}`；`openpyxl` 仅在 `.xlsx` 分支内 import
- `core/buffer/time_response.py` — 能量守恒反推 `compute_time_response(curve, impact_solution, mass_kg, options) -> dict | None`

**新增 UI 文件**

- `app/ui/pages/buffer_energy_page.py` — `BufferEnergyPage(BaseChapterPage)`，7 个章节，其中第 4 章是方案 A 工作台总览而非纯文本结果页
- `app/ui/widgets/buffer_energy_curve.py` — `BufferEnergyCurveWidget`（F-x + 滞回填充 + 标注）
- `app/ui/widgets/buffer_response_curve.py` — `BufferResponseCurveWidget`（时域曲线，下拉切换 `x/v/a/F`）

**修改文件**

- `app/ui/main_window.py` — `_page_factories` 增加 `"缓冲块吸能仿真"` 条目 + `_make_buffer_energy_page` 工厂
- `requirements.txt` — 增加 `openpyxl>=3.1`

**示例与配置**

- `examples/buffer_energy_case_01.csv` — 宽表，三角形加载 + 滞回卸载
- `examples/buffer_energy_case_02.xlsx` — 长表，渐进硬化曲线
- `examples/buffer_energy_input_conditions.json` — 默认输入条件

**测试文件**

- `tests/core/buffer/__init__.py` — 必须创建（pytest 同名模块冲突防护，见 CLAUDE.md "测试目录需 `__init__.py`"）
- `tests/core/buffer/test_calculator.py`
- `tests/core/buffer/test_curve_import.py`
- `tests/core/buffer/test_time_response.py`
- `tests/ui/test_buffer_energy_page.py`

## Task Decomposition

20 个任务、7 个阶段。每个任务遵循 TDD：写失败测试 → 跑测试确认失败 → 写实现 → 跑测试确认通过 → commit。

- Phase 1 (Tasks 1–5): Core 能量计算
- Phase 2 (Tasks 6–7): 时域反推
- Phase 3 (Tasks 8–10): 曲线导入
- Phase 4 (Task 11): 测试样例
- Phase 5 (Tasks 12–13): UI Widgets
- Phase 6 (Tasks 14–19): UI Page（7 章节 + 报告导出 + 输入条件保存）
- Phase 7 (Task 20): MainWindow 集成 + UI smoke

---

## Phase 1: Core Energy Calculator

### Task 1: Module skeleton + curve normalization

**Files:**
- Create: `core/buffer/__init__.py`
- Create: `core/buffer/calculator.py`
- Create: `tests/core/buffer/__init__.py`
- Create: `tests/core/buffer/test_calculator.py`

- [ ] **Step 1: Write failing tests for curve normalization**

写入 `tests/core/buffer/test_calculator.py`:

```python
"""Tests for buffer energy calculator core."""

import unittest

from core.buffer.calculator import (
    InputError,
    _normalize_curve,
)


class CurveNormalizationTests(unittest.TestCase):
    def test_sorts_and_dedups_points(self) -> None:
        raw = [
            {"x_mm": 5.0, "force_n": 800.0},
            {"x_mm": 0.0, "force_n": 0.0},
            {"x_mm": 5.0, "force_n": 820.0},
            {"x_mm": 10.0, "force_n": 1800.0},
        ]
        norm, warnings = _normalize_curve(raw, "loading", force_scale=1.0, stroke_scale=1.0)
        self.assertEqual([p["x_mm"] for p in norm], [0.0, 5.0, 10.0])
        self.assertAlmostEqual(norm[1]["force_n"], 810.0, places=6)
        self.assertEqual(warnings, [])

    def test_inserts_origin_when_missing(self) -> None:
        raw = [
            {"x_mm": 2.0, "force_n": 200.0},
            {"x_mm": 5.0, "force_n": 800.0},
        ]
        norm, warnings = _normalize_curve(raw, "loading", force_scale=1.0, stroke_scale=1.0)
        self.assertEqual(norm[0], {"x_mm": 0.0, "force_n": 0.0})
        self.assertTrue(any("起点" in w for w in warnings))

    def test_applies_scales(self) -> None:
        raw = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 1000.0}]
        norm, _ = _normalize_curve(raw, "loading", force_scale=2.0, stroke_scale=0.5)
        self.assertEqual(norm[-1], {"x_mm": 5.0, "force_n": 2000.0})

    def test_rejects_negative_force(self) -> None:
        raw = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 5.0, "force_n": -10.0}]
        with self.assertRaises(InputError):
            _normalize_curve(raw, "loading", force_scale=1.0, stroke_scale=1.0)


if __name__ == "__main__":
    unittest.main()
```

写入 `tests/core/buffer/__init__.py`:

```python
```

(空文件，仅占位让 pytest 把目录视为 package — 见 CLAUDE.md "测试目录需 `__init__.py`")

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/donghang/Documents/Codex/AI-assistant
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

Expected: 4 个测试均 FAIL，错误信息形如 `ModuleNotFoundError: No module named 'core.buffer'`。

- [ ] **Step 3: Implement skeleton + normalization**

写入 `core/buffer/__init__.py`:

```python
"""Buffer block energy simulation package."""

from core.buffer.calculator import InputError, calculate_buffer_energy

__all__ = ["InputError", "calculate_buffer_energy"]
```

写入 `core/buffer/calculator.py`:

```python
"""Buffer block single-impact energy-method calculator (DIN-agnostic).

Reference: docs/superpowers/specs/2026-05-02-buffer-energy-simulation-design.md
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


class InputError(ValueError):
    """Raised when input data is incomplete or physically invalid."""


def _require(section: Dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        raise InputError(f"缺少必填字段: {section_name}.{key}")
    return section[key]


def _positive(value: float, name: str, allow_zero: bool = False) -> float:
    if allow_zero and value == 0:
        return value
    if value <= 0:
        raise InputError(f"{name} 必须 > 0，当前值 {value}")
    return value


_DUP_X_TOL = 1e-6  # mm


def _normalize_curve(
    raw_points: Sequence[Dict[str, float]],
    label: str,
    *,
    force_scale: float,
    stroke_scale: float,
) -> Tuple[List[Dict[str, float]], List[str]]:
    """Sort, dedup, scale and validate one curve branch.

    Returns ``(normalized_points, warnings)``. Raises ``InputError`` on
    structurally invalid data (negative force, non-numeric, empty after scale).
    Inserting `(0, 0)` and other repair operations append warnings instead.
    """
    if not raw_points:
        raise InputError(f"{label} 曲线为空")

    scaled: List[Tuple[float, float]] = []
    for idx, p in enumerate(raw_points):
        try:
            x = float(p["x_mm"]) * stroke_scale
            f = float(p["force_n"]) * force_scale
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(f"{label} 曲线第 {idx + 1} 行解析失败: {exc}") from exc
        if f < 0:
            raise InputError(f"{label} 曲线第 {idx + 1} 行力为负 ({f:.3f} N)")
        scaled.append((x, f))

    scaled.sort(key=lambda t: t[0])

    merged: List[Tuple[float, float]] = []
    for x, f in scaled:
        if merged and abs(x - merged[-1][0]) < _DUP_X_TOL:
            prev_x, prev_f = merged[-1]
            merged[-1] = (prev_x, (prev_f + f) / 2.0)
        else:
            merged.append((x, f))

    warnings: List[str] = []
    if merged[0][0] > _DUP_X_TOL:
        merged.insert(0, (0.0, 0.0))
        warnings.append(f"{label} 曲线起点不是 (0,0)，已补充 (0,0) 用于积分")

    return [{"x_mm": x, "force_n": f} for x, f in merged], warnings
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

Expected: 4 PASS。

- [ ] **Step 5: Commit**

```bash
git add core/buffer/__init__.py core/buffer/calculator.py \
        tests/core/buffer/__init__.py tests/core/buffer/test_calculator.py
git commit -m "feat(buffer): add core skeleton with curve normalization"
```

---

### Task 2: Energy integration + curve_summary

**Files:**
- Modify: `core/buffer/calculator.py`
- Modify: `tests/core/buffer/test_calculator.py`

- [ ] **Step 1: Write failing tests for energy integration**

追加到 `tests/core/buffer/test_calculator.py`（在 `if __name__` 之前）:

```python
from core.buffer.calculator import (
    _accumulate_loading_energy,
    _trapezoid_area,
    _curve_summary,
    _tangent_stiffness_range,
)


class EnergyIntegrationTests(unittest.TestCase):
    def test_triangle_loading_energy_matches_analytic(self) -> None:
        # F=k*x with k=200 N/mm, 0..10 mm => area = 0.5 * 10 * 2000 = 10000 N*mm = 10 J
        pts = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 2.5, 5.0, 7.5, 10.0)]
        e_x, e_j = _accumulate_loading_energy(pts)
        self.assertAlmostEqual(e_j[-1], 10.0, places=4)
        self.assertEqual(len(e_x), len(e_j))
        self.assertEqual(e_j[0], 0.0)

    def test_trapezoid_area_unit_conversion(self) -> None:
        # 1 N over 1 mm = 0.001 J
        pts = [{"x_mm": 0.0, "force_n": 1.0}, {"x_mm": 1.0, "force_n": 1.0}]
        self.assertAlmostEqual(_trapezoid_area(pts), 0.001, places=9)

    def test_tangent_stiffness_range(self) -> None:
        pts = [
            {"x_mm": 0.0, "force_n": 0.0},
            {"x_mm": 5.0, "force_n": 500.0},   # k = 100
            {"x_mm": 10.0, "force_n": 2000.0}, # k = 300
        ]
        k_min, k_max = _tangent_stiffness_range(pts)
        self.assertAlmostEqual(k_min, 100.0)
        self.assertAlmostEqual(k_max, 300.0)

    def test_curve_summary_fields_present(self) -> None:
        loading = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 2000.0}]
        unloading = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 1000.0}]
        summary = _curve_summary(loading, unloading)
        self.assertAlmostEqual(summary["max_stroke_mm"], 10.0)
        self.assertAlmostEqual(summary["peak_loading_force_n"], 2000.0)
        self.assertAlmostEqual(summary["loading_energy_j"], 10.0, places=4)
        self.assertAlmostEqual(summary["unloading_energy_j"], 5.0, places=4)
        self.assertAlmostEqual(summary["curve_hysteresis_energy_j"], 5.0, places=4)
        self.assertAlmostEqual(summary["energy_absorption_ratio"], 0.5, places=4)
        self.assertAlmostEqual(summary["equivalent_stiffness_n_per_mm"], 200.0, places=4)
```

- [ ] **Step 2: Run tests, verify failures**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

Expected: new 4 tests fail (ImportError on helpers).

- [ ] **Step 3: Implement energy integration & summary**

追加到 `core/buffer/calculator.py`:

```python
_MM_TO_M = 1e-3  # 1 mm * 1 N = 0.001 J


def _trapezoid_area(points: Sequence[Dict[str, float]]) -> float:
    """Trapezoid integral over (x_mm, force_n) returning energy in J."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        total += 0.5 * (prev["force_n"] + curr["force_n"]) * dx
    return total * _MM_TO_M


def _accumulate_loading_energy(
    points: Sequence[Dict[str, float]],
) -> Tuple[List[float], List[float]]:
    """Return cumulative energy curve (x_mm list, energy_j list)."""
    if not points:
        return [], []
    xs: List[float] = [points[0]["x_mm"]]
    es: List[float] = [0.0]
    cum = 0.0
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        cum += 0.5 * (prev["force_n"] + curr["force_n"]) * dx * _MM_TO_M
        xs.append(curr["x_mm"])
        es.append(cum)
    return xs, es


def _tangent_stiffness_range(points: Sequence[Dict[str, float]]) -> Tuple[float, float]:
    """Min/max of (ΔF / Δx) along the loading curve, ignoring near-duplicate x."""
    slopes: List[float] = []
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        if dx < _DUP_X_TOL:
            continue
        slopes.append((curr["force_n"] - prev["force_n"]) / dx)
    if not slopes:
        return 0.0, 0.0
    return min(slopes), max(slopes)


def _curve_summary(
    loading: Sequence[Dict[str, float]],
    unloading: Sequence[Dict[str, float]],
) -> Dict[str, float]:
    max_stroke = loading[-1]["x_mm"]
    peak_force = max(p["force_n"] for p in loading)
    e_load = _trapezoid_area(loading)
    e_unload = _trapezoid_area(unloading)
    hysteresis = max(0.0, e_load - e_unload)
    ratio = (hysteresis / e_load) if e_load > 0 else 0.0
    k_eq = (peak_force / max_stroke) if max_stroke > 0 else 0.0
    k_min, k_max = _tangent_stiffness_range(loading)
    return {
        "max_stroke_mm": max_stroke,
        "peak_loading_force_n": peak_force,
        "loading_energy_j": e_load,
        "unloading_energy_j": e_unload,
        "curve_hysteresis_energy_j": hysteresis,
        "energy_absorption_ratio": ratio,
        "equivalent_stiffness_n_per_mm": k_eq,
        "tangent_stiffness_min_n_per_mm": k_min,
        "tangent_stiffness_max_n_per_mm": k_max,
    }
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

Expected: all 8 PASS.

- [ ] **Step 5: Commit**

```bash
git add core/buffer/calculator.py tests/core/buffer/test_calculator.py
git commit -m "feat(buffer): trapezoid energy integration and curve summary"
```

---

### Task 3: Impact solve (both branches) + average force

**Files:**
- Modify: `core/buffer/calculator.py`
- Modify: `tests/core/buffer/test_calculator.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/core/buffer/test_calculator.py`:

```python
from core.buffer.calculator import _solve_impact


def _linear_loading(k_n_per_mm: float, x_max_mm: float, n: int = 21) -> list:
    step = x_max_mm / (n - 1)
    return [{"x_mm": i * step, "force_n": k_n_per_mm * i * step} for i in range(n)]


class ImpactSolveTests(unittest.TestCase):
    def test_non_bottom_out_solution(self) -> None:
        loading = _linear_loading(200.0, 50.0)
        # E0 = 0.5 * 1 kg * (2 m/s)^2 = 2 J
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=2.0,
            available_stroke_mm=50.0,
            allowable_peak_force_n=10000.0,
        )
        self.assertFalse(result["bottom_out"])
        # E_load(x) = 0.5 * k * x^2 in N*mm, divided by 1000 -> J
        # 2 J = 0.5 * 200 * x^2 / 1000 -> x^2 = 20 -> x ≈ 4.4721 mm
        self.assertAlmostEqual(result["max_compression_mm"], 4.4721, places=3)
        self.assertAlmostEqual(result["peak_force_n"], 200.0 * 4.4721, places=2)
        self.assertEqual(result["peak_force_status"], "ok")
        self.assertAlmostEqual(result["absorbed_energy_j"], 2.0, places=4)

    def test_bottom_out_marks_unknown_peak(self) -> None:
        loading = _linear_loading(50.0, 10.0)  # capacity = 0.5*50*10^2/1000 = 2.5 J
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=5.0,           # E0 = 12.5 J >> 2.5 J
            available_stroke_mm=10.0,
            allowable_peak_force_n=10000.0,
        )
        self.assertTrue(result["bottom_out"])
        self.assertIsNone(result["peak_force_n"])
        self.assertEqual(result["peak_force_status"], "bottom_out_unknown")
        self.assertAlmostEqual(result["max_compression_mm"], 10.0)
        self.assertAlmostEqual(result["absorbed_energy_j"], 2.5, places=4)

    def test_peak_force_exceeds_limit(self) -> None:
        loading = _linear_loading(200.0, 50.0)
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=2.0,
            available_stroke_mm=50.0,
            allowable_peak_force_n=500.0,        # peak ~894 N exceeds
        )
        self.assertEqual(result["peak_force_status"], "exceeds_limit")

    def test_average_force(self) -> None:
        loading = _linear_loading(200.0, 50.0)
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=2.0,
            available_stroke_mm=50.0,
            allowable_peak_force_n=10000.0,
        )
        # absorbed = 2 J, x_max ~ 4.4721 mm
        # F_avg = 2 * 1000 / 4.4721 ≈ 447.2 N
        self.assertAlmostEqual(result["average_force_n"], 447.2, places=1)
```

- [ ] **Step 2: Run tests, verify failures**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py::ImpactSolveTests -v
```

- [ ] **Step 3: Implement `_solve_impact`**

追加到 `core/buffer/calculator.py`:

```python
def _interp_linear(xs: Sequence[float], ys: Sequence[float], target_x: float) -> float:
    """Linear interpolation; clamps to endpoints when out of range."""
    if target_x <= xs[0]:
        return ys[0]
    if target_x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        if x0 <= target_x <= x1 and x1 > x0:
            t = (target_x - x0) / (x1 - x0)
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _invert_energy_curve(
    energy_xs: Sequence[float],
    energy_js: Sequence[float],
    target_e: float,
) -> float:
    """Find x such that E_load(x) = target_e (linear interpolation)."""
    if target_e <= energy_js[0]:
        return energy_xs[0]
    if target_e >= energy_js[-1]:
        return energy_xs[-1]
    for i in range(len(energy_js) - 1):
        e0, e1 = energy_js[i], energy_js[i + 1]
        if e0 <= target_e <= e1 and e1 > e0:
            t = (target_e - e0) / (e1 - e0)
            return energy_xs[i] + t * (energy_xs[i + 1] - energy_xs[i])
    return energy_xs[-1]


def _solve_impact(
    *,
    loading: Sequence[Dict[str, float]],
    mass_kg: float,
    initial_velocity_m_s: float,
    available_stroke_mm: float,
    allowable_peak_force_n: float,
) -> Dict[str, Any]:
    e0 = 0.5 * mass_kg * initial_velocity_m_s ** 2

    energy_xs, energy_js = _accumulate_loading_energy(loading)
    max_test_stroke = energy_xs[-1]
    effective_stroke = min(available_stroke_mm, max_test_stroke)
    available_capacity = _interp_linear(energy_xs, energy_js, effective_stroke)

    loading_xs = [p["x_mm"] for p in loading]
    loading_fs = [p["force_n"] for p in loading]

    if e0 <= available_capacity:
        x_max = _invert_energy_curve(energy_xs, energy_js, e0)
        peak_f = _interp_linear(loading_xs, loading_fs, x_max)
        absorbed = e0
        bottom_out = False
        if peak_f > allowable_peak_force_n:
            peak_status = "exceeds_limit"
        else:
            peak_status = "ok"
        peak_value: Optional[float] = peak_f
    else:
        x_max = effective_stroke
        absorbed = available_capacity
        bottom_out = True
        peak_value = None
        peak_status = "bottom_out_unknown"

    avg_force = (absorbed * 1000.0 / x_max) if x_max > 0 else 0.0

    return {
        "initial_energy_j": e0,
        "available_energy_capacity_j": available_capacity,
        "effective_stroke_mm": effective_stroke,
        "max_compression_mm": x_max,
        "peak_force_n": peak_value,
        "peak_force_status": peak_status,
        "average_force_n": avg_force,
        "absorbed_energy_j": absorbed,
        "bottom_out": bottom_out,
    }
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/buffer/calculator.py tests/core/buffer/test_calculator.py
git commit -m "feat(buffer): impact-solve with bottom-out branch and avg force"
```

---

### Task 4: Rebound estimate + checks + overall pass

**Files:**
- Modify: `core/buffer/calculator.py`
- Modify: `tests/core/buffer/test_calculator.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/core/buffer/test_calculator.py`:

```python
from core.buffer.calculator import _estimate_rebound, _build_checks


class ReboundAndCheckTests(unittest.TestCase):
    def test_rebound_uses_truncated_unloading_area(self) -> None:
        unloading = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 1000.0}]
        # Truncate at x_max = 5.0 mm => triangle area = 0.5 * 5 * 500 = 1250 N*mm = 1.25 J
        rebound = _estimate_rebound(unloading, x_max_mm=5.0, mass_kg=1.0)
        self.assertAlmostEqual(rebound["rebound_energy_j"], 1.25, places=4)
        # v = sqrt(2 * 1.25 / 1) = sqrt(2.5) ≈ 1.5811 m/s
        self.assertAlmostEqual(rebound["estimated_rebound_velocity_m_s"], 1.5811, places=3)

    def test_checks_non_bottom_out(self) -> None:
        impact = {
            "max_compression_mm": 5.0,
            "peak_force_n": 1000.0,
            "peak_force_status": "ok",
            "bottom_out": False,
        }
        checks = _build_checks(impact, available_stroke_mm=10.0, allowable_peak_force_n=2000.0)
        self.assertTrue(checks["stroke_ok"])
        self.assertTrue(checks["peak_force_ok"])
        self.assertTrue(checks["energy_capacity_ok"])

    def test_checks_bottom_out_returns_none_for_peak(self) -> None:
        impact = {
            "max_compression_mm": 10.0,
            "peak_force_n": None,
            "peak_force_status": "bottom_out_unknown",
            "bottom_out": True,
        }
        checks = _build_checks(impact, available_stroke_mm=10.0, allowable_peak_force_n=2000.0)
        self.assertFalse(checks["stroke_ok"])  # forced False on bottom_out
        self.assertIsNone(checks["peak_force_ok"])
        self.assertFalse(checks["energy_capacity_ok"])

    def test_checks_peak_force_exceeds(self) -> None:
        impact = {
            "max_compression_mm": 5.0,
            "peak_force_n": 3000.0,
            "peak_force_status": "exceeds_limit",
            "bottom_out": False,
        }
        checks = _build_checks(impact, available_stroke_mm=10.0, allowable_peak_force_n=2000.0)
        self.assertFalse(checks["peak_force_ok"])
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py::ReboundAndCheckTests -v
```

- [ ] **Step 3: Implement rebound + checks**

追加到 `core/buffer/calculator.py`:

```python
import math


def _truncate_to_xmax(
    points: Sequence[Dict[str, float]],
    x_max_mm: float,
) -> List[Dict[str, float]]:
    """Return points up to and including the interpolated point at x_max_mm."""
    if x_max_mm <= 0:
        return [{"x_mm": 0.0, "force_n": 0.0}]
    xs = [p["x_mm"] for p in points]
    fs = [p["force_n"] for p in points]
    out: List[Dict[str, float]] = []
    for x, f in zip(xs, fs):
        if x < x_max_mm:
            out.append({"x_mm": x, "force_n": f})
        else:
            break
    f_at_max = _interp_linear(xs, fs, x_max_mm)
    out.append({"x_mm": x_max_mm, "force_n": f_at_max})
    return out


def _estimate_rebound(
    unloading: Sequence[Dict[str, float]],
    *,
    x_max_mm: float,
    mass_kg: float,
) -> Dict[str, float]:
    truncated = _truncate_to_xmax(unloading, x_max_mm)
    e_rebound = _trapezoid_area(truncated)
    v_rebound = math.sqrt(2.0 * e_rebound / mass_kg) if mass_kg > 0 else 0.0
    return {
        "rebound_energy_j": e_rebound,
        "estimated_rebound_velocity_m_s": v_rebound,
    }


def _build_checks(
    impact: Dict[str, Any],
    *,
    available_stroke_mm: float,
    allowable_peak_force_n: float,
) -> Dict[str, Any]:
    if impact["bottom_out"]:
        return {
            "stroke_ok": False,
            "peak_force_ok": None,
            "energy_capacity_ok": False,
        }
    return {
        "stroke_ok": impact["max_compression_mm"] <= available_stroke_mm + _DUP_X_TOL,
        "peak_force_ok": (impact["peak_force_n"] is not None
                          and impact["peak_force_n"] <= allowable_peak_force_n),
        "energy_capacity_ok": True,
    }
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/buffer/calculator.py tests/core/buffer/test_calculator.py
git commit -m "feat(buffer): rebound estimate and checks with bottom-out semantics"
```

---

### Task 5: `calculate_buffer_energy` main entry

**Files:**
- Modify: `core/buffer/calculator.py`
- Modify: `tests/core/buffer/test_calculator.py`

- [ ] **Step 1: Write failing end-to-end test**

追加到 `tests/core/buffer/test_calculator.py`:

```python
from core.buffer.calculator import calculate_buffer_energy


class CalculateBufferEnergyEndToEndTests(unittest.TestCase):
    def _payload(self, overrides=None):
        loading = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        unloading = [{"x_mm": x, "force_n": 100.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        payload = {
            "curve": {"loading": loading, "unloading": unloading},
            "impact": {
                "mass_kg": 1.0,
                "initial_velocity_m_s": 2.0,
                "available_stroke_mm": 50.0,
                "allowable_peak_force_n": 10000.0,
            },
            "options": {
                "force_scale": 1.0,
                "stroke_scale": 1.0,
                "noise_tolerance_n": 5.0,
                "time_samples": 200,
            },
        }
        if overrides:
            for section, values in overrides.items():
                payload[section].update(values)
        return payload

    def test_returns_top_level_keys(self) -> None:
        result = calculate_buffer_energy(self._payload())
        for key in ("inputs_echo", "curve_summary", "impact", "checks",
                    "overall_pass", "curves", "warnings", "assumptions"):
            self.assertIn(key, result)

    def test_overall_pass_true_for_clean_case(self) -> None:
        result = calculate_buffer_energy(self._payload())
        self.assertTrue(result["overall_pass"])
        self.assertFalse(result["impact"]["bottom_out"])

    def test_overall_pass_false_when_bottom_out(self) -> None:
        result = calculate_buffer_energy(
            self._payload({"impact": {"initial_velocity_m_s": 30.0}})
        )
        self.assertTrue(result["impact"]["bottom_out"])
        self.assertFalse(result["overall_pass"])
        self.assertIsNone(result["impact"]["peak_force_n"])

    def test_input_validation_rejects_negative_mass(self) -> None:
        with self.assertRaises(InputError):
            calculate_buffer_energy(self._payload({"impact": {"mass_kg": -1.0}}))

    def test_curves_segment_includes_energy_curve(self) -> None:
        result = calculate_buffer_energy(self._payload())
        self.assertEqual(
            len(result["curves"]["loading_energy_x_mm"]),
            len(result["curves"]["loading_energy_j"]),
        )
        self.assertGreater(result["curves"]["loading_energy_j"][-1], 0.0)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py::CalculateBufferEnergyEndToEndTests -v
```

- [ ] **Step 3: Implement main entry**

追加到 `core/buffer/calculator.py`:

```python
def _validate_unloading_against_loading(
    loading: Sequence[Dict[str, float]],
    unloading: Sequence[Dict[str, float]],
    noise_tolerance_n: float,
) -> List[str]:
    warnings: List[str] = []
    loading_xs = [p["x_mm"] for p in loading]
    loading_fs = [p["force_n"] for p in loading]
    hard_limit = noise_tolerance_n * 5.0
    soft_excursions = 0
    for p in unloading:
        f_load_at_x = _interp_linear(loading_xs, loading_fs, p["x_mm"])
        delta = p["force_n"] - f_load_at_x
        if delta > hard_limit:
            raise InputError(
                f"卸载力在 x={p['x_mm']:.3f} mm 处比加载力高出 {delta:.2f} N，"
                f"超过容差 {hard_limit:.2f} N，违反耗散假设"
            )
        if delta > noise_tolerance_n:
            soft_excursions += 1
    if soft_excursions:
        warnings.append(
            f"卸载曲线在 {soft_excursions} 个点处局部高于加载曲线 "
            f"(>{noise_tolerance_n:.1f} N)，已忽略噪声"
        )
    e_load = _trapezoid_area(loading)
    e_unload = _trapezoid_area(unloading)
    if e_load > 0 and e_unload > e_load * 1.10:
        raise InputError(
            f"卸载曲线总面积 {e_unload:.3f} J 超过加载曲线 {e_load:.3f} J 的 10%，"
            "违反耗散假设"
        )
    if e_load > 0 and e_unload > e_load:
        warnings.append("卸载曲线总面积略大于加载面积，已截断为非负耗散")
    return warnings


def _build_assumptions() -> List[str]:
    return [
        "本工具基于加载/卸载 F-x 曲线的单次冲击能量法。",
        "未使用时间域数据，不能唯一识别真实粘性阻尼系数 c。",
        "回弹速度为基于卸载曲线能量的估算值。",
        "若输入动能超过曲线容量，peak_force_n 标记为不可判定；触底后真实冲击峰值显著高于曲线末端力。",
        "时域响应曲线为由能量守恒反推的近似映射，不含应变率效应。",
        "假设水平冲击或重力做功相对动能可忽略；垂直跌落工况需把 m·g·x_max 加入 E0。",
        "卸载段简化假设：测试卸载曲线形状只与位移有关；当工况最大压缩小于测试最大压缩时，仍按测试卸载曲线在 [0, x_max] 段积分。",
    ]


def calculate_buffer_energy(data: Dict[str, Any]) -> Dict[str, Any]:
    """Single-impact buffer-block energy-method solver. See spec for schema."""
    if not isinstance(data, dict):
        raise InputError("输入必须是 dict")

    curve = _require(data, "curve", "data")
    impact_in = _require(data, "impact", "data")
    options = data.get("options", {}) or {}

    force_scale = float(options.get("force_scale", 1.0))
    stroke_scale = float(options.get("stroke_scale", 1.0))
    noise_tolerance = float(options.get("noise_tolerance_n", 5.0))

    loading_raw = _require(curve, "loading", "curve")
    unloading_raw = _require(curve, "unloading", "curve")

    loading, w_load = _normalize_curve(
        loading_raw, "加载", force_scale=force_scale, stroke_scale=stroke_scale
    )
    unloading, w_unload = _normalize_curve(
        unloading_raw, "卸载", force_scale=force_scale, stroke_scale=stroke_scale
    )
    if loading[-1]["x_mm"] <= 0:
        raise InputError("加载曲线最大行程必须 > 0")
    if _trapezoid_area(loading) <= 0:
        raise InputError("加载曲线总能量为 0")

    warnings: List[str] = list(w_load) + list(w_unload)
    # Pad unloading to load-max if shorter
    if unloading[-1]["x_mm"] < loading[-1]["x_mm"] - _DUP_X_TOL:
        unloading.append({"x_mm": loading[-1]["x_mm"], "force_n": loading[-1]["force_n"]})
        warnings.append("卸载曲线最大位移小于加载曲线，已补 (x_load_max, F_load_max) 用于积分")
    warnings.extend(_validate_unloading_against_loading(loading, unloading, noise_tolerance))

    mass_kg = _positive(float(_require(impact_in, "mass_kg", "impact")), "质量")
    v0 = _positive(
        float(_require(impact_in, "initial_velocity_m_s", "impact")), "初速度"
    )
    available_stroke = _positive(
        float(_require(impact_in, "available_stroke_mm", "impact")), "可用行程"
    )
    allowable_peak = _positive(
        float(_require(impact_in, "allowable_peak_force_n", "impact")), "允许峰值力"
    )

    if available_stroke > loading[-1]["x_mm"] + _DUP_X_TOL:
        warnings.append(
            f"可用行程 {available_stroke:.2f} mm 大于测试曲线最大行程 "
            f"{loading[-1]['x_mm']:.2f} mm，能量容量按测试曲线截断"
        )

    summary = _curve_summary(loading, unloading)
    impact = _solve_impact(
        loading=loading,
        mass_kg=mass_kg,
        initial_velocity_m_s=v0,
        available_stroke_mm=available_stroke,
        allowable_peak_force_n=allowable_peak,
    )
    rebound = _estimate_rebound(unloading, x_max_mm=impact["max_compression_mm"], mass_kg=mass_kg)
    impact["rebound_energy_j"] = rebound["rebound_energy_j"]
    impact["estimated_rebound_velocity_m_s"] = rebound["estimated_rebound_velocity_m_s"]
    impact["impact_dissipated_energy_j"] = max(
        0.0, impact["absorbed_energy_j"] - rebound["rebound_energy_j"]
    )
    if impact["bottom_out"]:
        warnings.append("触底情况下回弹能量仅供参考；时域响应仅返回压缩段。")

    checks = _build_checks(
        impact, available_stroke_mm=available_stroke, allowable_peak_force_n=allowable_peak
    )
    overall_pass = bool(
        checks["stroke_ok"] and checks["energy_capacity_ok"]
        and checks["peak_force_ok"] is True
    )

    energy_xs, energy_js = _accumulate_loading_energy(loading)

    return {
        "inputs_echo": {
            "impact": dict(impact_in),
            "options": {
                "force_scale": force_scale,
                "stroke_scale": stroke_scale,
                "noise_tolerance_n": noise_tolerance,
                "time_samples": int(options.get("time_samples", 200)),
            },
        },
        "curve_summary": summary,
        "impact": impact,
        "checks": checks,
        "overall_pass": overall_pass,
        "curves": {
            "loading_x_mm": [p["x_mm"] for p in loading],
            "loading_force_n": [p["force_n"] for p in loading],
            "unloading_x_mm": [p["x_mm"] for p in unloading],
            "unloading_force_n": [p["force_n"] for p in unloading],
            "loading_energy_x_mm": energy_xs,
            "loading_energy_j": energy_js,
        },
        "_normalized": {  # private cache, used by time_response wrapper
            "loading": loading,
            "unloading": unloading,
        },
        "warnings": warnings,
        "assumptions": _build_assumptions(),
    }
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_calculator.py -v
```

Expected: all PASS (≥17 tests).

- [ ] **Step 5: Commit**

```bash
git add core/buffer/__init__.py core/buffer/calculator.py tests/core/buffer/test_calculator.py
git commit -m "feat(buffer): calculate_buffer_energy main entry with full schema"
```

---

## Phase 2: Time-Domain Reconstruction

### Task 6: Compression segment time integration with singularity handling

**Files:**
- Create: `core/buffer/time_response.py`
- Create: `tests/core/buffer/test_time_response.py`

- [ ] **Step 1: Write failing tests**

写入 `tests/core/buffer/test_time_response.py`:

```python
"""Tests for energy-conservation time-domain reconstruction."""

import math
import unittest

from core.buffer.calculator import calculate_buffer_energy
from core.buffer.time_response import (
    _compression_time_history,
    compute_time_response,
)


def _linear_curve(k_n_per_mm: float, x_max_mm: float, n: int = 21):
    step = x_max_mm / (n - 1)
    return [{"x_mm": i * step, "force_n": k_n_per_mm * i * step} for i in range(n)]


class CompressionTimeHistoryTests(unittest.TestCase):
    def test_linear_spring_quarter_period_matches_analytic(self) -> None:
        # m=1 kg, k=1000 N/mm = 1e6 N/m, omega = sqrt(k/m) = 1000 rad/s
        # T/4 = pi/(2*omega) ~ 1.5708 ms
        loading = _linear_curve(1000.0, 50.0, n=101)
        x_max = 5.0  # arbitrary within range
        # E0 such that x_max satisfies 0.5*k*x^2 (in J): k_SI = 1e6, x_SI = 0.005
        # E0 = 0.5*1e6*(0.005)^2 = 12.5 J
        result = _compression_time_history(
            loading=loading, mass_kg=1.0, e0_j=12.5, x_max_mm=x_max, samples=200
        )
        expected_quarter = math.pi / 2.0 / math.sqrt(1e6 / 1.0)
        self.assertAlmostEqual(result["duration_s"], expected_quarter, delta=expected_quarter * 0.05)

    def test_velocity_zero_at_xmax(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        result = _compression_time_history(
            loading=loading, mass_kg=1.0, e0_j=2.0, x_max_mm=4.4721, samples=100
        )
        self.assertAlmostEqual(result["velocity_m_s"][-1], 0.0, places=2)
        self.assertGreater(result["velocity_m_s"][0], 0.0)

    def test_energy_conservation_within_tolerance(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        e0 = 2.0
        result = _compression_time_history(
            loading=loading, mass_kg=1.0, e0_j=e0, x_max_mm=4.4721, samples=200
        )
        # Sample mid-history, check 0.5*m*v^2 + E_load(x) ~ E0
        mid = len(result["time_s"]) // 2
        v = result["velocity_m_s"][mid]
        x = result["displacement_mm"][mid]
        # E_load(x) for linear F=200x: 0.5*200*x^2 / 1000 J
        e_load = 0.5 * 200.0 * x ** 2 / 1000.0
        self.assertAlmostEqual(0.5 * 1.0 * v * v + e_load, e0, delta=e0 * 0.02)


class ComputeTimeResponseTests(unittest.TestCase):
    def test_returns_none_when_solver_state_invalid(self) -> None:
        # Empty curve degenerates -> calculate_buffer_energy raises before this is called.
        # Here we test the wrapper's defensive path: pass a result dict where x_max is 0.
        fake_result = {
            "_normalized": {
                "loading": [{"x_mm": 0.0, "force_n": 0.0}],
                "unloading": [{"x_mm": 0.0, "force_n": 0.0}],
            },
            "impact": {
                "max_compression_mm": 0.0,
                "initial_energy_j": 0.0,
                "bottom_out": False,
            },
            "inputs_echo": {"impact": {"mass_kg": 1.0}, "options": {"time_samples": 100}},
        }
        out = compute_time_response(fake_result)
        self.assertIsNone(out)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_time_response.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement compression time history**

写入 `core/buffer/time_response.py`:

```python
"""Energy-conservation reconstruction of approximate time histories.

Pure post-processing on top of `calculate_buffer_energy` results. Returns
``None`` if reconstruction is numerically infeasible; never raises on
non-fatal numerical issues — surfaces them via the caller's warnings list.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence


_MM_TO_M = 1e-3
_EPS_V = 1e-6  # m/s, threshold below which we treat as singular


def _interp(xs: Sequence[float], ys: Sequence[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1] and xs[i + 1] > xs[i]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _accumulate_energy(points: Sequence[Dict[str, float]]):
    xs: List[float] = [points[0]["x_mm"]]
    es: List[float] = [0.0]
    cum = 0.0
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        cum += 0.5 * (prev["force_n"] + curr["force_n"]) * dx * _MM_TO_M
        xs.append(curr["x_mm"])
        es.append(cum)
    return xs, es


def _compression_time_history(
    *,
    loading: Sequence[Dict[str, float]],
    mass_kg: float,
    e0_j: float,
    x_max_mm: float,
    samples: int,
) -> Dict[str, Any]:
    if samples < 4:
        samples = 4
    if x_max_mm <= 0:
        raise ValueError("x_max_mm must be > 0")

    energy_xs, energy_js = _accumulate_energy(loading)
    loading_xs = [p["x_mm"] for p in loading]
    loading_fs = [p["force_n"] for p in loading]

    n = samples
    dx = x_max_mm / (n - 1)
    xs_mm = [i * dx for i in range(n)]
    forces: List[float] = [_interp(loading_xs, loading_fs, x) for x in xs_mm]
    accels: List[float] = [f / mass_kg for f in forces]

    # Velocities from energy conservation
    vels: List[float] = []
    for x in xs_mm:
        e_load = _interp(energy_xs, energy_js, x)
        kinetic = e0_j - e_load
        if kinetic <= 0:
            vels.append(0.0)
        else:
            vels.append(math.sqrt(2.0 * kinetic / mass_kg))

    # Time integration: trapezoid on dt = dx/v, with constant-acceleration
    # closure at the singular endpoint where v -> 0.
    times: List[float] = [0.0]
    for i in range(1, n):
        v_prev = vels[i - 1]
        v_curr = vels[i]
        dx_m = (xs_mm[i] - xs_mm[i - 1]) * _MM_TO_M
        if v_curr < _EPS_V:
            # Final segment: constant-acceleration approximation using a at endpoint
            a_end = max(accels[i], 1.0)  # guard zero
            dt = math.sqrt(2.0 * dx_m / a_end)
        elif v_prev < _EPS_V:
            a_start = max(accels[i - 1], 1.0)
            dt = math.sqrt(2.0 * dx_m / a_start)
        else:
            dt = 0.5 * (1.0 / v_prev + 1.0 / v_curr) * dx_m
        if not math.isfinite(dt):
            raise ValueError("non-finite dt in time integration")
        times.append(times[-1] + dt)

    return {
        "duration_s": times[-1],
        "time_s": times,
        "displacement_mm": xs_mm,
        "velocity_m_s": vels,
        "acceleration_m_s2": accels,
        "force_n": forces,
    }


def compute_time_response(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Wrap _compression_time_history (and rebound, in Task 7) into the schema."""
    impact = result.get("impact", {})
    norm = result.get("_normalized", {})
    options = result.get("inputs_echo", {}).get("options", {})
    impact_in = result.get("inputs_echo", {}).get("impact", {})

    x_max = float(impact.get("max_compression_mm", 0.0) or 0.0)
    e0 = float(impact.get("initial_energy_j", 0.0) or 0.0)
    mass_kg = float(impact_in.get("mass_kg", 0.0) or 0.0)
    samples = int(options.get("time_samples", 200))

    if x_max <= 0 or e0 <= 0 or mass_kg <= 0 or not norm.get("loading"):
        return None
    try:
        compression = _compression_time_history(
            loading=norm["loading"],
            mass_kg=mass_kg,
            e0_j=e0,
            x_max_mm=x_max,
            samples=max(4, samples // 2),
        )
    except (ValueError, ZeroDivisionError):
        return None

    # Rebound segment is added in Task 7. For now, return compression only;
    # bottom_out path also returns compression only by spec.
    return {
        "duration_s": compression["duration_s"],
        "compression_duration_s": compression["duration_s"],
        "rebound_duration_s": 0.0,
        "time_s": list(compression["time_s"]),
        "displacement_mm": list(compression["displacement_mm"]),
        "velocity_m_s": list(compression["velocity_m_s"]),
        "acceleration_m_s2": list(compression["acceleration_m_s2"]),
        "force_n": list(compression["force_n"]),
    }
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_time_response.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/buffer/time_response.py tests/core/buffer/test_time_response.py
git commit -m "feat(buffer): compression-segment time history via energy conservation"
```

---

### Task 7: Rebound segment + integrate into `calculate_buffer_energy`

**Files:**
- Modify: `core/buffer/time_response.py`
- Modify: `core/buffer/calculator.py`
- Modify: `tests/core/buffer/test_time_response.py`
- Modify: `tests/core/buffer/test_calculator.py`

- [ ] **Step 1: Write failing tests for rebound segment**

追加到 `tests/core/buffer/test_time_response.py`:

```python
class ReboundTimeHistoryTests(unittest.TestCase):
    def test_full_response_has_velocity_zero_then_negative(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        unloading = _linear_curve(100.0, 50.0)
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 2.0,
                    "available_stroke_mm": 50.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 200},
            }
        )
        tr = result["time_response"]
        self.assertIsNotNone(tr)
        # find index of max compression
        peak_idx = tr["displacement_mm"].index(max(tr["displacement_mm"]))
        self.assertAlmostEqual(tr["velocity_m_s"][peak_idx], 0.0, places=2)
        self.assertLess(tr["velocity_m_s"][-1], 0.0)
        self.assertGreater(tr["compression_duration_s"], 0.0)
        self.assertGreater(tr["rebound_duration_s"], 0.0)
        self.assertAlmostEqual(
            tr["duration_s"],
            tr["compression_duration_s"] + tr["rebound_duration_s"],
            places=6,
        )

    def test_bottom_out_returns_compression_only(self) -> None:
        loading = _linear_curve(50.0, 10.0)
        unloading = _linear_curve(25.0, 10.0)
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 5.0,
                    "available_stroke_mm": 10.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 100},
            }
        )
        self.assertTrue(result["impact"]["bottom_out"])
        tr = result["time_response"]
        self.assertIsNotNone(tr)
        self.assertEqual(tr["rebound_duration_s"], 0.0)
        # last velocity should remain non-zero (kinetic energy not depleted)
        self.assertGreater(abs(tr["velocity_m_s"][-1]), 0.5)
```

追加到 `tests/core/buffer/test_calculator.py`:

```python
class TimeResponseIntegrationTests(unittest.TestCase):
    def test_calculate_buffer_energy_includes_time_response(self) -> None:
        loading = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        unloading = [{"x_mm": x, "force_n": 100.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 2.0,
                    "available_stroke_mm": 50.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 100},
            }
        )
        self.assertIn("time_response", result)
        self.assertIsNotNone(result["time_response"])
        self.assertEqual(
            len(result["time_response"]["time_s"]),
            len(result["time_response"]["displacement_mm"]),
        )
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_time_response.py tests/core/buffer/test_calculator.py::TimeResponseIntegrationTests -v
```

- [ ] **Step 3: Implement rebound + wire into main entry**

替换 `core/buffer/time_response.py` 中 `compute_time_response` 函数为完整实现。在 `_compression_time_history` 之后追加:

```python
def _rebound_time_history(
    *,
    unloading: Sequence[Dict[str, float]],
    mass_kg: float,
    x_max_mm: float,
    samples: int,
    start_time_s: float,
) -> Dict[str, Any]:
    """Reverse-time integrate from x_max down to 0 along the unloading curve."""
    if samples < 4:
        samples = 4

    # Build truncated unloading energy curve up to x_max
    unloading_xs = [p["x_mm"] for p in unloading]
    unloading_fs = [p["force_n"] for p in unloading]

    # Energy released as x decreases from x_max to x: ∫_x^x_max F_unload(x') dx'
    n = samples
    dx = x_max_mm / (n - 1)
    xs_desc = [x_max_mm - i * dx for i in range(n)]  # x_max -> 0
    forces = [_interp(unloading_xs, unloading_fs, x) for x in xs_desc]
    accels = [-f / mass_kg for f in forces]

    # Cumulative released energy at xs_desc[i] (relative to x_max)
    rel_e: List[float] = [0.0]
    for i in range(1, n):
        f0 = forces[i - 1]
        f1 = forces[i]
        seg_dx = (xs_desc[i - 1] - xs_desc[i]) * _MM_TO_M  # positive
        rel_e.append(rel_e[-1] + 0.5 * (f0 + f1) * seg_dx)

    vels: List[float] = [
        -math.sqrt(2.0 * max(0.0, e) / mass_kg) for e in rel_e
    ]

    times: List[float] = [start_time_s]
    for i in range(1, n):
        v_prev = abs(vels[i - 1])
        v_curr = abs(vels[i])
        dx_m = (xs_desc[i - 1] - xs_desc[i]) * _MM_TO_M
        if v_prev < _EPS_V:
            a_start = max(abs(accels[i - 1]), 1.0)
            dt = math.sqrt(2.0 * dx_m / a_start)
        elif v_curr < _EPS_V:
            a_end = max(abs(accels[i]), 1.0)
            dt = math.sqrt(2.0 * dx_m / a_end)
        else:
            dt = 0.5 * (1.0 / v_prev + 1.0 / v_curr) * dx_m
        if not math.isfinite(dt):
            raise ValueError("non-finite dt in rebound integration")
        times.append(times[-1] + dt)

    return {
        "duration_s": times[-1] - start_time_s,
        "time_s": times,
        "displacement_mm": xs_desc,
        "velocity_m_s": vels,
        "acceleration_m_s2": accels,
        "force_n": forces,
    }
```

替换 `compute_time_response`:

```python
def compute_time_response(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    impact = result.get("impact", {})
    norm = result.get("_normalized", {})
    options = result.get("inputs_echo", {}).get("options", {})
    impact_in = result.get("inputs_echo", {}).get("impact", {})

    x_max = float(impact.get("max_compression_mm", 0.0) or 0.0)
    e0 = float(impact.get("initial_energy_j", 0.0) or 0.0)
    mass_kg = float(impact_in.get("mass_kg", 0.0) or 0.0)
    samples = int(options.get("time_samples", 200))
    bottom_out = bool(impact.get("bottom_out", False))

    if x_max <= 0 or e0 <= 0 or mass_kg <= 0 or not norm.get("loading"):
        return None

    half_samples = max(4, samples // 2)
    try:
        compression = _compression_time_history(
            loading=norm["loading"],
            mass_kg=mass_kg,
            e0_j=e0,
            x_max_mm=x_max,
            samples=half_samples,
        )
    except (ValueError, ZeroDivisionError):
        return None

    if bottom_out:
        return {
            "duration_s": compression["duration_s"],
            "compression_duration_s": compression["duration_s"],
            "rebound_duration_s": 0.0,
            "time_s": list(compression["time_s"]),
            "displacement_mm": list(compression["displacement_mm"]),
            "velocity_m_s": list(compression["velocity_m_s"]),
            "acceleration_m_s2": list(compression["acceleration_m_s2"]),
            "force_n": list(compression["force_n"]),
        }

    try:
        rebound = _rebound_time_history(
            unloading=norm["unloading"],
            mass_kg=mass_kg,
            x_max_mm=x_max,
            samples=half_samples,
            start_time_s=compression["duration_s"],
        )
    except (ValueError, ZeroDivisionError):
        return {
            "duration_s": compression["duration_s"],
            "compression_duration_s": compression["duration_s"],
            "rebound_duration_s": 0.0,
            "time_s": list(compression["time_s"]),
            "displacement_mm": list(compression["displacement_mm"]),
            "velocity_m_s": list(compression["velocity_m_s"]),
            "acceleration_m_s2": list(compression["acceleration_m_s2"]),
            "force_n": list(compression["force_n"]),
        }

    # Concatenate, drop duplicate seam point
    return {
        "duration_s": compression["duration_s"] + rebound["duration_s"],
        "compression_duration_s": compression["duration_s"],
        "rebound_duration_s": rebound["duration_s"],
        "time_s": list(compression["time_s"]) + list(rebound["time_s"][1:]),
        "displacement_mm": list(compression["displacement_mm"]) + list(rebound["displacement_mm"][1:]),
        "velocity_m_s": list(compression["velocity_m_s"]) + list(rebound["velocity_m_s"][1:]),
        "acceleration_m_s2": list(compression["acceleration_m_s2"]) + list(rebound["acceleration_m_s2"][1:]),
        "force_n": list(compression["force_n"]) + list(rebound["force_n"][1:]),
    }
```

修改 `core/buffer/calculator.py` 的 `calculate_buffer_energy`，在 `return` 字典构造前 import 并附加 `time_response`。把 `return` 语句之前的代码改为：

```python
    response_payload = {
        # ... existing fields above ...
    }
```

具体地，修改 `calculate_buffer_energy` 末尾的 return 块为：

```python
    base = {
        "inputs_echo": {
            "impact": dict(impact_in),
            "options": {
                "force_scale": force_scale,
                "stroke_scale": stroke_scale,
                "noise_tolerance_n": noise_tolerance,
                "time_samples": int(options.get("time_samples", 200)),
            },
        },
        "curve_summary": summary,
        "impact": impact,
        "checks": checks,
        "overall_pass": overall_pass,
        "curves": {
            "loading_x_mm": [p["x_mm"] for p in loading],
            "loading_force_n": [p["force_n"] for p in loading],
            "unloading_x_mm": [p["x_mm"] for p in unloading],
            "unloading_force_n": [p["force_n"] for p in unloading],
            "loading_energy_x_mm": energy_xs,
            "loading_energy_j": energy_js,
        },
        "_normalized": {"loading": loading, "unloading": unloading},
        "warnings": warnings,
        "assumptions": _build_assumptions(),
    }

    # Time-response is post-processing; failure must not poison the main result.
    from core.buffer.time_response import compute_time_response
    tr = compute_time_response(base)
    if tr is None:
        base["time_response"] = None
        base["warnings"].append("时域响应反推失败（数值不收敛或输入退化），仅返回能量法结果")
    else:
        base["time_response"] = tr
    base.pop("_normalized", None)
    return base
```

**注意**：`_normalized` 字段已被弹出；`compute_time_response` 不能再从外部调用 `calculate_buffer_energy` 的返回结果。`Task 6` 的测试 `test_returns_none_when_solver_state_invalid` 仍然有效，因为它构造的是 fake dict、自带 `_normalized`。

- [ ] **Step 4: Run all buffer tests**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add core/buffer/time_response.py core/buffer/calculator.py \
        tests/core/buffer/test_time_response.py tests/core/buffer/test_calculator.py
git commit -m "feat(buffer): rebound segment time history and full schema integration"
```

---

## Phase 3: Curve Import (CSV / XLSX)

### Task 8: CSV wide-table import + alias resolution

**Files:**
- Create: `core/buffer/curve_import.py`
- Create: `tests/core/buffer/test_curve_import.py`

- [ ] **Step 1: Write failing tests**

写入 `tests/core/buffer/test_curve_import.py`:

```python
"""Tests for buffer curve import (CSV / XLSX)."""

import os
import tempfile
import unittest
from pathlib import Path

from core.buffer.curve_import import InputError, load_buffer_curve


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class CSVWideTableTests(unittest.TestCase):
    def test_parses_basic_wide_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "wide.csv"
            _write(
                csv_path,
                "x_mm,loading_force_n,unloading_force_n\n"
                "0,0,0\n5,800,300\n10,1800,900\n",
            )
            result = load_buffer_curve(csv_path)
        self.assertEqual(result["metadata"]["format"], "wide")
        self.assertEqual(len(result["loading"]), 3)
        self.assertEqual(len(result["unloading"]), 3)
        self.assertEqual(result["loading"][2], {"x_mm": 10.0, "force_n": 1800.0})

    def test_supports_chinese_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "wide_cn.csv"
            _write(
                csv_path,
                "位移_mm,加载力_n,卸载力_n\n0,0,0\n5,800,300\n",
            )
            result = load_buffer_curve(csv_path)
        self.assertEqual(len(result["loading"]), 2)
        self.assertEqual(result["unloading"][1]["force_n"], 300.0)

    def test_missing_displacement_column_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "bad.csv"
            _write(csv_path, "loading_force_n,unloading_force_n\n0,0\n")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(csv_path)
            self.assertIn("位移", str(ctx.exception))

    def test_unknown_extension_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "data.txt"
            _write(bad, "x_mm,loading_force_n\n0,0\n")
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(bad)
            self.assertIn("文件类型", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_curve_import.py -v
```

- [ ] **Step 3: Implement CSV wide-table loader + alias resolution**

写入 `core/buffer/curve_import.py`:

```python
"""CSV / XLSX loader for buffer-block test curves.

`openpyxl` is imported lazily inside the XLSX branch so the dependency
does not affect application startup time.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


class InputError(ValueError):
    """Raised when a curve file cannot be parsed."""


_DISPLACEMENT_ALIASES = {"x_mm", "displacement_mm", "位移_mm", "x", "displacement"}
_LOADING_ALIASES = {"loading_force_n", "force_loading_n", "加载力_n", "loading", "f_load"}
_UNLOADING_ALIASES = {"unloading_force_n", "force_unloading_n", "卸载力_n", "unloading", "f_unload"}
_BRANCH_ALIASES = {"branch", "phase", "曲线"}
_FORCE_ALIASES = {"force_n", "力_n", "force", "f"}

_BRANCH_LOAD_VALUES = {"loading", "load", "加载", "压缩"}
_BRANCH_UNLOAD_VALUES = {"unloading", "unload", "卸载", "回弹"}


def _normalize_header(name: str) -> str:
    return name.strip().lstrip("﻿").lower()


def _match_column(headers: Sequence[str], aliases: set) -> int:
    lowered = [_normalize_header(h) for h in headers]
    for i, h in enumerate(lowered):
        if h in {a.lower() for a in aliases}:
            return i
    return -1


def _to_float(value: str, label: str, row: int) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise InputError(f"{label} 第 {row} 行不是数字: {value!r}") from exc


def _read_csv_rows(path: Path) -> Tuple[List[str], List[List[str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
    except UnicodeDecodeError:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
    if not rows:
        raise InputError("CSV 文件为空")
    headers = rows[0]
    if not any(h.strip() for h in headers):
        raise InputError("CSV 缺少表头")
    data = [r for r in rows[1:] if any(c.strip() for c in r)]
    return headers, data


def _parse_wide_table(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> Dict[str, Any]:
    x_idx = _match_column(headers, _DISPLACEMENT_ALIASES)
    load_idx = _match_column(headers, _LOADING_ALIASES)
    unload_idx = _match_column(headers, _UNLOADING_ALIASES)
    if x_idx < 0:
        raise InputError("未识别到位移列（支持: x_mm/displacement_mm/位移_mm）")
    if load_idx < 0:
        raise InputError("未识别到加载曲线（支持: loading_force_n/加载力_n 等）")
    if unload_idx < 0:
        raise InputError("未识别到卸载曲线（支持: unloading_force_n/卸载力_n 等）")

    loading: List[Dict[str, float]] = []
    unloading: List[Dict[str, float]] = []
    for r, row in enumerate(rows, start=2):
        if len(row) <= max(x_idx, load_idx, unload_idx):
            raise InputError(f"第 {r} 行列数不足")
        x = _to_float(row[x_idx], "位移", r)
        f_load = _to_float(row[load_idx], "加载力", r)
        f_unload = _to_float(row[unload_idx], "卸载力", r)
        loading.append({"x_mm": x, "force_n": f_load})
        unloading.append({"x_mm": x, "force_n": f_unload})

    return {
        "loading": loading,
        "unloading": unloading,
        "metadata": {
            "format": "wide",
            "rows": len(rows),
            "loading_count": len(loading),
            "unloading_count": len(unloading),
        },
    }


def load_buffer_curve(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".csv":
        headers, rows = _read_csv_rows(p)
        # Long-table & XLSX support added in Tasks 9 / 10
        return _parse_wide_table(headers, rows)
    if suffix == ".xlsx":
        # Implemented in Task 10
        raise InputError("XLSX 暂不支持（待 Task 10 实现）")
    raise InputError(f"文件类型不支持，仅支持 .csv / .xlsx (当前: {suffix})")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_curve_import.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/buffer/curve_import.py tests/core/buffer/test_curve_import.py
git commit -m "feat(buffer): CSV wide-table import with alias resolution"
```

---

### Task 9: CSV long-table import (bilingual branch values)

**Files:**
- Modify: `core/buffer/curve_import.py`
- Modify: `tests/core/buffer/test_curve_import.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/core/buffer/test_curve_import.py`:

```python
class CSVLongTableTests(unittest.TestCase):
    def test_parses_basic_long_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.csv"
            _write(
                path,
                "branch,x_mm,force_n\n"
                "loading,0,0\nloading,5,800\nloading,10,1800\n"
                "unloading,10,900\nunloading,5,300\nunloading,0,0\n",
            )
            result = load_buffer_curve(path)
        self.assertEqual(result["metadata"]["format"], "long")
        self.assertEqual(len(result["loading"]), 3)
        self.assertEqual(len(result["unloading"]), 3)

    def test_long_table_chinese_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long_cn.csv"
            _write(
                path,
                "曲线,位移_mm,力_n\n"
                "加载,0,0\n加载,10,1800\n"
                "卸载,10,900\n卸载,0,0\n",
            )
            result = load_buffer_curve(path)
        self.assertEqual(len(result["loading"]), 2)
        self.assertEqual(result["unloading"][0]["force_n"], 900.0)

    def test_unknown_branch_value_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long_bad.csv"
            _write(
                path,
                "branch,x_mm,force_n\nbogus,0,0\nloading,10,1800\n",
            )
            with self.assertRaises(InputError) as ctx:
                load_buffer_curve(path)
            self.assertIn("branch", str(ctx.exception).lower())
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_curve_import.py::CSVLongTableTests -v
```

- [ ] **Step 3: Implement long-table parsing**

修改 `core/buffer/curve_import.py`：在 `_parse_wide_table` 之后追加：

```python
def _parse_long_table(
    headers: Sequence[str], rows: Sequence[Sequence[str]]
) -> Dict[str, Any]:
    branch_idx = _match_column(headers, _BRANCH_ALIASES)
    x_idx = _match_column(headers, _DISPLACEMENT_ALIASES)
    f_idx = _match_column(headers, _FORCE_ALIASES)
    if branch_idx < 0 or x_idx < 0 or f_idx < 0:
        raise InputError("长表必须含 branch / 位移 / 力 三列")

    loading: List[Dict[str, float]] = []
    unloading: List[Dict[str, float]] = []
    for r, row in enumerate(rows, start=2):
        if len(row) <= max(branch_idx, x_idx, f_idx):
            raise InputError(f"第 {r} 行列数不足")
        branch_raw = row[branch_idx].strip().lower()
        if branch_raw in {b.lower() for b in _BRANCH_LOAD_VALUES}:
            target = loading
        elif branch_raw in {b.lower() for b in _BRANCH_UNLOAD_VALUES}:
            target = unloading
        else:
            raise InputError(
                f"第 {r} 行 branch 值 {row[branch_idx]!r} 无法识别 "
                "(支持 loading/load/加载/压缩 / unloading/unload/卸载/回弹)"
            )
        x = _to_float(row[x_idx], "位移", r)
        f = _to_float(row[f_idx], "力", r)
        target.append({"x_mm": x, "force_n": f})

    if not loading:
        raise InputError("长表未识别到加载曲线")
    if not unloading:
        raise InputError("长表未识别到卸载曲线")

    return {
        "loading": loading,
        "unloading": unloading,
        "metadata": {
            "format": "long",
            "rows": len(rows),
            "loading_count": len(loading),
            "unloading_count": len(unloading),
        },
    }


def _detect_format(headers: Sequence[str]) -> str:
    """Return 'wide' if headers contain a loading-force column, 'long' if branch."""
    if _match_column(headers, _LOADING_ALIASES) >= 0 and _match_column(headers, _UNLOADING_ALIASES) >= 0:
        return "wide"
    if _match_column(headers, _BRANCH_ALIASES) >= 0 and _match_column(headers, _FORCE_ALIASES) >= 0:
        return "long"
    raise InputError(
        "无法识别表格形态：宽表需 loading/unloading 力列，长表需 branch + force 列"
    )
```

修改 `load_buffer_curve` 的 CSV 分支：

```python
    if suffix == ".csv":
        headers, rows = _read_csv_rows(p)
        fmt = _detect_format(headers)
        if fmt == "wide":
            return _parse_wide_table(headers, rows)
        return _parse_long_table(headers, rows)
```

- [ ] **Step 4: Run tests, verify all pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_curve_import.py -v
```

- [ ] **Step 5: Commit**

```bash
git add core/buffer/curve_import.py tests/core/buffer/test_curve_import.py
git commit -m "feat(buffer): CSV long-table import with bilingual branch values"
```

---

### Task 10: XLSX import (lazy openpyxl) + dependency update

**Files:**
- Modify: `core/buffer/curve_import.py`
- Modify: `requirements.txt`
- Modify: `tests/core/buffer/test_curve_import.py`

- [ ] **Step 1: Add openpyxl dependency**

修改 `requirements.txt`，在末尾追加（保留原有内容）：

```
openpyxl>=3.1
```

- [ ] **Step 2: Install and write failing test**

```bash
python3 -m pip install -r requirements.txt
```

追加到 `tests/core/buffer/test_curve_import.py`:

```python
class XLSXImportTests(unittest.TestCase):
    def _write_xlsx(self, path: Path, headers, rows) -> None:
        from openpyxl import Workbook  # local import is fine in tests

        wb = Workbook()
        ws = wb.active
        ws.append(list(headers))
        for r in rows:
            ws.append(list(r))
        wb.save(path)

    def test_parses_xlsx_wide_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wide.xlsx"
            self._write_xlsx(
                path,
                ["x_mm", "loading_force_n", "unloading_force_n"],
                [(0, 0, 0), (5, 800, 300), (10, 1800, 900)],
            )
            result = load_buffer_curve(path)
        self.assertEqual(result["metadata"]["format"], "wide")
        self.assertEqual(len(result["loading"]), 3)

    def test_parses_xlsx_long_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "long.xlsx"
            self._write_xlsx(
                path,
                ["branch", "x_mm", "force_n"],
                [
                    ("loading", 0, 0),
                    ("loading", 10, 1800),
                    ("unloading", 10, 900),
                    ("unloading", 0, 0),
                ],
            )
            result = load_buffer_curve(path)
        self.assertEqual(result["metadata"]["format"], "long")

    def test_openpyxl_not_imported_when_loading_csv(self) -> None:
        """Smoke check: importing curve_import does not pre-import openpyxl."""
        import importlib
        import sys

        for mod in list(sys.modules):
            if mod == "openpyxl" or mod.startswith("openpyxl."):
                del sys.modules[mod]
        importlib.reload(importlib.import_module("core.buffer.curve_import"))
        self.assertNotIn("openpyxl", sys.modules)
```

- [ ] **Step 3: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/test_curve_import.py::XLSXImportTests -v
```

- [ ] **Step 4: Implement lazy XLSX loader**

追加到 `core/buffer/curve_import.py`:

```python
def _read_xlsx_rows(path: Path) -> Tuple[List[str], List[List[str]]]:
    # Lazy import — keeps app startup unaffected for users who never open .xlsx.
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise InputError("缺少依赖 openpyxl，请 pip install openpyxl") from exc

    try:
        wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    except Exception as exc:
        raise InputError(f"无法打开 XLSX 文件: {exc}") from exc
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration as exc:
        raise InputError("XLSX 工作表为空") from exc
    headers = ["" if v is None else str(v) for v in header_row]
    if not any(h.strip() for h in headers):
        raise InputError("XLSX 缺少表头")
    data: List[List[str]] = []
    for row in rows_iter:
        cells = ["" if v is None else str(v) for v in row]
        if any(c.strip() for c in cells):
            data.append(cells)
    return headers, data
```

修改 `load_buffer_curve` 的 XLSX 分支：

```python
    if suffix == ".xlsx":
        headers, rows = _read_xlsx_rows(p)
        fmt = _detect_format(headers)
        if fmt == "wide":
            return _parse_wide_table(headers, rows)
        return _parse_long_table(headers, rows)
```

- [ ] **Step 5: Run tests, commit**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/ -v
```

```bash
git add core/buffer/curve_import.py requirements.txt tests/core/buffer/test_curve_import.py
git commit -m "feat(buffer): XLSX import with lazy openpyxl + dependency"
```

---

## Phase 4: Test Fixtures (Examples & Inputs)

### Task 11: Sample CSV / XLSX / input-conditions JSON

**Files:**
- Create: `examples/buffer_energy_case_01.csv`
- Create: `examples/buffer_energy_case_02.xlsx` (生成脚本一次性运行)
- Create: `examples/buffer_energy_input_conditions.json`

- [ ] **Step 1: Write CSV sample (case 01, wide table, soft polymer)**

写入 `examples/buffer_energy_case_01.csv`:

```csv
x_mm,loading_force_n,unloading_force_n
0,0,0
2,160,40
4,360,120
6,620,240
8,940,400
10,1320,600
12,1760,830
14,2260,1100
16,2820,1410
18,3440,1760
20,4120,2150
22,4860,2580
24,5660,3050
26,6520,3560
28,7440,4110
30,8420,4700
```

- [ ] **Step 2: Write Python script and generate case 02 XLSX (long table, progressive hardening)**

执行（一次性 generator，不入库）：

```bash
python3 - << 'PY'
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "long"
ws.append(["branch", "x_mm", "force_n"])

# Loading: progressive hardening F = 30*x + 4*x^2 (N), 0..25 mm
for x in range(0, 26):
    ws.append(["loading", x, 30 * x + 4 * x * x])

# Unloading: 50% area retained, smooth descent, 25 mm down to 0
for x in range(25, -1, -1):
    f = (30 * x + 4 * x * x) * 0.45 if x > 0 else 0
    ws.append(["unloading", x, round(f, 2)])

wb.save("examples/buffer_energy_case_02.xlsx")
print("wrote case 02")
PY
```

- [ ] **Step 3: Write input-conditions JSON**

写入 `examples/buffer_energy_input_conditions.json`:

```json
{
  "module": "buffer_energy",
  "version": 1,
  "fields": {
    "impact.mass_kg": "12.0",
    "impact.initial_velocity_m_s": "1.5",
    "impact.available_stroke_mm": "30.0",
    "impact.allowable_peak_force_n": "9000",
    "options.force_scale": "1.00",
    "options.stroke_scale": "1.00",
    "options.noise_tolerance_n": "5.0",
    "options.time_samples": "200"
  }
}
```

- [ ] **Step 4: Verify samples roundtrip via the loader**

```bash
QT_QPA_PLATFORM=offscreen python3 - << 'PY'
from pathlib import Path
from core.buffer.curve_import import load_buffer_curve
from core.buffer.calculator import calculate_buffer_energy

for name in ("buffer_energy_case_01.csv", "buffer_energy_case_02.xlsx"):
    curve = load_buffer_curve(Path("examples") / name)
    print(name, curve["metadata"])
    result = calculate_buffer_energy({
        "curve": {"loading": curve["loading"], "unloading": curve["unloading"]},
        "impact": {
            "mass_kg": 12.0, "initial_velocity_m_s": 1.5,
            "available_stroke_mm": 30.0, "allowable_peak_force_n": 9000.0,
        },
        "options": {"time_samples": 100},
    })
    print("  bottom_out=", result["impact"]["bottom_out"],
          "x_max=", round(result["impact"]["max_compression_mm"], 2),
          "duration_s=", round(result["time_response"]["duration_s"] * 1000, 2), "ms")
PY
```

Expected: 两个案例都成功打印且 `bottom_out=False`。

- [ ] **Step 5: Commit**

```bash
git add examples/buffer_energy_case_01.csv examples/buffer_energy_case_02.xlsx \
        examples/buffer_energy_input_conditions.json
git commit -m "feat(buffer): sample curves and default input conditions"
```

---

## Phase 5: UI Widgets (QPainter custom drawing)

### Task 12: `BufferEnergyCurveWidget` (F-x with hysteresis fill + annotations)

**Files:**
- Create: `app/ui/widgets/buffer_energy_curve.py`
- Create test stub: `tests/ui/test_buffer_energy_page.py` (only widget smoke; full page tests in Phase 6)

- [ ] **Step 1: Write failing widget smoke test**

写入 `tests/ui/test_buffer_energy_page.py`（先放 widget 部分；后续 task 追加页面测试）:

```python
"""Smoke tests for buffer-energy UI."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.widgets.buffer_energy_curve import BufferEnergyCurveWidget


class BufferEnergyCurveWidgetSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_constructs_with_no_data(self) -> None:
        w = BufferEnergyCurveWidget()
        w.resize(400, 300)
        # Should not crash on paint
        w.repaint()

    def test_set_curves_updates_geometry(self) -> None:
        w = BufferEnergyCurveWidget()
        w.set_curves(
            loading=[(0.0, 0.0), (5.0, 800.0), (10.0, 1800.0)],
            unloading=[(0.0, 0.0), (5.0, 300.0), (10.0, 900.0)],
            x_max_mm=4.0,
            available_stroke_mm=10.0,
            allowable_peak_n=2000.0,
            bottom_out=False,
        )
        w.resize(400, 300)
        w.repaint()

    def test_handles_bottom_out_flag(self) -> None:
        w = BufferEnergyCurveWidget()
        w.set_curves(
            loading=[(0.0, 0.0), (10.0, 1800.0)],
            unloading=[(0.0, 0.0), (10.0, 900.0)],
            x_max_mm=10.0,
            available_stroke_mm=12.0,
            allowable_peak_n=2000.0,
            bottom_out=True,
        )
        w.resize(400, 300)
        w.repaint()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

Expected: ImportError on widget module.

- [ ] **Step 3: Implement widget**

写入 `app/ui/widgets/buffer_energy_curve.py`:

```python
"""F-x curve widget for buffer energy module (QPainter custom-drawn)."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


_BG = QColor("#FBFAF7")
_GRID = QColor("#E5E0D6")
_LOADING = QColor("#D97757")
_UNLOADING = QColor("#7A8DA8")
_FILL = QColor(217, 119, 87, 50)        # translucent loading orange
_MARKER = QColor("#3F2E1E")
_LIMIT_LINE = QColor("#A85033")
_BOTTOM_OUT = QColor(168, 80, 51, 90)


class BufferEnergyCurveWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._loading: List[Tuple[float, float]] = []
        self._unloading: List[Tuple[float, float]] = []
        self._x_max_mm = 0.0
        self._available_stroke_mm = 0.0
        self._allowable_peak_n = 0.0
        self._bottom_out = False
        self.setMinimumHeight(280)
        self.setFont(make_ui_font())

    def set_curves(
        self,
        *,
        loading: Sequence[Tuple[float, float]],
        unloading: Sequence[Tuple[float, float]],
        x_max_mm: float,
        available_stroke_mm: float,
        allowable_peak_n: float,
        bottom_out: bool,
    ) -> None:
        self._loading = [(float(x), float(f)) for x, f in loading]
        self._unloading = [(float(x), float(f)) for x, f in unloading]
        self._x_max_mm = float(x_max_mm)
        self._available_stroke_mm = float(available_stroke_mm)
        self._allowable_peak_n = float(allowable_peak_n)
        self._bottom_out = bool(bottom_out)
        self.update()

    def paintEvent(self, _evt) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(48, 16, -16, -36)
        painter.fillRect(self.rect(), _BG)

        if not self._loading or not self._unloading:
            painter.setPen(QColor("#8B7E68"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "导入曲线后显示 F-x 关系")
            return

        max_x = max(
            self._available_stroke_mm,
            max((x for x, _ in self._loading), default=0.0),
            max((x for x, _ in self._unloading), default=0.0),
            1.0,
        )
        max_f = max(
            self._allowable_peak_n,
            max((f for _, f in self._loading), default=0.0),
            max((f for _, f in self._unloading), default=0.0),
            1.0,
        ) * 1.05

        def to_px(x: float, f: float) -> QPointF:
            px = rect.left() + (x / max_x) * rect.width()
            py = rect.bottom() - (f / max_f) * rect.height()
            return QPointF(px, py)

        # Grid + axes
        painter.setPen(QPen(_GRID, 1))
        for i in range(1, 5):
            y = rect.top() + i * rect.height() / 5
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        painter.setPen(QPen(QColor("#3F2E1E"), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())

        # Bottom-out shaded zone (between effective stroke and available stroke)
        if self._bottom_out and self._available_stroke_mm > self._x_max_mm:
            zone = QRectF(
                to_px(self._x_max_mm, max_f).x(),
                rect.top(),
                to_px(self._available_stroke_mm, 0).x() - to_px(self._x_max_mm, 0).x(),
                rect.height(),
            )
            painter.fillRect(zone, _BOTTOM_OUT)

        # Hysteresis fill (loading minus unloading)
        path = QPainterPath()
        path.moveTo(to_px(*self._loading[0]))
        for pt in self._loading[1:]:
            path.lineTo(to_px(*pt))
        for pt in reversed(self._unloading):
            path.lineTo(to_px(*pt))
        path.closeSubpath()
        painter.fillPath(path, _FILL)

        # Loading curve
        painter.setPen(QPen(_LOADING, 2))
        for a, b in zip(self._loading, self._loading[1:]):
            painter.drawLine(to_px(*a), to_px(*b))
        # Unloading curve
        painter.setPen(QPen(_UNLOADING, 2, Qt.PenStyle.DashLine))
        for a, b in zip(self._unloading, self._unloading[1:]):
            painter.drawLine(to_px(*a), to_px(*b))

        # Available stroke vertical line
        painter.setPen(QPen(_LIMIT_LINE, 1, Qt.PenStyle.DotLine))
        x_line = to_px(self._available_stroke_mm, 0).x()
        painter.drawLine(QPointF(x_line, rect.top()), QPointF(x_line, rect.bottom()))

        # Allowable peak horizontal line
        y_line = to_px(0.0, self._allowable_peak_n).y()
        painter.drawLine(QPointF(rect.left(), y_line), QPointF(rect.right(), y_line))

        # Max-compression marker
        if self._x_max_mm > 0:
            f_at_xmax = self._interp_loading(self._x_max_mm)
            cx = to_px(self._x_max_mm, f_at_xmax)
            painter.setPen(QPen(_MARKER, 1.5))
            painter.setBrush(_MARKER)
            painter.drawEllipse(cx, 4.0, 4.0)
            painter.drawText(
                cx + QPointF(6, -6),
                f"x_max={self._x_max_mm:.2f} mm  F={f_at_xmax:.0f} N",
            )

        # Axis labels
        painter.setPen(QColor("#3F2E1E"))
        painter.drawText(rect.bottomRight() + QPointF(-60, 24), "位移 mm")
        painter.drawText(rect.topLeft() + QPointF(-44, -4), "力 N")

    def _interp_loading(self, x: float) -> float:
        for (x0, f0), (x1, f1) in zip(self._loading, self._loading[1:]):
            if x0 <= x <= x1 and x1 > x0:
                t = (x - x0) / (x1 - x0)
                return f0 + t * (f1 - f0)
        return self._loading[-1][1]
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/widgets/buffer_energy_curve.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): F-x curve widget with hysteresis fill and annotations"
```

---

### Task 13: `BufferResponseCurveWidget` (time-domain `x/v/a/F` switch)

**Files:**
- Create: `app/ui/widgets/buffer_response_curve.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
from app.ui.widgets.buffer_response_curve import BufferResponseCurveWidget


class BufferResponseCurveWidgetSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _sample_response(self) -> dict:
        n = 50
        import math
        ts = [i * 1e-3 for i in range(n)]
        xs = [10.0 * math.sin(math.pi * i / (n - 1)) for i in range(n)]
        vs = [10.0 * math.cos(math.pi * i / (n - 1)) for i in range(n)]
        accs = [-100.0 * math.sin(math.pi * i / (n - 1)) for i in range(n)]
        forces = [200.0 * x for x in xs]
        return {
            "time_s": ts,
            "displacement_mm": xs,
            "velocity_m_s": vs,
            "acceleration_m_s2": accs,
            "force_n": forces,
            "duration_s": ts[-1],
            "compression_duration_s": ts[n // 2],
            "rebound_duration_s": ts[-1] - ts[n // 2],
        }

    def test_constructs_empty(self) -> None:
        w = BufferResponseCurveWidget()
        w.resize(400, 280)
        w.repaint()

    def test_switch_variable_does_not_raise(self) -> None:
        w = BufferResponseCurveWidget()
        w.set_response(self._sample_response())
        for var in ("x", "v", "a", "F"):
            w.set_variable(var)
            w.repaint()

    def test_invalid_variable_raises(self) -> None:
        w = BufferResponseCurveWidget()
        with self.assertRaises(ValueError):
            w.set_variable("xyz")
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferResponseCurveWidgetSmokeTests -v
```

- [ ] **Step 3: Implement widget**

写入 `app/ui/widgets/buffer_response_curve.py`:

```python
"""Time-domain response widget (x/v/a/F switchable) for buffer energy module."""

from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


_BG = QColor("#FBFAF7")
_GRID = QColor("#E5E0D6")
_AXIS = QColor("#3F2E1E")
_CURVE = QColor("#3D6B8E")
_PEAK = QColor("#A85033")

_VARIABLES = {
    "x": ("displacement_mm", "位移 (mm)"),
    "v": ("velocity_m_s", "速度 (m/s)"),
    "a": ("acceleration_m_s2", "加速度 (m/s²)"),
    "F": ("force_n", "反力 (N)"),
}


class BufferResponseCurveWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._response: Optional[Dict[str, Any]] = None
        self._variable = "x"
        self.setMinimumHeight(260)
        self.setFont(make_ui_font())

    def set_response(self, response: Optional[Dict[str, Any]]) -> None:
        self._response = response
        self.update()

    def set_variable(self, variable: str) -> None:
        if variable not in _VARIABLES:
            raise ValueError(f"未知变量: {variable!r} (可选: x/v/a/F)")
        self._variable = variable
        self.update()

    def variable(self) -> str:
        return self._variable

    def paintEvent(self, _evt) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), _BG)
        rect = self.rect().adjusted(56, 28, -16, -36)

        # Header text (durations)
        painter.setPen(_AXIS)
        if self._response:
            comp = self._response.get("compression_duration_s", 0.0) * 1000.0
            reb = self._response.get("rebound_duration_s", 0.0) * 1000.0
            tot = self._response.get("duration_s", 0.0) * 1000.0
            painter.drawText(
                self.rect().adjusted(8, 4, -8, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                f"压缩 {comp:.2f} ms  回弹 {reb:.2f} ms  总时长 {tot:.2f} ms",
            )

        if self._response is None:
            painter.setPen(QColor("#8B7E68"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "执行计算后显示时域响应")
            return

        key, axis_label = _VARIABLES[self._variable]
        ys = list(self._response.get(key, []))
        ts = list(self._response.get("time_s", []))
        if len(ys) < 2 or len(ts) != len(ys):
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "时域响应数据不足")
            return

        t_min = ts[0]
        t_max = max(ts[-1], t_min + 1e-9)
        y_min = min(ys)
        y_max = max(ys)
        if abs(y_max - y_min) < 1e-12:
            y_max = y_min + 1.0
        y_pad = 0.10 * (y_max - y_min)
        y_min -= y_pad
        y_max += y_pad

        def to_px(t: float, y: float) -> QPointF:
            px = rect.left() + (t - t_min) / (t_max - t_min) * rect.width()
            py = rect.bottom() - (y - y_min) / (y_max - y_min) * rect.height()
            return QPointF(px, py)

        # Grid
        painter.setPen(QPen(_GRID, 1))
        for i in range(1, 5):
            y = rect.top() + i * rect.height() / 5
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        # Zero line if range crosses zero
        if y_min < 0 < y_max:
            zero_y = to_px(t_min, 0).y()
            painter.setPen(QPen(QColor("#B0A188"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(rect.left(), zero_y), QPointF(rect.right(), zero_y))

        painter.setPen(QPen(_AXIS, 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topLeft(), rect.bottomLeft())

        # Curve
        painter.setPen(QPen(_CURVE, 2))
        for i in range(len(ts) - 1):
            painter.drawLine(to_px(ts[i], ys[i]), to_px(ts[i + 1], ys[i + 1]))

        # Peak / max-compression marker (when var is x or F, mark argmax)
        if self._variable in ("x", "F"):
            idx = max(range(len(ys)), key=lambda i: ys[i])
            pt = to_px(ts[idx], ys[idx])
            painter.setBrush(_PEAK)
            painter.setPen(QPen(_PEAK, 1))
            painter.drawEllipse(pt, 3.5, 3.5)

        # Labels
        painter.setPen(_AXIS)
        painter.drawText(rect.bottomRight() + QPointF(-60, 24), "时间 s")
        painter.drawText(rect.topLeft() + QPointF(-50, -8), axis_label)
        painter.drawText(rect.bottomLeft() + QPointF(-40, 14), f"{y_min:.1f}")
        painter.drawText(rect.topLeft() + QPointF(-40, 8), f"{y_max:.1f}")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/widgets/buffer_response_curve.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): time-domain response widget with x/v/a/F switching"
```

---

## Phase 6: UI Page (BufferEnergyPage with 7 chapters + Scheme A workbench)

**实现策略**：UI 页面较大，分 6 个 task（14–19）。Task 14 搭骨架（actions、章节框架、免责横幅、方案 A 工作台总览占位）；Tasks 15–17 逐章填充。`吸能结果` 章节必须是一屏式工作台：中央关键指标 + F-x 曲线 + 能量条，右侧总体结论 / 模型边界 / 参数对比摘要。`响应时程` 和 `参数对比` 章节保留为详细页。Task 18 报告导出 + sample 加载 + 输入条件保存；Task 19 综合 UI smoke + 集成测试。

参考实现样板：`app/ui/pages/hertz_contact_page.py`（章节构造、`FieldSpec` 用法、`_create_editor` / `_create_chapter_page` 私有 helper、`_apply_defaults`、`_build_payload`、`_render_result`、`_save_input_conditions` / `_load_input_conditions` 与 `input_condition_store` 的对接）。

### Task 14: Page skeleton + actions + Scheme A workbench overview

**Files:**
- Create: `app/ui/pages/buffer_energy_page.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
from app.ui.pages.buffer_energy_page import BufferEnergyPage


class BufferEnergyPageSkeletonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_page_constructs(self) -> None:
        page = BufferEnergyPage()
        self.assertIsNotNone(page)

    def test_seven_chapters_registered(self) -> None:
        page = BufferEnergyPage()
        self.assertEqual(page.chapter_list.count(), 7)

    def test_disclaimer_banner_visible(self) -> None:
        page = BufferEnergyPage()
        self.assertTrue(page.disclaimer_label.isVisible() or not page.disclaimer_label.isHidden())
        self.assertIn("能量法", page.disclaimer_label.text())

    def test_action_buttons_present(self) -> None:
        page = BufferEnergyPage()
        # Must have these buttons by name (used by tests below)
        for attr in ("btn_import_curve", "btn_save_inputs", "btn_load_inputs",
                     "btn_calculate", "btn_clear", "btn_save_report",
                     "btn_load_1", "btn_load_2"):
            self.assertTrue(hasattr(page, attr), f"missing {attr}")

    def test_scheme_a_workbench_widgets_present(self) -> None:
        page = BufferEnergyPage()
        for attr in (
            "metric_labels",
            "overview_curve_widget",
            "energy_strip_label",
            "overall_verdict_label",
            "model_boundary_label",
            "compare_preview_table",
            "results_label",
        ):
            self.assertTrue(hasattr(page, attr), f"missing {attr}")
        self.assertIn("initial_energy", page.metric_labels)
        self.assertEqual(page.compare_preview_table.columnCount(), 4)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyPageSkeletonTests -v
```

- [ ] **Step 3: Implement skeleton**

写入 `app/ui/pages/buffer_energy_page.py`:

```python
"""Buffer block energy simulation chapter page."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.fonts import make_ui_font
from app.ui.input_condition_store import (
    build_form_snapshot,
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    read_input_conditions,
    write_input_conditions,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import export_report_lines
from app.ui.widgets.buffer_energy_curve import BufferEnergyCurveWidget
from app.ui.widgets.buffer_response_curve import BufferResponseCurveWidget
from core.buffer.calculator import InputError, calculate_buffer_energy
from core.buffer.curve_import import (
    InputError as CurveInputError,
    load_buffer_curve,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)

DISCLAIMER_TEXT = (
    "本工具基于准静态 F-x 曲线的单次冲击能量法。回弹速度与时域响应均为反推估算值，"
    "不含应变率效应，不能替代真实时域仿真。"
)


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    label: str
    unit: str
    hint: str
    mapping: Optional[Tuple[str, str]] = None
    default: str = ""
    placeholder: str = ""


IMPACT_FIELDS: List[FieldSpec] = [
    FieldSpec("impact.mass_kg", "冲击质量 m", "kg",
              "撞击物等效质量。", mapping=("impact", "mass_kg"),
              default="12.0", placeholder="例如 12.0"),
    FieldSpec("impact.initial_velocity_m_s", "初始速度 v₀", "m/s",
              "撞击瞬间的速度。", mapping=("impact", "initial_velocity_m_s"),
              default="1.5", placeholder="例如 1.5"),
    FieldSpec("impact.available_stroke_mm", "可用行程", "mm",
              "缓冲块允许的最大压缩位移。", mapping=("impact", "available_stroke_mm"),
              default="30.0", placeholder="例如 30"),
    FieldSpec("impact.allowable_peak_force_n", "允许峰值力", "N",
              "结构允许的最大反力。", mapping=("impact", "allowable_peak_force_n"),
              default="9000", placeholder="例如 9000"),
    FieldSpec("options.force_scale", "曲线力倍率", "-",
              "对加载/卸载曲线力值统一缩放，做敏感度分析。",
              mapping=("options", "force_scale"), default="1.00"),
    FieldSpec("options.stroke_scale", "曲线行程倍率", "-",
              "对加载/卸载曲线行程统一缩放。",
              mapping=("options", "stroke_scale"), default="1.00"),
    FieldSpec("options.noise_tolerance_n", "卸载噪声容差", "N",
              "局部卸载力高于加载力的容差阈值。",
              mapping=("options", "noise_tolerance_n"), default="5.0"),
    FieldSpec("options.time_samples", "时域采样点数", "点",
              "时域反推总采样点（压缩+回弹），默认 200。",
              mapping=("options", "time_samples"), default="200"),
]


class BufferEnergyPage(BaseChapterPage):
    """Single-impact buffer-block energy method, 7-chapter workflow."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            title="缓冲块吸能仿真",
            subtitle="导入加载/卸载 F-x 测试曲线，按能量法求解单次冲击响应并反推近似时域曲线。",
            parent=parent,
        )
        self._curve_data: Optional[Dict[str, Any]] = None
        self._curve_source: Optional[Path] = None
        self._last_payload: Optional[Dict[str, Any]] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._field_widgets: Dict[str, QWidget] = {}
        self._field_specs: Dict[str, FieldSpec] = {s.field_id: s for s in IMPACT_FIELDS}

        self._build_disclaimer_banner()

        # Action buttons
        self.btn_import_curve = self.add_action_button("导入曲线文件", primary=True)
        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行仿真", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_save_report = self.add_action_button("导出结果说明")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")
        self.btn_save_report.setEnabled(False)

        # Build chapter pages (placeholder bodies — filled in Tasks 15-17)
        self.overview_curve_widget = BufferEnergyCurveWidget()
        self.curve_check_widget = BufferEnergyCurveWidget()
        self.response_widget = BufferResponseCurveWidget()
        self._build_chapter_curve_import()
        self._build_chapter_curve_check()
        self._build_chapter_impact_inputs()
        self._build_chapter_energy_results()
        self._build_chapter_time_response()
        self._build_chapter_parameter_compare()
        self._build_chapter_export_doc()
        self.set_current_chapter(0)

        # Wire actions
        self.btn_import_curve.clicked.connect(self._on_import_curve)
        self.btn_save_inputs.clicked.connect(self._on_save_inputs)
        self.btn_load_inputs.clicked.connect(self._on_load_inputs)
        self.btn_calculate.clicked.connect(self._on_calculate)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_save_report.clicked.connect(self._on_save_report)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("buffer_energy_case_01.csv"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("buffer_energy_case_02.xlsx"))

        self._apply_defaults()

    # ---------- Layout helpers ----------

    def _build_disclaimer_banner(self) -> None:
        self.disclaimer_label = QLabel(DISCLAIMER_TEXT, self)
        self.disclaimer_label.setObjectName("WarnBanner")
        self.disclaimer_label.setWordWrap(True)
        # Insert disclaimer right under the header (above actions)
        layout: QVBoxLayout = self.layout()  # type: ignore[assignment]
        layout.insertWidget(1, self.disclaimer_label)

    def _build_chapter_curve_import(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QLabel("测试曲线导入", page)
        title.setObjectName("SectionTitle")
        v.addWidget(title)
        hint = QLabel(
            "支持 CSV / XLSX，宽表（x_mm / loading_force_n / unloading_force_n）或长表"
            "（branch / x_mm / force_n）。表头允许中文别名。",
            page,
        )
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.curve_summary_label = QLabel("尚未导入曲线", page)
        self.curve_summary_label.setObjectName("SectionHint")
        self.curve_summary_label.setWordWrap(True)
        v.addWidget(self.curve_summary_label)
        v.addStretch(1)
        self.add_chapter("测试曲线导入", page)

    def _build_chapter_curve_check(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QLabel("曲线检查与能量", page)
        title.setObjectName("SectionTitle")
        v.addWidget(title)
        v.addWidget(self.curve_check_widget, 1)
        self.curve_metrics_label = QLabel("导入曲线后显示能量与刚度指标。", page)
        self.curve_metrics_label.setObjectName("SectionHint")
        self.curve_metrics_label.setWordWrap(True)
        v.addWidget(self.curve_metrics_label)
        self.add_chapter("曲线检查与能量", page)

    def _build_chapter_impact_inputs(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QLabel("单次冲击工况", page)
        title.setObjectName("SectionTitle")
        v.addWidget(title)
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        form = QVBoxLayout(container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        for spec in IMPACT_FIELDS:
            card = self._build_field_card(spec, container)
            form.addWidget(card)
        form.addStretch(1)
        scroll.setWidget(container)
        v.addWidget(scroll, 1)
        self.add_chapter("单次冲击工况", page)

    def _build_field_card(self, spec: FieldSpec, parent: QWidget) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        grid = QGridLayout(card)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        label = QLabel(spec.label, card)
        label.setObjectName("SubSectionTitle")
        editor = QLineEdit(card)
        editor.setPlaceholderText(spec.placeholder)
        editor.setText(spec.default)
        editor.setFont(make_ui_font())
        unit = QLabel(spec.unit, card)
        unit.setObjectName("UnitLabel")
        hint = QLabel(spec.hint, card)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        grid.addWidget(label, 0, 0)
        grid.addWidget(editor, 0, 1)
        grid.addWidget(unit, 0, 2)
        grid.addWidget(hint, 1, 0, 1, 3)
        self._field_widgets[spec.field_id] = editor
        return card

    def _build_metric_card(self, parent: QWidget, key: str, label_text: str, unit: str) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        title = QLabel(label_text, card)
        title.setObjectName("SectionHint")
        value = QLabel(f"-- {unit}".strip(), card)
        value.setObjectName("SubSectionTitle")
        value.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(value)
        self.metric_labels[key] = value
        return card

    def _build_chapter_energy_results(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        root = QVBoxLayout(page)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)
        title = QLabel("吸能结果 · 工作台总览", page)
        title.setObjectName("SectionTitle")
        root.addWidget(title)

        overview = QWidget(page)
        grid = QGridLayout(overview)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        root.addWidget(overview, 1)

        central = QWidget(overview)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(8)

        self.metric_labels: Dict[str, QLabel] = {}
        metric_row = QGridLayout()
        metric_row.setContentsMargins(0, 0, 0, 0)
        metric_row.setHorizontalSpacing(8)
        metric_row.addWidget(self._build_metric_card(central, "initial_energy", "初始动能", "J"), 0, 0)
        metric_row.addWidget(self._build_metric_card(central, "max_compression", "最大压缩量", "mm"), 0, 1)
        metric_row.addWidget(self._build_metric_card(central, "peak_force", "峰值输出力", "N"), 0, 2)
        metric_row.addWidget(self._build_metric_card(central, "rebound_velocity", "估算回弹速度", "m/s"), 0, 3)
        central_layout.addLayout(metric_row)

        chart_card = QFrame(central)
        chart_card.setObjectName("SubCard")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(10, 8, 10, 8)
        chart_layout.setSpacing(6)
        chart_title = QLabel("F-x 滞回曲线与能量积分", chart_card)
        chart_title.setObjectName("SubSectionTitle")
        chart_layout.addWidget(chart_title)
        self.overview_curve_widget.setMinimumHeight(260)
        chart_layout.addWidget(self.overview_curve_widget, 1)
        central_layout.addWidget(chart_card, 1)

        self.energy_strip_label = QLabel("加载能量 -- J · 工况耗散 -- J · 接触时长 -- ms", central)
        self.energy_strip_label.setObjectName("SectionHint")
        self.energy_strip_label.setWordWrap(True)
        central_layout.addWidget(self.energy_strip_label)

        right = QFrame(overview)
        right.setObjectName("SubCard")
        right.setMinimumWidth(280)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(8)

        self.overall_verdict_label = QLabel("总体结论: 待计算", right)
        self.overall_verdict_label.setObjectName("SubSectionTitle")
        self.overall_verdict_label.setWordWrap(True)
        right_layout.addWidget(self.overall_verdict_label)

        self.model_boundary_label = QLabel(DISCLAIMER_TEXT, right)
        self.model_boundary_label.setObjectName("SectionHint")
        self.model_boundary_label.setWordWrap(True)
        right_layout.addWidget(self.model_boundary_label)

        self.check_badges: Dict[str, QLabel] = {}
        for key, name in (
            ("stroke_ok", "行程"),
            ("peak_force_ok", "峰值力"),
            ("energy_capacity_ok", "曲线能量容量"),
        ):
            lbl = QLabel(f"{name}: 待计算", right)
            lbl.setObjectName("WaitBadge")
            self.check_badges[key] = lbl
            right_layout.addWidget(lbl)

        preview_title = QLabel("参数对比摘要", right)
        preview_title.setObjectName("SubSectionTitle")
        right_layout.addWidget(preview_title)
        self.compare_preview_table = QTableWidget(0, 4, right)
        self.compare_preview_table.setHorizontalHeaderLabels(["方案", "x", "Fpk", "回弹"])
        self.compare_preview_table.setMinimumHeight(130)
        right_layout.addWidget(self.compare_preview_table)

        self.results_label = QPlainTextEdit(right)
        self.results_label.setReadOnly(True)
        self.results_label.setMaximumHeight(150)
        self.results_label.setPlainText("执行计算后显示消息与建议。")
        right_layout.addWidget(self.results_label)
        right_layout.addStretch(1)

        grid.addWidget(central, 0, 0, 1, 3)
        grid.addWidget(right, 0, 3)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 0)
        self.add_chapter("吸能结果", page)

    def _build_chapter_time_response(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QLabel("响应时程", page)
        title.setObjectName("SectionTitle")
        v.addWidget(title)
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("变量:", page))
        self.response_var_combo = QComboBox(page)
        self.response_var_combo.addItem("位移 x(t)", "x")
        self.response_var_combo.addItem("速度 v(t)", "v")
        self.response_var_combo.addItem("加速度 a(t)", "a")
        self.response_var_combo.addItem("反力 F(t)", "F")
        sel_row.addWidget(self.response_var_combo)
        sel_row.addStretch(1)
        v.addLayout(sel_row)
        v.addWidget(self.response_widget, 1)
        self.response_var_combo.currentIndexChanged.connect(
            lambda _i: self.response_widget.set_variable(self.response_var_combo.currentData())
        )
        self.add_chapter("响应时程", page)

    def _build_chapter_parameter_compare(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QLabel("参数对比", page)
        title.setObjectName("SectionTitle")
        v.addWidget(title)
        hint = QLabel(
            "勾选要扫描的力倍率/行程倍率组合，执行仿真时一并输出。当前默认 0.8 / 1.0 / 1.2。",
            page,
        )
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.compare_table = QTableWidget(0, 9, page)
        self.compare_table.setHorizontalHeaderLabels(
            ["force_scale", "stroke_scale", "max_compression_mm", "peak_force_n",
             "bottom_out", "energy_capacity_ok", "stroke_ok", "peak_force_ok", "duration_s"]
        )
        v.addWidget(self.compare_table, 1)
        self.add_chapter("参数对比", page)

    def _build_chapter_export_doc(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        v = QVBoxLayout(page)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        title = QLabel("结果说明 / 导出", page)
        title.setObjectName("SectionTitle")
        v.addWidget(title)
        self.report_preview = QPlainTextEdit(page)
        self.report_preview.setReadOnly(True)
        self.report_preview.setPlainText("执行计算后显示报告内容预览。")
        v.addWidget(self.report_preview, 1)
        self.add_chapter("结果说明 / 导出", page)

    # ---------- Stub action handlers (filled in later tasks) ----------

    def _apply_defaults(self) -> None:
        for spec in IMPACT_FIELDS:
            w = self._field_widgets.get(spec.field_id)
            if isinstance(w, QLineEdit):
                w.setText(spec.default)

    def _on_import_curve(self) -> None: ...
    def _on_save_inputs(self) -> None: ...
    def _on_load_inputs(self) -> None: ...
    def _on_calculate(self) -> None: ...
    def _on_clear(self) -> None: ...
    def _on_save_report(self) -> None: ...
    def _load_sample(self, filename: str) -> None: ...
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyPageSkeletonTests -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/buffer_energy_page.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): page skeleton with 7 chapters and disclaimer banner"
```

---

### Task 15: Wire up curve import + curve check chapters

**Files:**
- Modify: `app/ui/pages/buffer_energy_page.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
class BufferEnergyImportFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_load_sample_populates_curve_summary(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        self.assertIsNotNone(page._curve_data)
        self.assertIn("点", page.curve_summary_label.text())
        self.assertIn("最大行程", page.curve_summary_label.text())

    def test_invalid_file_shows_messagebox(self) -> None:
        from unittest.mock import patch
        page = BufferEnergyPage()
        with patch.object(QMessageBox, "warning") as mock_warn:
            page._open_curve_path(Path("/nonexistent/file.csv"))
        self.assertTrue(mock_warn.called)
        self.assertIsNone(page._curve_data)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyImportFlowTests -v
```

- [ ] **Step 3: Implement curve import flow**

替换 `BufferEnergyPage` 中 `_on_import_curve`、`_load_sample` 桩函数，并新增 `_open_curve_path`：

```python
    def _on_import_curve(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "选择缓冲块测试曲线文件",
            str(EXAMPLES_DIR),
            "曲线数据 (*.csv *.xlsx)",
        )
        if not path_str:
            return
        self._open_curve_path(Path(path_str))

    def _load_sample(self, filename: str) -> None:
        self._open_curve_path(EXAMPLES_DIR / filename)

    def _open_curve_path(self, path: Path) -> None:
        try:
            data = load_buffer_curve(path)
        except (CurveInputError, FileNotFoundError, OSError) as exc:
            QMessageBox.warning(self, "曲线导入失败", str(exc))
            self._curve_data = None
            self.curve_summary_label.setText("尚未导入曲线")
            for widget in (self.curve_check_widget, self.overview_curve_widget):
                widget.set_curves(
                    loading=[], unloading=[], x_max_mm=0.0,
                    available_stroke_mm=0.0, allowable_peak_n=0.0, bottom_out=False,
                )
            return
        self._curve_data = data
        self._curve_source = path
        loading = data["loading"]
        unloading = data["unloading"]
        max_stroke = max((p["x_mm"] for p in loading), default=0.0)
        max_force = max((p["force_n"] for p in loading), default=0.0)
        meta = data.get("metadata", {})
        self.curve_summary_label.setText(
            f"已导入 {path.name} · 格式 {meta.get('format', '?')} · "
            f"加载 {len(loading)} 点 / 卸载 {len(unloading)} 点 · "
            f"最大行程 {max_stroke:.2f} mm · 最大加载力 {max_force:.0f} N"
        )
        # Pre-fill curve widget with raw curves (no impact yet)
        for widget in (self.curve_check_widget, self.overview_curve_widget):
            widget.set_curves(
                loading=[(p["x_mm"], p["force_n"]) for p in loading],
                unloading=[(p["x_mm"], p["force_n"]) for p in unloading],
                x_max_mm=0.0,
                available_stroke_mm=self._read_field_float("impact.available_stroke_mm", 0.0),
                allowable_peak_n=self._read_field_float("impact.allowable_peak_force_n", 0.0),
                bottom_out=False,
            )
        self.curve_metrics_label.setText(
            "曲线已加载，执行仿真后此处显示能量积分与刚度指标。"
        )
        self.btn_save_report.setEnabled(False)

    def _read_field_float(self, field_id: str, default: float) -> float:
        w = self._field_widgets.get(field_id)
        if isinstance(w, QLineEdit):
            try:
                return float(w.text().strip())
            except ValueError:
                return default
        return default
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/buffer_energy_page.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): wire curve import + sample loading + summary label"
```

---

### Task 16: Wire calculate flow + render energy results + time-response chapter

**Files:**
- Modify: `app/ui/pages/buffer_energy_page.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
class BufferEnergyCalculateFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_calculate_after_sample_pass(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        page._on_calculate()
        self.assertIsNotNone(page._last_result)
        text = page.results_label.toPlainText()
        for keyword in ("最大压缩", "峰值", "吸收能量", "回弹", "接触时长"):
            self.assertIn(keyword, text)
        self.assertNotIn("--", page.metric_labels["initial_energy"].text())
        self.assertIn("总体结论", page.overall_verdict_label.text())
        self.assertIn("加载能量", page.energy_strip_label.text())
        # Time response widget receives data
        self.assertIsNotNone(page.response_widget._response)

    def test_calculate_with_bottom_out_marks_badge(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        # Force bottom-out via excessive velocity
        page._field_widgets["impact.initial_velocity_m_s"].setText("50")
        page._on_calculate()
        self.assertTrue(page._last_result["impact"]["bottom_out"])
        self.assertEqual(page.check_badges["peak_force_ok"].text(), "峰值力: 不可判定")

    def test_invalid_field_shows_messagebox(self) -> None:
        from unittest.mock import patch
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        page._field_widgets["impact.mass_kg"].setText("abc")
        with patch.object(QMessageBox, "warning") as mock_warn:
            page._on_calculate()
        self.assertTrue(mock_warn.called)

    def test_calculate_without_curve_warns(self) -> None:
        from unittest.mock import patch
        page = BufferEnergyPage()
        with patch.object(QMessageBox, "warning") as mock_warn:
            page._on_calculate()
        self.assertTrue(mock_warn.called)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyCalculateFlowTests -v
```

- [ ] **Step 3: Implement build_payload + calculate + render**

替换 `_on_calculate` 桩，并新增私有 helpers：

```python
    def _build_payload(self) -> Dict[str, Any]:
        if self._curve_data is None:
            raise InputError("请先导入曲线文件或加载测试案例")
        payload: Dict[str, Any] = {
            "curve": {
                "loading": list(self._curve_data["loading"]),
                "unloading": list(self._curve_data["unloading"]),
            },
            "impact": {},
            "options": {},
        }
        for spec in IMPACT_FIELDS:
            if spec.mapping is None:
                continue
            section, key = spec.mapping
            w = self._field_widgets[spec.field_id]
            text = w.text().strip() if isinstance(w, QLineEdit) else ""
            if not text:
                raise InputError(f"{spec.label} 不能为空")
            try:
                value: Any = int(text) if key == "time_samples" else float(text)
            except ValueError as exc:
                raise InputError(f"{spec.label} 不是数字: {text!r}") from exc
            payload[section][key] = value
        return payload

    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_buffer_energy(payload)
        except (InputError, KeyError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "输入或计算错误", str(exc))
            self.btn_save_report.setEnabled(False)
            return
        self._last_payload = payload
        self._last_result = result
        self._render_result(result)
        self.btn_save_report.setEnabled(True)

    def _render_result(self, result: Dict[str, Any]) -> None:
        impact = result["impact"]
        summary = result["curve_summary"]
        tr = result.get("time_response")

        peak_text = "触底，未知" if impact["peak_force_n"] is None else f"{impact['peak_force_n']:.1f} N"
        duration_s = tr["duration_s"] if tr else 0.0
        lines = [
            f"初始动能 E0 = {impact['initial_energy_j']:.3f} J",
            f"曲线在可用行程内吸能容量 = {impact['available_energy_capacity_j']:.3f} J",
            f"最大压缩量 = {impact['max_compression_mm']:.3f} mm",
            f"峰值输出力 = {peak_text}",
            f"平均反力 = {impact['average_force_n']:.1f} N",
            f"吸收能量 = {impact['absorbed_energy_j']:.3f} J",
            f"工况耗散能量 = {impact['impact_dissipated_energy_j']:.3f} J",
            f"回弹能量 = {impact['rebound_energy_j']:.3f} J",
            f"估算回弹速度 = {impact['estimated_rebound_velocity_m_s']:.3f} m/s",
            f"接触时长 = {duration_s * 1000.0:.2f} ms",
            "",
            f"测试曲线最大行程 = {summary['max_stroke_mm']:.2f} mm",
            f"测试曲线峰值力 = {summary['peak_loading_force_n']:.1f} N",
            f"测试曲线滞回能量 = {summary['curve_hysteresis_energy_j']:.3f} J",
            f"等效刚度 = {summary['equivalent_stiffness_n_per_mm']:.1f} N/mm",
            f"切线刚度区间 = [{summary['tangent_stiffness_min_n_per_mm']:.1f}, "
            f"{summary['tangent_stiffness_max_n_per_mm']:.1f}] N/mm",
        ]
        if result["warnings"]:
            lines.append("")
            lines.append("提示:")
            lines.extend(f"- {w}" for w in result["warnings"])
        self.results_label.setPlainText("\n".join(lines))

        self.metric_labels["initial_energy"].setText(f"{impact['initial_energy_j']:.2f} J")
        self.metric_labels["max_compression"].setText(f"{impact['max_compression_mm']:.2f} mm")
        self.metric_labels["peak_force"].setText(peak_text)
        self.metric_labels["rebound_velocity"].setText(
            f"{impact['estimated_rebound_velocity_m_s']:.3f} m/s"
        )
        self.energy_strip_label.setText(
            f"加载能量 {summary['loading_energy_j']:.3f} J · "
            f"工况耗散 {impact['impact_dissipated_energy_j']:.3f} J · "
            f"接触时长 {duration_s * 1000.0:.2f} ms"
        )
        if impact["bottom_out"]:
            verdict = "总体结论: 触底 / 峰值未知"
        elif result["overall_pass"]:
            verdict = "总体结论: 通过"
        else:
            verdict = "总体结论: 不通过"
        self.overall_verdict_label.setText(verdict)
        boundary_lines = [DISCLAIMER_TEXT]
        if impact["bottom_out"]:
            boundary_lines.append("触底后真实冲击峰值未知，当前曲线末端力不能代表触底峰值。")
        self.model_boundary_label.setText("\n".join(boundary_lines))

        # Update F-x widget with impact context
        for widget in (self.curve_check_widget, self.overview_curve_widget):
            widget.set_curves(
                loading=list(zip(result["curves"]["loading_x_mm"], result["curves"]["loading_force_n"])),
                unloading=list(zip(result["curves"]["unloading_x_mm"], result["curves"]["unloading_force_n"])),
                x_max_mm=impact["max_compression_mm"],
                available_stroke_mm=self._read_field_float("impact.available_stroke_mm", 0.0),
                allowable_peak_n=self._read_field_float("impact.allowable_peak_force_n", 0.0),
                bottom_out=impact["bottom_out"],
            )
        self.curve_metrics_label.setText(
            f"加载能量 {summary['loading_energy_j']:.3f} J · "
            f"卸载能量 {summary['unloading_energy_j']:.3f} J · "
            f"滞回 {summary['curve_hysteresis_energy_j']:.3f} J · "
            f"吸能比例 {summary['energy_absorption_ratio'] * 100.0:.1f}%"
        )

        # Time-response widget
        self.response_widget.set_response(tr)
        self.response_widget.set_variable(self.response_var_combo.currentData() or "x")

        # Per-check badges
        self._set_check_badge("stroke_ok", "行程", result["checks"]["stroke_ok"])
        self._set_check_badge("peak_force_ok", "峰值力", result["checks"]["peak_force_ok"])
        self._set_check_badge("energy_capacity_ok", "曲线能量容量", result["checks"]["energy_capacity_ok"])

        # Overall badge
        if result["overall_pass"]:
            self.set_overall_status("整体通过", "pass")
        else:
            self.set_overall_status("整体不通过 / 触底", "fail")

    def _set_check_badge(self, key: str, name: str, value) -> None:
        lbl = self.check_badges[key]
        if value is True:
            lbl.setText(f"{name}: 通过")
            obj = "PassBadge"
        elif value is False:
            lbl.setText(f"{name}: 不通过")
            obj = "FailBadge"
        else:  # None — unjudgeable (bottom-out)
            lbl.setText(f"{name}: 不可判定")
            obj = "WaitBadge"
        lbl.setObjectName(obj)
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/buffer_energy_page.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): wire calculate, render energy results and time response"
```

---

### Task 17: Parameter compare table + clear handler

**Files:**
- Modify: `app/ui/pages/buffer_energy_page.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
class BufferEnergyParameterCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_parameter_compare_table_populated(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        page._on_calculate()
        # Default scan: 3 force_scale x 3 stroke_scale = 9 rows
        self.assertEqual(page.compare_table.rowCount(), 9)
        # Each row must have force_scale and duration in last column
        first_row = [page.compare_table.item(0, c).text() for c in range(page.compare_table.columnCount())]
        self.assertEqual(first_row[0], "0.80")
        self.assertGreaterEqual(page.compare_preview_table.rowCount(), 3)
        self.assertEqual(page.compare_preview_table.columnCount(), 4)

    def test_clear_resets_state(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        page._on_calculate()
        page._on_clear()
        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_save_report.isEnabled())
        self.assertEqual(page.results_label.toPlainText().strip().startswith("执行计算后"), True)
        self.assertEqual(page.compare_preview_table.rowCount(), 0)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyParameterCompareTests -v
```

- [ ] **Step 3: Implement parameter sweep + clear**

在 `_on_calculate` 末尾追加调用并实现 helpers：

```python
    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_buffer_energy(payload)
        except (InputError, KeyError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "输入或计算错误", str(exc))
            self.btn_save_report.setEnabled(False)
            return
        self._last_payload = payload
        self._last_result = result
        self._render_result(result)
        self._populate_parameter_compare(payload)
        self.btn_save_report.setEnabled(True)

    def _populate_parameter_compare(self, base_payload: Dict[str, Any]) -> None:
        scales = (0.8, 1.0, 1.2)
        rows: List[List[str]] = []
        for fs in scales:
            for ss in scales:
                payload = json.loads(json.dumps(base_payload))  # deep copy
                payload["options"]["force_scale"] = fs
                payload["options"]["stroke_scale"] = ss
                try:
                    r = calculate_buffer_energy(payload)
                except InputError as exc:
                    rows.append([f"{fs:.2f}", f"{ss:.2f}", f"err: {exc}", "", "", "", "", "", ""])
                    continue
                impact = r["impact"]
                checks = r["checks"]
                tr = r.get("time_response") or {}
                peak_str = "触底" if impact["peak_force_n"] is None else f"{impact['peak_force_n']:.0f}"
                rows.append([
                    f"{fs:.2f}", f"{ss:.2f}",
                    f"{impact['max_compression_mm']:.2f}", peak_str,
                    "是" if impact["bottom_out"] else "否",
                    "通过" if checks["energy_capacity_ok"] else "不通过",
                    "通过" if checks["stroke_ok"] else "不通过",
                    {True: "通过", False: "不通过", None: "不可判定"}[checks["peak_force_ok"]],
                    f"{tr.get('duration_s', 0.0) * 1000.0:.2f} ms",
                ])
        self.compare_table.setRowCount(len(rows))
        for r_idx, row in enumerate(rows):
            for c_idx, text in enumerate(row):
                self.compare_table.setItem(r_idx, c_idx, QTableWidgetItem(text))
        self.compare_table.resizeColumnsToContents()

        # Scheme A right-rail preview: show a compact high-signal subset.
        preview_specs = (("0.80", "1.00", "0.8F"), ("1.00", "1.00", "1.0F"),
                         ("1.20", "1.00", "1.2F"), ("1.00", "1.20", "1.2S"))
        preview_rows: List[List[str]] = []
        for fs_text, ss_text, label in preview_specs:
            match = next((row for row in rows if row[0] == fs_text and row[1] == ss_text), None)
            if match is None:
                continue
            preview_rows.append([label, match[2], match[3], match[8]])
        self.compare_preview_table.setRowCount(len(preview_rows))
        for r_idx, row in enumerate(preview_rows):
            for c_idx, text in enumerate(row):
                self.compare_preview_table.setItem(r_idx, c_idx, QTableWidgetItem(text))
        self.compare_preview_table.resizeColumnsToContents()

    def _on_clear(self) -> None:
        self._last_payload = None
        self._last_result = None
        self._curve_data = None
        self._curve_source = None
        self._apply_defaults()
        self.curve_summary_label.setText("尚未导入曲线")
        self.curve_metrics_label.setText("导入曲线后显示能量与刚度指标。")
        for label in self.metric_labels.values():
            label.setText("--")
        self.energy_strip_label.setText("加载能量 -- J · 工况耗散 -- J · 接触时长 -- ms")
        self.overall_verdict_label.setText("总体结论: 待计算")
        self.model_boundary_label.setText(DISCLAIMER_TEXT)
        self.results_label.setPlainText("执行计算后显示消息与建议。")
        self.report_preview.setPlainText("执行计算后显示报告内容预览。")
        for widget in (self.curve_check_widget, self.overview_curve_widget):
            widget.set_curves(
                loading=[], unloading=[], x_max_mm=0.0,
                available_stroke_mm=0.0, allowable_peak_n=0.0, bottom_out=False,
            )
        self.response_widget.set_response(None)
        self.compare_table.setRowCount(0)
        self.compare_preview_table.setRowCount(0)
        for key in self.check_badges:
            self._set_check_badge(key, {"stroke_ok": "行程", "peak_force_ok": "峰值力",
                                         "energy_capacity_ok": "曲线能量容量"}[key], None)
            self.check_badges[key].setText({"stroke_ok": "行程: 待计算",
                                             "peak_force_ok": "峰值力: 待计算",
                                             "energy_capacity_ok": "曲线能量容量: 待计算"}[key])
        self.set_overall_status("等待计算", "wait")
        self.btn_save_report.setEnabled(False)
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/buffer_energy_page.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): parameter sweep table and clear handler"
```

---

### Task 18: Report export (text/PDF) + report preview

**Files:**
- Modify: `app/ui/pages/buffer_energy_page.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
class BufferEnergyReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_build_report_lines_contains_disclaimers(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        page._on_calculate()
        lines = page._build_report_lines()
        text = "\n".join(lines)
        for keyword in ("能量法", "应变率", "重力", "回弹"):
            self.assertIn(keyword, text)

    def test_report_preview_updates_on_calculate(self) -> None:
        page = BufferEnergyPage()
        page._load_sample("buffer_energy_case_01.csv")
        page._on_calculate()
        self.assertIn("缓冲块吸能仿真", page.report_preview.toPlainText())
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyReportTests -v
```

- [ ] **Step 3: Implement report builder + on_save_report**

在 `BufferEnergyPage` 中追加：

```python
    def _build_report_lines(self) -> List[str]:
        if not self._last_result:
            return ["缓冲块吸能仿真报告", "", "（尚未执行计算）"]
        r = self._last_result
        impact = r["impact"]
        summary = r["curve_summary"]
        tr = r.get("time_response") or {}
        peak_text = "触底，不可判定" if impact["peak_force_n"] is None else f"{impact['peak_force_n']:.2f} N"
        lines: List[str] = [
            "缓冲块吸能仿真报告",
            "=" * 30,
            "",
            "1. 输入条件",
            f"  质量            m   = {self._read_field_float('impact.mass_kg', 0.0):.3f} kg",
            f"  初始速度        v0  = {self._read_field_float('impact.initial_velocity_m_s', 0.0):.3f} m/s",
            f"  可用行程            = {self._read_field_float('impact.available_stroke_mm', 0.0):.2f} mm",
            f"  允许峰值力          = {self._read_field_float('impact.allowable_peak_force_n', 0.0):.0f} N",
            f"  曲线源              = {self._curve_source.name if self._curve_source else '(unknown)'}",
            "",
            "2. 测试曲线指标",
            f"  最大行程            = {summary['max_stroke_mm']:.2f} mm",
            f"  最大加载力          = {summary['peak_loading_force_n']:.1f} N",
            f"  加载能量            = {summary['loading_energy_j']:.3f} J",
            f"  卸载能量            = {summary['unloading_energy_j']:.3f} J",
            f"  滞回能量            = {summary['curve_hysteresis_energy_j']:.3f} J",
            f"  吸能比例            = {summary['energy_absorption_ratio'] * 100.0:.1f} %",
            f"  等效刚度            = {summary['equivalent_stiffness_n_per_mm']:.1f} N/mm",
            "",
            "3. 单次冲击工况结果",
            f"  初始动能      E0    = {impact['initial_energy_j']:.3f} J",
            f"  最大压缩量          = {impact['max_compression_mm']:.3f} mm",
            f"  峰值输出力          = {peak_text}",
            f"  平均反力            = {impact['average_force_n']:.1f} N",
            f"  吸收能量            = {impact['absorbed_energy_j']:.3f} J",
            f"  工况耗散能量        = {impact['impact_dissipated_energy_j']:.3f} J",
            f"  回弹能量            = {impact['rebound_energy_j']:.3f} J",
            f"  估算回弹速度        = {impact['estimated_rebound_velocity_m_s']:.3f} m/s",
            f"  接触时长            = {tr.get('duration_s', 0.0) * 1000.0:.2f} ms",
            f"  是否触底            = {'是' if impact['bottom_out'] else '否'}",
            "",
            "4. 校核",
            f"  行程          : {self._fmt_check(r['checks']['stroke_ok'])}",
            f"  峰值力        : {self._fmt_check(r['checks']['peak_force_ok'])}",
            f"  曲线能量容量  : {self._fmt_check(r['checks']['energy_capacity_ok'])}",
            f"  整体          : {'通过' if r['overall_pass'] else '不通过'}",
            "",
            "5. 假设与免责说明",
        ]
        for note in r["assumptions"]:
            lines.append(f"  - {note}")
        if r["warnings"]:
            lines.append("")
            lines.append("6. 计算提示")
            for w in r["warnings"]:
                lines.append(f"  - {w}")
        return lines

    @staticmethod
    def _fmt_check(value) -> str:
        if value is True:
            return "通过"
        if value is False:
            return "不通过"
        return "不可判定"

    def _on_save_report(self) -> None:
        if not self._last_result:
            QMessageBox.information(self, "导出报告", "请先执行仿真，再导出结果说明。")
            return
        lines = self._build_report_lines()
        export_report_lines(self, lines, default_basename="buffer_energy_report")

    # Update _render_result to refresh preview as well: append at the end of _render_result
    # (for plan clarity, replace the closing of _render_result by inserting:
    #   self.report_preview.setPlainText("\n".join(self._build_report_lines()))
```

修改 `_render_result` 的最后一行（在 `set_overall_status` 之前或之后），追加：

```python
        self.report_preview.setPlainText("\n".join(self._build_report_lines()))
```

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/buffer_energy_page.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): report builder, preview, and export wiring"
```

---

### Task 19: Save / load input conditions (JSON persistence)

**Files:**
- Modify: `app/ui/pages/buffer_energy_page.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing tests**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
class BufferEnergyInputConditionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_save_then_load_roundtrip(self) -> None:
        import tempfile
        page = BufferEnergyPage()
        page._field_widgets["impact.mass_kg"].setText("99.5")
        page._field_widgets["impact.initial_velocity_m_s"].setText("3.21")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "saved.json"
            page._write_input_conditions(path)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["module"], "buffer_energy")

            page._field_widgets["impact.mass_kg"].setText("0")
            page._field_widgets["impact.initial_velocity_m_s"].setText("0")
            page._read_input_conditions(path)
            self.assertEqual(page._field_widgets["impact.mass_kg"].text(), "99.5")
            self.assertEqual(page._field_widgets["impact.initial_velocity_m_s"].text(), "3.21")
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyInputConditionsTests -v
```

- [ ] **Step 3: Implement persistence helpers**

在 `BufferEnergyPage` 中追加：

```python
    def _on_save_inputs(self) -> None:
        path = choose_save_input_conditions_path(self, SAVED_INPUTS_DIR, "buffer_energy")
        if not path:
            return
        try:
            self._write_input_conditions(path)
            QMessageBox.information(self, "保存成功", f"输入条件已保存至:\n{path}")
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))

    def _on_load_inputs(self) -> None:
        path = choose_load_input_conditions_path(self, SAVED_INPUTS_DIR)
        if not path:
            return
        try:
            self._read_input_conditions(path)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            QMessageBox.warning(self, "加载失败", str(exc))

    def _write_input_conditions(self, path: Path) -> None:
        snapshot = build_form_snapshot(
            module="buffer_energy",
            field_widgets=self._field_widgets,
        )
        write_input_conditions(path, snapshot)

    def _read_input_conditions(self, path: Path) -> None:
        data = read_input_conditions(path)
        for field_id, value in data.get("fields", {}).items():
            w = self._field_widgets.get(field_id)
            if isinstance(w, QLineEdit):
                w.setText(str(value))
        # On load, results no longer reflect inputs
        self.btn_save_report.setEnabled(False)
        self._last_result = None
```

**Note**: Inspect `build_form_snapshot` signature in `app/ui/input_condition_store.py`. If it expects `field_specs` instead of `field_widgets`, adjust accordingly (read `app/ui/input_condition_store.py` lines 21-46 for the canonical signature). The test above is structural — it just checks that the file roundtrips through `_write_input_conditions` / `_read_input_conditions`.

- [ ] **Step 4: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/ui/pages/buffer_energy_page.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): input-condition save/load via shared store"
```

---

## Phase 7: Integration

### Task 20: MainWindow registration + final UI smoke

**Files:**
- Modify: `app/ui/main_window.py`
- Modify: `tests/ui/test_buffer_energy_page.py`

- [ ] **Step 1: Write failing integration test**

追加到 `tests/ui/test_buffer_energy_page.py`:

```python
class BufferEnergyMainWindowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_module_registered_in_mainwindow(self) -> None:
        from app.ui.main_window import MainWindow
        win = MainWindow()
        names = [name for name, _factory in win._page_factories]
        self.assertIn("缓冲块吸能仿真", names)

    def test_lazy_construct_buffer_page(self) -> None:
        from app.ui.main_window import MainWindow
        win = MainWindow()
        # Find index, trigger lazy construction
        idx = next(i for i, (n, _) in enumerate(win._page_factories) if n == "缓冲块吸能仿真")
        page = win._ensure_page(idx)
        self.assertIsNotNone(page)
        self.assertEqual(page.__class__.__name__, "BufferEnergyPage")
```

- [ ] **Step 2: Run tests, verify failure**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_buffer_energy_page.py::BufferEnergyMainWindowIntegrationTests -v
```

- [ ] **Step 3: Register in MainWindow**

修改 `app/ui/main_window.py`：

在 `_page_factories` 列表（line ~94）的 "材料与标准库" 之前插入：

```python
            ("缓冲块吸能仿真", self._make_buffer_energy_page),
```

最终的 `_page_factories` 应为：

```python
        self._page_factories: List[Tuple[str, PageFactory]] = [
            ("螺栓连接", self._make_bolt_page),
            ("轴向受力螺纹连接", self._make_bolt_tapped_axial_page),
            ("过盈配合", self._make_interference_fit_page),
            ("花键连接校核", self._make_spline_fit_page),
            ("蜗轮蜗杆设计", self._make_worm_gear_page),
            ("赫兹应力", self._make_hertz_contact_page),
            ("缓冲块吸能仿真", self._make_buffer_energy_page),
            ("材料与标准库", self._make_placeholder_page),
        ]
```

在 `_make_hertz_contact_page` 之后追加工厂方法：

```python
    def _make_buffer_energy_page(self) -> QWidget:
        from app.ui.pages.buffer_energy_page import BufferEnergyPage
        return BufferEnergyPage(self)
```

- [ ] **Step 4: Run full test suite**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/buffer/ tests/ui/test_buffer_energy_page.py -v
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -q
```

Expected: 全部 PASS（含原有模块）。注意检查 `__pycache__` 干净：若有 import 异常可先 `find . -name __pycache__ -exec rm -rf {} +`。

- [ ] **Step 5: Final manual smoke + commit**

```bash
QT_QPA_PLATFORM=offscreen python3 - << 'PY'
from PySide6.QtWidgets import QApplication
import sys
app = QApplication.instance() or QApplication([])
from app.ui.main_window import MainWindow
win = MainWindow()
idx = next(i for i, (n, _) in enumerate(win._page_factories) if n == "缓冲块吸能仿真")
page = win._ensure_page(idx)
page._load_sample("buffer_energy_case_01.csv")
page._on_calculate()
print("OK", page._last_result["overall_pass"], page._last_result["impact"]["max_compression_mm"])
PY
```

```bash
git add app/ui/main_window.py tests/ui/test_buffer_energy_page.py
git commit -m "feat(buffer): register module in MainWindow with lazy factory"
```

---

## Self-Review Checklist (run after Task 20)

执行完所有任务后，对照 spec 自查：

- [ ] **Spec coverage**: spec 中所有字段（`curve_summary`, `impact.*`, `time_response.*`, `checks.*`, `warnings`, `assumptions`）均在 calculator 输出与 page 渲染中出现。
- [ ] **触底语义**: `bottom_out=True` 时 `peak_force_n=None`、`peak_force_ok=None`、`stroke_ok=False`、`overall_pass=False`，UI badge 显示"不可判定"。
- [ ] **方案 A 工作台**: `吸能结果` 章节一屏内包含 `metric_labels`、`overview_curve_widget`、`energy_strip_label`、`overall_verdict_label`、`model_boundary_label`、`compare_preview_table`，用户不用切换到 `响应时程` / `参数对比` 章节即可完成初步判断。
- [ ] **常驻免责横幅**: `BufferEnergyPage.disclaimer_label` 始终可见，文案包含"能量法"、"应变率"。
- [ ] **`openpyxl` 懒加载**: `core/buffer/curve_import.py` 顶层不 import `openpyxl`，只在 `_read_xlsx_rows` 函数体内 import；测试 `test_openpyxl_not_imported_when_loading_csv` 通过。
- [ ] **时域反推**: 线性弹簧情况下 `compression_duration_s` 与解析值（quarter period）误差 < 5%；触底情况下仅返回压缩段、`rebound_duration_s == 0`。
- [ ] **报告免责**: `_build_report_lines` 输出含"能量法"、"应变率"、"重力"、"卸载段简化假设"等关键文案。
- [ ] **MainWindow 启动时间**: 启动时不构造 `BufferEnergyPage`（依赖 `LazyStackedWidget`）；切换到该模块时 < 200 ms 完成构造（与 hertz_contact_page 同量级）。
- [ ] **测试目录布局**: `tests/core/buffer/__init__.py` 已创建，避免 pytest 同名模块冲突。
- [ ] **无 Unicode 智能引号**: 所有新增 Python 文件中无 `"` `"`（U+201C/U+201D）。

如发现遗漏，回到对应 task 补 step；测试已写则补实现，反之亦然。

---

## Execution Handoff

Plan 完整，已落地至 `docs/superpowers/plans/2026-05-02-buffer-energy-simulation.md`。两种执行方式：

**1. Subagent-Driven（推荐）** — 每个 task 派发独立 subagent，task 之间做两阶段 review，迭代快、上下文干净。

**2. Inline Execution** — 在当前会话内分批执行，配合 checkpoint 复核。

请告诉我使用哪种方式，我即可启动相应 sub-skill（`superpowers:subagent-driven-development` 或 `superpowers:executing-plans`）。
