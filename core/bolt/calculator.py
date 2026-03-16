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


# VDI 2230 表 5.4/1 简化：典型单界面嵌入量 (μm)
_EMBED_FZ_PER_INTERFACE: dict[str, float] = {
    "rough": 3.0,    # Ra ≈ 6.3 μm
    "medium": 2.5,   # Ra ≈ 3.2 μm
    "fine": 1.0,     # Ra ≈ 1.6 μm
}


def _estimate_embed_loss(
    joint_type: str,
    part_count: int,
    surface_class: str,
    delta_s: float,
    delta_p: float,
) -> Dict[str, Any]:
    """根据 VDI 2230 表 5.4/1 估算嵌入损失。"""
    fz_per_if = _EMBED_FZ_PER_INTERFACE.get(surface_class)
    if fz_per_if is None:
        return {
            "embed_auto_estimated": False,
            "embed_auto_value_N": 0.0,
            "embed_interfaces": 0,
            "embed_fz_per_if_um": 0.0,
        }
    if joint_type == "through":
        n_interfaces = part_count + 2
    else:
        n_interfaces = part_count + 1
    fz_total_mm = fz_per_if * n_interfaces * 1e-3
    f_z = fz_total_mm / (delta_s + delta_p)
    return {
        "embed_auto_estimated": True,
        "embed_auto_value_N": f_z,
        "embed_interfaces": n_interfaces,
        "embed_fz_per_if_um": fz_per_if,
    }


def calculate_vdi2230_core(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate VDI 2230 core-chain outputs for a single bolt joint."""
    fastener = data.get("fastener", {})
    tightening = data.get("tightening", {})
    loads = data.get("loads", {})
    stiffness = data.get("stiffness", {})
    bearing = data.get("bearing", {})
    checks = data.get("checks", {})
    operating = data.get("operating", {})
    clamped = data.get("clamped", {})
    options = data.get("options", {})

    check_level = str(options.get("check_level", "basic"))
    if check_level not in {"basic", "thermal", "fatigue"}:
        raise InputError(f"options.check_level 无效：{check_level}")

    calculation_mode = str(options.get("calculation_mode", "design"))
    if calculation_mode not in {"design", "verify"}:
        raise InputError(f"options.calculation_mode 无效：{calculation_mode}")

    joint_type = str(options.get("joint_type", "tapped"))
    if joint_type not in {"tapped", "through"}:
        raise InputError(f"options.joint_type 无效：{joint_type}，应为 tapped 或 through")

    d = _positive(float(_require(fastener, "d", "fastener")), "fastener.d")
    p = _positive(float(_require(fastener, "p", "fastener")), "fastener.p")
    rp02 = _positive(float(_require(fastener, "Rp02", "fastener")), "fastener.Rp02")
    alpha_a = _positive(float(_require(tightening, "alpha_A", "tightening")), "tightening.alpha_A")
    if alpha_a < 1.0:
        raise InputError(f"tightening.alpha_A 必须 >= 1（当前值 {alpha_a}），散差系数不能使 FMmax < FMmin。")
    mu_thread = _positive(float(_require(tightening, "mu_thread", "tightening")), "tightening.mu_thread")
    if mu_thread > 1.0:
        raise InputError(f"tightening.mu_thread 超出合理范围（{mu_thread} > 1），请确认单位。")
    mu_bearing = _positive(float(_require(tightening, "mu_bearing", "tightening")), "tightening.mu_bearing")
    if mu_bearing > 1.0:
        raise InputError(f"tightening.mu_bearing 超出合理范围（{mu_bearing} > 1），请确认单位。")
    utilization = _positive(float(tightening.get("utilization", 0.9)), "tightening.utilization")
    if utilization > 1.0:
        raise InputError(f"tightening.utilization 不能超过 1（当前值 {utilization}）。")
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
    load_cycles = _positive(float(operating.get("load_cycles", 2_000_000.0)), "operating.load_cycles")
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
    if phi_n >= 1.0:
        raise InputError(
            f"载荷分配系数 phi_n = {phi_n:.3f} >= 1，外载全部进入螺栓，无物理意义。"
            "请检查刚度模型（δs/δp）与载荷导入系数 n。"
        )

    # ------------------------------------------------------------------
    # 热预紧力损失自动估算（VDI 2230 温差公式）
    # F_th ≈ |Δα × ΔT| × (c_s × c_p) / (c_s + c_p) × l_K
    # 其中 Δα = α_bolt - α_parts, ΔT = T_bolt - T_parts,
    #      c_s = 1/δ_s, c_p = 1/δ_p 为螺栓和被夹件刚度，l_K 为夹紧长度。
    # 条件：用户手动输入的 thermal_force_loss 为 0 或空时才使用估算值；
    #        需要温度差、刚度和夹紧长度信息齐备才能估算。
    # ------------------------------------------------------------------
    _ALPHA_STEEL_DEFAULT = 11.5e-6  # 1/K
    alpha_bolt = float(operating.get("alpha_bolt", _ALPHA_STEEL_DEFAULT))
    alpha_parts = float(operating.get("alpha_parts", _ALPHA_STEEL_DEFAULT))

    thermal_auto_estimated = False
    thermal_auto_value = 0.0
    if thermal_force_loss == 0.0:
        temp_bolt = operating.get("temp_bolt")
        temp_parts = operating.get("temp_parts")
        l_K = clamped.get("total_thickness")

        if (
            temp_bolt is not None
            and temp_parts is not None
            and l_K is not None
        ):
            try:
                temp_bolt = float(temp_bolt)
                temp_parts = float(temp_parts)
                l_K = float(l_K)
                delta_T = temp_bolt - temp_parts
                if delta_T != 0.0 and l_K > 0.0:
                    c_s = 1.0 / delta_s  # 螺栓刚度 N/mm
                    c_p = 1.0 / delta_p  # 被夹件刚度 N/mm
                    thermal_auto_value = abs(
                        (alpha_bolt - alpha_parts) * delta_T
                        * (c_s * c_p) / (c_s + c_p)
                        * l_K
                    )
                    if thermal_auto_value > 0.0:
                        thermal_force_loss = thermal_auto_value
                        thermal_auto_estimated = True
            except (ValueError, ZeroDivisionError):
                # 参数不全或异常时静默跳过，保留 thermal_force_loss = 0
                pass

    # ------------------------------------------------------------------
    # 嵌入损失自动估算 (VDI 2230 §5.4.2)
    # ------------------------------------------------------------------
    part_count = int(clamped.get("part_count", 1))
    surface_class = clamped.get("surface_class")
    embed_estimation: Dict[str, Any]
    if embed_loss == 0.0 and surface_class is not None:
        embed_estimation = _estimate_embed_loss(
            joint_type, part_count, str(surface_class), delta_s, delta_p
        )
        if embed_estimation["embed_auto_estimated"]:
            embed_loss = embed_estimation["embed_auto_value_N"]
    else:
        embed_estimation = {
            "embed_auto_estimated": False,
            "embed_auto_value_N": 0.0,
            "embed_interfaces": 0,
            "embed_fz_per_if_um": 0.0,
        }

    f_slip_required = 0.0 if fq_max == 0 else fq_max / (slip_mu * interfaces)
    f_k_required = max(seal_force_required, f_slip_required)

    thermal_effective = thermal_force_loss if check_level in {"thermal", "fatigue"} else 0.0
    if calculation_mode == "verify":
        fm_min_input = _positive(
            float(_require(loads, "FM_min_input", "loads")),
            "loads.FM_min_input",
        )
        fm_min = fm_min_input
        r3_note = "校核模式：独立验证已知预紧力是否满足残余夹紧需求"
    else:
        fm_min = f_k_required + (1.0 - phi_n) * fa_max + embed_loss + thermal_effective
        r3_note = "设计模式下 FM_min 由 FK_req 反推，R3 自动满足"
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

    if calculation_mode == "verify":
        f_k_residual = fm_min - embed_loss - thermal_effective - (1.0 - phi_n) * fa_max
        pass_residual = f_k_residual >= f_k_required
    else:
        f_k_residual = f_k_required  # 设计模式下恒等
        pass_residual = True

    thermal_loss_ratio = 0.0 if fm_min <= 0 else thermal_effective / fm_min
    pass_thermal = thermal_loss_ratio <= 0.25

    sigma_a = phi_n * fa_max / (2.0 * geometry["As"])
    sigma_m = (fm_max + 0.5 * phi_n * fa_max) / geometry["As"]
    cycle_factor = (2_000_000.0 / load_cycles) ** 0.08 if load_cycles < 2_000_000.0 else 1.0
    sigma_a_base = 0.18 * rp02 * cycle_factor
    goodman_factor = max(0.1, 1.0 - sigma_m / (0.9 * rp02))
    sigma_a_allow = sigma_a_base * goodman_factor
    pass_fatigue = sigma_a <= sigma_a_allow

    # 附加载荷能力参考估算（非 VDI 2230 正式校核项）：
    # 基于 10% 屈服强度裕量估算允许附加轴向载荷上限，供参考。
    # VDI 2230 对轴向外载的正式控制通过 FMmin 设计（R1）和应力校核（R4/R5）完成。
    if phi_n <= 0:
        f_a_perm = math.inf
        pass_additional = False
    else:
        f_a_perm = 0.1 * rp02 * geometry["As"] / phi_n
        pass_additional = fa_max <= f_a_perm

    # --- R7 支承面压强校核 ---
    p_g_allow = float(bearing.get("p_G_allow", 0.0))
    r7_active = p_g_allow > 0
    r7_note = ""
    if r7_active:
        a_bearing = math.pi / 4.0 * (bearing_d_outer**2 - bearing_d_inner**2)
        p_bearing = fm_max / a_bearing
        pass_bearing = p_bearing <= p_g_allow
        if joint_type == "through":
            r7_note = "通孔连接：螺栓头端与螺母端均需满足支承面压强要求（当前使用同一组支承面参数校核）"
        else:
            r7_note = "螺纹孔连接：仅校核螺栓头端支承面压强"

    warnings = []
    if utilization > 0.95:
        warnings.append("装配利用系数偏高（>0.95），建议核查摩擦散差与装配工艺能力。")
    if check_level in {"thermal", "fatigue"} and thermal_loss_ratio > 0.15:
        warnings.append("热损失占比偏高（>15%），建议核查温差工况与材料热膨胀差。")

    checks_out = {
        "assembly_von_mises_ok": pass_assembly,
        "operating_axial_ok": pass_work,
        "residual_clamp_ok": pass_residual,
    }
    if check_level in {"thermal", "fatigue"}:
        checks_out["thermal_loss_ok"] = pass_thermal
    if check_level == "fatigue":
        checks_out["fatigue_ok"] = pass_fatigue
    if r7_active:
        checks_out["bearing_pressure_ok"] = pass_bearing

    stresses_out = {
        "sigma_ax_assembly": sigma_ax_assembly,
        "tau_assembly": tau_assembly,
        "sigma_vm_assembly": sigma_vm_assembly,
        "sigma_allow_assembly": sigma_allow_assembly,
        "sigma_ax_work": sigma_ax_work,
        "sigma_allow_work": sigma_allow_work,
    }
    if r7_active:
        stresses_out["p_bearing"] = p_bearing
        stresses_out["p_G_allow"] = p_g_allow
        stresses_out["A_bearing_mm2"] = a_bearing

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
        "stresses_mpa": stresses_out,
        "forces": {
            "F_bolt_work_max_N": f_bolt_work_max,
            "F_K_residual_N": f_k_residual,
        },
        "references": {
            "additional_load_ok": pass_additional,
            "FA_perm_N": f_a_perm,
            "is_reference": True,
            "note": "附加载荷能力为参考估算（基于 10% Rp0.2 裕量），非 VDI 2230 正式校核项",
        },
        "checks": checks_out,
        "check_level": check_level,
        "calculation_mode": calculation_mode,
        "joint_type": joint_type,
        "r3_note": r3_note,
        "r7_note": r7_note,
        "thermal": {
            "thermal_loss_effective_N": thermal_effective,
            "thermal_loss_ratio": thermal_loss_ratio,
            "thermal_loss_ratio_limit": 0.25,
            "thermal_auto_estimated": thermal_auto_estimated,
            "thermal_auto_value_N": thermal_auto_value,
            "alpha_bolt": alpha_bolt,
            "alpha_parts": alpha_parts,
        },
        "embed_estimation": embed_estimation,
        "clamped_info": {
            "basic_solid": clamped.get("basic_solid"),
            "part_count": clamped.get("part_count"),
            "total_thickness_mm": clamped.get("total_thickness"),
        },
        "fatigue": {
            "sigma_a": sigma_a,
            "sigma_m": sigma_m,
            "sigma_a_allow": sigma_a_allow,
            "load_cycles": load_cycles,
            "cycle_factor": cycle_factor,
            "goodman_factor": goodman_factor,
        },
        "overall_pass": all(checks_out.values()),
        "warnings": warnings,
        "scope_note": (
            f"连接形式：{'通孔螺栓连接' if joint_type == 'through' else '螺纹孔连接'}。"
            "本工具覆盖 VDI 2230 核心链路（装配强度、服役强度、残余夹紧力），"
            "并提供温度与疲劳的工程化扩展校核。"
        ),
    }
