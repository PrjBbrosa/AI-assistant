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
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.placeholder_page import PlaceholderPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage


ModuleSpec = Tuple[str, QWidget]


class MainWindow(QMainWindow):
    """Desktop shell with module sidebar and content stack."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Local Engineering Assistant")
        self.resize(1400, 860)
        self.setMinimumSize(900, 620)

        root = QWidget(self)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = self._build_sidebar()
        self.stack = QStackedWidget(root)
        self.stack.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal, root)
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(sidebar)
        splitter.addWidget(self.stack)
        splitter.setSizes([243, 1157])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter)

        self.modules: List[ModuleSpec] = [
            ("螺栓连接", BoltPage(self)),
            ("轴向受力螺纹连接", BoltTappedAxialPage(self)),
            ("过盈配合", InterferenceFitPage(self)),
            ("花键过盈配合", SplineFitPage(self)),
            ("蜗轮蜗杆设计", WormGearPage(self)),
            ("赫兹应力", HertzContactPage(self)),
            ("材料与标准库", PlaceholderPage("材料与标准库", self)),
        ]

        for name, widget in self.modules:
            index = self.module_list.count() + 1
            item = QListWidgetItem(f"{index}. {name}")
            self.module_list.addItem(item)
            self.stack.addWidget(widget)

        self.module_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.module_list.setCurrentRow(0)
        self.statusBar().showMessage("桌面框架就绪。当前模块：1. 螺栓连接")
        self.module_list.currentTextChanged.connect(
            lambda text: self.statusBar().showMessage(f"当前模块：{text}")
        )

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame(self)
        sidebar.setObjectName("SidebarPanel")
        sidebar.setMinimumWidth(160)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(12)

        brand = QLabel("Engineering Assistant", sidebar)
        brand.setObjectName("BrandTitle")
        subtitle = QLabel("Local Mechanical Design Workbench", sidebar)
        subtitle.setObjectName("BrandSubtitle")
        subtitle.setWordWrap(True)

        self.module_list = QListWidget(sidebar)
        self.module_list.setObjectName("ModuleList")
        self.module_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        helper = QLabel("左侧保留模块入口，当前已实现”螺栓连接””过盈配合””赫兹应力””蜗轮蜗杆设计”。", sidebar)
        helper.setObjectName("BrandSubtitle")
        helper.setWordWrap(True)
        helper.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addWidget(self.module_list, 1)
        layout.addWidget(helper)
        return sidebar
