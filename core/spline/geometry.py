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
        # Consistency check: if module and tooth_count are provided,
        # verify that the explicit reference_diameter is close to m * z.
        d_theoretical = m * z
        if d_theoretical > 0:
            relative_deviation = abs(d - d_theoretical) / d_theoretical
            if relative_deviation > 0.05:
                messages.append(
                    f"显式参考直径 d={d:.2f} mm 与 m*z={d_theoretical:.2f} mm "
                    f"偏差 {relative_deviation * 100:.1f}%，超过 5% 阈值，"
                    "请确认模数和齿数是否与图纸一致。"
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
        # DIN 5480-2:2015 保守近似：不同模数/齿数条目下 catalog 中 h_w/m
        # 最小值 ≈ 0.5（W 25x2.5x8 / W 20x2x8 等小齿数大模数规格）。
        # 取 h_w = 0.5·m 作保守下限，保证"近似模式算出的 p_flank 不低于真实值"，
        # 避免 m≥1.75 时高估齿高、低估齿面压力而给出假 PASS。
        #   d_a1 = d - 0.5m（外花键齿顶）
        #   d_a2 = d - 1.5m（内花键齿顶）
        #   d_f1 = d - 2.0m（外花键齿根）
        # 不同 catalog 规格实际 h_w/m 在 0.5~1.08 之间，近似偏差方向始终保守。
        d = m * z
        d_a1 = d - 0.5 * m
        d_a2 = d - 1.5 * m
        d_f1 = d - 2.0 * m
        geometry_source = "approximation_from_module_and_tooth_count"
        approximation_used = True
        messages.append(
            "近似模式使用 DIN 5480-2 catalog 最小 h_w/m=0.5 作保守下限，"
            "实际几何 h_w 在不同模数下可能偏大 5%~110%。"
            "重要设计请切换到公开/图纸尺寸模式并录入实测值。"
        )
    else:
        raise GeometryError(
            "缺少显式 DIN 5480 参考尺寸：reference_diameter_mm。"
            "若仅做预估，请显式启用近似模式。"
        )

    h_w = (d_a1 - d_a2) / 2.0         # 有效齿高（单侧）
    d_m = (d_a1 + d_a2) / 2.0         # 平均直径（接触区中心）

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
