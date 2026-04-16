"""Common PDF report primitives shared across all modules.

Provides color palette, page layout constants, font registration,
paragraph styles, formatting helpers, and reusable building blocks
(header bar, verdict badge, metric cards, check pills, tables, etc.).
"""

from __future__ import annotations

import os
from typing import Any, Callable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
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
C_INCOMPLETE = colors.HexColor("#F6A623")  # 橙色：三态校核中的"未校核/不完整"
C_TEXT = colors.HexColor("#2D2D2D")
C_MUTED = colors.HexColor("#888888")
C_WHITE = colors.HexColor("#FFFFFF")
C_LIGHT_PASS = colors.HexColor("#E8F5E9")
C_LIGHT_FAIL = colors.HexColor("#FFEBEE")
C_LIGHT_INCOMPLETE = colors.HexColor("#FFF4E5")  # 浅橙，三态副标题背景

# ---------------------------------------------------------------------------
# Page layout constants
# ---------------------------------------------------------------------------
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
    return "\u901a\u8fc7" if passed else "\u4e0d\u901a\u8fc7"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def _header_bar(styles: dict, title: str, date_str: str) -> Table:
    """Full-width colored header bar with title and date."""
    title_p = Paragraph(title, styles["title"])
    date_p = Paragraph(date_str, styles["title_date"])
    t = Table([[title_p, date_p]], colWidths=[CONTENT_W * 0.7, CONTENT_W * 0.3])
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


def _verdict_block(
    styles: dict,
    overall_pass: bool | str,
    subtitle: str,
) -> Table:
    """Large verdict badge + subtitle.

    For backward compatibility the first argument may still be a bool
    (True = pass, False = fail). Callers that need the tri-state
    semantics (pass / fail / incomplete) may pass the string
    ``overall_status`` directly. ``incomplete`` renders in orange with a
    "校核不完整" badge so PDF reports match the UI tri-state (Codex
    follow-up 2026-04-16).
    """
    if isinstance(overall_pass, str):
        status = overall_pass
    else:
        status = "pass" if overall_pass else "fail"

    if status == "pass":
        badge_color = C_PASS
        badge_text = "ALL PASS"
        badge_style = styles["badge_pass"]
        sub_bg = C_LIGHT_PASS
    elif status == "incomplete":
        badge_color = C_INCOMPLETE
        badge_text = "校核不完整"
        # reuse badge_fail style for white text on coloured background
        badge_style = styles["badge_fail"]
        sub_bg = C_LIGHT_INCOMPLETE
    else:  # fail (and any unknown falls here)
        badge_color = C_FAIL
        badge_text = "FAIL"
        badge_style = styles["badge_fail"]
        sub_bg = C_LIGHT_FAIL

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
        ("BACKGROUND", (1, 0), (1, 0), sub_bg),
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
    """Horizontal row of check pills.

    Supports a three-state ``checks[key]`` value (Codex follow-up 2026-04-16):
      * ``True``  -> green "通过"
      * ``False`` -> red   "不通过"
      * ``None``  -> grey  "未校核"

    The pill background is chosen accordingly so unchecked items no longer
    render as red FAIL in PDF exports.
    """
    cells = []
    for key, label in check_labels.items():
        if key == "additional_load_ok":
            passed = refs.get("additional_load_ok", True)
            short = label.split("\uff08")[0] if "\uff08" in label else label
            text_str = f"{short}: {'\u901a\u8fc7' if passed else '\u8d85\u9650'}(\u53c2\u8003)"
        elif key in checks:
            raw = checks[key]
            short = label.split("\uff08")[0] if "\uff08" in label else label
            if raw is None:
                text_str = f"{short}: \u672a\u6821\u6838"  # 未校核
            else:
                text_str = f"{short}: {_pass_text(bool(raw))}"
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
        else:
            raw = checks.get(key)
            if raw is None:
                bg = C_MUTED
            elif raw:
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
# Footer factory
# ---------------------------------------------------------------------------
def make_footer(tool_name: str) -> Callable:
    """Return a footer callback for BaseDocTemplate with the given tool name."""
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT_CN, 7)
        canvas.setFillColor(C_MUTED)
        canvas.drawCentredString(
            PAGE_W / 2, 10 * mm,
            f"{tool_name} | \u4ec5\u4f9b\u5de5\u7a0b\u53c2\u8003\uff0c\u4e0d\u66ff\u4ee3\u4e13\u4e1a\u5224\u65ad | \u7b2c {doc.page} \u9875",
        )
        canvas.restoreState()
    return _footer


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------
def build_pdf(path, elements: list, tool_name: str) -> None:
    """Create a BaseDocTemplate with standard layout and footer, then build."""
    _register_fonts()
    footer = make_footer(tool_name)
    frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B, id="main")
    template = PageTemplate(id="report", frames=[frame], onPage=footer)
    doc = BaseDocTemplate(str(path), pagesize=A4, pageTemplates=[template])
    doc.build(elements)
