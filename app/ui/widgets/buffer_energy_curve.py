"""Custom F-x curve widget for buffer block energy simulation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


_BG = QColor("#FBF8F3")
_AXIS = QColor("#3F2E1E")
_GRID = QColor("#E5DED3")
_TEXT = QColor("#5B5147")
_LOADING = QColor("#D97757")
_UNLOADING = QColor("#3D6B8E")
_FILL = QColor(217, 119, 87, 46)
_LIMIT = QColor("#9D4F37")
_BOTTOM_OUT = QColor(170, 62, 42, 72)
_MARKER = QColor("#2F2A24")


class BufferEnergyCurveWidget(QWidget):
    """Draw loading/unloading F-x curves with impact annotations."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._loading: list[tuple[float, float]] = []
        self._unloading: list[tuple[float, float]] = []
        self._x_max_mm = 0.0
        self._available_stroke_mm = 0.0
        self._allowable_peak_n = 0.0
        self._bottom_out = False
        self.setMinimumHeight(260)
        self.setFont(make_ui_font(12))

    def set_curves(
        self,
        *,
        loading: Sequence[tuple[float, float]],
        unloading: Sequence[tuple[float, float]],
        x_max_mm: float,
        available_stroke_mm: float,
        allowable_peak_n: float,
        bottom_out: bool,
    ) -> None:
        self._loading = [(float(x), float(force)) for x, force in loading]
        self._unloading = [(float(x), float(force)) for x, force in unloading]
        self._x_max_mm = max(0.0, float(x_max_mm))
        self._available_stroke_mm = max(0.0, float(available_stroke_mm))
        self._allowable_peak_n = max(0.0, float(allowable_peak_n))
        self._bottom_out = bool(bottom_out)
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), _BG)

        plot = QRectF(self.rect()).adjusted(54, 18, -18, -38)
        if plot.width() <= 8 or plot.height() <= 8:
            return

        if not self._loading or not self._unloading:
            painter.setPen(_TEXT)
            painter.drawText(plot, Qt.AlignmentFlag.AlignCenter, "导入曲线后显示 F-x 滞回曲线")
            return

        max_x = max(
            1.0,
            self._available_stroke_mm,
            self._x_max_mm,
            *(x for x, _force in self._loading),
            *(x for x, _force in self._unloading),
        )
        max_f = max(
            1.0,
            self._allowable_peak_n,
            *(force for _x, force in self._loading),
            *(force for _x, force in self._unloading),
        )
        max_f *= 1.08

        def to_px(x_mm: float, force_n: float) -> QPointF:
            x = plot.left() + x_mm / max_x * plot.width()
            y = plot.bottom() - force_n / max_f * plot.height()
            return QPointF(x, y)

        self._draw_grid(painter, plot)

        if self._bottom_out and self._available_stroke_mm > self._x_max_mm:
            x0 = to_px(self._x_max_mm, 0.0).x()
            x1 = to_px(self._available_stroke_mm, 0.0).x()
            painter.fillRect(QRectF(x0, plot.top(), max(0.0, x1 - x0), plot.height()), _BOTTOM_OUT)

        self._draw_hysteresis_fill(painter, to_px)
        self._draw_polyline(painter, self._loading, to_px, QPen(_LOADING, 2.2))
        self._draw_polyline(
            painter,
            self._unloading,
            to_px,
            QPen(_UNLOADING, 2.0, Qt.PenStyle.DashLine),
        )
        self._draw_limits(painter, plot, to_px)
        self._draw_marker(painter, to_px)
        self._draw_labels(painter, plot, max_x, max_f)

    def _draw_grid(self, painter: QPainter, plot: QRectF) -> None:
        painter.setPen(QPen(_GRID, 1))
        for index in range(1, 5):
            y = plot.top() + plot.height() * index / 5
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            x = plot.left() + plot.width() * index / 5
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        painter.setPen(QPen(_AXIS, 1))
        painter.drawLine(plot.bottomLeft(), plot.bottomRight())
        painter.drawLine(plot.topLeft(), plot.bottomLeft())

    def _draw_hysteresis_fill(self, painter: QPainter, to_px) -> None:
        path = QPainterPath()
        path.moveTo(to_px(*self._loading[0]))
        for point in self._loading[1:]:
            path.lineTo(to_px(*point))
        for point in reversed(self._unloading):
            path.lineTo(to_px(*point))
        path.closeSubpath()
        painter.fillPath(path, _FILL)

    def _draw_polyline(self, painter: QPainter, points, to_px, pen: QPen) -> None:
        painter.setPen(pen)
        for start, end in zip(points, points[1:]):
            painter.drawLine(to_px(*start), to_px(*end))

    def _draw_limits(self, painter: QPainter, plot: QRectF, to_px) -> None:
        painter.setPen(QPen(_LIMIT, 1, Qt.PenStyle.DotLine))
        if self._available_stroke_mm > 0:
            x = to_px(self._available_stroke_mm, 0.0).x()
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            painter.drawText(QPointF(x + 4, plot.bottom() - 6), "行程限值")
        if self._allowable_peak_n > 0:
            y = to_px(0.0, self._allowable_peak_n).y()
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.drawText(QPointF(plot.left() + 6, y - 4), "峰值力限值")

    def _draw_marker(self, painter: QPainter, to_px) -> None:
        if self._x_max_mm <= 0:
            return
        force = self._interp_loading(self._x_max_mm)
        point = to_px(self._x_max_mm, force)
        painter.setPen(QPen(_MARKER, 1.2))
        painter.setBrush(_MARKER)
        painter.drawEllipse(point, 4.0, 4.0)
        label = "触底" if self._bottom_out else "最大压缩"
        painter.drawText(point + QPointF(7, -7), f"{label} {self._x_max_mm:.2f} mm")

    def _draw_labels(self, painter: QPainter, plot: QRectF, max_x: float, max_f: float) -> None:
        painter.setPen(_TEXT)
        painter.drawText(QPointF(plot.left(), plot.bottom() + 24), "0")
        painter.drawText(QPointF(plot.right() - 72, plot.bottom() + 24), f"{max_x:.1f} mm")
        painter.drawText(QPointF(plot.left() - 48, plot.top() + 8), f"{max_f:.0f} N")
        painter.drawText(QPointF(plot.right() - 116, plot.top() + 16), "加载")
        painter.setPen(_LOADING)
        painter.drawLine(QPointF(plot.right() - 74, plot.top() + 12), QPointF(plot.right() - 50, plot.top() + 12))
        painter.setPen(_TEXT)
        painter.drawText(QPointF(plot.right() - 116, plot.top() + 34), "卸载")
        painter.setPen(QPen(_UNLOADING, 1.8, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(plot.right() - 74, plot.top() + 30), QPointF(plot.right() - 50, plot.top() + 30))

    def _interp_loading(self, x_mm: float) -> float:
        if not self._loading:
            return 0.0
        if x_mm <= self._loading[0][0]:
            return self._loading[0][1]
        for (x0, f0), (x1, f1) in zip(self._loading, self._loading[1:]):
            if x0 <= x_mm <= x1 and x1 > x0:
                ratio = (x_mm - x0) / (x1 - x0)
                return f0 + ratio * (f1 - f0)
        return self._loading[-1][1]
