"""Engineering cross-section joint diagram rendered via SVG."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from app.ui.design_tokens import qcolor, qpen, svg_palette
from app.ui.fonts import UI_FONT_FAMILY_SVG, make_ui_font


def _token(name: str, alpha: int | float | None = None) -> QColor:
    color = qcolor(name)
    if isinstance(alpha, float):
        color.setAlphaF(alpha)
    elif isinstance(alpha, int):
        color.setAlpha(alpha)
    return color


def _svg_opaque(token: str) -> str:
    """Opaque #RRGGBB for Qt SVG attributes (rgba() is not reliable there)."""
    parsed = qcolor(token)
    return f"#{parsed.red():02X}{parsed.green():02X}{parsed.blue():02X}"


def _svg_colors() -> dict[str, str]:
    pal = svg_palette()
    return {
        "UI_FONT_FAMILY_SVG": UI_FONT_FAMILY_SVG,
        "accent": pal["accent"],
        "steel0": _svg_opaque("surface_glass_strong"),
        "steel1": _svg_opaque("surface_glass"),
        "steel2": pal["ink_quiet"],
        "shank0": pal["secondary_soft"],
        "shank1": _svg_opaque("surface_glass_strong"),
        "shank2": pal["ink_quiet"],
        "hatch": pal["ink_quiet"],
        "member_fill": pal["secondary_soft"],
        "member_stroke": pal["ink_quiet"],
        "contact": pal["ink_muted"],
        "steel_stroke": pal["ink_muted"],
        "washer": pal["secondary_soft"],
        "washer_stroke": pal["ink_muted"],
        "clearance": pal["ink_quiet"],
        "thread_fill": pal["secondary_soft"],
        "thread_stroke": pal["ink_muted"],
        "centerline": pal["ink_quiet"],
        "label": pal["ink_primary"],
        "muted": pal["ink_muted"],
        "marker_fill": _svg_opaque("surface_glass_strong"),
        "marker_stroke": pal["ink_quiet"],
    }


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

    def diagram_state(self) -> tuple[str, float, float, float]:
        """Stored joint type and force values consumed by paintEvent."""
        return (self._joint_type, self._fm, self._fa, self._fk)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        margin = 20.0

        # Background panel
        panel = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(_token("surface_glass_soft"))
        painter.drawRoundedRect(panel, 12, 12)

        # Regions: legend / engineering section / force stack.  Labels are
        # deliberately outside the SVG body so they cannot cover the section.
        left_legend_rect = QRectF(panel.left() + 16, panel.top() + 18, panel.width() * 0.17, panel.height() - 36)
        right_values_rect = QRectF(panel.left() + panel.width() * 0.73, panel.top() + 24, panel.width() * 0.24, panel.height() - 48)

        # Center engineering cross-section drawing (SVG)
        diagram = QRectF(
            panel.left() + panel.width() * 0.21,
            panel.top() + 12.0,
            panel.width() * 0.48,
            panel.height() - 24.0,
        )
        self._svg_renderer.load(self._build_svg().encode("utf-8"))
        self._svg_renderer.render(painter, diagram)

        top = diagram.top() + diagram.height() * 0.16
        bottom = diagram.top() + diagram.height() * 0.86
        mid = (top + bottom) * 0.5

        # Force arrows
        x_right = right_values_rect.left() + 24
        x_left = diagram.left() - panel.width() * 0.035

        arrow_pen = QPen(_token("accent"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(arrow_pen)
        self._draw_arrow(painter, QPointF(x_right, mid - 12), QPointF(x_right, top + 10))
        self._draw_arrow(painter, QPointF(x_right, mid + 12), QPointF(x_right, bottom - 10))

        ext_pen = QPen(_token("secondary"), 2.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(ext_pen)
        self._draw_arrow(painter, QPointF(x_left, top + 14), QPointF(x_left, top - 22))
        self._draw_arrow(painter, QPointF(x_left, bottom - 14), QPointF(x_left, bottom + 22))

        # Force labels in isolated boxes to avoid overlap
        self._draw_label_box(painter, QRectF(x_right + 18, top + 16, 126, 28), "FM 预紧力")
        self._draw_label_box(painter, QRectF(x_right + 18, bottom - 54, 142, 28), "FK 残余夹紧力")
        self._draw_label_box(painter, QRectF(x_left - 56, top - 50, 98, 28), "FA (外载)")

        # Left-side component legend (to avoid overlap with drawing callouts)
        painter.setPen(qpen("ink_primary", 1.0))
        painter.setFont(make_ui_font(9))
        painter.drawText(
            left_legend_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            self._legend_text(),
        )

        painter.setFont(make_ui_font(10))
        painter.setPen(qpen("ink_muted", 1.0))
        painter.drawText(
            right_values_rect.adjusted(68, 2, -4, -4),
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
        return _THROUGH_SVG.format(**_svg_colors())

    def _build_tapped_svg(self) -> str:
        return _TAPPED_SVG.format(**_svg_colors())

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
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(_token("surface_glass_strong", 235))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(qpen("ink_primary", 1.0))
        painter.setFont(make_ui_font(9, 700))
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

    def triangle_state(self) -> tuple[float, float, float]:
        """Stored triangle inputs consumed by paintEvent (no derived safety)."""
        return (self._fm_max, self._lead_angle, self._friction_angle)

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        margin = 14.0
        panel = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(_token("surface_glass_soft"))
        painter.drawRoundedRect(panel, 10, 10)

        # Triangle area.  Keep labels away from the vector edges; the right
        # card carries the explanatory text and numeric values.
        base_y = panel.bottom() - 38
        x0 = panel.left() + 58
        x1 = panel.left() + panel.width() * 0.58
        apex = QPointF(x1, panel.top() + 42)
        p0 = QPointF(x0, base_y)
        p1 = QPointF(x1, base_y)

        painter.setPen(qpen("ink_muted", 2.0))
        painter.setBrush(_token("secondary_soft", 60))
        painter.drawPolygon(QPolygonF([p0, p1, apex]))

        # Axes/edges
        self._draw_arrow(painter, p0, p1, _token("secondary"), 2.2)  # Tangential
        self._draw_arrow(painter, p0, apex, _token("accent"), 2.2)  # Resultant/normal side
        self._draw_arrow(painter, p1, apex, _token("pass_fg"), 2.2)  # Axial side

        painter.setPen(qpen("ink_primary", 1.0))
        painter.setFont(make_ui_font(10, 600))
        painter.drawText(QRectF(p0.x() + 8, base_y - 28, 138, 22), "Ft 切向力")
        painter.drawText(QRectF((p0.x() + apex.x()) / 2 - 82, (p0.y() + apex.y()) / 2 - 22, 110, 22), "Fn 法向力")
        painter.drawText(QRectF(p1.x() + 10, (p1.y() + apex.y()) / 2 - 10, 104, 22), "Fa 轴向分力")

        # Angle arcs: lead angle at the screw helix and equivalent friction
        # angle near the resultant side.  They are intentionally short and
        # labelled below the triangle so they do not collide with the edges.
        painter.setPen(qpen("accent_ink", 1.4))
        painter.drawArc(QRectF(p0.x() + 18, base_y - 40, 78, 78), 0, 26 * 16)
        painter.drawText(QRectF(p0.x() + 96, base_y - 24, 86, 20), f"lambda={self._lead_angle:.2f} deg")
        painter.setPen(qpen("ink_muted", 1.4))
        painter.drawArc(QRectF(p0.x() + 38, base_y - 66, 112, 112), 22 * 16, 34 * 16)
        painter.drawText(QRectF(p0.x() + 190, base_y - 24, 98, 20), f"rho'={self._friction_angle:.2f} deg")

        painter.setFont(make_ui_font(10))
        painter.setPen(qpen("ink_muted", 1.0))
        info_rect = QRectF(panel.left() + panel.width() * 0.69, panel.top() + 22, panel.width() * 0.28, panel.height() - 44)
        painter.setPen(qpen("line_structural", 1.0))
        painter.setBrush(_token("surface_glass_soft"))
        painter.drawRoundedRect(info_rect, 8, 8)
        painter.setPen(qpen("ink_muted", 1.0))
        painter.drawText(
            info_rect.adjusted(12, 10, -12, -10),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            "螺纹受力三角\n"
            f"FMmax = {self._fm_max:,.0f} N\n"
            f"lambda = {self._lead_angle:.2f} deg\n"
            f"rho' = {self._friction_angle:.2f} deg\n\n"
            "用于理解轴向预紧力、\n螺纹切向力与法向力的\n分解关系。",
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


_THROUGH_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
  <defs>
    <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{steel0}"/>
      <stop offset="50%" stop-color="{steel1}"/>
      <stop offset="100%" stop-color="{steel2}"/>
    </linearGradient>
    <linearGradient id="shank" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{shank0}"/>
      <stop offset="50%" stop-color="{shank1}"/>
      <stop offset="100%" stop-color="{shank2}"/>
    </linearGradient>
    <pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
      <line x1="0" y1="0" x2="0" y2="10" stroke="{hatch}" stroke-width="2"/>
    </pattern>
  </defs>

  <!-- load path: bolt head -> clamped parts -> nut -->
  <path d="M330 150 L410 150 L490 356 L250 356 Z" fill="{accent}" opacity="0.12"/>
  <path d="M325 356 L495 356 L448 418 L372 418 Z" fill="{accent}" opacity="0.11"/>

  <!-- Clamped members (continuous contact: no gaps) -->
  <rect x="160" y="164" width="540" height="94" rx="3" fill="{member_fill}" stroke="{member_stroke}" stroke-width="2"/>
  <rect x="160" y="258" width="540" height="94" rx="3" fill="{member_fill}" stroke="{member_stroke}" stroke-width="2"/>
  <rect x="160" y="164" width="540" height="94" fill="url(#hatch)" opacity="0.22"/>
  <rect x="160" y="258" width="540" height="94" fill="url(#hatch)" opacity="0.22"/>

  <!-- Contact plane between clamped parts -->
  <line x1="160" y1="258" x2="700" y2="258" stroke="{contact}" stroke-width="1.6"/>

  <!-- Bolt head and bearing washer -->
  <polygon points="336,78 464,78 490,116 464,154 336,154 310,116"
           fill="url(#steel)" stroke="{steel_stroke}" stroke-width="2"/>
  <rect x="300" y="154" width="200" height="14" rx="4" fill="{washer}" stroke="{washer_stroke}" stroke-width="1.4"/>

  <!-- Shank -->
  <rect x="374" y="154" width="52" height="260" fill="url(#shank)" stroke="{steel_stroke}" stroke-width="2"/>
  <rect x="362" y="168" width="76" height="184" fill="none" stroke="{clearance}" stroke-width="1.2" stroke-dasharray="5 5"/>

  <!-- Thread section -->
  <rect x="374" y="292" width="52" height="122" fill="{thread_fill}" opacity="0.55"/>
  <g stroke="{thread_stroke}" stroke-width="1.5">
    <line x1="374" y1="300" x2="426" y2="316"/>
    <line x1="374" y1="316" x2="426" y2="332"/>
    <line x1="374" y1="332" x2="426" y2="348"/>
    <line x1="374" y1="348" x2="426" y2="364"/>
    <line x1="374" y1="364" x2="426" y2="380"/>
    <line x1="374" y1="380" x2="426" y2="396"/>
    <line x1="374" y1="396" x2="426" y2="412"/>
  </g>

  <!-- Nut -->
  <polygon points="336,360 464,360 490,398 464,436 336,436 310,398"
           fill="url(#steel)" stroke="{steel_stroke}" stroke-width="2"/>

  <!-- Sectioned internal thread in nut -->
  <g stroke="{thread_stroke}" stroke-width="1.3">
    <line x1="374" y1="368" x2="426" y2="382"/>
    <line x1="374" y1="384" x2="426" y2="398"/>
    <line x1="374" y1="400" x2="426" y2="414"/>
    <line x1="374" y1="416" x2="426" y2="430"/>
  </g>

  <!-- Center line -->
  <line x1="400" y1="62" x2="400" y2="500" stroke="{centerline}" stroke-width="1.2" stroke-dasharray="8 8"/>
  <text x="510" y="414" font-family="{UI_FONT_FAMILY_SVG}" font-size="15" fill="{muted}">Nut</text>

  <!-- Component index markers -->
  <g font-family="{UI_FONT_FAMILY_SVG}" font-size="12" fill="{label}">
    <circle cx="292" cy="116" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="288" y="121">1</text>
    <circle cx="178" cy="210" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="174" y="215">2</text>
    <circle cx="178" cy="306" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="174" y="311">3</text>
    <circle cx="292" cy="398" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="288" y="403">4</text>
  </g>

</svg>
""".strip()


_TAPPED_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
  <defs>
    <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{steel0}"/>
      <stop offset="50%" stop-color="{steel1}"/>
      <stop offset="100%" stop-color="{steel2}"/>
    </linearGradient>
    <linearGradient id="shank" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{shank0}"/>
      <stop offset="50%" stop-color="{shank1}"/>
      <stop offset="100%" stop-color="{shank2}"/>
    </linearGradient>
    <pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
      <line x1="0" y1="0" x2="0" y2="10" stroke="{hatch}" stroke-width="2"/>
    </pattern>
  </defs>

  <!-- load path: bolt head -> clamped parts -> tapped internal thread -->
  <path d="M330 150 L410 150 L500 402 L300 402 Z" fill="{accent}" opacity="0.12"/>

  <!-- Clamped members -->
  <rect x="160" y="164" width="540" height="94" rx="3" fill="{member_fill}" stroke="{member_stroke}" stroke-width="2"/>
  <rect x="160" y="258" width="540" height="132" rx="3" fill="{member_fill}" stroke="{member_stroke}" stroke-width="2"/>
  <rect x="160" y="164" width="540" height="94" fill="url(#hatch)" opacity="0.22"/>
  <rect x="160" y="258" width="540" height="132" fill="url(#hatch)" opacity="0.22"/>

  <!-- Contact plane -->
  <line x1="160" y1="258" x2="700" y2="258" stroke="{contact}" stroke-width="1.6"/>

  <!-- Bolt head and bearing washer -->
  <polygon points="336,78 464,78 490,116 464,154 336,154 310,116"
           fill="url(#steel)" stroke="{steel_stroke}" stroke-width="2"/>
  <rect x="300" y="154" width="200" height="14" rx="4" fill="{washer}" stroke="{washer_stroke}" stroke-width="1.4"/>

  <!-- Shank -->
  <rect x="374" y="154" width="52" height="244" fill="url(#shank)" stroke="{steel_stroke}" stroke-width="2"/>
  <rect x="362" y="168" width="76" height="222" fill="none" stroke="{clearance}" stroke-width="1.2" stroke-dasharray="5 5"/>

  <!-- Threaded shank in tapped hole -->
  <rect x="374" y="286" width="52" height="132" fill="{thread_fill}" opacity="0.55"/>
  <g stroke="{thread_stroke}" stroke-width="1.5">
    <line x1="374" y1="292" x2="426" y2="308"/>
    <line x1="374" y1="308" x2="426" y2="324"/>
    <line x1="374" y1="324" x2="426" y2="340"/>
    <line x1="374" y1="340" x2="426" y2="356"/>
    <line x1="374" y1="356" x2="426" y2="372"/>
    <line x1="374" y1="372" x2="426" y2="388"/>
    <line x1="374" y1="388" x2="426" y2="404"/>
  </g>

  <!-- Internal thread / tapped region -->
  <rect x="356" y="286" width="88" height="132" fill="none" stroke="{steel_stroke}" stroke-width="1.6"/>
  <g stroke="{thread_stroke}" stroke-width="1.3">
    <line x1="356" y1="294" x2="374" y2="306"/>
    <line x1="426" y1="306" x2="444" y2="294"/>
    <line x1="356" y1="314" x2="374" y2="326"/>
    <line x1="426" y1="326" x2="444" y2="314"/>
    <line x1="356" y1="334" x2="374" y2="346"/>
    <line x1="426" y1="346" x2="444" y2="334"/>
    <line x1="356" y1="354" x2="374" y2="366"/>
    <line x1="426" y1="366" x2="444" y2="354"/>
    <line x1="356" y1="374" x2="374" y2="386"/>
    <line x1="426" y1="386" x2="444" y2="374"/>
    <line x1="356" y1="394" x2="374" y2="406"/>
    <line x1="426" y1="406" x2="444" y2="394"/>
  </g>
  <text x="470" y="404" font-family="{UI_FONT_FAMILY_SVG}" font-size="15" fill="{muted}">内螺纹</text>
  <text x="470" y="382" font-family="{UI_FONT_FAMILY_SVG}" font-size="13" fill="{muted}">m_eff</text>

  <!-- Center line -->
  <line x1="400" y1="62" x2="400" y2="500" stroke="{centerline}" stroke-width="1.2" stroke-dasharray="8 8"/>

  <!-- Component index markers -->
  <g font-family="{UI_FONT_FAMILY_SVG}" font-size="12" fill="{label}">
    <circle cx="292" cy="116" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="288" y="121">1</text>
    <circle cx="178" cy="210" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="174" y="215">2</text>
    <circle cx="178" cy="320" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="174" y="325">3</text>
    <circle cx="454" cy="348" r="10" fill="{marker_fill}" stroke="{marker_stroke}" stroke-width="1.2"/><text x="450" y="353">4</text>
  </g>

</svg>
""".strip()
