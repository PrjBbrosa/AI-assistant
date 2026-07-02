import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui import input_condition_store
from app.ui.input_condition_store import (
    build_form_snapshot,
    build_saved_inputs_dir,
    read_input_conditions,
    write_input_conditions,
)
from app.ui.pages.base_chapter_page import BaseChapterPage


@dataclass(frozen=True)
class DummyFieldSpec:
    field_id: str
    mapping: tuple[str, str] | None = None


class InputConditionStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_build_saved_inputs_dir_uses_project_saved_inputs_folder(self) -> None:
        root = Path("/tmp/project-root")
        self.assertEqual(build_saved_inputs_dir(root), root / "saved_inputs")

    def test_write_and_read_input_conditions_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "case.json"
            payload = {"geometry": {"d": 40.0}, "loads": {"f": 1200.0}}

            write_input_conditions(out_path, payload)
            loaded = read_input_conditions(out_path)

            self.assertEqual(loaded, payload)

    def test_build_form_snapshot_splits_inputs_and_ui_state(self) -> None:
        specs = [
            DummyFieldSpec("geometry.shaft_d_mm", ("geometry", "shaft_d_mm")),
            DummyFieldSpec("materials.shaft_material"),
            DummyFieldSpec("roughness.profile"),
            DummyFieldSpec("fit.mode"),
            DummyFieldSpec("fit.preferred_fit_name"),
            DummyFieldSpec("assembly.method"),
            DummyFieldSpec("assembly.clearance_mode"),
            DummyFieldSpec("advanced.repeated_load_mode"),
        ]
        values = {
            "geometry.shaft_d_mm": "40.0",
            "materials.shaft_material": "45钢",
            "roughness.profile": "DIN 7190-1:2017（k=0.4）",
            "fit.mode": "优选配合",
            "fit.preferred_fit_name": "H7/s6",
            "assembly.method": "force_fit",
            "assembly.clearance_mode": "diameter_rule",
            "advanced.repeated_load_mode": "on",
        }

        snapshot = build_form_snapshot(
            specs,
            lambda spec: values[spec.field_id],
            extra_state={"check_level": "fatigue"},
        )

        self.assertEqual(
            snapshot,
            {
                "inputs": {"geometry": {"shaft_d_mm": "40.0"}},
                "ui_state": {
                    "materials.shaft_material": "45钢",
                    "roughness.profile": "DIN 7190-1:2017（k=0.4）",
                    "fit.mode": "优选配合",
                    "fit.preferred_fit_name": "H7/s6",
                    "assembly.method": "force_fit",
                    "assembly.clearance_mode": "diameter_rule",
                    "advanced.repeated_load_mode": "on",
                    "check_level": "fatigue",
                },
            },
        )

    def test_validate_snapshot_rejects_non_dict_json_root(self) -> None:
        with self.assertRaisesRegex(input_condition_store.InputConditionError, "JSON 对象"):
            input_condition_store.validate_snapshot(["not", "an", "object"])

    def test_validate_snapshot_returns_dict_without_copying(self) -> None:
        payload = {"inputs": {"geometry": {"diameter": "40"}}}

        validated = input_condition_store.validate_snapshot(payload)

        self.assertIs(validated, payload)

    def test_build_form_snapshot_writes_and_omits_module_id(self) -> None:
        specs = [DummyFieldSpec("geometry.d_mm", ("geometry", "d_mm"))]
        values = {"geometry.d_mm": "40"}

        snapshot = build_form_snapshot(specs, lambda spec: values[spec.field_id])
        tagged = build_form_snapshot(
            specs,
            lambda spec: values[spec.field_id],
            module_id="hertz_contact",
        )

        self.assertNotIn("module", snapshot)
        self.assertEqual(tagged["module"], "hertz_contact")

    def test_hertz_load_rejects_non_dict_json_without_crashing(self) -> None:
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from app.ui.pages import hertz_contact_page

        page = hertz_contact_page.HertzContactPage()
        with tempfile.TemporaryDirectory() as tmp:
            in_path = Path(tmp) / "bad.json"
            in_path.write_text("[\"not\", \"object\"]", encoding="utf-8")

            with (
                patch(
                    "app.ui.pages.hertz_contact_page.choose_load_input_conditions_path",
                    return_value=in_path,
                ),
                patch.object(QMessageBox, "critical", return_value=None) as critical,
            ):
                page._load_input_conditions()

        critical.assert_called_once()
        self.assertEqual(critical.call_args.args[1], "文件格式错误")
        self.assertIn("JSON 对象", critical.call_args.args[2])

    def test_hertz_load_mismatched_module_aborts_when_user_declines(self) -> None:
        from unittest.mock import patch

        from PySide6.QtWidgets import QMessageBox

        from app.ui.pages import hertz_contact_page

        page = hertz_contact_page.HertzContactPage()
        with tempfile.TemporaryDirectory() as tmp:
            in_path = Path(tmp) / "other_module.json"
            write_input_conditions(in_path, {"module": "worm_gear", "inputs": {}})

            with (
                patch(
                    "app.ui.pages.hertz_contact_page.choose_load_input_conditions_path",
                    return_value=in_path,
                ),
                patch.object(
                    QMessageBox,
                    "question",
                    return_value=QMessageBox.StandardButton.No,
                ) as question,
                patch.object(page, "_apply_input_data") as apply_input_data,
            ):
                page._load_input_conditions()

        question.assert_called_once()
        apply_input_data.assert_not_called()


class BaseChapterPageActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_add_action_button_supports_left_and_right_groups(self) -> None:
        page = BaseChapterPage("Title", "Subtitle")

        left = page.add_action_button("保存输入条件")
        right = page.add_action_button("测试案例 1", side="right")

        self.assertEqual(page.left_actions_layout.count(), 1)
        self.assertEqual(page.right_actions_layout.count(), 1)
        self.assertIs(page.left_actions_layout.itemAt(0).widget(), left)
        self.assertIs(page.right_actions_layout.itemAt(0).widget(), right)


if __name__ == "__main__":
    unittest.main()
