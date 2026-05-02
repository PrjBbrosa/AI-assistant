"""Buffer block single-impact energy-method calculator.

Reference: docs/superpowers/specs/2026-05-02-buffer-energy-simulation-design.md
Sections: Core API, Curve Normalization, Energy Integration, Impact Solve,
Rebound Estimate, Time-domain Reconstruction, Checks.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple


class InputError(ValueError):
    """Raised when input data is incomplete or physically invalid."""


_DUP_X_TOL = 1e-6
_MM_TO_M = 1e-3


def _require(section: Dict[str, Any], key: str, label: str) -> Any:
    if not isinstance(section, dict):
        raise InputError(f"{label} 必须是字典")
    if key not in section:
        raise InputError(f"缺少必填字段: {label}.{key}")
    return section[key]


def _positive(value: float, label: str, allow_zero: bool = False) -> float:
    if allow_zero and value == 0:
        return value
    if value <= 0:
        raise InputError(f"{label} 必须 > 0，当前值 {value}")
    return value


def _normalize_curve(
    raw_points: Sequence[Dict[str, float]],
    label: str,
    *,
    force_scale: float,
    stroke_scale: float,
) -> Tuple[List[Dict[str, float]], List[str]]:
    """Sort, scale, merge duplicate-x points, and validate one curve branch."""
    if not raw_points:
        raise InputError(f"{label} 曲线为空")

    scaled: List[Tuple[float, float]] = []
    for idx, point in enumerate(raw_points):
        try:
            x = float(point["x_mm"]) * stroke_scale
            force = float(point["force_n"]) * force_scale
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(f"{label} 曲线第 {idx + 1} 行解析失败: {exc}") from exc
        if not math.isfinite(x) or not math.isfinite(force):
            raise InputError(f"{label} 曲线第 {idx + 1} 行包含 NaN/Inf")
        if x < -_DUP_X_TOL:
            raise InputError(f"{label} 曲线第 {idx + 1} 行位移为负 ({x:.6g} mm)")
        if force < 0:
            raise InputError(f"{label} 曲线第 {idx + 1} 行力为负 ({force:.6g} N)")
        scaled.append((0.0 if abs(x) < _DUP_X_TOL else x, force))

    scaled.sort(key=lambda item: item[0])

    merged: List[Tuple[float, float]] = []
    i = 0
    while i < len(scaled):
        x0 = scaled[i][0]
        force_sum = scaled[i][1]
        count = 1
        i += 1
        while i < len(scaled) and abs(scaled[i][0] - x0) < _DUP_X_TOL:
            force_sum += scaled[i][1]
            count += 1
            i += 1
        merged.append((x0, force_sum / count))

    warnings: List[str] = []
    if merged[0][0] > _DUP_X_TOL:
        merged.insert(0, (0.0, 0.0))
        warnings.append(f"{label} 曲线起点不是 (0,0)，已补充 (0,0) 用于积分")

    return [{"x_mm": x, "force_n": force} for x, force in merged], warnings


def _trapezoid_area(points: Sequence[Dict[str, float]]) -> float:
    """Trapezoid integral over x-mm / force-N points, returning energy in J."""
    if len(points) < 2:
        return 0.0
    total_n_mm = 0.0
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        if dx <= _DUP_X_TOL:
            continue
        total_n_mm += 0.5 * (prev["force_n"] + curr["force_n"]) * dx
    return total_n_mm * _MM_TO_M


def _accumulate_loading_energy(
    points: Sequence[Dict[str, float]],
) -> Tuple[List[float], List[float]]:
    """Return cumulative loading energy curve as x-mm and energy-J lists."""
    if not points:
        return [], []
    xs: List[float] = [points[0]["x_mm"]]
    energies: List[float] = [0.0]
    cumulative = 0.0
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        if dx <= _DUP_X_TOL:
            continue
        cumulative += 0.5 * (prev["force_n"] + curr["force_n"]) * dx * _MM_TO_M
        xs.append(curr["x_mm"])
        energies.append(cumulative)
    return xs, energies


def _tangent_stiffness_range(points: Sequence[Dict[str, float]]) -> Tuple[float, float]:
    """Return min/max adjacent tangent stiffness dF/dx in N/mm."""
    slopes: List[float] = []
    for prev, curr in zip(points, points[1:]):
        dx = curr["x_mm"] - prev["x_mm"]
        if dx <= _DUP_X_TOL:
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
    peak_force = max(point["force_n"] for point in loading)
    loading_energy = _trapezoid_area(loading)
    unloading_energy = _trapezoid_area(unloading)
    hysteresis = max(0.0, loading_energy - unloading_energy)
    ratio = hysteresis / loading_energy if loading_energy > 0 else 0.0
    k_eq = peak_force / max_stroke if max_stroke > 0 else 0.0
    k_min, k_max = _tangent_stiffness_range(loading)
    return {
        "max_stroke_mm": max_stroke,
        "peak_loading_force_n": peak_force,
        "loading_energy_j": loading_energy,
        "unloading_energy_j": unloading_energy,
        "curve_hysteresis_energy_j": hysteresis,
        "energy_absorption_ratio": ratio,
        "equivalent_stiffness_n_per_mm": k_eq,
        "tangent_stiffness_min_n_per_mm": k_min,
        "tangent_stiffness_max_n_per_mm": k_max,
    }


def _interp_linear(xs: Sequence[float], ys: Sequence[float], target_x: float) -> float:
    """Linear interpolation with endpoint clamping."""
    if not xs:
        raise InputError("插值数据为空")
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


def _energy_at_x(points: Sequence[Dict[str, float]], target_x_mm: float) -> float:
    """Integrate a piecewise-linear F-x curve from zero to target x."""
    if target_x_mm <= 0:
        return 0.0
    energy_n_mm = 0.0
    for prev, curr in zip(points, points[1:]):
        x0 = prev["x_mm"]
        x1 = curr["x_mm"]
        if x1 <= x0 + _DUP_X_TOL:
            continue
        f0 = prev["force_n"]
        f1 = curr["force_n"]
        if target_x_mm >= x1:
            energy_n_mm += 0.5 * (f0 + f1) * (x1 - x0)
            continue
        if target_x_mm <= x0:
            break
        f_target = _interp_linear([x0, x1], [f0, f1], target_x_mm)
        energy_n_mm += 0.5 * (f0 + f_target) * (target_x_mm - x0)
        break
    return energy_n_mm * _MM_TO_M


def _invert_energy_curve(points: Sequence[Dict[str, float]], target_e_j: float) -> float:
    """Find x where the piecewise-linear loading energy equals target_e_j."""
    if target_e_j <= 0:
        return points[0]["x_mm"]
    cumulative = 0.0
    for prev, curr in zip(points, points[1:]):
        x0 = prev["x_mm"]
        x1 = curr["x_mm"]
        if x1 <= x0 + _DUP_X_TOL:
            continue
        seg_j = 0.5 * (prev["force_n"] + curr["force_n"]) * (x1 - x0) * _MM_TO_M
        if cumulative + seg_j >= target_e_j - 1e-12:
            lo = x0
            hi = x1
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                e_mid = cumulative + (
                    0.5
                    * (prev["force_n"] + _interp_linear([x0, x1], [prev["force_n"], curr["force_n"]], mid))
                    * (mid - x0)
                    * _MM_TO_M
                )
                if e_mid < target_e_j:
                    lo = mid
                else:
                    hi = mid
            return 0.5 * (lo + hi)
        cumulative += seg_j
    return points[-1]["x_mm"]


def _solve_impact(
    *,
    loading: Sequence[Dict[str, float]],
    mass_kg: float,
    initial_velocity_m_s: float,
    available_stroke_mm: float,
    allowable_peak_force_n: float,
) -> Dict[str, Any]:
    e0 = 0.5 * mass_kg * initial_velocity_m_s**2
    max_test_stroke = loading[-1]["x_mm"]
    effective_stroke = min(available_stroke_mm, max_test_stroke)
    available_capacity = _energy_at_x(loading, effective_stroke)
    loading_xs = [point["x_mm"] for point in loading]
    loading_forces = [point["force_n"] for point in loading]

    if e0 <= available_capacity + 1e-12:
        x_max = _invert_energy_curve(loading, e0)
        peak_force = _interp_linear(loading_xs, loading_forces, x_max)
        bottom_out = False
        peak_value: Optional[float] = peak_force
        peak_status = "exceeds_limit" if peak_force > allowable_peak_force_n else "ok"
        absorbed = e0
    else:
        x_max = effective_stroke
        bottom_out = True
        peak_value = None
        peak_status = "bottom_out_unknown"
        absorbed = available_capacity

    average_force = absorbed * 1000.0 / x_max if x_max > 0 else 0.0
    return {
        "initial_energy_j": e0,
        "available_energy_capacity_j": available_capacity,
        "effective_stroke_mm": effective_stroke,
        "max_compression_mm": x_max,
        "peak_force_n": peak_value,
        "peak_force_status": peak_status,
        "average_force_n": average_force,
        "absorbed_energy_j": absorbed,
        "bottom_out": bottom_out,
    }


def _truncate_to_xmax(
    points: Sequence[Dict[str, float]],
    x_max_mm: float,
) -> List[Dict[str, float]]:
    if x_max_mm <= 0:
        return [{"x_mm": 0.0, "force_n": 0.0}]
    xs = [point["x_mm"] for point in points]
    forces = [point["force_n"] for point in points]
    truncated: List[Dict[str, float]] = []
    for point in points:
        if point["x_mm"] < x_max_mm - _DUP_X_TOL:
            truncated.append({"x_mm": point["x_mm"], "force_n": point["force_n"]})
        else:
            break
    truncated.append({"x_mm": x_max_mm, "force_n": _interp_linear(xs, forces, x_max_mm)})
    return truncated


def _estimate_rebound(
    unloading: Sequence[Dict[str, float]],
    *,
    x_max_mm: float,
    mass_kg: float,
) -> Dict[str, float]:
    truncated = _truncate_to_xmax(unloading, x_max_mm)
    rebound_energy = _trapezoid_area(truncated)
    rebound_velocity = math.sqrt(2.0 * rebound_energy / mass_kg) if mass_kg > 0 else 0.0
    return {
        "rebound_energy_j": rebound_energy,
        "estimated_rebound_velocity_m_s": rebound_velocity,
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
        "peak_force_ok": (
            impact["peak_force_n"] is not None
            and impact["peak_force_n"] <= allowable_peak_force_n
        ),
        "energy_capacity_ok": True,
    }


def _validate_unloading_against_loading(
    loading: Sequence[Dict[str, float]],
    unloading: Sequence[Dict[str, float]],
    noise_tolerance_n: float,
) -> List[str]:
    warnings: List[str] = []
    loading_xs = [point["x_mm"] for point in loading]
    loading_forces = [point["force_n"] for point in loading]
    soft_limit = max(0.0, noise_tolerance_n)
    hard_limit = soft_limit * 5.0
    soft_excursions = 0
    max_delta = 0.0
    for point in unloading:
        loading_force = _interp_linear(loading_xs, loading_forces, point["x_mm"])
        delta = point["force_n"] - loading_force
        if delta > max_delta:
            max_delta = delta
        if delta > hard_limit:
            raise InputError(
                f"卸载力在 x={point['x_mm']:.3f} mm 处比加载力高出 {delta:.2f} N，"
                f"超过硬阈值 {hard_limit:.2f} N，违反耗散假设"
            )
        if delta > soft_limit:
            soft_excursions += 1
    if soft_excursions:
        warnings.append(
            f"卸载曲线在 {soft_excursions} 个点处局部高于加载曲线，"
            f"最大超出 {max_delta:.2f} N；未超过硬阈值，按噪声处理"
        )

    loading_energy = _trapezoid_area(loading)
    unloading_energy = _trapezoid_area(unloading)
    if loading_energy > 0 and unloading_energy > loading_energy * 1.10:
        raise InputError(
            f"卸载曲线总面积 {unloading_energy:.3f} J 超过加载曲线 "
            f"{loading_energy:.3f} J 的 10%，违反耗散假设"
        )
    if loading_energy > 0 and unloading_energy > loading_energy:
        warnings.append("卸载曲线总面积略大于加载面积，滞回耗能按 0 处理")
    return warnings


def _build_assumptions() -> List[str]:
    return [
        "本工具基于加载/卸载 F-x 曲线的单次冲击能量法。",
        "未使用时间域数据，不能唯一识别真实粘性阻尼系数 c。",
        "回弹速度为基于卸载曲线能量的估算值。",
        "若输入动能超过曲线容量，peak_force_n 标记为不可判定；触底后真实冲击峰值显著高于曲线末端力。",
        "时域响应曲线为由能量守恒反推的近似映射，不含应变率效应，不能替代真实时域动力学仿真。",
        "假设水平冲击或重力做功相对动能可忽略；垂直跌落工况需把 m*g*x_max 加入 E0。",
        "卸载段简化假设：测试卸载曲线形状只与位移有关；当工况最大压缩小于测试最大压缩时，仍按测试卸载曲线在 [0, x_max] 段积分。",
    ]


def calculate_buffer_energy(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate a single-impact buffer energy simulation from F-x curves."""
    if not isinstance(data, dict):
        raise InputError("输入必须是 dict")
    curve = _require(data, "curve", "data")
    impact_in = _require(data, "impact", "data")
    options = data.get("options", {}) or {}
    if not isinstance(options, dict):
        raise InputError("options 必须是字典")

    force_scale = _positive(float(options.get("force_scale", 1.0)), "力倍率")
    stroke_scale = _positive(float(options.get("stroke_scale", 1.0)), "行程倍率")
    noise_tolerance = _positive(
        float(options.get("noise_tolerance_n", 5.0)), "噪声容差", allow_zero=True
    )
    time_samples = int(options.get("time_samples", 200))
    if time_samples < 8:
        raise InputError("time_samples 必须 >= 8")

    loading_raw = _require(curve, "loading", "curve")
    unloading_raw = _require(curve, "unloading", "curve")
    loading, loading_warnings = _normalize_curve(
        loading_raw, "加载", force_scale=force_scale, stroke_scale=stroke_scale
    )
    unloading, unloading_warnings = _normalize_curve(
        unloading_raw, "卸载", force_scale=force_scale, stroke_scale=stroke_scale
    )
    if loading[-1]["x_mm"] <= 0:
        raise InputError("加载曲线最大行程必须 > 0")
    if _trapezoid_area(loading) <= 0:
        raise InputError("加载曲线总能量为 0")

    warnings: List[str] = list(loading_warnings) + list(unloading_warnings)
    if unloading[-1]["x_mm"] < loading[-1]["x_mm"] - _DUP_X_TOL:
        unloading.append({"x_mm": loading[-1]["x_mm"], "force_n": loading[-1]["force_n"]})
        warnings.append("卸载曲线最大位移小于加载曲线，已补充加载顶点作为卸载起点")
    warnings.extend(_validate_unloading_against_loading(loading, unloading, noise_tolerance))

    mass_kg = _positive(float(_require(impact_in, "mass_kg", "impact")), "质量")
    initial_velocity = _positive(
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
        initial_velocity_m_s=initial_velocity,
        available_stroke_mm=available_stroke,
        allowable_peak_force_n=allowable_peak,
    )
    rebound = _estimate_rebound(
        unloading, x_max_mm=impact["max_compression_mm"], mass_kg=mass_kg
    )
    impact["rebound_energy_j"] = rebound["rebound_energy_j"]
    impact["impact_dissipated_energy_j"] = max(
        0.0, impact["absorbed_energy_j"] - rebound["rebound_energy_j"]
    )
    impact["estimated_rebound_velocity_m_s"] = rebound["estimated_rebound_velocity_m_s"]
    if impact["bottom_out"]:
        warnings.append(
            "输入动能超过可用行程内吸能容量；触底后真实峰值力未知，"
            "回弹能量仅供参考，触底后时域响应未建模。"
        )

    checks = _build_checks(
        impact, available_stroke_mm=available_stroke, allowable_peak_force_n=allowable_peak
    )
    overall_pass = bool(
        checks["stroke_ok"] and checks["energy_capacity_ok"] and checks["peak_force_ok"] is True
    )
    energy_xs, energy_js = _accumulate_loading_energy(loading)

    base: Dict[str, Any] = {
        "inputs_echo": {
            "impact": {
                "mass_kg": mass_kg,
                "initial_velocity_m_s": initial_velocity,
                "available_stroke_mm": available_stroke,
                "allowable_peak_force_n": allowable_peak,
            },
            "options": {
                "force_scale": force_scale,
                "stroke_scale": stroke_scale,
                "noise_tolerance_n": noise_tolerance,
                "time_samples": time_samples,
            },
        },
        "curve_summary": summary,
        "impact": impact,
        "checks": checks,
        "overall_pass": overall_pass,
        "curves": {
            "loading_x_mm": [point["x_mm"] for point in loading],
            "loading_force_n": [point["force_n"] for point in loading],
            "unloading_x_mm": [point["x_mm"] for point in unloading],
            "unloading_force_n": [point["force_n"] for point in unloading],
            "loading_energy_x_mm": energy_xs,
            "loading_energy_j": energy_js,
        },
        "_normalized": {"loading": loading, "unloading": unloading},
        "warnings": warnings,
        "assumptions": _build_assumptions(),
    }

    from core.buffer.time_response import compute_time_response

    time_response = compute_time_response(base)
    if time_response is None:
        base["time_response"] = None
        base["warnings"].append("时域响应反推失败（数值不收敛或输入退化），仅返回能量法结果")
    else:
        base["time_response"] = time_response
    base.pop("_normalized", None)
    return base
