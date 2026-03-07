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


MATERIAL_FRICTION_HINTS = {
    ("20CrMnTi", "ZCuSn12Ni2"): 0.055,
    ("16MnCr5", "ZCuSn12Ni2"): 0.055,
    ("42CrMo", "ZCuSn12Ni2"): 0.060,
}


def _estimate_friction(worm_material: str, wheel_material: str) -> float:
    return MATERIAL_FRICTION_HINTS.get((worm_material, wheel_material), 0.065)


def calculate_worm_geometry(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate DIN 3975-style geometry summary and basic performance values."""
    geometry = data.get("geometry", {})
    operating = data.get("operating", {})
    materials = data.get("materials", {})
    load_capacity = data.get("load_capacity", {})

    z1 = _positive(float(_require(geometry, "z1", "geometry")), "geometry.z1")
    z2 = _positive(float(_require(geometry, "z2", "geometry")), "geometry.z2")
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

    power_kw = _positive(float(_require(operating, "power_kw", "operating")), "operating.power_kw")
    speed_rpm = _positive(float(_require(operating, "speed_rpm", "operating")), "operating.speed_rpm")

    worm_material = str(materials.get("worm_material", "钢制蜗杆")).strip() or "钢制蜗杆"
    wheel_material = str(materials.get("wheel_material", "青铜蜗轮")).strip() or "青铜蜗轮"

    ratio = z2 / z1
    lead_angle_rad = math.radians(lead_angle_deg)
    pitch_diameter_worm_mm = diameter_factor_q * module_mm
    pitch_diameter_wheel_mm = max(1e-6, 2.0 * center_distance_mm - pitch_diameter_worm_mm)
    theoretical_center_distance_mm = module_mm * (diameter_factor_q + z2) / 2.0
    center_distance_delta_mm = center_distance_mm - theoretical_center_distance_mm
    worm_tip_diameter_mm = pitch_diameter_worm_mm + 2.0 * module_mm
    worm_root_diameter_mm = max(1e-6, pitch_diameter_worm_mm - 2.4 * module_mm)
    wheel_tip_diameter_mm = pitch_diameter_wheel_mm + 2.0 * module_mm
    wheel_root_diameter_mm = max(1e-6, pitch_diameter_wheel_mm - 2.4 * module_mm)
    lead_mm = math.pi * pitch_diameter_worm_mm * math.tan(lead_angle_rad)
    axial_pitch_mm = lead_mm / z1

    worm_pitch_line_speed_mps = math.pi * pitch_diameter_worm_mm * speed_rpm / 60000.0
    wheel_speed_rpm = speed_rpm / ratio
    wheel_pitch_line_speed_mps = math.pi * pitch_diameter_wheel_mm * wheel_speed_rpm / 60000.0
    output_torque_nm = 9550.0 * power_kw / max(wheel_speed_rpm, 1e-6)

    friction_mu = _estimate_friction(worm_material, wheel_material)
    efficiency_estimate = math.tan(lead_angle_rad) / math.tan(lead_angle_rad + math.atan(friction_mu))
    efficiency_estimate = _fraction(min(0.98, max(0.30, efficiency_estimate)), "performance.efficiency_estimate")

    power_loss_kw = power_kw * (1.0 / efficiency_estimate - 1.0)
    thermal_capacity_kw = power_kw + power_loss_kw * 0.55

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
        p_loss_i = power_kw * factor * (1.0 / eta_i - 1.0)
        p_thermal_i = power_kw * factor + p_loss_i * 0.55
        efficiency_curve.append(eta_i)
        power_loss_curve.append(p_loss_i)
        thermal_capacity_curve.append(p_thermal_i)
        if abs(factor - 1.0) < closest_delta:
            closest_delta = abs(factor - 1.0)
            current_index = idx

    method = str(load_capacity.get("method", "DIN 3996 Method B"))

    return {
        "inputs_echo": data,
        "geometry": {
            "ratio": ratio,
            "module_mm": module_mm,
            "center_distance_mm": center_distance_mm,
            "theoretical_center_distance_mm": theoretical_center_distance_mm,
            "center_distance_delta_mm": center_distance_delta_mm,
            "pitch_diameter_worm_mm": pitch_diameter_worm_mm,
            "pitch_diameter_wheel_mm": pitch_diameter_wheel_mm,
            "lead_angle_deg": lead_angle_deg,
            "worm_speed_rpm": speed_rpm,
            "wheel_speed_rpm": wheel_speed_rpm,
            "worm_dimensions": {
                "pitch_diameter_mm": pitch_diameter_worm_mm,
                "tip_diameter_mm": worm_tip_diameter_mm,
                "root_diameter_mm": worm_root_diameter_mm,
                "lead_mm": lead_mm,
                "axial_pitch_mm": axial_pitch_mm,
                "pitch_line_speed_mps": worm_pitch_line_speed_mps,
            },
            "wheel_dimensions": {
                "pitch_diameter_mm": pitch_diameter_wheel_mm,
                "tip_diameter_mm": wheel_tip_diameter_mm,
                "root_diameter_mm": wheel_root_diameter_mm,
                "pitch_line_speed_mps": wheel_pitch_line_speed_mps,
                "tooth_height_mm": 2.25 * module_mm,
            },
            "mesh_dimensions": {
                "ratio": ratio,
                "center_distance_mm": center_distance_mm,
                "theoretical_center_distance_mm": theoretical_center_distance_mm,
                "center_distance_delta_mm": center_distance_delta_mm,
                "worm_speed_rpm": speed_rpm,
                "wheel_speed_rpm": wheel_speed_rpm,
                "output_torque_nm": output_torque_nm,
            },
        },
        "performance": {
            "worm_pitch_line_speed_mps": worm_pitch_line_speed_mps,
            "efficiency_estimate": efficiency_estimate,
            "power_loss_kw": power_loss_kw,
            "thermal_capacity_kw": thermal_capacity_kw,
            "output_torque_nm": output_torque_nm,
            "friction_mu": friction_mu,
        },
        "curve": {
            "load_factor": load_factors,
            "efficiency": efficiency_curve,
            "power_loss_kw": power_loss_curve,
            "thermal_capacity_kw": thermal_capacity_curve,
            "current_load_factor": 1.0,
            "current_index": current_index,
            "current_efficiency": efficiency_estimate,
            "current_power_loss_kw": power_loss_kw,
            "current_thermal_capacity_kw": thermal_capacity_kw,
        },
        "load_capacity": {
            "enabled": bool(load_capacity.get("enabled", False)),
            "method": method,
            "status": "DIN 3996 校核尚未开始",
        },
    }
