"""Static Cloud Porcelain stress-field canvas.

Paints once per resize / palette / theme change. No timer, no mouse follow,
and no animation. Not wired into MainWindow in Wave 1.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen, QRadialGradient
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui.design_tokens import cloud_porcelain_palette, qcolor


class CloudCanvas(QWidget):
    """Application-canvas primitive with a static concentric stress field."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CloudCanvas")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def sizeHint(self) -> QSize:
        return QSize(800, 600)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self.update()
        super().changeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        palette = cloud_porcelain_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), qcolor(palette.canvas_base))

        width = float(self.width())
        height = float(self.height())
        center = QPointF(width - 90.0, 70.0)

        coral = qcolor(palette.accent)
        coral.setAlpha(32)
        coral_clear = QColor(coral)
        coral_clear.setAlpha(0)
        coral_glow = QRadialGradient(center, 340.0)
        coral_glow.setColorAt(0.0, coral)
        coral_glow.setColorAt(1.0, coral_clear)
        painter.fillRect(self.rect(), coral_glow)

        secondary = qcolor(palette.secondary)
        secondary.setAlpha(24)
        secondary_clear = QColor(secondary)
        secondary_clear.setAlpha(0)
        lower_left = QPointF(width * 0.12, height + 40.0)
        blue_glow = QRadialGradient(lower_left, 340.0)
        blue_glow.setColorAt(0.0, secondary)
        blue_glow.setColorAt(1.0, secondary_clear)
        painter.fillRect(self.rect(), blue_glow)

        radii = list(range(64, 341, 36))
        if radii[-1] != 340:
            radii.append(340)
        count = len(radii)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for index, radius in enumerate(radii):
            t = index / max(count - 1, 1)
            alpha = int(round(55 - t * (55 - 35)))
            pen = QPen(QColor(255, 255, 255, alpha))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawEllipse(center, float(radius), float(radius))

        painter.end()
