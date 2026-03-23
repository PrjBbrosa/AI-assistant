"""Professional PDF report generator for spline interference-fit results.

Uses reportlab to produce a modern, visually designed A4 report with:
- Colored header bar, pass/fail badges, key metric cards
- Scenario A (flank pressure) and optional Scenario B (cylindrical interference)
- Conditional recommendations based on check results
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict

from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    Spacer,
)

from app.ui.report_pdf_common import (
    _build_styles,
    _fmt,
    _header_bar,
    _input_table,
    _kv_table,
    _metric_cards,
    _pass_text,
    _register_fonts,
    _rstep_card,
    _section_title,
    _verdict_block,
    build_pdf,
)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
def build_spline_recommendations(result: Dict[str, Any]) -> list[str]:
    """Build recommendation strings from spline result dict."""
    recs: list[str] = []

    # Scenario A checks
    a = result.get("scenario_a", {})
    if not a.get("flank_ok", True):
        recs.append(
            "齿面承压安全系数不足：可增大啮合长度、增大齿数或降低设计扭矩。"
        )

    # Scenario B checks (only if combined mode)
    b = result.get("scenario_b")
    if b is not None:
        checks = b.get("checks", {})
        if not checks.get("torque_ok", True):
            recs.append(
                "光滑段扭矩能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
            )
        if not checks.get("axial_ok", True):
            recs.append(
                "光滑段轴向力能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
            )
        if not checks.get("combined_ok", True):
            recs.append(
                "光滑段联合作用校核不通过：扭矩和轴向力组合超限，需增大过盈量或减小载荷。"
            )
        if not checks.get("shaft_stress_ok", True):
            recs.append(
                "轴侧应力安全系数不足：可更换更高强度的轴材料或减小过盈量。"
            )
        if not checks.get("hub_stress_ok", True):
            recs.append(
                "轮毂应力安全系数不足：可增大轮毂外径、更换更高强度材料或减小过盈量。"
            )

    if not recs:
        recs.append("所有校核均通过，当前设计满足要求。")
    return recs


# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------
def generate_spline_report(
    path: Path,
    payload: dict,
    result: dict,
) -> None:
    """Generate a professional PDF report for spline interference fit."""
    _register_fonts()
    styles = _build_styles()
    elems: list = []

    overall = result.get("overall_pass", False)
    mode = result.get("mode", "spline_only")
    loads = result.get("loads", {})
    a = result.get("scenario_a", {})
    b = result.get("scenario_b")
    messages = result.get("messages", [])
    verdict_level = result.get("overall_verdict_level", "")

    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Mode description
    if mode == "combined":
        mode_desc = "联合模式 (花键齿面 + 光滑段过盈)"
    else:
        mode_desc = "仅花键齿面承压"
    subtitle = f"{mode_desc} | {verdict_level}"

    # 1. Header bar
    elems.append(_header_bar(styles, "花键连接校核报告", date_str))
    elems.append(Spacer(1, 8))

    # 2. Verdict block
    elems.append(_verdict_block(styles, overall, subtitle))
    elems.append(Spacer(1, 8))

    # 3. Metric cards
    metrics = [
        ("齿面压力 (MPa)", _fmt(a.get("flank_pressure_mpa"), 2)),
        ("齿面安全系数", _fmt(a.get("flank_safety"), 2)),
    ]
    if b is not None:
        p_min = b.get("pressure_mpa", {}).get("p_min")
        metrics.append(("p_min (MPa)", _fmt(p_min, 2)))
    metrics.append(("设计扭矩 (N*m)", _fmt(loads.get("torque_design_nm"), 1)))
    elems.append(_metric_cards(styles, metrics))
    elems.append(Spacer(1, 10))

    # 4. Scenario A section
    elems.append(_section_title(styles, "Scenario A \u2014 花键齿面承压"))

    # Scenario A input table
    spline_input = payload.get("spline", {})
    a_input_rows = [
        ("模数 m", _fmt(spline_input.get("module_mm"), 2, "mm")),
        ("齿数 z", _fmt(spline_input.get("tooth_count"), 0)),
        ("啮合长度 L", _fmt(a.get("engagement_length_mm"), 2, "mm")),
        ("载荷分布系数 K_alpha", _fmt(a.get("k_alpha"), 2)),
        ("许用齿面压力 p_zul", _fmt(a.get("p_allowable_mpa"), 1, "MPa")),
        ("工况系数 K_A", _fmt(loads.get("application_factor_ka"), 2)),
        ("名义扭矩 T", _fmt(loads.get("torque_required_nm"), 1, "N*m")),
        ("设计扭矩 T_d", _fmt(loads.get("torque_design_nm"), 1, "N*m")),
    ]
    elems.append(_input_table(styles, a_input_rows))
    elems.append(Spacer(1, 6))

    # Scenario A geometry + result card
    geo = a.get("geometry", {})
    geo_mode = a.get("geometry_mode", "")
    geo_mode_label = "近似推导" if geo_mode == "approximate" else "公开/图纸尺寸"
    a_values = [
        f"几何模式: {geo_mode_label}",
        f"参考直径 d_B = {_fmt(geo.get('reference_diameter_mm'), 2, 'mm')}",
        f"有效齿高 h_w = {_fmt(geo.get('effective_tooth_height_mm'), 2, 'mm')}",
        f"平均直径 d_m = {_fmt(geo.get('mean_diameter_mm'), 2, 'mm')}",
        f"齿面压力 p = {_fmt(a.get('flank_pressure_mpa'), 2, 'MPa')} (许用 {_fmt(a.get('p_allowable_mpa'), 0, 'MPa')})",
        f"安全系数 S = {_fmt(a.get('flank_safety'), 2)} (最小 {_fmt(a.get('flank_safety_min'), 2)})",
        f"扭矩容量 T_cap = {_fmt(a.get('torque_capacity_nm'), 1, 'N*m')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "齿面承压校核", a_values, passed=a.get("flank_ok")),
        Spacer(1, 6),
    ]))

    # Scenario A messages
    a_msgs = a.get("messages", [])
    if a_msgs:
        for msg in a_msgs:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 4))

    # Model assumptions and not-covered checks
    assumptions = a.get("model_assumptions", [])
    not_covered = a.get("not_covered_checks", [])
    notes = []
    if assumptions:
        notes.append("模型假设: " + ", ".join(assumptions))
    if not_covered:
        notes.append("未覆盖校核项: " + ", ".join(not_covered))
    if notes:
        for note in notes:
            elems.append(Paragraph(note, styles["muted"]))
        elems.append(Spacer(1, 8))

    # 5. Scenario B section (only if combined)
    if b is not None:
        elems.append(_section_title(styles, "Scenario B \u2014 光滑段圆柱过盈"))

        # Scenario B input table
        b_input_rows = [
            ("名义配合长度", _fmt(b.get("nominal_fit_length_mm"), 2, "mm")),
            ("退刀槽宽度", _fmt(b.get("relief_groove_width_mm"), 2, "mm")),
            ("有效配合长度", _fmt(b.get("effective_fit_length_mm"), 2, "mm")),
        ]
        elems.append(_input_table(styles, b_input_rows))
        elems.append(Spacer(1, 6))

        # Pressure kv_table
        bp = b.get("pressure_mpa", {})
        p_rows = [
            ("面压 p_min / p_mean / p_max",
             f"{_fmt(bp.get('p_min'), 2)} / {_fmt(bp.get('p_mean'), 2)} / {_fmt(bp.get('p_max'), 2)} MPa"),
            ("需求面压 p_required", _fmt(bp.get("p_required"), 2, "MPa")),
            ("需求面压 p_required,total", _fmt(bp.get("p_required_total"), 2, "MPa")),
        ]
        elems.append(_kv_table(styles, p_rows, 0.45))
        elems.append(Spacer(1, 6))

        # Capacity card
        cap = b.get("capacity", {})
        asm = b.get("assembly", {})
        cap_values = [
            f"扭矩容量 min/mean/max: {_fmt(cap.get('torque_min_nm'), 1)} / "
            f"{_fmt(cap.get('torque_mean_nm'), 1)} / "
            f"{_fmt(cap.get('torque_max_nm'), 1)} N*m",
            f"轴向力容量 min/mean/max: {_fmt(cap.get('axial_min_n'), 0)} / "
            f"{_fmt(cap.get('axial_mean_n'), 0)} / "
            f"{_fmt(cap.get('axial_max_n'), 0)} N",
            f"压入力 min/mean/max: {_fmt(asm.get('press_force_min_n'), 0)} / "
            f"{_fmt(asm.get('press_force_mean_n'), 0)} / "
            f"{_fmt(asm.get('press_force_max_n'), 0)} N",
        ]
        b_checks = b.get("checks", {})
        cap_pass = b_checks.get("torque_ok", True) and b_checks.get("axial_ok", True)
        elems.append(KeepTogether([
            _rstep_card(styles, "传力能力", cap_values, passed=cap_pass),
            Spacer(1, 6),
        ]))

        # Safety card
        safety = b.get("safety", {})
        slip_min = safety.get("slip_safety_min", 0)
        stress_min = safety.get("stress_safety_min", 0)
        safety_values = [
            f"扭矩安全系数: {_fmt(safety.get('torque_sf'), 2)}",
            f"轴向力安全系数: {_fmt(safety.get('axial_sf'), 2)}",
            f"联合安全系数: {_fmt(safety.get('combined_sf'), 2)}",
            f"轴侧安全系数: {_fmt(safety.get('shaft_sf'), 2)}",
            f"轮毂安全系数: {_fmt(safety.get('hub_sf'), 2)}",
        ]
        safety_pass = b.get("overall_pass", False)
        elems.append(KeepTogether([
            _rstep_card(
                styles, "安全系数", safety_values, passed=safety_pass,
                note=f"最小滑移安全系数: {_fmt(slip_min, 2)} | 最小应力安全系数: {_fmt(stress_min, 2)}",
            ),
            Spacer(1, 6),
        ]))

        # Scenario B messages
        b_msgs = b.get("messages", [])
        if b_msgs:
            for msg in b_msgs:
                elems.append(Paragraph(f"- {msg}", styles["body"]))
            elems.append(Spacer(1, 4))

    # 6. Warnings
    if messages:
        elems.append(_section_title(styles, "警告信息"))
        for msg in messages:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 7. Recommendations
    recs = build_spline_recommendations(result)
    elems.append(_section_title(styles, "建议"))
    for rec in recs:
        elems.append(Paragraph(f"- {rec}", styles["body"]))

    build_pdf(path, elems, "花键连接校核")
