"""Placeholder page for modules not implemented yet."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    """Simple module placeholder."""

    def __init__(self, module_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        card = QFrame(self)
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)

        title = QLabel(module_name, card)
        title.setObjectName("SectionTitle")
        hint = QLabel("模块框架已预留，当前版本未实现详细计算流程。", card)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)

        card_layout.addWidget(title)
        card_layout.addWidget(hint)
        card_layout.addStretch(1)
        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignTop)

