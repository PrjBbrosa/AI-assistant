"""Markdown 帮助内容的弹出窗口。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from app.ui.help_provider import HelpProvider


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
        popover = cls(title=entry.title, body_md=entry.body_md, parent=anchor.window())
        cls._current = popover

        # 定位：锚点右下偏移 +8，屏幕边界翻转
        anchor_rect = anchor.rect()
        top_left_global = anchor.mapToGlobal(QPoint(anchor_rect.right(), anchor_rect.bottom()))
        target = top_left_global + QPoint(8, 8)

        screen = anchor.screen().availableGeometry()
        w, h = popover.width(), popover.height()
        if target.x() + w > screen.right():
            target.setX(screen.right() - w - 8)
        if target.y() + h > screen.bottom():
            target.setY(screen.bottom() - h - 8)

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
