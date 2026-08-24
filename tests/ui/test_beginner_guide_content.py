"""Content contract for the module-level beginner guides."""

from __future__ import annotations

import pytest

from app.ui.help_provider import HelpProvider


GUIDES = (
    (
        "modules/bolt_tapped_axial/beginner_guide",
        ("轴向", "螺纹"),
        "执行校核",
        ("校核不完整", "m_eff"),
    ),
    (
        "modules/interference/beginner_guide",
        ("过盈",),
        "执行校核",
        ("Fretting", "不改变基础总体"),
    ),
    (
        "modules/spline/beginner_guide",
        ("花键",),
        "执行校核",
        ("简化预校核", "联合"),
    ),
    (
        "modules/worm/beginner_guide",
        ("蜗轮", "蜗杆"),
        "执行校核",
        ("Method B 风格最小子集", "Method C", "拒绝"),
    ),
    (
        "modules/hertz/beginner_guide",
        ("赫兹",),
        "执行校核",
        ("855.68", "负曲率", "外接触"),
    ),
    (
        "modules/buffer/beginner_guide",
        ("缓冲",),
        "执行仿真",
        ("13.50 J", "触底", "峰值力为不可判定"),
    ),
)


@pytest.mark.parametrize(
    "help_ref,title_tokens,run_token,critical_tokens",
    GUIDES,
)
def test_beginner_guide_is_complete_and_beginner_oriented(
    help_ref,
    title_tokens,
    run_token,
    critical_tokens,
):
    entry = HelpProvider().get(help_ref)

    assert not entry.title.startswith("帮助内容缺失")
    assert all(token in entry.title for token in title_tokens)
    assert entry.category is not None
    assert len(entry.body_md) >= 600
    assert "测试案例 1" in entry.body_md
    assert run_token in entry.body_md
    assert all(token in entry.body_md for token in critical_tokens)
    assert any(token in entry.body_md for token in ("输入", "准备"))
    assert any(token in entry.body_md for token in ("结果", "PASS", "通过"))
    assert any(
        token in entry.body_md
        for token in ("边界", "不适用", "不支持", "不包含", "不能")
    )
