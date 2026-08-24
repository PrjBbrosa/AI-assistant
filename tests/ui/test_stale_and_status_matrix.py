"""Wave 6: stale/error visuals and cross-export verdict credibility."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable
from unittest.mock import patch

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
)

from app.ui.design_tokens import qss_rgba
from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.buffer_energy_page import BufferEnergyPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage
from app.ui.result_contract import (
    from_bolt,
    from_buffer,
    from_hertz,
    from_interference,
    from_spline,
    from_tapped_axial,
    from_worm,
)
from app.ui.theme import apply_theme, build_style_sheet
from core.bolt.calculator import InputError as BoltInputError
from core.bolt.tapped_axial_joint import InputError as TappedInputError
from core.buffer.calculator import InputError as BufferInputError
from core.hertz.calculator import InputError as HertzInputError
from core.interference.calculator import InputError as InterferenceInputError
from core.spline.calculator import InputError as SplineInputError
from core.worm.calculator import InputError as WormInputError


_QT_APP: QApplication | None = None
PASS_BADGE = "PassBadge"
FAIL_BADGE = "FailBadge"
NEUTRAL_BADGES = frozenset({"WaitBadge", "RefBadge", "IncompleteBadge"})
WAIT_COPY = ("尚未执行计算", "待计算", "尚无结果", "等待计算", "待仿真")


def _app() -> QApplication:
    global _QT_APP
    existing = QApplication.instance()
    if existing is not None:
        _QT_APP = existing
        return existing
    _QT_APP = QApplication([])
    apply_theme(_QT_APP)
    return _QT_APP


@dataclass(frozen=True)
class StatusContract:
    name: str
    page_cls: type[Any]
    calculate_method: str
    export_button_names: tuple[str, ...]
    widget_map_name: str
    edit_field_id: str
    view_builder: Callable[[dict[str, Any], dict[str, Any] | None], Any]
    calculator_patch: str
    input_error: type[Exception]
    sample: str | None = None
    clear_method: str = "_clear"
    auto_result_on_init: bool = False
    load_auto_recalculates: bool = False
    supports_incomplete_overall: bool = False
    supports_not_checked: bool = False
    supports_reference_only: bool = False


STATUS_CONTRACTS: tuple[StatusContract, ...] = (
    StatusContract(
        name="bolt",
        page_cls=BoltPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="loads.FA_max",
        view_builder=from_bolt,
        calculator_patch="app.ui.pages.bolt_page.calculate_vdi2230_core",
        input_error=BoltInputError,
        sample="input_case_01.json",
        supports_incomplete_overall=True,
        supports_not_checked=True,
        supports_reference_only=True,
    ),
    StatusContract(
        name="tapped",
        page_cls=BoltTappedAxialPage,
        calculate_method="_run_calculation",
        export_button_names=("btn_export_text", "btn_export_pdf"),
        widget_map_name="_field_widgets",
        edit_field_id="fastener.d",
        view_builder=from_tapped_axial,
        calculator_patch="app.ui.pages.bolt_tapped_axial_page.calculate_tapped_axial_joint",
        input_error=TappedInputError,
        sample="tapped_axial_joint_case_01.json",
        supports_incomplete_overall=True,
        supports_not_checked=True,
    ),
    StatusContract(
        name="hertz",
        page_cls=HertzContactPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="loads.normal_force_n",
        view_builder=from_hertz,
        calculator_patch="app.ui.pages.hertz_contact_page.calculate_hertz_contact",
        input_error=HertzInputError,
        sample="hertz_case_01.json",
    ),
    StatusContract(
        name="interference",
        page_cls=InterferenceFitPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="loads.torque_required_nm",
        view_builder=from_interference,
        calculator_patch="app.ui.pages.interference_fit_page.calculate_interference_fit",
        input_error=InterferenceInputError,
        sample="interference_case_01.json",
    ),
    StatusContract(
        name="spline",
        page_cls=SplineFitPage,
        calculate_method="_on_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_widgets",
        edit_field_id="loads.torque_required_nm",
        view_builder=from_spline,
        calculator_patch="app.ui.pages.spline_fit_page.calculate_spline_fit",
        input_error=SplineInputError,
        sample="spline_case_01.json",
        auto_result_on_init=True,
        load_auto_recalculates=True,
        supports_not_checked=True,
    ),
    StatusContract(
        name="worm",
        page_cls=WormGearPage,
        calculate_method="_calculate",
        export_button_names=("btn_save",),
        widget_map_name="_field_widgets",
        edit_field_id="operating.input_torque_nm",
        view_builder=from_worm,
        calculator_patch="app.ui.pages.worm_gear_page.calculate_worm_geometry",
        input_error=WormInputError,
        sample="worm_case_01.json",
        supports_incomplete_overall=True,
        supports_reference_only=True,
    ),
    StatusContract(
        name="buffer",
        page_cls=BufferEnergyPage,
        calculate_method="_on_calculate",
        export_button_names=("btn_save_report",),
        widget_map_name="_field_widgets",
        edit_field_id="impact.mass_kg",
        view_builder=from_buffer,
        calculator_patch="core.buffer.calculator.calculate_buffer_energy",
        input_error=BufferInputError,
        sample="buffer_energy_case_01.csv",
        clear_method="_on_clear",
    ),
)


def _make_page(contract: StatusContract) -> Any:
    app = _app()
    page = contract.page_cls()
    app.processEvents()
    if contract.sample:
        page._load_sample(contract.sample)
        app.processEvents()
    return page


def _export_buttons(page: Any, names: tuple[str, ...]) -> list[QPushButton]:
    return [getattr(page, name) for name in names]


def _relayout_actions(page: Any) -> None:
    page.show()
    page.resize(640, 400)
    _app().processEvents()
    controller = getattr(page, "_action_overflow", None)
    assert controller is not None
    controller.relayout()
    _app().processEvents()


def _assert_export_action_matches(page: Any, button: QPushButton) -> None:
    """Hidden QMenu QActions report isEnabled() False in Qt; only overflowed ones are meaningful."""
    controller = page._action_overflow
    action = controller.action_for(button)
    assert action is not None, f"missing overflow QAction for {button.text()!r}"
    controller.sync_button(button)
    if button in controller.overflowed_buttons() or action.isVisible():
        assert action.isEnabled() == button.isEnabled()
    else:
        assert not action.isVisible()


def _assert_export_disabled(page: Any, names: tuple[str, ...]) -> None:
    _relayout_actions(page)
    buttons = _export_buttons(page, names)
    assert all(not button.isEnabled() for button in buttons)
    for button in buttons:
        _assert_export_action_matches(page, button)


def _assert_export_enabled(page: Any, names: tuple[str, ...]) -> None:
    _relayout_actions(page)
    buttons = _export_buttons(page, names)
    assert all(button.isEnabled() for button in buttons)
    for button in buttons:
        _assert_export_action_matches(page, button)


def _result_badges(page: Any) -> list[QLabel]:
    badges: list[QLabel] = []
    raw = getattr(page, "_check_badges", None)
    if isinstance(raw, dict):
        for item in raw.values():
            badges.append(item[1] if isinstance(item, tuple) else item)
    raw = getattr(page, "check_badges", None)
    if isinstance(raw, dict):
        badges.extend(raw.values())
    labels = getattr(page, "_result_labels", None)
    if isinstance(labels, dict):
        for key, widget in labels.items():
            if "badge" in key:
                badges.append(widget)
    for attr in ("_overall_lc_badge", "load_capacity_status"):
        widget = getattr(page, attr, None)
        if isinstance(widget, QLabel):
            badges.append(widget)
    flowchart = getattr(page, "flowchart_nav", None)
    if flowchart is not None:
        badges.append(flowchart._verdict_badge)
        for node in flowchart._nodes:
            if node.badge is not None:
                badges.append(node.badge)
    return badges


def _assert_no_pass_badge(page: Any) -> None:
    leftover = [
        (badge.text(), badge.objectName())
        for badge in _result_badges(page)
        if badge.objectName() == PASS_BADGE
    ]
    assert leftover == [], leftover


def _assert_footer_not_overall_pass(page: Any) -> None:
    info = getattr(page, "info_label", None)
    if isinstance(info, QLabel):
        assert info.objectName() not in {PASS_BADGE, FAIL_BADGE}
    workbench = getattr(page, "workbench_status_label", None)
    if isinstance(workbench, QLabel):
        assert workbench.objectName() not in {PASS_BADGE, FAIL_BADGE}


def _assert_wait_or_empty_copy(page: Any) -> None:
    title = getattr(page, "result_title", None)
    if isinstance(title, QLabel):
        assert any(token in title.text() for token in WAIT_COPY), title.text()
    verdict = getattr(page, "overall_verdict_label", None)
    if isinstance(verdict, QLabel):
        assert any(token in verdict.text() for token in WAIT_COPY), verdict.text()
    metrics = getattr(page, "metrics_text", None)
    if isinstance(metrics, QLabel):
        assert any(token in metrics.text() for token in WAIT_COPY), metrics.text()
    metrics_box = getattr(page, "result_metrics", None)
    if isinstance(metrics_box, QPlainTextEdit):
        assert any(token in metrics_box.toPlainText() for token in WAIT_COPY)
    message = getattr(page, "message_box", None)
    if isinstance(message, QPlainTextEdit):
        assert message.toPlainText() == ""
    for label in getattr(page, "metric_labels", {}).values():
        text = label.text().strip()
        assert text in {"--", "—"} or text.startswith("--")


def _assert_charts_not_current_result(page: Any) -> None:
    curve = getattr(page, "curve_widget", None)
    if curve is not None and hasattr(curve, "curve_data") and not curve.isHidden():
        assert curve.curve_data()[0] == []
    performance = getattr(page, "performance_curve", None)
    if performance is not None and hasattr(performance, "curve_data"):
        load_factor = performance.curve_data()[0]
        assert load_factor == []
    stress = getattr(page, "stress_curve", None)
    if stress is not None and getattr(page, "_stress_curve_ready", False):
        assert stress._theta_deg == []
    response = getattr(page, "response_widget", None)
    if response is not None and hasattr(response, "response_data"):
        _variable, payload = response.response_data()
        assert payload is None
    diagram = getattr(page, "diagram_widget", None)
    if diagram is not None and hasattr(diagram, "_fm"):
        assert diagram._fm == 0.0
        assert diagram._fa == 0.0
        assert diagram._fk == 0.0
    for table_name in ("compare_table", "compare_preview_table"):
        table = getattr(page, table_name, None)
        if isinstance(table, QTableWidget):
            assert table.rowCount() == 0
    preview = getattr(page, "report_preview", None)
    if isinstance(preview, QPlainTextEdit):
        text = preview.toPlainText()
        assert "执行计算后显示" in text or "尚未" in text


def _assert_stale_surfaces(page: Any, names: tuple[str, ...]) -> None:
    _assert_export_disabled(page, names)
    _assert_no_pass_badge(page)
    _assert_wait_or_empty_copy(page)
    _assert_charts_not_current_result(page)
    _assert_footer_not_overall_pass(page)


def _assert_badge_matches_status(badge: QLabel, status: str) -> None:
    name = badge.objectName()
    if status == "pass":
        assert name == PASS_BADGE, (badge.text(), name)
        assert "不通过" not in badge.text()
    elif status == "fail":
        assert name == FAIL_BADGE, (badge.text(), name)
        assert "不通过" in badge.text() or "超限" in badge.text()
    else:
        assert name != PASS_BADGE, (status, badge.text(), name)
        assert name != FAIL_BADGE, (status, badge.text(), name)
        assert name in NEUTRAL_BADGES, (status, badge.text(), name)


def _overall_report_line(report: str) -> str:
    for line in report.splitlines():
        stripped = line.strip()
        if stripped.startswith("总体结论") or stripped.startswith("- 整体:"):
            return stripped
    return report


def _assert_verdict_family(text: str, status: str) -> None:
    if status == "fail":
        assert "不通过" in text, text
    elif status == "pass":
        assert "通过" in text, text
        assert "不通过" not in text, text
        assert "不完整" not in text, text
    elif status == "incomplete":
        assert "不完整" in text, text
        assert "校核通过" not in text, text
        assert "预校核通过" not in text, text
    elif status == "not_checked":
        assert "未校核" in text, text
    elif status == "reference_only":
        assert "参考" in text, text
    else:
        raise AssertionError(f"unknown status {status!r}")


def _title_widget(page: Any) -> QLabel:
    if isinstance(getattr(page, "result_title", None), QLabel):
        return page.result_title
    return page.overall_verdict_label


def _check_badge_for(page: Any, check_id: str) -> QLabel | None:
    raw = getattr(page, "_check_badges", None)
    if isinstance(raw, dict) and check_id in raw:
        item = raw[check_id]
        return item[1] if isinstance(item, tuple) else item
    raw = getattr(page, "check_badges", None)
    if isinstance(raw, dict) and check_id in raw:
        return raw[check_id]
    labels = getattr(page, "_result_labels", None)
    if isinstance(labels, dict):
        mapping = {"flank_ok": "a_badge", "slip_ok": "b_badge", "stress_ok": "b_badge"}
        key = mapping.get(check_id)
        if key and key in labels:
            return labels[key]
    return None


def _force_fail(result: dict[str, Any]) -> dict[str, Any]:
    bad = deepcopy(result)

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            if isinstance(obj.get("overall_pass"), bool):
                obj["overall_pass"] = False
            if obj.get("overall_status") in ("pass", "incomplete"):
                obj["overall_status"] = "fail"
            for key, value in obj.items():
                if isinstance(value, bool) and (
                    key.endswith("_ok") or key == "geometry_consistent"
                ):
                    obj[key] = False
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(bad)
    bad["overall_pass"] = False
    bad["overall_status"] = "fail"
    return bad


def _silence_boxes() -> Any:
    return patch.object(QMessageBox, "critical", return_value=None), patch.object(
        QMessageBox, "warning", return_value=None
    )


def _calculate(page: Any, contract: StatusContract) -> None:
    getattr(page, contract.calculate_method)()
    _app().processEvents()


def _edit_mapped_field(page: Any, contract: StatusContract) -> None:
    widgets = getattr(page, contract.widget_map_name)
    field = widgets[contract.edit_field_id]
    assert isinstance(field, QLineEdit)
    text = field.text().strip() or "1"
    try:
        new_text = f"{float(text) + 1:g}"
    except ValueError:
        new_text = f"{text}_edited"
    field.setText(new_text)
    field.textEdited.emit(new_text)
    _app().processEvents()
    timer = getattr(page, "_recalc_timer", None)
    if timer is not None:
        timer.stop()


def test_fail_badge_uses_fail_fg_not_accent() -> None:
    qss = build_style_sheet()
    fail_block = qss.split("QLabel#FailBadge")[1].split("QLabel#")[0]
    assert qss_rgba("fail_fg") in fail_block
    assert qss_rgba("accent") not in fail_block
    assert qss_rgba("accent_action") not in fail_block


@pytest.mark.parametrize(
    "contract",
    STATUS_CONTRACTS,
    ids=[item.name for item in STATUS_CONTRACTS],
)
def test_initial_uncalculated_disables_export_and_has_no_pass_badge(
    contract: StatusContract,
) -> None:
    app = _app()
    page = contract.page_cls()
    app.processEvents()
    _assert_export_disabled(page, contract.export_button_names)
    _assert_footer_not_overall_pass(page)
    if contract.auto_result_on_init:
        return
    _assert_no_pass_badge(page)
    _assert_wait_or_empty_copy(page)


@pytest.mark.parametrize(
    "contract",
    STATUS_CONTRACTS,
    ids=[item.name for item in STATUS_CONTRACTS],
)
def test_sample_calculate_matches_view_model_and_report(
    contract: StatusContract,
) -> None:
    page = _make_page(contract)
    _calculate(page, contract)
    assert isinstance(page._last_result, dict)
    view = contract.view_builder(page._last_result, page._last_payload)
    _assert_export_enabled(page, contract.export_button_names)
    title = _title_widget(page)
    assert view.title_zh in title.text()
    _assert_verdict_family(title.text(), view.overall_status)
    _assert_footer_not_overall_pass(page)
    raw_overall = page._last_result.get("overall_status")
    if raw_overall in ("pass", "fail", "incomplete"):
        assert view.overall_status == raw_overall
    elif "overall_pass" in page._last_result:
        expected = "pass" if page._last_result.get("overall_pass") else "fail"
        if view.overall_status in ("pass", "fail"):
            assert view.overall_status == expected or view.overall_status == "incomplete"
    for check in view.checks:
        badge = _check_badge_for(page, check.id)
        if badge is None:
            continue
        _assert_badge_matches_status(badge, check.status)
    report = "\n".join(page._build_report_lines())
    _assert_verdict_family(_overall_report_line(report), view.overall_status)
    for check in view.checks:
        if check.status == "not_checked":
            assert "未校核" in report, (check.id, report)
        elif check.status == "incomplete":
            assert "不完整" in report, (check.id, report)
        elif check.status == "fail":
            assert "不通过" in report, (check.id, report)
        elif check.status == "pass":
            assert "通过" in report, (check.id, report)


@pytest.mark.parametrize(
    "contract",
    STATUS_CONTRACTS,
    ids=[item.name for item in STATUS_CONTRACTS],
)
def test_fail_paints_fail_badge_not_accent(
    contract: StatusContract,
) -> None:
    page = _make_page(contract)
    _calculate(page, contract)
    view = contract.view_builder(page._last_result, page._last_payload)
    if view.overall_status != "fail":
        failed = _force_fail(page._last_result)
        crit, warn = _silence_boxes()
        with patch(contract.calculator_patch, return_value=failed), crit, warn:
            _calculate(page, contract)
        view = contract.view_builder(page._last_result, page._last_payload)
    assert view.overall_status == "fail"
    title = _title_widget(page)
    _assert_verdict_family(title.text(), "fail")
    fail_badges = [badge for badge in _result_badges(page) if badge.objectName() == FAIL_BADGE]
    assert fail_badges, "formal fail must paint at least one FailBadge"
    for badge in fail_badges:
        assert "通过" not in badge.text() or "不通过" in badge.text()
    _assert_verdict_family(_overall_report_line("\n".join(page._build_report_lines())), "fail")
    _assert_footer_not_overall_pass(page)


@pytest.mark.parametrize(
    "contract",
    [item for item in STATUS_CONTRACTS if item.supports_incomplete_overall or item.supports_not_checked or item.supports_reference_only],
    ids=[
        item.name
        for item in STATUS_CONTRACTS
        if item.supports_incomplete_overall or item.supports_not_checked or item.supports_reference_only
    ],
)
def test_incomplete_not_checked_reference_are_not_pass_or_fail(
    contract: StatusContract,
) -> None:
    page = _make_page(contract)
    if contract.name == "tapped":
        page._field_widgets["service.FA_max"].setText("2000")
        page._field_widgets["thread_strip.m_eff"].setText("")
        page._field_widgets["thread_strip.tau_BM"].setText("")
        page._field_widgets["thread_strip.tau_BS"].setText("")
    if contract.name == "worm":
        page._field_widgets["advanced.humidity_rh"].setText("80")
    _calculate(page, contract)
    view = contract.view_builder(page._last_result, page._last_payload)
    if contract.supports_incomplete_overall:
        if view.overall_status != "incomplete":
            patched = deepcopy(page._last_result)
            patched["overall_status"] = "incomplete"
            patched["overall_pass"] = False
            lc = patched.get("load_capacity")
            if isinstance(lc, dict):
                lc["overall_status"] = "incomplete"
                lc["overall_pass"] = False
            crit, warn = _silence_boxes()
            with patch(contract.calculator_patch, return_value=patched), crit, warn:
                _calculate(page, contract)
            view = contract.view_builder(page._last_result, page._last_payload)
        assert view.overall_status == "incomplete"
        title = _title_widget(page)
        _assert_verdict_family(title.text(), "incomplete")
        assert title.objectName() != PASS_BADGE
        overall_badge = getattr(page, "_overall_lc_badge", None)
        if isinstance(overall_badge, QLabel):
            _assert_badge_matches_status(overall_badge, "incomplete")
        _assert_verdict_family(
            _overall_report_line("\n".join(page._build_report_lines())),
            "incomplete",
        )
    saw_neutral = False
    for check in view.checks:
        if check.status not in {"incomplete", "not_checked", "reference_only"}:
            continue
        if not contract.supports_not_checked and check.status == "not_checked":
            continue
        if not contract.supports_reference_only and check.status == "reference_only":
            continue
        badge = _check_badge_for(page, check.id)
        if badge is None:
            continue
        _assert_badge_matches_status(badge, check.status)
        saw_neutral = True
    if contract.supports_not_checked:
        assert saw_neutral or view.overall_status == "incomplete"
    _assert_footer_not_overall_pass(page)


@pytest.mark.parametrize(
    "contract",
    STATUS_CONTRACTS,
    ids=[item.name for item in STATUS_CONTRACTS],
)
def test_input_error_and_core_exception_clear_success(
    contract: StatusContract,
) -> None:
    page = _make_page(contract)
    _calculate(page, contract)
    assert page._last_result is not None
    crit, warn = _silence_boxes()
    with patch(contract.calculator_patch, side_effect=contract.input_error("测试输入错误")), crit, warn:
        _calculate(page, contract)
    timer = getattr(page, "_recalc_timer", None)
    if timer is not None:
        timer.stop()
    _assert_stale_surfaces(page, contract.export_button_names)
    assert page._last_result is None
    _calculate(page, contract)
    assert page._last_result is not None
    crit, warn = _silence_boxes()
    with patch(contract.calculator_patch, side_effect=RuntimeError("core boom")), crit, warn:
        _calculate(page, contract)
    if timer is not None:
        timer.stop()
    _assert_stale_surfaces(page, contract.export_button_names)
    assert page._last_result is None
    _calculate(page, contract)
    assert page._last_result is not None
    _assert_export_enabled(page, contract.export_button_names)


@pytest.mark.parametrize(
    "contract",
    STATUS_CONTRACTS,
    ids=[item.name for item in STATUS_CONTRACTS],
)
def test_dirty_input_and_clear_remove_pass_and_disable_overflow(
    contract: StatusContract,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
    page = _make_page(contract)
    _calculate(page, contract)
    assert page._last_result is not None
    _assert_export_enabled(page, contract.export_button_names)
    _edit_mapped_field(page, contract)
    _assert_stale_surfaces(page, contract.export_button_names)
    _calculate(page, contract)
    getattr(page, contract.clear_method)()
    _app().processEvents()
    timer = getattr(page, "_recalc_timer", None)
    if timer is not None:
        timer.stop()
    _assert_stale_surfaces(page, contract.export_button_names)
    assert page._last_result is None
    if not contract.sample or contract.load_auto_recalculates:
        return
    _calculate(page, contract)
    page._load_sample(contract.sample)
    _app().processEvents()
    if timer is not None:
        timer.stop()
    _assert_stale_surfaces(page, contract.export_button_names)
