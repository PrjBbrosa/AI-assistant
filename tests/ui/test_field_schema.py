"""Unit tests for shared FieldSchema validation and payload collection."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.ui.field_schema import (
    FieldSchema,
    FieldSpec,
    build_payload,
    parse_payload_value,
    validate_text,
)
from app.ui.pages.bolt_tapped_axial_page import CHAPTERS
from core.bolt.grades import BOLT_GRADE_CUSTOM, bolt_grade_options


def _chapter_specs() -> dict[str, FieldSchema]:
    specs: dict[str, FieldSchema] = {}
    for chapter in CHAPTERS:
        for spec in chapter["fields"]:
            specs[spec.field_id] = spec
    return specs


def test_field_spec_factory_builds_mapped_float_schema() -> None:
    schema = FieldSpec("fastener.d", "公称直径 d", "mm", "hint", default="10.0")

    assert isinstance(schema, FieldSchema)
    assert schema.value_type == "float"
    assert schema.widget_type == "number"
    assert schema.mapping == ("fastener", "d")
    assert schema.finite is True
    assert schema.hint == "hint"
    assert schema.default == "10.0"


def test_field_spec_choice_becomes_enum() -> None:
    schema = FieldSpec(
        "assembly.tightening_method",
        "拧紧方式",
        "-",
        "",
        widget_type="choice",
        options=("torque", "angle"),
        default="torque",
    )

    assert schema.value_type == "enum"
    assert schema.widget_type == "choice"
    assert schema.options == ("torque", "angle")


def test_validate_text_rejects_non_numeric() -> None:
    schema = FieldSpec("service.FA_max", "最大轴向载荷 FA_max", "N", "")

    for raw in ("abc", "1_000", "１２", "+1000", ".5", "1.", "nan", "inf", "-inf"):
        ok, message = validate_text(schema, raw)
        assert not ok, raw
        assert "有效数字" in message


def test_validate_text_rejects_non_finite_overflow() -> None:
    schema = FieldSpec("service.FA_max", "最大轴向载荷 FA_max", "N", "")

    ok, message = validate_text(schema, "1e999")

    assert not ok
    assert "有限" in message


def test_validate_text_accepts_scientific_notation() -> None:
    schema = FieldSpec("service.FA_max", "最大轴向载荷 FA_max", "N", "")

    ok, message = validate_text(schema, "1.5e3")

    assert ok
    assert message == ""
    assert parse_payload_value(schema, "1.5e3") == 1500.0


def test_validate_text_safety_min_rejects_below_one() -> None:
    schema = FieldSpec(
        "thread_strip.safety_required",
        "脱扣目标安全系数",
        "-",
        "",
        min_value=1.0,
        default="1.5",
    )

    ok, message = validate_text(schema, "0.5")

    assert not ok
    assert ">= 1.0" in message
    assert parse_payload_value(schema, "1.0") == 1.0
    assert parse_payload_value(schema, "1.5") == 1.5


def test_validate_text_enum_rejects_unknown() -> None:
    schema = FieldSpec(
        "fatigue.surface_treatment",
        "螺纹表面处理",
        "-",
        "",
        widget_type="choice",
        options=("rolled", "cut"),
        default="rolled",
    )

    ok, message = validate_text(schema, "polished")

    assert not ok
    assert "无效" in message
    assert parse_payload_value(schema, "cut") == "cut"


def test_validate_text_optional_empty_is_ok() -> None:
    schema = FieldSpec(
        "thread_strip.m_eff",
        "有效啮合长度 m_eff",
        "mm",
        "",
        required=False,
    )

    ok, message = validate_text(schema, "")

    assert ok
    assert message == ""
    assert parse_payload_value(schema, "") is None


def test_validate_text_required_when_depends_on_sibling() -> None:
    schema = FieldSpec(
        "thread_strip.tau_BM",
        "母材许用剪应力 tau_BM",
        "MPa",
        "",
        required=False,
        required_when=("neq", "thread_strip.m_eff", ""),
    )

    ok_empty, _ = validate_text(
        schema, "", values={"thread_strip.m_eff": "", "thread_strip.tau_BM": ""}
    )
    ok_required, message = validate_text(
        schema, "", values={"thread_strip.m_eff": "10", "thread_strip.tau_BM": ""}
    )

    assert ok_empty
    assert not ok_required
    assert "必填" in message


def test_build_payload_omits_unmapped_and_hidden_fields() -> None:
    mapped = FieldSpec("fastener.d", "公称直径 d", "mm", "", default="10")
    unmapped = FieldSpec(
        "notes",
        "备注",
        "-",
        "",
        mapping=None,
        value_type="text",
        required=False,
        default="hello",
    )
    hidden = FieldSpec(
        "hidden.value",
        "隐藏值",
        "-",
        "",
        default="9",
        visible_when=("eq", "mode", "full"),
    )
    values = {
        "fastener.d": "10",
        "notes": "hello",
        "hidden.value": "9",
        "mode": "compact",
    }

    payload = build_payload([mapped, unmapped, hidden], values)

    assert payload == {"fastener": {"d": 10.0}}
    assert "notes" not in payload
    assert "hidden" not in payload


def test_tapped_axial_field_schema_contract() -> None:
    specs = _chapter_specs()
    safety = specs["thread_strip.safety_required"]
    assert isinstance(safety, FieldSchema)
    assert safety.value_type == "float"
    assert safety.finite is True
    assert safety.min_value == 1.0
    assert safety.min_inclusive is True
    assert safety.mapping == ("thread_strip", "safety_required")
    assert safety.required is True

    grade = specs["fastener.grade"]
    assert grade.value_type == "enum"
    assert grade.options == bolt_grade_options()
    assert BOLT_GRADE_CUSTOM in grade.options
    assert grade.widget_type == "choice"

    for field_id in ("fastener.As", "fastener.d2", "fastener.d3"):
        assert specs[field_id].source_kind == "derived"
        assert specs[field_id].mapping is not None

    yield_safety = specs["checks.yield_safety_operating"]
    assert yield_safety.min_value == 1.0

    mapped = [spec for spec in specs.values() if spec.mapping is not None]
    assert mapped
    for spec in mapped:
        section, key = spec.mapping
        assert spec.field_id == f"{section}.{key}"
