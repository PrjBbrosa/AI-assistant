"""Shared FieldSchema for UI widgets, live validation, and payload build."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from core._validation import bounded_float, enum_value, finite_float, safety_factor_min

ValueType = Literal["float", "int", "enum", "text", "bool"]
Condition = Callable[[Mapping[str, str]], bool] | tuple[str, str, Any]

_UNSET: Any = object()
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$", flags=re.ASCII)
_INT_RE = re.compile(r"^-?\d+$", flags=re.ASCII)
_BOOL_TRUE = frozenset({"true", "1", "yes", "on"})
_BOOL_FALSE = frozenset({"false", "0", "no", "off"})


@dataclass(frozen=True)
class FieldSchema:
    field_id: str
    label: str
    unit: str = ""
    value_type: ValueType = "float"
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True
    finite: bool = True
    options: tuple[str, ...] = ()
    default: Any = ""
    mapping: tuple[str, str] | None = None
    source_kind: str = "user"
    visible_when: Condition | None = None
    required_when: Condition | None = None
    help_ref: str | None = None
    hint: str = ""
    placeholder: str = ""

    @property
    def widget_type(self) -> str:
        if self.value_type in ("enum", "bool"):
            return "choice"
        if self.value_type == "text":
            return "text"
        return "number"


def FieldSpec(
    field_id: str,
    label: str,
    unit: str,
    hint: str = "",
    *,
    widget_type: str = "number",
    options: tuple[str, ...] = (),
    default: Any = "",
    help_ref: str | None = None,
    value_type: ValueType | None = None,
    required: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
    min_inclusive: bool = True,
    max_inclusive: bool = True,
    finite: bool = True,
    mapping: tuple[str, str] | None = _UNSET,
    source_kind: str = "user",
    visible_when: Condition | None = None,
    required_when: Condition | None = None,
    placeholder: str = "",
) -> FieldSchema:
    """Compatibility constructor matching page-local FieldSpec call sites."""
    if value_type is None:
        if widget_type == "choice":
            resolved_type: ValueType = "enum"
        elif widget_type == "text":
            resolved_type = "text"
        else:
            resolved_type = "float"
    else:
        resolved_type = value_type
    resolved_mapping: tuple[str, str] | None
    if mapping is _UNSET:
        if "." in field_id:
            section, key = field_id.split(".", 1)
            resolved_mapping = (section, key)
        else:
            resolved_mapping = None
    else:
        resolved_mapping = mapping
    return FieldSchema(
        field_id=field_id,
        label=label,
        unit=unit,
        value_type=resolved_type,
        required=required,
        min_value=min_value,
        max_value=max_value,
        min_inclusive=min_inclusive,
        max_inclusive=max_inclusive,
        finite=finite,
        options=tuple(options),
        default="" if default is None else default,
        mapping=resolved_mapping,
        source_kind=source_kind,
        visible_when=visible_when,
        required_when=required_when,
        help_ref=help_ref or None,
        hint=hint,
        placeholder=placeholder,
    )


def evaluate_condition(
    condition: Condition | None,
    values: Mapping[str, str],
) -> bool:
    if condition is None:
        return True
    if callable(condition):
        return bool(condition(values))
    op, field_id, expected = condition
    actual = values.get(field_id, "")
    expected_text = "" if expected is None else str(expected)
    if op == "eq":
        return actual == expected_text
    if op == "neq":
        return actual != expected_text
    raise ValueError(f"不支持的条件运算符: {op}")


def is_schema_visible(
    schema: FieldSchema,
    values: Mapping[str, str] | None = None,
) -> bool:
    if schema.visible_when is None:
        return True
    if values is None:
        return True
    return evaluate_condition(schema.visible_when, values)


def is_schema_required(
    schema: FieldSchema,
    values: Mapping[str, str] | None = None,
) -> bool:
    if schema.required:
        return True
    if schema.required_when is None or values is None:
        return False
    return evaluate_condition(schema.required_when, values)


def validate_text(
    schema: FieldSchema,
    raw: Any,
    *,
    values: Mapping[str, str] | None = None,
) -> tuple[bool, str]:
    """Return (ok, message) using the same finite/range/enum rules as core."""
    if values is not None and not is_schema_visible(schema, values):
        return True, ""
    text = _as_text(raw)
    required = is_schema_required(schema, values)
    if text == "":
        if required:
            return False, f"{schema.label} 为必填项"
        return True, ""
    try:
        _validate_non_empty(schema, text)
    except ValueError as exc:
        return False, str(exc)
    return True, ""


def parse_payload_value(
    schema: FieldSchema,
    raw: Any,
    *,
    values: Mapping[str, str] | None = None,
) -> Any:
    ok, message = validate_text(schema, raw, values=values)
    if not ok:
        raise ValueError(message)
    text = _as_text(raw)
    if text == "":
        return None
    if schema.value_type in ("enum", "text"):
        return text
    if schema.value_type == "bool":
        return text.casefold() in _BOOL_TRUE
    if schema.value_type == "int":
        return int(text)
    return float(text)


def build_payload(
    schemas: Iterable[FieldSchema],
    raw_values: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Build calculator payload; skip hidden and unmapped fields."""
    payload: dict[str, dict[str, Any]] = {}
    for schema in schemas:
        if schema.mapping is None:
            continue
        if not is_schema_visible(schema, raw_values):
            continue
        value = parse_payload_value(
            schema,
            raw_values.get(schema.field_id, ""),
            values=raw_values,
        )
        if value is None:
            continue
        section, key = schema.mapping
        payload.setdefault(section, {})[key] = value
    return payload


def _as_text(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw).strip()


def _validate_non_empty(schema: FieldSchema, text: str) -> None:
    if schema.value_type == "enum":
        enum_value(text, schema.label, schema.options, error_cls=ValueError)
        return
    if schema.value_type == "bool":
        folded = text.casefold()
        if folded not in _BOOL_TRUE and folded not in _BOOL_FALSE:
            raise ValueError(f"{schema.label} 无效：{text}（支持 true/false）")
        return
    if schema.value_type == "text":
        return
    if schema.value_type == "int":
        if not _INT_RE.fullmatch(text):
            raise ValueError(f'字段"{schema.label}"请输入有效整数，当前值: {text}')
    elif not _NUMBER_RE.fullmatch(text):
        raise ValueError(f'字段"{schema.label}"请输入有效数字，当前值: {text}')
    _validate_numeric_domain(schema, text)


def _validate_numeric_domain(schema: FieldSchema, text: str) -> float:
    name = schema.label
    if (
        schema.min_value == 1.0
        and schema.max_value is None
        and schema.min_inclusive
    ):
        return safety_factor_min(text, name, error_cls=ValueError)
    if schema.min_value is not None or schema.max_value is not None:
        return bounded_float(
            text,
            name,
            min_value=schema.min_value,
            max_value=schema.max_value,
            min_inclusive=schema.min_inclusive,
            max_inclusive=schema.max_inclusive,
            error_cls=ValueError,
        )
    if schema.finite:
        return finite_float(text, name, error_cls=ValueError)
    try:
        return float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'字段"{name}"请输入有效数字，当前值: {text}') from exc
