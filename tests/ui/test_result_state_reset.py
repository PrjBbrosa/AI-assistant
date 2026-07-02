from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage
from core.spline.calculator import InputError as SplineInputError


_QT_APP: QApplication | None = None


def _app() -> QApplication:
    global _QT_APP
    _QT_APP = QApplication.instance() or _QT_APP or QApplication([])
    return _QT_APP


def test_worm_clear_resets_badges_cards_and_curves() -> None:
    app = _app()
    page = WormGearPage()
    page._calculate()
    app.processEvents()

    assert page._last_result is not None
    assert page._life_card.isHidden() is False
    assert page._efficiency_subtitle_card.isHidden() is False
    assert page.stress_curve._theta_deg
    page.geometry_overview.set_geometry_state(
        d1_mm=55.0,
        d2_mm=190.0,
        a_mm=122.5,
        gamma_deg=14.0,
        z1=3,
        z2=38,
        handedness="left",
    )
    assert page.geometry_overview._geom_state["d1_mm"] == 55.0

    page._clear()

    assert page._last_result is None
    assert page._last_payload is None
    for _key, (_name, badge) in page._check_badges.items():
        assert badge.text() == "待计算"
        assert badge.objectName() == "WaitBadge"
    assert page._overall_lc_badge.text() == "待计算"
    assert page._overall_lc_badge.objectName() == "WaitBadge"
    assert page._life_card.isHidden()
    assert page._efficiency_subtitle_card.isHidden()
    assert page.stress_curve._theta_deg == []
    assert page.stress_curve._sigma_h_mpa == []
    assert page.stress_curve._sigma_f_mpa == []
    assert page.geometry_overview._geom_state["d1_mm"] == 40.0
    assert page.geometry_overview._geom_state["d2_mm"] == 160.0


def test_tapped_clear_resets_visible_result_panels() -> None:
    _app()
    page = BoltTappedAxialPage()
    page._field_widgets["service.FA_max"].setText("2000")
    page._run_calculation()

    assert page._last_result is not None
    assert page.result_title.text() != "尚未执行计算"

    page._clear()

    assert page.result_title.text() == "尚未执行计算"
    assert page.result_summary.text() == "尚无结果。"
    assert page.metrics_text.text() == "尚无结果。"
    assert page.message_box.toPlainText() == ""
    for badge in page._check_badges.values():
        assert badge.text() == "待计算"
        assert badge.objectName() == "WaitBadge"
    assert page.overall_badge.text() == "等待计算"
    assert page.overall_badge.objectName() == "WaitBadge"


def test_tapped_apply_input_data_resets_visible_result_panels() -> None:
    _app()
    page = BoltTappedAxialPage()
    page._field_widgets["service.FA_max"].setText("2000")
    page._run_calculation()
    snapshot = page._capture_input_snapshot()

    page._apply_input_data(snapshot)

    assert page.result_title.text() == "尚未执行计算"
    assert page.result_summary.text() == "尚无结果。"
    assert page.metrics_text.text() == "尚无结果。"
    assert page.message_box.toPlainText() == ""
    for badge in page._check_badges.values():
        assert badge.text() == "待计算"
        assert badge.objectName() == "WaitBadge"
    assert page.overall_badge.text() == "等待计算"
    assert page.overall_badge.objectName() == "WaitBadge"


def test_tapped_input_change_marks_overall_badge_stale() -> None:
    _app()
    page = BoltTappedAxialPage()
    page._field_widgets["service.FA_max"].setText("2000")
    page._run_calculation()

    page._field_widgets["service.FA_max"].setText("3000")

    assert page.overall_badge.text() == "输入已变更，待重新计算"
    assert page.overall_badge.objectName() == "WaitBadge"
    assert page._last_result is None
    assert page._last_payload is None


def test_spline_input_error_resets_scenario_cards() -> None:
    app = _app()
    page = SplineFitPage()
    app.processEvents()

    assert page._result_labels["a_badge"].text() in ("PASS", "FAIL")

    with patch(
        "app.ui.pages.spline_fit_page.calculate_spline_fit",
        side_effect=SplineInputError("花键输入错误"),
    ):
        page._run_calculation(strict=True)

    assert page._last_payload is None
    assert page._last_result is None
    # 默认"仅花键"模式：场景 A 显示"待计算"，场景 B 显示"未启用"（mode-aware 复位）
    a_badge = page._result_labels["a_badge"]
    assert a_badge.text() == "待计算"
    assert a_badge.objectName() == "WaitBadge"
    b_badge = page._result_labels["b_badge"]
    assert b_badge.text() == "未启用"
    assert b_badge.objectName() == "WaitBadge"
    assert page._result_labels["a_detail"].text() == ""
    assert page._result_labels["b_detail"].text() == "仅花键模式，光滑段过盈校核已跳过。"
    assert page.curve_widget is not None
    assert page.curve_widget.isHidden()
    assert page.message_box is not None
    assert page.message_box.toPlainText() == ""
    assert "花键输入错误" in page.info_label.text()


def test_spline_combined_mode_reset_shows_pending_for_scenario_b() -> None:
    app = _app()
    page = SplineFitPage()
    app.processEvents()

    # 切到"联合"模式后，场景 B 复位应显示"待计算"而非"未启用"
    page._widgets["mode"].setCurrentText("联合")
    with patch(
        "app.ui.pages.spline_fit_page.calculate_spline_fit",
        side_effect=SplineInputError("花键输入错误"),
    ):
        page._run_calculation(strict=True)

    b_badge = page._result_labels["b_badge"]
    assert b_badge.text() == "待计算"
    assert b_badge.objectName() == "WaitBadge"
    assert page._result_labels["b_detail"].text() == ""
