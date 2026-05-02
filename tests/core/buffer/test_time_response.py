"""Tests for energy-conservation time-domain reconstruction."""

from __future__ import annotations

import math
import unittest

from core.buffer.calculator import calculate_buffer_energy
from core.buffer.time_response import _compression_time_history, compute_time_response


def _linear_curve(k_n_per_mm: float, x_max_mm: float, n: int = 21) -> list[dict[str, float]]:
    step = x_max_mm / (n - 1)
    return [{"x_mm": i * step, "force_n": k_n_per_mm * i * step} for i in range(n)]


class CompressionTimeHistoryTests(unittest.TestCase):
    def test_linear_spring_quarter_period_matches_analytic(self) -> None:
        loading = _linear_curve(1000.0, 50.0, n=101)
        result = _compression_time_history(
            loading=loading, mass_kg=1.0, e0_j=12.5, x_max_mm=5.0, samples=400
        )
        expected_quarter = math.pi / 2.0 / math.sqrt(1e6)
        self.assertAlmostEqual(
            result["duration_s"], expected_quarter, delta=expected_quarter * 0.05
        )

    def test_velocity_zero_at_xmax(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        x_max = math.sqrt(20.0)
        result = _compression_time_history(
            loading=loading, mass_kg=1.0, e0_j=2.0, x_max_mm=x_max, samples=100
        )
        self.assertAlmostEqual(result["velocity_m_s"][-1], 0.0, places=2)
        self.assertGreater(result["velocity_m_s"][0], 0.0)

    def test_energy_conservation_within_tolerance(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        e0 = 2.0
        result = _compression_time_history(
            loading=loading, mass_kg=1.0, e0_j=e0, x_max_mm=4.4721, samples=200
        )
        mid = len(result["time_s"]) // 2
        v = result["velocity_m_s"][mid]
        x = result["displacement_mm"][mid]
        e_load = 0.5 * 200.0 * x**2 / 1000.0
        self.assertAlmostEqual(0.5 * v * v + e_load, e0, delta=e0 * 0.02)


class ComputeTimeResponseTests(unittest.TestCase):
    def test_returns_none_when_solver_state_invalid(self) -> None:
        fake_result = {
            "_normalized": {
                "loading": [{"x_mm": 0.0, "force_n": 0.0}],
                "unloading": [{"x_mm": 0.0, "force_n": 0.0}],
            },
            "impact": {
                "max_compression_mm": 0.0,
                "initial_energy_j": 0.0,
                "bottom_out": False,
            },
            "inputs_echo": {"impact": {"mass_kg": 1.0}, "options": {"time_samples": 100}},
        }
        out = compute_time_response(fake_result)
        self.assertIsNone(out)


class ReboundTimeHistoryTests(unittest.TestCase):
    def test_full_response_has_velocity_zero_then_negative(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        unloading = _linear_curve(100.0, 50.0)
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 2.0,
                    "available_stroke_mm": 50.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 200},
            }
        )
        tr = result["time_response"]
        self.assertIsNotNone(tr)
        peak_idx = tr["displacement_mm"].index(max(tr["displacement_mm"]))
        self.assertAlmostEqual(tr["velocity_m_s"][peak_idx], 0.0, places=2)
        self.assertLess(tr["velocity_m_s"][-1], 0.0)
        self.assertGreater(tr["compression_duration_s"], 0.0)
        self.assertGreater(tr["rebound_duration_s"], 0.0)
        self.assertAlmostEqual(
            tr["duration_s"],
            tr["compression_duration_s"] + tr["rebound_duration_s"],
            places=6,
        )
        self.assertEqual(len(tr["time_s"]), 200)

    def test_bottom_out_returns_compression_only_with_nonzero_terminal_velocity(self) -> None:
        loading = _linear_curve(50.0, 10.0)
        unloading = _linear_curve(25.0, 10.0)
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 5.0,
                    "available_stroke_mm": 10.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 100},
            }
        )
        self.assertTrue(result["impact"]["bottom_out"])
        tr = result["time_response"]
        self.assertIsNotNone(tr)
        self.assertEqual(tr["rebound_duration_s"], 0.0)
        self.assertGreater(abs(tr["velocity_m_s"][-1]), 0.5)
        self.assertTrue(any("触底后时域响应未建模" in w for w in result["warnings"]))

    def test_force_matches_branch_interpolation(self) -> None:
        loading = _linear_curve(200.0, 50.0)
        unloading = _linear_curve(100.0, 50.0)
        result = calculate_buffer_energy(
            {
                "curve": {"loading": loading, "unloading": unloading},
                "impact": {
                    "mass_kg": 1.0,
                    "initial_velocity_m_s": 2.0,
                    "available_stroke_mm": 50.0,
                    "allowable_peak_force_n": 10000.0,
                },
                "options": {"time_samples": 80},
            }
        )
        tr = result["time_response"]
        peak_idx = tr["displacement_mm"].index(max(tr["displacement_mm"]))
        self.assertAlmostEqual(
            tr["force_n"][peak_idx // 2],
            200.0 * tr["displacement_mm"][peak_idx // 2],
            places=6,
        )
        self.assertAlmostEqual(
            tr["force_n"][-1],
            100.0 * tr["displacement_mm"][-1],
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
