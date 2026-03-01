"""VDI 2230 core bolt verification functions."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict


class InputError(ValueError):
    """Raised when input data is incomplete or physically invalid."""


def _require(section: Dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        raise InputError(f"Missing required field: {section_name}.{key}")
    return section[key]


def _positive(value: float, name: str, allow_zero: bool = False) -> float:
    if allow_zero and value == 0:
        return value
    if value <= 0:
        raise InputError(f"{name} must be > 0, got {value}")
    return value


def load_input_json(path: Path) -> Dict[str, Any]:
    """Load input JSON and normalize errors as InputError."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise InputError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"Input file is not valid JSON: {exc}") from exc


def _derive_thread_geometry(d: float, p: float, fastener: Dict[str, Any]) -> Dict[str, float]:
    as_val = float(fastener.get("As", math.pi / 4.0 * (d - 0.9382 * p) ** 2))
    d2 = float(fastener.get("d2", d - 0.64952 * p))
    d3 = float(fastener.get("d3", d - 1.22687 * p))
    return {
        "As": _positive(as_val, "fastener.As"),
        "d2": _positive(d2, "fastener.d2"),
        "d3": _positive(d3, "fastener.d3"),
    }


def _resolve_compliance(stiffness: Dict[str, Any]) -> Dict[str, float]:
    has_compliance = "bolt_compliance" in stiffness and "clamped_compliance" in stiffness
    has_stiffness = "bolt_stiffness" in stiffness and "clamped_stiffness" in stiffness

    if has_compliance:
        delta_s = _positive(float(stiffness["bolt_compliance"]), "stiffness.bolt_compliance")
        delta_p = _positive(float(stiffness["clamped_compliance"]), "stiffness.clamped_compliance")
    elif has_stiffness:
        k_s = _positive(float(stiffness["bolt_stiffness"]), "stiffness.bolt_stiffness")
        k_p = _positive(float(stiffness["clamped_stiffness"]), "stiffness.clamped_stiffness")
        delta_s = 1.0 / k_s
        delta_p = 1.0 / k_p
    else:
        raise InputError(
            "Provide either stiffness.{bolt_compliance,clamped_compliance} "
            "or stiffness.{bolt_stiffness,clamped_stiffness}"
        )

    n = float(stiffness.get("load_introduction_factor_n", 1.0))
    _positive(n, "stiffness.load_introduction_factor_n")
    return {"delta_s": delta_s, "delta_p": delta_p, "n": n}


def calculate_vdi2230_core(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate VDI 2230 core-chain outputs for a single bolt joint."""
    fastener = data.get("fastener", {})
    tightening = data.get("tightening", {})
    loads = data.get("loads", {})
    stiffness = data.get("stiffness", {})
    bearing = data.get("bearing", {})
    checks = data.get("checks", {})

    d = _positive(float(_require(fastener, "d", "fastener")), "fastener.d")
    p = _positive(float(_require(fastener, "p", "fastener")), "fastener.p")
    rp02 = _positive(float(_require(fastener, "Rp02", "fastener")), "fastener.Rp02")
    alpha_a = _positive(float(_require(tightening, "alpha_A", "tightening")), "tightening.alpha_A")
    mu_thread = _positive(float(_require(tightening, "mu_thread", "tightening")), "tightening.mu_thread")
    mu_bearing = _positive(float(_require(tightening, "mu_bearing", "tightening")), "tightening.mu_bearing")
    utilization = _positive(float(tightening.get("utilization", 0.9)), "tightening.utilization")
    prevailing_torque = float(tightening.get("prevailing_torque", 0.0))
    flank_angle_deg = float(tightening.get("thread_flank_angle_deg", 60.0))

    fa_max = _positive(float(_require(loads, "FA_max", "loads")), "loads.FA_max", allow_zero=True)
    fq_max = _positive(float(loads.get("FQ_max", 0.0)), "loads.FQ_max", allow_zero=True)
    seal_force_required = _positive(
        float(loads.get("seal_force_required", 0.0)),
        "loads.seal_force_required",
        allow_zero=True,
    )
    embed_loss = _positive(float(loads.get("embed_loss", 0.0)), "loads.embed_loss", allow_zero=True)
    thermal_force_loss = _positive(
        float(loads.get("thermal_force_loss", 0.0)),
        "loads.thermal_force_loss",
        allow_zero=True,
    )
    slip_mu = float(loads.get("slip_friction_coefficient", mu_bearing))
    if fq_max > 0 and slip_mu <= 0:
        raise InputError("loads.slip_friction_coefficient must be > 0 when loads.FQ_max > 0")
    interfaces = float(loads.get("friction_interfaces", 1.0))
    _positive(interfaces, "loads.friction_interfaces")

    bearing_d_inner = _positive(
        float(_require(bearing, "bearing_d_inner", "bearing")),
        "bearing.bearing_d_inner",
    )
    bearing_d_outer = _positive(
        float(_require(bearing, "bearing_d_outer", "bearing")),
        "bearing.bearing_d_outer",
    )
    if bearing_d_outer <= bearing_d_inner:
        raise InputError("bearing.bearing_d_outer must be greater than bearing.bearing_d_inner")

    geometry = _derive_thread_geometry(d, p, fastener)
    compliance = _resolve_compliance(stiffness)

    delta_s = compliance["delta_s"]
    delta_p = compliance["delta_p"]
    n = compliance["n"]
    phi = delta_p / (delta_s + delta_p)
    phi_n = n * phi

    f_slip_required = 0.0 if fq_max == 0 else fq_max / (slip_mu * interfaces)
    f_k_required = max(seal_force_required, f_slip_required)

    fm_min = f_k_required + (1.0 - phi_n) * fa_max + embed_loss + thermal_force_loss
    if fm_min <= 0:
        raise InputError("Calculated FMmin <= 0; check loads/stiffness inputs.")
    fm_max = alpha_a * fm_min

    flank_angle = math.radians(flank_angle_deg)
    lead_angle = math.atan(p / (math.pi * geometry["d2"]))
    friction_angle = math.atan(mu_thread / math.cos(flank_angle / 2.0))
    k_thread = (geometry["d2"] / 2.0) * math.tan(lead_angle + friction_angle)
    d_km = (bearing_d_inner + bearing_d_outer) / 2.0
    k_bearing = mu_bearing * d_km / 2.0

    def tightening_torque(preload: float) -> float:
        return preload * (k_thread + k_bearing) / 1000.0 + prevailing_torque

    ma_min = tightening_torque(fm_min)
    ma_max = tightening_torque(fm_max)

    m_thread = fm_max * k_thread
    sigma_ax_assembly = fm_max / geometry["As"]
    tau_assembly = 16.0 * m_thread / (math.pi * geometry["d3"] ** 3)
    sigma_vm_assembly = math.sqrt(sigma_ax_assembly**2 + 3.0 * tau_assembly**2)
    sigma_allow_assembly = utilization * rp02
    pass_assembly = sigma_vm_assembly <= sigma_allow_assembly

    f_bolt_work_max = fm_max + phi_n * fa_max
    sigma_ax_work = f_bolt_work_max / geometry["As"]
    yield_safety_operating = _positive(
        float(checks.get("yield_safety_operating", 1.1)),
        "checks.yield_safety_operating",
    )
    sigma_allow_work = rp02 / yield_safety_operating
    pass_work = sigma_ax_work <= sigma_allow_work

    f_k_residual = fm_min - embed_loss - thermal_force_loss - (1.0 - phi_n) * fa_max
    residual_tol = max(1e-6, 1e-9 * max(abs(f_k_residual), abs(f_k_required), 1.0))
    pass_residual = f_k_residual + residual_tol >= f_k_required

    if phi_n <= 0:
        f_a_perm = math.inf
        pass_additional = False
    else:
        f_a_perm = 0.1 * rp02 * geometry["As"] / phi_n
        pass_additional = fa_max <= f_a_perm

    warnings = []
    if phi_n >= 1.0:
        warnings.append(
            "phi_n >= 1.0, axial external load almost fully enters bolt; check stiffness model and n."
        )
    if utilization > 0.95:
        warnings.append("High assembly utilization (>0.95). Verify friction scatter and process capability.")

    checks_out = {
        "assembly_von_mises_ok": pass_assembly,
        "operating_axial_ok": pass_work,
        "residual_clamp_ok": pass_residual,
        "additional_load_ok": pass_additional,
    }

    return {
        "inputs_echo": data,
        "derived_geometry_mm": geometry,
        "stiffness_model": {"delta_s_mm_per_n": delta_s, "delta_p_mm_per_n": delta_p, "n": n},
        "intermediate": {
            "phi": phi,
            "phi_n": phi_n,
            "F_slip_required_N": f_slip_required,
            "F_K_required_N": f_k_required,
            "FMmin_N": fm_min,
            "FMmax_N": fm_max,
            "k_thread_mm": k_thread,
            "k_bearing_mm": k_bearing,
            "lead_angle_deg": math.degrees(lead_angle),
            "friction_angle_deg": math.degrees(friction_angle),
            "Dkm_mm": d_km,
            "M_thread_Nmm_at_FMmax": m_thread,
        },
        "torque": {"MA_min_Nm": ma_min, "MA_max_Nm": ma_max},
        "stresses_mpa": {
            "sigma_ax_assembly": sigma_ax_assembly,
            "tau_assembly": tau_assembly,
            "sigma_vm_assembly": sigma_vm_assembly,
            "sigma_allow_assembly": sigma_allow_assembly,
            "sigma_ax_work": sigma_ax_work,
            "sigma_allow_work": sigma_allow_work,
        },
        "forces": {
            "F_bolt_work_max_N": f_bolt_work_max,
            "F_K_residual_N": f_k_residual,
            "FA_perm_N": f_a_perm,
        },
        "checks": checks_out,
        "overall_pass": all(checks_out.values()),
        "warnings": warnings,
        "scope_note": (
            "This is a VDI 2230 core-chain implementation (engineering first pass), "
            "not a full-standard all-cases solver."
        ),
    }

