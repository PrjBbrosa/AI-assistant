"""Shared result view-model for UI pages and PDF/text reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.ui.model_scope import (
    HERTZ_ALLOWABLE_SOURCE_NOTE,
    HERTZ_SCOPE,
    MODEL_LEVEL_REFERENCE,
    SPLINE_SCOPE,
    WORM_SCOPE,
    ModuleScope,
)

CheckStatus = Literal[
    "pass",
    "fail",
    "incomplete",
    "not_checked",
    "reference_only",
]
OverallStatus = Literal["pass", "fail", "incomplete"]

CHECK_STATUS_LABEL_ZH: dict[str, str] = {
    "pass": "通过",
    "fail": "不通过",
    "incomplete": "不完整",
    "not_checked": "未校核",
    "reference_only": "参考项",
}

OVERALL_TITLE_ZH: dict[str, str] = {
    "pass": "校核通过",
    "fail": "校核不通过",
    "incomplete": "校核不完整",
}

HERTZ_CHECK_LABELS: dict[str, str] = {
    "contact_stress_ok": "最大接触应力校核",
}

SPLINE_CHECK_LABELS: dict[str, str] = {
    "flank_ok": "齿面承压校核",
    "slip_ok": "光滑段防滑校核",
    "stress_ok": "光滑段应力校核",
}

WORM_CHECK_LABELS: dict[str, str] = {
    "geometry_consistent": "几何一致性",
    "contact_ok": "齿面接触应力",
    "root_ok": "齿根弯曲应力",
    "fatigue_life": "疲劳寿命",
    "wear_life": "磨损寿命",
}

_SPLINE_OVERALL_TITLE_ZH: dict[str, str] = {
    "pass": "预校核通过",
    "fail": "预校核不通过",
    "incomplete": "预校核不完整",
}

_MODE_ZH = {"line": "线接触", "point": "点接触"}
_SPLINE_MODE_ZH = {
    "spline_only": "仅花键齿面承压",
    "combined": "联合模式 (花键齿面 + 光滑段过盈)",
}
_SPLINE_GEO_MODE_ZH = {
    "approximate": "近似推导",
    "reference_dimensions": "公开/图纸尺寸",
}


@dataclass(frozen=True)
class CheckView:
    id: str
    label_zh: str
    status: CheckStatus
    actual: float | None = None
    limit: float | None = None
    unit: str = ""
    model_level: str = ""
    message: str = ""
    source_kind: str = ""


@dataclass(frozen=True)
class MetricView:
    label: str
    value: str
    unit: str = ""


@dataclass(frozen=True)
class ResultViewModel:
    overall_status: OverallStatus
    title_zh: str
    summary_zh: str
    checks: tuple[CheckView, ...]
    metrics: tuple[MetricView, ...]
    warnings: tuple[str, ...]
    model_scope: ModuleScope
    source_notes: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    verdict_subtitle_zh: str = ""

    @property
    def status_label_zh(self) -> str:
        return status_label_zh(self.overall_status)


def status_label_zh(status: str) -> str:
    """Single source for pass/fail/incomplete/not_checked labels."""
    return CHECK_STATUS_LABEL_ZH.get(status, status)


def overall_title_zh(status: str, model_level: str = "") -> str:
    title = OVERALL_TITLE_ZH.get(status, OVERALL_TITLE_ZH["fail"])
    if model_level:
        return f"{title}（{model_level}）"
    return title


def from_hertz(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the Hertz UI/PDF view model from calculator output."""
    del payload  # inputs are echoed on the result; payload kept for call-site symmetry
    contact = result["contact"]
    derived = result["derived"]
    check = result["check"]
    if not isinstance(contact, dict):
        raise TypeError("contact")
    if not isinstance(derived, dict):
        raise TypeError("derived")
    if not isinstance(check, dict):
        raise TypeError("check")

    overall_status: OverallStatus = (
        "pass" if bool(result.get("overall_pass")) else "fail"
    )
    mode = result.get("mode")
    mode_zh = _MODE_ZH.get(str(mode), str(mode or "-"))
    model_level = HERTZ_SCOPE.model_level
    title = overall_title_zh(overall_status, model_level)
    if overall_status == "pass":
        summary = (
            "该工况满足允许接触应力要求。"
            f"{HERTZ_ALLOWABLE_SOURCE_NOTE}。"
        )
    else:
        summary = (
            "最大接触应力超过允许值，请调整几何/材料/载荷。"
            f"{HERTZ_ALLOWABLE_SOURCE_NOTE}。"
        )

    p0 = contact.get("p0_mpa")
    allowable = check.get("allowable_p0_mpa")
    raw_ok = result.get("checks", {}).get("contact_stress_ok") if isinstance(
        result.get("checks"), dict
    ) else None
    check_status: CheckStatus = "pass" if raw_ok else "fail"
    checks = (
        CheckView(
            id="contact_stress_ok",
            label_zh=HERTZ_CHECK_LABELS["contact_stress_ok"],
            status=check_status,
            actual=_as_float(p0),
            limit=_as_float(allowable),
            unit="MPa",
            model_level=model_level,
            source_kind="user",
        ),
    )

    metrics: list[MetricView] = [
        MetricView("接触模型", mode_zh),
        *_optional_metric("等效弹性模量 E'", derived.get("e_eq_mpa"), "MPa", 1),
        *_optional_metric("等效曲率半径 R'", derived.get("r_eq_mm"), "mm", 4),
    ]
    if mode == "line":
        metrics.extend(
            _optional_metric("接触半宽 b", contact.get("semi_width_mm"), "mm", 4)
        )
    elif mode == "point":
        metrics.extend(
            _optional_metric(
                "接触半径 a", contact.get("contact_radius_mm"), "mm", 4
            )
        )
    else:
        metrics.extend(
            _optional_metric("接触半宽 b", contact.get("semi_width_mm"), "mm", 4)
        )
        metrics.extend(
            _optional_metric(
                "接触半径 a", contact.get("contact_radius_mm"), "mm", 4
            )
        )
    metrics.extend(_optional_metric("最大接触应力 p0", p0, "MPa", 2))
    metrics.extend(
        _optional_metric("平均接触应力 p_mean", contact.get("p_mean_mpa"), "MPa", 2)
    )
    metrics.extend(_optional_metric("许用接触应力 [p0]", allowable, "MPa", 2))
    metrics.extend(
        _optional_metric("安全系数 S", check.get("safety_factor"), "", 3)
    )
    metrics.extend(
        _optional_metric("接触面积 A", contact.get("contact_area_mm2"), "mm²", 4)
    )

    warnings = tuple(
        str(msg) for msg in result.get("warnings", []) if msg is not None
    )
    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=summary,
        checks=checks,
        metrics=tuple(metrics),
        warnings=warnings,
        model_scope=HERTZ_SCOPE,
        source_notes=(HERTZ_ALLOWABLE_SOURCE_NOTE,),
        recommendations=_hertz_recommendations(result),
        verdict_subtitle_zh=f"模型等级: {model_level} | 模型: {mode_zh}",
    )


def from_spline(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the spline UI/PDF view model from calculator output."""
    scenario_a = result.get("scenario_a")
    if not isinstance(scenario_a, dict):
        raise TypeError("scenario_a")
    scenario_b = result.get("scenario_b")
    if scenario_b is not None and not isinstance(scenario_b, dict):
        raise TypeError("scenario_b")

    overall_status: OverallStatus = (
        "pass" if bool(result.get("overall_pass")) else "fail"
    )
    mode = result.get("mode")
    mode_zh = _SPLINE_MODE_ZH.get(str(mode), str(mode or "-"))
    model_level = SPLINE_SCOPE.model_level
    title = _spline_overall_title(overall_status, model_level)
    if overall_status == "pass":
        summary = (
            "该工况满足简化预校核要求。"
            f"{SPLINE_SCOPE.applicability}"
        )
    else:
        summary = (
            "简化预校核不通过，请调整几何、载荷或材料。"
            f"{SPLINE_SCOPE.applicability}"
        )

    checks = (
        _spline_flank_check(scenario_a, model_level),
        *_spline_scenario_b_checks(mode, scenario_b, payload, result, model_level),
    )
    metrics = _spline_metrics(result, scenario_a, scenario_b, mode_zh)
    warnings = tuple(
        str(msg) for msg in result.get("messages", []) if msg is not None
    )
    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=summary,
        checks=checks,
        metrics=metrics,
        warnings=warnings,
        model_scope=SPLINE_SCOPE,
        source_notes=(SPLINE_SCOPE.applicability,),
        recommendations=_spline_recommendations(result),
        verdict_subtitle_zh=f"{mode_zh} | 模型等级: {model_level}",
    )


def _spline_overall_title(status: str, model_level: str = "") -> str:
    title = _SPLINE_OVERALL_TITLE_ZH.get(status, _SPLINE_OVERALL_TITLE_ZH["fail"])
    if model_level:
        return f"{title}（{model_level}）"
    return title


def _spline_input_source(
    payload: dict[str, Any] | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(payload, dict) and payload:
        return payload
    echo = result.get("inputs_echo")
    return echo if isinstance(echo, dict) else {}


def _spline_flank_check(scenario_a: dict[str, Any], model_level: str) -> CheckView:
    status: CheckStatus = "pass" if scenario_a.get("flank_ok") else "fail"
    return CheckView(
        id="flank_ok",
        label_zh=SPLINE_CHECK_LABELS["flank_ok"],
        status=status,
        actual=_as_float(scenario_a.get("flank_safety")),
        limit=_as_float(scenario_a.get("flank_safety_min")),
        unit="",
        model_level=model_level,
        source_kind="user",
    )


def _spline_scenario_b_checks(
    mode: Any,
    scenario_b: dict[str, Any] | None,
    payload: dict[str, Any] | None,
    result: dict[str, Any],
    model_level: str,
) -> tuple[CheckView, CheckView]:
    skipped_message = "仅花键模式，光滑段过盈校核已跳过。"
    combined = mode == "combined" and scenario_b is not None
    if not combined:
        return (
            CheckView(
                id="slip_ok",
                label_zh=SPLINE_CHECK_LABELS["slip_ok"],
                status="not_checked",
                model_level=model_level,
                message=skipped_message,
            ),
            CheckView(
                id="stress_ok",
                label_zh=SPLINE_CHECK_LABELS["stress_ok"],
                status="not_checked",
                model_level=model_level,
                message=skipped_message,
            ),
        )

    assert scenario_b is not None
    b_checks = scenario_b.get("checks")
    if not isinstance(b_checks, dict):
        b_checks = {}
    safety = scenario_b.get("safety")
    if not isinstance(safety, dict):
        safety = {}
    source = _spline_input_source(payload, result)
    source_checks = source.get("checks")
    if not isinstance(source_checks, dict):
        source_checks = {}

    slip_ok = all(
        bool(b_checks.get(key)) for key in ("torque_ok", "axial_ok", "combined_ok")
    )
    stress_ok = all(
        bool(b_checks.get(key)) for key in ("shaft_stress_ok", "hub_stress_ok")
    )
    return (
        CheckView(
            id="slip_ok",
            label_zh=SPLINE_CHECK_LABELS["slip_ok"],
            status="pass" if slip_ok else "fail",
            actual=_as_float(safety.get("slip_safety_min")),
            limit=_as_float(source_checks.get("slip_safety_min")),
            unit="",
            model_level=model_level,
            source_kind="user",
        ),
        CheckView(
            id="stress_ok",
            label_zh=SPLINE_CHECK_LABELS["stress_ok"],
            status="pass" if stress_ok else "fail",
            actual=_as_float(safety.get("stress_safety_min")),
            limit=_as_float(source_checks.get("stress_safety_min")),
            unit="",
            model_level=model_level,
            source_kind="user",
        ),
    )


def _spline_metrics(
    result: dict[str, Any],
    scenario_a: dict[str, Any],
    scenario_b: dict[str, Any] | None,
    mode_zh: str,
) -> tuple[MetricView, ...]:
    geo = scenario_a.get("geometry")
    if not isinstance(geo, dict):
        geo = {}
    loads = result.get("loads")
    if not isinstance(loads, dict):
        loads = {}
    geo_mode = scenario_a.get("geometry_mode", "")
    geo_mode_zh = _SPLINE_GEO_MODE_ZH.get(str(geo_mode), str(geo_mode or "-"))

    metrics: list[MetricView] = [
        MetricView("校核模式", mode_zh),
        MetricView("几何模式", geo_mode_zh),
        *_optional_metric("参考直径 d_B", geo.get("reference_diameter_mm"), "mm", 2),
        *_optional_metric(
            "有效齿高 h_w", geo.get("effective_tooth_height_mm"), "mm", 2
        ),
        *_optional_metric("平均直径 d_m", geo.get("mean_diameter_mm"), "mm", 2),
        *_optional_metric(
            "啮合长度 L", scenario_a.get("engagement_length_mm"), "mm", 2
        ),
        *_optional_metric("载荷分布系数 K_alpha", scenario_a.get("k_alpha"), "", 2),
        *_optional_metric("齿面压力 p", scenario_a.get("flank_pressure_mpa"), "MPa", 2),
        *_optional_metric(
            "许用齿面压力 p_zul", scenario_a.get("p_allowable_mpa"), "MPa", 1
        ),
        *_optional_metric("安全系数 S", scenario_a.get("flank_safety"), "", 2),
        *_optional_metric(
            "扭矩容量 T_cap", scenario_a.get("torque_capacity_nm"), "N*m", 1
        ),
        *_optional_metric("设计扭矩 T_d", loads.get("torque_design_nm"), "N*m", 1),
        *_optional_metric(
            "扭矩容量比 T_cap/T_d", scenario_a.get("torque_capacity_sf"), "", 2
        ),
        *_optional_metric("工况系数 K_A", loads.get("application_factor_ka"), "", 2),
        *_optional_metric("名义扭矩 T", loads.get("torque_required_nm"), "N*m", 1),
    ]
    if scenario_b is None:
        return tuple(metrics)

    pressure = scenario_b.get("pressure_mpa")
    if not isinstance(pressure, dict):
        pressure = {}
    safety = scenario_b.get("safety")
    if not isinstance(safety, dict):
        safety = {}
    metrics.extend(
        _optional_metric(
            "有效配合长度", scenario_b.get("effective_fit_length_mm"), "mm", 1
        )
    )
    metrics.extend(_optional_metric("面压 p_min", pressure.get("p_min"), "MPa", 2))
    metrics.extend(_optional_metric("面压 p_mean", pressure.get("p_mean"), "MPa", 2))
    metrics.extend(_optional_metric("面压 p_max", pressure.get("p_max"), "MPa", 2))
    metrics.extend(_optional_metric("扭矩安全系数", safety.get("torque_sf"), "", 2))
    metrics.extend(_optional_metric("轴向力安全系数", safety.get("axial_sf"), "", 2))
    metrics.extend(_optional_metric("联合安全系数", safety.get("combined_sf"), "", 2))
    metrics.extend(_optional_metric("轴侧安全系数", safety.get("shaft_sf"), "", 2))
    metrics.extend(_optional_metric("轮毂安全系数", safety.get("hub_sf"), "", 2))
    return tuple(metrics)


def _spline_recommendations(result: dict[str, Any]) -> tuple[str, ...]:
    recs: list[str] = []
    scenario_a = result.get("scenario_a")
    if isinstance(scenario_a, dict) and scenario_a.get("flank_ok") is False:
        recs.append(
            "齿面承压安全系数不足：可增大啮合长度、增大齿数或降低设计扭矩。"
        )

    scenario_b = result.get("scenario_b")
    if isinstance(scenario_b, dict):
        checks = scenario_b.get("checks")
        if not isinstance(checks, dict):
            checks = {}
        if checks.get("torque_ok") is False:
            recs.append(
                "光滑段扭矩能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
            )
        if checks.get("axial_ok") is False:
            recs.append(
                "光滑段轴向力能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
            )
        if checks.get("combined_ok") is False:
            recs.append(
                "光滑段联合作用校核不通过：扭矩和轴向力组合超限，需增大过盈量或减小载荷。"
            )
        if checks.get("shaft_stress_ok") is False:
            recs.append(
                "轴侧应力安全系数不足：可更换更高强度的轴材料或减小过盈量。"
            )
        if checks.get("hub_stress_ok") is False:
            recs.append(
                "轮毂应力安全系数不足：可增大轮毂外径、更换更高强度材料或减小过盈量。"
            )

    if not recs:
        recs.append("所有校核均通过，当前设计满足要求。")
    return tuple(recs)


def _hertz_recommendations(result: dict[str, Any]) -> tuple[str, ...]:
    checks = result.get("checks", {}) if isinstance(result.get("checks"), dict) else {}
    check = result.get("check", {}) if isinstance(result.get("check"), dict) else {}
    recs: list[str] = []
    if checks.get("contact_stress_ok") is False:
        recs.append(
            "最大接触应力超过许用值：可增大等效曲率半径、降低法向载荷或提高材料许用接触应力。"
        )
    safety = check.get("safety_factor")
    if isinstance(safety, (int, float)) and not isinstance(safety, bool) and safety < 1.2:
        recs.append("安全系数低于 1.2，建议增加工程裕量并复核疲劳寿命。")
    if not recs:
        recs.append(
            "当前工况满足接触应力校核要求，建议结合疲劳寿命与润滑/表面状态继续复核。"
        )
    return tuple(recs)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_metric(
    label: str,
    value: Any,
    unit: str,
    digits: int,
) -> tuple[MetricView, ...]:
    if isinstance(value, bool) or value is None:
        return ()
    if isinstance(value, (int, float)):
        text = f"{value:.{digits}f}"
    else:
        text = str(value)
    return (MetricView(label=label, value=text, unit=unit),)


def from_worm(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the worm UI/PDF view model from calculator output."""
    del payload  # inputs are echoed on the result; payload kept for call-site symmetry
    geometry = result.get("geometry")
    if not isinstance(geometry, dict):
        raise TypeError("geometry")
    performance = result.get("performance")
    if not isinstance(performance, dict):
        raise TypeError("performance")
    load_capacity = result.get("load_capacity")
    if load_capacity is not None and not isinstance(load_capacity, dict):
        raise TypeError("load_capacity")
    if not isinstance(load_capacity, dict):
        load_capacity = {}

    lc_enabled = bool(load_capacity.get("enabled", False))
    overall_status = _worm_overall_status(result, load_capacity, lc_enabled)
    model_level = WORM_SCOPE.model_level
    title = overall_title_zh(overall_status, model_level)
    lc_status = str(load_capacity.get("status") or "").strip()
    if lc_enabled:
        subtitle = f"Load Capacity | 模型等级: {model_level}"
        if lc_status:
            subtitle = f"{subtitle} | {lc_status}"
    else:
        subtitle = f"Load Capacity 未启用 | 模型等级: {model_level}"

    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=_worm_summary(overall_status),
        checks=_worm_checks(load_capacity, lc_enabled, model_level),
        metrics=_worm_metrics(geometry, performance, load_capacity, lc_enabled),
        warnings=_worm_warnings(geometry, performance, load_capacity),
        model_scope=WORM_SCOPE,
        source_notes=(WORM_SCOPE.applicability,),
        recommendations=_worm_recommendations(load_capacity, lc_enabled, overall_status),
        verdict_subtitle_zh=subtitle,
    )


def _worm_overall_status(
    result: dict[str, Any],
    load_capacity: dict[str, Any],
    lc_enabled: bool,
) -> OverallStatus:
    raw_status = result.get("overall_status")
    if raw_status in ("pass", "fail", "incomplete"):
        return raw_status
    if "overall_pass" in result:
        return "pass" if bool(result.get("overall_pass")) else "fail"
    if not lc_enabled:
        return "incomplete"
    # Missing load-capacity overall_pass must not be inferred from checks.
    return "pass" if bool(load_capacity.get("overall_pass")) else "fail"


def _worm_summary(overall_status: OverallStatus) -> str:
    scope = WORM_SCOPE.applicability
    if overall_status == "pass":
        return (
            "该工况满足 Method B 风格最小负载能力子集要求。"
            "负载能力（Load Capacity）为正式子集，不是完整 DIN 3996 签发。"
            f"{scope}"
        )
    if overall_status == "incomplete":
        return (
            "已完成蜗杆副几何与基础性能；负载能力（Load Capacity）未启用或未校核，总体结论不完整。"
            f"{scope}"
        )
    return (
        "负载能力（Load Capacity）校核不通过，请调整几何、载荷或材料。"
        "负载能力为正式子集，不是完整 DIN 3996 签发。"
        f"{scope}"
    )


def _worm_flag_status(enabled: bool, raw: Any) -> CheckStatus:
    if not enabled:
        return "not_checked"
    return "pass" if raw else "fail"


def _worm_checks(
    load_capacity: dict[str, Any],
    lc_enabled: bool,
    model_level: str,
) -> tuple[CheckView, ...]:
    raw_checks = load_capacity.get("checks")
    if not isinstance(raw_checks, dict):
        raw_checks = {}
    contact = load_capacity.get("contact")
    if not isinstance(contact, dict):
        contact = {}
    root = load_capacity.get("root")
    if not isinstance(root, dict):
        root = {}
    skipped = "负载能力校核：未启用"
    checks: list[CheckView] = [
        CheckView(
            id="geometry_consistent",
            label_zh=WORM_CHECK_LABELS["geometry_consistent"],
            status=_worm_flag_status(lc_enabled, raw_checks.get("geometry_consistent")),
            model_level=model_level,
            message="" if lc_enabled else skipped,
        ),
        CheckView(
            id="contact_ok",
            label_zh=WORM_CHECK_LABELS["contact_ok"],
            status=_worm_flag_status(lc_enabled, raw_checks.get("contact_ok")),
            actual=_as_float(contact.get("sigma_hm_peak_mpa")),
            limit=_as_float(contact.get("allowable_contact_stress_mpa")),
            unit="MPa",
            model_level=model_level,
            message="" if lc_enabled else skipped,
            source_kind="user",
        ),
        CheckView(
            id="root_ok",
            label_zh=WORM_CHECK_LABELS["root_ok"],
            status=_worm_flag_status(lc_enabled, raw_checks.get("root_ok")),
            actual=_as_float(root.get("sigma_f_peak_mpa")),
            limit=_as_float(root.get("allowable_root_stress_mpa")),
            unit="MPa",
            model_level=model_level,
            message="" if lc_enabled else skipped,
            source_kind="user",
        ),
    ]
    checks.extend(_worm_life_checks(load_capacity.get("life")))
    return tuple(checks)


def _worm_life_checks(life: Any) -> tuple[CheckView, ...]:
    if not isinstance(life, dict) or not life:
        return ()
    checks: list[CheckView] = []
    ref_message = "参考项，不参与总体判定。"
    if life.get("fatigue_life_hours") is not None:
        checks.append(
            CheckView(
                id="fatigue_life",
                label_zh=WORM_CHECK_LABELS["fatigue_life"],
                status="reference_only",
                actual=_as_float(life.get("fatigue_life_hours")),
                unit="h",
                model_level=MODEL_LEVEL_REFERENCE,
                message=ref_message,
            )
        )
    if (
        life.get("wear_life_hours_until_0p3mm") is not None
        or life.get("wear_depth_mm_per_hour") is not None
    ):
        checks.append(
            CheckView(
                id="wear_life",
                label_zh=WORM_CHECK_LABELS["wear_life"],
                status="reference_only",
                actual=_as_float(life.get("wear_life_hours_until_0p3mm")),
                unit="h",
                model_level=MODEL_LEVEL_REFERENCE,
                message=ref_message,
            )
        )
    return tuple(checks)


def _worm_metrics(
    geometry: dict[str, Any],
    performance: dict[str, Any],
    load_capacity: dict[str, Any],
    lc_enabled: bool,
) -> tuple[MetricView, ...]:
    worm_dimensions = geometry.get("worm_dimensions")
    if not isinstance(worm_dimensions, dict):
        worm_dimensions = {}
    wheel_dimensions = geometry.get("wheel_dimensions")
    if not isinstance(wheel_dimensions, dict):
        wheel_dimensions = {}
    contact = load_capacity.get("contact")
    if not isinstance(contact, dict):
        contact = {}
    root = load_capacity.get("root")
    if not isinstance(root, dict):
        root = {}
    ripple = load_capacity.get("torque_ripple")
    if not isinstance(ripple, dict):
        ripple = {}
    raw_checks = load_capacity.get("checks")
    if not isinstance(raw_checks, dict):
        raw_checks = {}
    life = load_capacity.get("life")
    if not isinstance(life, dict):
        life = {}

    metrics: list[MetricView] = [
        *_optional_metric("传动比 i", geometry.get("ratio"), "", 3),
        *_optional_metric("中心距 a", geometry.get("center_distance_mm"), "mm", 3),
        *_optional_metric(
            "理论中心距 a_th", geometry.get("theoretical_center_distance_mm"), "mm", 3
        ),
        *_optional_metric(
            "蜗杆分度圆直径 d1", worm_dimensions.get("pitch_diameter_mm"), "mm", 3
        ),
        *_optional_metric(
            "蜗轮分度圆直径 d2", wheel_dimensions.get("pitch_diameter_mm"), "mm", 3
        ),
        *_optional_metric("导程角 gamma", geometry.get("lead_angle_deg"), "deg", 3),
        *_optional_metric("效率估算 eta", performance.get("efficiency_estimate"), "", 4),
        *_optional_metric(
            "输入功率 P1（反算）", performance.get("input_power_kw"), "kW", 4
        ),
        *_optional_metric("输出功率 P2", performance.get("output_power_kw"), "kW", 4),
        *_optional_metric("输出扭矩 T2", performance.get("output_torque_nm"), "N·m", 3),
        *_optional_metric("损失功率", performance.get("power_loss_kw"), "kW", 4),
    ]
    if lc_enabled:
        metrics.extend(
            _optional_metric(
                "齿面接触应力 sigma_H", contact.get("sigma_hm_peak_mpa"), "MPa", 3
            )
        )
        metrics.extend(
            _optional_metric("齿根应力 sigma_F", root.get("sigma_f_peak_mpa"), "MPa", 3)
        )
        metrics.extend(
            _optional_metric(
                "扭矩波动 peak", ripple.get("output_torque_peak_nm"), "N·m", 3
            )
        )
        metrics.extend(
            _optional_metric(
                "sigma_H,nom", contact.get("sigma_hm_nominal_mpa"), "MPa", 3
            )
        )
        metrics.extend(
            _optional_metric(
                "sigma_H,peak", contact.get("sigma_hm_peak_mpa"), "MPa", 3
            )
        )
        metrics.extend(
            _optional_metric("SH_peak", contact.get("safety_factor_peak"), "", 3)
        )
        metrics.extend(
            _optional_metric("sigma_F,nom", root.get("sigma_f_nominal_mpa"), "MPa", 3)
        )
        metrics.extend(
            _optional_metric("sigma_F,peak", root.get("sigma_f_peak_mpa"), "MPa", 3)
        )
        metrics.extend(
            _optional_metric("SF_peak", root.get("safety_factor_peak"), "", 3)
        )
        metrics.extend(
            _optional_metric(
                "T2_nom", ripple.get("output_torque_nominal_nm"), "N·m", 3
            )
        )
        metrics.extend(
            _optional_metric("T2_rms", ripple.get("output_torque_rms_nm"), "N·m", 3)
        )
        metrics.extend(
            _optional_metric("T2_peak", ripple.get("output_torque_peak_nm"), "N·m", 3)
        )
        geo_text = (
            "通过" if raw_checks.get("geometry_consistent") else "存在警告"
        )
        metrics.append(MetricView("几何一致性", geo_text))
    else:
        metrics.extend(
            (
                MetricView("齿面接触应力 sigma_H", "未启用"),
                MetricView("齿根应力 sigma_F", "未启用"),
                MetricView("扭矩波动 peak", "未启用"),
                MetricView("负载能力校核", "未启用"),
            )
        )

    wear_rate = life.get("wear_depth_mm_per_hour")
    metrics.extend(
        _optional_metric("疲劳寿命 (参考项)", life.get("fatigue_life_hours"), "h", 0)
    )
    if isinstance(wear_rate, (int, float)) and not isinstance(wear_rate, bool):
        metrics.extend(
            _optional_metric("磨损速率 (参考项)", wear_rate * 1000.0, "um/h", 3)
        )
    metrics.extend(
        _optional_metric(
            "磨损寿命 (参考项)", life.get("wear_life_hours_until_0p3mm"), "h", 0
        )
    )
    metrics.extend(
        _optional_metric(
            "滑动速度 vs (参考项)", life.get("sliding_velocity_mps"), "m/s", 2
        )
    )
    return tuple(metrics)


def _worm_warnings(
    geometry: dict[str, Any],
    performance: dict[str, Any],
    load_capacity: dict[str, Any],
) -> tuple[str, ...]:
    messages: list[str] = []
    for source in (
        load_capacity.get("warnings"),
        performance.get("warnings"),
    ):
        if isinstance(source, list):
            messages.extend(str(msg) for msg in source if msg is not None)
    consistency = geometry.get("consistency")
    if isinstance(consistency, dict):
        geo_warnings = consistency.get("warnings")
        if isinstance(geo_warnings, list):
            messages.extend(str(msg) for msg in geo_warnings if msg is not None)
    return tuple(messages)


def _worm_recommendations(
    load_capacity: dict[str, Any],
    lc_enabled: bool,
    overall_status: OverallStatus,
) -> tuple[str, ...]:
    if not lc_enabled:
        return (
            "负载能力（Load Capacity）未启用。如需校核齿面/齿根安全系数，请在基本设置中启用。",
        )
    recs: list[str] = []
    raw_checks = load_capacity.get("checks")
    if not isinstance(raw_checks, dict):
        raw_checks = {}
    if raw_checks.get("geometry_consistent") is False:
        recs.append(
            "几何一致性存在警告：请核对导程角与中心距是否与 m、q、z1、z2 自洽。"
        )
    if raw_checks.get("contact_ok") is False:
        recs.append(
            "齿面接触应力不通过：可增大模数/齿宽、降低载荷或提高许用接触应力。"
        )
    if raw_checks.get("root_ok") is False:
        recs.append(
            "齿根弯曲应力不通过：可增大模数、增大齿宽或提高许用齿根应力。"
        )
    if overall_status == "fail" and not recs:
        recs.append(
            "负载能力总体不通过：请按 Method B 最小子集复核几何、许用应力与载荷。"
        )
    if not recs:
        recs.append(
            "当前工况满足 Method B 风格最小负载能力子集；寿命与磨损为参考项，不替代完整 DIN 3996 签发。"
        )
    return tuple(recs)
