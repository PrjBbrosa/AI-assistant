"""Rich PDF report for fatigue strength and reliability pre-checks."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.ui.model_scope import FATIGUE_SCOPE, scope_kv_rows
from app.ui.report_export import write_report_atomically
from app.ui.report_pdf_common import (
    C_BG,
    C_FAIL,
    C_INCOMPLETE,
    C_PASS,
    _build_styles,
    _header_bar,
    _register_fonts,
)
from app.ui.report_trace import build_report_trace
from app.ui.result_contract import from_fatigue, status_label_zh


def _paragraph(value: Any, style) -> Paragraph:
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text, style)


def _table(rows: list[list[Any]], widths: list[float], styles: dict, *, header: bool = True) -> Table:
    converted = [
        [_paragraph(cell, styles["body_bold"] if header and row_index == 0 else styles["body"]) for cell in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E0E6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0E7E1")))
    table.setStyle(TableStyle(commands))
    return table


def _sn_chart(payload: dict[str, Any], result: dict[str, Any]) -> io.BytesIO | None:
    fit = result.get("fit")
    rows = payload.get("test_data", {}).get("specimens", [])
    if not isinstance(fit, dict) or fit.get("status") != "valid" or not rows:
        return None
    failures = [row for row in rows if str(row.get("status")) in {"failure", "断裂", "失效"}]
    runouts = [row for row in rows if row not in failures]
    fig, axis = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    if failures:
        axis.scatter(
            [float(row["cycles"]) for row in failures],
            [float(row["stress_amplitude_mpa"]) for row in failures],
            color="#2F72B7",
            label="failure",
            zorder=3,
        )
    if runouts:
        axis.scatter(
            [float(row["cycles"]) for row in runouts],
            [float(row["stress_amplitude_mpa"]) for row in runouts],
            facecolors="none",
            edgecolors="#B7791F",
            marker=">",
            label="runout",
            zorder=3,
        )
    stresses = np.geomspace(float(fit["stress_min_mpa"]), float(fit["stress_max_mpa"]), 160)
    from scipy.stats import norm

    for survival, color, label in ((0.5, "#2F72B7", "Ps=50%"), (float(payload["sn_model"].get("design_survival_probability", 0.9)), "#D97757", "design Ps")):
        z = norm.ppf(1.0 - survival)
        lives = np.power(
            10.0,
            float(fit["a"])
            - float(fit["b"]) * np.log10(stresses)
            + float(fit["scatter_log10_n"]) * z,
        )
        axis.plot(lives, stresses, color=color, label=label)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set_xlabel("Life N [cycles]")
    axis.set_ylabel("Stress amplitude Sa [MPa]")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    axis.set_title("S-N / P-S-N finite-life fit")
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _build_pdf(path: Path, payload: dict[str, Any], result: dict[str, Any]) -> None:
    _register_fonts()
    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="疲劳强度与可靠性预校核报告",
        author="Local Engineering Assistant",
    )
    view = from_fatigue(result, payload)
    trace = build_report_trace(FATIGUE_SCOPE.module_id, payload, model_level=FATIGUE_SCOPE.model_level)
    fit = result.get("fit") or {}
    evidence = result.get("fatigue_limit_evidence") or {}
    damage = result.get("damage") or {}
    reliability = result.get("reliability") or {}
    material = payload.get("material_condition", {})
    sn_source = payload.get("test_data", {}).get("source") or {}
    spectrum_source = payload.get("spectrum", {}).get("source") or {}
    story: list[Any] = [
        _header_bar(styles, "疲劳强度与可靠性预校核报告", trace.generated_at[:10]),
        Spacer(1, 5 * mm),
    ]
    status_color = C_PASS if view.overall_status == "pass" else C_FAIL if view.overall_status == "fail" else C_INCOMPLETE
    verdict = Table(
        [[_paragraph(view.title_zh, styles["body_bold"]), _paragraph(view.summary_zh, styles["body"]) ]],
        colWidths=[45 * mm, 118 * mm],
    )
    verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), status_color),
        ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), C_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([verdict, Spacer(1, 5 * mm), _paragraph("追溯信息", styles["h2"])])
    trace_rows = [
        ["软件版本", trace.software_version],
        ["生成时间", trace.generated_at],
        ["模块/等级", f"{trace.module_id} / {trace.model_level}"],
        ["输入哈希", trace.input_hash],
    ]
    story.extend([_table(trace_rows, [38 * mm, 125 * mm], styles, header=False), _paragraph("1. 模型范围与试验条件", styles["h2"])])
    scope_rows = [[label, value] for label, value in scope_kv_rows(FATIGUE_SCOPE)]
    condition_rows = [
        ["材料/数据集", material.get("material_name", "-")],
        ["材料类型", material.get("material_type", "-")],
        ["批次/对象", f"{material.get('batch', '-')} / {material.get('object_type', '-')}"] ,
        ["温度/湿度/频率/R", f"{material.get('temperature_c')} °C / {material.get('humidity_rh')} %RH / {material.get('frequency_hz')} Hz / {material.get('r_ratio')}"] ,
        ["热处理/成型条件", material.get("process_condition", "-")],
        ["方向/调湿/表面", f"{material.get('orientation', '-')} / {material.get('conditioning', '-')} / {material.get('surface', '-')}"] ,
        ["S-N 数据来源", f"{sn_source.get('file_name', '-')} / {sn_source.get('sheet_name', '-')}"] ,
        ["S-N 来源 SHA-256", sn_source.get("sha256", "-")],
    ]
    story.extend(
        [
            _table(
                scope_rows + condition_rows,
                [42 * mm, 121 * mm],
                styles,
                header=False,
            ),
            PageBreak(),
            _paragraph("2. S-N/P-S-N 拟合", styles["h2"]),
        ]
    )
    fit_rows = [
        ["方法", "含 runout 右删失项的对数正态极大似然"],
        ["状态", fit.get("status", "-")],
        ["断裂 / runout", f"{fit.get('failure_count', 0)} / {fit.get('runout_count', 0)}"],
        ["模型", "log10(N) = a - b*log10(Sa,eq) + epsilon"],
        ["a / b / s", f"{fit.get('a', '-')} / {fit.get('b', '-')} / {fit.get('scatter_log10_n', '-')}"],
        ["有限寿命实测应力范围 [MPa]", f"{fit.get('stress_min_mpa', '-')} .. {fit.get('stress_max_mpa', '-')}"],
        ["疲劳极限证据区间 [MPa]", f"{evidence.get('possible_lower_bound_mpa', '-')} .. {evidence.get('possible_upper_bound_mpa', '-')}（全 runout 级不入有限寿命线）"],
        ["对照方法", "Johnson/MRR 与仅断裂点 OLS；不参与主结论"],
    ]
    story.append(_table(fit_rows, [42 * mm, 121 * mm], styles, header=False))
    chart = _sn_chart(payload, result)
    if chart is not None:
        story.extend([Spacer(1, 3 * mm), Image(chart, width=160 * mm, height=98 * mm)])
    story.extend([PageBreak(), _paragraph("3. 谱、损伤与可靠性", styles["h2"])])
    reliability_rows = [
        ["谱类型 / 传递", f"{payload.get('spectrum', {}).get('kind')} / {payload.get('transfer', {}).get('mode')}"] ,
        ["谱数据来源", f"{spectrum_source.get('file_name', '-')} / {spectrum_source.get('sheet_name', '-')}"] ,
        ["谱来源 SHA-256", spectrum_source.get("sha256", "-")],
        ["单谱块 / 目标 Miner 损伤", f"{damage.get('damage_per_spectrum_block', '-')} / {damage.get('target_damage', '-')}"],
        ["目标谱块数", reliability.get("target_spectrum_blocks", "-")],
        ["目标可靠度 R", reliability.get("reliability", "-")],
        ["目标寿命前失效概率 Pf [ppm]", reliability.get("pf_ppm", "-")],
        ["Pf 95% 置信区间", reliability.get("pf_confidence_interval_95", "-")],
        ["存活率 Ps=90% 对应寿命 [谱块]", (reliability.get("life_quantiles_blocks") or {}).get("Ps90", "-")],
        ["Monte Carlo / bootstrap / seed", f"{reliability.get('monte_carlo_samples', '-')} / {reliability.get('bootstrap_successful', '-')}/{reliability.get('bootstrap_requested', '-')} / {reliability.get('seed', '-')}"],
    ]
    story.append(_table(reliability_rows, [58 * mm, 105 * mm], styles, header=False))
    contributions = damage.get("contributions") if isinstance(damage, dict) else None
    if isinstance(contributions, list) and contributions:
        damage_rows = [["Sa,eq [MPa]", "均值 [MPa]", "循环数", "单谱块损伤", "贡献率"]]
        total = float(damage.get("damage_per_spectrum_block", 0.0))
        for row in contributions[:12]:
            contribution = float(row.get("damage_per_block", 0.0))
            damage_rows.append([
                f"{float(row.get('equivalent_amplitude_mpa', 0)):.6g}",
                f"{float(row.get('mean_mpa', 0)):.6g}",
                f"{float(row.get('cycles', 0)):.6g}",
                f"{contribution:.6g}",
                f"{contribution / total:.2%}" if total > 0 else "-",
            ])
        story.extend([Spacer(1, 4 * mm), _paragraph("主要谱级损伤贡献", styles["h2"]), _table(damage_rows, [32 * mm] * 5, styles)])
    story.append(_paragraph("4. 校核项", styles["h2"]))
    check_rows = [["校核项", "状态", "实际值", "限值"]]
    for check in view.checks:
        check_rows.append([
            check.label_zh,
            status_label_zh(check.status),
            "-" if check.actual is None else f"{check.actual:.6g}",
            "-" if check.limit is None else f"{check.limit:.6g}",
        ])
    story.append(_table(check_rows, [66 * mm, 28 * mm, 35 * mm, 34 * mm], styles))
    story.append(_paragraph("5. 警告与限制", styles["h2"]))
    if result.get("warnings"):
        for item in result["warnings"]:
            story.append(_paragraph(f"- {item}", styles["body"]))
    else:
        story.append(_paragraph("- 无。", styles["body"]))
    story.append(_paragraph("6. 模型假设", styles["h2"]))
    for item in result.get("assumptions", []):
        story.append(_paragraph(f"- {item}", styles["body"]))
    doc.build(story)


def generate_fatigue_report(
    out_path: Path | str, payload: dict[str, Any], result: dict[str, Any]
) -> None:
    """Generate an atomic, traceable PDF fatigue pre-check report."""
    destination = Path(out_path)
    write_report_atomically(destination, lambda temporary: _build_pdf(temporary, payload, result))
