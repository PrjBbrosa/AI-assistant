"""Involute spline geometry derivation with explicit DIN 5480-style inputs."""

from __future__ import annotations


class GeometryError(ValueError):
    """Raised when spline geometry parameters are invalid."""


def derive_involute_geometry(
    *,
    module_mm: float,
    tooth_count: int,
    reference_diameter_mm: float | None = None,
    tip_diameter_shaft_mm: float | None = None,
    root_diameter_shaft_mm: float | None = None,
    tip_diameter_hub_mm: float | None = None,
    allow_approximation: bool = False,
    pressure_angle_deg: float = 30.0,
) -> dict:
    """Derive involute spline geometry.

    Preferred path: use explicit DIN 5480-style reference dimensions
    from a drawing, catalog, or standard table. Approximation from
    `module_mm` and `tooth_count` is still available, but it is marked
    explicitly as a precheck-only fallback.
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
    explicit_values = (
        reference_diameter_mm,
        tip_diameter_shaft_mm,
        root_diameter_shaft_mm,
        tip_diameter_hub_mm,
    )

    messages: list[str] = []
    if all(value is not None for value in explicit_values):
        d = float(reference_diameter_mm)
        d_a1 = float(tip_diameter_shaft_mm)
        d_f1 = float(root_diameter_shaft_mm)
        d_a2 = float(tip_diameter_hub_mm)
        for value, name in (
            (d, "reference_diameter_mm"),
            (d_a1, "tip_diameter_shaft_mm"),
            (d_f1, "root_diameter_shaft_mm"),
            (d_a2, "tip_diameter_hub_mm"),
        ):
            if value <= 0:
                raise GeometryError(f"{name} 必须 > 0，当前值 {value}")
        if not (d_f1 < d_a2 < d_a1 < d):
            raise GeometryError(
                "显式花键尺寸必须满足 root_diameter_shaft < "
                "tip_diameter_hub < tip_diameter_shaft < reference_diameter"
            )
        geometry_source = "explicit_reference_dimensions"
        approximation_used = False
    elif any(value is not None for value in explicit_values):
        raise GeometryError(
            "显式花键几何输入不完整；需要同时提供 "
            "reference_diameter_mm、tip_diameter_shaft_mm、"
            "root_diameter_shaft_mm、tip_diameter_hub_mm。"
        )
    elif allow_approximation:
        d = m * z                          # 近似参考直径
        d_a1 = m * (z + 1.0)              # 近似外花键齿顶圆
        d_f1 = m * (z - 1.25)             # 近似外花键齿根圆
        d_a2 = m * (z - 1.0)              # 近似内花键齿顶圆
        geometry_source = "approximation_from_module_and_tooth_count"
        approximation_used = True
        messages.append(
            "当前花键几何采用 module + tooth_count 的近似推导，"
            "仅适合简化预校核。"
        )
    else:
        raise GeometryError(
            "缺少显式 DIN 5480 参考尺寸：reference_diameter_mm。"
            "若仅做预估，请显式启用近似模式。"
        )

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
        "geometry_source": geometry_source,
        "approximation_used": approximation_used,
        "messages": messages,
    }
