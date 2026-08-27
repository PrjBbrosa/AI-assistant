from __future__ import annotations

import pytest

from core.fatigue.rainflow import aggregate_cycles, count_rainflow, extract_turning_points


def test_turning_points_remove_duplicates_and_monotonic_interior() -> None:
    assert extract_turning_points([0, 0, 1, 2, 1, 0, -1, -1, 0]) == [0.0, 2.0, -1.0, 0.0]


def test_simple_closed_history_counts_one_full_cycle() -> None:
    cycles = count_rainflow([-10, 10, -10])
    total = sum(item["count"] for item in cycles)
    weighted_range = sum(item["range"] * item["count"] for item in cycles)
    assert total == pytest.approx(1.0)
    assert weighted_range == pytest.approx(20.0)


def test_residual_open_history_retains_half_cycles() -> None:
    cycles = count_rainflow([0, 10, 5])
    assert [(item["range"], item["count"]) for item in cycles] == [(10.0, 0.5), (5.0, 0.5)]


def test_cycle_aggregation_preserves_half_counts() -> None:
    result = aggregate_cycles(
        [
            {"amplitude": 5.0, "mean": 5.0, "count": 0.5},
            {"amplitude": 5.0, "mean": 5.0, "count": 0.5},
        ]
    )
    assert result == [{"amplitude_mpa": 5.0, "mean_mpa": 5.0, "cycles": 1.0}]
