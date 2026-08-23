"""Shared result view-model for UI pages and PDF/text reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.ui.model_scope import (
    HERTZ_ALLOWABLE_SOURCE_NOTE,
    HERTZ_SCOPE,
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

_MODE_ZH = {"line": "线接触", "point": "点接触"}


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
