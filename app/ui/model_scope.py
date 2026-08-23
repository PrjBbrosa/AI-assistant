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

MODULE_SCOPES: dict[str, ModuleScope] = {
    HERTZ_SCOPE.module_id: HERTZ_SCOPE,
    SPLINE_SCOPE.module_id: SPLINE_SCOPE,
    WORM_SCOPE.module_id: WORM_SCOPE,
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
