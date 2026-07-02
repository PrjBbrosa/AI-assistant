import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QMessageBox

from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage
from core.bolt.calculator import calculate_vdi2230_core
from core.bolt.tapped_axial_joint import calculate_tapped_axial_joint
from core.hertz.calculator import calculate_hertz_contact
from core.interference.calculator import calculate_interference_fit
from core.spline.calculator import calculate_spline_fit
from core.worm.calculator import calculate_worm_geometry


PageFactory = Callable[[], Any]
PageMutator = Callable[[Any], None]
PayloadAdjuster = Callable[[Any, dict[str, Any]], dict[str, Any]]
Calculator = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class PageCase:
    name: str
    page_factory: PageFactory
    calculator: Calculator
    mapping_mutators: tuple[PageMutator, ...] = ()
    payload_adjuster: PayloadAdjuster | None = None
    expected_omissions: frozenset[str] = frozenset()


def _identity_payload(_page: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return payload


def _bolt_payload_with_check_level(page: BoltPage, payload: dict[str, Any]) -> dict[str, Any]:
    # BoltPage._calculate() injects check_level after _build_payload(); mirror that
    # contract so the default payload is tested against the same core entry path.
    payload.setdefault("options", {})["check_level"] = page._current_check_level()
    return payload


def _widget(page: Any, field_id: str) -> Any:
    for attr in ("_field_widgets", "_widgets"):
        widgets = getattr(page, attr, {})
        if field_id in widgets:
            return widgets[field_id]
    raise KeyError(f"{type(page).__name__} has no widget for {field_id}")


def _set_field(page: Any, field_id: str, value: str) -> None:
    widget = _widget(page, field_id)
    if isinstance(widget, QComboBox):
        widget.setCurrentText(value)
    elif isinstance(widget, QLineEdit):
        widget.setText(value)
    else:
        raise TypeError(f"Unsupported widget type for {field_id}: {type(widget).__name__}")


def _prepare_interference_shrink_fit(page: InterferenceFitPage) -> None:
    _set_field(page, "assembly.method", "shrink_fit")


def _prepare_interference_force_fit(page: InterferenceFitPage) -> None:
    _set_field(page, "assembly.method", "force_fit")


def _prepare_worm_optional_override(page: WormGearPage) -> None:
    _set_field(page, "advanced.friction_override", "0.08")


def _prepare_spline_combined(page: SplineFitPage) -> None:
    # 默认是"仅花键"，会裁剪 smooth_* 段；切到"联合"后这些 mapped
    # FieldSpec 才属于活跃 core payload。
    _set_field(page, "mode", "联合")


def _prepare_bolt_optional_fields(page: BoltPage) -> None:
    # 刚度字段与柔度字段是二选一输入；默认覆盖柔度，额外场景覆盖刚度。
    _set_field(page, "stiffness.bolt_stiffness", "454545.45")
    _set_field(page, "stiffness.clamped_stiffness", "322580.65")
    _set_field(page, "loads.FM_min_input", "12000")
    _set_field(page, "thread_strip.m_eff", "10.0")
    _set_field(page, "thread_strip.tau_BM", "350.0")
    _set_field(page, "thread_strip.tau_BS", "400.0")


def _prepare_tapped_thread_strip(page: BoltTappedAxialPage) -> None:
    # m_eff 留空时 core 按"未校核"处理；这里填入以证明 mapping 可落点。
    _set_field(page, "thread_strip.m_eff", "10.0")
    _set_field(page, "thread_strip.tau_BM", "350.0")
    _set_field(page, "thread_strip.tau_BS", "400.0")


# BufferEnergyPage 默认 payload 需要曲线 points；无导入/示例曲线时 core
# 输入本来就不完整，因此不纳入这个"默认页面 payload 可被 core 接受"契约。
PAGE_CASES: tuple[PageCase, ...] = (
    PageCase("hertz", HertzContactPage, calculate_hertz_contact),
    PageCase(
        "interference",
        InterferenceFitPage,
        calculate_interference_fit,
        mapping_mutators=(
            _prepare_interference_shrink_fit,
            _prepare_interference_force_fit,
        ),
    ),
    PageCase(
        "worm",
        WormGearPage,
        calculate_worm_geometry,
        mapping_mutators=(_prepare_worm_optional_override,),
    ),
    PageCase(
        "spline",
        SplineFitPage,
        calculate_spline_fit,
        mapping_mutators=(_prepare_spline_combined,),
    ),
    PageCase(
        "bolt",
        BoltPage,
        calculate_vdi2230_core,
        mapping_mutators=(_prepare_bolt_optional_fields,),
        payload_adjuster=_bolt_payload_with_check_level,
    ),
    PageCase(
        "bolt_tapped",
        BoltTappedAxialPage,
        calculate_tapped_axial_joint,
        mapping_mutators=(_prepare_tapped_thread_strip,),
    ),
)


@pytest.fixture(scope="module")
def app() -> QApplication:
    instance = QApplication.instance() or QApplication([])
    return instance


@pytest.fixture(autouse=True)
def no_real_message_box(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_message_box(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("UI contract tests must not open QMessageBox")

    monkeypatch.setattr(QMessageBox, "critical", fail_message_box)
    monkeypatch.setattr(QMessageBox, "warning", fail_message_box)
    monkeypatch.setattr(QMessageBox, "information", fail_message_box)


def _payload_variants(case: PageCase) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for mutator in ((lambda _page: None), *case.mapping_mutators):
        page = case.page_factory()
        mutator(page)
        payloads.append(page._build_payload())
    return payloads


@pytest.mark.parametrize("case", PAGE_CASES, ids=lambda case: case.name)
def test_mapped_fields_land_in_payload(app: QApplication, case: PageCase) -> None:
    page = case.page_factory()
    payloads = _payload_variants(case)

    missing: list[str] = []
    for spec in page._field_specs.values():
        mapping = getattr(spec, "mapping", None)
        if mapping is None:
            continue
        if spec.field_id in case.expected_omissions:
            continue
        section, key = mapping
        if not any(section in payload and key in payload[section] for payload in payloads):
            missing.append(f"{spec.field_id} -> {section}.{key}")

    assert missing == []


@pytest.mark.parametrize("case", PAGE_CASES, ids=lambda case: case.name)
def test_default_payload_accepted_by_core(app: QApplication, case: PageCase) -> None:
    page = case.page_factory()
    payload = page._build_payload()
    adjuster = case.payload_adjuster or _identity_payload
    payload = adjuster(page, payload)

    result = case.calculator(payload)

    assert isinstance(result, dict)
