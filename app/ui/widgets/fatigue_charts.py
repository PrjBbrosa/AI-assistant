"""Lightweight native-Qt charts for the fatigue reliability page."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app.ui.design_tokens import qcolor
from app.ui.widgets.interactive_chart import ChartSample, InteractiveChartWidget


_INK = qcolor("ink_primary")
_MUTED = qcolor("ink_muted")
_GRID = qcolor("line_structural")
_ACCENT = qcolor("accent")
_BLUE = qcolor("secondary")
_RUNOUT = qcolor("warning_fg")


class _ChartBase(InteractiveChartWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(300)

    def _frame(self) -> QRectF:
        return QRectF(58, 44, max(80.0, self.width() - 100.0), max(80.0, self.height() - 90.0))

    @staticmethod
    def _line(painter: QPainter, color: QColor, width: float = 1.0, style=Qt.PenStyle.SolidLine) -> None:
        painter.setPen(QPen(color, width, style))

    def _empty(self, painter: QPainter, text: str) -> None:
        painter.setPen(_MUTED)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class FatigueSnChart(_ChartBase):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._specimens: list[dict[str, Any]] = []
        self._fit: dict[str, Any] = {}
        self._survival = 0.9

    def set_data(self, specimens: list[dict[str, Any]], fit: dict[str, Any], survival: float) -> None:
        self._specimens = list(specimens)
        self._fit = dict(fit)
        self._survival = survival
        self.update()

    def clear(self) -> None:
        self.reset_view()
        self.set_data([], {}, 0.9)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.begin_interactive_paint()
        if not self._specimens:
            self._empty(painter, "导入 S-N 试验数据后显示断裂点与 runout")
            return
        points = [
            (float(row.get("cycles", 0)), float(row.get("stress_amplitude_mpa", row.get("amplitude_mpa", 0))))
            for row in self._specimens
            if float(row.get("cycles", 0)) > 0
            and float(row.get("stress_amplitude_mpa", row.get("amplitude_mpa", 0))) > 0
        ]
        if not points:
            self._empty(painter, "S-N 数据没有有效正值")
            return
        frame = self._frame()
        xs = [math.log10(item[0]) for item in points]
        ys = [math.log10(item[1]) for item in points]
        x_pad = max((max(xs) - min(xs)) * 0.15, 0.35)
        y_pad = max((max(ys) - min(ys)) * 0.15, 0.08)
        auto_x = (10 ** (min(xs) - x_pad), 10 ** (max(xs) + x_pad))
        auto_y = (10 ** (min(ys) - y_pad), 10 ** (max(ys) + y_pad))
        samples = [
            ChartSample(
                cycles,
                stress,
                f"{row.get('specimen_id', '试样')} · N={cycles:.4g} · Sa={stress:.4g} MPa · {row.get('status', 'failure')}",
            )
            for row in self._specimens
            if (cycles := float(row.get("cycles", 0))) > 0
            and (stress := float(row.get("stress_amplitude_mpa", row.get("amplitude_mpa", 0)))) > 0
        ]
        x_min, x_max, y_min, y_max = self.prepare_plot_context(
            "sn",
            frame,
            auto_x,
            auto_y,
            samples=samples,
            x_label="寿命 N [cycles]",
            y_label="应力幅 Sa [MPa]",
            x_log=True,
            y_log=True,
        )

        def map_point(cycles: float, stress: float) -> QPointF:
            return self.map_data("sn", cycles, stress)

        self._line(painter, _GRID)
        for index in range(6):
            ratio = index / 5.0
            x = frame.left() + ratio * frame.width()
            y = frame.top() + ratio * frame.height()
            painter.drawLine(QPointF(x, frame.top()), QPointF(x, frame.bottom()))
            painter.drawLine(QPointF(frame.left(), y), QPointF(frame.right(), y))
        painter.setPen(_MUTED)
        for index in range(6):
            ratio = index / 5.0
            x = frame.left() + ratio * frame.width()
            y = frame.top() + ratio * frame.height()
            log_n = math.log10(x_min) + ratio * (math.log10(x_max) - math.log10(x_min))
            log_s = math.log10(y_max) - ratio * (math.log10(y_max) - math.log10(y_min))
            painter.drawText(QRectF(x - 34, frame.bottom() + 2, 68, 18), Qt.AlignmentFlag.AlignCenter, f"{10**log_n:.2g}")
            painter.drawText(QRectF(frame.left() - 54, y - 9, 48, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{10**log_s:.2g}")
        self._line(painter, _INK, 1.2)
        painter.drawRect(frame)
        painter.drawText(QRectF(frame.left(), frame.bottom() + 12, frame.width(), 22), Qt.AlignmentFlag.AlignCenter, "寿命 N [cycles]（log）")
        painter.save()
        painter.translate(16, frame.center().y())
        painter.rotate(-90)
        painter.drawText(QRectF(-frame.height() / 2, -12, frame.height(), 24), Qt.AlignmentFlag.AlignCenter, "应力幅 Sa [MPa]（log）")
        painter.restore()

        if self._fit.get("status") == "valid":
            try:
                from scipy.stats import norm

                for probability, color, style in (
                    (0.5, _BLUE, Qt.PenStyle.SolidLine),
                    (self._survival, _ACCENT, Qt.PenStyle.DashLine),
                ):
                    z = float(norm.ppf(1.0 - probability))
                    path = QPainterPath()
                    for index in range(101):
                        log_s = math.log10(y_min) + index / 100.0 * (math.log10(y_max) - math.log10(y_min))
                        log_n = (
                            float(self._fit["a"])
                            - float(self._fit["b"]) * log_s
                            + float(self._fit["scatter_log10_n"]) * z
                        )
                        point = map_point(10**log_n, 10**log_s)
                        path.moveTo(point) if index == 0 else path.lineTo(point)
                    self._line(painter, color, 2.0, style)
                    painter.drawPath(path)
            except Exception:
                pass

        for row in self._specimens:
            cycles = float(row.get("cycles", 0))
            stress = float(row.get("stress_amplitude_mpa", row.get("amplitude_mpa", 0)))
            if cycles <= 0 or stress <= 0:
                continue
            point = map_point(cycles, stress)
            status = str(row.get("status", "failure"))
            if status == "runout":
                self._line(painter, _RUNOUT, 2.0)
                painter.drawEllipse(point, 4, 4)
                painter.drawLine(point + QPointF(4, 0), point + QPointF(14, 0))
                painter.drawLine(point + QPointF(14, 0), point + QPointF(10, -4))
                painter.drawLine(point + QPointF(14, 0), point + QPointF(10, 4))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(_BLUE)
                painter.drawEllipse(point, 4.5, 4.5)
        painter.setPen(_INK)
        painter.drawText(QRectF(frame.right() - 210, frame.top() + 6, 200, 20), Qt.AlignmentFlag.AlignRight, "● 断裂   ○→ runout")
        self.draw_interaction_overlay(painter)


class FatigueDamageChart(_ChartBase):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []

    def set_data(self, rows: list[dict[str, Any]]) -> None:
        self._rows = list(rows[:10])
        self.update()

    def clear(self) -> None:
        self.reset_view()
        self.set_data([])

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.begin_interactive_paint()
        if not self._rows:
            self._empty(painter, "计算后显示主要谱级 Miner 损伤贡献")
            return
        frame = self._frame()
        maximum = max(float(row.get("damage_per_block", 0.0)) for row in self._rows)
        total = sum(float(row.get("damage_per_block", 0.0)) for row in self._rows)
        auto_maximum = max(maximum * 1.08, 1e-12)
        samples = [
            ChartSample(
                float(row.get("damage_per_block", 0.0)),
                float(index),
                f"Sa={float(row.get('equivalent_amplitude_mpa', 0)):.4g} MPa · D={float(row.get('damage_per_block', 0)):.4g}",
            )
            for index, row in enumerate(self._rows)
        ]
        x_min, x_max, y_min, y_max = self.prepare_plot_context(
            "damage",
            frame,
            (0.0, auto_maximum),
            (-0.5, max(len(self._rows) - 0.5, 0.5)),
            samples=samples,
            x_label="单谱块损伤 D",
            y_label="谱级排序",
        )
        bar_height = frame.height() / max(y_max - y_min, 1.0) * 0.62
        painter.setFont(self.font())
        for index, row in enumerate(self._rows):
            damage = float(row.get("damage_per_block", 0.0))
            start = self.map_data("damage", max(x_min, 0.0), float(index))
            end = self.map_data("damage", damage, float(index))
            y = start.y()
            width = max(0.0, end.x() - start.x())
            painter.setBrush(_ACCENT)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(frame.left(), y - bar_height / 2, width, bar_height), 3, 3)
            share = damage / total if total > 0 else 0
            label = f"Sa={float(row.get('equivalent_amplitude_mpa', 0)):.3g} MPa  {share:.1%}"
            if width > frame.width() * 0.55:
                painter.setPen(Qt.GlobalColor.white)
                painter.drawText(
                    QRectF(frame.left() + 6, y - 10, max(width - 12, 1), 20),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    label,
                )
            else:
                painter.setPen(_INK)
                painter.drawText(
                    QRectF(
                        frame.left() + width + 8,
                        y - 10,
                        frame.width() - width - 8,
                        20,
                    ),
                    label,
                )
        painter.drawText(QRectF(frame.left(), frame.bottom() + 12, frame.width(), 22), Qt.AlignmentFlag.AlignCenter, "按单谱块损伤从高到低")
        self.draw_interaction_overlay(painter)


class FatigueReliabilityChart(_ChartBase):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, Any] = {}

    def set_data(self, data: dict[str, Any]) -> None:
        self._data = dict(data)
        self.update()

    def clear(self) -> None:
        self.reset_view()
        self.set_data({})

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.begin_interactive_paint()
        quantiles = self._data.get("life_quantiles_blocks")
        if not isinstance(quantiles, dict):
            self._empty(painter, "计算后显示存活率寿命分位点与目标可靠度")
            return
        raw_points = [
            (float(quantiles[key]), probability)
            for key, probability in (("Ps99", 0.99), ("Ps95", 0.95), ("Ps90", 0.90), ("Ps50", 0.50))
            if quantiles.get(key) not in (None, 0)
        ]
        if not raw_points:
            self._empty(painter, "可靠性分位点不可用")
            return
        frame = self._frame()
        logs = [math.log10(item[0]) for item in raw_points]
        pad = max((max(logs) - min(logs)) * 0.2, 0.2)
        auto_x = (10 ** (min(logs) - pad), 10 ** (max(logs) + pad))
        samples = [
            ChartSample(life, survival, f"Ps={survival:.0%} · 寿命={life:.5g} 谱块")
            for life, survival in raw_points
        ]
        x_min, x_max, _y_min, _y_max = self.prepare_plot_context(
            "reliability",
            frame,
            auto_x,
            (0.0, 1.0),
            samples=samples,
            x_label="寿命 [谱块]",
            y_label="存活率 Ps",
            x_log=True,
        )

        def point(life: float, survival: float) -> QPointF:
            return self.map_data("reliability", life, survival)

        self._line(painter, _GRID)
        for index in range(6):
            ratio = index / 5.0
            painter.drawLine(QPointF(frame.left(), frame.bottom() - ratio * frame.height()), QPointF(frame.right(), frame.bottom() - ratio * frame.height()))
        self._line(painter, _INK, 1.2)
        painter.drawRect(frame)
        path = QPainterPath()
        ordered = sorted(raw_points)
        for index, (life, survival) in enumerate(ordered):
            current = point(life, survival)
            path.moveTo(current) if index == 0 else path.lineTo(current)
        self._line(painter, _BLUE, 2.3)
        painter.drawPath(path)
        painter.setBrush(_BLUE)
        for life, survival in raw_points:
            current = point(life, survival)
            painter.drawEllipse(current, 4, 4)
            label_offset = {0.99: -12, 0.95: 2, 0.90: 16, 0.50: -6}.get(
                survival, -6
            )
            painter.drawText(
                current + QPointF(6, label_offset), f"Ps={survival:.0%}"
            )
        target = float(self._data.get("target_spectrum_blocks", 0.0))
        if target > 0 and x_min <= target <= x_max:
            x = point(target, 0).x()
            self._line(painter, _ACCENT, 1.6, Qt.PenStyle.DashLine)
            painter.drawLine(QPointF(x, frame.top()), QPointF(x, frame.bottom()))
            painter.drawText(QRectF(x - 60, frame.top(), 120, 20), Qt.AlignmentFlag.AlignCenter, "目标寿命")
        painter.setPen(_INK)
        painter.drawText(QRectF(frame.left(), frame.bottom() + 12, frame.width(), 22), Qt.AlignmentFlag.AlignCenter, "寿命 [谱块]（log）")
        self.draw_interaction_overlay(painter)
