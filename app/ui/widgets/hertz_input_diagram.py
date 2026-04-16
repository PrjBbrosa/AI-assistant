"""Input-condition diagram for Hertz contact module."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


class HertzInputDiagramWidget(QWidget):
    """Draw line/point contact input conditions and formula hints."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = "line"
        self._r1 = 30.0
        self._r2 = 0.0
        self._length = 20.0
        self._force = 10000.0
        self._e_eq = 115000.0
        self.setMinimumHeight(380)

    def set_context(
        self,
        mode: str,
        r1_mm: float,
        r2_mm: float,
        length_mm: float,
        normal_force_n: float,
        e_eq_mpa: float,
    ) -> None:
        self._mode = "point" if mode == "point" else "line"
        self._r1 = max(0.0, float(r1_mm))
        self._r2 = max(0.0, float(r2_mm))
        self._length = max(0.0, float(length_mm))
        self._force = max(0.0, float(normal_force_n))
        self._e_eq = max(0.0, float(e_eq_mpa))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        panel = QRectF(12, 12, w - 24, h - 24)
        painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
        painter.setBrush(QColor("#FBF8F3"))
        painter.drawRoundedRect(panel, 10, 10)

        left = QRectF(panel.left() + 10, panel.top() + 10, panel.width() * 0.54, panel.height() - 20)
        right = QRectF(left.right() + 10, panel.top() + 10, panel.right() - left.right() - 20, panel.height() - 20)

        painter.setFont(make_ui_font(14, 700))
        painter.setPen(QPen(QColor("#2E2A25"), 1.0))
        title = "线接触输入示意" if self._mode == "line" else "点接触输入示意"
        painter.drawText(QRectF(left.left(), left.top(), left.width(), 26), Qt.AlignmentFlag.AlignLeft, title)

        if self._mode == "line":
            self._draw_line_contact(painter, left)
            formula = (
                "数学表达（线接触）\n"
                "E' = 1 / [ (1-ν₁²)/E₁ + (1-ν₂²)/E₂ ]\n"
                "F' = F / L\n"
                "b = √( 4·F'·R' / (π·E') )\n"
                "p₀ = 2·F' / (π·b)\n"
                "p_mean = F' / (2·b)"
            )
        else:
            self._draw_point_contact(painter, left)
            formula = (
                "数学表达（点接触）\n"
                "E' = 1 / [ (1-ν₁²)/E₁ + (1-ν₂²)/E₂ ]\n"
                "a = ( 3·F·R' / (4·E') )^(1/3)\n"
                "p₀ = 3·F / (2·π·a²)\n"
                "p_mean = 2·F / (3·π·a²)\n"
                "A = π·a²"
            )

        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(12))
        value_text = (
            f"当前输入\n"
            f"R1 = {self._r1:.2f} mm\n"
            f"R2 = {self._r2:.2f} mm (0=平面)\n"
            f"L = {self._length:.2f} mm\n"
            f"F = {self._force:.1f} N\n"
            f"E' = {self._e_eq:.1f} MPa"
        )
        painter.drawText(
            QRectF(right.left(), right.top(), right.width(), right.height() * 0.44),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            value_text,
        )
        painter.setFont(make_ui_font(12, 600))
        painter.drawText(
            QRectF(right.left(), right.top() + right.height() * 0.42, right.width(), right.height() * 0.58),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            formula,
        )

    def _draw_line_contact(self, painter: QPainter, rect: QRectF) -> None:
        cx = rect.left() + rect.width() * 0.42
        mid_y = rect.center().y() + 8
        radius = min(rect.width(), rect.height()) * 0.14

        top_circle = QRectF(cx - radius, mid_y - 2 * radius - 8, 2 * radius, 2 * radius)
        painter.setPen(QPen(QColor("#7F7260"), 1.8))
        painter.setBrush(QColor("#E8DFD3"))
        painter.drawEllipse(top_circle)

        if self._r2 == 0:
            y_plane = mid_y + 8
            painter.setPen(QPen(QColor("#7F7260"), 2.0))
            painter.drawLine(QPointF(cx - radius * 1.8, y_plane), QPointF(cx + radius * 1.8, y_plane))
            painter.setPen(QPen(QColor("#9B8D7A"), 1.0, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(cx, y_plane - 30), QPointF(cx, y_plane + 30))
        else:
            bottom_circle = QRectF(cx - radius, mid_y + 8, 2 * radius, 2 * radius)
            painter.setPen(QPen(QColor("#7F7260"), 1.8))
            painter.setBrush(QColor("#E8DFD3"))
            painter.drawEllipse(bottom_circle)

        # Force arrow
        top = QPointF(cx, rect.top() + 24)
        contact = QPointF(cx, mid_y - 8)
        self._draw_arrow(painter, top, contact, QColor("#D97757"))
        painter.setFont(make_ui_font(13, 700))
        painter.setPen(QPen(QColor("#7F2D1A"), 1.0))
        painter.drawText(QRectF(contact.x() + 8, top.y() - 8, 64, 16), "F")

        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(11))
        painter.drawText(QRectF(cx - 96, rect.bottom() - 40, 192, 20), Qt.AlignmentFlag.AlignCenter, "接触线长度方向为 L")

    def _draw_point_contact(self, painter: QPainter, rect: QRectF) -> None:
        cx = rect.left() + rect.width() * 0.42
        cy = rect.center().y() - 4
        radius = min(rect.width(), rect.height()) * 0.16

        sphere = QRectF(cx - radius, cy - radius - 12, 2 * radius, 2 * radius)
        painter.setPen(QPen(QColor("#7F7260"), 1.8))
        painter.setBrush(QColor("#E8DFD3"))
        painter.drawEllipse(sphere)

        y_plane = cy + radius + 8
        painter.setPen(QPen(QColor("#7F7260"), 2.0))
        painter.drawLine(QPointF(cx - radius * 1.8, y_plane), QPointF(cx + radius * 1.8, y_plane))
        painter.setBrush(QColor("#D97757"))
        painter.setPen(QPen(QColor("#D97757"), 1.0))
        painter.drawEllipse(QPointF(cx, y_plane), 4.0, 2.4)

        top = QPointF(cx, rect.top() + 24)
        contact = QPointF(cx, cy - 4)
        self._draw_arrow(painter, top, contact, QColor("#D97757"))
        painter.setFont(make_ui_font(13, 700))
        painter.setPen(QPen(QColor("#7F2D1A"), 1.0))
        painter.drawText(QRectF(contact.x() + 8, top.y() - 8, 64, 16), "F")

        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(11))
        painter.drawText(QRectF(cx - 102, rect.bottom() - 40, 204, 20), Qt.AlignmentFlag.AlignCenter, "椭圆接触区在示意中简化为点")

    def _draw_arrow(self, painter: QPainter, p0: QPointF, p1: QPointF, color: QColor) -> None:
        painter.setPen(QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p0, p1)
        dx = p1.x() - p0.x()
        dy = p1.y() - p0.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            return
        ux = dx / length
        uy = dy / length
        size = 7.0
        left = QPointF(p1.x() - ux * size - uy * size * 0.6, p1.y() - uy * size + ux * size * 0.6)
        right = QPointF(p1.x() - ux * size + uy * size * 0.6, p1.y() - uy * size - ux * size * 0.6)
        painter.drawLine(p1, left)
        painter.drawLine(p1, right)
