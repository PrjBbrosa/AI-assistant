"""Performance curve panel for worm gear modules."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


class WormPerformanceCurveWidget(QWidget):
    """Draw efficiency, power-loss and temperature-rise curves together."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._load_factor: list[float] = []
        self._efficiency: list[float] = []
        self._power_loss_kw: list[float] = []
        self._temperature_rise_k: list[float] = []
        self._current_index = -1
        self.setMinimumHeight(300)

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

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter()
        if not painter.begin(self):
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            panel = QRectF(14.0, 14.0, self.width() - 28.0, self.height() - 28.0)
            painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
            painter.setBrush(QColor("#FBF8F3"))
            painter.drawRoundedRect(panel, 10, 10)

            title_rect = QRectF(panel.left() + 18, panel.top() + 12, panel.width() - 36, 22)
            painter.setPen(QPen(QColor("#2E2A25"), 1.0))
            painter.setFont(make_ui_font(12, 600))
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "性能曲线")

            if len(self._load_factor) < 2:
                painter.setPen(QPen(QColor("#6B665E"), 1.0))
                painter.setFont(make_ui_font(10))
                painter.drawText(panel, Qt.AlignmentFlag.AlignCenter, "执行计算后显示效率 / 损失功率曲线")
                return

            chart_top = panel.top() + 48
            chart_height = (panel.height() - 72) / 3.0
            charts = [
                (QRectF(panel.left() + 18, chart_top + chart_height * 0, panel.width() - 36, chart_height - 10), self._efficiency, QColor("#D97757"), "效率 eta"),
                (QRectF(panel.left() + 18, chart_top + chart_height * 1, panel.width() - 36, chart_height - 10), self._power_loss_kw, QColor("#5A7D9E"), "损失功率 P_loss"),
                (QRectF(panel.left() + 18, chart_top + chart_height * 2, panel.width() - 36, chart_height - 10), self._temperature_rise_k, QColor("#8A7740"), "温升 delta_T (K)"),
            ]
            for rect, values, color, label in charts:
                self._draw_chart(painter, rect, values, color, label)
        finally:
            painter.end()

    def _draw_chart(self, painter: QPainter, rect: QRectF, values: list[float], color: QColor, label: str) -> None:
        painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(QColor("#6B665E"), 1.0))
        painter.setFont(make_ui_font(9, 500))
        painter.drawText(QRectF(rect.left() + 10, rect.top() + 8, 180, 14), Qt.AlignmentFlag.AlignLeft, label)

        plot = QRectF(rect.left() + 54, rect.top() + 12, rect.width() - 72, rect.height() - 28)
        painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
        for idx in range(1, 4):
            y = plot.top() + plot.height() * idx / 4.0
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        x0 = min(self._load_factor)
        x1 = max(self._load_factor)
        y0 = min(values)
        y1 = max(values)
        if y1 <= y0:
            y1 = y0 + 1.0

        def sx(value: float) -> float:
            if x1 <= x0:
                return plot.left()
            return plot.left() + (value - x0) / (x1 - x0) * plot.width()

        def sy(value: float) -> float:
            return plot.bottom() - (value - y0) / (y1 - y0) * plot.height()

        painter.setPen(QPen(color, 2.2))
        for idx in range(1, len(self._load_factor)):
            painter.drawLine(
                QPointF(sx(self._load_factor[idx - 1]), sy(values[idx - 1])),
                QPointF(sx(self._load_factor[idx]), sy(values[idx])),
            )

        if 0 <= self._current_index < len(self._load_factor):
            current_x = sx(self._load_factor[self._current_index])
            current_y = sy(values[self._current_index])
            painter.setPen(QPen(QColor("#5C574F"), 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(current_x, plot.top()), QPointF(current_x, plot.bottom()))
            painter.setPen(QPen(color, 1.0))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(current_x, current_y), 4.0, 4.0)

        painter.setPen(QPen(QColor("#7A7369"), 1.0))
        painter.setFont(make_ui_font(8))
        painter.drawText(QRectF(rect.left() + 8, plot.center().y() - 8, 40, 16), Qt.AlignmentFlag.AlignRight, f"{y1:.2f}")
        painter.drawText(QRectF(rect.left() + 8, plot.bottom() - 8, 40, 16), Qt.AlignmentFlag.AlignRight, f"{y0:.2f}")
        painter.drawText(QRectF(plot.left(), plot.bottom() + 4, plot.width(), 14), Qt.AlignmentFlag.AlignCenter, "负载系数")
