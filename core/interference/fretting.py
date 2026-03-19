"""Rule-based fretting risk assessment for interference fits."""

from __future__ import annotations

from typing import Any


_LOAD_SPECTRUM_SCORES = {
    "steady": 0.0,
    "pulsating": 1.0,
    "reversing": 2.0,
}
_DUTY_SEVERITY_SCORES = {
    "light": 0.0,
    "medium": 1.0,
    "heavy": 2.0,
}
_SURFACE_CONDITION_SCORES = {
    "coated": 0.0,
    "oiled": 1.0,
    "dry": 2.0,
}
_IMPORTANCE_LEVEL_SCORES = {
    "general": 0.0,
    "important": 1.0,
    "critical": 2.0,
}
_MAX_SCORE = 14.0


def _normalized_choice(raw: Any, default: str, allowed: dict[str, float] | None = None) -> str:
    value = str(raw if raw is not None else default).strip().lower() or default
    if allowed is not None and value not in allowed:
        return default
    return value


def _risk_level_from_score(score: float) -> str:
    if score <= 3.0:
        return "low"
    if score <= 8.0:
        return "medium"
    return "high"


def _append_driver(drivers: list[dict[str, str]], key: str, label: str, severity: str, detail: str) -> None:
    drivers.append(
        {
            "key": key,
            "label": label,
            "severity": severity,
            "detail": detail,
        }
    )


def _slip_reserve_score(value: float | None) -> tuple[float, str | None]:
    if value is None:
        return 0.0, None
    if value <= 1.2:
        return 3.0, "high"
    if value <= 1.5:
        return 2.0, "medium"
    if value <= 2.0:
        return 1.0, "low"
    return 0.0, None


def assess_fretting_risk(
    fretting_input: dict[str, Any] | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Assess fretting risk for the simplified interference-fit model."""
    fretting = fretting_input or {}
    mode = _normalized_choice(fretting.get("mode"), "off")
    enabled = mode == "on"
    if not enabled:
        return {
            "enabled": False,
            "applicable": False,
            "risk_level": "not_applicable",
            "risk_score": 0.0,
            "max_score": _MAX_SCORE,
            "drivers": [],
            "recommendations": [],
            "confidence": "low",
            "notes": ["disabled"],
        }

    length_ratio = float(context.get("length_ratio_l_over_d", 0.0))
    modulus_ratio = float(context.get("modulus_ratio", 1.0))
    has_bending = bool(context.get("has_bending", False))
    has_hollow_shaft = bool(context.get("has_hollow_shaft", False))
    notes: list[str] = []
    if length_ratio <= 0.25:
        notes.append("not applicable: LF/DF must be greater than 0.25.")
    if has_hollow_shaft:
        notes.append("not applicable: simplified repeated-load/fretting estimate assumes a solid shaft, not a hollow shaft.")
    if modulus_ratio > 0.05:
        notes.append("not applicable: repeated-load estimate assumes similar elastic modulus.")
    if has_bending:
        notes.append("not applicable: rotating bending is excluded from the simplified estimate.")
    if notes:
        return {
            "enabled": True,
            "applicable": False,
            "risk_level": "not_applicable",
            "risk_score": 0.0,
            "max_score": _MAX_SCORE,
            "drivers": [],
            "recommendations": [
                "当前简化 Step 5 方法不适用于该工况，建议结合更完整模型或试验评估微动腐蚀风险。"
            ],
            "confidence": "low",
            "notes": notes,
        }

    load_spectrum = _normalized_choice(
        fretting.get("load_spectrum"),
        "pulsating",
        _LOAD_SPECTRUM_SCORES,
    )
    duty_severity = _normalized_choice(
        fretting.get("duty_severity"),
        "medium",
        _DUTY_SEVERITY_SCORES,
    )
    surface_condition = _normalized_choice(
        fretting.get("surface_condition"),
        "dry",
        _SURFACE_CONDITION_SCORES,
    )
    importance_level = _normalized_choice(
        fretting.get("importance_level"),
        "important",
        _IMPORTANCE_LEVEL_SCORES,
    )

    torque_sf = context.get("torque_sf")
    combined_sf = context.get("combined_sf")
    torque_sf_val = None if torque_sf is None else float(torque_sf)
    combined_sf_val = None if combined_sf is None else float(combined_sf)

    drivers: list[dict[str, str]] = []
    recommendations: list[str] = []
    score = 0.0

    torque_score, torque_severity = _slip_reserve_score(torque_sf_val)
    score += torque_score
    if torque_severity is not None:
        _append_driver(
            drivers,
            "torque_reserve",
            "扭矩储备",
            torque_severity,
            f"当前 S_torque={torque_sf_val:.2f}，循环微滑移风险偏高。",
        )
        recommendations.append("优先提高最小过盈或配合长度，增加周向防滑储备。")

    combined_score, combined_severity = _slip_reserve_score(combined_sf_val)
    score += combined_score
    if combined_severity is not None:
        _append_driver(
            drivers,
            "combined_reserve",
            "联合作用储备",
            combined_severity,
            f"当前 S_comb={combined_sf_val:.2f}，扭矩与轴向共同作用下的微动风险升高。",
        )
        recommendations.append("降低联合作用幅值，避免只看单项通过而忽略共同载荷。")

    score += _LOAD_SPECTRUM_SCORES[load_spectrum]
    if load_spectrum != "steady":
        severity = "medium" if load_spectrum == "pulsating" else "high"
        _append_driver(
            drivers,
            "load_spectrum",
            "载荷谱",
            severity,
            f"载荷谱为 {load_spectrum}，相较 steady 更易触发接触界面微滑移。",
        )
        recommendations.append("若可能，降低扭矩波动幅值或避免反向循环载荷。")

    score += _DUTY_SEVERITY_SCORES[duty_severity]
    if duty_severity != "light":
        severity = "medium" if duty_severity == "medium" else "high"
        _append_driver(
            drivers,
            "duty_severity",
            "工况严酷度",
            severity,
            f"当前 duty={duty_severity}，接触副在循环载荷下更容易形成 fretting 条件。",
        )

    score += _SURFACE_CONDITION_SCORES[surface_condition]
    if surface_condition != "coated":
        severity = "medium" if surface_condition == "oiled" else "high"
        _append_driver(
            drivers,
            "surface_condition",
            "表面状态",
            severity,
            f"当前表面状态为 {surface_condition}，界面保护能力有限。",
        )
        recommendations.append("改善表面状态，可考虑润滑或防微动腐蚀涂层。")

    score += _IMPORTANCE_LEVEL_SCORES[importance_level]
    if importance_level != "general":
        severity = "medium" if importance_level == "important" else "high"
        _append_driver(
            drivers,
            "importance_level",
            "部件重要度",
            severity,
            f"当前部件等级为 {importance_level}，建议采用更保守的 fretting 风险判断。",
        )

    risk_level = _risk_level_from_score(score)
    confidence = "high" if modulus_ratio <= 0.02 else "medium"
    notes.append("Applicable: simplified Step 5 fretting assessment based on repeated-load reserve and categorical modifiers.")
    if not recommendations:
        recommendations.append("当前 fretting 风险较低，建议保持现有过盈与表面工艺，并继续监控服役工况。")

    return {
        "enabled": True,
        "applicable": True,
        "risk_level": risk_level,
        "risk_score": score,
        "max_score": _MAX_SCORE,
        "drivers": drivers,
        "recommendations": list(dict.fromkeys(recommendations)),
        "confidence": confidence,
        "notes": notes,
    }
