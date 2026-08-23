"""Shared finite-number, range, and enum validation for calculator inputs."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

E = TypeVar("E", bound=BaseException)


def require_mapping(
    data: Any,
    name: str = "data",
    *,
    error_cls: type[E] = ValueError,
) -> Mapping[str, Any]:
    """Require a dict-like mapping; reject list/str/bool/None."""
    if isinstance(data, (str, bytes, bytearray)) or not isinstance(data, Mapping):
        raise error_cls(f"{name} 必须是字典")
    return data


def section(
    data: Mapping[str, Any],
    key: str,
    *,
    error_cls: type[E] = ValueError,
) -> Mapping[str, Any]:
    """Return a dict section; missing/None becomes {}, non-dict raises."""
    if key not in data or data[key] is None:
        return {}
    value = data[key]
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Mapping):
        raise error_cls(f"{key} 必须是字典")
    return value


def finite_float(value: Any, name: str, *, error_cls: type[E] = ValueError) -> float:
    """Parse a finite float. Reject bool, NaN, and +/-Inf."""
    if isinstance(value, bool):
        raise error_cls(f"{name} 必须为有限数字，当前值: {value}")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise error_cls(f"{name} 必须为数字，当前值: {value}") from exc
    if not math.isfinite(parsed):
        raise error_cls(f"{name} 必须为有限数字，当前值: {value}")
    return parsed


def positive_float(
    value: Any,
    name: str,
    allow_zero: bool = False,
    *,
    error_cls: type[E] = ValueError,
) -> float:
    """Require a finite number that is > 0, or >= 0 when allow_zero=True."""
    numeric = finite_float(value, name, error_cls=error_cls)
    if allow_zero and numeric == 0:
        return numeric
    if numeric <= 0:
        raise error_cls(f"{name} 必须 > 0，当前值 {numeric}")
    return numeric


def bounded_float(
    value: Any,
    name: str,
    min_value: float | None = None,
    max_value: float | None = None,
    min_inclusive: bool = True,
    max_inclusive: bool = True,
    *,
    error_cls: type[E] = ValueError,
) -> float:
    """Require a finite number inside an optional [min, max] window."""
    numeric = finite_float(value, name, error_cls=error_cls)
    lo_ok = True
    hi_ok = True
    if min_value is not None:
        lo_ok = numeric >= min_value if min_inclusive else numeric > min_value
    if max_value is not None:
        hi_ok = numeric <= max_value if max_inclusive else numeric < max_value
    if lo_ok and hi_ok:
        return numeric

    if min_value is not None and max_value is not None:
        lo_op = "<=" if min_inclusive else "<"
        hi_op = "<=" if max_inclusive else "<"
        bound_txt = f"{min_value} {lo_op} 值 {hi_op} {max_value}"
    elif min_value is not None:
        op = ">=" if min_inclusive else ">"
        bound_txt = f"值 {op} {min_value}"
    else:
        op = "<=" if max_inclusive else "<"
        bound_txt = f"值 {op} {max_value}"
    raise error_cls(f"{name} 必须满足 {bound_txt}，当前值 {numeric}")


def enum_value(
    value: Any,
    name: str,
    allowed: Iterable[Any],
    *,
    error_cls: type[E] = ValueError,
) -> Any:
    """Require membership in an explicit whitelist. No silent fallback."""
    allowed_seq = tuple(allowed)
    if value not in allowed_seq:
        allowed_txt = "/".join(str(item) for item in allowed_seq)
        raise error_cls(f"{name} 无效：{value}（支持 {allowed_txt}）")
    return value


def safety_factor_min(
    value: Any,
    name: str,
    *,
    error_cls: type[E] = ValueError,
) -> float:
    """Required safety threshold: finite and >= 1.0."""
    numeric = finite_float(value, name, error_cls=error_cls)
    if numeric < 1.0:
        raise error_cls(f"{name} 必须 >= 1.0，当前值 {numeric}")
    return numeric


def load_amplification(
    value: Any,
    name: str,
    *,
    error_cls: type[E] = ValueError,
) -> float:
    """Load amplification / distribution factor (KA/KV/KH*): finite and >= 1.0."""
    numeric = finite_float(value, name, error_cls=error_cls)
    if numeric < 1.0:
        raise error_cls(f"{name} 必须 >= 1.0，当前值 {numeric}")
    return numeric
