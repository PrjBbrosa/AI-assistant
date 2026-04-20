"""Shared font configuration for the desktop UI."""

from __future__ import annotations

import platform

from PySide6.QtGui import QFont


def _build_ui_font_families() -> list[str]:
    """Prefer Microsoft YaHei on Windows while keeping cross-platform fallbacks."""
    if platform.system() == "Windows":
        return ["Microsoft YaHei", "Microsoft YaHei UI", "DengXian", "Segoe UI"]
    if platform.system() == "Darwin":
        return ["PingFang SC", "Hiragino Sans GB", "Avenir Next", "Helvetica Neue"]
    return ["Noto Sans CJK SC", "DengXian", "Microsoft YaHei UI", "Segoe UI"]


def _build_css_font_family(families: list[str]) -> str:
    return ", ".join(f'"{family}"' for family in families)


def _build_svg_font_family(families: list[str]) -> str:
    return ", ".join(f"'{family}'" if " " in family else family for family in families) + ", sans-serif"


UI_FONT_FAMILIES = _build_ui_font_families()
UI_FONT_FAMILY_CSS = _build_css_font_family(UI_FONT_FAMILIES)
UI_FONT_FAMILY_SVG = _build_svg_font_family(UI_FONT_FAMILIES)


def make_ui_font(
    point_size: int,
    weight: QFont.Weight | int = QFont.Weight.Normal,
) -> QFont:
    """Create a UI font with an explicit Windows-friendly fallback chain."""
    font = QFont()
    if hasattr(font, "setFamilies"):
        font.setFamilies(UI_FONT_FAMILIES)
    else:  # pragma: no cover - kept for older Qt bindings.
        font.setFamily(UI_FONT_FAMILIES[0])
    font.setPointSize(point_size)
    font.setWeight(QFont.Weight(weight))
    return font


def _build_matplotlib_cjk_chain() -> list[str]:
    """Font chain matplotlib can resolve on each platform for CJK labels."""
    if platform.system() == "Windows":
        return ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    if platform.system() == "Darwin":
        # Hiragino Sans GB / Arial Unicode MS are the two reliably
        # matplotlib-discoverable CJK fonts on stock macOS.
        return ["Hiragino Sans GB", "Arial Unicode MS", "Songti SC", "DejaVu Sans"]
    return ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]


_MPL_CONFIGURED = False


def configure_matplotlib_fonts() -> None:
    """Make matplotlib use a CJK-capable font so Chinese labels render.

    Silences the stream of `Glyph XXXX missing from font(s) DejaVu Sans`
    warnings emitted by the worm-gear stress curves at startup.
    """
    global _MPL_CONFIGURED
    if _MPL_CONFIGURED:
        return
    import matplotlib  # local import: matplotlib is optional until widgets load

    chain = _build_matplotlib_cjk_chain()
    matplotlib.rcParams["font.sans-serif"] = chain
    matplotlib.rcParams["font.family"] = "sans-serif"
    # Fix minus-sign rendering when a CJK font replaces DejaVu.
    matplotlib.rcParams["axes.unicode_minus"] = False
    _MPL_CONFIGURED = True
