"""Professional PDF report generator for DIN 3975 worm gear results.

Uses reportlab to produce a modern, visually designed A4 report with:
- Colored header bar, pass/fail badges, key metric cards
- Geometry tables for worm and wheel dimensions
- Performance summary
- Optional load capacity section with check pills and stress cards
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
    C_PRIMARY,
    _build_styles,
    _check_pills,
    _fmt,
    _header_bar,
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
# Check labels (load capacity only)
# ---------------------------------------------------------------------------
LC_CHECK_LABELS = {
    "geometry_consistent": "几何一致性",
    "contact_ok": "齿面接触应力",
    "root_ok": "齿根弯曲应力",
}


# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------
def generate_worm_report(
    path: Path,
    payload: dict,
    result: dict,
) -> None:
    """Generate a professional PDF report for worm gear design."""
    _register_fonts()
    styles = _build_styles()
    elems: list = []

    geometry = result.get("geometry", {})
    performance = result.get("performance", {})
    lc = result.get("load_capacity", {})
    lc_enabled = lc.get("enabled", False)
    checks = lc.get("checks", {})

    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Determine overall pass/fail
    if lc_enabled and checks:
        overall = all(checks.values())
    else:
        overall = None

    # 1. Header bar
    elems.append(_header_bar(styles, "DIN 3975 蜗杆副设计报告", date_str))
    elems.append(Spacer(1, 8))

    # 2. Verdict block
    if overall is not None:
        subtitle = lc.get("status", "")
        elems.append(_verdict_block(styles, overall, subtitle))
    else:
        # Geometry-only mode: show primary accent, no pass/fail
        subtitle = "几何与性能设计"
        elems.append(_rstep_card(styles, subtitle, [], passed=None))
    elems.append(Spacer(1, 8))

    # 3. Metric cards
    metrics = [
        ("传动比 i", _fmt(geometry.get("ratio"), 3)),
        ("中心距 a (mm)", _fmt(geometry.get("center_distance_mm"), 2)),
        ("效率 eta", _fmt(performance.get("efficiency_estimate"), 3)),
        ("输出扭矩 T2 (N*m)", _fmt(performance.get("output_torque_nm"), 1)),
    ]
    elems.append(_metric_cards(styles, metrics))
    elems.append(Spacer(1, 10))

    # 4. Geometry section
    elems.append(_section_title(styles, "几何尺寸"))

    # 4a. Worm dimensions
    wd = geometry.get("worm_dimensions", {})
    worm_rows = [
        ("分度圆直径 d1", _fmt(wd.get("pitch_diameter_mm"), 3, "mm")),
        ("齿顶圆直径 da1", _fmt(wd.get("tip_diameter_mm"), 3, "mm")),
        ("齿根圆直径 df1", _fmt(wd.get("root_diameter_mm"), 3, "mm")),
        ("齿宽 b1", _fmt(wd.get("face_width_mm"), 3, "mm")),
        ("导程 pz", _fmt(wd.get("lead_mm"), 3, "mm")),
        ("轴向齿距 px", _fmt(wd.get("axial_pitch_mm"), 3, "mm")),
    ]
    elems.append(Paragraph("蜗杆尺寸", styles["body_bold"]))
    elems.append(Spacer(1, 2))
    elems.append(_kv_table(styles, worm_rows, 0.45))
    elems.append(Spacer(1, 6))

    # 4b. Wheel dimensions
    whd = geometry.get("wheel_dimensions", {})
    wheel_rows = [
        ("分度圆直径 d2", _fmt(whd.get("pitch_diameter_mm"), 3, "mm")),
        ("齿顶圆直径 da2", _fmt(whd.get("tip_diameter_mm"), 3, "mm")),
        ("齿根圆直径 df2", _fmt(whd.get("root_diameter_mm"), 3, "mm")),
        ("齿宽 b2", _fmt(whd.get("face_width_mm"), 3, "mm")),
        ("齿高 h", _fmt(whd.get("tooth_height_mm"), 3, "mm")),
    ]
    elems.append(Paragraph("蜗轮尺寸", styles["body_bold"]))
    elems.append(Spacer(1, 2))
    elems.append(_kv_table(styles, wheel_rows, 0.45))
    elems.append(Spacer(1, 10))

    # 5. Performance section
    elems.append(_section_title(styles, "性能参数"))
    perf_rows = [
        ("输入功率 P1", _fmt(performance.get("input_power_kw"), 4, "kW")),
        ("输出功率 P2", _fmt(performance.get("output_power_kw"), 4, "kW")),
        ("效率 eta", _fmt(performance.get("efficiency_estimate"), 4)),
        ("摩擦系数 mu", _fmt(performance.get("friction_mu"), 4)),
        ("蜗杆分度圆线速度 v1", _fmt(performance.get("worm_pitch_line_speed_mps"), 3, "m/s")),
        ("热功率容量 Pth", _fmt(performance.get("thermal_capacity_kw"), 4, "kW")),
    ]
    elems.append(_kv_table(styles, perf_rows, 0.45))
    elems.append(Spacer(1, 10))

    # 6. Load capacity section (only if enabled)
    if lc_enabled:
        elems.append(_section_title(styles, "负载能力校核"))

        # Check pills
        if checks:
            elems.append(_check_pills(styles, checks, LC_CHECK_LABELS, {}))
            elems.append(Spacer(1, 8))

        # Forces card
        forces = lc.get("forces", {})
        if forces:
            force_values = [
                f"蜗轮切向力 Ft2 = {_fmt(forces.get('tangential_force_wheel_n'), 1, 'N')}",
                f"蜗轮轴向力 Fa2 = {_fmt(forces.get('axial_force_wheel_n'), 1, 'N')}",
                f"径向力 Fr = {_fmt(forces.get('radial_force_wheel_n'), 1, 'N')}",
                f"法向力 Fn = {_fmt(forces.get('normal_force_n'), 1, 'N')}",
            ]
            elems.append(KeepTogether([
                _rstep_card(styles, "齿面力", force_values, passed=None),
                Spacer(1, 6),
            ]))

        # Contact stress card
        contact = lc.get("contact", {})
        if contact:
            contact_values = [
                f"齿面接触应力 sigma_Hm = {_fmt(contact.get('sigma_hm_nominal_mpa'), 1, 'MPa')}",
                f"许用接触应力 sigma_HP = {_fmt(contact.get('allowable_contact_stress_mpa'), 1, 'MPa')}",
                f"名义安全系数 SH = {_fmt(contact.get('safety_factor_nominal'), 2)}",
                f"峰值安全系数 SH,peak = {_fmt(contact.get('safety_factor_peak'), 2)}",
            ]
            elems.append(KeepTogether([
                _rstep_card(styles, "齿面接触应力校核", contact_values,
                            passed=checks.get("contact_ok")),
                Spacer(1, 6),
            ]))

        # Root stress card
        root = lc.get("root", {})
        if root:
            root_values = [
                f"齿根弯曲应力 sigma_F = {_fmt(root.get('sigma_f_nominal_mpa'), 1, 'MPa')}",
                f"许用齿根应力 sigma_FP = {_fmt(root.get('allowable_root_stress_mpa'), 1, 'MPa')}",
                f"名义安全系数 SF = {_fmt(root.get('safety_factor_nominal'), 2)}",
                f"峰值安全系数 SF,peak = {_fmt(root.get('safety_factor_peak'), 2)}",
            ]
            elems.append(KeepTogether([
                _rstep_card(styles, "齿根弯曲应力校核", root_values,
                            passed=checks.get("root_ok")),
                Spacer(1, 6),
            ]))

        # Factors table
        factors = lc.get("factors", {})
        if factors:
            factor_rows = [
                ("工况系数 KA", _fmt(factors.get("application_factor"), 2)),
                ("动载系数 KV", _fmt(factors.get("dynamic_factor_kv"), 2)),
                ("齿向载荷分布系数 KHalpha", _fmt(factors.get("transverse_load_factor_kha"), 2)),
                ("齿面载荷分布系数 KHbeta", _fmt(factors.get("face_load_factor_khb"), 2)),
            ]
            elems.append(_kv_table(styles, factor_rows, 0.5))
            elems.append(Spacer(1, 6))

        # Torque ripple table
        ripple = lc.get("torque_ripple", {})
        if ripple and ripple.get("percent") is not None:
            ripple_rows = [
                ("扭矩波动", _fmt(ripple.get("percent"), 1, "%")),
                ("名义输出扭矩 T2,nom", _fmt(ripple.get("output_torque_nominal_nm"), 1, "N*m")),
                ("峰值输出扭矩 T2,peak", _fmt(ripple.get("output_torque_peak_nm"), 1, "N*m")),
            ]
            elems.append(_kv_table(styles, ripple_rows, 0.5))
            elems.append(Spacer(1, 6))

    # 7. Warnings
    all_warnings = []
    all_warnings.extend(lc.get("warnings", []))
    all_warnings.extend(geometry.get("consistency", {}).get("warnings", []))
    if all_warnings:
        elems.append(_section_title(styles, "警告信息"))
        for msg in all_warnings:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 8. Assumptions
    assumptions = lc.get("assumptions", [])
    if lc_enabled and assumptions:
        elems.append(_section_title(styles, "模型假设"))
        for a in assumptions:
            elems.append(Paragraph(a, styles["muted"]))
        elems.append(Spacer(1, 4))

    build_pdf(path, elems, "DIN 3975 蜗杆副设计")
