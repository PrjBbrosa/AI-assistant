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

    input_torque_nm = _positive(float(_require(operating, "input_torque_nm", "operating")), "operating.input_torque_nm")
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

    power_kw = input_torque_nm * speed_rpm / 9550.0

    handedness = str(materials.get("handedness", "right")).strip().lower()
    lubrication = str(materials.get("lubrication", "grease")).strip().lower()

    friction_override = advanced.get("friction_override", "")
    if friction_override in ("", None):
        friction_mu = _estimate_friction(worm_material, wheel_material)
    else:
        friction_mu = float(friction_override)
        if not (0.01 <= friction_mu <= 0.30):
            raise InputError(f"摩擦系数覆盖值必须在 0.01~0.30 范围内，当前值 {friction_mu}")

    # 润滑方式影响摩擦系数（塑料-钢副）
    # 油浴润滑降摩擦约 10%，干摩擦升约 35%（工程经验）
    LUB_MU_MULTIPLIER = {"oil_bath": 0.90, "grease": 1.00, "dry": 1.35}
    friction_mu = friction_mu * LUB_MU_MULTIPLIER.get(lubrication, 1.00)
    # 润滑修正后重新检查上限
    friction_mu = min(friction_mu, 0.50)

    # 提前读取法向压力角（效率和自锁公式共用）
    normal_pressure_angle_deg = _positive(
        float(advanced.get("normal_pressure_angle_deg", 20.0)),
        "advanced.normal_pressure_angle_deg",
    )
    normal_pressure_angle_rad = math.radians(normal_pressure_angle_deg)

    # 效率公式（含当量摩擦角 phi' = atan(mu / cos(alpha_n))）
    # DIN 3975 / Niemann §24：eta = tan(gamma) / tan(gamma + phi')
    phi_prime_rad = math.atan(friction_mu / max(math.cos(normal_pressure_angle_rad), 1e-6))
    phi_prime_deg = math.degrees(phi_prime_rad)
    efficiency_estimate = math.tan(lead_angle_calc_rad) / math.tan(lead_angle_calc_rad + phi_prime_rad)
    # Apply only physical upper limit (lossless is impossible); no lower clamp — caller sees true value.
    efficiency_estimate = min(0.98, efficiency_estimate)

    # 自锁判定：gamma <= phi' 则无法反向驱动蜗杆
    self_locking = lead_angle_calc_rad <= phi_prime_rad

    output_power_kw = power_kw * efficiency_estimate
    power_loss_kw = power_kw - output_power_kw
    output_torque_nm = 9550.0 * output_power_kw / max(wheel_speed_rpm, 1e-6)

    # 热容量按简化箱体散热公式（DIN 3996 简化）
    # Q_th = k * A * ΔT / 1000  (kW)
    # 塑料蜗轮散热系数 k 约 12-18 W/(m²·K)，此处取 14
    # 接触面积 A 按 2·d2·b2 简化（单位 m²）
    # 允许温升 ΔT = 50 K（PA66 工程上限约 80℃，环境 30℃）
    thermal_heat_transfer_coefficient = float(advanced.get("thermal_k_w_m2k", 14.0))
    thermal_allowable_delta_t_k = float(advanced.get("thermal_delta_t_k", 50.0))
    thermal_area_m2 = (2.0 * pitch_diameter_wheel_mm * wheel_face_width_mm) / 1.0e6
    thermal_capacity_kw = thermal_heat_transfer_coefficient * thermal_area_m2 * thermal_allowable_delta_t_k / 1000.0

    # Collect performance-level warnings (does not modify computed values)
    performance_warnings: list[str] = []
    if self_locking:
        performance_warnings.append(
            f"自锁：gamma={lead_angle_calc_deg:.2f} deg <= phi'={phi_prime_deg:.2f} deg，"
            f"不可反向驱动。"
        )
    if efficiency_estimate <= 0:
        performance_warnings.append(
            f"效率估算值 eta={efficiency_estimate:.4f} <= 0，蜗轮副在当前导程角 gamma={lead_angle_calc_deg:.2f} deg"
            f" 和摩擦系数 mu={friction_mu:.3f} 下处于自锁状态，功率无法从蜗杆传递至蜗轮。"
        )
    elif efficiency_estimate < 0.30:
        performance_warnings.append(
            f"效率估算值 eta={efficiency_estimate:.4f} 异常偏低（< 0.30），"
            f"对应导程角 gamma={lead_angle_calc_deg:.2f} deg、摩擦系数 mu={friction_mu:.3f}，"
            f"请确认设计参数是否合理。"
        )
    if power_loss_kw > thermal_capacity_kw:
        performance_warnings.append(
            f"热负荷超限：损失功率 P_loss={power_loss_kw:.3f} kW > 允许散热 Q_th={thermal_capacity_kw:.3f} kW。"
        )

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
    temperature_rise_curve: list[float] = []
    current_index = 0
    closest_delta = float("inf")
    for idx in range(curve_points):
        factor = 0.4 + 0.9 * idx / (curve_points - 1)
        load_factors.append(factor)
        eta_i = max(0.25, min(0.98, efficiency_estimate - 0.06 * (factor - 1.0) ** 2))
        input_power_i = power_kw * factor
        output_power_i = input_power_i * eta_i
        p_loss_i = input_power_i - output_power_i
        # 温升 = 损失功率 / 散热容量 * 允许温升（线性比例）
        delta_t_i = p_loss_i / max(thermal_capacity_kw, 1e-6) * thermal_allowable_delta_t_k
        efficiency_curve.append(eta_i)
        power_loss_curve.append(p_loss_i)
        temperature_rise_curve.append(delta_t_i)
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
        "self_locking": self_locking,
        "phi_prime_deg": phi_prime_deg,
        "warnings": performance_warnings,
    }
    curve_out: Dict[str, Any] = {
        "load_factor": load_factors,
        "efficiency": efficiency_curve,
        "power_loss_kw": power_loss_curve,
        "temperature_rise_k": temperature_rise_curve,
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
                "stress_curve": {},
            },
        }

    # ---- Method 解析（在所有参数解析之前，Method C 立即拒绝） ----
    method = str(load_capacity.get("method", "DIN 3996 Method B")).strip()
    method_normalized = method.upper().replace(" ", "")

    if "METHODC" in method_normalized:
        raise InputError(
            "Method C 需要 FEA 输入，当前版本未实现。请使用 Method A 或 Method B。"
        )

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

    # 蜗杆力系分解（Niemann §24 / DIN 3975）
    # 坐标约定：蜗杆轴向 ≡ 蜗轮切向（F_a1 = F_t2），蜗杆切向 ≡ 蜗轮轴向（F_t1 = F_a2）
    # 参考案例（spec 验证）：m=4, z1=1, z2=40, q=10, alpha_n=20 deg, mu=0.05, T2=500 N·m
    #   d2=160 mm, F_t2=6250 N, gamma=5.7106 deg, phi'=3.0466 deg
    #   F_a2 = F_t2·tan(gamma+phi') = 6250·tan(8.757°) = 962.8 N
    #   F_r  = F_t2·tan(alpha_n)/cos(gamma) = 6250·0.36397/0.99504 = 2285.8 N
    #   F_n  = F_t2/(cos(alpha_n)·cos(gamma)) = 6250/(0.93969·0.99504) = 6683.5 N
    #   eta  = tan(gamma)/tan(gamma+phi') = 0.1000/0.15401 = 0.6493
    cos_alpha_n = math.cos(normal_pressure_angle_rad)
    sin_gamma = math.sin(lead_angle_calc_rad)
    cos_gamma = math.cos(lead_angle_calc_rad)
    tan_gamma = math.tan(lead_angle_calc_rad)

    # 当量摩擦角（法向摩擦角投影到轴向）phi' = atan(mu / cos(alpha_n))
    phi_prime_force_rad = math.atan(friction_mu / max(cos_alpha_n, 1e-6))
    tan_gamma_plus_phi = math.tan(lead_angle_calc_rad + phi_prime_force_rad)

    # F_a2（蜗轮轴向力）= F_t1（蜗杆切向力）= F_t2·tan(gamma+phi')
    axial_force_wheel_n = tangential_force_wheel_n * tan_gamma_plus_phi
    # F_r（径向力）= F_t2·tan(alpha_n)/cos(gamma)
    radial_force_wheel_n = tangential_force_wheel_n * math.tan(normal_pressure_angle_rad) / max(cos_gamma, 1e-6)
    # F_n（法向力）= F_t2/(cos(alpha_n)·cos(gamma))
    normal_force_n = tangential_force_wheel_n / max(cos_alpha_n * cos_gamma, 1e-6)
    normal_force_peak_n = tangential_force_wheel_peak_n / max(cos_alpha_n * cos_gamma, 1e-6)
    normal_force_rms_n = tangential_force_wheel_rms_n / max(cos_alpha_n * cos_gamma, 1e-6)

    design_normal_force_n = normal_force_n * design_force_factor
    design_normal_force_peak_n = normal_force_peak_n * design_force_factor
    design_normal_force_rms_n = normal_force_rms_n * design_force_factor
    design_tangential_force_n = tangential_force_wheel_n * design_force_factor
    design_tangential_force_peak_n = tangential_force_wheel_peak_n * design_force_factor
    design_tangential_force_rms_n = tangential_force_wheel_rms_n * design_force_factor

    equivalent_modulus_mpa = 1.0 / (((1.0 - worm_nu * worm_nu) / worm_e_mpa) + ((1.0 - wheel_nu * wheel_nu) / wheel_e_mpa))
    contact_length_mm = max(1e-6, min(worm_face_width_mm, wheel_face_width_mm))
    equivalent_radius_mm = 1.0 / ((2.0 / pitch_diameter_worm_mm) + (2.0 / pitch_diameter_wheel_mm))
    # 齿根弦齿厚（DIN 3975 简化）: s_Ft ≈ π·m·cos(α_n)/2
    tooth_root_thickness_mm = max(math.pi * module_mm * math.cos(normal_pressure_angle_rad) / 2.0, 1e-6)

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

    # Method A：手册系数法，效率折减 0.92，接触应力折减 0.95（波 0 简化实现）
    # Method B（默认）：DIN 3996 最小子集，直接使用上述计算结果
    if "METHODA" in method_normalized:
        method_efficiency_factor = 0.92
        # 更新 performance_out 中的效率（Method A 使用手册保守系数）
        performance_out["efficiency_estimate"] = performance_out["efficiency_estimate"] * method_efficiency_factor
        # 接触应力乘以 0.95 折减（Method A 手册方式）
        sigma_hm_nominal_mpa = sigma_hm_nominal_mpa * 0.95
        sigma_hm_rms_mpa = sigma_hm_rms_mpa * 0.95
        sigma_hm_peak_mpa = sigma_hm_peak_mpa * 0.95

    contact_safety_factor_nominal = allowable_contact_stress_mpa / max(sigma_hm_nominal_mpa, 1e-6)
    contact_safety_factor_peak = allowable_contact_stress_mpa / max(sigma_hm_peak_mpa, 1e-6)
    root_safety_factor_nominal = allowable_root_stress_mpa / max(sigma_f_nominal_mpa, 1e-6)
    root_safety_factor_peak = allowable_root_stress_mpa / max(sigma_f_peak_mpa, 1e-6)
    contact_ok = contact_safety_factor_peak >= required_contact_safety
    root_ok = root_safety_factor_peak >= required_root_safety

    # ---- Mesh stress curve: contact geometry variation over one worm revolution ----
    curve_n_points = 360
    r_root1_mm = worm_root_diameter_mm / 2.0
    r_tip1_mm = worm_tip_diameter_mm / 2.0
    r_pitch1_mm = pitch_diameter_worm_mm / 2.0

    theta_deg_list: list[float] = []
    sigma_h_curve: list[float] = []
    sigma_f_curve: list[float] = []

    z1_int = int(z1)
    mesh_period_deg = 360.0 / z1_int

    for i in range(curve_n_points):
        theta = i * 360.0 / curve_n_points
        theta_deg_list.append(theta)

        # Mesh phase within one tooth cycle [0, 1)
        # Offset by 0.5 so that the root contact (peak stress) falls at
        # the centre of each cycle, making peaks interior to the curve.
        phase_raw = (theta % mesh_period_deg) / mesh_period_deg
        phi = (phase_raw + 0.5) % 1.0

        # Contact radius on worm: root -> tip -> root (triangular profile)
        r1 = r_root1_mm + (r_tip1_mm - r_root1_mm) * (1.0 - abs(2.0 * phi - 1.0))

        # Worm-side curvature radius
        rho1 = r1 * math.sin(lead_angle_calc_rad)
        rho1 = max(rho1, 0.1)

        # Wheel-side curvature radius (concave envelope)
        rho2 = center_distance_mm - r1
        rho2 = max(rho2, 0.1)

        # Equivalent curvature radius (convex-concave contact)
        if rho2 > rho1:
            rho_eq = (rho1 * rho2) / (rho2 - rho1)
        else:
            rho_eq = rho1 * 10.0

        rho_eq = max(rho_eq, 0.01)

        # Hertz contact stress at this phase
        specific_load = design_normal_force_n / contact_length_mm
        sigma_h_phi = math.sqrt(specific_load * equivalent_modulus_mpa / (math.pi * rho_eq))
        sigma_h_curve.append(sigma_h_phi)

        # Root bending stress
        h_phi = max(r1 - r_root1_mm, 0.01)
        section_modulus_mm3 = contact_length_mm * tooth_root_thickness_mm ** 2 / 6.0
        sigma_f_phi = design_tangential_force_n * h_phi / max(section_modulus_mm3, 1e-6)
        sigma_f_curve.append(sigma_f_phi)

    # Nominal values at pitch circle
    rho1_nom = r_pitch1_mm * math.sin(lead_angle_calc_rad)
    rho2_nom = center_distance_mm - r_pitch1_mm
    if rho2_nom > rho1_nom:
        rho_eq_nom = (rho1_nom * rho2_nom) / (rho2_nom - rho1_nom)
    else:
        rho_eq_nom = rho1_nom * 10.0
    rho_eq_nom = max(rho_eq_nom, 0.01)
    sigma_h_nominal_curve = math.sqrt(
        (design_normal_force_n / contact_length_mm) * equivalent_modulus_mpa / (math.pi * rho_eq_nom)
    )
    h_nom = max(r_pitch1_mm - r_root1_mm, 0.01)
    section_mod = contact_length_mm * tooth_root_thickness_mm ** 2 / 6.0
    sigma_f_nominal_curve = design_tangential_force_n * h_nom / max(section_mod, 1e-6)

    stress_curve_out: dict[str, Any] = {
        "theta_deg": theta_deg_list,
        "sigma_h_mpa": sigma_h_curve,
        "sigma_f_mpa": sigma_f_curve,
        "sigma_h_nominal_mpa": sigma_h_nominal_curve,
        "sigma_f_nominal_mpa": sigma_f_nominal_curve,
        "sigma_h_peak_mpa": max(sigma_h_curve),
        "sigma_f_peak_mpa": max(sigma_f_curve),
        "mesh_frequency_per_rev": int(z1),
    }

    return {
        "inputs_echo": data,
        "geometry": geometry_out,
        "performance": performance_out,
        "curve": curve_out,
        "load_capacity": {
            "enabled": True,
            "method": method,
            "status": (
                f"{method} 最小子集校核通过"
                if contact_ok and root_ok and not geometry_warnings
                else f"{method} 最小子集已计算（存在警告或不通过项）"
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
                "handedness": handedness,
                "radial_force_direction": "inward" if handedness == "right" else "outward",
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
                # geometry_consistent 仅判断导程角和中心距是否自洽，
                # q 不在推荐序列仅为提示性警告，不影响几何自洽判断
                "geometry_consistent": (
                    abs(lead_angle_delta_deg) <= 0.5
                    and abs(center_distance_delta_mm) <= max(0.25 * module_mm, 0.5)
                ),
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
                "Method A: 手册系数法，接触应力乘 0.95 折减；Method B（默认）: DIN 3996 最小子集；Method C: 需 FEA 输入，当前版本拒绝。",
            ],
            "stress_curve": stress_curve_out,
        },
    }
