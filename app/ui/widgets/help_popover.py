"""Markdown 帮助内容的弹出窗口。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QKeyEvent, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from app.ui.help_provider import HelpProvider


def _anchor_is_valid(widget: Optional[QWidget]) -> bool:
    """判断 anchor 对应的 C++ 对象是否仍然存活。

    如果 widget 已被底层 C++ 释放（例如父页面先于帮助弹窗的 slot 被销毁），
    任何属性访问都会抛 RuntimeError。用一次廉价的属性访问做探测。
    """
    if widget is None:
        return False
    try:
        _ = widget.objectName()
        return True
    except RuntimeError:
        return False


class HelpPopover(QDialog):
    """460x520 无模态 Markdown 弹窗。"""

    _current: Optional["HelpPopover"] = None

    def __init__(
        self,
        title: str,
        body_md: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(False)
        self.setFixedSize(460, 520)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("HelpPopoverTitle")
        self._title_label.setWordWrap(True)

        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)

        header = QHBoxLayout()
        header.setContentsMargins(12, 10, 12, 6)
        header.addWidget(self._title_label, 1)
        header.addWidget(close_btn, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setMarkdown(body_md)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self._browser, 1)

    @classmethod
    def show_for(
        cls,
        help_ref: str,
        anchor: QWidget,
    ) -> "HelpPopover":
        # 同时只允许一个实例。Qt.WA_DeleteOnClose + 类级 _current 组合可能
        # 留下野引用，访问已销毁的 C++ 对象会抛 RuntimeError——吞掉并复位。
        try:
            if cls._current is not None and cls._current.isVisible():
                cls._current.close()
        except RuntimeError:
            pass
        cls._current = None

        entry = HelpProvider.instance().get(help_ref)

        # 锚点可能已被销毁（父页面先关闭、signal 残留、连点竞态）。所有
        # anchor.* 访问都会抛 RuntimeError——先探测，失效则退回游标定位。
        anchor_valid = _anchor_is_valid(anchor)
        parent_widget: Optional[QWidget] = anchor.window() if anchor_valid else None
        popover = cls(title=entry.title, body_md=entry.body_md, parent=parent_widget)
        cls._current = popover

        w, h = popover.width(), popover.height()
        if anchor_valid:
            # 定位：锚点右下偏移 +8，屏幕边界翻转
            anchor_rect = anchor.rect()
            top_left_global = anchor.mapToGlobal(
                QPoint(anchor_rect.right(), anchor_rect.bottom())
            )
            target = top_left_global + QPoint(8, 8)
            screen_geom = anchor.screen().availableGeometry()
        else:
            # 退化路径：游标右下偏移 +8，屏幕取 primaryScreen。
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
        popover.show()
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
