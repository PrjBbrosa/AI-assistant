"""Main window with module navigation."""

from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.placeholder_page import PlaceholderPage


ModuleSpec = Tuple[str, QWidget]


class MainWindow(QMainWindow):
    """Desktop shell with module sidebar and content stack."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Local Engineering Assistant")
        self.resize(1400, 860)

        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = self._build_sidebar()
        self.stack = QStackedWidget(root)
        self.stack.setContentsMargins(0, 0, 0, 0)

        root_layout.addWidget(sidebar, 0)
        root_layout.addWidget(self.stack, 1)

        self.modules: List[ModuleSpec] = [
            ("螺栓连接", BoltPage(self)),
            ("轴连接", PlaceholderPage("轴连接", self)),
            ("轴承", PlaceholderPage("轴承", self)),
            ("蜗轮", PlaceholderPage("蜗轮", self)),
            ("弹簧", PlaceholderPage("弹簧", self)),
            ("材料与标准库", PlaceholderPage("材料与标准库", self)),
        ]

        for name, widget in self.modules:
            item = QListWidgetItem(name)
            self.module_list.addItem(item)
            self.stack.addWidget(widget)

        self.module_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.module_list.setCurrentRow(0)
        self.statusBar().showMessage("桌面框架就绪。当前模块：螺栓连接")
        self.module_list.currentTextChanged.connect(
            lambda text: self.statusBar().showMessage(f"当前模块：{text}")
        )

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(self)
        sidebar.setObjectName("SidebarPanel")
        sidebar.setFixedWidth(270)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(12)

        brand = QLabel("Claude-tone Assistant", sidebar)
        brand.setObjectName("BrandTitle")
        subtitle = QLabel("Local Mechanical Design Workbench", sidebar)
        subtitle.setObjectName("BrandSubtitle")
        subtitle.setWordWrap(True)

        self.module_list = QListWidget(sidebar)
        self.module_list.setObjectName("ModuleList")
        self.module_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        helper = QLabel("左侧保留模块入口，首版仅实现“螺栓连接”。", sidebar)
        helper.setObjectName("BrandSubtitle")
        helper.setWordWrap(True)
        helper.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addWidget(self.module_list, 1)
        layout.addWidget(helper)
        return sidebar

