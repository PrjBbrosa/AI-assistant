"""Tests for BaseChapterPage add_chapter contract — P0-1 regression guard."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QScrollArea

from app.ui.design_tokens import cloud_porcelain_controls
from app.ui.pages.base_chapter_page import BaseChapterPage


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_chapter_page_at_returns_original_page_without_help_ref(qapp):
    """When help_ref is None, chapter_page_at must return the exact page passed in."""
    shell = BaseChapterPage("t", "s")
    original = QFrame()
    idx = shell.add_chapter("step", original)
    assert shell.chapter_page_at(idx) is original


def test_chapter_page_at_returns_original_page_with_help_ref(qapp):
    """When help_ref is set, chapter_page_at must still return the original page,
    not the header wrapper."""
    shell = BaseChapterPage("t", "s")
    original = QScrollArea()
    idx = shell.add_chapter("step", original, help_ref="foo/bar")
    assert shell.chapter_page_at(idx) is original


def test_chapter_container_at_returns_wrapper_when_help_ref(qapp):
    """chapter_container_at returns the widget actually inserted into chapter_stack."""
    shell = BaseChapterPage("t", "s")
    original = QScrollArea()
    idx = shell.add_chapter("step", original, help_ref="foo/bar")
    container = shell.chapter_container_at(idx)
    # Container is the wrapper when help_ref is set — not the original page
    assert container is not original
    assert container is shell.chapter_stack.widget(idx)


def test_chapter_container_at_equals_page_without_help_ref(qapp):
    """Without help_ref, container and page are the same widget."""
    shell = BaseChapterPage("t", "s")
    original = QFrame()
    idx = shell.add_chapter("step", original)
    assert shell.chapter_container_at(idx) is original
    assert shell.chapter_page_at(idx) is original


def test_chapter_page_at_out_of_range_raises(qapp):
    """Accessing out-of-range index raises IndexError."""
    shell = BaseChapterPage("t", "s")
    with pytest.raises(IndexError):
        shell.chapter_page_at(0)


def test_footer_has_info_label_not_overall_badge(qapp):
    """UI-S04: footer shows run/save/error info, not a competing overall PASS/FAIL badge."""
    shell = BaseChapterPage("t", "s")
    assert not hasattr(shell, "overall_badge")
    assert shell.info_label.text()
    original = shell.info_label.text()
    shell.set_overall_status("总体通过", "pass")
    assert shell.info_label.text() == original
    assert "总体通过" not in shell.info_label.text()
    shell.set_overall_status("总体不通过", "fail")
    assert "总体不通过" not in shell.info_label.text()
    shell.set_overall_status("输入已变更，待重新计算", "wait")
    assert shell.info_label.text() == "输入已变更，待重新计算"


def test_combined_header_contains_title_and_actions(qapp):
    """PAGE-01: title, subtitle, and action buttons share one glass header."""
    shell = BaseChapterPage("赫兹应力", "subtitle")
    button = shell.add_action_button("执行校核", primary=True)
    assert isinstance(button, QPushButton)
    header = shell.chapter_header
    assert header.objectName() == "ChapterHeader"
    assert header.minimumHeight() >= cloud_porcelain_controls().header_min_height
    title = header.findChild(QLabel, "ChapterTitle")
    assert title is not None
    assert title.text() == "赫兹应力"
    assert header.isAncestorOf(title)
    assert header.isAncestorOf(button)
    assert header.isAncestorOf(shell.overflow_button)
    assert shell.add_action_stretch() is None


def test_second_primary_action_is_demoted(qapp):
    """Only one PrimaryButton remains; the earlier primary is demoted."""
    shell = BaseChapterPage("t", "s")
    first = shell.add_action_button("导入曲线文件", primary=True)
    second = shell.add_action_button("执行仿真", primary=True)
    assert first.objectName() != "PrimaryButton"
    assert second.objectName() == "PrimaryButton"
