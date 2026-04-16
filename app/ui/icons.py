"""Application icon helpers."""

from __future__ import annotations

import platform
import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def _resource_root() -> Path:
    """Resolve the app resource root for source and PyInstaller builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "app"
    return Path(__file__).resolve().parents[1]


def app_icon_path() -> Path:
    assets_dir = _resource_root() / "assets"
    if platform.system() == "Windows":
        icon_path = assets_dir / "assistant_icon.ico"
        if icon_path.exists():
            return icon_path
    return assets_dir / "assistant_icon.png"


def load_app_icon() -> QIcon:
    return QIcon(str(app_icon_path()))
