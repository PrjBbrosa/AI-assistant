"""Shared interaction layer for native engineering data charts.

The chart widgets keep ownership of their engineering-specific drawing.  This
base class supplies a consistent viewport contract: fit, numeric axis ranges,
wheel zoom, drag pan, and nearest-sample readout.  Geometry schematics do not
inherit this class because their coordinates are illustrative rather than
measured data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.design_tokens import qcolor


@dataclass(frozen=True)
class ChartSample:
    """One inspectable data point in chart data coordinates."""

    x: float
    y: float
    label: str


@dataclass
class _PlotContext:
    key: str
    rect: QRectF
    auto_bounds: tuple[float, float, float, float]
    view_bounds: tuple[float, float, float, float]
    samples: list[ChartSample]
    x_label: str
    y_label: str
    x_log: bool = False
    y_log: bool = False


class InteractiveChartWidget(QWidget):
    """Base class for charts with one or more independently adjustable axes."""

    toolbar_height = 30

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("ChartSurface")
        self._contexts: dict[str, _PlotContext] = {}
        self._manual_bounds: dict[str, tuple[float, float, float, float]] = {}
        self._active_key: str | None = None
        self._hover_sample: tuple[str, ChartSample] | None = None
        self._drag_origin: QPointF | None = None
        self._drag_bounds: tuple[float, float, float, float] | None = None

        self.chart_toolbar = QFrame(self)
        self.chart_toolbar.setObjectName("ChartToolbar")
        toolbar_layout = QHBoxLayout(self.chart_toolbar)
        toolbar_layout.setContentsMargins(6, 2, 6, 2)
        toolbar_layout.setSpacing(4)

        self.chart_gesture_hint = QLabel("滚轮缩放 · 拖动平移 · 悬停取值", self.chart_toolbar)
        self.chart_gesture_hint.setObjectName("ChartGestureHint")
        toolbar_layout.addWidget(self.chart_gesture_hint)
        toolbar_layout.addStretch(1)

        self.chart_readout = QLabel("", self.chart_toolbar)
        self.chart_readout.setObjectName("ChartReadout")
        self.chart_readout.setMinimumWidth(110)
        self.chart_readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        toolbar_layout.addWidget(self.chart_readout, 1)

        self.fit_view_button = self._tool_button("适应", "恢复为全部数据范围")
        self.axis_range_button = self._tool_button("坐标", "输入当前图的 X/Y 坐标范围")
        toolbar_layout.addWidget(self.fit_view_button)
        toolbar_layout.addWidget(self.axis_range_button)
        self.fit_view_button.clicked.connect(self.reset_view)
        self.axis_range_button.clicked.connect(self._edit_axis_ranges)

    def _tool_button(self, text: str, tooltip: str) -> QToolButton:
        button = QToolButton(self.chart_toolbar)
        button.setObjectName("ChartToolButton")
        button.setText(text)
        button.setToolTip(tooltip)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.setAutoRaise(False)
        button.setFixedHeight(24)
        return button

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.chart_toolbar.setGeometry(8, 6, max(40, self.width() - 16), self.toolbar_height)
        self.chart_toolbar.raise_()

    def begin_interactive_paint(self) -> None:
        """Start a paint pass and discard contexts no longer drawn this frame."""
        self._contexts = {}

    @staticmethod
    def _safe_bounds(low: float, high: float, *, logarithmic: bool) -> tuple[float, float]:
        low = float(low)
        high = float(high)
        if logarithmic:
            low = max(low, 1e-300)
            high = max(high, low * (1.0 + 1e-9))
        elif high <= low:
            pad = max(abs(low) * 0.05, 0.5)
            low -= pad
            high += pad
        return low, high

    def prepare_plot_context(
        self,
        key: str,
        rect: QRectF,
        x_bounds: tuple[float, float],
        y_bounds: tuple[float, float],
        *,
        samples: Iterable[ChartSample] = (),
        x_label: str = "X",
        y_label: str = "Y",
        x_log: bool = False,
        y_log: bool = False,
    ) -> tuple[float, float, float, float]:
        """Register one data viewport and return its effective view bounds."""
        x0, x1 = self._safe_bounds(*x_bounds, logarithmic=x_log)
        y0, y1 = self._safe_bounds(*y_bounds, logarithmic=y_log)
        auto = (x0, x1, y0, y1)
        view = self._manual_bounds.get(key, auto)
        if not self._bounds_valid(view, x_log=x_log, y_log=y_log):
            view = auto
            self._manual_bounds.pop(key, None)
        context = _PlotContext(
            key=key,
            rect=QRectF(rect),
            auto_bounds=auto,
            view_bounds=view,
            samples=list(samples),
            x_label=x_label,
            y_label=y_label,
            x_log=x_log,
            y_log=y_log,
        )
        self._contexts[key] = context
        if self._active_key is None or self._active_key not in self._contexts:
            self._active_key = key
        return view

    @staticmethod
    def _bounds_valid(
        bounds: tuple[float, float, float, float], *, x_log: bool, y_log: bool
    ) -> bool:
        x0, x1, y0, y1 = bounds
        values = (x0, x1, y0, y1)
        return (
            all(math.isfinite(value) for value in values)
            and x1 > x0
            and y1 > y0
            and (not x_log or x0 > 0)
            and (not y_log or y0 > 0)
        )

    @staticmethod
    def _axis_forward(value: float, logarithmic: bool) -> float:
        return math.log10(max(value, 1e-300)) if logarithmic else value

    @staticmethod
    def _axis_inverse(value: float, logarithmic: bool) -> float:
        return 10.0**value if logarithmic else value

    def map_data(self, key: str, x: float, y: float) -> QPointF:
        context = self._contexts[key]
        x0, x1, y0, y1 = context.view_bounds
        tx0 = self._axis_forward(x0, context.x_log)
        tx1 = self._axis_forward(x1, context.x_log)
        ty0 = self._axis_forward(y0, context.y_log)
        ty1 = self._axis_forward(y1, context.y_log)
        tx = self._axis_forward(x, context.x_log)
        ty = self._axis_forward(y, context.y_log)
        px = context.rect.left() + (tx - tx0) / max(tx1 - tx0, 1e-300) * context.rect.width()
        py = context.rect.bottom() - (ty - ty0) / max(ty1 - ty0, 1e-300) * context.rect.height()
        return QPointF(px, py)

    def reset_view(self) -> None:
        """Restore every data panel to its full calculated extent."""
        self._manual_bounds.clear()
        self._hover_sample = None
        self.chart_readout.clear()
        self.update()

    def _context_at(self, position: QPointF) -> _PlotContext | None:
        for context in self._contexts.values():
            if context.rect.contains(position):
                return context
        return self._contexts.get(self._active_key or "")

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802
        context = self._context_at(event.position())
        if context is None or not context.rect.contains(event.position()):
            super().wheelEvent(event)
            return
        factor = 0.82 if event.angleDelta().y() > 0 else 1.22
        x_only = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        y_only = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._zoom_context(context, event.position(), factor, zoom_x=not y_only, zoom_y=not x_only)
        event.accept()

    def _zoom_context(
        self,
        context: _PlotContext,
        position: QPointF,
        factor: float,
        *,
        zoom_x: bool,
        zoom_y: bool,
    ) -> None:
        x0, x1, y0, y1 = context.view_bounds
        tx0 = self._axis_forward(x0, context.x_log)
        tx1 = self._axis_forward(x1, context.x_log)
        ty0 = self._axis_forward(y0, context.y_log)
        ty1 = self._axis_forward(y1, context.y_log)
        rx = min(1.0, max(0.0, (position.x() - context.rect.left()) / max(context.rect.width(), 1.0)))
        ry = min(1.0, max(0.0, (context.rect.bottom() - position.y()) / max(context.rect.height(), 1.0)))
        cx = tx0 + rx * (tx1 - tx0)
        cy = ty0 + ry * (ty1 - ty0)
        if zoom_x:
            tx0 = cx - (cx - tx0) * factor
            tx1 = cx + (tx1 - cx) * factor
        if zoom_y:
            ty0 = cy - (cy - ty0) * factor
            ty1 = cy + (ty1 - cy) * factor
        bounds = (
            self._axis_inverse(tx0, context.x_log),
            self._axis_inverse(tx1, context.x_log),
            self._axis_inverse(ty0, context.y_log),
            self._axis_inverse(ty1, context.y_log),
        )
        self._manual_bounds[context.key] = bounds
        context.view_bounds = bounds
        self._active_key = context.key
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            context = self._context_at(event.position())
            if context is not None and context.rect.contains(event.position()):
                self._active_key = context.key
                self._drag_origin = event.position()
                self._drag_bounds = context.view_bounds
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        context = self._context_at(event.position())
        if self._drag_origin is not None and self._drag_bounds is not None and context is not None:
            self._pan_context(context, event.position())
            event.accept()
            return
        if context is not None and context.rect.contains(event.position()):
            self._active_key = context.key
            self._update_nearest_sample(context, event.position())
        else:
            self._hover_sample = None
            self.chart_readout.clear()
        self.update()
        super().mouseMoveEvent(event)

    def _pan_context(self, context: _PlotContext, position: QPointF) -> None:
        assert self._drag_origin is not None and self._drag_bounds is not None
        x0, x1, y0, y1 = self._drag_bounds
        tx0 = self._axis_forward(x0, context.x_log)
        tx1 = self._axis_forward(x1, context.x_log)
        ty0 = self._axis_forward(y0, context.y_log)
        ty1 = self._axis_forward(y1, context.y_log)
        dx = (position.x() - self._drag_origin.x()) / max(context.rect.width(), 1.0) * (tx1 - tx0)
        dy = (position.y() - self._drag_origin.y()) / max(context.rect.height(), 1.0) * (ty1 - ty0)
        bounds = (
            self._axis_inverse(tx0 - dx, context.x_log),
            self._axis_inverse(tx1 - dx, context.x_log),
            self._axis_inverse(ty0 + dy, context.y_log),
            self._axis_inverse(ty1 + dy, context.y_log),
        )
        self._manual_bounds[context.key] = bounds
        context.view_bounds = bounds
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._drag_origin is not None:
            self._drag_origin = None
            self._drag_bounds = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        context = self._context_at(event.position())
        if context is not None:
            self._manual_bounds.pop(context.key, None)
            self._hover_sample = None
            self.chart_readout.clear()
            self.update()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _update_nearest_sample(self, context: _PlotContext, position: QPointF) -> None:
        candidates: list[tuple[float, ChartSample]] = []
        for sample in context.samples:
            if (context.x_log and sample.x <= 0) or (context.y_log and sample.y <= 0):
                continue
            point = self.map_data(context.key, sample.x, sample.y)
            distance = math.hypot(point.x() - position.x(), point.y() - position.y())
            candidates.append((distance, sample))
        if not candidates:
            self._hover_sample = None
            self.chart_readout.clear()
            return
        _distance, sample = min(candidates, key=lambda item: item[0])
        self._hover_sample = (context.key, sample)
        self.chart_readout.setText(sample.label)

    def draw_interaction_overlay(self, painter: QPainter) -> None:
        """Draw a crosshair for the currently inspected sample."""
        if self._hover_sample is None:
            return
        key, sample = self._hover_sample
        context = self._contexts.get(key)
        if context is None:
            return
        point = self.map_data(key, sample.x, sample.y)
        if not context.rect.contains(point):
            return
        painter.save()
        painter.setPen(QPen(qcolor("secondary"), 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(context.rect.left(), point.y()), QPointF(context.rect.right(), point.y()))
        painter.drawLine(QPointF(point.x(), context.rect.top()), QPointF(point.x(), context.rect.bottom()))
        painter.setBrush(qcolor("surface_field"))
        painter.setPen(QPen(qcolor("accent"), 1.5))
        painter.drawEllipse(point, 4.5, 4.5)
        painter.restore()

    def _edit_axis_ranges(self) -> None:
        context = self._contexts.get(self._active_key or "")
        if context is None:
            return
        dialog = QDialog(self)
        dialog.setObjectName("AxisRangeDialog")
        dialog.setWindowTitle(f"坐标范围 · {context.x_label} / {context.y_label}")
        root = QVBoxLayout(dialog)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        root.addLayout(form)
        values = context.view_bounds
        labels = ("X 最小值", "X 最大值", "Y 最小值", "Y 最大值")
        boxes: list[QDoubleSpinBox] = []
        for label, value in zip(labels, values):
            box = QDoubleSpinBox(dialog)
            box.setDecimals(8)
            box.setRange(-1e150, 1e150)
            box.setValue(value)
            box.setKeyboardTracking(False)
            form.addRow(label, box)
            boxes.append(box)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        root.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        bounds = tuple(box.value() for box in boxes)
        if not self._bounds_valid(bounds, x_log=context.x_log, y_log=context.y_log):
            return
        self._manual_bounds[context.key] = bounds  # type: ignore[assignment]
        context.view_bounds = bounds  # type: ignore[assignment]
        self.update()
