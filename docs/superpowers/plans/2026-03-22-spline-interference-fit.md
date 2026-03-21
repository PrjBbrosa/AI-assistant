# 花键过盈配合模块 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建独立模块"花键过盈配合"，支持两种场景的扭矩传递校核——(A) 渐开线花键齿面过盈、(B) 花键轴光滑段圆柱过盈——并在同一页面中呈现。

**Architecture:**
- `core/spline/calculator.py`：纯计算引擎，输入 dict → 输出 dict，不依赖 Qt。场景 A 实现齿面承压校核（Niemann/DIN 5466 简化公式），场景 B 复用现有 DIN 7190 Lamé 模型（调用 `core.interference.calculator` 内部函数）。
- `app/ui/pages/spline_fit_page.py`：章节式 UI 页面，继承 `BaseChapterPage`，遵循现有 `FieldSpec` + `CHAPTERS` 模式。
- 渐开线花键几何由用户输入 (m, z)，α=30° 固定，自动推导 d/da/df 等尺寸。矩形花键接口预留。

**Tech Stack:** Python 3.12, PySide6, pytest, 现有 `core/interference/calculator.py` Lamé 模型复用

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `core/spline/__init__.py` | Public API exports |
| Create | `core/spline/calculator.py` | 花键过盈配合计算引擎（场景 A + B） |
| Create | `core/spline/geometry.py` | 渐开线花键几何推导（DIN 5480 基础公式） |
| Create | `tests/core/spline/__init__.py` | Test package init |
| Create | `tests/core/spline/test_geometry.py` | 花键几何推导测试 |
| Create | `tests/core/spline/test_calculator.py` | 计算引擎测试 |
| Create | `app/ui/pages/spline_fit_page.py` | UI 页面 |
| Modify | `app/ui/main_window.py:61-68` | 侧栏注册新模块（替换 PlaceholderPage） |

---

## 场景 A 核心公式：渐开线花键齿面过盈

### 几何推导（DIN 5480, α=30°）
```
d   = m × z                    # 分度圆直径
d_a = m × (z + 1.0)            # 齿顶圆直径（外花键）
d_f = m × (z - 1.25)           # 齿根圆直径（外花键）
d_a2 = m × (z - 1.0)           # 内花键齿顶圆直径（≈外花键齿根径附近）
h_w = (d_a - d_a2) / 2         # 有效齿高（单侧）
d_m = (d_a + d_f) / 2          # 平均直径
```

### 齿面承载压力（Niemann 简化）
```
p_flank = (2 × T × K_A × K_alpha) / (z × h_w × d_m × L)
```

- `T` = 设计扭矩 [N·mm]
- `K_A` = 工况系数
- `K_alpha` = 载荷分布不均匀系数（过盈配合取 1.0~1.2）
- `z` = 齿数
- `h_w` = 有效齿高 [mm]
- `d_m` = 平均直径 [mm]
- `L` = 有效啮合长度 [mm]

### 扭矩传递能力
```
T_form = p_zul × z × h_w × d_m × L / (2 × K_alpha)
```
- `p_zul` = 许用齿面压力 [MPa]（由用户选择材料工况查表或直接输入）

### 许用齿面压力参考值

| 连接条件 | 材料状态 | p_zul [MPa] |
|----------|---------|-------------|
| 固定连接，静载 | 调质钢 | 80~150 |
| 固定连接，静载 | 渗碳淬火 | 100~200 |
| 固定连接，脉动载荷 | 调质钢 | 40~80 |
| 固定连接，脉动载荷 | 渗碳淬火 | 60~120 |

### 安全系数
```
S_flank = p_zul / p_flank          >= S_min
```

---

## 场景 B 核心公式：光滑段圆柱过盈

复用 `core/interference/calculator.py` 的 Lamé 模型。差异点：

1. **有效配合长度** = 用户输入配合长度 - 退刀槽宽度
2. **默认安全系数** 建议值提高至 1.5（静载）/ 2.0（动载），因花键过渡区应力集中

输出与现有过盈配合模块相同：接触压力、打滑扭矩、轴向力、von Mises 应力、压入力曲线等。

---

## 综合校核逻辑

两个场景**独立校核**，不叠加扭矩能力。UI 同时展示两个场景的结果。
- `overall_pass` = 场景 A pass **AND** 场景 B pass（如果场景 B 启用）
- 场景 B 默认启用，用户可关闭（纯花键无光滑段时）

---

## Task 1: 花键几何推导模块

**Files:**
- Create: `core/spline/__init__.py`
- Create: `core/spline/geometry.py`
- Create: `tests/core/spline/__init__.py`
- Create: `tests/core/spline/test_geometry.py`

- [ ] **Step 1: Write failing test for involute spline geometry derivation**

```python
# tests/core/spline/test_geometry.py
import math
import pytest
from core.spline.geometry import derive_involute_geometry, GeometryError


class TestDeriveInvoluteGeometry:
    def test_basic_m2_z20(self):
        """m=2, z=20, alpha=30° → d=40, d_a=42, d_f=37.5"""
        r = derive_involute_geometry(module_mm=2.0, tooth_count=20)
        assert r["reference_diameter_mm"] == pytest.approx(40.0)
        assert r["tip_diameter_shaft_mm"] == pytest.approx(42.0)
        assert r["root_diameter_shaft_mm"] == pytest.approx(37.5)
        assert r["tip_diameter_hub_mm"] == pytest.approx(38.0)
        assert r["effective_tooth_height_mm"] == pytest.approx(2.0)
        assert r["mean_diameter_mm"] == pytest.approx(39.75)
        assert r["pressure_angle_deg"] == pytest.approx(30.0)

    def test_m1_25_z22(self):
        """DIN 5480 - 30×1.25×22 典型规格"""
        r = derive_involute_geometry(module_mm=1.25, tooth_count=22)
        assert r["reference_diameter_mm"] == pytest.approx(27.5)
        assert r["tip_diameter_shaft_mm"] == pytest.approx(28.75)

    def test_invalid_module_zero(self):
        with pytest.raises(GeometryError, match="模数"):
            derive_involute_geometry(module_mm=0.0, tooth_count=20)

    def test_invalid_tooth_count_too_small(self):
        with pytest.raises(GeometryError, match="齿数"):
            derive_involute_geometry(module_mm=2.0, tooth_count=5)

    def test_output_keys(self):
        r = derive_involute_geometry(module_mm=2.0, tooth_count=20)
        expected_keys = {
            "module_mm", "tooth_count", "pressure_angle_deg",
            "reference_diameter_mm", "tip_diameter_shaft_mm",
            "root_diameter_shaft_mm", "tip_diameter_hub_mm",
            "effective_tooth_height_mm", "mean_diameter_mm",
        }
        assert expected_keys.issubset(set(r.keys()))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_geometry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.spline'`

- [ ] **Step 3: Implement geometry module**

```python
# core/spline/__init__.py
"""Spline interference-fit calculation module."""

from .geometry import GeometryError, derive_involute_geometry

__all__ = ["GeometryError", "derive_involute_geometry"]
```

```python
# core/spline/geometry.py
"""Involute spline geometry derivation (DIN 5480 simplified)."""

from __future__ import annotations


class GeometryError(ValueError):
    """Raised when spline geometry parameters are invalid."""


def derive_involute_geometry(
    *,
    module_mm: float,
    tooth_count: int,
    pressure_angle_deg: float = 30.0,
) -> dict:
    """Derive involute spline geometry from module and tooth count.

    DIN 5480 simplified: external spline (shaft) geometry.
    Returns all dimensions in mm.
    """
    if module_mm <= 0:
        raise GeometryError(f"模数 m 必须 > 0，当前值 {module_mm}")
    if tooth_count < 6:
        raise GeometryError(f"齿数 z 必须 >= 6，当前值 {tooth_count}")
    if not (15.0 <= pressure_angle_deg <= 45.0):
        raise GeometryError(
            f"压力角必须在 15°~45° 之间，当前值 {pressure_angle_deg}"
        )

    m = module_mm
    z = tooth_count

    d = m * z                          # 分度圆直径
    d_a1 = m * (z + 1.0)              # 外花键齿顶圆
    d_f1 = m * (z - 1.25)             # 外花键齿根圆
    d_a2 = m * (z - 1.0)              # 内花键齿顶圆
    h_w = (d_a1 - d_a2) / 2.0         # 有效齿高（单侧）
    d_m = (d_a1 + d_f1) / 2.0         # 平均直径

    return {
        "module_mm": m,
        "tooth_count": z,
        "pressure_angle_deg": pressure_angle_deg,
        "reference_diameter_mm": d,
        "tip_diameter_shaft_mm": d_a1,
        "root_diameter_shaft_mm": d_f1,
        "tip_diameter_hub_mm": d_a2,
        "effective_tooth_height_mm": h_w,
        "mean_diameter_mm": d_m,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_geometry.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/spline/__init__.py core/spline/geometry.py \
        tests/core/spline/__init__.py tests/core/spline/test_geometry.py
git commit -m "feat(spline): add involute spline geometry derivation (DIN 5480)"
```

---

## Task 2: 场景 A 计算引擎 — 齿面承压校核

**Files:**
- Create: `core/spline/calculator.py`
- Create: `tests/core/spline/test_calculator.py`

- [ ] **Step 1: Write failing tests for scenario A**

```python
# tests/core/spline/test_calculator.py
import math
import pytest
from core.spline.calculator import (
    InputError,
    calculate_spline_fit,
)


def make_scenario_a_case() -> dict:
    """Scenario A: involute spline tooth flank interference only."""
    return {
        "mode": "spline_only",
        "spline": {
            "module_mm": 2.0,
            "tooth_count": 20,
            "engagement_length_mm": 30.0,
            "k_alpha": 1.0,
            "p_allowable_mpa": 100.0,
        },
        "loads": {
            "torque_required_nm": 500.0,
            "application_factor_ka": 1.25,
        },
        "checks": {
            "flank_safety_min": 1.3,
        },
    }


class TestScenarioA:
    def test_nominal_case_passes(self):
        result = calculate_spline_fit(make_scenario_a_case())
        assert result["scenario_a"]["flank_pressure_mpa"] > 0
        assert result["scenario_a"]["torque_capacity_nm"] > 0
        assert result["scenario_a"]["flank_safety"] >= 1.3
        assert result["scenario_a"]["flank_ok"] is True
        assert result["overall_pass"] is True

    def test_geometry_auto_derived(self):
        result = calculate_spline_fit(make_scenario_a_case())
        geo = result["scenario_a"]["geometry"]
        assert geo["reference_diameter_mm"] == pytest.approx(40.0)
        assert geo["effective_tooth_height_mm"] == pytest.approx(2.0)

    def test_high_torque_fails(self):
        case = make_scenario_a_case()
        case["loads"]["torque_required_nm"] = 50000.0
        result = calculate_spline_fit(case)
        assert result["scenario_a"]["flank_ok"] is False
        assert result["overall_pass"] is False

    def test_flank_pressure_formula(self):
        """Verify: p = 2*T*K_A*K_alpha / (z*h_w*d_m*L)"""
        case = make_scenario_a_case()
        result = calculate_spline_fit(case)
        T = 500.0 * 1000  # N·mm
        K_A = 1.25
        K_alpha = 1.0
        z = 20
        h_w = 2.0
        d_m = 39.75
        L = 30.0
        p_expected = (2 * T * K_A * K_alpha) / (z * h_w * d_m * L)
        assert result["scenario_a"]["flank_pressure_mpa"] == pytest.approx(
            p_expected, rel=1e-3
        )

    def test_torque_capacity_formula(self):
        """Verify: T_form = p_zul * z * h_w * d_m * L / (2 * K_alpha)"""
        case = make_scenario_a_case()
        result = calculate_spline_fit(case)
        p_zul = 100.0
        z = 20
        h_w = 2.0
        d_m = 39.75
        L = 30.0
        K_alpha = 1.0
        T_expected_nmm = p_zul * z * h_w * d_m * L / (2 * K_alpha)
        T_expected_nm = T_expected_nmm / 1000.0
        assert result["scenario_a"]["torque_capacity_nm"] == pytest.approx(
            T_expected_nm, rel=1e-3
        )

    def test_missing_module_raises(self):
        case = make_scenario_a_case()
        del case["spline"]["module_mm"]
        with pytest.raises(InputError, match="module_mm"):
            calculate_spline_fit(case)

    def test_missing_torque_raises(self):
        case = make_scenario_a_case()
        del case["loads"]["torque_required_nm"]
        with pytest.raises(InputError, match="torque_required_nm"):
            calculate_spline_fit(case)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_calculator.py -v`
Expected: FAIL — `ImportError: cannot import name 'calculate_spline_fit'`

- [ ] **Step 3: Implement scenario A calculation**

```python
# core/spline/calculator.py
"""Spline interference-fit calculator: tooth-flank (A) + smooth-bore (B)."""

from __future__ import annotations

import math
from typing import Any, Dict

from .geometry import derive_involute_geometry


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


def _calculate_scenario_a(
    spline: Dict[str, Any],
    torque_design_nm: float,
    flank_safety_min: float,
) -> Dict[str, Any]:
    """Scenario A: involute spline tooth flank bearing stress check."""
    m = _positive(float(_require(spline, "module_mm", "spline")), "spline.module_mm")
    z = int(_require(spline, "tooth_count", "spline"))
    L = _positive(
        float(_require(spline, "engagement_length_mm", "spline")),
        "spline.engagement_length_mm",
    )
    k_alpha = _positive(
        float(spline.get("k_alpha", 1.0)), "spline.k_alpha"
    )
    p_zul = _positive(
        float(_require(spline, "p_allowable_mpa", "spline")),
        "spline.p_allowable_mpa",
    )

    geo = derive_involute_geometry(module_mm=m, tooth_count=z)
    h_w = geo["effective_tooth_height_mm"]
    d_m = geo["mean_diameter_mm"]

    T_design_nmm = torque_design_nm * 1000.0

    p_flank = (2.0 * T_design_nmm * k_alpha) / (z * h_w * d_m * L)

    T_cap_nmm = p_zul * z * h_w * d_m * L / (2.0 * k_alpha)
    T_cap_nm = T_cap_nmm / 1000.0

    flank_sf = p_zul / p_flank if p_flank > 0 else math.inf
    flank_ok = flank_sf >= flank_safety_min

    return {
        "geometry": geo,
        "engagement_length_mm": L,
        "k_alpha": k_alpha,
        "p_allowable_mpa": p_zul,
        "flank_pressure_mpa": p_flank,
        "torque_capacity_nm": T_cap_nm,
        "torque_design_nm": torque_design_nm,
        "flank_safety": flank_sf,
        "flank_safety_min": flank_safety_min,
        "flank_ok": flank_ok,
    }


def calculate_spline_fit(data: Dict[str, Any]) -> Dict[str, Any]:
    """Main entry point for spline interference-fit calculation."""
    mode = str(data.get("mode", "spline_only"))
    spline = data.get("spline", {})
    loads = data.get("loads", {})
    checks = data.get("checks", {})

    torque_required_nm = _positive(
        float(_require(loads, "torque_required_nm", "loads")),
        "loads.torque_required_nm",
    )
    ka = _positive(float(loads.get("application_factor_ka", 1.0)), "loads.application_factor_ka")
    torque_design_nm = torque_required_nm * ka

    flank_safety_min = _positive(
        float(checks.get("flank_safety_min", 1.3)), "checks.flank_safety_min"
    )

    scenario_a = _calculate_scenario_a(spline, torque_design_nm, flank_safety_min)

    scenario_b = None
    scenario_b_pass = True
    if mode == "combined":
        # Scenario B placeholder — implemented in Task 3
        pass

    overall_pass = scenario_a["flank_ok"] and scenario_b_pass

    warnings: list[str] = []
    if not scenario_a["flank_ok"]:
        warnings.append(
            f"齿面承压安全系数 {scenario_a['flank_safety']:.2f}"
            f" < 最小要求 {flank_safety_min}，齿面承载不足。"
        )

    result: Dict[str, Any] = {
        "inputs_echo": data,
        "mode": mode,
        "loads": {
            "torque_required_nm": torque_required_nm,
            "torque_design_nm": torque_design_nm,
            "application_factor_ka": ka,
        },
        "scenario_a": scenario_a,
        "overall_pass": overall_pass,
        "messages": warnings,
    }
    if scenario_b is not None:
        result["scenario_b"] = scenario_b
    return result
```

Update `__init__.py`:
```python
# core/spline/__init__.py
"""Spline interference-fit calculation module."""

from .calculator import InputError, calculate_spline_fit
from .geometry import GeometryError, derive_involute_geometry

__all__ = [
    "InputError",
    "GeometryError",
    "calculate_spline_fit",
    "derive_involute_geometry",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/spline/calculator.py core/spline/__init__.py \
        tests/core/spline/test_calculator.py
git commit -m "feat(spline): add scenario A tooth-flank bearing stress calculator"
```

---

## Task 3: 场景 B 计算引擎 — 光滑段圆柱过盈（复用 DIN 7190）

**Files:**
- Modify: `core/spline/calculator.py`
- Modify: `tests/core/spline/test_calculator.py`

- [ ] **Step 1: Write failing tests for scenario B**

追加到 `tests/core/spline/test_calculator.py`：

```python
def make_combined_case() -> dict:
    """Combined mode: scenario A + scenario B."""
    return {
        "mode": "combined",
        "spline": {
            "module_mm": 2.0,
            "tooth_count": 20,
            "engagement_length_mm": 30.0,
            "k_alpha": 1.0,
            "p_allowable_mpa": 100.0,
        },
        "smooth_fit": {
            "shaft_d_mm": 40.0,
            "shaft_inner_d_mm": 0.0,
            "hub_outer_d_mm": 80.0,
            "fit_length_mm": 45.0,
            "relief_groove_width_mm": 3.0,
            "delta_min_um": 20.0,
            "delta_max_um": 45.0,
        },
        "smooth_materials": {
            "shaft_e_mpa": 210000.0,
            "shaft_nu": 0.30,
            "shaft_yield_mpa": 600.0,
            "hub_e_mpa": 210000.0,
            "hub_nu": 0.30,
            "hub_yield_mpa": 320.0,
        },
        "smooth_roughness": {
            "shaft_rz_um": 6.3,
            "hub_rz_um": 6.3,
        },
        "smooth_friction": {
            "mu_torque": 0.14,
            "mu_axial": 0.14,
            "mu_assembly": 0.12,
        },
        "loads": {
            "torque_required_nm": 500.0,
            "axial_force_required_n": 0.0,
            "application_factor_ka": 1.25,
        },
        "checks": {
            "flank_safety_min": 1.3,
            "slip_safety_min": 1.5,
            "stress_safety_min": 1.2,
        },
    }


class TestScenarioB:
    def test_combined_mode_has_both_scenarios(self):
        result = calculate_spline_fit(make_combined_case())
        assert "scenario_a" in result
        assert "scenario_b" in result

    def test_scenario_b_pressure_positive(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert b["pressure_mpa"]["p_min"] > 0
        assert b["pressure_mpa"]["p_max"] > b["pressure_mpa"]["p_min"]

    def test_relief_groove_reduces_effective_length(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert b["effective_fit_length_mm"] == pytest.approx(42.0)

    def test_scenario_b_torque_capacity(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert b["capacity"]["torque_min_nm"] > 0

    def test_scenario_b_slip_safety(self):
        result = calculate_spline_fit(make_combined_case())
        b = result["scenario_b"]
        assert "torque_sf" in b["safety"]

    def test_overall_pass_requires_both(self):
        case = make_combined_case()
        case["loads"]["torque_required_nm"] = 50000.0
        result = calculate_spline_fit(case)
        assert result["overall_pass"] is False

    def test_spline_only_mode_no_scenario_b(self):
        case = make_combined_case()
        case["mode"] = "spline_only"
        result = calculate_spline_fit(case)
        assert "scenario_b" not in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_calculator.py::TestScenarioB -v`
Expected: FAIL — scenario_b not implemented yet

- [ ] **Step 3: Implement scenario B in calculator.py**

Add `_calculate_scenario_b` function to `core/spline/calculator.py`:

```python
def _calculate_scenario_b(
    smooth_fit: Dict[str, Any],
    smooth_materials: Dict[str, Any],
    smooth_roughness: Dict[str, Any],
    smooth_friction: Dict[str, Any],
    torque_design_nm: float,
    axial_design_n: float,
    slip_safety_min: float,
    stress_safety_min: float,
) -> Dict[str, Any]:
    """Scenario B: smooth-section cylindrical press fit (reuse DIN 7190 Lamé)."""
    from core.interference.calculator import calculate_interference_fit

    l_nominal = _positive(
        float(_require(smooth_fit, "fit_length_mm", "smooth_fit")),
        "smooth_fit.fit_length_mm",
    )
    relief_groove = float(smooth_fit.get("relief_groove_width_mm", 0.0))
    if relief_groove < 0:
        raise InputError("smooth_fit.relief_groove_width_mm 不能为负数")
    l_fit = l_nominal - relief_groove
    if l_fit <= 0:
        raise InputError("退刀槽宽度 >= 配合长度，有效配合长度 <= 0")

    # Delegate to existing DIN 7190 calculator with effective fit length.
    # Validation of geometry/materials/friction is handled by the delegate.
    delegate_data = {
        "geometry": {
            "shaft_d_mm": float(smooth_fit.get("shaft_d_mm", 0)),
            "shaft_inner_d_mm": float(smooth_fit.get("shaft_inner_d_mm", 0)),
            "hub_outer_d_mm": float(smooth_fit.get("hub_outer_d_mm", 0)),
            "fit_length_mm": l_fit,  # effective length after groove deduction
        },
        "materials": smooth_materials,
        "fit": {
            "delta_min_um": float(smooth_fit.get("delta_min_um", 0)),
            "delta_max_um": float(smooth_fit.get("delta_max_um", 0)),
        },
        "roughness": smooth_roughness,
        "friction": smooth_friction,
        "loads": {
            "torque_required_nm": torque_design_nm,  # already factored by K_A
            "axial_force_required_n": axial_design_n,
            "application_factor_ka": 1.0,  # K_A already applied
        },
        "checks": {
            "slip_safety_min": slip_safety_min,
            "stress_safety_min": stress_safety_min,
        },
    }
    din7190_result = calculate_interference_fit(delegate_data)

    return {
        "nominal_fit_length_mm": l_nominal,
        "relief_groove_width_mm": relief_groove,
        "effective_fit_length_mm": l_fit,
        "pressure_mpa": din7190_result["pressure_mpa"],
        "capacity": din7190_result["capacity"],
        "assembly": din7190_result["assembly"],
        "stress_mpa": din7190_result["stress_mpa"],
        "safety": din7190_result["safety"],
        "checks": din7190_result["checks"],
        "overall_pass": din7190_result["overall_pass"],
        "press_force_curve": din7190_result["press_force_curve"],
        "roughness": din7190_result["roughness"],
        "messages": din7190_result["messages"],
    }
```

Update `calculate_spline_fit` to wire scenario B — replace the `if mode == "combined": pass` block with:

```python
    scenario_b = None
    scenario_b_pass = True
    if mode == "combined":
        smooth_fit = data.get("smooth_fit", {})
        smooth_materials = data.get("smooth_materials", {})
        smooth_roughness = data.get("smooth_roughness", {})
        smooth_friction = data.get("smooth_friction", {})
        axial_required_n = _positive(
            float(loads.get("axial_force_required_n", 0.0)),
            "loads.axial_force_required_n",
            allow_zero=True,
        )
        axial_design_n = axial_required_n * ka
        slip_safety_min = _positive(
            float(checks.get("slip_safety_min", 1.5)), "checks.slip_safety_min"
        )
        stress_safety_min = _positive(
            float(checks.get("stress_safety_min", 1.2)), "checks.stress_safety_min"
        )
        scenario_b = _calculate_scenario_b(
            smooth_fit, smooth_materials, smooth_roughness, smooth_friction,
            torque_design_nm, axial_design_n, slip_safety_min, stress_safety_min,
        )
        scenario_b_pass = scenario_b["overall_pass"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/spline/calculator.py tests/core/spline/test_calculator.py
git commit -m "feat(spline): add scenario B smooth-bore press fit via DIN 7190 delegation"
```

---

## Task 4: UI 页面 — 花键过盈配合

**Files:**
- Create: `app/ui/pages/spline_fit_page.py`
- Modify: `app/ui/main_window.py:61-68`

- [ ] **Step 1: Create spline_fit_page.py with chapter-style layout**

页面章节结构：

| 步骤 | 章节标题 | 内容 |
|------|---------|------|
| 1 | 校核目标 | 安全系数、KA、模式选择（仅花键 / 联合） |
| 2 | 花键几何 | m, z, 啮合长度, K_α, 许用齿面压力, 材料工况下拉 |
| 3 | 光滑段过盈 | 配合直径, 轮毂外径, 配合长度, 退刀槽, 过盈量, 材料, 摩擦 |
| 4 | 载荷工况 | 扭矩, 轴向力 |
| 5 | 计算结果 | 双场景结果卡片 + 总判定 |

遵循现有 `InterferenceFitPage` 的 `FieldSpec` + `CHAPTERS` 数据驱动模式。

关键实现要点：
- 继承 `BaseChapterPage`
- `FieldSpec` 定义所有字段，`mapping` 指向 payload 路径
- `_build_payload()` 构建 `calculate_spline_fit(data)` 的 dict
- "仅花键" 模式下隐藏步骤 3 的所有字段
- 结果章节用 PassBadge/FailBadge 展示两个场景的判定
- "计算" 按钮触发 `_on_calculate()`

```python
# app/ui/pages/spline_fit_page.py
"""Spline interference-fit module page with chapter-style workflow."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.base_chapter_page import BaseChapterPage
from core.spline.calculator import InputError, calculate_spline_fit


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    label: str
    unit: str
    hint: str
    mapping: tuple[str, str] | None = None
    widget_type: str = "number"
    options: tuple[str, ...] = ()
    default: str = ""
    placeholder: str = ""


# --- Material / condition presets ---

LOAD_CONDITION_OPTIONS: tuple[str, ...] = (
    "固定连接，静载，调质钢",
    "固定连接，静载，渗碳淬火",
    "固定连接，脉动载荷，调质钢",
    "固定连接，脉动载荷，渗碳淬火",
    "自定义",
)
LOAD_CONDITION_P_ZUL: dict[str, float] = {
    "固定连接，静载，调质钢": 100.0,
    "固定连接，静载，渗碳淬火": 150.0,
    "固定连接，脉动载荷，调质钢": 60.0,
    "固定连接，脉动载荷，渗碳淬火": 80.0,
}

MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "45钢": {"e_mpa": 210000.0, "nu": 0.30},
    "40Cr": {"e_mpa": 210000.0, "nu": 0.29},
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29},
    "自定义": None,
}

SMOOTH_FIT_FIELD_IDS: list[str] = [
    "smooth_fit.shaft_d_mm", "smooth_fit.shaft_inner_d_mm",
    "smooth_fit.hub_outer_d_mm", "smooth_fit.fit_length_mm",
    "smooth_fit.relief_groove_width_mm",
    "smooth_fit.delta_min_um", "smooth_fit.delta_max_um",
    "smooth_materials.shaft_material", "smooth_materials.shaft_e_mpa",
    "smooth_materials.shaft_nu", "smooth_materials.shaft_yield_mpa",
    "smooth_materials.hub_material", "smooth_materials.hub_e_mpa",
    "smooth_materials.hub_nu", "smooth_materials.hub_yield_mpa",
    "smooth_friction.mu_torque", "smooth_friction.mu_axial",
    "smooth_friction.mu_assembly",
    "smooth_roughness.shaft_rz_um", "smooth_roughness.hub_rz_um",
]

# --- Chapter definitions ---

CHAPTERS: list[dict[str, Any]] = [
    {
        "title": "校核目标",
        "subtitle": "选择校核模式、安全系数与工况系数。",
        "fields": [
            FieldSpec(
                "mode", "校核模式", "-",
                "仅花键：只校核齿面承压；联合：同时校核光滑段圆柱过盈。",
                widget_type="choice",
                options=("仅花键", "联合"),
                default="联合",
            ),
            FieldSpec(
                "checks.flank_safety_min", "齿面最小安全系数 S_flank,min", "-",
                "场景 A 齿面承压校核使用的最小安全系数。",
                mapping=("checks", "flank_safety_min"),
                default="1.30", placeholder="建议 1.2~1.5",
            ),
            FieldSpec(
                "checks.slip_safety_min", "防滑最小安全系数 S_slip,min", "-",
                "场景 B 光滑段防滑校核使用的最小安全系数。",
                mapping=("checks", "slip_safety_min"),
                default="1.50", placeholder="建议 1.2~2.0",
            ),
            FieldSpec(
                "checks.stress_safety_min", "材料最小安全系数 S_sigma,min", "-",
                "场景 B 轴/轮毂应力校核使用的最小安全系数。",
                mapping=("checks", "stress_safety_min"),
                default="1.20", placeholder="建议 1.1~1.8",
            ),
            FieldSpec(
                "loads.application_factor_ka", "工况系数 KA", "-",
                "同时放大场景 A 和场景 B 的设计载荷。",
                mapping=("loads", "application_factor_ka"),
                default="1.25", placeholder="建议 1.0~2.25",
            ),
        ],
    },
    {
        "title": "花键几何",
        "subtitle": "渐开线花键 (DIN 5480) 参数，α=30° 固定。",
        "fields": [
            FieldSpec(
                "spline.module_mm", "模数 m", "mm",
                "渐开线花键模数。",
                mapping=("spline", "module_mm"),
                default="2.0", placeholder="例如 1.25, 2.0",
            ),
            FieldSpec(
                "spline.tooth_count", "齿数 z", "-",
                "花键齿数，最小 6。",
                mapping=("spline", "tooth_count"),
                default="20", placeholder="例如 20, 30",
            ),
            FieldSpec(
                "spline.engagement_length_mm", "有效啮合长度 L", "mm",
                "花键齿面轴向有效接触长度。",
                mapping=("spline", "engagement_length_mm"),
                default="30.0", placeholder="例如 30",
            ),
            FieldSpec(
                "spline.k_alpha", "载荷分布系数 K_α", "-",
                "过盈配合取 1.0~1.2；间隙配合取 1.5~2.0。",
                mapping=("spline", "k_alpha"),
                default="1.0", placeholder="过盈配合建议 1.0",
            ),
            FieldSpec(
                "spline.load_condition", "载荷工况", "-",
                "选择后自动填充许用齿面压力；切到自定义手工输入。",
                widget_type="choice",
                options=LOAD_CONDITION_OPTIONS,
                default="固定连接，静载，调质钢",
            ),
            FieldSpec(
                "spline.p_allowable_mpa", "许用齿面压力 p_zul", "MPa",
                "取决于材料状态和载荷类型（见参考值表）。",
                mapping=("spline", "p_allowable_mpa"),
                default="100.0", placeholder="例如 60~200",
            ),
        ],
    },
    {
        "title": "光滑段过盈",
        "subtitle": "花键轴光滑段压入圆柱孔的 DIN 7190 圆柱过盈参数。仅花键模式下跳过此步。",
        "fields": [
            FieldSpec(
                "smooth_fit.shaft_d_mm", "配合直径 d", "mm",
                "光滑段轴径（与花键分度圆径可能不同）。",
                mapping=("smooth_fit", "shaft_d_mm"),
                default="40.0", placeholder="例如 40",
            ),
            FieldSpec(
                "smooth_fit.shaft_inner_d_mm", "轴内径 d_i", "mm",
                "0 表示实心轴。",
                mapping=("smooth_fit", "shaft_inner_d_mm"),
                default="0.0", placeholder="实心轴填 0",
            ),
            FieldSpec(
                "smooth_fit.hub_outer_d_mm", "轮毂外径 D", "mm",
                "轮毂外圆直径。",
                mapping=("smooth_fit", "hub_outer_d_mm"),
                default="80.0", placeholder="例如 80",
            ),
            FieldSpec(
                "smooth_fit.fit_length_mm", "名义配合长度 L", "mm",
                "轴向名义接触长度（含退刀槽，计算时自动扣除）。",
                mapping=("smooth_fit", "fit_length_mm"),
                default="45.0", placeholder="例如 45",
            ),
            FieldSpec(
                "smooth_fit.relief_groove_width_mm", "退刀槽宽度", "mm",
                "花键→光滑段过渡处退刀槽宽度，自动从配合长度中扣除。",
                mapping=("smooth_fit", "relief_groove_width_mm"),
                default="3.0", placeholder="例如 2~5",
            ),
            FieldSpec(
                "smooth_fit.delta_min_um", "最小过盈量 δ_min", "um",
                "直径值。", mapping=("smooth_fit", "delta_min_um"),
                default="20.0", placeholder="例如 20",
            ),
            FieldSpec(
                "smooth_fit.delta_max_um", "最大过盈量 δ_max", "um",
                "直径值。", mapping=("smooth_fit", "delta_max_um"),
                default="45.0", placeholder="例如 45",
            ),
            FieldSpec(
                "smooth_materials.shaft_material", "轴材料", "-",
                "选择后自动填充 E 与 nu。",
                widget_type="choice",
                options=tuple(MATERIAL_LIBRARY.keys()),
                default="45钢",
            ),
            FieldSpec(
                "smooth_materials.shaft_e_mpa", "轴弹性模量 E_s", "MPa",
                "", mapping=("smooth_materials", "shaft_e_mpa"),
                default="210000", placeholder="例如 210000",
            ),
            FieldSpec(
                "smooth_materials.shaft_nu", "轴泊松比 ν_s", "-",
                "", mapping=("smooth_materials", "shaft_nu"),
                default="0.30",
            ),
            FieldSpec(
                "smooth_materials.shaft_yield_mpa", "轴屈服强度 Re_s", "MPa",
                "", mapping=("smooth_materials", "shaft_yield_mpa"),
                default="600",
            ),
            FieldSpec(
                "smooth_materials.hub_material", "轮毂材料", "-",
                "",
                widget_type="choice",
                options=tuple(MATERIAL_LIBRARY.keys()),
                default="45钢",
            ),
            FieldSpec(
                "smooth_materials.hub_e_mpa", "轮毂弹性模量 E_h", "MPa",
                "", mapping=("smooth_materials", "hub_e_mpa"),
                default="210000",
            ),
            FieldSpec(
                "smooth_materials.hub_nu", "轮毂泊松比 ν_h", "-",
                "", mapping=("smooth_materials", "hub_nu"),
                default="0.30",
            ),
            FieldSpec(
                "smooth_materials.hub_yield_mpa", "轮毂屈服强度 Re_h", "MPa",
                "", mapping=("smooth_materials", "hub_yield_mpa"),
                default="320",
            ),
            FieldSpec(
                "smooth_friction.mu_torque", "摩擦系数 μ_T（扭矩）", "-",
                "", mapping=("smooth_friction", "mu_torque"),
                default="0.14",
            ),
            FieldSpec(
                "smooth_friction.mu_axial", "摩擦系数 μ_ax（轴向）", "-",
                "", mapping=("smooth_friction", "mu_axial"),
                default="0.14",
            ),
            FieldSpec(
                "smooth_friction.mu_assembly", "装配摩擦系数 μ_M", "-",
                "", mapping=("smooth_friction", "mu_assembly"),
                default="0.12",
            ),
            FieldSpec(
                "smooth_roughness.shaft_rz_um", "轴 Rz", "um",
                "", mapping=("smooth_roughness", "shaft_rz_um"),
                default="6.3",
            ),
            FieldSpec(
                "smooth_roughness.hub_rz_um", "轮毂 Rz", "um",
                "", mapping=("smooth_roughness", "hub_rz_um"),
                default="6.3",
            ),
        ],
    },
    {
        "title": "载荷工况",
        "subtitle": "输入设计扭矩和轴向力（两场景共用）。",
        "fields": [
            FieldSpec(
                "loads.torque_required_nm", "名义扭矩 T", "N·m",
                "两场景共用的名义扭矩。",
                mapping=("loads", "torque_required_nm"),
                default="500.0", placeholder="例如 500",
            ),
            FieldSpec(
                "loads.axial_force_required_n", "轴向力 F_ax", "N",
                "仅场景 B 使用。",
                mapping=("loads", "axial_force_required_n"),
                default="0.0", placeholder="例如 0",
            ),
        ],
    },
    {
        "title": "计算结果",
        "subtitle": "场景 A（齿面承压）+ 场景 B（光滑段过盈）独立校核结果。",
        "fields": [],
    },
]


# --- Mode mapping ---
MODE_MAP: dict[str, str] = {"仅花键": "spline_only", "联合": "combined"}


class SplineFitPage(BaseChapterPage):
    """Spline interference-fit page with chapter navigation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("花键过盈配合", "渐开线花键 (DIN 5480) 齿面承压 + 光滑段圆柱过盈 (DIN 7190)", parent)

        self._widgets: dict[str, QWidget] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._result_labels: dict[str, QLabel] = {}

        calc_btn = self.add_action_button("计算", primary=True)
        calc_btn.clicked.connect(self._on_calculate)

        for chapter in CHAPTERS:
            page = self._build_chapter_page(chapter)
            self.add_chapter(chapter["title"], page)

        self.set_current_chapter(0)
        # Connect mode combo to show/hide smooth-fit fields
        mode_combo = self._widgets.get("mode")
        if isinstance(mode_combo, QComboBox):
            mode_combo.currentTextChanged.connect(self._on_mode_changed)
            self._on_mode_changed(mode_combo.currentText())

    # --- Chapter page builder (same pattern as InterferenceFitPage) ---

    def _build_chapter_page(self, chapter: dict) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        if chapter["title"] == "计算结果":
            self._build_result_chapter(layout)
        else:
            sub = QLabel(chapter.get("subtitle", ""))
            sub.setObjectName("SectionHint")
            sub.setWordWrap(True)
            layout.addWidget(sub)
            for spec in chapter["fields"]:
                card = self._build_field_card(spec)
                layout.addWidget(card)
                self._field_cards[spec.field_id] = card

        layout.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    def _build_field_card(self, spec: FieldSpec) -> QFrame:
        """Build a single field card with label + widget + hint."""
        card = QFrame()
        card.setObjectName("SubCard")
        grid = QGridLayout(card)
        grid.setContentsMargins(8, 6, 8, 6)
        label = QLabel(f"{spec.label} [{spec.unit}]" if spec.unit != "-" else spec.label)
        grid.addWidget(label, 0, 0)

        if spec.widget_type == "choice":
            w = QComboBox()
            w.addItems(spec.options)
            if spec.default:
                idx = w.findText(spec.default)
                if idx >= 0:
                    w.setCurrentIndex(idx)
        else:
            w = QLineEdit()
            w.setText(spec.default)
            w.setPlaceholderText(spec.placeholder)
        grid.addWidget(w, 0, 1)

        if spec.hint:
            hint = QLabel(spec.hint)
            hint.setObjectName("SectionHint")
            hint.setWordWrap(True)
            grid.addWidget(hint, 1, 0, 1, 2)

        self._widgets[spec.field_id] = w
        return card

    def _build_result_chapter(self, layout: QVBoxLayout) -> None:
        """Build the result display chapter with labels for both scenarios."""
        for scenario, title in [("a", "场景 A — 齿面承压"), ("b", "场景 B — 光滑段过盈")]:
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            title_lbl = QLabel(title)
            title_lbl.setObjectName("SectionTitle")
            card_layout.addWidget(title_lbl)
            badge = QLabel("等待计算")
            badge.setObjectName("WaitBadge")
            card_layout.addWidget(badge)
            detail = QLabel("")
            detail.setWordWrap(True)
            card_layout.addWidget(detail)
            self._result_labels[f"{scenario}_badge"] = badge
            self._result_labels[f"{scenario}_detail"] = detail
            layout.addWidget(card)

    # --- Mode switching ---

    def _on_mode_changed(self, text: str) -> None:
        is_combined = (text == "联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = self._field_cards.get(fid)
            if card:
                card.setVisible(is_combined)
        # Also show/hide slip & stress safety fields
        for fid in ("checks.slip_safety_min", "checks.stress_safety_min"):
            card = self._field_cards.get(fid)
            if card:
                card.setVisible(is_combined)

    # --- Build payload ---

    def _get_value(self, field_id: str) -> str:
        w = self._widgets.get(field_id)
        if isinstance(w, QComboBox):
            return w.currentText()
        if isinstance(w, QLineEdit):
            return w.text().strip()
        return ""

    def _build_payload(self) -> dict:
        mode_text = self._get_value("mode")
        mode = MODE_MAP.get(mode_text, "spline_only")

        payload: dict[str, Any] = {"mode": mode, "spline": {}, "loads": {}, "checks": {}}
        for chapter in CHAPTERS:
            for spec in chapter["fields"]:
                if spec.mapping is None:
                    continue
                section, key = spec.mapping
                if section not in payload:
                    payload[section] = {}
                raw = self._get_value(spec.field_id)
                if not raw:
                    continue
                try:
                    payload[section][key] = float(raw)
                except ValueError:
                    payload[section][key] = raw
        return payload

    # --- Calculate ---

    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_spline_fit(payload)
        except (InputError, Exception) as exc:
            self.set_overall_status(f"输入错误: {exc}", "fail")
            self.set_info(str(exc))
            return

        self._display_result(result)

    def _display_result(self, result: dict) -> None:
        a = result["scenario_a"]
        a_badge = self._result_labels["a_badge"]
        a_detail = self._result_labels["a_detail"]
        if a["flank_ok"]:
            a_badge.setText("PASS")
            a_badge.setObjectName("PassBadge")
        else:
            a_badge.setText("FAIL")
            a_badge.setObjectName("FailBadge")
        a_badge.style().unpolish(a_badge)
        a_badge.style().polish(a_badge)
        a_detail.setText(
            f"齿面压力 p = {a['flank_pressure_mpa']:.1f} MPa, "
            f"许用 p_zul = {a['p_allowable_mpa']:.0f} MPa, "
            f"安全系数 S = {a['flank_safety']:.2f}"
        )

        b_badge = self._result_labels["b_badge"]
        b_detail = self._result_labels["b_detail"]
        if "scenario_b" in result:
            b = result["scenario_b"]
            if b["overall_pass"]:
                b_badge.setText("PASS")
                b_badge.setObjectName("PassBadge")
            else:
                b_badge.setText("FAIL")
                b_badge.setObjectName("FailBadge")
            b_badge.style().unpolish(b_badge)
            b_badge.style().polish(b_badge)
            b_detail.setText(
                f"接触压力 p_min = {b['pressure_mpa']['p_min']:.1f} MPa, "
                f"打滑扭矩 T_min = {b['capacity']['torque_min_nm']:.1f} N·m, "
                f"有效长度 = {b['effective_fit_length_mm']:.1f} mm"
            )
        else:
            b_badge.setText("未启用")
            b_badge.setObjectName("WaitBadge")
            b_badge.style().unpolish(b_badge)
            b_badge.style().polish(b_badge)
            b_detail.setText("仅花键模式，光滑段过盈校核已跳过。")

        if result["overall_pass"]:
            self.set_overall_status("ALL PASS", "pass")
        else:
            self.set_overall_status("FAIL", "fail")

        msgs = result.get("messages", [])
        self.set_info("\n".join(msgs) if msgs else "校核完成。")
```

- [ ] **Step 2: Register in main_window.py**

Replace the placeholder line:
```python
# Before:
("花键过盈配合设计", PlaceholderPage("花键过盈配合设计", self)),

# After:
("花键过盈配合", SplineFitPage(self)),
```

Add import:
```python
from app.ui.pages.spline_fit_page import SplineFitPage
```

- [ ] **Step 3: Run app manually to verify layout**

Run: `python3 app/main.py`
Expected: 侧栏显示"花键过盈配合"，点击进入可看到章节导航和字段表单。

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/spline_fit_page.py app/ui/main_window.py
git commit -m "feat(spline): add spline interference fit UI page"
```

---

## Task 5: UI 测试

**Files:**
- Create: `tests/ui/test_spline_fit_page.py`

- [ ] **Step 1: Write UI smoke tests**

```python
# tests/ui/test_spline_fit_page.py
import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.spline_fit_page import SMOOTH_FIT_FIELD_IDS, SplineFitPage


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestSplineFitPage:
    def test_page_creates_without_error(self, app):
        page = SplineFitPage()
        assert page is not None

    def test_chapter_count(self, app):
        page = SplineFitPage()
        assert page.chapter_stack.count() == 5

    def test_calculate_with_defaults(self, app):
        page = SplineFitPage()
        page._on_calculate()
        assert page.overall_badge.objectName() in ("PassBadge", "FailBadge")

    def test_mode_switch_hides_smooth_fields(self, app):
        page = SplineFitPage()
        mode_combo = page._widgets["mode"]
        # Switch to "仅花键" — smooth_fit fields should be hidden
        mode_combo.setCurrentText("仅花键")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = page._field_cards.get(fid)
            if card:
                assert not card.isVisible(), f"{fid} should be hidden in spline-only mode"
        # Switch back to "联合" — smooth_fit fields should be visible
        mode_combo.setCurrentText("联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = page._field_cards.get(fid)
            if card:
                assert card.isVisible(), f"{fid} should be visible in combined mode"
```

- [ ] **Step 2: Run UI tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_spline_fit_page.py -v`
Expected: ALL PASS

- [ ] **Step 3: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: ALL PASS (including existing tests)

- [ ] **Step 4: Commit**

```bash
git add tests/ui/test_spline_fit_page.py
git commit -m "test(spline): add UI smoke tests for spline fit page"
```

---

## Task 6: 集成验证与清理

**Files:**
- All files from Tasks 1-5

- [ ] **Step 1: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Manual app verification**

Run: `python3 app/main.py`
Verify:
1. 侧栏"花键过盈配合"可点击进入
2. 步骤 1~5 章节导航正常
3. 默认参数下点击"计算"能得到结果
4. 切换"仅花键/联合"模式，字段显隐正确
5. 输入不合法参数，错误提示为中文

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore(spline): integration cleanup"
```
