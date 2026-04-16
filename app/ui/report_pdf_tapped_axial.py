"""Professional PDF report for tapped axial threaded joint check results.

Uses reportlab to produce an A4 report with:
- Colored header bar, pass/fail verdict
- Input summary, check pills, key metrics
- Detailed stress results and fatigue data
- Warnings and recommendations
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

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
    _kv_table,
    _metric_cards,
    _register_fonts,
    _rstep_card,
    _section_title,
    _verdict_block,
    build_pdf,
)

CHECK_LABELS = {
    "assembly_von_mises_ok": "装配强度",
    "service_von_mises_ok": "服役最大强度",
    "fatigue_ok": "交变轴向疲劳",
    "thread_strip_ok": "螺纹脱扣",
}


def generate_tapped_axial_report(
    path: Path,
    payload: dict,
    result: dict,
) -> None:
    """Generate a professional PDF report for tapped axial threaded joint."""
    _register_fonts()
    styles = _build_styles()
    elems: list = []

    checks = result.get("checks", {})
    # Codex follow-up 2026-04-16：使用 overall_status 三态（pass/fail/incomplete），
    # 避免 None 分项被 bool() 当作 fail 导出为红色 FAIL 报告。
    overall_status = result.get(
        "overall_status",
        "pass" if result.get("overall_pass") else "fail",
    )
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. Header bar
    elems.append(_header_bar(styles, "轴向受力螺纹连接校核报告", date_str))
    elems.append(Spacer(1, 8))

    # 2. Verdict（三态：pass / fail / incomplete）
    scope = result.get("scope_note", "")
    elems.append(_verdict_block(styles, overall_status, scope))
    elems.append(Spacer(1, 8))

    # 3. Metric cards
    asm = result.get("assembly", {})
    stresses = result.get("stresses_mpa", {})
    fatigue = result.get("fatigue", {})
    metrics = [
        ("F_preload_max (N)", _fmt(asm.get("F_preload_max_N"), 0)),
        ("MA_max (N*m)", _fmt(asm.get("MA_max_Nm"), 2)),
        ("sigma_vm_assembly (MPa)", _fmt(stresses.get("sigma_vm_assembly"), 1)),
        ("sigma_a_allow (MPa)", _fmt(fatigue.get("sigma_a_allow"), 2)),
    ]
    elems.append(_metric_cards(styles, metrics))
    elems.append(Spacer(1, 10))

    # 4. Check pills
    refs = result.get("references", {})
    elems.append(_check_pills(styles, checks, CHECK_LABELS, refs))
    elems.append(Spacer(1, 10))

    # 5. Input summary
    elems.append(_section_title(styles, "输入摘要"))
    fastener = payload.get("fastener", {})
    assembly = payload.get("assembly", {})
    service = payload.get("service", {})
    fat_in = payload.get("fatigue", {})
    input_rows = [
        ("公称直径 d", _fmt(fastener.get("d"), 1, "mm")),
        ("螺距 p", _fmt(fastener.get("p"), 2, "mm")),
        ("屈服强度 Rp0.2", _fmt(fastener.get("Rp02"), 0, "MPa")),
        ("最小预紧力 F_preload_min", _fmt(assembly.get("F_preload_min"), 0, "N")),
        ("拧紧散差 alpha_A", _fmt(assembly.get("alpha_A"), 2)),
        ("螺纹摩擦 mu_thread", _fmt(assembly.get("mu_thread"), 3)),
        ("支承面摩擦 mu_bearing", _fmt(assembly.get("mu_bearing"), 3)),
        ("拧紧方式", str(assembly.get("tightening_method", ""))),
        ("最小轴向载荷 FA_min", _fmt(service.get("FA_min"), 0, "N")),
        ("最大轴向载荷 FA_max", _fmt(service.get("FA_max"), 0, "N")),
        ("载荷循环次数", _fmt(fat_in.get("load_cycles"), 0)),
        ("表面处理", str(fat_in.get("surface_treatment", ""))),
    ]
    elems.append(_kv_table(styles, input_rows, 0.45))
    elems.append(Spacer(1, 10))

    # 6. Assembly strength card
    trace = result.get("trace", {}).get("intermediate", {})
    asm_values = [
        f"轴向装配应力 sigma_ax = {_fmt(stresses.get('sigma_ax_assembly'), 1, 'MPa')}",
        f"装配扭转应力 tau = {_fmt(stresses.get('tau_assembly'), 1, 'MPa')}",
        f"装配 von Mises sigma_vm = {_fmt(stresses.get('sigma_vm_assembly'), 1, 'MPa')}",
        f"许用装配应力 = {_fmt(trace.get('sigma_allow_assembly'), 1, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "装配强度校核", asm_values,
                    passed=checks.get("assembly_von_mises_ok")),
        Spacer(1, 6),
    ]))

    # 7. Service strength card
    svc_values = [
        f"最大服役轴向应力 sigma_ax = {_fmt(stresses.get('sigma_ax_service_max'), 1, 'MPa')}",
        f"服役 von Mises sigma_vm = {_fmt(stresses.get('sigma_vm_service_max'), 1, 'MPa')}",
        f"许用服役应力 = {_fmt(trace.get('sigma_allow_service'), 1, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "服役最大强度校核", svc_values,
                    passed=checks.get("service_von_mises_ok")),
        Spacer(1, 6),
    ]))

    # 8. Fatigue card
    fat_values = [
        f"疲劳平均应力 sigma_m = {_fmt(stresses.get('sigma_m_fatigue'), 1, 'MPa')}",
        f"疲劳应力幅 sigma_a = {_fmt(stresses.get('sigma_a_fatigue'), 2, 'MPa')}",
        f"sigma_ASV = {_fmt(fatigue.get('sigma_ASV'), 1, 'MPa')}",
        f"Goodman 折减系数 = {_fmt(fatigue.get('goodman_factor'), 3)}",
        f"许用应力幅 sigma_a_allow = {_fmt(fatigue.get('sigma_a_allow'), 2, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "交变轴向疲劳校核", fat_values,
                    passed=checks.get("fatigue_ok")),
        Spacer(1, 6),
    ]))

    # 9. Thread strip card
    ts = result.get("thread_strip", {})
    if ts.get("active"):
        ts_values = [
            f"螺栓侧剪切面积 A_SB = {_fmt(ts.get('A_SB_mm2'), 1, 'mm2')}",
            f"壳体侧剪切面积 A_SM = {_fmt(ts.get('A_SM_mm2'), 1, 'mm2')}",
            f"螺栓最大拉力 F_bolt_max = {_fmt(ts.get('F_bolt_max_N'), 0, 'N')}",
            f"脱扣安全系数 S = {_fmt(ts.get('strip_safety'), 2)}"
            f" (要求 >= {_fmt(ts.get('strip_safety_required'), 2)})",
            ts.get("note", ""),
        ]
        elems.append(KeepTogether([
            _rstep_card(styles, "螺纹脱扣校核", ts_values,
                        passed=ts.get("check_passed")),
            Spacer(1, 6),
        ]))
    else:
        elems.append(KeepTogether([
            _rstep_card(styles, "螺纹脱扣校核",
                        [ts.get("note", "未启用")], passed=None),
            Spacer(1, 6),
        ]))

    # 10. Warnings
    warnings = result.get("warnings", [])
    if warnings:
        elems.append(_section_title(styles, "警告信息"))
        for msg in warnings:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 11. Recommendations
    recs = result.get("recommendations", [])
    if recs:
        elems.append(_section_title(styles, "优化建议"))
        for msg in recs:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 12. References
    elems.append(_section_title(styles, "标准引用"))
    for k, v in result.get("references", {}).items():
        elems.append(Paragraph(f"{k}: {v}", styles["muted"]))
    elems.append(Spacer(1, 4))

    build_pdf(path, elems, "轴向受力螺纹连接校核")
