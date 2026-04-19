"""Hertzian contact-stress calculator for line and point contact."""

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


def _nu(value: float, name: str) -> float:
    if not (0.0 < value < 0.5):
        raise InputError(f"{name} 必须满足 0 < nu < 0.5，当前值 {value}")
    return value


def _radius_inverse(radius_mm: float, name: str) -> float:
    """Map 0 to plane/infinite radius, positive to curvature inverse."""
    _positive(radius_mm, name, allow_zero=True)
    if radius_mm == 0:
        return 0.0
    return 1.0 / radius_mm


def calculate_hertz_contact(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate Hertzian maximum contact pressure and contact patch size.

    Parameters
    ----------
    data : dict
        Must contain sub-dicts: ``geometry``, ``materials``, ``loads``, and
        optionally ``checks`` and ``options``.

    Returns
    -------
    dict
        Top-level keys and their key sub-keys:

        ``mode``
            ``"line"`` or ``"point"`` (string).

        ``derived``
            ``e_eq_mpa``, ``r_eq_mm``, ``inv_r1_per_mm``, ``inv_r2_per_mm``.

        ``contact``
            ``p0_mpa``, ``p_mean_mpa``, ``normal_force_n``,
            ``contact_area_mm2`` (always present),
            ``semi_width_mm`` (line contact only; 0.0 for point),
            ``contact_radius_mm`` (point contact only; 0.0 for line),
            ``length_mm`` (**line contact only** — key absent for point contact).

        ``check``
            ``allowable_p0_mpa``, ``safety_factor``.

        ``checks``
            ``contact_stress_ok`` (bool).

        ``curve``
            ``force_n``, ``p0_mpa``, ``force_design_n``, ``p0_design_mpa``.

        ``overall_pass``
            bool — True when ``p0_mpa <= allowable_p0_mpa``.

        ``warnings``
            list of Chinese warning strings (edge effect, low SF, clamped
            options).

        ``options``
            ``curve_points`` and ``curve_force_scale`` **effective** values
            after clamping (always present regardless of clamping).

        ``inputs_echo``
            The original ``data`` dict passed in.

    Notes
    -----
    ``contact_area_mm2`` lives at ``result["contact"]["contact_area_mm2"]``,
    **not** at the top level.  UI and report code must use the two-level path.
    """
    geometry = data.get("geometry", {})
    materials = data.get("materials", {})
    loads = data.get("loads", {})
    checks = data.get("checks", {})
    options = data.get("options", {})

    mode = str(_require(geometry, "contact_mode", "geometry")).strip().lower()
    if mode not in {"line", "point"}:
        raise InputError(f"geometry.contact_mode 无效：{mode}（支持 line/point）")

    r1 = _positive(float(_require(geometry, "r1_mm", "geometry")), "geometry.r1_mm", allow_zero=True)
    r2 = _positive(float(_require(geometry, "r2_mm", "geometry")), "geometry.r2_mm", allow_zero=True)
    inv_r = _radius_inverse(r1, "geometry.r1_mm") + _radius_inverse(r2, "geometry.r2_mm")
    if inv_r <= 0:
        raise InputError("等效曲率为 0，至少一个曲率半径必须为正数。")
    r_eq = 1.0 / inv_r

    e1 = _positive(float(_require(materials, "e1_mpa", "materials")), "materials.e1_mpa")
    nu1 = _nu(float(_require(materials, "nu1", "materials")), "materials.nu1")
    e2 = _positive(float(_require(materials, "e2_mpa", "materials")), "materials.e2_mpa")
    nu2 = _nu(float(_require(materials, "nu2", "materials")), "materials.nu2")

    e_eq = 1.0 / (((1.0 - nu1 * nu1) / e1) + ((1.0 - nu2 * nu2) / e2))
    normal_force = _positive(float(_require(loads, "normal_force_n", "loads")), "loads.normal_force_n")
    allowable_p0 = _positive(
        float(checks.get("allowable_p0_mpa", 1500.0)),
        "checks.allowable_p0_mpa",
    )

    # length_mm 仅线接触需要且必须 >0；点接触时该参数无物理意义，不校验
    if mode == "line":
        length_mm: float = _positive(
            float(geometry.get("length_mm", 10.0)),
            "geometry.length_mm",
        )
    else:
        # 点接触：忽略 length_mm，不做正值校验，不回填默认值
        length_mm = 0.0  # 仅用于内部分支占位，不写入结果

    semi_width = 0.0
    contact_radius = 0.0
    contact_area_mm2 = 0.0
    if mode == "line":
        load_per_length = normal_force / length_mm
        semi_width = math.sqrt((4.0 * load_per_length * r_eq) / (math.pi * e_eq))
        p0 = (2.0 * load_per_length) / (math.pi * semi_width)
        mean_pressure = load_per_length / (2.0 * semi_width)
        contact_area_mm2 = 2.0 * semi_width * length_mm
    else:
        contact_radius = ((3.0 * normal_force * r_eq) / (4.0 * e_eq)) ** (1.0 / 3.0)
        p0 = (3.0 * normal_force) / (2.0 * math.pi * contact_radius * contact_radius)
        mean_pressure = normal_force / (math.pi * contact_radius * contact_radius)
        contact_area_mm2 = math.pi * contact_radius * contact_radius

    safety_factor = allowable_p0 / p0 if p0 > 0 else math.inf
    pass_contact = p0 <= allowable_p0

    _curve_points_raw = int(float(options.get("curve_points", 41)))
    curve_points = max(11, min(201, _curve_points_raw))
    _force_scale_raw = float(options.get("curve_force_scale", 1.30))
    force_scale = max(1.05, min(2.0, _force_scale_raw))
    force_curve: list[float] = []
    pressure_curve: list[float] = []
    for i in range(curve_points):
        f_i = normal_force * force_scale * i / (curve_points - 1)
        f_i = max(f_i, 1e-6)
        force_curve.append(f_i)
        if mode == "line":
            q_i = f_i / length_mm
            b_i = math.sqrt((4.0 * q_i * r_eq) / (math.pi * e_eq))
            p_i = (2.0 * q_i) / (math.pi * b_i)
        else:
            a_i = ((3.0 * f_i * r_eq) / (4.0 * e_eq)) ** (1.0 / 3.0)
            p_i = (3.0 * f_i) / (2.0 * math.pi * a_i * a_i)
        pressure_curve.append(p_i)

    warnings: list[str] = []
    if mode == "line" and length_mm < 5.0:
        warnings.append("接触长度较短，建议核查边缘效应和三维修正。")
    if safety_factor < 1.2:
        warnings.append("接触应力安全系数偏低，建议提高材料或优化接触半径/载荷。")
    # HR-04：钳位后追加 warning，告知实际生效值
    if curve_points != _curve_points_raw:
        warnings.append(
            f"curve_points 已钳位至 {curve_points}（原输入 {_curve_points_raw}）"
        )
    if force_scale != _force_scale_raw:
        warnings.append(
            f"curve_force_scale 已钳位至 {force_scale:.4g}（原输入 {_force_scale_raw:.4g}）"
        )

    # HR-03：contact 字典中 length_mm 仅线接触写入
    contact_dict: Dict[str, Any] = {
        "semi_width_mm": semi_width,
        "contact_radius_mm": contact_radius,
        "p0_mpa": p0,
        "p_mean_mpa": mean_pressure,
        "normal_force_n": normal_force,
        "contact_area_mm2": contact_area_mm2,
    }
    if mode == "line":
        contact_dict["length_mm"] = length_mm

    return {
        "inputs_echo": data,
        "mode": mode,
        "derived": {
            "e_eq_mpa": e_eq,
            "r_eq_mm": r_eq,
            "inv_r1_per_mm": _radius_inverse(r1, "geometry.r1_mm"),
            "inv_r2_per_mm": _radius_inverse(r2, "geometry.r2_mm"),
        },
        "contact": contact_dict,
        "check": {
            "allowable_p0_mpa": allowable_p0,
            "safety_factor": safety_factor,
        },
        "checks": {
            "contact_stress_ok": pass_contact,
        },
        "curve": {
            "force_n": force_curve,
            "p0_mpa": pressure_curve,
            "force_design_n": normal_force,
            "p0_design_mpa": p0,
        },
        "overall_pass": pass_contact,
        "warnings": warnings,
        # HR-04：回显实际生效的 options 值，方便下游追溯
        "options": {
            "curve_points": curve_points,
            "curve_force_scale": force_scale,
        },
    }
