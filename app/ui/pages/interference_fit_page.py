"""Interference-fit module page with chapter-style workflow."""

from __future__ import annotations

import datetime as dt
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.input_condition_store import (
    build_form_snapshot,
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    read_input_conditions,
    write_input_conditions,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import export_report_lines
from app.ui.widgets.press_force_curve import PressForceCurveWidget
from core.interference.calculator import InputError, calculate_interference_fit
from core.interference.fit_selection import (
    PREFERRED_FIT_OPTIONS,
    derive_interference_from_deviations,
    derive_interference_from_preferred_fit,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)

MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "45钢": {"e_mpa": 210000.0, "nu": 0.30},
    "40Cr": {"e_mpa": 210000.0, "nu": 0.29},
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29},
    "QT500-7": {"e_mpa": 170000.0, "nu": 0.28},
    "灰铸铁 HT250": {"e_mpa": 120000.0, "nu": 0.26},
    "铝合金 6061-T6": {"e_mpa": 69000.0, "nu": 0.33},
    "压铸铝 AlSi9Cu3": {"e_mpa": 71000.0, "nu": 0.33},
    "自定义": None,
}
MATERIAL_OPTIONS: tuple[str, ...] = tuple(MATERIAL_LIBRARY.keys())

MATERIAL_CATEGORY: dict[str, str] = {
    "45钢": "steel",
    "40Cr": "steel",
    "42CrMo": "steel",
    "QT500-7": "cast_iron",
    "灰铸铁 HT250": "cast_iron",
    "铝合金 6061-T6": "aluminum",
    "压铸铝 AlSi9Cu3": "alsi9cu3",
}

SURFACE_CONDITIONS: tuple[str, ...] = ("干摩擦", "轻油润滑", "自定义")

FRICTION_TABLE: dict[tuple[frozenset[str], str], dict[str, float]] = {
    # 钢-钢 (DIN 7190-1 参考)
    (frozenset({"steel", "steel"}), "干摩擦"): {"mu_torque": 0.15, "mu_axial": 0.12, "mu_assembly": 0.12},
    (frozenset({"steel", "steel"}), "轻油润滑"): {"mu_torque": 0.11, "mu_axial": 0.08, "mu_assembly": 0.08},
    # 钢-铸铁 (DIN 7190-1 参考)
    (frozenset({"steel", "cast_iron"}), "干摩擦"): {"mu_torque": 0.12, "mu_axial": 0.10, "mu_assembly": 0.10},
    (frozenset({"steel", "cast_iron"}), "轻油润滑"): {"mu_torque": 0.09, "mu_axial": 0.07, "mu_assembly": 0.07},
    # 钢-铝 (DIN 7190-1 参考)
    (frozenset({"steel", "aluminum"}), "干摩擦"): {"mu_torque": 0.12, "mu_axial": 0.10, "mu_assembly": 0.10},
    (frozenset({"steel", "aluminum"}), "轻油润滑"): {"mu_torque": 0.08, "mu_axial": 0.06, "mu_assembly": 0.06},
    # 钢-压铸铝 AlSi9Cu3 (经验值)
    (frozenset({"steel", "alsi9cu3"}), "干摩擦"): {"mu_torque": 0.15, "mu_axial": 0.15, "mu_assembly": 0.15},
    (frozenset({"steel", "alsi9cu3"}), "轻油润滑"): {"mu_torque": 0.125, "mu_axial": 0.125, "mu_assembly": 0.125},
    # 铸铁-铸铁 (DIN 7190-1 参考)
    (frozenset({"cast_iron", "cast_iron"}), "干摩擦"): {"mu_torque": 0.12, "mu_axial": 0.10, "mu_assembly": 0.10},
    (frozenset({"cast_iron", "cast_iron"}), "轻油润滑"): {"mu_torque": 0.08, "mu_axial": 0.06, "mu_assembly": 0.06},
    # 铸铁-铝 (DIN 7190-1 参考)
    (frozenset({"cast_iron", "aluminum"}), "干摩擦"): {"mu_torque": 0.10, "mu_axial": 0.08, "mu_assembly": 0.08},
    (frozenset({"cast_iron", "aluminum"}), "轻油润滑"): {"mu_torque": 0.07, "mu_axial": 0.05, "mu_assembly": 0.05},
    # 铝-铝 (DIN 7190-1 参考)
    (frozenset({"aluminum", "aluminum"}), "干摩擦"): {"mu_torque": 0.10, "mu_axial": 0.08, "mu_assembly": 0.08},
    (frozenset({"aluminum", "aluminum"}), "轻油润滑"): {"mu_torque": 0.07, "mu_axial": 0.05, "mu_assembly": 0.05},
    # 压铸铝 AlSi9Cu3 自配对 (经验值)
    (frozenset({"alsi9cu3", "alsi9cu3"}), "干摩擦"): {"mu_torque": 0.20, "mu_axial": 0.20, "mu_assembly": 0.20},
    (frozenset({"alsi9cu3", "alsi9cu3"}), "轻油润滑"): {"mu_torque": 0.175, "mu_axial": 0.175, "mu_assembly": 0.175},
}

CATEGORY_DISPLAY: dict[str, str] = {
    "steel": "钢",
    "cast_iron": "铸铁",
    "aluminum": "铝",
    "alsi9cu3": "压铸铝 AlSi9Cu3",
}

_FRICTION_MU_FIELDS: tuple[str, ...] = (
    "friction.mu_torque",
    "friction.mu_axial",
    "friction.mu_assembly",
)

ROUGHNESS_PROFILE_FACTORS: dict[str, float | None] = {
    "DIN 7190-1:2017（k=0.4）": 0.4,
    "DIN 7190:2001（k=0.8）": 0.8,
    "自定义k": None,
}
ROUGHNESS_PROFILE_OPTIONS: tuple[str, ...] = tuple(ROUGHNESS_PROFILE_FACTORS.keys())
ROUGHNESS_BATCH_WARNING_TITLE = "批量生产提示：粗糙度会放大压入散差"
ROUGHNESS_BATCH_WARNING_TEXT = (
    "批量生产中，压入力突然偏大或偏小，很多时候并不只是公差波动，"
    "而是配合面机加工状态变化导致有效过盈与装配摩擦同时变化。\n\n"
    "可优先从以下方向排查：\n"
    "1. 看 Rz 与压平量是否波动：粗糙峰压平会改变有效过盈，直接影响接触压力与压入力。\n"
    "2. 不要只看 Ra：波纹度、圆柱度、刀纹方向和局部毛刺，往往比单一粗糙度数字更影响压入散差。\n"
    "3. 区分是过盈变了还是摩擦变了：若压入力与脱出力一起变化，多半先看有效过盈；若只压入力异常，优先排查润滑、清洁度和表面擦伤。\n"
    "4. 批量管控优先项：统一机加工参数、Rz 检测口径、润滑方式、压装速度、倒角去毛刺和清洁度。"
)


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    label: str
    unit: str
    hint: str
    mapping: tuple[str, str] | None = None
    widget_type: str = "number"
    options: tuple[str, ...] = ()
    default: str = ""
    placeholder: str = ""


CHAPTERS: list[dict[str, Any]] = [
    {
        "title": "校核目标",
        "subtitle": "定义最小安全系数与工况系数 KA，按设计载荷执行校核。",
        "fields": [
            FieldSpec(
                "checks.slip_safety_min",
                "防滑最小安全系数 S_slip,min",
                "-",
                "对扭矩与轴向载荷校核使用的最小安全系数门槛。",
                mapping=("checks", "slip_safety_min"),
                default="1.20",
                placeholder="建议 1.1~1.5",
            ),
            FieldSpec(
                "checks.stress_safety_min",
                "材料最小安全系数 S_sigma,min",
                "-",
                "对轴与轮毂应力校核使用的最小安全系数门槛。",
                mapping=("checks", "stress_safety_min"),
                default="1.20",
                placeholder="建议 1.1~1.8",
            ),
            FieldSpec(
                "loads.application_factor_ka",
                "工况系数 KA",
                "-",
                "按 DIN 3990 取值，用于把名义载荷放大到设计载荷。",
                mapping=("loads", "application_factor_ka"),
                default="1.20",
                placeholder="建议 1.0~2.25",
            ),
            FieldSpec(
                "options.curve_points",
                "压入力曲线采样点数",
                "点",
                "曲线图离散点数量；越大越平滑，计算耗时略增，仅影响曲线显示。",
                mapping=("options", "curve_points"),
                default="41",
                placeholder="11~201",
            ),
        ],
    },
    {
        "title": "几何与过盈",
        "subtitle": "圆柱面过盈（实心轴/空心轴 + 厚壁轮毂）几何输入。",
        "fields": [
            FieldSpec(
                "geometry.shaft_d_mm",
                "配合直径 d",
                "mm",
                "轴与轮毂名义配合直径。",
                mapping=("geometry", "shaft_d_mm"),
                default="40.0",
                placeholder="例如 40",
            ),
            FieldSpec(
                "geometry.shaft_inner_d_mm",
                "轴内径 d_i",
                "mm",
                "0 表示实心轴；非零时按空心轴修正轴侧柔度与应力。",
                mapping=("geometry", "shaft_inner_d_mm"),
                default="0.0",
                placeholder="实心轴填 0，例如 20",
            ),
            FieldSpec(
                "geometry.hub_outer_d_mm",
                "轮毂外径 D",
                "mm",
                "轮毂外圆直径，必须大于 d。",
                mapping=("geometry", "hub_outer_d_mm"),
                default="80.0",
                placeholder="例如 80",
            ),
            FieldSpec(
                "geometry.fit_length_mm",
                "配合长度 L",
                "mm",
                "轴向有效接触长度。",
                mapping=("geometry", "fit_length_mm"),
                default="45.0",
                placeholder="例如 45",
            ),
            FieldSpec(
                "fit.mode",
                "过盈来源模式",
                "-",
                "可直接输入过盈窗口，或通过优选配合/轴孔偏差自动换算。",
                widget_type="choice",
                options=("直接输入过盈量", "优选配合", "偏差换算"),
                default="直接输入过盈量",
            ),
            FieldSpec(
                "fit.preferred_fit_name",
                "优选配合代号",
                "-",
                "优选配合模式下使用；当前仅内置常见孔基制干涉配合的有限预设。",
                widget_type="choice",
                options=PREFERRED_FIT_OPTIONS,
                default="H7/s6",
            ),
            FieldSpec(
                "fit.shaft_upper_deviation_um",
                "轴上偏差 es",
                "um",
                "偏差换算模式下使用；以名义尺寸为基准，正值表示大于名义尺寸。",
                default="",
                placeholder="例如 35",
            ),
            FieldSpec(
                "fit.shaft_lower_deviation_um",
                "轴下偏差 ei",
                "um",
                "偏差换算模式下使用；必须 <= 轴上偏差。",
                default="",
                placeholder="例如 20",
            ),
            FieldSpec(
                "fit.hub_upper_deviation_um",
                "孔上偏差 ES",
                "um",
                "偏差换算模式下使用；负值表示孔尺寸小于名义尺寸。",
                default="",
                placeholder="例如 -10",
            ),
            FieldSpec(
                "fit.hub_lower_deviation_um",
                "孔下偏差 EI",
                "um",
                "偏差换算模式下使用；必须 <= 孔上偏差。",
                default="",
                placeholder="例如 -20",
            ),
            FieldSpec(
                "fit.delta_min_um",
                "最小过盈量 delta_min",
                "um",
                "制造与装配偏差下可保证的最小过盈量（直径值）。",
                mapping=("fit", "delta_min_um"),
                default="20.0",
                placeholder="例如 20",
            ),
            FieldSpec(
                "fit.delta_max_um",
                "最大过盈量 delta_max",
                "um",
                "制造与装配偏差下可出现的最大过盈量（直径值）。",
                mapping=("fit", "delta_max_um"),
                default="45.0",
                placeholder="例如 45",
            ),
        ],
    },
    {
        "title": "材料参数",
        "subtitle": "材料弹性与屈服参数（用于压力-应力转换与安全系数）。",
        "fields": [
            FieldSpec(
                "materials.shaft_material",
                "轴材料",
                "-",
                "选择后自动填充轴侧 E 与 nu；可切到“自定义”手工输入。",
                widget_type="choice",
                options=MATERIAL_OPTIONS,
                default="45钢",
            ),
            FieldSpec(
                "materials.shaft_e_mpa",
                "轴弹性模量 E_s",
                "MPa",
                "钢材常见约 206000~210000 MPa。",
                mapping=("materials", "shaft_e_mpa"),
                default="210000",
                placeholder="例如 210000",
            ),
            FieldSpec(
                "materials.shaft_nu",
                "轴泊松比 nu_s",
                "-",
                "钢材常见约 0.28~0.30。",
                mapping=("materials", "shaft_nu"),
                default="0.30",
                placeholder="0<nu<0.5",
            ),
            FieldSpec(
                "materials.shaft_yield_mpa",
                "轴屈服强度 Re_s",
                "MPa",
                "用于轴侧应力安全系数计算。",
                mapping=("materials", "shaft_yield_mpa"),
                default="600",
                placeholder="例如 600",
            ),
            FieldSpec(
                "materials.hub_material",
                "轮毂材料",
                "-",
                "选择后自动填充轮毂侧 E 与 nu；可切到“自定义”手工输入。",
                widget_type="choice",
                options=MATERIAL_OPTIONS,
                default="45钢",
            ),
            FieldSpec(
                "materials.hub_e_mpa",
                "轮毂弹性模量 E_h",
                "MPa",
                "钢材常见约 206000~210000 MPa。",
                mapping=("materials", "hub_e_mpa"),
                default="210000",
                placeholder="例如 210000",
            ),
            FieldSpec(
                "materials.hub_nu",
                "轮毂泊松比 nu_h",
                "-",
                "钢材常见约 0.28~0.30。",
                mapping=("materials", "hub_nu"),
                default="0.30",
                placeholder="0<nu<0.5",
            ),
            FieldSpec(
                "materials.hub_yield_mpa",
                "轮毂屈服强度 Re_h",
                "MPa",
                "用于轮毂侧应力安全系数计算。",
                mapping=("materials", "hub_yield_mpa"),
                default="320",
                placeholder="例如 320",
            ),
        ],
    },
    {
        "title": "载荷与附加载荷",
        "subtitle": "输入扭矩、轴向力、径向力和弯矩，校核防滑与张口缝风险。",
        "fields": [
            FieldSpec(
                "loads.torque_required_nm",
                "需求传递扭矩 T_req",
                "N·m",
                "服役工况下的最大传递扭矩需求。",
                mapping=("loads", "torque_required_nm"),
                default="350",
                placeholder="例如 350",
            ),
            FieldSpec(
                "loads.axial_force_required_n",
                "需求轴向力 F_req",
                "N",
                "如同时要求抗轴向窜动，可填此值；无要求可填 0。",
                mapping=("loads", "axial_force_required_n"),
                default="0",
                placeholder="例如 0",
            ),
            FieldSpec(
                "loads.radial_force_required_n",
                "需求径向力 F_r,req",
                "N",
                "用于附加接触压强与张口缝校核；无要求可填 0。",
                mapping=("loads", "radial_force_required_n"),
                default="0",
                placeholder="例如 0",
            ),
            FieldSpec(
                "loads.bending_moment_required_nm",
                "需求弯矩 M_b,req",
                "N·m",
                "用于附加接触压强与张口缝校核；本轮按保守简化处理。",
                mapping=("loads", "bending_moment_required_nm"),
                default="0",
                placeholder="例如 0",
            ),
        ],
    },
    {
        "title": "摩擦与粗糙度",
        "subtitle": "分开输入服役摩擦与装配摩擦，并按 DIN 7190 粗糙度压平修正有效过盈。",
        "fields": [
            FieldSpec(
                "friction.surface_condition",
                "表面状态",
                "-",
                "配合面润滑状态，与材料配对共同决定推荐摩擦系数。",
                widget_type="choice",
                options=SURFACE_CONDITIONS,
                default="干摩擦",
            ),
            FieldSpec(
                "friction.mu_torque",
                "扭矩方向摩擦系数 mu_T",
                "-",
                "服役阶段周向摩擦系数，用于扭矩传递能力。",
                mapping=("friction", "mu_torque"),
                default="0.14",
                placeholder="建议 0.08~0.20",
            ),
            FieldSpec(
                "friction.mu_axial",
                "轴向方向摩擦系数 mu_Ax",
                "-",
                "服役阶段轴向摩擦系数，用于抗窜动能力。",
                mapping=("friction", "mu_axial"),
                default="0.14",
                placeholder="建议 0.08~0.20",
            ),
            FieldSpec(
                "friction.mu_assembly",
                "装配摩擦系数 mu_Assy",
                "-",
                "装配压入阶段摩擦系数，用于压入力估算。",
                mapping=("friction", "mu_assembly"),
                default="0.12",
                placeholder="建议 0.06~0.18",
            ),
            FieldSpec(
                "roughness.profile",
                "粗糙度压平模型",
                "-",
                "按标准版本选择压平系数 k；可切换到自定义。",
                widget_type="choice",
                options=ROUGHNESS_PROFILE_OPTIONS,
                default="DIN 7190-1:2017（k=0.4）",
            ),
            FieldSpec(
                "roughness.smoothing_factor",
                "压平系数 k",
                "-",
                "压平公式 s = k * (Rz_s + Rz_h) 中的 k。",
                mapping=("roughness", "smoothing_factor"),
                default="0.40",
                placeholder="建议 0.4 或 0.8",
            ),
            FieldSpec(
                "roughness.shaft_rz_um",
                "轴表面粗糙度 Rz_s",
                "um",
                "按 Rz 输入；常见 Ra0.8 对应 Rz 约 6.3。",
                mapping=("roughness", "shaft_rz_um"),
                default="6.3",
                placeholder="例如 6.3",
            ),
            FieldSpec(
                "roughness.hub_rz_um",
                "轮毂表面粗糙度 Rz_h",
                "um",
                "按 Rz 输入；常见 Ra0.8 对应 Rz 约 6.3。",
                mapping=("roughness", "hub_rz_um"),
                default="6.3",
                placeholder="例如 6.3",
            ),
        ],
    },
    {
        "title": "装配流程",
        "subtitle": "区分 manual_only、shrink_fit、force_fit，并追溯服役摩擦与装配摩擦的角色。",
        "fields": [
            FieldSpec(
                "assembly.method",
                "装配模式",
                "-",
                "只做通用压入力估算时选 manual_only；热装选 shrink_fit；压装选 force_fit。",
                widget_type="choice",
                options=("manual_only", "shrink_fit", "force_fit"),
                default="manual_only",
            ),
            FieldSpec(
                "assembly.clearance_mode",
                "热装配合间隙模式",
                "-",
                "shrink_fit 下可按直径经验值自动估算，或直接指定装配间隙。",
                widget_type="choice",
                options=("diameter_rule", "direct_value"),
                default="diameter_rule",
            ),
            FieldSpec(
                "assembly.room_temperature_c",
                "环境温度",
                "°C",
                "shrink_fit 下用于求解轮毂所需加热温度。",
                mapping=("assembly", "room_temperature_c"),
                default="20",
                placeholder="例如 20",
            ),
            FieldSpec(
                "assembly.shaft_temperature_c",
                "轴装配温度",
                "°C",
                "若轴已预冷，可填低于环境温度的数值。",
                mapping=("assembly", "shaft_temperature_c"),
                default="20",
                placeholder="例如 20 或 -78.4",
            ),
            FieldSpec(
                "assembly.clearance_um",
                "装配间隙",
                "um",
                "direct_value 模式下直接输入；diameter_rule 模式按 0.001*d 自动估算。",
                mapping=("assembly", "clearance_um"),
                default="0",
                placeholder="例如 25",
            ),
            FieldSpec(
                "assembly.alpha_hub_1e6_per_c",
                "轮毂线膨胀系数 alpha_h",
                "10^-6/°C",
                "用于 shrink_fit 轮毂加热量估算。",
                mapping=("assembly", "alpha_hub_1e6_per_c"),
                default="11",
                placeholder="例如 11",
            ),
            FieldSpec(
                "assembly.alpha_shaft_1e6_per_c",
                "轴线膨胀系数 alpha_s",
                "10^-6/°C",
                "用于考虑轴预冷或非钢材时的热装修正。",
                mapping=("assembly", "alpha_shaft_1e6_per_c"),
                default="11",
                placeholder="例如 11",
            ),
            FieldSpec(
                "assembly.hub_temp_limit_c",
                "轮毂允许最高装配温度",
                "°C",
                "若已知热处理限制，建议填入以判断热装温度是否越界。",
                mapping=("assembly", "hub_temp_limit_c"),
                default="250",
                placeholder="例如 250 或 300",
            ),
            FieldSpec(
                "assembly.mu_press_in",
                "压入摩擦系数 mu_in",
                "-",
                "force_fit 下用于估算 press-in 力；与服役摩擦不同。",
                mapping=("assembly", "mu_press_in"),
                default="0.08",
                placeholder="例如 0.08",
            ),
            FieldSpec(
                "assembly.mu_press_out",
                "压出摩擦系数 mu_out",
                "-",
                "force_fit 下用于估算 extraction force 与建议设备能力。",
                mapping=("assembly", "mu_press_out"),
                default="0.06",
                placeholder="例如 0.06",
            ),
        ],
    },
    {
        "title": "Fretting 风险评估",
        "subtitle": "Step 5 增强结果：评估微动腐蚀风险等级与建议，不参与基础 DIN verdict。",
        "fields": [
            FieldSpec(
                "fretting.mode",
                "Fretting 评估开关",
                "-",
                "off 时不计算；on 时在满足简化适用条件时输出风险等级与建议。",
                widget_type="choice",
                options=("off", "on"),
                default="off",
            ),
            FieldSpec(
                "fretting.load_spectrum",
                "载荷谱",
                "-",
                "按首版简化规则区分 steady、pulsating 与 reversing 对 fretting 的影响。",
                widget_type="choice",
                options=("steady", "pulsating", "reversing"),
                default="pulsating",
            ),
            FieldSpec(
                "fretting.duty_severity",
                "工况严酷度",
                "-",
                "根据设备循环频次与冲击程度选择 light、medium 或 heavy。",
                widget_type="choice",
                options=("light", "medium", "heavy"),
                default="medium",
            ),
            FieldSpec(
                "fretting.surface_condition",
                "表面状态",
                "-",
                "首版按 coated、oiled、dry 三档评估表面保护能力。",
                widget_type="choice",
                options=("coated", "oiled", "dry"),
                default="dry",
            ),
            FieldSpec(
                "fretting.importance_level",
                "部件重要度",
                "-",
                "用于在一般件、重要件、关键件之间施加不同的保守度。",
                widget_type="choice",
                options=("general", "important", "critical"),
                default="important",
            ),
        ],
    },
]

CHECK_LABELS = {
    "torque_ok": "扭矩能力校核（按最小过盈）",
    "axial_ok": "轴向力能力校核（按最小过盈）",
    "combined_ok": "联合作用校核（扭矩 + 轴向）",
    "gaping_ok": "张口缝校核（p_min >= p_r + p_b）",
    "fit_range_ok": "最大过盈端覆盖需求校核",
    "shaft_stress_ok": "轴侧应力安全系数校核",
    "hub_stress_ok": "轮毂应力安全系数校核",
}

BEGINNER_GUIDES: dict[str, str] = {
    "loads.application_factor_ka": "工况越冲击，KA 越大，需求过盈也会随之提高。",
    "options.curve_points": "仅影响曲线显示精细度，不改变任何通过/不通过结论。",
    "geometry.shaft_d_mm": "决定接触面积与接触半径，直接影响扭矩能力。",
    "geometry.shaft_inner_d_mm": "填 0 表示实心轴；内孔越大，轴越柔，通常会降低接触压力和传递能力。",
    "geometry.hub_outer_d_mm": "外径越大，轮毂柔度越低；按当前厚壁轮毂模型，同等过盈下接触压力越高。",
    "fit.mode": "如果只知道标准配合代号，优先用“优选配合”；如果已有轴/孔偏差，改用“偏差换算”。",
    "fit.preferred_fit_name": "当前只提供受限的常用孔基制优选配合，用于快速得到可追溯的过盈窗口。",
    "fit.shaft_upper_deviation_um": "偏差换算时，系统会自动把轴/孔偏差转换为 delta_min / delta_max。",
    "fit.shaft_lower_deviation_um": "若算出的最小过盈 < 0，则说明该组合包含间隙或过渡，不适用于当前模块。",
    "fit.hub_upper_deviation_um": "孔偏差通常与轴偏差符号相反，输入时请保持工程图纸的原始符号。",
    "fit.hub_lower_deviation_um": "推荐优先核对偏差上下限顺序，再观察自动换算出的过盈窗口是否合理。",
    "fit.delta_min_um": "校核安全时应优先关注最小过盈工况。",
    "fit.delta_max_um": "校核应力时应优先关注最大过盈工况。",
    "loads.radial_force_required_n": "径向力会抬高附加接触压强，过大时可能导致张口缝。",
    "loads.bending_moment_required_nm": "弯矩会让接触压力分布恶化，本轮按保守简化估算附加压强。",
    "friction.mu_torque": "与表面状态/润滑密切相关，是扭矩能力计算最敏感参数之一。",
    "friction.mu_axial": "轴向抗滑移能力可与周向能力采用不同摩擦系数。",
    "friction.mu_assembly": "主要影响装配压入力，可与服役摩擦系数不同。",
    "materials.shaft_material": "标准材料会自动带出弹性模量和泊松比，便于快速建模。",
    "materials.hub_material": "轮毂材料对压力-应力转换影响显著，建议按实际牌号选择。",
    "materials.hub_yield_mpa": "轮毂常是薄弱侧，建议优先核查其屈服强度。",
    "roughness.profile": "标准版本差异主要体现在压平系数 k：新版常用 0.4，旧版常用 0.8。",
    "roughness.smoothing_factor": "压平量 s 越大，有效过盈越小，压力与压入力都会下降。",
    "roughness.shaft_rz_um": "若只有 Ra，可先按标准对照关系近似换算至 Rz。",
    "roughness.hub_rz_um": "推荐输入制造图纸或检测报告中的 Rz 值。",
    "assembly.method": "装配模式不会改变 DIN 7190 的通过/不通过逻辑，但会改变装配工艺建议与报告追溯。",
    "assembly.clearance_mode": "diameter_rule 会按 0.001*d 自动估算装配间隙；direct_value 适合已有工艺标准时使用。",
    "assembly.room_temperature_c": "热装默认以环境温度为基准，预冷轴会降低所需轮毂加热温度。",
    "assembly.shaft_temperature_c": "若采用液氮或干冰冷装，请把轴装配温度填成冷却后的温度。",
    "assembly.clearance_um": "这不是服役过盈，而是装配瞬间为了避免咬死所预留的最小间隙。",
    "assembly.alpha_hub_1e6_per_c": "钢材常见约 11，铝合金更高；直接影响所需加热温度。",
    "assembly.alpha_shaft_1e6_per_c": "若轴和轮毂材料不同，建议不要偷懒沿用同一数值。",
    "assembly.hub_temp_limit_c": "用于检查热装温度是否超过热处理允许范围；未知时可保留默认估算值。",
    "assembly.mu_press_in": "压入摩擦通常低于干摩擦；推荐结合润滑状态单独输入。",
    "assembly.mu_press_out": "压出摩擦用于估算 extraction force，与 press-in 不一定相同。",
    "fretting.mode": "Step 5 是增强结果，不改变基础 DIN verdict；关闭后不输出 fretting 评估。",
    "fretting.load_spectrum": "循环方向越激烈，越容易出现界面微滑移与 fretting 风险。",
    "fretting.duty_severity": "可以理解为把使用频率、冲击程度和持续时间合并成一个简化严重度输入。",
    "fretting.surface_condition": "首版不做详细材料学模型，用类别化表面状态近似界面保护能力。",
    "fretting.importance_level": "部件越关键，建议越保守；它会抬高风险分级和建议强度。",
}


class InterferenceFitPage(BaseChapterPage):
    """Cylindrical interference-fit chapter page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="过盈配合 · 圆柱面校核",
            subtitle="DIN 7190 核心增强版：实心轴/空心轴 + 厚壁轮毂，覆盖防滑、张口缝与应力校核。",
            parent=parent,
        )
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._widget_hints: dict[QWidget, str] = {}
        self._check_badges: dict[str, QLabel] = {}
        self.roughness_warning_box: QFrame | None = None
        self.roughness_warning_text: QLabel | None = None
        self._ref_badges: dict[str, QLabel] = {}
        self._friction_ref_values: dict[str, float] = {}
        self._friction_source_text: str = ""
        self._material_links: dict[str, tuple[str, str]] = {
            "materials.shaft_material": ("materials.shaft_e_mpa", "materials.shaft_nu"),
            "materials.hub_material": ("materials.hub_e_mpa", "materials.hub_nu"),
        }
        self._roughness_profile_field = "roughness.profile"
        self._roughness_factor_field = "roughness.smoothing_factor"
        self._fit_mode_field = "fit.mode"
        self._fit_preferred_field = "fit.preferred_fit_name"
        self._fit_nominal_field = "geometry.shaft_d_mm"
        self._fit_delta_fields = ("fit.delta_min_um", "fit.delta_max_um")
        self._fit_deviation_fields = (
            "fit.shaft_upper_deviation_um",
            "fit.shaft_lower_deviation_um",
            "fit.hub_upper_deviation_um",
            "fit.hub_lower_deviation_um",
        )
        self._assembly_method_field = "assembly.method"
        self._assembly_clearance_mode_field = "assembly.clearance_mode"
        self._fretting_mode_field = "fretting.mode"
        self._fretting_field_ids = (
            "fretting.mode",
            "fretting.load_spectrum",
            "fretting.duty_severity",
            "fretting.surface_condition",
            "fretting.importance_level",
        )
        self._assembly_shrink_fields = (
            "assembly.room_temperature_c",
            "assembly.shaft_temperature_c",
            "assembly.clearance_um",
            "assembly.alpha_hub_1e6_per_c",
            "assembly.alpha_shaft_1e6_per_c",
            "assembly.hub_temp_limit_c",
        )
        self._assembly_force_fields = (
            "assembly.mu_press_in",
            "assembly.mu_press_out",
        )

        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行校核", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_save = self.add_action_button("导出结果说明")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")

        self._build_input_chapters()
        self._build_curve_chapter()
        self._build_results_chapter()
        self.set_current_chapter(0)

        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("interference_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("interference_case_02.json"))
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save.clicked.connect(self._save_report)

        self._register_material_bindings()
        self._register_roughness_binding()
        self._register_fit_bindings()
        self._register_assembly_bindings()
        self._register_fretting_bindings()
        self._apply_defaults()
        self._sync_friction_from_material()
        self._load_sample("interference_case_01.json")
        self._sync_material_inputs()
        self._sync_roughness_factor()
        self._sync_fit_mode_fields()
        self._sync_assembly_fields()
        self._sync_fretting_fields()

    def eventFilter(self, watched, event):  # noqa: N802
        if watched in self._widget_hints and event.type() in (QEvent.Type.FocusIn, QEvent.Type.Enter):
            self.set_info(self._widget_hints[watched])
        return super().eventFilter(watched, event)

    def _build_input_chapters(self) -> None:
        for chapter in CHAPTERS:
            page = self._create_chapter_page(chapter["title"], chapter["subtitle"], chapter["fields"])
            self.add_chapter(chapter["title"], page)

    def _create_chapter_page(self, title: str, subtitle: str, fields: list[FieldSpec]) -> QWidget:
        page = QFrame(self)
        page.setObjectName("Card")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(14, 12, 14, 12)
        page_layout.setSpacing(10)

        title_label = QLabel(title, page)
        title_label.setObjectName("SectionTitle")
        subtitle_label = QLabel(subtitle, page)
        subtitle_label.setObjectName("SectionHint")
        subtitle_label.setWordWrap(True)
        page_layout.addWidget(title_label)
        page_layout.addWidget(subtitle_label)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll)
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        for spec in fields:
            field_card = QFrame(container)
            field_card.setObjectName("SubCard")
            row = QGridLayout(field_card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setHorizontalSpacing(10)
            row.setVerticalSpacing(4)

            label = QLabel(spec.label, field_card)
            label.setObjectName("SubSectionTitle")
            editor = self._create_editor(spec, field_card)
            unit = QLabel(spec.unit, field_card)
            unit.setObjectName("UnitLabel")
            hint = QLabel(spec.hint, field_card)
            hint.setObjectName("SectionHint")
            hint.setWordWrap(True)

            row.addWidget(label, 0, 0)
            row.addWidget(editor, 0, 1)
            row.addWidget(unit, 0, 2)
            row.addWidget(hint, 1, 0, 1, 3)
            if spec.field_id in _FRICTION_MU_FIELDS:
                ref_badge = QLabel("", field_card)
                ref_badge.setObjectName("RefBadge")
                ref_badge.setVisible(False)
                row.addWidget(ref_badge, 2, 0, 1, 3)
                self._ref_badges[spec.field_id] = ref_badge
            form_layout.addWidget(field_card)
            self._field_cards[spec.field_id] = field_card

        if title == "摩擦与粗糙度":
            form_layout.addWidget(self._build_roughness_warning_card(container))

        form_layout.addStretch(1)
        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)
        return page

    def _build_roughness_warning_card(self, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("WarningCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(ROUGHNESS_BATCH_WARNING_TITLE, card)
        title.setObjectName("WarningTitle")
        title.setWordWrap(True)

        body = QLabel(ROUGHNESS_BATCH_WARNING_TEXT, card)
        body.setObjectName("WarningBody")
        body.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(body)
        self.roughness_warning_box = card
        self.roughness_warning_text = body
        return card

    def _create_editor(self, spec: FieldSpec, parent: QWidget) -> QWidget:
        if spec.widget_type == "choice":
            editor = QComboBox(parent)
            editor.addItems(spec.options)
            if spec.default:
                idx = editor.findText(spec.default)
                if idx >= 0:
                    editor.setCurrentIndex(idx)
        else:
            editor = QLineEdit(parent)
            editor.setObjectName("InputField")
            if spec.placeholder:
                editor.setPlaceholderText(spec.placeholder)
            else:
                editor.setPlaceholderText("请输入数值")
            if spec.default:
                editor.setText(spec.default)

        help_text = self._build_field_help(spec)
        editor.setToolTip(help_text)
        editor.installEventFilter(self)
        self._widget_hints[editor] = help_text
        self._field_widgets[spec.field_id] = editor
        self._field_specs[spec.field_id] = spec
        return editor

    def _build_field_help(self, spec: FieldSpec) -> str:
        unit_part = f"（单位：{spec.unit}）" if spec.unit and spec.unit != "-" else ""
        newbie = BEGINNER_GUIDES.get(spec.field_id, "建议先加载测试案例运行，再替换为实际数据。")
        return f"{spec.label}{unit_part}\n参数说明：{spec.hint}\n新手提示：{newbie}"

    def _build_curve_chapter(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title = QLabel("压入力曲线图", page)
        title.setObjectName("SectionTitle")
        hint = QLabel("横轴为过盈量 delta，纵轴为压入力 F_press；用于评估装配工艺窗口。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        self.curve_widget = PressForceCurveWidget(page)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.curve_widget, 1)
        self.add_chapter("压入力曲线图", page)

    def _build_results_chapter(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        content = QVBoxLayout(container)
        content.setContentsMargins(8, 8, 8, 8)
        content.setSpacing(8)

        title = QLabel("校核结果与消息", container)
        title.setObjectName("SectionTitle")
        hint = QLabel("按最小过盈校核承载能力，按最大过盈校核应力，并单独显示最大过盈端是否覆盖需求。", container)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        content.addWidget(title)
        content.addWidget(hint)

        summary_card = QFrame(container)
        summary_card.setObjectName("SubCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)
        self.result_title = QLabel("尚未执行计算", summary_card)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel("填写参数并点击“执行校核”后，这里显示结论。", summary_card)
        self.result_summary.setObjectName("SectionHint")
        self.result_summary.setWordWrap(True)
        summary_layout.addWidget(self.result_title)
        summary_layout.addWidget(self.result_summary)
        content.addWidget(summary_card)

        checks_card = QFrame(container)
        checks_card.setObjectName("SubCard")
        checks_layout = QGridLayout(checks_card)
        checks_layout.setContentsMargins(12, 10, 12, 10)
        checks_layout.setHorizontalSpacing(12)
        checks_layout.setVerticalSpacing(8)
        checks_layout.addWidget(QLabel("分项校核"), 0, 0)
        checks_layout.addWidget(QLabel("状态"), 0, 1)
        row = 1
        for key, text in CHECK_LABELS.items():
            name = QLabel(text, checks_card)
            status = QLabel("待计算", checks_card)
            status.setObjectName("WaitBadge")
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setMinimumWidth(64)
            status.setFixedHeight(24)
            checks_layout.addWidget(name, row, 0)
            checks_layout.addWidget(status, row, 1)
            self._check_badges[key] = status
            row += 1
        content.addWidget(checks_card)

        metrics_card = QFrame(container)
        metrics_card.setObjectName("SubCard")
        metrics_layout = QVBoxLayout(metrics_card)
        metrics_layout.setContentsMargins(12, 10, 12, 10)
        metrics_layout.setSpacing(6)
        metrics_title = QLabel("关键结果值", metrics_card)
        metrics_title.setObjectName("SubSectionTitle")
        self.metrics_text = QLabel("尚无结果。", metrics_card)
        self.metrics_text.setObjectName("SectionHint")
        self.metrics_text.setWordWrap(True)
        metrics_layout.addWidget(metrics_title)
        metrics_layout.addWidget(self.metrics_text)
        content.addWidget(metrics_card)

        msg_card = QFrame(container)
        msg_card.setObjectName("SubCard")
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setContentsMargins(12, 10, 12, 10)
        msg_layout.setSpacing(6)
        msg_title = QLabel("消息与建议", msg_card)
        msg_title.setObjectName("SubSectionTitle")
        self.message_box = QPlainTextEdit(msg_card)
        self.message_box.setReadOnly(True)
        self.message_box.setMinimumHeight(180)
        msg_layout.addWidget(msg_title)
        msg_layout.addWidget(self.message_box)
        content.addWidget(msg_card)
        content.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        self.add_chapter("校核结果与消息", page)

    def _apply_defaults(self) -> None:
        for spec in self._field_specs.values():
            widget = self._field_widgets[spec.field_id]
            if spec.widget_type == "choice":
                combo = widget  # type: ignore[assignment]
                if spec.default:
                    idx = combo.findText(spec.default)  # type: ignore[attr-defined]
                    if idx >= 0:
                        combo.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(spec.default)  # type: ignore[attr-defined]
        self._sync_material_inputs()
        self._sync_roughness_factor()
        self._sync_fit_mode_fields()
        self._sync_assembly_fields()

    def _register_material_bindings(self) -> None:
        for selector_id in self._material_links:
            selector = self._field_widgets.get(selector_id)
            if not isinstance(selector, QComboBox):
                continue
            selector.currentTextChanged.connect(
                lambda _text, sid=selector_id: self._apply_material_selection(sid)
            )

        # Friction coefficient auto-fill from material pair + surface condition
        for fid in ("materials.shaft_material", "materials.hub_material", "friction.surface_condition"):
            combo = self._field_widgets.get(fid)
            if isinstance(combo, QComboBox):
                combo.currentTextChanged.connect(lambda _t: self._sync_friction_from_material())

        # Detect manual edits to friction fields
        for fid in _FRICTION_MU_FIELDS:
            widget = self._field_widgets.get(fid)
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _t: self._check_friction_modified())

    def _sync_material_inputs(self) -> None:
        for selector_id in self._material_links:
            self._apply_material_selection(selector_id)

    def _apply_material_selection(self, selector_id: str) -> None:
        selector = self._field_widgets.get(selector_id)
        if not isinstance(selector, QComboBox):
            return
        target = self._material_links.get(selector_id)
        if target is None:
            return
        e_id, nu_id = target
        e_widget = self._field_widgets.get(e_id)
        nu_widget = self._field_widgets.get(nu_id)
        if not isinstance(e_widget, QLineEdit) or not isinstance(nu_widget, QLineEdit):
            return

        material_name = selector.currentText().strip()
        material = MATERIAL_LIBRARY.get(material_name)
        is_custom = material is None
        e_widget.setReadOnly(not is_custom)
        nu_widget.setReadOnly(not is_custom)

        if material is None:
            return
        e_widget.setText(f"{material['e_mpa']:.0f}")
        nu_widget.setText(f"{material['nu']:.2f}")

    def _hide_all_ref_badges(self) -> None:
        for badge in self._ref_badges.values():
            badge.setVisible(False)

    def _sync_friction_from_material(self) -> None:
        shaft_combo = self._field_widgets.get("materials.shaft_material")
        hub_combo = self._field_widgets.get("materials.hub_material")
        surface_combo = self._field_widgets.get("friction.surface_condition")
        if not all(isinstance(c, QComboBox) for c in (shaft_combo, hub_combo, surface_combo)):
            return

        cat_shaft = MATERIAL_CATEGORY.get(shaft_combo.currentText().strip())
        cat_hub = MATERIAL_CATEGORY.get(hub_combo.currentText().strip())
        surface = surface_combo.currentText().strip()

        if cat_shaft is None or cat_hub is None or surface == "自定义":
            self._hide_all_ref_badges()
            return

        key = (frozenset({cat_shaft, cat_hub}), surface)
        entry = FRICTION_TABLE.get(key)
        if entry is None:
            self._hide_all_ref_badges()
            return

        cat_a = CATEGORY_DISPLAY.get(cat_shaft, cat_shaft)
        cat_b = CATEGORY_DISPLAY.get(cat_hub, cat_hub)
        # AlSi9Cu3 配对标注为经验值，其余标注 DIN 7190-1
        if "alsi9cu3" in {cat_shaft, cat_hub}:
            self._friction_source_text = f"经验值 \u00b7 {cat_a}/{cat_b} \u00b7 {surface}"
        else:
            self._friction_source_text = f"DIN 7190-1 参考 \u00b7 {cat_a}/{cat_b} \u00b7 {surface}"

        self._friction_ref_values.clear()
        for fid in _FRICTION_MU_FIELDS:
            mu_key = fid.split(".")[-1]
            value = entry[mu_key]
            self._friction_ref_values[fid] = value
            widget = self._field_widgets.get(fid)
            if isinstance(widget, QLineEdit):
                widget.blockSignals(True)
                widget.setText(f"{value:.2f}")
                widget.blockSignals(False)
            badge = self._ref_badges.get(fid)
            if badge is not None:
                badge.setText(self._friction_source_text)
                badge.setVisible(True)

    def _check_friction_modified(self) -> None:
        if not self._friction_ref_values:
            return
        for fid in _FRICTION_MU_FIELDS:
            ref = self._friction_ref_values.get(fid)
            if ref is None:
                continue
            widget = self._field_widgets.get(fid)
            badge = self._ref_badges.get(fid)
            if badge is None or not isinstance(widget, QLineEdit):
                continue
            try:
                current = float(widget.text())
            except (ValueError, TypeError):
                badge.setText(f"已修改（参考值 {ref}）")
                continue
            if abs(current - ref) < 1e-9:
                badge.setText(self._friction_source_text)
            else:
                badge.setText(f"已修改（参考值 {ref}）")

    def _infer_material_preset(self, e_value: Any, nu_value: Any) -> str:
        try:
            e_numeric = float(e_value)
            nu_numeric = float(nu_value)
        except (TypeError, ValueError):
            return "自定义"
        for name, material in MATERIAL_LIBRARY.items():
            if material is None:
                continue
            if abs(e_numeric - float(material["e_mpa"])) < 1e-6 and abs(nu_numeric - float(material["nu"])) < 1e-9:
                return name
        return "自定义"

    def _infer_roughness_profile(self, smoothing_factor: Any) -> str:
        try:
            factor_numeric = float(smoothing_factor)
        except (TypeError, ValueError):
            return "自定义k"
        for name, factor in ROUGHNESS_PROFILE_FACTORS.items():
            if factor is None:
                continue
            if abs(factor_numeric - float(factor)) < 1e-9:
                return name
        return "自定义k"

    def _register_roughness_binding(self) -> None:
        selector = self._field_widgets.get(self._roughness_profile_field)
        if isinstance(selector, QComboBox):
            selector.currentTextChanged.connect(lambda _text: self._sync_roughness_factor())

    def _sync_roughness_factor(self) -> None:
        selector = self._field_widgets.get(self._roughness_profile_field)
        factor_widget = self._field_widgets.get(self._roughness_factor_field)
        if not isinstance(selector, QComboBox) or not isinstance(factor_widget, QLineEdit):
            return
        profile = selector.currentText().strip()
        factor = ROUGHNESS_PROFILE_FACTORS.get(profile)
        is_custom = factor is None
        factor_widget.setReadOnly(not is_custom)
        if factor is not None:
            factor_widget.setText(f"{factor:.2f}")

    def _register_fit_bindings(self) -> None:
        selector = self._field_widgets.get(self._fit_mode_field)
        if isinstance(selector, QComboBox):
            selector.currentTextChanged.connect(lambda _text: self._sync_fit_mode_fields())
        preferred = self._field_widgets.get(self._fit_preferred_field)
        if isinstance(preferred, QComboBox):
            preferred.currentTextChanged.connect(lambda _text: self._sync_fit_mode_fields())
        nominal = self._field_widgets.get(self._fit_nominal_field)
        if isinstance(nominal, QLineEdit):
            nominal.textChanged.connect(lambda _text: self._sync_fit_mode_fields())
        for field_id in self._fit_deviation_fields:
            widget = self._field_widgets.get(field_id)
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _text, _fid=field_id: self._sync_fit_mode_fields())

    def _register_assembly_bindings(self) -> None:
        selector = self._field_widgets.get(self._assembly_method_field)
        if isinstance(selector, QComboBox):
            selector.currentTextChanged.connect(lambda _text: self._sync_assembly_fields())
        clearance_mode = self._field_widgets.get(self._assembly_clearance_mode_field)
        if isinstance(clearance_mode, QComboBox):
            clearance_mode.currentTextChanged.connect(lambda _text: self._sync_assembly_fields())
        nominal = self._field_widgets.get(self._fit_nominal_field)
        if isinstance(nominal, QLineEdit):
            nominal.textChanged.connect(lambda _text: self._sync_assembly_fields())

    def _set_card_disabled(self, field_id: str, disabled: bool) -> None:
        """Toggle a field card between normal SubCard and disabled AutoCalcCard style."""
        card = self._field_cards.get(field_id)
        if card is None:
            return
        card.setObjectName("AutoCalcCard" if disabled else "SubCard")
        card.style().unpolish(card)
        card.style().polish(card)
        # Also propagate to child widgets so QSS descendant selectors take effect
        for child in card.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
        widget = self._field_widgets.get(field_id)
        if isinstance(widget, QLineEdit):
            widget.setReadOnly(disabled)
        elif isinstance(widget, QComboBox):
            widget.setEnabled(not disabled)

    def _sync_assembly_fields(self) -> None:
        selector = self._field_widgets.get(self._assembly_method_field)
        if not isinstance(selector, QComboBox):
            return
        method = selector.currentText().strip()
        use_shrink = method == "shrink_fit"
        use_force = method == "force_fit"

        clearance_mode = self._field_widgets.get(self._assembly_clearance_mode_field)
        if isinstance(clearance_mode, QComboBox):
            clearance_mode.setEnabled(use_shrink)
        self._set_card_disabled(self._assembly_clearance_mode_field, not use_shrink)
        clearance_direct = (
            isinstance(clearance_mode, QComboBox)
            and clearance_mode.currentText().strip() == "direct_value"
        )

        for field_id in self._assembly_shrink_fields:
            widget = self._field_widgets.get(field_id)
            if not isinstance(widget, QLineEdit):
                continue
            if field_id == "assembly.clearance_um":
                disabled = not use_shrink or not clearance_direct
                self._set_card_disabled(field_id, disabled)
                if use_shrink and not clearance_direct:
                    nominal_widget = self._field_widgets.get(self._fit_nominal_field)
                    if isinstance(nominal_widget, QLineEdit):
                        raw_nominal = nominal_widget.text().strip()
                        try:
                            widget.setText(f"{float(raw_nominal):.3f}".rstrip("0").rstrip("."))
                        except ValueError:
                            pass
            else:
                self._set_card_disabled(field_id, not use_shrink)

        for field_id in self._assembly_force_fields:
            self._set_card_disabled(field_id, not use_force)

    def _register_fretting_bindings(self) -> None:
        mode_widget = self._field_widgets.get(self._fretting_mode_field)
        if isinstance(mode_widget, QComboBox):
            mode_widget.currentTextChanged.connect(lambda _: self._sync_fretting_fields())

    def _sync_fretting_fields(self) -> None:
        mode_widget = self._field_widgets.get(self._fretting_mode_field)
        enabled = isinstance(mode_widget, QComboBox) and mode_widget.currentText() == "on"
        for field_id in self._fretting_field_ids:
            if field_id == self._fretting_mode_field:
                continue
            self._set_card_disabled(field_id, not enabled)

    def _sync_fit_mode_fields(self) -> None:
        selector = self._field_widgets.get(self._fit_mode_field)
        if not isinstance(selector, QComboBox):
            return
        mode = selector.currentText().strip()
        use_deviations = mode == "偏差换算"
        use_preferred = mode == "优选配合"

        for field_id in self._fit_delta_fields:
            self._set_card_disabled(field_id, use_deviations or use_preferred)

        for field_id in self._fit_deviation_fields:
            self._set_card_disabled(field_id, not use_deviations)

        self._set_card_disabled(self._fit_preferred_field, not use_preferred)

        if not use_deviations and not use_preferred:
            return

        try:
            if use_deviations:
                raw_values: dict[str, float] = {}
                for field_id in self._fit_deviation_fields:
                    widget = self._field_widgets.get(field_id)
                    if not isinstance(widget, QLineEdit):
                        return
                    raw = widget.text().strip()
                    if raw == "":
                        return
                    raw_values[field_id] = float(raw)

                derived = derive_interference_from_deviations(
                    shaft_upper_um=raw_values["fit.shaft_upper_deviation_um"],
                    shaft_lower_um=raw_values["fit.shaft_lower_deviation_um"],
                    hub_upper_um=raw_values["fit.hub_upper_deviation_um"],
                    hub_lower_um=raw_values["fit.hub_lower_deviation_um"],
                )
            else:
                preferred_widget = self._field_widgets.get(self._fit_preferred_field)
                if not isinstance(preferred_widget, QComboBox):
                    return
                nominal_widget = self._field_widgets.get(self._fit_nominal_field)
                if not isinstance(nominal_widget, QLineEdit):
                    return
                raw_nominal = nominal_widget.text().strip()
                if raw_nominal == "":
                    return
                derived = derive_interference_from_preferred_fit(
                    fit_name=preferred_widget.currentText().strip(),
                    nominal_diameter_mm=float(raw_nominal),
                )
        except (InputError, ValueError):
            return

        for field_id, key in (
            ("fit.delta_min_um", "delta_min_um"),
            ("fit.delta_max_um", "delta_max_um"),
        ):
            widget = self._field_widgets.get(field_id)
            if isinstance(widget, QLineEdit):
                widget.setText(f"{float(derived[key]):.3f}".rstrip("0").rstrip("."))

    def _set_badge(self, label: QLabel, text: str, state: str) -> None:
        if state == "pass":
            obj = "PassBadge"
        elif state == "fail":
            obj = "FailBadge"
        else:
            obj = "WaitBadge"
        label.setText(text)
        label.setObjectName(obj)
        label.style().unpolish(label)
        label.style().polish(label)

    def _read_widget_value(self, spec: FieldSpec) -> str:
        widget = self._field_widgets[spec.field_id]
        if spec.widget_type == "choice":
            return widget.currentText().strip()  # type: ignore[attr-defined]
        return widget.text().strip()  # type: ignore[attr-defined]

    def _build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for spec in self._field_specs.values():
            if spec.mapping is None:
                continue
            raw = self._read_widget_value(spec)
            if raw == "":
                continue
            try:
                value = float(raw)
            except ValueError as exc:
                raise InputError(f"字段“{spec.label}”请输入数字，当前值: {raw}") from exc
            sec, key = spec.mapping
            payload.setdefault(sec, {})[key] = value

        fit_mode = self._read_widget_value(self._field_specs[self._fit_mode_field])
        if fit_mode == "偏差换算":
            derived = derive_interference_from_deviations(
                shaft_upper_um=float(self._read_widget_value(self._field_specs["fit.shaft_upper_deviation_um"])),
                shaft_lower_um=float(self._read_widget_value(self._field_specs["fit.shaft_lower_deviation_um"])),
                hub_upper_um=float(self._read_widget_value(self._field_specs["fit.hub_upper_deviation_um"])),
                hub_lower_um=float(self._read_widget_value(self._field_specs["fit.hub_lower_deviation_um"])),
            )
            payload.setdefault("fit", {})["delta_min_um"] = float(derived["delta_min_um"])
            payload.setdefault("fit", {})["delta_max_um"] = float(derived["delta_max_um"])
            payload["fit_selection"] = derived
        elif fit_mode == "优选配合":
            derived = derive_interference_from_preferred_fit(
                fit_name=self._read_widget_value(self._field_specs[self._fit_preferred_field]),
                nominal_diameter_mm=float(self._read_widget_value(self._field_specs[self._fit_nominal_field])),
            )
            payload.setdefault("fit", {})["delta_min_um"] = float(derived["delta_min_um"])
            payload.setdefault("fit", {})["delta_max_um"] = float(derived["delta_max_um"])
            payload["fit_selection"] = derived
        else:
            fit_data = payload.setdefault("fit", {})
            payload["fit_selection"] = {
                "mode": "manual_interference",
                "delta_min_um": float(fit_data.get("delta_min_um", 0.0)),
                "delta_max_um": float(fit_data.get("delta_max_um", 0.0)),
            }

        assembly_mode = self._read_widget_value(self._field_specs[self._assembly_method_field]) or "manual_only"
        assembly_payload = payload.get("assembly", {}).copy()
        if assembly_mode == "manual_only":
            payload["assembly"] = {"method": "manual_only"}
        elif assembly_mode == "shrink_fit":
            assembly_payload["method"] = "shrink_fit"
            assembly_payload["clearance_mode"] = self._read_widget_value(
                self._field_specs[self._assembly_clearance_mode_field]
            )
            assembly_payload.pop("mu_press_in", None)
            assembly_payload.pop("mu_press_out", None)
            payload["assembly"] = assembly_payload
        else:
            assembly_payload["method"] = "force_fit"
            for key in (
                "room_temperature_c",
                "shaft_temperature_c",
                "clearance_um",
                "alpha_hub_1e6_per_c",
                "alpha_shaft_1e6_per_c",
                "hub_temp_limit_c",
            ):
                assembly_payload.pop(key, None)
            assembly_payload.pop("clearance_mode", None)
            payload["assembly"] = assembly_payload
        payload["fretting"] = {
            "mode": self._read_widget_value(self._field_specs[self._fretting_mode_field]) or "off",
            "load_spectrum": self._read_widget_value(self._field_specs["fretting.load_spectrum"]) or "pulsating",
            "duty_severity": self._read_widget_value(self._field_specs["fretting.duty_severity"]) or "medium",
            "surface_condition": self._read_widget_value(self._field_specs["fretting.surface_condition"]) or "dry",
            "importance_level": self._read_widget_value(self._field_specs["fretting.importance_level"]) or "important",
        }
        return payload

    def _calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_interference_fit(payload)
        except InputError as exc:
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        self._last_payload = payload
        self._last_result = result
        self._render_result(result)
        self.set_current_chapter(self.chapter_stack.count() - 1)

    def _render_result(self, result: dict[str, Any]) -> None:
        overall = bool(result.get("overall_pass"))
        checks = result["checks"]
        fit_trace_lines = self._build_fit_trace_lines()

        if overall:
            self.result_title.setText("校核通过")
            self.result_summary.setText("该工况在当前输入范围内满足 DIN 7190 核心能力、联合作用、张口缝与应力要求。")
            self.set_overall_status("总体通过", "pass")
        else:
            self.result_title.setText("校核不通过")
            self.result_summary.setText("存在未满足项，请优先查看联合作用、张口缝、需求过盈和应力侧提示。")
            self.set_overall_status("总体不通过", "fail")

        for key, badge in self._check_badges.items():
            ok = bool(checks.get(key, False))
            self._set_badge(badge, "通过" if ok else "不通过", "pass" if ok else "fail")

        p = result["pressure_mpa"]
        cap = result["capacity"]
        asm = result["assembly"]
        asm_detail = result.get("assembly_detail", {})
        req = result["required"]
        rough = result["roughness"]
        stress = result["stress_mpa"]
        safety = result["safety"]
        add_p = result["additional_pressure_mpa"]
        model = result.get("model", {})
        derived = result.get("derived", {})
        assembly_lines = self._build_assembly_trace_lines()
        fretting_lines = self._build_fretting_trace_lines()
        shaft_type = "hollow shaft" if model.get("shaft_type") == "hollow_shaft" else "solid shaft"
        shaft_inner_d_mm = float(derived.get("shaft_inner_d_mm", 0.0))

        metric_lines = [
            f"• 几何模型: {shaft_type}, shaft inner diameter={shaft_inner_d_mm:.2f} mm",
            f"• 设计需求压强: p_req,T={req['p_required_torque_mpa']:.2f} MPa, p_req,Ax={req['p_required_axial_mpa']:.2f} MPa, "
            f"p_req,comb={req['p_required_combined_mpa']:.2f} MPa, p_gap={req['p_required_gap_mpa']:.2f} MPa, "
            f"p_req,total={req['p_required_mpa']:.2f} MPa",
            *[f"• {line}" for line in fit_trace_lines],
            f"• 设计载荷与需求过盈: KA={safety['application_factor_ka']:.2f}, delta_req={req['delta_required_um']:.2f} um",
            f"• 接触压力 min/mean/max: {p['p_min']:.2f} / {p['p_mean']:.2f} / {p['p_max']:.2f} MPa",
            f"• 扭矩能力 min/mean/max: {cap['torque_min_nm']:.1f} / {cap['torque_mean_nm']:.1f} / {cap['torque_max_nm']:.1f} N·m",
            f"• 轴向能力 min/mean/max: {cap['axial_min_n']:.0f} / {cap['axial_mean_n']:.0f} / {cap['axial_max_n']:.0f} N",
            f"• 压入力 min/mean/max: {asm['press_force_min_n']:.0f} / {asm['press_force_mean_n']:.0f} / {asm['press_force_max_n']:.0f} N",
            *[f"• {line}" for line in assembly_lines],
            *[f"• {line}" for line in fretting_lines],
            f"• 附加载荷压强: p_r={add_p['p_radial']:.2f} MPa, p_b={add_p['p_bending']:.2f} MPa, p_gap={add_p['p_gap']:.2f} MPa",
            f"• 粗糙度修正: s={rough['subsidence_um']:.2f} um, delta_eff,min/mean/max={rough['delta_effective_min_um']:.2f} / {rough['delta_effective_mean_um']:.2f} / {rough['delta_effective_max_um']:.2f} um",
            f"• 应力 max: shaft_vm={stress['shaft_vm_max']:.1f} MPa, hub_vm={stress['hub_vm_max']:.1f} MPa, hub_sigma_theta={stress['hub_hoop_inner_max']:.1f} MPa",
            f"• 安全系数: S_torque={safety['torque_sf']:.2f}, S_axial={safety['axial_sf']:.2f}, "
                f"S_comb={safety['combined_sf']:.2f}, S_shaft={safety['shaft_sf']:.2f}, S_hub={safety['hub_sf']:.2f}",
        ]
        self.metrics_text.setText("\n".join(metric_lines))

        curve = result["press_force_curve"]
        self.curve_widget.set_curve(
            curve["interference_um"],
            curve["force_n"],
            curve["delta_min_um"],
            curve["delta_max_um"],
            curve["delta_required_um"],
        )

        messages = []
        for msg in result.get("messages", []):
            messages.append(f"[提示] {msg}")
        messages.extend(self._build_recommendations(result))
        fretting_result = result.get("fretting", {})
        if isinstance(fretting_result, dict) and fretting_result.get("enabled"):
            risk_level = str(fretting_result.get("risk_level", "not_applicable"))
            messages.append(f"[Step 5] Fretting 风险等级: {risk_level}")
            for recommendation in fretting_result.get("recommendations", []):
                messages.append(f"[Step 5 建议] {recommendation}")
        messages.append(
            "[说明] 当前模型为 DIN 7190 核心增强版：线弹性、均匀接触压力、恒定摩擦。"
            "弯矩附加压强按 QW=0 的保守简化处理；当前仅内置有限范围的优选配合预设，"
            "阶梯轮毂与离心力未纳入本轮。空心轴主模型已支持，但重复载荷简化式仍仅适用于实心轴。"
        )
        messages.append("[说明] Step 5 Fretting 风险评估属于增强结果，不改变基础通过/不通过结论。")
        self.message_box.setPlainText("\n".join(messages))

    def _build_recommendations(self, result: dict[str, Any]) -> list[str]:
        checks = result.get("checks", {})
        recs: list[str] = []
        if not checks.get("gaping_ok", True):
            recs.append("[建议] 存在张口缝风险：优先增大最小过盈、提高配合长度或降低径向力/弯矩。")
        if not checks.get("torque_ok", True):
            recs.append("[建议] 扭矩能力不足：可增大最小过盈、提高 mu_T 或增大配合长度。")
        if not checks.get("axial_ok", True):
            recs.append("[建议] 轴向能力不足：可增大最小过盈、提高 mu_Ax 或增加接触面积。")
        if not checks.get("combined_ok", True):
            recs.append("[建议] 联合作用不足：需同时提高扭矩与轴向共同承载能力，不能只看单项通过。")
        if not checks.get("fit_range_ok", True):
            recs.append("[建议] 最大过盈端仍不足以覆盖需求：请提升公差带或调整结构尺寸。")
        if not checks.get("shaft_stress_ok", True):
            recs.append("[建议] 轴侧应力安全系数不足：降低最大过盈或提高轴材料屈服强度。")
        if not checks.get("hub_stress_ok", True):
            recs.append("[建议] 轮毂应力安全系数不足：优先增大轮毂外径或提高轮毂材料强度。")
        if not recs:
            recs.append("[建议] 当前工况满足全部校核，建议至少保留 10% 工程裕量。")
        return recs

    def _build_fit_trace_lines(self) -> list[str]:
        fit_selection = {}
        if isinstance(self._last_payload, dict):
            fit_selection = self._last_payload.get("fit_selection", {})
        if not isinstance(fit_selection, dict):
            fit_selection = {}

        mode = str(fit_selection.get("mode", "manual_interference"))
        lines = [f"fit source: {mode}"]

        if mode == "user_defined_deviations":
            deviations = fit_selection.get("deviations_um", {})
            if isinstance(deviations, dict):
                lines.append(
                    "fit deviations um: "
                    f"shaft_es={float(deviations.get('shaft_upper_um', 0.0)):.3f}, "
                    f"shaft_ei={float(deviations.get('shaft_lower_um', 0.0)):.3f}, "
                    f"hub_ES={float(deviations.get('hub_upper_um', 0.0)):.3f}, "
                    f"hub_EI={float(deviations.get('hub_lower_um', 0.0)):.3f}"
                )
        elif mode == "preferred_fit":
            lines.append(f"fit name: {fit_selection.get('fit_name', '-')}")
            lines.append(
                "fit standard: "
                f"{fit_selection.get('standard', 'ISO 286 curated preferred-fit subset')}"
            )
            band = fit_selection.get("diameter_band_mm", {})
            if isinstance(band, dict):
                lines.append(
                    "fit nominal/band mm: "
                    f"{float(fit_selection.get('nominal_diameter_mm', 0.0)):.3f} / "
                    f"{float(band.get('lower_mm', 0.0)):.0f}~{float(band.get('upper_mm', 0.0)):.0f}"
                )
            warnings = fit_selection.get("warnings", [])
            if isinstance(warnings, list):
                for warning in warnings:
                    lines.append(f"fit warning: {warning}")

        delta_min_um = fit_selection.get("delta_min_um")
        delta_max_um = fit_selection.get("delta_max_um")
        if delta_min_um is not None and delta_max_um is not None:
            lines.append(
                f"fit delta window: {float(delta_min_um):.3f} / {float(delta_max_um):.3f} um"
            )
        return lines

    def _build_assembly_trace_lines(self) -> list[str]:
        if not isinstance(self._last_result, dict):
            return []
        assembly_detail = self._last_result.get("assembly_detail", {})
        if not isinstance(assembly_detail, dict):
            return []

        method = str(assembly_detail.get("method", "manual_only"))
        lines = [f"assembly method: {method}"]
        service = assembly_detail.get("service_friction", {})
        assembly_friction = assembly_detail.get("assembly_friction", {})
        if isinstance(service, dict) and isinstance(assembly_friction, dict):
            lines.append(
                "assembly friction trace: "
                f"mu_T={float(service.get('mu_torque', 0.0)):.3f}, "
                f"mu_Ax={float(service.get('mu_axial', 0.0)):.3f}, "
                f"mu_Assy={float(assembly_friction.get('mu_generic', 0.0)):.3f}"
            )

        if method == "shrink_fit":
            shrink = assembly_detail.get("shrink_fit", {})
            if isinstance(shrink, dict):
                lines.append(
                    "required_hub_temperature / clearance: "
                    f"{float(shrink.get('required_hub_temperature_c', 0.0)):.3f} °C / "
                    f"{float(shrink.get('clearance_um', 0.0)):.3f} um"
                )
        elif method == "force_fit":
            force_fit = assembly_detail.get("force_fit", {})
            if isinstance(force_fit, dict):
                lines.append(
                    "press_in_force / press_out_force: "
                    f"{float(force_fit.get('press_in_force_n', 0.0)):.3f} / "
                    f"{float(force_fit.get('press_out_force_n', 0.0)):.3f} N"
                )
        return lines

    def _build_fretting_trace_lines(self) -> list[str]:
        if not isinstance(self._last_result, dict):
            return []
        fretting = self._last_result.get("fretting", {})
        if not isinstance(fretting, dict):
            return []

        lines = [
            "fretting: "
            f"enabled={fretting.get('enabled', False)}, applicable={fretting.get('applicable', False)}"
        ]
        lines.append(f"risk level: {fretting.get('risk_level', 'not_applicable')}")
        risk_score = fretting.get("risk_score")
        if risk_score is not None:
            lines.append(f"risk score: {float(risk_score):.3f} / {float(fretting.get('max_score', 0.0)):.3f}")
        notes = fretting.get("notes", [])
        if isinstance(notes, list):
            for note in notes:
                lines.append(f"fretting note: {note}")
        return lines

    def _build_input_source_trace_lines(self) -> list[str]:
        def read(field_id: str, fallback: str = "-") -> str:
            spec = self._field_specs.get(field_id)
            if spec is None:
                return fallback
            value = self._read_widget_value(spec)
            return value or fallback

        lines = [
            f"shaft inner diameter: {read('geometry.shaft_inner_d_mm', '0')}",
            f"shaft material preset: {read('materials.shaft_material')}",
            f"hub material preset: {read('materials.hub_material')}",
            f"roughness profile source: {read('roughness.profile')}",
            f"fit ui mode: {read('fit.mode')}",
            f"assembly ui mode: {read('assembly.method')}",
            f"fretting mode: {read('fretting.mode')}",
        ]
        preferred_fit = read("fit.preferred_fit_name", "")
        if preferred_fit:
            lines.append(f"preferred fit selector: {preferred_fit}")
        return lines

    def _capture_input_snapshot(self) -> dict[str, Any]:
        return build_form_snapshot(self._field_specs.values(), self._read_widget_value)

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        inputs_data = data.get("inputs")
        inputs = inputs_data if isinstance(inputs_data, dict) else data
        ui_state_data = data.get("ui_state")
        ui_state = ui_state_data if isinstance(ui_state_data, dict) else {}
        legacy_ui_repeated_mode = ui_state.get("advanced.repeated_load_mode")

        self._clear()
        # Default surface condition to "自定义" before restoring fields;
        # will be overwritten if present in ui_state during the for-loop.
        sc_widget = self._field_widgets.get("friction.surface_condition")
        if isinstance(sc_widget, QComboBox):
            sc_widget.setCurrentText("自定义")
        legacy_repeated_mode = None
        advanced_section = inputs.get("advanced")
        if isinstance(advanced_section, dict):
            legacy_repeated_mode = advanced_section.get("repeated_load_mode")
        for spec in self._field_specs.values():
            value: Any | None = None
            if spec.field_id in ui_state:
                value = ui_state[spec.field_id]
            elif spec.field_id == "materials.shaft_material" and "materials.shaft_material" not in ui_state:
                materials_section = inputs.get("materials")
                if isinstance(materials_section, dict):
                    value = self._infer_material_preset(
                        materials_section.get("shaft_e_mpa"),
                        materials_section.get("shaft_nu"),
                    )
            elif spec.field_id == "materials.hub_material" and "materials.hub_material" not in ui_state:
                materials_section = inputs.get("materials")
                if isinstance(materials_section, dict):
                    value = self._infer_material_preset(
                        materials_section.get("hub_e_mpa"),
                        materials_section.get("hub_nu"),
                    )
            elif spec.field_id == "roughness.profile" and "roughness.profile" not in ui_state:
                roughness_section = inputs.get("roughness")
                if isinstance(roughness_section, dict):
                    value = self._infer_roughness_profile(roughness_section.get("smoothing_factor"))
            elif spec.field_id == "assembly.method" and "assembly.method" not in ui_state:
                assembly_section = inputs.get("assembly")
                if isinstance(assembly_section, dict) and "method" in assembly_section:
                    value = assembly_section["method"]
            elif spec.field_id == "assembly.clearance_mode" and "assembly.clearance_mode" not in ui_state:
                assembly_section = inputs.get("assembly")
                if isinstance(assembly_section, dict) and "clearance_mode" in assembly_section:
                    value = assembly_section["clearance_mode"]
            elif spec.field_id == "fit.mode" and "fit.mode" not in ui_state:
                fit_selection_section = inputs.get("fit_selection")
                if isinstance(fit_selection_section, dict):
                    mode = str(fit_selection_section.get("mode", "")).strip()
                    if mode == "preferred_fit":
                        value = "优选配合"
                    elif mode == "user_defined_deviations":
                        value = "偏差换算"
                    elif mode:
                        value = "直接输入过盈量"
            elif spec.field_id == "fit.preferred_fit_name" and "fit.preferred_fit_name" not in ui_state:
                fit_selection_section = inputs.get("fit_selection")
                if isinstance(fit_selection_section, dict) and "fit_name" in fit_selection_section:
                    value = fit_selection_section["fit_name"]
            elif spec.field_id.startswith("fit.") and "fit.mode" not in ui_state:
                fit_selection_section = inputs.get("fit_selection")
                if isinstance(fit_selection_section, dict) and str(fit_selection_section.get("mode", "")).strip() == "user_defined_deviations":
                    deviations = fit_selection_section.get("deviations_um")
                    if isinstance(deviations, dict):
                        deviation_map = {
                            "fit.shaft_upper_deviation_um": "shaft_upper_um",
                            "fit.shaft_lower_deviation_um": "shaft_lower_um",
                            "fit.hub_upper_deviation_um": "hub_upper_um",
                            "fit.hub_lower_deviation_um": "hub_lower_um",
                        }
                        deviation_key = deviation_map.get(spec.field_id)
                        if deviation_key and deviation_key in deviations:
                            value = deviations[deviation_key]
            elif spec.field_id == "fretting.mode" and "fretting.mode" not in ui_state:
                fretting_section = inputs.get("fretting")
                if isinstance(fretting_section, dict) and "mode" in fretting_section:
                    value = fretting_section["mode"]
                elif legacy_ui_repeated_mode is not None:
                    value = legacy_ui_repeated_mode
                elif legacy_repeated_mode is not None:
                    value = legacy_repeated_mode
            elif spec.field_id.startswith("fretting.") and "fretting.mode" not in ui_state:
                fretting_section = inputs.get("fretting")
                if isinstance(fretting_section, dict):
                    key = spec.field_id.split(".", 1)[1]
                    if key in fretting_section:
                        value = fretting_section[key]
            elif spec.mapping is not None:
                sec, key = spec.mapping
                section = inputs.get(sec)
                if isinstance(section, dict) and key in section:
                    value = section[key]
                elif (
                    sec == "friction"
                    and key in {"mu_torque", "mu_axial"}
                    and isinstance(section, dict)
                    and "mu_static" in section
                ):
                    value = section["mu_static"]
            if value is None:
                continue
            widget = self._field_widgets[spec.field_id]
            text = str(value)
            if spec.widget_type == "choice":
                idx = widget.findText(text)  # type: ignore[attr-defined]
                if idx >= 0:
                    widget.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(text)  # type: ignore[attr-defined]

        self._sync_material_inputs()
        self._sync_roughness_factor()
        self._sync_fit_mode_fields()
        self._sync_assembly_fields()

    def _load_sample(self, filename: str) -> None:
        sample_path = EXAMPLES_DIR / filename
        if not sample_path.exists():
            QMessageBox.warning(self, "测试案例不存在", f"未找到测试案例文件: {sample_path}")
            return

        try:
            data = read_input_conditions(sample_path)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "测试案例损坏", f"测试案例文件不是有效 JSON：{exc}")
            return

        self._apply_input_data(data)
        self.set_info(f"已加载测试案例：{filename}。可直接执行校核并查看压入力曲线。")

    def _save_input_conditions(self) -> None:
        default_path = SAVED_INPUTS_DIR / "interference_fit_input_conditions.json"
        out_path = choose_save_input_conditions_path(self, "保存输入条件", default_path)
        if out_path is None:
            return
        try:
            write_input_conditions(out_path, self._capture_input_snapshot())
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", f"输入条件保存失败：{exc}")
            return
        self.set_info(f"输入条件已保存：{out_path}")

    def _load_input_conditions(self) -> None:
        in_path = choose_load_input_conditions_path(self, "加载输入条件", SAVED_INPUTS_DIR)
        if in_path is None:
            return
        try:
            data = read_input_conditions(in_path)
        except FileNotFoundError:
            QMessageBox.warning(self, "文件不存在", f"未找到输入条件文件：{in_path}")
            return
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "文件损坏", f"输入条件文件不是有效 JSON：{exc}")
            return
        except OSError as exc:
            QMessageBox.critical(self, "加载失败", f"输入条件加载失败：{exc}")
            return

        self._apply_input_data(data)
        self.set_info(f"已加载输入条件：{in_path}")

    def _clear(self) -> None:
        self._friction_ref_values.clear()
        self._hide_all_ref_badges()
        self._apply_defaults()
        self._sync_friction_from_material()
        self._last_payload = None
        self._last_result = None
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText("填写参数并点击“执行校核”后，这里显示结论。")
        self.metrics_text.setText("尚无结果。")
        self.message_box.clear()
        for badge in self._check_badges.values():
            self._set_badge(badge, "待计算", "wait")
        self.curve_widget.set_curve([], [], 0.0, 0.0, 0.0)
        self.set_overall_status("等待计算", "wait")
        self.set_info("参数已重置为默认值。")

    def _save_report(self) -> None:
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行校核计算。")
            return

        default_path = EXAMPLES_DIR / "interference_fit_report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出校核报告", str(default_path),
            "PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = out_path.suffix.lower()
        if suffix == ".pdf":
            try:
                mod = importlib.import_module("app.ui.report_pdf_interference")
                mod.generate_interference_report(out_path, self._last_payload, self._last_result)
            except Exception:
                from app.ui.report_export import _export_pdf
                _export_pdf(out_path, self._build_report_lines())
        elif suffix == ".docx":
            from app.ui.report_export import _export_docx
            _export_docx(out_path, self._build_report_lines())
        else:
            out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
        self.set_info(f"校核报告已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        assert self._last_result is not None
        result = self._last_result
        checks = result["checks"]
        p = result["pressure_mpa"]
        cap = result["capacity"]
        asm = result["assembly"]
        stress = result["stress_mpa"]
        safety = result["safety"]
        req = result["required"]
        rough = result["roughness"]
        add_p = result["additional_pressure_mpa"]
        model = result.get("model", {})
        derived = result.get("derived", {})
        shaft_type = "hollow shaft" if model.get("shaft_type") == "hollow_shaft" else "solid shaft"
        shaft_inner_d_mm = float(derived.get("shaft_inner_d_mm", 0.0))

        lines = [
            "过盈配合校核报告（DIN 7190 核心增强版）",
            f"生成时间: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"总体结论: {'通过' if result['overall_pass'] else '不通过'}",
            "",
            "分项结果:",
        ]
        for key, title in CHECK_LABELS.items():
            lines.append(f"- {title}: {'通过' if checks.get(key) else '不通过'}")

        lines.extend(
            [
                "",
                "输入来源追溯:",
                *[f"- {line}" for line in self._build_input_source_trace_lines()],
                "",
                "关键值:",
                f"- shaft type / shaft inner diameter: {shaft_type} / {shaft_inner_d_mm:.3f} mm",
                f"- p_min / p_mean / p_max / p_req: {p['p_min']:.3f} / {p['p_mean']:.3f} / {p['p_max']:.3f} / {p['p_required']:.3f} MPa",
                f"- p_req,T / p_req,Ax / p_req,comb / p_gap: {req['p_required_torque_mpa']:.3f} / {req['p_required_axial_mpa']:.3f} / {req['p_required_combined_mpa']:.3f} / {req['p_required_gap_mpa']:.3f} MPa",
                *[f"- {line}" for line in self._build_fit_trace_lines()],
                *[f"- {line}" for line in self._build_assembly_trace_lines()],
                "",
                "Step 5 Fretting 风险评估:",
                *[f"- {line}" for line in self._build_fretting_trace_lines()],
                "- Step 5 fretting risk assessment is an enhancement result and does not change the base pass/fail verdict.",
                f"- p_r / p_b / p_gap: {add_p['p_radial']:.3f} / {add_p['p_bending']:.3f} / {add_p['p_gap']:.3f} MPa",
                f"- roughness subsidence s: {rough['subsidence_um']:.3f} um",
                f"- delta_eff,min / mean / max: {rough['delta_effective_min_um']:.3f} / {rough['delta_effective_mean_um']:.3f} / {rough['delta_effective_max_um']:.3f} um",
                f"- T_min / mean / max: {cap['torque_min_nm']:.3f} / {cap['torque_mean_nm']:.3f} / {cap['torque_max_nm']:.3f} N·m",
                f"- F_min / mean / max: {cap['axial_min_n']:.3f} / {cap['axial_mean_n']:.3f} / {cap['axial_max_n']:.3f} N",
                f"- F_press,min / mean / max: {asm['press_force_min_n']:.3f} / {asm['press_force_mean_n']:.3f} / {asm['press_force_max_n']:.3f} N",
                f"- delta_required: {req['delta_required_um']:.3f} um",
                f"- shaft_vm_max / hub_vm_max: {stress['shaft_vm_max']:.3f} / {stress['hub_vm_max']:.3f} MPa",
                f"- S_torque / S_axial / S_comb: {safety['torque_sf']:.3f} / {safety['axial_sf']:.3f} / {safety['combined_sf']:.3f}",
                f"- S_shaft / S_hub: {safety['shaft_sf']:.3f} / {safety['hub_sf']:.3f}",
                "",
                "模型假设与排除:",
                "- 当前模型为 DIN 7190 核心增强版：线弹性、均匀接触压力、恒定摩擦；已支持实心轴与空心轴主模型。",
                "- 弯矩附加压强按 QW=0 的保守简化处理。",
                "- 本轮显式排除：centrifugal force、stepped hub geometry；repeated-load 简化式仍只适用于实心轴。",
            ]
        )
        return lines
