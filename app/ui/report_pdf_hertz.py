"""Reportlab PDF report generator for Hertz contact-stress results."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.platypus import KeepTogether, Paragraph, Spacer

from core.hertz.calculator import OUTER_CONTACT_SCOPE_NOTE
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


CHECK_LABELS = {
    "contact_stress_ok": "最大接触应力校核",
}


def _mode_text(mode: Any) -> str:
    if mode == "line":
        return "线接触"
    if mode == "point":
        return "点接触"
    return str(mode or "-")


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


def _build_input_rows(payload: dict, result: dict) -> list[tuple[str, str]]:
    echo = result.get("inputs_echo")
    source = echo if isinstance(echo, dict) else payload
    geometry = source.get("geometry", {}) if isinstance(source.get("geometry", {}), dict) else {}
    materials = source.get("materials", {}) if isinstance(source.get("materials", {}), dict) else {}
    loads = source.get("loads", {}) if isinstance(source.get("loads", {}), dict) else {}
    checks = source.get("checks", {}) if isinstance(source.get("checks", {}), dict) else {}
    options = source.get("options", {}) if isinstance(source.get("options", {}), dict) else {}

    mode = result.get("mode", geometry.get("contact_mode"))
    rows: list[tuple[str, str]] = [("接触模型", _mode_text(mode))]
    _append_row(rows, "曲率半径 R1", geometry.get("r1_mm"), 3, "mm")
    _append_row(rows, "曲率半径 R2", geometry.get("r2_mm"), 3, "mm")
    if mode == "line" or geometry.get("length_mm") is not None:
        _append_row(rows, "接触长度 L", geometry.get("length_mm"), 3, "mm")
    _append_row(rows, "接触体 1 弹性模量 E1", materials.get("e1_mpa"), 0, "MPa")
    _append_row(rows, "接触体 1 泊松比 nu1", materials.get("nu1"), 3)
    _append_row(rows, "接触体 2 弹性模量 E2", materials.get("e2_mpa"), 0, "MPa")
    _append_row(rows, "接触体 2 泊松比 nu2", materials.get("nu2"), 3)
    _append_row(rows, "法向载荷 F", loads.get("normal_force_n"), 1, "N")
    _append_row(rows, "允许最大接触应力 [p0]", checks.get("allowable_p0_mpa"), 1, "MPa")
    _append_row(rows, "曲线采样点数", options.get("curve_points"), 0)
    _append_row(rows, "曲线载荷上限倍率", options.get("curve_force_scale"), 2)
    return rows


def _build_contact_rows(result: dict) -> list[tuple[str, str]]:
    contact = result.get("contact", {}) if isinstance(result.get("contact", {}), dict) else {}
    derived = result.get("derived", {}) if isinstance(result.get("derived", {}), dict) else {}
    check = result.get("check", {}) if isinstance(result.get("check", {}), dict) else {}
    mode = result.get("mode")

    rows: list[tuple[str, str]] = []
    _append_row(rows, "等效弹性模量 E'", derived.get("e_eq_mpa"), 1, "MPa")
    _append_row(rows, "等效曲率半径 R'", derived.get("r_eq_mm"), 4, "mm")
    _append_row(rows, "最大接触应力 p0", contact.get("p0_mpa"), 2, "MPa")
    _append_row(rows, "平均接触应力 p_mean", contact.get("p_mean_mpa"), 2, "MPa")
    if mode == "line":
        _append_row(rows, "接触半宽 b", contact.get("semi_width_mm"), 5, "mm")
        _append_row(rows, "接触长度 L", contact.get("length_mm"), 3, "mm")
    elif mode == "point":
        _append_row(rows, "接触半轴/半径 a", contact.get("contact_radius_mm"), 5, "mm")
    else:
        _append_row(rows, "接触半宽 b", contact.get("semi_width_mm"), 5, "mm")
        _append_row(rows, "接触半轴/半径 a", contact.get("contact_radius_mm"), 5, "mm")
    _append_row(rows, "接触面积 A", contact.get("contact_area_mm2"), 5, "mm^2")
    _append_row(rows, "法向载荷 F", contact.get("normal_force_n"), 1, "N")
    _append_row(rows, "许用接触应力 [p0]", check.get("allowable_p0_mpa"), 2, "MPa")
    _append_row(rows, "安全系数 S", check.get("safety_factor"), 3)
    return rows


def _build_recommendations(result: dict) -> list[str]:
    checks = result.get("checks", {}) if isinstance(result.get("checks", {}), dict) else {}
    check = result.get("check", {}) if isinstance(result.get("check", {}), dict) else {}
    recs: list[str] = []
    if checks.get("contact_stress_ok") is False:
        recs.append("最大接触应力超过许用值：可增大等效曲率半径、降低法向载荷或提高材料许用接触应力。")
    safety = check.get("safety_factor")
    if isinstance(safety, (int, float)) and safety < 1.2:
        recs.append("安全系数低于 1.2，建议增加工程裕量并复核疲劳寿命。")
    if not recs:
        recs.append("当前工况满足接触应力校核要求，建议结合疲劳寿命与润滑/表面状态继续复核。")
    return recs


def generate_hertz_report(out_path: Path, payload: dict, result: dict) -> None:
    """Generate a reportlab PDF report for Hertz contact-stress results."""
    _register_fonts()
    styles = _build_styles()
    elems: list[Any] = []

    contact = result.get("contact", {}) if isinstance(result.get("contact", {}), dict) else {}
    check = result.get("check", {}) if isinstance(result.get("check", {}), dict) else {}
    checks = result.get("checks", {}) if isinstance(result.get("checks", {}), dict) else {}
    mode = result.get("mode")
    overall = bool(result.get("overall_pass", False))
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    elems.append(_header_bar(styles, "赫兹接触应力校核报告", date_str))
    elems.append(Spacer(1, 8))
    elems.append(_verdict_block(styles, overall, f"模型: {_mode_text(mode)}"))
    elems.append(Spacer(1, 8))

    patch_label = "b (mm)" if mode == "line" else "a (mm)"
    patch_value = contact.get("semi_width_mm") if mode == "line" else contact.get("contact_radius_mm")
    metrics = [
        ("p0 (MPa)", _fmt(contact.get("p0_mpa"), 2)),
        (patch_label, _fmt(patch_value, 5)),
        ("A (mm^2)", _fmt(contact.get("contact_area_mm2"), 5)),
        ("S", _fmt(check.get("safety_factor"), 3)),
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

    contact_rows = _build_contact_rows(result)
    if contact_rows:
        elems.append(_section_title(styles, "接触结果"))
        elems.append(_kv_table(styles, contact_rows, 0.45))
        elems.append(Spacer(1, 10))

    result_text = "通过" if overall else "不通过"
    allowable = check.get("allowable_p0_mpa")
    p0 = contact.get("p0_mpa")
    compare_values = [
        f"最大接触应力 p0: {_fmt(p0, 2, 'MPa')}",
        f"许用接触应力 [p0]: {_fmt(allowable, 2, 'MPa')}",
        f"结论: {result_text}",
    ]
    elems.append(KeepTogether([
        _rstep_card(
            styles,
            "许用对比与结论",
            compare_values,
            passed=overall,
            note="按 p0 不大于 [p0] 判定接触应力校核。",
        ),
        Spacer(1, 8),
    ]))

    warnings = result.get("warnings", [])
    if warnings:
        elems.append(_section_title(styles, "提示"))
        for msg in warnings:
            elems.append(_paragraph(styles, f"- {msg}"))
        elems.append(Spacer(1, 8))

    elems.append(_section_title(styles, "建议"))
    for rec in _build_recommendations(result):
        elems.append(_paragraph(styles, f"- {rec}"))
    elems.append(Spacer(1, 8))

    elems.append(_section_title(styles, "模型边界说明"))
    boundary = [
        OUTER_CONTACT_SCOPE_NOTE,
        "当前基于标准赫兹弹性接触理论。",
        "未包含弹塑性、残余应力、表面粗糙度、润滑状态和边缘效应修正。",
        "冲击或动载工况需先折算为峰值法向载荷；疲劳寿命需另行校核。",
    ]
    for note in boundary:
        elems.append(_paragraph(styles, f"- {note}"))

    build_pdf(out_path, elems, "赫兹接触应力校核")
