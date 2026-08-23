"""Shared model-level banners for result pages and reports.

MODEL-S01: each module declares 正式子集 / 简化预校核 / 快速估算 / 参考项,
plus covered and not-covered items. Text here is the single source for UI
headers, text reports, and PDF helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.hertz.calculator import OUTER_CONTACT_SCOPE_NOTE

MODEL_LEVEL_QUICK = "快速估算"
MODEL_LEVEL_PRECHECK = "简化预校核"
MODEL_LEVEL_FORMAL_SUBSET = "正式子集"
MODEL_LEVEL_REFERENCE = "参考项"

SOURCE_USER = "用户输入"
SOURCE_RECOMMENDED = "建议值"

HERTZ_ALLOWABLE_SOURCE_NOTE = (
    "来源：用户输入（材料牌号只填充 E/ν 建议值，不会自动生成权威 [p0]）"
)


@dataclass(frozen=True)
class ModuleScope:
    module_id: str
    model_level: str
    covered: tuple[str, ...]
    not_covered: tuple[str, ...]
    applicability: str


HERTZ_SCOPE = ModuleScope(
    module_id="hertz_contact",
    model_level=MODEL_LEVEL_QUICK,
    covered=(
        "外接触线接触（圆柱-圆柱 / 圆柱-平面）",
        "外接触点接触（球-球 / 球-平面）",
        "弹性赫兹最大接触应力 p0 与斑尺寸快速估算",
    ),
    not_covered=(
        "内接触 / 负曲率",
        "弹塑性、残余应力、粗糙度与润滑修正",
        "边缘效应三维修正",
        "疲劳寿命谱",
    ),
    applicability=OUTER_CONTACT_SCOPE_NOTE,
)

SPLINE_SCOPE = ModuleScope(
    module_id="spline_fit",
    model_level=MODEL_LEVEL_PRECHECK,
    covered=(
        "花键齿面平均承压简化预校核",
        "可选光滑段圆柱过盈（DIN 7190 风格防滑 / 屈服）",
    ),
    not_covered=(
        "齿根弯曲强度",
        "剪切承载",
        "内花键胀裂 / 轮毂局部强度",
        "磨损与寿命",
        "完整公差 / 变位 / 齿侧间隙链",
        "完整 DIN 5480 / DIN 6892 签发校核",
    ),
    applicability=(
        "当前结论仅为简化预校核，不能作为正式 DIN 5480 / DIN 6892 签发结果。"
    ),
)

WORM_SCOPE = ModuleScope(
    module_id="worm_gear",
    model_level=MODEL_LEVEL_FORMAL_SUBSET,
    covered=(
        "DIN 3975 几何与基础性能",
        "DIN 3996 Method B 风格最小负载能力子集（齿面接触 / 齿根弯曲）",
        "塑料蜗轮温度 / 湿度降额（建议值）",
        f"寿命与磨损估算（{MODEL_LEVEL_REFERENCE}）",
    ),
    not_covered=(
        "完整 DIN 3996 / ISO/TS 14521",
        "Method C（需 FEA，当前拒绝计算）",
        "完整实验 / FEM Method A 链",
        "包角与完整接触线模型",
    ),
    applicability=(
        "负载能力（Load Capacity）为 Method B 风格最小工程子集，"
        "不是完整标准签发校核。寿命 / 磨损为参考项。"
    ),
)

INTERFERENCE_SCOPE = ModuleScope(
    module_id="interference_fit",
    model_level=MODEL_LEVEL_FORMAL_SUBSET,
    covered=(
        "DIN 7190 风格圆柱面过盈配合（实心轴 / 空心轴）",
        "防滑（扭矩 / 轴向 / 联合作用）与张口缝",
        "轴 / 轮毂应力（取内孔壁与配合面较大者）",
        "装配（热装 / 压装）",
        f"Fretting 风险定性评估（{MODEL_LEVEL_REFERENCE}）",
    ),
    not_covered=(
        "服役温度 / 热膨胀工作过盈",
        "转速",
        "离心力",
        "阶梯轴 / 阶梯轮毂几何",
        "完整 DIN 7190 签发校核",
    ),
    applicability=(
        "当前结论为 DIN 7190 风格核心校核，不是完整标准签发结果。"
        "线弹性、均匀接触压力、恒定摩擦；弯矩附加压强按 QW=0 保守简化。"
    ),
)

TAPPED_SCOPE = ModuleScope(
    module_id="bolt_tapped_axial",
    model_level=MODEL_LEVEL_FORMAL_SUBSET,
    covered=(
        "无被夹件内螺纹连接的纯轴向拉载荷校核",
        "装配 / 服役 von Mises 强度",
        "交变轴向疲劳（Goodman 折减，无人为下限）",
        "可选螺纹脱扣（需提供有效啮合长度 m_eff）",
    ),
    not_covered=(
        "横向力 / 剪切",
        "弯矩 / 偏心载荷",
        "多螺栓并联",
        "压向载荷",
        "VDI 2230 夹紧连接主链（残余夹紧力 / Φ_N）",
        "完整螺纹脱扣与完整疲劳谱（FKN 法）",
    ),
    applicability=(
        "仅适用于螺栓拧入螺纹对手件、中间无被夹件、纯轴向拉载荷。"
        "螺纹脱扣未提供 m_eff 时该项为未校核，总体结论为校核不完整，不会给出虚假通过。"
        "本模型是正式子集风格的工程校核，不是完整 VDI 2230 夹紧连接签发结果。"
    ),
)

BUFFER_SCOPE = ModuleScope(
    module_id="buffer_energy",
    model_level=MODEL_LEVEL_QUICK,
    covered=(
        "准静态 F-x 曲线的单次冲击能量法",
        "行程 / 峰值力 / 曲线能量容量快速估算",
        "回弹速度与时域响应反推估算",
    ),
    not_covered=(
        "应变率效应",
        "真实时域动力学仿真",
        "粘性阻尼识别",
        "完整缓冲器 / 阻尼器认证试验",
        "垂直跌落重力做功自动计入",
    ),
    applicability=(
        "当前结论仅为快速估算，不能替代完整缓冲器认证或真实时域仿真。"
        "触底后峰值力不可判定，整体按不通过处理。"
    ),
)

MODULE_SCOPES: dict[str, ModuleScope] = {
    HERTZ_SCOPE.module_id: HERTZ_SCOPE,
    SPLINE_SCOPE.module_id: SPLINE_SCOPE,
    WORM_SCOPE.module_id: WORM_SCOPE,
    INTERFERENCE_SCOPE.module_id: INTERFERENCE_SCOPE,
    TAPPED_SCOPE.module_id: TAPPED_SCOPE,
    BUFFER_SCOPE.module_id: BUFFER_SCOPE,
}


def format_scope_banner_text(scope: ModuleScope) -> str:
    covered = "；".join(scope.covered)
    not_covered = "；".join(scope.not_covered)
    return (
        f"模型等级：{scope.model_level}\n"
        f"覆盖工况：{covered}\n"
        f"未覆盖：{not_covered}\n"
        f"适用范围：{scope.applicability}"
    )


def scope_report_lines(scope: ModuleScope) -> list[str]:
    lines = [
        f"模型等级: {scope.model_level}",
        "覆盖工况:",
        *[f"- {item}" for item in scope.covered],
        "未覆盖:",
        *[f"- {item}" for item in scope.not_covered],
        f"适用范围: {scope.applicability}",
    ]
    return lines


def scope_kv_rows(scope: ModuleScope) -> list[tuple[str, str]]:
    return [
        ("模型等级", scope.model_level),
        ("覆盖工况", "；".join(scope.covered)),
        ("未覆盖", "；".join(scope.not_covered)),
        ("适用范围", scope.applicability),
    ]


def format_source_label(kind: str, detail: str = "") -> str:
    if detail:
        return f"来源：{kind}（{detail}）"
    return f"来源：{kind}"


def make_scope_banner(parent, scope: ModuleScope):
    """Create a word-wrapped result-header banner. Imports Qt lazily."""
    from PySide6.QtWidgets import QLabel

    label = QLabel(format_scope_banner_text(scope), parent)
    label.setObjectName("ModelScopeBanner")
    label.setWordWrap(True)
    return label
