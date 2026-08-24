"""显示 '?' 的小按钮，触发 HelpPopover。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget

from app.ui.design_tokens import cloud_porcelain_controls


class HelpButton(QToolButton):
    """24x24 的紧凑帮助入口；与相邻标题按视觉重量而非触控块对齐。"""

    _HIT_SIZE = cloud_porcelain_controls().help_button_outer

    def __init__(self, help_ref: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("HelpButton")
        self.setText("?")
        self.setFixedSize(self._HIT_SIZE, self._HIT_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击查看帮助")
        self.setAccessibleName("帮助")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._help_ref = help_ref
        self.clicked.connect(self._on_click)

    @property
    def help_ref(self) -> str:
        return self._help_ref

    def _on_click(self) -> None:
        # 导入放在方法内部避免循环导入
        from app.ui.widgets.help_popover import HelpPopover
        popover = HelpPopover.show_for(self._help_ref, anchor=self)
        # HelpPopover 自管理生命周期
        _ = popover
