import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

from app.ui.field_schema import FieldSpec
from app.ui.pages.bolt_page import BOLT_GRADE_TABLE as PAGE_GRADE_TABLE
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from core.bolt.grades import BOLT_GRADE_CUSTOM, BOLT_GRADE_TABLE, rp02_source_zh

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


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

    def test_numeric_fields_reject_fullwidth_and_underscore_literals(self) -> None:
        page = BoltTappedAxialPage()

        for raw in ("1_000", "１２", "+1000", ".5", "1."):
            with self.subTest(raw=raw):
                page._field_widgets["service.FA_max"].setText(raw)  # type: ignore[attr-defined]
                with self.assertRaisesRegex(ValueError, "有效数字"):
                    page._build_payload()

    def test_numeric_fields_accept_scientific_notation(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("1.5e3")  # type: ignore[attr-defined]

        payload = page._build_payload()

        self.assertEqual(payload["service"]["FA_max"], 1500.0)

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
        self.assertFalse(page.btn_export_pdf.isEnabled())
        self.assertFalse(page.btn_export_text.isEnabled())
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        self.assertTrue(page.btn_export_pdf.isEnabled())
        self.assertTrue(page.btn_export_text.isEnabled())

    def test_input_change_invalidates_cache_and_exports(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        # 改任意输入字段
        page._field_widgets["service.FA_max"].setText("3000")  # type: ignore[attr-defined]
        self.assertIsNone(page._last_result)
        self.assertIsNone(page._last_payload)
        self.assertFalse(page.btn_export_pdf.isEnabled())
        self.assertFalse(page.btn_export_text.isEnabled())

    def test_clear_invalidates_cache_and_exports(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        self.assertIsNotNone(page._last_result)
        page._clear()
        self.assertIsNone(page._last_result)
        self.assertIsNone(page._last_payload)
        self.assertFalse(page.btn_export_pdf.isEnabled())
        self.assertFalse(page.btn_export_text.isEnabled())

    def test_apply_input_data_invalidates_cache(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()
        snapshot = page._capture_input_snapshot()
        # apply 后缓存必须失效
        page._apply_input_data(snapshot)
        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_export_pdf.isEnabled())
        self.assertFalse(page.btn_export_text.isEnabled())

    def test_text_report_button_exports_report_lines(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")  # type: ignore[attr-defined]
        page._run_calculation()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "tapped_axial_report.txt"
            with patch(
                "app.ui.pages.bolt_tapped_axial_page.export_report_lines",
                return_value=out,
            ) as export:
                page._export_text_report()

        export.assert_called_once()
        parent, title, default_path, lines = export.call_args.args
        self.assertIs(parent, page)
        self.assertEqual(title, "导出文本报告")
        self.assertEqual(default_path.name, "tapped_axial_report.txt")
        self.assertIn("轴向受力螺纹连接校核报告", "\n".join(lines))

    # --- INPUT-S01：强度等级 → Rp0.2 单一事实源 ---

    def test_shared_grade_table_matches_bolt_page(self) -> None:
        self.assertIs(PAGE_GRADE_TABLE, BOLT_GRADE_TABLE)
        self.assertEqual(BOLT_GRADE_TABLE["8.8"], 640)
        self.assertEqual(BOLT_GRADE_TABLE["10.9"], 900)
        self.assertEqual(BOLT_GRADE_TABLE["12.9"], 1080)
        self.assertEqual(rp02_source_zh("10.9"), "预设等级 10.9")
        self.assertEqual(rp02_source_zh(BOLT_GRADE_CUSTOM), "用户值")

    def test_grade_presets_fill_rp02_and_lock_field(self) -> None:
        page = BoltTappedAxialPage()
        grade = page._field_widgets["fastener.grade"]
        rp02 = page._field_widgets["fastener.Rp02"]
        self.assertIsInstance(rp02, QLineEdit)

        for value, expected in (("8.8", "640"), ("10.9", "900"), ("12.9", "1080")):
            with self.subTest(grade=value):
                grade.setCurrentText(value)
                self.assertEqual(rp02.text(), expected)
                self.assertTrue(rp02.isReadOnly())
                self.assertEqual(
                    page._field_cards["fastener.Rp02"].objectName(),
                    "AutoCalcCard",
                )

    def test_custom_grade_makes_rp02_editable(self) -> None:
        page = BoltTappedAxialPage()
        grade = page._field_widgets["fastener.grade"]
        rp02 = page._field_widgets["fastener.Rp02"]
        self.assertTrue(rp02.isReadOnly())

        grade.setCurrentText(BOLT_GRADE_CUSTOM)

        self.assertFalse(rp02.isReadOnly())
        self.assertEqual(rp02.text(), "")
        self.assertEqual(page._field_cards["fastener.Rp02"].objectName(), "SubCard")

    def test_payload_contains_matching_grade_and_rp02(self) -> None:
        page = BoltTappedAxialPage()
        payload = page._build_payload()
        self.assertEqual(payload["fastener"]["grade"], "8.8")
        self.assertEqual(payload["fastener"]["Rp02"], 640.0)

        page._field_widgets["fastener.grade"].setCurrentText("10.9")
        payload = page._build_payload()
        self.assertEqual(payload["fastener"]["grade"], "10.9")
        self.assertEqual(payload["fastener"]["Rp02"], 900.0)

        page._field_widgets["fastener.grade"].setCurrentText("12.9")
        payload = page._build_payload()
        self.assertEqual(payload["fastener"]["grade"], "12.9")
        self.assertEqual(payload["fastener"]["Rp02"], 1080.0)

        page._field_widgets["fastener.grade"].setCurrentText(BOLT_GRADE_CUSTOM)
        page._field_widgets["fastener.Rp02"].setText("450")
        payload = page._build_payload()
        self.assertEqual(payload["fastener"]["grade"], BOLT_GRADE_CUSTOM)
        self.assertEqual(payload["fastener"]["Rp02"], 450.0)

    def test_grade_change_disables_export(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        self.assertTrue(page.btn_export_pdf.isEnabled())
        self.assertTrue(page.btn_export_text.isEnabled())

        page._field_widgets["fastener.grade"].setCurrentText("10.9")

        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_export_pdf.isEnabled())
        self.assertFalse(page.btn_export_text.isEnabled())

    def test_load_matching_grade_does_not_prompt(self) -> None:
        page = BoltTappedAxialPage()
        data = json.loads(
            (EXAMPLES_DIR / "tapped_axial_joint_case_01.json").read_text(
                encoding="utf-8"
            )
        )
        with patch.object(page, "_confirm_grade_rp02_mismatch") as confirm:
            page._apply_input_data(data)

        confirm.assert_not_called()
        self.assertEqual(page._field_widgets["fastener.grade"].currentText(), "8.8")
        self.assertEqual(float(page._field_widgets["fastener.Rp02"].text()), 640.0)
        self.assertTrue(page._field_widgets["fastener.Rp02"].isReadOnly())

    def test_load_mismatched_grade_does_not_silently_overwrite(self) -> None:
        page = BoltTappedAxialPage()
        data = json.loads(
            (EXAMPLES_DIR / "tapped_axial_joint_case_02.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["fastener"]["grade"], "10.9")
        self.assertEqual(data["fastener"]["Rp02"], 940.0)

        with patch.object(
            page, "_confirm_grade_rp02_mismatch", return_value="keep_file"
        ) as confirm:
            page._apply_input_data(data)

        confirm.assert_called_once()
        grade, stored, table = confirm.call_args.args
        self.assertEqual(grade, "10.9")
        self.assertEqual(stored, 940.0)
        self.assertEqual(table, 900.0)
        self.assertEqual(
            page._field_widgets["fastener.grade"].currentText(),
            BOLT_GRADE_CUSTOM,
        )
        self.assertEqual(float(page._field_widgets["fastener.Rp02"].text()), 940.0)
        self.assertFalse(page._field_widgets["fastener.Rp02"].isReadOnly())
        self.assertFalse(page.btn_export_pdf.isEnabled())

    def test_load_mismatched_grade_can_apply_table_after_confirm(self) -> None:
        page = BoltTappedAxialPage()
        data = json.loads(
            (EXAMPLES_DIR / "tapped_axial_joint_case_02.json").read_text(
                encoding="utf-8"
            )
        )
        with patch.object(
            page, "_confirm_grade_rp02_mismatch", return_value="use_table"
        ):
            page._apply_input_data(data)

        self.assertEqual(page._field_widgets["fastener.grade"].currentText(), "10.9")
        self.assertEqual(page._field_widgets["fastener.Rp02"].text(), "900")
        self.assertTrue(page._field_widgets["fastener.Rp02"].isReadOnly())

    def test_report_lines_show_rp02_source(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")
        page._run_calculation()
        preset_text = "\n".join(page._build_report_lines())
        self.assertIn("预设等级 8.8", preset_text)
        self.assertIn("强度等级: 8.8", preset_text)

        page._field_widgets["fastener.grade"].setCurrentText(BOLT_GRADE_CUSTOM)
        page._field_widgets["fastener.Rp02"].setText("450")
        page._run_calculation()
        custom_text = "\n".join(page._build_report_lines())
        self.assertIn("用户值", custom_text)
        self.assertIn(f"强度等级: {BOLT_GRADE_CUSTOM}", custom_text)

    def test_safety_required_live_error_for_value_below_one(self) -> None:
        page = BoltTappedAxialPage()
        widget = page._field_widgets["thread_strip.safety_required"]
        error = page._field_error_labels["thread_strip.safety_required"]
        self.assertTrue(error.isHidden())

        widget.setText("0.5")

        self.assertFalse(error.isHidden())
        self.assertIn(">= 1.0", error.text())
        self.assertIn(widget.property("fieldError"), (True, "true"))
        self.assertTrue(page.btn_calculate.isEnabled())

        widget.setText("1.5")

        self.assertTrue(error.isHidden())
        self.assertIn(widget.property("fieldError"), (False, "false", None))

    def test_calculate_with_invalid_safety_shows_errors_and_skips_result(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["thread_strip.safety_required"].setText("0.5")
        page._field_widgets["service.FA_max"].setText("abc")

        with patch.object(QMessageBox, "critical", side_effect=AssertionError("no dialog")):
            page._run_calculation()

        self.assertIsNone(page._last_result)
        self.assertFalse(page.btn_export_pdf.isEnabled())
        self.assertTrue(page.btn_calculate.isEnabled())
        safety_error = page._field_error_labels["thread_strip.safety_required"]
        fa_error = page._field_error_labels["service.FA_max"]
        self.assertFalse(safety_error.isHidden())
        self.assertFalse(fa_error.isHidden())
        self.assertEqual(page.chapter_list.currentRow(), 3)
        self.assertIn("字段需要修正", page.info_label.text())

    def test_payload_omits_mapping_none_fields(self) -> None:
        page = BoltTappedAxialPage()
        spec = FieldSpec(
            "notes",
            "备注",
            "-",
            "",
            mapping=None,
            value_type="text",
            required=False,
            default="should-not-land",
        )
        editor = QLineEdit(page)
        editor.setText("should-not-land")
        page._field_specs[spec.field_id] = spec
        page._field_widgets[spec.field_id] = editor

        payload = page._build_payload()

        self.assertNotIn("notes", payload)
        dumped = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("should-not-land", dumped)
        self.assertIn("fastener", payload)


if __name__ == "__main__":
    unittest.main()
