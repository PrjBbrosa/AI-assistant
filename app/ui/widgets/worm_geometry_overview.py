"""Engineering diagram widget for worm-gear geometry overview."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.design_tokens import qcolor, qpen
from app.ui.fonts import make_ui_font


DEFAULT_GEOM_STATE: dict = {
    "d1_mm": 40.0,
    "d2_mm": 160.0,
    "a_mm": 100.0,
    "gamma_deg": 11.31,
    "z1": 2,
    "z2": 40,
    "handedness": "right",
}


def _token(name: str, alpha: int | float | None = None) -> QColor:
    color = qcolor(name)
    if isinstance(alpha, float):
        color.setAlphaF(alpha)
    elif isinstance(alpha, int):
        color.setAlpha(alpha)
    return color


class WormGeometryOverviewWidget(QWidget):
    """Render a worm-pair diagram aligned with the DIN geometry calculation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = "几何总览"
        self._note = "按 DIN 3975 展示蜗杆螺旋、蜗轮副、中心距与导程角关系。"
        self._geom_state: dict = DEFAULT_GEOM_STATE.copy()
        self.setMinimumHeight(340)

    def set_display_state(self, title: str, note: str) -> None:
        self._title = title.strip() or "几何总览"
        self._note = note.strip() or "按 DIN 3975 展示蜗杆螺旋、蜗轮副、中心距与导程角关系。"
        self.update()

    def reset_geometry_state(self) -> None:
        self._geom_state = DEFAULT_GEOM_STATE.copy()
        self.update()

    def set_geometry_state(
        self,
        *,
        d1_mm: float,
        d2_mm: float,
        a_mm: float,
        gamma_deg: float,
        z1: int,
        z2: int,
        handedness: str,
    ) -> None:
        self._geom_state = {
            "d1_mm": max(float(d1_mm), 1.0),
            "d2_mm": max(float(d2_mm), 1.0),
            "a_mm": max(float(a_mm), 1.0),
            "gamma_deg": float(gamma_deg),
            "z1": int(z1),
            "z2": int(z2),
            "handedness": str(handedness).strip().lower() or "right",
        }
        self.update()

    def geometry_state(self) -> dict:
        """Stored geometry parameters consumed by paintEvent (no derived safety)."""
        return dict(self._geom_state)

    def _panel_rect(self) -> QRectF:
        return QRectF(14.0, 14.0, self.width() - 28.0, self.height() - 28.0)

    def _diagram_rect_for_testing(self) -> QRectF:
        panel = self._panel_rect()
        return QRectF(panel.left() + 22, panel.top() + 44, panel.width() * 0.67, panel.height() - 66)

    def _compute_geometry_layout(self, diagram: QRectF) -> dict:
        d1_mm = self._geom_state["d1_mm"]
        d2_mm = self._geom_state["d2_mm"]
        a_mm = self._geom_state["a_mm"]

        vertical_need = a_mm + d2_mm * 0.5 + d1_mm * 0.5 + 28.0
        horizontal_need = max(d2_mm + 96.0, d1_mm * 3.0 + 120.0)
        scale = min(
            (diagram.width() - 70.0) / max(horizontal_need, 1.0),
            (diagram.height() - 50.0) / max(vertical_need, 1.0),
            2.2,
        )
        scale = max(scale, 0.35)

        d1_px = d1_mm * scale
        d2_px = d2_mm * scale
        a_px = a_mm * scale
        worm_w = max(d1_px * 3.2, 130.0)

        center_x = diagram.left() + diagram.width() * 0.43
        worm_axis_y = diagram.bottom() - max(44.0, d1_px * 0.5 + 34.0)
        wheel_center_y = worm_axis_y - a_px
        min_wheel_center_y = diagram.top() + d2_px * 0.5 + 18.0
        if wheel_center_y < min_wheel_center_y:
            shift = min_wheel_center_y - wheel_center_y
            worm_axis_y += shift
            wheel_center_y += shift

        worm_rect = QRectF(center_x - worm_w * 0.5, worm_axis_y - d1_px * 0.5, worm_w, d1_px)
        wheel_rect = QRectF(center_x - d2_px * 0.5, wheel_center_y - d2_px * 0.5, d2_px, d2_px)

        dim_x = min(wheel_rect.left() - 26.0, worm_rect.left() - 18.0)
        center_distance = {
            "p0": QPointF(dim_x, wheel_center_y),
            "p1": QPointF(dim_x, worm_axis_y),
            "label": QRectF(dim_x - 72.0, (wheel_center_y + worm_axis_y) * 0.5 - 10.0, 64.0, 20.0),
        }

        return {
            "scale": scale,
            "d1_px": d1_px,
            "d2_px": d2_px,
            "a_px": a_px,
            "center_x": center_x,
            "worm_axis_y": worm_axis_y,
            "wheel_center": QPointF(center_x, wheel_center_y),
            "worm_rect": worm_rect,
            "wheel_rect": wheel_rect,
            "center_distance": center_distance,
        }

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter()
        if not painter.begin(self):
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            panel = self._panel_rect()
            painter.setPen(qpen("line_structural", 1.0))
            painter.setBrush(_token("surface_glass_soft"))
            painter.drawRoundedRect(panel, 12, 12)

            painter.setPen(qpen("ink_primary", 1.0))
            painter.setFont(make_ui_font(12, 600))
            painter.drawText(
                QRectF(panel.left() + 18, panel.top() + 12, panel.width() - 36, 20),
                Qt.AlignmentFlag.AlignLeft,
                self._title,
            )

            diagram = self._diagram_rect_for_testing()
            info = QRectF(diagram.right() + 16, diagram.top(), panel.right() - diagram.right() - 24, diagram.height())

            painter.setPen(qpen("line_structural", 1.0))
            painter.setBrush(_token("surface_glass_soft"))
            painter.drawRoundedRect(diagram, 10, 10)
            painter.drawRoundedRect(info, 10, 10)

            layout = self._compute_geometry_layout(diagram)
            self._draw_pair(painter, diagram, layout)
            self._draw_info_panel(painter, info)
        finally:
            painter.end()

    def _draw_pair(self, painter: QPainter, diagram: QRectF, layout: dict) -> None:
        d1_mm = self._geom_state["d1_mm"]
        d2_mm = self._geom_state["d2_mm"]
        a_mm = self._geom_state["a_mm"]
        gamma_deg = self._geom_state["gamma_deg"]
        handedness = self._geom_state["handedness"]

        worm_rect: QRectF = layout["worm_rect"]
        wheel_rect: QRectF = layout["wheel_rect"]
        wheel_center: QPointF = layout["wheel_center"]
        worm_axis_y = layout["worm_axis_y"]
        center_distance = layout["center_distance"]

        # Axes first, behind the shapes.
        painter.setPen(QPen(_token("ink_quiet"), 1.1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(worm_rect.left() - 36, worm_axis_y), QPointF(worm_rect.right() + 36, worm_axis_y))
        painter.drawLine(QPointF(wheel_center.x(), wheel_rect.top() - 18), QPointF(wheel_center.x(), worm_rect.bottom() + 28))

        # Wheel body with subtle tooth ticks.
        painter.setPen(qpen("ink_muted", 2.0))
        painter.setBrush(_token("secondary_soft"))
        painter.drawEllipse(wheel_rect)
        bore = wheel_rect.adjusted(wheel_rect.width() * 0.32, wheel_rect.height() * 0.32, -wheel_rect.width() * 0.32, -wheel_rect.height() * 0.32)
        painter.setBrush(_token("surface_glass_soft"))
        painter.drawEllipse(bore)

        outer_radius = wheel_rect.width() * 0.5
        inner_radius = bore.width() * 0.5 + 7.0
        painter.setPen(qpen("secondary", 1.2))
        for idx in range(24):
            angle = math.radians(idx * 15.0)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            painter.drawLine(
                QPointF(wheel_center.x() + inner_radius * cos_a, wheel_center.y() + inner_radius * sin_a),
                QPointF(wheel_center.x() + outer_radius * cos_a, wheel_center.y() + outer_radius * sin_a),
            )

        # Worm body and helix.
        painter.setPen(qpen("ink_muted", 2.0))
        painter.setBrush(_token("surface_glass"))
        painter.drawRoundedRect(worm_rect, min(worm_rect.height() * 0.45, 18), min(worm_rect.height() * 0.45, 18))

        hand_sign = 1.0 if handedness == "right" else -1.0
        painter.setPen(QPen(_token("accent"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        line_count = max(5, min(11, int(worm_rect.width() / 18)))
        for idx in range(line_count):
            x0 = worm_rect.left() + 12 + idx * (worm_rect.width() - 24) / max(line_count - 1, 1)
            painter.drawLine(
                QPointF(x0, worm_rect.top() + 6),
                QPointF(x0 + hand_sign * worm_rect.width() * 0.14, worm_rect.bottom() - 6),
            )

        # Mesh patch: placed between wheel pitch circle and worm crown.
        mesh = QPointF(wheel_center.x(), (wheel_rect.bottom() + worm_rect.top()) * 0.5)
        painter.setPen(qpen("accent", 1.8))
        painter.setBrush(_token("accent", 48))
        painter.drawEllipse(mesh, 15.0, 9.0)
        self._draw_badge(painter, QRectF(mesh.x() - 78, mesh.y() - 34, 56, 22), "啮合区")

        # Vertical center distance: this is the important corrected logic.
        self._draw_dimension(
            painter,
            center_distance["p0"],
            center_distance["p1"],
            f"a={a_mm:.1f}mm",
            _token("secondary"),
            label_rect=center_distance["label"],
        )

        # d1 and d2 dimensions live outside shapes to avoid text overlap.
        d1_x = worm_rect.left() - 18.0
        self._draw_dimension(
            painter,
            QPointF(d1_x, worm_rect.top()),
            QPointF(d1_x, worm_rect.bottom()),
            f"d1={d1_mm:.0f}",
            _token("secondary"),
        )
        d2_x = wheel_rect.right() + 20.0
        self._draw_dimension(
            painter,
            QPointF(d2_x, wheel_rect.top()),
            QPointF(d2_x, wheel_rect.bottom()),
            f"d2={d2_mm:.0f}",
            _token("secondary"),
        )

        # Lead angle guide near the worm, offset from the mesh label.
        gamma_center = QPointF(worm_rect.right() - 34, worm_rect.top() - 8)
        painter.setPen(qpen("accent_ink", 1.4))
        painter.drawLine(gamma_center, QPointF(gamma_center.x() + 56, gamma_center.y()))
        slope = 56.0 * math.tan(math.radians(max(0.0, min(abs(gamma_deg), 38.0))))
        painter.drawLine(gamma_center, QPointF(gamma_center.x() + 56, gamma_center.y() + slope))
        painter.drawArc(QRectF(gamma_center.x() - 20, gamma_center.y() - 20, 40, 40), 0, 42 * 16)
        self._draw_badge(painter, QRectF(gamma_center.x() + 62, gamma_center.y() - 12, 96, 22), f"gamma={gamma_deg:.1f}deg")

        direction = "右旋" if handedness == "right" else "左旋"
        arrow_y = min(diagram.bottom() - 20, worm_rect.bottom() + 22)
        painter.setPen(QPen(_token("accent_ink"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        x_start = worm_rect.left() + 16
        x_end = worm_rect.right() - 16
        if handedness != "right":
            x_start, x_end = x_end, x_start
        painter.drawLine(QPointF(x_start, arrow_y), QPointF(x_end, arrow_y))
        self._draw_arrow_head(painter, QPointF(x_end, arrow_y), 1.0 if handedness == "right" else -1.0)
        painter.setFont(make_ui_font(9))
        painter.setPen(qpen("accent_ink", 1.0))
        painter.drawText(QRectF(worm_rect.left() + 10, arrow_y + 4, 112, 18), Qt.AlignmentFlag.AlignLeft, f"{direction}蜗杆")

    def _draw_info_panel(self, painter: QPainter, info: QRectF) -> None:
        z1 = self._geom_state["z1"]
        z2 = self._geom_state["z2"]
        d1_mm = self._geom_state["d1_mm"]
        d2_mm = self._geom_state["d2_mm"]
        a_mm = self._geom_state["a_mm"]
        gamma_deg = self._geom_state["gamma_deg"]
        handedness = self._geom_state["handedness"]

        painter.setPen(qpen("ink_muted", 1.0))
        painter.setFont(make_ui_font(9))
        painter.drawText(
            info.adjusted(14, 14, -14, -14),
            int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            "蜗杆副要点\n\n"
            f"- z1={z1}  z2={z2}\n"
            f"- d1={d1_mm:.1f} mm\n"
            f"- d2={d2_mm:.1f} mm\n"
            f"- a={a_mm:.1f} mm\n"
            f"- gamma={gamma_deg:.2f} deg\n"
            f"- {'右旋' if handedness == 'right' else '左旋'}\n\n"
            f"说明\n{self._note}",
        )

    def _draw_dimension(
        self,
        painter: QPainter,
        p0: QPointF,
        p1: QPointF,
        label: str,
        color: QColor,
        *,
        label_rect: QRectF | None = None,
    ) -> None:
        painter.setPen(QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p0, p1)
        if abs(p1.x() - p0.x()) < abs(p1.y() - p0.y()):
            painter.drawLine(QPointF(p0.x() - 6, p0.y()), QPointF(p0.x() + 6, p0.y()))
            painter.drawLine(QPointF(p1.x() - 6, p1.y()), QPointF(p1.x() + 6, p1.y()))
            default_rect = QRectF(p0.x() + 8, (p0.y() + p1.y()) * 0.5 - 10, 74, 20)
        else:
            painter.drawLine(QPointF(p0.x(), p0.y() - 6), QPointF(p0.x(), p0.y() + 6))
            painter.drawLine(QPointF(p1.x(), p1.y() - 6), QPointF(p1.x(), p1.y() + 6))
            default_rect = QRectF((p0.x() + p1.x()) * 0.5 - 44, p0.y() - 24, 88, 20)
        rect = label_rect or default_rect
        painter.setPen(QPen(color, 1.0))
        painter.setFont(make_ui_font(9, 600))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_badge(self, painter: QPainter, rect: QRectF, text: str) -> None:
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(_token("surface_glass_strong", 235))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(qpen("ink_muted", 1.0))
        painter.setFont(make_ui_font(8, 600))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_arrow_head(self, painter: QPainter, point: QPointF, x_direction: float) -> None:
        size = 7.0
        painter.drawLine(point, QPointF(point.x() - x_direction * size, point.y() - size * 0.7))
        painter.drawLine(point, QPointF(point.x() - x_direction * size, point.y() + size * 0.7))
