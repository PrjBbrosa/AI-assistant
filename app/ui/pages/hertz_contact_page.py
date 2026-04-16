"""Hertz contact-stress module page with chapter workflow."""

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
from app.ui.fonts import make_ui_font
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import export_report_lines
from app.ui.widgets.hertz_input_diagram import HertzInputDiagramWidget
from core.hertz.calculator import InputError, calculate_hertz_contact

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)

MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29},
    "GCr15": {"e_mpa": 208000.0, "nu": 0.30},
    "45钢": {"e_mpa": 210000.0, "nu": 0.30},
    "铸铁 HT250": {"e_mpa": 120000.0, "nu": 0.26},
    "铝合金 6061-T6": {"e_mpa": 69000.0, "nu": 0.33},
    "自定义": None,
}
MATERIAL_OPTIONS: tuple[str, ...] = tuple(MATERIAL_LIBRARY.keys())
CONTACT_MODE_OPTIONS = ("线接触", "点接触")


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
        "subtitle": "定义允许接触应力和曲线采样参数。",
        "fields": [
            FieldSpec(
                "checks.allowable_p0_mpa",
                "允许最大接触应力 [p0]",
                "MPa",
                "与材料接触疲劳极限或规范限值对应。",
                mapping=("checks", "allowable_p0_mpa"),
                default="1500",
                placeholder="例如 1500",
            ),
            FieldSpec(
                "options.curve_points",
                "压力-载荷曲线采样点数",
                "点",
                "结果曲线离散点数量（11~201）。",
                mapping=("options", "curve_points"),
                default="41",
                placeholder="例如 41",
            ),
            FieldSpec(
                "options.curve_force_scale",
                "曲线载荷上限倍率",
                "-",
                "曲线终点载荷 = 设计载荷 * 倍率。",
                mapping=("options", "curve_force_scale"),
                default="1.30",
                placeholder="1.05~2.0",
            ),
        ],
    },
    {
        "title": "接触模型与几何",
        "subtitle": "线接触和点接触共用输入；点接触时长度 L 不参与。",
        "fields": [
            FieldSpec(
                "geometry.contact_mode",
                "接触类型",
                "-",
                "线接触：圆柱-圆柱/圆柱-平面；点接触：球-球/球-平面。",
                widget_type="choice",
                options=CONTACT_MODE_OPTIONS,
                default="线接触",
            ),
            FieldSpec(
                "geometry.r1_mm",
                "曲率半径 R1",
                "mm",
                "第 1 接触体曲率半径。",
                mapping=("geometry", "r1_mm"),
                default="30.0",
                placeholder="例如 30",
            ),
            FieldSpec(
                "geometry.r2_mm",
                "曲率半径 R2",
                "mm",
                "第 2 接触体曲率半径；平面可填 0。",
                mapping=("geometry", "r2_mm"),
                default="0.0",
                placeholder="平面填 0",
            ),
            FieldSpec(
                "geometry.length_mm",
                "接触长度 L（线接触）",
                "mm",
                "线接触按单位长度载荷计算；点接触时该值仅记录。",
                mapping=("geometry", "length_mm"),
                default="20.0",
                placeholder="例如 20",
            ),
        ],
    },
    {
        "title": "材料参数",
        "subtitle": "两侧材料参数共同决定等效弹性模量 E'。",
        "fields": [
            FieldSpec(
                "materials.body1_material",
                "接触体 1 材料",
                "-",
                "选择后自动带出 E1/nu1；可切到自定义。",
                widget_type="choice",
                options=MATERIAL_OPTIONS,
                default="42CrMo",
            ),
            FieldSpec(
                "materials.e1_mpa",
                "弹性模量 E1",
                "MPa",
                "接触体 1 弹性模量。",
                mapping=("materials", "e1_mpa"),
                default="210000",
            ),
            FieldSpec(
                "materials.nu1",
                "泊松比 nu1",
                "-",
                "接触体 1 泊松比。",
                mapping=("materials", "nu1"),
                default="0.29",
            ),
            FieldSpec(
                "materials.body2_material",
                "接触体 2 材料",
                "-",
                "选择后自动带出 E2/nu2；可切到自定义。",
                widget_type="choice",
                options=MATERIAL_OPTIONS,
                default="45钢",
            ),
            FieldSpec(
                "materials.e2_mpa",
                "弹性模量 E2",
                "MPa",
                "接触体 2 弹性模量。",
                mapping=("materials", "e2_mpa"),
                default="210000",
            ),
            FieldSpec(
                "materials.nu2",
                "泊松比 nu2",
                "-",
                "接触体 2 泊松比。",
                mapping=("materials", "nu2"),
                default="0.30",
            ),
        ],
    },
    {
        "title": "载荷输入",
        "subtitle": "赫兹接触按法向载荷计算接触区与最大接触应力。",
        "fields": [
            FieldSpec(
                "loads.normal_force_n",
                "法向载荷 F",
                "N",
                "作用在接触区法向方向的载荷。",
                mapping=("loads", "normal_force_n"),
                default="12000",
                placeholder="例如 12000",
            ),
        ],
    },
]

CHECK_LABELS = {
    "contact_stress_ok": "最大接触应力校核",
}

BEGINNER_GUIDES: dict[str, str] = {
    "geometry.contact_mode": "先选接触类型，再填对应几何参数。",
    "geometry.r2_mm": "若为平面接触可输入 0，程序按无穷大半径处理。",
    "geometry.length_mm": "仅在线接触时用于把 F 转换为单位长度载荷 F'。",
    "checks.allowable_p0_mpa": "可按材料/热处理接触疲劳许用值设置。",
    "loads.normal_force_n": "取峰值载荷；冲击工况建议乘载荷系数后输入。",
}


class HertzContactPage(BaseChapterPage):
    """Hertz contact-stress chapter page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="赫兹应力 · 接触校核",
            subtitle="替代轴承占位模块，支持线接触/点接触的赫兹最大接触应力计算。",
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
        self._apply_defaults()
        self._load_sample("hertz_case_01.json")
        self._sync_material_inputs()
        self._apply_mode_visibility()
        self._refresh_diagram_from_inputs()

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
            if spec.field_id == self._mode_field_id:
                editor.currentTextChanged.connect(lambda _text: self._apply_mode_visibility())
                editor.currentTextChanged.connect(lambda _text: self._refresh_diagram_from_inputs())
            if spec.field_id in self._material_links:
                editor.currentTextChanged.connect(lambda _text: self._refresh_diagram_from_inputs())
        else:
            editor = QLineEdit(parent)
            editor.setObjectName("InputField")
            editor.setPlaceholderText(spec.placeholder or "请输入数值")
            if spec.default:
                editor.setText(spec.default)
            if spec.field_id in {
                "geometry.r1_mm",
                "geometry.r2_mm",
                "geometry.length_mm",
                "loads.normal_force_n",
                "materials.e1_mpa",
                "materials.nu1",
                "materials.e2_mpa",
                "materials.nu2",
            }:
                editor.textChanged.connect(lambda _text: self._refresh_diagram_from_inputs())

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
        material = MATERIAL_LIBRARY.get(selector.currentText().strip())
        is_custom = material is None
        e_widget.setReadOnly(not is_custom)
        nu_widget.setReadOnly(not is_custom)
        if material is not None:
            e_widget.setText(f"{material['e_mpa']:.0f}")
            nu_widget.setText(f"{material['nu']:.2f}")

    def _sync_material_inputs(self) -> None:
        for selector_id in self._material_links:
            self._apply_material_selection(selector_id)

    def _is_point_mode(self) -> bool:
        mode_widget = self._field_widgets.get(self._mode_field_id)
        if not isinstance(mode_widget, QComboBox):
            return False
        return mode_widget.currentText() == "点接触"

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
            if spec.widget_type == "choice":
                combo = widget  # type: ignore[assignment]
                if spec.default:
                    idx = combo.findText(spec.default)  # type: ignore[attr-defined]
                    if idx >= 0:
                        combo.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(spec.default)  # type: ignore[attr-defined]
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
            if spec.widget_type == "choice":
                value: Any = raw
            else:
                if raw == "":
                    continue
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise InputError(f"字段“{spec.label}”请输入数字，当前值: {raw}") from exc
            sec, key = spec.mapping
            payload.setdefault(sec, {})[key] = value

        mode_text = self._field_widgets[self._mode_field_id].currentText().strip()  # type: ignore[attr-defined]
        payload.setdefault("geometry", {})["contact_mode"] = "point" if mode_text == "点接触" else "line"
        return payload

    def _calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_hertz_contact(payload)
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
        if overall:
            self.result_title.setText("校核通过")
            self.result_summary.setText("该工况满足允许接触应力要求。")
            self.set_overall_status("总体通过", "pass")
        else:
            self.result_title.setText("校核不通过")
            self.result_summary.setText("最大接触应力超过允许值，请调整几何/材料/载荷。")
            self.set_overall_status("总体不通过", "fail")

        for key, badge in self._check_badges.items():
            ok = bool(result.get("checks", {}).get(key, False))
            self._set_badge(badge, "通过" if ok else "不通过", "pass" if ok else "fail")

        mode = "线接触" if result["mode"] == "line" else "点接触"
        contact = result["contact"]
        derived = result["derived"]
        check = result["check"]
        if result["mode"] == "line":
            patch_line = f"• 接触半宽: b = {contact['semi_width_mm']:.4f} mm"
        else:
            patch_line = f"• 接触半径: a = {contact['contact_radius_mm']:.4f} mm"
        lines = [
            f"• 接触模型: {mode}",
            f"• 等效弹性模量: E' = {derived['e_eq_mpa']:.1f} MPa",
            f"• 等效曲率半径: R' = {derived['r_eq_mm']:.4f} mm",
            patch_line,
            f"• 最大接触应力: p0 = {contact['p0_mpa']:.2f} MPa",
            f"• 平均接触应力: p_mean = {contact['p_mean_mpa']:.2f} MPa",
            f"• 允许应力与安全系数: [p0]={check['allowable_p0_mpa']:.2f} MPa, S={check['safety_factor']:.3f}",
        ]
        self.metrics_text.setText("\n".join(lines))

        self._refresh_diagram_from_inputs()
        messages: list[str] = []
        for msg in result.get("warnings", []):
            messages.append(f"[提示] {msg}")
        messages.extend(self._build_recommendations(result))
        messages.append("[说明] 当前基于标准赫兹弹性接触理论，未包含弹塑性与边缘修正。")
        self.message_box.setPlainText("\n".join(messages))

    def _build_recommendations(self, result: dict[str, Any]) -> list[str]:
        recs: list[str] = []
        if not result.get("checks", {}).get("contact_stress_ok", True):
            recs.append("[建议] 可增大等效曲率半径、降低法向载荷或提高材料许用接触应力。")
        if result.get("check", {}).get("safety_factor", 0.0) < 1.2:
            recs.append("[建议] 安全系数低于 1.2，建议增加工程裕量。")
        if not recs:
            recs.append("[建议] 当前工况满足校核要求，建议结合疲劳寿命再复核。")
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
                mode_widget.setCurrentText("点接触" if mode == "point" else "线接触")

        self._sync_material_inputs()
        self._apply_mode_visibility()
        self._refresh_diagram_from_inputs()

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
        self.set_overall_status("等待计算", "wait")
        self.set_info("参数已重置为默认值。")
        self._refresh_diagram_from_inputs()

    def _save_report(self) -> None:
        if self._last_result is None:
            QMessageBox.information(self, "无结果", "请先执行校核计算。")
            return
        default_path = EXAMPLES_DIR / "hertz_contact_report.pdf"
        out_path = export_report_lines(self, "导出结果说明", default_path, self._build_report_lines())
        if out_path is not None:
            self.set_info(f"结果说明已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        assert self._last_result is not None
        result = self._last_result
        contact = result["contact"]
        derived = result["derived"]
        check = result["check"]
        lines = [
            "赫兹接触应力校核报告（本地版）",
            f"生成时间: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"接触模型: {'线接触' if result['mode'] == 'line' else '点接触'}",
            "",
            f"总体结论: {'通过' if result['overall_pass'] else '不通过'}",
            "",
            "关键结果:",
            f"- E': {derived['e_eq_mpa']:.3f} MPa",
            f"- R': {derived['r_eq_mm']:.6f} mm",
            f"- p0: {contact['p0_mpa']:.3f} MPa",
            f"- p_mean: {contact['p_mean_mpa']:.3f} MPa",
            f"- [p0]: {check['allowable_p0_mpa']:.3f} MPa",
            f"- Safety: {check['safety_factor']:.3f}",
        ]
        if result["mode"] == "line":
            lines.append(f"- b: {contact['semi_width_mm']:.6f} mm")
        else:
            lines.append(f"- a: {contact['contact_radius_mm']:.6f} mm")
        lines.extend(["", "建议:"])
        lines.extend(f"- {msg}" for msg in self._build_recommendations(result))
        return lines
