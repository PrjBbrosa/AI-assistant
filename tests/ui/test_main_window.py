import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    apply_theme(instance)
    yield instance


def test_main_window_minimum_supported_size(app):
    window = MainWindow()
    try:
        assert window.minimumWidth() == 1180
        assert window.minimumHeight() == 720
    finally:
        window.close()


def test_materials_library_sidebar_is_marked_unfinished(app):
    window = MainWindow()
    try:
        items = [
            window.module_list.item(i).text()
            for i in range(window.module_list.count())
        ]
        assert any("材料与标准库" in text and "即将推出" in text for text in items)
    finally:
        window.close()
