"""Shared result view-model for UI pages and PDF/text reports."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from app.ui.model_scope import (
    BOLT_SCOPE,
    BUFFER_SCOPE,
    HERTZ_ALLOWABLE_SOURCE_NOTE,
    HERTZ_SCOPE,
    INTERFERENCE_SCOPE,
    MODEL_LEVEL_REFERENCE,
    SPLINE_SCOPE,
    TAPPED_SCOPE,
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

INTERFERENCE_CHECK_LABELS: dict[str, str] = {
    "torque_ok": "扭矩能力校核（按最小过盈）",
    "axial_ok": "轴向力能力校核（按最小过盈）",
    "combined_ok": "联合作用校核（扭矩 + 轴向）",
    "gaping_ok": "张口缝校核（p_min >= p_r + p_b）",
    "fit_range_ok": "最大过盈端覆盖需求校核",
    "shaft_stress_ok": "轴侧应力安全系数校核（取内孔壁/配合面较大者）",
    "hub_stress_ok": "轮毂应力安全系数校核",
}

INTERFERENCE_SLIP_CHECK_IDS: tuple[str, ...] = (
    "torque_ok",
    "axial_ok",
    "combined_ok",
    "gaping_ok",
    "fit_range_ok",
)
INTERFERENCE_STRESS_CHECK_IDS: tuple[str, ...] = (
    "shaft_stress_ok",
    "hub_stress_ok",
)

TAPPED_CHECK_LABELS: dict[str, str] = {
    "assembly_von_mises_ok": "装配 von Mises 强度",
    "service_von_mises_ok": "服役最大 von Mises 强度",
    "fatigue_ok": "交变轴向疲劳",
    "thread_strip_ok": "螺纹脱扣",
}

BUFFER_CHECK_LABELS: dict[str, str] = {
    "stroke_ok": "行程校核",
    "peak_force_ok": "峰值力校核",
    "energy_capacity_ok": "曲线能量容量校核",
}

BOLT_CHECK_LABELS: dict[str, str] = {
    "assembly_von_mises_ok": "装配等效应力校核（VDI R4）",
    "operating_axial_ok": "服役轴向应力校核（VDI R5）",
    "residual_clamp_ok": "残余夹紧力校核（VDI R3）",
    "additional_load_ok": "附加载荷能力估算 ⚠ 参考",
    "thermal_loss_ok": "温度损失影响校核",
    "fatigue_ok": "疲劳校核（简化 Goodman）",
    "bearing_pressure_ok": "支承面压强校核（R7）",
    "thread_strip_ok": "螺纹脱扣校核",
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
    """Normalized verdict row.

    ``source_kind`` describes the origin of the verdict limit/basis, not the
    calculated ``actual`` value. A limit combined from multiple origins is
    marked ``derived`` and its ingredients are explained in ``source_notes``.
    """

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
        source_notes=(
            SPLINE_SCOPE.applicability,
            "来源追踪：安全系数门槛与工况系数 K_A 来自用户输入；"
            "齿面许用压力可由载荷工况预设自动填充或由用户自定义。",
        ),
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
        source_notes=_worm_source_notes(result, payload, load_capacity),
        recommendations=_worm_recommendations(load_capacity, lc_enabled, overall_status),
        verdict_subtitle_zh=subtitle,
    )


def _worm_overall_status(
    result: dict[str, Any],
    load_capacity: dict[str, Any],
    lc_enabled: bool,
) -> OverallStatus:
    load_capacity_status = load_capacity.get("overall_status")
    if load_capacity_status in ("pass", "fail", "incomplete"):
        return load_capacity_status
    raw_status = result.get("overall_status")
    if raw_status in ("pass", "fail", "incomplete"):
        return raw_status
    if "overall_pass" in result:
        return "pass" if bool(result.get("overall_pass")) else "fail"
    if not lc_enabled:
        return "incomplete"
    # Missing load-capacity overall_pass must not be inferred from checks.
    return "pass" if bool(load_capacity.get("overall_pass")) else "fail"


def _worm_source_notes(
    result: dict[str, Any],
    payload: dict[str, Any] | None,
    load_capacity: dict[str, Any],
) -> tuple[str, ...]:
    source = payload if isinstance(payload, dict) and payload else result.get("inputs_echo")
    if not isinstance(source, dict):
        source = {}
    materials = source.get("materials")
    if not isinstance(materials, dict):
        materials = {}
    advanced = source.get("advanced")
    if not isinstance(advanced, dict):
        advanced = {}
    source_lc = source.get("load_capacity")
    if not isinstance(source_lc, dict):
        source_lc = {}
    contact = load_capacity.get("contact")
    if not isinstance(contact, dict):
        contact = {}
    root = load_capacity.get("root")
    if not isinstance(root, dict):
        root = {}

    allowable_source = "来自显式输入或计算结果回显"
    material_name = materials.get("wheel_material")
    expected_allowables: tuple[float, float] | None = None
    preset_description = f"材料预设 {material_name}"
    try:
        from core.worm.materials import PLASTIC_MATERIALS, apply_derate

        material = PLASTIC_MATERIALS[str(material_name)]
        expected_allowables = apply_derate(
            material,
            operating_temp_c=float(advanced.get("operating_temp_c", 23.0)),
            humidity_rh=float(advanced.get("humidity_rh", 50.0)),
        )
        preset_description = f"材料预设 {material_name}，并按输入温度/湿度派生"
    except (KeyError, TypeError, ValueError):
        try:
            from core.worm.calculator import MATERIAL_ALLOWABLE_HINTS

            material_hint = MATERIAL_ALLOWABLE_HINTS[str(material_name)]
            expected_allowables = (
                float(material_hint["contact_mpa"]),
                float(material_hint["root_mpa"]),
            )
        except (KeyError, TypeError, ValueError):
            expected_allowables = None

    if expected_allowables is not None:
        expected_contact, expected_root = expected_allowables
        actual_contact = _as_float(contact.get("allowable_contact_stress_mpa"))
        actual_root = _as_float(root.get("allowable_root_stress_mpa"))
        matches_material_model = (
            actual_contact is not None
            and actual_root is not None
            and math.isclose(actual_contact, expected_contact, rel_tol=1e-6, abs_tol=0.02)
            and math.isclose(actual_root, expected_root, rel_tol=1e-6, abs_tol=0.02)
        )
        if matches_material_model:
            allowable_source = f"来自{preset_description}"
        elif {
            "allowable_contact_stress_mpa",
            "allowable_root_stress_mpa",
        } & source_lc.keys():
            allowable_source = "来自负载能力参数中的显式覆盖值"
        else:
            allowable_source = "未匹配当前材料温湿度模型，按计算结果回显"
    else:
        if {
            "allowable_contact_stress_mpa",
            "allowable_root_stress_mpa",
        } & source_lc.keys():
            allowable_source = "来自负载能力参数中的显式覆盖值"

    return (
        WORM_SCOPE.applicability,
        f"来源追踪：齿面/齿根许用应力{allowable_source}；目标安全系数与"
        "K_A、Kv、KHalpha、KHbeta 来自用户输入；分项有效应力门槛由"
        "许用应力除以目标安全系数派生。",
    )


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
            "已完成蜗杆副几何与基础性能；负载能力（Load Capacity）未启用、"
            "未校核或材料模型超出可信域，总体结论不完整。"
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
    contact_limit = _effective_stress_limit(
        contact.get("allowable_contact_stress_mpa"),
        contact.get("required_contact_safety"),
    )
    root_limit = _effective_stress_limit(
        root.get("allowable_root_stress_mpa"),
        root.get("required_root_safety"),
    )
    skipped = "负载能力校核：未启用"
    checks: list[CheckView] = [
        CheckView(
            id="geometry_consistent",
            label_zh=WORM_CHECK_LABELS["geometry_consistent"],
            status=_worm_flag_status(lc_enabled, raw_checks.get("geometry_consistent")),
            model_level=model_level,
            message="" if lc_enabled else skipped,
            source_kind="derived",
        ),
        CheckView(
            id="contact_ok",
            label_zh=WORM_CHECK_LABELS["contact_ok"],
            status=_worm_flag_status(lc_enabled, raw_checks.get("contact_ok")),
            actual=_as_float(contact.get("sigma_hm_peak_mpa")),
            limit=contact_limit,
            unit="MPa",
            model_level=model_level,
            message="" if lc_enabled else skipped,
            source_kind="derived",
        ),
        CheckView(
            id="root_ok",
            label_zh=WORM_CHECK_LABELS["root_ok"],
            status=_worm_flag_status(lc_enabled, raw_checks.get("root_ok")),
            actual=_as_float(root.get("sigma_f_peak_mpa")),
            limit=root_limit,
            unit="MPa",
            model_level=model_level,
            message="" if lc_enabled else skipped,
            source_kind="derived",
        ),
    ]
    checks.extend(_worm_life_checks(load_capacity.get("life")))
    return tuple(checks)


def _effective_stress_limit(allowable: Any, required_safety: Any) -> float | None:
    """Return the stress threshold equivalent to ``allowable / S_required``."""
    allowable_value = _as_float(allowable)
    required_value = _as_float(required_safety)
    if allowable_value is None:
        return None
    if required_value is None:
        required_value = 1.0
    if required_value <= 0.0:
        return None
    return allowable_value / required_value


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
                source_kind="reference",
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
                source_kind="reference",
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

_INTERFERENCE_SHAFT_TYPE_ZH = {
    "hollow_shaft": "空心轴",
    "solid_shaft": "实心轴",
}

_INTERFERENCE_CHECK_ACTUAL = {
    "torque_ok": "torque_sf",
    "axial_ok": "axial_sf",
    "combined_ok": "combined_sf",
    "gaping_ok": "gaping_margin_mpa",
    "shaft_stress_ok": "shaft_sf",
    "hub_stress_ok": "hub_sf",
}


def from_interference(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the interference UI/PDF view model from calculator output."""
    checks_raw = result.get("checks")
    if not isinstance(checks_raw, dict):
        raise TypeError("checks")

    overall_status: OverallStatus = (
        "pass" if bool(result.get("overall_pass")) else "fail"
    )
    model = result.get("model")
    if not isinstance(model, dict):
        model = {}
    shaft_type = str(model.get("shaft_type") or "solid_shaft")
    shaft_type_zh = _INTERFERENCE_SHAFT_TYPE_ZH.get(shaft_type, "实心轴")
    model_level = INTERFERENCE_SCOPE.model_level
    title = overall_title_zh(overall_status, model_level)
    if overall_status == "pass":
        summary = (
            "该工况在当前输入范围内满足 DIN 7190 风格核心能力、联合作用、张口缝与应力要求。"
            f"{INTERFERENCE_SCOPE.applicability}"
        )
    else:
        summary = (
            "存在未满足项，请优先查看联合作用、张口缝、需求过盈和应力侧提示。"
            f"{INTERFERENCE_SCOPE.applicability}"
        )

    safety = result.get("safety")
    if not isinstance(safety, dict):
        safety = {}
    source = _interference_input_source(payload, result)
    source_checks = source.get("checks")
    if not isinstance(source_checks, dict):
        source_checks = {}
    source_fit = source.get("fit")
    if not isinstance(source_fit, dict):
        source_fit = {}
    required = result.get("required")
    if not isinstance(required, dict):
        required = {}
    slip_limit = source_checks.get("slip_safety_min", safety.get("slip_safety_min"))
    stress_limit = source_checks.get(
        "stress_safety_min", safety.get("stress_safety_min")
    )
    limit_by_id = {
        "torque_ok": slip_limit,
        "axial_ok": slip_limit,
        "combined_ok": slip_limit,
        "gaping_ok": 0.0,
        "fit_range_ok": required.get("delta_required_um"),
        "shaft_stress_ok": stress_limit,
        "hub_stress_ok": stress_limit,
    }
    actual_by_id = {
        check_id: safety.get(actual_key)
        for check_id, actual_key in _INTERFERENCE_CHECK_ACTUAL.items()
    }
    actual_by_id["fit_range_ok"] = source_fit.get("delta_max_um")
    unit_by_id = {"gaping_ok": "MPa", "fit_range_ok": "um"}
    source_kind_by_id = {
        "torque_ok": "user",
        "axial_ok": "user",
        "combined_ok": "user",
        "gaping_ok": "derived",
        "fit_range_ok": "derived",
        "shaft_stress_ok": "user",
        "hub_stress_ok": "user",
    }

    checks = tuple(
        CheckView(
            id=check_id,
            label_zh=label,
            status="pass" if checks_raw.get(check_id) else "fail",
            actual=_as_float(actual_by_id.get(check_id)),
            limit=_as_float(limit_by_id.get(check_id)),
            unit=unit_by_id.get(check_id, ""),
            model_level=model_level,
            source_kind=source_kind_by_id[check_id],
        )
        for check_id, label in INTERFERENCE_CHECK_LABELS.items()
    )

    warnings = tuple(
        str(msg) for msg in result.get("messages", []) if msg is not None
    )
    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=summary,
        checks=checks,
        metrics=_interference_metrics(result, shaft_type_zh),
        warnings=warnings,
        model_scope=INTERFERENCE_SCOPE,
        source_notes=(
            INTERFERENCE_SCOPE.applicability,
            "来源追踪：防滑/材料安全系数门槛与工况系数 K_A 来自用户输入；"
            "张口缝零裕量门槛及最大过盈覆盖需求由输入载荷、几何和模型派生。",
        ),
        recommendations=_interference_recommendations(result),
        verdict_subtitle_zh=(
            f"模型: 圆柱面过盈配合（{shaft_type_zh}） | 模型等级: {model_level}"
        ),
    )


def _interference_input_source(
    payload: dict[str, Any] | None,
    result: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(payload, dict) and payload:
        return payload
    echo = result.get("inputs_echo")
    return echo if isinstance(echo, dict) else {}


def _interference_metrics(
    result: dict[str, Any],
    shaft_type_zh: str,
) -> tuple[MetricView, ...]:
    derived = result.get("derived")
    if not isinstance(derived, dict):
        derived = {}
    pressure = result.get("pressure_mpa")
    if not isinstance(pressure, dict):
        pressure = {}
    required = result.get("required")
    if not isinstance(required, dict):
        required = {}
    capacity = result.get("capacity")
    if not isinstance(capacity, dict):
        capacity = {}
    assembly = result.get("assembly")
    if not isinstance(assembly, dict):
        assembly = {}
    safety = result.get("safety")
    if not isinstance(safety, dict):
        safety = {}
    stress = result.get("stress_mpa")
    if not isinstance(stress, dict):
        stress = {}
    roughness = result.get("roughness")
    if not isinstance(roughness, dict):
        roughness = {}
    add_p = result.get("additional_pressure_mpa")
    if not isinstance(add_p, dict):
        add_p = {}

    metrics: list[MetricView] = [
        MetricView("几何模型", shaft_type_zh),
        *_optional_metric(
            "轴内径", derived.get("shaft_inner_d_mm"), "mm", 2
        ),
        *_optional_metric("面压 p_min", pressure.get("p_min"), "MPa", 2),
        *_optional_metric("面压 p_mean", pressure.get("p_mean"), "MPa", 2),
        *_optional_metric("面压 p_max", pressure.get("p_max"), "MPa", 2),
        *_optional_metric(
            "需求面压 p_required", required.get("p_required_mpa"), "MPa", 2
        ),
        *_optional_metric(
            "需求面压 p_req,T", required.get("p_required_torque_mpa"), "MPa", 2
        ),
        *_optional_metric(
            "需求面压 p_req,Ax", required.get("p_required_axial_mpa"), "MPa", 2
        ),
        *_optional_metric(
            "需求面压 p_req,comb",
            required.get("p_required_combined_mpa"),
            "MPa",
            2,
        ),
        *_optional_metric("附加面压 p_gap", add_p.get("p_gap"), "MPa", 2),
        *_optional_metric(
            "扭矩容量 T_min", capacity.get("torque_min_nm"), "N*m", 1
        ),
        *_optional_metric(
            "轴向力容量 F_min", capacity.get("axial_min_n"), "N", 0
        ),
        *_optional_metric(
            "压入力 F_press,min", assembly.get("press_force_min_n"), "N", 0
        ),
        *_optional_metric(
            "粗糙度损失 s", roughness.get("subsidence_um"), "um", 2
        ),
        *_optional_metric("扭矩安全系数", safety.get("torque_sf"), "", 2),
        *_optional_metric("轴向力安全系数", safety.get("axial_sf"), "", 2),
        *_optional_metric("联合安全系数", safety.get("combined_sf"), "", 2),
        *_optional_metric("轴侧安全系数", safety.get("shaft_sf"), "", 2),
        *_optional_metric("轮毂安全系数", safety.get("hub_sf"), "", 2),
        *_optional_metric(
            "轴 von Mises max", stress.get("shaft_vm_max"), "MPa", 1
        ),
        *_optional_metric(
            "轮毂 von Mises max", stress.get("hub_vm_max"), "MPa", 1
        ),
    ]
    return tuple(metrics)


def _interference_recommendations(result: dict[str, Any]) -> tuple[str, ...]:
    checks = result.get("checks")
    if not isinstance(checks, dict):
        checks = {}
    recs: list[str] = []
    if checks.get("torque_ok") is False:
        recs.append("扭矩能力不足：可增大过盈量、增大配合长度或提高摩擦系数。")
    if checks.get("axial_ok") is False:
        recs.append(
            "轴向力能力不足：可增大过盈量、增大配合长度或提高摩擦系数。"
        )
    if checks.get("combined_ok") is False:
        recs.append(
            "联合作用校核不通过：扭矩和轴向力组合超限，需增大过盈量或减小载荷。"
        )
    if checks.get("gaping_ok") is False:
        recs.append(
            "张口缝校核不通过：最小面压不足以抵抗弯矩/径向力引起的张开趋势，"
            "需增大最小过盈量。"
        )
    if checks.get("fit_range_ok") is False:
        recs.append(
            "过盈覆盖需求校核不通过：当前最大可用过盈小于载荷所需过盈，"
            "需增大最大可用过盈、增加配合长度/摩擦系数或降低载荷。"
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
        recs.append("所有校核均通过，当前设计满足 DIN 7190 风格核心要求。")
    return tuple(recs)

def from_tapped_axial(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the tapped-axial UI/PDF view model from calculator output."""
    raw_status = result.get("overall_status")
    if raw_status in ("pass", "fail", "incomplete"):
        overall_status: OverallStatus = raw_status
    else:
        overall_status = "pass" if result.get("overall_pass") else "fail"
    model_level = TAPPED_SCOPE.model_level
    title = overall_title_zh(overall_status, model_level)
    if overall_status == "pass":
        summary = "该工况满足全部校核要求。"
    elif overall_status == "incomplete":
        summary = (
            "部分分项尚未校核（常见为螺纹脱扣未填啮合长度）。"
            "请补齐输入后重新计算再给出结论。"
        )
    else:
        summary = "存在不满足校核要求的项目，请查看分项结果与建议。"
    summary = f"{summary}{TAPPED_SCOPE.applicability}"

    checks_raw = result.get("checks")
    if not isinstance(checks_raw, dict):
        checks_raw = {}
    checks = tuple(
        _tapped_check_view(check_id, label, checks_raw.get(check_id), result, model_level)
        for check_id, label in TAPPED_CHECK_LABELS.items()
    )
    metrics = _tapped_metrics(result)
    warnings = tuple(
        str(msg) for msg in result.get("warnings", []) if msg is not None
    )
    recs = result.get("recommendations")
    recommendations = (
        tuple(str(msg) for msg in recs if msg is not None)
        if isinstance(recs, list)
        else ()
    )
    scope_note = result.get("scope_note")
    source_notes = _tapped_source_notes(payload, scope_note)
    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=summary,
        checks=checks,
        metrics=metrics,
        warnings=warnings,
        model_scope=TAPPED_SCOPE,
        source_notes=source_notes,
        recommendations=recommendations,
        verdict_subtitle_zh=f"模型等级: {model_level}",
    )


def from_buffer(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the buffer-energy UI/PDF view model from calculator output."""
    impact = result.get("impact")
    if not isinstance(impact, dict):
        impact = {}
    curve_summary = result.get("curve_summary")
    if not isinstance(curve_summary, dict):
        curve_summary = {}
    checks_raw = result.get("checks")
    if not isinstance(checks_raw, dict):
        checks_raw = {}
    source = payload if isinstance(payload, dict) and payload else result.get("inputs_echo")
    if not isinstance(source, dict):
        source = {}
    impact_input = source.get("impact")
    if not isinstance(impact_input, dict):
        impact_input = {}
    actual_by_id = {
        "stroke_ok": impact.get("max_compression_mm"),
        "peak_force_ok": impact.get("peak_force_n"),
        "energy_capacity_ok": impact.get("initial_energy_j"),
    }
    limit_by_id = {
        "stroke_ok": impact_input.get("available_stroke_mm"),
        "peak_force_ok": impact_input.get("allowable_peak_force_n"),
        "energy_capacity_ok": impact.get("available_energy_capacity_j"),
    }
    unit_by_id = {
        "stroke_ok": "mm",
        "peak_force_ok": "N",
        "energy_capacity_ok": "J",
    }
    source_kind_by_id = {
        "stroke_ok": "user",
        "peak_force_ok": "user",
        "energy_capacity_ok": "derived",
    }
    overall_status: OverallStatus = (
        "pass" if bool(result.get("overall_pass")) else "fail"
    )
    model_level = BUFFER_SCOPE.model_level
    title = overall_title_zh(overall_status, model_level)
    bottom_out = bool(impact.get("bottom_out"))
    if overall_status == "pass":
        summary = "当前工况满足行程、峰值力和曲线能量容量校核。"
    elif bottom_out:
        summary = (
            "触底 / 峰值未知，当前曲线不能外推触底刚化峰值。整体按不通过处理。"
        )
    else:
        summary = "存在不满足校核要求的项目，请调整行程、刚度和冲击能量。"
    summary = f"{summary}{BUFFER_SCOPE.applicability}"

    checks = tuple(
        CheckView(
            id=check_id,
            label_zh=label,
            status=_check_status_from_raw(checks_raw.get(check_id)),
            actual=_as_float(actual_by_id.get(check_id)),
            limit=_as_float(limit_by_id.get(check_id)),
            unit=unit_by_id[check_id],
            model_level=model_level,
            message=(
                "触底，不可判定"
                if check_id == "peak_force_ok" and checks_raw.get(check_id) is None
                else ""
            ),
            source_kind=source_kind_by_id[check_id],
        )
        for check_id, label in BUFFER_CHECK_LABELS.items()
    )
    metrics = _buffer_metrics(impact, curve_summary, result)
    warnings = tuple(
        str(msg) for msg in result.get("warnings", []) if msg is not None
    )
    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=summary,
        checks=checks,
        metrics=metrics,
        warnings=warnings,
        model_scope=BUFFER_SCOPE,
        source_notes=(
            BUFFER_SCOPE.applicability,
            "来源追踪：可用行程与允许峰值力来自用户输入；能量容量门槛由"
            "导入测试曲线和有效行程派生。",
        ),
        recommendations=_buffer_recommendations(result, impact, checks_raw),
        verdict_subtitle_zh=_buffer_verdict_subtitle(model_level, bottom_out),
    )


def _check_status_from_raw(value: Any) -> CheckStatus:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "not_checked"


def _tapped_source_notes(
    payload: dict[str, Any] | None,
    scope_note: Any,
) -> tuple[str, ...]:
    scope = str(scope_note) if scope_note else TAPPED_SCOPE.applicability
    fastener = payload.get("fastener") if isinstance(payload, dict) else None
    if not isinstance(fastener, dict):
        fastener = {}
    grade = fastener.get("grade")
    rp02_source = (
        f"预设强度等级 {grade}"
        if isinstance(grade, str) and grade and grade != "自定义"
        else "用户输入"
    )
    return (
        scope,
        f"来源追踪：Rp0.2 来自{rp02_source}；装配、服役和疲劳许用值由 "
        "Rp0.2、用户安全门槛/利用系数及模型公式派生；"
        "螺纹脱扣目标安全系数来自用户输入。",
    )


def _tapped_check_view(
    check_id: str,
    label: str,
    raw: Any,
    result: dict[str, Any],
    model_level: str,
) -> CheckView:
    stresses = result.get("stresses_mpa")
    if not isinstance(stresses, dict):
        stresses = {}
    fatigue = result.get("fatigue")
    if not isinstance(fatigue, dict):
        fatigue = {}
    trace = result.get("trace")
    intermediate = (
        trace.get("intermediate") if isinstance(trace, dict) else None
    )
    if not isinstance(intermediate, dict):
        intermediate = {}
    thread_strip = result.get("thread_strip")
    if not isinstance(thread_strip, dict):
        thread_strip = {}

    actual: float | None = None
    limit: float | None = None
    unit = ""
    if check_id == "assembly_von_mises_ok":
        actual = _as_float(stresses.get("sigma_vm_assembly"))
        limit = _as_float(intermediate.get("sigma_allow_assembly"))
        unit = "MPa"
    elif check_id == "service_von_mises_ok":
        actual = _as_float(stresses.get("sigma_vm_service_max"))
        limit = _as_float(intermediate.get("sigma_allow_service"))
        unit = "MPa"
    elif check_id == "fatigue_ok":
        actual = _as_float(stresses.get("sigma_a_fatigue"))
        limit = _as_float(fatigue.get("sigma_a_allow"))
        unit = "MPa"
    elif check_id == "thread_strip_ok":
        actual = _as_float(thread_strip.get("strip_safety"))
        limit = _as_float(thread_strip.get("strip_safety_required"))
    message = ""
    if check_id == "thread_strip_ok" and raw is None:
        message = str(thread_strip.get("note") or "未提供 m_eff，未执行螺纹脱扣校核。")
    source_kind_by_id = {
        "assembly_von_mises_ok": "derived",
        "service_von_mises_ok": "derived",
        "fatigue_ok": "derived",
        "thread_strip_ok": "user",
    }
    return CheckView(
        id=check_id,
        label_zh=label,
        status=_check_status_from_raw(raw),
        actual=actual,
        limit=limit,
        unit=unit,
        model_level=model_level,
        message=message,
        source_kind=source_kind_by_id[check_id],
    )


def _tapped_metrics(result: dict[str, Any]) -> tuple[MetricView, ...]:
    assembly = result.get("assembly")
    if not isinstance(assembly, dict):
        assembly = {}
    stresses = result.get("stresses_mpa")
    if not isinstance(stresses, dict):
        stresses = {}
    fatigue = result.get("fatigue")
    if not isinstance(fatigue, dict):
        fatigue = {}
    trace = result.get("trace")
    intermediate = (
        trace.get("intermediate") if isinstance(trace, dict) else None
    )
    if not isinstance(intermediate, dict):
        intermediate = {}
    thread_strip = result.get("thread_strip")
    if not isinstance(thread_strip, dict):
        thread_strip = {}

    f_min = assembly.get("F_preload_min_N", 0)
    if f_min is None:
        raise TypeError("assembly.F_preload_min_N")
    f_max = assembly.get("F_preload_max_N", 0)
    ma_min = assembly.get("MA_min_Nm", 0)
    ma_max = assembly.get("MA_max_Nm", 0)
    metrics: list[MetricView] = [
        MetricView(
            "预紧力范围",
            f"F_min = {_fmt_metric(f_min, 0)} N  /  F_max = {_fmt_metric(f_max, 0)} N",
        ),
        MetricView(
            "装配扭矩范围",
            f"MA_min = {_fmt_metric(ma_min, 2)} N·m"
            f"  /  MA_max = {_fmt_metric(ma_max, 2)} N·m",
        ),
        MetricView(
            "装配 von Mises",
            f"sigma_vm = {_fmt_metric(stresses.get('sigma_vm_assembly', 0), 1)} MPa"
            f"  (许用: {_fmt_metric(intermediate.get('sigma_allow_assembly', 0), 1)} MPa)",
        ),
        MetricView(
            "服役最大 von Mises",
            f"sigma_vm = {_fmt_metric(stresses.get('sigma_vm_service_max', 0), 1)} MPa"
            f"  (许用: {_fmt_metric(intermediate.get('sigma_allow_service', 0), 1)} MPa)",
        ),
        MetricView(
            "疲劳应力幅",
            f"sigma_a = {_fmt_metric(stresses.get('sigma_a_fatigue', 0), 2)} MPa"
            f"  (许用: {_fmt_metric(fatigue.get('sigma_a_allow', 0), 2)} MPa)",
        ),
        MetricView(
            "疲劳平均应力",
            f"sigma_m = {_fmt_metric(stresses.get('sigma_m_fatigue', 0), 1)} MPa",
        ),
        MetricView(
            "Goodman 折减系数",
            _fmt_metric(fatigue.get("goodman_factor", 0), 3),
        ),
    ]
    if thread_strip.get("active"):
        metrics.append(
            MetricView(
                "螺纹脱扣安全系数",
                f"S = {_fmt_metric(thread_strip.get('strip_safety', 0), 2)}"
                f"  (要求: >= {_fmt_metric(thread_strip.get('strip_safety_required', 0), 2)})",
            )
        )
        note = thread_strip.get("note")
        if note:
            metrics.append(MetricView("临界侧", str(note)))
    else:
        metrics.append(
            MetricView("螺纹脱扣", str(thread_strip.get("note", "")))
        )
    return tuple(metrics)


def _buffer_metrics(
    impact: dict[str, Any],
    curve_summary: dict[str, Any],
    result: dict[str, Any],
) -> tuple[MetricView, ...]:
    response = result.get("time_response")
    if not isinstance(response, dict):
        response = {}
    peak = impact.get("peak_force_n")
    if peak is None:
        peak_metric = MetricView("峰值输出力", "触底，未知")
    else:
        peak_metric = MetricView("峰值输出力", _fmt_metric(peak, 1), "N")
    duration_s = response.get("duration_s", 0.0)
    try:
        duration_ms = float(duration_s) * 1000.0
    except (TypeError, ValueError):
        duration_ms = 0.0
    metrics: list[MetricView] = [
        *_optional_metric("初始动能", impact.get("initial_energy_j"), "J", 3),
        *_optional_metric("可用吸能容量", impact.get("available_energy_capacity_j"), "J", 3),
        *_optional_metric("有效行程", impact.get("effective_stroke_mm"), "mm", 3),
        *_optional_metric("最大压缩", impact.get("max_compression_mm"), "mm", 3),
        peak_metric,
        *_optional_metric("平均反力", impact.get("average_force_n"), "N", 1),
        *_optional_metric("吸收能量", impact.get("absorbed_energy_j"), "J", 3),
        *_optional_metric(
            "工况耗散能量", impact.get("impact_dissipated_energy_j"), "J", 3
        ),
        *_optional_metric("回弹能量", impact.get("rebound_energy_j"), "J", 3),
        *_optional_metric(
            "估算回弹速度", impact.get("estimated_rebound_velocity_m_s"), "m/s", 3
        ),
        MetricView("接触时长", f"{duration_ms:.2f}", "ms"),
        MetricView("是否触底", "是" if impact.get("bottom_out") else "否"),
        *_optional_metric("测试曲线最大行程", curve_summary.get("max_stroke_mm"), "mm", 2),
        *_optional_metric(
            "测试曲线峰值力", curve_summary.get("peak_loading_force_n"), "N", 1
        ),
        *_optional_metric("加载能量", curve_summary.get("loading_energy_j"), "J", 3),
        *_optional_metric("卸载能量", curve_summary.get("unloading_energy_j"), "J", 3),
        *_optional_metric(
            "测试曲线滞回能量", curve_summary.get("curve_hysteresis_energy_j"), "J", 3
        ),
    ]
    ratio = curve_summary.get("energy_absorption_ratio")
    if isinstance(ratio, (int, float)) and not isinstance(ratio, bool):
        metrics.append(MetricView("吸能比例", f"{float(ratio) * 100.0:.1f}", "%"))
    metrics.extend(
        _optional_metric(
            "等效刚度", curve_summary.get("equivalent_stiffness_n_per_mm"), "N/mm", 1
        )
    )
    return tuple(metrics)


def _buffer_recommendations(
    result: dict[str, Any],
    impact: dict[str, Any],
    checks: dict[str, Any],
) -> tuple[str, ...]:
    recs: list[str] = []
    if impact.get("bottom_out") or checks.get("energy_capacity_ok") is False:
        recs.append(
            "输入动能超过可用行程内吸能容量：需增大可用行程、换用更高容量缓冲块或降低冲击能量。"
        )
    if checks.get("peak_force_ok") is False:
        recs.append(
            "峰值力超过允许值：需降低缓冲块刚度峰值、增大行程或提高安装结构承载能力。"
        )
    if checks.get("stroke_ok") is False:
        recs.append(
            "最大压缩量超过可用行程：需增加机械行程或选择更短压缩量方案。"
        )
    if not recs:
        recs.append("当前工况满足行程、峰值力和曲线能量容量校核。")
    return tuple(recs)


def _buffer_verdict_subtitle(model_level: str, bottom_out: bool) -> str:
    subtitle = f"模型等级: {model_level} | 单次冲击能量法"
    if bottom_out:
        subtitle += " - 触底 / 峰值未知"
    return subtitle


def _fmt_metric(value: Any, digits: int) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return str(value)
    return f"{float(value):.{digits}f}"

def from_bolt(
    result: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> ResultViewModel:
    """Build the VDI 2230 bolt UI/PDF view model from calculator output."""
    del payload  # inputs are echoed on the result; payload kept for call-site symmetry
    checks_raw = result.get("checks")
    if not isinstance(checks_raw, dict):
        checks_raw = {}
    refs = result.get("references")
    if not isinstance(refs, dict):
        refs = {}

    raw_overall = result.get("overall_status")
    overall_status: OverallStatus
    if raw_overall in ("pass", "fail", "incomplete"):
        overall_status = raw_overall  # type: ignore[assignment]
    else:
        overall_status = "pass" if result.get("overall_pass") else "fail"

    model_level = BOLT_SCOPE.model_level
    title = overall_title_zh(overall_status, model_level)
    if overall_status == "pass":
        summary = "该工况满足当前模型下全部分项要求。"
    elif overall_status == "incomplete":
        summary = (
            "无分项不通过，但存在未校核项（见'未校核'徽章与警告），"
            "请补充输入后重新校核。"
        )
    else:
        summary = "该工况存在未满足项，请查看下方分项状态与调整建议。"

    calc_mode = str(result.get("calculation_mode", "design"))
    joint_type = str(result.get("joint_type", "tapped"))
    check_level = str(result.get("check_level", "basic"))
    joint_zh = "螺纹孔连接" if joint_type == "tapped" else "通孔螺栓连接"
    mode_zh = "设计模式" if calc_mode == "design" else "校核模式"
    checks = (
        _bolt_check(
            "assembly_von_mises_ok",
            checks_raw,
            model_level,
        ),
        _bolt_check(
            "operating_axial_ok",
            checks_raw,
            model_level,
        ),
        _bolt_residual_check(checks_raw, calc_mode, model_level),
        _bolt_additional_load_check(refs, model_level),
        _bolt_check("thermal_loss_ok", checks_raw, model_level),
        _bolt_check("fatigue_ok", checks_raw, model_level),
        _bolt_check("bearing_pressure_ok", checks_raw, model_level),
        _bolt_check("thread_strip_ok", checks_raw, model_level),
    )
    metrics = _bolt_metrics(result)
    warnings = tuple(
        str(msg) for msg in result.get("warnings", []) if msg is not None
    )
    return ResultViewModel(
        overall_status=overall_status,
        title_zh=title,
        summary_zh=summary,
        checks=checks,
        metrics=metrics,
        warnings=warnings,
        model_scope=BOLT_SCOPE,
        source_notes=(BOLT_SCOPE.applicability,),
        recommendations=_bolt_recommendations(result),
        verdict_subtitle_zh=(
            f"{mode_zh} | {joint_zh} | 层级: {check_level} | 模型等级: {model_level}"
        ),
    )


def _bolt_check(
    check_id: str,
    checks_raw: dict[str, Any],
    model_level: str,
    *,
    message: str = "",
) -> CheckView:
    label = BOLT_CHECK_LABELS[check_id]
    if check_id not in checks_raw:
        return CheckView(
            id=check_id,
            label_zh=label,
            status="not_checked",
            model_level=model_level,
            message=message or "未校核",
        )
    status: CheckStatus = "pass" if checks_raw.get(check_id) else "fail"
    return CheckView(
        id=check_id,
        label_zh=label,
        status=status,
        model_level=model_level,
        message=status_label_zh(status) if not message else message,
    )


def _bolt_residual_check(
    checks_raw: dict[str, Any],
    calc_mode: str,
    model_level: str,
) -> CheckView:
    if calc_mode == "design" and checks_raw.get("residual_clamp_ok"):
        return CheckView(
            id="residual_clamp_ok",
            label_zh=BOLT_CHECK_LABELS["residual_clamp_ok"],
            status="pass",
            model_level=model_level,
            message="通过（设计模式自动满足）",
        )
    return _bolt_check("residual_clamp_ok", checks_raw, model_level)


def _bolt_additional_load_check(
    refs: dict[str, Any],
    model_level: str,
) -> CheckView:
    ref_pass = bool(refs.get("additional_load_ok", True))
    return CheckView(
        id="additional_load_ok",
        label_zh=BOLT_CHECK_LABELS["additional_load_ok"],
        status="reference_only",
        model_level=model_level,
        message="通过" if ref_pass else "超限（仅参考）",
        source_kind="reference",
    )


def _bolt_metrics(result: dict[str, Any]) -> tuple[MetricView, ...]:
    inter = result.get("intermediate")
    if not isinstance(inter, dict):
        inter = {}
    torque = result.get("torque")
    if not isinstance(torque, dict):
        torque = {}
    forces = result.get("forces")
    if not isinstance(forces, dict):
        forces = {}
    stresses = result.get("stresses_mpa")
    if not isinstance(stresses, dict):
        stresses = {}
    refs = result.get("references")
    if not isinstance(refs, dict):
        refs = {}
    metrics: list[MetricView] = [
        *_optional_metric("FMmin", inter.get("FMmin_N"), "N", 2),
        *_optional_metric("FMmax", inter.get("FMmax_N"), "N", 2),
        *_optional_metric("MAmin", torque.get("MA_min_Nm"), "N·m", 3),
        *_optional_metric("MAmax", torque.get("MA_max_Nm"), "N·m", 3),
        *_optional_metric("FK_residual", forces.get("F_K_residual_N"), "N", 2),
        *_optional_metric("FK_required", inter.get("F_K_required_N"), "N", 2),
        *_optional_metric("FA_perm", refs.get("FA_perm_N"), "N", 2),
        *_optional_metric(
            "sigma_vm_assembly", stresses.get("sigma_vm_assembly"), "MPa", 2
        ),
        *_optional_metric("sigma_vm_work", stresses.get("sigma_vm_work"), "MPa", 2),
    ]
    return tuple(metrics)


def _bolt_recommendations(result: dict[str, Any]) -> tuple[str, ...]:
    checks = result.get("checks")
    if not isinstance(checks, dict):
        checks = {}
    recs: list[str] = []
    if not checks.get("assembly_von_mises_ok", True):
        recs.append(
            "[建议] 装配应力超限：可提高螺栓等级、降低目标预紧力散差(αA)、或优化摩擦控制。"
        )
    if not checks.get("operating_axial_ok", True):
        recs.append("[建议] 服役应力超限：可增大规格 d、提高强度等级、或降低外载 FA。")
    if not checks.get("residual_clamp_ok", True):
        recs.append("[建议] 残余夹紧力不足：可提高 FMmin、减小嵌入损失、或增加摩擦面能力。")
    refs = result.get("references")
    if not isinstance(refs, dict):
        refs = {}
    if not refs.get("additional_load_ok", True):
        recs.append("[参考] 附加载荷超限（参考估算）：可提高 As、降低 n 或减少轴向外载。")
    if "thermal_loss_ok" in checks and not checks.get("thermal_loss_ok", True):
        recs.append("[建议] 热损失偏大：可补偿预紧力、优化材料热匹配或降低温差。")
    if "fatigue_ok" in checks and not checks.get("fatigue_ok", True):
        recs.append("[建议] 疲劳不通过：可降低应力幅、提高螺栓等级、优化载荷谱或增大规格。")
    if "bearing_pressure_ok" in checks and not checks.get("bearing_pressure_ok", True):
        recs.append(
            "[建议] 支承面压强不通过：可增大支承直径、加垫圈、降低预紧力或提高支承面材料许用压强。"
        )
    if "thread_strip_ok" in checks and not checks.get("thread_strip_ok", True):
        strip = result.get("thread_strip")
        if not isinstance(strip, dict):
            strip = {}
        side = strip.get("critical_side", "")
        if side == "nut":
            recs.append(
                "[建议] 螺纹脱扣不通过（壳体侧）：可加深旋合深度、换用更高强度壳体材料、或加大螺栓规格。"
            )
        else:
            recs.append("[建议] 螺纹脱扣不通过（螺栓侧）：可加深旋合深度或提高螺栓强度等级。")
    not_checked = result.get("not_checked", [])
    if not recs and not_checked:
        recs.append("[建议] 当前结论不完整：请补充 " + "、".join(not_checked) + " 后重新校核。")
    if not recs:
        recs.append("[建议] 当前工况满足全部校核。建议保留 10% 以上工程裕量。")
    return tuple(recs)
