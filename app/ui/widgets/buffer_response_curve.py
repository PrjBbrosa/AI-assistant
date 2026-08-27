"""Switchable time-response curve widget for buffer block simulation."""

from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.design_tokens import qcolor, qpen
from app.ui.fonts import make_ui_font
from app.ui.widgets.interactive_chart import ChartSample, InteractiveChartWidget


GRID_ALPHA = 0.55

_VARIABLES = {
    "x": ("displacement_mm", "位移 mm"),
    "v": ("velocity_m_s", "速度 m/s"),
    "a": ("acceleration_m_s2", "加速度 m/s^2"),
    "F": ("force_n", "反力 N"),
}


def _token(name: str, alpha: int | float | None = None) -> QColor:
    color = qcolor(name)
    if isinstance(alpha, float):
        color.setAlphaF(alpha)
    elif isinstance(alpha, int):
        color.setAlpha(alpha)
    return color


class BufferResponseCurveWidget(InteractiveChartWidget):
    """Draw x(t), v(t), a(t), or F(t) from reconstructed time response."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._response: Optional[dict[str, Any]] = None
        self._variable = "x"
        self.setMinimumHeight(300)
        self.setFont(make_ui_font(12))

    def set_response(self, response: Optional[dict[str, Any]]) -> None:
        self._response = response
        self.update()

    def set_variable(self, variable: str) -> None:
        if variable not in _VARIABLES:
            raise ValueError(f"未知时域变量: {variable!r}")
        self._variable = variable
        self.reset_view()
        self.update()

    def variable(self) -> str:
        return self._variable

    def response_data(self) -> tuple[str, Optional[dict[str, Any]]]:
        """Stored variable key and response dict consumed by paintEvent."""
        return self._variable, self._response

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), _token("surface_glass_soft"))
        self.begin_interactive_paint()

        plot = QRectF(self.rect()).adjusted(58, 58, -18, -38)
        if plot.width() <= 8 or plot.height() <= 8:
            return

        self._draw_header(painter)
        if self._response is None:
            painter.setPen(qpen("ink_muted", 1.0))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "执行仿真后显示响应时程")
            return

        key, axis_label = _VARIABLES[self._variable]
        times = [float(v) for v in self._response.get("time_s", [])]
        values = [float(v) for v in self._response.get(key, [])]
        if len(times) < 2 or len(times) != len(values):
            painter.setPen(qpen("ink_muted", 1.0))
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "响应数据不足")
            return

        auto_t_min = times[0]
        auto_t_max = max(times[-1], auto_t_min + 1e-9)
        auto_y_min = min(values)
        auto_y_max = max(values)
        if abs(auto_y_max - auto_y_min) < 1e-12:
            auto_y_min -= 0.5
            auto_y_max += 0.5
        else:
            pad = (auto_y_max - auto_y_min) * 0.10
            auto_y_min -= pad
            auto_y_max += pad
        samples = [
            ChartSample(t_s, value, f"t={t_s:.6g} s · {axis_label}={value:.6g}")
            for t_s, value in zip(times, values)
        ]
        t_min, t_max, y_min, y_max = self.prepare_plot_context(
            f"response_{self._variable}",
            plot,
            (auto_t_min, auto_t_max),
            (auto_y_min, auto_y_max),
            samples=samples,
            x_label="时间 t [s]",
            y_label=axis_label,
        )

        def to_px(t_s: float, value: float) -> QPointF:
            return self.map_data(f"response_{self._variable}", t_s, value)

        self._draw_grid(painter, plot, to_px, y_min, y_max)
        painter.setPen(QPen(_token("accent"), 2.0))
        for index in range(len(times) - 1):
            painter.drawLine(to_px(times[index], values[index]), to_px(times[index + 1], values[index + 1]))
        self._draw_markers(painter, plot, times, values, to_px)
        self._draw_labels(painter, plot, axis_label, t_max, y_min, y_max)
        self.draw_interaction_overlay(painter)

    def _draw_header(self, painter: QPainter) -> None:
        if self._response is None:
            return
        compression = float(self._response.get("compression_duration_s", 0.0)) * 1000.0
        rebound = float(self._response.get("rebound_duration_s", 0.0)) * 1000.0
        total = float(self._response.get("duration_s", 0.0)) * 1000.0
        painter.setPen(qpen("ink_muted", 1.0))
        painter.drawText(
            QRectF(self.rect()).adjusted(10, 38, -10, -4),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            f"压缩 {compression:.2f} ms    回弹 {rebound:.2f} ms    总时长 {total:.2f} ms",
        )

    def _draw_grid(self, painter: QPainter, plot: QRectF, to_px, y_min: float, y_max: float) -> None:
        painter.setPen(QPen(_token("line_structural", GRID_ALPHA), 1))
        for index in range(1, 5):
            y = plot.top() + plot.height() * index / 5
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            x = plot.left() + plot.width() * index / 5
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        if y_min < 0.0 < y_max:
            zero_y = to_px(0.0, 0.0).y()
            painter.setPen(QPen(_token("ink_quiet"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(plot.left(), zero_y), QPointF(plot.right(), zero_y))
        painter.setPen(qpen("ink_primary", 1))
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        painter.drawLine(plot.topLeft(), plot.bottomLeft())

    def _draw_markers(self, painter: QPainter, plot: QRectF, times, values, to_px) -> None:
        displacements = self._response.get("displacement_mm", []) if self._response else []
        if displacements and len(displacements) == len(times):
            peak_index = max(range(len(displacements)), key=lambda idx: float(displacements[idx]))
            peak_t = times[peak_index]
            painter.setPen(QPen(_token("accent"), 1.0, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(to_px(peak_t, values[peak_index]).x(), plot.top()), QPointF(to_px(peak_t, values[peak_index]).x(), plot.bottom()))
            painter.setBrush(_token("accent"))
            painter.drawEllipse(to_px(peak_t, values[peak_index]), 3.5, 3.5)

        rebound_duration = float(self._response.get("rebound_duration_s", 0.0)) if self._response else 0.0
        if rebound_duration <= 0.0:
            painter.setPen(QPen(_token("fail_fg"), 1.2, Qt.PenStyle.DashLine))
            end_x = to_px(times[-1], values[-1]).x()
            painter.drawLine(QPointF(end_x, plot.top()), QPointF(end_x, plot.bottom()))
            painter.drawText(QPointF(end_x - 88, plot.top() + 16), "触底，速度未归零")

    def _draw_labels(
        self,
        painter: QPainter,
        plot: QRectF,
        axis_label: str,
        t_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        painter.setPen(qpen("ink_muted", 1.0))
        painter.drawText(QPointF(plot.left(), plot.bottom() + 24), "0 s")
        painter.drawText(QPointF(plot.right() - 72, plot.bottom() + 24), f"{t_max:.4f} s")
        painter.drawText(QPointF(plot.left() - 52, plot.bottom()), f"{y_min:.2g}")
        painter.drawText(QPointF(plot.left() - 52, plot.top() + 8), f"{y_max:.2g}")
        painter.drawText(QPointF(plot.left(), plot.top() - 10), axis_label)
