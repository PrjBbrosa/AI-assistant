"""Professional PDF report generator for VDI 2230 bolt check results.

Uses reportlab to produce a modern, visually designed A4 report with:
- Colored header bar, pass/fail badges, key metric cards
- Compact input summary tables grouped by category
- R-step calculation chain with colored accent bars
- Conditional extended checks (thermal, fatigue) and recommendations
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
# Recommendations (standalone, no UI dependency)
# ---------------------------------------------------------------------------
def build_bolt_recommendations(result: Dict[str, Any]) -> list[str]:
    """Build recommendation strings from result dict."""
    checks = result.get("checks", {})
    recs: list[str] = []
    if not checks.get("residual_clamp_ok", True):
        recs.append("\u6b8b\u4f59\u5939\u7d27\u529b\u4e0d\u8db3\uff1a\u53ef\u52a0\u5927\u9884\u7d27\u529b\u3001\u6362\u66f4\u5927\u87ba\u6813\u6216\u964d\u4f4e\u5916\u8f7d\u3002")
    if not checks.get("assembly_von_mises_ok", True):
        recs.append("\u88c5\u914d\u5e94\u529b\u8fc7\u9ad8\uff1a\u53ef\u964d\u4f4e\u5229\u7528\u7cfb\u6570\u3001\u6362\u66f4\u9ad8\u7b49\u7ea7\u87ba\u6813\u6216\u51cf\u5c0f\u6469\u64e6\u3002")
    if not checks.get("operating_axial_ok", True):
        recs.append("\u670d\u5f79\u5e94\u529b\u8fc7\u9ad8\uff1a\u53ef\u6362\u66f4\u5927\u87ba\u6813\u3001\u964d\u4f4e\u5916\u8f7d\u6216\u63d0\u9ad8\u87ba\u6813\u7b49\u7ea7\u3002")
    if not checks.get("thermal_loss_ok", True):
        recs.append("\u70ed\u635f\u5931\u504f\u5927\uff1a\u53ef\u8865\u507f\u9884\u7d27\u529b\u3001\u4f18\u5316\u6750\u6599\u70ed\u5339\u914d\u6216\u964d\u4f4e\u6e29\u5dee\u3002")
    if not checks.get("fatigue_ok", True):
        recs.append("\u75b2\u52b3\u4e0d\u901a\u8fc7\uff1a\u53ef\u964d\u4f4e\u5e94\u529b\u5e45\u3001\u63d0\u9ad8\u87ba\u6813\u7b49\u7ea7\u3001\u4f18\u5316\u8f7d\u8377\u8c31\u6216\u589e\u5927\u89c4\u683c\u3002")
    if not checks.get("bearing_pressure_ok", True):
        recs.append("\u652f\u627f\u9762\u538b\u5f3a\u8d85\u9650\uff1a\u53ef\u52a0\u5927\u57ab\u5708\u3001\u589e\u5927\u87ba\u6813\u89c4\u683c\u6216\u9009\u7528\u66f4\u786c\u7684\u88ab\u5939\u4ef6\u6750\u6599\u3002")
    strip = result.get("thread_strip", {})
    if not checks.get("thread_strip_ok", True):
        side = strip.get("critical_side", "")
        if side == "nut":
            recs.append("\u87ba\u7eb9\u8131\u6263\u4e0d\u901a\u8fc7\uff08\u58f3\u4f53\u4fa7\uff09\uff1a\u53ef\u52a0\u6df1\u65cb\u5408\u6df1\u5ea6\u3001\u6362\u66f4\u9ad8\u5f3a\u5ea6\u58f3\u4f53\u6750\u6599\u3002")
        else:
            recs.append("\u87ba\u7eb9\u8131\u6263\u4e0d\u901a\u8fc7\uff08\u87ba\u6813\u4fa7\uff09\uff1a\u53ef\u52a0\u6df1\u65cb\u5408\u6df1\u5ea6\u6216\u63d0\u9ad8\u87ba\u6813\u5f3a\u5ea6\u7b49\u7ea7\u3002")
    if not recs:
        recs.append("\u5f53\u524d\u5de5\u51b5\u6ee1\u8db3\u5168\u90e8\u6821\u6838\u3002\u5efa\u8bae\u4fdd\u7559 10% \u4ee5\u4e0a\u5de5\u7a0b\u88d5\u91cf\u3002")
    return recs


# ---------------------------------------------------------------------------
# Check labels (consistent with UI)
# ---------------------------------------------------------------------------
CHECK_LABELS = {
    "residual_clamp_ok": "\u6b8b\u4f59\u5939\u7d27\u529b R3",
    "assembly_von_mises_ok": "\u88c5\u914d\u5e94\u529b R4",
    "operating_axial_ok": "\u670d\u5f79\u5e94\u529b R5",
    "thermal_loss_ok": "\u6e29\u5ea6\u5f71\u54cd",
    "fatigue_ok": "\u75b2\u52b3 R6",
    "bearing_pressure_ok": "\u652f\u627f\u9762 R7",
    "thread_strip_ok": "\u8131\u6263 R8",
    "additional_load_ok": "\u9644\u52a0\u8f7d\u8377(\u53c2\u8003)",
}

# ---------------------------------------------------------------------------
# Tightening method translation
# ---------------------------------------------------------------------------
_METHOD_CN = {
    "torque": "\u626d\u77e9\u6cd5",
    "angle": "\u8f6c\u89d2\u6cd5",
    "hydraulic": "\u6db2\u538b\u62c9\u4f38\u6cd5",
    "thermal": "\u70ed\u88c5\u6cd5",
}

_JOINT_CN = {
    "tapped": "\u87ba\u7eb9\u5b54\u8fde\u63a5",
    "through": "\u901a\u5b54\u8fde\u63a5",
}

_LEVEL_CN = {
    "basic": "\u5e38\u89c4 (R3/R4/R5)",
    "thermal": "\u542b\u6e29\u5ea6\u5f71\u54cd",
    "fatigue": "\u542b\u75b2\u52b3\u6821\u6838",
}

_MODE_CN = {
    "check": "\u6821\u6838\u6a21\u5f0f",
    "design": "\u8bbe\u8ba1\u6a21\u5f0f",
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def generate_bolt_report(
    path: Path,
    payload: Dict[str, Any],
    result: Dict[str, Any],
) -> None:
    """Generate a professional PDF report for VDI 2230 bolt check."""
    _register_fonts()
    styles = _build_styles()

    elements: list = []

    # -- Header --
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(_header_bar(styles, "VDI 2230 \u87ba\u6813\u8fde\u63a5\u6821\u6838\u62a5\u544a", date_str))
    elements.append(Spacer(1, 8))

    # -- Overall verdict --
    overall = result.get("overall_pass", False)
    joint_type = result.get("joint_type", "tapped")
    check_level = result.get("check_level", "basic")
    method = result.get("tightening_method", "torque")
    calc_mode = result.get("calculation_mode", "check")

    subtitle_parts = [
        _MODE_CN.get(calc_mode, calc_mode),
        _JOINT_CN.get(joint_type, joint_type),
        _LEVEL_CN.get(check_level, check_level),
        _METHOD_CN.get(method, method),
    ]
    elements.append(_verdict_block(styles, overall, " | ".join(subtitle_parts)))
    elements.append(Spacer(1, 8))

    # -- Key metrics --
    inter = result.get("intermediate", {})
    torque = result.get("torque", {})
    forces = result.get("forces", {})

    metrics = [
        ("FM,min", _fmt(inter.get("FMmin_N"), 0, "N")),
        ("MA", f"{_fmt(torque.get('MA_min_Nm'), 1)} ~ {_fmt(torque.get('MA_max_Nm'), 1)} N-m"),
        ("FK,residual", _fmt(forces.get("F_K_residual_N"), 0, "N")),
    ]
    elements.append(_metric_cards(styles, metrics))
    elements.append(Spacer(1, 6))

    # -- Check pills --
    checks = result.get("checks", {})
    refs = result.get("references", {})
    elements.append(_check_pills(styles, checks, CHECK_LABELS, refs))
    elements.append(Spacer(1, 10))

    # -- Input summary --
    elements.append(_section_title(styles, "\u8f93\u5165\u53c2\u6570"))
    fastener = payload.get("fastener", {})
    loads = payload.get("loads", {})
    assembly = payload.get("assembly", {})
    clamped = payload.get("clamped", {})
    stiffness = payload.get("stiffness", {})
    geom = result.get("derived_geometry_mm", {})

    input_rows = [
        ("\u7d27\u56fa\u4ef6", (
            f"M{fastener.get('d', '?')}x{fastener.get('p', '?')}"
            f"  Rp0.2 = {fastener.get('Rp02', '?')} MPa"
            f"  E = {fastener.get('E_bolt', '?')} MPa"
            f"  As = {_fmt(geom.get('As'), 2)} mm2"
            f"  d2 = {_fmt(geom.get('d2'), 2)} mm"
        )),
        ("\u5916\u90e8\u8f7d\u8377", (
            f"FA,max = {loads.get('FA_max', '?')} N"
            f"  FQ,max = {loads.get('FQ_max', 0)} N"
            + (f"  FK,seal = {loads.get('FK_seal', 0)} N" if loads.get("FK_seal") else "")
        )),
        ("\u88c5\u914d\u6761\u4ef6", (
            f"{_METHOD_CN.get(method, method)}"
            f"  aA = {assembly.get('alpha_A', '?')}"
            f"  v = {assembly.get('utilization', '?')}"
            f"  muG = {assembly.get('mu_thread', '?')}"
            f"  muK = {assembly.get('mu_bearing', '?')}"
        )),
        ("\u88ab\u5939\u4ef6", (
            f"\u5c42\u6570: {clamped.get('part_count', 1)}"
            f"  lK = {clamped.get('total_thickness', '?')} mm"
            f"  \u6a21\u578b: {clamped.get('basic_solid', 'cylinder')}"
            f"  DA = {clamped.get('D_A', '?')} mm"
        )),
    ]

    stiff_model = result.get("stiffness_model", {})
    if stiff_model.get("auto_modeled"):
        stiff_text = (
            f"\u81ea\u52a8\u8ba1\u7b97  ds = {_fmt(stiff_model.get('delta_s_mm_per_n'), 2, 'e')} mm/N"
            f"  dp = {_fmt(stiff_model.get('delta_p_mm_per_n'), 2, 'e')} mm/N"
        )
    else:
        ds = stiffness.get("bolt_compliance") or stiffness.get("bolt_stiffness", "?")
        dp = stiffness.get("clamped_compliance") or stiffness.get("clamped_stiffness", "?")
        stiff_text = f"\u624b\u52a8\u8f93\u5165  ds = {ds}  dp = {dp}"
    input_rows.append(("\u67d4\u5ea6/\u521a\u5ea6", stiff_text))

    elements.append(_input_table(styles, input_rows))
    elements.append(Spacer(1, 10))

    # -- Stiffness & force ratio --
    elements.append(_section_title(styles, "\u67d4\u5ea6\u4e0e\u529b\u6bd4"))
    phi_rows = [
        ("\u87ba\u6813\u67d4\u5ea6 ds", _fmt(stiff_model.get("delta_s_mm_per_n"), 4, "mm/N")),
        ("\u88ab\u5939\u4ef6\u67d4\u5ea6 dp", _fmt(stiff_model.get("delta_p_mm_per_n"), 4, "mm/N")),
        ("\u529b\u6bd4\u7cfb\u6570 phi", _fmt(inter.get("phi"), 4)),
        ("\u4fee\u6b63\u529b\u6bd4 phi_n", _fmt(inter.get("phi_n"), 4)),
        ("\u8f7d\u8377\u5bfc\u5165\u7cfb\u6570 n", _fmt(stiff_model.get("n"), 2)),
    ]
    elements.append(_kv_table(styles, phi_rows, col_ratio=0.4))
    elements.append(Spacer(1, 8))

    # -- R1 Preload --
    thermal = result.get("thermal", {})
    embed = result.get("embed_estimation", {})
    fz_val = embed.get("embed_auto_value_N", 0) if embed.get("embed_auto_estimated") else payload.get("loads", {}).get("FZ", 0)

    r1_values = [
        f"FK,req = {_fmt(inter.get('F_K_required_N'), 1)} N"
        f"    FZ = {_fmt(fz_val, 1)} N"
        f"    F_thermal = {_fmt(thermal.get('thermal_loss_effective_N'), 1)} N",
        f"FM,min = {_fmt(inter.get('FMmin_N'), 1)} N"
        f"    FM,max = {_fmt(inter.get('FMmax_N'), 1)} N",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R1 \u2014 \u9884\u7d27\u529b\u786e\u5b9a", r1_values),
        Spacer(1, 5),
    ]))

    # -- R2 Tightening torque --
    r2_values = [
        f"MA,min = {_fmt(torque.get('MA_min_Nm'), 2)} N-m"
        f"    MA,max = {_fmt(torque.get('MA_max_Nm'), 2)} N-m",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R2 \u2014 \u62e7\u7d27\u626d\u77e9", r2_values),
        Spacer(1, 5),
    ]))

    # -- R3 Residual clamping --
    r3_pass = checks.get("residual_clamp_ok")
    r3_values = [
        f"FK,res = {_fmt(forces.get('F_K_residual_N'), 1)} N"
        f"    FK,req = {_fmt(inter.get('F_K_required_N'), 1)} N",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R3 \u2014 \u6b8b\u4f59\u5939\u7d27\u529b", r3_values, r3_pass, result.get("r3_note", "")),
        Spacer(1, 5),
    ]))

    # -- R4 Assembly stress --
    stresses = result.get("stresses_mpa", {})
    r4_pass = checks.get("assembly_von_mises_ok")
    r4_values = [
        f"sigma_vm = {_fmt(stresses.get('sigma_vm_assembly'), 1)} MPa"
        f"    sigma_allow = {_fmt(stresses.get('sigma_allow_assembly'), 1)} MPa",
        f"sigma_ax = {_fmt(stresses.get('sigma_ax_assembly'), 1)} MPa"
        f"    tau = {_fmt(stresses.get('tau_assembly'), 1)} MPa"
        f"    k_tau = {_fmt(stresses.get('k_tau'), 3)}",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R4 \u2014 \u88c5\u914d\u5e94\u529b\u6821\u6838", r4_values, r4_pass),
        Spacer(1, 5),
    ]))

    # -- R5 Operating stress --
    r5_pass = checks.get("operating_axial_ok")
    r5_values = [
        f"F_bolt_max = {_fmt(forces.get('F_bolt_work_max_N'), 1)} N",
        f"sigma_vm_work = {_fmt(stresses.get('sigma_vm_work'), 1)} MPa"
        f"    sigma_allow = {_fmt(stresses.get('sigma_allow_work'), 1)} MPa",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R5 \u2014 \u670d\u5f79\u5e94\u529b\u6821\u6838", r5_values, r5_pass),
        Spacer(1, 5),
    ]))

    # -- R7 Bearing pressure (if active) --
    if "bearing_pressure_ok" in checks:
        r7_pass = checks["bearing_pressure_ok"]
        r7_values = [
            f"p_bearing = {_fmt(stresses.get('p_bearing'), 1)} MPa"
            f"    p_allow = {_fmt(stresses.get('p_G_allow'), 1)} MPa"
            f"    A_bearing = {_fmt(stresses.get('A_bearing_mm2'), 1)} mm2",
        ]
        elements.append(KeepTogether([
            _rstep_card(styles, "R7 \u2014 \u652f\u627f\u9762\u538b\u5f3a", r7_values, r7_pass, result.get("r7_note", "")),
            Spacer(1, 5),
        ]))

    # -- R8 Thread stripping (if active) --
    strip = result.get("thread_strip", {})
    if "thread_strip_ok" in checks:
        r8_pass = checks["thread_strip_ok"]
        side_cn = "\u87ba\u6813\u4fa7" if strip.get("critical_side") == "bolt" else "\u87ba\u6bcd/\u58f3\u4f53\u4fa7"
        r8_values = [
            f"\u5b89\u5168\u7cfb\u6570 = {_fmt(strip.get('strip_safety'), 2)}"
            f"    \u8981\u6c42 >= {_fmt(strip.get('strip_safety_required'), 2)}",
            f"F_strip_bolt = {_fmt(strip.get('F_strip_bolt_N'), 0)} N"
            f"    F_strip_nut = {_fmt(strip.get('F_strip_nut_N'), 0)} N",
            f"\u4e34\u754c\u4fa7: {side_cn}",
        ]
        elements.append(KeepTogether([
            _rstep_card(styles, "R8 \u2014 \u87ba\u7eb9\u8131\u6263", r8_values, r8_pass, result.get("r8_note", "")),
            Spacer(1, 5),
        ]))

    # -- Thermal (if active) --
    if check_level in ("thermal", "fatigue"):
        elements.append(Spacer(1, 4))
        elements.append(_section_title(styles, "\u6e29\u5ea6\u5f71\u54cd"))
        th_rows = [
            ("\u70ed\u635f\u5931", _fmt(thermal.get("thermal_loss_effective_N"), 1, "N")),
            ("\u70ed\u635f\u5931\u5360\u6bd4", _fmt(thermal.get("thermal_loss_ratio"), 3)),
            ("\u87ba\u6813\u70ed\u81a8\u80c0\u7cfb\u6570", _fmt(thermal.get("alpha_bolt"), 2, "1e-6/K")),
            ("\u88ab\u5939\u4ef6\u70ed\u81a8\u80c0\u7cfb\u6570", _fmt(thermal.get("alpha_parts"), 2, "1e-6/K")),
        ]
        if thermal.get("thermal_auto_estimated"):
            th_rows.append(("\u81ea\u52a8\u4f30\u7b97\u503c", _fmt(thermal.get("thermal_auto_value_N"), 1, "N")))
        elements.append(_kv_table(styles, th_rows, col_ratio=0.4))
        elements.append(Spacer(1, 5))

    # -- R6 Fatigue (if active) --
    fatigue = result.get("fatigue", {})
    if check_level == "fatigue" and "fatigue_ok" in checks:
        r6_pass = checks["fatigue_ok"]
        treatment_cn = {"rolled": "\u8f67\u5236\u87ba\u7eb9", "cut": "\u5207\u524a\u87ba\u7eb9"}.get(
            fatigue.get("surface_treatment", ""), str(fatigue.get("surface_treatment", ""))
        )
        r6_values = [
            f"sigma_a = {_fmt(fatigue.get('sigma_a'), 2)} MPa"
            f"    sigma_a_allow = {_fmt(fatigue.get('sigma_a_allow'), 2)} MPa",
            f"sigma_ASV = {_fmt(fatigue.get('sigma_ASV'), 1)} MPa"
            f"    Goodman = {_fmt(fatigue.get('goodman_factor'), 3)}"
            f"    {treatment_cn}",
        ]
        elements.append(KeepTogether([
            _rstep_card(styles, "R6 \u2014 \u75b2\u52b3\u6821\u6838 (\u7b80\u5316 Goodman)", r6_values, r6_pass),
            Spacer(1, 5),
        ]))

    # -- Warnings --
    warnings = result.get("warnings", [])
    if warnings:
        elements.append(Spacer(1, 4))
        elements.append(_section_title(styles, "\u8b66\u544a"))
        for w in warnings:
            elements.append(Paragraph(f"  {w}", styles["body"]))
            elements.append(Spacer(1, 2))

    # -- Recommendations --
    recs = build_bolt_recommendations(result)
    elements.append(Spacer(1, 4))
    elements.append(_section_title(styles, "\u5efa\u8bae"))
    for r in recs:
        elements.append(Paragraph(f"  {r}", styles["body"]))
        elements.append(Spacer(1, 2))

    # -- Scope note --
    scope = result.get("scope_note", "")
    if scope:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(scope, styles["muted"]))

    # -- Build PDF --
    build_pdf(path, elements, "VDI 2230 \u87ba\u6813\u6821\u6838\u5de5\u5177")
