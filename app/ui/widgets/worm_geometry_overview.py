"""Engineering placeholder for worm-gear geometry overview."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


class WormGeometryOverviewWidget(QWidget):
    """Render a dense engineering-style placeholder for worm geometry."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = "几何总览"
        self._note = "按 DIN 3975 展示蜗杆螺旋、蜗轮副、中心距与导程角关系。"
        self.setMinimumHeight(340)

    def set_display_state(self, title: str, note: str) -> None:
        self._title = title.strip() or "几何总览"
        self._note = note.strip() or "按 DIN 3975 展示蜗杆螺旋、蜗轮副、中心距与导程角关系。"
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
            painter.drawRoundedRect(panel, 12, 12)

            painter.setPen(QPen(QColor("#2B2723"), 1.0))
            painter.setFont(make_ui_font(12, 600))
            painter.drawText(QRectF(panel.left() + 18, panel.top() + 12, panel.width() - 36, 20), Qt.AlignmentFlag.AlignLeft, self._title)

            diagram = QRectF(panel.left() + 22, panel.top() + 44, panel.width() * 0.67, panel.height() - 66)
            info = QRectF(diagram.right() + 16, diagram.top(), panel.right() - diagram.right() - 24, diagram.height())

            painter.setPen(QPen(QColor("#E4DDD2"), 1.0))
            painter.drawRoundedRect(diagram, 10, 10)
            painter.drawRoundedRect(info, 10, 10)

            axis_y = diagram.center().y() + 24
            worm_rect = QRectF(diagram.left() + 36, axis_y - 38, diagram.width() * 0.36, 76)
            wheel_diameter = min(diagram.height() * 0.72, diagram.width() * 0.28)
            wheel_rect = QRectF(diagram.left() + diagram.width() * 0.62, axis_y - wheel_diameter * 0.5 - 58, wheel_diameter, wheel_diameter)
            wheel_center = wheel_rect.center()

            painter.setPen(QPen(QColor("#8B7C67"), 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(worm_rect.left() - 26, worm_rect.center().y()), QPointF(wheel_rect.right() + 26, worm_rect.center().y()))
            painter.drawLine(QPointF(wheel_center.x(), wheel_rect.top() - 20), QPointF(wheel_center.x(), wheel_rect.bottom() + 28))

            painter.setPen(QPen(QColor("#7F7260"), 2.2))
            painter.setBrush(QColor("#E6DCCE"))
            painter.drawRoundedRect(worm_rect, 28, 28)
            painter.setBrush(QColor("#E3D3C0"))
            painter.drawEllipse(wheel_rect)
            bore_rect = wheel_rect.adjusted(wheel_rect.width() * 0.26, wheel_rect.height() * 0.26, -wheel_rect.width() * 0.26, -wheel_rect.height() * 0.26)
            painter.setBrush(QColor("#FBF8F3"))
            painter.drawEllipse(bore_rect)

            painter.setPen(QPen(QColor("#B65E2C"), 2.1))
            for idx in range(7):
                x0 = worm_rect.left() + 8 + idx * worm_rect.width() / 7.0
                painter.drawLine(
                    QPointF(x0, worm_rect.top() + 7),
                    QPointF(x0 + worm_rect.width() * 0.15, worm_rect.bottom() - 7),
                )

            painter.setPen(QPen(QColor("#8D6E63"), 1.4))
            outer_radius = wheel_rect.width() * 0.5
            inner_radius = bore_rect.width() * 0.5 + 8.0
            for idx in range(18):
                angle = math.radians(idx * 20.0)
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                painter.drawLine(
                    QPointF(wheel_center.x() + inner_radius * cos_a, wheel_center.y() + inner_radius * sin_a),
                    QPointF(wheel_center.x() + outer_radius * cos_a, wheel_center.y() + outer_radius * sin_a),
                )

            mesh_spot = QPointF(wheel_rect.left() + 16, worm_rect.center().y() - 6)
            painter.setPen(QPen(QColor("#C55A11"), 2.0))
            painter.setBrush(QColor(197, 90, 17, 45))
            painter.drawEllipse(mesh_spot, 14.0, 14.0)
            painter.drawText(QRectF(mesh_spot.x() - 12, mesh_spot.y() - 34, 72, 16), Qt.AlignmentFlag.AlignLeft, "啮合区")

            a_y = worm_rect.center().y() - 82
            x_left = worm_rect.center().x()
            x_right = wheel_center.x()
            painter.setPen(QPen(QColor("#35637A"), 1.6))
            painter.drawLine(QPointF(x_left, a_y), QPointF(x_right, a_y))
            painter.drawLine(QPointF(x_left, a_y - 8), QPointF(x_left, a_y + 8))
            painter.drawLine(QPointF(x_right, a_y - 8), QPointF(x_right, a_y + 8))
            painter.setFont(make_ui_font(9, 500))
            painter.drawText(QRectF((x_left + x_right) * 0.5 - 42, a_y - 22, 84, 16), Qt.AlignmentFlag.AlignCenter, "中心距 a")

            d1_x = worm_rect.left() + worm_rect.width() * 0.18
            painter.setPen(QPen(QColor("#58707E"), 1.3))
            painter.drawLine(QPointF(d1_x, worm_rect.top() - 12), QPointF(d1_x, worm_rect.bottom() + 12))
            painter.drawLine(QPointF(d1_x - 8, worm_rect.top()), QPointF(d1_x + 8, worm_rect.top()))
            painter.drawLine(QPointF(d1_x - 8, worm_rect.bottom()), QPointF(d1_x + 8, worm_rect.bottom()))
            painter.drawText(QRectF(d1_x - 18, worm_rect.top() - 30, 40, 16), Qt.AlignmentFlag.AlignCenter, "d1")

            d2_x = wheel_rect.right() + 18
            painter.drawLine(QPointF(d2_x, wheel_rect.top()), QPointF(d2_x, wheel_rect.bottom()))
            painter.drawLine(QPointF(d2_x - 8, wheel_rect.top()), QPointF(d2_x + 8, wheel_rect.top()))
            painter.drawLine(QPointF(d2_x - 8, wheel_rect.bottom()), QPointF(d2_x + 8, wheel_rect.bottom()))
            painter.drawText(QRectF(d2_x - 18, wheel_rect.top() - 22, 40, 16), Qt.AlignmentFlag.AlignCenter, "d2")

            painter.setPen(QPen(QColor("#A6472A"), 1.5))
            gamma_center = QPointF(worm_rect.right() - 28, worm_rect.center().y())
            painter.drawArc(QRectF(gamma_center.x() - 28, gamma_center.y() - 28, 56, 56), 0, 56 * 16)
            painter.drawText(QRectF(gamma_center.x() + 10, gamma_center.y() - 32, 54, 16), Qt.AlignmentFlag.AlignLeft, "gamma")

            painter.setPen(QPen(QColor("#7A3E2B"), 1.5))
            painter.drawLine(QPointF(worm_rect.left() + 16, worm_rect.bottom() + 20), QPointF(worm_rect.right() - 10, worm_rect.bottom() + 20))
            painter.drawLine(QPointF(worm_rect.right() - 10, worm_rect.bottom() + 20), QPointF(worm_rect.right() - 18, worm_rect.bottom() + 12))
            painter.drawLine(QPointF(worm_rect.right() - 10, worm_rect.bottom() + 20), QPointF(worm_rect.right() - 18, worm_rect.bottom() + 28))
            painter.drawText(QRectF(worm_rect.left() + 14, worm_rect.bottom() + 24, 88, 16), Qt.AlignmentFlag.AlignLeft, "右旋示意")

            painter.setPen(QPen(QColor("#5F584F"), 1.0))
            painter.setFont(make_ui_font(9))
            painter.drawText(
                info.adjusted(14, 14, -14, -14),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                "蜗杆副要点\n\n"
                "- 蜗杆分度圆 d1 与直径系数 q\n"
                "- 蜗轮分度圆 d2 与传动比 i\n"
                "- 蜗杆螺旋方向与导程角 gamma\n"
                "- 啮合区、中心距 a、旋向标识\n\n"
                f"说明\n{self._note}",
            )
        finally:
            painter.end()
