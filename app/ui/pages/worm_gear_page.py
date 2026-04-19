"""Worm gear module page with DIN 3975 first-pass workflow."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# 尝试导入塑料材料库；若 core-engineer 尚未创建，延迟到实际使用时报错
try:
    from core.worm.materials import PLASTIC_MATERIALS
    _PLASTIC_MATERIALS_AVAILABLE = True
except ImportError:
    PLASTIC_MATERIALS = {}
    _PLASTIC_MATERIALS_AVAILABLE = False

from app.ui.input_condition_store import (
    build_form_snapshot,
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    read_input_conditions,
    write_input_conditions,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.widgets.latex_label import LatexLabel
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget
from app.ui.widgets.worm_performance_curve import WormPerformanceCurveWidget
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget
from core.worm.calculator import InputError, calculate_worm_geometry


LOAD_CAPACITY_OPTIONS = (
    "DIN 3996 Method A -- 基于实验/FEM，精度最高",
    "DIN 3996 Method B -- 标准解析计算（推荐）",
    "DIN 3996 Method C -- 简化估算",
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    label: str
    unit: str
    hint: str
    widget_type: str = "number"
    options: tuple[str, ...] = ()
    default: str = ""
    placeholder: str = ""
    help_ref: str = ""

    @property
    def mapping(self) -> tuple[str, str] | None:
        if "." not in self.field_id:
            return None
        return tuple(self.field_id.split(".", 1))  # type: ignore[return-value]


BASIC_SETTINGS_FIELDS = [
    FieldSpec("meta.note", "项目备注", "-", "当前计算任务简述。", widget_type="text", default="Method B 最小子集"),
    FieldSpec(
        "load_capacity.enabled",
        "启用 Load Capacity 页",
        "-",
        "是否显示负载能力骨架状态。",
        widget_type="choice",
        options=("启用", "关闭"),
        default="启用",
    ),
    FieldSpec(
        "load_capacity.method",
        "校核方法",
        "-",
        "当前版本各方法计算逻辑相同，仅作标记用途。",
        widget_type="choice",
        options=LOAD_CAPACITY_OPTIONS,
        default="DIN 3996 Method B -- 标准解析计算（推荐）",
        help_ref="modules/worm/din3996_method_b",
    ),
]

WORM_GEOMETRY_FIELDS = [
    FieldSpec("geometry.z1", "蜗杆头数 z1", "-", "蜗杆起始头数。", default="2"),
    FieldSpec("geometry.module_mm", "模数 m", "mm", "几何主输入。", default="4.0", help_ref="terms/module"),
    FieldSpec("geometry.diameter_factor_q", "直径系数 q", "-", "蜗杆直径系数。", default="10.0", help_ref="terms/diameter_factor_q"),
    FieldSpec("geometry.lead_angle_deg", "导程角 gamma", "deg", "蜗杆导程角。默认值与 z1/q 保持自洽。", default="11.31", help_ref="terms/lead_angle"),
    FieldSpec("geometry.worm_face_width_mm", "蜗杆齿宽 b1", "mm", "蜗杆工作齿宽。", default="32.0"),
    FieldSpec("geometry.x1", "蜗杆变位系数 x1", "-", "蜗杆齿形变位系数。", default="0.0", help_ref="terms/profile_shift"),
]

WHEEL_GEOMETRY_FIELDS = [
    FieldSpec("geometry.z2", "蜗轮齿数 z2", "-", "蜗轮总齿数。", default="40"),
    FieldSpec("geometry.wheel_face_width_mm", "蜗轮齿宽 b2", "mm", "蜗轮工作齿宽。", default="28.0"),
    FieldSpec("geometry.x2", "蜗轮变位系数 x2", "-", "蜗轮齿形变位系数。塑料蜗轮常用大正变位。", default="0.0", help_ref="terms/profile_shift"),
]

MESH_GEOMETRY_FIELDS = [
    FieldSpec("geometry.center_distance_mm", "中心距 a", "mm", "蜗杆与蜗轮轴线距离。默认值与 m/q/z2 保持自洽。", default="100.0"),
]

MATERIAL_FIELDS = [
    FieldSpec(
        "materials.worm_material",
        "蜗杆材料",
        "-",
        "例如渗碳钢。",
        widget_type="choice",
        options=("37CrS4",),
        default="37CrS4",
    ),
    FieldSpec(
        "materials.wheel_material",
        "蜗轮材料",
        "-",
        "塑料蜗轮材料，选择后自动填充弹性模量和许用应力。",
        widget_type="choice",
        options=("PA66", "PA66+GF30", "POM", "PA46", "PEEK"),
        default="PA66",
    ),
    FieldSpec(
        "materials.handedness",
        "旋向",
        "-",
        "影响摩擦力矩方向及几何总览螺旋示意。",
        widget_type="choice",
        options=("right", "left"),
        default="right",
    ),
    FieldSpec(
        "materials.lubrication",
        "润滑方式",
        "-",
        "影响有效摩擦系数（oil_bath -10%，dry +35%）。",
        widget_type="choice",
        options=("oil_bath", "grease", "dry"),
        default="grease",
        help_ref="terms/lubrication",
    ),
    FieldSpec("materials.worm_e_mpa", "蜗杆弹性模量 E1", "MPa", "Method B 最小子集使用的材料弹性参数。", default="210000", help_ref="terms/elastic_modulus"),
    FieldSpec("materials.worm_nu", "蜗杆泊松比 nu1", "-", "Method B 最小子集使用的材料弹性参数。", default="0.30", help_ref="terms/poisson_ratio"),
    FieldSpec("materials.wheel_e_mpa", "蜗轮弹性模量 E2", "MPa", "Method B 最小子集使用的材料弹性参数。", default="3000", help_ref="terms/elastic_modulus"),
    FieldSpec("materials.wheel_nu", "蜗轮泊松比 nu2", "-", "Method B 最小子集使用的材料弹性参数。", default="0.38", help_ref="terms/poisson_ratio"),
]

OPERATING_FIELDS = [
    FieldSpec("operating.input_torque_nm", "输入扭矩 T1", "Nm", "蜗杆轴输入扭矩。", default="19.76"),
    FieldSpec("operating.speed_rpm", "输入转速 n", "rpm", "蜗杆轴转速。", default="1450"),
    FieldSpec("operating.application_factor", "使用系数 KA", "-", "工况冲击影响的简化系数。", default="1.25", help_ref="terms/application_factor_ka"),
    FieldSpec("operating.torque_ripple_percent", "扭矩波动", "%", "围绕名义扭矩的峰值波动幅值。", default="0.0"),
]

ADVANCED_FIELDS = [
    FieldSpec(
        "advanced.friction_override",
        "摩擦系数覆盖",
        "-",
        "为空时使用材料配对的默认经验值。",
        default="",
        placeholder="留空则自动",
    ),
    FieldSpec("advanced.normal_pressure_angle_deg", "法向压力角 alpha_n", "deg", "力分解与最小齿面/齿根模型的几何参数。", default="20.0", help_ref="terms/pressure_angle"),
    FieldSpec(
        "advanced.operating_temp_c",
        "工作温度",
        "℃",
        "齿面工作温度，用于塑料材料降额计算（PA 系列高温强度下降明显）。",
        default="23",
    ),
    FieldSpec(
        "advanced.humidity_rh",
        "相对湿度",
        "%",
        "环境相对湿度，PA 系列吸水后弹性模量和强度降额使用。",
        default="50",
    ),
]

LOAD_CAPACITY_PARAMETER_FIELDS = [
    FieldSpec("load_capacity.allowable_contact_stress_mpa", "许用齿面应力", "MPa", "用于最小齿面安全系数计算。", default="42.0", help_ref="terms/allowable_contact_stress"),
    FieldSpec("load_capacity.allowable_root_stress_mpa", "许用齿根应力", "MPa", "用于最小齿根安全系数计算。", default="55.0", help_ref="terms/allowable_root_stress"),
    FieldSpec("load_capacity.dynamic_factor_kv", "动载系数 Kv", "-", "最小子集中的动载放大系数。", default="1.05", help_ref="terms/kv_factor"),
    FieldSpec("load_capacity.transverse_load_factor_kha", "横向载荷系数 KHalpha", "-", "横向载荷分配系数。", default="1.00", help_ref="terms/kh_alpha"),
    FieldSpec("load_capacity.face_load_factor_khb", "齿宽载荷系数 KHbeta", "-", "齿宽方向载荷分配系数。", default="1.10", help_ref="terms/kh_beta"),
    FieldSpec("load_capacity.required_contact_safety", "目标齿面安全系数", "-", "用于通过/不通过判定。", default="1.00"),
    FieldSpec("load_capacity.required_root_safety", "目标齿根安全系数", "-", "用于通过/不通过判定。", default="1.00"),
]

WORM_DIMENSION_FIELDS = [
    ("pitch_diameter_mm", "分度圆直径 d1", "mm", "由模数和直径系数自动计算。"),
    ("tip_diameter_mm", "顶圆直径 da1", "mm", "按首版近似关系自动计算。"),
    ("root_diameter_mm", "根圆直径 df1", "mm", "按首版近似关系自动计算。"),
    ("lead_mm", "导程 l", "mm", "由导程角和分度圆自动计算。"),
    ("axial_pitch_mm", "轴向节距 px", "mm", "导程除以头数得到。"),
    ("pitch_line_speed_mps", "圆周速度 v1", "m/s", "用于基础效率估算。"),
]

WHEEL_DIMENSION_FIELDS = [
    ("pitch_diameter_mm", "分度圆直径 d2", "mm", "由 d2 = z2 × m 自动计算。"),
    ("tip_diameter_mm", "顶圆直径 da2", "mm", "按首版近似关系自动计算。"),
    ("root_diameter_mm", "根圆直径 df2", "mm", "按首版近似关系自动计算。"),
    ("tooth_height_mm", "齿高 h", "mm", "按首版近似关系自动计算。"),
    ("pitch_line_speed_mps", "圆周速度 v2", "m/s", "由蜗轮转速和分度圆自动计算。"),
]


class WormGearPage(BaseChapterPage):
    """DIN 3975 worm-gear module shell with deferred load-capacity workflow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="蜗轮和蜗杆 · DIN 3975",
            subtitle="实现 DIN 3975 几何、基础性能和 Method B 风格最小负载能力子集。",
            parent=parent,
        )
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._last_result: dict[str, Any] | None = None
        self._last_payload: dict[str, Any] | None = None
        # Step 1: throttle timer for geometry preview
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._do_refresh_preview)
        self._preview_call_count = 0
        self.geometry_group_titles = [
            "蜗杆参数",
            "蜗轮参数",
            "啮合与装配",
            "蜗杆自动计算尺寸",
            "蜗轮自动计算尺寸",
        ]
        self.worm_dimension_labels: dict[str, QLabel] = {}
        self.wheel_dimension_labels: dict[str, QLabel] = {}

        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行计算", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_save = self.add_action_button("导出结果说明")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")
        # Step 3: dirty-state status label (reuses the base info area but also
        # keeps a dedicated QLabel we can show inline in the action row)
        self._result_status_label = QLabel("", self)
        self._result_status_label.setObjectName("SectionHint")
        self._result_status_label.setWordWrap(True)
        # Export button starts disabled until a calculation completes
        self.btn_save.setEnabled(False)

        self._build_input_steps()
        self._build_graphics_step()
        self._build_load_capacity_step()
        self._build_results_step()
        self._apply_defaults()
        self._field_widgets["load_capacity.enabled"].currentTextChanged.connect(self._on_lc_enabled_changed)
        self._field_widgets["load_capacity.method"].currentTextChanged.connect(self._on_method_changed)
        self._field_widgets["materials.worm_material"].currentTextChanged.connect(lambda: self._on_material_changed())
        self._field_widgets["materials.wheel_material"].currentTextChanged.connect(lambda: self._on_material_changed())
        # 温湿度变化时，塑料降额许用应力需要重新自动填充，保持与 core 一致
        for fid in ("advanced.operating_temp_c", "advanced.humidity_rh"):
            w = self._field_widgets.get(fid)
            if isinstance(w, QLineEdit):
                w.editingFinished.connect(lambda: self._on_material_changed())
        self.set_current_chapter(0)
        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save.clicked.connect(self._export_report)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("worm_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("worm_case_02.json"))
        # Step 3: connect every input widget change to dirty-state marker
        self._connect_dirty_signals()
        self.set_info("按左侧顺序输入 DIN 3975 / Method B 参数，再执行计算。")

    def _build_input_steps(self) -> None:
        self.add_chapter(
            "基本设置",
            self._create_form_page(
                "基本设置",
                "设置校核的范围和算法：是否启用齿面/齿根负载能力校核、选用 DIN 3996 的哪一种方法。",
                BASIC_SETTINGS_FIELDS,
            ),
            help_ref="modules/worm/_section_basic",
        )
        self.add_chapter(
            "几何参数",
            self._create_geometry_page(),
            help_ref="modules/worm/_section_geometry",
        )
        self.add_chapter(
            "材料与配对",
            self._create_form_page(
                "材料与配对",
                "选择蜗杆/蜗轮材料；选中塑料蜗轮后会自动带入弹性模量和许用应力，也可手动覆盖。旋向与润滑方式会影响摩擦力与安全系数。",
                MATERIAL_FIELDS,
            ),
            help_ref="modules/worm/_section_material",
        )
        self.add_chapter(
            "工况与润滑",
            self._create_form_page(
                "工况与润滑",
                "输入运行工况：输入扭矩 T1、转速 n、反映冲击的使用系数 KA、扭矩波动百分比。这些值直接影响齿面应力与动载系数 Kv 的计算。",
                OPERATING_FIELDS,
            ),
            help_ref="modules/worm/_section_operating",
        )

    def _create_form_page(self, title: str, subtitle: str, fields: list[FieldSpec]) -> QWidget:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel(title, page)
        title_label.setObjectName("SectionTitle")
        subtitle_label = QLabel(subtitle, page)
        subtitle_label.setObjectName("SectionHint")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(2, 2, 2, 2)
        form_layout.setSpacing(8)

        for spec in fields:
            form_layout.addWidget(self._create_input_row_card(spec, container))

        form_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        return page

    def _create_geometry_page(self) -> QWidget:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel("几何参数", page)
        title_label.setObjectName("SectionTitle")
        subtitle_label = QLabel(
            "分组输入几何参数：蜗杆（z1/m/q/导程角）、蜗轮（z2/变位）、啮合中心距。下方只读区会实时给出派生尺寸（分度圆、齿顶/齿根圆）。",
            page,
        )
        subtitle_label.setObjectName("SectionHint")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        body = QVBoxLayout(container)
        body.setContentsMargins(2, 2, 2, 2)
        body.setSpacing(10)

        top_groups = QHBoxLayout()
        top_groups.setSpacing(10)
        top_groups.addWidget(self._create_group_input_card("蜗杆参数", WORM_GEOMETRY_FIELDS, container), 1)
        top_groups.addWidget(self._create_group_input_card("蜗轮参数", WHEEL_GEOMETRY_FIELDS, container), 1)
        body.addLayout(top_groups)

        body.addWidget(self._create_group_input_card("啮合与装配", MESH_GEOMETRY_FIELDS, container))

        preview_hint = QLabel("修改基础输入后，下面的只读尺寸会即时更新。", container)
        preview_hint.setObjectName("SectionHint")
        preview_hint.setWordWrap(True)
        body.addWidget(preview_hint)

        preview_groups = QHBoxLayout()
        preview_groups.setSpacing(10)
        preview_groups.addWidget(
            self._create_dimension_group_card("蜗杆自动计算尺寸", WORM_DIMENSION_FIELDS, self.worm_dimension_labels, container),
            1,
        )
        preview_groups.addWidget(
            self._create_dimension_group_card("蜗轮自动计算尺寸", WHEEL_DIMENSION_FIELDS, self.wheel_dimension_labels, container),
            1,
        )
        body.addLayout(preview_groups)
        body.addWidget(self._create_group_input_card("高级参数", ADVANCED_FIELDS, container))
        body.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        return page

    def _create_group_input_card(self, title: str, fields: list[FieldSpec], parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel(title, card)
        title_label.setObjectName("SubSectionTitle")
        layout.addWidget(title_label)

        for spec in fields:
            layout.addWidget(self._create_input_row_card(spec, card))
        return card

    def _create_input_row_card(self, spec: FieldSpec, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        row = QGridLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setHorizontalSpacing(10)
        row.setVerticalSpacing(4)

        label = QLabel(spec.label, card)
        label.setObjectName("SubSectionTitle")
        editor = self._create_input(spec, card)
        unit = QLabel(spec.unit, card)
        unit.setObjectName("SectionHint")
        hint = QLabel(spec.hint, card)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)

        row.addWidget(label, 0, 0)
        row.addWidget(editor, 0, 1)
        row.addWidget(unit, 0, 2)
        row.addWidget(hint, 1, 0, 1, 3)
        return card

    def _create_dimension_group_card(
        self,
        title: str,
        fields: list[tuple[str, str, str, str]],
        target: dict[str, QLabel],
        parent: QWidget,
    ) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("AutoCalcCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel(title, card)
        title_label.setObjectName("SubSectionTitle")
        layout.addWidget(title_label)

        for key, label_text, unit_text, hint_text in fields:
            row_card = QFrame(card)
            row_card.setObjectName("AutoCalcCard")
            row = QGridLayout(row_card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setHorizontalSpacing(10)
            row.setVerticalSpacing(4)

            label = QLabel(label_text, row_card)
            label.setObjectName("SubSectionTitle")
            value_label = QLabel("待输入", row_card)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setObjectName("SectionHint")
            value_label.setStyleSheet("color: #3A4F63; font-weight: 600;")
            unit = QLabel(unit_text, row_card)
            unit.setObjectName("SectionHint")
            hint = QLabel(hint_text, row_card)
            hint.setWordWrap(True)
            hint.setObjectName("SectionHint")

            row.addWidget(label, 0, 0)
            row.addWidget(value_label, 0, 1)
            row.addWidget(unit, 0, 2)
            row.addWidget(hint, 1, 0, 1, 3)
            layout.addWidget(row_card)
            target[key] = value_label
        return card

    def _create_input(self, spec: FieldSpec, parent: QWidget) -> QWidget:
        if spec.widget_type == "choice":
            combo = QComboBox(parent)
            combo.addItems(spec.options)
            if spec.default:
                index = combo.findText(spec.default)
                if index >= 0:
                    combo.setCurrentIndex(index)
            if spec.field_id.startswith("geometry."):
                combo.currentTextChanged.connect(lambda _text: self._schedule_preview())
            self._field_widgets[spec.field_id] = combo
            self._field_specs[spec.field_id] = spec
            return combo

        editor = QLineEdit(parent)
        editor.setText(spec.default)
        if spec.placeholder:
            editor.setPlaceholderText(spec.placeholder)
        if spec.field_id.startswith("geometry."):
            editor.textChanged.connect(lambda _text: self._schedule_preview())
        self._field_widgets[spec.field_id] = editor
        self._field_specs[spec.field_id] = spec
        return editor

    def _build_graphics_step(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("图形与曲线", page)
        title.setObjectName("SectionTitle")
        hint = QLabel("几何图先用高质量占位图，性能曲线在接入计算后展示真实结果。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        self.graphics_scroll_area = QScrollArea(page)
        self.graphics_scroll_area.setWidgetResizable(True)
        self.graphics_scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(self.graphics_scroll_area)
        body = QVBoxLayout(container)
        body.setContentsMargins(2, 2, 2, 2)
        body.setSpacing(10)

        self.geometry_overview = WormGeometryOverviewWidget(container)
        self.performance_curve = WormPerformanceCurveWidget(container)
        self.stress_curve = WormStressCurveWidget(container)
        body.addWidget(self.geometry_overview)
        body.addWidget(self.performance_curve)
        body.addWidget(self.stress_curve)
        body.addStretch(1)

        self.graphics_scroll_area.setWidget(container)
        layout.addWidget(self.graphics_scroll_area)
        self.add_chapter("图形与曲线", page)

    def _build_load_capacity_step(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Load Capacity", page)
        title.setObjectName("SectionTitle")
        hint = QLabel("齿面/齿根负载能力校核的参数：许用应力、动载系数 Kv、载荷分配系数 KHα/KHβ 以及目标安全系数。对齿面和齿根分别算出 SH/SF 后与目标值对比判断通过/不通过。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        self.load_capacity_status = QLabel("DIN 3996 校核尚未开始", page)
        self.load_capacity_status.setObjectName("WaitBadge")
        self.load_capacity_note = QLabel(
            "当前版本输出 Method B 最小子集结果，不替代完整标准实现；所有简化假设都会在结果区显式说明。",
            page,
        )
        self.load_capacity_note.setObjectName("SectionHint")
        self.load_capacity_note.setWordWrap(True)
        self.load_capacity_metrics = QPlainTextEdit(page)
        self.load_capacity_metrics.setReadOnly(True)
        self.load_capacity_metrics.setMinimumHeight(240)
        self.load_capacity_metrics.setPlainText("尚无 Load Capacity 结果。")

        self._check_badges: dict[str, tuple[QLabel, QLabel]] = {}
        badges_card = QFrame(page)
        badges_card.setObjectName("SubCard")
        badges_layout = QVBoxLayout(badges_card)
        badges_layout.setContentsMargins(12, 12, 12, 12)
        badges_layout.setSpacing(6)
        badges_title = QLabel("校核徽章", badges_card)
        badges_title.setObjectName("SubSectionTitle")
        badges_layout.addWidget(badges_title)
        for key, label_text in [
            ("contact_ok", "齿面应力校核"),
            ("root_ok", "齿根应力校核"),
            ("geometry_consistent", "几何一致性"),
        ]:
            row = QHBoxLayout()
            name_label = QLabel(label_text, badges_card)
            name_label.setObjectName("SectionHint")
            badge = QLabel("待计算", badges_card)
            badge.setObjectName("WaitBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedHeight(28)
            row.addWidget(name_label)
            row.addStretch(1)
            row.addWidget(badge)
            badges_layout.addLayout(row)
            self._check_badges[key] = (name_label, badge)

        overall_row = QHBoxLayout()
        overall_name = QLabel("总体校核", badges_card)
        overall_name.setObjectName("SubSectionTitle")
        self._overall_lc_badge = QLabel("待计算", badges_card)
        self._overall_lc_badge.setObjectName("WaitBadge")
        self._overall_lc_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overall_lc_badge.setFixedHeight(28)
        overall_row.addWidget(overall_name)
        overall_row.addStretch(1)
        overall_row.addWidget(self._overall_lc_badge)
        badges_layout.addLayout(overall_row)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.load_capacity_status, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.load_capacity_note)
        self._lc_params_card = self._create_group_input_card("Method B 最小子集参数", LOAD_CAPACITY_PARAMETER_FIELDS, page)
        layout.addWidget(self._lc_params_card)
        layout.addWidget(badges_card)

        formulas_card = QFrame(page)
        formulas_card.setObjectName("AutoCalcCard")
        formulas_layout = QVBoxLayout(formulas_card)
        formulas_layout.setContentsMargins(12, 12, 12, 12)
        formulas_layout.setSpacing(8)

        formulas_title = QLabel("校核公式", formulas_card)
        formulas_title.setObjectName("SubSectionTitle")
        formulas_layout.addWidget(formulas_title)

        self._latex_hertz = LatexLabel(formulas_card)
        self._latex_hertz.set_latex(
            r"$\sigma_H = \sqrt{\frac{F_n \cdot E^*}{\pi \cdot L_c \cdot \rho_{eq}}}$",
            fontsize=16,
        )
        formulas_layout.addWidget(self._latex_hertz)

        self._latex_root = LatexLabel(formulas_card)
        self._latex_root.set_latex(
            r"$\sigma_F = \frac{F_t \cdot h}{W_{section}}$",
            fontsize=16,
        )
        formulas_layout.addWidget(self._latex_root)

        layout.addWidget(formulas_card)
        layout.addWidget(self.load_capacity_metrics)
        layout.addStretch(1)
        self.add_chapter("Load Capacity", page, help_ref="modules/worm/_section_load_capacity")

    def _build_results_step(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("结果与报告", page)
        title.setObjectName("SectionTitle")
        self.result_title = QLabel("尚未执行计算", page)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel("执行计算后显示 DIN 3975 几何结果、基础性能和 Load Capacity 延后状态。", page)
        self.result_summary.setObjectName("SectionHint")
        self.result_summary.setWordWrap(True)
        self.result_metrics = QPlainTextEdit(page)
        self.result_metrics.setReadOnly(True)
        self.result_metrics.setMinimumHeight(180)
        self.result_metrics.setPlainText("尚无结果。")

        # 效率与自锁副标题卡
        self._efficiency_subtitle_card = QFrame(page)
        self._efficiency_subtitle_card.setObjectName("SubCard")
        eff_layout = QVBoxLayout(self._efficiency_subtitle_card)
        eff_layout.setContentsMargins(12, 10, 12, 10)
        eff_layout.setSpacing(4)
        eff_card_title = QLabel("效率与自锁分析", self._efficiency_subtitle_card)
        eff_card_title.setObjectName("SubSectionTitle")
        self._efficiency_subtitle_label = QLabel("执行计算后显示。", self._efficiency_subtitle_card)
        self._efficiency_subtitle_label.setObjectName("SectionHint")
        self._efficiency_subtitle_label.setWordWrap(True)
        eff_layout.addWidget(eff_card_title)
        eff_layout.addWidget(self._efficiency_subtitle_label)
        self._efficiency_subtitle_card.setVisible(False)

        # 寿命评估卡
        self._life_card = QFrame(page)
        self._life_card.setObjectName("SubCard")
        life_layout = QVBoxLayout(self._life_card)
        life_layout.setContentsMargins(12, 12, 12, 12)
        life_layout.setSpacing(6)
        life_card_title = QLabel("寿命评估", self._life_card)
        life_card_title.setObjectName("SubSectionTitle")
        life_layout.addWidget(life_card_title)

        self._life_row_labels: dict[str, QLabel] = {}
        for row_key, row_label_text in [
            ("fatigue_life_hours", "疲劳寿命"),
            ("wear_depth_mm_per_hour", "磨损速率"),
            ("wear_life_hours_until_0p3mm", "磨损寿命 (至 0.3 mm)"),
            ("sliding_velocity_mps", "滑动速度"),
        ]:
            row_frame = QFrame(self._life_card)
            row_frame.setObjectName("AutoCalcCard")
            row_h = QHBoxLayout(row_frame)
            row_h.setContentsMargins(8, 6, 8, 6)
            row_h.setSpacing(8)
            row_name = QLabel(row_label_text, row_frame)
            row_name.setObjectName("SectionHint")
            row_val = QLabel("—", row_frame)
            row_val.setObjectName("SectionHint")
            row_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row_val.setStyleSheet("color: #3A4F63; font-weight: 600;")
            row_h.addWidget(row_name)
            row_h.addStretch(1)
            row_h.addWidget(row_val)
            life_layout.addWidget(row_frame)
            self._life_row_labels[row_key] = row_val

        self._life_card.setVisible(False)

        layout.addWidget(title)
        layout.addWidget(self.result_title)
        layout.addWidget(self.result_summary)
        layout.addWidget(self.result_metrics)
        layout.addWidget(self._efficiency_subtitle_card)
        layout.addWidget(self._life_card)
        self.add_chapter("结果与报告", page)

    def _read_widget_value(self, spec: FieldSpec) -> str:
        widget = self._field_widgets[spec.field_id]
        if spec.widget_type == "choice":
            return widget.currentText().strip()  # type: ignore[attr-defined]
        return widget.text().strip()  # type: ignore[attr-defined]

    def _apply_defaults(self) -> None:
        for spec in self._field_specs.values():
            widget = self._field_widgets[spec.field_id]
            if spec.widget_type == "choice":
                index = widget.findText(spec.default)  # type: ignore[attr-defined]
                if index >= 0:
                    widget.setCurrentIndex(index)  # type: ignore[attr-defined]
            else:
                widget.setText(spec.default)  # type: ignore[attr-defined]
        self._refresh_derived_geometry_preview()

    def _capture_input_snapshot(self) -> dict[str, Any]:
        return build_form_snapshot(self._field_specs.values(), self._read_widget_value)

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        self._field_widgets["materials.worm_material"].blockSignals(True)
        self._field_widgets["materials.wheel_material"].blockSignals(True)
        ui_state_data = data.get("ui_state")
        ui_state = ui_state_data if isinstance(ui_state_data, dict) else {}
        inputs_data = data.get("inputs")
        inputs = inputs_data if isinstance(inputs_data, dict) else {}
        self._apply_defaults()
        for spec in self._field_specs.values():
            if spec.field_id in ui_state:
                value = ui_state[spec.field_id]
            else:
                section, key = spec.field_id.split(".", 1)
                section_data = inputs.get(section)
                if not isinstance(section_data, dict) or key not in section_data:
                    section_data = data.get(section)
                if not isinstance(section_data, dict) or key not in section_data:
                    continue
                value = section_data[key]
            widget = self._field_widgets[spec.field_id]
            if spec.widget_type == "choice":
                if spec.field_id == "load_capacity.enabled":
                    text = "启用" if value in (True, "启用", "true") else "关闭"
                else:
                    text = str(value)
                index = widget.findText(text)  # type: ignore[attr-defined]
                if index >= 0:
                    widget.setCurrentIndex(index)  # type: ignore[attr-defined]
            else:
                widget.setText(str(value))  # type: ignore[attr-defined]
        self._field_widgets["materials.worm_material"].blockSignals(False)
        self._field_widgets["materials.wheel_material"].blockSignals(False)
        self._refresh_derived_geometry_preview()

    def _build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for spec in self._field_specs.values():
            raw = self._read_widget_value(spec)
            if raw == "":
                continue
            if spec.widget_type == "choice":
                if spec.field_id == "load_capacity.enabled":
                    value: Any = raw == "启用"
                else:
                    value = raw
            elif spec.widget_type == "text":
                value = raw
            else:
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise InputError(f"字段 {spec.label} 请输入数字，当前值: {raw}") from exc
            section, key = spec.field_id.split(".", 1)
            payload.setdefault(section, {})[key] = value
        return payload

    def _set_card_style(self, field_id: str, *, auto: bool) -> None:
        """将字段的外层 SubCard frame 切换为 AutoCalcCard（auto=True）或 SubCard（auto=False）。
        同时设置 QLineEdit 的 readOnly 状态。
        """
        widget = self._field_widgets.get(field_id)
        if widget is None:
            return
        # 找到直接父 frame（即 _create_input_row_card 返回的 card）
        parent_frame = widget.parent()
        if isinstance(parent_frame, QWidget):
            # 向上找到 QFrame（SubCard 级别）
            frame = parent_frame if isinstance(parent_frame, QFrame) else None
            if frame is None:
                return
            obj_name = "AutoCalcCard" if auto else "SubCard"
            frame.setObjectName(obj_name)
            frame.style().unpolish(frame)
            frame.style().polish(frame)
            for child in frame.findChildren(QWidget):
                child.style().unpolish(child)
                child.style().polish(child)
        if isinstance(widget, QLineEdit):
            widget.setReadOnly(auto)
        elif isinstance(widget, QComboBox):
            widget.setEnabled(not auto)

    def _apply_plastic_defaults(self, material_name: str) -> None:
        """从塑料材料库自动填充弹性参数和许用应力，并切换为 AutoCalcCard 样式。

        许用应力按当前 advanced.operating_temp_c 和 advanced.humidity_rh 降额，
        与 core 计算保持一致，避免用户看到名义值而 core 用降额值导致的歧义。
        """
        if not _PLASTIC_MATERIALS_AVAILABLE:
            return
        mat = PLASTIC_MATERIALS.get(material_name)
        if mat is None:
            # 未知材料：解锁字段让用户手动输入
            for fid in ("materials.wheel_e_mpa", "materials.wheel_nu",
                        "load_capacity.allowable_contact_stress_mpa",
                        "load_capacity.allowable_root_stress_mpa"):
                self._set_card_style(fid, auto=False)
            return
        # 读取当前工况温湿度，与 core 降额模型保持一致
        from core.worm.materials import apply_derate
        try:
            op_t = float(self._field_widgets["advanced.operating_temp_c"].text() or 23.0)
        except (KeyError, ValueError):
            op_t = 23.0
        try:
            rh = float(self._field_widgets["advanced.humidity_rh"].text() or 50.0)
        except (KeyError, ValueError):
            rh = 50.0
        sigma_hlim_d, sigma_flim_d = apply_derate(mat, operating_temp_c=op_t, humidity_rh=rh)
        # 填充默认值（E / ν 不随温湿度变化，σ 用降额后值）
        w_e = self._field_widgets.get("materials.wheel_e_mpa")
        if isinstance(w_e, QLineEdit):
            w_e.setReadOnly(False)
            w_e.setText(str(mat.e_mpa))
        w_nu = self._field_widgets.get("materials.wheel_nu")
        if isinstance(w_nu, QLineEdit):
            w_nu.setReadOnly(False)
            w_nu.setText(str(mat.nu))
        w_contact = self._field_widgets.get("load_capacity.allowable_contact_stress_mpa")
        if isinstance(w_contact, QLineEdit):
            w_contact.setReadOnly(False)
            w_contact.setText(f"{sigma_hlim_d:.2f}")
        w_root = self._field_widgets.get("load_capacity.allowable_root_stress_mpa")
        if isinstance(w_root, QLineEdit):
            w_root.setReadOnly(False)
            w_root.setText(f"{sigma_flim_d:.2f}")
        # 切换为 AutoCalcCard 样式（setReadOnly 在 _set_card_style 里处理）
        for fid in ("materials.wheel_e_mpa", "materials.wheel_nu",
                    "load_capacity.allowable_contact_stress_mpa",
                    "load_capacity.allowable_root_stress_mpa"):
            self._set_card_style(fid, auto=True)

    def _on_material_changed(self) -> None:
        from core.worm.calculator import MATERIAL_ELASTIC_HINTS, MATERIAL_ALLOWABLE_HINTS, MATERIAL_FRICTION_HINTS
        worm_mat = self._field_widgets["materials.worm_material"].currentText()
        wheel_mat = self._field_widgets["materials.wheel_material"].currentText()
        worm_hints = MATERIAL_ELASTIC_HINTS.get(worm_mat, {})
        wheel_hints = MATERIAL_ELASTIC_HINTS.get(wheel_mat, {})
        allowable_hints = MATERIAL_ALLOWABLE_HINTS.get(wheel_mat, {})
        if worm_hints:
            self._field_widgets["materials.worm_e_mpa"].setText(str(worm_hints["e_mpa"]))
            self._field_widgets["materials.worm_nu"].setText(str(worm_hints["nu"]))
            # 蜗杆弹性参数由材料下拉派生 -> AutoCalcCard
            for fid in ("materials.worm_e_mpa", "materials.worm_nu"):
                self._set_card_style(fid, auto=True)
        else:
            # 未知蜗杆材料：解锁手动输入
            for fid in ("materials.worm_e_mpa", "materials.worm_nu"):
                self._set_card_style(fid, auto=False)
        if wheel_hints:
            self._field_widgets["materials.wheel_e_mpa"].setText(str(wheel_hints["e_mpa"]))
            self._field_widgets["materials.wheel_nu"].setText(str(wheel_hints["nu"]))
            for fid in ("materials.wheel_e_mpa", "materials.wheel_nu"):
                self._set_card_style(fid, auto=True)
        else:
            for fid in ("materials.wheel_e_mpa", "materials.wheel_nu"):
                self._set_card_style(fid, auto=False)
        if allowable_hints:
            self._field_widgets["load_capacity.allowable_contact_stress_mpa"].setText(str(allowable_hints["contact_mpa"]))
            self._field_widgets["load_capacity.allowable_root_stress_mpa"].setText(str(allowable_hints["root_mpa"]))
            for fid in ("load_capacity.allowable_contact_stress_mpa", "load_capacity.allowable_root_stress_mpa"):
                self._set_card_style(fid, auto=True)
        # 塑料材料库优先：若 PLASTIC_MATERIALS 中有该材料，覆盖上面的填充并设为 AutoCalcCard
        self._apply_plastic_defaults(wheel_mat)
        default_mu = MATERIAL_FRICTION_HINTS.get((worm_mat, wheel_mat), 0.20)
        self._field_widgets["advanced.friction_override"].setPlaceholderText(f"留空则自动 \u03bc={default_mu:.2f}")
        self._refresh_derived_geometry_preview()

    def _on_method_changed(self, method_label: str) -> None:
        if "Method C" in method_label:
            self.set_info("提示：Method C 需要 FEA 输入，当前版本未实现；执行将报错。")
        else:
            self.set_info("按左侧顺序输入 DIN 3975 / Method B 参数，再执行计算。")

    def _on_lc_enabled_changed(self, text: str) -> None:
        disabled = text != "启用"
        style_name = "AutoCalcCard" if disabled else "SubCard"
        self._lc_params_card.setObjectName(style_name)
        self._lc_params_card.style().unpolish(self._lc_params_card)
        self._lc_params_card.style().polish(self._lc_params_card)
        for child in self._lc_params_card.findChildren(QFrame):
            child.setObjectName(style_name)
            child.style().unpolish(child)
            child.style().polish(child)
        for child in self._lc_params_card.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
        for spec_id in (
            "load_capacity.allowable_contact_stress_mpa",
            "load_capacity.allowable_root_stress_mpa",
            "load_capacity.dynamic_factor_kv",
            "load_capacity.transverse_load_factor_kha",
            "load_capacity.face_load_factor_khb",
            "load_capacity.required_contact_safety",
            "load_capacity.required_root_safety",
        ):
            widget = self._field_widgets.get(spec_id)
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(disabled)

    def _schedule_preview(self) -> None:
        """Throttled signal handler: restarts 300 ms timer on every keystroke.

        Signals from input widgets connect here to avoid recalculating on every
        intermediate keystroke.  The actual calculation fires via the timer.
        """
        self._preview_timer.start()

    def _refresh_derived_geometry_preview(self) -> None:
        """Immediate geometry preview update (for programmatic callers and _apply_defaults).

        Direct callers bypass the timer; signals from input widgets should use
        _schedule_preview instead.
        """
        self._do_refresh_preview()

    def _do_refresh_preview(self) -> None:
        """Actual geometry preview calculation, called by timer or directly."""
        self._preview_call_count += 1
        try:
            payload = self._build_payload()
            geometry = calculate_worm_geometry(payload)["geometry"]
        except (InputError, ValueError):
            self._reset_dimension_preview_labels()
            self.set_info("输入不完整或无效，预览已重置")
            return

        self._set_dimension_group_values(self.worm_dimension_labels, geometry.get("worm_dimensions", {}), WORM_DIMENSION_FIELDS)
        self._set_dimension_group_values(self.wheel_dimension_labels, geometry.get("wheel_dimensions", {}), WHEEL_DIMENSION_FIELDS)

    def _reset_dimension_preview_labels(self) -> None:
        for label in list(self.worm_dimension_labels.values()) + list(self.wheel_dimension_labels.values()):
            label.setText("待输入")

    # ------------------------------------------------------------------
    # Step 3: dirty-state helpers
    # ------------------------------------------------------------------
    def _mark_results_dirty(self) -> None:
        """Called on any input change: disable export, show stale warning."""
        self.btn_save.setEnabled(False)
        self._result_status_label.setText("结果已过期，请重新执行计算。")
        self._result_status_label.setStyleSheet("color: #C44536;")

    def _mark_results_fresh(self) -> None:
        """Called after successful calculation: enable export, clear warning."""
        self.btn_save.setEnabled(True)
        self._result_status_label.setText("")
        self._result_status_label.setStyleSheet("")

    def _connect_dirty_signals(self) -> None:
        """Connect every FieldSpec widget's change signal to _mark_results_dirty."""
        for fid, widget in self._field_widgets.items():
            if isinstance(widget, QLineEdit):
                widget.textEdited.connect(self._mark_results_dirty)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._mark_results_dirty)

    def _set_dimension_group_values(
        self,
        labels: dict[str, QLabel],
        values: dict[str, Any],
        specs: list[tuple[str, str, str, str]],
    ) -> None:
        for key, _label, unit_text, _hint in specs:
            value = values.get(key)
            if isinstance(value, (int, float)):
                labels[key].setText(self._format_value(value, unit_text))
            else:
                labels[key].setText("待输入")

    @staticmethod
    def _format_value(value: float, unit_text: str) -> str:
        if unit_text == "-":
            return f"{value:.3f}"
        return f"{value:.3f} {unit_text}"

    def _set_badge(self, label: QLabel, text: str, level: str) -> None:
        label.setText(text)
        obj_name = "PassBadge" if level == "pass" else ("FailBadge" if level == "fail" else "WaitBadge")
        label.setObjectName(obj_name)
        label.style().unpolish(label)
        label.style().polish(label)

    def _calculate(self) -> None:
        try:
            payload = self._build_payload()
            self._last_payload = payload
            result = calculate_worm_geometry(payload)
        except InputError as exc:
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        self._last_result = result
        geometry = result["geometry"]
        performance = result["performance"]
        curve = result["curve"]
        load_capacity = result["load_capacity"]
        worm_dimensions = geometry["worm_dimensions"]
        wheel_dimensions = geometry["wheel_dimensions"]
        contact = load_capacity.get("contact", {})
        root = load_capacity.get("root", {})
        ripple = load_capacity.get("torque_ripple", {})
        warnings = load_capacity.get("warnings", [])
        checks = load_capacity.get("checks", {})
        lc_enabled = bool(load_capacity.get("enabled", len(checks) > 0))

        self.result_title.setText("已完成蜗杆副几何、基础性能与 Method B 最小校核")
        self.result_summary.setText("当前版本已输出几何结果、效率估算、齿面应力、齿根应力和扭矩波动摘要。")

        # W-03: 当 LC 未启用时，应力/力/扭矩显示"未启用"而非 0.000
        if lc_enabled:
            sigma_hm_line = f"齿面应力 sigma_Hm = {contact.get('sigma_hm_peak_mpa', 0.0):.3f} MPa"
            sigma_f_line = f"齿根应力 sigma_F = {root.get('sigma_f_peak_mpa', 0.0):.3f} MPa"
            ripple_line = f"扭矩波动 peak = {ripple.get('output_torque_peak_nm', 0.0):.3f} N·m"
        else:
            sigma_hm_line = "齿面应力 sigma_Hm = 未启用"
            sigma_f_line = "齿根应力 sigma_F = 未启用"
            ripple_line = "扭矩波动 peak = 未启用"

        self.result_metrics.setPlainText(
            "\n".join(
                [
                    f"传动比 i = {geometry['ratio']:.3f}",
                    f"中心距 a = {geometry['center_distance_mm']:.3f} mm",
                    f"理论中心距 a_th = {geometry['theoretical_center_distance_mm']:.3f} mm",
                    f"蜗杆分度圆直径 d1 = {worm_dimensions['pitch_diameter_mm']:.3f} mm",
                    f"蜗轮分度圆直径 d2 = {wheel_dimensions['pitch_diameter_mm']:.3f} mm",
                    f"导程角 gamma = {geometry['lead_angle_deg']:.3f} deg",
                    f"效率估算 eta = {performance['efficiency_estimate']:.4f}",
                    f"输入功率 P1 = {performance['input_power_kw']:.4f} kW（反算）",
                    f"输出功率 P2 = {performance['output_power_kw']:.4f} kW",
                    f"输出扭矩 T2 = {performance['output_torque_nm']:.3f} N·m",
                    f"损失功率 = {performance['power_loss_kw']:.4f} kW",
                    sigma_hm_line,
                    sigma_f_line,
                    ripple_line,
                ]
            )
        )
        # 温升曲线：优先用 core 提供的 temperature_rise_k，否则从热容量派生
        thermal_cap_kw_curve = curve.get("thermal_capacity_kw", [])
        power_loss_curve = curve.get("power_loss_kw", [])
        if curve.get("temperature_rise_k"):
            temp_rise_curve = curve["temperature_rise_k"]
        elif thermal_cap_kw_curve and power_loss_curve:
            # 简化派生：ΔT ≈ P_loss / Q_th * 50 K（50 K 为参考允许温升）
            temp_rise_curve = [
                p / max(q, 1e-6) * 50.0
                for p, q in zip(power_loss_curve, thermal_cap_kw_curve)
            ]
        else:
            temp_rise_curve = []
        self.performance_curve.set_curves(
            load_factor=curve["load_factor"],
            efficiency=curve["efficiency"],
            power_loss_kw=curve["power_loss_kw"],
            temperature_rise_k=temp_rise_curve,
            current_index=curve["current_index"],
        )
        stress_curve_data = load_capacity.get("stress_curve", {})
        if stress_curve_data and stress_curve_data.get("theta_deg"):
            self.stress_curve.set_curves(
                theta_deg=stress_curve_data["theta_deg"],
                sigma_h_mpa=stress_curve_data["sigma_h_mpa"],
                sigma_f_mpa=stress_curve_data["sigma_f_mpa"],
                sigma_h_nominal_mpa=stress_curve_data.get("sigma_h_nominal_mpa", 0.0),
                sigma_f_nominal_mpa=stress_curve_data.get("sigma_f_nominal_mpa", 0.0),
            )
        # 更新几何总览动态绘制（Step 4）
        inputs_echo = result.get("inputs_echo", {})
        echo_geometry = inputs_echo.get("geometry", {})
        echo_materials = inputs_echo.get("materials", {})
        self.geometry_overview.set_geometry_state(
            d1_mm=worm_dimensions.get("pitch_diameter_mm", geometry.get("pitch_diameter_worm_mm", 40.0)),
            d2_mm=wheel_dimensions.get("pitch_diameter_mm", geometry.get("pitch_diameter_wheel_mm", 160.0)),
            a_mm=geometry["center_distance_mm"],
            gamma_deg=geometry.get("lead_angle_calc_deg", geometry.get("lead_angle_deg", 11.31)),
            z1=int(echo_geometry.get("z1", payload.get("geometry", {}).get("z1", 2))),
            z2=int(echo_geometry.get("z2", payload.get("geometry", {}).get("z2", 40))),
            handedness=echo_materials.get("handedness", payload.get("materials", {}).get("handedness", "right")),
        )
        self.geometry_overview.set_display_state(
            "几何总览",
            f"i={geometry['ratio']:.2f}，a={geometry['center_distance_mm']:.1f} mm，gamma={geometry.get('lead_angle_calc_deg', geometry.get('lead_angle_deg', 0.0)):.1f} deg",
        )
        self.load_capacity_status.setText(load_capacity["status"])

        # W-03: LC 未启用时，负载能力详情区显示"未计算"占位
        if lc_enabled:
            lc_metrics_lines = [
                f"sigma_Hm,nom = {contact.get('sigma_hm_nominal_mpa', 0.0):.3f} MPa",
                f"sigma_Hm,peak = {contact.get('sigma_hm_peak_mpa', 0.0):.3f} MPa",
                f"SH_peak = {contact.get('safety_factor_peak', 0.0):.3f}",
                f"sigma_F,nom = {root.get('sigma_f_nominal_mpa', 0.0):.3f} MPa",
                f"sigma_F,peak = {root.get('sigma_f_peak_mpa', 0.0):.3f} MPa",
                f"SF_peak = {root.get('safety_factor_peak', 0.0):.3f}",
                f"T2_nom = {ripple.get('output_torque_nominal_nm', 0.0):.3f} N·m",
                f"T2_rms = {ripple.get('output_torque_rms_nm', 0.0):.3f} N·m",
                f"T2_peak = {ripple.get('output_torque_peak_nm', 0.0):.3f} N·m",
                f"几何一致性 = {'通过' if checks.get('geometry_consistent', False) else '存在警告'}",
                *[f"warning: {msg}" for msg in warnings],
            ]
        else:
            lc_metrics_lines = [
                "负载能力校核：未启用",
                "如需校核齿面/齿根安全系数，请在【基本设置】中启用 Load Capacity 页。",
                *[f"warning: {msg}" for msg in warnings],
            ]

        self.load_capacity_metrics.setPlainText("\n".join(lc_metrics_lines))
        self._refresh_derived_geometry_preview()

        # W-03 + W-02: LC 未启用时不显示通过/不通过徽章；几何不一致时总体为不通过
        if lc_enabled:
            for key, (_, badge) in self._check_badges.items():
                ok = checks.get(key, False)
                self._set_badge(badge, "通过" if ok else "不通过", "pass" if ok else "fail")
            # W-02: 总体判定纳入 geometry_consistent
            geometry_ok = checks.get("geometry_consistent", False)
            overall_lc_ok = geometry_ok and checks.get("contact_ok", False) and checks.get("root_ok", False)
            self._set_badge(
                self._overall_lc_badge,
                "总体通过" if overall_lc_ok else "总体不通过",
                "pass" if overall_lc_ok else "fail",
            )
            if overall_lc_ok:
                self.set_overall_status("Load Capacity 通过", "pass")
            else:
                self.set_overall_status("Load Capacity 需复核", "wait")
        else:
            # LC 未启用：徽章显示"未启用"，整体状态为等待
            for _key, (_, badge) in self._check_badges.items():
                self._set_badge(badge, "未启用", "wait")
            self._set_badge(self._overall_lc_badge, "未启用", "wait")
            self.set_overall_status("Load Capacity 未启用", "wait")
        # Step 4: 效率与自锁副标题
        lead_angle_calc_deg = geometry.get("lead_angle_calc_deg", geometry.get("lead_angle_deg", 0.0))
        friction_mu = performance.get("friction_mu", 0.0)
        alpha_n_deg = result.get("inputs_echo", {}).get("advanced", {}).get("normal_pressure_angle_deg", 20.0)
        try:
            phi_prime_deg = math.degrees(math.atan(friction_mu / math.cos(math.radians(float(alpha_n_deg)))))
        except (ValueError, ZeroDivisionError):
            phi_prime_deg = 0.0
        self_lock = lead_angle_calc_deg <= phi_prime_deg
        self._efficiency_subtitle_label.setText(
            f"gamma = {lead_angle_calc_deg:.2f} deg  /  phi' = {phi_prime_deg:.2f} deg  /  "
            f"自锁：{'是' if self_lock else '否'}"
        )
        self._efficiency_subtitle_card.setVisible(True)

        # Step 5: 寿命/磨损评估
        life = load_capacity.get("life", {})
        fatigue_h = life.get("fatigue_life_hours")
        wear_rate = life.get("wear_depth_mm_per_hour")
        wear_life = life.get("wear_life_hours_until_0p3mm")
        sliding_v = life.get("sliding_velocity_mps")
        self._life_row_labels["fatigue_life_hours"].setText(
            f"{fatigue_h:.0f} h" if fatigue_h is not None else "—"
        )
        self._life_row_labels["wear_depth_mm_per_hour"].setText(
            f"{wear_rate * 1000:.3f} \u00b5m/h" if wear_rate is not None else "—"
        )
        self._life_row_labels["wear_life_hours_until_0p3mm"].setText(
            f"{wear_life:.0f} h" if wear_life is not None else "—"
        )
        self._life_row_labels["sliding_velocity_mps"].setText(
            f"{sliding_v:.2f} m/s" if sliding_v is not None else "—"
        )
        self._life_card.setVisible(True)

        self.set_info("已完成蜗杆副几何、基础性能与 Method B 最小子集计算。")
        self._mark_results_fresh()
        self.set_current_chapter(self.chapter_stack.count() - 1)

    def _export_report(self) -> None:
        if self._last_result is None:
            QMessageBox.warning(self, "无结果", "请先执行计算。")
            return
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出计算报告", "worm_report.pdf",
            "PDF Files (*.pdf);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = out_path.suffix.lower()
        if suffix == ".pdf":
            try:
                import importlib
                mod = importlib.import_module("app.ui.report_pdf_worm")
                mod.generate_worm_report(out_path, self._last_payload or {}, self._last_result)
            except Exception:
                # Fallback to text
                out_path = out_path.with_suffix(".txt")
                self._write_text_report(out_path)
        else:
            self._write_text_report(out_path)
        self.set_info(f"报告已导出: {out_path}")

    def _write_text_report(self, path: Path) -> None:
        from datetime import datetime
        note = self._last_result.get("inputs_echo", {}).get("meta", {}).get("note", "")
        header = f"蜗杆副计算报告 -- {note}\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{'=' * 60}\n\n"
        body = self.result_metrics.toPlainText() + "\n\n" + self.load_capacity_metrics.toPlainText()
        path.write_text(header + body, encoding="utf-8")

    def _save_input_conditions(self) -> None:
        out_path = choose_save_input_conditions_path(
            self,
            "保存输入条件",
            SAVED_INPUTS_DIR / "worm_input_conditions.json",
        )
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
        self._mark_results_dirty()
        self.set_info(f"已加载输入条件：{in_path}")

    def _load_sample(self, filename: str) -> None:
        sample_path = EXAMPLES_DIR / filename
        if not sample_path.exists():
            QMessageBox.warning(self, "测试案例不存在", f"未找到测试案例文件：{sample_path}")
            return
        try:
            data = read_input_conditions(sample_path)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "测试案例损坏", f"测试案例文件不是有效 JSON：{exc}")
            return
        self._apply_input_data(data)
        self._mark_results_dirty()
        self.set_info(f"已加载测试案例：{filename}")

    def _clear(self) -> None:
        self._last_result = None
        self._last_payload = None
        self._apply_defaults()
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText("执行计算后显示几何、基础性能以及 Method B 最小子集结果。")
        self.result_metrics.setPlainText("尚无结果。")
        self.performance_curve.set_curves(
            load_factor=[],
            efficiency=[],
            power_loss_kw=[],
            temperature_rise_k=[],
            current_index=-1,
        )
        self.geometry_overview.set_display_state("几何总览", "按 DIN 3975 展示蜗杆、蜗轮、中心距与导程角关系。")
        self.load_capacity_status.setText("DIN 3996 校核尚未开始")
        self.load_capacity_metrics.setPlainText("尚无 Load Capacity 结果。")
        self.set_overall_status("等待计算", "wait")
        self._mark_results_dirty()
        self.set_info("参数已重置，可重新执行蜗杆副计算。")
