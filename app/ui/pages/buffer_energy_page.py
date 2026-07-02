"""Buffer block energy simulation page."""

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
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.fonts import make_ui_font
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
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import ReportExportError
from app.ui.theme import mark_input_field_surface
from app.ui.widgets.buffer_energy_curve import BufferEnergyCurveWidget
from app.ui.widgets.buffer_response_curve import BufferResponseCurveWidget


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)
MODULE_ID = "buffer_energy"

DISCLAIMER_TEXT = (
    "本工具基于准静态 F-x 曲线的单次冲击能量法。回弹速度与时域响应均为反推估算值，"
    "不含应变率效应，不能替代真实时域仿真。"
)


@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    label: str
    unit: str
    hint: str
    mapping: tuple[str, str] | None
    widget_type: str = "number"
    default: str = ""
    placeholder: str = ""


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "impact.mass_kg",
        "冲击质量 m",
        "kg",
        "撞击物或运动部件的等效质量。",
        ("impact", "mass_kg"),
        default="12.0",
        placeholder="例如 12.0",
    ),
    FieldSpec(
        "impact.initial_velocity_m_s",
        "初始速度 v0",
        "m/s",
        "接触缓冲块前的速度。",
        ("impact", "initial_velocity_m_s"),
        default="1.5",
        placeholder="例如 1.5",
    ),
    FieldSpec(
        "impact.available_stroke_mm",
        "可用行程",
        "mm",
        "机构允许缓冲块压缩的最大行程。",
        ("impact", "available_stroke_mm"),
        default="30.0",
        placeholder="例如 30",
    ),
    FieldSpec(
        "impact.allowable_peak_force_n",
        "允许峰值力",
        "N",
        "结构、导轨或安装件允许承受的峰值反力。",
        ("impact", "allowable_peak_force_n"),
        default="9000",
        placeholder="例如 9000",
    ),
    FieldSpec(
        "options.force_scale",
        "曲线力倍率",
        "-",
        "对测试曲线的力值统一缩放，用于选型敏感度。",
        ("options", "force_scale"),
        default="1.00",
    ),
    FieldSpec(
        "options.stroke_scale",
        "曲线行程倍率",
        "-",
        "对测试曲线的位移统一缩放，用于行程敏感度。",
        ("options", "stroke_scale"),
        default="1.00",
    ),
    FieldSpec(
        "options.noise_tolerance_n",
        "卸载噪声容差",
        "N",
        "允许卸载曲线局部略高于加载曲线的噪声阈值。",
        ("options", "noise_tolerance_n"),
        default="5.0",
    ),
    FieldSpec(
        "options.time_samples",
        "时域采样点数",
        "点",
        "能量守恒反推响应曲线的总采样点数。",
        ("options", "time_samples"),
        default="200",
    ),
)


class BufferEnergyPage(BaseChapterPage):
    """Chapter-based UI for single-impact buffer energy simulation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="缓冲块吸能仿真",
            subtitle="导入加载/卸载 F-x 测试曲线，用能量法求解单次冲击吸能、回弹和近似响应时程。",
            parent=parent,
        )
        self._curve_data: dict[str, Any] | None = None
        self._curve_source: Path | None = None
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._field_specs: dict[str, FieldSpec] = {spec.field_id: spec for spec in FIELD_SPECS}
        self._field_widgets: dict[str, QWidget] = {}
        self._field_cards: dict[str, QWidget] = {}

        self._insert_disclaimer()

        self.btn_import_curve = self.add_action_button("导入曲线文件", primary=True)
        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行仿真", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_save_report = self.add_action_button("导出结果说明")
        self.btn_load_1 = self.add_action_button("测试案例 1", side="right")
        self.btn_load_2 = self.add_action_button("测试案例 2", side="right")
        self.btn_save_report.setEnabled(False)
        self.btn_calculate.setEnabled(False)

        self.overview_curve_widget = BufferEnergyCurveWidget()
        self.curve_check_widget = BufferEnergyCurveWidget()
        self.response_widget = BufferResponseCurveWidget()

        self._build_curve_import_chapter()
        self._build_curve_check_chapter()
        self._build_impact_chapter()
        self._build_energy_result_chapter()
        self._build_response_chapter()
        self._build_compare_chapter()
        self._build_export_chapter()
        self.set_current_chapter(0)

        self.btn_import_curve.clicked.connect(self._on_import_curve)
        self.btn_save_inputs.clicked.connect(self._on_save_inputs)
        self.btn_load_inputs.clicked.connect(self._on_load_inputs)
        self.btn_calculate.clicked.connect(self._on_calculate)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_save_report.clicked.connect(self._on_save_report)
        self.btn_load_1.clicked.connect(lambda: self._load_sample("buffer_energy_case_01.csv"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("buffer_energy_case_02.xlsx"))

        self._apply_defaults()
        self._connect_input_signals()

    def _insert_disclaimer(self) -> None:
        banner = QFrame(self)
        banner.setObjectName("WarningCard")
        layout = QVBoxLayout(banner)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        title = QLabel("模型边界提醒", banner)
        title.setObjectName("WarningTitle")
        self.disclaimer_label = QLabel(DISCLAIMER_TEXT, banner)
        self.disclaimer_label.setObjectName("WarningBody")
        self.disclaimer_label.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(self.disclaimer_label)
        root = self.layout()
        root.insertWidget(1, banner)

    def _build_curve_import_chapter(self) -> None:
        page, body = self._chapter_shell("测试曲线导入", "支持 CSV / XLSX；宽表或长表均可，表头允许中英文别名。")
        self.curve_summary_label = QLabel("尚未导入曲线。", page)
        self.curve_summary_label.setObjectName("SectionHint")
        self.curve_summary_label.setWordWrap(True)
        body.addWidget(self.curve_summary_label)
        body.addStretch(1)
        self.add_chapter("测试曲线导入", page)

    def _build_curve_check_chapter(self) -> None:
        page, body = self._chapter_shell("曲线检查与能量", "导入曲线后可快速核对加载/卸载路径；执行仿真后显示能量积分和刚度指标。")
        body.addWidget(self.curve_check_widget, 1)
        self.curve_metrics_label = QLabel("导入曲线后显示能量与刚度指标。", page)
        self.curve_metrics_label.setObjectName("SectionHint")
        self.curve_metrics_label.setWordWrap(True)
        body.addWidget(self.curve_metrics_label)
        self.add_chapter("曲线检查与能量", page)

    def _build_impact_chapter(self) -> None:
        page, body = self._chapter_shell("单次冲击工况", "填写质量、速度、可用行程、允许峰值力和曲线缩放参数。")
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        form = QVBoxLayout(container)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        for spec in FIELD_SPECS:
            form.addWidget(self._build_field_card(spec, container))
        form.addStretch(1)
        scroll.setWidget(container)
        body.addWidget(scroll, 1)
        self.add_chapter("单次冲击工况", page)

    def _build_energy_result_chapter(self) -> None:
        page, body = self._chapter_shell("吸能结果", "方案 A 工作台总览：关键指标、F-x 曲线、总体结论、模型边界和参数对比摘要。")
        scroll = QScrollArea(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget(scroll)
        outer = QGridLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setHorizontalSpacing(10)
        outer.setVerticalSpacing(8)

        status_card = QFrame(container)
        status_card.setObjectName("SubCard")
        status_card.setMinimumWidth(210)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(10, 8, 10, 8)
        status_layout.setSpacing(8)
        status_title = QLabel("当前数据状态", status_card)
        status_title.setObjectName("SubSectionTitle")
        self.workbench_status_label = QLabel("尚未导入曲线。", status_card)
        self.workbench_status_label.setObjectName("SectionHint")
        self.workbench_status_label.setWordWrap(True)
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.workbench_status_label)
        status_layout.addStretch(1)

        center = QWidget(container)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        self.metric_labels: dict[str, QLabel] = {}
        metric_grid = QGridLayout()
        metric_grid.setContentsMargins(0, 0, 0, 0)
        metric_grid.setHorizontalSpacing(8)
        metrics = (
            ("initial_energy", "初始动能", "J"),
            ("max_compression", "最大压缩量", "mm"),
            ("peak_force", "峰值输出力", "N"),
            ("rebound_velocity", "估算回弹速度", "m/s"),
        )
        for index, (key, title, unit) in enumerate(metrics):
            metric_grid.addWidget(self._metric_card(center, key, title, unit), 0, index)
        center_layout.addLayout(metric_grid)

        curve_card = QFrame(center)
        curve_card.setObjectName("SubCard")
        curve_layout = QVBoxLayout(curve_card)
        curve_layout.setContentsMargins(10, 8, 10, 8)
        curve_layout.setSpacing(6)
        curve_title = QLabel("F-x 滞回曲线", curve_card)
        curve_title.setObjectName("SubSectionTitle")
        curve_layout.addWidget(curve_title)
        curve_layout.addWidget(self.overview_curve_widget, 1)
        center_layout.addWidget(curve_card, 1)

        self.energy_strip_label = QLabel("加载能量 -- J · 工况耗散 -- J · 接触时长 -- ms", center)
        self.energy_strip_label.setObjectName("SectionHint")
        self.energy_strip_label.setWordWrap(True)
        center_layout.addWidget(self.energy_strip_label)

        right = QFrame(container)
        right.setObjectName("SubCard")
        right.setMinimumWidth(290)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 8, 10, 8)
        right_layout.setSpacing(8)
        self.overall_verdict_label = QLabel("总体结论: 待计算", right)
        self.overall_verdict_label.setObjectName("SubSectionTitle")
        self.overall_verdict_label.setWordWrap(True)
        right_layout.addWidget(self.overall_verdict_label)
        self.model_boundary_label = QLabel(DISCLAIMER_TEXT, right)
        self.model_boundary_label.setObjectName("SectionHint")
        self.model_boundary_label.setWordWrap(True)
        right_layout.addWidget(self.model_boundary_label)

        self.check_badges: dict[str, QLabel] = {}
        for key, name in (
            ("stroke_ok", "行程"),
            ("peak_force_ok", "峰值力"),
            ("energy_capacity_ok", "曲线能量容量"),
        ):
            badge = QLabel(f"{name}: 待计算", right)
            badge.setObjectName("WaitBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.check_badges[key] = badge
            right_layout.addWidget(badge)

        preview_title = QLabel("参数对比摘要", right)
        preview_title.setObjectName("SubSectionTitle")
        right_layout.addWidget(preview_title)
        self.compare_preview_table = QTableWidget(0, 4, right)
        self.compare_preview_table.setHorizontalHeaderLabels(["方案", "x", "Fpk", "回弹"])
        self.compare_preview_table.setMinimumHeight(124)
        right_layout.addWidget(self.compare_preview_table)

        self.results_label = QPlainTextEdit(right)
        self.results_label.setReadOnly(True)
        self.results_label.setPlainText("执行计算后显示消息与建议。")
        self.results_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.results_label.setMaximumHeight(170)
        right_layout.addWidget(self.results_label)
        right_layout.addStretch(1)

        outer.addWidget(status_card, 0, 0)
        outer.addWidget(center, 0, 1)
        outer.addWidget(right, 0, 2)
        outer.setColumnStretch(0, 0)
        outer.setColumnStretch(1, 1)
        outer.setColumnStretch(2, 0)
        scroll.setWidget(container)
        body.addWidget(scroll, 1)
        self.add_chapter("吸能结果", page)

    def _build_response_chapter(self) -> None:
        page, body = self._chapter_shell("响应时程", "由能量守恒反推近似 x(t) / v(t) / a(t) / F(t)，不含应变率效应。")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(QLabel("显示变量:", page))
        self.response_var_combo = QComboBox(page)
        self.response_var_combo.addItem("位移 x(t)", "x")
        self.response_var_combo.addItem("速度 v(t)", "v")
        self.response_var_combo.addItem("加速度 a(t)", "a")
        self.response_var_combo.addItem("反力 F(t)", "F")
        row.addWidget(self.response_var_combo)
        row.addStretch(1)
        body.addLayout(row)
        body.addWidget(self.response_widget, 1)
        self.response_var_combo.currentIndexChanged.connect(
            lambda _idx: self.response_widget.set_variable(self.response_var_combo.currentData() or "x")
        )
        self.add_chapter("响应时程", page)

    def _build_compare_chapter(self) -> None:
        page, body = self._chapter_shell("参数对比", "默认扫描 0.8 / 1.0 / 1.2 的力倍率和行程倍率，帮助判断选型裕量。")
        self.compare_table = QTableWidget(0, 9, page)
        self.compare_table.setHorizontalHeaderLabels(
            [
                "force_scale",
                "stroke_scale",
                "max_compression_mm",
                "peak_force_n",
                "bottom_out",
                "energy_capacity_ok",
                "stroke_ok",
                "peak_force_ok",
                "duration_s",
            ]
        )
        body.addWidget(self.compare_table, 1)
        self.add_chapter("参数对比", page)

    def _build_export_chapter(self) -> None:
        page, body = self._chapter_shell("结果说明 / 导出", "报告文本包含输入条件、曲线指标、冲击结果、校核结论和模型边界说明。")
        self.report_preview = QPlainTextEdit(page)
        self.report_preview.setReadOnly(True)
        self.report_preview.setPlainText("执行计算后显示报告内容预览。")
        body.addWidget(self.report_preview, 1)
        self.add_chapter("结果说明 / 导出", page)

    def _chapter_shell(self, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title_label = QLabel(title, page)
        title_label.setObjectName("SectionTitle")
        subtitle_label = QLabel(subtitle, page)
        subtitle_label.setObjectName("SectionHint")
        subtitle_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return page, layout

    def _build_field_card(self, spec: FieldSpec, parent: QWidget) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        mark_input_field_surface(card)
        grid = QGridLayout(card)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        label = QLabel(spec.label, card)
        label.setObjectName("SubSectionTitle")
        editor = QLineEdit(card)
        editor.setObjectName("InputField")
        editor.setFont(make_ui_font(12))
        editor.setPlaceholderText(spec.placeholder or "请输入数值")
        unit = QLabel(spec.unit, card)
        unit.setObjectName("UnitLabel")
        hint = QLabel(spec.hint, card)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        grid.addWidget(label, 0, 0)
        grid.addWidget(editor, 0, 1)
        grid.addWidget(unit, 0, 2)
        grid.addWidget(hint, 1, 0, 1, 3)
        self._field_widgets[spec.field_id] = editor
        self._field_cards[spec.field_id] = card
        return card

    def _metric_card(self, parent: QWidget, key: str, title: str, unit: str) -> QWidget:
        card = QFrame(parent)
        card.setObjectName("SubCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        name = QLabel(title, card)
        name.setObjectName("SectionHint")
        value = QLabel(f"-- {unit}", card)
        value.setObjectName("SubSectionTitle")
        value.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(value)
        self.metric_labels[key] = value
        return card

    def _apply_defaults(self) -> None:
        for spec in FIELD_SPECS:
            widget = self._field_widgets.get(spec.field_id)
            if isinstance(widget, QLineEdit):
                widget.setText(spec.default)

    def _connect_input_signals(self) -> None:
        for widget in self._field_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _text: self._invalidate_result())

    def _invalidate_result(self) -> None:
        self._last_payload = None
        self._last_result = None
        if hasattr(self, "metric_labels"):
            self._reset_result_outputs("执行计算后显示消息与建议。")
            self._set_workbench_status_from_curve()
            self._set_curve_widgets_from_raw()
        self.btn_save_report.setEnabled(False)
        self.btn_calculate.setEnabled(self._curve_data is not None)

    def _read_value(self, spec: FieldSpec) -> str:
        widget = self._field_widgets[spec.field_id]
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        return ""

    def _read_field_float(self, field_id: str, default: float) -> float:
        widget = self._field_widgets.get(field_id)
        if not isinstance(widget, QLineEdit):
            return default
        try:
            return float(widget.text().strip())
        except ValueError:
            return default

    def _load_buffer_curve(self, path: Path) -> dict[str, Any]:
        from core.buffer.curve_import import load_buffer_curve

        return load_buffer_curve(path)

    def _calculate_buffer_energy(self, payload: dict[str, Any]) -> dict[str, Any]:
        from core.buffer.calculator import calculate_buffer_energy

        return calculate_buffer_energy(payload)

    def _on_import_curve(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "选择缓冲块测试曲线文件",
            str(EXAMPLES_DIR),
            "曲线数据 (*.csv *.xlsx);;All Files (*)",
        )
        if path_str:
            self._open_curve_path(Path(path_str))

    def _load_sample(self, filename: str) -> None:
        self._open_curve_path(EXAMPLES_DIR / filename)

    def _open_curve_path(self, path: Path) -> None:
        try:
            data = self._load_buffer_curve(path)
        except Exception as exc:  # noqa: BLE001 - UI boundary converts import/parse errors to message box.
            QMessageBox.warning(self, "曲线导入失败", str(exc))
            self._curve_data = None
            self._curve_source = None
            self.btn_calculate.setEnabled(False)
            self.curve_summary_label.setText("尚未导入曲线。")
            self._clear_curve_widgets()
            self._invalidate_result()
            return

        self._curve_data = data
        self._curve_source = path
        self.btn_calculate.setEnabled(True)
        loading = data.get("loading", [])
        unloading = data.get("unloading", [])
        meta = data.get("metadata", {})
        max_stroke = max((float(p.get("x_mm", 0.0)) for p in loading), default=0.0)
        max_force = max((float(p.get("force_n", 0.0)) for p in loading), default=0.0)
        warning_count = len(meta.get("warnings", []) or data.get("warnings", []) or [])
        self.curve_summary_label.setText(
            f"已导入 {path.name} · 格式 {meta.get('format', '?')} · "
            f"加载 {len(loading)} 点 / 卸载 {len(unloading)} 点 · "
            f"最大行程 {max_stroke:.2f} mm · 最大加载力 {max_force:.0f} N · "
            f"warning {warning_count} 条"
        )
        self.curve_metrics_label.setText("曲线已加载；执行仿真后显示积分能量、滞回能量和刚度指标。")
        self._set_curve_widgets_from_raw()
        self._invalidate_result()

    def _set_curve_widgets_from_raw(self) -> None:
        if not self._curve_data:
            self._clear_curve_widgets()
            return
        loading = self._points_from_curve(self._curve_data.get("loading", []))
        unloading = self._points_from_curve(self._curve_data.get("unloading", []))
        for widget in (self.curve_check_widget, self.overview_curve_widget):
            widget.set_curves(
                loading=loading,
                unloading=unloading,
                x_max_mm=0.0,
                available_stroke_mm=self._read_field_float("impact.available_stroke_mm", 0.0),
                allowable_peak_n=self._read_field_float("impact.allowable_peak_force_n", 0.0),
                bottom_out=False,
            )

    def _clear_curve_widgets(self) -> None:
        for widget in (self.curve_check_widget, self.overview_curve_widget):
            widget.set_curves(
                loading=[],
                unloading=[],
                x_max_mm=0.0,
                available_stroke_mm=0.0,
                allowable_peak_n=0.0,
                bottom_out=False,
            )

    def _set_workbench_status_from_curve(self) -> None:
        if not self._curve_data:
            self.workbench_status_label.setText("尚未导入曲线。")
            return
        loading = self._curve_data.get("loading", [])
        unloading = self._curve_data.get("unloading", [])
        meta = self._curve_data.get("metadata", {})
        max_stroke = max((float(p.get("x_mm", 0.0)) for p in loading), default=0.0)
        warning_count = len(meta.get("warnings", []) or self._curve_data.get("warnings", []) or [])
        self.workbench_status_label.setText(
            f"曲线文件: {self._curve_source.name if self._curve_source else '(未记录)'}\n"
            f"格式: {meta.get('format', '?')}\n"
            f"加载/卸载点数: {len(loading)} / {len(unloading)}\n"
            f"最大行程: {max_stroke:.2f} mm\n"
            f"warning: {warning_count} 条\n"
            "状态: 待仿真"
        )

    @staticmethod
    def _points_from_curve(points: list[dict[str, Any]]) -> list[tuple[float, float]]:
        return [(float(p.get("x_mm", 0.0)), float(p.get("force_n", 0.0))) for p in points]

    def _build_payload(self) -> dict[str, Any]:
        if self._curve_data is None:
            raise ValueError("请先导入曲线文件或加载测试案例。")
        payload: dict[str, Any] = {
            "curve": {
                "loading": list(self._curve_data.get("loading", [])),
                "unloading": list(self._curve_data.get("unloading", [])),
            },
            "impact": {},
            "options": {},
        }
        for spec in FIELD_SPECS:
            if spec.mapping is None:
                continue
            raw = self._read_value(spec)
            if raw == "":
                raise ValueError(f"{spec.label} 不能为空。")
            try:
                value: Any = int(raw) if spec.field_id == "options.time_samples" else float(raw)
            except ValueError as exc:
                raise ValueError(f"{spec.label} 不是数字: {raw!r}") from exc
            section, key = spec.mapping
            payload[section][key] = value
        return payload

    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = self._calculate_buffer_energy(payload)
            self._last_payload = payload
            self._last_result = result
            self._render_result(result)
            self._populate_parameter_compare(payload)
        except Exception as exc:  # noqa: BLE001 - keep the Qt slot from crashing.
            self._last_payload = None
            self._last_result = None
            self._reset_result_outputs("计算未完成，已清除本次部分结果。")
            self._set_workbench_status_from_curve()
            self._set_curve_widgets_from_raw()
            QMessageBox.warning(self, "输入或计算错误", str(exc))
            self.btn_save_report.setEnabled(False)
            return
        self.btn_save_report.setEnabled(True)

    def _render_result(self, result: dict[str, Any]) -> None:
        impact = result["impact"]
        summary = result["curve_summary"]
        response = result.get("time_response") or {}
        duration_ms = float(response.get("duration_s", 0.0)) * 1000.0
        peak_text = "触底，未知" if impact.get("peak_force_n") is None else f"{impact['peak_force_n']:.1f} N"

        self.metric_labels["initial_energy"].setText(f"{impact['initial_energy_j']:.2f} J")
        self.metric_labels["max_compression"].setText(f"{impact['max_compression_mm']:.2f} mm")
        self.metric_labels["peak_force"].setText(peak_text)
        self.metric_labels["rebound_velocity"].setText(f"{impact['estimated_rebound_velocity_m_s']:.3f} m/s")
        self.energy_strip_label.setText(
            f"加载能量 {summary['loading_energy_j']:.3f} J · "
            f"工况耗散 {impact['impact_dissipated_energy_j']:.3f} J · "
            f"接触时长 {duration_ms:.2f} ms"
        )

        if impact.get("bottom_out"):
            verdict = "总体结论: 触底 / 峰值未知"
            status = "fail"
        elif result.get("overall_pass"):
            verdict = "总体结论: 通过"
            status = "pass"
        else:
            verdict = "总体结论: 不通过"
            status = "fail"
        self.overall_verdict_label.setText(verdict)
        self.set_overall_status(verdict.replace("总体结论: ", ""), status)

        boundary = [DISCLAIMER_TEXT]
        if impact.get("bottom_out"):
            boundary.append("触底后真实冲击峰值未知，当前曲线不能外推触底刚化峰值。")
        boundary.extend(result.get("warnings", []))
        self.model_boundary_label.setText("\n".join(boundary))

        lines = self._result_lines(result)
        self.results_label.setPlainText("\n".join(lines))
        self.curve_metrics_label.setText(
            f"加载能量 {summary['loading_energy_j']:.3f} J · "
            f"卸载能量 {summary['unloading_energy_j']:.3f} J · "
            f"滞回 {summary['curve_hysteresis_energy_j']:.3f} J · "
            f"吸能比例 {summary['energy_absorption_ratio'] * 100.0:.1f}% · "
            f"等效刚度 {summary['equivalent_stiffness_n_per_mm']:.1f} N/mm"
        )

        for widget in (self.curve_check_widget, self.overview_curve_widget):
            widget.set_curves(
                loading=list(zip(result["curves"]["loading_x_mm"], result["curves"]["loading_force_n"])),
                unloading=list(zip(result["curves"]["unloading_x_mm"], result["curves"]["unloading_force_n"])),
                x_max_mm=float(impact["max_compression_mm"]),
                available_stroke_mm=self._read_field_float("impact.available_stroke_mm", 0.0),
                allowable_peak_n=self._read_field_float("impact.allowable_peak_force_n", 0.0),
                bottom_out=bool(impact.get("bottom_out")),
            )

        self.response_widget.set_response(result.get("time_response"))
        self.response_widget.set_variable(self.response_var_combo.currentData() or "x")
        self._set_check_badge("stroke_ok", "行程", result["checks"]["stroke_ok"])
        self._set_check_badge("peak_force_ok", "峰值力", result["checks"]["peak_force_ok"])
        self._set_check_badge("energy_capacity_ok", "曲线能量容量", result["checks"]["energy_capacity_ok"])
        self._update_workbench_status(result)
        self.report_preview.setPlainText("\n".join(self._build_report_lines()))

    def _result_lines(self, result: dict[str, Any]) -> list[str]:
        impact = result["impact"]
        summary = result["curve_summary"]
        response = result.get("time_response") or {}
        peak_text = "触底，未知" if impact.get("peak_force_n") is None else f"{impact['peak_force_n']:.1f} N"
        lines = [
            f"最大压缩 = {impact['max_compression_mm']:.3f} mm",
            f"峰值输出力 = {peak_text}",
            f"平均反力 = {impact['average_force_n']:.1f} N",
            f"吸收能量 = {impact['absorbed_energy_j']:.3f} J",
            f"工况耗散能量 = {impact['impact_dissipated_energy_j']:.3f} J",
            f"回弹能量 = {impact['rebound_energy_j']:.3f} J",
            f"估算回弹速度 = {impact['estimated_rebound_velocity_m_s']:.3f} m/s",
            f"接触时长 = {float(response.get('duration_s', 0.0)) * 1000.0:.2f} ms",
            "",
            f"测试曲线最大行程 = {summary['max_stroke_mm']:.2f} mm",
            f"测试曲线峰值力 = {summary['peak_loading_force_n']:.1f} N",
            f"测试曲线滞回能量 = {summary['curve_hysteresis_energy_j']:.3f} J",
        ]
        warnings = result.get("warnings", [])
        if warnings:
            lines.extend(["", "提示与建议:"])
            lines.extend(f"- {item}" for item in warnings)
        return lines

    def _set_check_badge(self, key: str, name: str, value: Any) -> None:
        badge = self.check_badges[key]
        if value is True:
            text, obj = f"{name}: 通过", "PassBadge"
        elif value is False:
            text, obj = f"{name}: 不通过", "FailBadge"
        else:
            text, obj = f"{name}: 不可判定", "WaitBadge"
        badge.setText(text)
        badge.setObjectName(obj)
        badge.style().unpolish(badge)
        badge.style().polish(badge)

    def _populate_parameter_compare(self, base_payload: dict[str, Any]) -> None:
        rows: list[list[str]] = []
        for force_scale in (0.8, 1.0, 1.2):
            for stroke_scale in (0.8, 1.0, 1.2):
                payload = json.loads(json.dumps(base_payload))
                payload.setdefault("options", {})["force_scale"] = force_scale
                payload.setdefault("options", {})["stroke_scale"] = stroke_scale
                try:
                    result = self._calculate_buffer_energy(payload)
                    impact = result["impact"]
                    checks = result["checks"]
                    response = result.get("time_response") or {}
                    peak = "触底" if impact.get("peak_force_n") is None else f"{impact['peak_force_n']:.0f}"
                    rows.append(
                        [
                            f"{force_scale:.2f}",
                            f"{stroke_scale:.2f}",
                            f"{impact['max_compression_mm']:.2f}",
                            peak,
                            "是" if impact.get("bottom_out") else "否",
                            self._fmt_check(checks["energy_capacity_ok"]),
                            self._fmt_check(checks["stroke_ok"]),
                            self._fmt_check(checks["peak_force_ok"]),
                            f"{float(response.get('duration_s', 0.0)) * 1000.0:.2f} ms",
                        ]
                    )
                except Exception as exc:  # noqa: BLE001 - compare table should tolerate invalid scan rows.
                    rows.append([f"{force_scale:.2f}", f"{stroke_scale:.2f}", f"错误: {exc}", "", "", "", "", "", ""])
        self.compare_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, text in enumerate(row):
                self.compare_table.setItem(row_index, col_index, QTableWidgetItem(text))
        self.compare_table.resizeColumnsToContents()

        preview_specs = (
            ("0.80", "1.00", "0.8F"),
            ("1.00", "1.00", "1.0F"),
            ("1.20", "1.00", "1.2F"),
            ("1.00", "1.20", "1.2S"),
        )
        preview_rows: list[list[str]] = []
        for force_text, stroke_text, label in preview_specs:
            match = next((row for row in rows if row[0] == force_text and row[1] == stroke_text), None)
            if match:
                preview_rows.append([label, match[2], match[3], match[8]])
        self.compare_preview_table.setRowCount(len(preview_rows))
        for row_index, row in enumerate(preview_rows):
            for col_index, text in enumerate(row):
                self.compare_preview_table.setItem(row_index, col_index, QTableWidgetItem(text))
        self.compare_preview_table.resizeColumnsToContents()

    def _on_clear(self) -> None:
        self._curve_data = None
        self._curve_source = None
        self._last_payload = None
        self._last_result = None
        self._apply_defaults()
        self.curve_summary_label.setText("尚未导入曲线。")
        self.curve_metrics_label.setText("导入曲线后显示能量与刚度指标。")
        self.workbench_status_label.setText("尚未导入曲线。")
        self._reset_result_outputs("执行计算后显示消息与建议。")
        self._clear_curve_widgets()
        self.set_info("参数已清空，导出结果已失效。")
        self.btn_save_report.setEnabled(False)
        self.btn_calculate.setEnabled(False)

    def _reset_result_outputs(self, message: str) -> None:
        for label in self.metric_labels.values():
            label.setText("--")
        self.energy_strip_label.setText("加载能量 -- J · 工况耗散 -- J · 接触时长 -- ms")
        self.overall_verdict_label.setText("总体结论: 待计算")
        self.model_boundary_label.setText(DISCLAIMER_TEXT)
        self.results_label.setPlainText(message)
        self.report_preview.setPlainText("执行计算后显示报告内容预览。")
        for key, name in (
            ("stroke_ok", "行程"),
            ("peak_force_ok", "峰值力"),
            ("energy_capacity_ok", "曲线能量容量"),
        ):
            badge = self.check_badges[key]
            badge.setText(f"{name}: 待计算")
            badge.setObjectName("WaitBadge")
            badge.style().unpolish(badge)
            badge.style().polish(badge)
        self.response_widget.set_response(None)
        self.compare_table.setRowCount(0)
        self.compare_preview_table.setRowCount(0)
        self.set_overall_status("等待计算", "wait")

    def _update_workbench_status(self, result: dict[str, Any]) -> None:
        if not self._curve_data:
            self.workbench_status_label.setText("尚未导入曲线。")
            return
        meta = self._curve_data.get("metadata", {})
        loading = self._curve_data.get("loading", [])
        unloading = self._curve_data.get("unloading", [])
        warnings_count = len(result.get("warnings", []))
        if result["impact"].get("bottom_out"):
            status = "触底 / 不通过"
        elif result.get("overall_pass"):
            status = "通过"
        else:
            status = "不通过"
        self.workbench_status_label.setText(
            f"曲线文件: {self._curve_source.name if self._curve_source else '(未记录)'}\n"
            f"格式: {meta.get('format', '?')}\n"
            f"加载/卸载点数: {len(loading)} / {len(unloading)}\n"
            f"warning: {warnings_count} 条\n"
            f"最大压缩: {result['impact']['max_compression_mm']:.2f} mm\n"
            f"状态: {status}"
        )

    def _on_save_report(self) -> None:
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行仿真，再导出结果说明。")
            return
        default_path = EXAMPLES_DIR / "buffer_energy_report.pdf"
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
                    from app.ui.report_pdf_buffer import generate_buffer_report

                    generate_buffer_report(out_path, self._last_payload, self._last_result)
                except Exception:
                    from app.ui.report_export import _export_pdf

                    _export_pdf(out_path, self._build_report_lines())
                    self.set_info(f"结果说明已导出: {out_path}（已使用简化格式）")
                    return
            elif suffix == ".docx":
                from app.ui.report_export import _export_docx

                _export_docx(out_path, self._build_report_lines())
            else:
                out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
        except (ReportExportError, OSError) as exc:
            QMessageBox.critical(self, "导出失败", f"导出失败：{exc}")
            return
        self.set_info(f"结果说明已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        if self._last_result is None:
            return ["缓冲块吸能仿真报告", "", "尚未执行仿真。"]
        result = self._last_result
        impact = result["impact"]
        summary = result["curve_summary"]
        response = result.get("time_response") or {}
        peak_text = "触底，不可判定" if impact.get("peak_force_n") is None else f"{impact['peak_force_n']:.2f} N"
        lines = [
            "缓冲块吸能仿真报告",
            "=" * 28,
            "",
            "1. 输入条件",
            f"- 曲线文件: {self._curve_source.name if self._curve_source else '(未记录)'}",
            f"- 质量: {self._read_field_float('impact.mass_kg', 0.0):.3f} kg",
            f"- 初始速度: {self._read_field_float('impact.initial_velocity_m_s', 0.0):.3f} m/s",
            f"- 可用行程: {self._read_field_float('impact.available_stroke_mm', 0.0):.2f} mm",
            f"- 允许峰值力: {self._read_field_float('impact.allowable_peak_force_n', 0.0):.0f} N",
            "",
            "2. 曲线指标",
            f"- 最大测试行程: {summary['max_stroke_mm']:.2f} mm",
            f"- 最大加载力: {summary['peak_loading_force_n']:.1f} N",
            f"- 加载能量: {summary['loading_energy_j']:.3f} J",
            f"- 卸载能量: {summary['unloading_energy_j']:.3f} J",
            f"- 滞回能量: {summary['curve_hysteresis_energy_j']:.3f} J",
            f"- 吸能比例: {summary['energy_absorption_ratio'] * 100.0:.1f} %",
            "",
            "3. 单次冲击结果",
            f"- 初始动能: {impact['initial_energy_j']:.3f} J",
            f"- 最大压缩量: {impact['max_compression_mm']:.3f} mm",
            f"- 峰值输出力: {peak_text}",
            f"- 平均反力: {impact['average_force_n']:.1f} N",
            f"- 吸收能量: {impact['absorbed_energy_j']:.3f} J",
            f"- 工况耗散能量: {impact['impact_dissipated_energy_j']:.3f} J",
            f"- 回弹能量: {impact['rebound_energy_j']:.3f} J",
            f"- 估算回弹速度: {impact['estimated_rebound_velocity_m_s']:.3f} m/s",
            f"- 接触时长: {float(response.get('duration_s', 0.0)) * 1000.0:.2f} ms",
            f"- 是否触底: {'是' if impact.get('bottom_out') else '否'}",
            "",
            "4. 校核结论",
            f"- 行程: {self._fmt_check(result['checks']['stroke_ok'])}",
            f"- 峰值力: {self._fmt_check(result['checks']['peak_force_ok'])}",
            f"- 曲线能量容量: {self._fmt_check(result['checks']['energy_capacity_ok'])}",
            f"- 整体: {'通过' if result.get('overall_pass') else '不通过'}",
            "",
            "5. 模型边界与免责",
        ]
        for note in result.get("assumptions", []):
            lines.append(f"- {note}")
        lines.extend(
            [
                "- 本工具基于加载 / 卸载 F-x 曲线的单次冲击能量法。",
                "- 回弹速度为基于卸载曲线能量的估算值。",
                "- 时域响应曲线为由能量守恒反推的近似映射，不含应变率效应，不能替代真实时域动力学仿真。",
                "- 假设水平冲击或重力做功相对动能可忽略；垂直跌落工况需把 m*g*x_max 加入 E0，本版本暂不自动处理。",
                "- 卸载段简化假设：测试卸载曲线形状只与位移有关；浅压缩下真实卸载支路可能不同。",
            ]
        )
        warnings = result.get("warnings", [])
        if warnings:
            lines.extend(["", "6. 提示"])
            lines.extend(f"- {item}" for item in warnings)
        return lines

    @staticmethod
    def _fmt_check(value: Any) -> str:
        if value is True:
            return "通过"
        if value is False:
            return "不通过"
        return "不可判定"

    def _on_save_inputs(self) -> None:
        default_path = SAVED_INPUTS_DIR / "buffer_energy_input_conditions.json"
        out_path = choose_save_input_conditions_path(self, "保存输入条件", default_path)
        if out_path is None:
            return
        try:
            self._write_input_conditions(out_path)
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", str(exc))
            return
        self.set_info(f"输入条件已保存：{out_path}")

    def _on_load_inputs(self) -> None:
        in_path = choose_load_input_conditions_path(self, "加载输入条件", SAVED_INPUTS_DIR)
        if in_path is None:
            return
        try:
            loaded = self._read_input_conditions(in_path)
        except InputConditionError as exc:
            QMessageBox.critical(self, "文件格式错误", str(exc))
            return
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "加载失败", str(exc))
            return
        if not loaded:
            return
        self.set_info(f"已加载输入条件：{in_path}")

    def _write_input_conditions(self, path: Path) -> None:
        snapshot = build_form_snapshot(
            self._field_specs.values(),
            self._read_value,
            extra_state={
                "curve_source": str(self._curve_source) if self._curve_source else "",
            },
            module_id=MODULE_ID,
        )
        snapshot["version"] = 1
        write_input_conditions(path, snapshot)

    def _read_input_conditions(self, path: Path) -> bool:
        data = validate_snapshot(read_input_conditions(path))
        if not confirm_snapshot_module(self, data, MODULE_ID):
            return False
        self._apply_input_data(data)
        self._invalidate_result()
        return True

    def _apply_input_data(self, data: dict[str, Any]) -> None:
        inputs = data.get("inputs") if isinstance(data.get("inputs"), dict) else {}
        ui_state = data.get("ui_state") if isinstance(data.get("ui_state"), dict) else {}

        for spec in FIELD_SPECS:
            value: Any | None = None
            if spec.field_id in ui_state:
                value = ui_state[spec.field_id]
            elif spec.mapping is not None:
                section, key = spec.mapping
                section_values = inputs.get(section)
                if isinstance(section_values, dict) and key in section_values:
                    value = section_values[key]
            if value is None:
                continue
            widget = self._field_widgets.get(spec.field_id)
            if isinstance(widget, QLineEdit):
                old = widget.blockSignals(True)
                widget.setText(str(value))
                widget.blockSignals(old)

        curve_source = str(ui_state.get("curve_source", "") or "")
        if curve_source:
            path = Path(curve_source)
            if path.exists():
                self._open_curve_path(path)
