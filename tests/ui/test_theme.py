"""Application theme regression tests."""

from __future__ import annotations

import pytest

from app.ui import fonts
from app.ui.fonts import UI_FONT_FAMILIES
from app.ui.theme import apply_theme


class _FontRecorder:
    def __init__(self) -> None:
        self._families: list[str] = []

    def families(self) -> list[str]:
        return self._families

    def setFamilies(self, families: list[str]) -> None:
        self._families = list(families)


class _StyleSheetRecorder:
    def __init__(self) -> None:
        self.value = ""
        self.apply_count = 0
        self.font_apply_count = 0
        self.font_value = _FontRecorder()

    def font(self) -> _FontRecorder:
        return self.font_value

    def setFont(self, font: _FontRecorder) -> None:
        self.font_value = font
        self.font_apply_count += 1

    def styleSheet(self) -> str:
        return self.value

    def setStyleSheet(self, value: str) -> None:
        self.value = value
        self.apply_count += 1


def test_apply_theme_is_idempotent_for_unchanged_stylesheet() -> None:
    app = _StyleSheetRecorder()

    apply_theme(app)  # type: ignore[arg-type]
    apply_theme(app)  # type: ignore[arg-type]

    assert app.apply_count == 1
    assert app.value
    assert app.font_apply_count == 1
    assert app.font().families() == UI_FONT_FAMILIES


def test_apply_theme_does_not_reapply_matching_font() -> None:
    app = _StyleSheetRecorder()
    app.font_value.setFamilies(UI_FONT_FAMILIES)

    apply_theme(app)  # type: ignore[arg-type]
    apply_theme(app)  # type: ignore[arg-type]

    assert app.font_apply_count == 0
    assert app.font().families() == UI_FONT_FAMILIES


@pytest.mark.parametrize(
    ("system_name", "expected_first"),
    (
        ("Windows", "Microsoft YaHei"),
        ("Darwin", "PingFang SC"),
        ("Linux", "Noto Sans CJK SC"),
    ),
)
def test_ui_font_family_platform_priority(monkeypatch, system_name, expected_first) -> None:
    monkeypatch.setattr(fonts.platform, "system", lambda: system_name)

    families = fonts._build_ui_font_families()

    assert families[0] == expected_first
    assert len(families) == len(set(families))
