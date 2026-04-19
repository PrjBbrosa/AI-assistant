import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QSizeGrip, QTextBrowser, QLabel

from app.ui.help_provider import HelpProvider
from app.ui.widgets.help_popover import HelpPopover


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fixture_help_provider():
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "help"
    original = HelpProvider._instance
    HelpProvider._instance = HelpProvider(root=fixture_root)
    try:
        yield HelpProvider._instance
    finally:
        HelpProvider._instance = original


from PySide6.QtCore import QSettings, QSize


@pytest.fixture(autouse=True)
def _isolate_popover_settings(tmp_path, monkeypatch):
    """Every test in this file gets a fresh QSettings file."""
    path = tmp_path / "help_popover_settings.ini"
    monkeypatch.setattr(
        "app.ui.widgets.help_popover._settings",
        lambda: QSettings(str(path), QSettings.IniFormat),
    )
    yield


def test_popover_has_named_chrome_widgets(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.findChild(QWidget, "HelpPopoverRoot") is not None
    assert popover.findChild(QWidget, "HelpPopoverHeader") is not None
    assert popover.findChild(QWidget, "HelpPopoverFooter") is not None
    body = popover.findChild(QTextBrowser, "HelpPopoverBody")
    assert body is not None
    popover.close()


def test_popover_has_size_grip_for_resizing(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    grip = popover.findChild(QSizeGrip)
    assert grip is not None
    assert grip.isVisible()
    popover.close()


def test_popover_default_size_is_520_640(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.size().width() == 520
    assert popover.size().height() == 640
    popover.close()


def test_popover_minimum_size(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.minimumWidth() == 380
    assert popover.minimumHeight() == 320
    popover.close()


def test_popover_shows_category_and_source_when_available(app, fixture_help_provider):
    # _sample.md has "**出处**：internal fixture" -> source visible; ref="terms/_sample"
    # has no known prefix -> category falls back to "通用 · 术语"
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    cat = popover.findChild(QLabel, "HelpPopoverCategory")
    src = popover.findChild(QLabel, "HelpPopoverSource")
    assert cat is not None and cat.isVisible()
    assert cat.text() == "通用 · 术语"
    assert src is not None and src.isVisible()
    assert "internal fixture" in src.text()
    popover.close()


def test_popover_hides_category_and_source_text_when_missing(app):
    # ref="missing/ref_totally_unknown" -> infer_category returns None; missing ref has no source
    anchor = QWidget()
    popover = HelpPopover.show_for("missing/ref_totally_unknown", anchor=anchor)
    cat = popover.findChild(QLabel, "HelpPopoverCategory")
    footer = popover.findChild(QWidget, "HelpPopoverFooter")
    src = popover.findChild(QLabel, "HelpPopoverSource")
    prefix = popover.findChild(QLabel, "HelpPopoverSourcePrefix")
    assert cat is not None and not cat.isVisible()
    assert footer is not None and footer.isVisible()
    assert src is not None and not src.isVisible()
    assert prefix is not None and not prefix.isVisible()
    popover.close()


def test_popover_preserves_public_api(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert "示例术语" in popover.title_text()
    assert "仅供自测" in popover.body_markdown()
    popover.close()


def test_size_grip_is_visible_even_without_source(app):
    anchor = QWidget()
    popover = HelpPopover.show_for("missing/ref_no_source", anchor=anchor)
    grip = popover.findChild(QSizeGrip)
    assert grip is not None
    assert grip.isVisible()
    popover.close()


def test_popover_size_is_persisted_via_qsettings(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    popover.resize(612, 700)
    popover.close()

    popover2 = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover2.size() == QSize(612, 700)
    popover2.close()


def test_popover_first_open_uses_default_size(app, fixture_help_provider):
    # autouse fixture gives us a pristine settings file
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.size() == QSize(520, 640)
    popover.close()


def test_unpinned_popover_closes_on_focus_out(app, fixture_help_provider):
    parent = QWidget()
    parent.show()
    anchor = QWidget(parent)
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.isVisible()
    assert not popover.is_pinned()

    # Direct invocation simulates focus landing on parent (outside popover tree)
    popover._on_app_focus_changed(popover, parent)

    assert not popover.isVisible()
    parent.close()


def test_pinned_popover_stays_on_focus_out(app, fixture_help_provider):
    parent = QWidget()
    parent.show()
    anchor = QWidget(parent)
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    popover._pin_btn.setChecked(True)  # pin it

    popover._on_app_focus_changed(popover, parent)

    assert popover.isVisible()
    popover.close()
    parent.close()


def test_focus_change_inside_popover_tree_keeps_open(app, fixture_help_provider):
    """Focusing a child widget of the popover itself must not trigger close."""
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    from PySide6.QtWidgets import QTextBrowser
    body = popover.findChild(QTextBrowser, "HelpPopoverBody")
    # Simulate focus moving onto the popover's own body
    popover._on_app_focus_changed(popover, body)
    assert popover.isVisible()
    popover.close()


def test_body_html_contains_styled_code_block(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    from app.ui.help_provider import HelpEntry
    popover._apply_entry(HelpEntry(
        title="T", body_md="正文\n\n```\nhello = 1\n```\n",
        category=None, source=None,
    ))
    html = popover._browser.toHtml()
    # Accent bar table should be present (Qt normalises hex colours to lowercase)
    assert "d97757" in html.lower()
    assert "hello = 1" in html
    popover.close()


def test_body_html_adds_table_border(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    from app.ui.help_provider import HelpEntry
    popover._apply_entry(HelpEntry(
        title="T",
        body_md="| A | B |\n|---|---|\n| 1 | 2 |\n",
        category=None, source=None,
    ))
    html = popover._browser.toHtml()
    # Border should be injected
    assert 'border="1"' in html
    popover.close()


def test_body_html_styles_blockquote(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    from app.ui.help_provider import HelpEntry
    popover._apply_entry(HelpEntry(
        title="T", body_md="> 引用内容",
        category=None, source=None,
    ))
    html = popover._browser.toHtml()
    # Qt's markdown parser renders "> text" as indented <p>, not <blockquote>,
    # so we pre-process the markdown.  The accent bar colour ends up lowercased
    # by Qt's HTML normaliser.
    assert "8a8782" in html.lower()  # accent bar color
    assert "引用内容" in html
    popover.close()
