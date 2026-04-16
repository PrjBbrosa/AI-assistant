"""Core calculator for tapped axial threaded joints."""

from __future__ import annotations

import math
from typing import Any

from .calculator import InputError

_ALPHA_A_RANGES: dict[str, tuple[float, float]] = {
    "torque": (1.4, 1.8),
    "angle": (1.1, 1.3),
    "hydraulic": (1.05, 1.15),
    "thermal": (1.05, 1.15),
}

# Ref: VDI 2230-1:2015, Table A4 — 轧制螺纹疲劳极限 σ_ASV (MPa)
# (公称直径 d [mm], σ_ASV [MPa])
_ASV_TABLE_ROLLED: list[tuple[float, float]] = [
    (6, 50),
    (8, 47),
    (10, 44),
    (12, 41),
    (14, 39),
    (16, 38),
    (20, 36),
    (24, 34),
    (30, 32),
    (36, 30),
]
# 切削螺纹折减系数: 0.65 (VDI 2230-1:2015, Table A4 注)
_CUT_THREAD_FACTOR = 0.65
_METHOD_NAMES = {
    "torque": "扭矩法",
    "angle": "转角法",
    "hydraulic": "液压拉伸法",
    "thermal": "热装法",
}


def _require(section: dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        raise InputError(f"Missing required field: {section_name}.{key}")
    return section[key]


def _to_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise InputError(f"{name} 必须为有限数字，当前值: {value}")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise InputError(f"{name} 必须为数字，当前值: {value}") from exc
    if not math.isfinite(parsed):
        raise InputError(f"{name} 必须为有限数字，当前值: {value}")
    return parsed


def _positive(value: Any, name: str, allow_zero: bool = False) -> float:
    parsed = _to_float(value, name)
    if allow_zero and parsed == 0:
        return parsed
    if parsed <= 0:
        raise InputError(f"{name} 必须大于 0，当前值: {parsed}")
    return parsed


def _float_or_none(value: Any, name: str) -> float | None:
    if value in (None, ""):
        return None
    return _to_float(value, name)


_THREAD_SECTION_TOLERANCE = 0.01  # 1% relative; protects against stale As/d2/d3


def _derive_thread_section(d: float, p: float) -> dict[str, float]:
    """Pure formula: ISO metric thread section from nominal d and pitch p.

    References:
        DIN 13-1 (ISO 724): ISO metric thread dimensions.
        ISO 898-1:2013, Sec 9.1.6: stress cross-section formula.
    """
    return {
        "As": math.pi / 4.0 * (d - 0.9382 * p) ** 2,
        "d2": d - 0.64952 * p,
        "d3": d - 1.22687 * p,
    }


def _derive_thread_geometry(fastener: dict[str, Any]) -> dict[str, float]:
    """Derive ISO metric thread geometry from nominal d and pitch p.

    Always uses formula values for As/d2/d3. If the caller provides any of
    those fields, they are checked for consistency with d/p (relative
    tolerance 1%). Inconsistency raises InputError, preventing the
    "new spec + stale section" silent miscalculation flagged by Codex
    adversarial review 2026-04-16 §3.2.
    """
    d = _positive(_require(fastener, "d", "fastener"), "fastener.d")
    p = _positive(_require(fastener, "p", "fastener"), "fastener.p")
    derived = _derive_thread_section(d, p)

    for key in ("As", "d2", "d3"):
        raw = fastener.get(key)
        if raw in (None, ""):
            continue
        user_value = _to_float(raw, f"fastener.{key}")
        derived_value = derived[key]
        if derived_value <= 0:
            raise InputError(
                f"fastener.{key} 由 d={d}, p={p} 派生的值 {derived_value} 非正，"
                "请复核 d 与 p。"
            )
        rel_dev = abs(user_value - derived_value) / derived_value
        if rel_dev > _THREAD_SECTION_TOLERANCE:
            raise InputError(
                f"fastener.{key}={user_value} 与由 d={d}, p={p} 派生的 "
                f"{derived_value:.4f} 不一致（相对偏差 {rel_dev * 100:.1f}% > "
                f"{_THREAD_SECTION_TOLERANCE * 100:.0f}%）；请清空该字段让系统"
                "自动计算，或修正 d/p 与截面数据的对应关系。"
            )

    return {
        "d": d,
        "p": p,
        "As": _positive(derived["As"], "fastener.As"),
        "d2": _positive(derived["d2"], "fastener.d2"),
        "d3": _positive(derived["d3"], "fastener.d3"),
    }


def _fatigue_limit_asv(d: float, surface_treatment: str) -> float:
    if surface_treatment not in {"rolled", "cut"}:
        raise InputError(
            f"fatigue.surface_treatment 无效：{surface_treatment}，应为 rolled 或 cut"
        )
    table = _ASV_TABLE_ROLLED
    if d <= table[0][0]:
        asv = table[0][1]
    elif d >= table[-1][0]:
        asv = table[-1][1]
    else:
        asv = table[-1][1]
        for index in range(len(table) - 1):
            d0, v0 = table[index]
            d1, v1 = table[index + 1]
            if d0 <= d <= d1:
                asv = v0 + (v1 - v0) * (d - d0) / (d1 - d0)
                break
    if surface_treatment == "cut":
        asv *= _CUT_THREAD_FACTOR
    return asv


def calculate_tapped_axial_joint(data: dict[str, Any]) -> dict[str, Any]:
    """Calculate a tapped axial threaded joint with no clamped parts."""
    fastener = data.get("fastener", {})
    assembly = data.get("assembly", {})
    service = data.get("service", {})
    fatigue = data.get("fatigue", {})
    thread_strip = data.get("thread_strip", {})
    checks = data.get("checks", {})

    geometry = _derive_thread_geometry(fastener)
    d = geometry["d"]
    p = geometry["p"]
    as_val = geometry["As"]
    d2 = geometry["d2"]
    d3 = geometry["d3"]
    rp02 = _positive(_require(fastener, "Rp02", "fastener"), "fastener.Rp02")

    f_preload_min = _positive(
        _require(assembly, "F_preload_min", "assembly"),
        "assembly.F_preload_min",
    )
    alpha_a = _positive(_require(assembly, "alpha_A", "assembly"), "assembly.alpha_A")
    if alpha_a < 1.0:
        raise InputError(f"assembly.alpha_A 必须 >= 1（当前值 {alpha_a}）。")

    mu_thread = _positive(_require(assembly, "mu_thread", "assembly"), "assembly.mu_thread")
    mu_bearing = _positive(
        _require(assembly, "mu_bearing", "assembly"),
        "assembly.mu_bearing",
    )
    if mu_thread > 1.0:
        raise InputError(f"assembly.mu_thread 超出合理范围（{mu_thread} > 1）。")
    if mu_bearing > 1.0:
        raise InputError(f"assembly.mu_bearing 超出合理范围（{mu_bearing} > 1）。")

    bearing_d_inner = _positive(
        _require(assembly, "bearing_d_inner", "assembly"),
        "assembly.bearing_d_inner",
    )
    bearing_d_outer = _positive(
        _require(assembly, "bearing_d_outer", "assembly"),
        "assembly.bearing_d_outer",
    )
    if bearing_d_outer <= bearing_d_inner:
        raise InputError(
            "assembly.bearing_d_outer 必须大于 assembly.bearing_d_inner"
        )

    prevailing_torque = _float_or_none(assembly.get("prevailing_torque", 0.0), "assembly.prevailing_torque")
    prevailing_torque = 0.0 if prevailing_torque is None else prevailing_torque
    flank_angle_deg = _positive(
        assembly.get("thread_flank_angle_deg", 60.0),
        "assembly.thread_flank_angle_deg",
    )
    tightening_method = str(assembly.get("tightening_method", "torque"))
    if tightening_method not in _ALPHA_A_RANGES:
        raise InputError(
            "assembly.tightening_method 无效："
            f"{tightening_method}，应为 torque、angle、hydraulic 或 thermal"
        )
    utilization = _positive(assembly.get("utilization", 0.9), "assembly.utilization")
    if utilization > 1.0:
        raise InputError(f"assembly.utilization 不能超过 1（当前值 {utilization}）。")

    fa_min = _positive(_require(service, "FA_min", "service"), "service.FA_min", allow_zero=True)
    fa_max = _positive(_require(service, "FA_max", "service"), "service.FA_max", allow_zero=True)
    if fa_min > fa_max:
        raise InputError(
            f"service.FA_min 必须 <= service.FA_max（当前值 {fa_min} > {fa_max}）。"
        )

    load_cycles = _positive(_require(fatigue, "load_cycles", "fatigue"), "fatigue.load_cycles")
    surface_treatment = str(fatigue.get("surface_treatment", "rolled"))

    yield_safety_operating = _positive(
        checks.get("yield_safety_operating", 1.1),
        "checks.yield_safety_operating",
    )
    if yield_safety_operating < 1.0:
        raise InputError(
            "checks.yield_safety_operating 必须 >= 1。"
        )

    f_preload_max = alpha_a * f_preload_min

    # Ref: VDI 2230-1:2015, Sec 5.4.2, Eq. (5.4/1)
    flank_angle = math.radians(flank_angle_deg)
    lead_angle = math.atan(p / (math.pi * d2))
    friction_angle = math.atan(mu_thread / math.cos(flank_angle / 2.0))
    k_thread = (d2 / 2.0) * math.tan(lead_angle + friction_angle)
    d_km = (bearing_d_inner + bearing_d_outer) / 2.0
    k_bearing = mu_bearing * d_km / 2.0

    def tightening_torque(preload: float) -> float:
        return preload * (k_thread + k_bearing) / 1000.0 + prevailing_torque

    ma_min = tightening_torque(f_preload_min)
    ma_max = tightening_torque(f_preload_max)

    # Ref: VDI 2230-1:2015, Sec 5.5.1, Eq. (5.5/1)
    sigma_ax_assembly = f_preload_max / as_val
    m_thread = f_preload_max * k_thread
    tau_assembly = 16.0 * m_thread / (math.pi * d3**3)
    sigma_vm_assembly = math.sqrt(sigma_ax_assembly**2 + 3.0 * tau_assembly**2)
    sigma_allow_assembly = utilization * rp02
    assembly_ok = sigma_vm_assembly <= sigma_allow_assembly

    # Ref: VDI 2230-1:2015, Sec 5.5.2
    f_service_min = f_preload_max + fa_min
    f_service_max = f_preload_max + fa_max
    sigma_ax_service_max = f_service_max / as_val
    k_tau = 0.5 if tightening_method == "torque" else 0.0  # 扭矩法保留 50% 装配扭转 (VDI 2230-1 惯例)
    sigma_vm_service_max = math.sqrt(
        sigma_ax_service_max**2 + 3.0 * (k_tau * tau_assembly) ** 2
    )
    sigma_allow_service = rp02 / yield_safety_operating
    service_ok = sigma_vm_service_max <= sigma_allow_service

    # Ref: VDI 2230-1:2015, Sec 5.5.3, Table A4
    f_mean = f_preload_max + 0.5 * (fa_min + fa_max)
    f_amplitude = 0.5 * (fa_max - fa_min)
    sigma_m = f_mean / as_val
    sigma_a = f_amplitude / as_val
    cycle_factor = (2_000_000.0 / load_cycles) ** 0.08 if load_cycles < 2_000_000.0 else 1.0
    sigma_asv = _fatigue_limit_asv(d, surface_treatment) * cycle_factor
    # Ref: Codex adversarial review 2026-04-16 §3.1 —— 不对 Goodman 因子设人为下限。
    # 原始因子 <= 0 表示 σ_m 已超过 0.9·Rp0.2，物理上疲劳不通过。
    goodman_factor_raw = 1.0 - sigma_m / (0.9 * rp02)
    goodman_factor = goodman_factor_raw if goodman_factor_raw > 0.0 else 0.0
    sigma_a_allow = sigma_asv * goodman_factor
    fatigue_ok = (goodman_factor > 0.0) and (sigma_a <= sigma_a_allow)

    m_eff = _float_or_none(thread_strip.get("m_eff"), "thread_strip.m_eff")
    tau_bm = _float_or_none(thread_strip.get("tau_BM"), "thread_strip.tau_BM")
    tau_bs_raw = thread_strip.get("tau_BS", rp02 * 0.6)
    c1_input = thread_strip.get("C1", 0.75)
    c3_input = thread_strip.get("C3", 0.58)
    c1 = 0.75 if c1_input in (None, "") else _to_float(c1_input, "thread_strip.C1")
    c3 = 0.58 if c3_input in (None, "") else _to_float(c3_input, "thread_strip.C3")
    strip_active = m_eff is not None
    strip_ok = True
    strip_result = {
        "active": False,
        "check_passed": True,
        "A_SB_mm2": 0.0,
        "A_SM_mm2": 0.0,
        "tau_BS_MPa": 0.0,
        "tau_BM_MPa": 0.0,
        "F_strip_bolt_N": 0.0,
        "F_strip_nut_N": 0.0,
        "F_bolt_max_N": 0.0,
        "critical_side": "",
        "strip_safety": 0.0,
        "strip_safety_required": 0.0,
        "note": "未提供 m_eff，未执行螺纹脱扣校核。",
    }
    if strip_active:
        # Ref: VDI 2230-1:2015, Sec 5.5.5; ISO 898-1:2013, Sec 9.2
        m_eff = _positive(m_eff, "thread_strip.m_eff")
        tau_bs = _positive(tau_bs_raw, "thread_strip.tau_BS")
        if tau_bm is None or tau_bm <= 0:
            raise InputError("thread_strip.tau_BM（内螺纹材料剪切强度）必须 > 0。")
        tau_bm = _positive(tau_bm, "thread_strip.tau_BM")
        strip_safety_required = _positive(
            thread_strip.get("safety_required", 1.25),
            "thread_strip.safety_required",
        )

        a_sb = math.pi * d3 * m_eff * c1
        a_sm = math.pi * d * m_eff * c3
        f_strip_bolt = a_sb * tau_bs
        f_strip_nut = a_sm * tau_bm
        f_bolt_max = f_preload_max + fa_max
        critical_side = "bolt" if f_strip_bolt <= f_strip_nut else "counterpart"
        f_strip_min = min(f_strip_bolt, f_strip_nut)
        strip_safety = f_strip_min / f_bolt_max if f_bolt_max > 0 else math.inf
        strip_ok = strip_safety >= strip_safety_required
        note = (
            "脱扣临界侧：螺栓侧（外螺纹）"
            if critical_side == "bolt"
            else "脱扣临界侧：壳体侧（内螺纹）"
        )
        strip_result = {
            "active": True,
            "check_passed": strip_ok,
            "A_SB_mm2": a_sb,
            "A_SM_mm2": a_sm,
            "tau_BS_MPa": tau_bs,
            "tau_BM_MPa": tau_bm,
            "F_strip_bolt_N": f_strip_bolt,
            "F_strip_nut_N": f_strip_nut,
            "F_bolt_max_N": f_bolt_max,
            "critical_side": critical_side,
            "strip_safety": strip_safety,
            "strip_safety_required": strip_safety_required,
            "note": note,
        }

    warnings: list[str] = []
    lo, hi = _ALPHA_A_RANGES[tightening_method]
    if alpha_a < lo or alpha_a > hi:
        warnings.append(
            f"alpha_A = {alpha_a:.2f} 超出{_METHOD_NAMES[tightening_method]}建议范围 [{lo}, {hi}]。"
        )
    if tightening_method != "torque":
        warnings.append(
            "当前非扭矩工艺的装配强度采用等效扭矩近似；服役残余扭转按 0 处理。"
        )
    if utilization > 0.95:
        warnings.append("装配利用系数偏高，建议复核摩擦散差与装配工艺能力。")
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

    recommendations: list[str] = []
    if not assembly_ok:
        recommendations.append("装配强度不通过：可降低预紧力、改用低扭转残余装配方式、提高强度等级或增大规格。")
    if not service_ok:
        recommendations.append("服役最大强度不通过：可增大规格、降低外载或提高螺栓强度等级。")
    if not fatigue_ok:
        recommendations.append("疲劳不通过：可降低应力幅和平均应力、改善螺纹表面质量或增大规格。")
    if strip_active and not strip_ok:
        if strip_result["critical_side"] == "bolt":
            recommendations.append("脱扣由螺栓侧控制：可提高螺栓强度或增大有效啮合长度。")
        else:
            recommendations.append("脱扣由壳体侧控制：可提高对手件材料强度或增大有效啮合长度。")

    checks_out = {
        "assembly_von_mises_ok": assembly_ok,
        "service_von_mises_ok": service_ok,
        "fatigue_ok": fatigue_ok,
        "thread_strip_ok": strip_ok,
    }
    overall_pass = all(checks_out.values())

    return {
        "overall_pass": overall_pass,
        "model_type": "tapped_axial_threaded_joint",
        "scope_note": (
            "仅适用于螺栓拧入螺纹对手件、中间无被夹件、纯轴向拉载荷工况。"
            "本模型不是 VDI 2230 夹紧连接主链，不输出残余夹紧力语义。"
        ),
        "derived_geometry": {
            "As_mm2": as_val,
            "d2_mm": d2,
            "d3_mm": d3,
        },
        "assembly": {
            "F_preload_min_N": f_preload_min,
            "F_preload_max_N": f_preload_max,
            "MA_min_Nm": ma_min,
            "MA_max_Nm": ma_max,
            "k_thread_mm": k_thread,
            "k_bearing_mm": k_bearing,
            "tightening_method": tightening_method,
        },
        "forces": {
            "F_service_min_N": f_service_min,
            "F_service_max_N": f_service_max,
            "F_mean_N": f_mean,
            "F_amplitude_N": f_amplitude,
        },
        "stresses_mpa": {
            "sigma_ax_assembly": sigma_ax_assembly,
            "tau_assembly": tau_assembly,
            "sigma_vm_assembly": sigma_vm_assembly,
            "sigma_ax_service_max": sigma_ax_service_max,
            "sigma_vm_service_max": sigma_vm_service_max,
            "sigma_m_fatigue": sigma_m,
            "sigma_a_fatigue": sigma_a,
        },
        "fatigue": {
            "sigma_ASV": sigma_asv,
            "goodman_factor": goodman_factor,
            "goodman_factor_raw": goodman_factor_raw,
            "sigma_a_allow": sigma_a_allow,
            "load_cycles": load_cycles,
            "surface_treatment": surface_treatment,
        },
        "thread_strip": strip_result,
        "checks": checks_out,
        "trace": {
            "assumptions": [
                "仅适用于无被夹件、纯轴向拉载荷工况。",
                "外轴力全部进入螺栓主链，不建模 phi_n 或残余夹紧力。",
                (
                    "非扭矩工艺下，装配强度采用等效扭矩近似；"
                    "服役残余扭转按 0 处理。"
                    if tightening_method != "torque"
                    else "扭矩法工况保留 50% 装配扭转载荷进入服役 von Mises 校核。"
                ),
            ],
            "intermediate": {
                "lead_angle_rad": lead_angle,
                "friction_angle_rad": friction_angle,
                "cycle_factor": cycle_factor,
                "C1": c1,
                "C3": c3,
                "sigma_allow_assembly": sigma_allow_assembly,
                "sigma_allow_service": sigma_allow_service,
            },
        },
        "warnings": warnings,
        "recommendations": recommendations,
        "references": {
            "geometry": "DIN 13-1 (ISO 724); ISO 898-1:2013, Sec 9.1.6",
            "assembly_strength": "VDI 2230-1:2015, Sec 5.5.1, Eq. (5.5/1)",
            "service_strength": "VDI 2230-1:2015, Sec 5.5.2",
            "fatigue": "VDI 2230-1:2015, Sec 5.5.3, Table A4 (sigma_ASV + Goodman)",
            "thread_strip": "VDI 2230-1:2015, Sec 5.5.5; ISO 898-1:2013, Sec 9.2",
        },
    }
