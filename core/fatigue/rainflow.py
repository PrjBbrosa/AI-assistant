"""Turning-point extraction and ASTM-style rainflow cycle counting."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Any


def extract_turning_points(values: Sequence[float]) -> list[float]:
    """Remove duplicates and non-reversing interior points from a scalar history."""
    cleaned: list[float] = []
    for raw in values:
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("时序包含 NaN/Inf")
        if not cleaned or value != cleaned[-1]:
            cleaned.append(value)
    if len(cleaned) <= 2:
        return cleaned

    result = [cleaned[0]]
    for index in range(1, len(cleaned) - 1):
        left = cleaned[index] - cleaned[index - 1]
        right = cleaned[index + 1] - cleaned[index]
        if left * right < 0:
            result.append(cleaned[index])
    result.append(cleaned[-1])
    return result


def count_rainflow(values: Sequence[float]) -> list[dict[str, float]]:
    """Return range/amplitude/mean/count records, retaining residual half cycles."""
    points = extract_turning_points(values)
    if len(points) < 2:
        return []

    stack: list[float] = []
    cycles: list[dict[str, float]] = []

    def append_cycle(first: float, second: float, count: float) -> None:
        stress_range = abs(second - first)
        if stress_range <= 0:
            return
        cycles.append(
            {
                "range": stress_range,
                "amplitude": stress_range / 2.0,
                "mean": (first + second) / 2.0,
                "count": count,
            }
        )

    for point in points:
        stack.append(point)
        while len(stack) >= 3:
            previous_range = abs(stack[-2] - stack[-3])
            latest_range = abs(stack[-1] - stack[-2])
            if previous_range > latest_range:
                break
            if len(stack) == 3:
                append_cycle(stack[-3], stack[-2], 0.5)
                stack.pop(0)
            else:
                append_cycle(stack[-3], stack[-2], 1.0)
                newest = stack[-1]
                del stack[-3:]
                stack.append(newest)

    for first, second in zip(stack, stack[1:]):
        append_cycle(first, second, 0.5)
    return cycles


def aggregate_cycles(
    cycles: Iterable[dict[str, Any]], *, precision: int = 6
) -> list[dict[str, float]]:
    """Aggregate identical amplitude/mean bins without losing half-cycle counts."""
    grouped: dict[tuple[float, float], float] = {}
    for cycle in cycles:
        amplitude = round(float(cycle["amplitude"]), precision)
        mean = round(float(cycle.get("mean", 0.0)), precision)
        grouped[(amplitude, mean)] = grouped.get((amplitude, mean), 0.0) + float(
            cycle.get("count", 0.0)
        )
    return [
        {"amplitude_mpa": amplitude, "mean_mpa": mean, "cycles": count}
        for (amplitude, mean), count in sorted(grouped.items(), reverse=True)
        if amplitude > 0 and count > 0
    ]
