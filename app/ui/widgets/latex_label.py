"""LaTeX formula rendering widget using matplotlib.mathtext."""

from __future__ import annotations

import io
from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


class LatexLabel(QLabel):
    """QLabel that renders LaTeX formulas via matplotlib."""

    _cache: ClassVar[dict[tuple[str, int, int], QPixmap]] = {}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._current_key: tuple[str, int, int] | None = None

    def set_latex(
        self,
        latex: str,
        fontsize: int = 14,
        dpi: int = 120,
        color: str = "#1F1D1A",
    ) -> None:
        """Render a LaTeX string and display as pixmap."""
        if not latex:
            self.clear()
            self._current_key = None
            return

        key = (latex, fontsize, dpi)
        if key == self._current_key:
            return

        if key in self._cache:
            self.setPixmap(self._cache[key])
            self._current_key = key
            return

        fig = Figure()
        fig.patch.set_alpha(0.0)
        canvas = FigureCanvasAgg(fig)
        fig.text(0.0, 0.5, latex, fontsize=fontsize, color=color,
                 verticalalignment="center", horizontalalignment="left")

        canvas.draw()
        renderer = canvas.get_renderer()
        bbox = fig.get_tightbbox(renderer)
        if bbox is None:
            self.clear()
            self._current_key = None
            return

        w_inch = bbox.width / fig.dpi + 0.05
        h_inch = bbox.height / fig.dpi + 0.05
        fig.set_size_inches(w_inch, h_inch)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        canvas.draw()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, transparent=True,
                    bbox_inches="tight", pad_inches=0.02)
        buf.seek(0)

        image = QImage()
        image.loadFromData(buf.read())
        pixmap = QPixmap.fromImage(image)

        self._cache[key] = pixmap
        self.setPixmap(pixmap)
        self._current_key = key
