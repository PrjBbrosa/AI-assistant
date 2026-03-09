"""Engineering placeholder for worm backlash and tolerance overview."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class WormToleranceOverviewWidget(QWidget):
    """Render a dense engineering-style placeholder for backlash/tolerance concepts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = "公差与回差"
        self._note = "展示蜗杆齿面、蜗轮齿槽、公差带、中心距偏差与回差概念。"
        self.setMinimumHeight(340)

    def set_display_state(self, title: str, note: str) -> None:
        self._title = title.strip() or "公差与回差"
        self._note = note.strip() or "展示蜗杆齿面、蜗轮齿槽、公差带、中心距偏差与回差概念。"
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
            painter.setFont(QFont("Avenir Next", 12, 600))
            painter.drawText(QRectF(panel.left() + 18, panel.top() + 12, panel.width() - 36, 20), Qt.AlignmentFlag.AlignLeft, self._title)

            left = QRectF(panel.left() + 22, panel.top() + 44, panel.width() * 0.6, panel.height() - 66)
            right = QRectF(left.right() + 16, left.top(), panel.right() - left.right() - 24, left.height())
            painter.setPen(QPen(QColor("#E4DDD2"), 1.0))
            painter.drawRoundedRect(left, 10, 10)
            painter.drawRoundedRect(right, 10, 10)

            worm_block = QRectF(left.left() + 34, left.center().y() - 42, left.width() * 0.3, 84)
            wheel_tooth = QRectF(left.left() + left.width() * 0.56, left.center().y() - 74, left.width() * 0.18, 148)
            painter.setPen(QPen(QColor("#7F7260"), 2.0))
            painter.setBrush(QColor("#E7DCCD"))
            painter.drawRoundedRect(worm_block, 26, 26)
            painter.setBrush(QColor("#E2D2BD"))
            painter.drawRoundedRect(wheel_tooth, 12, 12)

            painter.setPen(QPen(QColor("#B65E2C"), 2.0))
            for idx in range(6):
                x0 = worm_block.left() + 10 + idx * worm_block.width() / 6.0
                painter.drawLine(QPointF(x0, worm_block.top() + 8), QPointF(x0 + 18, worm_block.bottom() - 8))

            tooth_gap_left = wheel_tooth.left() - 24
            tooth_gap_right = wheel_tooth.left() - 4
            painter.setPen(QPen(QColor("#2F855A"), 1.7, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(tooth_gap_left, worm_block.top() - 20), QPointF(tooth_gap_left, worm_block.bottom() + 20))
            painter.drawLine(QPointF(tooth_gap_right, worm_block.top() - 20), QPointF(tooth_gap_right, worm_block.bottom() + 20))
            painter.drawText(QRectF(tooth_gap_left - 18, worm_block.top() - 40, 84, 16), Qt.AlignmentFlag.AlignCenter, "回差 jn")

            band_left = wheel_tooth.right() + 28
            band_rect = QRectF(band_left, wheel_tooth.top() + 18, 42, wheel_tooth.height() - 36)
            painter.setPen(QPen(QColor("#B65E2C"), 1.5))
            painter.setBrush(QColor(198, 90, 17, 36))
            painter.drawRect(band_rect)
            painter.drawText(QRectF(band_left - 20, wheel_tooth.top() - 8, 96, 16), Qt.AlignmentFlag.AlignCenter, "齿厚公差带")

            center_y = left.top() + 52
            center_x0 = worm_block.center().x()
            center_x1 = wheel_tooth.center().x()
            painter.setPen(QPen(QColor("#35637A"), 1.5))
            painter.drawLine(QPointF(center_x0, center_y), QPointF(center_x1, center_y))
            painter.drawLine(QPointF(center_x0, center_y - 6), QPointF(center_x0, center_y + 6))
            painter.drawLine(QPointF(center_x1, center_y - 6), QPointF(center_x1, center_y + 6))
            painter.drawText(QRectF((center_x0 + center_x1) * 0.5 - 52, center_y - 24, 104, 16), Qt.AlignmentFlag.AlignCenter, "中心距偏差 Δa")

            painter.setPen(QPen(QColor("#917860"), 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(worm_block.left() - 18, worm_block.center().y()), QPointF(wheel_tooth.right() + 92, worm_block.center().y()))
            painter.drawText(QRectF(worm_block.left() - 8, worm_block.bottom() + 18, 90, 16), Qt.AlignmentFlag.AlignLeft, "蜗杆齿面")
            painter.drawText(QRectF(wheel_tooth.left() - 6, wheel_tooth.bottom() + 18, 90, 16), Qt.AlignmentFlag.AlignLeft, "蜗轮齿槽")

            painter.setPen(QPen(QColor("#5F584F"), 1.0))
            painter.setFont(QFont("Avenir Next", 9))
            painter.drawText(
                right.adjusted(14, 14, -14, -14),
                int(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
                "蜗杆副公差要点\n\n"
                "- 蜗杆齿面与蜗轮齿槽之间的法向回差\n"
                "- 齿厚公差带与制造偏差\n"
                "- 中心距偏差对侧隙和啮合的影响\n"
                "- 装配余量与热膨胀补偿\n\n"
                f"备注\n{self._note}",
            )
        finally:
            painter.end()
