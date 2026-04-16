import math
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage


class BoltTappedAxialPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_page_builds_expected_chapters(self) -> None:
        page = BoltTappedAxialPage()

        titles = [page.chapter_list.item(i).text() for i in range(page.chapter_list.count())]

        self.assertTrue(any("适用范围" in title for title in titles))
        self.assertTrue(any("交变轴向疲劳" in title for title in titles))

    def test_page_exposes_spec_fields_without_clamped_or_stiffness(self) -> None:
        page = BoltTappedAxialPage()

        self.assertIn("fastener.d", page._field_widgets)  # type: ignore[attr-defined]
        self.assertIn("assembly.F_preload_min", page._field_widgets)  # type: ignore[attr-defined]
        self.assertIn("service.FA_min", page._field_widgets)  # type: ignore[attr-defined]
        self.assertIn("fatigue.surface_treatment", page._field_widgets)  # type: ignore[attr-defined]
        self.assertNotIn("clamped.parts", page._field_widgets)  # type: ignore[attr-defined]
        self.assertNotIn("stiffness.delta_p", page._field_widgets)  # type: ignore[attr-defined]

    def test_build_payload_matches_new_schema(self) -> None:
        page = BoltTappedAxialPage()

        payload = page._build_payload()

        self.assertIn("fastener", payload)
        self.assertIn("assembly", payload)
        self.assertIn("service", payload)
        self.assertIn("fatigue", payload)
        self.assertIn("thread_strip", payload)
        self.assertIn("checks", payload)
        self.assertIn("options", payload)
        self.assertNotIn("clamped", payload)
        self.assertNotIn("stiffness", payload)
        self.assertEqual(payload["assembly"]["tightening_method"], "torque")
        self.assertEqual(payload["fatigue"]["surface_treatment"], "rolled")
        self.assertEqual(payload["options"]["report_mode"], "full")

    def test_snapshot_round_trip_preserves_service_range_and_surface_treatment(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_min"].setText("2000")  # type: ignore[attr-defined]
        page._field_widgets["service.FA_max"].setText("8000")  # type: ignore[attr-defined]
        page._field_widgets["fatigue.surface_treatment"].setCurrentText("cut")  # type: ignore[attr-defined]

        snapshot = page._capture_input_snapshot()

        clone = BoltTappedAxialPage()
        clone._apply_input_data(snapshot)

        self.assertEqual(clone._field_widgets["service.FA_min"].text(), "2000")  # type: ignore[attr-defined]
        self.assertEqual(clone._field_widgets["service.FA_max"].text(), "8000")  # type: ignore[attr-defined]
        self.assertEqual(clone._field_widgets["fatigue.surface_treatment"].currentText(), "cut")  # type: ignore[attr-defined]


    def test_run_calculation_sets_result_title_pass(self) -> None:
        """执行计算后标题非空，取值属于新三态中的任意一种（pass/fail/incomplete）."""
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        self.assertIn(
            page.result_title.text(),
            ("校核通过", "校核不通过", "校核不完整"),
        )

    def test_run_calculation_populates_check_badges(self) -> None:
        """徽标文本允许 "通过/不通过/未校核" 三态；未校核对应 m_eff 未填的脱扣项."""
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        for key, badge in page._check_badges.items():
            self.assertIn(badge.text(), ("通过", "不通过", "未校核"))

    def test_missing_m_eff_shows_incomplete_status_and_unchecked_badge(self) -> None:
        """Codex §3.3：未填啮合长度时，螺纹脱扣徽标为"未校核"，整体为校核不完整."""
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        strip_badge = page._check_badges["thread_strip_ok"]
        self.assertEqual(strip_badge.text(), "未校核")
        self.assertEqual(strip_badge.objectName(), "WaitBadge")
        # 总体结论标题
        self.assertEqual(page.result_title.text(), "校核不完整")
        # _last_result 反映 overall_status
        self.assertEqual(page._last_result["overall_status"], "incomplete")  # type: ignore[index]
        self.assertFalse(page._last_result["overall_pass"])  # type: ignore[index]

    def test_m_eff_provided_shows_pass_or_fail_overall(self) -> None:
        """填入 m_eff 与对手件参数后，脱扣徽标不再为"未校核"，整体在 pass/fail 二选一."""
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._field_widgets["thread_strip.m_eff"].setText("10.0")  # type: ignore[attr-defined]
        page._field_widgets["thread_strip.tau_BM"].setText("350.0")  # type: ignore[attr-defined]
        page._field_widgets["thread_strip.tau_BS"].setText("400.0")  # type: ignore[attr-defined]
        page._run_calculation()
        strip_badge = page._check_badges["thread_strip_ok"]
        self.assertIn(strip_badge.text(), ("通过", "不通过"))
        self.assertIn(page._last_result["overall_status"], ("pass", "fail"))  # type: ignore[index]

    def test_run_calculation_populates_metrics_text(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        text = page.metrics_text.text()
        self.assertIn("预紧力范围", text)
        self.assertIn("装配 von Mises", text)
        self.assertIn("疲劳应力幅", text)

    def test_build_report_lines_contains_scope_note(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        lines = page._build_report_lines()
        report_text = "\n".join(lines)
        self.assertIn("轴向受力螺纹连接校核报告", report_text)
        self.assertIn("适用范围", report_text)
        self.assertIn("螺纹脱扣", report_text)
        self.assertNotIn("FK_residual", report_text)

    # --- Codex §3.2 / §3.4：As/d2/d3 自动派生 + 缓存失效 ---

    def test_thread_section_fields_are_autocalccard_readonly(self) -> None:
        """As/d2/d3 不再允许手动编辑，以避免旧截面残留与新规格混算."""
        page = BoltTappedAxialPage()
        for fid in ("fastener.As", "fastener.d2", "fastener.d3"):
            card = page._field_cards[fid]
            self.assertEqual(
                card.objectName(), "AutoCalcCard",
                f"{fid} 应为 AutoCalcCard，实际 {card.objectName()}",
            )
            widget = page._field_widgets[fid]
            self.assertTrue(
                widget.isReadOnly(),  # type: ignore[attr-defined]
                f"{fid} 应 readOnly",
            )

    def test_changing_d_refreshes_as_d2_d3(self) -> None:
        """改 d/p 后 As/d2/d3 字段应自动按 ISO 898-1 公式重算."""
        page = BoltTappedAxialPage()
        page._field_widgets["fastener.d"].setText("12")  # type: ignore[attr-defined]
        page._field_widgets["fastener.p"].setText("1.75")  # type: ignore[attr-defined]
        expected_as = math.pi / 4.0 * (12.0 - 0.9382 * 1.75) ** 2
        expected_d2 = 12.0 - 0.64952 * 1.75
        expected_d3 = 12.0 - 1.22687 * 1.75
        self.assertAlmostEqual(
            float(page._field_widgets["fastener.As"].text()),  # type: ignore[attr-defined]
            expected_as, places=3,
        )
        self.assertAlmostEqual(
            float(page._field_widgets["fastener.d2"].text()),  # type: ignore[attr-defined]
            expected_d2, places=4,
        )
        self.assertAlmostEqual(
            float(page._field_widgets["fastener.d3"].text()),  # type: ignore[attr-defined]
            expected_d3, places=4,
        )

    def test_export_buttons_disabled_until_calculate(self) -> None:
        page = BoltTappedAxialPage()
        self.assertFalse(page.btn_export_text.isEnabled())
        self.assertFalse(page.btn_export_pdf.isEnabled())
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        self.assertTrue(page.btn_export_text.isEnabled())
        self.assertTrue(page.btn_export_pdf.isEnabled())

    def test_input_change_invalidates_cache_and_exports(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        # 改任意输入字段
        page._field_widgets["service.FA_max"].setText("3000")  # type: ignore[attr-defined]
        self.assertIsNone(page._last_result)
        self.assertIsNone(page._last_payload)
        self.assertFalse(page.btn_export_text.isEnabled())
        self.assertFalse(page.btn_export_pdf.isEnabled())

    def test_clear_invalidates_cache_and_exports(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        page._clear()
        self.assertIsNone(page._last_result)
        self.assertIsNone(page._last_payload)
        self.assertFalse(page.btn_export_text.isEnabled())

    def test_apply_input_data_invalidates_cache(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        snapshot = page._capture_input_snapshot()
        # apply 后缓存必须失效
        page._apply_input_data(snapshot)
        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_export_text.isEnabled())


if __name__ == "__main__":
    unittest.main()
