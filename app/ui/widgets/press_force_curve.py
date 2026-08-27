"""Press-force curve widget for interference-fit assembly."""

from __future__ import annotations

from typing import Iterable

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


class PressForceCurveWidget(InteractiveChartWidget):
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

    def curve_data(self) -> tuple[list[float], list[float], float, float, float]:
        """Stored series and marker x-values consumed by paintEvent."""
        return (
            list(self._x),
            list(self._y),
            self._delta_min,
            self._delta_max,
            self._delta_req,
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.begin_interactive_paint()

        w = float(self.width())
        h = float(self.height())
        margin = 14.0
        panel = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(_token("surface_glass_soft"))
        painter.drawRoundedRect(panel, 10, 10)

        plot = QRectF(panel.left() + 68, panel.top() + 40, panel.width() - 98, panel.height() - 86)
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(plot)

        if len(self._x) < 2 or len(self._y) < 2:
            painter.setPen(qpen("ink_muted", 1.0))
            painter.setFont(make_ui_font(11))
            painter.drawText(panel, Qt.AlignmentFlag.AlignCenter, "执行校核后显示压入力曲线")
            return

        auto_x_min = min(self._x)
        auto_x_max = max(self._x)
        auto_y_min = 0.0
        y_max_raw = max(max(self._y), 1.0)
        # Auto-scale: use kN when peak force >= 10 kN for readability
        use_kn = y_max_raw >= 10_000.0
        y_scale = 0.001 if use_kn else 1.0
        y_unit = "kN" if use_kn else "N"
        auto_y_max = y_max_raw * y_scale
        samples = [
            ChartSample(
                x,
                y * y_scale,
                f"delta={x:.4g} um · F={y * y_scale:.5g} {y_unit}",
            )
            for x, y in zip(self._x, self._y)
        ]
        x_min, x_max, y_min, y_max = self.prepare_plot_context(
            "press_force",
            plot,
            (auto_x_min, auto_x_max),
            (auto_y_min, auto_y_max),
            samples=samples,
            x_label="过盈量 delta [um]",
            y_label=f"压入力 F_press [{y_unit}]",
        )

        def sx(x: float) -> float:
            return self.map_data("press_force", x, y_min).x()

        def sy(y_raw: float) -> float:
            y = y_raw * y_scale
            return self.map_data("press_force", x_min, y).y()

        # Grid
        grid_pen = QPen(_token("line_structural", GRID_ALPHA), 1.0)
        painter.setPen(grid_pen)
        for i in range(1, 5):
            yy = plot.top() + plot.height() * i / 5.0
            painter.drawLine(QPointF(plot.left(), yy), QPointF(plot.right(), yy))

        # Highlight available interference window [delta_min, delta_max].
        left_x = max(plot.left(), min(plot.right(), sx(self._delta_min)))
        right_x = max(plot.left(), min(plot.right(), sx(self._delta_max)))
        if right_x > left_x:
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(_token("secondary", 28))
            painter.drawRect(QRectF(left_x, plot.top(), right_x - left_x, plot.height()))

        # Curve
        curve_pen = qpen("accent", 2.4)
        painter.setPen(curve_pen)
        for i in range(1, len(self._x)):
            painter.drawLine(QPointF(sx(self._x[i - 1]), sy(self._y[i - 1])), QPointF(sx(self._x[i]), sy(self._y[i])))

        # Explicit axes with arrow heads and ticks.
        axis_pen = qpen("ink_muted", 1.3)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right() + 10, plot.bottom()))
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.left(), plot.top() - 10))
        self._draw_arrow_head(painter, QPointF(plot.right() + 10, plot.bottom()), QPointF(1.0, 0.0), _token("ink_muted"))
        self._draw_arrow_head(painter, QPointF(plot.left(), plot.top() - 10), QPointF(0.0, -1.0), _token("ink_muted"))

        painter.setFont(make_ui_font(8))
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
        self._draw_marker(painter, sx, plot, self._delta_min, _token("secondary"), "delta_min")
        self._draw_marker(painter, sx, plot, self._delta_max, _token("pass_fg"), "delta_max")
        self._draw_marker(painter, sx, plot, self._delta_req, _token("fail_fg"), "delta_req")
        self._draw_curve_point(painter, sx(self._delta_min), sy(self._interp_force(self._delta_min)), _token("secondary"))
        self._draw_curve_point(painter, sx(self._delta_max), sy(self._interp_force(self._delta_max)), _token("pass_fg"))

        # Axis labels
        painter.setPen(qpen("ink_muted", 1.0))
        painter.setFont(make_ui_font(10))
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
        painter.setFont(make_ui_font(9))
        painter.setPen(qpen("ink_muted", 1.0))
        painter.drawText(
            QRectF(plot.right() - 130, plot.top() + 6, 124, 70),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            label,
        )
        self.draw_interaction_overlay(painter)

    def _draw_marker(self, painter: QPainter, sx, plot: QRectF, x: float, color: QColor, name: str) -> None:
        x_coord = sx(x)
        if x_coord < plot.left() or x_coord > plot.right():
            return
        pen = QPen(color, 1.4, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(x_coord, plot.top()), QPointF(x_coord, plot.bottom()))
        painter.setFont(make_ui_font(8))
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
