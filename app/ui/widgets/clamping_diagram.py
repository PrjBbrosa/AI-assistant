"""Simple clamping force schematic for bolt joint."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ClampingDiagramWidget(QWidget):
    """Draw a lightweight bolt clamping schematic with key force labels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fm = 0.0
        self._fa = 0.0
        self._fk = 0.0
        self.setMinimumHeight(260)

    def set_forces(self, fm: float, fa: float, fk: float) -> None:
        self._fm = max(0.0, fm)
        self._fa = max(0.0, fa)
        self._fk = max(0.0, fk)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        margin = 20.0

        # Background panel
        panel = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
        painter.setBrush(QColor("#F6F1EA"))
        painter.drawRoundedRect(panel, 12, 12)

        cx = panel.left() + panel.width() * 0.33
        top = panel.top() + 34
        bottom = panel.bottom() - 34
        mid = (top + bottom) / 2.0

        # Clamped parts
        part_w = panel.width() * 0.48
        part_h = 36.0
        part_x = cx - part_w / 2.0
        upper_part = QRectF(part_x, mid - 54, part_w, part_h)
        lower_part = QRectF(part_x, mid + 18, part_w, part_h)
        painter.setBrush(QColor("#E8DFD3"))
        painter.setPen(QPen(QColor("#BCAF9E"), 1.0))
        painter.drawRoundedRect(upper_part, 8, 8)
        painter.drawRoundedRect(lower_part, 8, 8)

        # Bolt shank
        painter.setPen(QPen(QColor("#8A7E6F"), 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(cx, top + 12), QPointF(cx, bottom - 12))

        # Head and nut
        painter.setPen(QPen(QColor("#7B6D5E"), 1.0))
        painter.setBrush(QColor("#D8CCBD"))
        painter.drawRoundedRect(QRectF(cx - 36, top - 2, 72, 18), 6, 6)
        painter.drawRoundedRect(QRectF(cx - 36, bottom - 16, 72, 18), 6, 6)

        # Force arrows
        arrow_pen = QPen(QColor("#D97757"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(arrow_pen)
        self._draw_arrow(painter, QPointF(cx + 76, mid - 10), QPointF(cx + 76, top + 6))
        self._draw_arrow(painter, QPointF(cx + 76, mid + 10), QPointF(cx + 76, bottom - 6))

        ext_pen = QPen(QColor("#4C627A"), 2.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(ext_pen)
        self._draw_arrow(painter, QPointF(cx - 84, top + 10), QPointF(cx - 84, top - 20))
        self._draw_arrow(painter, QPointF(cx - 84, bottom - 10), QPointF(cx - 84, bottom + 20))

        # Text
        painter.setPen(QPen(QColor("#1F1D1A"), 1.0))
        painter.setFont(QFont("Avenir Next", 10, 600))
        painter.drawText(QRectF(cx + 88, mid - 26, 170, 26), "FM (预紧力)")
        painter.drawText(QRectF(cx - 170, top - 40, 145, 24), "FA (外载)")
        painter.drawText(QRectF(cx + 88, mid + 2, 170, 26), "FK (残余夹紧力)")

        painter.setFont(QFont("Avenir Next", 9))
        painter.setPen(QPen(QColor("#6B665E"), 1.0))
        painter.drawText(
            QRectF(panel.left() + panel.width() * 0.57, panel.top() + 48, panel.width() * 0.36, 140),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            f"FM = {self._fm:,.0f} N\nFA = {self._fa:,.0f} N\nFK = {self._fk:,.0f} N",
        )

    def _draw_arrow(self, painter: QPainter, p0: QPointF, p1: QPointF) -> None:
        painter.drawLine(p0, p1)
        dx = p1.x() - p0.x()
        dy = p1.y() - p0.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            return
        ux = dx / length
        uy = dy / length

        # Arrow head
        size = 7.5
        left = QPointF(
            p1.x() - ux * size - uy * size * 0.65,
            p1.y() - uy * size + ux * size * 0.65,
        )
        right = QPointF(
            p1.x() - ux * size + uy * size * 0.65,
            p1.y() - uy * size - ux * size * 0.65,
        )
        painter.drawLine(p1, left)
        painter.drawLine(p1, right)

