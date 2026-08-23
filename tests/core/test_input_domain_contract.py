"""Phase 0/1 contract: finite scalars, safety >= 1, KA >= 1, dict root, enums."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Callable

import pytest

from core.bolt.calculator import InputError as BoltInputError
from core.bolt.calculator import calculate_vdi2230_core
from core.bolt.tapped_axial_joint import calculate_tapped_axial_joint
from core.buffer.calculator import InputError as BufferInputError
from core.buffer.calculator import calculate_buffer_energy
from core.hertz.calculator import InputError as HertzInputError
from core.hertz.calculator import calculate_hertz_contact
from core.interference.calculator import InputError as InterferenceInputError
from core.interference.calculator import calculate_interference_fit
from core.spline.calculator import InputError as SplineInputError
from core.spline.calculator import calculate_spline_fit
from core.worm.calculator import InputError as WormInputError
from core.worm.calculator import calculate_worm_geometry

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
NON_FINITE = (math.nan, math.inf, -math.inf)


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def _set_path(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    clone = copy.deepcopy(data)
    cursor: Any = clone
    keys = path.split(".")
    for key in keys[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[keys[-1]] = value
    return clone


def _hertz_payload() -> dict[str, Any]:
    return _load_json("hertz_case_01.json")


def _interference_payload() -> dict[str, Any]:
    return _load_json("interference_case_01.json")["inputs"]


def _worm_payload() -> dict[str, Any]:
    return _load_json("worm_case_01.json")


def _spline_payload() -> dict[str, Any]:
    return _load_json("spline_case_02.json")


def _bolt_payload() -> dict[str, Any]:
    return _load_json("input_case_01.json")


def _tapped_payload() -> dict[str, Any]:
    return _load_json("tapped_axial_joint_case_01.json")


def _buffer_payload() -> dict[str, Any]:
    loading = [{"x_mm": x, "force_n": 200.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
    unloading = [{"x_mm": x, "force_n": 100.0 * x} for x in (0.0, 5.0, 10.0, 20.0, 50.0)]
    return {
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


CALCULATORS: list[tuple[str, Callable[[dict[str, Any]], Any], type[Exception], Callable[[], dict[str, Any]]]] = [
    ("hertz", calculate_hertz_contact, HertzInputError, _hertz_payload),
    ("interference", calculate_interference_fit, InterferenceInputError, _interference_payload),
    ("worm", calculate_worm_geometry, WormInputError, _worm_payload),
    ("buffer", calculate_buffer_energy, BufferInputError, _buffer_payload),
    ("spline", calculate_spline_fit, SplineInputError, _spline_payload),
    ("bolt", calculate_vdi2230_core, BoltInputError, _bolt_payload),
    ("tapped", calculate_tapped_axial_joint, BoltInputError, _tapped_payload),
]


SCALAR_PATHS: dict[str, tuple[str, ...]] = {
    "hertz": ("checks.allowable_p0_mpa", "materials.e1_mpa", "loads.normal_force_n"),
    "interference": ("materials.shaft_yield_mpa", "materials.hub_yield_mpa", "geometry.shaft_d_mm"),
    "worm": (
        "load_capacity.allowable_contact_stress_mpa",
        "load_capacity.allowable_root_stress_mpa",
        "operating.input_torque_nm",
    ),
    "buffer": ("impact.available_stroke_mm", "impact.allowable_peak_force_n", "impact.mass_kg"),
    "spline": ("loads.torque_required_nm", "spline.p_allowable_mpa", "checks.flank_safety_min"),
    "bolt": ("fastener.Rp02", "loads.FA_max", "thread_strip.safety_required"),
    "tapped": ("fastener.Rp02", "thread_strip.safety_required", "checks.yield_safety_operating"),
}


SAFETY_CASES: list[tuple[str, Callable, type[Exception], Callable[[], dict], str]] = [
    ("bolt", calculate_vdi2230_core, BoltInputError, _bolt_payload, "thread_strip.safety_required"),
    ("tapped", calculate_tapped_axial_joint, BoltInputError, _tapped_payload, "thread_strip.safety_required"),
    ("spline", calculate_spline_fit, SplineInputError, _spline_payload, "checks.flank_safety_min"),
    ("worm_contact", calculate_worm_geometry, WormInputError, _worm_payload, "load_capacity.required_contact_safety"),
    ("worm_root", calculate_worm_geometry, WormInputError, _worm_payload, "load_capacity.required_root_safety"),
    ("interference_slip", calculate_interference_fit, InterferenceInputError, _interference_payload, "checks.slip_safety_min"),
    ("interference_stress", calculate_interference_fit, InterferenceInputError, _interference_payload, "checks.stress_safety_min"),
]


KA_CASES: list[tuple[str, Callable, type[Exception], Callable[[], dict], str]] = [
    ("spline", calculate_spline_fit, SplineInputError, _spline_payload, "loads.application_factor_ka"),
    ("interference", calculate_interference_fit, InterferenceInputError, _interference_payload, "loads.application_factor_ka"),
    ("worm_ka", calculate_worm_geometry, WormInputError, _worm_payload, "operating.application_factor"),
    ("worm_kv", calculate_worm_geometry, WormInputError, _worm_payload, "load_capacity.dynamic_factor_kv"),
    ("worm_kha", calculate_worm_geometry, WormInputError, _worm_payload, "load_capacity.transverse_load_factor_kha"),
    ("worm_khb", calculate_worm_geometry, WormInputError, _worm_payload, "load_capacity.face_load_factor_khb"),
]


@pytest.mark.parametrize("name,calculate,error_cls,factory", CALCULATORS)
def test_root_list_raises_input_error(name: str, calculate, error_cls, factory) -> None:
    with pytest.raises(error_cls, match="字典"):
        calculate([])  # type: ignore[arg-type]


@pytest.mark.parametrize("name,calculate,error_cls,factory", CALCULATORS)
@pytest.mark.parametrize("bad", NON_FINITE)
def test_nonfinite_scalars_raise_input_error(name: str, calculate, error_cls, factory, bad: float) -> None:
    for path in SCALAR_PATHS[name]:
        data = _set_path(factory(), path, bad)
        if name == "bolt" and path == "thread_strip.safety_required":
            data.setdefault("thread_strip", {})["m_eff"] = 10.0
            data["thread_strip"]["tau_BM"] = 400.0
        with pytest.raises(error_cls):
            calculate(data)


@pytest.mark.parametrize("name,calculate,error_cls,factory,path", SAFETY_CASES)
def test_safety_min_rejects_below_one(name, calculate, error_cls, factory, path) -> None:
    data = _set_path(factory(), path, 0.5)
    if name == "bolt":
        data.setdefault("thread_strip", {})["m_eff"] = 10.0
        data["thread_strip"]["tau_BM"] = 400.0
    with pytest.raises(error_cls, match=">= 1"):
        calculate(data)


@pytest.mark.parametrize("name,calculate,error_cls,factory,path", SAFETY_CASES)
@pytest.mark.parametrize("ok_value", [1.0, 1.5])
def test_safety_min_allows_one_and_above(name, calculate, error_cls, factory, path, ok_value: float) -> None:
    data = _set_path(factory(), path, ok_value)
    if name == "bolt":
        data.setdefault("thread_strip", {})["m_eff"] = 10.0
        data["thread_strip"]["tau_BM"] = 400.0
    result = calculate(data)
    assert isinstance(result, dict)


@pytest.mark.parametrize("name,calculate,error_cls,factory,path", KA_CASES)
def test_load_amplification_rejects_below_one(name, calculate, error_cls, factory, path) -> None:
    data = _set_path(factory(), path, 0.1)
    with pytest.raises(error_cls, match=">= 1"):
        calculate(data)


@pytest.mark.parametrize("name,calculate,error_cls,factory,path", KA_CASES)
@pytest.mark.parametrize("ok_value", [1.0, 1.25])
def test_load_amplification_allows_one_and_above(name, calculate, error_cls, factory, path, ok_value: float) -> None:
    data = _set_path(factory(), path, ok_value)
    result = calculate(data)
    assert isinstance(result, dict)


def test_worm_case_01_low_safety_is_input_error_not_pass() -> None:
    data = _worm_payload()
    data["load_capacity"]["required_contact_safety"] = 0.01
    data["load_capacity"]["required_root_safety"] = 0.01
    with pytest.raises(WormInputError):
        calculate_worm_geometry(data)


def test_worm_case_01_tiny_application_factor_is_input_error() -> None:
    data = _worm_payload()
    data["operating"]["application_factor"] = 0.001
    with pytest.raises(WormInputError):
        calculate_worm_geometry(data)


def test_spline_high_torque_low_flank_safety_is_input_error() -> None:
    data = _spline_payload()
    data["loads"]["torque_required_nm"] = 30000.0
    data["checks"]["flank_safety_min"] = 0.1
    with pytest.raises(SplineInputError):
        calculate_spline_fit(data)


def test_spline_high_torque_tiny_ka_is_input_error() -> None:
    data = _spline_payload()
    data["loads"]["torque_required_nm"] = 30000.0
    data["loads"]["application_factor_ka"] = 0.1
    with pytest.raises(SplineInputError):
        calculate_spline_fit(data)


def test_spline_unknown_mode_is_input_error() -> None:
    data = _spline_payload()
    data["mode"] = "splne_only"
    with pytest.raises(SplineInputError, match="mode"):
        calculate_spline_fit(data)


def test_interference_raised_torque_tiny_ka_is_input_error() -> None:
    data = _interference_payload()
    data["loads"]["torque_required_nm"] = 200.0
    data["loads"]["application_factor_ka"] = 0.1
    with pytest.raises(InterferenceInputError):
        calculate_interference_fit(data)


def test_hertz_infinite_allowable_is_input_error() -> None:
    data = _hertz_payload()
    data["checks"]["allowable_p0_mpa"] = math.inf
    with pytest.raises(HertzInputError):
        calculate_hertz_contact(data)


@pytest.mark.parametrize("field", ["available_stroke_mm", "allowable_peak_force_n"])
def test_buffer_infinite_limits_are_input_error(field: str) -> None:
    data = _buffer_payload()
    data["impact"][field] = math.inf
    with pytest.raises(BufferInputError):
        calculate_buffer_energy(data)


def test_happy_path_examples_still_calculate() -> None:
    assert isinstance(calculate_hertz_contact(_hertz_payload()), dict)
    assert isinstance(calculate_interference_fit(_interference_payload()), dict)
    assert isinstance(calculate_worm_geometry(_worm_payload()), dict)
    assert isinstance(calculate_spline_fit(_spline_payload()), dict)
    assert isinstance(calculate_vdi2230_core(_bolt_payload()), dict)
    assert isinstance(calculate_tapped_axial_joint(_tapped_payload()), dict)
    assert isinstance(calculate_buffer_energy(_buffer_payload()), dict)
