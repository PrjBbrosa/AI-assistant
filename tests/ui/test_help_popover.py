import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

from app.ui.help_provider import HelpProvider
from app.ui.widgets.help_button import HelpButton
from app.ui.widgets.help_popover import HelpPopover


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fixture_help_provider():
    """用测试 fixture 树替换 HelpProvider 单例，测试结束后复原。"""
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "help"
    original = HelpProvider._instance
    HelpProvider._instance = HelpProvider(root=fixture_root)
    try:
        yield HelpProvider._instance
    finally:
        HelpProvider._instance = original


def test_popover_opens_with_title_and_body(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.isVisible()
    assert "示例术语" in popover.windowTitle() or "示例术语" in popover.title_text()
    assert "仅供自测" in popover.body_markdown()
    popover.close()


def test_popover_missing_ref_shows_placeholder(app):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/definitely_missing", anchor=anchor)
    assert popover.isVisible()
    assert "缺失" in popover.title_text()
    popover.close()


def test_help_button_objectname(app):
    btn = HelpButton("terms/_sample")
    assert btn.objectName() == "HelpButton"
    assert btn.text() == "?"
    assert btn.help_ref == "terms/_sample"


def test_show_for_with_destroyed_anchor_does_not_crash(app, tmp_path, monkeypatch):
    """If the anchor widget's C++ object has been destroyed, show_for must
    degrade to cursor-position fallback instead of raising RuntimeError.

    Repro: create a HelpButton, wrap in a parent page, show_for fires, then
    parent page is deleted -> anchor.window() raises RuntimeError.
    """
    import shiboken6
    from PySide6.QtWidgets import QWidget
    from app.ui.widgets.help_popover import HelpPopover

    # Build a parent hierarchy, then delete the parent to invalidate child anchor
    parent = QWidget()
    anchor = QWidget(parent)
    # Force immediate C++ deletion so the anchor wrapper is invalid.
    shiboken6.delete(parent)
    app.processEvents()
    # Now anchor's underlying C++ object is gone. Python wrapper still exists.
    # Any attribute access that touches the C++ object will raise RuntimeError.

    # show_for must not crash; must return a HelpPopover
    popover = HelpPopover.show_for("missing/ref", anchor)
    assert popover is not None
    assert isinstance(popover, HelpPopover)
    popover.close()


def test_show_for_with_valid_anchor_still_works(app):
    from PySide6.QtWidgets import QWidget
    from app.ui.widgets.help_popover import HelpPopover
    parent = QWidget()
    parent.show()
    anchor = QWidget(parent)
    popover = HelpPopover.show_for("missing/ref", anchor)
    assert popover is not None
    assert popover.isVisible()
    popover.close()
    parent.close()
