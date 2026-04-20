"""Chapter-style page for tapped axial threaded joint inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
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

from app.ui.input_condition_store import (
    build_form_snapshot,
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    read_input_conditions,
    write_input_conditions,
)
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.widgets.help_button import HelpButton
from core.bolt.tapped_axial_joint import (
    _derive_thread_section,
    calculate_tapped_axial_joint,
)
from core.bolt import InputError


# Codex §3.2：As/d2/d3 自动派生，不允许手动覆盖
_AUTO_DERIVED_FIELDS: tuple[str, ...] = ("fastener.As", "fastener.d2", "fastener.d3")


PROJECT_ROOT = Path(__file__).resolve().parents[3]
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
    help_ref: str = ""

    @property
    def mapping(self) -> tuple[str, str] | None:
        if "." not in self.field_id:
            return None
        return tuple(self.field_id.split(".", 1))  # type: ignore[return-value]


CHECK_LABELS: dict[str, str] = {
    "assembly_von_mises_ok": "装配 von Mises 强度",
    "service_von_mises_ok": "服役最大 von Mises 强度",
    "fatigue_ok": "交变轴向疲劳",
    "thread_strip_ok": "螺纹脱扣",
}

CHAPTERS: list[dict[str, Any]] = [
    {
        "id": "scope",
        "title": "适用范围与建模假设",
        "subtitle": "确认你的连接适合这个模块：螺栓直接拧入螺纹孔、无被夹件、纯轴向拉载荷。带法兰/垫片的夹紧连接请用 VDI 2230 螺栓页。",
        "help_ref": "modules/bolt_tapped_axial/_section_scope",
        "fields": [],
        "notes": [
            "带被夹件的夹紧连接（法兰+垫片+法兰）请使用「螺栓连接」模块，本页结果不适用。",
            "本模块不支持横向力、弯矩、多螺栓并联、压向载荷；这些工况需另做专项分析。",
        ],
    },
    {
        "id": "fastener_material",
        "title": "螺纹与材料参数",
        "subtitle": "填螺栓规格与材料强度：公称直径 d 和螺距 p 填好后，中径 d2、小径 d3、应力截面积 As 会按 ISO 公式自动派生并锁为只读。",
        "help_ref": "modules/bolt_tapped_axial/_section_fastener_material",
        "fields": [
            FieldSpec("fastener.d", "公称直径 d", "mm", "螺栓公称直径，按实际螺纹规格填写。", default="10.0", help_ref="terms/bolt_thread_nominal"),
            FieldSpec("fastener.p", "螺距 p", "mm", "螺纹螺距。", default="1.5", help_ref="terms/bolt_thread_pitch"),
            FieldSpec("fastener.d2", "中径 d2", "mm", "由 d/p 自动派生。", default="", help_ref="terms/bolt_stress_area"),
            FieldSpec("fastener.d3", "小径 d3", "mm", "由 d/p 自动派生。", default="", help_ref="terms/bolt_stress_area"),
            FieldSpec("fastener.As", "应力截面积 As", "mm²", "由 d/p 自动派生。", default="", help_ref="terms/bolt_stress_area"),
            FieldSpec("fastener.Rp02", "屈服强度 Rp0.2", "MPa", "螺栓材料屈服强度。", default="640.0", help_ref="terms/bolt_yield_strength"),
            FieldSpec("fastener.E_bolt", "螺栓弹性模量 E_bolt", "MPa", "螺栓弹性模量。", default="210000.0", help_ref="terms/elastic_modulus"),
            FieldSpec(
                "fastener.grade",
                "强度等级 grade",
                "-",
                "强度等级字符串，保留为便于追溯。",
                widget_type="choice",
                options=("8.8", "10.9", "12.9"),
                default="8.8",
                help_ref="terms/bolt_grade",
            ),
        ],
    },
    {
        "id": "assembly_preload",
        "title": "预紧与装配参数",
        "subtitle": "设置装配过程：最小预紧力、装配散差 α_A、摩擦系数、支承几何、拧紧工艺。这些决定装配扭矩 MA 与装配 von Mises 校核。",
        "help_ref": "modules/bolt_tapped_axial/_section_assembly_preload",
        "fields": [
            FieldSpec("assembly.F_preload_min", "最小预紧力 F_preload_min", "N", "装配后可保证达到的最小预紧力。", default="12000.0", help_ref="terms/bolt_preload_fm"),
            FieldSpec("assembly.alpha_A", "装配散差系数 alpha_A", "-", "预紧力上限与下限的比值。", default="1.6", help_ref="terms/bolt_tightening_factor_alpha_a"),
            FieldSpec("assembly.mu_thread", "螺纹摩擦系数 mu_thread", "-", "螺纹副摩擦系数。", default="0.12", help_ref="terms/bolt_friction_thread"),
            FieldSpec("assembly.mu_bearing", "支承面摩擦系数 mu_bearing", "-", "支承面摩擦系数。", default="0.14", help_ref="terms/bolt_friction_bearing"),
            FieldSpec("assembly.bearing_d_inner", "支承内径 bearing_d_inner", "mm", "支承面内径。", default="11.0"),
            FieldSpec("assembly.bearing_d_outer", "支承外径 bearing_d_outer", "mm", "支承面外径。", default="18.0"),
            FieldSpec("assembly.prevailing_torque", "附加防松扭矩 prevailing_torque", "N·m", "锁紧件（尼龙圈螺母、螺纹胶等）产生的附加扭矩。", default="0.0", help_ref="terms/bolt_tapped_axial_prevailing_torque"),
            FieldSpec("assembly.thread_flank_angle_deg", "牙型角 thread_flank_angle_deg", "deg", "公制螺纹常用 60°。", default="60.0"),
            FieldSpec(
                "assembly.tightening_method",
                "拧紧方式 tightening_method",
                "-",
                "拧紧工艺；决定 α_A 建议区间与服役残余扭转系数 k_τ。",
                widget_type="choice",
                options=("torque", "angle", "hydraulic", "thermal"),
                default="torque",
                help_ref="terms/bolt_tightening_method",
            ),
            FieldSpec("assembly.utilization", "装配利用系数 utilization", "-", "预紧力利用比例 ν；装配许用应力 = ν·Rp0.2。", default="0.9", help_ref="terms/bolt_utilization_nu"),
        ],
    },
    {
        "id": "axial_load",
        "title": "轴向工作载荷",
        "subtitle": "填一个循环中外部轴向拉力的最小值 FA_min 和最大值 FA_max。两者共同决定服役应力、疲劳平均应力与应力幅。",
        "help_ref": "modules/bolt_tapped_axial/_section_axial_load",
        "fields": [
            FieldSpec("service.FA_min", "最小轴向载荷 FA_min", "N", "一个循环中的最小轴向拉载荷。静载时 = FA_max。", default="0.0", help_ref="terms/bolt_tapped_axial_axial_load_range"),
            FieldSpec("service.FA_max", "最大轴向载荷 FA_max", "N", "一个循环中的最大轴向拉载荷（含动载放大系数）。", default="6000.0", help_ref="terms/bolt_tapped_axial_axial_load_range"),
        ],
    },
    {
        "id": "thread_strip",
        "title": "螺纹脱扣",
        "subtitle": "校核螺纹是否会被剪断（尤其重要：螺栓旋入铝/铸铁壳体）。留空 m_eff 会让整体结论判为「校核不完整」，不会给绿灯。",
        "help_ref": "modules/bolt_tapped_axial/_section_thread_strip",
        "fields": [
            FieldSpec("thread_strip.m_eff", "有效啮合长度 m_eff", "mm", "螺栓实际旋入内螺纹的承载长度。留空跳过 R8 并判 incomplete。", default="", help_ref="terms/bolt_thread_engagement"),
            FieldSpec("thread_strip.tau_BM", "母材许用剪应力 tau_BM", "MPa", "内螺纹对手件的剪切强度；典型 0.6·Rp0.2。启用 R8 时必填。", default="", help_ref="terms/bolt_thread_strip_tau"),
            FieldSpec("thread_strip.tau_BS", "螺栓许用剪应力 tau_BS", "MPa", "外螺纹剪切强度；留空默认 0.6·Rp0.2。", default="", help_ref="terms/bolt_thread_strip_tau"),
            FieldSpec("thread_strip.safety_required", "脱扣目标安全系数", "-", "设计要求的最小 S_strip。典型 1.25–1.5。", default="1.5", help_ref="terms/bolt_tapped_axial_strip_safety_required"),
        ],
    },
    {
        "id": "fatigue_output",
        "title": "交变轴向疲劳与输出选项",
        "subtitle": "设置疲劳参数（循环次数、螺纹成形工艺）与服役屈服安全系数；选择报告详细程度。",
        "help_ref": "modules/bolt_tapped_axial/_section_fatigue_output",
        "fields": [
            FieldSpec("fatigue.load_cycles", "载荷循环次数 load_cycles", "次", "服役寿命内的疲劳循环次数。高周默认 2×10⁶ 保守。", default="1000000.0", help_ref="terms/bolt_tapped_axial_load_cycles"),
            FieldSpec(
                "fatigue.surface_treatment",
                "螺纹表面处理 surface_treatment",
                "-",
                "螺纹成形方式：rolled（标准螺栓滚轧）/ cut（后加工切削）。cut 会让 σ_ASV 折减至 65%。",
                widget_type="choice",
                options=("rolled", "cut"),
                default="rolled",
                help_ref="terms/bolt_tapped_axial_surface_treatment",
            ),
            FieldSpec("checks.yield_safety_operating", "服役屈服安全系数 yield_safety_operating", "-", "服役 von Mises 许用 = Rp0.2 / S_yield。", default="1.15", help_ref="terms/bolt_yield_safety"),
            FieldSpec(
                "options.report_mode",
                "报告模式 report_mode",
                "-",
                "报告详细程度；不影响计算。",
                widget_type="choice",
                options=("full", "compact"),
                default="full",
            ),
        ],
    },
]


class BoltTappedAxialPage(BaseChapterPage):
    """Chapter page for the tapped axial threaded joint module."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="轴向受力螺纹连接 · ISO 898 / VDI",
            subtitle="螺栓拧入螺纹对手件、无被夹件、纯轴向拉载荷场景。",
            parent=parent,
        )
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._suspend_live_feedback = False

        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_calculate = self.add_action_button("开始计算")
        self.btn_export_text = self.add_action_button("导出文本报告")
        self.btn_export_pdf = self.add_action_button("导出 PDF 报告")

        self._build_input_chapters()
        self._build_result_chapter()
        self.set_current_chapter(0)

        self.btn_save_inputs.clicked.connect(self._save_input_conditions)
        self.btn_load_inputs.clicked.connect(self._load_input_conditions)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_calculate.clicked.connect(self._run_calculation)
        self.btn_export_text.clicked.connect(self._export_text_report)
        self.btn_export_pdf.clicked.connect(self._export_pdf_report)

        # Codex §3.2：把 As/d2/d3 改为只读 AutoCalcCard
        for fid in _AUTO_DERIVED_FIELDS:
            self._set_card_autocalc(fid, True)

        self._suspend_live_feedback = True
        self._apply_defaults()
        self._refresh_thread_section()
        self._suspend_live_feedback = False

        self._invalidate_cache()  # 初始禁用导出按钮
        self.set_overall_status("等待计算", "wait")
        self.set_info('填写输入条件后点击"开始计算"。')

    def _build_input_chapters(self) -> None:
        for chapter in CHAPTERS:
            page = self._create_chapter_page(
                chapter["title"],
                chapter["subtitle"],
                chapter["fields"],
                chapter.get("notes", []),
                help_ref=chapter.get("help_ref", ""),
            )
            self.add_chapter(chapter["title"], page)

    def _create_chapter_page(
        self,
        title: str,
        subtitle: str,
        fields: list[FieldSpec],
        notes: list[str],
        help_ref: str = "",
    ) -> QWidget:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title_label = QLabel(title, page)
        title_label.setObjectName("SectionTitle")
        if help_ref:
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
            layout.addWidget(header_row)
        else:
            layout.addWidget(title_label)
        subtitle_label = QLabel(subtitle, page)
        subtitle_label.setObjectName("SectionHint")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

        if notes:
            note_card = QFrame(page)
            note_card.setObjectName("SubCard")
            note_layout = QVBoxLayout(note_card)
            note_layout.setContentsMargins(12, 10, 12, 10)
            note_layout.setSpacing(4)
            for note in notes:
                label = QLabel(f"• {note}", note_card)
                label.setObjectName("SectionHint")
                label.setWordWrap(True)
                note_layout.addWidget(label)
            layout.addWidget(note_card)

        if fields:
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
            layout.addWidget(scroll, 1)
        else:
            spacer = QLabel("该章节仅提供范围说明，不包含输入项。", page)
            spacer.setObjectName("SectionHint")
            spacer.setWordWrap(True)
            layout.addWidget(spacer)

        return page

    def _build_result_chapter(self) -> None:
        """Build the result display chapter with badges, metrics, and messages."""
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # --- 摘要卡片 ---
        summary_card = QFrame(page)
        summary_card.setObjectName("SubCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)
        self.result_title = QLabel("尚未执行计算", summary_card)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel(
            "填写参数并点击\u201c开始计算\u201d后，这里显示结论。", summary_card
        )
        self.result_summary.setObjectName("SectionHint")
        self.result_summary.setWordWrap(True)
        summary_layout.addWidget(self.result_title)
        summary_layout.addWidget(self.result_summary)
        layout.addWidget(summary_card)

        # --- 分项校核卡片 ---
        checks_card = QFrame(page)
        checks_card.setObjectName("SubCard")
        checks_layout = QGridLayout(checks_card)
        checks_layout.setContentsMargins(12, 10, 12, 10)
        checks_layout.setHorizontalSpacing(12)
        checks_layout.setVerticalSpacing(8)
        checks_layout.addWidget(QLabel("分项校核", checks_card), 0, 0)
        checks_layout.addWidget(QLabel("状态", checks_card), 0, 1)
        self._check_badges: dict[str, QLabel] = {}
        row = 1
        for key, text in CHECK_LABELS.items():
            name_label = QLabel(text, checks_card)
            status_label = QLabel("待计算", checks_card)
            status_label.setObjectName("WaitBadge")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setMinimumWidth(64)
            status_label.setFixedHeight(24)
            checks_layout.addWidget(name_label, row, 0)
            checks_layout.addWidget(status_label, row, 1)
            self._check_badges[key] = status_label
            row += 1
        layout.addWidget(checks_card)

        # --- 关键结果值卡片 ---
        metrics_card = QFrame(page)
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
        layout.addWidget(metrics_card)

        # --- 消息与建议卡片 ---
        msg_card = QFrame(page)
        msg_card.setObjectName("SubCard")
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setContentsMargins(12, 10, 12, 10)
        msg_layout.setSpacing(6)
        msg_title_label = QLabel("消息与建议", msg_card)
        msg_title_label.setObjectName("SubSectionTitle")
        self.message_box = QPlainTextEdit(msg_card)
        self.message_box.setReadOnly(True)
        self.message_box.setMinimumHeight(140)
        msg_layout.addWidget(msg_title_label)
        msg_layout.addWidget(self.message_box)
        layout.addWidget(msg_card)

        self.add_chapter("校核结果", page)

    def _create_editor(self, spec: FieldSpec, parent: QWidget) -> QWidget:
        if spec.widget_type == "choice":
            editor = QComboBox(parent)
            editor.addItems(spec.options)
            if spec.default:
                idx = editor.findText(spec.default)
                if idx >= 0:
                    editor.setCurrentIndex(idx)
            editor.currentTextChanged.connect(
                lambda _text, fid=spec.field_id: self._on_input_changed(fid)
            )
        else:
            editor = QLineEdit(parent)
            editor.setObjectName("InputField")
            editor.setPlaceholderText(spec.label)
            if spec.default:
                editor.setText(spec.default)
            editor.textChanged.connect(
                lambda _text, fid=spec.field_id: self._on_input_changed(fid)
            )

        editor.setToolTip(f"{spec.label}：{spec.hint}")
        self._field_widgets[spec.field_id] = editor
        self._field_specs[spec.field_id] = spec
        return editor

    def _apply_defaults(self) -> None:
        for spec in self._field_specs.values():
            widget = self._field_widgets[spec.field_id]
            if spec.widget_type == "choice":
                widget.setCurrentText(spec.default)  # type: ignore[attr-defined]
            else:
                widget.setText(spec.default)  # type: ignore[attr-defined]

    def _read_widget_value(self, spec: FieldSpec) -> str:
        widget = self._field_widgets[spec.field_id]
        if spec.widget_type == "choice":
            return widget.currentText().strip()  # type: ignore[attr-defined]
        return widget.text().strip()  # type: ignore[attr-defined]

    def _convert_value(self, spec: FieldSpec, raw: str) -> Any:
        if spec.widget_type == "choice":
            return raw
        if raw == "":
            return None
        try:
            if raw.lower() in {"nan", "inf", "-inf"}:
                raise ValueError(raw)
            return float(raw)
        except ValueError as exc:
            raise ValueError(f"字段“{spec.label}”请输入有效数字，当前值: {raw}") from exc

    def _build_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for spec in self._field_specs.values():
            raw = self._read_widget_value(spec)
            value = self._convert_value(spec, raw)
            if value is None:
                continue
            section, key = spec.mapping or (None, None)
            if section is None or key is None:
                continue
            payload.setdefault(section, {})[key] = value
        return payload

    def _capture_input_snapshot(self) -> dict[str, Any]:
        return build_form_snapshot(self._field_specs.values(), self._read_widget_value)

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        inputs_data = data.get("inputs")
        inputs = inputs_data if isinstance(inputs_data, dict) else data
        ui_state_data = data.get("ui_state")
        ui_state = ui_state_data if isinstance(ui_state_data, dict) else {}

        self._suspend_live_feedback = True
        self._apply_defaults()
        for spec in self._field_specs.values():
            # Codex §3.2：由 d/p 派生的字段不接受文件回填，避免旧截面残留
            if spec.field_id in _AUTO_DERIVED_FIELDS:
                continue
            value: Any | None = None
            if spec.field_id in ui_state:
                value = ui_state[spec.field_id]
            else:
                section, key = spec.mapping or (None, None)
                if section is not None and key is not None:
                    section_data = inputs.get(section)
                    if isinstance(section_data, dict) and key in section_data:
                        value = section_data[key]
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
        # 根据新 d/p 重算 As/d2/d3
        self._refresh_thread_section()
        self._suspend_live_feedback = False
        self._invalidate_cache()

    def _save_input_conditions(self) -> None:
        default_path = SAVED_INPUTS_DIR / "bolt_tapped_axial_input_conditions.json"
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
        self._suspend_live_feedback = True
        self._apply_defaults()
        self._refresh_thread_section()
        self._suspend_live_feedback = False
        self._invalidate_cache()
        self.set_overall_status("等待计算", "wait")
        self.set_info("参数已重置为默认值。")

    # --- Codex §3.2 / §3.4：AutoCalcCard + 缓存失效 ---

    def _set_card_autocalc(self, field_id: str, auto: bool) -> None:
        """Toggle a field card between SubCard and AutoCalcCard (auto-filled) style."""
        card = self._field_cards.get(field_id)
        if card is None:
            return
        card.setObjectName("AutoCalcCard" if auto else "SubCard")
        card.style().unpolish(card)
        card.style().polish(card)
        for child in card.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
        widget = self._field_widgets.get(field_id)
        if isinstance(widget, QLineEdit):
            widget.setReadOnly(auto)
        elif isinstance(widget, QComboBox):
            widget.setEnabled(not auto)

    def _refresh_thread_section(self) -> None:
        """Recompute As/d2/d3 from current d/p and push to the auto-filled widgets."""
        d_text = self._field_widgets.get("fastener.d")
        p_text = self._field_widgets.get("fastener.p")
        if not isinstance(d_text, QLineEdit) or not isinstance(p_text, QLineEdit):
            return
        try:
            d = float(d_text.text().strip())
            p = float(p_text.text().strip())
        except ValueError:
            return
        if d <= 0 or p <= 0:
            return
        section = _derive_thread_section(d, p)
        mapping = {
            "fastener.As": section["As"],
            "fastener.d2": section["d2"],
            "fastener.d3": section["d3"],
        }
        for fid, value in mapping.items():
            widget = self._field_widgets.get(fid)
            if not isinstance(widget, QLineEdit):
                continue
            widget.blockSignals(True)
            widget.setText(f"{value:.4f}")
            widget.blockSignals(False)

    def _invalidate_cache(self) -> None:
        """Clear cached calculation result and disable export buttons."""
        self._last_payload = None
        self._last_result = None
        self.btn_export_text.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)

    def _on_input_changed(self, field_id: str) -> None:
        if self._suspend_live_feedback:
            return
        # 派生字段自身变化不触发重算（它们由 _refresh_thread_section 写入，已 blockSignals）
        if field_id in _AUTO_DERIVED_FIELDS:
            return
        if field_id in ("fastener.d", "fastener.p"):
            self._refresh_thread_section()
        self._invalidate_cache()

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

    def _run_calculation(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_tapped_axial_joint(payload)
        except (InputError, ValueError) as exc:
            self._invalidate_cache()
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:
            self._invalidate_cache()
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        self._last_payload = payload
        self._last_result = result
        self.btn_export_text.setEnabled(True)
        self.btn_export_pdf.setEnabled(True)
        self._render_result(result)
        self.set_current_chapter(self.chapter_list.count() - 1)

    def _render_result(self, result: dict[str, Any]) -> None:
        # Codex §3.3：三态结论 pass / fail / incomplete
        overall_status = result.get("overall_status", "fail" if not result.get("overall_pass") else "pass")
        if overall_status == "pass":
            self.result_title.setText("校核通过")
            self.result_summary.setText("该工况满足全部校核要求。")
            self.set_overall_status("总体通过", "pass")
        elif overall_status == "incomplete":
            self.result_title.setText("校核不完整")
            self.result_summary.setText(
                "部分分项尚未校核（常见为螺纹脱扣未填啮合长度）。"
                "请补齐输入后重新计算再给出结论。"
            )
            self.set_overall_status("校核不完整", "wait")
        else:
            self.result_title.setText("校核不通过")
            self.result_summary.setText("存在不满足校核要求的项目，请查看分项结果与建议。")
            self.set_overall_status("总体不通过", "fail")

        for key, badge in self._check_badges.items():
            raw = result.get("checks", {}).get(key)
            if raw is None:
                self._set_badge(badge, "未校核", "wait")
            elif raw:
                self._set_badge(badge, "通过", "pass")
            else:
                self._set_badge(badge, "不通过", "fail")

        asm = result.get("assembly", {})
        stresses = result.get("stresses_mpa", {})
        fatigue = result.get("fatigue", {})
        ts = result.get("thread_strip", {})
        trace = result.get("trace", {}).get("intermediate", {})

        lines = [
            f"预紧力范围: F_min = {asm.get('F_preload_min_N', 0):.0f} N"
            f"  /  F_max = {asm.get('F_preload_max_N', 0):.0f} N",
            f"装配扭矩范围: MA_min = {asm.get('MA_min_Nm', 0):.2f} N·m"
            f"  /  MA_max = {asm.get('MA_max_Nm', 0):.2f} N·m",
            "",
            f"装配 von Mises: sigma_vm = {stresses.get('sigma_vm_assembly', 0):.1f} MPa"
            f"  (许用: {trace.get('sigma_allow_assembly', 0):.1f} MPa)",
            f"服役最大 von Mises: sigma_vm = {stresses.get('sigma_vm_service_max', 0):.1f} MPa"
            f"  (许用: {trace.get('sigma_allow_service', 0):.1f} MPa)",
            "",
            f"疲劳应力幅: sigma_a = {stresses.get('sigma_a_fatigue', 0):.2f} MPa"
            f"  (许用: {fatigue.get('sigma_a_allow', 0):.2f} MPa)",
            f"疲劳平均应力: sigma_m = {stresses.get('sigma_m_fatigue', 0):.1f} MPa",
            f"Goodman 折减系数: {fatigue.get('goodman_factor', 0):.3f}",
        ]

        if ts.get("active"):
            lines.append("")
            lines.append(
                f"螺纹脱扣安全系数: S = {ts.get('strip_safety', 0):.2f}"
                f"  (要求: >= {ts.get('strip_safety_required', 0):.2f})"
            )
            lines.append(f"临界侧: {ts.get('note', '')}")
        else:
            lines.append("")
            lines.append(f"螺纹脱扣: {ts.get('note', '')}")

        self.metrics_text.setText("\n".join(lines))

        messages: list[str] = []
        for w in result.get("warnings", []):
            messages.append(f"[警告] {w}")
        for r in result.get("recommendations", []):
            messages.append(f"[建议] {r}")
        scope = result.get("scope_note", "")
        if scope:
            messages.append(f"[说明] {scope}")
        self.message_box.setPlainText("\n".join(messages))

    def _build_report_lines(self) -> list[str]:
        if self._last_result is None:
            return ["尚未执行计算。"]

        result = self._last_result
        payload = self._last_payload or {}
        lines: list[str] = []

        lines.append("=" * 60)
        lines.append("轴向受力螺纹连接校核报告")
        lines.append("=" * 60)
        lines.append("")

        lines.append("--- 适用范围 ---")
        lines.append(result.get("scope_note", ""))
        lines.append("")

        lines.append("--- 输入摘要 ---")
        fastener = payload.get("fastener", {})
        assembly = payload.get("assembly", {})
        service = payload.get("service", {})
        lines.append(f"螺纹规格: M{fastener.get('d', '?')} x {fastener.get('p', '?')}")
        lines.append(f"材料屈服强度: Rp0.2 = {fastener.get('Rp02', '?')} MPa")
        lines.append(f"最小预紧力: {assembly.get('F_preload_min', '?')} N")
        lines.append(f"拧紧散差: alpha_A = {assembly.get('alpha_A', '?')}")
        lines.append(
            f"轴向载荷: FA_min = {service.get('FA_min', '?')} N"
            f" / FA_max = {service.get('FA_max', '?')} N"
        )
        lines.append("")

        lines.append("--- 分项校核结果 ---")
        checks = result.get("checks", {})
        for key, label in CHECK_LABELS.items():
            raw = checks.get(key)
            if raw is None:
                text = "未校核"
            elif raw:
                text = "通过"
            else:
                text = "不通过"
            lines.append(f"  {label}: {text}")
        overall_status = result.get(
            "overall_status",
            "pass" if result.get("overall_pass") else "fail",
        )
        status_text = {
            "pass": "通过",
            "fail": "不通过",
            "incomplete": "校核不完整",
        }.get(overall_status, overall_status)
        lines.append(f"  总体结论: {status_text}")
        lines.append("")

        lines.append("--- 关键数值 ---")
        lines.append(self.metrics_text.text())
        lines.append("")

        lines.append("--- 螺纹脱扣 ---")
        ts = result.get("thread_strip", {})
        lines.append(f"  状态: {'已启用' if ts.get('active') else '未启用'}")
        lines.append(f"  {ts.get('note', '')}")
        lines.append("")

        lines.append("--- trace ---")
        for a in result.get("trace", {}).get("assumptions", []):
            lines.append(f"  {a}")
        lines.append("")

        if result.get("warnings"):
            lines.append("--- 警告 ---")
            for w in result["warnings"]:
                lines.append(f"  {w}")
            lines.append("")
        if result.get("recommendations"):
            lines.append("--- 建议 ---")
            for r in result["recommendations"]:
                lines.append(f"  {r}")
            lines.append("")

        lines.append("--- 标准引用 ---")
        for k, v in result.get("references", {}).items():
            lines.append(f"  {k}: {v}")

        return lines

    def _ensure_export_payload_matches_current_inputs(self) -> bool:
        """Codex §3.4：导出前再比一次当前表单与缓存 payload，确保报告对应当前输入。"""
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "提示", "请先执行计算。")
            return False
        try:
            current = self._build_payload()
        except ValueError as exc:
            QMessageBox.warning(self, "输入格式错误", f"当前表单读取失败：{exc}")
            return False
        if current != self._last_payload:
            QMessageBox.warning(
                self, "输入已变更",
                "当前表单与上次计算时的输入不一致，请先点击\u201c开始计算\u201d"
                "刷新结果，再导出报告。",
            )
            return False
        return True

    def _export_text_report(self) -> None:
        if not self._ensure_export_payload_matches_current_inputs():
            return
        lines = self._build_report_lines()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出文本报告", "tapped_axial_report.txt",
            "Text Files (*.txt)"
        )
        if not path:
            return
        try:
            Path(path).write_text("\n".join(lines), encoding="utf-8")
            self.set_info(f"文本报告已导出: {path}")
        except OSError as exc:
            QMessageBox.critical(self, "导出失败", f"文件写入失败: {exc}")

    def _export_pdf_report(self) -> None:
        if not self._ensure_export_payload_matches_current_inputs():
            return
        try:
            from app.ui.report_pdf_tapped_axial import generate_tapped_axial_report
        except ImportError:
            QMessageBox.warning(
                self, "缺少依赖",
                "PDF 导出需要 reportlab 库。请运行:\npip install reportlab"
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 PDF 报告", "tapped_axial_report.pdf",
            "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            generate_tapped_axial_report(
                Path(path), self._last_payload, self._last_result
            )
            self.set_info(f"PDF 报告已导出: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", f"PDF 生成失败: {exc}")
