"""Markdown 帮助内容的弹出窗口。"""
from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QSettings, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QKeyEvent, QCursor, QMouseEvent, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizeGrip,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.design_tokens import cloud_porcelain_shadows, qcolor, qss_rgba
from app.ui.help_provider import HelpEntry, HelpProvider


def _html_hex(token: str) -> str:
    """Opaque #RRGGBB for Qt rich-text bgcolor / inline CSS."""
    parsed = qcolor(token)
    return f"#{parsed.red():02X}{parsed.green():02X}{parsed.blue():02X}"


def _doc_css() -> str:
    """Qt rich-text CSS subset. Do not copy browser CSS into QTextBrowser."""
    ink = qss_rgba("ink_primary")
    code_bg = qss_rgba("surface_field")
    code_fg = qss_rgba("accent_ink")
    th_bg = qss_rgba("accent_soft")
    return (
        f"h2 {{ color: {ink}; font-size: 14pt; margin-top: 18px; margin-bottom: 8px; }}\n"
        f"h3 {{ color: {ink}; font-size: 12pt; margin-top: 14px; margin-bottom: 6px; }}\n"
        f"p  {{ color: {ink}; margin: 0 0 10px 0; }}\n"
        f"code {{ background-color: {code_bg}; color: {code_fg}; }}\n"
        f"th {{ background-color: {th_bg}; color: {ink}; }}\n"
        "ul, ol { margin: 0 0 10px 18px; }\n"
    )

_PRE_RE = re.compile(r'<pre([^>]*)>(.*?)</pre>', re.DOTALL)
_BLOCKQUOTE_RE = re.compile(r'<blockquote([^>]*)>(.*?)</blockquote>', re.DOTALL)
_TABLE_OPEN_RE = re.compile(r'<table(?![^>]*\bborder=)([^>]*)>')

# Match one or more consecutive markdown blockquote lines (> ...) as a block.
# Each group of contiguous "> " lines is converted to an HTML accent-bar table
# before handing the content to setMarkdown, because Qt's markdown parser
# does NOT emit <blockquote> tags — it renders them as indented <p> elements,
# making post-processing impossible.
_MD_BLOCKQUOTE_BLOCK_RE = re.compile(
    r'^((?:[ \t]*>[ \t]?[^\n]*\n?)+)',
    re.MULTILINE,
)


def _preprocess_md_blockquotes(md: str) -> str:
    """Convert markdown blockquote blocks to HTML accent-bar tables.

    Qt's setMarkdown silently converts "> text" to indented <p> elements,
    stripping the <blockquote> tag and making CSS-based left-border styling
    impossible.  We intercept each blockquote block before parsing, strip the
    leading "> " markers, and replace the whole block with a raw HTML table
    that QTextBrowser will render faithfully.
    """
    def _replace(m: re.Match) -> str:
        block = m.group(1)
        # Strip the "> " prefix from each line
        stripped_lines = []
        for line in block.splitlines():
            stripped = re.sub(r'^[ \t]*>[ \t]?', '', line)
            stripped_lines.append(stripped)
        inner_text = '\n'.join(stripped_lines).strip()
        # Escape HTML special chars in the text content
        inner_text = (
            inner_text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
        quote_bar = _html_hex("secondary")
        quote_bg = _html_hex("surface_glass_soft")
        quote_fg = _html_hex("ink_muted")
        return (
            '<table cellspacing="0" cellpadding="0" border="0" width="100%">'
            '<tr>'
            f'<td width="3" bgcolor="{quote_bar}"></td>'
            f'<td bgcolor="{quote_bg}" style="padding:6px 12px; color:{quote_fg}; font-style:italic;">'
            f'{inner_text}'
            '</td>'
            '</tr></table>\n\n'
        )
    return _MD_BLOCKQUOTE_BLOCK_RE.sub(_replace, md)


def _decorate_html(html: str) -> str:
    """Post-process Qt-generated HTML so borders and accents render.

    QTextBrowser ignores background: shorthand and border-left on block
    elements. We work around this by wrapping <pre> in minimal HTML tables
    that supply the left accent bar via a colored <td>, and injecting border
    attributes on <table> elements.
    """
    # Tables without border attr: inject border + cellspacing
    html = _TABLE_OPEN_RE.sub(
        r'<table\1 border="1" cellspacing="0" cellpadding="6" width="100%">',
        html,
    )

    # Code blocks: wrap in accent-bar table
    def _wrap_pre(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        pre_bar = _html_hex("accent")
        pre_bg = _html_hex("surface_field")
        return (
            '<table cellspacing="0" cellpadding="0" border="0" width="100%">'
            '<tr>'
            f'<td width="3" bgcolor="{pre_bar}"></td>'
            f'<td bgcolor="{pre_bg}" style="padding:8px 12px;">'
            f'<pre{attrs} style="margin:0;">{inner}</pre>'
            '</td>'
            '</tr></table>'
        )
    html = _PRE_RE.sub(_wrap_pre, html)

    # Blockquotes: wrap in accent-bar table if <blockquote> tags are present
    # (only reachable if the HTML source already contains them, e.g. raw HTML in md)
    def _wrap_blockquote(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        quote_bar = _html_hex("secondary")
        quote_bg = _html_hex("surface_glass_soft")
        quote_fg = _html_hex("ink_muted")
        return (
            '<table cellspacing="0" cellpadding="0" border="0" width="100%">'
            '<tr>'
            f'<td width="3" bgcolor="{quote_bar}"></td>'
            f'<td bgcolor="{quote_bg}" style="padding:6px 12px; color:{quote_fg}; font-style:italic;">'
            f'<blockquote{attrs} style="margin:0;">{inner}</blockquote>'
            '</td>'
            '</tr></table>'
        )
    html = _BLOCKQUOTE_RE.sub(_wrap_blockquote, html)

    return html

_SIZE_KEY = "help_popover/size"


def _settings() -> QSettings:
    return QSettings("AI-assistant", "help_popover")


def _anchor_is_valid(widget: Optional[QWidget]) -> bool:
    if widget is None:
        return False
    try:
        _ = widget.objectName()
        return True
    except RuntimeError:
        return False


class _HeaderFrame(QFrame):
    """头部栏：承担拖动窗口的职责。"""

    def __init__(self, parent: "HelpPopover") -> None:
        super().__init__(parent)
        self._popover = parent
        self._drag_offset: Optional[QPoint] = None
        self.setObjectName("HelpPopoverHeader")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._popover.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self._popover.move(new_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None:
            self._drag_offset = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class _SizeGrip(QSizeGrip):
    """QSizeGrip with a visible dotted indicator at bottom-right."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.SizeFDiagCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 3 小圆点，沿右下对角线排布
        painter.setBrush(qcolor("ink_quiet"))
        painter.setPen(Qt.NoPen)
        w = self.width()
        h = self.height()
        r = 1.4
        dots = [
            (w - 3, h - 3),
            (w - 3, h - 7),
            (w - 7, h - 3),
        ]
        for (cx, cy) in dots:
            painter.drawEllipse(QPointF(cx, cy), r, r)


class HelpPopover(QDialog):
    """精致悬浮卡片：可缩放、可拖动、带分类与出处。"""

    _current: Optional["HelpPopover"] = None
    _DEFAULT_SIZE = QSize(520, 640)
    _MIN_SIZE = QSize(380, 320)

    def __init__(
        self,
        entry: HelpEntry,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("HelpPopover")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setModal(False)
        self.setMinimumSize(self._MIN_SIZE)
        self.resize(self._DEFAULT_SIZE)
        saved = _settings().value(_SIZE_KEY)
        if isinstance(saved, QSize) and saved.isValid():
            # clamp to min
            w = max(self._MIN_SIZE.width(), saved.width())
            h = max(self._MIN_SIZE.height(), saved.height())
            self.resize(w, h)

        # 外层 root frame（承载圆角 + 阴影）
        self._root = QFrame(self)
        self._root.setObjectName("HelpPopoverRoot")

        shadows = cloud_porcelain_shadows()
        shadow = QGraphicsDropShadowEffect(self._root)
        shadow.setBlurRadius(shadows.raised_blur)
        shadow.setOffset(0, shadows.raised_y_offset)
        shadow.setColor(qcolor(shadows.color))
        self._root.setGraphicsEffect(shadow)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 16, 18, 24)
        root_layout.addWidget(self._root)

        # ----- Header -----
        self._header = _HeaderFrame(self)
        self._category_label = QLabel()
        self._category_label.setObjectName("HelpPopoverCategory")
        self._title_label = QLabel()
        self._title_label.setObjectName("HelpPopoverTitle")
        self._title_label.setWordWrap(True)

        self._pin_btn = QToolButton()
        self._pin_btn.setObjectName("HelpPopoverIconBtn")
        self._pin_btn.setText("📌")
        self._pin_btn.setCheckable(True)
        self._pin_btn.setCursor(Qt.PointingHandCursor)
        self._pin_btn.setToolTip("固定：禁止点外面关闭")
        self._pin_btn.toggled.connect(self._on_pin_toggled)

        close_btn = QToolButton()
        close_btn.setObjectName("HelpPopoverIconBtn")
        close_btn.setText("×")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("关闭 (Esc)")
        close_btn.clicked.connect(self.close)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(4)
        cat_row = QHBoxLayout()
        cat_row.setContentsMargins(0, 0, 0, 0)
        cat_row.addWidget(self._category_label)
        cat_row.addStretch(1)
        title_col.addLayout(cat_row)
        title_col.addWidget(self._title_label)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(18, 12, 12, 12)
        header_layout.setSpacing(8)
        header_layout.addLayout(title_col, 1)
        header_layout.addWidget(self._pin_btn)
        header_layout.addWidget(close_btn)

        # ----- Body -----
        self._browser = QTextBrowser()
        self._browser.setObjectName("HelpPopoverBody")
        self._browser.setOpenExternalLinks(True)
        self._browser.document().setDefaultStyleSheet(_doc_css())

        # ----- Footer -----
        self._footer = QFrame()
        self._footer.setObjectName("HelpPopoverFooter")
        self._source_label = QLabel()
        self._source_label.setObjectName("HelpPopoverSource")
        self._source_label.setWordWrap(True)
        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(18, 8, 18, 10)
        self._prefix_label = QLabel("出处：")
        self._prefix_label.setObjectName("HelpPopoverSourcePrefix")
        footer_layout.addWidget(self._prefix_label)
        footer_layout.addWidget(self._source_label, 1)
        footer_layout.addStretch(1)
        # SizeGrip 放在 footer 右端
        self._size_grip = _SizeGrip(self._footer)
        footer_layout.addWidget(self._size_grip, 0, Qt.AlignRight | Qt.AlignBottom)

        # ----- Assemble root -----
        inner = QVBoxLayout(self._root)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)
        inner.addWidget(self._header)
        inner.addWidget(self._browser, 1)
        inner.addWidget(self._footer)

        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)

        self._apply_entry(entry)

    def _apply_entry(self, entry: HelpEntry) -> None:
        self._title_label.setText(entry.title)
        if entry.category:
            self._category_label.setText(entry.category)
            self._category_label.setVisible(True)
        else:
            self._category_label.setVisible(False)
        self._browser.setMarkdown(_preprocess_md_blockquotes(entry.body_md))
        html = self._browser.toHtml()
        self._browser.setHtml(_decorate_html(html))
        if entry.source:
            self._source_label.setText(entry.source)
            self._source_label.setVisible(True)
            self._prefix_label.setVisible(True)
        else:
            self._source_label.setVisible(False)
            self._prefix_label.setVisible(False)
        # footer remains visible so QSizeGrip is always accessible

    def _on_pin_toggled(self, checked: bool) -> None:
        self._pin_btn.setProperty("pinned", "true" if checked else "false")
        self._pin_btn.style().unpolish(self._pin_btn)
        self._pin_btn.style().polish(self._pin_btn)
        self._pin_btn.setToolTip(
            "已固定：点击取消" if checked else "固定：禁止点外面关闭"
        )

    def is_pinned(self) -> bool:
        return self._pin_btn.isChecked()

    def _on_app_focus_changed(
        self,
        old: Optional[QWidget],
        new: Optional[QWidget],
    ) -> None:
        if self.is_pinned():
            return
        if new is None:
            return
        # Walk up from `new` — if it reaches self, keep open
        w: Optional[QWidget] = new
        while w is not None:
            if w is self:
                return
            w = w.parentWidget()
        self.close()

    @classmethod
    def show_for(
        cls,
        help_ref: str,
        anchor: QWidget,
    ) -> "HelpPopover":
        try:
            if cls._current is not None and cls._current.isVisible():
                cls._current.close()
        except RuntimeError:
            pass
        cls._current = None

        entry = HelpProvider.instance().get(help_ref)
        anchor_valid = _anchor_is_valid(anchor)
        parent_widget: Optional[QWidget] = anchor.window() if anchor_valid else None
        popover = cls(entry=entry, parent=parent_widget)
        cls._current = popover

        w, h = popover.width(), popover.height()
        if anchor_valid:
            anchor_rect = anchor.rect()
            top_left_global = anchor.mapToGlobal(
                QPoint(anchor_rect.right(), anchor_rect.bottom())
            )
            target = top_left_global + QPoint(8, 8)
            screen_geom = anchor.screen().availableGeometry()
        else:
            target = QCursor.pos() + QPoint(8, 8)
            primary = QApplication.primaryScreen()
            screen_geom = (
                primary.availableGeometry() if primary is not None
                else QRect(0, 0, 1920, 1080)
            )

        if target.x() + w > screen_geom.right():
            target.setX(screen_geom.right() - w - 8)
        if target.y() + h > screen_geom.bottom():
            target.setY(screen_geom.bottom() - h - 8)

        popover.move(target)
        popover.setWindowOpacity(0.0)
        popover.show()
        anim = QPropertyAnimation(popover, b"windowOpacity", popover)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        return popover

    def title_text(self) -> str:
        return self._title_label.text()

    def body_markdown(self) -> str:
        return self._browser.toMarkdown()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        try:
            QApplication.instance().focusChanged.disconnect(self._on_app_focus_changed)
        except (RuntimeError, TypeError):
            pass
        _settings().setValue(_SIZE_KEY, self.size())
        super().closeEvent(event)
