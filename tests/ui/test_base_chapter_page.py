"""Tests for BaseChapterPage add_chapter contract — P0-1 regression guard."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QFrame, QScrollArea

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
