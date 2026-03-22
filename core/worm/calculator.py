"""DIN 3975 first-pass worm geometry and basic performance calculator."""

from __future__ import annotations

import math
from typing import Any, Dict


class InputError(ValueError):
    """Raised when worm-gear input data is incomplete or invalid."""


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


def _fraction(value: float, name: str) -> float:
    if not (0.0 < value < 1.0):
        raise InputError(f"{name} 必须满足 0 < 值 < 1，当前值 {value}")
    return value


def _nu(value: float, name: str) -> float:
    if not (0.0 < value < 0.5):
        raise InputError(f"{name} 必须满足 0 < nu < 0.5，当前值 {value}")
    return value


STANDARD_Q_VALUES = {6, 7, 8, 9, 10, 11, 12, 14, 17, 20}

MATERIAL_FRICTION_HINTS = {
    ("37CrS4", "PA66"):      0.18,
    ("37CrS4", "PA66+GF30"): 0.22,
}

MATERIAL_ELASTIC_HINTS = {
    "37CrS4":     {"e_mpa": 210000.0, "nu": 0.30},
    "PA66":       {"e_mpa":   3000.0, "nu": 0.38},
    "PA66+GF30":  {"e_mpa":  10000.0, "nu": 0.36},
}

MATERIAL_ALLOWABLE_HINTS = {
    "PA66":       {"contact_mpa": 42.0, "root_mpa": 55.0},
    "PA66+GF30":  {"contact_mpa": 58.0, "root_mpa": 70.0},
}


def _estimate_friction(worm_material: str, wheel_material: str) -> float:
    return MATERIAL_FRICTION_HINTS.get((worm_material, wheel_material), 0.20)


def calculate_worm_geometry(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate DIN 3975-style geometry summary and basic performance values."""
    geometry = data.get("geometry", {})
    operating = data.get("operating", {})
    materials = data.get("materials", {})
    advanced = data.get("advanced", {})
    load_capacity = data.get("load_capacity", {})

    z1 = _positive(float(_require(geometry, "z1", "geometry")), "geometry.z1")
    z2 = _positive(float(_require(geometry, "z2", "geometry")), "geometry.z2")
    if z1 != int(z1):
        raise InputError(f"z1 必须为正整数，当前值 {z1}")
    if z2 != int(z2):
        raise InputError(f"z2 必须为正整数，当前值 {z2}")
    module_mm = _positive(float(_require(geometry, "module_mm", "geometry")), "geometry.module_mm")
    center_distance_mm = _positive(
        float(_require(geometry, "center_distance_mm", "geometry")),
        "geometry.center_distance_mm",
    )
    diameter_factor_q = _positive(
        float(_require(geometry, "diameter_factor_q", "geometry")),
        "geometry.diameter_factor_q",
    )
    lead_angle_deg = _positive(
        float(_require(geometry, "lead_angle_deg", "geometry")),
        "geometry.lead_angle_deg",
    )
    if lead_angle_deg > 45:
        raise InputError(f"导程角必须 <= 45 deg，当前值 {lead_angle_deg}")

    power_kw = _positive(float(_require(operating, "power_kw", "operating")), "operating.power_kw")
    speed_rpm = _positive(float(_require(operating, "speed_rpm", "operating")), "operating.speed_rpm")
    application_factor = _positive(
        float(operating.get("application_factor", 1.0)),
        "operating.application_factor",
    )
    torque_ripple_percent = _positive(
        float(operating.get("torque_ripple_percent", 0.0)),
        "operating.torque_ripple_percent",
        allow_zero=True,
    )

    worm_material = str(materials.get("worm_material", "钢制蜗杆")).strip() or "钢制蜗杆"
    wheel_material = str(materials.get("wheel_material", "青铜蜗轮")).strip() or "青铜蜗轮"
    worm_elastic_defaults = MATERIAL_ELASTIC_HINTS.get(worm_material, {"e_mpa": 210000.0, "nu": 0.30})
    wheel_elastic_defaults = MATERIAL_ELASTIC_HINTS.get(wheel_material, {"e_mpa": 3000.0, "nu": 0.38})
    wheel_allowable_defaults = MATERIAL_ALLOWABLE_HINTS.get(wheel_material, {"contact_mpa": 42.0, "root_mpa": 55.0})

    worm_e_mpa = _positive(float(materials.get("worm_e_mpa", worm_elastic_defaults["e_mpa"])), "materials.worm_e_mpa")
    worm_nu = _nu(float(materials.get("worm_nu", worm_elastic_defaults["nu"])), "materials.worm_nu")
    wheel_e_mpa = _positive(float(materials.get("wheel_e_mpa", wheel_elastic_defaults["e_mpa"])), "materials.wheel_e_mpa")
    wheel_nu = _nu(float(materials.get("wheel_nu", wheel_elastic_defaults["nu"])), "materials.wheel_nu")

    x1 = float(geometry.get("x1", 0.0))
    x2 = float(geometry.get("x2", 0.0))

    ratio = z2 / z1
    lead_angle_rad = math.radians(lead_angle_deg)  # user input, for comparison only
    lead_angle_calc_rad = math.atan(z1 / diameter_factor_q)  # self-consistent value
    lead_angle_calc_deg = math.degrees(lead_angle_calc_rad)
    lead_angle_delta_deg = lead_angle_deg - lead_angle_calc_deg
    pitch_diameter_worm_mm = diameter_factor_q * module_mm
    pitch_diameter_wheel_mm = z2 * module_mm
    theoretical_center_distance_mm = module_mm * (diameter_factor_q + z2) / 2.0 + (x1 + x2) * module_mm
    center_distance_delta_mm = center_distance_mm - theoretical_center_distance_mm
    worm_tip_diameter_mm = pitch_diameter_worm_mm + 2.0 * module_mm * (1.0 + x1)
    worm_root_diameter_mm = max(1e-6, pitch_diameter_worm_mm - 2.0 * module_mm * (1.2 - x1))
    wheel_tip_diameter_mm = pitch_diameter_wheel_mm + 2.0 * module_mm * (1.0 + x2)
    wheel_root_diameter_mm = max(1e-6, pitch_diameter_wheel_mm - 2.0 * module_mm * (1.2 - x2))
    lead_mm = math.pi * pitch_diameter_worm_mm * math.tan(lead_angle_calc_rad)
    axial_pitch_mm = lead_mm / z1
    worm_face_width_mm = _positive(
        float(geometry.get("worm_face_width_mm", 8.0 * module_mm)),
        "geometry.worm_face_width_mm",
    )
    wheel_face_width_mm = _positive(
        float(geometry.get("wheel_face_width_mm", 7.0 * module_mm)),
        "geometry.wheel_face_width_mm",
    )

    worm_pitch_line_speed_mps = math.pi * pitch_diameter_worm_mm * speed_rpm / 60000.0
    wheel_speed_rpm = speed_rpm / ratio
    wheel_pitch_line_speed_mps = math.pi * pitch_diameter_wheel_mm * wheel_speed_rpm / 60000.0

    input_torque_nm = 9550.0 * power_kw / max(speed_rpm, 1e-6)

    friction_override = advanced.get("friction_override", "")
    if friction_override in ("", None):
        friction_mu = _estimate_friction(worm_material, wheel_material)
    else:
        friction_mu = float(friction_override)
        if not (0.01 <= friction_mu <= 0.30):
            raise InputError(f"摩擦系数覆盖值必须在 0.01~0.30 范围内，当前值 {friction_mu}")
    efficiency_estimate = math.tan(lead_angle_calc_rad) / math.tan(lead_angle_calc_rad + math.atan(friction_mu))
    efficiency_estimate = _fraction(min(0.98, max(0.30, efficiency_estimate)), "performance.efficiency_estimate")

    output_power_kw = power_kw * efficiency_estimate
    power_loss_kw = power_kw - output_power_kw
    output_torque_nm = 9550.0 * output_power_kw / max(wheel_speed_rpm, 1e-6)
    thermal_capacity_kw = power_loss_kw
    normal_pressure_angle_deg = _positive(
        float(advanced.get("normal_pressure_angle_deg", 20.0)),
        "advanced.normal_pressure_angle_deg",
    )
    normal_pressure_angle_rad = math.radians(normal_pressure_angle_deg)

    # Geometry consistency warnings (needed by both enabled and disabled paths)
    geometry_warnings: list[str] = []
    if diameter_factor_q not in STANDARD_Q_VALUES:
        geometry_warnings.append(f"直径系数 q={diameter_factor_q} 不在 DIN 标准推荐序列内。")
    if abs(lead_angle_delta_deg) > 0.5:
        geometry_warnings.append(
            f"导程角与 z1/q 不一致：输入 gamma={lead_angle_deg:.2f} deg，推导值 {lead_angle_calc_deg:.2f} deg。"
        )
    if abs(center_distance_delta_mm) > max(0.25 * module_mm, 0.5):
        geometry_warnings.append(
            f"中心距与理论中心距偏差较大：a-a_th={center_distance_delta_mm:.3f} mm。"
        )

    # Tooth geometry (needed for wheel_dimensions output regardless of LC enabled)
    tooth_height_mm = module_mm * (2.2 + x1 - x2)
    tooth_height_mm = max(tooth_height_mm, 1e-6)

    # Performance curve
    curve_points = 25
    load_factors: list[float] = []
    efficiency_curve: list[float] = []
    power_loss_curve: list[float] = []
    thermal_capacity_curve: list[float] = []
    current_index = 0
    closest_delta = float("inf")
    for idx in range(curve_points):
        factor = 0.4 + 0.9 * idx / (curve_points - 1)
        load_factors.append(factor)
        eta_i = max(0.25, min(0.98, efficiency_estimate - 0.06 * (factor - 1.0) ** 2))
        input_power_i = power_kw * factor
        output_power_i = input_power_i * eta_i
        p_loss_i = input_power_i - output_power_i
        p_thermal_i = p_loss_i
        efficiency_curve.append(eta_i)
        power_loss_curve.append(p_loss_i)
        thermal_capacity_curve.append(p_thermal_i)
        if abs(factor - 1.0) < closest_delta:
            closest_delta = abs(factor - 1.0)
            current_index = idx

    # Common output sections (geometry, performance, curve)
    geometry_out: Dict[str, Any] = {
        "ratio": ratio,
        "module_mm": module_mm,
        "center_distance_mm": center_distance_mm,
        "theoretical_center_distance_mm": theoretical_center_distance_mm,
        "center_distance_delta_mm": center_distance_delta_mm,
        "pitch_diameter_worm_mm": pitch_diameter_worm_mm,
        "pitch_diameter_wheel_mm": pitch_diameter_wheel_mm,
        "lead_angle_deg": lead_angle_calc_deg,
        "lead_angle_input_deg": lead_angle_deg,
        "lead_angle_calc_deg": lead_angle_calc_deg,
        "lead_angle_delta_deg": lead_angle_delta_deg,
        "worm_speed_rpm": speed_rpm,
        "wheel_speed_rpm": wheel_speed_rpm,
        "worm_dimensions": {
            "pitch_diameter_mm": pitch_diameter_worm_mm,
            "tip_diameter_mm": worm_tip_diameter_mm,
            "root_diameter_mm": worm_root_diameter_mm,
            "lead_mm": lead_mm,
            "axial_pitch_mm": axial_pitch_mm,
            "pitch_line_speed_mps": worm_pitch_line_speed_mps,
            "face_width_mm": worm_face_width_mm,
        },
        "wheel_dimensions": {
            "pitch_diameter_mm": pitch_diameter_wheel_mm,
            "tip_diameter_mm": wheel_tip_diameter_mm,
            "root_diameter_mm": wheel_root_diameter_mm,
            "pitch_line_speed_mps": wheel_pitch_line_speed_mps,
            "tooth_height_mm": tooth_height_mm,
            "face_width_mm": wheel_face_width_mm,
        },
        "mesh_dimensions": {
            "ratio": ratio,
            "center_distance_mm": center_distance_mm,
            "theoretical_center_distance_mm": theoretical_center_distance_mm,
            "center_distance_delta_mm": center_distance_delta_mm,
            "worm_speed_rpm": speed_rpm,
            "wheel_speed_rpm": wheel_speed_rpm,
            "input_torque_nm": input_torque_nm,
            "output_torque_nm": output_torque_nm,
        },
        "consistency": {
            "lead_angle_calc_deg": lead_angle_calc_deg,
            "lead_angle_delta_deg": lead_angle_delta_deg,
            "center_distance_delta_mm": center_distance_delta_mm,
            "warnings": geometry_warnings,
        },
    }
    performance_out: Dict[str, Any] = {
        "input_power_kw": power_kw,
        "output_power_kw": output_power_kw,
        "input_torque_nm": input_torque_nm,
        "worm_pitch_line_speed_mps": worm_pitch_line_speed_mps,
        "efficiency_estimate": efficiency_estimate,
        "power_loss_kw": power_loss_kw,
        "thermal_capacity_kw": thermal_capacity_kw,
        "output_torque_nm": output_torque_nm,
        "friction_mu": friction_mu,
        "application_factor": application_factor,
    }
    curve_out: Dict[str, Any] = {
        "load_factor": load_factors,
        "efficiency": efficiency_curve,
        "power_loss_kw": power_loss_curve,
        "thermal_capacity_kw": thermal_capacity_curve,
        "current_load_factor": 1.0,
        "current_index": current_index,
        "current_efficiency": efficiency_estimate,
        "current_power_loss_kw": power_loss_kw,
        "current_thermal_capacity_kw": thermal_capacity_kw,
    }

    # ---- Load capacity: enabled flag guard ----
    lc_enabled = bool(load_capacity.get("enabled", False))

    if not lc_enabled:
        return {
            "inputs_echo": data,
            "geometry": geometry_out,
            "performance": performance_out,
            "curve": curve_out,
            "load_capacity": {
                "enabled": False,
                "status": "未启用",
                "checks": {},
                "forces": {},
                "contact": {},
                "root": {},
                "torque_ripple": {},
                "factors": {},
                "warnings": [],
                "assumptions": [],
            },
        }

    # ---- Load capacity parameters (only parsed when enabled) ----
    dynamic_factor_kv = _positive(float(load_capacity.get("dynamic_factor_kv", 1.0)), "load_capacity.dynamic_factor_kv")
    transverse_load_factor_kha = _positive(
        float(load_capacity.get("transverse_load_factor_kha", 1.0)),
        "load_capacity.transverse_load_factor_kha",
    )
    face_load_factor_khb = _positive(
        float(load_capacity.get("face_load_factor_khb", 1.0)),
        "load_capacity.face_load_factor_khb",
    )
    allowable_contact_stress_mpa = _positive(
        float(load_capacity.get("allowable_contact_stress_mpa", wheel_allowable_defaults["contact_mpa"])),
        "load_capacity.allowable_contact_stress_mpa",
    )
    allowable_root_stress_mpa = _positive(
        float(load_capacity.get("allowable_root_stress_mpa", wheel_allowable_defaults["root_mpa"])),
        "load_capacity.allowable_root_stress_mpa",
    )
    required_contact_safety = _positive(
        float(load_capacity.get("required_contact_safety", 1.0)),
        "load_capacity.required_contact_safety",
    )
    required_root_safety = _positive(
        float(load_capacity.get("required_root_safety", 1.0)),
        "load_capacity.required_root_safety",
    )

    torque_ripple_ratio = torque_ripple_percent / 100.0
    design_force_factor = application_factor * dynamic_factor_kv * transverse_load_factor_kha * face_load_factor_khb

    output_torque_min_nm = max(0.0, output_torque_nm * (1.0 - torque_ripple_ratio))
    output_torque_peak_nm = output_torque_nm * (1.0 + torque_ripple_ratio)
    output_torque_rms_nm = output_torque_nm * math.sqrt(1.0 + 0.5 * torque_ripple_ratio * torque_ripple_ratio)
    input_torque_min_nm = max(0.0, input_torque_nm * (1.0 - torque_ripple_ratio))
    input_torque_peak_nm = input_torque_nm * (1.0 + torque_ripple_ratio)
    input_torque_rms_nm = input_torque_nm * math.sqrt(1.0 + 0.5 * torque_ripple_ratio * torque_ripple_ratio)

    tangential_force_wheel_n = 2000.0 * output_torque_nm / max(pitch_diameter_wheel_mm, 1e-6)
    tangential_force_wheel_peak_n = 2000.0 * output_torque_peak_nm / max(pitch_diameter_wheel_mm, 1e-6)
    tangential_force_wheel_rms_n = 2000.0 * output_torque_rms_nm / max(pitch_diameter_wheel_mm, 1e-6)
    tangential_force_wheel_min_n = 2000.0 * output_torque_min_nm / max(pitch_diameter_wheel_mm, 1e-6)

    sin_gamma = max(math.sin(lead_angle_calc_rad), 1e-6)
    cos_alpha_n = max(math.cos(normal_pressure_angle_rad), 1e-6)
    tan_gamma = max(math.tan(lead_angle_calc_rad), 1e-6)
    radial_factor = math.tan(normal_pressure_angle_rad) / sin_gamma
    normal_force_n = tangential_force_wheel_n / (cos_alpha_n * sin_gamma)
    normal_force_peak_n = tangential_force_wheel_peak_n / (cos_alpha_n * sin_gamma)
    normal_force_rms_n = tangential_force_wheel_rms_n / (cos_alpha_n * sin_gamma)
    axial_force_wheel_n = tangential_force_wheel_n / tan_gamma
    radial_force_wheel_n = tangential_force_wheel_n * radial_factor

    design_normal_force_n = normal_force_n * design_force_factor
    design_normal_force_peak_n = normal_force_peak_n * design_force_factor
    design_normal_force_rms_n = normal_force_rms_n * design_force_factor
    design_tangential_force_n = tangential_force_wheel_n * design_force_factor
    design_tangential_force_peak_n = tangential_force_wheel_peak_n * design_force_factor
    design_tangential_force_rms_n = tangential_force_wheel_rms_n * design_force_factor

    equivalent_modulus_mpa = 1.0 / (((1.0 - worm_nu * worm_nu) / worm_e_mpa) + ((1.0 - wheel_nu * wheel_nu) / wheel_e_mpa))
    contact_length_mm = max(1e-6, min(worm_face_width_mm, wheel_face_width_mm))
    equivalent_radius_mm = 1.0 / ((2.0 / pitch_diameter_worm_mm) + (2.0 / pitch_diameter_wheel_mm))
    tooth_root_thickness_mm = max(1.25 * module_mm, 1e-6)

    def _mean_hertz_stress(normal_force_value_n: float) -> float:
        specific_load = normal_force_value_n / contact_length_mm
        semi_width_mm = math.sqrt((4.0 * specific_load * equivalent_radius_mm) / (math.pi * equivalent_modulus_mpa))
        return specific_load / max(2.0 * semi_width_mm, 1e-6)

    def _root_stress(tangential_force_value_n: float) -> float:
        section_modulus_mm3 = contact_length_mm * tooth_root_thickness_mm * tooth_root_thickness_mm / 6.0
        bending_moment_nmm = tangential_force_value_n * tooth_height_mm
        return bending_moment_nmm / max(section_modulus_mm3, 1e-6)

    sigma_hm_nominal_mpa = _mean_hertz_stress(design_normal_force_n)
    sigma_hm_rms_mpa = _mean_hertz_stress(design_normal_force_rms_n)
    sigma_hm_peak_mpa = _mean_hertz_stress(design_normal_force_peak_n)
    sigma_f_nominal_mpa = _root_stress(design_tangential_force_n)
    sigma_f_rms_mpa = _root_stress(design_tangential_force_rms_n)
    sigma_f_peak_mpa = _root_stress(design_tangential_force_peak_n)

    contact_safety_factor_nominal = allowable_contact_stress_mpa / max(sigma_hm_nominal_mpa, 1e-6)
    contact_safety_factor_peak = allowable_contact_stress_mpa / max(sigma_hm_peak_mpa, 1e-6)
    root_safety_factor_nominal = allowable_root_stress_mpa / max(sigma_f_nominal_mpa, 1e-6)
    root_safety_factor_peak = allowable_root_stress_mpa / max(sigma_f_peak_mpa, 1e-6)
    contact_ok = contact_safety_factor_peak >= required_contact_safety
    root_ok = root_safety_factor_peak >= required_root_safety

    method = str(load_capacity.get("method", "DIN 3996 Method B"))

    return {
        "inputs_echo": data,
        "geometry": geometry_out,
        "performance": performance_out,
        "curve": curve_out,
        "load_capacity": {
            "enabled": True,
            "method": method,
            "status": (
                f"{method} 最小子集校核通过（当前版本各方法计算逻辑相同，仅作标记）"
                if contact_ok and root_ok and not geometry_warnings
                else f"{method} 最小子集已计算（存在警告或不通过项）（当前版本各方法计算逻辑相同，仅作标记）"
            ),
            "warnings": geometry_warnings,
            "factors": {
                "application_factor": application_factor,
                "dynamic_factor_kv": dynamic_factor_kv,
                "transverse_load_factor_kha": transverse_load_factor_kha,
                "face_load_factor_khb": face_load_factor_khb,
                "design_force_factor": design_force_factor,
            },
            "torque_ripple": {
                "percent": torque_ripple_percent,
                "ratio": torque_ripple_ratio,
                "input_torque_nominal_nm": input_torque_nm,
                "input_torque_min_nm": input_torque_min_nm,
                "input_torque_rms_nm": input_torque_rms_nm,
                "input_torque_peak_nm": input_torque_peak_nm,
                "output_torque_nominal_nm": output_torque_nm,
                "output_torque_min_nm": output_torque_min_nm,
                "output_torque_rms_nm": output_torque_rms_nm,
                "output_torque_peak_nm": output_torque_peak_nm,
            },
            "forces": {
                "tangential_force_wheel_n": tangential_force_wheel_n,
                "tangential_force_wheel_min_n": tangential_force_wheel_min_n,
                "tangential_force_wheel_rms_n": tangential_force_wheel_rms_n,
                "tangential_force_wheel_peak_n": tangential_force_wheel_peak_n,
                "axial_force_wheel_n": axial_force_wheel_n,
                "radial_force_wheel_n": radial_force_wheel_n,
                "normal_force_n": normal_force_n,
                "design_normal_force_n": design_normal_force_n,
                "design_normal_force_rms_n": design_normal_force_rms_n,
                "design_normal_force_peak_n": design_normal_force_peak_n,
            },
            "contact": {
                "equivalent_modulus_mpa": equivalent_modulus_mpa,
                "equivalent_radius_mm": equivalent_radius_mm,
                "contact_length_mm": contact_length_mm,
                "sigma_hm_nominal_mpa": sigma_hm_nominal_mpa,
                "sigma_hm_rms_mpa": sigma_hm_rms_mpa,
                "sigma_hm_peak_mpa": sigma_hm_peak_mpa,
                "allowable_contact_stress_mpa": allowable_contact_stress_mpa,
                "required_contact_safety": required_contact_safety,
                "safety_factor_nominal": contact_safety_factor_nominal,
                "safety_factor_peak": contact_safety_factor_peak,
            },
            "root": {
                "tooth_height_mm": tooth_height_mm,
                "tooth_root_thickness_mm": tooth_root_thickness_mm,
                "sigma_f_nominal_mpa": sigma_f_nominal_mpa,
                "sigma_f_rms_mpa": sigma_f_rms_mpa,
                "sigma_f_peak_mpa": sigma_f_peak_mpa,
                "allowable_root_stress_mpa": allowable_root_stress_mpa,
                "required_root_safety": required_root_safety,
                "safety_factor_nominal": root_safety_factor_nominal,
                "safety_factor_peak": root_safety_factor_peak,
            },
            "checks": {
                "geometry_consistent": not geometry_warnings,
                "contact_ok": contact_ok,
                "root_ok": root_ok,
            },
            "assumptions": [
                "当前结果为 Method B 风格最小工程子集，不是完整 DIN 3996 / ISO/TS 14521。",
                "齿形假设：ZK 型（锥面砂轮展成）。",
                "齿面应力采用线接触 Hertz 近似，等效曲率半径基于分度圆简化（未考虑蜗轮凹面修正）。",
                "接触长度取 min(b1, b2)，未考虑包角影响。",
                "齿根应力采用等效悬臂梁近似。",
                "蜗轮齿顶/齿根高系数与蜗杆相同（含变位修正），未单独处理间隙系数。",
                "钢-塑料配对，许用应力为常温干态工程经验值。",
                "当前版本各方法计算逻辑相同，仅作标记用途。",
            ],
        },
    }
