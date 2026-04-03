"""Mesh stress variation curve widget for worm gear module."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QVBoxLayout, QWidget

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class WormStressCurveWidget(QWidget):
    """Dual-axis plot of contact and root stress over one worm revolution."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theta_deg: list[float] = []
        self._sigma_h_mpa: list[float] = []
        self._sigma_f_mpa: list[float] = []
        self._sigma_h_nominal: float = 0.0
        self._sigma_f_nominal: float = 0.0

        self._figure = Figure(figsize=(8, 3.5), dpi=100)
        self._figure.patch.set_facecolor("#FBF8F3")
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

    def _draw_placeholder(self) -> None:
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor("#FBF8F3")
        ax.text(0.5, 0.5, "执行计算后显示啮合应力波动曲线",
                ha="center", va="center", fontsize=11, color="#6B665E",
                transform=ax.transAxes)
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

        ax1 = self._figure.add_subplot(111)
        ax1.set_facecolor("#FBF8F3")
        ax1.set_xlabel(r"蜗杆转角 $\theta$ (deg)", fontsize=10)
        ax1.set_ylabel(r"齿面接触应力 $\sigma_H$ (MPa)", color="#D97757", fontsize=10)
        ax1.plot(self._theta_deg, self._sigma_h_mpa, color="#D97757", linewidth=1.8,
                 label=r"$\sigma_H$")
        if self._sigma_h_nominal > 0:
            ax1.axhline(self._sigma_h_nominal, color="#D97757", linestyle="--",
                        linewidth=0.8, alpha=0.6)
        ax1.tick_params(axis="y", labelcolor="#D97757")

        ax2 = ax1.twinx()
        ax2.set_ylabel(r"齿根弯曲应力 $\sigma_F$ (MPa)", color="#2563EB", fontsize=10)
        ax2.plot(self._theta_deg, self._sigma_f_mpa, color="#2563EB", linewidth=1.8,
                 label=r"$\sigma_F$")
        if self._sigma_f_nominal > 0:
            ax2.axhline(self._sigma_f_nominal, color="#2563EB", linestyle="--",
                        linewidth=0.8, alpha=0.6)
        ax2.tick_params(axis="y", labelcolor="#2563EB")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

        ax1.set_xlim(0, 360)
        ax1.set_title("一个蜗杆旋转周期内啮合应力变化", fontsize=12, fontweight="bold",
                       color="#2E2A26")
        self._figure.tight_layout()
        self._canvas.draw()
