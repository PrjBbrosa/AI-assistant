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
        # Scenario B -- implemented in Task 3
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
