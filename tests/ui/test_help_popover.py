import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

from app.ui.widgets.help_button import HelpButton
from app.ui.widgets.help_popover import HelpPopover


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_popover_opens_with_title_and_body(app):
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
