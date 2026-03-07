"""Worm gear module page with DIN 3975 first-pass workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
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

from app.ui.input_condition_store import (
    build_form_snapshot,
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    read_input_conditions,
    write_input_conditions,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.widgets.worm_geometry_overview import WormGeometryOverviewWidget
from app.ui.widgets.worm_performance_curve import WormPerformanceCurveWidget
from app.ui.widgets.worm_tolerance_overview import WormToleranceOverviewWidget
from core.worm.calculator import InputError, calculate_worm_geometry


LOAD_CAPACITY_OPTIONS = (
    "DIN 3996 Method B",
    "ISO/TR 14521 Method B",
    "Niemann",
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

    @property
    def mapping(self) -> tuple[str, str] | None:
        if "." not in self.field_id:
            return None
        return tuple(self.field_id.split(".", 1))  # type: ignore[return-value]


BASIC_SETTINGS_FIELDS = [
    FieldSpec("meta.note", "项目备注", "-", "当前计算任务简述。", widget_type="text", default="DIN 3975 首版"),
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
        "首版只保留方法选择，不执行真实 3996/ISO/Niemann 公式。",
        widget_type="choice",
        options=LOAD_CAPACITY_OPTIONS,
        default="DIN 3996 Method B",
    ),
]

WORM_GEOMETRY_FIELDS = [
    FieldSpec("geometry.z1", "蜗杆头数 z1", "-", "蜗杆起始头数。", default="2"),
    FieldSpec("geometry.module_mm", "模数 m", "mm", "几何主输入。", default="4.0"),
    FieldSpec("geometry.diameter_factor_q", "直径系数 q", "-", "蜗杆直径系数。", default="10.0"),
    FieldSpec("geometry.lead_angle_deg", "导程角 gamma", "deg", "蜗杆导程角。", default="20.0"),
    FieldSpec(
        "geometry.handedness",
        "旋向",
        "-",
        "按 manual 保留旋向记录项。",
        widget_type="choice",
        options=("右旋", "左旋"),
        default="右旋",
    ),
    FieldSpec("geometry.worm_face_width_mm", "蜗杆齿宽 b1", "mm", "蜗杆工作齿宽。", default="32.0"),
]

WHEEL_GEOMETRY_FIELDS = [
    FieldSpec("geometry.z2", "蜗轮齿数 z2", "-", "蜗轮总齿数。", default="40"),
    FieldSpec("geometry.wheel_face_width_mm", "蜗轮齿宽 b2", "mm", "蜗轮工作齿宽。", default="28.0"),
]

MESH_GEOMETRY_FIELDS = [
    FieldSpec("geometry.center_distance_mm", "中心距 a", "mm", "蜗杆与蜗轮轴线距离。", default="84.0"),
]

MATERIAL_FIELDS = [
    FieldSpec(
        "materials.worm_material",
        "蜗杆材料",
        "-",
        "例如渗碳钢。",
        widget_type="choice",
        options=("20CrMnTi", "16MnCr5", "42CrMo"),
        default="20CrMnTi",
    ),
    FieldSpec(
        "materials.wheel_material",
        "蜗轮材料",
        "-",
        "例如锡青铜。",
        widget_type="choice",
        options=("ZCuSn12Ni2", "ZCuSn10P1", "AlCu4Ni2Fe"),
        default="ZCuSn12Ni2",
    ),
]

TOLERANCE_FIELDS = [
    FieldSpec("tolerance.tooth_thickness_allowance", "齿厚公差带", "mm", "齿厚/齿槽相关允许偏差记录项。", default="0.00"),
    FieldSpec("tolerance.center_distance_allowance", "中心距偏差", "mm", "装配中心距允许偏差。", default="0.00"),
    FieldSpec("tolerance.normal_backlash", "法向回差 j", "mm", "回差记录项。", default="0.10"),
]

OPERATING_FIELDS = [
    FieldSpec("operating.power_kw", "输入功率 P", "kW", "输入轴功率。", default="3.0"),
    FieldSpec("operating.speed_rpm", "输入转速 n", "rpm", "蜗杆轴转速。", default="1450"),
    FieldSpec("operating.application_factor", "使用系数 KA", "-", "工况冲击影响的简化系数。", default="1.25"),
    FieldSpec(
        "operating.lubrication",
        "润滑方式",
        "-",
        "润滑记录项。",
        widget_type="choice",
        options=("油浴润滑", "飞溅润滑", "强制润滑"),
        default="油浴润滑",
    ),
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
    ("pitch_diameter_mm", "分度圆直径 d2", "mm", "由中心距与蜗杆分度圆自动计算。"),
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
            subtitle="首版实现几何与基础性能，Load Capacity 保留 DIN 3996 / ISO / Niemann 骨架。",
            parent=parent,
        )
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._last_result: dict[str, Any] | None = None
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

        self._build_input_steps()
        self._build_graphics_step()
        self._build_load_capacity_step()
        self._build_results_step()
        self._apply_defaults()
        self.set_current_chapter(0)
        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("worm_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("worm_case_02.json"))
        self.set_info("按左侧顺序输入 DIN 3975 参数，再执行计算。")

    def _build_input_steps(self) -> None:
        self.add_chapter(
            "基本设置",
            self._create_form_page("基本设置", "定义本版标准边界和 Load Capacity 骨架状态。", BASIC_SETTINGS_FIELDS),
        )
        self.add_chapter("几何参数", self._create_geometry_page())
        self.add_chapter(
            "材料与配对",
            self._create_form_page("材料与配对", "为基础效率和后续 3996 留出材料接口。", MATERIAL_FIELDS),
        )
        self.add_chapter(
            "公差与回差",
            self._create_form_page("公差与回差", "先保留 manual 风格的输入与说明，图示首版为高质量占位图。", TOLERANCE_FIELDS),
        )
        self.add_chapter(
            "工况与润滑",
            self._create_form_page("工况与润滑", "基础效率、损失功率和热功率估算输入。", OPERATING_FIELDS),
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
            "按蜗杆、蜗轮、啮合装配分组输入。可推导尺寸放到只读区，避免与必要输入混淆。",
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
        card.setObjectName("SubCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel(title, card)
        title_label.setObjectName("SubSectionTitle")
        layout.addWidget(title_label)

        for key, label_text, unit_text, hint_text in fields:
            row_card = QFrame(card)
            row_card.setObjectName("SubCard")
            row = QGridLayout(row_card)
            row.setContentsMargins(12, 10, 12, 10)
            row.setHorizontalSpacing(10)
            row.setVerticalSpacing(4)

            label = QLabel(label_text, row_card)
            label.setObjectName("SubSectionTitle")
            value_label = QLabel("待输入", row_card)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setObjectName("SectionHint")
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
                combo.currentTextChanged.connect(lambda _text: self._refresh_derived_geometry_preview())
            self._field_widgets[spec.field_id] = combo
            self._field_specs[spec.field_id] = spec
            return combo

        editor = QLineEdit(parent)
        editor.setText(spec.default)
        if spec.placeholder:
            editor.setPlaceholderText(spec.placeholder)
        if spec.field_id.startswith("geometry."):
            editor.textChanged.connect(lambda _text: self._refresh_derived_geometry_preview())
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
        hint = QLabel("几何图和公差图先用高质量占位图，性能曲线在接入计算后展示真实结果。", page)
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
        self.tolerance_overview = WormToleranceOverviewWidget(container)
        self.performance_curve = WormPerformanceCurveWidget(container)
        body.addWidget(self.geometry_overview)
        body.addWidget(self.tolerance_overview)
        body.addWidget(self.performance_curve)
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
        hint = QLabel("保留 DIN 3996 / ISO 14521 / Niemann 的操作位置，但本版不执行真实校核。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        self.load_capacity_status = QLabel("DIN 3996 校核尚未开始", page)
        self.load_capacity_status.setObjectName("WaitBadge")
        self.load_capacity_note = QLabel(
            "当前版本只保存方法选择和相关输入，不输出接触强度、弯曲强度或热负载能力校核结果。",
            page,
        )
        self.load_capacity_note.setObjectName("SectionHint")
        self.load_capacity_note.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.load_capacity_status, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.load_capacity_note)
        layout.addStretch(1)
        self.add_chapter("Load Capacity", page)

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
        layout.addWidget(title)
        layout.addWidget(self.result_title)
        layout.addWidget(self.result_summary)
        layout.addWidget(self.result_metrics)
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
                text = "启用" if spec.field_id == "load_capacity.enabled" and bool(value) else str(value)
                if spec.field_id == "load_capacity.enabled" and str(value) == "关闭":
                    text = "关闭"
                index = widget.findText(text)  # type: ignore[attr-defined]
                if index >= 0:
                    widget.setCurrentIndex(index)  # type: ignore[attr-defined]
            else:
                widget.setText(str(value))  # type: ignore[attr-defined]
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
                    raise InputError(f"字段“{spec.label}”请输入数字，当前值: {raw}") from exc
            section, key = spec.field_id.split(".", 1)
            payload.setdefault(section, {})[key] = value
        return payload

    def _refresh_derived_geometry_preview(self) -> None:
        try:
            payload = self._build_payload()
            geometry = calculate_worm_geometry(payload)["geometry"]
        except (InputError, ValueError):
            self._reset_dimension_preview_labels()
            return

        self._set_dimension_group_values(self.worm_dimension_labels, geometry.get("worm_dimensions", {}), WORM_DIMENSION_FIELDS)
        self._set_dimension_group_values(self.wheel_dimension_labels, geometry.get("wheel_dimensions", {}), WHEEL_DIMENSION_FIELDS)

    def _reset_dimension_preview_labels(self) -> None:
        for label in list(self.worm_dimension_labels.values()) + list(self.wheel_dimension_labels.values()):
            label.setText("待输入")

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

    def _calculate(self) -> None:
        try:
            payload = self._build_payload()
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

        self.result_title.setText("已完成 DIN 3975 几何与基础性能计算")
        self.result_summary.setText("当前版本已生成几何结果、基础效率估算和性能曲线；Load Capacity 保持骨架状态。")
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
                    f"损失功率 = {performance['power_loss_kw']:.4f} kW",
                    f"热功率相关值 = {performance['thermal_capacity_kw']:.4f} kW",
                ]
            )
        )
        self.performance_curve.set_curves(
            load_factor=curve["load_factor"],
            efficiency=curve["efficiency"],
            power_loss_kw=curve["power_loss_kw"],
            thermal_capacity_kw=curve["thermal_capacity_kw"],
            current_index=curve["current_index"],
        )
        self.geometry_overview.set_display_state(
            "几何总览",
            f"i={geometry['ratio']:.2f}，a={geometry['center_distance_mm']:.1f} mm，gamma={geometry['lead_angle_deg']:.1f} deg",
        )
        self.tolerance_overview.set_display_state(
            "公差与回差",
            "首版保留说明结构与占位图；后续接入真实公差计算与回差算法。",
        )
        self.load_capacity_status.setText(load_capacity["status"])
        self._refresh_derived_geometry_preview()
        self.set_overall_status("DIN 3975 已计算", "pass")
        self.set_info("已完成 DIN 3975 几何与基础性能计算。DIN 3996 仍为延后状态。")
        self.set_current_chapter(self.chapter_stack.count() - 1)

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
        self.set_info(f"已加载测试案例：{filename}")

    def _clear(self) -> None:
        self._last_result = None
        self._apply_defaults()
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText("执行计算后显示 DIN 3975 几何结果、基础性能和 Load Capacity 延后状态。")
        self.result_metrics.setPlainText("尚无结果。")
        self.performance_curve.set_curves(
            load_factor=[],
            efficiency=[],
            power_loss_kw=[],
            thermal_capacity_kw=[],
            current_index=-1,
        )
        self.geometry_overview.set_display_state("几何总览", "按 DIN 3975 展示蜗杆、蜗轮、中心距与导程角关系。")
        self.tolerance_overview.set_display_state("公差与回差", "展示齿厚、公差带、中心距偏差与回差概念。")
        self.load_capacity_status.setText("DIN 3996 校核尚未开始")
        self.set_overall_status("等待计算", "wait")
        self.set_info("参数已重置，可重新执行 DIN 3975 计算。")
