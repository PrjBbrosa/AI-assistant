"""Main window with module navigation."""

from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

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

from app.ui.icons import brand_mark_pixmap

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

PageFactory = Callable[[], QWidget]
ModuleSpec = Tuple[str, QWidget]


# ---------------------------------------------------------------------------
# LazyStackedWidget — triggers lazy page construction on stack.widget() calls
# ---------------------------------------------------------------------------

class LazyStackedWidget(QStackedWidget):
    """QStackedWidget subclass that triggers lazy page construction transparently.

    When widget(index) is called for a slot that still holds a placeholder,
    the registered factory is invoked first so callers always receive the real
    page, not a blank QWidget placeholder.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # Populated by MainWindow after construction
        self._main_window: Optional["MainWindow"] = None

    def widget(self, index: int) -> Optional[QWidget]:  # type: ignore[override]
        if self._main_window is not None:
            self._main_window._ensure_page(index)
        return super().widget(index)


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Desktop shell with module sidebar and content stack."""

    def __init__(self) -> None:
        t0 = time.perf_counter()
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
        self.stack = LazyStackedWidget(root)
        self.stack._main_window = self
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

        # Factory list: each entry is (display_title, factory_callable)
        # Imports are deferred inside each factory to avoid pulling all heavy
        # modules at MainWindow import time.
        self._page_factories: List[Tuple[str, PageFactory]] = [
            ("螺栓连接", self._make_bolt_page),
            ("轴向受力螺纹连接", self._make_bolt_tapped_axial_page),
            ("过盈配合", self._make_interference_fit_page),
            ("花键连接校核", self._make_spline_fit_page),
            ("蜗轮蜗杆设计", self._make_worm_gear_page),
            ("赫兹应力", self._make_hertz_contact_page),
            ("材料与标准库", self._make_placeholder_page),
        ]

        # _pages[i] is None until the page has been constructed
        self._pages: List[Optional[QWidget]] = [None] * len(self._page_factories)

        # Populate sidebar list and stack placeholders
        for i, (name, _factory) in enumerate(self._page_factories):
            item = QListWidgetItem(f"{i + 1}. {name}")
            self.module_list.addItem(item)
            # Insert an empty placeholder widget; replaced when page is built
            self.stack.addWidget(QWidget())

        self.module_list.currentRowChanged.connect(self._on_row_changed)
        # Construct first page (BoltPage) immediately so startup shows content
        self._ensure_page(0)
        self.module_list.setCurrentRow(0)
        self.statusBar().showMessage("桌面框架就绪。当前模块：1. 螺栓连接")
        self.module_list.currentTextChanged.connect(
            lambda text: self.statusBar().showMessage(f"当前模块：{text}")
        )

        t1 = time.perf_counter()
        self.statusBar().showMessage(
            f"桌面框架就绪。当前模块：1. 螺栓连接  (启动耗时 {(t1 - t0) * 1000:.0f} ms)"
        )

    # ------------------------------------------------------------------
    # Lazy construction
    # ------------------------------------------------------------------

    def _ensure_page(self, index: int) -> Optional[QWidget]:
        """Construct the page at *index* if not yet built, replace placeholder.

        Safe to call multiple times; subsequent calls are no-ops.
        Returns the constructed (or already-constructed) page, or None if
        *index* is out of range.
        """
        if index < 0 or index >= len(self._page_factories):
            return None
        if self._pages[index] is None:
            _title, factory = self._page_factories[index]
            page = factory()
            # Replace the placeholder that was added at startup
            old_placeholder = super(LazyStackedWidget, self.stack).widget(index)
            self.stack.removeWidget(old_placeholder)
            old_placeholder.deleteLater()
            self.stack.insertWidget(index, page)
            self._pages[index] = page
        return self._pages[index]

    def _on_row_changed(self, index: int) -> None:
        """Navigate to the page at *index*, constructing it if necessary."""
        self._ensure_page(index)
        self.stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Backward-compatible property: window.modules -> [(name, page), ...]
    # Accessing this property triggers construction of ALL pages so that
    # callers receive real page instances (not placeholder QWidgets).
    # ------------------------------------------------------------------

    @property
    def modules(self) -> List[ModuleSpec]:
        """Return list of (title, page_widget) for all registered modules.

        Accessing this property causes all pages to be lazily constructed so
        callers always receive real instances.  Tests that iterate or type-
        check via this property will work correctly.
        """
        result: List[ModuleSpec] = []
        for i, (name, _factory) in enumerate(self._page_factories):
            page = self._ensure_page(i)
            result.append((name, page))  # type: ignore[arg-type]
        return result

    # ------------------------------------------------------------------
    # Page factory methods — deferred imports live here
    # ------------------------------------------------------------------

    def _make_bolt_page(self) -> QWidget:
        from app.ui.pages.bolt_page import BoltPage
        return BoltPage(self)

    def _make_bolt_tapped_axial_page(self) -> QWidget:
        from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
        return BoltTappedAxialPage(self)

    def _make_interference_fit_page(self) -> QWidget:
        from app.ui.pages.interference_fit_page import InterferenceFitPage
        return InterferenceFitPage(self)

    def _make_spline_fit_page(self) -> QWidget:
        from app.ui.pages.spline_fit_page import SplineFitPage
        return SplineFitPage(self)

    def _make_worm_gear_page(self) -> QWidget:
        from app.ui.pages.worm_gear_page import WormGearPage
        return WormGearPage(self)

    def _make_hertz_contact_page(self) -> QWidget:
        from app.ui.pages.hertz_contact_page import HertzContactPage
        return HertzContactPage(self)

    def _make_placeholder_page(self) -> QWidget:
        from app.ui.pages.placeholder_page import PlaceholderPage
        return PlaceholderPage("材料与标准库", self)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

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

        brand_mark = QLabel(sidebar)
        brand_mark.setObjectName("SidebarBrandMark")
        pixmap = brand_mark_pixmap(180)
        if not pixmap.isNull():
            brand_mark.setPixmap(pixmap)
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addWidget(self.module_list, 1)
        layout.addWidget(brand_mark)
        return sidebar
