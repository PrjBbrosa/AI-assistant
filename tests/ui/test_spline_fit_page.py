import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.ui.pages.spline_fit_page import SMOOTH_FIT_FIELD_IDS, SplineFitPage


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    yield instance


class TestSplineFitPage:
    @staticmethod
    def _label_texts(page: SplineFitPage) -> list[str]:
        return [label.text() for label in page.findChildren(QLabel)]

    def test_page_creates_without_error(self, app):
        page = SplineFitPage()
        assert page is not None

    def test_header_uses_connection_check_wording(self, app):
        page = SplineFitPage()
        texts = self._label_texts(page)
        assert "花键连接校核" in texts
        assert "花键过盈配合" not in texts

    def test_page_shows_engineering_scope_disclaimer(self, app):
        page = SplineFitPage()
        texts = self._label_texts(page)
        assert any("简化预校核" in text for text in texts)
        assert any("不替代 DIN 5480" in text and "DIN 6892" in text for text in texts)

    def test_chapter_count(self, app):
        page = SplineFitPage()
        assert page.chapter_stack.count() == 5

    def test_result_card_marks_scenario_a_as_simplified(self, app):
        page = SplineFitPage()
        texts = self._label_texts(page)
        assert "场景 A - 花键齿面承压（简化）" in texts

    def test_material_choice_autofills_elastic_properties(self, app):
        page = SplineFitPage()
        shaft_material = page._widgets["smooth_materials.shaft_material"]
        shaft_nu = page._widgets["smooth_materials.shaft_nu"]
        hub_material = page._widgets["smooth_materials.hub_material"]
        hub_nu = page._widgets["smooth_materials.hub_nu"]

        shaft_material.setCurrentText("40Cr")
        hub_material.setCurrentText("42CrMo")

        assert shaft_nu.text() == "0.29"
        assert hub_nu.text() == "0.29"

    def test_calculate_with_defaults(self, app):
        page = SplineFitPage()
        page._on_calculate()
        assert page.overall_badge.objectName() in ("PassBadge", "FailBadge")

    def test_default_combined_case_surfaces_scenario_b_failure_reason(self, app):
        page = SplineFitPage()
        page._on_calculate()
        assert "扭矩与轴向力联合作用超出当前最小过盈能力" in page.info_label.text()

    def test_mode_switch_disables_smooth_fields(self, app):
        page = SplineFitPage()
        mode_combo = page._widgets["mode"]
        # Switch to "仅花键" — smooth_fit fields should be disabled (AutoCalcCard)
        mode_combo.setCurrentText("仅花键")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = page._field_cards.get(fid)
            if card:
                assert card.objectName() == "AutoCalcCard", f"{fid} should be AutoCalcCard in spline-only mode"
        # Switch back to "联合" — smooth_fit fields should be enabled (SubCard),
        # except material-auto-filled e_mpa/nu fields which stay AutoCalcCard when non-custom material is selected
        MATERIAL_AUTO_FILLED = {
            "smooth_materials.shaft_e_mpa", "smooth_materials.shaft_nu",
            "smooth_materials.hub_e_mpa", "smooth_materials.hub_nu",
        }
        mode_combo.setCurrentText("联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            if fid in MATERIAL_AUTO_FILLED:
                continue
            card = page._field_cards.get(fid)
            if card:
                assert card.objectName() == "SubCard", f"{fid} should be SubCard in combined mode"

    def test_standard_designation_autofills_geometry(self, app):
        page = SplineFitPage()
        combo = page._widgets["spline.standard_designation"]
        combo.setCurrentText("W 25x1.25x18")
        assert page._widgets["spline.module_mm"].text() == "1.25"
        assert page._widgets["spline.tooth_count"].text() == "18"
        assert page._widgets["spline.reference_diameter_mm"].text() == "25.0"

    def test_standard_designation_custom_restores_editable(self, app):
        page = SplineFitPage()
        combo = page._widgets["spline.standard_designation"]
        combo.setCurrentText("W 25x1.25x18")
        combo.setCurrentText("自定义")
        card = page._field_cards.get("spline.module_mm")
        assert card.objectName() == "SubCard"

    def test_load_condition_autofills_with_blue_style(self, app):
        page = SplineFitPage()
        lc = page._widgets["spline.load_condition"]
        lc.setCurrentText("固定连接，静载，调质钢")
        card = page._field_cards.get("spline.p_allowable_mpa")
        assert card.objectName() == "AutoCalcCard"
        # 切自定义恢复
        lc.setCurrentText("自定义")
        assert card.objectName() == "SubCard"

    def test_material_autofills_with_blue_style(self, app):
        page = SplineFitPage()
        shaft_mat = page._widgets["smooth_materials.shaft_material"]
        shaft_mat.setCurrentText("40Cr")
        e_card = page._field_cards.get("smooth_materials.shaft_e_mpa")
        nu_card = page._field_cards.get("smooth_materials.shaft_nu")
        assert e_card.objectName() == "AutoCalcCard"
        assert nu_card.objectName() == "AutoCalcCard"
        # 切自定义恢复
        shaft_mat.setCurrentText("自定义")
        assert e_card.objectName() == "SubCard"
        assert nu_card.objectName() == "SubCard"

    def test_standard_designation_autofills_geometry_with_blue_style(self, app):
        page = SplineFitPage()
        combo = page._widgets["spline.standard_designation"]
        combo.setCurrentText("W 25x1.25x18")
        for fid in ["spline.module_mm", "spline.tooth_count", "spline.reference_diameter_mm"]:
            card = page._field_cards.get(fid)
            assert card.objectName() == "AutoCalcCard", f"{fid} should be AutoCalcCard"
        # 切自定义恢复
        combo.setCurrentText("自定义")
        for fid in ["spline.module_mm", "spline.tooth_count", "spline.reference_diameter_mm"]:
            card = page._field_cards.get(fid)
            assert card.objectName() == "SubCard", f"{fid} should be SubCard"
