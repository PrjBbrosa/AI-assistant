"""Paint-only module navigation delegate.

Draws a number tile plus label. Item text, tooltip, and model data stay
unchanged; this class does not create a QWidget per row.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from app.ui.design_tokens import (
    cloud_porcelain_controls,
    cloud_porcelain_palette,
    cloud_porcelain_radii,
    qcolor,
)
from app.ui.fonts import make_mono_font, make_ui_font


_ITEM_TEXT_RE = re.compile(r"^(\d+)\.\s+(.*)$")

_TILE_SIZE = 22
_PAD_X = 8
_GAP = 7


def parse_module_item_text(text: str) -> tuple[str, str]:
    """Split ``N. name`` into a zero-padded index tile label and the name."""
    match = _ITEM_TEXT_RE.match(text)
    if match is None:
        return "", text
    return f"{int(match.group(1)):02d}", match.group(2)


class ModuleNavigationDelegate(QStyledItemDelegate):
    """Paint index tile + module name; hover/selected colors from tokens."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._item_height = cloud_porcelain_controls().module_item_height
        self._radius = cloud_porcelain_radii().radius_control
        self._tile_radius = cloud_porcelain_radii().radius_small
        self._label_font = make_ui_font(11)
        self._label_font_selected = make_ui_font(11, QFont.Weight.DemiBold)
        self._index_font = make_mono_font(9, QFont.Weight.DemiBold)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        width = option.rect.width() if option.rect.width() > 0 else 160
        return QSize(width, self._item_height)

    def label_text_rect(self, option: QStyleOptionViewItem, index: QModelIndex) -> QRect:
        """Text rect used for the module name (excludes the number tile)."""
        del index
        rect = option.rect.adjusted(1, 1, -1, -1)
        left = rect.left() + _PAD_X + _TILE_SIZE + _GAP
        right_limit = rect.right() - _PAD_X
        width = max(0, right_limit - left + 1)
        return QRect(left, rect.top(), width, rect.height())

    def elided_label(self, option: QStyleOptionViewItem, index: QModelIndex) -> str:
        """Return the name string that ``paint`` would draw."""
        _tile, name = parse_module_item_text(str(index.data(Qt.ItemDataRole.DisplayRole) or ""))
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        font = self._label_font_selected if selected else self._label_font
        metrics = QFontMetrics(font)
        return metrics.elidedText(
            name,
            Qt.TextElideMode.ElideRight,
            self.label_text_rect(option, index).width(),
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        palette = cloud_porcelain_palette()
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        hovered = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        raw = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        tile_text, name = parse_module_item_text(raw)
        rect = opt.rect.adjusted(1, 1, -1, -1)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if selected:
            painter.setBrush(qcolor(palette.accent_soft))
            painter.setPen(qcolor(palette.accent))
            painter.drawRoundedRect(rect, self._radius, self._radius)
        elif hovered:
            painter.setBrush(qcolor(palette.surface_glass_soft))
            painter.setPen(qcolor(palette.line_structural))
            painter.drawRoundedRect(rect, self._radius, self._radius)

        tile_rect = QRect(
            rect.left() + _PAD_X,
            rect.center().y() - _TILE_SIZE // 2,
            _TILE_SIZE,
            _TILE_SIZE,
        )
        if selected:
            painter.setBrush(qcolor(palette.accent))
            painter.setPen(Qt.PenStyle.NoPen)
            tile_ink = QColor(255, 255, 255)
        else:
            tile_fill = QColor(255, 255, 255)
            tile_fill.setAlpha(84)
            painter.setBrush(tile_fill)
            painter.setPen(Qt.PenStyle.NoPen)
            tile_ink = qcolor(palette.ink_quiet)
        painter.drawRoundedRect(tile_rect, self._tile_radius, self._tile_radius)

        painter.setPen(tile_ink)
        painter.setFont(self._index_font)
        painter.drawText(tile_rect, int(Qt.AlignmentFlag.AlignCenter), tile_text)

        label_rect = self.label_text_rect(opt, index)
        label_font = self._label_font_selected if selected else self._label_font
        if selected:
            label_color = qcolor(palette.accent_ink)
        elif hovered:
            label_color = qcolor(palette.ink_primary)
        else:
            label_color = qcolor(palette.ink_muted)
        metrics = QFontMetrics(label_font)
        drawn = metrics.elidedText(
            name,
            Qt.TextElideMode.ElideRight,
            label_rect.width(),
        )
        painter.setFont(label_font)
        painter.setPen(label_color)
        painter.drawText(
            label_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            drawn,
        )
        painter.restore()
