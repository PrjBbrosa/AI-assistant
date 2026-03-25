"""Assembly helpers for shrink-fit and force-fit workflows."""

from __future__ import annotations

import math
from typing import Any

from .calculator import InputError


def _positive(value: Any, name: str, *, allow_zero: bool = False) -> float:
    numeric = float(value)
    if allow_zero and numeric == 0.0:
        return numeric
    if numeric <= 0.0:
        raise InputError(f"{name} 必须 > 0，当前值 {numeric}")
    return numeric


def _open_interval(value: Any, lo: float, hi: float, name: str) -> float:
    numeric = float(value)
    if not (lo < numeric < hi):
        raise InputError(f"{name} 必须满足 {lo} < 值 < {hi}，当前值 {numeric}")
    return numeric


def _recommended_edge_length_mm(shaft_d_mm: float) -> float:
    table = (
        (50.0, 80.0, 4.0),
        (80.0, 160.0, 5.0),
        (160.0, 250.0, 6.0),
        (250.0, 400.0, 7.0),
        (400.0, 630.0, 8.0),
        (630.0, 800.0, 9.0),
        (800.0, math.inf, 10.0),
    )
    for lower, upper, edge_length in table:
        if shaft_d_mm > lower and shaft_d_mm <= upper:
            return edge_length
    return max(3.0, round(shaft_d_mm ** (1.0 / 3.0), 2))


def calculate_assembly_detail(
    assembly_input: dict[str, Any] | None,
    context: dict[str, float],
) -> dict[str, Any]:
    """Build mode-specific assembly detail from the calculator context."""
    assembly = assembly_input or {}

    shaft_d_mm = _positive(context["shaft_d_mm"], "context.shaft_d_mm")
    fit_length_mm = _positive(context["fit_length_mm"], "context.fit_length_mm")
    delta_min_um = _positive(context["delta_min_um"], "context.delta_min_um", allow_zero=True)
    delta_mean_um = _positive(context["delta_mean_um"], "context.delta_mean_um", allow_zero=True)
    delta_max_um = _positive(context["delta_max_um"], "context.delta_max_um")
    p_min_mpa = _positive(context["p_min_mpa"], "context.p_min_mpa", allow_zero=True)
    p_mean_mpa = _positive(context["p_mean_mpa"], "context.p_mean_mpa", allow_zero=True)
    p_max_mpa = _positive(context["p_max_mpa"], "context.p_max_mpa", allow_zero=True)
    contact_area_mm2 = _positive(context["contact_area_mm2"], "context.contact_area_mm2")
    mu_assembly = _open_interval(context["mu_assembly"], 0.0, 1.0, "context.mu_assembly")
    mu_torque = _open_interval(context["mu_torque"], 0.0, 1.0, "context.mu_torque")
    mu_axial = _open_interval(context["mu_axial"], 0.0, 1.0, "context.mu_axial")

    def generic_press_force(pressure_mpa: float) -> float:
        return mu_assembly * pressure_mpa * contact_area_mm2

    method = str(assembly.get("method", "manual_only")).strip() or "manual_only"
    if method not in {"manual_only", "shrink_fit", "force_fit"}:
        raise InputError("assembly.method 必须是 manual_only、shrink_fit 或 force_fit")

    detail: dict[str, Any] = {
        "method": method,
        "generic_press_force": {
            "press_force_min_n": generic_press_force(p_min_mpa),
            "press_force_mean_n": generic_press_force(p_mean_mpa),
            "press_force_max_n": generic_press_force(p_max_mpa),
        },
        "service_friction": {
            "mu_torque": mu_torque,
            "mu_axial": mu_axial,
        },
        "assembly_friction": {
            "mu_generic": mu_assembly,
        },
        "source_trace": {
            "method": method,
        },
        "warnings": [],
    }

    if method == "manual_only":
        detail["manual_only"] = {
            "note": "Using generic assembly friction for press-force estimates only.",
        }
        return detail

    if method == "shrink_fit":
        clearance_mode = str(assembly.get("clearance_mode", "diameter_rule")).strip() or "diameter_rule"
        if clearance_mode not in {"diameter_rule", "direct_value"}:
            raise InputError("assembly.clearance_mode 必须是 diameter_rule 或 direct_value")
        clearance_um = shaft_d_mm if clearance_mode == "diameter_rule" else _positive(
            assembly.get("clearance_um", 0.0),
            "assembly.clearance_um",
            allow_zero=True,
        )
        room_temperature_c = float(assembly.get("room_temperature_c", 20.0))
        shaft_temperature_c = float(assembly.get("shaft_temperature_c", 20.0))
        alpha_hub = _positive(
            assembly.get("alpha_hub_1e6_per_c", 11.0),
            "assembly.alpha_hub_1e6_per_c",
        )
        alpha_shaft = _positive(
            assembly.get("alpha_shaft_1e6_per_c", 11.0),
            "assembly.alpha_shaft_1e6_per_c",
        )
        # Heat-joining temperature must clear the worst-case interference side.
        required_expansion_um = delta_max_um + clearance_um
        hub_growth_um_per_c = alpha_hub * shaft_d_mm / 1000.0
        if hub_growth_um_per_c <= 0.0:
            raise InputError("无法根据热膨胀系数计算热装温度。")
        required_hub_temperature_c = (
            room_temperature_c
            + required_expansion_um / hub_growth_um_per_c
            + (alpha_shaft / alpha_hub) * (shaft_temperature_c - room_temperature_c)
        )
        hub_temp_limit_raw = assembly.get("hub_temp_limit_c")
        hub_temp_limit_c = None if hub_temp_limit_raw in (None, "") else float(hub_temp_limit_raw)
        hub_temp_limit_ok = (
            None if hub_temp_limit_c is None else required_hub_temperature_c <= hub_temp_limit_c
        )
        if hub_temp_limit_ok is False:
            detail["warnings"].append("Required hub joining temperature exceeds the configured hub limit.")

        detail["source_trace"]["clearance_mode"] = clearance_mode
        detail["shrink_fit"] = {
            "room_temperature_c": room_temperature_c,
            "shaft_temperature_c": shaft_temperature_c,
            "clearance_mode": clearance_mode,
            "clearance_um": clearance_um,
            "required_expansion_um": required_expansion_um,
            "required_hub_temperature_c": required_hub_temperature_c,
            "alpha_hub_1e6_per_c": alpha_hub,
            "alpha_shaft_1e6_per_c": alpha_shaft,
            "hub_temp_limit_c": hub_temp_limit_c,
            "hub_temp_limit_ok": hub_temp_limit_ok,
        }
        return detail

    mu_press_in = _open_interval(
        assembly.get("mu_press_in", mu_assembly),
        0.0,
        1.0,
        "assembly.mu_press_in",
    )
    mu_press_out = _open_interval(
        assembly.get("mu_press_out", mu_assembly),
        0.0,
        1.0,
        "assembly.mu_press_out",
    )
    press_in_force_n = mu_press_in * p_max_mpa * contact_area_mm2
    press_out_force_n = mu_press_out * p_max_mpa * contact_area_mm2
    detail["assembly_friction"].update(
        {
            "mu_press_in": mu_press_in,
            "mu_press_out": mu_press_out,
        }
    )
    detail["force_fit"] = {
        "press_in_force_n": press_in_force_n,
        "press_out_force_n": press_out_force_n,
        "recommended_machine_force_n": 2.5 * press_out_force_n,
        "edge_length_recommendation_mm": _recommended_edge_length_mm(shaft_d_mm),
        "bevel_angle_max_deg": 5.0,
        "first_full_load_delay_h": 24.0,
        "pressure_reference_mpa": p_max_mpa,
    }
    detail["source_trace"]["pressure_reference"] = "p_max"
    detail["warnings"].append("Force-fit estimates use p_max and separate press-in / press-out friction.")
    return detail
