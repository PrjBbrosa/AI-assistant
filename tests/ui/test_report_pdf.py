"""Tests for the professional PDF report generator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ui.report_pdf import build_bolt_recommendations, generate_bolt_report
from core.bolt.calculator import calculate_vdi2230_core

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _load_example(name: str = "input_case_01.json") -> dict:
    return json.loads((EXAMPLES_DIR / name).read_text())


def _run_calc(data: dict) -> dict:
    return calculate_vdi2230_core(data)


class TestGenerateBoltReport:
    def test_basic_report_creates_nonempty_pdf(self, tmp_path: Path) -> None:
        data = _load_example()
        result = _run_calc(data)
        out = tmp_path / "report.pdf"
        generate_bolt_report(out, data, result)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_fatigue_report_creates_larger_pdf(self, tmp_path: Path) -> None:
        data = _load_example()
        data["options"]["check_level"] = "fatigue"
        data.setdefault("options", {})["surface_treatment"] = "rolled"
        result = _run_calc(data)
        out = tmp_path / "report_fatigue.pdf"
        generate_bolt_report(out, data, result)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_report_with_thread_strip(self, tmp_path: Path) -> None:
        data = _load_example()
        data["thread_strip"] = {"m_eff": 12, "tau_BM": 400, "safety_required": 1.25}
        result = _run_calc(data)
        out = tmp_path / "report_strip.pdf"
        generate_bolt_report(out, data, result)
        assert out.exists()
        assert "thread_strip_ok" in result["checks"]

    def test_report_with_auto_compliance(self, tmp_path: Path) -> None:
        data = _load_example()
        data["stiffness"] = {
            "auto_compliance": True,
            "E_clamped": 210000,
            "load_introduction_factor_n": 0.5,
        }
        data["clamped"]["basic_solid"] = "cylinder"
        data["clamped"]["D_A"] = 24
        result = _run_calc(data)
        out = tmp_path / "report_auto.pdf"
        generate_bolt_report(out, data, result)
        assert out.exists()
        assert result["stiffness_model"]["auto_modeled"]


class TestBuildBoltRecommendations:
    def test_all_pass_gives_positive_message(self) -> None:
        result = {"checks": {
            "residual_clamp_ok": True,
            "assembly_von_mises_ok": True,
            "operating_axial_ok": True,
        }}
        recs = build_bolt_recommendations(result)
        assert len(recs) == 1
        assert "满足" in recs[0]

    def test_fail_checks_give_specific_recommendations(self) -> None:
        result = {"checks": {
            "residual_clamp_ok": False,
            "assembly_von_mises_ok": False,
            "operating_axial_ok": True,
        }}
        recs = build_bolt_recommendations(result)
        assert len(recs) == 2
        assert any("夹紧力" in r for r in recs)
        assert any("装配应力" in r for r in recs)

    def test_thread_strip_fail_recommendation(self) -> None:
        result = {
            "checks": {"thread_strip_ok": False},
            "thread_strip": {"critical_side": "nut"},
        }
        recs = build_bolt_recommendations(result)
        assert any("壳体侧" in r for r in recs)
