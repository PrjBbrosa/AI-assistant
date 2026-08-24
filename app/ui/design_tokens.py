"""Cloud Porcelain design tokens — single source of truth for UI color and geometry.

Pages and widgets must import from this module instead of inventing parallel
hex palettes. This module stays QtGui-only (QColor / QBrush / QPen).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen


_RGBA_RE = re.compile(
    r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9]*\.?[0-9]+)\s*\)$",
    re.IGNORECASE,
)
_RGB_RE = re.compile(
    r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CloudPorcelainPalette:
    """Spec §6.1–§6.3 color tokens. Values are CSS hex or rgba strings."""

    canvas_outer: str = "#DFE3E5"
    canvas_base: str = "#EFF0EF"
    surface_glass: str = "rgba(252,252,250,0.68)"
    surface_glass_strong: str = "rgba(253,252,249,0.88)"
    surface_glass_soft: str = "rgba(249,249,247,0.50)"
    surface_field: str = "rgba(255,255,253,0.76)"
    ink_primary: str = "#282624"
    ink_muted: str = "#716D68"
    ink_quiet: str = "#96908A"
    line_highlight: str = "rgba(255,255,255,0.86)"
    line_structural: str = "rgba(91,82,74,0.16)"

    accent: str = "#C76C4D"
    accent_action: str = "#B75D40"
    accent_hover: str = "#A95338"
    accent_soft: str = "#F2D8CF"
    accent_ink: str = "#733C2B"
    secondary: str = "#71868A"
    secondary_soft: str = "#DCE7E8"
    focus_ring: str = "rgba(199,108,77,0.18)"

    pass_fg: str = "#2B715C"
    pass_bg: str = "#D8EBE4"
    fail_fg: str = "#9D4939"
    fail_bg: str = "#F2D9D3"
    incomplete_fg: str = "#946525"
    incomplete_bg: str = "#F3E5C9"
    not_checked_fg: str = "#6F716E"
    not_checked_bg: str = "#E5E6E3"
    reference_only_fg: str = "#566B72"
    reference_only_bg: str = "#DEE7E9"
    warning_fg: str = "#9B672F"
    warning_bg: str = "#F2E3CF"
    input_error_fg: str = "#A33F35"
    input_error_bg: str = "#F5DEDA"


@dataclass(frozen=True)
class CloudPorcelainRadii:
    """Spec §6.5 corner radii in device-independent pixels."""

    radius_window_reference: int = 30
    radius_sidebar: int = 22
    radius_primary: int = 20
    radius_panel: int = 14
    radius_control: int = 10
    radius_badge: int = 999
    radius_small: int = 8


@dataclass(frozen=True)
class CloudPorcelainSpacing:
    """Spec §6.6 spacing grid and shell metrics, in device-independent pixels."""

    grid: int = 4
    canvas_margin: int = 12
    sidebar_gap: int = 12
    sidebar_width: int = 228
    sidebar_min: int = 212
    sidebar_max: int = 280
    card_padding: int = 16
    subcard_padding: int = 12


@dataclass(frozen=True)
class CloudPorcelainControls:
    """Spec §6.6 control heights and HelpButton geometry contract."""

    module_item_height: int = 40
    header_min_height: int = 78
    button_height: int = 32
    primary_button_height: int = 34
    input_height: int = 36
    icon_hit: int = 32
    icon_hit_min: int = 28
    help_button_outer: int = 24
    help_button_inner: int = 22


@dataclass(frozen=True)
class CloudPorcelainShadows:
    """Painter/effect shadow spec. Qt QSS cannot emit CSS box-shadow."""

    color: str = "rgba(70,63,57,0.16)"
    color_soft: str = "rgba(70,63,57,0.08)"
    shell_y_offset: int = 8
    shell_blur: int = 24
    raised_y_offset: int = 4
    raised_blur: int = 12


_PALETTE = CloudPorcelainPalette()
_RADII = CloudPorcelainRadii()
_SPACING = CloudPorcelainSpacing()
_CONTROLS = CloudPorcelainControls()
_SHADOWS = CloudPorcelainShadows()


def cloud_porcelain_palette() -> CloudPorcelainPalette:
    """Readonly Cloud Porcelain color palette (single process-wide instance)."""
    return _PALETTE


def cloud_porcelain_radii() -> CloudPorcelainRadii:
    return _RADII


def cloud_porcelain_spacing() -> CloudPorcelainSpacing:
    return _SPACING


def cloud_porcelain_controls() -> CloudPorcelainControls:
    return _CONTROLS


def cloud_porcelain_shadows() -> CloudPorcelainShadows:
    return _SHADOWS


def _parse_css_color(spec: str) -> QColor:
    text = spec.strip()
    if text.startswith("#"):
        color = QColor(text)
        if not color.isValid():
            raise ValueError(f"invalid color spec: {spec!r}")
        return color
    rgba = _RGBA_RE.match(text)
    if rgba is not None:
        red, green, blue = (int(rgba.group(index)) for index in (1, 2, 3))
        alpha = float(rgba.group(4))
        color = QColor(red, green, blue)
        color.setAlphaF(max(0.0, min(1.0, alpha)))
        return color
    rgb = _RGB_RE.match(text)
    if rgb is not None:
        red, green, blue = (int(rgb.group(index)) for index in (1, 2, 3))
        return QColor(red, green, blue)
    raise ValueError(f"invalid color spec: {spec!r}")


def qcolor(token_or_spec: str | QColor) -> QColor:
    """Resolve a palette field name, CSS spec, or QColor to a QColor copy."""
    if isinstance(token_or_spec, QColor):
        return QColor(token_or_spec)
    spec = token_or_spec.strip()
    if spec.startswith("#") or spec.lower().startswith("rgb"):
        return _parse_css_color(spec)
    palette = cloud_porcelain_palette()
    if hasattr(palette, spec):
        return _parse_css_color(getattr(palette, spec))
    raise ValueError(f"unknown color token or spec: {token_or_spec!r}")


def qbrush(
    token_or_spec: str | QColor,
    style: Qt.BrushStyle = Qt.BrushStyle.SolidPattern,
) -> QBrush:
    return QBrush(qcolor(token_or_spec), style)


def qpen(
    token_or_spec: str | QColor,
    width: float = 1.0,
    style: Qt.PenStyle = Qt.PenStyle.SolidLine,
) -> QPen:
    pen = QPen(qcolor(token_or_spec))
    pen.setWidthF(width)
    pen.setStyle(style)
    return pen


def qss_rgba(color: QColor | str) -> str:
    """Serialize a color for QSS: opaque as #RRGGBB, else rgba(r,g,b,a)."""
    parsed = qcolor(color)
    if parsed.alpha() >= 255:
        return f"#{parsed.red():02X}{parsed.green():02X}{parsed.blue():02X}"
    alpha_txt = f"{parsed.alphaF():.2f}"
    return f"rgba({parsed.red()},{parsed.green()},{parsed.blue()},{alpha_txt})"


def relative_luminance(token_or_spec: str | QColor) -> float:
    """WCAG relative luminance of an sRGB color."""

    def _linearize(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    parsed = qcolor(token_or_spec)
    return (
        0.2126 * _linearize(parsed.redF())
        + 0.7152 * _linearize(parsed.greenF())
        + 0.0722 * _linearize(parsed.blueF())
    )


def contrast_ratio(foreground: str | QColor, background: str | QColor) -> float:
    """WCAG contrast ratio between two colors."""
    lighter = relative_luminance(foreground)
    darker = relative_luminance(background)
    if darker > lighter:
        lighter, darker = darker, lighter
    return (lighter + 0.05) / (darker + 0.05)


def matplotlib_palette() -> dict[str, str]:
    """Hex colors (with alpha when needed) for matplotlib artists."""
    palette = cloud_porcelain_palette()
    resolved: dict[str, str] = {}
    for field in fields(palette):
        parsed = qcolor(getattr(palette, field.name))
        if parsed.alpha() >= 255:
            resolved[field.name] = (
                f"#{parsed.red():02X}{parsed.green():02X}{parsed.blue():02X}"
            )
        else:
            resolved[field.name] = (
                f"#{parsed.red():02X}{parsed.green():02X}"
                f"{parsed.blue():02X}{parsed.alpha():02X}"
            )
    return resolved


def svg_palette() -> dict[str, str]:
    """CSS color strings for SVG fill/stroke interpolation."""
    palette = cloud_porcelain_palette()
    return {
        field.name: qss_rgba(getattr(palette, field.name))
        for field in fields(palette)
    }
