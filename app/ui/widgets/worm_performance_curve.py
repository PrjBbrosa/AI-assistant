"""Performance curve panel for worm gear modules."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.design_tokens import qcolor, qpen
from app.ui.fonts import make_ui_font
from app.ui.widgets.interactive_chart import ChartSample, InteractiveChartWidget


GRID_ALPHA = 0.55


def _token(name: str, alpha: int | float | None = None) -> QColor:
    color = qcolor(name)
    if isinstance(alpha, float):
        color.setAlphaF(alpha)
    elif isinstance(alpha, int):
        color.setAlpha(alpha)
    return color


class WormPerformanceCurveWidget(InteractiveChartWidget):
    """Draw efficiency, power-loss and temperature-rise curves together."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._load_factor: list[float] = []
        self._efficiency: list[float] = []
        self._power_loss_kw: list[float] = []
        self._temperature_rise_k: list[float] = []
        self._current_index = -1
        self.setMinimumHeight(360)

    def set_curves(
        self,
        *,
        load_factor: Iterable[float],
        efficiency: Iterable[float],
        power_loss_kw: Iterable[float],
        temperature_rise_k: Iterable[float],
        current_index: int,
    ) -> None:
        self._load_factor = [float(v) for v in load_factor]
        self._efficiency = [float(v) for v in efficiency]
        self._power_loss_kw = [float(v) for v in power_loss_kw]
        self._temperature_rise_k = [float(v) for v in temperature_rise_k]
        self._current_index = int(current_index)
        self.update()

    def curve_data(self) -> tuple[list[float], list[float], list[float], list[float], int]:
        """Stored series and working-index consumed by paintEvent."""
        return (
            list(self._load_factor),
            list(self._efficiency),
            list(self._power_loss_kw),
            list(self._temperature_rise_k),
            self._current_index,
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter()
        if not painter.begin(self):
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.begin_interactive_paint()

            panel = QRectF(14.0, 14.0, self.width() - 28.0, self.height() - 28.0)
            painter.setPen(qpen("line_structural", 1.0))
            painter.setBrush(_token("surface_glass_soft"))
            painter.drawRoundedRect(panel, 10, 10)

            title_rect = QRectF(panel.left() + 18, panel.top() + 38, panel.width() - 36, 22)
            painter.setPen(qpen("ink_primary", 1.0))
            painter.setFont(make_ui_font(12, 600))
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "性能曲线")

            if len(self._load_factor) < 2:
                painter.setPen(qpen("ink_muted", 1.0))
                painter.setFont(make_ui_font(10))
                painter.drawText(panel, Qt.AlignmentFlag.AlignCenter, "执行计算后显示效率 / 损失功率曲线")
                return

            chart_top = panel.top() + 66
            chart_height = (panel.height() - 88) / 3.0
            charts = [
                ("efficiency", QRectF(panel.left() + 18, chart_top + chart_height * 0, panel.width() - 36, chart_height - 8), self._efficiency, _token("accent"), "效率 eta"),
                ("power_loss", QRectF(panel.left() + 18, chart_top + chart_height * 1, panel.width() - 36, chart_height - 8), self._power_loss_kw, _token("secondary"), "损失功率 P_loss [kW]"),
                ("temperature", QRectF(panel.left() + 18, chart_top + chart_height * 2, panel.width() - 36, chart_height - 8), self._temperature_rise_k, _token("warning_fg"), "温升 delta_T [K]"),
            ]
            for key, rect, values, color, label in charts:
                self._draw_chart(painter, key, rect, values, color, label)
            self.draw_interaction_overlay(painter)
        finally:
            painter.end()

    def _draw_chart(self, painter: QPainter, key: str, rect: QRectF, values: list[float], color: QColor, label: str) -> None:
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(qpen("ink_muted", 1.0))
        painter.setFont(make_ui_font(9, 500))
        painter.drawText(QRectF(rect.left() + 10, rect.top() + 8, 180, 14), Qt.AlignmentFlag.AlignLeft, label)

        plot = QRectF(rect.left() + 54, rect.top() + 12, rect.width() - 72, rect.height() - 28)
        painter.setPen(QPen(_token("line_structural", GRID_ALPHA), 1.0))
        for idx in range(1, 4):
            y = plot.top() + plot.height() * idx / 4.0
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        auto_x0 = min(self._load_factor)
        auto_x1 = max(self._load_factor)
        auto_y0 = min(values)
        auto_y1 = max(values)
        if auto_y1 <= auto_y0:
            auto_y1 = auto_y0 + 1.0
        y_pad = max((auto_y1 - auto_y0) * 0.08, 1e-9)
        samples = [
            ChartSample(load, value, f"负载系数={load:.4g} · {label}={value:.5g}")
            for load, value in zip(self._load_factor, values)
        ]
        x0, x1, y0, y1 = self.prepare_plot_context(
            key,
            plot,
            (auto_x0, auto_x1),
            (auto_y0 - y_pad, auto_y1 + y_pad),
            samples=samples,
            x_label="负载系数",
            y_label=label,
        )

        def sx(value: float) -> float:
            return self.map_data(key, value, y0).x()

        def sy(value: float) -> float:
            return self.map_data(key, x0, value).y()

        painter.setPen(QPen(color, 2.2))
        for idx in range(1, len(self._load_factor)):
            painter.drawLine(
                QPointF(sx(self._load_factor[idx - 1]), sy(values[idx - 1])),
                QPointF(sx(self._load_factor[idx]), sy(values[idx])),
            )

        if 0 <= self._current_index < len(self._load_factor):
            current_x = sx(self._load_factor[self._current_index])
            current_y = sy(values[self._current_index])
            painter.setPen(QPen(_token("ink_muted"), 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(current_x, plot.top()), QPointF(current_x, plot.bottom()))
            painter.setPen(QPen(color, 1.0))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(current_x, current_y), 4.0, 4.0)

        painter.setPen(qpen("ink_quiet", 1.0))
        painter.setFont(make_ui_font(8))
        painter.drawText(QRectF(rect.left() + 8, plot.center().y() - 8, 40, 16), Qt.AlignmentFlag.AlignRight, f"{y1:.2f}")
        painter.drawText(QRectF(rect.left() + 8, plot.bottom() - 8, 40, 16), Qt.AlignmentFlag.AlignRight, f"{y0:.2f}")
        painter.drawText(QRectF(plot.left(), plot.bottom() + 4, plot.width(), 14), Qt.AlignmentFlag.AlignCenter, "负载系数")
