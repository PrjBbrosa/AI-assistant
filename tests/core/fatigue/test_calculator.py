from __future__ import annotations

import copy
import json
import math

import pytest
from scipy.stats import norm

from core.fatigue.calculator import InputError, calculate_fatigue_reliability


def _specimens() -> list[dict]:
    # Approximately log10(N) = 12 - 3*log10(Sa), with modest scatter.
    rows: list[dict] = []
    multipliers = (0.82, 0.93, 1.0, 1.08, 1.18)
    for stress in (100.0, 140.0, 200.0):
        median = 10 ** (12.0 - 3.0 * math.log10(stress))
        for index, factor in enumerate(multipliers):
            rows.append(
                {
                    "specimen_id": f"{int(stress)}-{index}",
                    "stress_amplitude_mpa": stress,
                    "stress_mean_mpa": 0.0,
                    "cycles": median * factor,
                    "status": "failure",
                }
            )
    rows.append(
        {
            "specimen_id": "100-R",
            "stress_amplitude_mpa": 100.0,
            "stress_mean_mpa": 0.0,
            "cycles": 1_250_000,
            "status": "runout",
        }
    )
    return rows


def _payload() -> dict:
    return {
        "material_condition": {
            "material_type": "metal",
            "material_name": "synthetic steel",
            "temperature_c": 23.0,
            "r_ratio": -1.0,
        },
        "test_data": {"specimens": _specimens()},
        "sn_model": {
            "mean_stress_model": "none",
            "design_survival_probability": 0.9,
            "allow_extrapolation": False,
        },
        "spectrum": {
            "kind": "blocks",
            "value_kind": "stress",
            "condition": {"temperature_c": 23.0, "r_ratio": -1.0},
            "blocks": [
                {"amplitude": 120.0, "mean": 0.0, "cycles": 1000},
                {"amplitude": 180.0, "mean": 0.0, "cycles": 20},
            ],
        },
        "transfer": {"mode": "direct_stress"},
        "reliability": {
            "target_spectrum_blocks": 10.0,
            "required_reliability": 0.9,
            "load_cov": 0.0,
            "monte_carlo_samples": 2000,
            "bootstrap_samples": 20,
            "seed": 1729,
        },
    }


def test_censored_fit_damage_and_reliability_are_serializable() -> None:
    result = calculate_fatigue_reliability(_payload())
    fit = result["fit"]
    assert fit["status"] == "valid"
    assert fit["b"] == pytest.approx(3.0, rel=0.2)
    assert fit["runout_count"] == 1
    assert result["damage"]["damage_per_spectrum_block"] > 0
    assert 0 <= result["reliability"]["probability_of_failure"] <= 1
    assert result["reliability"]["seed"] == 1729
    assert result["overall_status"] in {"pass", "fail"}
    json.dumps(result, ensure_ascii=False, allow_nan=False)


def test_all_runout_is_incomplete_not_pass() -> None:
    payload = _payload()
    for row in payload["test_data"]["specimens"]:
        row["status"] = "runout"
    result = calculate_fatigue_reliability(payload)
    assert result["fit"]["status"] == "all_runout"
    assert result["overall_status"] == "incomplete"
    assert result["overall_pass"] is False
    assert result["damage"] is None


def test_single_failure_level_is_incomplete() -> None:
    payload = _payload()
    payload["test_data"]["specimens"] = [
        row for row in payload["test_data"]["specimens"] if row["stress_amplitude_mpa"] == 100.0
    ]
    result = calculate_fatigue_reliability(payload)
    assert result["fit"]["status"] == "single_level"
    assert result["overall_status"] == "incomplete"


def test_optimizer_nonconvergence_is_incomplete(monkeypatch) -> None:
    class FailedOptimization:
        success = False
        x = (12.0, 3.0, 0.1)
        fun = 123.0

    monkeypatch.setattr(
        "core.fatigue.calculator.minimize",
        lambda *args, **kwargs: FailedOptimization(),
    )
    result = calculate_fatigue_reliability(_payload())
    assert result["fit"]["status"] == "not_converged"
    assert result["overall_status"] == "incomplete"


def test_all_runout_level_is_fatigue_limit_evidence_not_fit_input() -> None:
    baseline_payload = _payload()
    baseline_payload["test_data"]["specimens"] = [
        row
        for row in baseline_payload["test_data"]["specimens"]
        if row["status"] == "failure"
    ]
    baseline = calculate_fatigue_reliability(baseline_payload)

    with_limit = copy.deepcopy(baseline_payload)
    with_limit["test_data"]["specimens"].extend(
        [
            {
                "specimen_id": "L-1",
                "stress_amplitude_mpa": 80.0,
                "stress_mean_mpa": 0.0,
                "cycles": 2_000_000,
                "status": "runout",
            },
            {
                "specimen_id": "L-2",
                "stress_amplitude_mpa": 80.0,
                "stress_mean_mpa": 0.0,
                "cycles": 2_000_000,
                "status": "runout",
            },
        ]
    )
    result = calculate_fatigue_reliability(with_limit)
    assert result["fit"]["a"] == pytest.approx(baseline["fit"]["a"], rel=1e-12)
    assert result["fit"]["b"] == pytest.approx(baseline["fit"]["b"], rel=1e-12)
    assert result["fit"]["excluded_all_runout_count"] == 2
    assert result["fatigue_limit_evidence"]["possible_lower_bound_mpa"] == 80.0


def test_outside_test_range_is_incomplete_and_stops_damage() -> None:
    payload = _payload()
    payload["spectrum"]["blocks"] = [{"amplitude": 250.0, "mean": 0.0, "cycles": 1}]
    result = calculate_fatigue_reliability(payload)
    assert result["checks"]["extrapolation"] == "incomplete"
    assert result["damage"] is None
    assert result["overall_status"] == "incomplete"


def test_explicit_trend_extrapolation_calculates_but_never_passes() -> None:
    payload = _payload()
    payload["sn_model"]["allow_extrapolation"] = True
    payload["spectrum"]["blocks"] = [{"amplitude": 250.0, "mean": 0.0, "cycles": 1}]
    result = calculate_fatigue_reliability(payload)
    assert result["damage"] is not None
    assert result["overall_status"] == "incomplete"


def test_goodman_is_metal_only() -> None:
    payload = _payload()
    payload["material_condition"].update(
        {
            "material_type": "plastic",
            "humidity_rh": 50,
            "frequency_hz": 5,
            "orientation": "flow",
            "conditioning": "dry",
        }
    )
    payload["sn_model"].update({"mean_stress_model": "goodman", "ultimate_strength_mpa": 500})
    with pytest.raises(InputError, match="塑料首版"):
        calculate_fatigue_reliability(payload)


def test_goodman_for_metal_increases_equivalent_amplitude() -> None:
    payload = _payload()
    payload["sn_model"].update(
        {"mean_stress_model": "goodman", "ultimate_strength_mpa": 900.0}
    )
    payload["spectrum"]["blocks"] = [
        {"amplitude": 100.0, "mean": 100.0, "cycles": 10.0}
    ]
    result = calculate_fatigue_reliability(payload)
    assert result["counted_spectrum"][0][
        "equivalent_amplitude_mpa"
    ] == pytest.approx(112.5)


def test_linear_transfer_matches_direct_stress_blocks() -> None:
    direct = calculate_fatigue_reliability(_payload())
    payload = _payload()
    payload["spectrum"]["value_kind"] = "load"
    payload["spectrum"]["blocks"] = [
        {"amplitude": 1200.0, "mean": 0.0, "cycles": 1000},
        {"amplitude": 1800.0, "mean": 0.0, "cycles": 20},
    ]
    payload["transfer"] = {"mode": "linear", "factor_mpa_per_unit": 0.1, "offset_mpa": 0.0}
    transferred = calculate_fatigue_reliability(payload)
    assert transferred["damage"]["damage_per_spectrum_block"] == pytest.approx(
        direct["damage"]["damage_per_spectrum_block"], rel=1e-12
    )


def test_fixed_seed_is_reproducible() -> None:
    first = calculate_fatigue_reliability(_payload())["reliability"]
    second = calculate_fatigue_reliability(_payload())["reliability"]
    assert first == second


def test_single_spectrum_level_monte_carlo_matches_lognormal_solution() -> None:
    payload = _payload()
    payload["spectrum"]["blocks"] = [
        {"amplitude": 140.0, "mean": 0.0, "cycles": 1000.0}
    ]
    payload["reliability"].update(
        {
            "target_spectrum_blocks": 350.0,
            "monte_carlo_samples": 20_000,
            "bootstrap_samples": 0,
        }
    )
    result = calculate_fatigue_reliability(payload)
    fit = result["fit"]
    median_log_blocks = (
        fit["a"] - fit["b"] * math.log10(140.0) - math.log10(1000.0)
    )
    expected_pf = float(
        norm.cdf(
            (math.log10(350.0) - median_log_blocks)
            / fit["scatter_log10_n"]
        )
    )
    assert result["reliability"]["probability_of_failure"] == pytest.approx(
        expected_pf, abs=0.02
    )


def test_higher_load_cov_does_not_improve_reliability_for_this_case() -> None:
    base = _payload()
    base["reliability"]["target_spectrum_blocks"] = 500.0
    baseline = calculate_fatigue_reliability(base)["reliability"]["reliability"]
    varied = copy.deepcopy(base)
    varied["reliability"]["load_cov"] = 0.2
    with_cov = calculate_fatigue_reliability(varied)["reliability"]["reliability"]
    assert with_cov <= baseline


def test_lookup_transfer_interpolates_and_rejects_nonmonotonic_curve() -> None:
    payload = _payload()
    payload["spectrum"]["value_kind"] = "load"
    payload["spectrum"]["blocks"] = [{"amplitude": 1200.0, "mean": 0.0, "cycles": 100}]
    payload["transfer"] = {
        "mode": "lookup",
        "points": [
            {"load": -2000, "stress_mpa": -200},
            {"load": 0, "stress_mpa": 0},
            {"load": 2000, "stress_mpa": 200},
        ],
    }
    result = calculate_fatigue_reliability(payload)
    assert result["counted_spectrum"][0]["amplitude_mpa"] == pytest.approx(120.0)

    payload["transfer"]["points"] = [
        {"load": -2000, "stress_mpa": -200},
        {"load": 0, "stress_mpa": 20},
        {"load": 2000, "stress_mpa": 10},
    ]
    with pytest.raises(InputError, match="必须单调"):
        calculate_fatigue_reliability(payload)


def test_lookup_transfer_rejects_out_of_range_by_default() -> None:
    payload = _payload()
    payload["spectrum"]["value_kind"] = "load"
    payload["spectrum"]["blocks"] = [{"amplitude": 1500.0, "mean": 0.0, "cycles": 10}]
    payload["transfer"] = {
        "mode": "lookup",
        "points": [
            {"load": -1000, "stress_mpa": -100},
            {"load": 1000, "stress_mpa": 100},
        ],
    }
    with pytest.raises(InputError, match="默认禁止外推"):
        calculate_fatigue_reliability(payload)


def test_plastic_condition_mismatch_is_incomplete() -> None:
    payload = _payload()
    payload["material_condition"].update(
        {
            "material_type": "short_fiber_plastic",
            "humidity_rh": 50.0,
            "frequency_hz": 5.0,
            "orientation": "flow",
            "conditioning": "dry",
        }
    )
    payload["spectrum"]["condition"].update({"humidity_rh": 80.0, "frequency_hz": 5.0, "orientation": "flow", "conditioning": "dry"})
    result = calculate_fatigue_reliability(payload)
    assert result["checks"]["condition_compatibility"] == "incomplete"
    assert result["overall_status"] == "incomplete"


def test_multiple_test_condition_groups_are_not_merged() -> None:
    payload = _payload()
    for index, row in enumerate(payload["test_data"]["specimens"]):
        row["condition_group"] = "C1" if index % 2 == 0 else "C2"
    result = calculate_fatigue_reliability(payload)
    assert result["checks"]["condition_compatibility"] == "incomplete"
    assert result["overall_status"] == "incomplete"
    assert any("多个条件组" in warning for warning in result["warnings"])


def test_time_series_keeps_half_cycles() -> None:
    payload = _payload()
    payload["spectrum"] = {
        "kind": "time_series",
        "value_kind": "stress",
        "condition": {"temperature_c": 23.0, "r_ratio": -1.0},
        "series": [
            {"value": -120.0},
            {"value": 120.0},
            {"value": -120.0},
        ],
    }
    result = calculate_fatigue_reliability(payload)
    assert result["counted_spectrum"] == [
        {
            "amplitude_mpa": 120.0,
            "mean_mpa": 0.0,
            "cycles": 1.0,
            "equivalent_amplitude_mpa": 120.0,
        }
    ]


def test_equivalent_block_and_closed_time_series_have_same_miner_damage() -> None:
    block_payload = _payload()
    block_payload["spectrum"]["blocks"] = [
        {"amplitude": 120.0, "mean": 0.0, "cycles": 1.0}
    ]
    block_result = calculate_fatigue_reliability(block_payload)

    series_payload = _payload()
    series_payload["spectrum"] = {
        "kind": "time_series",
        "value_kind": "stress",
        "condition": {"temperature_c": 23.0, "r_ratio": -1.0},
        "series": [{"value": -120.0}, {"value": 120.0}, {"value": -120.0}],
    }
    series_result = calculate_fatigue_reliability(series_payload)
    assert series_result["damage"]["damage_per_spectrum_block"] == pytest.approx(
        block_result["damage"]["damage_per_spectrum_block"], rel=1e-12
    )


def test_zero_spectrum_cycles_are_rejected() -> None:
    payload = _payload()
    payload["spectrum"]["blocks"] = [
        {"amplitude": 120.0, "mean": 0.0, "cycles": 0.0}
    ]
    with pytest.raises(InputError, match="cycles"):
        calculate_fatigue_reliability(payload)
