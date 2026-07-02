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

        left = QRectF(panel.left() + 12, panel.top() + 12, panel.width() * 0.55, panel.height() - 24)
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
                "2b = 2·√( 4·F'·R' / (π·E') )\n"
                "p₀ = 2·F' / (π·b)\n"
                "A = 2b·L"
            )
        else:
            self._draw_point_contact(painter, left)
            formula = (
                "数学表达（点接触）\n"
                "E' = 1 / [ (1-ν₁²)/E₁ + (1-ν₂²)/E₂ ]\n"
                "a = ( 3·F·R' / (4·E') )^(1/3)\n"
                "p₀ = 3·F / (2·π·a²)\n"
                "A = π·a²"
            )

        length_line = f"L = {self._length:.2f} mm" if self._mode == "line" else "L = 点接触不参与计算"
        value_text = (
            f"当前输入\n"
            f"R1 = {self._r1:.2f} mm\n"
            f"R2 = {self._r2:.2f} mm (0=平面)\n"
            f"{length_line}\n"
            f"F = {self._force:.1f} N\n"
            f"E' = {self._e_eq:.1f} MPa"
        )
        self._draw_text_card(painter, QRectF(right.left(), right.top(), right.width(), right.height() * 0.42), value_text)
        self._draw_text_card(
            painter,
            QRectF(right.left(), right.top() + right.height() * 0.46, right.width(), right.height() * 0.54),
            formula,
            bold_title=True,
        )

    def _draw_line_contact(self, painter: QPainter, rect: QRectF) -> None:
        cx = rect.left() + rect.width() * 0.46
        mid_y = rect.center().y() + 10
        radius = min(rect.width(), rect.height()) * 0.16
        contact_y = mid_y + 8

        top_circle = QRectF(cx - radius, contact_y - 2 * radius, 2 * radius, 2 * radius)
        painter.setPen(QPen(QColor("#7F7260"), 1.8))
        painter.setBrush(QColor("#E8DFD3"))
        painter.drawEllipse(top_circle)

        if self._r2 == 0:
            painter.setPen(QPen(QColor("#7F7260"), 2.0))
            painter.drawLine(QPointF(cx - radius * 2.2, contact_y), QPointF(cx + radius * 2.2, contact_y))
            painter.setPen(QPen(QColor("#9B8D7A"), 1.0, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(cx, contact_y - 38), QPointF(cx, contact_y + 38))
            self._draw_badge(painter, QRectF(cx + radius * 1.35, contact_y + 10, 78, 24), "R2=平面")
        else:
            bottom_circle = QRectF(cx - radius, contact_y, 2 * radius, 2 * radius)
            painter.setPen(QPen(QColor("#7F7260"), 1.8))
            painter.setBrush(QColor("#E8DFD3"))
            painter.drawEllipse(bottom_circle)
            self._draw_badge(painter, QRectF(cx + radius * 1.35, contact_y + 18, 76, 24), "R2")

        # Contact strip and semi-width dimension.  The real contact is a
        # rectangle 2b by L; we show it as a warm strip at the interface.
        strip = QRectF(cx - radius * 0.55, contact_y - 3.2, radius * 1.10, 6.4)
        painter.setPen(QPen(QColor("#D97757"), 1.2))
        painter.setBrush(QColor(217, 119, 87, 95))
        painter.drawRoundedRect(strip, 3, 3)
        self._draw_dimension(
            painter,
            QPointF(strip.left(), contact_y + 18),
            QPointF(strip.right(), contact_y + 18),
            "2b",
            QColor("#A6472A"),
        )

        # Length direction shown as a small perspective rail below the patch.
        rail_y = rect.bottom() - 88
        painter.setPen(QPen(QColor("#58707E"), 1.5))
        painter.drawLine(QPointF(cx - 92, rail_y), QPointF(cx + 92, rail_y))
        painter.drawLine(QPointF(cx - 92, rail_y), QPointF(cx - 64, rail_y - 16))
        painter.drawLine(QPointF(cx + 92, rail_y), QPointF(cx + 120, rail_y - 16))
        painter.drawLine(QPointF(cx - 64, rail_y - 16), QPointF(cx + 120, rail_y - 16))
        self._draw_dimension(
            painter,
            QPointF(cx - 92, rail_y + 18),
            QPointF(cx + 92, rail_y + 18),
            "L 接触线长度",
            QColor("#58707E"),
        )

        # Force arrow
        top = QPointF(cx, rect.top() + 34)
        contact = QPointF(cx, top_circle.bottom() - 4)
        self._draw_arrow(painter, top, contact, QColor("#D97757"))
        painter.setFont(make_ui_font(13, 700))
        painter.setPen(QPen(QColor("#7F2D1A"), 1.0))
        painter.drawText(QRectF(contact.x() + 10, top.y() - 8, 84, 18), "F")
        self._draw_badge(painter, QRectF(cx - radius * 1.8, contact_y - radius * 1.2, 82, 24), "R1")
        self._draw_badge(painter, QRectF(rect.left() + 24, rect.top() + 42, 94, 24), "F' = F / L")

        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(11))
        painter.drawText(QRectF(cx - 120, rect.bottom() - 28, 240, 20), Qt.AlignmentFlag.AlignCenter, "线接触：压力沿长度 L 分布")

    def _draw_point_contact(self, painter: QPainter, rect: QRectF) -> None:
        cx = rect.left() + rect.width() * 0.46
        cy = rect.center().y() - 2
        radius = min(rect.width(), rect.height()) * 0.18

        sphere = QRectF(cx - radius, cy - radius - 12, 2 * radius, 2 * radius)
        painter.setPen(QPen(QColor("#7F7260"), 1.8))
        painter.setBrush(QColor("#E8DFD3"))
        painter.drawEllipse(sphere)

        y_plane = cy + radius + 8
        if self._r2 == 0:
            painter.setPen(QPen(QColor("#7F7260"), 2.0))
            painter.drawLine(QPointF(cx - radius * 2.1, y_plane), QPointF(cx + radius * 2.1, y_plane))
            self._draw_badge(painter, QRectF(cx + radius * 1.35, y_plane + 10, 78, 24), "R2=平面")
        else:
            bottom = QRectF(cx - radius * 0.92, y_plane - 4, radius * 1.84, radius * 1.84)
            painter.setPen(QPen(QColor("#7F7260"), 1.8))
            painter.setBrush(QColor("#E8DFD3"))
            painter.drawEllipse(bottom)
            self._draw_badge(painter, QRectF(cx + radius * 1.35, y_plane + 12, 76, 24), "R2")

        painter.setBrush(QColor("#D97757"))
        painter.setPen(QPen(QColor("#D97757"), 1.0))
        patch = QRectF(cx - 18, y_plane - 5, 36, 10)
        painter.drawEllipse(patch)
        self._draw_dimension(
            painter,
            QPointF(cx, y_plane),
            QPointF(cx + 34, y_plane),
            "a",
            QColor("#A6472A"),
        )

        top = QPointF(cx, rect.top() + 34)
        contact = QPointF(cx, cy - 4)
        self._draw_arrow(painter, top, contact, QColor("#D97757"))
        painter.setFont(make_ui_font(13, 700))
        painter.setPen(QPen(QColor("#7F2D1A"), 1.0))
        painter.drawText(QRectF(contact.x() + 10, top.y() - 8, 84, 18), "F")
        self._draw_badge(painter, QRectF(cx - radius * 1.9, cy - radius * 0.9, 78, 24), "R1")
        self._draw_badge(painter, QRectF(rect.left() + 24, rect.top() + 42, 110, 24), "A = pi·a²")

        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(11))
        painter.drawText(QRectF(cx - 126, rect.bottom() - 32, 252, 20), Qt.AlignmentFlag.AlignCenter, "点接触：示意中放大显示接触斑")

    def _draw_text_card(self, painter: QPainter, rect: QRectF, text: str, bold_title: bool = False) -> None:
        painter.setPen(QPen(QColor("#E4DDD2"), 1.0))
        painter.setBrush(QColor("#FBF8F3"))
        painter.drawRoundedRect(rect, 8, 8)
        lines = text.splitlines()
        if not lines:
            return
        title_rect = QRectF(rect.left() + 12, rect.top() + 10, rect.width() - 24, 20)
        painter.setPen(QPen(QColor("#2E2A25"), 1.0))
        painter.setFont(make_ui_font(11, 700 if bold_title else 600))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft, lines[0])
        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(10))
        painter.drawText(
            rect.adjusted(12, 34, -12, -10),
            int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            "\n".join(lines[1:]),
        )

    def _draw_badge(self, painter: QPainter, rect: QRectF, text: str) -> None:
        painter.setPen(QPen(QColor("#CDBFAA"), 1.0))
        painter.setBrush(QColor(251, 248, 243, 235))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QPen(QColor("#5C574F"), 1.0))
        painter.setFont(make_ui_font(9, 600))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_dimension(self, painter: QPainter, p0: QPointF, p1: QPointF, label: str, color: QColor) -> None:
        painter.setPen(QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p0, p1)
        if abs(p1.x() - p0.x()) >= abs(p1.y() - p0.y()):
            painter.drawLine(QPointF(p0.x(), p0.y() - 5), QPointF(p0.x(), p0.y() + 5))
            painter.drawLine(QPointF(p1.x(), p1.y() - 5), QPointF(p1.x(), p1.y() + 5))
            rect = QRectF((p0.x() + p1.x()) * 0.5 - 58, p0.y() + 4, 116, 18)
        else:
            painter.drawLine(QPointF(p0.x() - 5, p0.y()), QPointF(p0.x() + 5, p0.y()))
            painter.drawLine(QPointF(p1.x() - 5, p1.y()), QPointF(p1.x() + 5, p1.y()))
            rect = QRectF(p0.x() + 8, (p0.y() + p1.y()) * 0.5 - 9, 94, 18)
        painter.setPen(QPen(color, 1.0))
        painter.setFont(make_ui_font(9, 600))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

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
