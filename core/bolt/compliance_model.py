"""VDI 2230 螺栓/被夹件弹性柔度计算模型。"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from core.bolt.calculator import InputError, _positive


def calculate_bolt_compliance(
    d: float, p: float, l_K: float, E_bolt: float,
) -> Dict[str, float]:
    """计算螺栓弹性柔度 δs (mm/N)。

    简化模型：δs = l_eff / (E × As)
    l_eff = l_K + 0.4·d（考虑螺栓头和螺纹过渡段的等效长度）
    """
    _positive(d, "d")
    _positive(p, "p")
    _positive(l_K, "l_K")
    _positive(E_bolt, "E_bolt")
    As = math.pi / 4.0 * (d - 0.9382 * p) ** 2
    l_eff = l_K + 0.4 * d
    delta_s = l_eff / (E_bolt * As)
    return {"delta_s": delta_s, "As": As, "l_eff": l_eff}


def calculate_clamped_compliance(
    model: str | None = None,
    d_h: float = 0, D_A: float = 0, D_w: float = 0,
    D_outer: float = 0, D_inner: float = 0,
    l_K: float = 0, E_clamped: float = 0,
    layers: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """计算被夹件弹性柔度 δp (mm/N)。

    支持三种模型：
    - cylinder: 圆柱体 δp = l_K / (E × π/4 × (D_A² - d_h²))
    - cone: VDI 2230 锥台（Lori-Engel 近似锥角）
    - sleeve: 套筒 δp = l_K / (E × π/4 × (D_outer² - D_inner²))
    - 多层: layers 参数，各层 δp 串联求和
    """
    if layers is not None:
        total_delta = 0.0
        for layer in layers:
            r = calculate_clamped_compliance(**layer)
            total_delta += r["delta_p"]
        return {"delta_p": total_delta, "model": "multi_layer", "n_layers": len(layers)}

    if model is None:
        raise InputError("必须指定 model 或 layers")

    if model == "cylinder":
        _positive(d_h, "d_h")
        _positive(D_A, "D_A")
        _positive(l_K, "l_K")
        _positive(E_clamped, "E_clamped")
        A_p = math.pi / 4.0 * (D_A**2 - d_h**2)
        delta_p = l_K / (E_clamped * A_p)
        return {"delta_p": delta_p, "model": "cylinder", "A_p": A_p}

    if model == "cone":
        _positive(d_h, "d_h")
        _positive(D_w, "D_w")
        _positive(D_A, "D_A")
        _positive(l_K, "l_K")
        _positive(E_clamped, "E_clamped")
        # Lori-Engel 近似锥角
        r_DA = max(D_A / 2.0 / l_K, 0.01)
        r_lK = max(l_K / D_w, 0.01)
        phi_rad = math.atan(0.362 + 0.032 * math.log(r_DA) + 0.153 * math.log(r_lK))
        tan_phi = math.tan(phi_rad)
        if tan_phi <= 0:
            tan_phi = 0.3  # 安全下限
        numer = (D_w + d_h) * (D_A - d_h)
        denom = (D_w - d_h) * (D_A + d_h)
        if denom <= 0 or numer <= 0:
            raise InputError("锥台模型几何参数不合理: D_w > d_h 且 D_A > d_h 必须满足")
        delta_p = 2.0 * math.log(numer / denom) / (E_clamped * math.pi * d_h * tan_phi)
        return {
            "delta_p": delta_p, "model": "cone",
            "cone_angle_deg": math.degrees(phi_rad),
        }

    if model == "sleeve":
        _positive(D_outer, "D_outer")
        _positive(D_inner, "D_inner")
        _positive(l_K, "l_K")
        _positive(E_clamped, "E_clamped")
        A_p = math.pi / 4.0 * (D_outer**2 - D_inner**2)
        delta_p = l_K / (E_clamped * A_p)
        return {"delta_p": delta_p, "model": "sleeve", "A_p": A_p}

    raise InputError(f"未知的被夹件模型: {model}")
