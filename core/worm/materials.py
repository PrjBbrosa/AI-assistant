"""塑料蜗轮材料库（塑-钢副）与降额模型。

数据来源：DIN 3996:2019、PA66 / POM / PA46 / PEEK 厂商 PDS、ISO 14521、
         DuPont Zytel 技术手册、Celanese Acetal 技术手册。

仅覆盖钢蜗杆 + 塑料蜗轮配对，不支持钢-青铜副或钢-钢副。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class PlasticMaterial:
    """塑料蜗轮材料参数（常温干态基准值）。

    Fields
    ------
    name : str
        材料牌号（与 PLASTIC_MATERIALS 键对应）
    e_mpa : float
        弹性模量 [MPa]（常温干态）
    nu : float
        泊松比（常温干态）
    sigma_hlim_mpa : float
        接触疲劳极限许用应力 [MPa]（常温干态，N=10^7 周期基准）
    sigma_flim_mpa : float
        弯曲疲劳极限许用应力 [MPa]（常温干态，N=10^7 周期基准）
    allowable_surface_temp_c : float
        最高允许齿面温度 [℃]（超过此值材料性能急剧下降）
    temp_derate_per_10c : float
        每超过基准温度（23℃）10℃ 的强度降额系数（乘法因子，< 1.0）
    humidity_derate_at_50rh : float
        50%RH 相对于干态（0%RH）的强度降额系数（PA 系列因吸水降额，
        POM/PEEK 对湿度不敏感，数值接近 1.0）
    """
    name: str
    e_mpa: float
    nu: float
    sigma_hlim_mpa: float
    sigma_flim_mpa: float
    allowable_surface_temp_c: float
    temp_derate_per_10c: float
    humidity_derate_at_50rh: float


# 材料库数据说明：
#   - PA66：干态 E=3.0 GPa，σ_Hlim=42 MPa（DIN 3996 附录 A 塑料轮参考值）
#   - PA66+GF30：30% 玻纤增强，E=10 GPa，σ_Hlim=58 MPa（DuPont Zytel 70G30 PDS）
#   - POM：聚甲醛，E=2.8 GPa，σ_Hlim=48 MPa（Celanese Hostaform PDS + ISO 14521）
#   - PA46：高温 PA 品种，耐热性优于 PA66，σ_Hlim=52 MPa（DSM Stanyl PA46 PDS）
#   - PEEK：高性能工程塑料，E=3.6 GPa，σ_Hlim=90 MPa（Victrex PEEK 450G PDS）
#
#   temp_derate_per_10c：每升高 10℃ 的乘法衰减因子，即
#       temp_factor = temp_derate_per_10c ^ ((T - 23) / 10)
#   humidity_derate_at_50rh：PA 系列吸水后强度下降约 20~30%；POM/PEEK 对湿度不敏感

PLASTIC_MATERIALS: Dict[str, PlasticMaterial] = {
    "PA66": PlasticMaterial(
        name="PA66",
        e_mpa=3000.0,
        nu=0.38,
        sigma_hlim_mpa=42.0,
        sigma_flim_mpa=55.0,
        allowable_surface_temp_c=100.0,
        temp_derate_per_10c=0.92,
        humidity_derate_at_50rh=0.70,
    ),
    "PA66+GF30": PlasticMaterial(
        name="PA66+GF30",
        e_mpa=10000.0,
        nu=0.36,
        sigma_hlim_mpa=58.0,
        sigma_flim_mpa=70.0,
        allowable_surface_temp_c=110.0,
        temp_derate_per_10c=0.90,
        humidity_derate_at_50rh=0.78,
    ),
    "POM": PlasticMaterial(
        name="POM",
        e_mpa=2800.0,
        nu=0.37,
        sigma_hlim_mpa=48.0,
        sigma_flim_mpa=62.0,
        allowable_surface_temp_c=95.0,
        temp_derate_per_10c=0.93,
        humidity_derate_at_50rh=0.98,
    ),
    "PA46": PlasticMaterial(
        name="PA46",
        e_mpa=3300.0,
        nu=0.38,
        sigma_hlim_mpa=52.0,
        sigma_flim_mpa=68.0,
        allowable_surface_temp_c=125.0,
        temp_derate_per_10c=0.90,
        humidity_derate_at_50rh=0.72,
    ),
    "PEEK": PlasticMaterial(
        name="PEEK",
        e_mpa=3600.0,
        nu=0.40,
        sigma_hlim_mpa=90.0,
        sigma_flim_mpa=140.0,
        allowable_surface_temp_c=180.0,
        temp_derate_per_10c=0.92,
        humidity_derate_at_50rh=0.99,
    ),
}


def apply_derate(
    material: PlasticMaterial,
    *,
    operating_temp_c: float = 23.0,
    humidity_rh: float = 0.0,
) -> Tuple[float, float]:
    """计算温度和湿度降额后的许用应力。

    Parameters
    ----------
    material : PlasticMaterial
        材料对象（来自 PLASTIC_MATERIALS）
    operating_temp_c : float
        齿面工作温度 [℃]（基准温度 23℃）
    humidity_rh : float
        环境相对湿度 [%]（0 ~ 100）

    Returns
    -------
    (sigma_Hlim_derated, sigma_Flim_derated) : Tuple[float, float]
        降额后接触疲劳极限 [MPa]、弯曲疲劳极限 [MPa]

    Notes
    -----
    温度降额：幂函数模型，每升高 10℃ 乘以 temp_derate_per_10c。
        factor_T = temp_derate_per_10c ^ max(0, (T - 23) / 10)

    湿度降额：线性插值，0%RH = 1.0，50%RH = humidity_derate_at_50rh。
        factor_RH = 1.0 - (1.0 - humidity_derate_at_50rh) * clamp(RH, 0, 50) / 50

    注意：当 humidity_rh > 50% 时按 50% 钳位（保守）；PA 系列实测数据超过 50%RH
    后强度下降趋于饱和，此简化模型在 0~50% 区间的精度较高。
    """
    base_temp = 23.0

    # 温度降额（仅超过基准时有效）
    temp_factor = 1.0
    if operating_temp_c > base_temp:
        steps = (operating_temp_c - base_temp) / 10.0
        temp_factor = material.temp_derate_per_10c ** max(0.0, steps)

    # 湿度降额（线性插值，0% RH = 1.0，50% RH = humidity_derate_at_50rh）
    # clamp 到 [0, 50] 区间：超过 50% RH 的 PA 吸水近似饱和，用 50% 保守估算
    rh_clamped = max(0.0, min(float(humidity_rh), 50.0))
    humidity_factor = 1.0 - (1.0 - material.humidity_derate_at_50rh) * rh_clamped / 50.0

    sigma_hlim_derated = material.sigma_hlim_mpa * temp_factor * humidity_factor
    sigma_flim_derated = material.sigma_flim_mpa * temp_factor * humidity_factor

    return sigma_hlim_derated, sigma_flim_derated
