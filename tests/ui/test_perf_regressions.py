"""Performance and dead-code regression tests for PySide UI pages."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from app.ui.pages import worm_gear_page
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


def test_worm_calculate_calls_core_geometry_once(app, monkeypatch) -> None:
    page = worm_gear_page.WormGearPage()
    original = worm_gear_page.calculate_worm_geometry
    calls = {"count": 0}

    def counting_calculate(payload):
        calls["count"] += 1
        return original(payload)

    monkeypatch.setattr(worm_gear_page, "calculate_worm_geometry", counting_calculate)

    page._calculate()

    assert calls["count"] == 1


def test_worm_render_does_not_fallback_to_thermal_capacity_curve(app) -> None:
    page = worm_gear_page.WormGearPage()
    payload = page._build_payload()
    result = worm_gear_page.calculate_worm_geometry(payload)
    result["curve"].pop("temperature_rise_k", None)
    result["curve"]["thermal_capacity_kw"] = [1.0 for _ in result["curve"]["power_loss_kw"]]
    page._last_payload = payload

    page._render_result(result)

    assert page.performance_curve._temperature_rise_k == []


def test_spline_live_recalculation_uses_300ms_single_shot_timer(app) -> None:
    page = SplineFitPage()

    assert page._recalc_timer.interval() == 300
    assert page._recalc_timer.isSingleShot()


def test_worm_page_init_does_not_construct_stress_curve_widget(app, monkeypatch) -> None:
    constructed = {"count": 0}
    original = worm_gear_page.WormStressCurveWidget

    class CountingWidget(original):
        def __init__(self, *args, **kwargs):
            constructed["count"] += 1
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(worm_gear_page, "WormStressCurveWidget", CountingWidget)
    page = worm_gear_page.WormGearPage()

    assert constructed["count"] == 0
    assert not isinstance(page.stress_curve, original)
    assert isinstance(page.stress_curve, QWidget)
    assert page.stress_curve.minimumHeight() >= 350
    assert page._stress_curve_ready is False

    page._ensure_stress_curve()
    assert constructed["count"] == 1
    assert isinstance(page.stress_curve, original)
    assert page._stress_curve_ready is True

    page._ensure_stress_curve()
    assert constructed["count"] == 1


def test_worm_graphics_chapter_constructs_stress_curve_widget(app, monkeypatch) -> None:
    constructed = {"count": 0}
    original = worm_gear_page.WormStressCurveWidget

    class CountingWidget(original):
        def __init__(self, *args, **kwargs):
            constructed["count"] += 1
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(worm_gear_page, "WormStressCurveWidget", CountingWidget)
    page = worm_gear_page.WormGearPage()
    assert constructed["count"] == 0

    page.set_current_chapter(page._graphics_chapter_index)

    assert constructed["count"] == 1
    assert isinstance(page.stress_curve, original)


def test_worm_calculate_with_curve_data_constructs_stress_curve_widget(app) -> None:
    page = worm_gear_page.WormGearPage()
    assert not isinstance(page.stress_curve, WormStressCurveWidget)

    page._calculate()

    assert isinstance(page.stress_curve, WormStressCurveWidget)
    assert page.stress_curve._theta_deg


def test_worm_page_init_does_not_import_matplotlib() -> None:
    """Fresh interpreter: constructing WormGearPage must not import matplotlib.

    In-process pytest always loads matplotlib via tests/conftest.py, so this
    probe runs in a subprocess with the repo on PYTHONPATH.
    """
    repo = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(repo) if not existing else os.pathsep.join((str(repo), existing))
    script = (
        "import os, sys\n"
        "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
        "assert 'matplotlib' not in sys.modules\n"
        "from PySide6.QtWidgets import QApplication\n"
        "app = QApplication.instance() or QApplication([])\n"
        "from app.ui.pages.worm_gear_page import WormGearPage\n"
        "from app.ui.widgets.worm_stress_curve import WormStressCurveWidget\n"
        "assert 'matplotlib' not in sys.modules\n"
        "page = WormGearPage()\n"
        "assert 'matplotlib' not in sys.modules\n"
        "assert not isinstance(page.stress_curve, WormStressCurveWidget)\n"
        "page._ensure_stress_curve()\n"
        "assert 'matplotlib' in sys.modules\n"
        "assert isinstance(page.stress_curve, WormStressCurveWidget)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
