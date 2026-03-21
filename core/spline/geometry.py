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
