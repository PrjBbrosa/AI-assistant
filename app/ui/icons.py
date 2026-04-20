"""Application icon helpers."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap


def _resource_root() -> Path:
    """Resolve the app resource root for source and PyInstaller builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "app"
    return Path(__file__).resolve().parents[1]


def app_icon_path() -> Path:
    assets_dir = _resource_root() / "assets"
    if platform.system() == "Windows":
        icon_path = assets_dir / "assistant_icon.ico"
        if icon_path.exists():
            return icon_path
    return assets_dir / "assistant_icon.png"


def load_app_icon() -> QIcon:
    return QIcon(str(app_icon_path()))


# Cache for the processed brand-mark pixmap keyed by (size, bg).
_BRAND_MARK_CACHE: dict[tuple[int, str], QPixmap] = {}


def brand_mark_pixmap(size: int) -> QPixmap:
    """Return the app icon softened for the warm-neutral sidebar.

    The source PNG has a stark black rounded-rectangle backdrop that looks
    too aggressive against the warm sidebar. We flip the tonal range so the
    icon fully blends into the sidebar background, leaving only the gears
    and orange accents visible — no competing card outline.

    Grayscale pixels are remapped linearly from ``SIDEBAR → INK_DARK``
    instead of the original ``BLACK → WHITE``:

    * Original black backdrop → ``#EEE7DE`` (sidebar color), so the rounded
      rectangle disappears.
    * Original white gears/rings → warm dark ``#2E2820``.
    * Anti-aliased edges blend proportionally.
    * Colored pixels (orange ``#D97757`` accents) are kept unchanged.
    """
    cache_key = (size, "sidebar-blend")
    cached = _BRAND_MARK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    image = QImage(str(app_icon_path()))
    if image.isNull():
        return QPixmap()
    image = image.convertToFormat(QImage.Format.Format_ARGB32)

    CARD_LIGHT = (238, 231, 222)  # #EEE7DE — matches QFrame#SidebarPanel
    INK_DARK = (46, 40, 32)       # #2E2820 — warm near-black for the gears

    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
            if a == 0:
                continue
            # Grayscale test: channels within ~25 of each other.
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn <= 25:
                t = (r + g + b) / (3.0 * 255.0)  # 0 at original black, 1 at original white
                new_r = int(CARD_LIGHT[0] + (INK_DARK[0] - CARD_LIGHT[0]) * t)
                new_g = int(CARD_LIGHT[1] + (INK_DARK[1] - CARD_LIGHT[1]) * t)
                new_b = int(CARD_LIGHT[2] + (INK_DARK[2] - CARD_LIGHT[2]) * t)
                image.setPixelColor(x, y, QColor(new_r, new_g, new_b, a))
            # else: colored pixel (orange accent) — keep as-is.

    pixmap = QPixmap.fromImage(image).scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    _BRAND_MARK_CACHE[cache_key] = pixmap
    return pixmap
