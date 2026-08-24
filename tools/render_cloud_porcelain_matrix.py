#!/usr/bin/env python3
"""Wave 7 Cloud Porcelain render / geometry matrix.

Writes screenshots, overlay crops, and a numeric parity table under an
explicit temp directory (default /tmp). Never writes into the repo.

Offscreen is the default QPA. Popup capture failures are logged as 未验证
and do not fail the process. macOS cocoa shots are optional via --macos-fg.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = Path("/tmp/cloud-porcelain-baseline/screenshots/w7-offscreen")
DEFAULT_OVERLAY = Path("/tmp/cloud-porcelain-baseline/w7-overlay")
DEFAULT_PARITY = Path("/tmp/cloud-porcelain-baseline/W7-PARITY.md")
DEFAULT_LOG = Path("/tmp/cloud-porcelain-baseline/w7-render-log.txt")
DEFAULT_MACOS_FG = Path("/tmp/cloud-porcelain-baseline/screenshots/w7-macos-fg")
HTML_MOCKUP = REPO_ROOT / "docs" / "ui-mockups" / "claude-glass-theme-options.html"
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

MODULES: tuple[tuple[int, str, str, str], ...] = (
    (0, "bolt", "input_case_01.json", "_calculate"),
    (1, "bolt_tapped_axial", "tapped_axial_joint_case_01.json", "_run_calculation"),
    (2, "interference", "interference_case_01.json", "_calculate"),
    (3, "spline", "spline_case_01.json", "_on_calculate"),
    (4, "worm", "worm_case_01.json", "_calculate"),
    (5, "hertz", "hertz_case_01.json", "_calculate"),
    (6, "buffer", "buffer_energy_case_01.csv", "_on_calculate"),
)

OLD_BEIGE = (0xEE, 0xE7, 0xDE)
CANVAS_BASE_RGB = (0xEF, 0xF0, 0xEF)
ACCENT_ACTION_RGB = (0xB7, 0x5D, 0x40)
ACCENT_RGB = (0xC7, 0x6C, 0x4D)
ACCENT_SOFT_RGB = (0xF2, 0xD8, 0xCF)
GREEN_READY = (0x2B, 0x71, 0x5C)


# ---------------------------------------------------------------------------
# Color math (CIEDE2000)
# ---------------------------------------------------------------------------


def rgb_tuple(color: Any) -> tuple[int, int, int]:
    return (int(color.red()), int(color.green()), int(color.blue()))


def rgb_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _srgb_to_linear(channel: float) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    red, green, blue = (_srgb_to_linear(c) for c in rgb)
    x = red * 0.4124564 + green * 0.3575761 + blue * 0.1804375
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = red * 0.0193339 + green * 0.1191920 + blue * 0.9503041
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    def _f(t: float) -> float:
        delta = 6.0 / 29.0
        if t > delta**3:
            return t ** (1.0 / 3.0)
        return t / (3.0 * delta * delta) + 4.0 / 29.0

    fx, fy, fz = _f(x / xn), _f(y / yn), _f(z / zn)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e2000(
    rgb_a: tuple[int, int, int], rgb_b: tuple[int, int, int]
) -> float:
    """CIEDE2000 colour difference (Sharma et al. 2005), kL=kC=kH=1."""

    L1, a1, b1 = rgb_to_lab(rgb_a)
    L2, a2, b2 = rgb_to_lab(rgb_b)
    avg_l = (L1 + L2) / 2.0
    c1 = math.sqrt(a1 * a1 + b1 * b1)
    c2 = math.sqrt(a2 * a2 + b2 * b2)
    avg_c = (c1 + c2) / 2.0
    g = 0.5 * (1.0 - math.sqrt(avg_c**7 / (avg_c**7 + 25.0**7)))
    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = math.sqrt(a1p * a1p + b1 * b1)
    c2p = math.sqrt(a2p * a2p + b2 * b2)
    avg_cp = (c1p + c2p) / 2.0

    def _atan2(bb: float, aa: float) -> float:
        if bb == 0.0 and aa == 0.0:
            return 0.0
        value = math.degrees(math.atan2(bb, aa))
        return value + 360.0 if value < 0.0 else value

    h1p = _atan2(b1, a1p)
    h2p = _atan2(b2, a2p)
    delta_lp = L2 - L1
    delta_cp = c2p - c1p
    if c1p * c2p == 0.0:
        delta_hp = 0.0
    else:
        diff = h2p - h1p
        if diff > 180.0:
            diff -= 360.0
        elif diff < -180.0:
            diff += 360.0
        delta_hp = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(diff) / 2.0)

    if c1p * c2p == 0.0:
        avg_hp = h1p + h2p
    else:
        diff = abs(h1p - h2p)
        if diff <= 180.0:
            avg_hp = (h1p + h2p) / 2.0
        elif h1p + h2p < 360.0:
            avg_hp = (h1p + h2p + 360.0) / 2.0
        else:
            avg_hp = (h1p + h2p - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(avg_hp - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * avg_hp))
        + 0.32 * math.cos(math.radians(3.0 * avg_hp + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * avg_hp - 63.0))
    )
    sl = 1.0 + (0.015 * (avg_l - 50.0) ** 2) / math.sqrt(20.0 + (avg_l - 50.0) ** 2)
    sc = 1.0 + 0.045 * avg_cp
    sh = 1.0 + 0.015 * avg_cp * t
    delta_theta = 30.0 * math.exp(-(((avg_hp - 275.0) / 25.0) ** 2))
    rc = 2.0 * math.sqrt(avg_cp**7 / (avg_cp**7 + 25.0**7))
    rt = -math.sin(math.radians(2.0 * delta_theta)) * rc
    return math.sqrt(
        (delta_lp / sl) ** 2
        + (delta_cp / sc) ** 2
        + (delta_hp / sh) ** 2
        + rt * (delta_cp / sc) * (delta_hp / sh)
    )


def composite_over(
    fg: tuple[int, int, int], alpha: float, bg: tuple[int, int, int]
) -> tuple[int, int, int]:
    a = max(0.0, min(1.0, alpha))
    return tuple(int(round(f * a + b * (1.0 - a))) for f, b in zip(fg, bg))  # type: ignore[return-value]


def hex_rgb(spec: str) -> tuple[int, int, int]:
    text = spec.strip().lstrip("#")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def parse_rgba(spec: str) -> tuple[tuple[int, int, int], float]:
    text = spec.strip()
    if text.startswith("#"):
        return hex_rgb(text), 1.0
    inner = text[text.find("(") + 1 : text.rfind(")")]
    parts = [p.strip() for p in inner.split(",")]
    rgb = (int(parts[0]), int(parts[1]), int(parts[2]))
    alpha = float(parts[3]) if len(parts) > 3 else 1.0
    return rgb, alpha


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class Logger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.unverified_items: list[str] = []
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def log(self, msg: str) -> None:
        print(msg, flush=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    def unverified(self, item: str, reason: str) -> None:
        line = f"未验证\t{item}\t{reason}"
        self.unverified_items.append(line)
        self.log(line)


# ---------------------------------------------------------------------------
# Qt helpers (imported after QPA is set)
# ---------------------------------------------------------------------------


def _ensure_repo_on_path() -> None:
    text = str(REPO_ROOT)
    if text not in sys.path:
        sys.path.insert(0, text)


def pump(app: Any, n: int = 8) -> None:
    for _ in range(n):
        app.processEvents()


def wait_ms(app: Any, ms: int) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    pump(app, 4)


def logical_pixel(image: Any, widget: Any, x: int, y: int) -> tuple[int, int, int]:
    width = max(widget.width(), 1)
    height = max(widget.height(), 1)
    sx = min(image.width() - 1, max(0, int(round(x * image.width() / width))))
    sy = min(image.height() - 1, max(0, int(round(y * image.height() / height))))
    return rgb_tuple(image.pixelColor(sx, sy))


def save_widget(widget: Any, path: Path, logger: Logger) -> Path | None:
    try:
        if widget is None:
            logger.unverified(path.name, "widget is None")
            return None
        pix = widget.grab()
        if pix.isNull():
            logger.unverified(path.name, "grab() returned null pixmap")
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        ok = pix.save(str(path), "PNG")
        if not ok:
            logger.unverified(path.name, "QPixmap.save returned False")
            return None
        logger.log(f"saved {path} {pix.width()}x{pix.height()}")
        return path
    except Exception as exc:
        logger.unverified(path.name, f"{type(exc).__name__}: {exc}")
        return None


def install_messagebox_noop() -> None:
    from PySide6.QtWidgets import QMessageBox

    def _inner(*_args: Any, **_kwargs: Any) -> Any:
        return QMessageBox.StandardButton.Ok

    QMessageBox.critical = staticmethod(_inner)  # type: ignore[method-assign]
    QMessageBox.warning = staticmethod(_inner)  # type: ignore[method-assign]
    QMessageBox.information = staticmethod(_inner)  # type: ignore[method-assign]


def current_page(win: Any) -> Any:
    row = win.module_list.currentRow()
    pages = getattr(win, "_pages", [])
    if 0 <= row < len(pages):
        return pages[row]
    return win.stack.currentWidget()


def jump_named_chapter(page: Any, *needles: str) -> bool:
    chapter_list = getattr(page, "chapter_list", None)
    if chapter_list is None:
        return False
    for index in range(chapter_list.count()):
        item = chapter_list.item(index)
        text = item.text() if item is not None else ""
        if any(token in text for token in needles):
            chapter_list.setCurrentRow(index)
            return True
    return False


def jump_result_chapter(page: Any) -> None:
    chapter_list = getattr(page, "chapter_list", None)
    if chapter_list is None or chapter_list.count() <= 0:
        return
    target = chapter_list.count() - 1
    for index in range(chapter_list.count()):
        item = chapter_list.item(index)
        text = item.text() if item is not None else ""
        if "结果" in text:
            target = index
            break
    chapter_list.setCurrentRow(target)


def chapter_content_gap(page: Any) -> int | None:
    chapter_list = getattr(page, "chapter_list", None)
    stack = getattr(page, "chapter_stack", None)
    if chapter_list is None or stack is None:
        return None
    from PySide6.QtCore import QPoint

    nav = chapter_list
    while nav is not None:
        parent = nav.parent()
        if parent is not None and stack.parent() is parent:
            break
        nav = parent
    if nav is None:
        return None
    nav_right = nav.mapTo(page, QPoint(nav.width(), 0)).x()
    stack_left = stack.mapTo(page, QPoint(0, 0)).x()
    return stack_left - nav_right


# ---------------------------------------------------------------------------
# Parity measurement
# ---------------------------------------------------------------------------


@dataclass
class ParityRow:
    item: str
    spec: str
    measured: str
    tolerance: str
    verdict: str
    notes: str = ""


@dataclass
class ParityReport:
    rows: list[ParityRow] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def add(
        self,
        item: str,
        spec: str,
        measured: str,
        tolerance: str,
        verdict: str,
        notes: str = "",
    ) -> None:
        self.rows.append(
            ParityRow(item, spec, measured, tolerance, verdict, notes)
        )


def _verdict(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def measure_parity(app: Any, win: Any, logger: Logger) -> ParityReport:
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame, QLabel, QPushButton

    from app.ui.design_tokens import (
        cloud_porcelain_controls,
        cloud_porcelain_palette,
        cloud_porcelain_radii,
        cloud_porcelain_spacing,
        qss_rgba,
    )
    from app.ui.theme import build_style_sheet
    from app.ui.widgets.cloud_canvas import CloudCanvas

    report = ParityReport()
    spacing = cloud_porcelain_spacing()
    controls = cloud_porcelain_controls()
    radii = cloud_porcelain_radii()
    palette = cloud_porcelain_palette()

    win.resize(1400, 860)
    win.show()
    pump(app, 12)
    canvas = win.centralWidget()
    assert isinstance(canvas, CloudCanvas)
    canvas_image = canvas.grab().toImage()

    margins = canvas.layout().contentsMargins()
    margin_ok = all(
        abs(value - spacing.canvas_margin) <= 2
        for value in (
            margins.left(),
            margins.top(),
            margins.right(),
            margins.bottom(),
        )
    )
    report.add(
        "shell outer margin",
        "12 px (spec §6.6)",
        f"L{margins.left()} T{margins.top()} R{margins.right()} B{margins.bottom()}",
        "±2 px",
        _verdict(margin_ok),
    )

    sidebar = win.findChild(QFrame, "SidebarPanel")
    chrome = win.findChild(QFrame, "WorkspaceChrome")
    sidebar_w = sidebar.width() if sidebar is not None else -1
    report.add(
        "sidebar width",
        "228 px (spec; HTML mockup is 226)",
        f"{sidebar_w} px",
        "±2 px",
        _verdict(abs(sidebar_w - spacing.sidebar_width) <= 2),
        "spec is authoritative over HTML 226",
    )
    report.add(
        "sidebar min/max",
        "212–280 px",
        f"min={sidebar.minimumWidth()} max={sidebar.maximumWidth()}",
        "exact",
        _verdict(
            sidebar.minimumWidth() == spacing.sidebar_min
            and sidebar.maximumWidth() == spacing.sidebar_max
        ),
    )

    gap = None
    if sidebar is not None and chrome is not None:
        sidebar_right = sidebar.mapTo(canvas, QPoint(sidebar.width(), 0)).x()
        chrome_left = chrome.mapTo(canvas, QPoint(0, 0)).x()
        gap = chrome_left - sidebar_right
    report.add(
        "sidebar–workspace gap",
        "12 px",
        f"{gap} px",
        "±2 px",
        _verdict(gap is not None and abs(gap - spacing.sidebar_gap) <= 2),
    )

    stylesheet = build_style_sheet()
    radius_in_qss = "border-radius: 22px" in stylesheet and "QFrame#SidebarPanel" in stylesheet
    report.add(
        "sidebar radius (QSS)",
        "22 px",
        "22 px in QFrame#SidebarPanel" if radius_in_qss else "missing",
        "exact token",
        _verdict(radii.radius_sidebar == 22 and radius_in_qss),
    )

    header = win.findChild(QFrame, "ChapterHeader")
    header_h = header.height() if header is not None else -1
    header_min = header.minimumHeight() if header is not None else -1
    report.add(
        "chapter header min height",
        "~78 px (spec §6.6)",
        f"min={header_min} actual={header_h}",
        "min ≥78; actual ±2 of min when content allows",
        _verdict(header_min >= controls.header_min_height),
    )

    chrome_h = chrome.height() if chrome is not None else -1
    report.add(
        "workspace chrome height",
        "36–40 px (SHELL-03)",
        f"{chrome_h} px",
        "in range",
        _verdict(36 <= chrome_h <= 40),
    )

    page = current_page(win)
    content_gap = chapter_content_gap(page) if page is not None else None
    # Bolt uses QHBoxLayout spacing 12; BaseChapterPage uses splitter handle 4.
    # Both sit on the spec 4 px grid. HTML content-grid gap is 9 (not spec).
    grid_ok = content_gap is not None and any(
        abs(content_gap - step) <= 2 for step in (4, 8, 12)
    )
    report.add(
        "chapter/content gap",
        "4 px grid (4/8/12); HTML content-grid gap is 9",
        f"{content_gap} px (bolt default page)",
        "on-grid ±2",
        _verdict(grid_ok),
        "spec grid is authoritative; HTML 9 px is not on the 4 px grid",
    )
    try:
        win.module_list.setCurrentRow(5)
        app.processEvents()
        hertz_page = current_page(win)
        hertz_gap = chapter_content_gap(hertz_page) if hertz_page is not None else None
        hertz_ok = hertz_gap is not None and any(
            abs(hertz_gap - step) <= 2 for step in (4, 8, 12)
        )
        report.add(
            "chapter/content gap (hertz / BaseChapterPage)",
            "splitter handle 4 px on 4 px grid",
            f"{hertz_gap} px",
            "on-grid ±2",
            _verdict(hertz_ok),
        )
        win.module_list.setCurrentRow(0)
        app.processEvents()
    except Exception as exc:
        report.add(
            "chapter/content gap (hertz / BaseChapterPage)",
            "splitter handle 4 px on 4 px grid",
            f"error {type(exc).__name__}",
            "on-grid ±2",
            "FAIL",
        )
        win.module_list.setCurrentRow(0)
        app.processEvents()

    solid_samples: list[tuple[str, str, tuple[int, int, int], Callable[[], tuple[int, int, int] | None]]] = []

    brand = win.findChild(QLabel, "BrandTile")
    if brand is not None:
        def _brand() -> tuple[int, int, int] | None:
            img = brand.grab().toImage()
            # Left edge, vertical centre: tile fill, not the centred 23 px icon.
            return logical_pixel(img, brand, 3, brand.height() // 2)

        solid_samples.append(("BrandTile fill", palette.accent, ACCENT_RGB, _brand))

    primary = win.findChild(QPushButton, "PrimaryButton")
    if primary is not None:
        def _primary() -> tuple[int, int, int] | None:
            img = primary.grab().toImage()
            # Top-centre, inside radius, above glyph.
            return logical_pixel(img, primary, max(8, primary.width() // 2), 6)

        solid_samples.append(
            ("PrimaryButton fill", palette.accent_action, ACCENT_ACTION_RGB, _primary)
        )

    for label, token, expected, sampler in solid_samples:
        sample = sampler()
        if sample is None:
            report.add(label, token, "unsampled", "exact solid token", "FAIL")
            continue
        dist = rgb_distance(sample, expected)
        de = delta_e2000(sample, expected)
        # Anti-alias / subpixel on a 1 px border. Solid fills should be near-exact.
        ok = dist <= 12 and de <= 3.0
        notes = ""
        if label.startswith("PrimaryButton"):
            dist_old = rgb_distance(sample, ACCENT_RGB)
            ok = ok and dist < dist_old
            notes = f"not insufficient accent {palette.accent}; ΔE(accent)={delta_e2000(sample, ACCENT_RGB):.2f}"
        report.add(
            label,
            f"{token} exact",
            f"rgb{sample} ΔE2000={de:.2f} rgbΔ={dist:.1f}",
            "solid token; ΔE2000 ≤3 / rgbΔ ≤12 (AA)",
            _verdict(ok),
            notes,
        )

    # Glass composite: five fixed canvas-local points.
    glass_rgb, glass_a = parse_rgba(palette.surface_glass)
    strong_rgb, strong_a = parse_rgba(palette.surface_glass_strong)
    soft_rgb, soft_a = parse_rgba(palette.surface_glass_soft)
    expected_glass = composite_over(glass_rgb, glass_a, CANVAS_BASE_RGB)
    expected_strong = composite_over(strong_rgb, strong_a, CANVAS_BASE_RGB)
    expected_soft = composite_over(soft_rgb, soft_a, CANVAS_BASE_RGB)

    def _canvas_px(x: int, y: int) -> tuple[int, int, int]:
        return logical_pixel(canvas_image, canvas, x, y)

    points: list[tuple[str, tuple[int, int], tuple[int, int, int]]] = []
    points.append(("canvas corner (2,2)", (2, 2), CANVAS_BASE_RGB))
    if sidebar is not None:
        origin = sidebar.mapTo(canvas, QPoint(0, 0))
        points.append(
            (
                "sidebar interior",
                (origin.x() + min(40, sidebar.width() // 3), origin.y() + min(80, sidebar.height() // 4)),
                expected_glass,
            )
        )
        points.append(
            (
                "sidebar info-card-ish lower",
                (origin.x() + min(36, sidebar.width() // 3), origin.y() + max(20, sidebar.height() - 48)),
                expected_soft,
            )
        )
    if header is not None:
        h_origin = header.mapTo(canvas, QPoint(0, 0))
        points.append(
            (
                "ChapterHeader interior",
                (h_origin.x() + 8, h_origin.y() + 8),
                expected_strong,
            )
        )
    if page is not None:
        nav = getattr(page, "chapter_list", None)
        if nav is not None:
            n_origin = nav.mapTo(canvas, QPoint(0, 0))
            points.append(
                (
                    "chapter list / nav card",
                    (n_origin.x() + 24, n_origin.y() + 24),
                    expected_strong,
                )
            )
    # Keep exactly five samples.
    points = points[:5]
    de_values = []
    for name, (x, y), expected in points:
        sample = _canvas_px(x, y)
        de = delta_e2000(sample, expected)
        dist = rgb_distance(sample, expected)
        de_values.append(de)
        # Canvas corner is a solid token; glass is composited and may include
        # the static stress field, so the gate is ΔE2000 ≤3 as spec §14.2.
        ok = de <= 3.0 or (name.startswith("canvas") and dist <= 8)
        report.add(
            f"glass sample: {name}",
            f"expected rgb{expected}",
            f"rgb{sample} @ ({x},{y}) ΔE2000={de:.2f} rgbΔ={dist:.1f}",
            "ΔE2000 ≤3 (AA edge ≤5); implemented",
            _verdict(ok),
        )
    report.extra["glass_delta_e"] = de_values

    # Sidebar rounded corner: pixel just outside the 22 px quarter-circle.
    if sidebar is not None:
        origin = sidebar.mapTo(canvas, QPoint(0, 0))
        corner = _canvas_px(origin.x() + 1, origin.y() + 1)
        inside = _canvas_px(
            origin.x() + min(40, sidebar.width() // 3),
            origin.y() + min(40, sidebar.height() // 4),
        )
        canvas_ref = _canvas_px(2, 2)
        dist_canvas = rgb_distance(corner, canvas_ref)
        dist_inside = rgb_distance(corner, inside)
        dist_beige = rgb_distance(corner, OLD_BEIGE)
        rounded = dist_canvas < dist_inside and dist_beige > dist_canvas
        report.add(
            "sidebar 22px corner (outside arc)",
            "canvas_base, not opaque leftover panel / #EEE7DE",
            f"corner rgb{corner} dist(canvas)={dist_canvas:.1f} dist(inside)={dist_inside:.1f} dist(#EEE7DE)={dist_beige:.1f}",
            "closer to canvas than panel interior",
            _verdict(rounded),
        )

    # Selected module fill vs green ready-dot.
    from PySide6.QtWidgets import QListWidget

    module_list: Any = win.module_list
    assert isinstance(module_list, QListWidget)
    item_rect = module_list.visualItemRect(module_list.item(0))
    list_img = module_list.grab().toImage()
    fill_x = item_rect.left() + min(56, max(36, item_rect.width() // 2))
    fill_y = item_rect.center().y()
    selected = logical_pixel(list_img, module_list, fill_x, fill_y)
    dist_soft = rgb_distance(selected, ACCENT_SOFT_RGB)
    dist_green = rgb_distance(selected, GREEN_READY)
    report.add(
        "selected module fill",
        "accent_soft #F2D8CF, not green ready-dot",
        f"rgb{selected} dist(soft)={dist_soft:.1f} dist(green)={dist_green:.1f}",
        "closer to accent_soft than pass green",
        _verdict(dist_soft < dist_green),
    )

    # Stress field presence, not mouse-following.
    field_pt = _canvas_px(max(2, canvas.width() - 90), 70)
    canvas_pt = _canvas_px(2, 2)
    source = (
        REPO_ROOT / "app" / "ui" / "widgets" / "cloud_canvas.py"
    ).read_text(encoding="utf-8")
    no_mouse = "mouseMoveEvent" not in source and "QTimer" not in source
    present = rgb_distance(field_pt, canvas_pt) >= 2.0
    report.add(
        "stress-field presence",
        "static concentric field; no timer / mouse follow",
        f"center-ish rgb{field_pt} vs corner rgb{canvas_pt}; source_ok={no_mouse}",
        "visible difference; no mouse tracking",
        _verdict(present and no_mouse),
    )

    # Secondary / status tokens from QSS (exact literals).
    for name, expected in (
        ("secondary", palette.secondary),
        ("pass_fg", palette.pass_fg),
        ("pass_bg", palette.pass_bg),
        ("fail_fg", palette.fail_fg),
        ("fail_bg", palette.fail_bg),
        ("accent_action", palette.accent_action),
        ("accent", palette.accent),
    ):
        present_qss = qss_rgba(expected) in stylesheet or expected.upper() in stylesheet.upper()
        report.add(
            f"token in QSS: {name}",
            expected,
            "present" if present_qss else "missing",
            "exact solid token",
            _verdict(present_qss),
        )

    logger.log(f"parity rows={len(report.rows)}")
    return report


def write_parity_md(report: ParityReport, path: Path, logger: Logger) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# W7 HTML / spec parity (1400×860, Qt central widget)",
        "",
        "Spec is authoritative where it disagrees with HTML (sidebar 228 vs HTML 226).",
        "No qualitative “看起来差不多”. Measured on this host with offscreen Qt unless noted.",
        "",
        "| Item | Spec | Measured | Tolerance | Verdict | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for row in report.rows:
        notes = row.notes.replace("|", "/")
        lines.append(
            f"| {row.item} | {row.spec} | {row.measured} | {row.tolerance} | **{row.verdict}** | {notes} |"
        )
    passed = sum(1 for row in report.rows if row.verdict == "PASS")
    failed = sum(1 for row in report.rows if row.verdict == "FAIL")
    skipped = sum(1 for row in report.rows if row.verdict not in ("PASS", "FAIL"))
    lines.extend(
        [
            "",
            f"Totals: PASS={passed} FAIL={failed} other={skipped} of {len(report.rows)}.",
            "",
            "## ΔE2000",
            "",
            "CIEDE2000 is implemented in `tools/render_cloud_porcelain_matrix.py` "
            "(sRGB D65 → Lab → Sharma 2005, kL=kC=kH=1).",
            "",
            "## Windows",
            "",
            "Windows 100/125/150% **未验证** (this host is macOS).",
            "",
        ]
    )
    if logger.unverified_items:
        lines.append("## 未验证 log")
        lines.append("")
        for item in logger.unverified_items:
            lines.append(f"- `{item}`")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.log(f"wrote {path}")


# ---------------------------------------------------------------------------
# HTML overlay
# ---------------------------------------------------------------------------


def _write_isolated_html(dest: Path) -> Path:
    source = HTML_MOCKUP.read_text(encoding="utf-8")
    inject = """
<style id="w7-isolate">
  html, body {
    margin: 0 !important;
    padding: 0 !important;
    min-width: 0 !important;
    overflow: hidden !important;
    background: #EFF0EF !important;
  }
  .review-page {
    width: 1400px !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  .review-head, .theme-notes, .theme-switcher { display: none !important; }
  .window {
    width: 1400px !important;
    height: 860px !important;
    border-radius: 0 !important;
    box-shadow: none !important;
  }
  .window-dots { display: none !important; }
</style>
"""
    if "</head>" in source:
        source = source.replace("</head>", inject + "</head>", 1)
    else:
        source = inject + source
    dest.write_text(source, encoding="utf-8")
    return dest


def capture_html_window(overlay_dir: Path, logger: Logger) -> Path | None:
    overlay_dir.mkdir(parents=True, exist_ok=True)
    html_path = overlay_dir / "html-window-isolated.html"
    png_path = overlay_dir / "html-window-1400x860.png"
    _write_isolated_html(html_path)
    if not CHROME.exists():
        logger.unverified("html overlay", f"Chrome not found at {CHROME}")
        return None
    profile = Path("/tmp/cloud-porcelain-baseline/w7-chrome-profile")
    profile.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(CHROME),
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-dev-shm-usage",
        f"--user-data-dir={profile}",
        "--window-size=1400,860",
        "--virtual-time-budget=8000",
        f"--screenshot={png_path}",
        html_path.as_uri(),
    ]
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            if png_path.exists() and png_path.stat().st_size > 1024:
                proc.kill()
                logger.log(
                    f"saved html overlay source {png_path} "
                    f"({png_path.stat().st_size} bytes)"
                )
                return png_path
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        if proc.poll() is None:
            proc.kill()
        stderr = ""
        if proc.stderr is not None:
            stderr = proc.stderr.read()[-400:]
        if png_path.exists() and png_path.stat().st_size > 1024:
            logger.log(
                f"saved html overlay source {png_path} "
                f"({png_path.stat().st_size} bytes) after chrome exit"
            )
            return png_path
        logger.unverified(
            "html overlay",
            f"chrome rc={proc.returncode} stderr={stderr!r}",
        )
        return None
    except Exception as exc:
        if proc is not None and proc.poll() is None:
            proc.kill()
        logger.unverified("html overlay", f"{type(exc).__name__}: {exc}")
        return None


def write_overlay(
    html_png: Path | None,
    qt_png: Path | None,
    overlay_dir: Path,
    logger: Logger,
) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter

    overlay_dir.mkdir(parents=True, exist_ok=True)
    if html_png is None or qt_png is None or not html_png.exists() or not qt_png.exists():
        logger.unverified(
            "w7-overlay blend",
            "missing HTML and/or Qt PNG; overlay 未验证",
        )
        return
    html_img = QImage(str(html_png))
    qt_img = QImage(str(qt_png))
    if html_img.isNull() or qt_img.isNull():
        logger.unverified("w7-overlay blend", "QImage load failed")
        return
    target = qt_img.size()
    html_scaled = html_img.scaled(
        target,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    blend = QImage(target, QImage.Format.Format_ARGB32)
    painter = QPainter(blend)
    painter.drawImage(0, 0, qt_img)
    painter.setOpacity(0.5)
    painter.drawImage(0, 0, html_scaled)
    painter.end()
    out = overlay_dir / "overlay-50-html-over-qt.png"
    blend.save(str(out), "PNG")
    logger.log(f"saved {out} {blend.width()}x{blend.height()}")


# ---------------------------------------------------------------------------
# Screenshot matrix
# ---------------------------------------------------------------------------


def capture_popups(app: Any, win: Any, out_dir: Path, logger: Logger) -> None:
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QComboBox, QMenu, QMessageBox

    from app.ui.widgets.app_combo_box import AppComboBox
    from app.ui.widgets.beginner_guide_dialog import BeginnerGuideDialog
    from app.ui.widgets.help_button import HelpButton
    from app.ui.widgets.help_popover import HelpPopover

    page = current_page(win)
    help_btn = None
    if page is not None:
        buttons = page.findChildren(HelpButton)
        if buttons:
            help_btn = buttons[0]
    if help_btn is None:
        help_btn = win.findChild(HelpButton)
    if help_btn is None:
        logger.unverified("popup-help-popover.png", "no HelpButton found")
    else:
        try:
            popover = HelpPopover.show_for(help_btn.help_ref, anchor=help_btn)
            wait_ms(app, 250)
            if popover is None or not popover.isVisible():
                logger.unverified(
                    "popup-help-popover.png",
                    "popover not visible (offscreen may hide frameless windows)",
                )
            else:
                save_widget(popover, out_dir / "popup-help-popover.png", logger)
            try:
                popover.close()
            except Exception:
                pass
            pump(app, 4)
        except Exception as exc:
            logger.unverified(
                "popup-help-popover.png",
                f"{type(exc).__name__}: {exc}",
            )

    try:
        dlg = BeginnerGuideDialog.from_help_ref(
            "modules/hertz/_section_geometry", parent=win
        )
        dlg.show()
        wait_ms(app, 200)
        if not dlg.isVisible():
            logger.unverified(
                "popup-beginner-guide.png",
                "BeginnerGuideDialog.show() did not become visible",
            )
        else:
            save_widget(dlg, out_dir / "popup-beginner-guide.png", logger)
        dlg.close()
        pump(app, 4)
    except Exception as exc:
        logger.unverified("popup-beginner-guide.png", f"{type(exc).__name__}: {exc}")

    combo = None
    if page is not None:
        combos = page.findChildren(AppComboBox)
        combo = combos[0] if combos else None
        if combo is None:
            qcombos = page.findChildren(QComboBox)
            combo = qcombos[0] if qcombos else None
    if combo is None:
        logger.unverified("popup-app-combo.png", "no combo on current page")
    else:
        try:
            combo.showPopup()
            wait_ms(app, 200)
            view = combo.view()
            container = view.window() if view is not None else None
            grabbed = False
            if (
                container is not None
                and container is not combo.window()
                and container.isVisible()
            ):
                save_widget(container, out_dir / "popup-app-combo.png", logger)
                grabbed = True
            elif view is not None:
                save_widget(view, out_dir / "popup-app-combo-view.png", logger)
                grabbed = True
            if not grabbed:
                logger.unverified(
                    "popup-app-combo.png",
                    "showPopup() did not yield a visible container/view",
                )
            combo.hidePopup()
            pump(app, 4)
        except Exception as exc:
            logger.unverified("popup-app-combo.png", f"{type(exc).__name__}: {exc}")

    try:
        menu = QMenu(win)
        menu.addAction("保存输入条件")
        menu.addAction("导出结果说明")
        act = menu.addAction("禁用项")
        act.setEnabled(False)
        menu.popup(win.mapToGlobal(QPoint(80, 80)))
        wait_ms(app, 150)
        if not menu.isVisible():
            logger.unverified("popup-qmenu.png", "QMenu.popup() not visible")
        else:
            save_widget(menu, out_dir / "popup-qmenu.png", logger)
        menu.close()
    except Exception as exc:
        logger.unverified("popup-qmenu.png", f"{type(exc).__name__}: {exc}")

    try:
        box = QMessageBox(win)
        box.setWindowTitle("示例")
        box.setText("W7 非阻塞 QMessageBox。")
        box.setInformativeText("未调用 exec()。")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.show()
        wait_ms(app, 150)
        if not box.isVisible():
            logger.unverified("popup-qmessagebox.png", "QMessageBox not visible")
        else:
            save_widget(box, out_dir / "popup-qmessagebox.png", logger)
        box.close()
    except Exception as exc:
        logger.unverified("popup-qmessagebox.png", f"{type(exc).__name__}: {exc}")


def capture_gallery(app: Any, out_dir: Path, logger: Logger) -> None:
    from tests.ui.cloud_component_gallery import build_cloud_component_gallery

    gallery = build_cloud_component_gallery()
    gallery.resize(980, 860)
    gallery.show()
    pump(app, 8)
    save_widget(gallery, out_dir / "gallery-states.png", logger)
    gallery.field_focus.setFocus()
    pump(app, 4)
    save_widget(gallery, out_dir / "gallery-focus.png", logger)
    gallery.btn_primary.setDown(True)
    pump(app, 2)
    save_widget(gallery, out_dir / "gallery-primary-pressed.png", logger)
    gallery.btn_primary.setDown(False)
    gallery.close()


def capture_diagrams(app: Any, page: Any, module: str, out_dir: Path, logger: Logger) -> None:
    mapping: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
        "hertz": [("diagram_widget", "diagram-hertz-input.png", ("图示", "输入条件图示"))],
        "bolt": [
            ("diagram_widget", "diagram-bolt-clamping.png", ("夹紧", "图示", "接头")),
            ("flowchart_nav", "diagram-bolt-flowchart.png", ()),
        ],
        "worm": [
            ("geometry_overview", "diagram-worm-geometry.png", ("图形",)),
            ("stress_curve", "diagram-worm-stress-curve.png", ("图形",)),
        ],
        "buffer": [
            ("curve_check_widget", "diagram-buffer-energy-curve.png", ("曲线检查", "能量")),
            ("response_widget", "diagram-buffer-response-curve.png", ("响应",)),
        ],
        "interference": [
            ("curve_widget", "diagram-interference-press-force.png", ("压入力",)),
        ],
        "spline": [("curve_widget", "diagram-spline-press-force.png", ())],
    }
    for attr, filename, needles in mapping.get(module, []):
        if needles:
            jump_named_chapter(page, *needles)
            pump(app, 6)
        widget = getattr(page, attr, None)
        if module == "worm" and attr == "stress_curve":
            ensure = getattr(page, "_ensure_stress_curve", None)
            if callable(ensure):
                try:
                    widget = ensure()
                    pump(app, 6)
                except Exception as exc:
                    logger.unverified(filename, f"_ensure_stress_curve: {exc}")
                    continue
        if widget is None:
            logger.unverified(filename, f"page has no attr {attr}")
            continue
        if module == "bolt" and attr == "flowchart_nav":
            nav_stack = getattr(page, "nav_stack", None)
            if nav_stack is not None:
                try:
                    nav_stack.setCurrentIndex(1)
                    pump(app, 4)
                except Exception:
                    pass
        save_widget(widget, out_dir / filename, logger)


def run_offscreen_matrix(args: argparse.Namespace) -> int:
    os.environ.setdefault("TMPDIR", "/tmp")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _ensure_repo_on_path()

    from PySide6.QtWidgets import QApplication, QFrame

    from app.ui.design_tokens import cloud_porcelain_spacing
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_theme

    logger = Logger(Path(args.log))
    out_dir = Path(args.out_dir)
    overlay_dir = Path(args.overlay_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    logger.log(f"platformName={app.platformName()}")
    apply_theme(app)
    install_messagebox_noop()
    pump(app, 4)

    win = MainWindow()
    win.show()
    pump(app, 12)

    win.resize(1180, 720)
    pump(app, 8)
    save_widget(win.centralWidget(), out_dir / "main-1180x720-initial.png", logger)

    win.resize(1400, 860)
    pump(app, 8)
    qt_shell = save_widget(
        win.centralWidget(), out_dir / "main-1400x860-initial.png", logger
    )
    if qt_shell is not None:
        save_widget(win.centralWidget(), overlay_dir / "qt-central-1400x860.png", logger)

    report = measure_parity(app, win, logger)
    write_parity_md(report, Path(args.parity_md), logger)
    (Path(args.out_dir).parent.parent / "w7-parity.json").write_text(
        json.dumps(
            [row.__dict__ for row in report.rows],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    html_png = None
    if not args.skip_html:
        html_png = capture_html_window(overlay_dir, logger)
        qt_png = overlay_dir / "qt-central-1400x860.png"
        write_overlay(
            html_png,
            qt_png if qt_png.exists() else qt_shell,
            overlay_dir,
            logger,
        )
        overlay_note = (
            f"HTML `.window` screenshot: `{html_png}`\n"
            f"Qt central widget: `{qt_png if qt_png.exists() else qt_shell}`\n"
            f"50% overlay: `{overlay_dir / 'overlay-50-html-over-qt.png'}`\n"
        )
        with Path(args.parity_md).open("a", encoding="utf-8") as fh:
            fh.write("\n## HTML overlay\n\n")
            fh.write(overlay_note)
            fh.write("Overlay is an alignment aid, not a binary-equality gate.\n")
    else:
        logger.unverified("html overlay", "--skip-html")

    for row, name, _sample, _calc in MODULES:
        try:
            win.module_list.setCurrentRow(row)
            pump(app, 10)
            save_widget(
                win.centralWidget(),
                out_dir / f"module-{name}-1400x860-input.png",
                logger,
            )
        except Exception as exc:
            logger.unverified(
                f"module-{name}-1400x860-input.png",
                f"{type(exc).__name__}: {exc}",
            )

    capture_popups(app, win, out_dir, logger)
    try:
        capture_gallery(app, out_dir, logger)
    except Exception as exc:
        logger.unverified("gallery", f"{type(exc).__name__}: {exc}")

    for row, name, sample, calc_method in MODULES:
        try:
            win.module_list.setCurrentRow(row)
            pump(app, 10)
            page = current_page(win)
            if page is None:
                logger.unverified(
                    f"module-{name}-1400x860-result.png",
                    "page is None after navigation",
                )
                continue
            page._load_sample(sample)
            pump(app, 8)
            getattr(page, calc_method)()
            pump(app, 12)
            jump_result_chapter(page)
            pump(app, 8)
            save_widget(
                win.centralWidget(),
                out_dir / f"module-{name}-1400x860-result.png",
                logger,
            )
            capture_diagrams(app, page, name, out_dir, logger)
        except Exception as exc:
            logger.unverified(
                f"module-{name}-1400x860-result.png",
                f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            )

    # Splitter extremes (offscreen evidence; cocoa re-takes separately).
    try:
        spacing = cloud_porcelain_spacing()
        sidebar = win.findChild(QFrame, "SidebarPanel")
        win.splitter.setSizes([spacing.sidebar_min, 2000])
        pump(app, 6)
        save_widget(
            win.centralWidget(),
            out_dir / "shell-1400x860-sidebar-min.png",
            logger,
        )
        win.splitter.setSizes([spacing.sidebar_max, 2000])
        pump(app, 6)
        save_widget(
            win.centralWidget(),
            out_dir / "shell-1400x860-sidebar-max.png",
            logger,
        )
        logger.log(
            f"splitter sidebar width after max setSizes={sidebar.width() if sidebar else None}"
        )
        win.splitter.setSizes([spacing.sidebar_width, 2000])
        pump(app, 4)
    except Exception as exc:
        logger.unverified("splitter resize", f"{type(exc).__name__}: {exc}")

    win.close()
    pngs = sorted(out_dir.glob("*.png"))
    logger.log(f"done png_count={len(pngs)} unverified={len(logger.unverified_items)}")
    (out_dir / "UNVERIFIED.txt").write_text(
        "\n".join(logger.unverified_items)
        + ("\n" if logger.unverified_items else ""),
        encoding="utf-8",
    )
    return 0


def run_macos_fg_worker(args: argparse.Namespace) -> int:
    os.environ.pop("QT_QPA_PLATFORM", None)
    os.environ.setdefault("QT_QPA_PLATFORM", "cocoa")
    os.environ.setdefault("TMPDIR", "/tmp")
    _ensure_repo_on_path()

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QFrame

    from app.ui.design_tokens import cloud_porcelain_spacing
    from app.ui.main_window import MainWindow
    from app.ui.theme import apply_theme

    out_dir = Path(args.macos_fg_dir)
    logger = Logger(out_dir / "macos-fg-log.txt")
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    platform = app.platformName()
    logger.log(f"platformName={platform}")
    if platform == "offscreen":
        logger.unverified("macos-fg", "platform is offscreen; cocoa not available")
        return 2
    screen = app.primaryScreen()
    if screen is None:
        logger.unverified("macos-fg", "primaryScreen() is None")
        return 3
    geom = screen.geometry()
    logger.log(
        f"screen={screen.name()} {geom.width()}x{geom.height()} "
        f"dpr={screen.devicePixelRatio()}"
    )
    apply_theme(app)
    install_messagebox_noop()

    win = MainWindow()
    errors: list[str] = []

    def grab(name: str) -> None:
        win.show()
        win.raise_()
        win.activateWindow()
        pump(app, 10)
        path = save_widget(win.centralWidget(), out_dir / name, logger)
        if path is None:
            errors.append(name)

    def run() -> None:
        try:
            win.resize(1400, 860)
            grab("w7-1400x860-shell.png")
            page = current_page(win)
            grab("w7-1400x860-bolt-input.png")
            if page is not None:
                try:
                    page._load_sample("input_case_01.json")
                    pump(app, 8)
                    page._calculate()
                    pump(app, 12)
                    jump_result_chapter(page)
                    pump(app, 8)
                    grab("w7-1400x860-bolt-result.png")
                except Exception as exc:
                    logger.unverified(
                        "w7-1400x860-bolt-result.png",
                        f"{type(exc).__name__}: {exc}",
                    )
            spacing = cloud_porcelain_spacing()
            sidebar = win.findChild(QFrame, "SidebarPanel")
            win.splitter.setSizes([spacing.sidebar_min, 2000])
            pump(app, 6)
            grab("w7-1400x860-splitter-min.png")
            logger.log(f"cocoa sidebar min width={sidebar.width() if sidebar else None}")
            win.splitter.setSizes([spacing.sidebar_max, 2000])
            pump(app, 6)
            grab("w7-1400x860-splitter-max.png")
            logger.log(f"cocoa sidebar max width={sidebar.width() if sidebar else None}")
        except Exception:
            logger.log(traceback.format_exc())
            errors.append("exception")
        finally:
            win.close()
            app.exit(1 if errors else 0)

    QTimer.singleShot(300, run)
    QTimer.singleShot(20000, lambda: app.exit(4))
    rc = app.exec()
    if rc == 4:
        logger.unverified("macos-fg", "cocoa capture timed out after 20s")
        return 4
    return rc


def spawn_macos_fg(args: argparse.Namespace, logger: Logger) -> int:
    env = os.environ.copy()
    env.pop("QT_QPA_PLATFORM", None)
    env["QT_QPA_PLATFORM"] = "cocoa"
    env.setdefault("TMPDIR", "/tmp")
    env.setdefault("PYTHONPATH", str(REPO_ROOT))
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--macos-fg-worker",
        "--macos-fg-dir",
        str(args.macos_fg_dir),
        "--out-dir",
        str(args.out_dir),
        "--log",
        str(Path(args.macos_fg_dir) / "spawn-log.txt"),
    ]
    try:
        completed = subprocess.run(
            cmd,
            env=env,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        logger.unverified("macos-fg spawn", f"{type(exc).__name__}: {exc}")
        return 1
    logger.log(completed.stdout[-2000:] if completed.stdout else "")
    if completed.returncode != 0:
        logger.unverified(
            "macos-fg",
            f"rc={completed.returncode} stderr={completed.stderr[-500:]!r}",
        )
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT),
        help="PNG output directory (must be under /tmp, never the repo)",
    )
    parser.add_argument("--overlay-dir", default=str(DEFAULT_OVERLAY))
    parser.add_argument("--parity-md", default=str(DEFAULT_PARITY))
    parser.add_argument("--log", default=str(DEFAULT_LOG))
    parser.add_argument("--macos-fg-dir", default=str(DEFAULT_MACOS_FG))
    parser.add_argument(
        "--macos-fg",
        action="store_true",
        help="After offscreen matrix, spawn a cocoa subprocess for Retina grabs",
    )
    parser.add_argument(
        "--macos-fg-worker",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--skip-html", action="store_true")
    parser.add_argument("--skip-offscreen", action="store_true")
    return parser


def _reject_repo_output(path: Path) -> None:
    resolved = path.resolve()
    repo = REPO_ROOT.resolve()
    if resolved == repo or repo in resolved.parents:
        raise SystemExit(f"refusing to write {path} inside the repo")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for raw in (args.out_dir, args.overlay_dir, args.parity_md, args.log, args.macos_fg_dir):
        _reject_repo_output(Path(raw))
    if args.macos_fg_worker:
        return run_macos_fg_worker(args)
    rc = 0
    if not args.skip_offscreen:
        rc = run_offscreen_matrix(args)
    if args.macos_fg:
        logger = Logger(Path(args.log))
        fg_rc = spawn_macos_fg(args, logger)
        if fg_rc not in (0, None):
            rc = rc or fg_rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
