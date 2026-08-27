"""Fatigue S-N/Woehler fitting, spectrum damage, and reliability page."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.input_condition_store import (
    build_saved_inputs_dir,
    choose_load_input_conditions_path,
    choose_save_input_conditions_path,
    confirm_snapshot_module,
    read_input_conditions,
    validate_snapshot,
    write_input_conditions,
)
from app.ui.model_scope import FATIGUE_SCOPE, make_scope_banner, scope_report_lines
from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.report_export import ReportExportError, _export_docx, write_text_report
from app.ui.report_trace import build_report_trace, trace_report_lines
from app.ui.result_contract import FATIGUE_CHECK_LABELS, from_fatigue, status_label_zh
from app.ui.status_badge import badge_object_name
from app.ui.theme import mark_input_field_surface
from app.ui.widgets.fatigue_charts import (
    FatigueDamageChart,
    FatigueReliabilityChart,
    FatigueSnChart,
)
from core.fatigue.calculator import InputError, calculate_fatigue_reliability
from core.fatigue.importers import (
    ImportError as FatigueImportError,
    list_xlsx_sheets,
    load_sn_test_data,
    load_spectrum_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SAVED_INPUTS_DIR = build_saved_inputs_dir(PROJECT_ROOT)
MODULE_ID = "fatigue_reliability"

MATERIAL_TYPES = {
    "金属": "metal",
    "工程塑料": "plastic",
    "短纤增强塑料": "short_fiber_plastic",
}
MEAN_STRESS_MODELS = {"不修正（要求 R 比一致）": "none", "Goodman（金属）": "goodman"}
SPECTRUM_KINDS = {"已计数块谱": "blocks", "单通道时序（rainflow）": "time_series"}
VALUE_KINDS = {"应力 [MPa]": "stress", "载荷/扭矩（需传递）": "load"}
TRANSFER_MODES = {"直接应力": "direct_stress", "线性 σ=kL+b": "linear", "载荷-应力查表": "lookup"}


class FatigueReliabilityPage(BaseChapterPage):
    """Seven-step engineering pre-check workflow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="疲劳强度与可靠性",
            subtitle="由 S-N/Wöhler 试验数据、载荷谱与热点应力换算计算 Miner 损伤、概率寿命和可靠度。",
            parent=parent,
        )
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._sn_source: dict[str, Any] = {}
        self._spectrum_source: dict[str, Any] = {}
        self._suspend_dirty = False
        self._field_labels: dict[QWidget, QLabel] = {}

        self.btn_import_sn = self.add_action_button("导入 S-N 数据", primary=True)
        self.btn_import_spectrum = self.add_action_button("导入载荷谱")
        self.btn_save_inputs = self.add_action_button("保存输入条件")
        self.btn_load_inputs = self.add_action_button("加载输入条件")
        self.btn_calculate = self.add_action_button("执行预校核", primary=True)
        self.btn_clear = self.add_action_button("清空参数")
        self.btn_export = self.add_action_button("导出结果说明")
        self.btn_sample = self.add_action_button("测试案例 1", side="right")
        self.add_guide_button("modules/fatigue/beginner_guide", button_text="预校核指南")
        self.btn_export.setEnabled(False)

        self._build_scope_chapter()
        self._build_condition_chapter()
        self._build_test_data_chapter()
        self._build_fit_chapter()
        self._build_spectrum_chapter()
        self._build_reliability_chapter()
        self._build_results_chapter()
        self.set_current_chapter(0)

        self.btn_import_sn.clicked.connect(self._on_import_sn)
        self.btn_import_spectrum.clicked.connect(self._on_import_spectrum)
        self.btn_save_inputs.clicked.connect(self._on_save_inputs)
        self.btn_load_inputs.clicked.connect(self._on_load_inputs)
        self.btn_calculate.clicked.connect(self._on_calculate)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_export.clicked.connect(self._on_export)
        self.btn_sample.clicked.connect(self._load_sample)
        self._connect_dirty_tracking()
        self.material_type_combo.currentTextChanged.connect(
            self._sync_material_controls
        )
        self.mean_stress_combo.currentTextChanged.connect(
            self._sync_material_controls
        )
        self.transfer_mode_combo.currentTextChanged.connect(
            self._sync_transfer_controls
        )
        self.value_kind_combo.currentTextChanged.connect(
            self._sync_transfer_controls
        )
        self._sync_material_controls()
        self._sync_transfer_controls()
        self._load_sample()

    # ------------------------------------------------------------------
    # Chapter builders
    # ------------------------------------------------------------------

    def _page(self, title: str, hint: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(self)
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        card = QFrame(page)
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        title_label = QLabel(title, card)
        title_label.setObjectName("SectionTitle")
        hint_label = QLabel(hint, card)
        hint_label.setObjectName("SectionHint")
        hint_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        root.addWidget(card, 1)
        return page, layout

    @staticmethod
    def _label(text: str, parent: QWidget) -> QLabel:
        label = QLabel(text, parent)
        label.setObjectName("FieldLabel")
        label.setWordWrap(True)
        return label

    def _line(self, default: str, parent: QWidget, placeholder: str = "") -> QLineEdit:
        widget = QLineEdit(default, parent)
        widget.setObjectName("InputField")
        widget.setPlaceholderText(placeholder)
        return widget

    def _combo(self, options: list[str], parent: QWidget) -> QComboBox:
        widget = QComboBox(parent)
        widget.addItems(options)
        return widget

    def _form_card(
        self,
        parent: QWidget,
        rows: list[tuple[str, QWidget]],
        *,
        columns: int = 2,
    ) -> QFrame:
        frame = QFrame(parent)
        frame.setObjectName("SubCard")
        mark_input_field_surface(frame)
        grid = QGridLayout(frame)
        grid.setContentsMargins(4, 2, 4, 2)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        for index, (label, widget) in enumerate(rows):
            row = index // columns
            slot = index % columns
            label_column = slot * 2
            editor_column = label_column + 1
            label_widget = self._label(label, frame)
            label_widget.setObjectName("SubSectionTitle")
            self._field_labels[widget] = label_widget
            grid.addWidget(label_widget, row, label_column)
            grid.addWidget(widget, row, editor_column)
            grid.setColumnStretch(editor_column, 1)
        return frame

    def _build_scope_chapter(self) -> None:
        page, body = self._page(
            "分析范围",
            "选择材料路径并记录对象。连续纤维层合板、多轴疲劳和应变寿命不在首版范围。",
        )
        self.scope_banner = make_scope_banner(page, FATIGUE_SCOPE)
        body.addWidget(self.scope_banner)
        self.material_type_combo = self._combo(list(MATERIAL_TYPES), page)
        self.material_name_edit = self._line("42CrMo", page, "材料牌号或零件数据集名称")
        self.batch_edit = self._line("BATCH-01", page)
        self.object_type_combo = self._combo(["材料试样", "零件/总成热点"], page)
        body.addWidget(
            self._form_card(
                page,
                [
                    ("材料类型", self.material_type_combo),
                    ("材料/数据集名称", self.material_name_edit),
                    ("批次", self.batch_edit),
                    ("试验对象", self.object_type_combo),
                ],
            )
        )
        body.addStretch(1)
        self.add_chapter("分析范围", page, help_ref="modules/fatigue/_section_scope")

    def _build_condition_chapter(self) -> None:
        page, body = self._page(
            "试验条件",
            "S-N 数据只能在可比条件下合并；塑料必须记录温湿度、频率、方向和调湿状态。",
        )
        self.temperature_edit = self._line("23", page)
        self.humidity_edit = self._line("50", page)
        self.frequency_edit = self._line("5", page)
        self.r_ratio_edit = self._line("-1", page)
        self.waveform_edit = self._line("sinusoidal", page)
        self.orientation_edit = self._line("flow", page)
        self.conditioning_edit = self._line("dry", page)
        self.process_edit = self._line("quenched_tempered", page)
        self.surface_edit = self._line("machined", page)
        self.mean_stress_combo = self._combo(list(MEAN_STRESS_MODELS), page)
        self.ultimate_edit = self._line("900", page, "Goodman 启用时必填")
        body.addWidget(
            self._form_card(
                page,
                [
                    ("试验温度 [°C]", self.temperature_edit),
                    ("相对湿度 [%RH]", self.humidity_edit),
                    ("频率 [Hz]", self.frequency_edit),
                    ("应力比 R", self.r_ratio_edit),
                    ("波形", self.waveform_edit),
                    ("成型/取样方向", self.orientation_edit),
                    ("调湿状态", self.conditioning_edit),
                    ("热处理/成型条件", self.process_edit),
                    ("表面状态", self.surface_edit),
                    ("平均应力模型", self.mean_stress_combo),
                    ("抗拉强度 Rm [MPa]", self.ultimate_edit),
                ],
            )
        )
        body.addStretch(1)
        self.add_chapter("试验条件", page, help_ref="modules/fatigue/_section_conditions")

    def _build_test_data_chapter(self) -> None:
        page, body = self._page(
            "S-N 试验数据导入与质量检查",
            "支持断裂与 runout。runout 是右删失数据，不能按普通断裂点处理。表格可直接编辑。",
        )
        self.sn_source_label = QLabel("尚未导入文件；当前可使用表内数据。", page)
        self.sn_source_label.setObjectName("SectionHint")
        self.sn_source_label.setWordWrap(True)
        body.addWidget(self.sn_source_label)
        self.sn_table = QTableWidget(0, 8, page)
        self.sn_table.setObjectName("EngineeringTable")
        self.sn_table.setHorizontalHeaderLabels(
            ["试样", "载荷级", "条件组", "应力幅 [MPa]", "平均应力 [MPa]", "循环数 N", "状态", "失效模式"]
        )
        self.sn_table.horizontalHeader().setStretchLastSection(True)
        self.sn_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sn_table.verticalHeader().setDefaultSectionSize(30)
        self.sn_table.setMinimumHeight(260)
        body.addWidget(self.sn_table, 1)
        actions = QHBoxLayout()
        add = QPushButton("新增试样", page)
        remove = QPushButton("删除选中行", page)
        add.clicked.connect(lambda: self._append_sn_row({}))
        remove.clicked.connect(lambda: self._remove_rows(self.sn_table))
        actions.addWidget(add)
        actions.addWidget(remove)
        actions.addStretch(1)
        body.addLayout(actions)
        self.add_chapter("S-N 数据与质量", page, help_ref="modules/fatigue/_section_sn_data")

    def _build_fit_chapter(self) -> None:
        page, body = self._page(
            "P-S-N 拟合",
            "主方法为含 runout 右删失的对数正态 MLE；MRR/仅断裂回归仅作审计对照。",
        )
        self.fit_summary_label = QLabel("执行预校核后显示拟合参数。", page)
        self.fit_summary_label.setObjectName("SectionHint")
        self.fit_summary_label.setWordWrap(True)
        body.addWidget(self.fit_summary_label)
        self.sn_chart = FatigueSnChart(page)
        body.addWidget(self.sn_chart, 1)
        self.add_chapter("P-S-N 拟合", page, help_ref="modules/fatigue/_section_fit")

    def _build_spectrum_chapter(self) -> None:
        page, body = self._page(
            "载荷谱导入与热点应力换算",
            "块谱直接使用；单通道时序先提取转折点并执行 rainflow。载荷可经线性系数或单调查表转换为应力。",
        )
        self.spectrum_kind_combo = self._combo(list(SPECTRUM_KINDS), page)
        self.value_kind_combo = self._combo(list(VALUE_KINDS), page)
        self.transfer_mode_combo = self._combo(list(TRANSFER_MODES), page)
        self.transfer_factor_edit = self._line("1.0", page)
        self.transfer_offset_edit = self._line("0.0", page)
        self.lookup_edit = QPlainTextEdit(page)
        self.lookup_edit.setObjectName("InputField")
        self.lookup_edit.setPlaceholderText("每行 load,stress_mpa，例如\n-1000,-100\n0,0\n1000,100")
        self.lookup_edit.setMaximumHeight(90)
        self.extrapolation_combo = self._combo(["禁止外推", "允许趋势外推（结果不完整）"], page)
        body.addWidget(
            self._form_card(
                page,
                [
                    ("谱文件形态", self.spectrum_kind_combo),
                    ("谱值类型", self.value_kind_combo),
                    ("传递方式", self.transfer_mode_combo),
                    ("线性系数 k [MPa/unit]", self.transfer_factor_edit),
                    ("线性偏置 b [MPa]", self.transfer_offset_edit),
                    ("载荷-应力查表", self.lookup_edit),
                    ("实测范围外处理", self.extrapolation_combo),
                ],
            )
        )
        self.spectrum_source_label = QLabel("尚未导入文件；当前可使用表内块谱。", page)
        self.spectrum_source_label.setObjectName("SectionHint")
        body.addWidget(self.spectrum_source_label)
        self.spectrum_table = QTableWidget(0, 3, page)
        self.spectrum_table.setObjectName("EngineeringTable")
        self.spectrum_table.setHorizontalHeaderLabels(["幅值/时序值", "均值/时间 [s]", "循环数"])
        self.spectrum_table.horizontalHeader().setStretchLastSection(True)
        self.spectrum_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.spectrum_table.verticalHeader().setDefaultSectionSize(30)
        self.spectrum_table.setMinimumHeight(190)
        body.addWidget(self.spectrum_table, 1)
        actions = QHBoxLayout()
        add = QPushButton("新增谱级", page)
        remove = QPushButton("删除选中行", page)
        add.clicked.connect(lambda: self._append_spectrum_row({}))
        remove.clicked.connect(lambda: self._remove_rows(self.spectrum_table))
        actions.addWidget(add)
        actions.addWidget(remove)
        actions.addStretch(1)
        body.addLayout(actions)
        self.add_chapter("载荷谱与应力换算", page, help_ref="modules/fatigue/_section_spectrum")

    def _build_reliability_chapter(self) -> None:
        page, body = self._page(
            "损伤与可靠性设置",
            "可靠性传播同一零件共享的 S-N 纵向散差，并可叠加均值为 1 的整体载荷倍率 COV。",
        )
        self.target_blocks_edit = self._line("10", page)
        self.required_reliability_edit = self._line("0.90", page)
        self.design_survival_edit = self._line("0.90", page)
        self.load_cov_edit = self._line("0.00", page)
        self.mc_samples_edit = self._line("20000", page)
        self.bootstrap_samples_edit = self._line("500", page)
        self.seed_edit = self._line("1729", page)
        body.addWidget(
            self._form_card(
                page,
                [
                    ("目标谱块数", self.target_blocks_edit),
                    ("要求可靠度 R", self.required_reliability_edit),
                    ("设计曲线存活率 Ps", self.design_survival_edit),
                    ("整体载荷 COV", self.load_cov_edit),
                    ("Monte Carlo 次数", self.mc_samples_edit),
                    ("bootstrap 次数", self.bootstrap_samples_edit),
                    ("随机种子", self.seed_edit),
                ],
            )
        )
        note = QLabel(
            "提示：20,000/500 是正式默认值；大样本拟合会耗时。固定随机种子保证相同输入可复现。",
            page,
        )
        note.setObjectName("SectionHint")
        note.setWordWrap(True)
        body.addWidget(note)
        body.addStretch(1)
        self.add_chapter("损伤与可靠性", page, help_ref="modules/fatigue/_section_reliability")

    def _build_results_chapter(self) -> None:
        page, body = self._page(
            "结果与报告",
            "总体结论只在数据充分、条件兼容且无外推时允许通过。",
        )
        self.overall_label = QLabel("总体结论：待计算", page)
        self.overall_label.setObjectName("WaitBadge")
        self.overall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(self.overall_label)
        badge_row = QGridLayout()
        self.check_badges: dict[str, QLabel] = {}
        for index, (check_id, label) in enumerate(FATIGUE_CHECK_LABELS.items()):
            badge = QLabel(f"{label}: 待计算", page)
            badge.setObjectName("WaitBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_row.addWidget(badge, index // 3, index % 3)
            self.check_badges[check_id] = badge
        body.addLayout(badge_row)
        self.metrics_label = QLabel("执行预校核后显示拟合、损伤和可靠性指标。", page)
        self.metrics_label.setObjectName("SectionHint")
        self.metrics_label.setWordWrap(True)
        body.addWidget(self.metrics_label)
        charts = QTabWidget(page)
        charts.setObjectName("ResultChartTabs")
        self.damage_chart = FatigueDamageChart(page)
        self.reliability_chart = FatigueReliabilityChart(page)
        charts.addTab(self.damage_chart, "损伤贡献")
        charts.addTab(self.reliability_chart, "寿命 / 可靠度")
        body.addWidget(charts, 1)
        self.report_preview = QPlainTextEdit(page)
        self.report_preview.setReadOnly(True)
        self.report_preview.setMaximumHeight(130)
        self.report_preview.setPlainText("执行预校核后显示报告预览。")
        body.addWidget(self.report_preview)
        self.add_chapter("结果与报告", page, help_ref="modules/fatigue/_section_results")

    # ------------------------------------------------------------------
    # Table and dirty-state helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _set_cell(table: QTableWidget, row: int, column: int, value: Any) -> None:
        table.setItem(row, column, QTableWidgetItem("" if value is None else str(value)))

    def _append_sn_row(self, data: dict[str, Any]) -> None:
        row = self.sn_table.rowCount()
        self.sn_table.insertRow(row)
        values = [
            data.get("specimen_id", row + 1),
            data.get("level_id", ""),
            data.get("condition_group", "C1"),
            data.get("stress_amplitude_mpa", data.get("amplitude_mpa", "")),
            data.get("stress_mean_mpa", data.get("mean_mpa", 0)),
            data.get("cycles", ""),
            data.get("status", "failure"),
            data.get("failure_mode", ""),
        ]
        for column, value in enumerate(values):
            self._set_cell(self.sn_table, row, column, value)

    def _append_spectrum_row(self, data: dict[str, Any]) -> None:
        row = self.spectrum_table.rowCount()
        self.spectrum_table.insertRow(row)
        values = [
            data.get("amplitude", data.get("value", "")),
            data.get("mean", data.get("time_s", 0)),
            data.get("cycles", ""),
        ]
        for column, value in enumerate(values):
            self._set_cell(self.spectrum_table, row, column, value)

    def _remove_rows(self, table: QTableWidget) -> None:
        rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        for row in rows:
            table.removeRow(row)
        self._invalidate_result("数据行已修改，旧结果已失效。")

    def _connect_dirty_tracking(self) -> None:
        lines = [
            self.material_name_edit,
            self.batch_edit,
            self.temperature_edit,
            self.humidity_edit,
            self.frequency_edit,
            self.r_ratio_edit,
            self.waveform_edit,
            self.orientation_edit,
            self.conditioning_edit,
            self.process_edit,
            self.surface_edit,
            self.ultimate_edit,
            self.transfer_factor_edit,
            self.transfer_offset_edit,
            self.target_blocks_edit,
            self.required_reliability_edit,
            self.design_survival_edit,
            self.load_cov_edit,
            self.mc_samples_edit,
            self.bootstrap_samples_edit,
            self.seed_edit,
        ]
        for widget in lines:
            widget.textChanged.connect(lambda _text: self._invalidate_result())
        for widget in (
            self.material_type_combo,
            self.object_type_combo,
            self.mean_stress_combo,
            self.spectrum_kind_combo,
            self.value_kind_combo,
            self.transfer_mode_combo,
            self.extrapolation_combo,
        ):
            widget.currentTextChanged.connect(lambda _text: self._invalidate_result())
        self.lookup_edit.textChanged.connect(self._invalidate_result)
        self.sn_table.itemChanged.connect(lambda _item: self._invalidate_result())
        self.spectrum_table.itemChanged.connect(lambda _item: self._invalidate_result())

    def _sync_material_controls(self, _text: str = "") -> None:
        is_metal = MATERIAL_TYPES[self.material_type_combo.currentText()] == "metal"
        if not is_metal and self.mean_stress_combo.currentIndex() != 0:
            self.mean_stress_combo.setCurrentIndex(0)
        self.mean_stress_combo.setEnabled(is_metal)
        self.ultimate_edit.setEnabled(
            is_metal and MEAN_STRESS_MODELS[self.mean_stress_combo.currentText()] == "goodman"
        )

    def _sync_transfer_controls(self, _text: str = "") -> None:
        """Hide transfer fields that do not participate in the current model."""
        uses_load = VALUE_KINDS[self.value_kind_combo.currentText()] == "load"
        if not uses_load and self.transfer_mode_combo.currentText() != "直接应力":
            self.transfer_mode_combo.setCurrentText("直接应力")
        self.transfer_mode_combo.setEnabled(uses_load)
        mode = TRANSFER_MODES[self.transfer_mode_combo.currentText()]
        visibility = {
            self.transfer_factor_edit: uses_load and mode == "linear",
            self.transfer_offset_edit: uses_load and mode == "linear",
            self.lookup_edit: uses_load and mode == "lookup",
        }
        for widget, visible in visibility.items():
            widget.setVisible(visible)
            label = self._field_labels.get(widget)
            if label is not None:
                label.setVisible(visible)

    def _invalidate_result(self, message: str = "输入已变化，旧结果和导出已失效。") -> None:
        if self._suspend_dirty:
            return
        self._last_payload = None
        self._last_result = None
        self.btn_export.setEnabled(False)
        self.overall_label.setText("总体结论：待计算")
        self.overall_label.setObjectName("WaitBadge")
        self.overall_label.style().unpolish(self.overall_label)
        self.overall_label.style().polish(self.overall_label)
        for check_id, badge in self.check_badges.items():
            badge.setText(f"{FATIGUE_CHECK_LABELS[check_id]}: 待计算")
            badge.setObjectName("WaitBadge")
            badge.style().unpolish(badge)
            badge.style().polish(badge)
        self.fit_summary_label.setText("执行预校核后显示拟合参数。")
        self.metrics_label.setText("执行预校核后显示拟合、损伤和可靠性指标。")
        self.sn_chart.clear()
        self.damage_chart.clear()
        self.reliability_chart.clear()
        self.report_preview.setPlainText("执行预校核后显示报告预览。")
        self.set_info(message)

    @staticmethod
    def _cell_text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return item.text().strip() if item else ""

    # ------------------------------------------------------------------
    # Payload, calculation, and rendering
    # ------------------------------------------------------------------

    def _test_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in range(self.sn_table.rowCount()):
            if not any(self._cell_text(self.sn_table, row, column) for column in range(8)):
                continue
            rows.append(
                {
                    "specimen_id": self._cell_text(self.sn_table, row, 0) or str(row + 1),
                    "level_id": self._cell_text(self.sn_table, row, 1),
                    "condition_group": self._cell_text(self.sn_table, row, 2),
                    "stress_amplitude_mpa": float(self._cell_text(self.sn_table, row, 3)),
                    "stress_mean_mpa": float(self._cell_text(self.sn_table, row, 4) or 0),
                    "cycles": float(self._cell_text(self.sn_table, row, 5)),
                    "status": self._cell_text(self.sn_table, row, 6) or "failure",
                    "failure_mode": self._cell_text(self.sn_table, row, 7),
                }
            )
        return rows

    def _spectrum_payload(self) -> dict[str, Any]:
        kind = SPECTRUM_KINDS[self.spectrum_kind_combo.currentText()]
        common = {
            "kind": kind,
            "value_kind": VALUE_KINDS[self.value_kind_combo.currentText()],
            "condition": {
                "temperature_c": float(self.temperature_edit.text()),
                "humidity_rh": float(self.humidity_edit.text()),
                "frequency_hz": float(self.frequency_edit.text()),
                "r_ratio": float(self.r_ratio_edit.text()),
                "orientation": self.orientation_edit.text().strip(),
                "conditioning": self.conditioning_edit.text().strip(),
            },
            "source": self._spectrum_source,
        }
        if kind == "blocks":
            blocks = []
            for row in range(self.spectrum_table.rowCount()):
                first = self._cell_text(self.spectrum_table, row, 0)
                if not first:
                    continue
                blocks.append(
                    {
                        "amplitude": float(first),
                        "mean": float(self._cell_text(self.spectrum_table, row, 1) or 0),
                        "cycles": float(self._cell_text(self.spectrum_table, row, 2)),
                    }
                )
            common["blocks"] = blocks
        else:
            series = []
            for row in range(self.spectrum_table.rowCount()):
                first = self._cell_text(self.spectrum_table, row, 0)
                if not first:
                    continue
                series.append(
                    {
                        "value": float(first),
                        "time_s": float(self._cell_text(self.spectrum_table, row, 1) or row),
                    }
                )
            common["series"] = series
        return common

    def _lookup_points(self) -> list[dict[str, float]]:
        points: list[dict[str, float]] = []
        for number, line in enumerate(self.lookup_edit.toPlainText().splitlines(), start=1):
            if not line.strip():
                continue
            parts = [item.strip() for item in line.replace("\t", ",").split(",")]
            if len(parts) != 2:
                raise ValueError(f"传递查表第 {number} 行必须是 load,stress_mpa")
            points.append({"load": float(parts[0]), "stress_mpa": float(parts[1])})
        return points

    def _build_payload(self) -> dict[str, Any]:
        mean_model = MEAN_STRESS_MODELS[self.mean_stress_combo.currentText()]
        transfer_mode = TRANSFER_MODES[self.transfer_mode_combo.currentText()]
        transfer: dict[str, Any] = {
            "mode": transfer_mode,
            "allow_extrapolation": self.extrapolation_combo.currentIndex() == 1,
        }
        if transfer_mode == "linear":
            transfer.update(
                {
                    "factor_mpa_per_unit": float(self.transfer_factor_edit.text()),
                    "offset_mpa": float(self.transfer_offset_edit.text()),
                }
            )
        elif transfer_mode == "lookup":
            transfer["points"] = self._lookup_points()
        sn_model: dict[str, Any] = {
            "mean_stress_model": mean_model,
            "design_survival_probability": float(self.design_survival_edit.text()),
            "allow_extrapolation": self.extrapolation_combo.currentIndex() == 1,
        }
        if mean_model == "goodman":
            sn_model["ultimate_strength_mpa"] = float(self.ultimate_edit.text())
        return {
            "material_condition": {
                "material_type": MATERIAL_TYPES[self.material_type_combo.currentText()],
                "material_name": self.material_name_edit.text().strip(),
                "batch": self.batch_edit.text().strip(),
                "object_type": self.object_type_combo.currentText(),
                "temperature_c": float(self.temperature_edit.text()),
                "humidity_rh": float(self.humidity_edit.text()),
                "frequency_hz": float(self.frequency_edit.text()),
                "r_ratio": float(self.r_ratio_edit.text()),
                "waveform": self.waveform_edit.text().strip(),
                "orientation": self.orientation_edit.text().strip(),
                "conditioning": self.conditioning_edit.text().strip(),
                "process_condition": self.process_edit.text().strip(),
                "surface": self.surface_edit.text().strip(),
            },
            "test_data": {"specimens": self._test_rows(), "source": self._sn_source},
            "sn_model": sn_model,
            "spectrum": self._spectrum_payload(),
            "transfer": transfer,
            "reliability": {
                "target_spectrum_blocks": float(self.target_blocks_edit.text()),
                "required_reliability": float(self.required_reliability_edit.text()),
                "load_cov": float(self.load_cov_edit.text()),
                "monte_carlo_samples": int(float(self.mc_samples_edit.text())),
                "bootstrap_samples": int(float(self.bootstrap_samples_edit.text())),
                "seed": int(float(self.seed_edit.text())),
            },
        }

    def _calculate_fatigue(self, payload: dict[str, Any]) -> dict[str, Any]:
        return calculate_fatigue_reliability(payload)

    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = self._calculate_fatigue(payload)
        except (InputError, ValueError, TypeError) as exc:
            self._invalidate_result("预校核失败，旧结果已清空。")
            QMessageBox.warning(self, "预校核失败", str(exc))
            return
        try:
            self._render_result(payload, result)
        except Exception as exc:
            self._invalidate_result("结果渲染失败，旧结果和导出已清空。")
            QMessageBox.critical(self, "结果渲染失败", str(exc))

    def _render_result(self, payload: dict[str, Any], result: dict[str, Any]) -> None:
        self._last_payload = payload
        self._last_result = result
        view = from_fatigue(result, payload)
        self.overall_label.setText(f"总体结论：{view.title_zh}")
        self.overall_label.setObjectName(badge_object_name(view.overall_status))
        self.overall_label.style().unpolish(self.overall_label)
        self.overall_label.style().polish(self.overall_label)
        for check in view.checks:
            badge = self.check_badges[check.id]
            badge.setText(f"{check.label_zh}: {status_label_zh(check.status)}")
            badge.setObjectName(badge_object_name(check.status))
            badge.style().unpolish(badge)
            badge.style().polish(badge)
        self.metrics_label.setText(" · ".join(
            f"{metric.label}: {metric.value}{(' ' + metric.unit) if metric.unit else ''}"
            for metric in view.metrics
        ) or "当前数据不足以形成数值结果。")
        fit = result.get("fit") if isinstance(result.get("fit"), dict) else {}
        evidence = (
            result.get("fatigue_limit_evidence")
            if isinstance(result.get("fatigue_limit_evidence"), dict)
            else {}
        )
        self.fit_summary_label.setText(
            f"拟合状态: {fit.get('status', '-')} · 断裂 {fit.get('failure_count', 0)} · "
            f"runout {fit.get('runout_count', 0)} · a={fit.get('a', '-')} · "
            f"b={fit.get('b', '-')} · s={fit.get('scatter_log10_n', '-')} · "
            f"疲劳极限证据区间={evidence.get('possible_lower_bound_mpa', '-')}.."
            f"{evidence.get('possible_upper_bound_mpa', '-')} MPa（仅证据，不作确定值）"
        )
        self.sn_chart.set_data(payload["test_data"]["specimens"], fit, payload["sn_model"]["design_survival_probability"])
        damage = result.get("damage") if isinstance(result.get("damage"), dict) else {}
        reliability = result.get("reliability") if isinstance(result.get("reliability"), dict) else {}
        self.damage_chart.set_data(damage.get("contributions", []) if isinstance(damage, dict) else [])
        self.reliability_chart.set_data(reliability)
        self.report_preview.setPlainText("\n".join(self._build_report_lines()))
        self.btn_export.setEnabled(True)
        self.set_info(f"预校核完成：{view.title_zh}")
        self.set_current_chapter(6)

    # ------------------------------------------------------------------
    # Import, save/load, sample, clear, report
    # ------------------------------------------------------------------

    def _choose_sheet(self, path: Path) -> str | None:
        sheets = list_xlsx_sheets(path)
        if len(sheets) <= 1:
            return sheets[0] if sheets else None
        selected, accepted = QInputDialog.getItem(self, "选择工作表", "工作表", sheets, 0, False)
        return selected if accepted else None

    def _on_import_sn(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择 S-N 试验数据", str(EXAMPLES_DIR), "数据文件 (*.csv *.xlsx);;All Files (*)"
        )
        if not file_name:
            return
        path = Path(file_name)
        sheet = self._choose_sheet(path)
        if path.suffix.lower() == ".xlsx" and sheet is None:
            return
        try:
            data = load_sn_test_data(path, sheet_name=sheet)
        except FatigueImportError as exc:
            QMessageBox.warning(self, "S-N 数据导入失败", str(exc))
            return
        self._suspend_dirty = True
        self.sn_table.setRowCount(0)
        for row in data["specimens"]:
            self._append_sn_row(row)
        self._sn_source = data["source"]
        self.sn_source_label.setText(
            f"已导入 {self._sn_source['file_name']} · 工作表 {self._sn_source['sheet_name']} · "
            f"{len(data['specimens'])} 件 · SHA-256 {self._sn_source['sha256'][:12]}…"
        )
        self._suspend_dirty = False
        self._invalidate_result("S-N 数据已导入，请执行预校核。")

    def _on_import_spectrum(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择载荷/应力谱", str(EXAMPLES_DIR), "数据文件 (*.csv *.xlsx);;All Files (*)"
        )
        if not file_name:
            return
        path = Path(file_name)
        sheet = self._choose_sheet(path)
        if path.suffix.lower() == ".xlsx" and sheet is None:
            return
        kind = SPECTRUM_KINDS[self.spectrum_kind_combo.currentText()]
        try:
            data = load_spectrum_data(path, kind=kind, sheet_name=sheet)
        except FatigueImportError as exc:
            QMessageBox.warning(self, "载荷谱导入失败", str(exc))
            return
        self._suspend_dirty = True
        self.spectrum_table.setRowCount(0)
        rows = data.get("blocks", data.get("series", []))
        for row in rows:
            self._append_spectrum_row(row)
        self._spectrum_source = data["source"]
        self.spectrum_source_label.setText(
            f"已导入 {self._spectrum_source['file_name']} · 工作表 {self._spectrum_source['sheet_name']} · "
            f"{len(rows)} 行 · SHA-256 {self._spectrum_source['sha256'][:12]}…"
        )
        self._suspend_dirty = False
        self._invalidate_result("载荷谱已导入，请执行预校核。")

    def _snapshot(self) -> dict[str, Any]:
        return {"module": MODULE_ID, "inputs": self._build_payload()}

    def _on_save_inputs(self) -> None:
        try:
            snapshot = self._snapshot()
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "保存失败", f"输入尚不能序列化：{exc}")
            return
        path = choose_save_input_conditions_path(
            self, "保存疲劳预校核输入", SAVED_INPUTS_DIR / "fatigue_reliability_inputs.json"
        )
        if path is None:
            return
        try:
            write_input_conditions(path, snapshot)
        except OSError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.set_info(f"输入条件已保存：{path}")

    def _on_load_inputs(self) -> None:
        path = choose_load_input_conditions_path(self, "加载疲劳预校核输入", SAVED_INPUTS_DIR)
        if path is None:
            return
        try:
            snapshot = validate_snapshot(read_input_conditions(path))
            if not confirm_snapshot_module(self, snapshot, MODULE_ID):
                return
            payload = snapshot.get("inputs")
            if not isinstance(payload, dict):
                raise ValueError("输入文件缺少 inputs 对象")
            self._apply_payload(payload)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "加载失败", str(exc))
            return
        self._invalidate_result("输入条件已加载，需重新执行预校核。")

    @staticmethod
    def _set_combo_by_value(combo: QComboBox, mapping: dict[str, str], value: str) -> None:
        label = next((label for label, core in mapping.items() if core == value), None)
        if label is not None:
            combo.setCurrentText(label)

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        self._suspend_dirty = True
        material = payload.get("material_condition", {})
        sn_model = payload.get("sn_model", {})
        spectrum = payload.get("spectrum", {})
        transfer = payload.get("transfer", {})
        reliability = payload.get("reliability", {})
        self._set_combo_by_value(self.material_type_combo, MATERIAL_TYPES, str(material.get("material_type", "metal")))
        self.material_name_edit.setText(str(material.get("material_name", "")))
        self.batch_edit.setText(str(material.get("batch", "")))
        self.object_type_combo.setCurrentText(str(material.get("object_type", "材料试样")))
        for widget, key, default in (
            (self.temperature_edit, "temperature_c", 23),
            (self.humidity_edit, "humidity_rh", 50),
            (self.frequency_edit, "frequency_hz", 5),
            (self.r_ratio_edit, "r_ratio", -1),
        ):
            widget.setText(str(material.get(key, default)))
        self.waveform_edit.setText(str(material.get("waveform", "sinusoidal")))
        self.orientation_edit.setText(str(material.get("orientation", "flow")))
        self.conditioning_edit.setText(str(material.get("conditioning", "dry")))
        self.process_edit.setText(str(material.get("process_condition", "")))
        self.surface_edit.setText(str(material.get("surface", "")))
        self._set_combo_by_value(self.mean_stress_combo, MEAN_STRESS_MODELS, str(sn_model.get("mean_stress_model", "none")))
        self.ultimate_edit.setText(str(sn_model.get("ultimate_strength_mpa", 900)))
        self.design_survival_edit.setText(str(sn_model.get("design_survival_probability", 0.9)))
        self.extrapolation_combo.setCurrentIndex(1 if sn_model.get("allow_extrapolation") else 0)
        self.sn_table.setRowCount(0)
        test_data = payload.get("test_data", {})
        for row in test_data.get("specimens", []):
            self._append_sn_row(row)
        self._sn_source = dict(test_data.get("source", {}))
        self._set_combo_by_value(self.spectrum_kind_combo, SPECTRUM_KINDS, str(spectrum.get("kind", "blocks")))
        self._set_combo_by_value(self.value_kind_combo, VALUE_KINDS, str(spectrum.get("value_kind", "stress")))
        self.spectrum_table.setRowCount(0)
        for row in spectrum.get("blocks", spectrum.get("series", [])):
            self._append_spectrum_row(row)
        self._spectrum_source = dict(spectrum.get("source", {}))
        self._set_combo_by_value(self.transfer_mode_combo, TRANSFER_MODES, str(transfer.get("mode", "direct_stress")))
        self.transfer_factor_edit.setText(str(transfer.get("factor_mpa_per_unit", 1.0)))
        self.transfer_offset_edit.setText(str(transfer.get("offset_mpa", 0.0)))
        self.lookup_edit.setPlainText("\n".join(
            f"{point.get('load')},{point.get('stress_mpa')}" for point in transfer.get("points", [])
        ))
        for widget, key, default in (
            (self.target_blocks_edit, "target_spectrum_blocks", 1),
            (self.required_reliability_edit, "required_reliability", 0.9),
            (self.load_cov_edit, "load_cov", 0),
            (self.mc_samples_edit, "monte_carlo_samples", 20000),
            (self.bootstrap_samples_edit, "bootstrap_samples", 500),
            (self.seed_edit, "seed", 1729),
        ):
            widget.setText(str(reliability.get(key, default)))
        self._suspend_dirty = False

    def _load_sample(self) -> None:
        specimens: list[dict[str, Any]] = []
        factors = (0.82, 0.93, 1.0, 1.08, 1.18)
        for stress in (100.0, 140.0, 200.0):
            median = 10 ** (12.0 - 3.0 * math.log10(stress))
            for index, factor in enumerate(factors):
                specimens.append(
                    {
                        "specimen_id": f"{int(stress)}-{index + 1}",
                        "level_id": f"S{int(stress)}",
                        "condition_group": "C1",
                        "stress_amplitude_mpa": stress,
                        "stress_mean_mpa": 0,
                        "cycles": round(median * factor),
                        "status": "failure",
                        "failure_mode": "截面断裂",
                    }
                )
        specimens.append(
            {
                "specimen_id": "100-R",
                "level_id": "S100",
                "condition_group": "C1",
                "stress_amplitude_mpa": 100,
                "stress_mean_mpa": 0,
                "cycles": 1_250_000,
                "status": "runout",
                "failure_mode": "",
            }
        )
        self._suspend_dirty = True
        self.sn_table.setRowCount(0)
        for row in specimens:
            self._append_sn_row(row)
        self.spectrum_table.setRowCount(0)
        for row in (
            {"amplitude": 120, "mean": 0, "cycles": 1000},
            {"amplitude": 180, "mean": 0, "cycles": 20},
        ):
            self._append_spectrum_row(row)
        self._sn_source = {"file_name": "内置测试案例 1", "sheet_name": "embedded", "sha256": "embedded"}
        self._spectrum_source = {"file_name": "内置测试案例 1", "sheet_name": "embedded", "sha256": "embedded"}
        self.sn_source_label.setText("已加载内置 S-N 测试案例：15 件断裂 + 1 件 runout。")
        self.spectrum_source_label.setText("已加载内置两级应力块谱。")
        self._suspend_dirty = False
        self._invalidate_result("测试案例 1 已加载，请执行预校核。")

    def _on_clear(self) -> None:
        self._suspend_dirty = True
        self.sn_table.setRowCount(0)
        self.spectrum_table.setRowCount(0)
        self._sn_source = {}
        self._spectrum_source = {}
        self.sn_source_label.setText("尚未导入文件；当前可使用表内数据。")
        self.spectrum_source_label.setText("尚未导入文件；当前可使用表内块谱。")
        self._suspend_dirty = False
        self._invalidate_result("参数已清空，导出结果已失效。")

    def _build_report_lines(self) -> list[str]:
        if self._last_result is None or self._last_payload is None:
            return ["疲劳强度与可靠性预校核报告", "", "尚未执行预校核。"]
        payload = self._last_payload
        result = self._last_result
        view = from_fatigue(result, payload)
        fit = result.get("fit", {})
        evidence = result.get("fatigue_limit_evidence") or {}
        damage = result.get("damage") or {}
        reliability = result.get("reliability") or {}
        sn_source = payload.get("test_data", {}).get("source") or {}
        spectrum_source = payload.get("spectrum", {}).get("source") or {}
        lines = [
            "疲劳强度与可靠性预校核报告",
            "=" * 32,
            *trace_report_lines(build_report_trace(MODULE_ID, payload, model_level=FATIGUE_SCOPE.model_level)),
            "",
            *scope_report_lines(FATIGUE_SCOPE),
            "",
            f"总体结论: {view.title_zh}",
            view.summary_zh,
            "",
            "1. 试验条件与数据",
            f"- 材料/数据集: {payload['material_condition'].get('material_name', '-')}",
            f"- 材料类型: {payload['material_condition'].get('material_type', '-')}",
            f"- 试样数: {len(payload['test_data'].get('specimens', []))}",
            f"- 断裂/runout: {fit.get('failure_count', 0)} / {fit.get('runout_count', 0)}",
            f"- S-N 来源: {sn_source.get('file_name', '-')} / {sn_source.get('sheet_name', '-')} / "
            f"SHA-256 {sn_source.get('sha256', '-')}",
            f"- 温度/湿度/频率/R: {payload['material_condition'].get('temperature_c')} °C / "
            f"{payload['material_condition'].get('humidity_rh')} %RH / "
            f"{payload['material_condition'].get('frequency_hz')} Hz / {payload['material_condition'].get('r_ratio')}",
            f"- 热处理/成型/表面/方向: {payload['material_condition'].get('process_condition', '-')} / "
            f"{payload['material_condition'].get('surface', '-')} / {payload['material_condition'].get('orientation', '-')}",
            "",
            "2. S-N/P-S-N 拟合",
            "- 主方法: 含 runout 右删失项的对数正态极大似然",
            f"- 拟合状态: {fit.get('status', '-')}",
            f"- log10(N) = a - b·log10(Sa,eq): a={fit.get('a', '-')}, b={fit.get('b', '-')}",
            f"- lgN 散差 s: {fit.get('scatter_log10_n', '-')}",
            f"- 疲劳极限证据区间: {evidence.get('possible_lower_bound_mpa', '-')} .. "
            f"{evidence.get('possible_upper_bound_mpa', '-')} MPa；全 runout 级不进入有限寿命直线。",
            "- Johnson/MRR 与仅断裂点回归只作审计对照，不参与主结论。",
            "",
            "3. 谱、损伤与可靠性",
            f"- 谱类型: {payload['spectrum'].get('kind')}",
            f"- 谱来源: {spectrum_source.get('file_name', '-')} / {spectrum_source.get('sheet_name', '-')} / "
            f"SHA-256 {spectrum_source.get('sha256', '-')}",
            f"- 载荷到应力传递: {payload.get('transfer', {}).get('mode', 'direct_stress')}",
            f"- 单谱块损伤: {damage.get('damage_per_spectrum_block', '-')}",
            f"- 目标 Miner 损伤: {damage.get('target_damage', '-')}",
            f"- 目标寿命前失效概率 Pf: {reliability.get('probability_of_failure', '-')} "
            f"({reliability.get('pf_ppm', '-')} ppm)",
            f"- 目标可靠度 R: {reliability.get('reliability', '-')}",
            f"- 存活率 Ps=90% 对应寿命: {(reliability.get('life_quantiles_blocks') or {}).get('Ps90', '-')} 谱块",
            f"- Pf 95% 置信区间: {reliability.get('pf_confidence_interval_95', '-')}",
            "",
            "4. 校核项",
        ]
        lines.extend(f"- {check.label_zh}: {status_label_zh(check.status)}" for check in view.checks)
        if view.warnings:
            lines.extend(["", "5. 警告与限制", *[f"- {item}" for item in view.warnings]])
        lines.extend(["", "6. 模型假设", *[f"- {item}" for item in result.get("assumptions", [])]])
        return lines

    def _on_export(self) -> None:
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行预校核。")
            return
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "导出疲劳强度与可靠性预校核报告",
            str(EXAMPLES_DIR / "fatigue_reliability_report.pdf"),
            "PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;All Files (*)",
        )
        if not file_name:
            return
        path = Path(file_name)
        try:
            if path.suffix.lower() == ".pdf":
                from app.ui.report_pdf_fatigue import generate_fatigue_report

                generate_fatigue_report(path, self._last_payload, self._last_result)
            elif path.suffix.lower() == ".docx":
                _export_docx(path, self._build_report_lines())
            else:
                write_text_report(path, "\n".join(self._build_report_lines()))
        except (OSError, ReportExportError) as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        self.set_info(f"结果说明已导出：{path}")
