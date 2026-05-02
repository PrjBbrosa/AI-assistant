"""One-shot script: pre-render fixed worm gear LaTeX formulas to PNG.

Usage:
    python3 tools/bake_worm_formulas.py

Outputs:
    app/assets/worm_formula_hertz.png   -- sigma_H Hertz contact stress formula
    app/assets/worm_formula_root.png    -- sigma_F root bending stress formula

The rendering parameters (fontsize, dpi, color) must match those used in
worm_gear_page.py exactly so that the static images look identical to
what LatexLabel.set_latex() would produce at runtime.

This script is idempotent: running it multiple times always produces the same
output files.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that app.ui.fonts is importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _render_latex_to_png(
    latex: str,
    output_path: Path,
    fontsize: int = 14,
    dpi: int = 120,
    color: str = "#1F1D1A",
) -> None:
    """Render a LaTeX string to a PNG file using the same pipeline as LatexLabel."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    # Configure CJK-capable fonts (same as configure_matplotlib_fonts in fonts.py)
    # so that any Chinese glyphs in future formulas render correctly.
    import platform
    if platform.system() == "Windows":
        matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    elif platform.system() == "Darwin":
        matplotlib.rcParams["font.sans-serif"] = ["Hiragino Sans GB", "Arial Unicode MS", "Songti SC", "DejaVu Sans"]
    else:
        matplotlib.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "DejaVu Sans"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["axes.unicode_minus"] = False

    fig = Figure()
    fig.patch.set_alpha(0.0)
    canvas = FigureCanvasAgg(fig)
    fig.text(0.0, 0.5, latex, fontsize=fontsize, color=color,
             verticalalignment="center", horizontalalignment="left")

    canvas.draw()
    renderer = canvas.get_renderer()
    bbox = fig.get_tightbbox(renderer)
    if bbox is None:
        raise RuntimeError(f"Could not get bounding box for formula: {latex!r}")

    w_inch = bbox.width / fig.dpi + 0.05
    h_inch = bbox.height / fig.dpi + 0.05
    fig.set_size_inches(w_inch, h_inch)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    canvas.draw()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, transparent=True,
                bbox_inches="tight", pad_inches=0.02)
    buf.seek(0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buf.read())
    print(f"  wrote {output_path.relative_to(PROJECT_ROOT)}  ({output_path.stat().st_size} bytes)")


def main() -> None:
    assets_dir = PROJECT_ROOT / "app" / "assets"

    formulas = [
        (
            r"$\sigma_H = \sqrt{\frac{F_n \cdot E^*}{\pi \cdot L_c \cdot \rho_{eq}}}$",
            assets_dir / "worm_formula_hertz.png",
            16,
            120,
            "#1F1D1A",
        ),
        (
            r"$\sigma_F = \frac{F_t \cdot h}{W_{section}}$",
            assets_dir / "worm_formula_root.png",
            16,
            120,
            "#1F1D1A",
        ),
    ]

    print("Baking worm formula PNGs...")
    for latex, path, fontsize, dpi, color in formulas:
        _render_latex_to_png(latex, path, fontsize=fontsize, dpi=dpi, color=color)
    print("Done.")


if __name__ == "__main__":
    main()
