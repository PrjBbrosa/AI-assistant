"""Engineering diagram widget for worm-gear geometry overview."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.ui.fonts import make_ui_font


class WormGeometryOverviewWidget(QWidget):
    """Render a dynamic engineering-style overview for worm geometry.

    After ``set_geometry_state`` is called the diagram scales d1, d2 and the
    centre distance proportionally.  The helix-line slope reflects the
    handedness (right-hand: lines slope down-right; left-hand: down-left).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = "几何总览"
        self._note = "按 DIN 3975 展示蜗杆螺旋、蜗轮副、中心距与导程角关系。"
        # 默认几何状态（m=4, z1=2, z2=40, q=10）
        self._geom_state: dict = {
            "d1_mm": 40.0,
            "d2_mm": 160.0,
            "a_mm": 100.0,
            "gamma_deg": 11.31,
            "z1": 2,
            "z2": 40,
            "handedness": "right",
        }
        self.setMinimumHeight(340)

    def set_display_state(self, title: str, note: str) -> None:
        self._title = title.strip() or "几何总览"
        self._note = note.strip() or "按 DIN 3975 展示蜗杆螺旋、蜗轮副、中心距与导程角关系。"
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
        """Update the geometry state and trigger a repaint.

        Parameters
        ----------
        d1_mm:      蜗杆分度圆直径 (mm)
        d2_mm:      蜗轮分度圆直径 (mm)
        a_mm:       中心距 (mm)
        gamma_deg:  导程角 (deg)
        z1:         蜗杆头数
        z2:         蜗轮齿数
        handedness: "right" 或 "left"
        """
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
            painter.drawText(
                QRectF(panel.left() + 18, panel.top() + 12, panel.width() - 36, 20),
                Qt.AlignmentFlag.AlignLeft,
                self._title,
            )

            diagram = QRectF(panel.left() + 22, panel.top() + 44, panel.width() * 0.67, panel.height() - 66)
            info = QRectF(diagram.right() + 16, diagram.top(), panel.right() - diagram.right() - 24, diagram.height())

            painter.setPen(QPen(QColor("#E4DDD2"), 1.0))
            painter.drawRoundedRect(diagram, 10, 10)
            painter.drawRoundedRect(info, 10, 10)

            # --- 动态缩放 ---
            d1_mm = self._geom_state["d1_mm"]
            d2_mm = self._geom_state["d2_mm"]
            a_mm = self._geom_state["a_mm"]
            gamma_deg = self._geom_state["gamma_deg"]
            z1 = self._geom_state["z1"]
            z2 = self._geom_state["z2"]
            handedness = self._geom_state["handedness"]

            # 水平方向：蜗杆宽度约 2.5*d1 + 间隔 + d2；垂直方向：max(d1, d2) + 中心距偏移
            horiz_needed_mm = d1_mm * 2.5 + d2_mm + 40.0
            vert_needed_mm = max(d2_mm, 40.0) + a_mm * 0.5

            scale_mm_to_px = min(
                (diagram.width() - 80.0) / max(horiz_needed_mm, 1.0),
                (diagram.height() - 100.0) / max(vert_needed_mm, 1.0),
            )
            # 为了可读性，限制最大 scale
            scale_mm_to_px = min(scale_mm_to_px, 3.0)

            d1_px = d1_mm * scale_mm_to_px
            d2_px = d2_mm * scale_mm_to_px
            a_px = a_mm * scale_mm_to_px

            # 蜗杆轴中心线 y 位置（靠下一些给蜗轮留空间）
            axis_y = diagram.top() + diagram.height() * 0.65

            # 蜗杆矩形（表示分度圆直径范围，宽度取 2.5*d1）
            worm_w = d1_px * 2.5
            worm_rect = QRectF(
                diagram.left() + 36,
                axis_y - d1_px * 0.5,
                worm_w,
                d1_px,
            )

            # 蜗轮圆心：在蜗杆中心上方 a_px
            wheel_center_x = worm_rect.center().x()
            wheel_center_y = axis_y - a_px
            wheel_center = QPointF(wheel_center_x, wheel_center_y)
            wheel_rect = QRectF(
                wheel_center_x - d2_px * 0.5,
                wheel_center_y - d2_px * 0.5,
                d2_px,
                d2_px,
            )

            # 中心线（虚线）
            painter.setPen(QPen(QColor("#8B7C67"), 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(
                QPointF(worm_rect.left() - 26, worm_rect.center().y()),
                QPointF(worm_rect.right() + 26, worm_rect.center().y()),
            )
            painter.drawLine(
                QPointF(wheel_center.x(), wheel_rect.top() - 20),
                QPointF(wheel_center.x(), wheel_rect.bottom() + 28),
            )

            # 蜗杆轮廓（圆角矩形）
            painter.setPen(QPen(QColor("#7F7260"), 2.2))
            painter.setBrush(QColor("#E6DCCE"))
            painter.drawRoundedRect(worm_rect, min(d1_px * 0.35, 28), min(d1_px * 0.35, 28))

            # 蜗轮轮廓（圆 + 内孔）
            painter.setBrush(QColor("#E3D3C0"))
            painter.drawEllipse(wheel_rect)
            bore_ratio = 0.26
            bore_rect = wheel_rect.adjusted(
                wheel_rect.width() * bore_ratio,
                wheel_rect.height() * bore_ratio,
                -wheel_rect.width() * bore_ratio,
                -wheel_rect.height() * bore_ratio,
            )
            painter.setBrush(QColor("#FBF8F3"))
            painter.drawEllipse(bore_rect)

            # 螺旋线（倾斜方向由 handedness 决定）
            # 右旋：线从左上到右下（hand_sign = +1 即正斜率）
            # 左旋：线从左下到右上（hand_sign = -1）
            hand_sign = 1.0 if handedness == "right" else -1.0
            painter.setPen(QPen(QColor("#B65E2C"), 2.1))
            num_lines = max(3, min(9, int(worm_rect.width() / 10)))
            for idx in range(num_lines):
                x0 = worm_rect.left() + 8 + idx * (worm_rect.width() - 16) / max(num_lines - 1, 1)
                painter.drawLine(
                    QPointF(x0, worm_rect.top() + 7),
                    QPointF(x0 + hand_sign * worm_rect.width() * 0.15, worm_rect.bottom() - 7),
                )

            # 蜗轮辐条线
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

            # 啮合区标记
            mesh_spot = QPointF(worm_rect.center().x(), axis_y - 6)
            painter.setPen(QPen(QColor("#C55A11"), 2.0))
            painter.setBrush(QColor(197, 90, 17, 45))
            painter.drawEllipse(mesh_spot, 14.0, 14.0)
            painter.setFont(make_ui_font(9))
            painter.setPen(QPen(QColor("#C55A11"), 1.0))
            painter.drawText(
                QRectF(mesh_spot.x() - 12, mesh_spot.y() - 34, 72, 16),
                Qt.AlignmentFlag.AlignLeft,
                "啮合区",
            )

            # 中心距尺寸线
            a_y_line = axis_y + d1_px * 0.5 + 20.0
            # 只有当 a_px 足够大时才画中心距线，否则会越界
            if a_px > 20.0:
                x_worm = worm_rect.center().x()
                x_wheel = wheel_center.x()
                a_line_y = max(worm_rect.top() - 28.0, panel.top() + 20.0)
                painter.setPen(QPen(QColor("#35637A"), 1.6))
                painter.drawLine(QPointF(x_worm, a_line_y), QPointF(x_wheel, a_line_y))
                painter.drawLine(QPointF(x_worm, a_line_y - 8), QPointF(x_worm, a_line_y + 8))
                painter.drawLine(QPointF(x_wheel, a_line_y - 8), QPointF(x_wheel, a_line_y + 8))
                painter.setFont(make_ui_font(9, 500))
                painter.drawText(
                    QRectF((x_worm + x_wheel) * 0.5 - 42, a_line_y - 22, 84, 16),
                    Qt.AlignmentFlag.AlignCenter,
                    f"a={a_mm:.1f}mm",
                )

            # d1 尺寸标注
            d1_x = worm_rect.left() + worm_rect.width() * 0.18
            painter.setPen(QPen(QColor("#58707E"), 1.3))
            painter.setFont(make_ui_font(9, 500))
            painter.drawLine(QPointF(d1_x, worm_rect.top() - 12), QPointF(d1_x, worm_rect.bottom() + 12))
            painter.drawLine(QPointF(d1_x - 8, worm_rect.top()), QPointF(d1_x + 8, worm_rect.top()))
            painter.drawLine(QPointF(d1_x - 8, worm_rect.bottom()), QPointF(d1_x + 8, worm_rect.bottom()))
            painter.drawText(
                QRectF(d1_x - 22, worm_rect.top() - 30, 48, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"d1={d1_mm:.0f}",
            )

            # d2 尺寸标注
            d2_x = wheel_rect.right() + 18
            painter.drawLine(QPointF(d2_x, wheel_rect.top()), QPointF(d2_x, wheel_rect.bottom()))
            painter.drawLine(QPointF(d2_x - 8, wheel_rect.top()), QPointF(d2_x + 8, wheel_rect.top()))
            painter.drawLine(QPointF(d2_x - 8, wheel_rect.bottom()), QPointF(d2_x + 8, wheel_rect.bottom()))
            painter.drawText(
                QRectF(d2_x - 22, wheel_rect.top() - 22, 52, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"d2={d2_mm:.0f}",
            )

            # 导程角标注（圆弧）
            painter.setPen(QPen(QColor("#A6472A"), 1.5))
            gamma_center = QPointF(worm_rect.right() - 28, worm_rect.center().y())
            painter.drawArc(QRectF(gamma_center.x() - 28, gamma_center.y() - 28, 56, 56), 0, 56 * 16)
            painter.setFont(make_ui_font(9))
            painter.drawText(
                QRectF(gamma_center.x() + 10, gamma_center.y() - 32, 64, 16),
                Qt.AlignmentFlag.AlignLeft,
                f"gamma={gamma_deg:.1f}",
            )

            # 旋向箭头与文字
            direction_label = "右旋示意" if handedness == "right" else "左旋示意"
            painter.setPen(QPen(QColor("#7A3E2B"), 1.5))
            arrow_y = worm_rect.bottom() + 20
            painter.drawLine(
                QPointF(worm_rect.left() + 16, arrow_y),
                QPointF(worm_rect.right() - 10, arrow_y),
            )
            painter.drawLine(
                QPointF(worm_rect.right() - 10, arrow_y),
                QPointF(worm_rect.right() - 18, arrow_y - 8),
            )
            painter.drawLine(
                QPointF(worm_rect.right() - 10, arrow_y),
                QPointF(worm_rect.right() - 18, arrow_y + 8),
            )
            painter.setFont(make_ui_font(9))
            painter.drawText(
                QRectF(worm_rect.left() + 14, arrow_y + 4, 88, 16),
                Qt.AlignmentFlag.AlignLeft,
                direction_label,
            )

            # 右侧信息面板
            painter.setPen(QPen(QColor("#5F584F"), 1.0))
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
        finally:
            painter.end()
