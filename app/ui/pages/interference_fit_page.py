"""Interference-fit module page with chapter-style workflow."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
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
    "自定义": None,
}
MATERIAL_OPTIONS: tuple[str, ...] = tuple(MATERIAL_LIBRARY.keys())
ROUGHNESS_PROFILE_FACTORS: dict[str, float | None] = {
    "DIN 7190-1:2017（k=0.4）": 0.4,
    "DIN 7190:2001（k=0.8）": 0.8,
    "自定义k": None,
}
ROUGHNESS_PROFILE_OPTIONS: tuple[str, ...] = tuple(ROUGHNESS_PROFILE_FACTORS.keys())


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
                "曲线图离散点数量；越大越平滑，计算耗时略增。",
                mapping=("options", "curve_points"),
                default="41",
                placeholder="11~201",
            ),
        ],
    },
    {
        "title": "几何与过盈",
        "subtitle": "圆柱面过盈（实心轴 + 厚壁轮毂）几何输入。",
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
]

CHECK_LABELS = {
    "torque_ok": "扭矩能力校核（按最小过盈）",
    "axial_ok": "轴向力能力校核（按最小过盈）",
    "gaping_ok": "张口缝校核（p_min >= p_r + p_b）",
    "fit_range_ok": "过盈量范围覆盖校核",
    "shaft_stress_ok": "轴侧应力安全系数校核",
    "hub_stress_ok": "轮毂应力安全系数校核",
}

BEGINNER_GUIDES: dict[str, str] = {
    "loads.application_factor_ka": "工况越冲击，KA 越大，需求过盈也会随之提高。",
    "geometry.shaft_d_mm": "决定接触面积与接触半径，直接影响扭矩能力。",
    "geometry.hub_outer_d_mm": "外径越大，轮毂刚度越高、同等过盈下接触压力越低。",
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
}


class InterferenceFitPage(BaseChapterPage):
    """Cylindrical interference-fit chapter page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="过盈配合 · 圆柱面校核",
            subtitle="DIN 7190 核心增强版：实心轴 + 厚壁轮毂，覆盖防滑、张口缝与应力校核。",
            parent=parent,
        )
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._widget_hints: dict[QWidget, str] = {}
        self._check_badges: dict[str, QLabel] = {}
        self._material_links: dict[str, tuple[str, str]] = {
            "materials.shaft_material": ("materials.shaft_e_mpa", "materials.shaft_nu"),
            "materials.hub_material": ("materials.hub_e_mpa", "materials.hub_nu"),
        }
        self._roughness_profile_field = "roughness.profile"
        self._roughness_factor_field = "roughness.smoothing_factor"

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
        self._apply_defaults()
        self._load_sample("interference_case_01.json")
        self._sync_material_inputs()
        self._sync_roughness_factor()

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
            form_layout.addWidget(field_card)
            self._field_cards[spec.field_id] = field_card

        form_layout.addStretch(1)
        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)
        return page

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
        hint = QLabel("按最小/最大过盈分别计算能力与应力。", container)
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

    def _register_material_bindings(self) -> None:
        for selector_id in self._material_links:
            selector = self._field_widgets.get(selector_id)
            if not isinstance(selector, QComboBox):
                continue
            selector.currentTextChanged.connect(
                lambda _text, sid=selector_id: self._apply_material_selection(sid)
            )

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

        if overall:
            self.result_title.setText("校核通过")
            self.result_summary.setText("该工况在当前输入范围内满足 DIN 7190 核心能力、张口缝与应力要求。")
            self.set_overall_status("总体通过", "pass")
        else:
            self.result_title.setText("校核不通过")
            self.result_summary.setText("存在未满足项，请优先查看张口缝、需求过盈和应力侧提示。")
            self.set_overall_status("总体不通过", "fail")

        for key, badge in self._check_badges.items():
            ok = bool(checks.get(key, False))
            self._set_badge(badge, "通过" if ok else "不通过", "pass" if ok else "fail")

        p = result["pressure_mpa"]
        cap = result["capacity"]
        asm = result["assembly"]
        req = result["required"]
        rough = result["roughness"]
        stress = result["stress_mpa"]
        safety = result["safety"]
        add_p = result["additional_pressure_mpa"]

        metric_lines = [
            f"• 设计载荷: KA={safety['application_factor_ka']:.2f}, p_req={p['p_required']:.2f} MPa, delta_req={req['delta_required_um']:.2f} um",
            f"• 接触压力 min/mean/max: {p['p_min']:.2f} / {p['p_mean']:.2f} / {p['p_max']:.2f} MPa",
            f"• 扭矩能力 min/mean/max: {cap['torque_min_nm']:.1f} / {cap['torque_mean_nm']:.1f} / {cap['torque_max_nm']:.1f} N·m",
            f"• 轴向能力 min/mean/max: {cap['axial_min_n']:.0f} / {cap['axial_mean_n']:.0f} / {cap['axial_max_n']:.0f} N",
            f"• 压入力 min/mean/max: {asm['press_force_min_n']:.0f} / {asm['press_force_mean_n']:.0f} / {asm['press_force_max_n']:.0f} N",
            f"• 附加载荷压强: p_r={add_p['p_radial']:.2f} MPa, p_b={add_p['p_bending']:.2f} MPa, p_gap={add_p['p_gap']:.2f} MPa",
            f"• 粗糙度修正: s={rough['subsidence_um']:.2f} um, delta_eff,min/mean/max={rough['delta_effective_min_um']:.2f} / {rough['delta_effective_mean_um']:.2f} / {rough['delta_effective_max_um']:.2f} um",
            f"• 应力 max: shaft_vm={stress['shaft_vm_max']:.1f} MPa, hub_vm={stress['hub_vm_max']:.1f} MPa, hub_sigma_theta={stress['hub_hoop_inner_max']:.1f} MPa",
            f"• 安全系数: S_torque={safety['torque_sf']:.2f}, S_axial={safety['axial_sf']:.2f}, S_shaft={safety['shaft_sf']:.2f}, S_hub={safety['hub_sf']:.2f}",
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
        messages.append(
            "[说明] 当前模型为 DIN 7190 核心增强版：线弹性、均匀接触压力、恒定摩擦。"
            "弯矩附加压强按 QW=0 的保守简化处理；阶梯轮毂、离心力与配合搜索未纳入本轮。"
        )
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
        if not checks.get("fit_range_ok", True):
            recs.append("[建议] 最大过盈不足以覆盖需求：请提升公差带或调整结构尺寸。")
        if not checks.get("shaft_stress_ok", True):
            recs.append("[建议] 轴侧应力安全系数不足：降低最大过盈或提高轴材料屈服强度。")
        if not checks.get("hub_stress_ok", True):
            recs.append("[建议] 轮毂应力安全系数不足：优先增大轮毂外径或提高轮毂材料强度。")
        if not recs:
            recs.append("[建议] 当前工况满足全部校核，建议至少保留 10% 工程裕量。")
        return recs

    def _capture_input_snapshot(self) -> dict[str, Any]:
        return build_form_snapshot(self._field_specs.values(), self._read_widget_value)

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        inputs_data = data.get("inputs")
        inputs = inputs_data if isinstance(inputs_data, dict) else data
        ui_state_data = data.get("ui_state")
        ui_state = ui_state_data if isinstance(ui_state_data, dict) else {}

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
        self._apply_defaults()
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
        out_path = export_report_lines(self, "导出结果说明", default_path, self._build_report_lines())
        if out_path is not None:
            self.set_info(f"结果说明已导出: {out_path}")

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
                "关键值:",
                f"- p_min / p_mean / p_max / p_req: {p['p_min']:.3f} / {p['p_mean']:.3f} / {p['p_max']:.3f} / {p['p_required']:.3f} MPa",
                f"- p_r / p_b / p_gap: {add_p['p_radial']:.3f} / {add_p['p_bending']:.3f} / {add_p['p_gap']:.3f} MPa",
                f"- roughness subsidence s: {rough['subsidence_um']:.3f} um",
                f"- delta_eff,min / mean / max: {rough['delta_effective_min_um']:.3f} / {rough['delta_effective_mean_um']:.3f} / {rough['delta_effective_max_um']:.3f} um",
                f"- T_min / mean / max: {cap['torque_min_nm']:.3f} / {cap['torque_mean_nm']:.3f} / {cap['torque_max_nm']:.3f} N·m",
                f"- F_min / mean / max: {cap['axial_min_n']:.3f} / {cap['axial_mean_n']:.3f} / {cap['axial_max_n']:.3f} N",
                f"- F_press,min / mean / max: {asm['press_force_min_n']:.3f} / {asm['press_force_mean_n']:.3f} / {asm['press_force_max_n']:.3f} N",
                f"- delta_required: {req['delta_required_um']:.3f} um",
                f"- shaft_vm_max / hub_vm_max: {stress['shaft_vm_max']:.3f} / {stress['hub_vm_max']:.3f} MPa",
                f"- S_torque / S_axial: {safety['torque_sf']:.3f} / {safety['axial_sf']:.3f}",
                f"- S_shaft / S_hub: {safety['shaft_sf']:.3f} / {safety['hub_sf']:.3f}",
                "",
                "说明:",
                "- 当前模型为 DIN 7190 核心增强版：线弹性、均匀接触压力、恒定摩擦。",
                "- 弯矩附加压强按 QW=0 的保守简化处理。",
            ]
        )
        return lines
