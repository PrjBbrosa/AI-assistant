import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

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
