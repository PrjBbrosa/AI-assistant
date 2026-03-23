"""Professional PDF report generator for DIN 7190 interference fit results.

Uses reportlab to produce a modern, visually designed A4 report with:
- Colored header bar, pass/fail badges, key metric cards
- Compact input summary tables grouped by category
- Pressure, capacity, safety, and stress sections
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
    _check_pills,
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
# Check labels
# ---------------------------------------------------------------------------
CHECK_LABELS = {
    "torque_ok": "扭矩能力校核",
    "axial_ok": "轴向力能力校核",
    "combined_ok": "联合作用校核",
    "gaping_ok": "张口缝校核",
    "fit_range_ok": "过盈覆盖需求校核",
    "shaft_stress_ok": "轴侧应力校核",
    "hub_stress_ok": "轮毂应力校核",
}


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
def build_interference_recommendations(result: Dict[str, Any]) -> list[str]:
    """Build recommendation strings from result dict."""
    checks = result.get("checks", {})
    recs: list[str] = []
    if not checks.get("torque_ok", True):
        recs.append(
            "扭矩能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
        )
    if not checks.get("axial_ok", True):
        recs.append(
            "轴向力能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
        )
    if not checks.get("combined_ok", True):
        recs.append(
            "联合作用校核不通过：扭矩和轴向力组合超限，需增大过盈量或减小载荷。"
        )
    if not checks.get("gaping_ok", True):
        recs.append(
            "张口缝校核不通过：最小面压不足以抵抗弯矩/径向力引起的张开趋势，"
            "需增大最小过盈量。"
        )
    if not checks.get("fit_range_ok", True):
        recs.append(
            "过盈覆盖需求校核不通过：最大过盈端面压超出材料许用范围，"
            "需缩小过盈公差带或提高材料强度。"
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
        recs.append("所有校核均通过，当前设计满足 DIN 7190 要求。")
    return recs


# ---------------------------------------------------------------------------
# Input summary helpers
# ---------------------------------------------------------------------------
def _build_input_rows(payload: dict, result: dict) -> list[tuple[str, str]]:
    """Build input summary rows from payload and result."""
    geo = payload.get("geometry", {})
    mat = payload.get("materials", {})
    fit = payload.get("fit", {})
    rough = payload.get("roughness", {})
    fric = payload.get("friction", {})
    loads = payload.get("loads", {})
    model = result.get("model", {})
    derived = result.get("derived", {})

    shaft_type_str = "空心轴" if model.get("shaft_type") == "hollow_shaft" else "实心轴"
    shaft_inner = derived.get("shaft_inner_d_mm", 0)

    rows = [
        ("轴类型", shaft_type_str),
        ("轴径 d", _fmt(geo.get("shaft_d_mm"), 2, "mm")),
        ("轮毂外径 D", _fmt(geo.get("hub_D_mm"), 2, "mm")),
        ("配合长度 L", _fmt(geo.get("fit_length_mm"), 2, "mm")),
    ]
    if shaft_inner:
        rows.append(("轴内径 d_i", _fmt(shaft_inner, 2, "mm")))

    rows.extend([
        ("轴 E / Rp0.2", f"{_fmt(mat.get('shaft_E_mpa'), 0, 'MPa')} / {_fmt(mat.get('shaft_Rp02_mpa'), 0, 'MPa')}"),
        ("轮毂 E / Rp0.2", f"{_fmt(mat.get('hub_E_mpa'), 0, 'MPa')} / {_fmt(mat.get('hub_Rp02_mpa'), 0, 'MPa')}"),
        ("过盈 min/max", f"{_fmt(fit.get('delta_min_um'), 1, 'um')} / {_fmt(fit.get('delta_max_um'), 1, 'um')}"),
        ("粗糙度 Rz 轴/毂", f"{_fmt(rough.get('shaft_rz_um'), 1, 'um')} / {_fmt(rough.get('hub_rz_um'), 1, 'um')}"),
        ("摩擦系数 纵/周", f"{_fmt(fric.get('mu_longitudinal'), 2)} / {_fmt(fric.get('mu_circumferential'), 2)}"),
        ("扭矩 T", _fmt(loads.get("torque_nm"), 1, "N*m")),
        ("轴向力 F_ax", _fmt(loads.get("axial_force_n"), 0, "N")),
        ("工况系数 K_A", _fmt(loads.get("application_factor_ka"), 2)),
    ])
    return rows


# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------
def generate_interference_report(
    path: Path,
    payload: dict,
    result: dict,
) -> None:
    """Generate a professional PDF report for DIN 7190 interference fit."""
    _register_fonts()
    styles = _build_styles()
    elems: list = []

    checks = result.get("checks", {})
    overall = result.get("overall_pass", False)
    pressure = result.get("pressure_mpa", {})
    capacity = result.get("capacity", {})
    assembly = result.get("assembly", {})
    stress = result.get("stress_mpa", {})
    safety = result.get("safety", {})
    required = result.get("required", {})
    roughness = result.get("roughness", {})
    add_p = result.get("additional_pressure_mpa", {})
    model = result.get("model", {})
    messages = result.get("messages", [])

    shaft_type_str = "空心轴" if model.get("shaft_type") == "hollow_shaft" else "实心轴"
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. Header bar
    elems.append(_header_bar(styles, "DIN 7190 过盈配合校核报告", date_str))
    elems.append(Spacer(1, 8))

    # 2. Verdict block
    subtitle = f"模型: 圆柱面过盈配合 ({shaft_type_str})"
    elems.append(_verdict_block(styles, overall, subtitle))
    elems.append(Spacer(1, 8))

    # 3. Metric cards
    metrics = [
        ("p_min (MPa)", _fmt(pressure.get("p_min"), 2)),
        ("p_max (MPa)", _fmt(pressure.get("p_max"), 2)),
        ("T_min (N*m)", _fmt(capacity.get("torque_min_nm"), 1)),
        ("S_combined", _fmt(safety.get("combined_sf"), 2)),
    ]
    elems.append(_metric_cards(styles, metrics))
    elems.append(Spacer(1, 8))

    # 4. Check pills
    elems.append(_check_pills(styles, checks, CHECK_LABELS, {}))
    elems.append(Spacer(1, 12))

    # 5. Input summary
    elems.append(_section_title(styles, "输入参数"))
    elems.append(_input_table(styles, _build_input_rows(payload, result)))
    elems.append(Spacer(1, 10))

    # 6. Pressure & roughness section
    elems.append(_section_title(styles, "面压与粗糙度"))
    p_rows = [
        ("面压 p_min / p_mean / p_max",
         f"{_fmt(pressure.get('p_min'), 2)} / {_fmt(pressure.get('p_mean'), 2)} / {_fmt(pressure.get('p_max'), 2)} MPa"),
        ("需求面压 p_required", _fmt(required.get("p_required_mpa"), 2, "MPa")),
        ("需求面压 p_required,total", _fmt(required.get("p_required_total_mpa"), 2, "MPa")),
        ("p_req,T / p_req,Ax / p_req,comb",
         f"{_fmt(required.get('p_required_torque_mpa'), 2)} / "
         f"{_fmt(required.get('p_required_axial_mpa'), 2)} / "
         f"{_fmt(required.get('p_required_combined_mpa'), 2)} MPa"),
        ("附加面压 p_gap", _fmt(add_p.get("p_gap"), 2, "MPa")),
        ("粗糙度损失 (Rz 沉陷)", _fmt(roughness.get("subsidence_um"), 2, "um")),
        ("有效过盈 min/mean/max",
         f"{_fmt(roughness.get('delta_effective_min_um'), 2)} / "
         f"{_fmt(roughness.get('delta_effective_mean_um'), 2)} / "
         f"{_fmt(roughness.get('delta_effective_max_um'), 2)} um"),
        ("需求过盈 (有效)", _fmt(required.get("delta_required_effective_um"), 2, "um")),
    ]
    elems.append(_kv_table(styles, p_rows, 0.45))
    elems.append(Spacer(1, 10))

    # 7. Capacity card
    cap_values = [
        f"扭矩容量 min/mean/max: {_fmt(capacity.get('torque_min_nm'), 1)} / "
        f"{_fmt(capacity.get('torque_mean_nm'), 1)} / "
        f"{_fmt(capacity.get('torque_max_nm'), 1)} N*m",
        f"轴向力容量 min/mean/max: {_fmt(capacity.get('axial_min_n'), 0)} / "
        f"{_fmt(capacity.get('axial_mean_n'), 0)} / "
        f"{_fmt(capacity.get('axial_max_n'), 0)} N",
        f"压入力 min/mean/max: {_fmt(assembly.get('press_force_min_n'), 0)} / "
        f"{_fmt(assembly.get('press_force_mean_n'), 0)} / "
        f"{_fmt(assembly.get('press_force_max_n'), 0)} N",
    ]
    elems.append(_section_title(styles, "传力能力与装配"))
    elems.append(KeepTogether([
        _rstep_card(styles, "传力能力", cap_values, passed=None,
                    note="基于最小/平均/最大有效过盈"),
        Spacer(1, 6),
    ]))

    # 8. Safety cards
    elems.append(_section_title(styles, "安全系数"))
    slip_min = safety.get("slip_safety_min", 0)
    slip_pass = slip_min >= 1.0 if isinstance(slip_min, (int, float)) else None
    slip_values = [
        f"扭矩安全系数: {_fmt(safety.get('torque_sf'), 2)}",
        f"轴向力安全系数: {_fmt(safety.get('axial_sf'), 2)}",
        f"联合安全系数: {_fmt(safety.get('combined_sf'), 2)}",
        f"联合利用度: {_fmt(safety.get('combined_usage'), 2)}",
        f"张口缝裕度: {_fmt(safety.get('gaping_margin_mpa'), 2, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "滑移安全", slip_values, passed=slip_pass,
                    note=f"最小滑移安全系数: {_fmt(slip_min, 2)}"),
        Spacer(1, 6),
    ]))

    stress_min = safety.get("stress_safety_min", 0)
    stress_pass = stress_min >= 1.0 if isinstance(stress_min, (int, float)) else None
    stress_sf_values = [
        f"轴侧安全系数: {_fmt(safety.get('shaft_sf'), 2)}",
        f"轮毂安全系数: {_fmt(safety.get('hub_sf'), 2)}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "应力安全", stress_sf_values, passed=stress_pass,
                    note=f"最小应力安全系数: {_fmt(stress_min, 2)}"),
        Spacer(1, 6),
    ]))

    # 9. Stress section
    elems.append(_section_title(styles, "等效应力"))
    stress_rows = [
        ("轴 VM min/mean/max",
         f"{_fmt(stress.get('shaft_vm_min'), 1)} / "
         f"{_fmt(stress.get('shaft_vm_mean'), 1)} / "
         f"{_fmt(stress.get('shaft_vm_max'), 1)} MPa"),
        ("轮毂 VM min/mean/max",
         f"{_fmt(stress.get('hub_vm_min'), 1)} / "
         f"{_fmt(stress.get('hub_vm_mean'), 1)} / "
         f"{_fmt(stress.get('hub_vm_max'), 1)} MPa"),
        ("轮毂环向应力 min/mean/max",
         f"{_fmt(stress.get('hub_hoop_inner_min'), 1)} / "
         f"{_fmt(stress.get('hub_hoop_inner_mean'), 1)} / "
         f"{_fmt(stress.get('hub_hoop_inner_max'), 1)} MPa"),
    ]
    elems.append(_kv_table(styles, stress_rows, 0.4))
    elems.append(Spacer(1, 10))

    # 10. Warnings
    if messages:
        elems.append(_section_title(styles, "警告信息"))
        for msg in messages:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 11. Recommendations
    recs = build_interference_recommendations(result)
    elems.append(_section_title(styles, "建议"))
    for rec in recs:
        elems.append(Paragraph(f"- {rec}", styles["body"]))

    build_pdf(path, elems, "DIN 7190 过盈配合校核")
