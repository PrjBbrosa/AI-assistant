"""Independent engineering benchmarks for every public calculator entry point.

The expected values below are derived from public references or elementary
mechanics, never copied from calculator output.  See the benchmark register in
``docs/references/2026-08-24-independent-calculation-benchmarks.md`` for source,
formula, units, tolerance, assumptions, and scope boundaries.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest

from core.bolt._common import derive_thread_section
from core.bolt.calculator import calculate_vdi2230_core
from core.bolt.grades import BOLT_GRADE_TABLE
from core.bolt.tapped_axial_joint import (
    _ASV_TABLE_ROLLED,
    _fatigue_limit_asv,
    calculate_tapped_axial_joint,
)
from core.buffer.calculator import calculate_buffer_energy
from core.hertz.calculator import calculate_hertz_contact
from core.interference.calculator import calculate_interference_fit
from core.spline.calculator import calculate_spline_fit
from core.worm.calculator import calculate_worm_geometry

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
TAPPED_CASE_01 = EXAMPLES_DIR / "tapped_axial_joint_case_01.json"


def _tapped_case_01() -> dict:
    return json.loads(TAPPED_CASE_01.read_text(encoding="utf-8"))


def test_m8x125_thread_section_matches_iso724_example_comment() -> None:
    """derive_thread_section vs ISO 724 / example comment values.

    Source, examples/tapped_axial_joint_case_01.json _comment:
        "M8 x 1.25, grade 8.8 — light-duty tapped steel-to-steel joint.
         Values from ISO 898-1 (Rp0.2 min 640 MPa for 8.8, d<=16),
         ISO 724 (thread geometry), ..."

    The same file records the documented M8x1.25 section as
    As=36.6 mm2, d2=7.188 mm, d3=6.466 mm.
    """
    case = _tapped_case_01()
    comment = str(case.get("_comment", ""))
    fastener = case["fastener"]

    assert "ISO 724" in comment
    assert fastener["d"] == 8.0
    assert fastener["p"] == 1.25
    assert fastener["As"] == 36.6
    assert fastener["d2"] == 7.188
    assert fastener["d3"] == 6.466

    derived = derive_thread_section(fastener["d"], fastener["p"])
    # As is commonly tabulated to 1 decimal (36.6 mm2); d2/d3 to 0.001 mm.
    assert derived["As"] == pytest.approx(fastener["As"], abs=0.05)
    assert derived["d2"] == pytest.approx(fastener["d2"], abs=1e-3)
    assert derived["d3"] == pytest.approx(fastener["d3"], abs=1e-3)


def test_grade_88_rp02_matches_iso898_1_example_comment() -> None:
    """BOLT_GRADE_TABLE 8.8 -> 640 matches the ISO 898-1 example comment.

    Source, examples/tapped_axial_joint_case_01.json _comment:
        "Values from ISO 898-1 (Rp0.2 min 640 MPa for 8.8, d<=16), ..."

    grades.py documents the 8.8 preset as 640 MPa (GB/T 3098.1 style, matching
    ISO 898-1 for 8.8 with d<=16).
    """
    case = _tapped_case_01()
    comment = str(case.get("_comment", ""))

    assert "ISO 898-1" in comment
    assert "640" in comment
    assert case["fastener"]["grade"] == "8.8"
    assert case["fastener"]["Rp02"] == 640.0
    assert BOLT_GRADE_TABLE["8.8"] == 640
    assert BOLT_GRADE_TABLE["8.8"] == case["fastener"]["Rp02"]


def test_asv_d8_rolled_matches_vdi_table_a4_example_comment() -> None:
    """VDI 2230-1 Table A4 ASV for d=8 rolled is 47 MPa in comment and table.

    Source, examples/tapped_axial_joint_case_01.json _comment:
        "VDI 2230-1:2015 Table A4 (sigma_ASV=47 MPa at d=8, rolled)"

    _ASV_TABLE_ROLLED in core/bolt/tapped_axial_joint.py is annotated
    "VDI 2230-1:2015, Table A4" and contains (8, 47). Lookup is
    _fatigue_limit_asv, not the overall joint PASS/FAIL.
    """
    case = _tapped_case_01()
    comment = str(case.get("_comment", ""))

    assert "Table A4" in comment
    assert "sigma_ASV=47" in comment
    assert "d=8" in comment
    assert (8, 47) in _ASV_TABLE_ROLLED
    assert _fatigue_limit_asv(8.0, "rolled") == pytest.approx(47.0)


def test_bolt_calculator_matches_two_spring_external_load_sharing() -> None:
    """NASA RP-1228: Fb = Fi + kb/(kb+kc) * Fe before separation."""
    payload = {
        "fastener": {"d": 10.0, "p": 1.5, "Rp02": 640.0},
        "tightening": {
            "alpha_A": 1.0,
            "mu_thread": 0.12,
            "mu_bearing": 0.12,
            "utilization": 0.9,
            "thread_flank_angle_deg": 60.0,
        },
        "loads": {
            "FA_max": 1000.0,
            "FQ_max": 0.0,
            "seal_force_required": 0.0,
            "embed_loss": 0.0,
            "thermal_force_loss": 0.0,
            "FM_min_input": 10000.0,
            "slip_friction_coefficient": 0.2,
            "friction_interfaces": 1.0,
        },
        # Compliance is inverse stiffness.  Therefore kb/(kb+kc)
        # = delta_p/(delta_s+delta_p) = 3/(2+3) = 0.6.
        "stiffness": {
            "bolt_compliance": 2.0e-6,
            "clamped_compliance": 3.0e-6,
            "load_introduction_factor_n": 1.0,
        },
        "bearing": {
            "bearing_d_inner": 11.0,
            "bearing_d_outer": 20.0,
            "p_G_allow": 1000.0,
        },
        "clamped": {"part_count": 1, "total_thickness": 20.0},
        "operating": {},
        "options": {"joint_type": "tapped", "calculation_mode": "verify"},
        "checks": {"yield_safety_operating": 1.1},
    }

    result = calculate_vdi2230_core(payload)

    assert result["intermediate"]["phi_n"] == pytest.approx(0.6, abs=1e-12)
    assert result["forces"]["F_bolt_work_max_N"] == pytest.approx(10600.0, abs=1e-9)

    # Dimensional scaling: at fixed stiffness ratio, doubling external force
    # doubles only the added bolt force (0.6*Fe), not the preload.
    scaled = deepcopy(payload)
    scaled["loads"]["FA_max"] = 2000.0
    scaled_result = calculate_vdi2230_core(scaled)
    assert scaled_result["forces"]["F_bolt_work_max_N"] == pytest.approx(
        11200.0,
        abs=1e-9,
    )


def test_tapped_axial_calculator_matches_direct_force_superposition() -> None:
    """Pure axial no-clamped-member model: Fmax=alpha*Fpreload+FAmax."""
    payload = _tapped_case_01()

    result = calculate_tapped_axial_joint(payload)

    # Independent hand calculation: 1.6*8000 + 1200 = 14000 N.
    assert result["forces"]["F_service_max_N"] == pytest.approx(14000.0, abs=1e-9)
    # NASA metric thread area formula gives As=36.6085 mm2 for M8x1.25;
    # elementary axial stress F/As therefore gives 382.43 MPa.
    assert result["stresses_mpa"]["sigma_ax_service_max"] == pytest.approx(
        382.43,
        abs=0.02,
    )
    assert result["overall_status"] == "pass"

    # Halving FA_max halves its additive force/stress contribution. The
    # preload remains 1.6*8000 = 12800 N.
    scaled = deepcopy(payload)
    scaled["service"]["FA_max"] = 600.0
    scaled_result = calculate_tapped_axial_joint(scaled)
    assert scaled_result["forces"]["F_service_max_N"] == pytest.approx(13400.0)
    assert scaled_result["stresses_mpa"]["sigma_ax_service_max"] == pytest.approx(
        13400.0 / 36.608465,
        abs=0.02,
    )
    assert scaled_result["overall_status"] == "pass"


def test_interference_calculator_matches_published_shaft_collar_problem() -> None:
    """PSU Problem S14: 40.026/40 mm steel fit in 80 mm collar -> 50 MPa."""
    payload = {
        "geometry": {
            "shaft_d_mm": 40.0,
            "hub_outer_d_mm": 80.0,
            "fit_length_mm": 20.0,
        },
        # Published diametral interference is 0.026 mm = 26 um.
        "fit": {"delta_min_um": 26.0, "delta_max_um": 26.0},
        "materials": {
            "shaft_e_mpa": 205000.0,
            "shaft_nu": 0.3,
            "shaft_yield_mpa": 1000.0,
            "hub_e_mpa": 205000.0,
            "hub_nu": 0.3,
            "hub_yield_mpa": 1000.0,
        },
        "loads": {
            "torque_required_nm": 0.0,
            "axial_force_required_n": 0.0,
            "application_factor_ka": 1.0,
        },
        "friction": {"mu_torque": 0.15, "mu_axial": 0.15, "mu_assembly": 0.1},
        "roughness": {"smoothing_factor": 0.0, "shaft_rz_um": 0.0, "hub_rz_um": 0.0},
        "checks": {"slip_safety_min": 1.2, "stress_safety_min": 1.2},
        "options": {"curve_points": 11},
    }

    result = calculate_interference_fit(payload)

    # The published answer is stated as approximately 50 MPa (two significant
    # digits), so the executable tolerance must not imply false precision.
    assert result["pressure_mpa"]["p_min"] == pytest.approx(50.0, abs=0.5)
    assert result["pressure_mpa"]["p_max"] == pytest.approx(50.0, abs=0.5)

    # Linear elasticity: pressure is proportional to interference. Halving
    # the diametral interference from 26 um to 13 um gives about 25 MPa.
    scaled = deepcopy(payload)
    scaled["fit"] = {"delta_min_um": 13.0, "delta_max_um": 13.0}
    scaled_result = calculate_interference_fit(scaled)
    assert scaled_result["pressure_mpa"]["p_min"] == pytest.approx(25.0, abs=0.5)
    assert scaled_result["pressure_mpa"]["p_max"] == pytest.approx(25.0, abs=0.5)


def test_hertz_calculator_matches_mit_line_contact_equations() -> None:
    """MIT line-contact equations for a 30 mm cylinder on an elastic plane."""
    payload = json.loads((EXAMPLES_DIR / "hertz_case_01.json").read_text(encoding="utf-8"))

    result = calculate_hertz_contact(payload)

    # Independent evaluation of MIT's b and q equations gives these fixed
    # values for F=12 kN, L=20 mm, R=30 mm and the two steel elastic pairs.
    assert result["contact"]["semi_width_mm"] == pytest.approx(0.446396, abs=1e-6)
    assert result["contact"]["p0_mpa"] == pytest.approx(855.680, abs=0.002)

    # MIT line-contact equations give b proportional to sqrt(F) and p0
    # proportional to sqrt(F). Quadrupling F therefore doubles both.
    scaled = deepcopy(payload)
    scaled["loads"]["normal_force_n"] = 48000.0
    scaled_result = calculate_hertz_contact(scaled)
    assert scaled_result["contact"]["semi_width_mm"] == pytest.approx(
        2.0 * 0.446396,
        abs=2e-6,
    )
    assert scaled_result["contact"]["p0_mpa"] == pytest.approx(
        2.0 * 855.680,
        abs=0.004,
    )


@pytest.mark.parametrize(
    ("allowable_p0_mpa", "expected_pass"),
    [(1000.0, True), (900.0, True), (800.0, False), (500.0, False)],
    ids=("pass-1000", "pass-900", "fail-800", "fail-500"),
)
def test_hertz_independent_threshold_contract_matrix(
    allowable_p0_mpa: float,
    expected_pass: bool,
) -> None:
    """Pass/fail thresholds bracket the independent MIT value 855.680 MPa."""
    payload = json.loads((EXAMPLES_DIR / "hertz_case_01.json").read_text(encoding="utf-8"))
    payload["checks"]["allowable_p0_mpa"] = allowable_p0_mpa

    result = calculate_hertz_contact(payload)

    assert result["checks"]["contact_stress_ok"] is expected_pass
    assert result["overall_pass"] is expected_pass


def test_worm_calculator_matches_public_gear_geometry_kinematics() -> None:
    """KHK axial-module worm relations: d1=q*m, d2=z2*m, n2=n1/i."""
    payload = json.loads((EXAMPLES_DIR / "worm_case_01.json").read_text(encoding="utf-8"))

    result = calculate_worm_geometry(payload)
    geometry = result["geometry"]

    assert geometry["ratio"] == pytest.approx(40.0, abs=1e-12)
    assert geometry["pitch_diameter_worm_mm"] == pytest.approx(40.0, abs=1e-12)
    assert geometry["pitch_diameter_wheel_mm"] == pytest.approx(160.0, abs=1e-12)
    assert geometry["wheel_speed_rpm"] == pytest.approx(37.5, abs=1e-12)
    assert geometry["theoretical_center_distance_mm"] == pytest.approx(100.0, abs=1e-12)

    # Scaling m by 0.5 scales all reference diameters and center distance by
    # 0.5, while tooth-count ratio and rotational speed ratio stay invariant.
    scaled = deepcopy(payload)
    scaled["geometry"]["module_mm"] = 2.0
    scaled["geometry"]["center_distance_mm"] = 50.0
    scaled_result = calculate_worm_geometry(scaled)["geometry"]
    assert scaled_result["pitch_diameter_worm_mm"] == pytest.approx(20.0)
    assert scaled_result["pitch_diameter_wheel_mm"] == pytest.approx(80.0)
    assert scaled_result["theoretical_center_distance_mm"] == pytest.approx(50.0)
    assert scaled_result["ratio"] == pytest.approx(40.0)
    assert scaled_result["wheel_speed_rpm"] == pytest.approx(37.5)


@pytest.mark.parametrize(
    ("gamma_delta_deg", "allowable_mpa", "expected_pass"),
    [(0.0, 1e6, True), (0.49, 1e6, True), (0.51, 1e6, False), (0.0, 1.0, False)],
    ids=("pass-exact", "pass-inside-geometry-boundary", "fail-outside-geometry-boundary", "fail-low-allowables"),
)
def test_worm_internal_pass_fail_contract_matrix(
    gamma_delta_deg: float,
    allowable_mpa: float,
    expected_pass: bool,
) -> None:
    """Internal verdict contract; this is not an external stress benchmark."""
    payload = json.loads((EXAMPLES_DIR / "worm_case_01.json").read_text(encoding="utf-8"))
    z1 = float(payload["geometry"]["z1"])
    q = float(payload["geometry"]["diameter_factor_q"])
    payload["geometry"]["lead_angle_deg"] = math.degrees(math.atan(z1 / q)) + gamma_delta_deg
    payload["load_capacity"]["allowable_contact_stress_mpa"] = allowable_mpa
    payload["load_capacity"]["allowable_root_stress_mpa"] = allowable_mpa

    result = calculate_worm_geometry(payload)

    assert result["load_capacity"]["overall_pass"] is expected_pass


def test_spline_calculator_matches_independent_flank_bearing_formula() -> None:
    """Mean flank pressure p=2*T*KA*k/(z*h*dm*L), a simplified precheck."""
    payload = json.loads((EXAMPLES_DIR / "spline_case_01.json").read_text(encoding="utf-8"))

    result = calculate_spline_fit(payload)

    # Tdesign=62.5 N.m, k=1.3, z=10, h=1.125 mm, dm=13.625 mm,
    # L=40 mm -> 26.5036 N/mm2.  This validates only the stated uniform
    # bearing-pressure model, not DIN 5480 geometry or DIN 6892 compliance.
    assert result["scenario_a"]["flank_pressure_mpa"] == pytest.approx(
        26.5036,
        abs=0.0001,
    )
    assert result["overall_pass"] is True

    # The published mean-pressure relation is linear in torque. Doubling
    # torque at fixed geometry and KA therefore doubles flank pressure.
    scaled = deepcopy(payload)
    scaled["loads"]["torque_required_nm"] = 100.0
    scaled_result = calculate_spline_fit(scaled)
    assert scaled_result["scenario_a"]["flank_pressure_mpa"] == pytest.approx(
        2.0 * 26.5036,
        abs=0.0002,
    )


def test_buffer_calculator_matches_work_energy_for_linear_force_curve() -> None:
    """OpenStax work-energy benchmark for F=kx and 1 J initial energy."""
    payload = {
        "curve": {
            "loading": [
                {"x_mm": 0.0, "force_n": 0.0},
                {"x_mm": 10.0, "force_n": 1000.0},
            ],
            "unloading": [
                {"x_mm": 0.0, "force_n": 0.0},
                {"x_mm": 10.0, "force_n": 1000.0},
            ],
        },
        "impact": {
            "mass_kg": 2.0,
            "initial_velocity_m_s": 1.0,
            "available_stroke_mm": 10.0,
            "allowable_peak_force_n": 1000.0,
        },
        "options": {"time_samples": 20},
    }

    result = calculate_buffer_energy(payload)
    impact = result["impact"]

    assert impact["initial_energy_j"] == pytest.approx(1.0, abs=1e-12)
    assert impact["available_energy_capacity_j"] == pytest.approx(5.0, abs=1e-12)
    assert impact["max_compression_mm"] == pytest.approx(math.sqrt(20.0), abs=1e-9)
    assert impact["peak_force_n"] == pytest.approx(100.0 * math.sqrt(20.0), abs=1e-9)

    # Kinetic energy scales with v^2. At v=sqrt(2) m/s the energy doubles;
    # for the same linear spring x and F scale by sqrt(2).
    scaled = deepcopy(payload)
    scaled["impact"]["initial_velocity_m_s"] = math.sqrt(2.0)
    scaled_result = calculate_buffer_energy(scaled)["impact"]
    assert scaled_result["initial_energy_j"] == pytest.approx(2.0, abs=1e-12)
    assert scaled_result["max_compression_mm"] == pytest.approx(math.sqrt(40.0), abs=1e-9)
    assert scaled_result["peak_force_n"] == pytest.approx(100.0 * math.sqrt(40.0), abs=1e-9)
