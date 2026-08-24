"""Main window with module navigation."""

from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent, QShowEvent
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

from app.ui.design_tokens import cloud_porcelain_spacing
from app.ui.icons import app_icon_pixmap
from app.ui.widgets.cloud_canvas import CloudCanvas
from app.ui.widgets.navigation_delegate import ModuleNavigationDelegate

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
        self.setMinimumSize(1180, 720)
        self._sidebar_sizes_applied = False

        spacing = cloud_porcelain_spacing()
        canvas = CloudCanvas(self)
        canvas_layout = QHBoxLayout(canvas)
        canvas_layout.setContentsMargins(
            spacing.canvas_margin,
            spacing.canvas_margin,
            spacing.canvas_margin,
            spacing.canvas_margin,
        )
        canvas_layout.setSpacing(0)
        self.setCentralWidget(canvas)

        sidebar = self._build_sidebar()
        self.stack = LazyStackedWidget(canvas)
        self.stack._main_window = self
        self.stack.setContentsMargins(0, 0, 0, 0)
        workspace = self._build_workspace()

        splitter = QSplitter(Qt.Orientation.Horizontal, canvas)
        splitter.setObjectName("ShellSplitter")
        splitter.setHandleWidth(4)
        splitter.setChildrenCollapsible(False)
        splitter.setOpaqueResize(True)
        splitter.addWidget(sidebar)
        splitter.addWidget(workspace)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.splitterMoved.connect(self._sync_shell_chrome)
        canvas_layout.addWidget(splitter)
        self.splitter = splitter
        self._apply_default_sidebar_width()

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
            ("缓冲块吸能仿真", self._make_buffer_energy_page),
            ("材料与标准库（即将推出）", self._make_placeholder_page),
        ]

        # _pages[i] is None until the page has been constructed
        self._pages: List[Optional[QWidget]] = [None] * len(self._page_factories)

        # Populate sidebar list and stack placeholders
        for i, (name, _factory) in enumerate(self._page_factories):
            item_text = f"{i + 1}. {name}"
            item = QListWidgetItem(item_text)
            item.setToolTip(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i + 1)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
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
        self._sync_shell_chrome()

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
        self._update_workspace_chrome(index)

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

    def _make_buffer_energy_page(self) -> QWidget:
        from app.ui.pages.buffer_energy_page import BufferEnergyPage
        return BufferEnergyPage(self)

    def _make_placeholder_page(self) -> QWidget:
        from app.ui.pages.placeholder_page import PlaceholderPage
        return PlaceholderPage("材料与标准库（即将推出）", self)

    # ------------------------------------------------------------------
    # Sidebar / workspace chrome
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        spacing = cloud_porcelain_spacing()
        sidebar = QFrame(self)
        sidebar.setObjectName("SidebarPanel")
        sidebar.setMinimumWidth(spacing.sidebar_min)
        sidebar.setMaximumWidth(spacing.sidebar_max)
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.sidebar = sidebar

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        brand_row = QWidget(sidebar)
        brand_row.setObjectName("BrandRow")
        brand_layout = QHBoxLayout(brand_row)
        brand_layout.setContentsMargins(0, 0, 0, 4)
        brand_layout.setSpacing(10)

        tile = QLabel(brand_row)
        tile.setObjectName("BrandTile")
        tile.setFixedSize(35, 35)
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pixmap = app_icon_pixmap(23)
        if not pixmap.isNull():
            tile.setPixmap(pixmap)
        self._brand_tile = tile

        copy = QWidget(brand_row)
        copy_layout = QVBoxLayout(copy)
        copy_layout.setContentsMargins(0, 0, 0, 0)
        copy_layout.setSpacing(2)
        brand = QLabel("Engineering Assistant", copy)
        brand.setObjectName("BrandTitle")
        subtitle = QLabel("Local Mechanical Design Workbench", copy)
        subtitle.setObjectName("BrandSubtitle")
        subtitle.setWordWrap(True)
        copy_layout.addWidget(brand)
        copy_layout.addWidget(subtitle)
        brand_layout.addWidget(tile, 0, Qt.AlignmentFlag.AlignVCenter)
        brand_layout.addWidget(copy, 1)

        nav_label = QLabel("模块", sidebar)
        nav_label.setObjectName("NavLabel")

        self.module_list = QListWidget(sidebar)
        self.module_list.setObjectName("ModuleList")
        self.module_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.module_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.module_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.module_list.setMouseTracking(True)
        self.module_list.viewport().setMouseTracking(True)
        self.module_list.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.module_list.setItemDelegate(ModuleNavigationDelegate(self.module_list))
        self.module_list.setSpacing(0)
        self.module_list.setFrameShape(QFrame.Shape.NoFrame)

        info = QFrame(sidebar)
        info.setObjectName("SidebarInfoCard")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(4)
        info_title = QLabel("本地工程计算", info)
        info_title.setObjectName("SidebarInfoTitle")
        info_body = QLabel("本地桌面机械设计预校核工具", info)
        info_body.setObjectName("SidebarInfoBody")
        info_body.setWordWrap(True)
        info_layout.addWidget(info_title)
        info_layout.addWidget(info_body)

        layout.addWidget(brand_row)
        layout.addWidget(nav_label)
        layout.addWidget(self.module_list, 1)
        layout.addWidget(info)
        return sidebar

    def _build_workspace(self) -> QWidget:
        spacing = cloud_porcelain_spacing()
        workspace = QWidget()
        workspace.setObjectName("WorkspaceColumn")
        # handleWidth is 4; remaining gutter makes the visible sidebar/workspace
        # gap match spacing.sidebar_gap (12px).
        gutter = max(0, spacing.sidebar_gap - 4)
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(gutter, 0, 0, 0)
        layout.setSpacing(8)

        chrome = QFrame(workspace)
        chrome.setObjectName("WorkspaceChrome")
        chrome.setFixedHeight(38)
        chrome_layout = QHBoxLayout(chrome)
        chrome_layout.setContentsMargins(4, 0, 4, 0)
        chrome_layout.setSpacing(8)
        breadcrumb = QLabel("本地机械设计工作台 / 螺栓连接", chrome)
        breadcrumb.setObjectName("WorkspaceBreadcrumb")
        breadcrumb.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        run_state = QLabel("本地运行", chrome)
        run_state.setObjectName("WorkspaceRunState")
        chrome_layout.addWidget(breadcrumb, 1)
        chrome_layout.addWidget(run_state, 0, Qt.AlignmentFlag.AlignVCenter)
        self._workspace_breadcrumb = breadcrumb
        self._workspace_run_state = run_state

        layout.addWidget(chrome)
        layout.addWidget(self.stack, 1)
        return workspace

    def _apply_default_sidebar_width(self) -> None:
        spacing = cloud_porcelain_spacing()
        total = max(self.splitter.size().width(), 1)
        rest = max(total - spacing.sidebar_width, 1)
        self.splitter.setSizes([spacing.sidebar_width, rest])

    def _update_workspace_chrome(self, index: int) -> None:
        if index < 0 or index >= len(self._page_factories):
            return
        name, _factory = self._page_factories[index]
        full = f"本地机械设计工作台 / {name}"
        width = max(40, self._workspace_breadcrumb.width())
        elided = self._workspace_breadcrumb.fontMetrics().elidedText(
            full, Qt.TextElideMode.ElideRight, width
        )
        self._workspace_breadcrumb.setText(elided)
        self._workspace_breadcrumb.setToolTip(full)

    def _sync_shell_chrome(self, *_args: object) -> None:
        spacing = cloud_porcelain_spacing()
        left = spacing.canvas_margin + self.sidebar.width() + spacing.sidebar_gap
        self.statusBar().setContentsMargins(left, 0, spacing.canvas_margin, 2)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._sidebar_sizes_applied:
            self._apply_default_sidebar_width()
            self._sidebar_sizes_applied = True
        self._sync_shell_chrome()
        self._update_workspace_chrome(self.module_list.currentRow())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._sync_shell_chrome()
        self._update_workspace_chrome(self.module_list.currentRow())
