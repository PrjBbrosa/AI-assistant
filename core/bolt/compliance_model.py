"""VDI 2230 螺栓/被夹件弹性柔度计算模型。"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Dict, List

from core._validation import positive_float
from core.bolt._common import InputError


def _positive(value: Any, name: str, allow_zero: bool = False) -> float:
    return positive_float(value, name, allow_zero=allow_zero, error_cls=InputError)


def _require_positive_finite(value: Any, name: str) -> float:
    numeric = _positive(value, name)
    if not math.isfinite(numeric):
        raise InputError(f"{name} 必须为有限数字，当前值: {value}")
    return numeric


def calculate_bolt_compliance(
    d: float, p: float, l_K: float, E_bolt: float, joint_type: str = "tapped",
) -> Dict[str, float]:
    """计算螺栓弹性柔度 δs (mm/N)。

    简化模型：δs = l_eff / (E × As)
    l_eff = l_K + l_add
    - 通孔连接：l_add ≈ 0.8·d（螺栓头/过渡段 + 螺母侧附加变形）
    - 螺纹孔连接：l_add ≈ 0.73·d（螺栓头/过渡段 + 螺纹啮合区等效长度）
    """
    d = _positive(d, "d")
    p = _positive(p, "p")
    l_K = _positive(l_K, "l_K")
    E_bolt = _positive(E_bolt, "E_bolt")
    if joint_type not in {"tapped", "through"}:
        raise InputError(f"未知的连接形式: {joint_type}")
    As = math.pi / 4.0 * (d - 0.9382 * p) ** 2
    if As <= 0 or not math.isfinite(As):
        raise InputError(f"螺栓应力截面积 As 必须 > 0，当前值 {As}")
    head_transition = 0.4 * d
    joint_extension = 0.4 * d if joint_type == "through" else 0.33 * d
    l_eff = l_K + head_transition + joint_extension
    delta_s = l_eff / (E_bolt * As)
    delta_s = _require_positive_finite(delta_s, "delta_s")
    return {
        "delta_s": delta_s,
        "As": As,
        "l_eff": l_eff,
        "joint_extension_mm": joint_extension,
        "joint_type": joint_type,
    }


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
        if not isinstance(layers, list):
            raise InputError("被夹件 layers 必须是列表")
        if not (1 <= len(layers) <= 10):
            raise InputError("被夹件层数须在 1~10 之间")
        total_delta = 0.0
        for idx, layer in enumerate(layers):
            if not isinstance(layer, Mapping) or isinstance(layer, (str, bytes, bytearray)):
                raise InputError(f"clamped.layers[{idx}] 必须是字典")
            r = calculate_clamped_compliance(**layer)
            total_delta += _require_positive_finite(r["delta_p"], f"layers[{idx}].delta_p")
        total_delta = _require_positive_finite(total_delta, "delta_p")
        return {"delta_p": total_delta, "model": "multi_layer", "n_layers": len(layers)}

    if model is None:
        raise InputError("必须指定 model 或 layers")

    if model == "cylinder":
        d_h = _positive(d_h, "d_h")
        D_A = _positive(D_A, "D_A")
        l_K = _positive(l_K, "l_K")
        E_clamped = _positive(E_clamped, "E_clamped")
        if not (D_A > d_h > 0):
            raise InputError(f"圆柱模型必须满足 D_A > d_h > 0，当前 D_A={D_A}, d_h={d_h}")
        A_p = math.pi / 4.0 * (D_A**2 - d_h**2)
        A_p = _require_positive_finite(A_p, "A_p")
        delta_p = l_K / (E_clamped * A_p)
        delta_p = _require_positive_finite(delta_p, "delta_p")
        return {"delta_p": delta_p, "model": "cylinder", "A_p": A_p}

    if model == "cone":
        d_h = _positive(d_h, "d_h")
        D_w = _positive(D_w, "D_w")
        D_A = _positive(D_A, "D_A")
        l_K = _positive(l_K, "l_K")
        E_clamped = _positive(E_clamped, "E_clamped")
        if not (D_w > d_h):
            raise InputError(f"锥台模型必须满足 D_w > d_h，当前 D_w={D_w}, d_h={d_h}")
        if not (D_A > d_h):
            raise InputError(f"锥台模型必须满足 D_A > d_h，当前 D_A={D_A}, d_h={d_h}")
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
        delta_p = _require_positive_finite(delta_p, "delta_p")
        return {
            "delta_p": delta_p, "model": "cone",
            "cone_angle_deg": math.degrees(phi_rad),
        }

    if model == "sleeve":
        D_outer = _positive(D_outer, "D_outer")
        D_inner = _positive(D_inner, "D_inner")
        l_K = _positive(l_K, "l_K")
        E_clamped = _positive(E_clamped, "E_clamped")
        if not (D_outer > D_inner > 0):
            raise InputError(
                f"套筒模型必须满足 D_outer > D_inner > 0，当前 D_outer={D_outer}, D_inner={D_inner}"
            )
        A_p = math.pi / 4.0 * (D_outer**2 - D_inner**2)
        A_p = _require_positive_finite(A_p, "A_p")
        delta_p = l_K / (E_clamped * A_p)
        delta_p = _require_positive_finite(delta_p, "delta_p")
        return {"delta_p": delta_p, "model": "sleeve", "A_p": A_p}

    raise InputError(f"未知的被夹件模型: {model}")
