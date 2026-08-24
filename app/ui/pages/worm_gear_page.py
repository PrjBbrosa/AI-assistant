"""Worm gear module page with DIN 3975 first-pass workflow."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
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
    QSizePolicy,
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

from app.ui.field_schema import (
    FieldSchema,
    FieldSpec,
    build_payload,
    validate_text,
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
from app.ui.model_scope import (
    SOURCE_RECOMMENDED,
    SOURCE_USER,
    WORM_SCOPE,
    format_source_label,
    make_scope_banner,
    scope_report_lines,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import ReportExportError, write_text_report
from app.ui.report_trace import build_report_trace, trace_report_lines
from app.ui.result_contract import ResultViewModel, from_worm, status_label_zh
from app.ui.theme import mark_input_field_surface
from app.ui.widgets.app_combo_box import AppComboBox
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
ASSETS_DIR = PROJECT_ROOT / "app" / "assets"
MODULE_ID = "worm_gear"

# Load-capacity parameter fields stay on the page (layout unchanged) but only
# enter the calculator payload / live-error set while the toggle is 启用.
_LC_ENABLED = ("eq", "load_capacity.enabled", "启用")
_MATERIAL_SOURCE_FIELDS = (
    "materials.worm_e_mpa",
    "materials.worm_nu",
    "materials.wheel_e_mpa",
    "materials.wheel_nu",
    "load_capacity.allowable_contact_stress_mpa",
    "load_capacity.allowable_root_stress_mpa",
)
_FRICTION_OVERRIDE_PLACEHOLDER = "留空则自动"


BASIC_SETTINGS_FIELDS = [
    FieldSpec("meta.note", "项目备注", "-", "当前计算任务简述。", widget_type="text", default="Method B 最小子集"),
    FieldSpec(
        "load_capacity.enabled",
        "启用负载能力 (Load Capacity) 页",
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
        "Method B 使用当前解析预校核；Method A 叠加经验修正；Method C 需要 FEA 输入，当前版本会拒绝计算。",
        widget_type="choice",
        options=LOAD_CAPACITY_OPTIONS,
        default="DIN 3996 Method B -- 标准解析计算（推荐）",
        help_ref="modules/worm/din3996_method_b",
    ),
]

WORM_GEOMETRY_FIELDS = [
    FieldSpec("geometry.z1", "蜗杆头数 z1", "-", "蜗杆起始头数，必须为 1~6 的整数。", default="2", value_type="int", min_value=1.0, max_value=6.0),
    FieldSpec("geometry.module_mm", "模数 m", "mm", "几何主输入。", default="4.0", help_ref="terms/module"),
    FieldSpec("geometry.diameter_factor_q", "直径系数 q", "-", "蜗杆直径系数。", default="10.0", help_ref="terms/diameter_factor_q"),
    FieldSpec("geometry.lead_angle_deg", "导程角 gamma", "deg", "蜗杆导程角。默认值与 z1/q 保持自洽。", default="11.31", min_value=0.0, max_value=45.0, min_inclusive=False, help_ref="terms/lead_angle"),
    FieldSpec("geometry.worm_face_width_mm", "蜗杆齿宽 b1", "mm", "蜗杆工作齿宽。", default="32.0"),
    FieldSpec("geometry.x1", "蜗杆变位系数 x1", "-", "蜗杆齿形变位系数。", default="0.0", help_ref="terms/gear_profile_shift"),
]

WHEEL_GEOMETRY_FIELDS = [
    FieldSpec("geometry.z2", "蜗轮齿数 z2", "-", "蜗轮总齿数，必须为正整数。", default="40", value_type="int", min_value=1.0),
    FieldSpec("geometry.wheel_face_width_mm", "蜗轮齿宽 b2", "mm", "蜗轮工作齿宽。", default="28.0"),
    FieldSpec("geometry.x2", "蜗轮变位系数 x2", "-", "蜗轮齿形变位系数。塑料蜗轮常用大正变位。", default="0.0", help_ref="terms/gear_profile_shift"),
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
        help_ref="terms/worm_lubrication_mode",
    ),
    FieldSpec(
        "materials.worm_e_mpa",
        "蜗杆弹性模量 E1",
        "MPa",
        "Method B 最小子集使用的材料弹性参数。",
        default="210000",
        source_kind="preset",
        help_ref="terms/elastic_modulus",
    ),
    FieldSpec(
        "materials.worm_nu",
        "蜗杆泊松比 nu1",
        "-",
        "Method B 最小子集使用的材料弹性参数。",
        default="0.30",
        source_kind="preset",
        help_ref="terms/poisson_ratio",
    ),
    FieldSpec(
        "materials.wheel_e_mpa",
        "蜗轮弹性模量 E2",
        "MPa",
        "Method B 最小子集使用的材料弹性参数。",
        default="3000",
        source_kind="preset",
        help_ref="terms/elastic_modulus",
    ),
    FieldSpec(
        "materials.wheel_nu",
        "蜗轮泊松比 nu2",
        "-",
        "Method B 最小子集使用的材料弹性参数。",
        default="0.38",
        source_kind="preset",
        help_ref="terms/poisson_ratio",
    ),
]

OPERATING_FIELDS = [
    FieldSpec("operating.input_torque_nm", "输入扭矩 T1", "Nm", "蜗杆轴输入扭矩。", default="19.76", min_value=0.0, min_inclusive=False),
    FieldSpec("operating.speed_rpm", "输入转速 n", "rpm", "蜗杆轴转速。", default="1450", min_value=0.0, min_inclusive=False),
    FieldSpec(
        "operating.application_factor",
        "使用系数 KA",
        "-",
        "工况冲击影响的简化系数，须 >= 1。",
        default="1.25",
        min_value=1.0,
        help_ref="terms/gear_application_factor_ka",
    ),
    FieldSpec("operating.torque_ripple_percent", "扭矩波动", "%", "围绕名义扭矩的峰值波动幅值。", default="0.0"),
]

ADVANCED_FIELDS = [
    FieldSpec(
        "advanced.friction_override",
        "摩擦系数覆盖",
        "-",
        "为空时使用材料配对的默认经验值。",
        default="",
        required=False,
    ),
    FieldSpec("advanced.normal_pressure_angle_deg", "法向压力角 alpha_n", "deg", "力分解与最小齿面/齿根模型的几何参数。", default="20.0", help_ref="terms/gear_pressure_angle"),
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
        "环境相对湿度，允许 0~100%；材料模型在 50%RH 后按吸湿饱和值计算并给出提示。",
        default="50",
        min_value=0.0,
        max_value=100.0,
    ),
]

LOAD_CAPACITY_PARAMETER_FIELDS = [
    FieldSpec(
        "load_capacity.allowable_contact_stress_mpa",
        "许用齿面应力",
        "MPa",
        "用于最小齿面安全系数计算。",
        default="42.0",
        source_kind="preset",
        visible_when=_LC_ENABLED,
        help_ref="terms/allowable_contact_stress",
    ),
    FieldSpec(
        "load_capacity.allowable_root_stress_mpa",
        "许用齿根应力",
        "MPa",
        "用于最小齿根安全系数计算。",
        default="55.0",
        source_kind="preset",
        visible_when=_LC_ENABLED,
        help_ref="terms/allowable_root_stress",
    ),
    FieldSpec(
        "load_capacity.dynamic_factor_kv",
        "动载系数 Kv",
        "-",
        "最小子集中的动载放大系数，须 >= 1。",
        default="1.05",
        min_value=1.0,
        visible_when=_LC_ENABLED,
        help_ref="terms/kv_factor",
    ),
    FieldSpec(
        "load_capacity.transverse_load_factor_kha",
        "横向载荷系数 KHalpha",
        "-",
        "横向载荷分配系数，须 >= 1。",
        default="1.00",
        min_value=1.0,
        visible_when=_LC_ENABLED,
        help_ref="terms/kh_alpha",
    ),
    FieldSpec(
        "load_capacity.face_load_factor_khb",
        "齿宽载荷系数 KHbeta",
        "-",
        "齿宽方向载荷分配系数，须 >= 1。",
        default="1.10",
        min_value=1.0,
        visible_when=_LC_ENABLED,
        help_ref="terms/kh_beta",
    ),
    FieldSpec(
        "load_capacity.required_contact_safety",
        "目标齿面安全系数",
        "-",
        "用于通过/不通过判定，须 >= 1。",
        default="1.00",
        min_value=1.0,
        visible_when=_LC_ENABLED,
    ),
    FieldSpec(
        "load_capacity.required_root_safety",
        "目标齿根安全系数",
        "-",
        "用于通过/不通过判定，须 >= 1。",
        default="1.00",
        min_value=1.0,
        visible_when=_LC_ENABLED,
    ),
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
            title="蜗轮蜗杆 · DIN 3975",
            subtitle="几何、基础性能和 Method B 最小负载能力子集。",
            parent=parent,
        )
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSchema] = {}
        self._field_cards: dict[str, QFrame] = {}
        self._field_error_labels: dict[str, QLabel] = {}
        self._field_chapter_index: dict[str, int] = {}
        self._source_labels: dict[str, QLabel] = {}
        self._last_result: dict[str, Any] | None = None
        self._last_payload: dict[str, Any] | None = None
        self._suspend_live_feedback = True
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
        self.btn_calculate = self.add_action_button("执行校核", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_save = self.add_action_button("导出结果说明")
        self.btn_help_guide = self.add_guide_button("modules/worm/beginner_guide")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")
        # Step 3: dirty-state status label (reuses the base info area but also
        # keeps a dedicated QLabel we can show inline in the action row)
        self._result_status_label = QLabel("", self)
        self._result_status_label.setObjectName("ResultStaleHint")
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
        self._on_material_changed()
        self.set_current_chapter(0)
        self.chapter_list.currentRowChanged.connect(self._on_chapter_row_changed)
        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save.clicked.connect(self._export_report)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("worm_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("worm_case_02.json"))
        # Step 3: connect every input widget change to dirty-state marker
        self._connect_dirty_signals()
        self._suspend_live_feedback = False
        self._refresh_all_field_errors()
        self.set_info("按左侧顺序输入 DIN 3975 / Method B 参数，再执行计算。")

    def _build_input_steps(self) -> None:
        basic_index = self.add_chapter(
            "基本设置",
            self._create_form_page(
                "基本设置",
                "设置校核的范围和算法：是否启用齿面/齿根负载能力校核、选用 DIN 3996 的哪一种方法。",
                BASIC_SETTINGS_FIELDS,
            ),
            help_ref="modules/worm/_section_basic",
        )
        self._register_chapter_fields(basic_index, BASIC_SETTINGS_FIELDS)
        geometry_index = self.add_chapter(
            "几何参数",
            self._create_geometry_page(),
            help_ref="modules/worm/_section_geometry",
        )
        self._register_chapter_fields(
            geometry_index,
            WORM_GEOMETRY_FIELDS + WHEEL_GEOMETRY_FIELDS + MESH_GEOMETRY_FIELDS + ADVANCED_FIELDS,
        )
        material_index = self.add_chapter(
            "材料与配对",
            self._create_form_page(
                "材料与配对",
                "选择蜗杆/蜗轮材料；选中塑料蜗轮后会自动带入弹性模量和许用应力，也可手动覆盖。旋向与润滑方式会影响摩擦力与安全系数。",
                MATERIAL_FIELDS,
            ),
            help_ref="modules/worm/_section_material",
        )
        self._register_chapter_fields(material_index, MATERIAL_FIELDS)
        operating_index = self.add_chapter(
            "工况与润滑",
            self._create_form_page(
                "工况与润滑",
                "输入运行工况：输入扭矩 T1、转速 n、表征冲击与载荷波动的使用系数 KA、扭矩波动百分比。这些值直接影响齿面应力与动载系数 Kv 的计算。",
                OPERATING_FIELDS,
            ),
            help_ref="modules/worm/_section_operating",
        )
        self._register_chapter_fields(operating_index, OPERATING_FIELDS)

    def _register_chapter_fields(self, chapter_index: int, fields: list[FieldSchema]) -> None:
        for spec in fields:
            self._field_chapter_index[spec.field_id] = chapter_index

    def _create_form_page(self, title: str, subtitle: str, fields: list[FieldSchema]) -> QWidget:
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

    def _create_group_input_card(self, title: str, fields: list[FieldSchema], parent: QWidget) -> QFrame:
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

    def _create_input_row_card(self, spec: FieldSchema, parent: QWidget) -> QFrame:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        mark_input_field_surface(card)
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

        error_label = QLabel("", card)
        error_label.setObjectName("FieldErrorLabel")
        error_label.setWordWrap(True)
        error_label.setVisible(False)

        row.addWidget(label, 0, 0)
        row.addWidget(editor, 0, 1)
        row.addWidget(unit, 0, 2)
        row.addWidget(hint, 1, 0, 1, 3)
        row.addWidget(error_label, 2, 0, 1, 3)
        next_row = 3
        if spec.field_id in _MATERIAL_SOURCE_FIELDS:
            source = QLabel("", card)
            source.setObjectName("SectionHint")
            source.setWordWrap(True)
            row.addWidget(source, next_row, 0, 1, 3)
            self._source_labels[spec.field_id] = source
        self._field_cards[spec.field_id] = card
        self._field_error_labels[spec.field_id] = error_label
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
            mark_input_field_surface(row_card)
            row = QGridLayout(row_card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setHorizontalSpacing(10)
            row.setVerticalSpacing(4)

            label = QLabel(label_text, row_card)
            label.setObjectName("SubSectionTitle")
            value_label = QLabel("待输入", row_card)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setObjectName("DerivedValue")
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

    def _create_input(self, spec: FieldSchema, parent: QWidget) -> QWidget:
        if spec.widget_type == "choice":
            combo = AppComboBox(parent)
            combo.addItems(spec.options)
            default_text = "" if spec.default is None else str(spec.default)
            if default_text:
                index = combo.findText(default_text)
                if index >= 0:
                    combo.setCurrentIndex(index)
            combo.currentTextChanged.connect(
                lambda _text, fid=spec.field_id: self._on_input_changed(fid)
            )
            if spec.field_id.startswith("geometry."):
                combo.currentTextChanged.connect(lambda _text: self._schedule_preview())
            self._field_widgets[spec.field_id] = combo
            self._field_specs[spec.field_id] = spec
            return combo

        editor = QLineEdit(parent)
        editor.setObjectName("InputField")
        default_text = "" if spec.default is None else str(spec.default)
        editor.setText(default_text)
        if spec.field_id == "advanced.friction_override":
            editor.setPlaceholderText(_FRICTION_OVERRIDE_PLACEHOLDER)
        editor.textChanged.connect(
            lambda _text, fid=spec.field_id: self._on_input_changed(fid)
        )
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
        hint = QLabel("展示蜗杆副的几何示意与负载-安全系数曲线，辅助直观判断当前工况是否接近能力边界。", page)
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
        # Defer WormStressCurveWidget (and matplotlib) until the graphics
        # chapter is shown or the first result actually has curve data.
        self._stress_curve_host = QWidget(container)
        host_layout = QVBoxLayout(self._stress_curve_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)
        placeholder = QWidget(self._stress_curve_host)
        placeholder.setObjectName("WormStressCurvePlaceholder")
        placeholder.setMinimumHeight(350)
        host_layout.addWidget(placeholder)
        self._stress_curve_placeholder = placeholder
        self._stress_curve_ready = False
        self.stress_curve = placeholder
        body.addWidget(self.geometry_overview)
        body.addWidget(self.performance_curve)
        body.addWidget(self._stress_curve_host)
        body.addStretch(1)

        self.graphics_scroll_area.setWidget(container)
        layout.addWidget(self.graphics_scroll_area)
        self._graphics_chapter_index = self.add_chapter("图形与曲线", page)

    def _on_chapter_row_changed(self, index: int) -> None:
        if index == getattr(self, "_graphics_chapter_index", -1):
            self._ensure_stress_curve()

    def _ensure_stress_curve(self) -> WormStressCurveWidget:
        if getattr(self, "_stress_curve_ready", False):
            return self.stress_curve

        host = self._stress_curve_host
        widget = WormStressCurveWidget(host)
        layout = host.layout()
        placeholder = getattr(self, "_stress_curve_placeholder", None)
        if layout is not None and placeholder is not None:
            layout.replaceWidget(placeholder, widget)
            placeholder.setParent(None)
            placeholder.deleteLater()
            self._stress_curve_placeholder = None
        elif layout is not None:
            layout.addWidget(widget)
        self.stress_curve = widget
        self._stress_curve_ready = True
        return widget

    def _build_load_capacity_step(self) -> None:
        # content widget：承载全部 Load Capacity 内容，高度由内容决定，不受 viewport 限制
        page = QFrame()
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("负载能力 (Load Capacity)", page)
        title.setObjectName("SectionTitle")
        hint = QLabel("齿面/齿根负载能力校核的参数：许用应力、动载系数 Kv、载荷分配系数 KHα/KHβ 以及目标安全系数（基于 DIN 3996 Method B 风格最小子集）。对齿面和齿根分别算出 SH/SF 后与目标值对比判断通过/不通过。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        self.load_capacity_status = QLabel("DIN 3996 校核尚未开始", page)
        self.load_capacity_status.setObjectName("WaitBadge")
        self.load_capacity_scope_banner = make_scope_banner(page, WORM_SCOPE)
        self.load_capacity_note = QLabel(
            "当前版本输出 Method B 风格最小子集结果，不替代完整 DIN 3996 / ISO/TS 14521；所有简化假设都会在结果区显式说明。",
            page,
        )
        self.load_capacity_note.setObjectName("SectionHint")
        self.load_capacity_note.setWordWrap(True)
        self.load_capacity_metrics = QPlainTextEdit(page)
        self.load_capacity_metrics.setReadOnly(True)
        self.load_capacity_metrics.setMinimumHeight(240)
        self.load_capacity_metrics.setPlainText("尚无负载能力结果。")

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
        layout.addWidget(self.load_capacity_scope_banner)
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

        # Static formula images pre-generated by tools/bake_worm_formulas.py.
        # Using QLabel+QPixmap avoids a matplotlib render call at page construction
        # time, which was a startup-path bottleneck.
        self._latex_hertz = QLabel(formulas_card)
        self._latex_hertz.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _hertz_png = ASSETS_DIR / "worm_formula_hertz.png"
        if _hertz_png.exists():
            self._latex_hertz.setPixmap(QPixmap(str(_hertz_png)))
        formulas_layout.addWidget(self._latex_hertz)

        self._latex_root = QLabel(formulas_card)
        self._latex_root.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        _root_png = ASSETS_DIR / "worm_formula_root.png"
        if _root_png.exists():
            self._latex_root.setPixmap(QPixmap(str(_root_png)))
        formulas_layout.addWidget(self._latex_root)

        layout.addWidget(formulas_card)
        layout.addWidget(self.load_capacity_metrics)
        layout.addStretch(1)

        # 用 QScrollArea 包裹内容，避免内容超出 viewport 时被 QVBoxLayout 压缩子控件
        scroll = QScrollArea(self)
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        lc_index = self.add_chapter("Load Capacity", scroll, help_ref="modules/worm/_section_load_capacity")
        self._register_chapter_fields(lc_index, LOAD_CAPACITY_PARAMETER_FIELDS)

    def _build_results_step(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("结果与报告", page)
        title.setObjectName("SectionTitle")
        self.model_scope_banner = make_scope_banner(page, WORM_SCOPE)
        self.result_title = QLabel("尚未执行计算", page)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel(
            "执行计算后显示 DIN 3975 几何结果、基础性能和负载能力（Load Capacity）状态。",
            page,
        )
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
            row_val.setObjectName("MetricValue")
            row_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row_h.addWidget(row_name)
            row_h.addStretch(1)
            row_h.addWidget(row_val)
            life_layout.addWidget(row_frame)
            self._life_row_labels[row_key] = row_val

        self._life_card.setVisible(False)

        layout.addWidget(title)
        layout.addWidget(self.model_scope_banner)
        layout.addWidget(self.result_title)
        layout.addWidget(self.result_summary)
        layout.addWidget(self.result_metrics)
        layout.addWidget(self._efficiency_subtitle_card)
        layout.addWidget(self._life_card)

        # 用 QScrollArea 包裹内容，窗口缩小时内容可滚动而非截断
        scroll = QScrollArea(self)
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.add_chapter("结果与报告", scroll)

    def _read_widget_value(self, spec: FieldSchema) -> str:
        widget = self._field_widgets[spec.field_id]
        if spec.widget_type == "choice":
            return widget.currentText().strip()  # type: ignore[attr-defined]
        return widget.text().strip()  # type: ignore[attr-defined]

    def _current_raw_values(self) -> dict[str, str]:
        return {
            field_id: self._read_widget_value(spec)
            for field_id, spec in self._field_specs.items()
        }

    def _apply_defaults(self) -> None:
        for spec in self._field_specs.values():
            widget = self._field_widgets[spec.field_id]
            default_text = "" if spec.default is None else str(spec.default)
            if spec.widget_type == "choice":
                index = widget.findText(default_text)  # type: ignore[attr-defined]
                if index >= 0:
                    widget.setCurrentIndex(index)  # type: ignore[attr-defined]
            else:
                widget.setText(default_text)  # type: ignore[attr-defined]
        self._refresh_derived_geometry_preview()

    def _capture_input_snapshot(self) -> dict[str, Any]:
        return build_form_snapshot(
            self._field_specs.values(),
            self._read_widget_value,
            module_id=MODULE_ID,
        )

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        previous = self._suspend_live_feedback
        self._suspend_live_feedback = True
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
                mapping = spec.mapping
                if mapping is None:
                    continue
                section, key = mapping
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
                if (
                    index < 0
                    and spec.field_id in {
                        "materials.worm_material",
                        "materials.wheel_material",
                    }
                    and text
                ):
                    # Saved custom materials must remain selectable so their
                    # explicitly stored elastic/allowable values are not
                    # replaced by the default material preset below.
                    widget.addItem(text)  # type: ignore[attr-defined]
                    self._field_specs[spec.field_id] = replace(
                        spec,
                        options=(*spec.options, text),
                    )
                    index = widget.findText(text)  # type: ignore[attr-defined]
                if index >= 0:
                    widget.setCurrentIndex(index)  # type: ignore[attr-defined]
            else:
                widget.setText(str(value))  # type: ignore[attr-defined]
        self._field_widgets["materials.worm_material"].blockSignals(False)
        self._field_widgets["materials.wheel_material"].blockSignals(False)
        # Reconcile all auto fields after every value has been restored.  The
        # material signals were intentionally blocked during loading, so
        # without this call a sample could retain the static FieldSpec defaults
        # instead of the selected material's temperature/humidity derating.
        # Unknown custom materials are left untouched by this handler.
        self._on_material_changed()
        self._suspend_live_feedback = previous
        if not self._suspend_live_feedback:
            self._refresh_all_field_errors()

    def _build_payload(self) -> dict[str, Any]:
        payload = build_payload(self._field_specs.values(), self._current_raw_values())
        lc = payload.get("load_capacity")
        if isinstance(lc, dict) and "enabled" in lc:
            enabled = lc["enabled"]
            if isinstance(enabled, str):
                lc["enabled"] = enabled == "启用"
        return payload

    def _set_card_style(self, field_id: str, *, auto: bool) -> None:
        """将字段的外层 SubCard frame 切换为 AutoCalcCard（auto=True）或 SubCard（auto=False）。
        同时设置 QLineEdit 的 readOnly 状态。
        """
        frame = self._field_cards.get(field_id)
        if frame is not None:
            obj_name = "AutoCalcCard" if auto else "SubCard"
            frame.setObjectName(obj_name)
            frame.style().unpolish(frame)
            frame.style().polish(frame)
            for child in frame.findChildren(QWidget):
                child.style().unpolish(child)
                child.style().polish(child)
        widget = self._field_widgets.get(field_id)
        if isinstance(widget, QLineEdit):
            widget.setReadOnly(auto)
        elif isinstance(widget, QComboBox):
            widget.setEnabled(not auto)

    def _set_source_label(self, field_id: str, kind: str, detail: str = "") -> None:
        label = self._source_labels.get(field_id)
        if label is None:
            return
        label.setText(format_source_label(kind, detail) if kind else "")

    def _refresh_material_source_labels(self) -> None:
        """Mark E/allowable fields as 建议值 or 用户输入 without rewriting values."""
        worm_mat = self._field_widgets["materials.worm_material"].currentText()
        wheel_mat = self._field_widgets["materials.wheel_material"].currentText()
        from core.worm.calculator import MATERIAL_ELASTIC_HINTS, MATERIAL_ALLOWABLE_HINTS

        worm_hints = MATERIAL_ELASTIC_HINTS.get(worm_mat, {})
        wheel_hints = MATERIAL_ELASTIC_HINTS.get(wheel_mat, {})
        if worm_hints:
            detail = f"{worm_mat} 材料库典型值"
            self._set_source_label("materials.worm_e_mpa", SOURCE_RECOMMENDED, detail)
            self._set_source_label("materials.worm_nu", SOURCE_RECOMMENDED, detail)
        else:
            self._set_source_label("materials.worm_e_mpa", SOURCE_USER)
            self._set_source_label("materials.worm_nu", SOURCE_USER)
        if wheel_hints:
            detail = f"{wheel_mat} 材料库典型值"
            self._set_source_label("materials.wheel_e_mpa", SOURCE_RECOMMENDED, detail)
            self._set_source_label("materials.wheel_nu", SOURCE_RECOMMENDED, detail)
        else:
            self._set_source_label("materials.wheel_e_mpa", SOURCE_USER)
            self._set_source_label("materials.wheel_nu", SOURCE_USER)

        plastic = PLASTIC_MATERIALS.get(wheel_mat) if _PLASTIC_MATERIALS_AVAILABLE else None
        allowable_hints = MATERIAL_ALLOWABLE_HINTS.get(wheel_mat, {})
        if plastic is not None:
            detail = f"{wheel_mat} 降额建议值，非完整标准许用"
            self._set_source_label(
                "load_capacity.allowable_contact_stress_mpa", SOURCE_RECOMMENDED, detail
            )
            self._set_source_label(
                "load_capacity.allowable_root_stress_mpa", SOURCE_RECOMMENDED, detail
            )
        elif allowable_hints:
            detail = f"{wheel_mat} 材料库建议值，非完整标准许用"
            self._set_source_label(
                "load_capacity.allowable_contact_stress_mpa", SOURCE_RECOMMENDED, detail
            )
            self._set_source_label(
                "load_capacity.allowable_root_stress_mpa", SOURCE_RECOMMENDED, detail
            )
        else:
            self._set_source_label("load_capacity.allowable_contact_stress_mpa", SOURCE_USER)
            self._set_source_label("load_capacity.allowable_root_stress_mpa", SOURCE_USER)

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
        if not math.isfinite(rh) or not 0.0 <= rh <= 100.0:
            # Keep the last valid auto-filled values; FieldSchema displays the
            # actionable range error and blocks calculation.
            return
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
        self._refresh_material_source_labels()
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
        if not self._suspend_live_feedback:
            self._refresh_all_field_errors()

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
            payload.setdefault("load_capacity", {})["enabled"] = False
            geometry = calculate_worm_geometry(payload)["geometry"]
        except Exception:
            self._reset_dimension_preview_labels()
            self.set_info("输入不完整或无效，预览已重置")
            return

        self._apply_geometry_preview(geometry)

    def _apply_geometry_preview(self, geometry: dict[str, Any]) -> None:
        """Update derived geometry labels from an already calculated geometry block."""
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
        self._last_payload = None
        self._last_result = None
        self.btn_save.setEnabled(False)
        self._result_status_label.setText("结果已过期，请重新执行计算。")
        self._result_status_label.setObjectName("ResultStaleHint")
        self._result_status_label.style().unpolish(self._result_status_label)
        self._result_status_label.style().polish(self._result_status_label)
        if getattr(self, "result_title", None) is not None:
            self._reset_result_panels()

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

    def _set_field_error(self, field_id: str, message: str | None) -> None:
        widget = self._field_widgets.get(field_id)
        label = self._field_error_labels.get(field_id)
        invalid = bool(message)
        if widget is not None:
            widget.setProperty("fieldError", invalid)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        if label is not None:
            label.setText(message or "")
            label.setVisible(invalid)

    def _refresh_field_error(self, field_id: str, values: dict[str, str] | None = None) -> None:
        spec = self._field_specs.get(field_id)
        if spec is None:
            return
        raw_values = values if values is not None else self._current_raw_values()
        ok, message = validate_text(spec, raw_values.get(field_id, ""), values=raw_values)
        self._set_field_error(field_id, None if ok else message)

    def _dependent_field_ids(self, field_id: str) -> list[str]:
        dependents: list[str] = []
        for spec in self._field_specs.values():
            for condition in (spec.required_when, spec.visible_when):
                if (
                    isinstance(condition, tuple)
                    and len(condition) >= 2
                    and condition[1] == field_id
                ):
                    dependents.append(spec.field_id)
                    break
        return dependents

    def _refresh_all_field_errors(self) -> None:
        values = self._current_raw_values()
        for field_id in self._field_specs:
            self._refresh_field_error(field_id, values)

    def _collect_field_errors(self, *, show: bool) -> list[str]:
        values = self._current_raw_values()
        invalid: list[str] = []
        for field_id, spec in self._field_specs.items():
            ok, message = validate_text(spec, values.get(field_id, ""), values=values)
            if not ok:
                invalid.append(field_id)
            if show:
                self._set_field_error(field_id, None if ok else message)
        return invalid

    def _focus_field(self, field_id: str) -> None:
        chapter_index = self._field_chapter_index.get(field_id)
        if chapter_index is not None:
            self.set_current_chapter(chapter_index)
        widget = self._field_widgets.get(field_id)
        if widget is None:
            return
        widget.setFocus(Qt.FocusReason.OtherFocusReason)
        parent = widget.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if isinstance(parent, QScrollArea):
            parent.ensureWidgetVisible(widget)

    def _on_input_changed(self, field_id: str) -> None:
        if self._suspend_live_feedback:
            return
        self._mark_results_dirty()
        self.set_info("输入已变更，待重新计算")
        self._refresh_field_error(field_id)
        for dependent_id in self._dependent_field_ids(field_id):
            self._refresh_field_error(dependent_id)

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
        invalid = self._collect_field_errors(show=True)
        if invalid:
            self._last_payload = None
            self._last_result = None
            self._mark_results_dirty()
            self._focus_field(invalid[0])
            self.set_info(f"有 {len(invalid)} 个字段需要修正。")
            return
        try:
            payload = self._build_payload()
            result = calculate_worm_geometry(payload)
        except (InputError, ValueError) as exc:
            self._last_payload = None
            self._last_result = None
            self._mark_results_dirty()
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            self._last_payload = None
            self._last_result = None
            self._mark_results_dirty()
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        self._last_payload = payload
        try:
            self._render_result(result)
        except Exception as exc:
            self._last_payload = None
            self._last_result = None
            self._reset_result_panels()
            self._mark_results_dirty()
            QMessageBox.critical(self, "渲染异常", str(exc))
            self.set_info(f"结果渲染失败：{exc}")
            return
        self._last_result = result

    @staticmethod
    def _format_metric_line(metric) -> str:
        unit = f" {metric.unit}" if metric.unit else ""
        return f"{metric.label} = {metric.value}{unit}"

    def _format_load_capacity_metrics(
        self,
        view: ResultViewModel,
        result: dict[str, Any],
    ) -> str:
        load_capacity = result.get("load_capacity")
        if not isinstance(load_capacity, dict):
            load_capacity = {}
        lc_enabled = bool(load_capacity.get("enabled", False))
        warning_lines = [f"warning: {msg}" for msg in view.warnings]
        if not lc_enabled:
            return "\n".join(
                [
                    "负载能力校核：未启用",
                    "如需校核齿面/齿根安全系数，请在【基本设置】中启用负载能力（Load Capacity）页。",
                    *warning_lines,
                ]
            )

        lc_labels = {
            "sigma_H,nom",
            "sigma_H,peak",
            "SH_peak",
            "sigma_F,nom",
            "sigma_F,peak",
            "SF_peak",
            "T2_nom",
            "T2_rms",
            "T2_peak",
            "几何一致性",
        }
        lines = [
            self._format_metric_line(metric)
            for metric in view.metrics
            if metric.label in lc_labels
        ]
        if not any(line.startswith("几何一致性") for line in lines):
            geo = next(
                (item for item in view.checks if item.id == "geometry_consistent"),
                None,
            )
            geo_ok = geo is not None and geo.status == "pass"
            lines.append(f"几何一致性 = {'通过' if geo_ok else '存在警告'}")
        lines.extend(warning_lines)
        return "\n".join(lines)

    def _render_result(self, result: dict[str, Any]) -> None:
        view = from_worm(result, self._last_payload)
        geometry = result["geometry"]
        performance = result["performance"]
        curve = result["curve"]
        load_capacity = result["load_capacity"]
        payload = self._last_payload or {}
        worm_dimensions = geometry["worm_dimensions"]
        wheel_dimensions = geometry["wheel_dimensions"]

        self.result_title.setText(view.title_zh)
        self.result_summary.setText(view.summary_zh)
        self.result_metrics.setPlainText(
            "\n".join(self._format_metric_line(metric) for metric in view.metrics)
        )
        temp_rise_curve = curve.get("temperature_rise_k", [])
        self.performance_curve.set_curves(
            load_factor=curve["load_factor"],
            efficiency=curve["efficiency"],
            power_loss_kw=curve["power_loss_kw"],
            temperature_rise_k=temp_rise_curve,
            current_index=curve["current_index"],
        )
        stress_curve_data = load_capacity.get("stress_curve", {})
        if stress_curve_data and stress_curve_data.get("theta_deg"):
            self._ensure_stress_curve().set_curves(
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
        self.load_capacity_status.setText(str(load_capacity.get("status", view.status_label_zh)))
        self.load_capacity_metrics.setPlainText(
            self._format_load_capacity_metrics(view, result)
        )
        self._apply_geometry_preview(geometry)

        checks_by_id = {item.id: item for item in view.checks}
        for key, (_, badge) in self._check_badges.items():
            check = checks_by_id.get(key)
            if check is None:
                self._set_badge(badge, status_label_zh("not_checked"), "not_checked")
            else:
                self._set_badge(badge, status_label_zh(check.status), check.status)
        self._set_badge(
            self._overall_lc_badge,
            status_label_zh(view.overall_status),
            view.overall_status,
        )
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
            self, "导出计算报告", str(EXAMPLES_DIR / "worm_report.pdf"),
            "PDF Files (*.pdf);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        out_path = Path(file_path)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            suffix = out_path.suffix.lower()
            if suffix == ".pdf":
                try:
                    import importlib
                    mod = importlib.import_module("app.ui.report_pdf_worm")
                    mod.generate_worm_report(out_path, self._last_payload or {}, self._last_result)
                except Exception:
                    out_path = out_path.with_suffix(".txt")
                    self._write_text_report(out_path)
                    self.set_info(f"报告已导出: {out_path}（已使用简化格式）")
                    return
            else:
                self._write_text_report(out_path)
        except (ReportExportError, OSError) as exc:
            QMessageBox.critical(self, "导出失败", f"导出失败：{exc}")
            return
        self.set_info(f"报告已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        assert self._last_result is not None
        payload = self._last_payload or {}
        view = from_worm(self._last_result, payload)
        note = self._last_result.get("inputs_echo", {}).get("meta", {}).get("note", "")
        lines = [
            f"蜗杆副计算报告 -- {note}",
            *trace_report_lines(
                build_report_trace(
                    MODULE_ID,
                    payload,
                    model_level=view.model_scope.model_level,
                )
            ),
            "",
            *scope_report_lines(view.model_scope),
            "",
            f"总体结论: {view.title_zh}",
            view.summary_zh,
            "",
            "分项结果:",
        ]
        for check in view.checks:
            lines.append(f"- {check.label_zh}: {status_label_zh(check.status)}")
        lines.extend(["", "关键结果:"])
        for metric in view.metrics:
            unit = f" {metric.unit}" if metric.unit else ""
            lines.append(f"- {metric.label}: {metric.value}{unit}")
        for note_text in view.source_notes:
            lines.append(f"- {note_text}")
        if view.warnings:
            lines.extend(["", "提示:"])
            lines.extend(f"- {msg}" for msg in view.warnings)
        lines.extend(["", "建议:"])
        lines.extend(f"- {msg}" for msg in view.recommendations)
        return lines

    def _write_text_report(self, path: Path) -> None:
        write_text_report(path, "\n".join(self._build_report_lines()))

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
        self._mark_results_dirty()
        self.set_info(f"已加载输入条件：{in_path}")

    def _load_sample(self, filename: str) -> None:
        sample_path = EXAMPLES_DIR / filename
        if not sample_path.exists():
            QMessageBox.warning(self, "测试案例不存在", f"未找到测试案例文件：{sample_path}")
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
        self._mark_results_dirty()
        self.set_info(f"已加载测试案例：{filename}")

    def _reset_result_panels(self) -> None:
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText(
            "执行计算后显示几何、基础性能以及 Method B 风格最小负载能力子集结果。"
        )
        self.result_metrics.setPlainText("尚无结果。")
        self.performance_curve.set_curves(
            load_factor=[],
            efficiency=[],
            power_loss_kw=[],
            temperature_rise_k=[],
            current_index=-1,
        )
        if getattr(self, "_stress_curve_ready", False):
            self.stress_curve.clear()
        self.geometry_overview.reset_geometry_state()
        self.geometry_overview.set_display_state("几何总览", "按 DIN 3975 展示蜗杆、蜗轮、中心距与导程角关系。")
        self.load_capacity_status.setText("DIN 3996 校核尚未开始")
        self.load_capacity_status.setObjectName("WaitBadge")
        self.load_capacity_status.style().unpolish(self.load_capacity_status)
        self.load_capacity_status.style().polish(self.load_capacity_status)
        self.load_capacity_metrics.setPlainText("尚无负载能力结果。")
        for _key, (_name, badge) in self._check_badges.items():
            self._set_badge(badge, "待计算", "wait")
        self._set_badge(self._overall_lc_badge, "待计算", "wait")
        self._efficiency_subtitle_label.setText("执行计算后显示。")
        self._efficiency_subtitle_card.setVisible(False)
        for label in self._life_row_labels.values():
            label.setText("—")
        self._life_card.setVisible(False)

    def _clear(self) -> None:
        self._last_result = None
        self._last_payload = None
        self._suspend_live_feedback = True
        self._apply_defaults()
        self._on_material_changed()
        self._suspend_live_feedback = False
        self._refresh_all_field_errors()
        self._reset_result_panels()
        self._mark_results_dirty()
        self.set_info("参数已重置，可重新执行蜗杆副计算。")
