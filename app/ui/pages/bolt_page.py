"""Bolt module page in eAssistant-style chapter layout."""

from __future__ import annotations

import datetime as dt
import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.input_condition_store import (
    InputConditionError,
    build_form_snapshot,
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    confirm_snapshot_module,
    read_input_conditions,
    validate_snapshot,
    write_input_conditions,
)
from app.ui.widgets.clamping_diagram import ClampingDiagramWidget, ThreadForceTriangleWidget
from app.ui.widgets.help_button import HelpButton
from app.ui.report_export import ReportExportError
from app.ui.pages import bolt_help_content as bolt_help
from app.ui.pages.bolt_flowchart import (
    FlowchartNavWidget, RStepDetailPage, R_STEPS,
)
from core.bolt.calculator import InputError, calculate_vdi2230_core

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)
MODULE_ID = "bolt_vdi2230"
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$", flags=re.ASCII)


def _export_bolt_pdf_report(
    out_path: Path,
    payload: dict[str, Any],
    result: dict[str, Any],
    report_lines: list[str],
) -> bool:
    """Export the rich PDF report when reportlab is available, else fall back."""
    try:
        report_pdf = importlib.import_module("app.ui.report_pdf")
    except ModuleNotFoundError as exc:
        missing_module = (exc.name or "").split(".")[0]
        if missing_module and missing_module != "reportlab":
            raise
        if not missing_module and "reportlab" not in str(exc):
            raise
        from app.ui.report_export import _export_pdf

        _export_pdf(out_path, report_lines)
        return False

    report_pdf.generate_bolt_report(out_path, payload, result)
    return True


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
    disabled: bool = False
    help_ref: str = ""



# GB/T 196 标准公制螺纹参数表
# (d, [(p_coarse, d2, d3, As), (p_fine1, d2, d3, As), ...])
# 粗牙排第一位，细牙在后。d2/d3/As 按 GB/T 196 / ISO 724 标准值。
# 螺栓强度等级 → 屈服强度 Rp0.2 (MPa)，参考 GB/T 3098.1
BOLT_GRADE_TABLE: dict[str, float] = {
    "4.6":  240,
    "4.8":  320,
    "5.6":  300,
    "5.8":  400,
    "8.8":  640,
    "9.8":  720,
    "10.9": 900,
    "12.9": 1080,
}


METRIC_THREAD_TABLE: dict[str, list[tuple[float, float, float, float]]] = {
    "M3":   [(0.5,  2.675, 2.387, 5.03)],
    "M4":   [(0.7,  3.545, 3.141, 8.78)],
    "M5":   [(0.8,  4.480, 4.019, 14.2)],
    "M6":   [(1.0,  5.350, 4.773, 20.1)],
    "M8":   [(1.25, 7.188, 6.466, 36.6),  (1.0,  7.350, 6.773, 39.2)],
    "M10":  [(1.5,  9.026, 8.160, 58.0),  (1.25, 9.188, 8.466, 61.2),
             (1.0,  9.350, 8.773, 64.5)],
    "M12":  [(1.75, 10.863, 9.853, 84.3), (1.5,  11.026, 10.160, 88.1),
             (1.25, 11.188, 10.466, 92.1)],
    "M14":  [(2.0,  12.701, 11.546, 115),  (1.5,  13.026, 12.160, 125)],
    "M16":  [(2.0,  14.701, 13.546, 157),  (1.5,  15.026, 14.160, 167)],
    "M18":  [(2.5,  16.376, 14.933, 192),  (1.5,  17.026, 16.160, 216)],
    "M20":  [(2.5,  18.376, 16.933, 245),  (1.5,  19.026, 18.160, 272)],
    "M22":  [(2.5,  20.376, 18.933, 303),  (1.5,  21.026, 20.160, 333)],
    "M24":  [(3.0,  22.051, 20.319, 353),  (2.0,  22.701, 21.546, 384)],
    "M27":  [(3.0,  25.051, 23.319, 459),  (2.0,  25.701, 24.546, 496)],
    "M30":  [(3.5,  27.727, 25.706, 561),  (2.0,  28.701, 27.546, 621)],
    "M33":  [(3.5,  30.727, 28.706, 694),  (2.0,  31.701, 30.546, 761)],
    "M36":  [(4.0,  33.402, 31.093, 817),  (3.0,  34.051, 32.319, 865)],
    "M39":  [(4.0,  36.402, 34.093, 976),  (3.0,  37.051, 35.319, 1030)],
    "M42":  [(4.5,  39.077, 36.479, 1120), (3.0,  40.051, 38.319, 1210)],
    "M48":  [(5.0,  44.752, 41.866, 1470), (3.0,  46.051, 44.319, 1600)],
}


def _make_layer_fields(n: int) -> list[FieldSpec]:
    """生成第 n 层被夹件的 FieldSpec 列表。"""
    return [
        FieldSpec(
            f"clamped.layer_{n}.thickness",
            f"第{n}层厚度",
            "mm",
            f"第{n}层被夹件厚度。",
            mapping=None,
            default="15",
            help_ref="terms/bolt_layer_thickness",
        ),
        FieldSpec(
            f"clamped.layer_{n}.D_A",
            f"第{n}层外径 DA",
            "mm",
            f"第{n}层被夹件外径。",
            mapping=None,
            default="24",
            help_ref="terms/bolt_layer_outer_da",
        ),
        FieldSpec(
            f"clamped.layer_{n}.E",
            f"第{n}层弹性模量",
            "MPa",
            f"第{n}层被夹件弹性模量。钢 210000 / 铝 70000。",
            mapping=None,
            default="210000",
            help_ref="terms/elastic_modulus",
        ),
        FieldSpec(
            f"clamped.layer_{n}.material",
            f"第{n}层材料",
            "-",
            f"第{n}层材料选择，用于自动填入热膨胀系数。",
            mapping=None,
            widget_type="choice",
            options=("钢", "铝合金", "铸铁", "不锈钢", "自定义"),
            default="钢",
            help_ref="terms/bolt_layer_material",
        ),
        FieldSpec(
            f"clamped.layer_{n}.alpha",
            f"第{n}层热膨胀系数",
            "1/K",
            f"第{n}层热膨胀系数。由材料选择自动填入。",
            mapping=None,
            default="11.5e-6",
            help_ref="terms/bolt_thermal_loss",
        ),
    ]


LAYER_FIELD_IDS: list[list[str]] = [
    [f"clamped.layer_{n}.{f}" for f in ("thickness", "D_A", "E", "material", "alpha")]
    for n in range(1, 6)
]

SLIP_MU_MODE_FOLLOW = "跟随支承面摩擦 μK"
SLIP_MU_MODE_CUSTOM = "单独输入 μT"

ELASTIC_MODULUS_PRESETS: dict[str, str] = {
    "钢": "210000",
    "不锈钢": "193000",
    "铝合金": "70000",
    "铸铁": "120000",
}

TIGHTENING_ALPHA_A_RECOMMENDATIONS: dict[str, str] = {
    "扭矩法": "1.6",
    "转角法": "1.2",
    "液压拉伸法": "1.1",
    "热装法": "1.1",
}

POSITION_N_RECOMMENDATIONS: dict[str, str] = {
    "螺栓头端": "1.0",
    "螺母端": "0.6",
    "中间": "0.4",
    "分布式": "0.5",
}

BEARING_GEOMETRY_PRESETS: dict[str, tuple[str, str]] = {
    "M3": ("3.4", "6"),
    "M4": ("4.5", "7"),
    "M5": ("5.5", "8"),
    "M6": ("6.6", "10"),
    "M8": ("9", "13"),
    "M10": ("11", "18"),
    "M12": ("13", "22"),
    "M14": ("15", "24"),
    "M16": ("17", "27"),
    "M18": ("20", "30"),
    "M20": ("22", "34"),
    "M22": ("24", "36"),
    "M24": ("26", "39"),
    "M27": ("30", "44"),
    "M30": ("33", "48"),
    "M33": ("36", "54"),
    "M36": ("39", "58"),
    "M39": ("42", "63"),
    "M42": ("45", "68"),
    "M48": ("52", "75"),
}


CHAPTERS: list[dict[str, Any]] = [
    {
        "id": "elements",
        "title": "连接件参数",
        "subtitle": "确定这颗螺栓的规格、强度与摩擦：填这些后，所有应力校核都有了几何与材料基础。",
        "help_ref": "modules/bolt_vdi/_section_elements",
        "fields": [
            FieldSpec(
                "elements.joint_type",
                "连接形式",
                "-",
                "螺纹孔连接：螺栓拧入基体，仅螺栓头端有支承面。"
                "通孔连接：螺栓穿过被夹件，头端+螺母端均有支承面。",
                widget_type="choice",
                options=("螺纹孔连接", "通孔螺栓连接"),
                default="螺纹孔连接",
                help_ref="terms/bolt_joint_type",
            ),
            FieldSpec(
                "fastener.d",
                "公称直径 d",
                "mm",
                "选择标准公制螺纹规格，或选「自定义」手动输入。",
                mapping=("fastener", "d"),
                widget_type="choice",
                options=tuple(METRIC_THREAD_TABLE.keys()) + ("自定义",),
                default="M10",
                help_ref="terms/bolt_thread_nominal",
            ),
            FieldSpec(
                "fastener.d_custom",
                "自定义公称直径",
                "mm",
                "手动输入非标螺纹公称直径。",
                mapping=None,
                help_ref="terms/bolt_thread_nominal",
            ),
            FieldSpec(
                "fastener.p",
                "螺距 p",
                "mm",
                "选择与公称直径匹配的螺距，或选「自定义」手动输入。",
                mapping=("fastener", "p"),
                widget_type="choice",
                options=("1.5",),
                default="1.5",
                help_ref="terms/bolt_thread_pitch",
            ),
            FieldSpec(
                "fastener.p_custom",
                "自定义螺距",
                "mm",
                "手动输入非标螺距。",
                mapping=None,
                help_ref="terms/bolt_thread_pitch",
            ),
            FieldSpec(
                "fastener.d2",
                "中径 d2（自动计算）",
                "mm",
                "由所选规格自动填入。自定义模式可手动输入。",
                mapping=("fastener", "d2"),
                help_ref="terms/bolt_stress_area",
            ),
            FieldSpec(
                "fastener.d3",
                "小径 d3（自动计算）",
                "mm",
                "由所选规格自动填入。自定义模式可手动输入。",
                mapping=("fastener", "d3"),
                help_ref="terms/bolt_stress_area",
            ),
            FieldSpec(
                "fastener.As",
                "应力截面积 As（自动计算）",
                "mm²",
                "由所选规格自动填入。自定义模式可手动输入或留空（系统估算）。",
                mapping=("fastener", "As"),
                help_ref="terms/bolt_stress_area",
            ),
            FieldSpec(
                "fastener.grade",
                "强度等级",
                "-",
                "选择螺栓强度等级以自动填入屈服强度 Rp0.2。选「自定义」可手动输入。",
                mapping=None,
                widget_type="choice",
                options=tuple(BOLT_GRADE_TABLE.keys()) + ("自定义",),
                default="8.8",
                help_ref="terms/bolt_grade",
            ),
            FieldSpec(
                "fastener.Rp02",
                "屈服强度 Rp0.2（自动计算）",
                "MPa",
                "由强度等级自动填入。自定义模式可手动输入。",
                mapping=("fastener", "Rp02"),
                default="640",
                help_ref="terms/bolt_yield_strength",
            ),
            FieldSpec(
                "tightening.mu_thread",
                "螺纹摩擦系数 μG",
                "-",
                "影响螺纹扭矩与扭转载荷。",
                mapping=("tightening", "mu_thread"),
                default="0.12",
                help_ref="terms/bolt_friction_thread",
            ),
            FieldSpec(
                "tightening.mu_bearing",
                "支承面摩擦系数 μK",
                "-",
                "影响支承面扭矩。",
                mapping=("tightening", "mu_bearing"),
                default="0.14",
                help_ref="terms/bolt_friction_bearing",
            ),
            FieldSpec(
                "tightening.thread_flank_angle_deg",
                "牙型角",
                "deg",
                "公制螺纹常用 60°。",
                mapping=("tightening", "thread_flank_angle_deg"),
                default="60",
                help_ref="terms/bolt_thread_flank_angle",
            ),
            FieldSpec(
                "bearing.bearing_d_inner",
                "支承内径 DKm,i",
                "mm",
                "螺栓头/螺母下支承面的内径，通常等于通孔直径。",
                mapping=("bearing", "bearing_d_inner"),
                default="11",
                help_ref="terms/bolt_bearing_pressure_allowable",
            ),
            FieldSpec(
                "bearing.bearing_d_outer",
                "支承外径 DKm,o",
                "mm",
                "螺栓头/螺母下支承面的外径，通常等于螺栓头对边宽度。",
                mapping=("bearing", "bearing_d_outer"),
                default="18",
                help_ref="terms/bolt_bearing_pressure_allowable",
            ),
            FieldSpec(
                "bearing.bearing_material", "支承面材料", "-",
                "选择支承面材料以自动填入许用压强。",
                mapping=None, widget_type="choice",
                options=("钢", "铝合金", "自定义"), default="钢",
                help_ref="terms/bolt_bearing_material",
            ),
            FieldSpec(
                "bearing.p_G_allow", "许用支承面压强 p_G", "MPa",
                "支承面许用面压强度。钢约 700 MPa，铝合金约 300 MPa。",
                mapping=("bearing", "p_G_allow"), default="700",
                help_ref="terms/bolt_bearing_pressure_allowable",
            ),
        ],
    },
    {
        "id": "clamped",
        "title": "被夹紧件和实体",
        "subtitle": "描述螺栓所夹零件的厚度与软硬：被夹件柔度 δp 与螺栓柔度 δs 共同决定载荷因数 Φ_N。",
        "help_ref": "modules/bolt_vdi/_section_clamped",
        "fields": [
            FieldSpec(
                "clamped.basic_solid",
                "基础实体类型",
                "-",
                "用于自动柔度建模。选择几何模型后，勾选自动计算可替代手动输入顺从度。",
                mapping=None,  # spec D12/W-10：payload 由专用翻译代码写入，避免中文双写
                widget_type="choice",
                options=("圆柱体", "锥体", "套筒"),
                default="圆柱体",
                help_ref="terms/bolt_clamped_solid_type",
            ),
            FieldSpec(
                "clamped.part_count",
                "被夹件数量",
                "-",
                "参与夹紧的零件数量。选 2 或自定义时可分层输入参数。",
                mapping=None,
                widget_type="choice",
                options=("1", "2", "自定义"),
                default="1",
                help_ref="terms/bolt_clamped_part_count",
            ),
            FieldSpec(
                "clamped.custom_count",
                "自定义层数",
                "个",
                "输入被夹件层数（3~5）。",
                mapping=None,
                default="3",
                help_ref="terms/bolt_custom_part_count",
            ),
            *_make_layer_fields(1),
            *_make_layer_fields(2),
            *_make_layer_fields(3),
            *_make_layer_fields(4),
            *_make_layer_fields(5),
            FieldSpec(
                "clamped.surface_class",
                "接触面粗糙度",
                "-",
                "用于嵌入损失自动估算。选择后当嵌入损失 FZ=0 时自动计算参考值。",
                mapping=None,  # spec D12/W-10：payload 由专用翻译代码写入，避免中文双写
                widget_type="choice",
                options=("粗糙 (Ra≈6.3μm)", "中等 (Ra≈3.2μm)", "精细 (Ra≈1.6μm)"),
                default="中等 (Ra≈3.2μm)",
                help_ref="terms/bolt_embed_loss",
            ),
            FieldSpec(
                "clamped.total_thickness",
                "总夹紧长度 lK",
                "mm",
                "被夹件厚度总和。用于热损失自动估算和将来的自动刚度建模。",
                mapping=("clamped", "total_thickness"),
                default="20",
                help_ref="terms/bolt_clamp_length_lk",
            ),
            FieldSpec(
                "clamped.D_A",
                "被夹件等效外径 DA",
                "mm",
                "圆柱/锥体模型表示等效外径；套筒模型下等同于套筒外径。自动柔度计算需要。",
                mapping=("clamped", "D_A"),
                default="24",
                help_ref="terms/bolt_equivalent_outer_da",
            ),
            FieldSpec(
                "stiffness.E_bolt",
                "螺栓弹性模量",
                "MPa",
                "钢约 210000 MPa。自动柔度计算需要。",
                mapping=("stiffness", "E_bolt"),
                default="210000",
                help_ref="terms/elastic_modulus",
            ),
            FieldSpec(
                "stiffness.E_clamped",
                "被夹件弹性模量",
                "MPa",
                "钢 210000 / 铝 70000 MPa。自动柔度计算需要。",
                mapping=("stiffness", "E_clamped"),
                default="210000",
                help_ref="terms/elastic_modulus",
            ),
            FieldSpec(
                "stiffness.auto_compliance",
                "弹性柔度计算方式",
                "-",
                "柔度 = 单位力引起的弹性变形量（mm/N），描述零件软硬程度。"
                "自动计算根据几何和材料估算；手动输入则直接填写工程经验值或试验值。",
                mapping=("stiffness", "auto_compliance"),
                widget_type="choice",
                options=("手动输入", "自动计算"),
                default="手动输入",
                help_ref="terms/bolt_compliance",
            ),
            FieldSpec(
                "stiffness.bolt_compliance",
                "螺栓柔度 δs",
                "mm/N",
                "1N 拉力下螺栓的伸长量。值越大螺栓越软。"
                "与被夹件柔度配套输入；若改用刚度输入可留空。",
                mapping=("stiffness", "bolt_compliance"),
                default="2.2e-06",
                help_ref="terms/bolt_compliance",
            ),
            FieldSpec(
                "stiffness.clamped_compliance",
                "被夹件柔度 δp",
                "mm/N",
                "1N 压力下被夹件的压缩量。值越大被夹件越软。"
                "与螺栓柔度配套输入。",
                mapping=("stiffness", "clamped_compliance"),
                default="3.1e-06",
                help_ref="terms/bolt_compliance",
            ),
            FieldSpec(
                "stiffness.bolt_stiffness",
                "螺栓刚度 cs",
                "N/mm",
                "刚度 = 1/柔度，即产生 1mm 变形所需的力。"
                "若使用刚度输入，填 cs 与 cp，柔度可留空。",
                mapping=("stiffness", "bolt_stiffness"),
                help_ref="terms/bolt_compliance",
            ),
            FieldSpec(
                "stiffness.clamped_stiffness",
                "被夹件刚度 cp",
                "N/mm",
                "刚度 = 1/柔度。与 cs 配套输入。",
                mapping=("stiffness", "clamped_stiffness"),
                help_ref="terms/bolt_compliance",
            ),
        ],
    },
    {
        "id": "assembly",
        "title": "装配属性",
        "subtitle": "设定装配工艺与散差：拧紧方式决定 αA，利用系数 ν 决定装配允许应力；嵌入与热损失在此扣除。",
        "help_ref": "modules/bolt_vdi/_section_assembly",
        "fields": [
            FieldSpec(
                "assembly.tightening_method",
                "拧紧方式",
                "-",
                "装配方式选项。用于 αA 建议范围提示，并影响扭矩法下 R5 的残余扭转载荷修正。",
                widget_type="choice",
                options=("扭矩法", "转角法", "液压拉伸法", "热装法"),
                default="扭矩法",
                help_ref="terms/bolt_tightening_method",
            ),
            FieldSpec(
                "tightening.alpha_A",
                "拧紧系数 αA",
                "-",
                "FMmax/FMmin，反映装配散差。扭矩法常见 1.4~1.8。",
                mapping=("tightening", "alpha_A"),
                default="1.6",
                help_ref="terms/bolt_tightening_factor_alpha_a",
            ),
            FieldSpec(
                "tightening.utilization",
                "装配利用系数 ν",
                "-",
                "装配阶段允许屈服利用比例，常见 0.8~0.95。",
                mapping=("tightening", "utilization"),
                default="0.9",
                help_ref="terms/bolt_utilization_nu",
            ),
            FieldSpec(
                "tightening.prevailing_torque",
                "附加防松扭矩 MA,prev",
                "N·m",
                "锁紧螺母等引入的附加扭矩。无则填 0。",
                mapping=("tightening", "prevailing_torque"),
                default="0",
                help_ref="terms/bolt_prevailing_torque",
            ),
            FieldSpec(
                "loads.embed_loss",
                "嵌入损失 FZ",
                "N",
                "接触面粗糙峰压实造成的预紧力损失。**填 0** 时若已选择接触面粗糙度，"
                "将按本模块简化模型（粗糙度 × 界面数）自动估算；填非零值时使用你的手动值。",
                mapping=("loads", "embed_loss"),
                default="0",
                help_ref="terms/bolt_embed_loss",
            ),
            FieldSpec(
                "loads.thermal_force_loss",
                "热损失 Fth",
                "N",
                "热膨胀差异折算的预紧力损失。",
                mapping=("loads", "thermal_force_loss"),
                default="0",
                help_ref="terms/bolt_thermal_loss",
            ),
            FieldSpec(
                "loads.FM_min_input",
                "已知最小预紧力 FM,min",
                "N",
                "校核模式下使用：输入已知的最小预紧力值。",
                mapping=("loads", "FM_min_input"),
                help_ref="terms/bolt_preload_fm",
            ),
        ],
    },
    {
        "id": "operating",
        "title": "工况数据",
        "subtitle": "填服役实际承受的外载、温度与循环次数：驱动 R3 残余夹紧、R5 服役应力、疲劳与热损失校核。",
        "help_ref": "modules/bolt_vdi/_section_operating",
        "fields": [
            FieldSpec(
                "operating.setup_case",
                "工况类型",
                "-",
                "载荷工况说明，用于记录设计场景。",
                widget_type="choice",
                options=("轴向载荷", "横向载荷", "轴向+横向", "自由输入"),
                default="轴向+横向",
                help_ref="terms/bolt_setup_case",
            ),
            FieldSpec(
                "loads.FA_max",
                "最大轴向工作载荷 FA,max",
                "N",
                "外部轴向拉载，作用于连接上的最大工作载荷。",
                mapping=("loads", "FA_max"),
                help_ref="terms/bolt_axial_load_fa",
            ),
            FieldSpec(
                "loads.FQ_max",
                "最大横向载荷 FQ,max",
                "N",
                "横向剪切载荷，用于防滑夹紧力校核。",
                mapping=("loads", "FQ_max"),
                default="0",
                help_ref="terms/bolt_axial_load_fa",
            ),
            FieldSpec(
                "loads.seal_force_required",
                "密封所需残余夹紧力 FK,req",
                "N",
                "若有密封要求，填该值；否则可填 0。",
                mapping=("loads", "seal_force_required"),
                default="0",
                help_ref="terms/bolt_seal_clamp_force",
            ),
            FieldSpec(
                "loads.friction_interfaces",
                "摩擦面数 qF",
                "-",
                "防滑校核中参与传力的摩擦界面数量。",
                mapping=("loads", "friction_interfaces"),
                default="1",
                help_ref="terms/bolt_friction_interfaces",
            ),
            FieldSpec(
                "loads.slip_mu_mode",
                "防滑摩擦系数来源",
                "-",
                "默认跟随支承面摩擦 μK；只有防滑界面状态明显不同时才单独输入 μT。",
                mapping=None,
                widget_type="choice",
                options=(SLIP_MU_MODE_FOLLOW, SLIP_MU_MODE_CUSTOM),
                default=SLIP_MU_MODE_FOLLOW,
            ),
            FieldSpec(
                "loads.slip_friction_coefficient",
                "防滑摩擦系数 μT",
                "-",
                "防滑工况使用的摩擦系数，常与支承面摩擦不同。",
                mapping=("loads", "slip_friction_coefficient"),
                default="0.18",
                help_ref="terms/bolt_slip_friction_coefficient",
            ),
            FieldSpec(
                "operating.load_cycles",
                "载荷循环次数 ND",
                "次",
                "用于疲劳校核的循环次数输入。",
                mapping=("operating", "load_cycles"),
                default="100000",
                help_ref="terms/bolt_load_cycles",
            ),
            FieldSpec(
                "options.surface_treatment",
                "螺纹表面处理",
                "-",
                "影响疲劳极限 σ_ASV。轧制螺纹强于切削螺纹。",
                mapping=None,
                widget_type="choice",
                options=("轧制", "切削"),
                default="轧制",
                help_ref="terms/bolt_surface_treatment",
            ),
            FieldSpec(
                "operating.bolt_material",
                "螺栓材料",
                "-",
                "选择螺栓材料以自动填入热膨胀系数。选「自定义」可手动输入。",
                mapping=None,
                widget_type="choice",
                options=("钢", "不锈钢", "自定义"),
                default="钢",
                help_ref="terms/bolt_bolt_material",
            ),
            FieldSpec(
                "operating.alpha_bolt",
                "螺栓热膨胀系数 α_bolt（自动计算）",
                "1/K",
                "由材料选择自动填入。自定义模式可手动输入。",
                mapping=("operating", "alpha_bolt"),
                default="11.5e-6",
                help_ref="terms/bolt_thermal_loss",
            ),
            FieldSpec(
                "operating.clamped_material",
                "被夹件/基体材料",
                "-",
                "选择被夹件材料以自动填入热膨胀系数。选「自定义」可手动输入。",
                mapping=None,
                widget_type="choice",
                options=("钢", "铝合金", "铸铁", "不锈钢", "自定义"),
                default="钢",
                help_ref="terms/bolt_clamped_material",
            ),
            FieldSpec(
                "operating.alpha_parts",
                "被夹件热膨胀系数 α_parts（自动计算）",
                "1/K",
                "由材料选择自动填入。自定义模式可手动输入。",
                mapping=("operating", "alpha_parts"),
                default="11.5e-6",
                help_ref="terms/bolt_thermal_loss",
            ),
            FieldSpec(
                "operating.temp_bolt",
                "螺栓温度",
                "°C",
                "用于热损失估算。若已知等效热损失可直接在下方输入。",
                mapping=("operating", "temp_bolt"),
                default="20",
                help_ref="terms/bolt_thermal_loss",
            ),
            FieldSpec(
                "operating.temp_parts",
                "被夹件温度",
                "°C",
                "与螺栓温度共同影响热预紧力损失。",
                mapping=("operating", "temp_parts"),
                default="20",
                help_ref="terms/bolt_thermal_loss",
            ),
        ],
    },
    {
        "id": "introduction",
        "title": "载荷导入",
        "subtitle": "决定外力从哪进入连接（n 越小螺栓分担越少）并设定服役屈服安全系数 S_F。",
        "help_ref": "modules/bolt_vdi/_section_introduction",
        "fields": [
            FieldSpec(
                "stiffness.load_introduction_factor_n",
                "载荷导入系数 n",
                "-",
                "修正外载导入比例。轴向端部导入通常取 1。",
                mapping=("stiffness", "load_introduction_factor_n"),
                default="1.0",
                help_ref="terms/bolt_load_intro_factor",
            ),
            FieldSpec(
                "introduction.position",
                "载荷导入位置",
                "-",
                "用于记录载荷导入方式。",
                widget_type="choice",
                options=("螺栓头端", "螺母端", "中间", "分布式"),
                default="螺栓头端",
                help_ref="terms/bolt_load_intro_factor",
            ),
            FieldSpec(
                "checks.yield_safety_operating",
                "服役屈服安全系数 S_F",
                "-",
                "服役轴向应力允许值：Rp0.2 / S_F。",
                mapping=("checks", "yield_safety_operating"),
                default="1.1",
                help_ref="terms/bolt_yield_safety",
            ),
            FieldSpec(
                "introduction.eccentric_clamp",
                "夹紧偏心 e_clamp",
                "mm",
                "偏心弯矩校核尚未启用，仅记录。",
                default="0",
                disabled=True,
                help_ref="terms/bolt_eccentric_clamp",
            ),
            FieldSpec(
                "introduction.eccentric_load",
                "载荷偏心 e_load",
                "mm",
                "偏心弯矩校核尚未启用，仅记录。",
                default="0",
                disabled=True,
                help_ref="terms/bolt_eccentric_load",
            ),
        ],
    },
    {
        "id": "thread_strip",
        "title": "螺纹脱扣校核",
        "subtitle": "检查螺纹是否会在最大预紧力下被剪断（滑牙），尤其关键于铝 / 铸铁基体或浅孔螺纹。",
        "help_ref": "modules/bolt_vdi/_section_thread_strip",
        "fields": [
            FieldSpec(
                "thread_strip.m_eff",
                "有效旋合深度 m_eff",
                "mm",
                "螺栓实际旋入螺母或螺纹孔的有效螺纹长度。"
                "标准螺母高度约 0.8d~1.0d；螺纹孔连接需实测。"
                "留空则跳过脱扣校核。",
                mapping=("thread_strip", "m_eff"),
                help_ref="terms/bolt_thread_engagement",
            ),
            FieldSpec(
                "thread_strip.tau_BM",
                "内螺纹剪切强度",
                "MPa",
                "螺母或壳体材料的剪切强度。"
                "钢螺母一般可取 Rp0.2 x 0.6；"
                "铝合金壳体约 150~200 MPa；铸铁约 200~250 MPa。",
                mapping=("thread_strip", "tau_BM"),
                help_ref="terms/bolt_thread_strip_tau",
            ),
            FieldSpec(
                "thread_strip.tau_BS",
                "外螺纹剪切强度",
                "MPa",
                "螺栓材料的剪切强度。留空时自动取 Rp0.2 x 0.6。",
                mapping=("thread_strip", "tau_BS"),
                help_ref="terms/bolt_thread_strip_tau",
            ),
            FieldSpec(
                "thread_strip.safety_required",
                "脱扣安全系数要求",
                "-",
                "最小脱扣安全系数，通常取 1.25。",
                mapping=("thread_strip", "safety_required"),
                default="1.25",
                help_ref="terms/bolt_strip_safety_required",
            ),
        ],
    },
]


CHECK_LABELS = {
    "assembly_von_mises_ok": "装配等效应力校核（VDI R4）",
    "operating_axial_ok": "服役轴向应力校核（VDI R5）",
    "residual_clamp_ok": "残余夹紧力校核（VDI R3）",
    "additional_load_ok": "附加载荷能力估算 ⚠ 参考",
    "thermal_loss_ok": "温度损失影响校核",
    "fatigue_ok": "疲劳校核（简化 Goodman）",
    "bearing_pressure_ok": "支承面压强校核（R7）",
    "thread_strip_ok": "螺纹脱扣校核",
}

_OVERALL_STATUS_TEXT = {
    "pass": "通过",
    "fail": "不通过",
    "incomplete": "不完整（存在未校核项，见警告）",
}

CHECK_LEVELS: tuple[tuple[str, str], ...] = (
    ("常规校核", "basic"),
    ("考虑温度", "thermal"),
    ("考虑温度+疲劳", "fatigue"),
)

THERMAL_FIELD_IDS: set[str] = {
    "operating.bolt_material",
    "operating.alpha_bolt",
    "operating.clamped_material",
    "operating.alpha_parts",
    "operating.temp_bolt",
    "operating.temp_parts",
    "loads.thermal_force_loss",
}
FATIGUE_FIELD_IDS: set[str] = {
    "operating.load_cycles",
    "options.surface_treatment",
}

SURFACE_TREATMENT_MAP: dict[str, str] = {
    "轧制": "rolled",
    "切削": "cut",
}
VERIFY_MODE_FIELD_IDS: set[str] = {"loads.FM_min_input"}
CUSTOM_THREAD_FIELD_IDS: set[str] = {"fastener.d_custom", "fastener.p_custom"}
# 手动柔度/刚度字段：自动计算模式下隐藏
MANUAL_COMPLIANCE_FIELD_IDS: set[str] = {
    "stiffness.bolt_compliance", "stiffness.clamped_compliance",
    "stiffness.bolt_stiffness", "stiffness.clamped_stiffness",
}
# 由 _on_part_count_changed 控制可见性的字段
LAYER_CONTROLLED_FIELD_IDS: set[str] = {
    "clamped.custom_count",
    *(fid for layer in LAYER_FIELD_IDS for fid in layer),
}
BEARING_MATERIAL_PRESETS: dict[str, str] = {"钢": "700", "铝合金": "300"}
JOINT_TYPE_MAP: dict[str, str] = {
    "螺纹孔连接": "tapped",
    "通孔螺栓连接": "through",
}

THERMAL_EXPANSION_PRESETS: dict[str, str] = {
    "钢": "11.5e-6",
    "不锈钢": "16.0e-6",
    "铝合金": "23.0e-6",
    "铸铁": "10.5e-6",
}

SURFACE_CLASS_MAP: dict[str, str] = {
    "粗糙 (Ra≈6.3μm)": "rough",
    "中等 (Ra≈3.2μm)": "medium",
    "精细 (Ra≈1.6μm)": "fine",
}

TIGHTENING_METHOD_MAP: dict[str, str] = {
    "扭矩法": "torque",
    "转角法": "angle",
    "液压拉伸法": "hydraulic",
    "热装法": "thermal",
}

BASIC_SOLID_MAP: dict[str, str] = {
    "圆柱体": "cylinder",
    "锥体": "cone",
    "套筒": "sleeve",
}

CALC_MODES: tuple[tuple[str, str], ...] = (
    ("设计模式（反推 FM_min）", "design"),
    ("校核模式（输入已知 FM_min）", "verify"),
)

SETUP_CASE_RULES: dict[str, dict[str, Any]] = {
    "轴向载荷": {
        "show": {"loads.FA_max", "loads.seal_force_required"},
        "force_zero": {"FQ_max": 0.0},
        "drop": {"friction_interfaces", "slip_friction_coefficient"},
    },
    "横向载荷": {
        "show": {
            "loads.FQ_max",
            "loads.seal_force_required",
            "loads.friction_interfaces",
            "loads.slip_mu_mode",
        },
        "force_zero": {"FA_max": 0.0},
        "drop": set(),
    },
    "轴向+横向": {
        "show": {
            "loads.FA_max",
            "loads.FQ_max",
            "loads.seal_force_required",
            "loads.friction_interfaces",
            "loads.slip_mu_mode",
        },
        "force_zero": {},
        "drop": set(),
    },
    "自由输入": {
        "show": {
            "loads.FA_max",
            "loads.FQ_max",
            "loads.seal_force_required",
            "loads.friction_interfaces",
            "loads.slip_mu_mode",
        },
        "force_zero": {},
        "drop": set(),
    },
}


class BoltPage(QWidget):
    """VDI 2230 bolt page with chapter navigation and readable results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._field_widgets: dict[str, QWidget] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._widget_hints: dict[QWidget, str] = {}
        self._check_badges: dict[str, QLabel] = {}
        self._check_name_labels: dict[str, QLabel] = {}
        self._chapter_step_index = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        header = QFrame(self)
        header.setObjectName("Card")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(2)
        title = QLabel("螺栓连接 · VDI 2230", header)
        title.setObjectName("SectionTitle")
        hint = QLabel("预紧螺栓连接的预紧力、工作载荷、疲劳与滑移校核。", header)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        actions = QFrame(self)
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        left_actions = QHBoxLayout()
        left_actions.setContentsMargins(0, 0, 0, 0)
        left_actions.setSpacing(8)
        right_actions = QHBoxLayout()
        right_actions.setContentsMargins(0, 0, 0, 0)
        right_actions.setSpacing(8)
        self.btn_save_inputs = QPushButton("保存输入条件", actions)
        self.btn_load_inputs = QPushButton("加载输入条件", actions)
        self.btn_calculate = QPushButton("执行校核", actions)
        self.btn_calculate.setObjectName("PrimaryButton")
        self.btn_clear = QPushButton("清空参数", actions)
        self.btn_save = QPushButton("导出结果说明", actions)
        self.btn_load_1 = QPushButton("测试案例 1", actions)
        self.btn_load_2 = QPushButton("测试案例 2", actions)
        self.check_level_combo = QComboBox(self)
        for text, value in CHECK_LEVELS:
            self.check_level_combo.addItem(text, value)
        left_actions.addWidget(self.btn_save_inputs)
        left_actions.addWidget(self.btn_load_inputs)
        left_actions.addWidget(self.btn_calculate)
        left_actions.addWidget(self.btn_clear)
        left_actions.addWidget(self.btn_save)
        self.btn_help_guide = QPushButton("校核指南", actions)
        right_actions.addWidget(self.btn_help_guide)
        right_actions.addWidget(self.btn_load_1)
        right_actions.addWidget(self.btn_load_2)
        actions_layout.addLayout(left_actions)
        actions_layout.addStretch(1)
        actions_layout.addLayout(right_actions)
        root.addWidget(actions)

        content = QHBoxLayout()
        content.setSpacing(12)
        root.addLayout(content, 1)

        nav_card = QFrame(self)
        nav_card.setObjectName("Card")
        nav_card.setMinimumWidth(220)
        nav_card.setMaximumWidth(320)
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(8)
        nav_title = QLabel("章节导航", nav_card)
        nav_title.setObjectName("SectionTitle")
        self.chapter_list = QListWidget(nav_card)
        self.chapter_list.setObjectName("ChapterList")
        nav_layout.addWidget(nav_title)

        # Tab buttons
        tab_bar = QHBoxLayout()
        self.btn_input_tab = QPushButton("输入步骤", nav_card)
        self.btn_input_tab.setObjectName("PrimaryButton")
        self.btn_flow_tab = QPushButton("校核链路", nav_card)
        tab_bar.addWidget(self.btn_input_tab)
        tab_bar.addWidget(self.btn_flow_tab)
        nav_layout.addLayout(tab_bar)

        # Navigation stack
        self.nav_stack = QStackedWidget(nav_card)
        self.nav_stack.addWidget(self.chapter_list)  # page 0
        self.flowchart_nav = FlowchartNavWidget(nav_card)
        self.nav_stack.addWidget(self.flowchart_nav)  # page 1
        nav_layout.addWidget(self.nav_stack, 1)

        content.addWidget(nav_card, 0)

        self.chapter_stack = QStackedWidget(self)
        content.addWidget(self.chapter_stack, 1)

        self._build_chapter_pages()
        self._build_diagram_page()
        self._build_results_page()

        self._r_pages: list[RStepDetailPage] = []
        self._r_page_start_index = self.chapter_stack.count()
        for step in R_STEPS:
            r_page = RStepDetailPage(step, self)
            self.chapter_stack.addWidget(r_page)
            self._r_pages.append(r_page)

        footer = QFrame(self)
        footer.setObjectName("Card")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        footer_layout.setSpacing(6)
        self.overall_badge = QLabel("等待计算", footer)
        self.overall_badge.setObjectName("WaitBadge")
        self.info_label = QLabel("选择左侧章节填写参数；聚焦任意字段可查看参数说明和新手提示。", footer)
        self.info_label.setObjectName("SectionHint")
        self.info_label.setWordWrap(True)
        footer_layout.addWidget(self.overall_badge, 0, Qt.AlignmentFlag.AlignLeft)
        footer_layout.addWidget(self.info_label)
        root.addWidget(footer)

        self.chapter_list.currentRowChanged.connect(self.chapter_stack.setCurrentIndex)
        self.chapter_list.setCurrentRow(0)

        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("input_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("input_case_02.json"))
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save.clicked.connect(self._save_report)
        self.btn_help_guide.clicked.connect(self._show_logic_guide)
        self.check_level_combo.currentIndexChanged.connect(self._apply_check_level_visibility)
        self.calc_mode_combo.currentIndexChanged.connect(self._apply_calculation_mode_visibility)
        self.btn_input_tab.clicked.connect(lambda: self._switch_nav_tab(0))
        self.btn_flow_tab.clicked.connect(lambda: self._switch_nav_tab(1))
        self.flowchart_nav.node_clicked.connect(self._on_flow_node_clicked)

        self._wire_combo("bearing.bearing_material", self._on_bearing_material_changed)
        # 强度等级联动
        self._wire_combo("fastener.grade", self._on_grade_changed)
        # 材料热膨胀联动
        self._wire_combo("operating.bolt_material", self._on_bolt_material_changed)
        self._wire_combo("operating.clamped_material", self._on_clamped_material_changed)
        # 被夹件数量联动
        self._wire_combo("clamped.part_count", self._on_part_count_changed)
        cc_widget = self._field_widgets.get("clamped.custom_count")
        if cc_widget and isinstance(cc_widget, QLineEdit):
            cc_widget.textChanged.connect(lambda _: self._on_part_count_changed())
        # 各层材料需要捕获层号，保留 lambda 个例。
        for ln in range(1, 6):
            mat_w = self._field_widgets.get(f"clamped.layer_{ln}.material")
            if mat_w and isinstance(mat_w, QComboBox):
                mat_w.currentTextChanged.connect(
                    lambda text, n=ln: self._on_layer_material_changed(n, text)
                )
                self._on_layer_material_changed(ln, mat_w.currentText())
        # 柔度计算方式联动
        self._wire_combo("stiffness.auto_compliance", self._on_compliance_mode_changed)
        # 初始化可见性
        self._wire_combo("operating.setup_case", self._on_setup_case_changed)
        self._wire_combo("loads.slip_mu_mode", self._on_slip_mu_mode_changed)
        # 拧紧方式联动 αA hint
        self._wire_combo("assembly.tightening_method", self._on_tightening_method_changed)
        # 载荷导入位置联动 n hint
        self._wire_combo("introduction.position", self._on_position_changed)
        # 螺纹规格联动
        self._wire_combo("fastener.d", self._on_thread_d_changed)
        self._wire_combo("fastener.p", self._on_thread_p_changed)
        self._wire_combo("elements.joint_type", self._sync_joint_diagram_from_ui)

        self._apply_defaults()
        self._load_sample("input_case_01.json")
        self._apply_check_level_visibility()
        self._connect_dirty_signals()
        self._mark_results_dirty()

    def eventFilter(self, watched, event):  # noqa: N802
        if watched in self._widget_hints and event.type() in (QEvent.Type.FocusIn, QEvent.Type.Enter):
            self.info_label.setText(self._widget_hints[watched])
        return super().eventFilter(watched, event)

    def _wire_combo(
        self,
        field_id: str,
        handler: Callable[[str], None],
    ) -> QComboBox | None:
        """Connect a field combo to a text handler and apply the initial state.

        注意：这里在 connect 之后立即 `handler(widget.currentText())` 触发一次，
        使各联动字段（材料自动填充、锁定态等）在页面构建阶段即进入正确初值。
        该初值随后会被 __init__ 末尾的 `_load_sample` 最终覆盖为样例数据；
        若调整 __init__ 中 _wire_combo 与 _load_sample 的先后顺序，须复核这一
        "构建期初值 -> 样例覆盖" 的依赖，避免联动字段停留在未覆盖的中间态。
        """
        widget = self._field_widgets.get(field_id)
        if not isinstance(widget, QComboBox):
            return None
        widget.currentTextChanged.connect(handler)
        handler(widget.currentText())
        return widget

    def _build_chapter_pages(self) -> None:
        self._add_step_item("校核层级设置")
        self.chapter_stack.addWidget(self._create_level_page())

        for chapter in CHAPTERS:
            self._add_step_item(chapter["title"])
            page = self._create_chapter_page(
                chapter["title"],
                chapter["subtitle"],
                chapter["fields"],
                help_ref=chapter.get("help_ref", ""),
            )
            if chapter["id"] == "assembly":
                self._append_assembly_guide(page)
            self.chapter_stack.addWidget(page)

    def _add_step_item(self, title: str) -> None:
        self._chapter_step_index += 1
        self.chapter_list.addItem(QListWidgetItem(f"步骤 {self._chapter_step_index}. {title}"))

    def _create_level_page(self) -> QWidget:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("校核层级设置", page)
        title.setObjectName("SectionTitle")
        hint = QLabel("先选择校核层级，再填写参数。不同层级会显示不同输入项。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        control_card = QFrame(page)
        control_card.setObjectName("SubCard")
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(10)
        label = QLabel("当前层级", control_card)
        label.setObjectName("SubSectionTitle")
        control_layout.addWidget(label)
        control_layout.addWidget(self.check_level_combo, 1)
        layout.addWidget(control_card)

        desc_card = QFrame(page)
        desc_card.setObjectName("SubCard")
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setContentsMargins(12, 10, 12, 10)
        desc_layout.setSpacing(6)
        desc_title = QLabel("层级差异与新增参数位置", desc_card)
        desc_title.setObjectName("SubSectionTitle")
        self.level_desc_label = QLabel(desc_card)
        self.level_desc_label.setObjectName("SectionHint")
        self.level_desc_label.setWordWrap(True)
        desc_layout.addWidget(desc_title)
        desc_layout.addWidget(self.level_desc_label)
        layout.addWidget(desc_card)

        # ---- 计算模式 ----
        mode_card = QFrame(page)
        mode_card.setObjectName("SubCard")
        mode_layout_inner = QVBoxLayout(mode_card)
        mode_layout_inner.setContentsMargins(12, 10, 12, 10)
        mode_title = QLabel("计算模式", mode_card)
        mode_title.setObjectName("SubSectionTitle")
        mode_layout_inner.addWidget(mode_title)
        self.calc_mode_combo = QComboBox(mode_card)
        self.calc_mode_combo.addItem("设计模式 — 由 FK_req 反推 FM_min", "design")
        self.calc_mode_combo.addItem("校核模式 — 使用已知 FM_min", "verify")
        mode_layout_inner.addWidget(self.calc_mode_combo)
        self.mode_desc_label = QLabel(
            "设计模式：由 FK_req 反推 FM_min，R3 自动满足。\n\n"
            "FK_req（所需夹紧力）：为保证密封、防滑等功能，螺栓连接在工作状态下至少需要维持的夹紧力。\n"
            "FM_min（最小装配预紧力）：拧紧时螺栓实际需要施加的最小预紧力，考虑了工作载荷、嵌入松弛、热膨胀等损失后，仍能满足 FK_req。",
            mode_card,
        )
        self.mode_desc_label.setObjectName("SectionHint")
        self.mode_desc_label.setWordWrap(True)
        mode_layout_inner.addWidget(self.mode_desc_label)
        layout.addWidget(mode_card)
        layout.addStretch(1)
        return page

    def _create_chapter_page(
        self,
        title: str,
        subtitle: str,
        fields: list[FieldSpec],
        help_ref: str = "",
    ) -> QWidget:
        page = QFrame(self)
        page.setObjectName("Card")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(14, 12, 14, 12)
        page_layout.setSpacing(10)

        title_label = QLabel(title, page)
        title_label.setObjectName("SectionTitle")
        if help_ref:
            # 章节标题 + HelpButton 同行布局
            header_row = QWidget(page)
            header_layout = QHBoxLayout(header_row)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(6)
            header_layout.addWidget(title_label)
            header_layout.addWidget(HelpButton(help_ref, parent=header_row), 0, Qt.AlignmentFlag.AlignVCenter)
            header_layout.addStretch(1)
            page_layout.addWidget(header_row)
        else:
            page_layout.addWidget(title_label)
        subtitle_label = QLabel(subtitle, page)
        subtitle_label.setObjectName("SectionHint")
        subtitle_label.setWordWrap(True)
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
            if spec.disabled:
                field_card.setObjectName("DisabledSubCard")
            elif spec.field_id in self._AUTO_FILLED_FIELDS:
                field_card.setObjectName("AutoCalcCard")
            else:
                field_card.setObjectName("SubCard")
            row = QGridLayout(field_card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setHorizontalSpacing(10)
            row.setVerticalSpacing(4)

            editor = self._create_editor(spec, field_card)
            unit = QLabel(spec.unit, field_card)
            unit.setObjectName("UnitLabel")
            hint = QLabel(spec.hint, field_card)
            hint.setObjectName("SectionHint")
            hint.setWordWrap(True)

            # 字段级 help_ref 存在时，把 label 与 HelpButton 包成一个水平布局放在 col 0
            if spec.help_ref:
                label_widget = QWidget(field_card)
                label_layout = QHBoxLayout(label_widget)
                label_layout.setContentsMargins(0, 0, 0, 0)
                label_layout.setSpacing(4)
                label_text = QLabel(spec.label, label_widget)
                label_text.setObjectName("SubSectionTitle")
                label_layout.addWidget(label_text)
                label_layout.addWidget(
                    HelpButton(spec.help_ref, parent=label_widget),
                    0,
                    Qt.AlignmentFlag.AlignVCenter,
                )
                label_layout.addStretch(1)
                label: QWidget = label_widget
            else:
                label = QLabel(spec.label, field_card)
                label.setObjectName("SubSectionTitle")

            if spec.disabled:
                badge = QLabel("暂未启用", field_card)
                badge.setObjectName("WaitBadge")
                row.addWidget(label, 0, 0)
                row.addWidget(badge, 0, 1, Qt.AlignmentFlag.AlignLeft)
                row.addWidget(editor, 0, 2)
                row.addWidget(unit, 0, 3)
                row.addWidget(hint, 1, 0, 1, 4)
                if isinstance(editor, QLineEdit):
                    editor.setReadOnly(True)
            else:
                row.addWidget(label, 0, 0)
                row.addWidget(editor, 0, 1)
                row.addWidget(unit, 0, 2)
                row.addWidget(hint, 1, 0, 1, 3)
            form_layout.addWidget(field_card)
            self._field_cards[spec.field_id] = field_card

        form_layout.addStretch(1)
        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)
        return page

    def _append_assembly_guide(self, page: QWidget) -> None:
        """在装配属性章节末尾添加新手说明面板。"""
        scroll = page.findChild(QScrollArea)
        if scroll is None:
            return
        container = scroll.widget()
        if container is None:
            return
        form_layout = container.layout()
        if form_layout is None:
            return
        # 移除末尾 stretch 以便插入说明卡片
        last = form_layout.itemAt(form_layout.count() - 1)
        if last and last.spacerItem():
            form_layout.removeItem(last)

        guide_card = QFrame(container)
        guide_card.setObjectName("SubCard")
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(12, 10, 12, 10)
        guide_layout.setSpacing(6)

        toggle_btn = QPushButton(bolt_help.ASSEMBLY_GUIDE_COLLAPSED_TITLE, guide_card)
        toggle_btn.setObjectName("LinkButton")
        toggle_btn.setFlat(True)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        guide_layout.addWidget(toggle_btn)

        guide_text = QLabel(guide_card)
        guide_text.setObjectName("SectionHint")
        guide_text.setWordWrap(True)
        guide_text.setText(bolt_help.ASSEMBLY_GUIDE_TEXT)
        guide_layout.addWidget(guide_text)
        guide_text.setVisible(False)

        def _toggle():
            visible = not guide_text.isVisible()
            guide_text.setVisible(visible)
            toggle_btn.setText(
                bolt_help.ASSEMBLY_GUIDE_EXPANDED_TITLE
                if visible
                else bolt_help.ASSEMBLY_GUIDE_COLLAPSED_TITLE
            )
            guide_layout.invalidate()
            guide_card.adjustSize()
            container.adjustSize()
            container.updateGeometry()

        toggle_btn.clicked.connect(_toggle)

        form_layout.addWidget(guide_card)
        form_layout.addStretch(1)

    # ------------------------------------------------------------------
    # 校核指南对话框
    # ------------------------------------------------------------------
    def _show_logic_guide(self) -> None:
        """弹出校核逻辑链路指南，帮助新手理解输入→计算→校核的完整思路。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("VDI 2230 螺栓校核指南")
        dlg.resize(720, 780)

        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(dlg)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ---------- 标题 ----------
        title = QLabel(bolt_help.LOGIC_GUIDE_TITLE, container)
        title.setObjectName("SectionTitle")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        intro = QLabel(bolt_help.LOGIC_GUIDE_INTRO, container)
        intro.setObjectName("SectionHint")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # ---------- 辅助函数 ----------
        def _section(title_text: str, body_text: str) -> QFrame:
            card = QFrame(container)
            card.setObjectName("SubCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(6)
            t = QLabel(title_text, card)
            t.setObjectName("SubSectionTitle")
            t.setStyleSheet("font-size: 14px;")
            b = QLabel(body_text, card)
            b.setObjectName("SectionHint")
            b.setWordWrap(True)
            card_layout.addWidget(t)
            card_layout.addWidget(b)
            return card

        def _flow_arrow() -> QLabel:
            arrow = QLabel("  ▼", container)
            arrow.setStyleSheet("color: #D97757; font-size: 18px; font-weight: bold;")
            return arrow

        for index, (section_title, section_body) in enumerate(bolt_help.LOGIC_GUIDE_SECTIONS):
            if index > 0 and index < len(bolt_help.LOGIC_GUIDE_SECTIONS) - 1:
                layout.addWidget(_flow_arrow())
            layout.addWidget(_section(section_title, section_body))

        layout.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll)

        close_btn = QPushButton("我明白了", dlg)
        close_btn.setObjectName("PrimaryButton")
        close_btn.clicked.connect(dlg.accept)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(24, 8, 24, 16)
        btn_layout.addStretch(1)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch(1)
        root.addLayout(btn_layout)

        dlg.exec()

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
        newbie = bolt_help.BEGINNER_GUIDES.get(spec.field_id, bolt_help.DEFAULT_BEGINNER_GUIDE)
        return f"{spec.label}{unit_part}\n参数说明：{spec.hint}\n新手提示：{newbie}"

    def _set_dynamic_field_help(self, field_id: str, extra_hint: str = "") -> None:
        widget = self._field_widgets.get(field_id)
        spec = self._field_specs.get(field_id)
        if widget is None or spec is None:
            return
        help_text = self._build_field_help(spec)
        if extra_hint:
            help_text = f"{help_text}\n当前建议：{extra_hint}"
        widget.setToolTip(help_text)  # type: ignore[attr-defined]
        self._widget_hints[widget] = help_text
        if widget.hasFocus():
            self.info_label.setText(help_text)

    def _apply_recommended_line_value(self, field_id: str, recommended: str) -> None:
        widget = self._field_widgets.get(field_id)
        if not isinstance(widget, QLineEdit):
            return

        def _same_value(left: str, right: str) -> bool:
            if left == right:
                return True
            try:
                return float(left) == float(right)
            except (TypeError, ValueError):
                return False

        current = widget.text().strip()
        last_auto = str(widget.property("auto_recommended_value") or "").strip()
        should_apply = (
            not current
            or _same_value(current, recommended)
            or (last_auto and _same_value(current, last_auto))
        )
        if should_apply and current != recommended:
            widget.setText(recommended)
        widget.setProperty("auto_recommended_value", recommended)

    def _current_check_level(self) -> str:
        level = self.check_level_combo.currentData()
        return str(level) if level else "basic"

    def _set_check_level(self, level: str) -> None:
        for index in range(self.check_level_combo.count()):
            if self.check_level_combo.itemData(index) == level:
                self.check_level_combo.setCurrentIndex(index)
                return

    def _build_level_desc_text(self, level: str) -> str:
        if level == "basic":
            return (
                "常规校核：覆盖 R3/R4/R5 + 附加载荷估算。\n"
                "隐藏参数：\n"
                "• 工况数据：螺栓温度、被夹件温度、载荷循环次数 ND\n"
                "• 装配属性：热损失 Fth"
            )
        if level == "thermal":
            return (
                "考虑温度：在常规校核上增加温度损失影响。\n"
                "新增参数位置：\n"
                "• 工况数据：螺栓温度、被夹件温度\n"
                "• 装配属性：热损失 Fth\n"
                "隐藏参数：载荷循环次数 ND"
            )
        return (
            "考虑温度+疲劳：在温度层级上增加疲劳简化 Goodman 校核。\n"
            "新增参数位置：\n"
            "• 工况数据：载荷循环次数 ND\n"
            "• 工况数据：螺栓温度、被夹件温度\n"
            "• 装配属性：热损失 Fth"
        )

    def _apply_check_level_visibility(self, *_args) -> None:
        level = self._current_check_level()
        show_thermal = level in ("thermal", "fatigue")
        show_fatigue = level == "fatigue"

        for field_id, card in self._field_cards.items():
            if field_id in THERMAL_FIELD_IDS:
                card.setVisible(show_thermal)
            elif field_id in FATIGUE_FIELD_IDS:
                card.setVisible(show_fatigue)
            elif field_id in VERIFY_MODE_FIELD_IDS:
                pass  # controlled by _apply_calculation_mode_visibility
            elif field_id in CUSTOM_THREAD_FIELD_IDS:
                pass  # controlled by _on_thread_d_changed
            elif field_id in LAYER_CONTROLLED_FIELD_IDS:
                pass  # controlled by _on_part_count_changed
            elif field_id in MANUAL_COMPLIANCE_FIELD_IDS:
                pass  # controlled by _on_compliance_mode_changed
            else:
                card.setVisible(True)

        for key, label in self._check_name_labels.items():
            if key == "thermal_loss_ok":
                visible = show_thermal
            elif key == "fatigue_ok":
                visible = show_fatigue
            else:
                visible = True
            label.setVisible(visible)
            if key in self._check_badges:
                self._check_badges[key].setVisible(visible)

        if show_fatigue:
            level_hint = "当前层级：考虑温度+疲劳。已显示温度与疲劳相关输入。"
        elif show_thermal:
            level_hint = "当前层级：考虑温度。已显示温度相关输入。"
        else:
            level_hint = "当前层级：常规校核。已隐藏温度/疲劳相关输入。"
        self.info_label.setText(level_hint)
        if hasattr(self, "level_desc_label"):
            self.level_desc_label.setText(self._build_level_desc_text(level))
        self._apply_calculation_mode_visibility()
        self._on_part_count_changed()
        setup_case_widget = self._field_widgets.get("operating.setup_case")
        if isinstance(setup_case_widget, QComboBox):
            self._on_setup_case_changed(setup_case_widget.currentText())
        if hasattr(self, "flowchart_nav"):
            self.flowchart_nav.set_r6_visible(show_fatigue)

    def _apply_calculation_mode_visibility(self, *_args) -> None:
        mode = self.calc_mode_combo.currentData() or "design"
        show_verify = mode == "verify"
        for field_id, card in self._field_cards.items():
            if field_id in VERIFY_MODE_FIELD_IDS:
                card.setVisible(show_verify)
        if mode == "verify":
            self.mode_desc_label.setText(
                "校核模式：跳过 FM_min 反推，直接用已知预紧力做校核。\n"
                "请在「步骤 3. 装配属性」中填写已知 FM,min 值。\n\n"
                "FK_req（所需夹紧力）：为保证密封、防滑等功能，螺栓连接在工作状态下至少需要维持的夹紧力。\n"
                "FM_min（最小装配预紧力）：拧紧时螺栓实际需要施加的最小预紧力，考虑了工作载荷、嵌入松弛、热膨胀等损失后，仍能满足 FK_req。"
            )
        else:
            self.mode_desc_label.setText(
                "设计模式：由 FK_req 反推 FM_min，R3 自动满足。\n\n"
                "FK_req（所需夹紧力）：为保证密封、防滑等功能，螺栓连接在工作状态下至少需要维持的夹紧力。\n"
                "FM_min（最小装配预紧力）：拧紧时螺栓实际需要施加的最小预紧力，考虑了工作载荷、嵌入松弛、热膨胀等损失后，仍能满足 FK_req。"
            )

    def _on_bearing_material_changed(self, text: str) -> None:
        preset = BEARING_MATERIAL_PRESETS.get(text)
        editor = self._field_widgets.get("bearing.p_G_allow")
        if editor and isinstance(editor, QLineEdit):
            if preset:
                editor.setText(preset)
            else:
                editor.clear()
                editor.setFocus()

    def _on_grade_changed(self, text: str) -> None:
        """强度等级下拉变更时自动填入 Rp0.2。"""
        rp02_w = self._field_widgets.get("fastener.Rp02")
        if not (rp02_w and isinstance(rp02_w, QLineEdit)):
            return
        preset = BOLT_GRADE_TABLE.get(text)
        if preset is not None:
            rp02_w.setText(str(int(preset)))
            rp02_w.setReadOnly(True)
        else:
            rp02_w.setReadOnly(False)
            rp02_w.clear()
            rp02_w.setFocus()

    def _apply_material_presets(self, text: str, alpha_field_id: str, e_field_id: str) -> None:
        alpha_w = self._field_widgets.get(alpha_field_id)
        e_w = self._field_widgets.get(e_field_id)
        alpha_preset = THERMAL_EXPANSION_PRESETS.get(text)
        e_preset = ELASTIC_MODULUS_PRESETS.get(text)

        if alpha_w and isinstance(alpha_w, QLineEdit):
            if alpha_preset is not None:
                alpha_w.setText(alpha_preset)
                alpha_w.setReadOnly(True)
            else:
                alpha_w.setReadOnly(False)
                alpha_w.clear()
                alpha_w.setFocus()

        if e_w and isinstance(e_w, QLineEdit):
            if e_preset is not None:
                e_w.setText(e_preset)

    def _on_bolt_material_changed(self, text: str) -> None:
        """螺栓材料下拉变更时自动填入热膨胀系数。"""
        self._apply_material_presets(text, "operating.alpha_bolt", "stiffness.E_bolt")

    def _on_clamped_material_changed(self, text: str) -> None:
        """被夹件材料下拉变更时自动填入热膨胀系数。"""
        self._apply_material_presets(text, "operating.alpha_parts", "stiffness.E_clamped")

    # -- 单层字段 ID（多层模式时隐藏）--
    _SINGLE_LAYER_FIELDS: set[str] = {
        "clamped.basic_solid", "clamped.total_thickness", "clamped.D_A",
        "stiffness.E_clamped",
    }
    # -- 单层热材料字段 --
    _SINGLE_THERMAL_FIELDS: set[str] = {
        "operating.clamped_material", "operating.alpha_parts",
    }

    def _get_effective_part_count(self) -> int:
        """从 UI 控件读取有效被夹件数量。"""
        pc_w = self._field_widgets.get("clamped.part_count")
        if not (pc_w and isinstance(pc_w, QComboBox)):
            return 1
        text = pc_w.currentText()
        if text == "1":
            return 1
        if text == "2":
            return 2
        # "自定义"
        cc_w = self._field_widgets.get("clamped.custom_count")
        if cc_w and isinstance(cc_w, QLineEdit):
            try:
                v = int(float(cc_w.text().strip()))
                return max(3, min(v, 5))
            except (ValueError, TypeError):
                return 3
        return 3

    def _on_part_count_changed(self, _text: str = "") -> None:
        """被夹件数量变更时切换单层/多层字段可见性。

        使用 self._field_cards[fid] 获取字段卡片控件（而非 w.parent()），
        这是本代码库中控制字段可见性的标准模式，见 _on_thread_d_changed。
        """
        count = self._get_effective_part_count()
        is_multi = count >= 2

        # 单层柔度字段
        for fid in self._SINGLE_LAYER_FIELDS:
            card = self._field_cards.get(fid)
            if card is not None:
                card.setVisible(not is_multi)

        # 单层热材料字段：需同时尊重 check_level（basic 级别下始终隐藏）
        level = self._current_check_level()
        show_thermal = level in ("thermal", "fatigue")
        for fid in self._SINGLE_THERMAL_FIELDS:
            card = self._field_cards.get(fid)
            if card is not None:
                card.setVisible(show_thermal and not is_multi)

        # custom_count 仅在"自定义"时显示
        pc_w = self._field_widgets.get("clamped.part_count")
        is_custom = pc_w and isinstance(pc_w, QComboBox) and pc_w.currentText() == "自定义"
        cc_card = self._field_cards.get("clamped.custom_count")
        if cc_card is not None:
            cc_card.setVisible(bool(is_custom))

        # 各层字段
        for layer_idx in range(5):
            visible = is_multi and layer_idx < count
            for fid in LAYER_FIELD_IDS[layer_idx]:
                card = self._field_cards.get(fid)
                if card is not None:
                    card.setVisible(visible)

    def _on_layer_material_changed(self, layer_n: int, text: str) -> None:
        """第 N 层材料变更时自动填入对应热膨胀系数。"""
        self._apply_material_presets(
            text,
            f"clamped.layer_{layer_n}.alpha",
            f"clamped.layer_{layer_n}.E",
        )

    def _on_compliance_mode_changed(self, _text: str = "") -> None:
        """柔度计算方式变更时切换手动输入字段可见性。"""
        ac_w = self._field_widgets.get("stiffness.auto_compliance")
        is_auto = (
            isinstance(ac_w, QComboBox) and ac_w.currentText() == "自动计算"
        )
        for fid in MANUAL_COMPLIANCE_FIELD_IDS:
            card = self._field_cards.get(fid)
            if card is not None:
                card.setVisible(not is_auto)

    def _on_setup_case_changed(self, text: str) -> None:
        """工况类型变更时切换轴向/横向字段可见性。"""
        rules = SETUP_CASE_RULES.get(text, SETUP_CASE_RULES["自由输入"])
        visible_fields = rules["show"]
        managed_fields = {
            "loads.FA_max",
            "loads.FQ_max",
            "loads.seal_force_required",
            "loads.friction_interfaces",
            "loads.slip_mu_mode",
            "loads.slip_friction_coefficient",
        }
        for field_id in managed_fields:
            card = self._field_cards.get(field_id)
            if card is not None:
                card.setVisible(field_id in visible_fields)
        self._on_slip_mu_mode_changed()

    def _on_slip_mu_mode_changed(self, _text: str = "") -> None:
        """根据 μT 来源模式与工况类型切换 μT 输入框可见性。"""
        mode_widget = self._field_widgets.get("loads.slip_mu_mode")
        case_widget = self._field_widgets.get("operating.setup_case")
        mu_card = self._field_cards.get("loads.slip_friction_coefficient")
        if not (
            isinstance(mode_widget, QComboBox)
            and isinstance(case_widget, QComboBox)
            and mu_card is not None
        ):
            return
        case_rules = SETUP_CASE_RULES.get(
            case_widget.currentText(),
            SETUP_CASE_RULES["自由输入"],
        )
        mode_visible = "loads.slip_mu_mode" in case_rules["show"]
        is_custom = mode_widget.currentText() == SLIP_MU_MODE_CUSTOM
        mu_card.setVisible(mode_visible and is_custom)

    def _on_tightening_method_changed(self, text: str) -> None:
        """拧紧方式变更时更新 αA 字段的 hint/tooltip。"""
        recommended = TIGHTENING_ALPHA_A_RECOMMENDATIONS.get(text)
        if recommended is not None:
            self._apply_recommended_line_value("tightening.alpha_A", recommended)
        self._set_dynamic_field_help("tightening.alpha_A", bolt_help.ALPHA_A_HINTS.get(text, ""))

    def _on_position_changed(self, text: str) -> None:
        """载荷导入位置变更时更新 n 字段的 hint/tooltip。"""
        recommended = POSITION_N_RECOMMENDATIONS.get(text)
        if recommended is not None:
            self._apply_recommended_line_value("stiffness.load_introduction_factor_n", recommended)
        self._set_dynamic_field_help(
            "stiffness.load_introduction_factor_n",
            bolt_help.N_POSITION_HINTS.get(text, ""),
        )

    def _on_thread_d_changed(self, text: str) -> None:
        """公称直径下拉变更时更新螺距选项和自定义字段可见性。"""
        is_custom = text == "自定义"
        # 自定义输入字段可见性
        for fid in CUSTOM_THREAD_FIELD_IDS:
            card = self._field_cards.get(fid)
            if card:
                card.setVisible(is_custom)
        # d2/d3/As 在标准模式下只读，自定义模式可编辑
        for fid in ("fastener.d2", "fastener.d3", "fastener.As"):
            w = self._field_widgets.get(fid)
            if w and isinstance(w, QLineEdit):
                w.setReadOnly(not is_custom)

        p_widget = self._field_widgets.get("fastener.p")
        if not (p_widget and isinstance(p_widget, QComboBox)):
            return

        p_widget.blockSignals(True)
        p_widget.clear()
        if is_custom:
            p_widget.addItem("自定义")
            # 清空自动填入值
            for fid in ("fastener.d2", "fastener.d3", "fastener.As"):
                w = self._field_widgets.get(fid)
                if w and isinstance(w, QLineEdit):
                    w.clear()
        else:
            entries = METRIC_THREAD_TABLE.get(text, [])
            for i, (p_val, _d2, _d3, _as) in enumerate(entries):
                label = f"{p_val}（粗牙）" if i == 0 else f"{p_val}（细牙）"
                p_widget.addItem(label, p_val)
            p_widget.addItem("自定义")
            if entries:
                p_widget.setCurrentIndex(0)
            bearing_preset = BEARING_GEOMETRY_PRESETS.get(text)
            if bearing_preset is not None:
                inner, outer = bearing_preset
                self._apply_recommended_line_value("bearing.bearing_d_inner", inner)
                self._apply_recommended_line_value("bearing.bearing_d_outer", outer)
        p_widget.blockSignals(False)
        self._on_thread_p_changed(p_widget.currentText())

    def _on_thread_p_changed(self, _text: str = "") -> None:
        """螺距下拉变更时自动填入 d2/d3/As。"""
        d_widget = self._field_widgets.get("fastener.d")
        p_widget = self._field_widgets.get("fastener.p")
        if not (d_widget and p_widget):
            return
        d_text = d_widget.currentText() if isinstance(d_widget, QComboBox) else ""
        is_p_custom = p_widget.currentText() == "自定义" if isinstance(p_widget, QComboBox) else True
        is_d_custom = d_text == "自定义"

        # 自定义螺距模式：显示自定义螺距输入，d2/d3/As 可编辑
        p_custom_card = self._field_cards.get("fastener.p_custom")
        if p_custom_card:
            p_custom_card.setVisible(is_p_custom and not is_d_custom)
        for fid in ("fastener.d2", "fastener.d3", "fastener.As"):
            w = self._field_widgets.get(fid)
            if w and isinstance(w, QLineEdit):
                w.setReadOnly(not (is_d_custom or is_p_custom))

        if is_d_custom or is_p_custom:
            return

        # 标准模式：从表中查找并自动填入
        p_val = p_widget.currentData() if isinstance(p_widget, QComboBox) else None
        entries = METRIC_THREAD_TABLE.get(d_text, [])
        for p_entry, d2, d3, as_val in entries:
            if p_entry == p_val:
                self._set_field("fastener.d2", f"{d2:.3f}")
                self._set_field("fastener.d3", f"{d3:.3f}")
                self._set_field("fastener.As", f"{as_val:.1f}")
                return

    def _set_field(self, field_id: str, value: str) -> None:
        w = self._field_widgets.get(field_id)
        if w and isinstance(w, QLineEdit):
            w.setText(value)

    def _switch_nav_tab(self, tab_index: int) -> None:
        self.nav_stack.setCurrentIndex(tab_index)
        if tab_index == 0:
            self.btn_input_tab.setObjectName("PrimaryButton")
            self.btn_flow_tab.setObjectName("")
            row = self.chapter_list.currentRow()
            if row >= 0:
                self.chapter_stack.setCurrentIndex(row)
        else:
            self.btn_flow_tab.setObjectName("PrimaryButton")
            self.btn_input_tab.setObjectName("")
            self._on_flow_node_clicked(self.flowchart_nav._selected_index)
        self.btn_input_tab.style().polish(self.btn_input_tab)
        self.btn_flow_tab.style().polish(self.btn_flow_tab)

    def _on_flow_node_clicked(self, r_index: int) -> None:
        self.chapter_stack.setCurrentIndex(self._r_page_start_index + r_index)

    def _build_diagram_page(self) -> None:
        self._add_step_item("连接示意图")
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        title = QLabel("连接示意图", container)
        title.setObjectName("SectionTitle")

        self.diagram_widget = ClampingDiagramWidget(container)
        self.diagram_widget.setMinimumHeight(340)
        self.diagram_help_label = QLabel(self._build_diagram_help_text("tapped"), container)
        self.diagram_help_label.setObjectName("SectionHint")
        self.diagram_help_label.setWordWrap(True)
        tri_title = QLabel("螺纹受力三角图", container)
        tri_title.setObjectName("SubSectionTitle")
        self.thread_triangle_widget = ThreadForceTriangleWidget(container)
        self.thread_triangle_widget.setMinimumHeight(240)

        content_layout.addWidget(title)
        content_layout.addWidget(self.diagram_widget, 3)
        content_layout.addWidget(self.diagram_help_label)
        content_layout.addWidget(tri_title)
        content_layout.addWidget(self.thread_triangle_widget, 2)
        content_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.chapter_stack.addWidget(page)

    def _build_diagram_help_text(self, joint_type: str) -> str:
        joint_note = bolt_help.DIAGRAM_HELP_JOINT_NOTES.get(
            joint_type,
            bolt_help.DIAGRAM_HELP_JOINT_NOTES["tapped"],
        )
        return f"{bolt_help.DIAGRAM_HELP_BASE}{joint_note}"

    def _sync_joint_diagram_from_ui(self, *_args) -> None:
        jt_widget = self._field_widgets.get("elements.joint_type")
        if not isinstance(jt_widget, QComboBox):
            joint_type = "tapped"
        else:
            joint_type = JOINT_TYPE_MAP.get(jt_widget.currentText(), "tapped")
        self.diagram_widget.set_joint_type(joint_type)
        if hasattr(self, "diagram_help_label"):
            self.diagram_help_label.setText(self._build_diagram_help_text(joint_type))

    def _build_results_page(self) -> None:
        self._add_step_item("校核结果与消息")
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        title = QLabel("校核结果与消息", container)
        title.setObjectName("SectionTitle")
        hint = QLabel("结果与分项状态。", container)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        content_layout.addWidget(title)
        content_layout.addWidget(hint)

        summary_card = QFrame(container)
        summary_card.setObjectName("SubCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)

        self.result_title = QLabel("尚未执行计算", summary_card)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel("填写参数并点击执行校核后，这里显示可读结论。", summary_card)
        self.result_summary.setObjectName("SectionHint")
        self.result_summary.setWordWrap(True)
        summary_layout.addWidget(self.result_title)
        summary_layout.addWidget(self.result_summary)
        content_layout.addWidget(summary_card)

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
            status.setObjectName("FailBadge")
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setMinimumWidth(64)
            status.setFixedHeight(24)
            checks_layout.addWidget(name, row, 0)
            checks_layout.addWidget(status, row, 1)
            self._check_badges[key] = status
            self._check_name_labels[key] = name
            row += 1
        content_layout.addWidget(checks_card)

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
        content_layout.addWidget(metrics_card)

        msg_card = QFrame(container)
        msg_card.setObjectName("SubCard")
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setContentsMargins(12, 10, 12, 10)
        msg_layout.setSpacing(6)
        msg_title = QLabel("消息与建议", msg_card)
        msg_title.setObjectName("SubSectionTitle")
        self.message_box = QPlainTextEdit(msg_card)
        self.message_box.setReadOnly(True)
        self.message_box.setMinimumHeight(200)
        msg_layout.addWidget(msg_title)
        msg_layout.addWidget(self.message_box)
        content_layout.addWidget(msg_card)
        content_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.chapter_stack.addWidget(page)

    _AUTO_FILLED_FIELDS: set[str] = {
        "fastener.d2", "fastener.d3", "fastener.As", "fastener.Rp02",
        "operating.alpha_bolt", "operating.alpha_parts",
        *(f"clamped.layer_{n}.alpha" for n in range(1, 6)),
    }

    def _apply_defaults(self) -> None:
        for spec in self._field_specs.values():
            if spec.field_id in self._AUTO_FILLED_FIELDS:
                continue  # auto-filled by thread linkage
            widget = self._field_widgets[spec.field_id]
            if spec.widget_type == "choice":
                combo = widget  # type: ignore[assignment]
                if spec.default:
                    idx = combo.findText(spec.default)  # type: ignore[attr-defined]
                    if idx >= 0:
                        combo.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(spec.default)  # type: ignore[attr-defined]
        # Re-trigger auto-fill after defaults are set
        d_w = self._field_widgets.get("fastener.d")
        if d_w and isinstance(d_w, QComboBox):
            self._on_thread_d_changed(d_w.currentText())
        g_w = self._field_widgets.get("fastener.grade")
        if g_w and isinstance(g_w, QComboBox):
            self._on_grade_changed(g_w.currentText())
        bm_w = self._field_widgets.get("operating.bolt_material")
        if bm_w and isinstance(bm_w, QComboBox):
            self._on_bolt_material_changed(bm_w.currentText())
        cm_w = self._field_widgets.get("operating.clamped_material")
        if cm_w and isinstance(cm_w, QComboBox):
            self._on_clamped_material_changed(cm_w.currentText())

    def _set_badge(self, label: QLabel, text: str, is_pass: bool) -> None:
        label.setText(text)
        label.setObjectName("PassBadge" if is_pass else "FailBadge")
        label.style().unpolish(label)
        label.style().polish(label)

    def _capture_input_snapshot(self) -> dict[str, Any]:
        snapshot = build_form_snapshot(
            self._field_specs.values(),
            self._read_widget_value,
            extra_state={
                "check_level": self._current_check_level(),
                "calculation_mode": self.calc_mode_combo.currentData() or "design",
            },
            module_id=MODULE_ID,
        )
        fastener = snapshot.setdefault("inputs", {}).setdefault("fastener", {})
        d_raw = self._resolve_thread_d()
        p_raw = self._resolve_thread_p()
        if d_raw:
            fastener["d"] = d_raw
        if p_raw:
            fastener["p"] = p_raw
        return snapshot

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        inputs_data = data.get("inputs")
        inputs = inputs_data if isinstance(inputs_data, dict) else data
        ui_state_data = data.get("ui_state")
        ui_state = ui_state_data if isinstance(ui_state_data, dict) else {}
        options_data = inputs.get("options")
        options = options_data if isinstance(options_data, dict) else {}
        fastener_data = inputs.get("fastener")
        fastener = fastener_data if isinstance(fastener_data, dict) else {}
        operating_data = inputs.get("operating")
        operating = operating_data if isinstance(operating_data, dict) else {}
        stiffness_data = inputs.get("stiffness")
        stiffness = stiffness_data if isinstance(stiffness_data, dict) else {}
        bearing_data = inputs.get("bearing")
        bearing = bearing_data if isinstance(bearing_data, dict) else {}
        clamped_data = inputs.get("clamped")
        clamped = clamped_data if isinstance(clamped_data, dict) else {}

        choice_restore_maps: dict[str, dict[str, str]] = {
            "elements.joint_type": {v: k for k, v in JOINT_TYPE_MAP.items()},
            "clamped.basic_solid": {v: k for k, v in BASIC_SOLID_MAP.items()},
            "clamped.surface_class": {v: k for k, v in SURFACE_CLASS_MAP.items()},
            "assembly.tightening_method": {v: k for k, v in TIGHTENING_METHOD_MAP.items()},
            "options.surface_treatment": {v: k for k, v in SURFACE_TREATMENT_MAP.items()},
        }

        def _parse_pitch_text(raw: Any) -> float | None:
            text = str(raw).strip()
            if not text:
                return None
            candidates = [text]
            if "（" in text:
                candidates.append(text.split("（", 1)[0].strip())
            for candidate in candidates:
                try:
                    return float(candidate)
                except ValueError:
                    continue
            return None

        def _restore_choice_text(field_id: str, raw: Any) -> str:
            if field_id == "stiffness.auto_compliance":
                if isinstance(raw, bool):
                    return "自动计算" if raw else "手动输入"
                text = str(raw).strip().lower()
                if text in {"true", "1", "自动计算"}:
                    return "自动计算"
                if text in {"false", "0", "手动输入"}:
                    return "手动输入"
                return str(raw)
            restore_map = choice_restore_maps.get(field_id)
            raw_text = str(raw).strip()
            if restore_map is None:
                return raw_text
            return restore_map.get(raw_text, raw_text)

        def _float_or_none(raw: Any) -> float | None:
            try:
                return float(str(raw).strip())
            except (TypeError, ValueError):
                return None

        def _numbers_match(raw: Any, preset: Any, *, tolerance: float = 1e-9) -> bool:
            raw_num = _float_or_none(raw)
            preset_num = _float_or_none(preset)
            if raw_num is None or preset_num is None:
                return False
            relative_tol = abs(preset_num) * 1e-6
            return abs(raw_num - preset_num) <= max(tolerance, relative_tol)

        def _set_combo_text(field_id: str, text: str) -> bool:
            widget = self._field_widgets.get(field_id)
            if not isinstance(widget, QComboBox):
                return False
            idx = widget.findText(text)
            if idx < 0:
                return False
            widget.setCurrentIndex(idx)
            return True

        self._clear()
        for spec in self._field_specs.values():
            value: Any | None = None
            if spec.field_id in ui_state:
                value = ui_state[spec.field_id]
            elif spec.mapping is not None:
                sec, key = spec.mapping
                section = inputs.get(sec)
                if isinstance(section, dict) and key in section:
                    value = section[key]
            if value is None:
                continue
            widget = self._field_widgets[spec.field_id]
            text = _restore_choice_text(spec.field_id, value)
            # 螺纹直径：JSON 中存的是数值 10，需转换为 "M10"
            if spec.field_id == "fastener.d" and isinstance(widget, QComboBox):
                d_key = f"M{int(float(text))}" if text.replace(".", "").isdigit() else text
                idx = widget.findText(d_key)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentText("自定义")
                    cw = self._field_widgets.get("fastener.d_custom")
                    if cw and isinstance(cw, QLineEdit):
                        cw.setText(text)
                continue
            # 螺距：JSON 中存的是数值 1.5，需匹配下拉中含该数值的项
            if spec.field_id == "fastener.p" and isinstance(widget, QComboBox):
                matched = False
                pitch_value = _parse_pitch_text(text)
                for i in range(widget.count()):
                    item_value = widget.itemData(i)
                    if pitch_value is None or item_value is None:
                        continue
                    if float(item_value) == pitch_value:
                        widget.setCurrentIndex(i)
                        matched = True
                        break
                if not matched:
                    widget.setCurrentText("自定义")
                    cw = self._field_widgets.get("fastener.p_custom")
                    if cw and isinstance(cw, QLineEdit):
                        cw.setText(text)
                continue
            if spec.widget_type == "choice":
                idx = widget.findText(text)  # type: ignore[attr-defined]
                if idx >= 0:
                    widget.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(text)  # type: ignore[attr-defined]

        explicit_e_fields: list[tuple[str, str, str]] = [
            ("stiffness.E_bolt", "stiffness", "E_bolt"),
            ("stiffness.E_clamped", "stiffness", "E_clamped"),
        ]
        for layer_idx in range(1, 6):
            explicit_e_fields.append((f"clamped.layer_{layer_idx}.E", "", ""))

        for field_id, section_name, key in explicit_e_fields:
            text: str | None = None
            if field_id in ui_state:
                text = str(ui_state[field_id])
            elif section_name:
                section = inputs.get(section_name)
                if isinstance(section, dict) and key in section:
                    text = str(section[key])
            widget = self._field_widgets.get(field_id)
            if text is None or not isinstance(widget, QLineEdit):
                continue
            widget.setText(text)

        raw_choice_fallbacks: tuple[tuple[str, dict[str, Any], str], ...] = (
            ("elements.joint_type", options, "joint_type"),
            ("clamped.basic_solid", clamped, "basic_solid"),
            ("clamped.surface_class", clamped, "surface_class"),
            ("assembly.tightening_method", options, "tightening_method"),
            ("options.surface_treatment", options, "surface_treatment"),
        )
        for field_id, section, key in raw_choice_fallbacks:
            if field_id in ui_state or key not in section:
                continue
            widget = self._field_widgets.get(field_id)
            if not isinstance(widget, QComboBox):
                continue
            restored_text = _restore_choice_text(field_id, section[key])
            idx = widget.findText(restored_text)
            if idx >= 0:
                widget.setCurrentIndex(idx)

        if "fastener.grade" not in ui_state and fastener.get("Rp02") not in (None, ""):
            rp02_raw = fastener.get("Rp02")
            rp02_value = _float_or_none(rp02_raw)
            grade_widget = self._field_widgets.get("fastener.grade")
            rp02_widget = self._field_widgets.get("fastener.Rp02")
            if isinstance(grade_widget, QComboBox) and isinstance(rp02_widget, QLineEdit):
                matched_grade = None
                if rp02_value is not None:
                    for grade_name, preset in BOLT_GRADE_TABLE.items():
                        if abs(float(preset) - rp02_value) <= 0.5:
                            matched_grade = grade_name
                            break
                if matched_grade is not None:
                    if _set_combo_text("fastener.grade", matched_grade):
                        self._on_grade_changed(matched_grade)
                else:
                    _set_combo_text("fastener.grade", "自定义")
                    rp02_widget.setText(str(rp02_raw))
                    rp02_widget.setReadOnly(False)

        def _restore_thermal_material(
            material_field_id: str,
            alpha_field_id: str,
            e_field_id: str,
            alpha_raw: Any,
            e_raw: Any,
        ) -> None:
            if material_field_id in ui_state:
                return
            has_alpha = alpha_raw not in (None, "")
            has_e = e_raw not in (None, "")
            if not has_alpha and not has_e:
                return

            material_widget = self._field_widgets.get(material_field_id)
            alpha_widget = self._field_widgets.get(alpha_field_id)
            e_widget = self._field_widgets.get(e_field_id)
            if not isinstance(material_widget, QComboBox):
                return

            matched_material = None
            for index in range(material_widget.count()):
                material_name = material_widget.itemText(index)
                if material_name == "自定义":
                    continue
                alpha_preset = THERMAL_EXPANSION_PRESETS.get(material_name)
                e_preset = ELASTIC_MODULUS_PRESETS.get(material_name)
                alpha_ok = not has_alpha or (
                    alpha_preset is not None and _numbers_match(alpha_raw, alpha_preset)
                )
                e_ok = not has_e or (
                    e_preset is not None and _numbers_match(e_raw, e_preset)
                )
                if alpha_ok and e_ok:
                    matched_material = material_name
                    break

            if matched_material is not None:
                material_widget.setCurrentText(matched_material)
                if isinstance(alpha_widget, QLineEdit):
                    alpha_widget.setText(
                        str(alpha_raw) if has_alpha else THERMAL_EXPANSION_PRESETS[matched_material]
                    )
                    alpha_widget.setReadOnly(True)
                if isinstance(e_widget, QLineEdit):
                    e_widget.setText(str(e_raw) if has_e else ELASTIC_MODULUS_PRESETS[matched_material])
                return

            material_widget.setCurrentText("自定义")
            if isinstance(alpha_widget, QLineEdit):
                alpha_widget.setText(str(alpha_raw) if has_alpha else "")
                alpha_widget.setReadOnly(False)
            if isinstance(e_widget, QLineEdit) and has_e:
                e_widget.setText(str(e_raw))

        _restore_thermal_material(
            "operating.bolt_material",
            "operating.alpha_bolt",
            "stiffness.E_bolt",
            operating.get("alpha_bolt"),
            stiffness.get("E_bolt"),
        )
        _restore_thermal_material(
            "operating.clamped_material",
            "operating.alpha_parts",
            "stiffness.E_clamped",
            operating.get("alpha_parts"),
            stiffness.get("E_clamped"),
        )

        if "bearing.bearing_material" not in ui_state and bearing.get("p_G_allow") not in (None, ""):
            bearing_material_widget = self._field_widgets.get("bearing.bearing_material")
            bearing_allow_widget = self._field_widgets.get("bearing.p_G_allow")
            if isinstance(bearing_material_widget, QComboBox):
                matched_bearing = None
                for material_name, preset in BEARING_MATERIAL_PRESETS.items():
                    if _numbers_match(bearing["p_G_allow"], preset, tolerance=0.5):
                        matched_bearing = material_name
                        break
                if matched_bearing is not None:
                    bearing_material_widget.setCurrentText(matched_bearing)
                else:
                    bearing_material_widget.setCurrentText("自定义")
                    if isinstance(bearing_allow_widget, QLineEdit):
                        bearing_allow_widget.setText(str(bearing["p_G_allow"]))
                        bearing_allow_widget.setReadOnly(False)

        # ---------- 多层被夹件 fallback 恢复（用于加载原始 payload JSON）----------
        # 正常 save/load 流程中，通用循环已通过 ui_state 恢复所有层字段。
        # 此处仅处理 inputs 中有 clamped.layers 但 ui_state 中无层字段的情况。
        saved_layers = clamped.get("layers")
        has_layer_ui_state = any(
            k.startswith("clamped.layer_") for k in ui_state
        )
        if isinstance(saved_layers, list) and len(saved_layers) >= 2 and not has_layer_ui_state:
            n = len(saved_layers)
            pc_w = self._field_widgets.get("clamped.part_count")
            if pc_w and isinstance(pc_w, QComboBox):
                if n == 2:
                    pc_w.setCurrentText("2")
                else:
                    pc_w.setCurrentText("自定义")
                    cc_w = self._field_widgets.get("clamped.custom_count")
                    if cc_w and isinstance(cc_w, QLineEdit):
                        cc_w.setText(str(n))
            # 填充各层参数
            op_data = inputs.get("operating", {})
            saved_thermals = op_data.get("layer_thermals", [])
            for i, layer in enumerate(saved_layers[:5], start=1):
                t_w = self._field_widgets.get(f"clamped.layer_{i}.thickness")
                if t_w and isinstance(t_w, QLineEdit):
                    t_w.setText(str(layer.get("l_K", "")))
                da_w = self._field_widgets.get(f"clamped.layer_{i}.D_A")
                if da_w and isinstance(da_w, QLineEdit):
                    da_w.setText(str(layer.get("D_A", "")))
                e_w = self._field_widgets.get(f"clamped.layer_{i}.E")
                if e_w and isinstance(e_w, QLineEdit):
                    e_w.setText(str(layer.get("E_clamped", "")))
                # 恢复材料和 alpha（先设材料触发信号，再覆盖 alpha 值）
                if i - 1 < len(saved_thermals):
                    alpha_val = saved_thermals[i - 1].get("alpha", "")
                    # 先从 alpha 反推材料（触发 _on_layer_material_changed 信号）
                    mat_w = self._field_widgets.get(f"clamped.layer_{i}.material")
                    matched = False
                    if mat_w and isinstance(mat_w, QComboBox):
                        for mat_name, preset_val in THERMAL_EXPANSION_PRESETS.items():
                            if str(alpha_val) == preset_val:
                                mat_w.setCurrentText(mat_name)
                                matched = True
                                break
                        if not matched:
                            mat_w.setCurrentText("自定义")
                    # 再设 alpha（覆盖信号可能清除的值）
                    alpha_w = self._field_widgets.get(f"clamped.layer_{i}.alpha")
                    if alpha_w and isinstance(alpha_w, QLineEdit):
                        alpha_w.setText(str(alpha_val))
                        alpha_w.setReadOnly(matched)
                    if e_w and isinstance(e_w, QLineEdit):
                        e_w.setText(str(layer.get("E_clamped", "")))
            self._on_part_count_changed()
            self._on_compliance_mode_changed()

        if "check_level" in ui_state:
            self._set_check_level(str(ui_state["check_level"]))
        else:
            if "check_level" in options:
                self._set_check_level(str(options["check_level"]))

        calc_mode = ui_state.get("calculation_mode")
        if calc_mode is None:
            calc_mode = options.get("calculation_mode")
        if calc_mode is not None:
            calc_idx = self.calc_mode_combo.findData(str(calc_mode))
            if calc_idx >= 0:
                self.calc_mode_combo.setCurrentIndex(calc_idx)

        if "operating.setup_case" not in ui_state:
            fa_val = inputs.get("loads", {}).get("FA_max", 0) if isinstance(inputs.get("loads"), dict) else 0
            fq_val = inputs.get("loads", {}).get("FQ_max", 0) if isinstance(inputs.get("loads"), dict) else 0
            case_widget = self._field_widgets.get("operating.setup_case")
            if isinstance(case_widget, QComboBox):
                try:
                    fa_num = float(fa_val or 0)
                    fq_num = float(fq_val or 0)
                except (TypeError, ValueError):
                    fa_num = 0.0
                    fq_num = 0.0
                if fa_num > 0 and fq_num > 0:
                    case_widget.setCurrentText("轴向+横向")
                elif fa_num > 0:
                    case_widget.setCurrentText("轴向载荷")
                elif fq_num > 0:
                    case_widget.setCurrentText("横向载荷")

        loads_section = inputs.get("loads")
        if "loads.slip_mu_mode" not in ui_state:
            slip_mode_widget = self._field_widgets.get("loads.slip_mu_mode")
            if isinstance(slip_mode_widget, QComboBox):
                has_slip_mu = isinstance(loads_section, dict) and "slip_friction_coefficient" in loads_section
                slip_mode_widget.setCurrentText(
                    SLIP_MU_MODE_CUSTOM if has_slip_mu else SLIP_MU_MODE_FOLLOW
                )

        self._apply_check_level_visibility()
        case_widget = self._field_widgets.get("operating.setup_case")
        if isinstance(case_widget, QComboBox):
            self._on_setup_case_changed(case_widget.currentText())
        self._mark_results_dirty()

    def _load_sample(self, filename: str) -> None:
        sample_path = EXAMPLES_DIR / filename
        if not sample_path.exists():
            QMessageBox.warning(self, "测试案例不存在", f"未找到测试案例文件: {sample_path}")
            return
        try:
            data = validate_snapshot(read_input_conditions(sample_path))
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "测试案例损坏", f"测试案例文件不是有效 JSON：{exc}")
            return
        except InputConditionError as exc:
            QMessageBox.critical(self, "文件格式错误", str(exc))
            return
        if not confirm_snapshot_module(self, data, MODULE_ID):
            return

        self._apply_input_data(data)
        self.info_label.setText(f"已加载测试案例：{filename}。可直接切换章节核对参数。")
        self._mark_results_dirty()

    def _save_input_conditions(self) -> None:
        default_path = SAVED_INPUTS_DIR / "bolt_input_conditions.json"
        out_path = choose_save_input_conditions_path(self, "保存输入条件", default_path)
        if out_path is None:
            return
        try:
            write_input_conditions(out_path, self._capture_input_snapshot())
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", f"输入条件保存失败：{exc}")
            return
        self.info_label.setText(f"输入条件已保存：{out_path}")

    def _load_input_conditions(self) -> None:
        in_path = choose_load_input_conditions_path(self, "加载输入条件", SAVED_INPUTS_DIR)
        if in_path is None:
            return
        try:
            data = validate_snapshot(read_input_conditions(in_path))
        except FileNotFoundError:
            QMessageBox.warning(self, "文件不存在", f"未找到输入条件文件：{in_path}")
            return
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "文件损坏", f"输入条件文件不是有效 JSON：{exc}")
            return
        except InputConditionError as exc:
            QMessageBox.critical(self, "文件格式错误", str(exc))
            return
        except OSError as exc:
            QMessageBox.critical(self, "加载失败", f"输入条件加载失败：{exc}")
            return
        if not confirm_snapshot_module(self, data, MODULE_ID):
            return

        self._apply_input_data(data)
        self.info_label.setText(f"已加载输入条件：{in_path}")

    def _clear(self) -> None:
        self._apply_defaults()
        self._last_payload = None
        self._last_result = None
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText("填写参数并点击执行校核后，这里显示可读结论。")
        self.metrics_text.setText("尚无结果。")
        self.message_box.clear()
        for badge in self._check_badges.values():
            self._set_badge(badge, "待计算", False)
        self.overall_badge.setText("等待计算")
        self.overall_badge.setObjectName("WaitBadge")
        self.overall_badge.style().unpolish(self.overall_badge)
        self.overall_badge.style().polish(self.overall_badge)
        self.diagram_widget.set_forces(0.0, 0.0, 0.0)
        self.thread_triangle_widget.set_thread_forces(0.0, 0.0, 0.0)
        self._apply_check_level_visibility()
        self.info_label.setText("参数已重置为默认值。")
        self._mark_results_dirty()

    def _mark_results_dirty(self) -> None:
        """输入变更后禁用导出，防止报告与当前屏幕输入不一致。"""
        self.btn_save.setEnabled(False)

    def _mark_results_fresh(self) -> None:
        """计算和渲染完整成功后允许导出。"""
        self.btn_save.setEnabled(True)

    def _connect_dirty_signals(self) -> None:
        """将用户输入变更连接到导出失效。"""
        for widget in self._field_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.textEdited.connect(self._mark_results_dirty)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._mark_results_dirty)

    def _read_widget_value(self, spec: FieldSpec) -> str:
        widget = self._field_widgets[spec.field_id]
        if spec.widget_type == "choice":
            return widget.currentText().strip()  # type: ignore[attr-defined]
        return widget.text().strip()  # type: ignore[attr-defined]

    def _build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        def _read_line_float(field_id: str, label: str) -> float:
            widget = self._field_widgets.get(field_id)
            raw = widget.text().strip() if isinstance(widget, QLineEdit) else ""
            if not raw:
                raise InputError(f"字段 [{label}] 不能为空，请输入数字。")
            if _NUMBER_RE.fullmatch(raw) is None:
                raise InputError(f"字段 [{label}] 请输入数字，当前值: {raw}")
            try:
                return float(raw)
            except ValueError as exc:
                raise InputError(f"字段 [{label}] 请输入数字，当前值: {raw}") from exc

        for spec in self._field_specs.values():
            if spec.mapping is None:
                continue
            raw = self._read_widget_value(spec)
            # 螺纹规格特殊处理：从下拉选项提取数值
            if spec.field_id == "fastener.d":
                raw = self._resolve_thread_d()
            elif spec.field_id == "fastener.p":
                raw = self._resolve_thread_p()
            if not raw:
                continue
            if spec.widget_type == "choice" and spec.field_id not in ("fastener.d", "fastener.p"):
                value: Any = raw
            else:
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise InputError(f"字段 [{spec.label}] 请输入数字，当前值: {raw}") from exc
            sec, key = spec.mapping
            payload.setdefault(sec, {})[key] = value
        payload.setdefault("options", {})["calculation_mode"] = (
            self.calc_mode_combo.currentData() or "design"
        )
        jt_widget = self._field_widgets.get("elements.joint_type")
        if jt_widget and isinstance(jt_widget, QComboBox):
            jt_text = jt_widget.currentText()
            payload.setdefault("options", {})["joint_type"] = JOINT_TYPE_MAP.get(jt_text, "tapped")
        sc_widget = self._field_widgets.get("clamped.surface_class")
        if sc_widget and isinstance(sc_widget, QComboBox):
            sc_text = sc_widget.currentText()
            payload.setdefault("clamped", {})["surface_class"] = SURFACE_CLASS_MAP.get(sc_text, "medium")
        # basic_solid 翻译
        bs_widget = self._field_widgets.get("clamped.basic_solid")
        if bs_widget and isinstance(bs_widget, QComboBox):
            bs_text = bs_widget.currentText()
            payload.setdefault("clamped", {})["basic_solid"] = BASIC_SOLID_MAP.get(bs_text, "cylinder")
        # auto_compliance 布尔转换
        ac_widget = self._field_widgets.get("stiffness.auto_compliance")
        if ac_widget and isinstance(ac_widget, QComboBox):
            is_auto = ac_widget.currentText() == "自动计算"
            payload.setdefault("stiffness", {})["auto_compliance"] = is_auto
            if is_auto:
                # 自动模式下删除手动柔度值，让 calculator 走 auto 路径
                payload.get("stiffness", {}).pop("bolt_compliance", None)
                payload.get("stiffness", {}).pop("clamped_compliance", None)
        method_w = self._field_widgets.get("assembly.tightening_method")
        if method_w is not None and isinstance(method_w, QComboBox):
            method_en = TIGHTENING_METHOD_MAP.get(method_w.currentText(), "torque")
            payload.setdefault("options", {})["tightening_method"] = method_en
        treatment_w = self._field_widgets.get("options.surface_treatment")
        if treatment_w is not None and isinstance(treatment_w, QComboBox):
            treatment_en = SURFACE_TREATMENT_MAP.get(treatment_w.currentText(), "rolled")
            payload.setdefault("options", {})["surface_treatment"] = treatment_en
        stiffness_section = payload.setdefault("stiffness", {})
        is_auto = bool(stiffness_section.get("auto_compliance"))
        has_any_stiffness = any(
            key in stiffness_section for key in ("bolt_stiffness", "clamped_stiffness")
        )
        has_full_stiffness = all(
            key in stiffness_section for key in ("bolt_stiffness", "clamped_stiffness")
        )
        if is_auto:
            stiffness_section.pop("bolt_compliance", None)
            stiffness_section.pop("clamped_compliance", None)
            stiffness_section.pop("bolt_stiffness", None)
            stiffness_section.pop("clamped_stiffness", None)
        elif has_any_stiffness:
            if not has_full_stiffness:
                raise InputError("若使用刚度输入，请同时填写螺栓刚度 cs 与被夹件刚度 cp。")
            stiffness_section.pop("bolt_compliance", None)
            stiffness_section.pop("clamped_compliance", None)

        check_level = self._current_check_level()
        if check_level in {"thermal", "fatigue"}:
            thermal_requirements = (
                ("operating.bolt_material", "operating.alpha_bolt", "螺栓热膨胀系数"),
                ("operating.clamped_material", "operating.alpha_parts", "被夹件/基体热膨胀系数"),
            )
            for material_id, alpha_id, alpha_label in thermal_requirements:
                material_w = self._field_widgets.get(material_id)
                if isinstance(material_w, QComboBox) and material_w.currentText() == "自定义":
                    _read_line_float(alpha_id, alpha_label)

        # ---------- 多层被夹件 payload 构建 ----------
        part_count = self._get_effective_part_count()
        payload.setdefault("clamped", {})["part_count"] = part_count

        if part_count >= 2:
            layers = []
            layer_thermals = []
            total_thickness = 0.0
            d_h_val = payload.get("bearing", {}).get("bearing_d_inner", 13.0)

            for i in range(1, part_count + 1):
                t_val = _read_line_float(f"clamped.layer_{i}.thickness", f"第{i}层厚度")
                da_val = _read_line_float(f"clamped.layer_{i}.D_A", f"第{i}层外径 DA")
                e_val = _read_line_float(f"clamped.layer_{i}.E", f"第{i}层弹性模量")
                alpha_val = _read_line_float(f"clamped.layer_{i}.alpha", f"第{i}层热膨胀系数")
                total_thickness += t_val
                layers.append({
                    "model": "cylinder",
                    "d_h": float(d_h_val),
                    "D_A": da_val,
                    "l_K": t_val,
                    "E_clamped": e_val,
                })
                layer_thermals.append({"alpha": alpha_val, "l_K": t_val})

            payload["clamped"]["layers"] = layers
            payload["clamped"]["total_thickness"] = total_thickness
            payload.setdefault("operating", {})["layer_thermals"] = layer_thermals
            # 多层模式移除单层参数
            payload.get("stiffness", {}).pop("E_clamped", None)
            payload.get("operating", {}).pop("alpha_parts", None)

        setup_case_widget = self._field_widgets.get("operating.setup_case")
        if isinstance(setup_case_widget, QComboBox):
            case_rules = SETUP_CASE_RULES.get(
                setup_case_widget.currentText(),
                SETUP_CASE_RULES["自由输入"],
            )
            loads_section = payload.setdefault("loads", {})
            for key, value in case_rules["force_zero"].items():
                loads_section[key] = value
            for key in case_rules["drop"]:
                loads_section.pop(key, None)
            slip_mode_widget = self._field_widgets.get("loads.slip_mu_mode")
            if (
                isinstance(slip_mode_widget, QComboBox)
                and slip_mode_widget.currentText() == SLIP_MU_MODE_FOLLOW
            ):
                loads_section.pop("slip_friction_coefficient", None)

        return payload

    def _resolve_thread_d(self) -> str:
        """从直径下拉提取数值：M10 → '10', 自定义 → 读自定义输入。"""
        w = self._field_widgets.get("fastener.d")
        if not (w and isinstance(w, QComboBox)):
            return ""
        text = w.currentText()
        if text == "自定义":
            cw = self._field_widgets.get("fastener.d_custom")
            return cw.text().strip() if cw and isinstance(cw, QLineEdit) else ""
        # "M10" → "10"
        return text.lstrip("Mm") if text.startswith(("M", "m")) else text

    def _resolve_thread_p(self) -> str:
        """从螺距下拉提取数值：'1.5（粗牙）' → '1.5', 自定义 → 读自定义输入。"""
        w = self._field_widgets.get("fastener.p")
        if not (w and isinstance(w, QComboBox)):
            return ""
        text = w.currentText()
        if text == "自定义":
            cw = self._field_widgets.get("fastener.p_custom")
            return cw.text().strip() if cw and isinstance(cw, QLineEdit) else ""
        data = w.currentData()
        return str(data) if data is not None else text.split("（")[0].strip()

    def _calculate(self) -> None:
        try:
            payload = self._build_payload()
            payload.setdefault("options", {})["check_level"] = self._current_check_level()
            result = calculate_vdi2230_core(payload)
        except InputError as exc:
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        try:
            self._render_result(payload, result)
            self.flowchart_nav.update_from_result(result)
            for r_page in self._r_pages:
                r_page.build_input_echo(self._field_specs, self._field_widgets, result)
                r_page.update_from_result(result, self._field_widgets)
        except Exception as exc:  # noqa: BLE001
            self._last_payload = None
            self._last_result = None
            self._mark_results_dirty()
            QMessageBox.critical(self, "渲染异常", f"结果展示失败：{exc}")
            self.info_label.setText(f"结果渲染失败：{exc}")
            return

        self._last_payload = payload
        self._last_result = result
        self._mark_results_fresh()

        # Jump to result chapter after run.
        self.chapter_list.setCurrentRow(self.chapter_list.count() - 1)

    def _render_result(self, payload: dict[str, Any], result: dict[str, Any]) -> None:
        overall_status = str(
            result.get("overall_status", "pass" if result.get("overall_pass") else "fail")
        )
        checks = result.get("checks", {})
        level = str(result.get("check_level", self._current_check_level()))

        if overall_status == "pass":
            title = "校核通过"
            summary = "该工况满足当前模型下全部分项要求。"
        elif overall_status == "incomplete":
            title = "校核结论不完整"
            summary = "无分项不通过，但存在未校核项（见'已跳过'徽章与警告），请补充输入后重新校核。"
        else:
            title = "校核不通过"
            summary = "该工况存在未满足项，请查看下方分项状态与调整建议。"
        self.result_title.setText(title)
        self.result_summary.setText(summary)
        if overall_status == "incomplete":
            self.overall_badge.setText("结论不完整")
            self.overall_badge.setObjectName("WaitBadge")
            self.overall_badge.style().unpolish(self.overall_badge)
            self.overall_badge.style().polish(self.overall_badge)
        else:
            self._set_badge(
                self.overall_badge,
                "总体通过" if overall_status == "pass" else "总体不通过",
                overall_status == "pass",
            )

        for key, badge in self._check_badges.items():
            if key == "residual_clamp_ok" and result.get("calculation_mode") == "design":
                self._set_badge(badge, "通过（设计模式自动满足）", True)
            elif key not in checks:
                badge.setObjectName("WaitBadge")
                badge.setText("已跳过")
                badge.style().polish(badge)
            else:
                self._set_badge(badge, "通过" if checks[key] else "不通过", checks[key])
        # 附加载荷参考 badge（从 references 读取，不在 checks 中）
        ref_badge = self._check_badges.get("additional_load_ok")
        if ref_badge:
            refs = result.get("references", {})
            ref_pass = refs.get("additional_load_ok", True)
            self._set_badge(ref_badge, "通过" if ref_pass else "超限（仅参考）", ref_pass)
        self._apply_check_level_visibility()

        inter = result["intermediate"]
        torque = result["torque"]
        force = result["forces"]
        stresses = result["stresses_mpa"]
        fa_max = payload.get("loads", {}).get("FA_max", 0.0)
        fatigue = result.get("fatigue", {})
        thermal = result.get("thermal", {})

        def _ratio(actual: float, allowed: float) -> str:
            if allowed == 0:
                return "N/A"
            return f"{actual / allowed * 100:.1f}%"

        metric_lines = [
            f"• 预紧力范围: FMmin = {inter['FMmin_N']:.1f} N,  FMmax = {inter['FMmax_N']:.1f} N",
            f"• 拧紧扭矩范围: MAmin = {torque['MA_min_Nm']:.2f} N·m,  MAmax = {torque['MA_max_Nm']:.2f} N·m",
            f"• 残余夹紧力: FK,res = {force['F_K_residual_N']:.1f} N  /  需求 {inter['F_K_required_N']:.1f} N",
            f"• 装配等效应力: {stresses['sigma_vm_assembly']:.1f} MPa  /  允许 {stresses['sigma_allow_assembly']:.1f} MPa"
            f"  [{_ratio(stresses['sigma_vm_assembly'], stresses['sigma_allow_assembly'])}]",
            f"• 服役等效应力: {stresses['sigma_vm_work']:.1f} MPa  /  允许 {stresses['sigma_allow_work']:.1f} MPa"
            f"  [{_ratio(stresses['sigma_vm_work'], stresses['sigma_allow_work'])}]",
            f"• 附加载荷参考: FA,max = {fa_max:.1f} N  /  参考上限 {result.get('references', {}).get('FA_perm_N', 0):.1f} N  (⚠ 参考估算，非 VDI 标准项)",
        ]
        if level in ("thermal", "fatigue"):
            thermal_line = f"• 热损失占比: {thermal.get('thermal_loss_ratio', 0.0) * 100:.1f}%  /  限值 25.0%"
            if thermal.get("thermal_auto_estimated"):
                a_b = thermal.get("alpha_bolt", 0)
                a_p = thermal.get("alpha_parts", 0)
                thermal_line += f"\n  热膨胀系数: α_bolt={a_b:.1e} /K, α_parts={a_p:.1e} /K（自动估算）"
            metric_lines.append(thermal_line)
        if level == "fatigue":
            metric_lines.append(
                f"• 疲劳应力幅: {fatigue.get('sigma_a', 0.0):.1f} MPa  /  允许 {fatigue.get('sigma_a_allow', 0.0):.1f} MPa"
                f"  [{_ratio(float(fatigue.get('sigma_a', 0.0)), float(fatigue.get('sigma_a_allow', 0.0)))}]"
            )
        embed_est = result.get("embed_estimation", {})
        if embed_est.get("embed_auto_estimated"):
            metric_lines.append(
                f"• 嵌入损失估算: FZ = {embed_est['embed_auto_value_N']:.0f} N"
                f"  ({embed_est['embed_interfaces']} 个界面 × {embed_est['embed_fz_per_if_um']:.1f} μm)"
            )
        self.metrics_text.setText("\n".join(metric_lines))

        messages = []
        for warning in result.get("warnings", []):
            messages.append(f"[警告] {warning}")
        messages.extend(self._build_recommendations(result))
        jt = result.get("joint_type", "tapped")
        jt_label = "螺纹孔连接" if jt == "tapped" else "通孔螺栓连接"
        messages.append(f"[连接形式] {jt_label}")
        r7_note = result.get("r7_note", "")
        if r7_note:
            messages.append(f"[R7 说明] {r7_note}")
        r8_note = result.get("r8_note", "")
        if r8_note:
            strip = result.get("thread_strip", {})
            messages.append(
                f"[R8 脱扣] {r8_note}，"
                f"安全系数 = {strip.get('strip_safety', 0):.2f}"
                f"（要求 >= {strip.get('strip_safety_required', 1.25):.2f}）"
            )
        messages.append(
            "[说明] 本版本支持分层校核：常规(R3/R4/R5)、温度影响、疲劳简化Goodman、螺纹脱扣(R8)。"
            "完整疲劳谱与偏心弯矩仍未覆盖。"
        )
        self.message_box.setPlainText("\n".join(messages))

        self.diagram_widget.set_joint_type(result.get("joint_type", "tapped"))
        if hasattr(self, "diagram_help_label"):
            self.diagram_help_label.setText(
                self._build_diagram_help_text(result.get("joint_type", "tapped"))
            )
        self.diagram_widget.set_forces(inter["FMmin_N"], fa_max, force["F_K_residual_N"])
        self.thread_triangle_widget.set_thread_forces(
            inter["FMmax_N"],
            inter["lead_angle_deg"],
            inter["friction_angle_deg"],
        )

    def _build_recommendations(self, result: dict[str, Any]) -> list[str]:
        checks = result.get("checks", {})
        recs: list[str] = []
        if not checks.get("assembly_von_mises_ok", True):
            recs.append(
                "[建议] 装配应力超限：可提高螺栓等级、降低目标预紧力散差(αA)、或优化摩擦控制。"
            )
        if not checks.get("operating_axial_ok", True):
            recs.append("[建议] 服役应力超限：可增大规格 d、提高强度等级、或降低外载 FA。")
        if not checks.get("residual_clamp_ok", True):
            recs.append("[建议] 残余夹紧力不足：可提高 FMmin、减小嵌入损失、或增加摩擦面能力。")
        refs = result.get("references", {})
        if not refs.get("additional_load_ok", True):
            recs.append("[参考] 附加载荷超限（参考估算）：可提高 As、降低 n 或减少轴向外载。")
        if "thermal_loss_ok" in checks and not checks.get("thermal_loss_ok", True):
            recs.append("[建议] 热损失偏大：可补偿预紧力、优化材料热匹配或降低温差。")
        if "fatigue_ok" in checks and not checks.get("fatigue_ok", True):
            recs.append("[建议] 疲劳不通过：可降低应力幅、提高螺栓等级、优化载荷谱或增大规格。")
        if "bearing_pressure_ok" in checks and not checks.get("bearing_pressure_ok", True):
            recs.append("[建议] 支承面压强不通过：可增大支承直径、加垫圈、降低预紧力或提高支承面材料许用压强。")
        if "thread_strip_ok" in checks and not checks.get("thread_strip_ok", True):
            strip = result.get("thread_strip", {})
            side = strip.get("critical_side", "")
            if side == "nut":
                recs.append("[建议] 螺纹脱扣不通过（壳体侧）：可加深旋合深度、换用更高强度壳体材料、或加大螺栓规格。")
            else:
                recs.append("[建议] 螺纹脱扣不通过（螺栓侧）：可加深旋合深度或提高螺栓强度等级。")
        not_checked = result.get("not_checked", [])
        if not recs and not_checked:
            recs.append("[建议] 当前结论不完整：请补充 " + "、".join(not_checked) + " 后重新校核。")
        if not recs:
            recs.append("[建议] 当前工况满足全部校核。建议保留 10% 以上工程裕量。")
        return recs

    def _save_report(self) -> None:
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行校核计算。")
            return

        default_path = EXAMPLES_DIR / "bolt_check_report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出校核报告", str(default_path),
            "PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        out_path = Path(file_path)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            suffix = out_path.suffix.lower()
            if suffix == ".pdf":
                report_lines = self._build_report_lines()
                used_rich_pdf = _export_bolt_pdf_report(
                    out_path,
                    self._last_payload,
                    self._last_result,
                    report_lines,
                )
                if not used_rich_pdf:
                    self.info_label.setText(
                        f"校核报告已导出: {out_path}（当前环境未安装 reportlab，已使用基础 PDF 导出）"
                    )
                    return
            elif suffix == ".docx":
                from app.ui.report_export import _export_docx
                _export_docx(out_path, self._build_report_lines())
            else:
                out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
        except (ReportExportError, OSError) as exc:
            QMessageBox.critical(self, "导出失败", f"导出失败：{exc}")
            return
        self.info_label.setText(f"校核报告已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        assert self._last_result is not None
        assert self._last_payload is not None
        result = self._last_result
        payload = self._last_payload
        checks = result["checks"]
        inter = result["intermediate"]
        torque = result["torque"]
        forces = result["forces"]
        stresses = result["stresses_mpa"]

        lines = [
            "VDI 2230 螺栓校核报告（本地版）",
            f"生成时间: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"校核层级: {result.get('check_level', self._current_check_level())}",
            "",
            "总体结论: " + _OVERALL_STATUS_TEXT.get(
                str(result.get("overall_status", "pass" if result.get("overall_pass") else "fail")),
                "不通过",
            ),
            "",
            "分项结果:",
        ]
        for key, title in CHECK_LABELS.items():
            if key in ("thermal_loss_ok", "fatigue_ok"):
                level = str(result.get("check_level", self._current_check_level()))
                if key == "thermal_loss_ok" and level == "basic":
                    continue
                if key == "fatigue_ok" and level != "fatigue":
                    continue
            if key == "additional_load_ok":
                refs = result.get("references", {})
                passed = refs.get("additional_load_ok", True)
                lines.append(f"- {title}: {'通过' if passed else '超限（仅参考）'}")
                continue
            if key not in checks:
                lines.append(f"- {title}: 已跳过")
            else:
                lines.append(f"- {title}: {'通过' if checks.get(key) else '不通过'}")

        lines.extend(
            [
                "",
                "关键结果:",
                f"- FMmin: {inter['FMmin_N']:.2f} N",
                f"- FMmax: {inter['FMmax_N']:.2f} N",
                f"- MAmin: {torque['MA_min_Nm']:.3f} N·m",
                f"- MAmax: {torque['MA_max_Nm']:.3f} N·m",
                f"- FK_residual: {forces['F_K_residual_N']:.2f} N",
                f"- FK_required: {inter['F_K_required_N']:.2f} N",
                f"- FA_perm: {result.get('references', {}).get('FA_perm_N', 0):.2f} N (参考估算)",
                f"- sigma_vm_assembly: {stresses['sigma_vm_assembly']:.2f} MPa",
                f"- sigma_vm_work: {stresses['sigma_vm_work']:.2f} MPa",
                "",
                "输入摘要:",
                f"- d: {payload.get('fastener', {}).get('d', 'N/A')} mm",
                f"- p: {payload.get('fastener', {}).get('p', 'N/A')} mm",
                f"- Rp0.2: {payload.get('fastener', {}).get('Rp02', 'N/A')} MPa",
                f"- FA_max: {payload.get('loads', {}).get('FA_max', 'N/A')} N",
                f"- FQ_max: {payload.get('loads', {}).get('FQ_max', 'N/A')} N",
                "",
                "建议:",
            ]
        )
        lines.extend(f"- {msg}" for msg in self._build_recommendations(result))
        return lines
