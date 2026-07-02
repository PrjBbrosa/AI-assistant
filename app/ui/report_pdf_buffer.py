"""Reportlab PDF report generator for buffer energy simulation results."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.platypus import KeepTogether, Paragraph, Spacer

from app.ui.report_pdf_common import (
    _build_styles,
    _check_pills,
    _fmt,
    _header_bar,
    _input_table,
    _kv_table,
    _metric_cards,
    _register_fonts,
    _rstep_card,
    _section_title,
    _verdict_block,
    build_pdf,
)


DISCLAIMER_TEXT = (
    "本工具基于准静态 F-x 曲线的单次冲击能量法。回弹速度与时域响应均为反推估算值，"
    "不含应变率效应，不能替代真实时域仿真。"
)

CHECK_LABELS = {
    "stroke_ok": "行程校核",
    "peak_force_ok": "峰值力校核",
    "energy_capacity_ok": "曲线能量容量校核",
}


def _append_row(
    rows: list[tuple[str, str]],
    label: str,
    value: Any,
    precision: int = 2,
    unit: str = "",
) -> None:
    if value is None:
        return
    rows.append((label, _fmt(value, precision, unit)))


def _paragraph(styles: dict, text: str) -> Paragraph:
    return Paragraph(escape(str(text)), styles["body"])


def _check_text(value: Any) -> str:
    if value is True:
        return "通过"
    if value is False:
        return "不通过"
    return "不可判定"


def _peak_force_text(value: Any) -> str:
    if value is None:
        return "触底，不可判定"
    return _fmt(value, 1, "N")


def _input_source(payload: dict, result: dict) -> dict:
    echo = result.get("inputs_echo")
    return echo if isinstance(echo, dict) else payload


def _build_input_rows(payload: dict, result: dict) -> list[tuple[str, str]]:
    source = _input_source(payload, result)
    impact = source.get("impact", {}) if isinstance(source.get("impact", {}), dict) else {}
    options = source.get("options", {}) if isinstance(source.get("options", {}), dict) else {}
    curve = payload.get("curve", {}) if isinstance(payload.get("curve", {}), dict) else {}
    loading = curve.get("loading", []) if isinstance(curve.get("loading", []), list) else []
    unloading = curve.get("unloading", []) if isinstance(curve.get("unloading", []), list) else []

    rows: list[tuple[str, str]] = []
    rows.append(("加载/卸载点数", f"{len(loading)} / {len(unloading)}"))
    _append_row(rows, "冲击质量 m", impact.get("mass_kg"), 3, "kg")
    _append_row(rows, "初始速度 v0", impact.get("initial_velocity_m_s"), 3, "m/s")
    _append_row(rows, "可用行程", impact.get("available_stroke_mm"), 2, "mm")
    _append_row(rows, "允许峰值力", impact.get("allowable_peak_force_n"), 0, "N")
    _append_row(rows, "曲线力倍率", options.get("force_scale"), 3)
    _append_row(rows, "曲线行程倍率", options.get("stroke_scale"), 3)
    _append_row(rows, "卸载噪声容差", options.get("noise_tolerance_n"), 2, "N")
    _append_row(rows, "时域采样点数", options.get("time_samples"), 0)
    return rows


def _build_curve_rows(result: dict) -> list[tuple[str, str]]:
    summary = result.get("curve_summary", {}) if isinstance(result.get("curve_summary", {}), dict) else {}
    rows: list[tuple[str, str]] = []
    _append_row(rows, "测试曲线最大行程", summary.get("max_stroke_mm"), 2, "mm")
    _append_row(rows, "最大加载力", summary.get("peak_loading_force_n"), 1, "N")
    _append_row(rows, "加载能量", summary.get("loading_energy_j"), 3, "J")
    _append_row(rows, "卸载能量", summary.get("unloading_energy_j"), 3, "J")
    _append_row(rows, "滞回能量", summary.get("curve_hysteresis_energy_j"), 3, "J")
    ratio = summary.get("energy_absorption_ratio")
    if isinstance(ratio, (int, float)):
        rows.append(("吸能比例", _fmt(ratio * 100.0, 1, "%")))
    _append_row(rows, "等效刚度", summary.get("equivalent_stiffness_n_per_mm"), 1, "N/mm")
    _append_row(rows, "切线刚度最小值", summary.get("tangent_stiffness_min_n_per_mm"), 1, "N/mm")
    _append_row(rows, "切线刚度最大值", summary.get("tangent_stiffness_max_n_per_mm"), 1, "N/mm")
    return rows


def _build_impact_rows(result: dict) -> list[tuple[str, str]]:
    impact = result.get("impact", {}) if isinstance(result.get("impact", {}), dict) else {}
    response = result.get("time_response", {}) if isinstance(result.get("time_response", {}), dict) else {}
    rows: list[tuple[str, str]] = []
    _append_row(rows, "初始动能", impact.get("initial_energy_j"), 3, "J")
    _append_row(rows, "可用吸能容量", impact.get("available_energy_capacity_j"), 3, "J")
    _append_row(rows, "有效行程", impact.get("effective_stroke_mm"), 3, "mm")
    _append_row(rows, "最大压缩量", impact.get("max_compression_mm"), 3, "mm")
    if "peak_force_n" in impact:
        rows.append(("峰值输出力", _peak_force_text(impact.get("peak_force_n"))))
    _append_row(rows, "平均反力", impact.get("average_force_n"), 1, "N")
    _append_row(rows, "吸收能量", impact.get("absorbed_energy_j"), 3, "J")
    _append_row(rows, "工况耗散能量", impact.get("impact_dissipated_energy_j"), 3, "J")
    _append_row(rows, "回弹能量", impact.get("rebound_energy_j"), 3, "J")
    _append_row(rows, "估算回弹速度", impact.get("estimated_rebound_velocity_m_s"), 3, "m/s")
    if "duration_s" in response:
        rows.append(("接触时长", _fmt(float(response.get("duration_s", 0.0)) * 1000.0, 2, "ms")))
    if "bottom_out" in impact:
        rows.append(("是否触底", "是" if impact.get("bottom_out") else "否"))
    return rows


def _build_recommendations(result: dict) -> list[str]:
    impact = result.get("impact", {}) if isinstance(result.get("impact", {}), dict) else {}
    checks = result.get("checks", {}) if isinstance(result.get("checks", {}), dict) else {}
    recs: list[str] = []
    if impact.get("bottom_out") or checks.get("energy_capacity_ok") is False:
        recs.append("输入动能超过可用行程内吸能容量：需增大可用行程、换用更高容量缓冲块或降低冲击能量。")
    if checks.get("peak_force_ok") is False:
        recs.append("峰值力超过允许值：需降低缓冲块刚度峰值、增大行程或提高安装结构承载能力。")
    if checks.get("stroke_ok") is False:
        recs.append("最大压缩量超过可用行程：需增加机械行程或选择更短压缩量方案。")
    if not recs:
        recs.append("当前工况满足行程、峰值力和曲线能量容量校核。")
    return recs


def generate_buffer_report(out_path: Path, payload: dict, result: dict) -> None:
    """Generate a reportlab PDF report for buffer energy simulation."""
    _register_fonts()
    styles = _build_styles()
    elems: list[Any] = []

    impact = result.get("impact", {}) if isinstance(result.get("impact", {}), dict) else {}
    checks = result.get("checks", {}) if isinstance(result.get("checks", {}), dict) else {}
    overall = bool(result.get("overall_pass", False))
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    elems.append(_header_bar(styles, "缓冲块吸能仿真报告", date_str))
    elems.append(Spacer(1, 8))
    subtitle = "单次冲击能量法"
    if impact.get("bottom_out"):
        subtitle += " - 触底 / 峰值未知"
    elems.append(_verdict_block(styles, overall, subtitle))
    elems.append(Spacer(1, 8))

    metrics = [
        ("E0 (J)", _fmt(impact.get("initial_energy_j"), 3)),
        ("x_max (mm)", _fmt(impact.get("max_compression_mm"), 3)),
        ("F_peak", _fmt(impact.get("peak_force_n"), 1, "N")),
        ("v_rebound (m/s)", _fmt(impact.get("estimated_rebound_velocity_m_s"), 3)),
    ]
    elems.append(_metric_cards(styles, metrics))
    elems.append(Spacer(1, 8))
    elems.append(_check_pills(styles, checks, CHECK_LABELS, {}))
    elems.append(Spacer(1, 12))

    input_rows = _build_input_rows(payload, result)
    if input_rows:
        elems.append(_section_title(styles, "输入回显"))
        elems.append(_input_table(styles, input_rows))
        elems.append(Spacer(1, 10))

    curve_rows = _build_curve_rows(result)
    if curve_rows:
        elems.append(_section_title(styles, "曲线摘要"))
        elems.append(_kv_table(styles, curve_rows, 0.45))
        elems.append(Spacer(1, 10))

    impact_rows = _build_impact_rows(result)
    if impact_rows:
        elems.append(_section_title(styles, "冲击结果"))
        elems.append(_kv_table(styles, impact_rows, 0.45))
        elems.append(Spacer(1, 10))

    check_values = [
        f"行程: {_check_text(checks.get('stroke_ok'))}",
        f"峰值力: {_check_text(checks.get('peak_force_ok'))}",
        f"曲线能量容量: {_check_text(checks.get('energy_capacity_ok'))}",
        f"整体结论: {'通过' if overall else '不通过'}",
    ]
    elems.append(KeepTogether([
        _rstep_card(
            styles,
            "校核结论",
            check_values,
            passed=overall,
            note="触底时峰值力为不可判定，整体结论按不通过处理。",
        ),
        Spacer(1, 8),
    ]))

    elems.append(_section_title(styles, "建议"))
    for rec in _build_recommendations(result):
        elems.append(_paragraph(styles, f"- {rec}"))
    elems.append(Spacer(1, 8))

    elems.append(_section_title(styles, "免责与边界"))
    boundary = [DISCLAIMER_TEXT]
    assumptions = result.get("assumptions", [])
    if isinstance(assumptions, list):
        boundary.extend(str(item) for item in assumptions)
    warnings = result.get("warnings", [])
    if isinstance(warnings, list):
        boundary.extend(str(item) for item in warnings)
    for note in boundary:
        elems.append(_paragraph(styles, f"- {note}"))

    build_pdf(out_path, elems, "缓冲块吸能仿真")
