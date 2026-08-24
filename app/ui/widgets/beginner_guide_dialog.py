"""Shared VDI-style modal dialog for module-level beginner guides."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.help_provider import HelpProvider


GuideSections = Sequence[tuple[str, str]]


def _markdown_to_plain_text(markdown: str) -> str:
    document = QTextDocument()
    document.setMarkdown(markdown.strip())
    return document.toPlainText().strip()


def _split_markdown_sections(body_md: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Split a help article into intro text and level-2 section cards."""
    intro_lines: list[str] = []
    sections: list[tuple[str, str]] = []
    section_title = ""
    section_lines: list[str] = []

    def _flush_section() -> None:
        nonlocal section_lines
        if section_title:
            sections.append(
                (section_title, _markdown_to_plain_text("\n".join(section_lines)))
            )
        section_lines = []

    for line in body_md.splitlines():
        if line.startswith("## "):
            _flush_section()
            section_title = line[3:].strip()
        elif section_title:
            section_lines.append(line)
        else:
            intro_lines.append(line)
    _flush_section()

    intro = _markdown_to_plain_text("\n".join(intro_lines))
    if not sections:
        sections.append(("使用说明", _markdown_to_plain_text(body_md)))
        intro = ""
    return intro, tuple(sections)


class BeginnerGuideDialog(QDialog):
    """Native modal guide with the same layout contract as the VDI 2230 guide."""

    def __init__(
        self,
        *,
        window_title: str,
        guide_title: str,
        intro: str,
        sections: GuideSections,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("BeginnerGuideDialog")
        self.setWindowTitle(window_title)
        self.resize(720, 780)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(self.scroll_area)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self.guide_title_label = QLabel(guide_title, container)
        self.guide_title_label.setObjectName("GuideTitle")
        self.guide_title_label.setWordWrap(True)
        layout.addWidget(self.guide_title_label)

        self.intro_label = QLabel(intro, container)
        self.intro_label.setObjectName("SectionHint")
        self.intro_label.setWordWrap(True)
        self.intro_label.setVisible(bool(intro.strip()))
        layout.addWidget(self.intro_label)

        self.section_cards: list[QFrame] = []
        section_items = tuple(sections)
        for index, (section_title, section_body) in enumerate(section_items):
            if index > 0 and index < len(section_items) - 1:
                arrow = QLabel("  ▼", container)
                arrow.setObjectName("GuideFlowArrow")
                layout.addWidget(arrow)

            card = QFrame(container)
            card.setObjectName("SubCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)

            title_label = QLabel(section_title, card)
            title_label.setObjectName("GuideSectionTitle")
            title_label.setWordWrap(True)
            body_label = QLabel(section_body, card)
            body_label.setObjectName("SectionHint")
            body_label.setWordWrap(True)

            card_layout.addWidget(title_label)
            card_layout.addWidget(body_label)
            layout.addWidget(card)
            self.section_cards.append(card)

        layout.addStretch(1)
        self.scroll_area.setWidget(container)
        root.addWidget(self.scroll_area)

        self.close_button = QPushButton("我明白了", self)
        self.close_button.setObjectName("PrimaryButton")
        self.close_button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(24, 8, 24, 16)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_button)
        button_layout.addStretch(1)
        root.addLayout(button_layout)

    @classmethod
    def from_help_ref(
        cls,
        help_ref: str,
        *,
        parent: QWidget | None = None,
    ) -> "BeginnerGuideDialog":
        entry = HelpProvider.instance().get(help_ref)
        intro, sections = _split_markdown_sections(entry.body_md)
        if not intro:
            intro = (
                "这份指南帮你快速理解：适用范围、输入准备、计算步骤，"
                "以及结果应该怎样判断。"
            )
        return cls(
            window_title=entry.title,
            guide_title=entry.title,
            intro=intro,
            sections=sections,
            parent=parent,
        )

    def showEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().showEvent(event)
        QTimer.singleShot(0, self._center_on_parent)

    def _center_on_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        target = parent.window().frameGeometry().center()
        geometry = self.frameGeometry()
        geometry.moveCenter(target)
        self.move(geometry.topLeft())
