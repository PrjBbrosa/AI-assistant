"""Spline interference-fit calculator: tooth-flank (A) + smooth-bore (B)."""

from __future__ import annotations

import math
from typing import Any, Dict

from .geometry import GeometryError, derive_involute_geometry


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


def _positive_int(value: Any, name: str) -> int:
    numeric = float(value)
    if not numeric.is_integer():
        raise InputError(f"{name} 必须为整数，当前值 {value}")
    integer = int(numeric)
    if integer <= 0:
        raise InputError(f"{name} 必须 > 0，当前值 {value}")
    return integer


def _calculate_scenario_a(
    spline: Dict[str, Any],
    torque_design_nm: float,
    flank_safety_min: float,
) -> Dict[str, Any]:
    """Scenario A: involute spline tooth flank bearing stress check."""
    m = _positive(float(_require(spline, "module_mm", "spline")), "spline.module_mm")
    z = _positive_int(_require(spline, "tooth_count", "spline"), "spline.tooth_count")
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
    geometry_mode = str(spline.get("geometry_mode", "approximate")).strip() or "approximate"
    if geometry_mode not in {"approximate", "reference_dimensions"}:
        raise InputError("spline.geometry_mode 必须是 approximate 或 reference_dimensions")

    def _optional_float(key: str) -> float | None:
        value = spline.get(key)
        if value in (None, ""):
            return None
        return float(value)

    try:
        geo = derive_involute_geometry(
            module_mm=m,
            tooth_count=z,
            reference_diameter_mm=_optional_float("reference_diameter_mm"),
            tip_diameter_shaft_mm=_optional_float("tip_diameter_shaft_mm"),
            root_diameter_shaft_mm=_optional_float("root_diameter_shaft_mm"),
            tip_diameter_hub_mm=_optional_float("tip_diameter_hub_mm"),
            allow_approximation=(geometry_mode == "approximate"),
        )
    except GeometryError as exc:
        raise InputError(str(exc)) from exc
    h_w = geo["effective_tooth_height_mm"]
    d_m = geo["mean_diameter_mm"]

    T_design_nmm = torque_design_nm * 1000.0

    p_flank = (2.0 * T_design_nmm * k_alpha) / (z * h_w * d_m * L)

    T_cap_nmm = p_zul * z * h_w * d_m * L / (2.0 * k_alpha)
    T_cap_nm = T_cap_nmm / 1000.0

    flank_sf = p_zul / p_flank if p_flank > 0 else math.inf
    flank_ok = flank_sf >= flank_safety_min
    messages = list(geo.get("messages", []))
    not_covered_checks = [
        "齿根弯曲强度",
        "剪切承载",
        "内花键胀裂/轮毂局部强度",
        "磨损与寿命",
        "完整公差/变位/齿侧间隙链",
    ]

    return {
        "geometry": geo,
        "geometry_mode": geometry_mode,
        "engagement_length_mm": L,
        "k_alpha": k_alpha,
        "p_allowable_mpa": p_zul,
        "flank_pressure_mpa": p_flank,
        "torque_capacity_nm": T_cap_nm,
        "torque_design_nm": torque_design_nm,
        "flank_safety": flank_sf,
        "flank_safety_min": flank_safety_min,
        "flank_ok": flank_ok,
        "messages": messages,
        "model_assumptions": [
            "齿面平均承压简化模型",
            "仅作为 simplified_precheck，不替代 DIN 5466 / DIN 6892 完整校核",
        ],
        "not_covered_checks": not_covered_checks,
        "overall_verdict_level": "simplified_precheck",
    }


def _calculate_scenario_b(
    smooth_fit: Dict[str, Any],
    smooth_materials: Dict[str, Any],
    smooth_roughness: Dict[str, Any],
    smooth_friction: Dict[str, Any],
    torque_design_nm: float,
    axial_design_n: float,
    application_factor_ka: float,
    slip_safety_min: float,
    stress_safety_min: float,
) -> Dict[str, Any]:
    """Scenario B: smooth-section cylindrical press fit (reuse DIN 7190 Lame)."""
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

    delegate_data = {
        "geometry": {
            "shaft_d_mm": float(smooth_fit.get("shaft_d_mm", 0)),
            "shaft_inner_d_mm": float(smooth_fit.get("shaft_inner_d_mm", 0)),
            "hub_outer_d_mm": float(smooth_fit.get("hub_outer_d_mm", 0)),
            "fit_length_mm": l_fit,
        },
        "materials": smooth_materials,
        "fit": {
            "delta_min_um": float(smooth_fit.get("delta_min_um", 0)),
            "delta_max_um": float(smooth_fit.get("delta_max_um", 0)),
        },
        "roughness": smooth_roughness,
        "friction": smooth_friction,
        "loads": {
            "torque_required_nm": torque_design_nm,
            "axial_force_required_n": axial_design_n,
            "application_factor_ka": 1.0,
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
        "design_loads": {
            "torque_design_nm": torque_design_nm,
            "axial_design_n": axial_design_n,
            "application_factor_ka": application_factor_ka,
            "delegated_application_factor_ka": 1.0,
        },
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
            torque_design_nm, axial_design_n, ka, slip_safety_min, stress_safety_min,
        )
        scenario_b_pass = scenario_b["overall_pass"]

    overall_pass = scenario_a["flank_ok"] and scenario_b_pass

    warnings: list[str] = []
    warnings.extend(f"场景 A: {message}" for message in scenario_a.get("messages", []))
    if not scenario_a["flank_ok"]:
        warnings.append(
            f"齿面承压安全系数 {scenario_a['flank_safety']:.2f}"
            f" < 最小要求 {flank_safety_min}，齿面承载不足。"
        )
    if scenario_b is not None:
        warnings.extend(f"场景 B: {message}" for message in scenario_b.get("messages", []))

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
        "overall_verdict_level": scenario_a["overall_verdict_level"],
        "messages": warnings,
    }
    if scenario_b is not None:
        result["scenario_b"] = scenario_b
    return result
