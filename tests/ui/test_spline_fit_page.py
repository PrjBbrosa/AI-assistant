import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages.spline_fit_page import SMOOTH_FIT_FIELD_IDS, SplineFitPage


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestSplineFitPage:
    def test_page_creates_without_error(self, app):
        page = SplineFitPage()
        assert page is not None

    def test_chapter_count(self, app):
        page = SplineFitPage()
        assert page.chapter_stack.count() == 5

    def test_calculate_with_defaults(self, app):
        page = SplineFitPage()
        page._on_calculate()
        assert page.overall_badge.objectName() in ("PassBadge", "FailBadge")

    def test_mode_switch_hides_smooth_fields(self, app):
        page = SplineFitPage()
        mode_combo = page._widgets["mode"]
        # Switch to "仅花键" — smooth_fit fields should be hidden
        mode_combo.setCurrentText("仅花键")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = page._field_cards.get(fid)
            if card:
                assert card.isHidden(), f"{fid} should be hidden in spline-only mode"
        # Switch back to "联合" — smooth_fit fields should be visible
        mode_combo.setCurrentText("联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = page._field_cards.get(fid)
            if card:
                assert not card.isHidden(), f"{fid} should be visible in combined mode"
