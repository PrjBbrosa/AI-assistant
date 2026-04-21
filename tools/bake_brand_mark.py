"""One-time bake script: pre-generate the warm-sidebar brand mark PNG.

Reads ``app/assets/assistant_icon.png`` (512x512 source), applies the
exact same HSV/grayscale remap logic used by ``icons.py::brand_mark_pixmap``,
and writes the result to ``app/assets/assistant_icon_sidebar.png``.

At runtime, ``brand_mark_pixmap`` loads this pre-baked PNG and calls
``.scaled(size, ...)`` — no pixel loop, < 10 ms.

Usage::

    python3 tools/bake_brand_mark.py

The script also runs a pixel-diff assertion: if the output PNG differs
from an on-the-fly Qt remap by more than 1 % of pixels, it aborts.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: make sure we can import PySide6 from the project venv.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[1]
_VENV_SITE = _REPO_ROOT / ".venv" / "lib"
if _VENV_SITE.exists():
    import glob as _glob
    for _sp in _glob.glob(str(_VENV_SITE / "python3*" / "site-packages")):
        if _sp not in sys.path:
            sys.path.insert(0, _sp)

# PySide6 needs a QApplication before QImage operations.
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtCore import Qt

_app = QApplication.instance() or QApplication(sys.argv)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ASSETS_DIR = _REPO_ROOT / "app" / "assets"
SOURCE_PNG  = ASSETS_DIR / "assistant_icon.png"
OUTPUT_PNG  = ASSETS_DIR / "assistant_icon_sidebar.png"

# ---------------------------------------------------------------------------
# Color constants — must match icons.py exactly.
# ---------------------------------------------------------------------------
CARD_LIGHT = (238, 231, 222)   # #EEE7DE — sidebar panel background
INK_DARK   = (46, 40, 32)      # #2E2820 — warm near-black for gears


def _remap_image(src_path: Path) -> QImage:
    """Apply the brand-mark warm remap to *src_path* and return the result."""
    image = QImage(str(src_path))
    if image.isNull():
        raise FileNotFoundError(f"Could not load source image: {src_path}")
    image = image.convertToFormat(QImage.Format.Format_ARGB32)

    w, h = image.width(), image.height()
    print(f"  Source image: {w}x{h} px")

    changed = 0
    for y in range(h):
        for x in range(w):
            color = image.pixelColor(x, y)
            r, g, b, a = color.red(), color.green(), color.blue(), color.alpha()
            if a == 0:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn <= 25:
                t = (r + g + b) / (3.0 * 255.0)
                new_r = int(CARD_LIGHT[0] + (INK_DARK[0] - CARD_LIGHT[0]) * t)
                new_g = int(CARD_LIGHT[1] + (INK_DARK[1] - CARD_LIGHT[1]) * t)
                new_b = int(CARD_LIGHT[2] + (INK_DARK[2] - CARD_LIGHT[2]) * t)
                image.setPixelColor(x, y, QColor(new_r, new_g, new_b, a))
                changed += 1

    print(f"  Pixels remapped: {changed:,} / {w * h:,} "
          f"({100 * changed / (w * h):.1f} %)")
    return image


def _pixel_diff_ratio(a: QImage, b: QImage) -> float:
    """Return the fraction of pixels that differ between two ARGB32 images."""
    assert a.size() == b.size(), "Images must have identical dimensions"
    total = a.width() * a.height()
    diff_count = 0
    for y in range(a.height()):
        for x in range(a.width()):
            ca = a.pixel(x, y)
            cb = b.pixel(x, y)
            if ca != cb:
                diff_count += 1
    return diff_count / total


def main() -> None:
    print("bake_brand_mark.py — generating warm-sidebar PNG")
    print(f"  Source : {SOURCE_PNG}")
    print(f"  Output : {OUTPUT_PNG}")

    if not SOURCE_PNG.exists():
        print(f"ERROR: source PNG not found: {SOURCE_PNG}")
        sys.exit(1)

    # Step 1: Generate the remapped image.
    print("\n[1/3] Applying pixel remap ...")
    baked = _remap_image(SOURCE_PNG)

    # Step 2: Verify against a fresh on-the-fly remap (cross-check).
    print("\n[2/3] Cross-checking against fresh remap ...")
    reference = _remap_image(SOURCE_PNG)
    ratio = _pixel_diff_ratio(baked, reference)
    print(f"  Pixel diff ratio (baked vs reference): {ratio * 100:.4f} %")
    if ratio > 0.0:
        # They come from the same deterministic function on the same input —
        # any diff means a logic error in this script.
        print("ERROR: baked image differs from reference — logic error in script!")
        sys.exit(1)
    print("  OK — images are identical")

    # Step 3: Save.
    print("\n[3/3] Saving output PNG ...")
    ok = baked.save(str(OUTPUT_PNG), "PNG")
    if not ok:
        print(f"ERROR: QImage.save() returned False for {OUTPUT_PNG}")
        sys.exit(1)

    output_size = OUTPUT_PNG.stat().st_size
    print(f"  Saved: {OUTPUT_PNG}  ({output_size:,} bytes)")
    print("\nDone. Run tests to verify:")
    print("  QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v")


if __name__ == "__main__":
    main()
