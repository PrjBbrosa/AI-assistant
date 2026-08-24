"""Cloud Porcelain token contract and stylesheet structure tests."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtGui import QColor

from app.ui.design_tokens import (
    CloudPorcelainPalette,
    contrast_ratio,
    cloud_porcelain_controls,
    cloud_porcelain_palette,
    cloud_porcelain_radii,
    cloud_porcelain_shadows,
    cloud_porcelain_spacing,
    matplotlib_palette,
    qbrush,
    qcolor,
    qpen,
    qss_rgba,
    svg_palette,
)
from app.ui.theme import apply_theme, build_style_sheet


ROOT = Path(__file__).resolve().parents[2]
WAVE1_FILES = (
    ROOT / "app" / "ui" / "design_tokens.py",
    ROOT / "app" / "ui" / "theme.py",
    ROOT / "app" / "ui" / "widgets" / "cloud_canvas.py",
)
OLD_BEIGE_HEXES = ("#F7F5F2", "#EEE7DE", "#FBF8F3")
REQUIRED_SELECTORS = (
    "QMainWindow",
    "QFrame#SidebarPanel",
    "QFrame#Card",
    "QFrame#SubCard",
    "QFrame#AutoCalcCard",
    "QFrame#DisabledSubCard",
    "QFrame#WarningCard",
    "QLineEdit#InputField",
    "QLineEdit#InputField:hover",
    "QLineEdit#InputField:focus",
    '[fieldError="true"]',
    ":disabled",
    ":read-only",
    "QPushButton#PrimaryButton",
    "QPushButton#SecondaryButton",
    "QPushButton#LinkButton",
    "QLabel#GuideTitle",
    "QLabel#GuideFlowArrow",
    "QDialog#HelpPopover",
    "PassBadge",
    "FailBadge",
    "WaitBadge",
    "RefBadge",
    "IncompleteBadge",
    "HelpButton",
    "ModuleList",
    "ChapterList",
    "HelpPopoverRoot",
)

EXACT_COLORS = {
    "canvas_outer": "#DFE3E5",
    "canvas_base": "#EFF0EF",
    "surface_glass": "rgba(252,252,250,0.68)",
    "surface_glass_strong": "rgba(253,252,249,0.88)",
    "surface_glass_soft": "rgba(249,249,247,0.50)",
    "surface_field": "rgba(255,255,253,0.76)",
    "ink_primary": "#282624",
    "ink_muted": "#716D68",
    "ink_quiet": "#96908A",
    "line_highlight": "rgba(255,255,255,0.86)",
    "line_structural": "rgba(91,82,74,0.16)",
    "accent": "#C76C4D",
    "accent_action": "#B75D40",
    "accent_hover": "#A95338",
    "accent_soft": "#F2D8CF",
    "accent_ink": "#733C2B",
    "secondary": "#71868A",
    "secondary_soft": "#DCE7E8",
    "focus_ring": "rgba(199,108,77,0.18)",
    "pass_fg": "#2B715C",
    "pass_bg": "#D8EBE4",
    "fail_fg": "#9D4939",
    "fail_bg": "#F2D9D3",
    "incomplete_fg": "#946525",
    "incomplete_bg": "#F3E5C9",
    "not_checked_fg": "#6F716E",
    "not_checked_bg": "#E5E6E3",
    "reference_only_fg": "#566B72",
    "reference_only_bg": "#DEE7E9",
    "warning_fg": "#9B672F",
    "warning_bg": "#F2E3CF",
    "input_error_fg": "#A33F35",
    "input_error_bg": "#F5DEDA",
}


def test_palette_matches_spec_token_values() -> None:
    palette = cloud_porcelain_palette()
    assert isinstance(palette, CloudPorcelainPalette)
    for name, expected in EXACT_COLORS.items():
        assert getattr(palette, name) == expected, name
    assert cloud_porcelain_palette() is palette


def test_geometry_tokens_match_spec() -> None:
    radii = cloud_porcelain_radii()
    spacing = cloud_porcelain_spacing()
    controls = cloud_porcelain_controls()
    shadows = cloud_porcelain_shadows()

    assert radii.radius_sidebar == 22
    assert radii.radius_primary == 20
    assert radii.radius_panel == 14
    assert radii.radius_control == 10
    assert radii.radius_badge == 999
    assert radii.radius_small == 8

    assert spacing.grid == 4
    assert spacing.canvas_margin == 12
    assert spacing.sidebar_gap == 12
    assert spacing.sidebar_width == 228
    assert spacing.sidebar_min == 212
    assert spacing.sidebar_max == 280
    assert spacing.card_padding == 16
    assert spacing.subcard_padding == 12

    assert controls.module_item_height == 40
    assert controls.header_min_height == 78
    assert controls.button_height == 32
    assert controls.primary_button_height == 34
    assert controls.input_height == 36
    assert controls.icon_hit == 32
    assert controls.icon_hit_min == 28
    assert controls.help_button_outer == 24
    assert controls.help_button_inner == 22

    assert shadows.color == "rgba(70,63,57,0.16)"
    assert shadows.color_soft == "rgba(70,63,57,0.08)"


def test_qss_rgba_serializes_opaque_hex_and_spec_alpha() -> None:
    palette = cloud_porcelain_palette()
    assert qss_rgba(palette.canvas_base) == "#EFF0EF"
    assert qss_rgba(palette.surface_glass) == "rgba(252,252,250,0.68)"
    assert qss_rgba("accent_action") == "#B75D40"
    brush = qbrush(palette.accent)
    pen = qpen(palette.secondary, width=1.0)
    assert brush.color() == qcolor(palette.accent)
    assert pen.color() == qcolor(palette.secondary)


def test_white_on_accent_action_meets_contrast() -> None:
    ratio = contrast_ratio("#FFFFFF", cloud_porcelain_palette().accent_action)
    assert ratio >= 4.5
    accent_ratio = contrast_ratio("#FFFFFF", cloud_porcelain_palette().accent)
    assert accent_ratio < 4.5


def test_fail_color_is_not_accent() -> None:
    palette = cloud_porcelain_palette()
    assert palette.fail_fg != palette.accent
    assert palette.fail_fg == "#9D4939"
    assert palette.accent == "#C76C4D"
    assert palette.accent_action == "#B75D40"


def test_build_style_sheet_contains_required_selectors() -> None:
    stylesheet = build_style_sheet(cloud_porcelain_palette())
    for selector in REQUIRED_SELECTORS:
        assert selector in stylesheet, selector


def test_help_button_qss_keeps_22px_inner_contract() -> None:
    stylesheet = build_style_sheet(cloud_porcelain_palette())
    match = re.search(
        r"QToolButton#HelpButton \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    assert "min-width: 22px" in body
    assert "max-width: 22px" in body
    assert "min-height: 22px" in body
    assert "max-height: 22px" in body
    assert "border-radius: 12px" in body
    assert "padding: 0" in body
    assert "QSS width excludes the 1px border; outer geometry remains 24px." in body


def test_primary_button_uses_accent_action_not_accent_fill() -> None:
    stylesheet = build_style_sheet(cloud_porcelain_palette())
    match = re.search(
        r"QPushButton#PrimaryButton \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    assert "#B75D40" in body
    assert "background-color: #B75D40" in body
    assert "#C76C4D" not in body
    hover = re.search(
        r"QPushButton#PrimaryButton:hover \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    pressed = re.search(
        r"QPushButton#PrimaryButton:pressed \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    assert hover is not None and pressed is not None
    assert "#A95338" in hover.group("body")
    assert "#A95338" not in pressed.group("body")
    assert "#B75D40" not in pressed.group("body")


def test_input_focus_uses_focus_ring_not_only_accent_border() -> None:
    stylesheet = build_style_sheet(cloud_porcelain_palette())
    match = re.search(
        r"QLineEdit#InputField:focus \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    assert "rgba(199,108,77,0.18)" in body
    assert "4px solid" in body
    assert "border: 1px solid #C76C4D" not in body


def test_status_bar_is_not_a_pass_banner() -> None:
    stylesheet = build_style_sheet(cloud_porcelain_palette())
    match = re.search(
        r"QStatusBar \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    assert match is not None
    body = match.group("body")
    palette = cloud_porcelain_palette()
    assert qss_rgba(palette.pass_bg) not in body
    assert qss_rgba(palette.fail_bg) not in body
    assert qss_rgba(palette.canvas_base) in body


def test_auto_calc_card_uses_secondary_soft() -> None:
    stylesheet = build_style_sheet(cloud_porcelain_palette())
    match = re.search(
        r"QFrame#AutoCalcCard \{(?P<body>.*?)\}",
        stylesheet,
        flags=re.DOTALL,
    )
    assert match is not None
    assert "#DCE7E8" in match.group("body")


def test_matplotlib_and_svg_palettes_use_token_entry() -> None:
    mpl = matplotlib_palette()
    svg = svg_palette()
    assert mpl["accent"] == "#C76C4D"
    assert mpl["accent_action"] == "#B75D40"
    assert svg["surface_glass"] == "rgba(252,252,250,0.68)"
    assert svg["canvas_base"] == "#EFF0EF"


def test_wave1_files_have_no_old_beige_literals() -> None:
    for path in WAVE1_FILES:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        for hex_value in OLD_BEIGE_HEXES:
            assert hex_value.lower() not in lowered, f"{path} contains {hex_value}"


def test_build_style_sheet_is_pure_and_stable() -> None:
    first = build_style_sheet(cloud_porcelain_palette())
    second = build_style_sheet(cloud_porcelain_palette())
    assert first == second
    assert first.strip()


def test_apply_theme_skips_identical_stylesheet() -> None:
    class _Font:
        def __init__(self) -> None:
            self._families: list[str] = []

        def families(self) -> list[str]:
            return self._families

        def setFamilies(self, families: list[str]) -> None:
            self._families = list(families)

    class _App:
        def __init__(self) -> None:
            self.value = ""
            self.apply_count = 0
            self.font_value = _Font()

        def font(self) -> _Font:
            return self.font_value

        def setFont(self, font: _Font) -> None:
            self.font_value = font

        def styleSheet(self) -> str:
            return self.value

        def setStyleSheet(self, value: str) -> None:
            self.value = value
            self.apply_count += 1

    app = _App()
    apply_theme(app)  # type: ignore[arg-type]
    apply_theme(app)  # type: ignore[arg-type]
    assert app.apply_count == 1
    assert app.value == build_style_sheet(cloud_porcelain_palette())
