"""Professional PDF report generator for VDI 2230 bolt check results.

Uses reportlab to produce a modern, visually designed A4 report with:
- Colored header bar, pass/fail badges, key metric cards
- Compact input summary tables grouped by category
- R-step calculation chain with colored accent bars
- Conditional extended checks (thermal, fatigue) and recommendations
"""

from __future__ import annotations

import datetime as dt
import math
import platform
import os
from pathlib import Path
from typing import Any, Dict, List, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Color palette (matches app theme)
# ---------------------------------------------------------------------------
C_PRIMARY = colors.HexColor("#D97757")
C_BG = colors.HexColor("#F7F5F2")
C_PASS = colors.HexColor("#4CAF50")
C_FAIL = colors.HexColor("#E53935")
C_TEXT = colors.HexColor("#2D2D2D")
C_MUTED = colors.HexColor("#888888")
C_WHITE = colors.HexColor("#FFFFFF")
C_LIGHT_PASS = colors.HexColor("#E8F5E9")
C_LIGHT_FAIL = colors.HexColor("#FFEBEE")

PAGE_W, PAGE_H = A4
MARGIN_L = 25 * mm
MARGIN_R = 20 * mm
MARGIN_T = 20 * mm
MARGIN_B = 22 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# ---------------------------------------------------------------------------
# Font setup
# ---------------------------------------------------------------------------
_FONT_REGISTERED = False
FONT_CN = "Helvetica"  # fallback
FONT_CN_BOLD = "Helvetica-Bold"

_FONT_CANDIDATES: list[tuple[str, str, str, int | None]] = [
    # (regular_name, path, bold_path_or_same, subfontIndex)
    # macOS
    ("STHeiti-Regular", "/System/Library/Fonts/STHeiti Medium.ttc", "", 0),
    ("STHeiti-Light", "/System/Library/Fonts/STHeiti Light.ttc", "", 0),
    # macOS Arial Unicode (single TTF, has CJK)
    ("ArialUnicode", "/Library/Fonts/Arial Unicode.ttf", "", None),
    # Windows
    ("MSYH", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc", 0),
    ("SimHei", "C:/Windows/Fonts/simhei.ttf", "", None),
    # Linux
    ("WenQuanYi", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "", 0),
]


def _register_fonts() -> None:
    global _FONT_REGISTERED, FONT_CN, FONT_CN_BOLD
    if _FONT_REGISTERED:
        return
    _FONT_REGISTERED = True

    for name, path, bold_path, sub_idx in _FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            kwargs = {"subfontIndex": sub_idx} if sub_idx is not None else {}
            font = TTFont(name, path, **kwargs)
            pdfmetrics.registerFont(font)
            FONT_CN = name
            # Try bold variant
            if bold_path and os.path.exists(bold_path):
                bold_kwargs = {"subfontIndex": sub_idx} if sub_idx is not None else {}
                bold_font = TTFont(name + "-Bold", bold_path, **bold_kwargs)
                pdfmetrics.registerFont(bold_font)
                FONT_CN_BOLD = name + "-Bold"
            else:
                FONT_CN_BOLD = name  # same weight for bold
            return
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def _build_styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    return {
        "title": ParagraphStyle(
            "title", fontName=FONT_CN_BOLD, fontSize=18, leading=24,
            textColor=C_WHITE, alignment=TA_LEFT,
        ),
        "title_date": ParagraphStyle(
            "title_date", fontName=FONT_CN, fontSize=9, leading=12,
            textColor=colors.HexColor("#FFE0D0"), alignment=TA_RIGHT,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=FONT_CN_BOLD, fontSize=12, leading=16,
            textColor=C_PRIMARY, spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body", fontName=FONT_CN, fontSize=9, leading=13,
            textColor=C_TEXT,
        ),
        "body_bold": ParagraphStyle(
            "body_bold", fontName=FONT_CN_BOLD, fontSize=9, leading=13,
            textColor=C_TEXT,
        ),
        "mono": ParagraphStyle(
            "mono", fontName="Courier", fontSize=9, leading=13,
            textColor=C_TEXT,
        ),
        "muted": ParagraphStyle(
            "muted", fontName=FONT_CN, fontSize=8, leading=11,
            textColor=C_MUTED,
        ),
        "badge_pass": ParagraphStyle(
            "badge_pass", fontName=FONT_CN_BOLD, fontSize=14, leading=18,
            textColor=C_WHITE, alignment=TA_CENTER,
        ),
        "badge_fail": ParagraphStyle(
            "badge_fail", fontName=FONT_CN_BOLD, fontSize=14, leading=18,
            textColor=C_WHITE, alignment=TA_CENTER,
        ),
        "pill": ParagraphStyle(
            "pill", fontName=FONT_CN, fontSize=8, leading=11,
            textColor=C_WHITE, alignment=TA_CENTER,
        ),
        "card_title": ParagraphStyle(
            "card_title", fontName=FONT_CN_BOLD, fontSize=10, leading=14,
            textColor=C_TEXT,
        ),
        "card_body": ParagraphStyle(
            "card_body", fontName=FONT_CN, fontSize=9, leading=12,
            textColor=C_TEXT,
        ),
        "card_value": ParagraphStyle(
            "card_value", fontName="Courier", fontSize=15, leading=20,
            textColor=C_TEXT, alignment=TA_CENTER,
        ),
        "card_label": ParagraphStyle(
            "card_label", fontName=FONT_CN, fontSize=8, leading=10,
            textColor=C_MUTED, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer", fontName=FONT_CN, fontSize=7, leading=9,
            textColor=C_MUTED, alignment=TA_CENTER,
        ),
    }


# ---------------------------------------------------------------------------
# Helper: format number
# ---------------------------------------------------------------------------
def _fmt(value: float | int | None, precision: int = 2, unit: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if abs(value) >= 1e4:
            s = f"{value:,.{precision}f}"
        elif abs(value) < 0.01 and value != 0:
            s = f"{value:.{precision}e}"
        else:
            s = f"{value:.{precision}f}"
    else:
        s = str(value)
    if unit:
        s += f" {unit}"
    return s


def _pass_text(passed: bool) -> str:
    return "通过" if passed else "不通过"


# ---------------------------------------------------------------------------
# Page template with footer
# ---------------------------------------------------------------------------
def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_CN, 7)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(
        PAGE_W / 2, 10 * mm,
        f"VDI 2230 螺栓校核工具 | 仅供工程参考，不替代专业判断 | 第 {doc.page} 页",
    )
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def _header_bar(styles: dict, date_str: str) -> Table:
    """Full-width colored header bar with title and date."""
    title = Paragraph("VDI 2230 螺栓连接校核报告", styles["title"])
    date_p = Paragraph(date_str, styles["title_date"])
    t = Table([[title, date_p]], colWidths=[CONTENT_W * 0.7, CONTENT_W * 0.3])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (-1, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def _verdict_block(styles: dict, overall_pass: bool, subtitle: str) -> Table:
    """Large pass/fail badge + subtitle."""
    badge_color = C_PASS if overall_pass else C_FAIL
    badge_text = "ALL PASS" if overall_pass else "FAIL"
    badge_style = styles["badge_pass"] if overall_pass else styles["badge_fail"]
    badge = Paragraph(badge_text, badge_style)
    sub = Paragraph(subtitle, styles["body"])

    t = Table([[badge, sub]], colWidths=[80, CONTENT_W - 80])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), badge_color),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (-1, -1), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (1, 0), (1, 0), C_LIGHT_PASS if overall_pass else C_LIGHT_FAIL),
    ]))
    return t


def _metric_cards(styles: dict, metrics: list[tuple[str, str]]) -> Table:
    """Row of 3~4 key metric mini cards."""
    n = len(metrics)
    col_w = CONTENT_W / n
    labels = []
    values = []
    for label, value in metrics:
        values.append(Paragraph(value, styles["card_value"]))
        labels.append(Paragraph(label, styles["card_label"]))

    t = Table([values, labels], colWidths=[col_w] * n)
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]
    for i in range(n):
        style_cmds.append(("BACKGROUND", (i, 0), (i, -1), C_BG if i % 2 == 0 else C_WHITE))
        if i < n - 1:
            style_cmds.append(("LINEAFTER", (i, 0), (i, -1), 0.5, colors.HexColor("#E0D8D0")))
    style_cmds.append(("ROUNDEDCORNERS", [4, 4, 4, 4]))
    t.setStyle(TableStyle(style_cmds))
    return t


def _check_pills(styles: dict, checks: dict, check_labels: dict, refs: dict) -> Table:
    """Horizontal row of pass/fail pills."""
    cells = []
    for key, label in check_labels.items():
        if key == "additional_load_ok":
            passed = refs.get("additional_load_ok", True)
            short = label.split("（")[0] if "（" in label else label
            color = C_MUTED
            text_str = f"{short}: {'通过' if passed else '超限'}(参考)"
        elif key in checks:
            passed = checks[key]
            short = label.split("（")[0] if "（" in label else label
            color = C_PASS if passed else C_FAIL
            text_str = f"{short}: {_pass_text(passed)}"
        else:
            continue
        cells.append(Paragraph(text_str, styles["pill"]))

    if not cells:
        return Spacer(1, 0)
    n = len(cells)
    col_w = CONTENT_W / n
    t = Table([cells], colWidths=[col_w] * n)
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]
    for i, key in enumerate(k for k in check_labels if k in checks or k == "additional_load_ok"):
        if key == "additional_load_ok":
            bg = C_MUTED
        elif checks.get(key, True):
            bg = C_PASS
        else:
            bg = C_FAIL
        style_cmds.append(("BACKGROUND", (i, 0), (i, 0), bg))
        style_cmds.append(("ROUNDEDCORNERS", [3, 3, 3, 3]))
    t.setStyle(TableStyle(style_cmds))
    return t


def _section_title(styles: dict, text: str) -> Paragraph:
    return Paragraph(text, styles["h2"])


def _input_table(styles: dict, rows: list[tuple[str, str]]) -> Table:
    """Compact input summary table with category labels."""
    data = []
    for label, value in rows:
        data.append([
            Paragraph(label, styles["body_bold"]),
            Paragraph(value, styles["body"]),
        ])
    t = Table(data, colWidths=[CONTENT_W * 0.2, CONTENT_W * 0.8])
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 8),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E0D8D0")),
    ]
    for i in range(len(data)):
        bg = C_BG if i % 2 == 0 else C_WHITE
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def _rstep_card(
    styles: dict,
    title: str,
    values: list[str],
    passed: bool | None = None,
    note: str = "",
) -> Table:
    """R-step card with left accent bar, title, values, and optional verdict pill."""
    accent = C_PASS if passed else C_FAIL if passed is not None else C_PRIMARY

    # Build content cell
    parts = [Paragraph(title, styles["card_title"])]
    for v in values:
        parts.append(Paragraph(v, styles["card_body"]))
    if note:
        parts.append(Paragraph(note, styles["muted"]))

    # Verdict pill
    if passed is not None:
        pill_color = C_PASS if passed else C_FAIL
        pill_text = _pass_text(passed)
        pill = Paragraph(pill_text, styles["pill"])
    else:
        pill = Paragraph("", styles["pill"])
        pill_color = None

    content_cell = []
    for p in parts:
        content_cell.append(p)

    # Use table layout: [accent_bar | content | verdict_pill]
    inner_parts = Paragraph("<br/>".join(
        f'<font face="{styles["card_title"].fontName}" size="10"><b>{title}</b></font>'
        if i == 0
        else f'<font face="{styles["card_body"].fontName}" size="9">{v}</font>'
        for i, v in enumerate([title] + values + ([f'<font color="#888888" size="8">{note}</font>'] if note else []))
    ), styles["card_body"])

    # Simpler approach: two-column table
    data = [[inner_parts, pill if passed is not None else ""]]
    t = Table(data, colWidths=[CONTENT_W - 60, 60])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), C_BG),
        ("VALIGN", (0, 0), (0, 0), "TOP"),
        ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (-1, -1), (-1, -1), 6),
        # Left accent bar
        ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]
    if pill_color is not None:
        style_cmds.append(("BACKGROUND", (1, 0), (1, 0), pill_color))
    t.setStyle(TableStyle(style_cmds))
    return t


def _kv_table(styles: dict, rows: list[tuple[str, str]], col_ratio: float = 0.5) -> Table:
    """Simple key-value table."""
    data = []
    for k, v in rows:
        data.append([Paragraph(k, styles["body"]), Paragraph(v, styles["mono"])])
    w1 = CONTENT_W * col_ratio
    w2 = CONTENT_W * (1 - col_ratio)
    t = Table(data, colWidths=[w1, w2])
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E0D8D0")),
    ]
    for i in range(len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


# ---------------------------------------------------------------------------
# Recommendations (standalone, no UI dependency)
# ---------------------------------------------------------------------------
def build_bolt_recommendations(result: Dict[str, Any]) -> list[str]:
    """Build recommendation strings from result dict."""
    checks = result.get("checks", {})
    recs: list[str] = []
    if not checks.get("residual_clamp_ok", True):
        recs.append("残余夹紧力不足：可加大预紧力、换更大螺栓或降低外载。")
    if not checks.get("assembly_von_mises_ok", True):
        recs.append("装配应力过高：可降低利用系数、换更高等级螺栓或减小摩擦。")
    if not checks.get("operating_axial_ok", True):
        recs.append("服役应力过高：可换更大螺栓、降低外载或提高螺栓等级。")
    if not checks.get("thermal_loss_ok", True):
        recs.append("热损失偏大：可补偿预紧力、优化材料热匹配或降低温差。")
    if not checks.get("fatigue_ok", True):
        recs.append("疲劳不通过：可降低应力幅、提高螺栓等级、优化载荷谱或增大规格。")
    if not checks.get("bearing_pressure_ok", True):
        recs.append("支承面压强超限：可加大垫圈、增大螺栓规格或选用更硬的被夹件材料。")
    strip = result.get("thread_strip", {})
    if not checks.get("thread_strip_ok", True):
        side = strip.get("critical_side", "")
        if side == "nut":
            recs.append("螺纹脱扣不通过（壳体侧）：可加深旋合深度、换更高强度壳体材料。")
        else:
            recs.append("螺纹脱扣不通过（螺栓侧）：可加深旋合深度或提高螺栓强度等级。")
    if not recs:
        recs.append("当前工况满足全部校核。建议保留 10% 以上工程裕量。")
    return recs


# ---------------------------------------------------------------------------
# Check labels (consistent with UI)
# ---------------------------------------------------------------------------
CHECK_LABELS = {
    "residual_clamp_ok": "残余夹紧力 R3",
    "assembly_von_mises_ok": "装配应力 R4",
    "operating_axial_ok": "服役应力 R5",
    "thermal_loss_ok": "温度影响",
    "fatigue_ok": "疲劳 R6",
    "bearing_pressure_ok": "支承面 R7",
    "thread_strip_ok": "脱扣 R8",
    "additional_load_ok": "附加载荷(参考)",
}

# ---------------------------------------------------------------------------
# Tightening method translation
# ---------------------------------------------------------------------------
_METHOD_CN = {
    "torque": "扭矩法",
    "angle": "转角法",
    "hydraulic": "液压拉伸法",
    "thermal": "热装法",
}

_JOINT_CN = {
    "tapped": "螺纹孔连接",
    "through": "通孔连接",
}

_LEVEL_CN = {
    "basic": "常规 (R3/R4/R5)",
    "thermal": "含温度影响",
    "fatigue": "含疲劳校核",
}

_MODE_CN = {
    "check": "校核模式",
    "design": "设计模式",
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

    # ── Header ──
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    elements.append(_header_bar(styles, date_str))
    elements.append(Spacer(1, 8))

    # ── Overall verdict ──
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

    # ── Key metrics ──
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

    # ── Check pills ──
    checks = result.get("checks", {})
    refs = result.get("references", {})
    elements.append(_check_pills(styles, checks, CHECK_LABELS, refs))
    elements.append(Spacer(1, 10))

    # ── Input summary ──
    elements.append(_section_title(styles, "输入参数"))
    fastener = payload.get("fastener", {})
    loads = payload.get("loads", {})
    assembly = payload.get("assembly", {})
    clamped = payload.get("clamped", {})
    stiffness = payload.get("stiffness", {})
    geom = result.get("derived_geometry_mm", {})

    input_rows = [
        ("紧固件", (
            f"M{fastener.get('d', '?')}x{fastener.get('p', '?')}"
            f"  Rp0.2 = {fastener.get('Rp02', '?')} MPa"
            f"  E = {fastener.get('E_bolt', '?')} MPa"
            f"  As = {_fmt(geom.get('As'), 2)} mm2"
            f"  d2 = {_fmt(geom.get('d2'), 2)} mm"
        )),
        ("外部载荷", (
            f"FA,max = {loads.get('FA_max', '?')} N"
            f"  FQ,max = {loads.get('FQ_max', 0)} N"
            + (f"  FK,seal = {loads.get('FK_seal', 0)} N" if loads.get("FK_seal") else "")
        )),
        ("装配条件", (
            f"{_METHOD_CN.get(method, method)}"
            f"  aA = {assembly.get('alpha_A', '?')}"
            f"  v = {assembly.get('utilization', '?')}"
            f"  muG = {assembly.get('mu_thread', '?')}"
            f"  muK = {assembly.get('mu_bearing', '?')}"
        )),
        ("被夹件", (
            f"层数: {clamped.get('part_count', 1)}"
            f"  lK = {clamped.get('total_thickness', '?')} mm"
            f"  模型: {clamped.get('basic_solid', 'cylinder')}"
            f"  DA = {clamped.get('D_A', '?')} mm"
        )),
    ]

    stiff_model = result.get("stiffness_model", {})
    if stiff_model.get("auto_modeled"):
        stiff_text = (
            f"自动计算  ds = {_fmt(stiff_model.get('delta_s_mm_per_n'), 2, 'e')} mm/N"
            f"  dp = {_fmt(stiff_model.get('delta_p_mm_per_n'), 2, 'e')} mm/N"
        )
    else:
        ds = stiffness.get("bolt_compliance") or stiffness.get("bolt_stiffness", "?")
        dp = stiffness.get("clamped_compliance") or stiffness.get("clamped_stiffness", "?")
        stiff_text = f"手动输入  ds = {ds}  dp = {dp}"
    input_rows.append(("柔度/刚度", stiff_text))

    elements.append(_input_table(styles, input_rows))
    elements.append(Spacer(1, 10))

    # ── Stiffness & force ratio ──
    elements.append(_section_title(styles, "柔度与力比"))
    phi_rows = [
        ("螺栓柔度 ds", _fmt(stiff_model.get("delta_s_mm_per_n"), 4, "mm/N")),
        ("被夹件柔度 dp", _fmt(stiff_model.get("delta_p_mm_per_n"), 4, "mm/N")),
        ("力比系数 phi", _fmt(inter.get("phi"), 4)),
        ("修正力比 phi_n", _fmt(inter.get("phi_n"), 4)),
        ("载荷导入系数 n", _fmt(stiff_model.get("n"), 2)),
    ]
    elements.append(_kv_table(styles, phi_rows, col_ratio=0.4))
    elements.append(Spacer(1, 8))

    # ── R1 Preload ──
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
        _rstep_card(styles, "R1 — 预紧力确定", r1_values),
        Spacer(1, 5),
    ]))

    # ── R2 Tightening torque ──
    r2_values = [
        f"MA,min = {_fmt(torque.get('MA_min_Nm'), 2)} N-m"
        f"    MA,max = {_fmt(torque.get('MA_max_Nm'), 2)} N-m",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R2 — 拧紧扭矩", r2_values),
        Spacer(1, 5),
    ]))

    # ── R3 Residual clamping ──
    r3_pass = checks.get("residual_clamp_ok")
    r3_values = [
        f"FK,res = {_fmt(forces.get('F_K_residual_N'), 1)} N"
        f"    FK,req = {_fmt(inter.get('F_K_required_N'), 1)} N",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R3 — 残余夹紧力", r3_values, r3_pass, result.get("r3_note", "")),
        Spacer(1, 5),
    ]))

    # ── R4 Assembly stress ──
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
        _rstep_card(styles, "R4 — 装配应力校核", r4_values, r4_pass),
        Spacer(1, 5),
    ]))

    # ── R5 Operating stress ──
    r5_pass = checks.get("operating_axial_ok")
    r5_values = [
        f"F_bolt_max = {_fmt(forces.get('F_bolt_work_max_N'), 1)} N",
        f"sigma_vm_work = {_fmt(stresses.get('sigma_vm_work'), 1)} MPa"
        f"    sigma_allow = {_fmt(stresses.get('sigma_allow_work'), 1)} MPa",
    ]
    elements.append(KeepTogether([
        _rstep_card(styles, "R5 — 服役应力校核", r5_values, r5_pass),
        Spacer(1, 5),
    ]))

    # ── R7 Bearing pressure (if active) ──
    if "bearing_pressure_ok" in checks:
        r7_pass = checks["bearing_pressure_ok"]
        r7_values = [
            f"p_bearing = {_fmt(stresses.get('p_bearing'), 1)} MPa"
            f"    p_allow = {_fmt(stresses.get('p_G_allow'), 1)} MPa"
            f"    A_bearing = {_fmt(stresses.get('A_bearing_mm2'), 1)} mm2",
        ]
        elements.append(KeepTogether([
            _rstep_card(styles, "R7 — 支承面压强", r7_values, r7_pass, result.get("r7_note", "")),
            Spacer(1, 5),
        ]))

    # ── R8 Thread stripping (if active) ──
    strip = result.get("thread_strip", {})
    if "thread_strip_ok" in checks:
        r8_pass = checks["thread_strip_ok"]
        side_cn = "螺栓侧" if strip.get("critical_side") == "bolt" else "螺母/壳体侧"
        r8_values = [
            f"安全系数 = {_fmt(strip.get('strip_safety'), 2)}"
            f"    要求 >= {_fmt(strip.get('strip_safety_required'), 2)}",
            f"F_strip_bolt = {_fmt(strip.get('F_strip_bolt_N'), 0)} N"
            f"    F_strip_nut = {_fmt(strip.get('F_strip_nut_N'), 0)} N",
            f"临界侧: {side_cn}",
        ]
        elements.append(KeepTogether([
            _rstep_card(styles, "R8 — 螺纹脱扣", r8_values, r8_pass, result.get("r8_note", "")),
            Spacer(1, 5),
        ]))

    # ── Thermal (if active) ──
    if check_level in ("thermal", "fatigue"):
        elements.append(Spacer(1, 4))
        elements.append(_section_title(styles, "温度影响"))
        th_rows = [
            ("热损失", _fmt(thermal.get("thermal_loss_effective_N"), 1, "N")),
            ("热损失占比", _fmt(thermal.get("thermal_loss_ratio"), 3)),
            ("螺栓热膨胀系数", _fmt(thermal.get("alpha_bolt"), 2, "1e-6/K")),
            ("被夹件热膨胀系数", _fmt(thermal.get("alpha_parts"), 2, "1e-6/K")),
        ]
        if thermal.get("thermal_auto_estimated"):
            th_rows.append(("自动估算值", _fmt(thermal.get("thermal_auto_value_N"), 1, "N")))
        elements.append(_kv_table(styles, th_rows, col_ratio=0.4))
        elements.append(Spacer(1, 5))

    # ── R6 Fatigue (if active) ──
    fatigue = result.get("fatigue", {})
    if check_level == "fatigue" and "fatigue_ok" in checks:
        r6_pass = checks["fatigue_ok"]
        treatment_cn = {"rolled": "轧制螺纹", "cut": "切削螺纹"}.get(
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
            _rstep_card(styles, "R6 — 疲劳校核 (简化 Goodman)", r6_values, r6_pass),
            Spacer(1, 5),
        ]))

    # ── Warnings ──
    warnings = result.get("warnings", [])
    if warnings:
        elements.append(Spacer(1, 4))
        elements.append(_section_title(styles, "警告"))
        for w in warnings:
            elements.append(Paragraph(f"  {w}", styles["body"]))
            elements.append(Spacer(1, 2))

    # ── Recommendations ──
    recs = build_bolt_recommendations(result)
    elements.append(Spacer(1, 4))
    elements.append(_section_title(styles, "建议"))
    for r in recs:
        elements.append(Paragraph(f"  {r}", styles["body"]))
        elements.append(Spacer(1, 2))

    # ── Scope note ──
    scope = result.get("scope_note", "")
    if scope:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(scope, styles["muted"]))

    # ── Build PDF ──
    frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B, id="main")
    template = PageTemplate(id="report", frames=[frame], onPage=_footer)
    doc = BaseDocTemplate(str(path), pagesize=A4, pageTemplates=[template])
    doc.build(elements)
