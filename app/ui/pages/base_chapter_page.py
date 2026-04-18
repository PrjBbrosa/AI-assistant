"""Shared chapter-style layout shell for engineering modules."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class BaseChapterPage(QWidget):
    """Reusable shell: header + actions + chapter navigation + footer state."""

    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QFrame(self)
        header.setObjectName("Card")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(2)
        title_label = QLabel(title, header)
        title_label.setObjectName("SectionTitle")
        hint_label = QLabel(subtitle, header)
        hint_label.setObjectName("SectionHint")
        hint_label.setWordWrap(True)
        header_layout.addWidget(title_label)
        header_layout.addWidget(hint_label)
        root.addWidget(header)

        actions = QFrame(self)
        self.actions_layout = QHBoxLayout(actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        self.left_actions_layout = QHBoxLayout()
        self.left_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.left_actions_layout.setSpacing(8)
        self.right_actions_layout = QHBoxLayout()
        self.right_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.right_actions_layout.setSpacing(8)
        self.actions_layout.addLayout(self.left_actions_layout)
        self.actions_layout.addStretch(1)
        self.actions_layout.addLayout(self.right_actions_layout)
        root.addWidget(actions)

        content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        content_splitter.setHandleWidth(4)
        content_splitter.setChildrenCollapsible(False)
        root.addWidget(content_splitter, 1)

        nav_card = QFrame(self)
        nav_card.setObjectName("Card")
        nav_card.setMinimumWidth(140)
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(8)
        self.nav_title_label = QLabel("计算顺序", nav_card)
        self.nav_title_label.setObjectName("SectionTitle")
        self.chapter_list = QListWidget(nav_card)
        self.chapter_list.setObjectName("ChapterList")
        nav_layout.addWidget(self.nav_title_label)
        nav_layout.addWidget(self.chapter_list, 1)
        content_splitter.addWidget(nav_card)
        self._chapter_step_index = 0

        self.chapter_stack = QStackedWidget(self)
        content_splitter.addWidget(self.chapter_stack)
        content_splitter.setSizes([198, 1000])
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)

        footer = QFrame(self)
        footer.setObjectName("Card")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        footer_layout.setSpacing(6)
        self.overall_badge = QLabel("等待计算", footer)
        self.overall_badge.setObjectName("WaitBadge")
        self.info_label = QLabel("选择左侧步骤填写参数后执行计算。", footer)
        self.info_label.setObjectName("SectionHint")
        self.info_label.setWordWrap(True)
        footer_layout.addWidget(self.overall_badge, 0, Qt.AlignmentFlag.AlignLeft)
        footer_layout.addWidget(self.info_label)
        root.addWidget(footer)

        self.chapter_list.currentRowChanged.connect(self.chapter_stack.setCurrentIndex)

    def add_action_button(self, text: str, primary: bool = False, side: str = "left") -> QPushButton:
        button = QPushButton(text, self)
        if primary:
            button.setObjectName("PrimaryButton")
        if side == "right":
            self.right_actions_layout.addWidget(button)
        else:
            self.left_actions_layout.addWidget(button)
        return button

    def add_action_stretch(self) -> None:
        # Retained for backwards compatibility with pages created before
        # the shared action bar was split into fixed left/right groups.
        return None

    def add_chapter(
        self,
        title: str,
        page: QWidget,
        *,
        help_ref: str | None = None,
    ) -> int:
        self._chapter_step_index += 1
        self.chapter_list.addItem(QListWidgetItem(f"步骤 {self._chapter_step_index}. {title}"))

        if help_ref:
            # Wrap page in a container with a chapter-header row: title + HelpButton.
            from app.ui.widgets.help_button import HelpButton
            wrapper = QWidget(self)
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.setSpacing(6)

            header_row = QFrame(wrapper)
            header_row.setObjectName("Card")
            header_layout = QHBoxLayout(header_row)
            header_layout.setContentsMargins(12, 6, 12, 6)
            header_layout.setSpacing(8)
            title_label = QLabel(title, header_row)
            title_label.setObjectName("SectionTitle")
            header_layout.addWidget(title_label, 0)
            header_layout.addWidget(HelpButton(help_ref, parent=header_row), 0)
            header_layout.addStretch(1)
            wrapper_layout.addWidget(header_row)
            wrapper_layout.addWidget(page, 1)

            return self.chapter_stack.addWidget(wrapper)

        return self.chapter_stack.addWidget(page)

    def set_current_chapter(self, index: int) -> None:
        self.chapter_list.setCurrentRow(index)

    def set_info(self, text: str) -> None:
        self.info_label.setText(text)

    def set_overall_status(self, text: str, status: str) -> None:
        if status == "pass":
            obj = "PassBadge"
        elif status == "fail":
            obj = "FailBadge"
        else:
            obj = "WaitBadge"
        self.overall_badge.setText(text)
        self.overall_badge.setObjectName(obj)
        self.overall_badge.style().unpolish(self.overall_badge)
        self.overall_badge.style().polish(self.overall_badge)
