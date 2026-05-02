"""Energy-conservation reconstruction of approximate time histories.

Reference: docs/superpowers/specs/2026-05-02-buffer-energy-simulation-design.md
section Time-domain Reconstruction.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence


_MM_TO_M = 1e-3
_EPS_V = 1e-6


def _interp(xs: Sequence[float], ys: Sequence[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        x0 = xs[i]
        x1 = xs[i + 1]
        if x0 <= x <= x1 and x1 > x0:
            t = (x - x0) / (x1 - x0)
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def _energy_at_x(points: Sequence[Dict[str, float]], target_x_mm: float) -> float:
    if target_x_mm <= 0:
        return 0.0
    total = 0.0
    for prev, curr in zip(points, points[1:]):
        x0 = prev["x_mm"]
        x1 = curr["x_mm"]
        if x1 <= x0:
            continue
        f0 = prev["force_n"]
        f1 = curr["force_n"]
        if target_x_mm >= x1:
            total += 0.5 * (f0 + f1) * (x1 - x0)
            continue
        if target_x_mm <= x0:
            break
        f_target = _interp([x0, x1], [f0, f1], target_x_mm)
        total += 0.5 * (f0 + f_target) * (target_x_mm - x0)
        break
    return total * _MM_TO_M


def _x_grid(start: float, stop: float, samples: int) -> List[float]:
    n = max(4, samples)
    if n == 1:
        return [start]
    step = (stop - start) / (n - 1)
    return [start + i * step for i in range(n)]


def _compression_time_history(
    *,
    loading: Sequence[Dict[str, float]],
    mass_kg: float,
    e0_j: float,
    x_max_mm: float,
    samples: int,
) -> Dict[str, Any]:
    if x_max_mm <= 0 or mass_kg <= 0 or e0_j <= 0 or len(loading) < 2:
        raise ValueError("invalid compression state")
    xs_mm = _x_grid(0.0, x_max_mm, samples)
    loading_xs = [point["x_mm"] for point in loading]
    loading_forces = [point["force_n"] for point in loading]
    forces = [_interp(loading_xs, loading_forces, x) for x in xs_mm]
    accelerations = [force / mass_kg for force in forces]
    velocities: List[float] = []
    for x in xs_mm:
        kinetic = e0_j - _energy_at_x(loading, x)
        velocities.append(math.sqrt(2.0 * max(0.0, kinetic) / mass_kg))

    times: List[float] = [0.0]
    for i in range(1, len(xs_mm)):
        dx_m = (xs_mm[i] - xs_mm[i - 1]) * _MM_TO_M
        v0 = velocities[i - 1]
        v1 = velocities[i]
        if v0 < _EPS_V and v1 < _EPS_V:
            dt = 0.0
        elif v1 < _EPS_V:
            a_end = max(abs(accelerations[i]), 1e-9)
            dt = math.sqrt(2.0 * dx_m / a_end)
        elif v0 < _EPS_V:
            a_start = max(abs(accelerations[i - 1]), 1e-9)
            dt = math.sqrt(2.0 * dx_m / a_start)
        else:
            dt = 0.5 * (1.0 / v0 + 1.0 / v1) * dx_m
        if not math.isfinite(dt):
            raise ValueError("non-finite compression dt")
        times.append(times[-1] + dt)

    return {
        "duration_s": times[-1],
        "time_s": times,
        "displacement_mm": xs_mm,
        "velocity_m_s": velocities,
        "acceleration_m_s2": accelerations,
        "force_n": forces,
    }


def _rebound_time_history(
    *,
    unloading: Sequence[Dict[str, float]],
    mass_kg: float,
    x_max_mm: float,
    samples: int,
    start_time_s: float,
) -> Dict[str, Any]:
    if x_max_mm <= 0 or mass_kg <= 0 or len(unloading) < 2:
        raise ValueError("invalid rebound state")
    xs_desc = _x_grid(x_max_mm, 0.0, samples)
    unloading_xs = [point["x_mm"] for point in unloading]
    unloading_forces = [point["force_n"] for point in unloading]
    forces = [_interp(unloading_xs, unloading_forces, x) for x in xs_desc]
    accelerations = [-force / mass_kg for force in forces]

    released: List[float] = [0.0]
    for i in range(1, len(xs_desc)):
        dx_m = (xs_desc[i - 1] - xs_desc[i]) * _MM_TO_M
        released.append(released[-1] + 0.5 * (forces[i - 1] + forces[i]) * dx_m)
    velocities = [-math.sqrt(2.0 * max(0.0, e) / mass_kg) for e in released]

    times: List[float] = [start_time_s]
    for i in range(1, len(xs_desc)):
        dx_m = (xs_desc[i - 1] - xs_desc[i]) * _MM_TO_M
        v0 = abs(velocities[i - 1])
        v1 = abs(velocities[i])
        if v0 < _EPS_V and v1 < _EPS_V:
            dt = 0.0
        elif v0 < _EPS_V:
            a_start = max(abs(accelerations[i - 1]), 1e-9)
            dt = math.sqrt(2.0 * dx_m / a_start)
        elif v1 < _EPS_V:
            a_end = max(abs(accelerations[i]), 1e-9)
            dt = math.sqrt(2.0 * dx_m / a_end)
        else:
            dt = 0.5 * (1.0 / v0 + 1.0 / v1) * dx_m
        if not math.isfinite(dt):
            raise ValueError("non-finite rebound dt")
        times.append(times[-1] + dt)

    return {
        "duration_s": times[-1] - start_time_s,
        "time_s": times,
        "displacement_mm": xs_desc,
        "velocity_m_s": velocities,
        "acceleration_m_s2": accelerations,
        "force_n": forces,
    }


def compute_time_response(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return x/v/a/F time histories from an internal calculator result."""
    impact = result.get("impact", {})
    norm = result.get("_normalized", {})
    options = result.get("inputs_echo", {}).get("options", {})
    impact_in = result.get("inputs_echo", {}).get("impact", {})
    try:
        x_max = float(impact.get("max_compression_mm", 0.0) or 0.0)
        e0 = float(impact.get("initial_energy_j", 0.0) or 0.0)
        mass_kg = float(impact_in.get("mass_kg", 0.0) or 0.0)
        samples = int(options.get("time_samples", 200))
    except (TypeError, ValueError):
        return None
    if x_max <= 0 or e0 <= 0 or mass_kg <= 0 or not norm.get("loading"):
        return None

    bottom_out = bool(impact.get("bottom_out", False))
    compression_samples = max(4, samples if bottom_out else samples // 2 + 1)
    try:
        compression = _compression_time_history(
            loading=norm["loading"],
            mass_kg=mass_kg,
            e0_j=e0,
            x_max_mm=x_max,
            samples=compression_samples,
        )
    except (ValueError, ZeroDivisionError, OverflowError):
        return None

    if bottom_out:
        return {
            "duration_s": compression["duration_s"],
            "compression_duration_s": compression["duration_s"],
            "rebound_duration_s": 0.0,
            "time_s": list(compression["time_s"]),
            "displacement_mm": list(compression["displacement_mm"]),
            "velocity_m_s": list(compression["velocity_m_s"]),
            "acceleration_m_s2": list(compression["acceleration_m_s2"]),
            "force_n": list(compression["force_n"]),
        }

    try:
        rebound_samples = max(4, samples - len(compression["time_s"]) + 1)
        rebound = _rebound_time_history(
            unloading=norm["unloading"],
            mass_kg=mass_kg,
            x_max_mm=x_max,
            samples=rebound_samples,
            start_time_s=compression["duration_s"],
        )
    except (ValueError, ZeroDivisionError, OverflowError):
        return {
            "duration_s": compression["duration_s"],
            "compression_duration_s": compression["duration_s"],
            "rebound_duration_s": 0.0,
            "time_s": list(compression["time_s"]),
            "displacement_mm": list(compression["displacement_mm"]),
            "velocity_m_s": list(compression["velocity_m_s"]),
            "acceleration_m_s2": list(compression["acceleration_m_s2"]),
            "force_n": list(compression["force_n"]),
        }

    return {
        "duration_s": compression["duration_s"] + rebound["duration_s"],
        "compression_duration_s": compression["duration_s"],
        "rebound_duration_s": rebound["duration_s"],
        "time_s": list(compression["time_s"]) + list(rebound["time_s"][1:]),
        "displacement_mm": list(compression["displacement_mm"])
        + list(rebound["displacement_mm"][1:]),
        "velocity_m_s": list(compression["velocity_m_s"]) + list(rebound["velocity_m_s"][1:]),
        "acceleration_m_s2": list(compression["acceleration_m_s2"])
        + list(rebound["acceleration_m_s2"][1:]),
        "force_n": list(compression["force_n"]) + list(rebound["force_n"][1:]),
    }
