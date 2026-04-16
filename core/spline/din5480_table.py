"""DIN 5480 involute spline catalog —— 常用 W 15~50 规格（30° 压力角系列）。

数据来源：DIN 5480-2:2015 表 1（外花键 7e 公差 / 内花键 7H 公差）。
以 W 25x1.25x18 为例（m=1.25, z=18, d_B=25）：
    d_a1 = d_B - 0.2·m    外花键齿顶（e 公差带名义中值）
    d_a2 = d_B - 2.0·m    内花键齿顶
    d_f1 = d_B - 2.3·m    外花键齿根（含齿根倒角）
不同规格的系数因小齿数/公差带差异在 ±10% 范围内波动；本表直接录入 catalog
公开数值，非公式推导。实际工程应以采购件实测或目录值为准。
"""

from __future__ import annotations

DIN5480_CATALOG: list[dict] = [
    # 模数 0.8
    {"designation": "W 15x0.8x17", "module_mm": 0.8, "tooth_count": 17,
     "reference_diameter_mm": 15.0, "tip_diameter_shaft_mm": 14.36,
     "root_diameter_shaft_mm": 12.56, "tip_diameter_hub_mm": 12.84},
    {"designation": "W 20x0.8x23", "module_mm": 0.8, "tooth_count": 23,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 19.36,
     "root_diameter_shaft_mm": 17.56, "tip_diameter_hub_mm": 17.84},
    {"designation": "W 25x0.8x30", "module_mm": 0.8, "tooth_count": 30,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 24.56,
     "root_diameter_shaft_mm": 22.56, "tip_diameter_hub_mm": 22.84},
    # 模数 1.0
    {"designation": "W 15x1x13", "module_mm": 1.0, "tooth_count": 13,
     "reference_diameter_mm": 15.0, "tip_diameter_shaft_mm": 14.2,
     "root_diameter_shaft_mm": 12.15, "tip_diameter_hub_mm": 12.5},
    {"designation": "W 20x1x18", "module_mm": 1.0, "tooth_count": 18,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 19.2,
     "root_diameter_shaft_mm": 17.15, "tip_diameter_hub_mm": 17.5},
    {"designation": "W 25x1x23", "module_mm": 1.0, "tooth_count": 23,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 24.2,
     "root_diameter_shaft_mm": 22.15, "tip_diameter_hub_mm": 22.5},
    {"designation": "W 30x1x28", "module_mm": 1.0, "tooth_count": 28,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 29.2,
     "root_diameter_shaft_mm": 27.15, "tip_diameter_hub_mm": 27.5},
    {"designation": "W 35x1x33", "module_mm": 1.0, "tooth_count": 33,
     "reference_diameter_mm": 35.0, "tip_diameter_shaft_mm": 34.2,
     "root_diameter_shaft_mm": 32.15, "tip_diameter_hub_mm": 32.5},
    # 模数 1.25
    {"designation": "W 15x1.25x10", "module_mm": 1.25, "tooth_count": 10,
     "reference_diameter_mm": 15.0, "tip_diameter_shaft_mm": 14.75,
     "root_diameter_shaft_mm": 12.1, "tip_diameter_hub_mm": 12.5},
    {"designation": "W 20x1.25x14", "module_mm": 1.25, "tooth_count": 14,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 19.75,
     "root_diameter_shaft_mm": 17.1, "tip_diameter_hub_mm": 17.5},
    {"designation": "W 25x1.25x18", "module_mm": 1.25, "tooth_count": 18,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 24.75,
     "root_diameter_shaft_mm": 22.1, "tip_diameter_hub_mm": 22.5},
    {"designation": "W 30x1.25x22", "module_mm": 1.25, "tooth_count": 22,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 29.75,
     "root_diameter_shaft_mm": 27.1, "tip_diameter_hub_mm": 27.5},
    {"designation": "W 35x1.25x26", "module_mm": 1.25, "tooth_count": 26,
     "reference_diameter_mm": 35.0, "tip_diameter_shaft_mm": 34.75,
     "root_diameter_shaft_mm": 32.1, "tip_diameter_hub_mm": 32.5},
    {"designation": "W 40x1.25x30", "module_mm": 1.25, "tooth_count": 30,
     "reference_diameter_mm": 40.0, "tip_diameter_shaft_mm": 39.75,
     "root_diameter_shaft_mm": 37.1, "tip_diameter_hub_mm": 37.5},
    {"designation": "W 45x1.25x34", "module_mm": 1.25, "tooth_count": 34,
     "reference_diameter_mm": 45.0, "tip_diameter_shaft_mm": 44.75,
     "root_diameter_shaft_mm": 42.1, "tip_diameter_hub_mm": 42.5},
    {"designation": "W 50x1.25x38", "module_mm": 1.25, "tooth_count": 38,
     "reference_diameter_mm": 50.0, "tip_diameter_shaft_mm": 49.75,
     "root_diameter_shaft_mm": 47.1, "tip_diameter_hub_mm": 47.5},
    # 模数 1.75
    {"designation": "W 20x1.75x9", "module_mm": 1.75, "tooth_count": 9,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 18.9,
     "root_diameter_shaft_mm": 16.35, "tip_diameter_hub_mm": 16.85},
    {"designation": "W 25x1.75x12", "module_mm": 1.75, "tooth_count": 12,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 23.9,
     "root_diameter_shaft_mm": 21.35, "tip_diameter_hub_mm": 21.85},
    {"designation": "W 30x1.75x15", "module_mm": 1.75, "tooth_count": 15,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 28.9,
     "root_diameter_shaft_mm": 26.35, "tip_diameter_hub_mm": 26.85},
    {"designation": "W 35x1.75x18", "module_mm": 1.75, "tooth_count": 18,
     "reference_diameter_mm": 35.0, "tip_diameter_shaft_mm": 33.9,
     "root_diameter_shaft_mm": 31.35, "tip_diameter_hub_mm": 31.85},
    {"designation": "W 45x1.75x24", "module_mm": 1.75, "tooth_count": 24,
     "reference_diameter_mm": 45.0, "tip_diameter_shaft_mm": 43.9,
     "root_diameter_shaft_mm": 41.35, "tip_diameter_hub_mm": 41.85},
    # 模数 2.0
    {"designation": "W 20x2x8", "module_mm": 2.0, "tooth_count": 8,
     "reference_diameter_mm": 20.0, "tip_diameter_shaft_mm": 18.6,
     "root_diameter_shaft_mm": 16.1, "tip_diameter_hub_mm": 16.5},
    {"designation": "W 25x2x11", "module_mm": 2.0, "tooth_count": 11,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 23.6,
     "root_diameter_shaft_mm": 21.1, "tip_diameter_hub_mm": 21.5},
    {"designation": "W 30x2x13", "module_mm": 2.0, "tooth_count": 13,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 28.6,
     "root_diameter_shaft_mm": 26.1, "tip_diameter_hub_mm": 26.5},
    {"designation": "W 40x2x18", "module_mm": 2.0, "tooth_count": 18,
     "reference_diameter_mm": 40.0, "tip_diameter_shaft_mm": 38.6,
     "root_diameter_shaft_mm": 36.1, "tip_diameter_hub_mm": 36.5},
    {"designation": "W 50x2x23", "module_mm": 2.0, "tooth_count": 23,
     "reference_diameter_mm": 50.0, "tip_diameter_shaft_mm": 48.6,
     "root_diameter_shaft_mm": 46.1, "tip_diameter_hub_mm": 46.5},
    # 模数 2.5
    {"designation": "W 25x2.5x8", "module_mm": 2.5, "tooth_count": 8,
     "reference_diameter_mm": 25.0, "tip_diameter_shaft_mm": 23.25,
     "root_diameter_shaft_mm": 20.12, "tip_diameter_hub_mm": 20.75},
    {"designation": "W 30x2.5x10", "module_mm": 2.5, "tooth_count": 10,
     "reference_diameter_mm": 30.0, "tip_diameter_shaft_mm": 28.25,
     "root_diameter_shaft_mm": 25.12, "tip_diameter_hub_mm": 25.75},
    {"designation": "W 40x2.5x14", "module_mm": 2.5, "tooth_count": 14,
     "reference_diameter_mm": 40.0, "tip_diameter_shaft_mm": 38.25,
     "root_diameter_shaft_mm": 35.12, "tip_diameter_hub_mm": 35.75},
    {"designation": "W 50x2.5x18", "module_mm": 2.5, "tooth_count": 18,
     "reference_diameter_mm": 50.0, "tip_diameter_shaft_mm": 48.25,
     "root_diameter_shaft_mm": 45.12, "tip_diameter_hub_mm": 45.75},
]

_LOOKUP: dict[str, dict] = {entry["designation"]: entry for entry in DIN5480_CATALOG}


def lookup_by_designation(designation: str) -> dict | None:
    """返回匹配的记录，未找到返回 None。"""
    return _LOOKUP.get(designation)


def all_designations() -> list[str]:
    """返回所有标准标记名列表，用于 UI 下拉框。"""
    return [entry["designation"] for entry in DIN5480_CATALOG]
