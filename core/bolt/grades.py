"""Bolt strength-grade presets shared by bolt and tapped-axial UIs.

Project table follows GB/T 3098.1 style values. ISO 898-1 lists 10.9 Rp0.2 min
as 940 MPa; this table uses 900 MPa. The UI is the single source of truth for
presets; calculators consume the numeric Rp02 the form sends.
"""

from __future__ import annotations

BOLT_GRADE_CUSTOM = "自定义"

# 螺栓强度等级 → 屈服强度 Rp0.2 (MPa)，参考 GB/T 3098.1
BOLT_GRADE_TABLE: dict[str, float] = {
    "4.6": 240,
    "4.8": 320,
    "5.6": 300,
    "5.8": 400,
    "8.8": 640,
    "9.8": 720,
    "10.9": 900,
    "12.9": 1080,
}


def bolt_grade_options() -> tuple[str, ...]:
    return tuple(BOLT_GRADE_TABLE.keys()) + (BOLT_GRADE_CUSTOM,)


def rp02_source_zh(grade: str | None) -> str:
    """Report label for whether Rp0.2 came from a preset grade or the user."""
    if isinstance(grade, str) and grade in BOLT_GRADE_TABLE:
        return f"预设等级 {grade}"
    return "用户值"
