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
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.design_tokens import cloud_porcelain_controls
from app.ui.widgets.action_overflow import ActionOverflowController, ChapterActionButton
from app.ui.widgets.chapter_delegate import ChapterNavigationDelegate


class BaseChapterPage(QWidget):
    """Reusable shell: combined header + chapter navigation + footer state."""

    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        controls = cloud_porcelain_controls()
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QFrame(self)
        header.setObjectName("ChapterHeader")
        header.setMinimumHeight(controls.header_min_height)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        title_block = QWidget(header)
        title_block.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        title_label = QLabel(title, title_block)
        title_label.setObjectName("ChapterTitle")
        hint_label = QLabel(subtitle, title_block)
        hint_label.setObjectName("SectionHint")
        hint_label.setWordWrap(True)
        title_layout.addWidget(title_label)
        title_layout.addWidget(hint_label)
        header_layout.addWidget(title_block, 1)

        actions = QWidget(header)
        actions.setObjectName("ChapterActions")
        actions.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
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

        self.overflow_button = QPushButton("更多", actions)
        self.actions_layout.addWidget(self.overflow_button)
        header_layout.addWidget(actions, 0)
        root.addWidget(header)

        self.chapter_header = header
        self._primary_action_button: QPushButton | None = None
        self._action_overflow = ActionOverflowController(header, self.overflow_button, self)

        content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        content_splitter.setHandleWidth(4)
        content_splitter.setChildrenCollapsible(False)
        root.addWidget(content_splitter, 1)

        nav_card = QFrame(self)
        nav_card.setObjectName("Card")
        # Include card/list padding in the supported-size width so current
        # long step labels render fully instead of creating horizontal scroll.
        nav_card.setMinimumWidth(260)
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(8)
        self.nav_title_label = QLabel("计算顺序", nav_card)
        self.nav_title_label.setObjectName("SubSectionTitle")
        self.chapter_list = QListWidget(nav_card)
        self.chapter_list.setObjectName("ChapterList")
        self.chapter_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chapter_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.chapter_list.setUniformItemSizes(True)
        self.chapter_list.setMouseTracking(True)
        self.chapter_list.viewport().setMouseTracking(True)
        self.chapter_list.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.chapter_list.setItemDelegate(ChapterNavigationDelegate(self.chapter_list))
        self.chapter_list.setSpacing(0)
        self.chapter_list.setFrameShape(QFrame.Shape.NoFrame)
        nav_layout.addWidget(self.nav_title_label)
        nav_layout.addWidget(self.chapter_list, 1)
        content_splitter.addWidget(nav_card)
        self._chapter_step_index = 0
        self._chapter_pages: list[QWidget] = []

        self.chapter_stack = QStackedWidget(self)
        content_splitter.addWidget(self.chapter_stack)
        content_splitter.setSizes([260, 940])
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)

        footer = QFrame(self)
        footer.setObjectName("Card")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        footer_layout.setSpacing(6)
        self.info_label = QLabel("选择左侧步骤填写参数后执行计算。", footer)
        self.info_label.setObjectName("SectionHint")
        self.info_label.setWordWrap(True)
        footer_layout.addWidget(self.info_label)
        root.addWidget(footer)

        self.chapter_list.currentRowChanged.connect(self.chapter_stack.setCurrentIndex)
        self.chapter_list.itemChanged.connect(self._sync_chapter_item_tooltip)

    @staticmethod
    def _sync_chapter_item_tooltip(item: QListWidgetItem) -> None:
        """Keep the complete dynamic step label available when text is elided."""
        if item.toolTip() != item.text():
            item.setToolTip(item.text())

    def add_action_button(self, text: str, primary: bool = False, side: str = "left") -> QPushButton:
        button = ChapterActionButton(text, self)
        controls = cloud_porcelain_controls()
        button.setMinimumHeight(controls.button_height)
        if primary:
            if (
                self._primary_action_button is not None
                and self._primary_action_button is not button
            ):
                self._demote_primary(self._primary_action_button)
            button.setObjectName("PrimaryButton")
            button.setMinimumHeight(controls.primary_button_height)
            self._primary_action_button = button
        if side == "right":
            self.right_actions_layout.addWidget(button)
        else:
            self.left_actions_layout.addWidget(button)
        self._action_overflow.register(button)
        return button

    def add_guide_button(
        self,
        help_ref: str,
        button_text: str = "校核指南",
    ) -> QPushButton:
        """Add a VDI-style modal walkthrough entry to the right action group."""
        button = self.add_action_button(button_text, side="right")
        button.setProperty("helpRef", help_ref)

        def _show_guide() -> None:
            from app.ui.widgets.beginner_guide_dialog import BeginnerGuideDialog

            dialog = BeginnerGuideDialog.from_help_ref(help_ref, parent=self)
            dialog.exec()

        button.clicked.connect(_show_guide)
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
        """Register a step page in ``chapter_stack``.

        Callers that need the original page widget should use
        ``chapter_page_at(i)``, not ``chapter_stack.widget(i)``. When
        ``help_ref`` is set, ``chapter_stack.widget(i)`` returns a wrapper
        (title row + HelpButton above ``page``); ``chapter_page_at(i)``
        always returns the original ``page`` passed into this method.

        Pages that pass ``help_ref`` should not render their own chapter
        title — the wrapper renders it alongside the "?" button.
        """
        self._chapter_step_index += 1
        item_text = f"步骤 {self._chapter_step_index}. {title}"
        item = QListWidgetItem(item_text)
        item.setToolTip(item_text)
        self.chapter_list.addItem(item)

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

            index = self.chapter_stack.addWidget(wrapper)
            self._chapter_pages.append(page)
            return index

        index = self.chapter_stack.addWidget(page)
        self._chapter_pages.append(page)
        return index

    def chapter_page_at(self, index: int) -> QWidget:
        """Return the original page widget registered via add_chapter(), regardless
        of whether a help_ref wrapper was applied. Use this instead of
        chapter_stack.widget(i) when you need the page itself."""
        return self._chapter_pages[index]

    def chapter_container_at(self, index: int) -> QWidget:
        """Return the widget actually inserted into chapter_stack — which is the
        help_ref wrapper if help_ref was set, otherwise the page itself."""
        return self.chapter_stack.widget(index)

    def set_current_chapter(self, index: int) -> None:
        self.chapter_list.setCurrentRow(index)

    def set_info(self, text: str) -> None:
        self.info_label.setText(text)

    def set_overall_status(self, text: str, status: str) -> None:
        """Footer carries run/save/error info only; overall verdict stays on the result card.

        Pass/fail conclusions are ignored so they are not duplicated as colored
        footer badges. Operational wait/error text is forwarded to ``info_label``.
        """
        if status == "pass":
            return
        if any(marker in text for marker in ("错误", "变更", "失败", "待重新")):
            self.set_info(text)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._action_overflow.relayout()

    @staticmethod
    def _demote_primary(button: QPushButton) -> None:
        button.setObjectName("")
        button.setMinimumHeight(cloud_porcelain_controls().button_height)
        style = button.style()
        style.unpolish(button)
        style.polish(button)
        button.update()
