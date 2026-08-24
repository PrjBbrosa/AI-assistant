"""Hertz contact-stress module page with chapter workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
from app.ui.fonts import make_ui_font
from app.ui.model_scope import (
    HERTZ_ALLOWABLE_SOURCE_NOTE,
    HERTZ_SCOPE,
    SOURCE_RECOMMENDED,
    SOURCE_USER,
    format_source_label,
    make_scope_banner,
    scope_report_lines,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import ReportExportError, write_text_report
from app.ui.report_trace import build_report_trace, trace_report_lines
from app.ui.result_contract import (
    HERTZ_CHECK_LABELS,
    from_hertz,
    status_label_zh,
)
from app.ui.theme import mark_input_field_label_wrap, mark_input_field_surface
from app.ui.widgets.app_combo_box import AppComboBox
from app.ui.widgets.help_button import HelpButton
from app.ui.widgets.hertz_input_diagram import HertzInputDiagramWidget
from core.hertz.calculator import InputError, calculate_hertz_contact

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)
MODULE_ID = "hertz_contact"

MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29},
    "GCr15": {"e_mpa": 208000.0, "nu": 0.30},
    "45钢": {"e_mpa": 210000.0, "nu": 0.30},
    "铸铁 HT250": {"e_mpa": 120000.0, "nu": 0.26},
    "铝合金 6061-T6": {"e_mpa": 69000.0, "nu": 0.33},
    "自定义": None,
}
MATERIAL_OPTIONS: tuple[str, ...] = tuple(MATERIAL_LIBRARY.keys())
CONTACT_MODE_LINE = "线接触"
CONTACT_MODE_POINT = "点接触"
CONTACT_MODE_OPTIONS = (CONTACT_MODE_LINE, CONTACT_MODE_POINT)
CONTACT_MODE_TO_CORE = {
    CONTACT_MODE_LINE: "line",
    CONTACT_MODE_POINT: "point",
}

FIELD_PLACEHOLDERS: dict[str, str] = {
    "checks.allowable_p0_mpa": "例如 1500",
    "options.curve_points": "例如 41",
    "options.curve_force_scale": "1.05~2.0",
    "geometry.r1_mm": "例如 30",
    "geometry.r2_mm": "平面填 0",
    "geometry.length_mm": "例如 20",
    "loads.normal_force_n": "例如 12000",
}

_RADIUS_KW = dict(min_value=0.0, min_inclusive=True, finite=True)
_POSITIVE_KW = dict(min_value=0.0, min_inclusive=False, finite=True)
_NU_KW = dict(
    min_value=0.0,
    max_value=0.5,
    min_inclusive=False,
    max_inclusive=False,
    finite=True,
)

CHAPTERS: list[dict[str, Any]] = [
    {
        "id": "checks",
        "title": "校核目标",
        "subtitle": "设置接触应力的许用值 [p0] 和结果曲线的采样参数：工具用 [p0] 对 p0 做 PASS/FAIL 判据，曲线参数仅影响可视化。",
        "help_ref": "modules/hertz/_section_checks",
        "fields": [
            FieldSpec(
                "checks.allowable_p0_mpa",
                "允许最大接触应力 [p0]",
                "MPa",
                "用户输入的许用值，用于 p0 判据。材料下拉只提供 E/ν 建议值，不会把牌号自动写成权威 [p0]。",
                mapping=("checks", "allowable_p0_mpa"),
                default="1500",
                source_kind="user",
                help_ref="terms/hertz_allowable_pressure",
                **_POSITIVE_KW,
            ),
            FieldSpec(
                "options.curve_points",
                "压力-载荷曲线采样点数",
                "点",
                "结果曲线离散点数量（11~201）。",
                mapping=("options", "curve_points"),
                value_type="int",
                min_value=11,
                max_value=201,
                finite=True,
                default="41",
                help_ref="terms/hertz_curve_sampling",
            ),
            FieldSpec(
                "options.curve_force_scale",
                "曲线载荷上限倍率",
                "-",
                "曲线终点载荷 = 设计载荷 * 倍率。",
                mapping=("options", "curve_force_scale"),
                min_value=1.05,
                max_value=2.0,
                finite=True,
                default="1.30",
                help_ref="terms/hertz_curve_sampling",
            ),
        ],
    },
    {
        "id": "geometry",
        "title": "接触模型与几何",
        "subtitle": "选择线接触 / 点接触并填写两接触体的曲率半径：本版仅支持外接触（曲率半径 ≥ 0，两正曲率相加）；内接触/负曲率不在本版范围。",
        "help_ref": "modules/hertz/_section_geometry",
        "fields": [
            FieldSpec(
                "geometry.contact_mode",
                "接触类型",
                "-",
                "外接触线接触：圆柱-圆柱/圆柱-平面；外接触点接触：球-球/球-平面。内接触不在本版范围。",
                widget_type="choice",
                options=CONTACT_MODE_OPTIONS,
                default=CONTACT_MODE_LINE,
                mapping=None,
                help_ref="terms/hertz_contact_mode",
            ),
            FieldSpec(
                "geometry.r1_mm",
                "曲率半径 R1",
                "mm",
                "第 1 接触体曲率半径。凸面填正值，平面填 0；负曲率/内接触不在本版范围。",
                mapping=("geometry", "r1_mm"),
                default="30.0",
                help_ref="terms/hertz_curvature_radius",
                **_RADIUS_KW,
            ),
            FieldSpec(
                "geometry.r2_mm",
                "曲率半径 R2",
                "mm",
                "第 2 接触体曲率半径。凸面填正值，平面可填 0；负曲率/内接触不在本版范围。",
                mapping=("geometry", "r2_mm"),
                default="0.0",
                help_ref="terms/hertz_curvature_radius",
                **_RADIUS_KW,
            ),
            FieldSpec(
                "geometry.length_mm",
                "接触长度 L（线接触）",
                "mm",
                "线接触按单位长度载荷计算；点接触时该值仅记录。",
                mapping=("geometry", "length_mm"),
                default="20.0",
                help_ref="terms/hertz_contact_length",
                visible_when=("eq", "geometry.contact_mode", CONTACT_MODE_LINE),
                **_POSITIVE_KW,
            ),
        ],
    },
    {
        "id": "materials",
        "title": "材料参数",
        "subtitle": "填写两接触体的弹性模量 E 和泊松比 ν：两组参数合成等效模量 E'，材料越硬 E' 越大、p0 也越高。",
        "help_ref": "modules/hertz/_section_materials",
        "fields": [
            FieldSpec(
                "materials.body1_material",
                "接触体 1 材料",
                "-",
                "选择后带出 E1/nu1 建议值（可切自定义覆盖）；不会据此生成权威 [p0]。",
                widget_type="choice",
                options=MATERIAL_OPTIONS,
                default="42CrMo",
                mapping=None,
            ),
            FieldSpec(
                "materials.e1_mpa",
                "弹性模量 E1",
                "MPa",
                "接触体 1 弹性模量。预设材料为建议值，自定义为用户输入。",
                mapping=("materials", "e1_mpa"),
                default="210000",
                help_ref="terms/elastic_modulus",
                **_POSITIVE_KW,
            ),
            FieldSpec(
                "materials.nu1",
                "泊松比 nu1",
                "-",
                "接触体 1 泊松比。预设材料为建议值，自定义为用户输入。",
                mapping=("materials", "nu1"),
                default="0.29",
                help_ref="terms/poisson_ratio",
                **_NU_KW,
            ),
            FieldSpec(
                "materials.body2_material",
                "接触体 2 材料",
                "-",
                "选择后带出 E2/nu2 建议值（可切自定义覆盖）；不会据此生成权威 [p0]。",
                widget_type="choice",
                options=MATERIAL_OPTIONS,
                default="45钢",
                mapping=None,
            ),
            FieldSpec(
                "materials.e2_mpa",
                "弹性模量 E2",
                "MPa",
                "接触体 2 弹性模量。预设材料为建议值，自定义为用户输入。",
                mapping=("materials", "e2_mpa"),
                default="210000",
                help_ref="terms/elastic_modulus",
                **_POSITIVE_KW,
            ),
            FieldSpec(
                "materials.nu2",
                "泊松比 nu2",
                "-",
                "接触体 2 泊松比。预设材料为建议值，自定义为用户输入。",
                mapping=("materials", "nu2"),
                default="0.30",
                help_ref="terms/poisson_ratio",
                **_NU_KW,
            ),
        ],
    },
    {
        "id": "loads",
        "title": "载荷输入",
        "subtitle": "填写作用在接触区的法向载荷 F：赫兹公式只接受纯法向力，切向/冲击/动载需预先折算到峰值法向载荷。",
        "help_ref": "modules/hertz/_section_loads",
        "fields": [
            FieldSpec(
                "loads.normal_force_n",
                "法向载荷 F",
                "N",
                "作用在接触区法向方向的载荷。",
                mapping=("loads", "normal_force_n"),
                default="12000",
                **_POSITIVE_KW,
            ),
        ],
    },
]

BEGINNER_GUIDES: dict[str, str] = {
    "geometry.contact_mode": "先选接触类型，再填对应几何参数。",
    "geometry.r2_mm": "若为平面接触可输入 0，程序按无穷大半径处理。本版只接受 ≥ 0 的外接触半径。",
    "geometry.length_mm": "仅在线接触时用于把 F 转换为单位长度载荷 F'。",
    "checks.allowable_p0_mpa": "来源为用户输入。材料牌号不会自动生成权威许用接触应力；可按材料/热处理手册自行折算后填入。",
    "loads.normal_force_n": "取峰值载荷；冲击工况建议乘载荷系数后输入。",
}


class HertzContactPage(BaseChapterPage):
    """Hertz contact-stress chapter page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="赫兹应力 · 接触校核",
            subtitle="线接触/点接触的赫兹最大接触应力计算。当前仅支持外接触（曲率半径 ≥ 0，两正曲率相加）；内接触/负曲率不在本版范围。",
            parent=parent,
        )
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSchema] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._field_error_labels: dict[str, QLabel] = {}
        self._field_chapter_index: dict[str, int] = {}
        self._source_labels: dict[str, QLabel] = {}
        self._widget_hints: dict[QWidget, str] = {}
        self._check_badges: dict[str, QLabel] = {}
        self._suspend_live_feedback = False

        self._material_links: dict[str, tuple[str, str]] = {
            "materials.body1_material": ("materials.e1_mpa", "materials.nu1"),
            "materials.body2_material": ("materials.e2_mpa", "materials.nu2"),
        }
        self._mode_field_id = "geometry.contact_mode"
        self._line_only_fields = {"geometry.length_mm"}

        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行校核", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_save = self.add_action_button("导出结果说明")
        self.btn_help_guide = self.add_guide_button("modules/hertz/beginner_guide")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")

        self._build_input_chapters()
        self._build_diagram_chapter()
        self._build_results_chapter()
        self.set_current_chapter(0)

        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("hertz_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("hertz_case_02.json"))
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save.clicked.connect(self._save_report)

        self._register_material_bindings()
        self._suspend_live_feedback = True
        self._apply_defaults()
        self._suspend_live_feedback = False

        def _deferred_sample_init():
            self._suspend_live_feedback = True
            self._load_sample("hertz_case_01.json")
            self._sync_material_inputs()
            self._apply_mode_visibility()
            self._refresh_diagram_from_inputs()
            self._suspend_live_feedback = False
            self._refresh_all_field_errors()
            self._mark_results_dirty()

        QTimer.singleShot(0, _deferred_sample_init)
        self._mark_results_dirty()

    def eventFilter(self, watched, event):  # noqa: N802
        if watched in self._widget_hints and event.type() in (QEvent.Type.FocusIn, QEvent.Type.Enter):
            self.set_info(self._widget_hints[watched])
        return super().eventFilter(watched, event)

    def _build_input_chapters(self) -> None:
        for chapter in CHAPTERS:
            chapter_index = self.chapter_list.count()
            page = self._create_chapter_page(
                chapter["title"],
                chapter["subtitle"],
                chapter["fields"],
                help_ref=chapter.get("help_ref", ""),
            )
            for spec in chapter["fields"]:
                self._field_chapter_index[spec.field_id] = chapter_index
            self.add_chapter(chapter["title"], page)

    def _create_chapter_page(
        self,
        title: str,
        subtitle: str,
        fields: list[FieldSchema],
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
            header_layout.addWidget(
                HelpButton(help_ref, parent=header_row),
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )
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
            field_card.setObjectName("SubCard")
            mark_input_field_surface(field_card)
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
            error_label = QLabel("", field_card)
            error_label.setObjectName("FieldErrorLabel")
            error_label.setWordWrap(True)
            error_label.setVisible(False)

            # 字段级 help_ref 存在时把 label + HelpButton 包在一个水平容器里
            if spec.help_ref:
                label_widget = QWidget(field_card)
                mark_input_field_label_wrap(label_widget)
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

            row.addWidget(label, 0, 0)
            row.addWidget(editor, 0, 1)
            row.addWidget(unit, 0, 2)
            row.addWidget(hint, 1, 0, 1, 3)
            row.addWidget(error_label, 2, 0, 1, 3)
            if spec.field_id in {
                "checks.allowable_p0_mpa",
                "materials.e1_mpa",
                "materials.nu1",
                "materials.e2_mpa",
                "materials.nu2",
            }:
                source = QLabel("", field_card)
                source.setObjectName("SectionHint")
                source.setWordWrap(True)
                if spec.field_id == "checks.allowable_p0_mpa":
                    source.setText(HERTZ_ALLOWABLE_SOURCE_NOTE)
                row.addWidget(source, 3, 0, 1, 3)
                self._source_labels[spec.field_id] = source
            form_layout.addWidget(field_card)
            self._field_cards[spec.field_id] = field_card
            self._field_error_labels[spec.field_id] = error_label

        form_layout.addStretch(1)
        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)
        return page

    def _create_editor(self, spec: FieldSchema, parent: QWidget) -> QWidget:
        if spec.value_type in ("enum", "bool") or spec.widget_type == "choice":
            editor = AppComboBox(parent)
            editor.addItems(spec.options)
            default_text = "" if spec.default is None else str(spec.default)
            if default_text:
                idx = editor.findText(default_text)
                if idx >= 0:
                    editor.setCurrentIndex(idx)
            editor.currentTextChanged.connect(
                lambda _text, fid=spec.field_id: self._on_input_changed(fid)
            )
        else:
            editor = QLineEdit(parent)
            editor.setObjectName("InputField")
            editor.setPlaceholderText(
                FIELD_PLACEHOLDERS.get(spec.field_id, "请输入数值")
            )
            default_text = "" if spec.default is None else str(spec.default)
            if default_text:
                editor.setText(default_text)
            editor.textChanged.connect(
                lambda _text, fid=spec.field_id: self._on_input_changed(fid)
            )

        help_text = self._build_field_help(spec)
        editor.setToolTip(help_text)
        editor.installEventFilter(self)
        self._widget_hints[editor] = help_text
        self._field_widgets[spec.field_id] = editor
        self._field_specs[spec.field_id] = spec
        return editor

    def _build_field_help(self, spec: FieldSchema) -> str:
        unit_part = f"（单位：{spec.unit}）" if spec.unit and spec.unit != "-" else ""
        newbie = BEGINNER_GUIDES.get(spec.field_id, "建议先加载测试案例运行，再替换为实际数据。")
        return f"{spec.label}{unit_part}\n参数说明：{spec.hint}\n新手提示：{newbie}"

    def _build_diagram_chapter(self) -> None:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title = QLabel("输入条件图示说明", page)
        title.setObjectName("SectionTitle")
        title.setFont(make_ui_font(20, 700))
        hint = QLabel("图示随输入实时变化，用于核对接触模型、载荷方向和关键参数。", page)
        hint.setObjectName("SectionHint")
        hint.setFont(make_ui_font(14))
        hint.setWordWrap(True)
        self.diagram_widget = HertzInputDiagramWidget(page)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.diagram_widget, 1)
        self.add_chapter("输入条件图示说明", page)

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
        hint = QLabel("输出接触斑尺寸、最大接触应力和安全系数。", container)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        self.model_scope_banner = make_scope_banner(container, HERTZ_SCOPE)
        content.addWidget(title)
        content.addWidget(hint)
        content.addWidget(self.model_scope_banner)

        summary_card = QFrame(container)
        summary_card.setObjectName("SubCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)
        self.result_title = QLabel("尚未执行计算", summary_card)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel("填写参数并点击\"执行校核\"后，这里显示结论。", summary_card)
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
        for key, text in HERTZ_CHECK_LABELS.items():
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

    def _register_material_bindings(self) -> None:
        for selector_id in self._material_links:
            selector = self._field_widgets.get(selector_id)
            if isinstance(selector, QComboBox):
                selector.currentTextChanged.connect(
                    lambda _text, sid=selector_id: self._apply_material_selection(sid)
                )

    def _apply_material_selection(self, selector_id: str) -> None:
        selector = self._field_widgets.get(selector_id)
        if not isinstance(selector, QComboBox):
            return
        links = self._material_links.get(selector_id)
        if links is None:
            return
        e_id, nu_id = links
        e_widget = self._field_widgets.get(e_id)
        nu_widget = self._field_widgets.get(nu_id)
        if not isinstance(e_widget, QLineEdit) or not isinstance(nu_widget, QLineEdit):
            return
        material_name = selector.currentText().strip()
        material = MATERIAL_LIBRARY.get(material_name)
        is_custom = material is None
        self._set_card_disabled(e_id, not is_custom)
        self._set_card_disabled(nu_id, not is_custom)
        if material is not None:
            e_widget.setText(f"{material['e_mpa']:.0f}")
            nu_widget.setText(f"{material['nu']:.2f}")
            source_text = format_source_label(
                SOURCE_RECOMMENDED, f"{material_name} 材料库典型值，可切自定义覆盖"
            )
        else:
            source_text = format_source_label(SOURCE_USER)
        for field_id in (e_id, nu_id):
            source_label = self._source_labels.get(field_id)
            if source_label is not None:
                source_label.setText(source_text)

    def _sync_material_inputs(self) -> None:
        for selector_id in self._material_links:
            self._apply_material_selection(selector_id)

    def _is_point_mode(self) -> bool:
        mode_widget = self._field_widgets.get(self._mode_field_id)
        if not isinstance(mode_widget, QComboBox):
            return False
        return mode_widget.currentText() == CONTACT_MODE_POINT

    def _set_card_disabled(self, field_id: str, disabled: bool) -> None:
        """Toggle a field card between normal SubCard and disabled AutoCalcCard style."""
        card = self._field_cards.get(field_id)
        if card is None:
            return
        card.setObjectName("AutoCalcCard" if disabled else "SubCard")
        card.style().unpolish(card)
        card.style().polish(card)
        for child in card.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
        widget = self._field_widgets.get(field_id)
        if isinstance(widget, QLineEdit):
            widget.setReadOnly(disabled)
        elif isinstance(widget, QComboBox):
            widget.setEnabled(not disabled)

    def _apply_mode_visibility(self) -> None:
        point_mode = self._is_point_mode()
        for field_id in self._line_only_fields:
            self._set_card_disabled(field_id, point_mode)
        self.set_info("当前为点接触模型，线接触长度 L 不参与计算。" if point_mode else "当前为线接触模型，已显示长度 L 输入。")

    def _safe_float(self, field_id: str, default: float) -> float:
        widget = self._field_widgets.get(field_id)
        if not isinstance(widget, QLineEdit):
            return default
        try:
            return float(widget.text().strip())
        except ValueError:
            return default

    def _refresh_diagram_from_inputs(self) -> None:
        mode = "point" if self._is_point_mode() else "line"
        r1 = self._safe_float("geometry.r1_mm", 30.0)
        r2 = self._safe_float("geometry.r2_mm", 0.0)
        length = self._safe_float("geometry.length_mm", 20.0)
        force = self._safe_float("loads.normal_force_n", 10000.0)
        e1 = self._safe_float("materials.e1_mpa", 210000.0)
        nu1 = self._safe_float("materials.nu1", 0.30)
        e2 = self._safe_float("materials.e2_mpa", 210000.0)
        nu2 = self._safe_float("materials.nu2", 0.30)
        denom = max(1e-9, (1.0 - nu1 * nu1) / max(e1, 1e-6) + (1.0 - nu2 * nu2) / max(e2, 1e-6))
        e_eq = 1.0 / denom
        self.diagram_widget.set_context(mode, r1, r2, length, force, e_eq)

    def _apply_defaults(self) -> None:
        for spec in self._field_specs.values():
            widget = self._field_widgets[spec.field_id]
            default_text = "" if spec.default is None else str(spec.default)
            if spec.widget_type == "choice":
                combo = widget  # type: ignore[assignment]
                if default_text:
                    idx = combo.findText(default_text)  # type: ignore[attr-defined]
                    if idx >= 0:
                        combo.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(default_text)  # type: ignore[attr-defined]
        self._sync_material_inputs()
        self._apply_mode_visibility()
        self._refresh_diagram_from_inputs()

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

    def _build_payload(self) -> dict[str, Any]:
        payload = build_payload(self._field_specs.values(), self._current_raw_values())
        mode_text = self._read_widget_value(self._field_specs[self._mode_field_id])
        payload.setdefault("geometry", {})["contact_mode"] = CONTACT_MODE_TO_CORE.get(
            mode_text, "line"
        )
        return payload

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
        if field_id == self._mode_field_id:
            self._apply_mode_visibility()
        self._refresh_field_error(field_id)
        for dependent_id in self._dependent_field_ids(field_id):
            self._refresh_field_error(dependent_id)
        self._refresh_diagram_from_inputs()

    def _calculate(self) -> None:
        invalid = self._collect_field_errors(show=True)
        if invalid:
            self._mark_results_dirty()
            self._focus_field(invalid[0])
            self.set_info(f"有 {len(invalid)} 个字段需要修正。")
            return
        try:
            payload = self._build_payload()
            result = calculate_hertz_contact(payload)
            self._render_result(result)
            self.set_current_chapter(self.chapter_stack.count() - 1)
        except (InputError, ValueError) as exc:
            self._mark_results_dirty()
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            self._last_payload = None
            self._last_result = None
            self._reset_result_display()
            self._mark_results_dirty()
            QMessageBox.critical(self, "渲染异常", str(exc))
            self.set_info(f"结果渲染失败：{exc}")
            return

        self._last_payload = payload
        self._last_result = result
        self._mark_results_fresh()

    def _render_result(self, result: dict[str, Any]) -> None:
        view = from_hertz(result, self._last_payload)
        self.result_title.setText(view.title_zh)
        self.result_summary.setText(view.summary_zh)

        for check in view.checks:
            badge = self._check_badges.get(check.id)
            if badge is None:
                continue
            self._set_badge(badge, status_label_zh(check.status), check.status)

        lines: list[str] = []
        for metric in view.metrics:
            unit = f" {metric.unit}" if metric.unit else ""
            lines.append(f"• {metric.label}: {metric.value}{unit}")
        for note in view.source_notes:
            lines.append(f"• {note}")
        self.metrics_text.setText("\n".join(lines))

        self._refresh_diagram_from_inputs()
        messages = [f"[提示] {msg}" for msg in view.warnings]
        messages.extend(f"[建议] {msg}" for msg in view.recommendations)
        messages.append("[说明] 当前基于标准赫兹弹性接触理论，未包含弹塑性与边缘修正。")
        self.message_box.setPlainText("\n".join(messages))

    def _capture_input_snapshot(self) -> dict[str, Any]:
        return build_form_snapshot(
            self._field_specs.values(),
            self._read_widget_value,
            module_id=MODULE_ID,
        )

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        inputs_data = data.get("inputs")
        inputs = inputs_data if isinstance(inputs_data, dict) else data
        ui_state_data = data.get("ui_state")
        ui_state = ui_state_data if isinstance(ui_state_data, dict) else {}

        previous = self._suspend_live_feedback
        self._suspend_live_feedback = True
        try:
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
                text = str(value)
                if spec.widget_type == "choice":
                    idx = widget.findText(text)  # type: ignore[attr-defined]
                    if idx >= 0:
                        widget.setCurrentIndex(idx)  # type: ignore[attr-defined]
                else:
                    widget.setText(text)  # type: ignore[attr-defined]

            if self._mode_field_id not in ui_state:
                mode_widget = self._field_widgets.get(self._mode_field_id)
                mode = str(inputs.get("geometry", {}).get("contact_mode", "line"))
                if isinstance(mode_widget, QComboBox):
                    mode_widget.setCurrentText(
                        CONTACT_MODE_POINT if mode == "point" else CONTACT_MODE_LINE
                    )

            self._sync_material_inputs()
            self._apply_mode_visibility()
            self._refresh_diagram_from_inputs()
        finally:
            self._suspend_live_feedback = previous
        if not previous:
            self._refresh_all_field_errors()
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
        self._mark_results_dirty()
        self.set_info(f"已加载测试案例：{filename}。可直接执行校核并查看图示。")

    def _save_input_conditions(self) -> None:
        default_path = SAVED_INPUTS_DIR / "hertz_contact_input_conditions.json"
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

    def _clear(self) -> None:
        previous = self._suspend_live_feedback
        self._suspend_live_feedback = True
        try:
            self._apply_defaults()
            self._last_payload = None
            self._last_result = None
            self._reset_result_display()
            self._refresh_diagram_from_inputs()
        finally:
            self._suspend_live_feedback = previous
        if not previous:
            self._refresh_all_field_errors()
        self.set_info("参数已重置为默认值。")
        self._mark_results_dirty()

    def _reset_result_display(self) -> None:
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText("填写参数并点击\"执行校核\"后，这里显示结论。")
        self.metrics_text.setText("尚无结果。")
        self.message_box.clear()
        for badge in self._check_badges.values():
            self._set_badge(badge, "待计算", "wait")

    def _mark_results_dirty(self) -> None:
        self.btn_save.setEnabled(False)

    def _mark_results_fresh(self) -> None:
        self.btn_save.setEnabled(True)

    def _save_report(self) -> None:
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行校核计算。")
            return
        default_path = EXAMPLES_DIR / "hertz_contact_report.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出结果说明",
            str(default_path),
            "PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        out_path = Path(file_path)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            suffix = out_path.suffix.lower()
            if suffix == ".pdf":
                try:
                    from app.ui.report_pdf_hertz import generate_hertz_report

                    generate_hertz_report(out_path, self._last_payload, self._last_result)
                except Exception:
                    from app.ui.report_export import _export_pdf

                    _export_pdf(out_path, self._build_report_lines())
                    self.set_info(f"结果说明已导出: {out_path}（已使用简化格式）")
                    return
            elif suffix == ".docx":
                from app.ui.report_export import _export_docx

                _export_docx(out_path, self._build_report_lines())
            else:
                write_text_report(out_path, "\n".join(self._build_report_lines()))
        except (ReportExportError, OSError) as exc:
            QMessageBox.critical(self, "导出失败", f"导出失败：{exc}")
            return
        self.set_info(f"结果说明已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        assert self._last_result is not None
        view = from_hertz(self._last_result, self._last_payload)
        lines = [
            "赫兹接触应力校核报告（本地版）",
            *trace_report_lines(
                build_report_trace(
                    MODULE_ID,
                    self._last_payload or {},
                    model_level=HERTZ_SCOPE.model_level,
                )
            ),
            "",
            *scope_report_lines(view.model_scope),
            "",
            f"总体结论: {view.status_label_zh}",
            "",
            "关键结果:",
        ]
        for metric in view.metrics:
            unit = f" {metric.unit}" if metric.unit else ""
            lines.append(f"- {metric.label}: {metric.value}{unit}")
        for note in view.source_notes:
            lines.append(f"- {note}")
        if view.warnings:
            lines.extend(["", "提示:"])
            lines.extend(f"- {msg}" for msg in view.warnings)
        lines.extend(["", "建议:"])
        lines.extend(f"- {msg}" for msg in view.recommendations)
        return lines
