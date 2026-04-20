import pytest
from PySide6.QtWidgets import QApplication, QLabel

from app.ui.main_window import MainWindow
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
        assert any("花键连接" in text for text in texts)
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

    def test_default_mode_prefers_spline_only_for_first_entry(self, app):
        page = SplineFitPage()
        assert page._widgets["mode"].currentText() == "仅花键"

    def test_page_exposes_state_closure_actions(self, app):
        page = SplineFitPage()
        assert page.btn_save_inputs.text() == "保存输入条件"
        assert page.btn_load_inputs.text() == "加载输入条件"
        assert page.btn_clear.text() == "清空参数"
        assert page.btn_load_1.text() == "测试案例 1"
        assert page.btn_load_2.text() == "测试案例 2"

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
        page._widgets["mode"].setCurrentText("联合")
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
        # except material-auto-filled E/ν/屈服强度 fields which stay AutoCalcCard
        # when non-custom material is selected
        MATERIAL_AUTO_FILLED = {
            "smooth_materials.shaft_e_mpa", "smooth_materials.shaft_nu",
            "smooth_materials.shaft_yield_mpa",
            "smooth_materials.hub_e_mpa", "smooth_materials.hub_nu",
            "smooth_materials.hub_yield_mpa",
        }
        mode_combo.setCurrentText("联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            if fid in MATERIAL_AUTO_FILLED:
                continue
            card = page._field_cards.get(fid)
            if card:
                assert card.objectName() == "SubCard", f"{fid} should be SubCard in combined mode"

    def test_mode_switch_updates_smooth_fit_chapter_title(self, app):
        page = SplineFitPage()
        mode_combo = page._widgets["mode"]

        mode_combo.setCurrentText("仅花键")
        assert "当前跳过" in page.chapter_list.item(2).text()

        mode_combo.setCurrentText("联合")
        assert "DIN 7190" in page.chapter_list.item(2).text()

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

    def test_snapshot_round_trip_preserves_ui_only_state(self, app):
        page = SplineFitPage()
        page._widgets["mode"].setCurrentText("联合")
        page._widgets["spline.standard_designation"].setCurrentText("W 25x1.25x18")
        page._widgets["spline.load_condition"].setCurrentText("自定义")
        page._widgets["spline.p_allowable_mpa"].setText("88")
        page._widgets["smooth_materials.shaft_material"].setCurrentText("自定义")
        page._widgets["smooth_materials.shaft_e_mpa"].setText("205000")

        snapshot = page._capture_input_snapshot()

        clone = SplineFitPage()
        clone._apply_input_data(snapshot)

        assert clone._widgets["mode"].currentText() == "联合"
        assert clone._widgets["spline.standard_designation"].currentText() == "W 25x1.25x18"
        assert clone._widgets["spline.load_condition"].currentText() == "自定义"
        assert clone._widgets["spline.p_allowable_mpa"].text() == "88"
        assert clone._widgets["smooth_materials.shaft_material"].currentText() == "自定义"
        assert clone._widgets["smooth_materials.shaft_e_mpa"].text() == "205000"

    def test_live_feedback_updates_result_without_manual_calculate(self, app):
        page = SplineFitPage()

        page._widgets["loads.torque_required_nm"].setText("100000")
        app.processEvents()

        assert page._result_labels["a_badge"].text() == "FAIL"
        assert page.message_box.toPlainText() != ""

    def test_material_autofills_with_blue_style(self, app):
        page = SplineFitPage()
        # material 相关控件仅在联合模式可用，测试环境需显式切换
        page._widgets["mode"].setCurrentText("联合")
        shaft_mat = page._widgets["smooth_materials.shaft_material"]
        shaft_mat.setCurrentText("40Cr")
        e_card = page._field_cards.get("smooth_materials.shaft_e_mpa")
        nu_card = page._field_cards.get("smooth_materials.shaft_nu")
        yield_card = page._field_cards.get("smooth_materials.shaft_yield_mpa")
        assert e_card.objectName() == "AutoCalcCard"
        assert nu_card.objectName() == "AutoCalcCard"
        assert yield_card.objectName() == "AutoCalcCard"
        # 切自定义恢复（仅在联合模式下解锁）
        shaft_mat.setCurrentText("自定义")
        assert e_card.objectName() == "SubCard"
        assert nu_card.objectName() == "SubCard"
        assert yield_card.objectName() == "SubCard"

    def test_material_custom_respects_mode_authority(self, app):
        """仅花键模式下即使 material=自定义 也保持 AutoCalcCard，守住 mode 权威不变量。"""
        page = SplineFitPage()
        page._widgets["mode"].setCurrentText("仅花键")
        shaft_mat = page._widgets["smooth_materials.shaft_material"]
        # 仅花键模式下 combo 本身 disabled，但编程方式仍可触发
        shaft_mat.setCurrentText("自定义")
        for fid in (
            "smooth_materials.shaft_e_mpa",
            "smooth_materials.shaft_nu",
            "smooth_materials.shaft_yield_mpa",
        ):
            assert page._field_cards[fid].objectName() == "AutoCalcCard"

    def test_material_choice_autofills_yield_strength(self, app):
        """选材料后屈服强度自动填充，切自定义可编辑（联合模式）。"""
        page = SplineFitPage()
        page._widgets["mode"].setCurrentText("联合")
        shaft_material = page._widgets["smooth_materials.shaft_material"]
        shaft_yield = page._widgets["smooth_materials.shaft_yield_mpa"]

        shaft_material.setCurrentText("40Cr")
        assert shaft_yield.text() == "785.0"

        shaft_material.setCurrentText("42CrMo")
        assert shaft_yield.text() == "930.0"

        shaft_material.setCurrentText("45钢")
        assert shaft_yield.text() == "355.0"

        shaft_material.setCurrentText("自定义")
        assert page._field_cards["smooth_materials.shaft_yield_mpa"].objectName() == "SubCard"

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

    def test_main_window_uses_connection_check_name_for_spline_module(self, app):
        window = MainWindow()
        items = [window.module_list.item(i).text() for i in range(window.module_list.count())]
        assert any("花键连接校核" in text for text in items)
        assert not any("花键过盈配合" in text for text in items)

    def test_payload_filters_smooth_sections_in_spline_only_mode(self, app):
        """仅花键模式下 payload 不包含 smooth_* 段，避免污染计算器输入。"""
        page = SplineFitPage()
        page._widgets["mode"].setCurrentText("仅花键")
        payload = page._build_payload()
        assert payload["mode"] == "spline_only"
        assert "smooth_fit" not in payload
        assert "smooth_materials" not in payload
        assert "smooth_roughness" not in payload
        assert "smooth_friction" not in payload
        # 联合模式恢复后 smooth_* 重新出现
        page._widgets["mode"].setCurrentText("联合")
        payload = page._build_payload()
        assert payload["mode"] == "combined"
        assert "smooth_fit" in payload
        assert "smooth_materials" in payload
