"""Compact-shell and shared chart interaction contracts."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from app.ui.design_tokens import cloud_porcelain_spacing
from app.ui.main_window import MainWindow
from app.ui.pages.fatigue_reliability_page import FatigueReliabilityPage
from app.ui.theme import apply_theme
from app.ui.widgets.buffer_energy_curve import BufferEnergyCurveWidget
from app.ui.widgets.buffer_response_curve import BufferResponseCurveWidget
from app.ui.widgets.fatigue_charts import FatigueDamageChart, FatigueReliabilityChart, FatigueSnChart
from app.ui.widgets.interactive_chart import InteractiveChartWidget
from app.ui.widgets.press_force_curve import PressForceCurveWidget
from app.ui.widgets.worm_performance_curve import WormPerformanceCurveWidget
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget


@pytest.fixture(scope="module")
def app() -> QApplication:
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    return instance


def test_shell_sidebar_collapses_to_numbered_rail_and_restores(app: QApplication) -> None:
    window = MainWindow()
    spacing = cloud_porcelain_spacing()
    try:
        window.resize(1280, 800)
        window.show()
        app.processEvents()
        assert not window.is_sidebar_collapsed()
        assert window.sidebar_toggle.text() == "收起模块"

        window.set_sidebar_collapsed(True)
        app.processEvents()
        assert window.is_sidebar_collapsed()
        assert window.sidebar.width() == spacing.sidebar_collapsed
        assert window._brand_copy.isHidden()
        assert window._sidebar_info.isHidden()
        assert window.sidebar_toggle.text() == "展开模块"

        window.set_sidebar_collapsed(False)
        app.processEvents()
        assert not window.is_sidebar_collapsed()
        assert spacing.sidebar_min <= window.sidebar.width() <= spacing.sidebar_max
        assert not window._brand_copy.isHidden()
    finally:
        window.close()


def test_fatigue_spectrum_keeps_five_visible_rows_and_uses_shared_input_style(
    app: QApplication,
) -> None:
    host = MainWindow()
    try:
        host.resize(1280, 800)
        host.show()
        host.module_list.setCurrentRow(7)
        app.processEvents()
        page = host.stack.currentWidget()
        assert isinstance(page, FatigueReliabilityPage)
        page.set_current_chapter(4)
        app.processEvents()
        assert page.material_name_edit.objectName() == "InputField"
        assert page.transfer_factor_edit.isHidden()
        assert page.lookup_edit.isHidden()
        row_height = page.spectrum_table.verticalHeader().defaultSectionSize()
        assert page.spectrum_table.viewport().height() >= row_height * 5
    finally:
        host.close()


def test_all_native_data_charts_share_the_interaction_contract(app: QApplication) -> None:
    chart_types = (
        FatigueSnChart,
        FatigueDamageChart,
        FatigueReliabilityChart,
        PressForceCurveWidget,
        WormPerformanceCurveWidget,
        BufferEnergyCurveWidget,
        BufferResponseCurveWidget,
    )
    for chart_type in chart_types:
        chart = chart_type()
        assert isinstance(chart, InteractiveChartWidget)
        assert chart.fit_view_button.text() == "适应"
        assert chart.axis_range_button.text() == "坐标"
        assert chart.chart_gesture_hint.text() == "滚轮缩放 · 拖动平移 · 悬停取值"


def test_native_chart_zoom_changes_view_and_fit_restores_it(app: QApplication) -> None:
    chart = PressForceCurveWidget()
    chart.set_curve([0, 10, 20], [0, 1000, 2500], 5, 18, 12)
    chart.resize(760, 320)
    chart.show()
    app.processEvents()
    chart.grab()
    context = chart._contexts["press_force"]
    auto = context.auto_bounds
    chart._zoom_context(context, context.rect.center(), 0.8, zoom_x=True, zoom_y=True)
    assert chart._manual_bounds["press_force"] != auto
    chart.reset_view()
    assert not chart._manual_bounds


def test_matplotlib_stress_chart_exposes_pan_zoom_coordinates_and_axis_control(
    app: QApplication,
) -> None:
    chart = WormStressCurveWidget()
    actions = [action.text() for action in chart._toolbar.actions()]
    assert "坐标" in actions
    assert chart._toolbar.coordinates
