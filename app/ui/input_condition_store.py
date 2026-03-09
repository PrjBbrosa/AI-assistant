"""Shared helpers for persisting engineering page input conditions."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QFileDialog, QWidget


INPUT_FILTER = "JSON Files (*.json);;All Files (*)"


def build_saved_inputs_dir(project_root: Path) -> Path:
    """Return the default project-local directory for saved input files."""
    return project_root / "saved_inputs"


def build_form_snapshot(
    field_specs: Iterable[Any],
    read_value: Callable[[Any], str],
    *,
    extra_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Split current form values into mapped inputs and UI-only state."""
    inputs: dict[str, dict[str, Any]] = {}
    ui_state: dict[str, Any] = {}
    for spec in field_specs:
        value = read_value(spec)
        if value == "":
            continue
        mapping = getattr(spec, "mapping", None)
        if mapping is None:
            ui_state[getattr(spec, "field_id")] = value
            continue
        section, key = mapping
        inputs.setdefault(section, {})[key] = value
    if extra_state:
        ui_state.update(extra_state)
    snapshot: dict[str, Any] = {"inputs": inputs}
    if ui_state:
        snapshot["ui_state"] = ui_state
    return snapshot


def write_input_conditions(out_path: Path, payload: dict[str, Any]) -> None:
    """Write input conditions as UTF-8 JSON, creating parent directories."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_input_conditions(in_path: Path) -> dict[str, Any]:
    """Read a JSON input-condition file."""
    return json.loads(in_path.read_text(encoding="utf-8"))


def choose_save_input_conditions_path(
    parent: QWidget,
    dialog_title: str,
    default_path: Path,
) -> Path | None:
    """Prompt for an output JSON path inside the saved-inputs directory."""
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        dialog_title,
        str(default_path),
        INPUT_FILTER,
    )
    if not file_path:
        return None
    out_path = Path(file_path)
    if out_path.suffix.lower() != ".json":
        out_path = out_path.with_suffix(".json")
    return out_path


def choose_load_input_conditions_path(
    parent: QWidget,
    dialog_title: str,
    default_dir: Path,
) -> Path | None:
    """Prompt for an existing input-condition JSON file."""
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        dialog_title,
        str(default_dir),
        INPUT_FILTER,
    )
    if not file_path:
        return None
    return Path(file_path)
