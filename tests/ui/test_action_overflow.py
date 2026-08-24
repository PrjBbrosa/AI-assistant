"""Action overflow: proxy clicks, enabled sync, destroy safety, P0 visibility."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget

from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.buffer_energy_page import BufferEnergyPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage
from app.ui.theme import apply_theme
from app.ui.widgets.action_overflow import classify_action_priority


BASE_CHAPTER_MODULES = (
    BoltTappedAxialPage,
    InterferenceFitPage,
    SplineFitPage,
    WormGearPage,
    HertzContactPage,
    BufferEnergyPage,
)


class _DemoPage(BaseChapterPage):
    def __init__(self) -> None:
        super().__init__("演示模块", "用于验证动作 overflow 的组合页头。")
        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行校核", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_export = self.add_action_button("导出结果说明")
        self.btn_help_guide = self.add_guide_button("modules/hertz/beginner_guide")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")
        self.btn_export.setEnabled(False)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    yield app


def _show_in_supported_host(app: QApplication, page: BaseChapterPage, width: int, height: int):
    host = QWidget()
    host.resize(width, height)
    layout = QHBoxLayout(host)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(12)
    sidebar = QWidget(host)
    sidebar.setFixedWidth(228)
    layout.addWidget(sidebar)
    layout.addWidget(page, 1)
    host.show()
    app.processEvents()
    return host


def _close_host(app: QApplication, host: QWidget, page: BaseChapterPage | None = None) -> None:
    if page is not None:
        page.setParent(None)
        page.hide()
    host.close()
    host.deleteLater()
    app.processEvents()


def _mapped_rect(widget: QWidget, host: QWidget):
    top_left = widget.mapTo(host, QPoint(0, 0))
    return top_left.x(), top_left.y(), widget.width(), widget.height()


def test_classify_action_priority_matches_text_rules() -> None:
    assert classify_action_priority("执行校核") == 0
    assert classify_action_priority("执行仿真") == 0
    assert classify_action_priority("导入曲线文件") == 0
    assert classify_action_priority("保存输入条件") == 1
    assert classify_action_priority("加载输入条件") == 1
    assert classify_action_priority("校核指南") == 1
    assert classify_action_priority("仿真指南") == 1
    assert classify_action_priority("清空参数") == 2
    assert classify_action_priority("测试案例 1") == 2
    assert classify_action_priority("导出结果说明") == 2
    assert classify_action_priority("导出文本报告") == 2


def test_add_action_button_returns_pushbutton_and_keeps_layout_groups(qapp):
    page = _DemoPage()
    assert isinstance(page.btn_calculate, QPushButton)
    assert page.left_actions_layout.count() == 5
    assert page.right_actions_layout.count() == 3
    assert page.left_actions_layout.itemAt(2).widget() is page.btn_calculate
    assert page.right_actions_layout.itemAt(0).widget() is page.btn_help_guide
    assert page.overflow_button.accessibleName() == "更多操作"
    assert page.overflow_button.focusPolicy() != Qt.FocusPolicy.NoFocus


def test_proxy_click_invokes_original_button(qapp):
    page = _DemoPage()
    hits: list[str] = []
    page.btn_clear.clicked.connect(lambda: hits.append("clear"))
    action = page._action_overflow.action_for(page.btn_clear)
    assert action is not None
    action.trigger()
    qapp.processEvents()
    assert hits == ["clear"]


def _force_overflow(app: QApplication, page: BaseChapterPage) -> None:
    page.show()
    page.resize(640, 400)
    app.processEvents()
    page._action_overflow.relayout()
    app.processEvents()


def test_enabled_sync_updates_closed_menu_action(qapp):
    page = _DemoPage()
    _force_overflow(qapp, page)
    try:
        action = page._action_overflow.action_for(page.btn_export)
        assert action is not None
        assert page.btn_export.isHidden()
        assert action.isVisible()
        assert not page.btn_export.isEnabled()
        assert not action.isEnabled()
        assert page.overflow_button.menu() is not None
        assert not page.overflow_button.menu().isVisible()

        page.btn_export.setEnabled(True)
        assert action.isEnabled()
        page.btn_export.setEnabled(False)
        assert not action.isEnabled()
    finally:
        page.close()


def test_disabled_export_stays_disabled_in_menu(qapp):
    page = _DemoPage()
    _force_overflow(qapp, page)
    try:
        hits: list[str] = []
        page.btn_export.clicked.connect(lambda: hits.append("export"))
        action = page._action_overflow.action_for(page.btn_export)
        assert action is not None
        assert page.btn_export.isHidden()
        assert action.isVisible()
        assert not page.btn_export.isEnabled()
        assert not action.isEnabled()
        action.trigger()
        qapp.processEvents()
        assert hits == []
        assert not page.btn_export.isEnabled()
        assert not action.isEnabled()
    finally:
        page.close()


def test_destroy_safety_does_not_touch_deleted_wrapper(qapp):
    page = _DemoPage()
    extra = page.add_action_button("清空参数")
    action = page._action_overflow.action_for(extra)
    assert action is not None
    extra.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()
    page._action_overflow._click_source(extra)
    page._action_overflow.relayout()
    qapp.processEvents()
    try:
        action.trigger()
    except RuntimeError:
        pass
    page.close()
    page.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def test_p0_calculate_visible_and_unclipped_at_1180(qapp):
    page = _DemoPage()
    host = _show_in_supported_host(qapp, page, 1180, 720)
    try:
        qapp.processEvents()
        calc = page.btn_calculate
        assert not calc.isHidden()
        x, y, width, height = _mapped_rect(calc, host)
        assert width > 0 and height > 0
        assert x >= 0
        assert x + width <= host.width()
        assert y >= 0
        assert y + height <= host.height()
        region = calc.visibleRegion().boundingRect()
        assert region.width() >= width - 1
        assert page.overflow_button.accessibleName() == "更多操作"
        if not page.overflow_button.isHidden():
            action = page._action_overflow.action_for(page.btn_export)
            assert action is not None
            assert not action.isEnabled()
            assert page.btn_clear in page._action_overflow.overflowed_buttons() or not page.btn_clear.isHidden()
    finally:
        _close_host(qapp, host, page)


def test_p2_enters_overflow_when_width_is_tight(qapp):
    page = _DemoPage()
    page.show()
    page.resize(640, 400)
    qapp.processEvents()
    page._action_overflow.relayout()
    qapp.processEvents()
    try:
        assert not page.btn_calculate.isHidden()
        overflowed = page._action_overflow.overflowed_buttons()
        assert page.btn_clear in overflowed or page.btn_load_1 in overflowed
        action = page._action_overflow.action_for(page.btn_clear)
        assert action is not None
        if page.btn_clear.isHidden():
            assert action.isVisible()
            assert action.isEnabled()
            hits: list[str] = []
            page.btn_clear.clicked.connect(lambda: hits.append("clear"))
            action.trigger()
            qapp.processEvents()
            assert hits == ["clear"]
        export_action = page._action_overflow.action_for(page.btn_export)
        assert export_action is not None
        assert not export_action.isEnabled()
        assert not page.overflow_button.isHidden()
        assert page.overflow_button.accessibleName() == "更多操作"
    finally:
        page.close()


@pytest.mark.parametrize("page_cls", BASE_CHAPTER_MODULES, ids=lambda cls: cls.__name__)
def test_six_base_chapter_pages_construct(qapp, page_cls):
    page = page_cls()
    assert page.chapter_header.objectName() == "ChapterHeader"
    assert page.chapter_list.objectName() == "ChapterList"
    assert isinstance(page.overflow_button, QPushButton)
    primaries = [
        child
        for child in page.findChildren(QPushButton)
        if child.objectName() == "PrimaryButton" and child is not page.overflow_button
    ]
    calculate = getattr(page, "btn_calculate", None)
    assert calculate is not None
    assert calculate.objectName() == "PrimaryButton"
    assert primaries == [calculate]
    page.deleteLater()
    qapp.processEvents()


def test_buffer_import_curve_is_p0_but_not_primary(qapp):
    page = BufferEnergyPage()
    assert page.btn_import_curve.objectName() != "PrimaryButton"
    assert page.btn_calculate.objectName() == "PrimaryButton"
    assert classify_action_priority(page.btn_import_curve.text()) == 0
    host = _show_in_supported_host(qapp, page, 1180, 720)
    try:
        qapp.processEvents()
        assert not page.btn_calculate.isHidden()
        assert not page.btn_import_curve.isHidden()
    finally:
        _close_host(qapp, host, page)
        page.deleteLater()
        qapp.processEvents()
