"""Shared validation and ISO thread-section helpers for bolt calculators."""

from __future__ import annotations

import math
from typing import Any


class InputError(ValueError):
    """Raised when input data is incomplete or physically invalid."""


def to_float(value: Any, name: str) -> float:
    """Parse a finite float and normalize validation errors to Chinese InputError."""
    if isinstance(value, bool):
        raise InputError(f"{name} 必须为有限数字，当前值: {value}")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{name} 必须为数字，当前值: {value}") from exc
    if not math.isfinite(parsed):
        raise InputError(f"{name} 必须为有限数字，当前值: {value}")
    return parsed


THREAD_SECTION_TOLERANCE = 0.01


def derive_thread_section(d: float, p: float) -> dict[str, float]:
    """ISO metric thread section from nominal diameter d and pitch p.

    References:
        DIN 13-1 / ISO 724 for metric thread geometry.
        ISO 898-1:2013, Sec 9.1.6 for stress cross-section formula.
    """
    return {
        "As": math.pi / 4.0 * (d - 0.9382 * p) ** 2,
        "d2": d - 0.64952 * p,
        "d3": d - 1.22687 * p,
    }


def check_thread_section_consistency(
    d: float,
    p: float,
    fastener: dict[str, Any],
) -> dict[str, float]:
    """Return d/p-derived As/d2/d3 after validating optional user values.

    用户提供 As/d2/d3 时仅做一致性校验；计算始终采用 d/p 派生值。
    Ref: 2026-07-02 review-fix spec D2.
    """
    derived = derive_thread_section(d, p)
    for key in ("As", "d2", "d3"):
        raw = fastener.get(key)
        if raw in (None, ""):
            continue
        user_value = to_float(raw, f"fastener.{key}")
        derived_value = derived[key]
        if derived_value <= 0:
            raise InputError(
                f"fastener.{key} 由 d={d}, p={p} 派生的值 {derived_value} 非正，"
                "请复核 d 与 p。"
            )
        rel_dev = abs(user_value - derived_value) / derived_value
        if rel_dev > THREAD_SECTION_TOLERANCE:
            raise InputError(
                f"fastener.{key}={user_value} 与由 d={d}, p={p} 派生的 "
                f"{derived_value:.4f} 不一致（相对偏差 {rel_dev * 100:.1f}% > "
                f"{THREAD_SECTION_TOLERANCE * 100:.0f}%）；请清空该字段让系统"
                "自动计算，或修正 d/p 与截面数据的对应关系。"
            )
    return derived
