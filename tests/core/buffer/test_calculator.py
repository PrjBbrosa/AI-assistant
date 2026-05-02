"""Tests for buffer energy calculator core."""

from __future__ import annotations

import math
import unittest

from core.buffer.calculator import (
    InputError,
    _accumulate_loading_energy,
    _build_checks,
    _curve_summary,
    _estimate_rebound,
    _normalize_curve,
    _solve_impact,
    _tangent_stiffness_range,
    _trapezoid_area,
    calculate_buffer_energy,
)


def _linear_loading(k_n_per_mm: float, x_max_mm: float, n: int = 21) -> list[dict[str, float]]:
    step = x_max_mm / (n - 1)
    return [{"x_mm": i * step, "force_n": k_n_per_mm * i * step} for i in range(n)]


class CurveNormalizationTests(unittest.TestCase):
    def test_sorts_and_dedups_points(self) -> None:
        raw = [
            {"x_mm": 5.0, "force_n": 800.0},
            {"x_mm": 0.0, "force_n": 0.0},
            {"x_mm": 5.0, "force_n": 820.0},
            {"x_mm": 10.0, "force_n": 1800.0},
        ]
        norm, warnings = _normalize_curve(raw, "loading", force_scale=1.0, stroke_scale=1.0)
        self.assertEqual([p["x_mm"] for p in norm], [0.0, 5.0, 10.0])
        self.assertAlmostEqual(norm[1]["force_n"], 810.0, places=6)
        self.assertEqual(warnings, [])

    def test_inserts_origin_when_missing(self) -> None:
        raw = [
            {"x_mm": 2.0, "force_n": 200.0},
            {"x_mm": 5.0, "force_n": 800.0},
        ]
        norm, warnings = _normalize_curve(raw, "loading", force_scale=1.0, stroke_scale=1.0)
        self.assertEqual(norm[0], {"x_mm": 0.0, "force_n": 0.0})
        self.assertTrue(any("起点" in w for w in warnings))

    def test_applies_scales(self) -> None:
        raw = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 1000.0}]
        norm, _ = _normalize_curve(raw, "loading", force_scale=2.0, stroke_scale=0.5)
        self.assertEqual(norm[-1], {"x_mm": 5.0, "force_n": 2000.0})

    def test_rejects_negative_force(self) -> None:
        raw = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 5.0, "force_n": -10.0}]
        with self.assertRaises(InputError):
            _normalize_curve(raw, "loading", force_scale=1.0, stroke_scale=1.0)


class EnergyIntegrationTests(unittest.TestCase):
    def test_triangle_loading_energy_matches_analytic(self) -> None:
        pts = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 2.5, 5.0, 7.5, 10.0)]
        e_x, e_j = _accumulate_loading_energy(pts)
        self.assertAlmostEqual(e_j[-1], 10.0, places=4)
        self.assertEqual(len(e_x), len(e_j))
        self.assertEqual(e_j[0], 0.0)

    def test_trapezoid_area_unit_conversion(self) -> None:
        pts = [{"x_mm": 0.0, "force_n": 1.0}, {"x_mm": 1.0, "force_n": 1.0}]
        self.assertAlmostEqual(_trapezoid_area(pts), 0.001, places=9)

    def test_tangent_stiffness_range(self) -> None:
        pts = [
            {"x_mm": 0.0, "force_n": 0.0},
            {"x_mm": 5.0, "force_n": 500.0},
            {"x_mm": 10.0, "force_n": 2000.0},
        ]
        k_min, k_max = _tangent_stiffness_range(pts)
        self.assertAlmostEqual(k_min, 100.0)
        self.assertAlmostEqual(k_max, 300.0)

    def test_curve_summary_fields_present(self) -> None:
        loading = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 2000.0}]
        unloading = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 1000.0}]
        summary = _curve_summary(loading, unloading)
        self.assertAlmostEqual(summary["max_stroke_mm"], 10.0)
        self.assertAlmostEqual(summary["peak_loading_force_n"], 2000.0)
        self.assertAlmostEqual(summary["loading_energy_j"], 10.0, places=4)
        self.assertAlmostEqual(summary["unloading_energy_j"], 5.0, places=4)
        self.assertAlmostEqual(summary["curve_hysteresis_energy_j"], 5.0, places=4)
        self.assertAlmostEqual(summary["energy_absorption_ratio"], 0.5, places=4)
        self.assertAlmostEqual(summary["equivalent_stiffness_n_per_mm"], 200.0, places=4)


class ImpactSolveTests(unittest.TestCase):
    def test_non_bottom_out_solution(self) -> None:
        loading = _linear_loading(200.0, 50.0)
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=2.0,
            available_stroke_mm=50.0,
            allowable_peak_force_n=10000.0,
        )
        self.assertFalse(result["bottom_out"])
        self.assertAlmostEqual(result["max_compression_mm"], 4.4721, places=3)
        self.assertAlmostEqual(result["peak_force_n"], 200.0 * math.sqrt(20.0), places=6)
        self.assertEqual(result["peak_force_status"], "ok")
        self.assertAlmostEqual(result["absorbed_energy_j"], 2.0, places=4)

    def test_bottom_out_marks_unknown_peak(self) -> None:
        loading = _linear_loading(50.0, 10.0)
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=5.0,
            available_stroke_mm=10.0,
            allowable_peak_force_n=10000.0,
        )
        self.assertTrue(result["bottom_out"])
        self.assertIsNone(result["peak_force_n"])
        self.assertEqual(result["peak_force_status"], "bottom_out_unknown")
        self.assertAlmostEqual(result["max_compression_mm"], 10.0)
        self.assertAlmostEqual(result["absorbed_energy_j"], 2.5, places=4)

    def test_peak_force_exceeds_limit(self) -> None:
        loading = _linear_loading(200.0, 50.0)
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=2.0,
            available_stroke_mm=50.0,
            allowable_peak_force_n=500.0,
        )
        self.assertEqual(result["peak_force_status"], "exceeds_limit")

    def test_average_force(self) -> None:
        loading = _linear_loading(200.0, 50.0)
        result = _solve_impact(
            loading=loading,
            mass_kg=1.0,
            initial_velocity_m_s=2.0,
            available_stroke_mm=50.0,
            allowable_peak_force_n=10000.0,
        )
        self.assertAlmostEqual(result["average_force_n"], 447.2, places=1)


class ReboundAndCheckTests(unittest.TestCase):
    def test_rebound_uses_truncated_unloading_area(self) -> None:
        unloading = [{"x_mm": 0.0, "force_n": 0.0}, {"x_mm": 10.0, "force_n": 1000.0}]
        rebound = _estimate_rebound(unloading, x_max_mm=5.0, mass_kg=1.0)
        self.assertAlmostEqual(rebound["rebound_energy_j"], 1.25, places=4)
        self.assertAlmostEqual(rebound["estimated_rebound_velocity_m_s"], 1.5811, places=3)

    def test_checks_non_bottom_out(self) -> None:
        impact = {
            "max_compression_mm": 5.0,
            "peak_force_n": 1000.0,
            "peak_force_status": "ok",
            "bottom_out": False,
        }
        checks = _build_checks(impact, available_stroke_mm=10.0, allowable_peak_force_n=2000.0)
        self.assertTrue(checks["stroke_ok"])
        self.assertTrue(checks["peak_force_ok"])
        self.assertTrue(checks["energy_capacity_ok"])

    def test_checks_bottom_out_returns_none_for_peak(self) -> None:
        impact = {
            "max_compression_mm": 10.0,
            "peak_force_n": None,
            "peak_force_status": "bottom_out_unknown",
            "bottom_out": True,
        }
        checks = _build_checks(impact, available_stroke_mm=10.0, allowable_peak_force_n=2000.0)
        self.assertFalse(checks["stroke_ok"])
        self.assertIsNone(checks["peak_force_ok"])
        self.assertFalse(checks["energy_capacity_ok"])

    def test_checks_peak_force_exceeds(self) -> None:
        impact = {
            "max_compression_mm": 5.0,
            "peak_force_n": 3000.0,
            "peak_force_status": "exceeds_limit",
            "bottom_out": False,
        }
        checks = _build_checks(impact, available_stroke_mm=10.0, allowable_peak_force_n=2000.0)
        self.assertFalse(checks["peak_force_ok"])


class CalculateBufferEnergyEndToEndTests(unittest.TestCase):
    def _payload(self, overrides: dict | None = None) -> dict:
        loading = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        unloading = [{"x_mm": x, "force_n": 100.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        payload = {
            "curve": {"loading": loading, "unloading": unloading},
            "impact": {
                "mass_kg": 1.0,
                "initial_velocity_m_s": 2.0,
                "available_stroke_mm": 50.0,
                "allowable_peak_force_n": 10000.0,
            },
            "options": {
                "force_scale": 1.0,
                "stroke_scale": 1.0,
                "noise_tolerance_n": 5.0,
                "time_samples": 200,
            },
        }
        if overrides:
            for section, values in overrides.items():
                payload[section].update(values)
        return payload

    def test_returns_top_level_keys(self) -> None:
        result = calculate_buffer_energy(self._payload())
        for key in (
            "inputs_echo",
            "curve_summary",
            "impact",
            "checks",
            "overall_pass",
            "curves",
            "time_response",
            "warnings",
            "assumptions",
        ):
            self.assertIn(key, result)
        self.assertNotIn("_normalized", result)

    def test_overall_pass_true_for_clean_case(self) -> None:
        result = calculate_buffer_energy(self._payload())
        self.assertTrue(result["overall_pass"])
        self.assertFalse(result["impact"]["bottom_out"])

    def test_bottom_out_schema_is_conservative(self) -> None:
        result = calculate_buffer_energy(self._payload({"impact": {"initial_velocity_m_s": 30.0}}))
        self.assertTrue(result["impact"]["bottom_out"])
        self.assertFalse(result["overall_pass"])
        self.assertIsNone(result["impact"]["peak_force_n"])
        self.assertEqual(result["impact"]["peak_force_status"], "bottom_out_unknown")
        self.assertFalse(result["checks"]["stroke_ok"])
        self.assertIsNone(result["checks"]["peak_force_ok"])
        self.assertFalse(result["checks"]["energy_capacity_ok"])

    def test_input_validation_rejects_negative_mass(self) -> None:
        with self.assertRaises(InputError):
            calculate_buffer_energy(self._payload({"impact": {"mass_kg": -1.0}}))

    def test_curves_segment_includes_energy_curve(self) -> None:
        result = calculate_buffer_energy(self._payload())
        self.assertEqual(
            len(result["curves"]["loading_energy_x_mm"]),
            len(result["curves"]["loading_energy_j"]),
        )
        self.assertGreater(result["curves"]["loading_energy_j"][-1], 0.0)

    def test_unloading_local_soft_exceed_only_warns(self) -> None:
        payload = self._payload()
        payload["curve"]["unloading"] = [
            {"x_mm": 0.0, "force_n": 0.0},
            {"x_mm": 5.0, "force_n": 1006.0},
            {"x_mm": 10.0, "force_n": 1000.0},
            {"x_mm": 20.0, "force_n": 2000.0},
            {"x_mm": 50.0, "force_n": 5000.0},
        ]
        payload["options"]["noise_tolerance_n"] = 5.0
        result = calculate_buffer_energy(payload)
        self.assertTrue(any("局部高于加载曲线" in w for w in result["warnings"]))

    def test_unloading_within_noise_tolerance_does_not_warn(self) -> None:
        payload = self._payload()
        payload["curve"]["unloading"][1]["force_n"] = 1004.0
        payload["options"]["noise_tolerance_n"] = 5.0
        result = calculate_buffer_energy(payload)
        self.assertFalse(any("局部高于加载曲线" in w for w in result["warnings"]))

    def test_unloading_local_hard_exceed_raises(self) -> None:
        payload = self._payload()
        payload["curve"]["unloading"][1]["force_n"] = 1026.0
        payload["options"]["noise_tolerance_n"] = 5.0
        with self.assertRaises(InputError) as ctx:
            calculate_buffer_energy(payload)
        self.assertIn("违反耗散假设", str(ctx.exception))

    def test_unloading_area_over_ten_percent_raises(self) -> None:
        payload = self._payload()
        payload["curve"]["unloading"] = [
            {"x_mm": x, "force_n": 230.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)
        ]
        payload["options"]["noise_tolerance_n"] = 1000.0
        with self.assertRaises(InputError) as ctx:
            calculate_buffer_energy(payload)
        self.assertIn("10%", str(ctx.exception))

    def test_curve_hysteresis_and_impact_dissipation_are_distinct(self) -> None:
        result = calculate_buffer_energy(self._payload())
        self.assertNotAlmostEqual(
            result["curve_summary"]["curve_hysteresis_energy_j"],
            result["impact"]["impact_dissipated_energy_j"],
        )


class TimeResponseIntegrationTests(unittest.TestCase):
    def test_calculate_buffer_energy_includes_time_response(self) -> None:
        loading = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        unloading = [{"x_mm": x, "force_n": 100.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 2.0,
                    "available_stroke_mm": 50.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 100},
            }
        )
        self.assertIn("time_response", result)
        self.assertIsNotNone(result["time_response"])
        self.assertEqual(
            len(result["time_response"]["time_s"]),
            len(result["time_response"]["displacement_mm"]),
        )

    def test_result_is_json_serializable(self) -> None:
        import json

        loading = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 5.0, 10.0)]
        unloading = [{"x_mm": x, "force_n": 100.0 * x} for x in (0.0, 5.0, 10.0)]
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": math.sqrt(2.0),
                    "available_stroke_mm": 10.0,
                    "allowable_peak_force_n": 10000.0,
                },
            }
        )
        json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
