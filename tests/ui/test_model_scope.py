"""Unit tests for shared MODEL-S01 module-scope banners."""

from core.hertz.calculator import OUTER_CONTACT_SCOPE_NOTE
from app.ui.model_scope import (
    HERTZ_SCOPE,
    MODEL_LEVEL_FORMAL_SUBSET,
    MODEL_LEVEL_PRECHECK,
    MODEL_LEVEL_QUICK,
    SPLINE_SCOPE,
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
