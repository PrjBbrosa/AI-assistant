"""Engineering cross-section joint diagram rendered via SVG."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


class ClampingDiagramWidget(QWidget):
    """Draw an engineering-style bolt joint cross-section using SVG."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fm = 0.0
        self._fa = 0.0
        self._fk = 0.0
        self._joint_type = "tapped"
        self._svg_renderer = QSvgRenderer(self)
        self.setMinimumHeight(320)

    def set_forces(self, fm: float, fa: float, fk: float) -> None:
        self._fm = max(0.0, fm)
        self._fa = max(0.0, fa)
        self._fk = max(0.0, fk)
        self.update()

    def set_joint_type(self, joint_type: str) -> None:
        self._joint_type = "through" if joint_type == "through" else "tapped"
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

        # Regions: left legend / center diagram / right values
        left_legend_rect = QRectF(panel.left() + 10, panel.top() + 16, panel.width() * 0.19, panel.height() - 32)
        right_values_rect = QRectF(panel.left() + panel.width() * 0.74, panel.top() + 34, panel.width() * 0.23, panel.height() - 44)

        # Center engineering cross-section drawing (SVG)
        diagram = QRectF(
            panel.left() + panel.width() * 0.24,
            panel.top() + 8.0,
            panel.width() * 0.40,
            panel.height() - 16.0,
        )
        self._svg_renderer.load(self._build_svg().encode("utf-8"))
        self._svg_renderer.render(painter, diagram)

        cx = diagram.left() + diagram.width() * 0.44
        top = diagram.top() + diagram.height() * 0.16
        bottom = diagram.top() + diagram.height() * 0.86
        mid = (top + bottom) * 0.5

        # Force arrows
        x_right = diagram.right() + panel.width() * 0.025
        x_left = diagram.left() - panel.width() * 0.055

        arrow_pen = QPen(QColor("#D97757"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(arrow_pen)
        self._draw_arrow(painter, QPointF(x_right, mid - 12), QPointF(x_right, top + 10))
        self._draw_arrow(painter, QPointF(x_right, mid + 12), QPointF(x_right, bottom - 10))

        ext_pen = QPen(QColor("#4C627A"), 2.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(ext_pen)
        self._draw_arrow(painter, QPointF(x_left, top + 14), QPointF(x_left, top - 22))
        self._draw_arrow(painter, QPointF(x_left, bottom - 14), QPointF(x_left, bottom + 22))

        # Force labels in isolated boxes to avoid overlap
        self._draw_label_box(painter, QRectF(x_right + 10, top + 18, 124, 28), "FM (预紧力)")
        self._draw_label_box(painter, QRectF(x_right + 10, bottom - 54, 138, 28), "FK (残余夹紧力)")
        self._draw_label_box(painter, QRectF(x_left - 56, top - 50, 98, 28), "FA (外载)")

        # Left-side component legend (to avoid overlap with drawing callouts)
        painter.setPen(QPen(QColor("#5A564F"), 1.0))
        painter.setFont(QFont("Avenir Next", 9))
        painter.drawText(
            left_legend_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._legend_text(),
        )

        painter.setFont(QFont("Avenir Next", 10))
        painter.setPen(QPen(QColor("#6B665E"), 1.0))
        painter.drawText(
            right_values_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            f"FM = {self._fm:,.0f} N\n"
            f"FA = {self._fa:,.0f} N\n"
            f"FK = {self._fk:,.0f} N",
        )

    def _build_svg(self) -> str:
        """Return an engineering-style section view in SVG."""
        if self._joint_type == "through":
            return self._build_through_svg()
        return self._build_tapped_svg()

    def _legend_text(self) -> str:
        if self._joint_type == "through":
            return (
                "零件说明:\n"
                "1 螺栓头\n"
                "2 上被连接件\n"
                "3 下被连接件\n"
                "4 螺母"
            )
        return (
            "零件说明:\n"
            "1 螺栓头\n"
            "2 上被连接件\n"
            "3 下被连接件/基体\n"
            "4 内螺纹啮合区"
        )

    def _build_through_svg(self) -> str:
        return """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
  <defs>
    <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f0eee9"/>
      <stop offset="50%" stop-color="#d8d2c7"/>
      <stop offset="100%" stop-color="#bdb3a5"/>
    </linearGradient>
    <linearGradient id="shank" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#c8bfb1"/>
      <stop offset="50%" stop-color="#f3efe6"/>
      <stop offset="100%" stop-color="#b5ab9d"/>
    </linearGradient>
    <pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
      <line x1="0" y1="0" x2="0" y2="10" stroke="#b9ad9b" stroke-width="2"/>
    </pattern>
  </defs>

  <!-- Clamped members (continuous contact: no gaps) -->
  <rect x="160" y="162" width="470" height="92" fill="#e8dfd3" stroke="#9e907d" stroke-width="2"/>
  <rect x="160" y="254" width="470" height="92" fill="#e8dfd3" stroke="#9e907d" stroke-width="2"/>
  <rect x="160" y="162" width="470" height="92" fill="url(#hatch)" opacity="0.28"/>
  <rect x="160" y="254" width="470" height="92" fill="url(#hatch)" opacity="0.28"/>

  <!-- Contact plane between clamped parts -->
  <line x1="160" y1="254" x2="630" y2="254" stroke="#8f816d" stroke-width="1.6"/>

  <!-- Bolt head -->
  <polygon points="308,86 432,86 454,118 432,150 308,150 286,118"
           fill="url(#steel)" stroke="#7f7260" stroke-width="2"/>

  <!-- Shank -->
  <rect x="350" y="150" width="40" height="268" fill="url(#shank)" stroke="#7f7260" stroke-width="2"/>

  <!-- Thread section -->
  <rect x="350" y="294" width="40" height="124" fill="#c9bfae" opacity="0.55"/>
  <g stroke="#6f6251" stroke-width="1.5">
    <line x1="350" y1="300" x2="390" y2="314"/>
    <line x1="350" y1="316" x2="390" y2="330"/>
    <line x1="350" y1="332" x2="390" y2="346"/>
    <line x1="350" y1="348" x2="390" y2="362"/>
    <line x1="350" y1="364" x2="390" y2="378"/>
    <line x1="350" y1="380" x2="390" y2="394"/>
    <line x1="350" y1="396" x2="390" y2="410"/>
  </g>

  <!-- Nut -->
  <polygon points="308,358 432,358 454,390 432,422 308,422 286,390"
           fill="url(#steel)" stroke="#7f7260" stroke-width="2"/>

  <!-- Sectioned internal thread in nut -->
  <g stroke="#6f6251" stroke-width="1.3">
    <line x1="350" y1="364" x2="390" y2="376"/>
    <line x1="350" y1="378" x2="390" y2="390"/>
    <line x1="350" y1="392" x2="390" y2="404"/>
    <line x1="350" y1="406" x2="390" y2="418"/>
  </g>

  <!-- Center line -->
  <line x1="370" y1="70" x2="370" y2="510" stroke="#9b8d7a" stroke-width="1.2" stroke-dasharray="8 8"/>

  <!-- Component index markers -->
  <g font-family="Arial, sans-serif" font-size="12" fill="#4b433a">
    <circle cx="270" cy="118" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="266" y="123">1</text>
    <circle cx="176" cy="206" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="172" y="211">2</text>
    <circle cx="176" cy="300" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="172" y="305">3</text>
    <circle cx="270" cy="390" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="266" y="395">4</text>
  </g>

</svg>
""".strip()

    def _build_tapped_svg(self) -> str:
        return """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
  <defs>
    <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f0eee9"/>
      <stop offset="50%" stop-color="#d8d2c7"/>
      <stop offset="100%" stop-color="#bdb3a5"/>
    </linearGradient>
    <linearGradient id="shank" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#c8bfb1"/>
      <stop offset="50%" stop-color="#f3efe6"/>
      <stop offset="100%" stop-color="#b5ab9d"/>
    </linearGradient>
    <pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
      <line x1="0" y1="0" x2="0" y2="10" stroke="#b9ad9b" stroke-width="2"/>
    </pattern>
  </defs>

  <!-- Clamped members -->
  <rect x="160" y="162" width="470" height="92" fill="#e8dfd3" stroke="#9e907d" stroke-width="2"/>
  <rect x="160" y="254" width="470" height="92" fill="#e8dfd3" stroke="#9e907d" stroke-width="2"/>
  <rect x="160" y="162" width="470" height="92" fill="url(#hatch)" opacity="0.28"/>
  <rect x="160" y="254" width="470" height="92" fill="url(#hatch)" opacity="0.28"/>

  <!-- Contact plane -->
  <line x1="160" y1="254" x2="630" y2="254" stroke="#8f816d" stroke-width="1.6"/>

  <!-- Bolt head -->
  <polygon points="308,86 432,86 454,118 432,150 308,150 286,118"
           fill="url(#steel)" stroke="#7f7260" stroke-width="2"/>

  <!-- Shank -->
  <rect x="350" y="150" width="40" height="214" fill="url(#shank)" stroke="#7f7260" stroke-width="2"/>

  <!-- Threaded shank in tapped hole -->
  <rect x="350" y="286" width="40" height="132" fill="#c9bfae" opacity="0.55"/>
  <g stroke="#6f6251" stroke-width="1.5">
    <line x1="350" y1="292" x2="390" y2="306"/>
    <line x1="350" y1="308" x2="390" y2="322"/>
    <line x1="350" y1="324" x2="390" y2="338"/>
    <line x1="350" y1="340" x2="390" y2="354"/>
    <line x1="350" y1="356" x2="390" y2="370"/>
    <line x1="350" y1="372" x2="390" y2="386"/>
    <line x1="350" y1="388" x2="390" y2="402"/>
  </g>

  <!-- Internal thread / tapped region -->
  <rect x="338" y="286" width="64" height="132" fill="none" stroke="#7f7260" stroke-width="1.6"/>
  <g stroke="#6f6251" stroke-width="1.3">
    <line x1="338" y1="294" x2="350" y2="304"/>
    <line x1="390" y1="304" x2="402" y2="294"/>
    <line x1="338" y1="314" x2="350" y2="324"/>
    <line x1="390" y1="324" x2="402" y2="314"/>
    <line x1="338" y1="334" x2="350" y2="344"/>
    <line x1="390" y1="344" x2="402" y2="334"/>
    <line x1="338" y1="354" x2="350" y2="364"/>
    <line x1="390" y1="364" x2="402" y2="354"/>
    <line x1="338" y1="374" x2="350" y2="384"/>
    <line x1="390" y1="384" x2="402" y2="374"/>
    <line x1="338" y1="394" x2="350" y2="404"/>
    <line x1="390" y1="404" x2="402" y2="394"/>
  </g>
  <text x="436" y="408" font-family="Arial, sans-serif" font-size="15" fill="#5a564f">内螺纹</text>

  <!-- Center line -->
  <line x1="370" y1="70" x2="370" y2="510" stroke="#9b8d7a" stroke-width="1.2" stroke-dasharray="8 8"/>

  <!-- Component index markers -->
  <g font-family="Arial, sans-serif" font-size="12" fill="#4b433a">
    <circle cx="270" cy="118" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="266" y="123">1</text>
    <circle cx="176" cy="206" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="172" y="211">2</text>
    <circle cx="176" cy="300" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="172" y="305">3</text>
    <circle cx="430" cy="352" r="10" fill="#f5efe6" stroke="#9e907d" stroke-width="1.2"/><text x="426" y="357">4</text>
  </g>

</svg>
""".strip()

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

    def _draw_label_box(self, painter: QPainter, rect: QRectF, text: str) -> None:
        painter.setPen(QPen(QColor("#CDBFAA"), 1.0))
        painter.setBrush(QColor(251, 248, 243, 235))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QPen(QColor("#1F1D1A"), 1.0))
        painter.setFont(QFont("Avenir Next", 9, 700))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class ThreadForceTriangleWidget(QWidget):
    """Draw a thread force triangle for axial/tangential/normal force relation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fm_max = 0.0
        self._lead_angle = 0.0
        self._friction_angle = 0.0
        self.setMinimumHeight(220)

    def set_thread_forces(self, fm_max: float, lead_angle_deg: float, friction_angle_deg: float) -> None:
        self._fm_max = max(0.0, fm_max)
        self._lead_angle = max(0.0, lead_angle_deg)
        self._friction_angle = max(0.0, friction_angle_deg)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        margin = 14.0
        panel = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        painter.setPen(QPen(QColor("#D9D3CA"), 1.0))
        painter.setBrush(QColor("#FBF8F3"))
        painter.drawRoundedRect(panel, 10, 10)

        # Triangle area
        base_y = panel.bottom() - 28
        x0 = panel.left() + 54
        x1 = panel.left() + panel.width() * 0.56
        apex = QPointF(x1, panel.top() + 36)
        p0 = QPointF(x0, base_y)
        p1 = QPointF(x1, base_y)

        painter.setPen(QPen(QColor("#7F7260"), 2.0))
        painter.setBrush(QColor(234, 223, 209, 60))
        painter.drawPolygon(QPolygonF([p0, p1, apex]))

        # Axes/edges
        self._draw_arrow(painter, p0, p1, QColor("#4C627A"), 2.2)  # Tangential
        self._draw_arrow(painter, p0, apex, QColor("#D97757"), 2.2)  # Resultant/normal side
        self._draw_arrow(painter, p1, apex, QColor("#5A8A5E"), 2.2)  # Axial side

        painter.setPen(QPen(QColor("#2E2A25"), 1.0))
        painter.setFont(QFont("Avenir Next", 10, 600))
        painter.drawText(QRectF(p0.x() + 10, base_y - 30, 150, 24), "Ft 螺纹切向力")
        painter.drawText(QRectF((p0.x() + apex.x()) / 2 - 20, (p0.y() + apex.y()) / 2 - 32, 150, 24), "Fn 法向力")
        painter.drawText(QRectF(p1.x() + 8, (p1.y() + apex.y()) / 2 - 12, 150, 24), "Fa 轴向分力")

        painter.setFont(QFont("Avenir Next", 10))
        painter.setPen(QPen(QColor("#6B665E"), 1.0))
        painter.drawText(
            QRectF(panel.left() + panel.width() * 0.67, panel.top() + 24, panel.width() * 0.30, panel.height() - 32),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "螺纹受力三角\n"
            f"FMmax = {self._fm_max:,.0f} N\n"
            f"导程角 λ = {self._lead_angle:.2f}°\n"
            f"摩擦角 ρ' = {self._friction_angle:.2f}°\n\n"
            "用于理解螺纹传力与\n扭矩分解关系。",
        )

    def _draw_arrow(self, painter: QPainter, p0: QPointF, p1: QPointF, color: QColor, width: float) -> None:
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(p0, p1)
        dx = p1.x() - p0.x()
        dy = p1.y() - p0.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1e-6:
            return
        ux = dx / length
        uy = dy / length
        size = 7.0
        left = QPointF(p1.x() - ux * size - uy * size * 0.65, p1.y() - uy * size + ux * size * 0.65)
        right = QPointF(p1.x() - ux * size + uy * size * 0.65, p1.y() - uy * size - ux * size * 0.65)
        painter.drawLine(p1, left)
        painter.drawLine(p1, right)
