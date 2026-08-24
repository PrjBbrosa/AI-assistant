"""Mesh stress variation curve widget for worm gear module."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.design_tokens import matplotlib_palette, qcolor
from app.ui.fonts import configure_matplotlib_fonts


GRID_ALPHA = 0.55


def _mpl_color(token: str, alpha: float | None = None) -> str:
    parsed = qcolor(token)
    if alpha is not None:
        parsed.setAlphaF(alpha)
    if parsed.alpha() >= 255:
        return f"#{parsed.red():02X}{parsed.green():02X}{parsed.blue():02X}"
    return (
        f"#{parsed.red():02X}{parsed.green():02X}"
        f"{parsed.blue():02X}{parsed.alpha():02X}"
    )


class WormStressCurveWidget(QWidget):
    """Dual-axis plot of contact and root stress over one worm revolution."""

    def __init__(self, parent: QWidget | None = None) -> None:
        configure_matplotlib_fonts()
        super().__init__(parent)
        self._theta_deg: list[float] = []
        self._sigma_h_mpa: list[float] = []
        self._sigma_f_mpa: list[float] = []
        self._sigma_h_nominal: float = 0.0
        self._sigma_f_nominal: float = 0.0
        self._palette = matplotlib_palette()

        # Deferred matplotlib import: only loaded when this canvas is first
        # constructed (graphics chapter visit or first result with curve data).
        # FigureCanvasQTAgg must be created on the GUI main thread — this __init__
        # is always called from the main thread, so the constraint is satisfied.
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        self._figure = Figure(figsize=(8, 3.5), dpi=100)
        self._figure.patch.set_facecolor(self._palette["surface_glass_soft"])
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.setMinimumHeight(350)
        self._draw_placeholder()

    def set_curves(
        self,
        *,
        theta_deg: Iterable[float],
        sigma_h_mpa: Iterable[float],
        sigma_f_mpa: Iterable[float],
        sigma_h_nominal_mpa: float,
        sigma_f_nominal_mpa: float,
    ) -> None:
        self._theta_deg = [float(v) for v in theta_deg]
        self._sigma_h_mpa = [float(v) for v in sigma_h_mpa]
        self._sigma_f_mpa = [float(v) for v in sigma_f_mpa]
        self._sigma_h_nominal = float(sigma_h_nominal_mpa)
        self._sigma_f_nominal = float(sigma_f_nominal_mpa)
        self._redraw()

    def curve_data(self) -> tuple[list[float], list[float], list[float], float, float]:
        """Stored theta / sigma series and nominal hline values."""
        return (
            list(self._theta_deg),
            list(self._sigma_h_mpa),
            list(self._sigma_f_mpa),
            self._sigma_h_nominal,
            self._sigma_f_nominal,
        )

    def clear(self) -> None:
        self._theta_deg = []
        self._sigma_h_mpa = []
        self._sigma_f_mpa = []
        self._sigma_h_nominal = 0.0
        self._sigma_f_nominal = 0.0
        self._figure.clear()
        self._canvas.draw()

    def _draw_placeholder(self) -> None:
        self._figure.clear()
        pal = self._palette
        ax = self._figure.add_subplot(111)
        ax.set_facecolor(pal["surface_glass_soft"])
        ax.text(
            0.5,
            0.5,
            "执行计算后显示啮合应力波动曲线",
            ha="center",
            va="center",
            fontsize=11,
            color=pal["ink_muted"],
            transform=ax.transAxes,
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        self._canvas.draw()

    def _redraw(self) -> None:
        self._figure.clear()
        if len(self._theta_deg) < 2:
            self._draw_placeholder()
            return

        pal = self._palette
        accent = pal["accent"]
        secondary = pal["secondary"]
        ink = pal["ink_primary"]
        structural = pal["line_structural"]
        grid = _mpl_color("line_structural", GRID_ALPHA)
        face = pal["surface_glass_soft"]

        ax1 = self._figure.add_subplot(111)
        ax1.set_facecolor(face)
        ax1.set_xlabel("蜗杆转角 θ (deg)", fontsize=10, color=ink)
        ax1.set_ylabel("齿面接触应力 σ_H (MPa)", color=accent, fontsize=10)
        ax1.plot(self._theta_deg, self._sigma_h_mpa, color=accent, linewidth=1.8,
                 label="σ_H")
        if self._sigma_h_nominal > 0:
            ax1.axhline(self._sigma_h_nominal, color=accent, linestyle="--",
                        linewidth=0.8, alpha=0.6)
        ax1.tick_params(axis="y", labelcolor=accent)
        ax1.tick_params(axis="x", colors=ink)
        for spine in ax1.spines.values():
            spine.set_edgecolor(structural)
        ax1.grid(color=grid, linewidth=0.5)

        ax2 = ax1.twinx()
        ax2.set_facecolor(face)
        ax2.set_ylabel("齿根弯曲应力 σ_F (MPa)", color=secondary, fontsize=10)
        ax2.plot(self._theta_deg, self._sigma_f_mpa, color=secondary, linewidth=1.8,
                 label="σ_F")
        if self._sigma_f_nominal > 0:
            ax2.axhline(self._sigma_f_nominal, color=secondary, linestyle="--",
                        linewidth=0.8, alpha=0.6)
        ax2.tick_params(axis="y", labelcolor=secondary)
        for spine in ax2.spines.values():
            spine.set_edgecolor(structural)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9,
                   facecolor=face, edgecolor=structural, labelcolor=ink)

        ax1.set_xlim(0, 360)
        ax1.set_title("一个蜗杆旋转周期内啮合应力变化", fontsize=12, fontweight="bold",
                       color=ink)
        self._figure.tight_layout()
        self._canvas.draw()
