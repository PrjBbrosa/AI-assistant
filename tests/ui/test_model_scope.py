"""Unit tests for shared MODEL-S01 module-scope banners."""

from core.hertz.calculator import OUTER_CONTACT_SCOPE_NOTE
from app.ui.model_scope import (
    BOLT_SCOPE,
    BUFFER_SCOPE,
    HERTZ_SCOPE,
    INTERFERENCE_SCOPE,
    MODEL_LEVEL_FORMAL_SUBSET,
    MODEL_LEVEL_PRECHECK,
    MODEL_LEVEL_QUICK,
    MODULE_SCOPES,
    SPLINE_SCOPE,
    TAPPED_SCOPE,
    WORM_SCOPE,
    format_scope_banner_text,
    scope_kv_rows,
    scope_report_lines,
)


def test_hertz_scope_reuses_outer_contact_note() -> None:
    assert HERTZ_SCOPE.model_level == MODEL_LEVEL_QUICK
    assert HERTZ_SCOPE.applicability == OUTER_CONTACT_SCOPE_NOTE
    banner = format_scope_banner_text(HERTZ_SCOPE)
    assert "模型等级：快速估算" in banner
    assert OUTER_CONTACT_SCOPE_NOTE in banner
    assert "内接触" in banner
    rows = dict(scope_kv_rows(HERTZ_SCOPE))
    assert rows["模型等级"] == MODEL_LEVEL_QUICK


def test_spline_and_worm_scope_levels() -> None:
    assert SPLINE_SCOPE.model_level == MODEL_LEVEL_PRECHECK
    assert WORM_SCOPE.model_level == MODEL_LEVEL_FORMAL_SUBSET
    spline_lines = "\n".join(scope_report_lines(SPLINE_SCOPE))
    worm_lines = "\n".join(scope_report_lines(WORM_SCOPE))
    assert "简化预校核" in spline_lines
    assert "DIN 5480" in spline_lines
    assert "正式子集" in worm_lines
    assert "负载能力" in worm_lines
    assert "完整 DIN 3996" in worm_lines


def test_interference_scope_is_din7190_style_not_full_cert() -> None:
    assert INTERFERENCE_SCOPE.module_id == "interference_fit"
    assert INTERFERENCE_SCOPE.model_level == MODEL_LEVEL_FORMAL_SUBSET
    assert MODULE_SCOPES[INTERFERENCE_SCOPE.module_id] is INTERFERENCE_SCOPE
    text = "\n".join(scope_report_lines(INTERFERENCE_SCOPE))
    assert "DIN 7190" in text
    assert "签发" in text
    assert "服役温度" in text
    assert "转速" in text
    assert "离心力" in text
    assert "阶梯" in text


def test_tapped_and_buffer_scope_levels() -> None:
    assert TAPPED_SCOPE.model_level == MODEL_LEVEL_FORMAL_SUBSET
    assert BUFFER_SCOPE.model_level == MODEL_LEVEL_QUICK
    assert MODULE_SCOPES[TAPPED_SCOPE.module_id] is TAPPED_SCOPE
    assert MODULE_SCOPES[BUFFER_SCOPE.module_id] is BUFFER_SCOPE
    tapped = "\n".join(scope_report_lines(TAPPED_SCOPE))
    buffer_lines = "\n".join(scope_report_lines(BUFFER_SCOPE))
    assert "正式子集" in tapped
    assert "横向力" in tapped
    assert "校核不完整" in tapped
    assert "快速估算" in buffer_lines
    assert "认证" in buffer_lines
    assert "应变率" in buffer_lines


def test_bolt_scope_is_formal_subset() -> None:
    assert BOLT_SCOPE.model_level == MODEL_LEVEL_FORMAL_SUBSET
    assert MODULE_SCOPES[BOLT_SCOPE.module_id] is BOLT_SCOPE
    banner = format_scope_banner_text(BOLT_SCOPE)
    assert "正式子集" in banner
    assert "偏心" in banner
    assert "疲劳" in banner
    assert "脱扣" in banner
    assert "完整 VDI 2230" in banner
    lines = "\n".join(scope_report_lines(BOLT_SCOPE))
    assert "不是完整标准签发校核" in lines
