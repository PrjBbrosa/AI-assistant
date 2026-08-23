"""Unit tests for shared calculator input validation."""

from __future__ import annotations

import math

import pytest

from core._validation import (
    bounded_float,
    enum_value,
    finite_float,
    load_amplification,
    positive_float,
    require_mapping,
    safety_factor_min,
    section,
)


class InputError(ValueError):
    """Stand-in for a module-level InputError."""


def test_require_mapping_rejects_list() -> None:
    with pytest.raises(InputError, match="必须是字典"):
        require_mapping([], error_cls=InputError)


def test_require_mapping_rejects_none_and_bool() -> None:
    with pytest.raises(InputError, match="必须是字典"):
        require_mapping(None, error_cls=InputError)
    with pytest.raises(InputError, match="必须是字典"):
        require_mapping(True, error_cls=InputError)


def test_require_mapping_accepts_dict() -> None:
    data = {"a": 1}
    assert require_mapping(data, error_cls=InputError) is data


def test_section_missing_returns_empty() -> None:
    assert section({}, "loads", error_cls=InputError) == {}


def test_section_rejects_non_dict() -> None:
    with pytest.raises(InputError, match="loads 必须是字典"):
        section({"loads": []}, "loads", error_cls=InputError)


@pytest.mark.parametrize("bad", [True, False, math.nan, math.inf, -math.inf, "abc", None, object()])
def test_finite_float_rejects_non_finite(bad: object) -> None:
    with pytest.raises(InputError):
        finite_float(bad, "field", error_cls=InputError)


def test_finite_float_accepts_numeric_string() -> None:
    assert finite_float("1.5", "field", error_cls=InputError) == 1.5


def test_positive_float_rejects_zero_by_default() -> None:
    with pytest.raises(InputError, match="必须 > 0"):
        positive_float(0.0, "field", error_cls=InputError)


def test_positive_float_allow_zero() -> None:
    assert positive_float(0.0, "field", allow_zero=True, error_cls=InputError) == 0.0


def test_positive_float_rejects_inf() -> None:
    with pytest.raises(InputError, match="有限"):
        positive_float(math.inf, "field", error_cls=InputError)


def test_bounded_float_open_and_closed() -> None:
    assert bounded_float(0.3, "nu", min_value=0.0, max_value=0.5, min_inclusive=False, max_inclusive=False, error_cls=InputError) == 0.3
    with pytest.raises(InputError, match="0.0 < 值 < 0.5"):
        bounded_float(0.0, "nu", min_value=0.0, max_value=0.5, min_inclusive=False, max_inclusive=False, error_cls=InputError)
    assert bounded_float(11, "n", min_value=11, max_value=201, error_cls=InputError) == 11.0
    with pytest.raises(InputError, match="11 <= 值 <= 201"):
        bounded_float(10, "n", min_value=11, max_value=201, error_cls=InputError)


def test_enum_value_no_silent_fallback() -> None:
    assert enum_value("line", "mode", ("line", "point"), error_cls=InputError) == "line"
    with pytest.raises(InputError, match="无效"):
        enum_value("area", "mode", ("line", "point"), error_cls=InputError)


@pytest.mark.parametrize("fn", [safety_factor_min, load_amplification])
def test_safety_and_ka_domain(fn) -> None:
    with pytest.raises(InputError, match=">= 1.0"):
        fn(0.99, "field", error_cls=InputError)
    assert fn(1.0, "field", error_cls=InputError) == 1.0
    assert fn(1.5, "field", error_cls=InputError) == 1.5
    with pytest.raises(InputError, match="有限"):
        fn(math.nan, "field", error_cls=InputError)
    with pytest.raises(InputError, match="有限"):
        fn(math.inf, "field", error_cls=InputError)
