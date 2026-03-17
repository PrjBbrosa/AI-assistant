"""Cylindrical interference-fit calculator (shaft-hub connection)."""

from __future__ import annotations

import math
from typing import Any, Dict


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


def _in_open_interval(value: float, lo: float, hi: float, name: str) -> float:
    if not (lo < value < hi):
        raise InputError(f"{name} 必须满足 {lo} < 值 < {hi}，当前值 {value}")
    return value


def _in_closed_interval(value: float, lo: float, hi: float, name: str) -> float:
    if not (lo <= value <= hi):
        raise InputError(f"{name} 必须满足 {lo} <= 值 <= {hi}，当前值 {value}")
    return value


def calculate_interference_fit(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate core checks for cylindrical press/shrink fits."""
    from .assembly import calculate_assembly_detail

    geometry = data.get("geometry", {})
    materials = data.get("materials", {})
    fit = data.get("fit", {})
    roughness = data.get("roughness", {})
    friction = data.get("friction", {})
    loads = data.get("loads", {})
    checks = data.get("checks", {})
    options = data.get("options", {})
    advanced = data.get("advanced", {})

    d = _positive(float(_require(geometry, "shaft_d_mm", "geometry")), "geometry.shaft_d_mm")
    d_outer = _positive(
        float(_require(geometry, "hub_outer_d_mm", "geometry")),
        "geometry.hub_outer_d_mm",
    )
    l_fit = _positive(float(_require(geometry, "fit_length_mm", "geometry")), "geometry.fit_length_mm")
    if d_outer <= d:
        raise InputError("geometry.hub_outer_d_mm 必须大于 geometry.shaft_d_mm")

    e_shaft = _positive(float(_require(materials, "shaft_e_mpa", "materials")), "materials.shaft_e_mpa")
    nu_shaft = _in_open_interval(
        float(_require(materials, "shaft_nu", "materials")),
        0.0,
        0.5,
        "materials.shaft_nu",
    )
    yield_shaft = _positive(
        float(_require(materials, "shaft_yield_mpa", "materials")),
        "materials.shaft_yield_mpa",
    )

    e_hub = _positive(float(_require(materials, "hub_e_mpa", "materials")), "materials.hub_e_mpa")
    nu_hub = _in_open_interval(
        float(_require(materials, "hub_nu", "materials")),
        0.0,
        0.5,
        "materials.hub_nu",
    )
    yield_hub = _positive(float(_require(materials, "hub_yield_mpa", "materials")), "materials.hub_yield_mpa")

    delta_min_um = _positive(float(_require(fit, "delta_min_um", "fit")), "fit.delta_min_um", allow_zero=True)
    delta_max_um = _positive(float(_require(fit, "delta_max_um", "fit")), "fit.delta_max_um")
    if delta_max_um < delta_min_um:
        raise InputError("fit.delta_max_um 必须 >= fit.delta_min_um")

    rz_shaft_um = _positive(
        float(roughness.get("shaft_rz_um", 0.0)),
        "roughness.shaft_rz_um",
        allow_zero=True,
    )
    rz_hub_um = _positive(
        float(roughness.get("hub_rz_um", 0.0)),
        "roughness.hub_rz_um",
        allow_zero=True,
    )
    smoothing_factor = _positive(
        float(roughness.get("smoothing_factor", 0.4)),
        "roughness.smoothing_factor",
        allow_zero=True,
    )
    if smoothing_factor > 1.0:
        raise InputError("roughness.smoothing_factor 建议不超过 1.0")
    subsidence_um = smoothing_factor * (rz_shaft_um + rz_hub_um)
    delta_eff_min_um = max(0.0, delta_min_um - subsidence_um)
    delta_eff_max_um = max(0.0, delta_max_um - subsidence_um)
    if delta_eff_max_um <= 0:
        raise InputError("粗糙度压平后有效过盈量 <= 0，请增大过盈量或降低 Rz。")

    delta_mean_um = 0.5 * (delta_min_um + delta_max_um)
    delta_eff_mean_um = max(0.0, delta_mean_um - subsidence_um)

    legacy_mu_static = friction.get("mu_static")
    mu_torque_source = friction.get("mu_torque", legacy_mu_static)
    if mu_torque_source is None:
        raise InputError("缺少必填字段: friction.mu_torque")
    mu_axial_source = friction.get("mu_axial", legacy_mu_static)
    if mu_axial_source is None:
        raise InputError("缺少必填字段: friction.mu_axial")

    mu_torque = _in_open_interval(
        float(mu_torque_source),
        0.0,
        1.0,
        "friction.mu_torque",
    )
    mu_axial = _in_open_interval(
        float(mu_axial_source),
        0.0,
        1.0,
        "friction.mu_axial",
    )
    mu_assembly = _in_open_interval(
        float(_require(friction, "mu_assembly", "friction")),
        0.0,
        1.0,
        "friction.mu_assembly",
    )

    torque_required_nm = _positive(
        float(loads.get("torque_required_nm", 0.0)),
        "loads.torque_required_nm",
        allow_zero=True,
    )
    axial_required_n = _positive(
        float(loads.get("axial_force_required_n", 0.0)),
        "loads.axial_force_required_n",
        allow_zero=True,
    )
    radial_required_n = _positive(
        float(loads.get("radial_force_required_n", 0.0)),
        "loads.radial_force_required_n",
        allow_zero=True,
    )
    bending_required_nm = _positive(
        float(loads.get("bending_moment_required_nm", 0.0)),
        "loads.bending_moment_required_nm",
        allow_zero=True,
    )
    application_factor = _positive(
        float(loads.get("application_factor_ka", 1.0)),
        "loads.application_factor_ka",
    )

    torque_design_nm = application_factor * torque_required_nm
    axial_design_n = application_factor * axial_required_n
    radial_design_n = application_factor * radial_required_n
    bending_design_nm = application_factor * bending_required_nm

    slip_safety_min = _positive(float(checks.get("slip_safety_min", 1.2)), "checks.slip_safety_min")
    stress_safety_min = _positive(float(checks.get("stress_safety_min", 1.2)), "checks.stress_safety_min")
    curve_points = int(options.get("curve_points", 41))
    curve_points = int(_in_closed_interval(float(curve_points), 11, 201, "options.curve_points"))
    repeated_load_mode = str(advanced.get("repeated_load_mode", "off")).strip() or "off"
    if repeated_load_mode not in {"off", "on"}:
        raise InputError("advanced.repeated_load_mode 必须是 off 或 on")

    radius = d / 2.0
    geometry_factor = (d_outer * d_outer + d * d) / (d_outer * d_outer - d * d)
    c_shaft = radius / e_shaft * (1.0 - nu_shaft * nu_shaft)
    c_hub = radius / e_hub * (geometry_factor + nu_hub)
    c_total = c_shaft + c_hub
    if c_total <= 0:
        raise InputError("干涉变形柔度计算异常（<=0），请检查材料与几何参数。")

    def pressure_from_effective_interference(delta_eff_um: float) -> float:
        delta_mm = delta_eff_um / 1000.0
        delta_r_mm = delta_mm / 2.0
        return delta_r_mm / c_total

    def pressure_from_input_interference(delta_input_um: float) -> float:
        delta_eff_um = max(0.0, delta_input_um - subsidence_um)
        return pressure_from_effective_interference(delta_eff_um)

    p_min = pressure_from_effective_interference(delta_eff_min_um)
    p_max = pressure_from_effective_interference(delta_eff_max_um)

    contact_area_mm2 = math.pi * d * l_fit

    def torque_capacity_nm(pressure_mpa: float) -> float:
        return mu_torque * pressure_mpa * contact_area_mm2 * radius / 1000.0

    def axial_capacity_n(pressure_mpa: float) -> float:
        return mu_axial * pressure_mpa * contact_area_mm2

    def press_force_n(pressure_mpa: float) -> float:
        return mu_assembly * pressure_mpa * contact_area_mm2

    hub_vm_coeff = math.sqrt(1.0 + geometry_factor + geometry_factor * geometry_factor)

    def build_state(delta_input_um: float) -> Dict[str, float]:
        delta_eff_um = max(0.0, delta_input_um - subsidence_um)
        pressure_mpa = pressure_from_effective_interference(delta_eff_um)
        torque_cap_nm = torque_capacity_nm(pressure_mpa)
        axial_cap_n = axial_capacity_n(pressure_mpa)
        press_force_val_n = press_force_n(pressure_mpa)
        shaft_vm_mpa = pressure_mpa
        hub_vm_mpa = pressure_mpa * hub_vm_coeff
        hub_hoop_inner_mpa = pressure_mpa * geometry_factor
        shaft_sf = math.inf if shaft_vm_mpa == 0 else yield_shaft / shaft_vm_mpa
        hub_sf = math.inf if hub_vm_mpa == 0 else yield_hub / hub_vm_mpa
        return {
            "delta_input_um": delta_input_um,
            "delta_effective_um": delta_eff_um,
            "pressure_mpa": pressure_mpa,
            "torque_cap_nm": torque_cap_nm,
            "axial_cap_n": axial_cap_n,
            "press_force_n": press_force_val_n,
            "shaft_vm_mpa": shaft_vm_mpa,
            "hub_vm_mpa": hub_vm_mpa,
            "hub_hoop_inner_mpa": hub_hoop_inner_mpa,
            "shaft_sf": shaft_sf,
            "hub_sf": hub_sf,
        }

    states = {
        "min": build_state(delta_min_um),
        "mean": build_state(delta_mean_um),
        "max": build_state(delta_max_um),
    }
    min_state = states["min"]
    mean_state = states["mean"]
    max_state = states["max"]

    p_min = min_state["pressure_mpa"]
    p_mean = mean_state["pressure_mpa"]
    p_max = max_state["pressure_mpa"]

    torque_min_nm = min_state["torque_cap_nm"]
    torque_mean_nm = mean_state["torque_cap_nm"]
    torque_max_nm = max_state["torque_cap_nm"]
    axial_min_n = min_state["axial_cap_n"]
    axial_mean_n = mean_state["axial_cap_n"]
    axial_max_n = max_state["axial_cap_n"]
    press_force_min_n = min_state["press_force_n"]
    press_force_mean_n = mean_state["press_force_n"]
    press_force_max_n = max_state["press_force_n"]

    shaft_vm_min = min_state["shaft_vm_mpa"]
    shaft_vm_mean = mean_state["shaft_vm_mpa"]
    shaft_vm_max = max_state["shaft_vm_mpa"]
    hub_vm_min = min_state["hub_vm_mpa"]
    hub_vm_mean = mean_state["hub_vm_mpa"]
    hub_vm_max = max_state["hub_vm_mpa"]
    hub_hoop_inner_min = min_state["hub_hoop_inner_mpa"]
    hub_hoop_inner_mean = mean_state["hub_hoop_inner_mpa"]
    hub_hoop_inner_max = max_state["hub_hoop_inner_mpa"]

    torque_capacity_per_mpa_nm = torque_capacity_nm(1.0)
    axial_capacity_per_mpa_n = axial_capacity_n(1.0)

    p_req_torque_service = 0.0
    if torque_design_nm > 0:
        p_req_torque_service = torque_design_nm / torque_capacity_per_mpa_nm
    p_req_axial_service = 0.0
    if axial_design_n > 0:
        p_req_axial_service = axial_design_n / axial_capacity_per_mpa_n
    p_req_torque = slip_safety_min * p_req_torque_service
    p_req_axial = slip_safety_min * p_req_axial_service
    p_req_combined = slip_safety_min * math.hypot(p_req_torque_service, p_req_axial_service)
    p_radial = radial_design_n / (d * l_fit) if radial_design_n > 0 else 0.0
    # Conservative simplification of the handbook expression by taking QW = 0.
    p_bending = 2.25 * bending_design_nm * 1000.0 / (d * l_fit * l_fit) if bending_design_nm > 0 else 0.0
    p_gap = p_radial + p_bending
    p_required = max(p_req_torque, p_req_axial, p_req_combined, p_gap)
    if p_required > 0:
        delta_required_eff_um = 2.0 * c_total * p_required * 1000.0
        delta_required_um = delta_required_eff_um + subsidence_um
    else:
        delta_required_eff_um = 0.0
        delta_required_um = 0.0

    shaft_sf_min = max_state["shaft_sf"]
    hub_sf_min = max_state["hub_sf"]
    shaft_ok = shaft_sf_min >= stress_safety_min
    hub_ok = hub_sf_min >= stress_safety_min

    torque_sf = math.inf if torque_design_nm == 0 else torque_min_nm / torque_design_nm
    axial_sf = math.inf if axial_design_n == 0 else axial_min_n / axial_design_n
    torque_ok = torque_sf >= slip_safety_min
    axial_ok = axial_sf >= slip_safety_min
    gaping_ok = p_min >= p_gap
    pressure_ok = p_min >= p_required
    fit_range_ok = delta_max_um >= delta_required_um

    combined_usage = 0.0
    if p_min > 0:
        combined_usage = math.hypot(p_req_torque_service, p_req_axial_service) / p_min
    combined_ok = combined_usage <= (1.0 / slip_safety_min if combined_usage > 0 else 1.0)
    combined_sf = math.inf if combined_usage == 0 else 1.0 / combined_usage

    assembly_detail = calculate_assembly_detail(
        data.get("assembly", {}),
        {
            "shaft_d_mm": d,
            "fit_length_mm": l_fit,
            "delta_min_um": delta_min_um,
            "delta_mean_um": delta_mean_um,
            "delta_max_um": delta_max_um,
            "p_min_mpa": p_min,
            "p_mean_mpa": p_mean,
            "p_max_mpa": p_max,
            "contact_area_mm2": contact_area_mm2,
            "mu_assembly": mu_assembly,
            "mu_torque": mu_torque,
            "mu_axial": mu_axial,
        },
    )

    repeated_notes: list[str] = []
    repeated_enabled = repeated_load_mode == "on"
    repeated_applicable = False
    repeated_max_torque_nm: float | None = None
    fretting_risk: bool | None = None
    length_ratio = l_fit / d
    modulus_ratio = abs(e_shaft - e_hub) / max(e_shaft, e_hub)
    if repeated_enabled:
        if length_ratio <= 0.25:
            repeated_notes.append("not applicable: LF/DF must be greater than 0.25.")
        elif modulus_ratio > 0.05:
            repeated_notes.append("not applicable: repeated-load estimate assumes equal elastic modulus.")
        elif bending_design_nm > 0.0:
            repeated_notes.append("not applicable: rotating bending is excluded from the simplified estimate.")
        else:
            repeated_applicable = True
            repeated_max_torque_nm = torque_min_nm * l_fit / (4.0 * d)
            fretting_risk = torque_design_nm > repeated_max_torque_nm
            repeated_notes.append(
                "Applicable: simplified DIN 7190/Niemann estimate for solid shaft, disk-shaped hub, QA=0."
            )
    else:
        repeated_notes.append("disabled")

    warnings: list[str] = []
    if not gaping_ok:
        warnings.append(
            f"最小接触压力 p_min={p_min:.2f} MPa 小于附加载荷要求 p_gap={p_gap:.2f} MPa，存在张口缝风险。"
        )
    if not combined_ok:
        warnings.append("扭矩与轴向力联合作用超出当前最小过盈能力，需同时提高接触压力储备。")
    if fit_range_ok and delta_max_um - delta_required_um < 2.0:
        warnings.append("最大过盈量接近需求下限，建议增加加工裕量。")
    if subsidence_um > 0 and delta_min_um > 0:
        warnings.append(
            f"粗糙度压平量 s={subsidence_um:.2f} um，已按有效过盈量参与计算。"
        )
    if hub_sf_min < shaft_sf_min:
        warnings.append("轮毂为薄弱侧，建议优先提高轮毂屈服强度或增大外径。")
    if press_force_max_n > 250_000:
        warnings.append("压入力较高，建议评估热装或液压装配工艺。")
    warnings.extend(str(msg) for msg in assembly_detail.get("warnings", []))
    if repeated_enabled and not repeated_applicable:
        warnings.append("Repeated-load / fretting estimate is enabled but not applicable for the current assumptions.")
    if fretting_risk:
        warnings.append("Repeated-load estimate indicates fretting risk; increase slip reserve or reduce cyclic torque.")

    curve_max_um = max(delta_max_um * 1.25, delta_required_um * 1.15, 1.0)
    if curve_max_um <= 0:
        curve_max_um = 1.0
    curve_x: list[float] = []
    curve_y: list[float] = []
    for idx in range(curve_points):
        delta_um = curve_max_um * idx / (curve_points - 1)
        pressure = pressure_from_input_interference(delta_um)
        curve_x.append(delta_um)
        curve_y.append(press_force_n(pressure))

    checks_out = {
        "torque_ok": torque_ok,
        "axial_ok": axial_ok,
        "gaping_ok": gaping_ok,
        "pressure_ok": pressure_ok,
        "fit_range_ok": fit_range_ok,
        "combined_ok": combined_ok,
        "shaft_stress_ok": shaft_ok,
        "hub_stress_ok": hub_ok,
    }
    overall_pass = all(
        checks_out[key]
        for key in (
            "torque_ok",
            "axial_ok",
            "combined_ok",
            "gaping_ok",
            "fit_range_ok",
            "shaft_stress_ok",
            "hub_stress_ok",
        )
    )

    return {
        "inputs_echo": data,
        "model": {
            "type": "cylindrical_interference_solid_shaft",
            "assumption": "线弹性、均匀接触压力、常摩擦系数、QW=0 保守简化",
        },
        "derived": {
            "geometry_factor": geometry_factor,
            "contact_area_mm2": contact_area_mm2,
            "radial_compliance_shaft_mm_per_mpa": c_shaft,
            "radial_compliance_hub_mm_per_mpa": c_hub,
            "radial_compliance_total_mm_per_mpa": c_total,
        },
        "pressure_mpa": {
            "p_min": p_min,
            "p_mean": p_mean,
            "p_max": p_max,
            "p_required": p_required,
            "p_required_total": p_required,
        },
        "additional_pressure_mpa": {
            "p_radial": p_radial,
            "p_bending": p_bending,
            "p_gap": p_gap,
        },
        "capacity": {
            "torque_min_nm": torque_min_nm,
            "torque_mean_nm": torque_mean_nm,
            "torque_max_nm": torque_max_nm,
            "axial_min_n": axial_min_n,
            "axial_mean_n": axial_mean_n,
            "axial_max_n": axial_max_n,
        },
        "assembly": {
            "press_force_min_n": press_force_min_n,
            "press_force_mean_n": press_force_mean_n,
            "press_force_max_n": press_force_max_n,
        },
        "assembly_detail": assembly_detail,
        "stress_mpa": {
            "shaft_vm_min": shaft_vm_min,
            "shaft_vm_mean": shaft_vm_mean,
            "shaft_vm_max": shaft_vm_max,
            "hub_vm_min": hub_vm_min,
            "hub_vm_mean": hub_vm_mean,
            "hub_vm_max": hub_vm_max,
            "hub_hoop_inner_min": hub_hoop_inner_min,
            "hub_hoop_inner_mean": hub_hoop_inner_mean,
            "hub_hoop_inner_max": hub_hoop_inner_max,
        },
        "safety": {
            "torque_sf": torque_sf,
            "axial_sf": axial_sf,
            "combined_sf": combined_sf,
            "shaft_sf": shaft_sf_min,
            "hub_sf": hub_sf_min,
            "combined_usage": combined_usage,
            "slip_safety_min": slip_safety_min,
            "stress_safety_min": stress_safety_min,
            "application_factor_ka": application_factor,
            "gaping_margin_mpa": p_min - p_gap,
        },
        "required": {
            "p_service_torque_mpa": p_req_torque_service,
            "p_service_axial_mpa": p_req_axial_service,
            "p_required_torque_mpa": p_req_torque,
            "p_required_axial_mpa": p_req_axial,
            "p_required_combined_mpa": p_req_combined,
            "p_required_gap_mpa": p_gap,
            "p_required_mpa": p_required,
            "p_required_total_mpa": p_required,
            "delta_required_effective_um": delta_required_eff_um,
            "delta_required_um": delta_required_um,
        },
        "roughness": {
            "shaft_rz_um": rz_shaft_um,
            "hub_rz_um": rz_hub_um,
            "smoothing_factor": smoothing_factor,
            "subsidence_um": subsidence_um,
            "delta_input_min_um": delta_min_um,
            "delta_input_mean_um": delta_mean_um,
            "delta_input_max_um": delta_max_um,
            "delta_effective_min_um": delta_eff_min_um,
            "delta_effective_mean_um": delta_eff_mean_um,
            "delta_effective_max_um": delta_eff_max_um,
        },
        "press_force_curve": {
            "interference_um": curve_x,
            "force_n": curve_y,
            "delta_required_um": delta_required_um,
            "delta_required_effective_um": delta_required_eff_um,
            "delta_min_um": delta_min_um,
            "delta_max_um": delta_max_um,
        },
        "repeated_load": {
            "enabled": repeated_enabled,
            "applicable": repeated_applicable,
            "max_transferable_torque_nm": repeated_max_torque_nm,
            "fretting_risk": fretting_risk,
            "length_ratio_l_over_d": length_ratio,
            "modulus_ratio": modulus_ratio,
            "notes": repeated_notes,
        },
        "checks": checks_out,
        "overall_pass": overall_pass,
        "messages": warnings,
    }
