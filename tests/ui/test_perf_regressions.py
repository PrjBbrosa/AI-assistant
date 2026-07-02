"""Performance and dead-code regression tests for PySide UI pages."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.pages import worm_gear_page
from app.ui.pages.spline_fit_page import SplineFitPage


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
