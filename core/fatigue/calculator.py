"""S-N/Woehler fitting, spectrum damage, and reliability pre-check calculator."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

from core._validation import finite_float, positive_float, require_mapping, section
from core.fatigue.rainflow import aggregate_cycles, count_rainflow


class InputError(ValueError):
    """Raised when fatigue inputs are incomplete or physically invalid."""


def _positive(value: Any, label: str, *, allow_zero: bool = False) -> float:
    return positive_float(value, label, allow_zero=allow_zero, error_cls=InputError)


def _finite(value: Any, label: str) -> float:
    return finite_float(value, label, error_cls=InputError)


def _require(mapping: dict[str, Any], key: str, label: str) -> Any:
    if key not in mapping:
        raise InputError(f"缺少必填字段: {label}.{key}")
    return mapping[key]


def _transfer_value(value: float, transfer: dict[str, Any]) -> tuple[float, bool]:
    mode = str(transfer.get("mode", "direct_stress"))
    allow_extrapolation = bool(transfer.get("allow_extrapolation", False))
    if mode == "direct_stress":
        return value, False
    if mode == "linear":
        factor = _finite(_require(transfer, "factor_mpa_per_unit", "transfer"), "transfer.factor_mpa_per_unit")
        offset = _finite(transfer.get("offset_mpa", 0.0), "transfer.offset_mpa")
        return factor * value + offset, False
    if mode != "lookup":
        raise InputError("transfer.mode 必须为 direct_stress / linear / lookup")
    raw_points = transfer.get("points")
    if not isinstance(raw_points, list) or len(raw_points) < 2:
        raise InputError("lookup 传递曲线至少需要 2 个点")
    points = [
        (
            _finite(_require(require_mapping(item, "transfer.points", error_cls=InputError), "load", "transfer.points"), "transfer.points.load"),
            _finite(_require(require_mapping(item, "transfer.points", error_cls=InputError), "stress_mpa", "transfer.points"), "transfer.points.stress_mpa"),
        )
        for item in raw_points
    ]
    points.sort()
    if any(x1 <= x0 for (x0, _), (x1, _) in zip(points, points[1:])):
        raise InputError("传递曲线 load 必须严格递增且不能重复")
    stresses = [stress for _, stress in points]
    monotonic_up = all(b >= a for a, b in zip(stresses, stresses[1:]))
    monotonic_down = all(b <= a for a, b in zip(stresses, stresses[1:]))
    if not (monotonic_up or monotonic_down):
        raise InputError("传递曲线 stress_mpa 必须单调")
    loads = [load for load, _ in points]
    outside = value < loads[0] or value > loads[-1]
    if outside and not allow_extrapolation:
        raise InputError("载荷超出传递曲线范围，默认禁止外推")
    if value <= loads[0]:
        pair = points[:2]
    elif value >= loads[-1]:
        pair = points[-2:]
    else:
        pair = next([points[i], points[i + 1]] for i in range(len(points) - 1) if points[i][0] <= value <= points[i + 1][0])
    (x0, y0), (x1, y1) = pair
    stress = y0 + (value - x0) * (y1 - y0) / (x1 - x0)
    return stress, outside


def _amplitude_mean(row: dict[str, Any], label: str) -> tuple[float, float]:
    if "stress_amplitude_mpa" in row:
        amplitude = _positive(row["stress_amplitude_mpa"], f"{label}.stress_amplitude_mpa")
        mean = _finite(row.get("stress_mean_mpa", 0.0), f"{label}.stress_mean_mpa")
        return amplitude, mean
    if "stress_max_mpa" in row and "stress_min_mpa" in row:
        maximum = _finite(row["stress_max_mpa"], f"{label}.stress_max_mpa")
        minimum = _finite(row["stress_min_mpa"], f"{label}.stress_min_mpa")
        return _positive(abs(maximum - minimum) / 2.0, f"{label}.stress_amplitude_mpa"), (maximum + minimum) / 2.0
    raise InputError(f"{label} 缺少应力幅/均值或最大/最小应力")


def _goodman_amplitude(
    amplitude: float,
    mean: float,
    material: dict[str, Any],
    sn_model: dict[str, Any],
) -> float:
    model = str(sn_model.get("mean_stress_model", "none"))
    if model == "none":
        return amplitude
    if model != "goodman":
        raise InputError("sn_model.mean_stress_model 仅支持 none / goodman")
    if str(material.get("material_type", "metal")) != "metal":
        raise InputError("塑料首版不支持通用 Goodman 跨 R 比修正")
    ultimate = _positive(_require(sn_model, "ultimate_strength_mpa", "sn_model"), "sn_model.ultimate_strength_mpa")
    denominator = 1.0 - mean / ultimate
    if denominator <= 0:
        raise InputError("平均应力达到/超过抗拉强度，Goodman 修正无定义")
    return amplitude / denominator


def _normalize_specimens(
    test_data: dict[str, Any], material: dict[str, Any], sn_model: dict[str, Any]
) -> list[dict[str, Any]]:
    raw = test_data.get("specimens")
    if not isinstance(raw, list) or not raw:
        raise InputError("test_data.specimens 不能为空")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        row = require_mapping(item, f"test_data.specimens[{index}]", error_cls=InputError)
        amplitude, mean = _amplitude_mean(row, f"test_data.specimens[{index}]")
        equivalent = _goodman_amplitude(amplitude, mean, material, sn_model)
        cycles = _positive(_require(row, "cycles", "test_data.specimens"), f"test_data.specimens[{index}].cycles")
        status = str(_require(row, "status", "test_data.specimens")).strip().lower()
        aliases = {"断裂": "failure", "失效": "failure", "未断裂": "runout", "无失效": "runout"}
        status = aliases.get(status, status)
        if status not in {"failure", "runout"}:
            raise InputError(f"test_data.specimens[{index}].status 必须为 failure/runout")
        result.append(
            {
                "specimen_id": str(row.get("specimen_id", index + 1)),
                "level_id": str(row.get("level_id", "")),
                "condition_group": str(row.get("condition_group", "")),
                "amplitude_mpa": amplitude,
                "mean_mpa": mean,
                "equivalent_amplitude_mpa": equivalent,
                "cycles": cycles,
                "status": status,
                "failure_mode": str(row.get("failure_mode", "")),
            }
        )
    return result


def _initial_fit(specimens: list[dict[str, Any]]) -> tuple[float, float, float]:
    failures = [item for item in specimens if item["status"] == "failure"]
    x = np.log10([item["equivalent_amplitude_mpa"] for item in failures])
    y = np.log10([item["cycles"] for item in failures])
    slope, intercept = np.polyfit(x, y, 1)
    residuals = y - (intercept + slope * x)
    scatter = max(float(np.std(residuals, ddof=1)) if len(y) > 2 else 0.15, 0.03)
    return float(intercept), max(float(-slope), 1e-3), scatter


def _fit_parameters(specimens: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [item for item in specimens if item["status"] == "failure"]
    levels = sorted({round(item["equivalent_amplitude_mpa"], 10) for item in failures})
    total_runouts = len(specimens) - len(failures)
    if not failures:
        return {
            "status": "all_runout",
            "converged": False,
            "failure_count": 0,
            "runout_count": len(specimens),
        }
    if len(levels) < 2 or len(failures) < 3:
        y = np.log10([item["cycles"] for item in failures])
        return {
            "status": "single_level",
            "converged": False,
            "failure_count": len(failures),
            "runout_count": total_runouts,
            "single_level_amplitude_mpa": levels[0] if levels else None,
            "single_level_log10_mean": float(np.mean(y)),
            "single_level_log10_scatter": float(np.std(y, ddof=1)) if len(y) > 1 else None,
        }
    # A stress level containing only runouts is fatigue-limit evidence, not a
    # finite-life line observation. Mixed levels retain their censored points.
    fit_specimens = [
        item
        for item in specimens
        if round(item["equivalent_amplitude_mpa"], 10) in levels
    ]
    fit_runouts = sum(item["status"] == "runout" for item in fit_specimens)
    initial = _initial_fit(fit_specimens)
    x = np.log10([item["equivalent_amplitude_mpa"] for item in fit_specimens])
    y = np.log10([item["cycles"] for item in fit_specimens])
    is_failure = np.array(
        [item["status"] == "failure" for item in fit_specimens], dtype=bool
    )

    def objective(params: np.ndarray) -> float:
        a, b, scatter = (float(value) for value in params)
        mu = a - b * x
        z = (y - mu) / scatter
        failure_ll = norm.logpdf(z[is_failure]) - math.log(scatter)
        runout_ll = norm.logsf(z[~is_failure])
        values = np.concatenate([failure_ll, runout_ll])
        if not np.all(np.isfinite(values)):
            return 1e100
        return float(-np.sum(values))

    optimized = minimize(
        objective,
        np.array(initial),
        method="L-BFGS-B",
        bounds=[(-20.0, 100.0), (1e-4, 100.0), (1e-4, 5.0)],
    )
    a, b, scatter = (float(value) for value in optimized.x)
    fitted = {
        "status": "valid" if optimized.success else "not_converged",
        "converged": bool(optimized.success),
        "a": a,
        "b": b,
        "scatter_log10_n": scatter,
        "negative_log_likelihood": float(optimized.fun),
        "failure_count": len(failures),
        "runout_count": total_runouts,
        "fit_runout_count": fit_runouts,
        "excluded_all_runout_count": total_runouts - fit_runouts,
        "stress_min_mpa": min(
            item["equivalent_amplitude_mpa"] for item in fit_specimens
        ),
        "stress_max_mpa": max(
            item["equivalent_amplitude_mpa"] for item in fit_specimens
        ),
        "distinct_failure_levels": len(levels),
    }
    fitted["failure_only_ols"] = _failure_ols(failures)
    fitted["mrr_johnson"] = _mrr_comparison(specimens)
    return fitted


def _failure_ols(failures: list[dict[str, Any]]) -> dict[str, float]:
    x = np.log10([item["equivalent_amplitude_mpa"] for item in failures])
    y = np.log10([item["cycles"] for item in failures])
    slope, intercept = np.polyfit(x, y, 1)
    predicted = intercept + slope * x
    total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - float(np.sum((y - predicted) ** 2)) / total if total > 0 else 1.0
    return {"a": float(intercept), "b": float(-slope), "r_squared": r_squared}


def _mrr_comparison(specimens: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for item in specimens:
        grouped[round(item["equivalent_amplitude_mpa"], 10)].append(item)
    medians: list[tuple[float, float, float]] = []
    for stress, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item["cycles"])
        n_total = len(ordered)
        adjusted_rank = 0.0
        previous_rank = 0.0
        failure_index = 0
        points: list[tuple[float, float]] = []
        for order_index, item in enumerate(ordered, start=1):
            if item["status"] != "failure":
                continue
            failure_index += 1
            increment = (n_total + 1.0 - previous_rank) / (n_total - order_index + 2.0)
            adjusted_rank = previous_rank + increment
            previous_rank = adjusted_rank
            plotting_position = (adjusted_rank - 0.3) / (n_total + 0.4)
            plotting_position = min(max(plotting_position, 1e-6), 1 - 1e-6)
            points.append((float(norm.ppf(plotting_position)), math.log10(item["cycles"])))
        if len(points) >= 2:
            z = np.array([point[0] for point in points])
            log_life = np.array([point[1] for point in points])
            scatter, mu = np.polyfit(z, log_life, 1)
            if scatter > 0:
                medians.append((stress, float(mu), float(scatter)))
    if len(medians) < 2:
        return {"status": "insufficient"}
    x = np.log10([item[0] for item in medians])
    y = np.array([item[1] for item in medians])
    slope, intercept = np.polyfit(x, y, 1)
    return {
        "status": "comparison_only",
        "a": float(intercept),
        "b": float(-slope),
        "scatter_log10_n": float(np.mean([item[2] for item in medians])),
        "level_count": len(medians),
    }


def _fatigue_limit_evidence(specimens: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for item in specimens:
        grouped[round(item["equivalent_amplitude_mpa"], 10)].append(item)
    all_runout = sorted(stress for stress, rows in grouped.items() if rows and all(row["status"] == "runout" for row in rows))
    failure_levels = sorted(stress for stress, rows in grouped.items() if any(row["status"] == "failure" for row in rows))
    lower = max(all_runout) if all_runout else None
    upper_candidates = [stress for stress in failure_levels if lower is None or stress > lower]
    upper = min(upper_candidates) if upper_candidates else None
    return {
        "all_runout_levels_mpa": all_runout,
        "failure_levels_mpa": failure_levels,
        "possible_lower_bound_mpa": lower,
        "possible_upper_bound_mpa": upper,
        "status": "bracket_only" if lower is not None and upper is not None else "insufficient",
        "note": "全 runout 仅构成寿命下限证据，不能据此宣称已确定疲劳极限。",
    }


def _normalize_spectrum(
    spectrum: dict[str, Any], transfer: dict[str, Any], material: dict[str, Any], sn_model: dict[str, Any]
) -> tuple[list[dict[str, float]], bool, dict[str, Any]]:
    kind = str(spectrum.get("kind", "blocks"))
    value_kind = str(spectrum.get("value_kind", "stress"))
    transfer_used = transfer if value_kind == "load" else {"mode": "direct_stress"}
    transfer_extrapolated = False
    if kind == "time_series":
        series = spectrum.get("series")
        if not isinstance(series, list) or len(series) < 2:
            raise InputError("time_series 至少需要 2 个点")
        values: list[float] = []
        for index, item in enumerate(series):
            row = require_mapping(item, f"spectrum.series[{index}]", error_cls=InputError)
            raw = _finite(_require(row, "value", "spectrum.series"), f"spectrum.series[{index}].value")
            stress, outside = _transfer_value(raw, transfer_used)
            values.append(stress)
            transfer_extrapolated = transfer_extrapolated or outside
        blocks = aggregate_cycles(count_rainflow(values))
        metadata = {"kind": kind, "point_count": len(values), "turning_cycle_bins": len(blocks)}
    elif kind == "blocks":
        raw_blocks = spectrum.get("blocks")
        if not isinstance(raw_blocks, list) or not raw_blocks:
            raise InputError("spectrum.blocks 不能为空")
        blocks = []
        for index, item in enumerate(raw_blocks):
            row = require_mapping(item, f"spectrum.blocks[{index}]", error_cls=InputError)
            if "amplitude" in row:
                raw_amplitude = _positive(row["amplitude"], f"spectrum.blocks[{index}].amplitude")
                raw_mean = _finite(row.get("mean", 0.0), f"spectrum.blocks[{index}].mean")
                maximum = raw_mean + raw_amplitude
                minimum = raw_mean - raw_amplitude
            elif "maximum" in row and "minimum" in row:
                maximum = _finite(row["maximum"], f"spectrum.blocks[{index}].maximum")
                minimum = _finite(row["minimum"], f"spectrum.blocks[{index}].minimum")
            else:
                raise InputError(f"spectrum.blocks[{index}] 缺少 amplitude/mean 或 maximum/minimum")
            stress_max, outside_max = _transfer_value(maximum, transfer_used)
            stress_min, outside_min = _transfer_value(minimum, transfer_used)
            transfer_extrapolated = transfer_extrapolated or outside_max or outside_min
            blocks.append(
                {
                    "amplitude_mpa": abs(stress_max - stress_min) / 2.0,
                    "mean_mpa": (stress_max + stress_min) / 2.0,
                    "cycles": _positive(_require(row, "cycles", "spectrum.blocks"), f"spectrum.blocks[{index}].cycles"),
                }
            )
        metadata = {"kind": kind, "input_block_count": len(blocks)}
    else:
        raise InputError("spectrum.kind 必须为 blocks / time_series")
    if not blocks:
        raise InputError("载荷谱没有形成有效循环")
    normalized: list[dict[str, float]] = []
    for block in blocks:
        amplitude = _positive(block["amplitude_mpa"], "spectrum.amplitude_mpa")
        mean = _finite(block.get("mean_mpa", 0.0), "spectrum.mean_mpa")
        normalized.append(
            {
                **block,
                "equivalent_amplitude_mpa": _goodman_amplitude(amplitude, mean, material, sn_model),
            }
        )
    return normalized, transfer_extrapolated, metadata


def _condition_compatibility(material: dict[str, Any], spectrum: dict[str, Any], sn_model: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    operating = spectrum.get("condition")
    if not isinstance(operating, dict):
        operating = {}
    material_type = str(material.get("material_type", "metal"))
    keys = ["temperature_c", "r_ratio"]
    if material_type in {"plastic", "short_fiber_plastic"}:
        required = ["temperature_c", "humidity_rh", "frequency_hz", "r_ratio", "orientation", "conditioning"]
        missing = [key for key in required if material.get(key) in (None, "")]
        if missing:
            warnings.append("塑料试验条件缺少: " + ", ".join(missing))
        keys.extend(["humidity_rh", "frequency_hz", "orientation", "conditioning"])
        if str(sn_model.get("mean_stress_model", "none")) != "none":
            warnings.append("塑料首版禁止通用跨 R 比平均应力修正")
    for key in dict.fromkeys(keys):
        test_value = material.get(key)
        service_value = operating.get(key, test_value)
        if test_value in (None, "") or service_value in (None, ""):
            continue
        if isinstance(test_value, (int, float)) and isinstance(service_value, (int, float)):
            tolerance = 0.02 if key == "r_ratio" else max(abs(float(test_value)) * 0.05, 1e-9)
            if abs(float(test_value) - float(service_value)) > tolerance:
                warnings.append(f"试验与服役条件 {key} 不一致: {test_value} vs {service_value}")
        elif str(test_value) != str(service_value):
            warnings.append(f"试验与服役条件 {key} 不一致: {test_value} vs {service_value}")
    return not warnings, warnings


def _design_damage(blocks: list[dict[str, float]], fit: dict[str, Any], survival: float, target_blocks: float) -> dict[str, Any]:
    z = float(norm.ppf(1.0 - survival))
    contributions: list[dict[str, float]] = []
    total = 0.0
    for block in blocks:
        stress = block["equivalent_amplitude_mpa"]
        log_life = fit["a"] - fit["b"] * math.log10(stress) + fit["scatter_log10_n"] * z
        life = 10.0**log_life
        damage = block["cycles"] / life
        total += damage
        contributions.append({**block, "design_life_cycles": life, "damage_per_block": damage})
    contributions.sort(key=lambda item: item["damage_per_block"], reverse=True)
    return {
        "design_survival_probability": survival,
        "damage_per_spectrum_block": total,
        "target_spectrum_blocks": target_blocks,
        "target_damage": total * target_blocks,
        "predicted_blocks_to_failure": None if total == 0 else 1.0 / total,
        "contributions": contributions,
    }


def _bootstrap_fits(specimens: list[dict[str, Any]], count: int, seed: int) -> list[tuple[float, float, float]]:
    if count <= 0:
        return []
    rng = np.random.default_rng(seed + 1)
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for item in specimens:
        grouped[round(item["equivalent_amplitude_mpa"], 10)].append(item)
    fits: list[tuple[float, float, float]] = []
    for _ in range(count):
        sampled: list[dict[str, Any]] = []
        for rows in grouped.values():
            indices = rng.integers(0, len(rows), size=len(rows))
            sampled.extend(rows[int(index)] for index in indices)
        fitted = _fit_parameters(sampled)
        if fitted.get("status") == "valid":
            fits.append((float(fitted["a"]), float(fitted["b"]), float(fitted["scatter_log10_n"])))
    return fits


def _reliability_simulation(
    blocks: list[dict[str, float]],
    fit: dict[str, Any],
    specimens: list[dict[str, Any]],
    reliability: dict[str, Any],
) -> dict[str, Any]:
    sample_count = int(_positive(reliability.get("monte_carlo_samples", 20000), "reliability.monte_carlo_samples"))
    if not 1000 <= sample_count <= 500000:
        raise InputError("monte_carlo_samples 必须在 1000..500000")
    bootstrap_count = int(_positive(reliability.get("bootstrap_samples", 500), "reliability.bootstrap_samples", allow_zero=True))
    if not 0 <= bootstrap_count <= 2000:
        raise InputError("bootstrap_samples 必须在 0..2000")
    seed = int(_finite(reliability.get("seed", 1729), "reliability.seed"))
    target_blocks = _positive(reliability.get("target_spectrum_blocks", 1.0), "reliability.target_spectrum_blocks")
    load_cov = _positive(reliability.get("load_cov", 0.0), "reliability.load_cov", allow_zero=True)
    if load_cov > 1.0:
        raise InputError("reliability.load_cov 必须在 0..1")
    bootstrap = _bootstrap_fits(specimens, bootstrap_count, seed)
    rng = np.random.default_rng(seed)
    if bootstrap:
        params = np.array(bootstrap, dtype=float)
        selected = params[rng.integers(0, len(params), size=sample_count)]
        a = selected[:, 0]
        b = selected[:, 1]
        scatter = selected[:, 2]
    else:
        a = np.full(sample_count, fit["a"], dtype=float)
        b = np.full(sample_count, fit["b"], dtype=float)
        scatter = np.full(sample_count, fit["scatter_log10_n"], dtype=float)
    unit_shift = rng.normal(0.0, scatter)
    if load_cov > 0:
        sigma_ln = math.sqrt(math.log1p(load_cov**2))
        mu_ln = -0.5 * sigma_ln**2
        load_multiplier = rng.lognormal(mu_ln, sigma_ln, size=sample_count)
    else:
        load_multiplier = np.ones(sample_count)
    damage = np.zeros(sample_count)
    for block in blocks:
        stress = np.maximum(block["equivalent_amplitude_mpa"] * load_multiplier, 1e-12)
        log_life = a - b * np.log10(stress) + unit_shift
        damage += block["cycles"] / np.power(10.0, log_life)
    life_blocks = np.divide(1.0, damage, out=np.full_like(damage, np.inf), where=damage > 0)
    failures = life_blocks < target_blocks
    pf = float(np.mean(failures))
    standard_error = math.sqrt(max(pf * (1.0 - pf) / sample_count, 0.0))
    ci_low = max(0.0, pf - 1.96 * standard_error)
    ci_high = min(1.0, pf + 1.96 * standard_error)
    return {
        "monte_carlo_samples": sample_count,
        "bootstrap_requested": bootstrap_count,
        "bootstrap_successful": len(bootstrap),
        "seed": seed,
        "load_cov": load_cov,
        "target_spectrum_blocks": target_blocks,
        "probability_of_failure": pf,
        "reliability": 1.0 - pf,
        "pf_ppm": pf * 1_000_000.0,
        "pf_confidence_interval_95": [ci_low, ci_high],
        "life_quantiles_blocks": {
            "Ps50": float(np.quantile(life_blocks, 0.50)),
            "Ps90": float(np.quantile(life_blocks, 0.10)),
            "Ps95": float(np.quantile(life_blocks, 0.05)),
            "Ps99": float(np.quantile(life_blocks, 0.01)),
        },
    }


def _incomplete_result(
    *, fit: dict[str, Any], evidence: dict[str, Any], blocks: list[dict[str, float]] | None, checks: dict[str, str], warnings: list[str], assumptions: list[str]
) -> dict[str, Any]:
    return {
        "fit": fit,
        "fatigue_limit_evidence": evidence,
        "counted_spectrum": blocks or [],
        "damage": None,
        "reliability": None,
        "checks": checks,
        "overall_status": "incomplete",
        "overall_pass": False,
        "warnings": warnings,
        "assumptions": assumptions,
    }


def calculate_fatigue_reliability(data: dict[str, Any]) -> dict[str, Any]:
    """Calculate a uniaxial fatigue/reliability engineering pre-check."""
    root = require_mapping(data, "data", error_cls=InputError)
    material = section(root, "material_condition", error_cls=InputError)
    test_data = section(root, "test_data", error_cls=InputError)
    sn_model = section(root, "sn_model", error_cls=InputError)
    spectrum = section(root, "spectrum", error_cls=InputError)
    transfer = root.get("transfer", {"mode": "direct_stress"})
    transfer = require_mapping(transfer, "transfer", error_cls=InputError)
    reliability_input = section(root, "reliability", error_cls=InputError)
    material_type = str(material.get("material_type", "metal"))
    if material_type not in {"metal", "plastic", "short_fiber_plastic"}:
        raise InputError("material_type 仅支持 metal/plastic/short_fiber_plastic")

    assumptions = [
        "单轴标量应力与线性累积损伤（Miner），不考虑载荷次序效应。",
        "有限寿命段采用单斜率对数正态 S-N 模型，runout 按右删失处理。",
        "同一模拟零件在所有谱级共享一个曲线纵向散差。",
        "本结果为工程预校核，不替代正式标准签发、试验认证或多轴/应变寿命分析。",
    ]
    warnings: list[str] = []
    specimens = _normalize_specimens(test_data, material, sn_model)
    fit = _fit_parameters(specimens)
    evidence = _fatigue_limit_evidence(specimens)
    checks: dict[str, str] = {
        "data_adequacy": "pass" if fit.get("status") == "valid" else "incomplete",
        "condition_compatibility": "incomplete",
        "extrapolation": "incomplete",
        "damage": "not_checked",
        "reliability": "not_checked",
    }
    if fit.get("status") != "valid":
        status = fit.get("status")
        if status == "all_runout":
            warnings.append("全部试样为 runout，只能给出寿命下限，不能拟合 S-N 曲线。")
        elif status == "single_level":
            warnings.append("有效断裂数据不足两个应力级，不能识别 S-N 斜率。")
        else:
            warnings.append("删失 S-N 极大似然拟合未收敛。")
        return _incomplete_result(fit=fit, evidence=evidence, blocks=None, checks=checks, warnings=warnings, assumptions=assumptions)

    conditions_ok, condition_warnings = _condition_compatibility(material, spectrum, sn_model)
    condition_groups = {
        item["condition_group"] for item in specimens if item["condition_group"]
    }
    if len(condition_groups) > 1:
        conditions_ok = False
        condition_warnings.append(
            "试验数据包含多个条件组，首版禁止直接合并；请拆分后分别拟合。"
        )
    warnings.extend(condition_warnings)
    checks["condition_compatibility"] = "pass" if conditions_ok else "incomplete"
    blocks, transfer_extrapolated, spectrum_metadata = _normalize_spectrum(spectrum, transfer, material, sn_model)
    spectrum_min = min(block["equivalent_amplitude_mpa"] for block in blocks)
    spectrum_max = max(block["equivalent_amplitude_mpa"] for block in blocks)
    stress_outside = spectrum_min < fit["stress_min_mpa"] or spectrum_max > fit["stress_max_mpa"]
    extrapolated = transfer_extrapolated or stress_outside
    allow_trend = bool(sn_model.get("allow_extrapolation", False))
    if extrapolated:
        checks["extrapolation"] = "incomplete"
        warnings.append(
            "载荷谱或传递换算超出实测有限寿命范围；趋势外推不能形成通过结论。"
        )
        if not allow_trend:
            return _incomplete_result(fit=fit, evidence=evidence, blocks=blocks, checks=checks, warnings=warnings, assumptions=assumptions)
    else:
        checks["extrapolation"] = "pass"

    target_blocks = _positive(reliability_input.get("target_spectrum_blocks", 1.0), "reliability.target_spectrum_blocks")
    required_reliability = _positive(reliability_input.get("required_reliability", 0.9), "reliability.required_reliability")
    if not 0.5 <= required_reliability < 1.0:
        raise InputError("required_reliability 必须在 [0.5, 1) 区间")
    design_survival = _positive(sn_model.get("design_survival_probability", required_reliability), "sn_model.design_survival_probability")
    if not 0.5 <= design_survival < 1.0:
        raise InputError("design_survival_probability 必须在 [0.5, 1) 区间")
    damage = _design_damage(blocks, fit, design_survival, target_blocks)
    reliability_result = _reliability_simulation(blocks, fit, specimens, reliability_input)
    bootstrap_requested = int(reliability_result["bootstrap_requested"])
    bootstrap_successful = int(reliability_result["bootstrap_successful"])
    bootstrap_adequate = (
        bootstrap_requested == 0
        or bootstrap_successful / bootstrap_requested >= 0.8
    )
    if not bootstrap_adequate:
        checks["data_adequacy"] = "incomplete"
        warnings.append(
            "分层 bootstrap 的有效拟合比例低于 80%，参数不确定性结果仅供参考。"
        )
    checks["damage"] = "pass" if damage["target_damage"] <= 1.0 else "fail"
    checks["reliability"] = "pass" if reliability_result["reliability"] >= required_reliability else "fail"
    if extrapolated or not conditions_ok or not bootstrap_adequate:
        overall_status = "incomplete"
    elif "fail" in {checks["damage"], checks["reliability"]}:
        overall_status = "fail"
    else:
        overall_status = "pass"
    return {
        "fit": fit,
        "fatigue_limit_evidence": evidence,
        "counted_spectrum": blocks,
        "spectrum_metadata": spectrum_metadata,
        "damage": damage,
        "reliability": reliability_result,
        "checks": checks,
        "overall_status": overall_status,
        "overall_pass": overall_status == "pass",
        "warnings": warnings,
        "assumptions": assumptions,
        "inputs_echo": root,
    }
