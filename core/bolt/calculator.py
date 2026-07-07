"""VDI 2230 core bolt verification functions."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict

from ._common import InputError, check_thread_section_consistency, to_float


def _require(section: Dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        raise InputError(f"缺少必填字段: {section_name}.{key}")
    return section[key]


def _positive(value: Any, name: str, allow_zero: bool = False) -> float:
    numeric = to_float(value, name)
    if allow_zero and numeric == 0:
        return numeric
    if numeric <= 0:
        raise InputError(f"{name} 必须 > 0，当前值 {numeric}")
    return numeric


def _float_or_none(value: Any, name: str) -> float | None:
    if value in (None, ""):
        return None
    return to_float(value, name)


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
    # 始终采用 d/p 派生值；用户提供的 As/d2/d3 仅做一致性校验（spec D2）。
    derived = check_thread_section_consistency(d, p, fastener)
    return {
        "As": _positive(derived["As"], "fastener.As"),
        "d2": _positive(derived["d2"], "fastener.d2"),
        "d3": _positive(derived["d3"], "fastener.d3"),
    }


def _resolve_compliance(
    stiffness: Dict[str, Any],
    d: float = 0, p: float = 0,
    bearing_d_inner: float = 0, bearing_d_outer: float = 0,
    clamped: Dict[str, Any] | None = None,
    joint_type: str = "tapped",
) -> Dict[str, float]:
    has_compliance = "bolt_compliance" in stiffness and "clamped_compliance" in stiffness
    has_stiffness = "bolt_stiffness" in stiffness and "clamped_stiffness" in stiffness
    auto_modeled = False

    if has_compliance:
        delta_s = _positive(stiffness["bolt_compliance"], "stiffness.bolt_compliance")
        delta_p = _positive(stiffness["clamped_compliance"], "stiffness.clamped_compliance")
    elif has_stiffness:
        k_s = _positive(stiffness["bolt_stiffness"], "stiffness.bolt_stiffness")
        k_p = _positive(stiffness["clamped_stiffness"], "stiffness.clamped_stiffness")
        delta_s = 1.0 / k_s
        delta_p = 1.0 / k_p
    elif stiffness.get("auto_compliance"):
        from core.bolt.compliance_model import (
            calculate_bolt_compliance, calculate_clamped_compliance,
        )
        E_bolt = _positive(stiffness.get("E_bolt", 210_000), "stiffness.E_bolt")
        cl = clamped or {}

        if "layers" in cl:
            # ---------- 多层模式 ----------
            layers = cl["layers"]
            if not isinstance(layers, list) or not (1 <= len(layers) <= 10):
                raise InputError("被夹件层数须在 1~10 之间")
            l_K = sum(
                _positive(
                    _require(layer, "l_K", f"clamped.layers[{idx}]"),
                    f"clamped.layers[{idx}].l_K",
                )
                for idx, layer in enumerate(layers)
            )
            _positive(l_K, "clamped.total_thickness (各层求和)")
            bolt_r = calculate_bolt_compliance(d, p, l_K, E_bolt, joint_type=joint_type)
            delta_s = bolt_r["delta_s"]
            d_h = bearing_d_inner
            for layer in layers:
                layer.setdefault("d_h", d_h)
            clamp_r = calculate_clamped_compliance(layers=layers)
            delta_p = clamp_r["delta_p"]
        else:
            # ---------- 单层模式（保持不变）----------
            E_clamped = _positive(stiffness.get("E_clamped", 210_000), "stiffness.E_clamped")
            l_K = _positive(cl.get("total_thickness", 0), "clamped.total_thickness")
            bolt_r = calculate_bolt_compliance(d, p, l_K, E_bolt, joint_type=joint_type)
            delta_s = bolt_r["delta_s"]
            solid_type = str(cl.get("basic_solid", "cylinder"))
            D_A = to_float(cl.get("D_A", bearing_d_outer), "clamped.D_A")
            d_h = bearing_d_inner
            D_w = (bearing_d_inner + bearing_d_outer) / 2.0
            if solid_type == "sleeve":
                clamp_r = calculate_clamped_compliance(
                    model=solid_type,
                    D_outer=D_A,
                    D_inner=d_h,
                    l_K=l_K,
                    E_clamped=E_clamped,
                )
            else:
                clamp_r = calculate_clamped_compliance(
                    model=solid_type, d_h=d_h, D_w=D_w, D_A=D_A,
                    l_K=l_K, E_clamped=E_clamped,
                )
            delta_p = clamp_r["delta_p"]
        auto_modeled = True
    else:
        raise InputError(
            "Provide either stiffness.{bolt_compliance,clamped_compliance} "
            "or stiffness.{bolt_stiffness,clamped_stiffness} "
            "or set stiffness.auto_compliance=true with geometry parameters"
        )

    n = _positive(stiffness.get("load_introduction_factor_n", 1.0), "stiffness.load_introduction_factor_n")
    if n > 1.0:
        raise InputError(
            "载荷导入系数 stiffness.load_introduction_factor_n 必须在 (0, 1] 区间，"
            f"当前值 {n}。n > 1 会使 phi_n 进入非物理范围并低估螺栓载荷。"
        )
    return {"delta_s": delta_s, "delta_p": delta_p, "n": n, "auto_modeled": auto_modeled}


# VDI 2230：拧紧方式对应 αA 建议范围
_ALPHA_A_RANGES: dict[str, tuple[float, float]] = {
    "torque": (1.4, 1.8),
    "angle": (1.1, 1.3),
    "hydraulic": (1.05, 1.15),
    "thermal": (1.05, 1.15),
}

# VDI 2230 Table A4：轧制螺纹疲劳极限 σ_ASV (MPa)，与 tapped 模块一致；纸质标准复核为准。
_ASV_TABLE_ROLLED: list[tuple[float, float]] = [
    (6, 50), (8, 47), (10, 44), (12, 41), (14, 39),
    (16, 38), (20, 36), (24, 34), (30, 32), (36, 30),
]
_CUT_THREAD_FACTOR = 0.65  # 切削螺纹约为轧制的 65%


def _fatigue_limit_asv(d: float, surface_treatment: str = "rolled") -> float:
    """VDI 2230 疲劳极限 σ_ASV，按螺纹公称直径线性插值。"""
    table = _ASV_TABLE_ROLLED
    if d <= table[0][0]:
        asv = table[0][1]
    elif d >= table[-1][0]:
        asv = table[-1][1]
    else:
        asv = table[-1][1]
        for i in range(len(table) - 1):
            d0, v0 = table[i]
            d1, v1 = table[i + 1]
            if d0 <= d <= d1:
                asv = v0 + (v1 - v0) * (d - d0) / (d1 - d0)
                break
    if surface_treatment == "cut":
        asv *= _CUT_THREAD_FACTOR
    return asv


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

    tightening_method = str(options.get("tightening_method", "torque"))

    d = _positive(_require(fastener, "d", "fastener"), "fastener.d")
    p = _positive(_require(fastener, "p", "fastener"), "fastener.p")
    rp02 = _positive(_require(fastener, "Rp02", "fastener"), "fastener.Rp02")
    alpha_a = _positive(_require(tightening, "alpha_A", "tightening"), "tightening.alpha_A")
    if alpha_a < 1.0:
        raise InputError(f"tightening.alpha_A 必须 >= 1（当前值 {alpha_a}），散差系数不能使 FMmax < FMmin。")
    mu_thread = _positive(_require(tightening, "mu_thread", "tightening"), "tightening.mu_thread")
    if mu_thread > 1.0:
        raise InputError(f"tightening.mu_thread 超出合理范围（{mu_thread} > 1），请确认单位。")
    mu_bearing = _positive(_require(tightening, "mu_bearing", "tightening"), "tightening.mu_bearing")
    if mu_bearing > 1.0:
        raise InputError(f"tightening.mu_bearing 超出合理范围（{mu_bearing} > 1），请确认单位。")
    utilization = _positive(tightening.get("utilization", 0.9), "tightening.utilization")
    if utilization > 1.0:
        raise InputError(f"tightening.utilization 不能超过 1（当前值 {utilization}）。")
    prevailing_torque = to_float(tightening.get("prevailing_torque", 0.0), "tightening.prevailing_torque")
    flank_angle_deg = to_float(tightening.get("thread_flank_angle_deg", 60.0), "tightening.thread_flank_angle_deg")

    fa_max = _positive(_require(loads, "FA_max", "loads"), "loads.FA_max", allow_zero=True)
    fq_max = _positive(loads.get("FQ_max", 0.0), "loads.FQ_max", allow_zero=True)
    seal_force_required = _positive(
        loads.get("seal_force_required", 0.0),
        "loads.seal_force_required",
        allow_zero=True,
    )
    embed_loss = _positive(loads.get("embed_loss", 0.0), "loads.embed_loss", allow_zero=True)
    thermal_force_loss = _positive(
        loads.get("thermal_force_loss", 0.0),
        "loads.thermal_force_loss",
        allow_zero=True,
    )
    load_cycles = _positive(operating.get("load_cycles", 2_000_000.0), "operating.load_cycles")
    slip_mu = to_float(loads.get("slip_friction_coefficient", mu_bearing), "loads.slip_friction_coefficient")
    if slip_mu > 1.0:
        raise InputError(f"loads.slip_friction_coefficient 摩擦系数必须 <= 1，当前值 {slip_mu}")
    if fq_max > 0 and slip_mu <= 0:
        raise InputError("loads.slip_friction_coefficient 摩擦系数必须 > 0（loads.FQ_max > 0 时需要防滑校核）。")
    interfaces = _positive(loads.get("friction_interfaces", 1.0), "loads.friction_interfaces")

    bearing_d_inner = _positive(
        _require(bearing, "bearing_d_inner", "bearing"),
        "bearing.bearing_d_inner",
    )
    bearing_d_outer = _positive(
        _require(bearing, "bearing_d_outer", "bearing"),
        "bearing.bearing_d_outer",
    )
    if bearing_d_outer <= bearing_d_inner:
        raise InputError("bearing.bearing_d_outer 必须大于 bearing.bearing_d_inner")

    geometry = _derive_thread_geometry(d, p, fastener)
    compliance = _resolve_compliance(
        stiffness, d=d, p=p,
        bearing_d_inner=bearing_d_inner, bearing_d_outer=bearing_d_outer,
        clamped=clamped,
        joint_type=joint_type,
    )

    delta_s = compliance["delta_s"]
    delta_p = compliance["delta_p"]
    n = compliance["n"]
    auto_modeled = compliance.get("auto_modeled", False)
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
    alpha_bolt = _float_or_none(operating.get("alpha_bolt"), "operating.alpha_bolt")
    alpha_parts = _float_or_none(operating.get("alpha_parts"), "operating.alpha_parts")

    thermal_auto_estimated = False
    thermal_auto_value = 0.0
    layer_thermals = operating.get("layer_thermals")

    if thermal_force_loss == 0.0:
        temp_bolt = _float_or_none(operating.get("temp_bolt"), "operating.temp_bolt")
        temp_parts = _float_or_none(operating.get("temp_parts"), "operating.temp_parts")
        l_K = _float_or_none(clamped.get("total_thickness"), "clamped.total_thickness")

        if (
            temp_bolt is not None
            and temp_parts is not None
            and l_K is not None
        ):
            try:
                delta_T = temp_bolt - temp_parts
                if delta_T != 0.0 and l_K > 0.0:
                    if layer_thermals:
                        if alpha_bolt is None:
                            raise InputError("operating.alpha_bolt 缺失，无法自动估算多层热损失。")
                        # 多层热位移：逐层求和
                        parsed_layer_thermals = []
                        for idx, lt in enumerate(layer_thermals):
                            if not isinstance(lt, dict):
                                raise InputError(
                                    f"operating.layer_thermals[{idx}] 必须为对象。"
                                )
                            layer_alpha = _float_or_none(
                                lt.get("alpha"),
                                f"operating.layer_thermals[{idx}].alpha",
                            )
                            layer_thickness = _float_or_none(
                                lt.get("l_K"),
                                f"operating.layer_thermals[{idx}].l_K",
                            )
                            if layer_alpha is None:
                                raise InputError(
                                    f"operating.layer_thermals[{idx}].alpha 缺失，无法自动估算热损失。"
                                )
                            if layer_thickness is None:
                                raise InputError(
                                    f"operating.layer_thermals[{idx}].l_K 缺失，无法自动估算热损失。"
                                )
                            parsed_layer_thermals.append(
                                {"alpha": layer_alpha, "l_K": layer_thickness}
                            )
                        delta_l_parts = sum(
                            lt["alpha"] * lt["l_K"] * delta_T
                            for lt in parsed_layer_thermals
                        )
                        delta_l_bolt = alpha_bolt * l_K * delta_T
                        thermal_auto_value = abs(delta_l_parts - delta_l_bolt) / (delta_s + delta_p)
                    else:
                        if alpha_bolt is None or alpha_parts is None:
                            missing_name = (
                                "operating.alpha_bolt"
                                if alpha_bolt is None
                                else "operating.alpha_parts"
                            )
                            raise InputError(
                                f"{missing_name} 缺失，无法自动估算热损失。"
                            )
                        # 单层热损失：保持原公式
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
            except InputError:
                raise
            except ZeroDivisionError:
                # 参数不全或异常时静默跳过，保留 thermal_force_loss = 0
                pass

    # ------------------------------------------------------------------
    # 嵌入损失自动估算 (VDI 2230 §5.4.2)
    # ------------------------------------------------------------------
    part_count_value = to_float(clamped.get("part_count", 1), "clamped.part_count")
    if not part_count_value.is_integer() or part_count_value <= 0:
        raise InputError(f"clamped.part_count 必须为正整数，当前值 {part_count_value}")
    part_count = int(part_count_value)
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
            _require(loads, "FM_min_input", "loads"),
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
    # R5 扭转残余：扭矩法保留约 50% 装配扭矩，其余方法扭矩基本释放
    k_tau = 0.5 if tightening_method == "torque" else 0.0
    sigma_vm_work = math.sqrt(sigma_ax_work**2 + 3.0 * (k_tau * tau_assembly)**2)
    yield_safety_operating = _positive(
        checks.get("yield_safety_operating", 1.1),
        "checks.yield_safety_operating",
    )
    if yield_safety_operating < 1.0:
        raise InputError(
            f"checks.yield_safety_operating 必须 >= 1，当前值 {yield_safety_operating}"
        )
    sigma_allow_work = rp02 / yield_safety_operating
    pass_work = sigma_vm_work <= sigma_allow_work

    if calculation_mode == "verify":
        f_k_residual = fm_min - embed_loss - thermal_effective - (1.0 - phi_n) * fa_max
        pass_residual = f_k_residual >= f_k_required
    else:
        f_k_residual = f_k_required  # 设计模式下恒等
        pass_residual = True

    thermal_loss_ratio = 0.0 if fm_min <= 0 else thermal_effective / fm_min
    pass_thermal = thermal_loss_ratio <= 0.25

    surface_treatment = str(options.get("surface_treatment", "rolled"))
    sigma_a = phi_n * fa_max / (2.0 * geometry["As"])
    sigma_m = (fm_max + 0.5 * phi_n * fa_max) / geometry["As"]
    # Fatigue knee at 2e6 cycles with a conservative 0.08 finite-life exponent;
    # this is the module's simplified engineering curve, not a full FKN spectrum.
    cycle_factor = (2_000_000.0 / load_cycles) ** 0.08 if load_cycles < 2_000_000.0 else 1.0
    sigma_asv = _fatigue_limit_asv(d, surface_treatment) * cycle_factor
    # Ref: 2026-07-02 review CALC-1；不对 Goodman 因子设人为下限。
    goodman_factor_raw = 1.0 - sigma_m / (0.9 * rp02)
    goodman_factor = goodman_factor_raw if goodman_factor_raw > 0.0 else 0.0
    sigma_a_allow = sigma_asv * goodman_factor
    pass_fatigue = (goodman_factor > 0.0) and (sigma_a <= sigma_a_allow)

    # 附加载荷能力参考估算（非 VDI 2230 正式校核项）：
    # 基于 10% 屈服强度裕量估算允许附加轴向载荷上限，供参考。
    # VDI 2230 对轴向外载的正式控制通过 FMmin 设计（R1）和应力校核（R4/R5）完成。
    if phi_n <= 0:
        f_a_perm = math.inf
        pass_additional = False
    else:
        f_a_perm = 0.1 * rp02 * geometry["As"] / phi_n
        pass_additional = fa_max <= f_a_perm

    # --- R8 螺纹脱扣校核 ---
    # VDI 2230: 比较螺栓最大拉力与内/外螺纹的剪切承载力。
    # 外螺纹（螺栓侧）剪切面积 A_SB = π × d3 × m_eff × C1
    # 内螺纹（螺母/壳体侧）剪切面积 A_SM = π × d × m_eff × C3
    # C1 ≈ 0.75 (ISO 公制标准螺纹的螺纹啮合修正系数)
    # C3 ≈ 0.58 (内螺纹参与承载的有效比例)
    # 安全系数 S_strip = min(F_strip_B, F_strip_M) / F_bolt_max
    thread_strip = data.get("thread_strip", {})
    m_eff = _float_or_none(thread_strip.get("m_eff"), "thread_strip.m_eff")
    tau_BM = _float_or_none(thread_strip.get("tau_BM"), "thread_strip.tau_BM")
    if m_eff is not None and m_eff <= 0:
        raise InputError("thread_strip.m_eff 必须 > 0；若不做脱扣校核，请留空该字段。")
    r8_active = m_eff is not None and m_eff > 0
    r8_note = ""
    strip_result: Dict[str, Any] = {}

    if r8_active:
        _positive(m_eff, "thread_strip.m_eff")
        # 螺栓侧（外螺纹）剪切强度：默认取 Rp0.2 × 0.6
        tau_BS = _positive(thread_strip.get("tau_BS", rp02 * 0.6), "thread_strip.tau_BS")
        # 内螺纹侧剪切强度（螺母/壳体材料）
        if tau_BM is None or tau_BM <= 0:
            raise InputError(
                "thread_strip.tau_BM（内螺纹材料剪切强度）必须 > 0。"
                "钢螺母一般可取 Rp0.2×0.6；铝壳体约 150~200 MPa。"
            )
        _positive(tau_BM, "thread_strip.tau_BM")

        C1 = _positive(thread_strip.get("C1", 0.75), "thread_strip.C1")
        C3 = _positive(thread_strip.get("C3", 0.58), "thread_strip.C3")

        # 外螺纹（螺栓侧）剪切面积和承载力
        A_SB = math.pi * geometry["d3"] * m_eff * C1
        F_strip_bolt = A_SB * tau_BS

        # 内螺纹（螺母/壳体侧）剪切面积和承载力
        A_SM = math.pi * d * m_eff * C3
        F_strip_nut = A_SM * tau_BM

        # 螺栓最大拉力
        F_bolt_max = f_bolt_work_max

        # 哪一侧先脱扣
        if F_strip_bolt <= F_strip_nut:
            critical_side = "bolt"
            F_strip_min = F_strip_bolt
        else:
            critical_side = "nut"
            F_strip_min = F_strip_nut

        strip_safety = F_strip_min / F_bolt_max if F_bolt_max > 0 else math.inf
        strip_safety_required = _positive(
            thread_strip.get("safety_required", 1.25),
            "thread_strip.safety_required",
        )
        pass_strip = strip_safety >= strip_safety_required

        side_cn = "螺栓侧（外螺纹）" if critical_side == "bolt" else "螺母/壳体侧（内螺纹）"
        r8_note = f"脱扣临界侧：{side_cn}"

        strip_result = {
            "m_eff_mm": m_eff,
            "A_SB_mm2": A_SB,
            "A_SM_mm2": A_SM,
            "tau_BS_MPa": tau_BS,
            "tau_BM_MPa": tau_BM,
            "F_strip_bolt_N": F_strip_bolt,
            "F_strip_nut_N": F_strip_nut,
            "F_bolt_max_N": F_bolt_max,
            "critical_side": critical_side,
            "strip_safety": strip_safety,
            "strip_safety_required": strip_safety_required,
            "C1": C1,
            "C3": C3,
        }

    # --- R7 支承面压强校核 ---
    p_g_allow_raw = bearing.get("p_G_allow")
    p_g_allow = 0.0
    if p_g_allow_raw not in (None, ""):
        p_g_allow = to_float(p_g_allow_raw, "bearing.p_G_allow")
        if p_g_allow < 0:
            raise InputError("bearing.p_G_allow 不能 < 0；若不做 R7 校核，请留空或填 0。")
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
    alpha_range = _ALPHA_A_RANGES.get(tightening_method)
    if alpha_range is not None:
        lo, hi = alpha_range
        if alpha_a < lo or alpha_a > hi:
            _method_names = {"torque": "扭矩法", "angle": "转角法",
                             "hydraulic": "液压拉伸法", "thermal": "热装法"}
            method_cn = _method_names.get(tightening_method, tightening_method)
            warnings.append(
                f"αA = {alpha_a:.2f} 超出{method_cn}建议范围 [{lo}–{hi}]，"
                "请确认装配工艺能力。"
            )
    if check_level == "fatigue":
        if goodman_factor_raw <= 0.0:
            warnings.append(
                "平均应力已超出 Goodman 折减范围（σ_m >= 0.9·Rp0.2），"
                "疲劳许用幅为 0，疲劳不通过。"
            )
        elif goodman_factor_raw < 0.1:
            warnings.append(
                f"Goodman 因子偏低（{goodman_factor_raw:.3f} < 0.1），"
                "疲劳裕度极小，建议降低平均应力或增大规格。"
            )

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
    if r8_active:
        checks_out["thread_strip_ok"] = pass_strip

    # ---- 总体三态判定（spec 2026-07-02 D3；对齐 tapped_axial_joint 契约）----
    # check_level 主动关闭 thermal/fatigue 不计 incomplete；R7/R8 因缺输入
    # 被动跳过必须显式标记，禁止伪绿灯。
    not_checked: list[str] = []
    if not r7_active:
        not_checked.append("R7 支承面压强")
    if not r8_active:
        not_checked.append("R8 螺纹脱扣")

    any_active_fail = any(value is False for value in checks_out.values())
    if any_active_fail:
        overall_status = "fail"
    elif not_checked:
        overall_status = "incomplete"
    else:
        overall_status = "pass"

    if overall_status == "incomplete":
        warnings.append(
            "以下校核项因缺少输入未执行：" + "、".join(not_checked)
            + "。总体结论标记为'不完整'；请补充输入后重新校核。"
        )

    stresses_out = {
        "sigma_ax_assembly": sigma_ax_assembly,
        "tau_assembly": tau_assembly,
        "sigma_vm_assembly": sigma_vm_assembly,
        "sigma_allow_assembly": sigma_allow_assembly,
        "sigma_ax_work": sigma_ax_work,
        "sigma_vm_work": sigma_vm_work,
        "k_tau": k_tau,
        "sigma_allow_work": sigma_allow_work,
    }
    if r7_active:
        stresses_out["p_bearing"] = p_bearing
        stresses_out["p_G_allow"] = p_g_allow
        stresses_out["A_bearing_mm2"] = a_bearing

    return {
        "inputs_echo": data,
        "derived_geometry_mm": geometry,
        "stiffness_model": {"delta_s_mm_per_n": delta_s, "delta_p_mm_per_n": delta_p, "n": n, "auto_modeled": auto_modeled},
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
        "tightening_method": tightening_method,
        "r3_note": r3_note,
        "r7_note": r7_note,
        "r8_note": r8_note,
        "thread_strip": strip_result,
        "thermal": {
            "thermal_loss_effective_N": thermal_effective,
            "thermal_loss_ratio": thermal_loss_ratio,
            "thermal_loss_ratio_limit": 0.25,
            "thermal_auto_estimated": thermal_auto_estimated,
            "thermal_auto_value_N": thermal_auto_value,
            "alpha_bolt": alpha_bolt,
            "alpha_parts": alpha_parts,
            **({"layer_thermals": layer_thermals} if layer_thermals else {}),
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
            "sigma_ASV": sigma_asv,
            "load_cycles": load_cycles,
            "cycle_factor": cycle_factor,
            "goodman_factor": goodman_factor,
            "goodman_factor_raw": goodman_factor_raw,
            "surface_treatment": surface_treatment,
        },
        "overall_pass": overall_status == "pass",
        "overall_status": overall_status,
        "not_checked": not_checked,
        "warnings": warnings,
        "scope_note": (
            f"连接形式：{'通孔螺栓连接' if joint_type == 'through' else '螺纹孔连接'}。"
            "本工具覆盖 VDI 2230 核心链路（装配强度、服役强度、残余夹紧力），"
            "并提供温度与疲劳的工程化扩展校核。"
        ),
    }
