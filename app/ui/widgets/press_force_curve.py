"""Press-force curve widget for interference-fit assembly."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class PressForceCurveWidget(QWidget):
    """Draw F_press - interference curve with key markers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._x: list[float] = []
        self._y: list[float] = []
        self._delta_min = 0.0
        self._delta_max = 0.0
        self._delta_req = 0.0
        self.setMinimumHeight(280)

    def set_curve(
        self,
        interference_um: Iterable[float],
        force_n: Iterable[float],
        delta_min_um: float,
        delta_max_um: float,
        delta_required_um: float,
    ) -> None:
        self._x = [float(v) for v in interference_um]
        self._y = [float(v) for v in force_n]
        self._delta_min = max(0.0, float(delta_min_um))
        self._delta_max = max(0.0, float(delta_max_um))
        self._delta_req = max(0.0, float(delta_required_um))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        margin = 14.0
        panel = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
        painter.setBrush(QColor("#FBF8F3"))
        painter.drawRoundedRect(panel, 10, 10)

        plot = QRectF(panel.left() + 68, panel.top() + 20, panel.width() - 98, panel.height() - 66)
        painter.setPen(QPen(QColor("#E1DBD1"), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(plot)

        if len(self._x) < 2 or len(self._y) < 2:
            painter.setPen(QPen(QColor("#6B665E"), 1.0))
            painter.setFont(QFont("Avenir Next", 11))
            painter.drawText(panel, Qt.AlignmentFlag.AlignCenter, "执行校核后显示压入力曲线")
            return

        x_min = min(self._x)
        x_max = max(self._x)
        y_min = 0.0
        y_max_raw = max(max(self._y), 1.0)
        # Auto-scale: use kN when peak force >= 10 kN for readability
        use_kn = y_max_raw >= 10_000.0
        y_scale = 0.001 if use_kn else 1.0
        y_unit = "kN" if use_kn else "N"
        y_max = y_max_raw * y_scale

        def sx(x: float) -> float:
            if x_max <= x_min:
                return plot.left()
            return plot.left() + (x - x_min) / (x_max - x_min) * plot.width()

        def sy(y_raw: float) -> float:
            y = y_raw * y_scale
            if y_max <= y_min:
                return plot.bottom()
            return plot.bottom() - (y - y_min) / (y_max - y_min) * plot.height()

        # Grid
        grid_pen = QPen(QColor("#ECE6DC"), 1.0)
        painter.setPen(grid_pen)
        for i in range(1, 5):
            yy = plot.top() + plot.height() * i / 5.0
            painter.drawLine(QPointF(plot.left(), yy), QPointF(plot.right(), yy))

        # Highlight available interference window [delta_min, delta_max].
        left_x = max(plot.left(), min(plot.right(), sx(self._delta_min)))
        right_x = max(plot.left(), min(plot.right(), sx(self._delta_max)))
        if right_x > left_x:
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(QColor(76, 98, 122, 28))
            painter.drawRect(QRectF(left_x, plot.top(), right_x - left_x, plot.height()))

        # Curve
        curve_pen = QPen(QColor("#D97757"), 2.4)
        painter.setPen(curve_pen)
        for i in range(1, len(self._x)):
            painter.drawLine(QPointF(sx(self._x[i - 1]), sy(self._y[i - 1])), QPointF(sx(self._x[i]), sy(self._y[i])))

        # Explicit axes with arrow heads and ticks.
        axis_pen = QPen(QColor("#5C574F"), 1.3)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right() + 10, plot.bottom()))
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.left(), plot.top() - 10))
        self._draw_arrow_head(painter, QPointF(plot.right() + 10, plot.bottom()), QPointF(1.0, 0.0), QColor("#5C574F"))
        self._draw_arrow_head(painter, QPointF(plot.left(), plot.top() - 10), QPointF(0.0, -1.0), QColor("#5C574F"))

        painter.setFont(QFont("Avenir Next", 8))
        for i in range(6):
            x_tick = plot.left() + plot.width() * i / 5.0
            painter.drawLine(QPointF(x_tick, plot.bottom()), QPointF(x_tick, plot.bottom() + 4))
            val = x_min + (x_max - x_min) * i / 5.0
            painter.drawText(QRectF(x_tick - 24, plot.bottom() + 6, 48, 14), Qt.AlignmentFlag.AlignCenter, f"{val:.0f}")
        y_tick_fmt = "{:.1f}" if use_kn else "{:.0f}"
        for i in range(6):
            y_tick = plot.bottom() - plot.height() * i / 5.0
            painter.drawLine(QPointF(plot.left() - 4, y_tick), QPointF(plot.left(), y_tick))
            val = y_min + (y_max - y_min) * i / 5.0
            painter.drawText(QRectF(plot.left() - 56, y_tick - 7, 50, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, y_tick_fmt.format(val))

        # Markers for min/max/required interference
        self._draw_marker(painter, sx, plot, self._delta_min, QColor("#4C627A"), "delta_min")
        self._draw_marker(painter, sx, plot, self._delta_max, QColor("#5A8A5E"), "delta_max")
        self._draw_marker(painter, sx, plot, self._delta_req, QColor("#7F2D1A"), "delta_req")
        self._draw_curve_point(painter, sx(self._delta_min), sy(self._interp_force(self._delta_min)), QColor("#4C627A"))
        self._draw_curve_point(painter, sx(self._delta_max), sy(self._interp_force(self._delta_max)), QColor("#5A8A5E"))

        # Axis labels
        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(QFont("Avenir Next", 10))
        painter.drawText(QRectF(plot.left(), panel.bottom() - 22, plot.width(), 18), Qt.AlignmentFlag.AlignCenter, "过盈量 delta (um)")
        painter.save()
        painter.translate(panel.left() + 20, plot.center().y())
        painter.rotate(-90)
        painter.drawText(QRectF(-plot.height() / 2, -22, plot.height(), 18), Qt.AlignmentFlag.AlignCenter, f"压入力 F_press ({y_unit})")
        painter.restore()

        # Values
        f_max_raw = max(self._y)
        f_max_label = f"Fmax={f_max_raw * 0.001:,.1f} kN" if use_kn else f"Fmax={f_max_raw:,.0f} N"
        label = (
            f"{f_max_label}\n"
            f"delta_min={self._delta_min:.2f} um\n"
            f"delta_max={self._delta_max:.2f} um\n"
            f"delta_req={self._delta_req:.2f} um"
        )
        painter.setFont(QFont("Avenir Next", 9))
        painter.setPen(QPen(QColor("#6B665E"), 1.0))
        painter.drawText(
            QRectF(plot.right() - 130, plot.top() + 6, 124, 70),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            label,
        )

    def _draw_marker(self, painter: QPainter, sx, plot: QRectF, x: float, color: QColor, name: str) -> None:
        x_coord = sx(x)
        if x_coord < plot.left() or x_coord > plot.right():
            return
        pen = QPen(color, 1.4, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(x_coord, plot.top()), QPointF(x_coord, plot.bottom()))
        painter.setFont(QFont("Avenir Next", 8))
        painter.drawText(QRectF(x_coord - 42, plot.top() + 3, 84, 14), Qt.AlignmentFlag.AlignCenter, name)

    def _interp_force(self, x: float) -> float:
        if not self._x or not self._y:
            return 0.0
        if x <= self._x[0]:
            return self._y[0]
        if x >= self._x[-1]:
            return self._y[-1]
        for idx in range(1, len(self._x)):
            x0 = self._x[idx - 1]
            x1 = self._x[idx]
            if x <= x1:
                y0 = self._y[idx - 1]
                y1 = self._y[idx]
                if x1 <= x0:
                    return y0
                t = (x - x0) / (x1 - x0)
                return y0 + t * (y1 - y0)
        return self._y[-1]

    def _draw_curve_point(self, painter: QPainter, x: float, y: float, color: QColor) -> None:
        painter.setPen(QPen(color, 1.0))
        painter.setBrush(color)
        painter.drawEllipse(QPointF(x, y), 3.5, 3.5)

    def _draw_arrow_head(self, painter: QPainter, point: QPointF, direction: QPointF, color: QColor) -> None:
        painter.setPen(QPen(color, 1.2))
        ux = direction.x()
        uy = direction.y()
        size = 7.0
        left = QPointF(
            point.x() - ux * size - uy * size * 0.5,
            point.y() - uy * size + ux * size * 0.5,
        )
        right = QPointF(
            point.x() - ux * size + uy * size * 0.5,
            point.y() - uy * size - ux * size * 0.5,
        )
        painter.drawLine(point, left)
        painter.drawLine(point, right)
