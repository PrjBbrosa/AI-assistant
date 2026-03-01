"""Bolt module page in eAssistant-style chapter layout."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
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

from app.ui.widgets.clamping_diagram import ClampingDiagramWidget
from core.bolt.calculator import InputError, calculate_vdi2230_core

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = PROJECT_ROOT / "examples"


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


CHAPTERS: list[dict[str, Any]] = [
    {
        "id": "operating",
        "title": "14.2 Operating Data",
        "subtitle": "工况与最小夹紧需求",
        "fields": [
            FieldSpec(
                "operating.setup_case",
                "工况类型",
                "-",
                "对应手册 14.2.1 的载荷工况说明，用于记录设计场景。",
                widget_type="choice",
                options=("轴向载荷", "横向载荷", "轴向+横向", "自由输入"),
                default="轴向+横向",
            ),
            FieldSpec(
                "loads.FA_max",
                "最大轴向工作载荷 FA,max",
                "N",
                "外部轴向拉载，作用于连接上的最大工作载荷。",
                mapping=("loads", "FA_max"),
            ),
            FieldSpec(
                "loads.FQ_max",
                "最大横向载荷 FQ,max",
                "N",
                "横向剪切载荷，用于防滑夹紧力校核。",
                mapping=("loads", "FQ_max"),
                default="0",
            ),
            FieldSpec(
                "loads.seal_force_required",
                "密封所需残余夹紧力 FK,req",
                "N",
                "若有密封要求，填该值；否则可填 0。",
                mapping=("loads", "seal_force_required"),
                default="0",
            ),
            FieldSpec(
                "loads.friction_interfaces",
                "摩擦面数 qF",
                "-",
                "防滑校核中参与传力的摩擦界面数量。",
                mapping=("loads", "friction_interfaces"),
                default="1",
            ),
            FieldSpec(
                "loads.slip_friction_coefficient",
                "防滑摩擦系数 μT",
                "-",
                "防滑工况使用的摩擦系数，常与支承面摩擦不同。",
                mapping=("loads", "slip_friction_coefficient"),
                default="0.18",
            ),
            FieldSpec(
                "operating.load_cycles",
                "载荷循环次数 ND",
                "次",
                "用于疲劳判断的记录参数。当前首版不参与疲劳计算。",
                default="100000",
            ),
            FieldSpec(
                "operating.temp_bolt",
                "螺栓温度",
                "°C",
                "用于热损失估算。若已知等效热损失可直接在下方输入。",
                default="20",
            ),
            FieldSpec(
                "operating.temp_parts",
                "被夹件温度",
                "°C",
                "与螺栓温度共同影响热预紧力损失。",
                default="20",
            ),
        ],
    },
    {
        "id": "assembly",
        "title": "14.3 Assembly Properties",
        "subtitle": "装配方式与预紧散差",
        "fields": [
            FieldSpec(
                "assembly.tightening_method",
                "拧紧方式",
                "-",
                "对应手册 14.3 的装配方式。首版用于记录，不参与算法分支。",
                widget_type="choice",
                options=("扭矩法", "转角法", "液压拉伸法", "热装法"),
                default="扭矩法",
            ),
            FieldSpec(
                "tightening.alpha_A",
                "拧紧系数 αA",
                "-",
                "FMmax/FMmin，反映装配散差。扭矩法常见 1.4~1.8。",
                mapping=("tightening", "alpha_A"),
                default="1.6",
            ),
            FieldSpec(
                "tightening.utilization",
                "装配利用系数 ν",
                "-",
                "装配阶段允许屈服利用比例，常见 0.8~0.95。",
                mapping=("tightening", "utilization"),
                default="0.9",
            ),
            FieldSpec(
                "tightening.prevailing_torque",
                "附加防松扭矩 MA,prev",
                "N·m",
                "锁紧螺母等引入的附加扭矩。无则填 0。",
                mapping=("tightening", "prevailing_torque"),
                default="0",
            ),
            FieldSpec(
                "loads.embed_loss",
                "嵌入损失 FZ",
                "N",
                "接触表面压平导致的预紧力损失。",
                mapping=("loads", "embed_loss"),
                default="1000",
            ),
            FieldSpec(
                "loads.thermal_force_loss",
                "热损失 Fth",
                "N",
                "热膨胀差异折算的预紧力损失。",
                mapping=("loads", "thermal_force_loss"),
                default="0",
            ),
        ],
    },
    {
        "id": "clamped",
        "title": "14.4 Clamped Parts and Basic Solid",
        "subtitle": "被夹件与基础实体",
        "fields": [
            FieldSpec(
                "clamped.basic_solid",
                "基础实体类型",
                "-",
                "对应手册 Basic Solid。首版用于记录。",
                widget_type="choice",
                options=("Cylinder", "Cone", "Sleeve", "Mixed"),
                default="Cylinder",
            ),
            FieldSpec(
                "clamped.part_count",
                "被夹件数量",
                "个",
                "参与夹紧的零件数量。首版用于记录。",
                default="2",
            ),
            FieldSpec(
                "clamped.total_thickness",
                "总夹紧长度 lK",
                "mm",
                "被夹件厚度总和。后续版本将用于自动刚度建模。",
                default="20",
            ),
            FieldSpec(
                "stiffness.bolt_compliance",
                "螺栓顺从度 δs",
                "mm/N",
                "与被夹件顺从度二选一输入；若填刚度可留空。",
                mapping=("stiffness", "bolt_compliance"),
                default="2.2e-06",
            ),
            FieldSpec(
                "stiffness.clamped_compliance",
                "被夹件顺从度 δp",
                "mm/N",
                "与螺栓顺从度配套输入。",
                mapping=("stiffness", "clamped_compliance"),
                default="3.1e-06",
            ),
            FieldSpec(
                "stiffness.bolt_stiffness",
                "螺栓刚度 cs",
                "N/mm",
                "若使用刚度输入，填 cs 与 cp，顺从度可留空。",
                mapping=("stiffness", "bolt_stiffness"),
            ),
            FieldSpec(
                "stiffness.clamped_stiffness",
                "被夹件刚度 cp",
                "N/mm",
                "与 cs 配套输入。",
                mapping=("stiffness", "clamped_stiffness"),
            ),
        ],
    },
    {
        "id": "elements",
        "title": "14.5 Joint Elements",
        "subtitle": "连接件参数与摩擦",
        "fields": [
            FieldSpec(
                "elements.joint_type",
                "连接形式",
                "-",
                "对应手册 Joint type。当前算法按单螺栓轴向模型计算。",
                widget_type="choice",
                options=("Through-bolt joint", "Tapped thread joint"),
                default="Through-bolt joint",
            ),
            FieldSpec(
                "fastener.d",
                "公称直径 d",
                "mm",
                "螺纹公称直径。",
                mapping=("fastener", "d"),
                default="10",
            ),
            FieldSpec(
                "fastener.p",
                "螺距 p",
                "mm",
                "公制螺纹螺距。",
                mapping=("fastener", "p"),
                default="1.5",
            ),
            FieldSpec(
                "fastener.Rp02",
                "屈服强度 Rp0.2",
                "MPa",
                "螺栓材料屈服强度。",
                mapping=("fastener", "Rp02"),
                default="640",
            ),
            FieldSpec(
                "fastener.As",
                "应力截面积 As",
                "mm²",
                "可不填，系统按 d/p 估算。",
                mapping=("fastener", "As"),
            ),
            FieldSpec(
                "fastener.d2",
                "中径 d2",
                "mm",
                "可不填，系统按 d/p 估算。",
                mapping=("fastener", "d2"),
            ),
            FieldSpec(
                "fastener.d3",
                "小径 d3",
                "mm",
                "可不填，系统按 d/p 估算。",
                mapping=("fastener", "d3"),
            ),
            FieldSpec(
                "tightening.mu_thread",
                "螺纹摩擦系数 μG",
                "-",
                "影响螺纹扭矩与扭转载荷。",
                mapping=("tightening", "mu_thread"),
                default="0.12",
            ),
            FieldSpec(
                "tightening.mu_bearing",
                "支承面摩擦系数 μK",
                "-",
                "影响支承面扭矩。",
                mapping=("tightening", "mu_bearing"),
                default="0.14",
            ),
            FieldSpec(
                "tightening.thread_flank_angle_deg",
                "牙型角",
                "deg",
                "公制螺纹常用 60°。",
                mapping=("tightening", "thread_flank_angle_deg"),
                default="60",
            ),
            FieldSpec(
                "bearing.bearing_d_inner",
                "支承内径 DKm,i",
                "mm",
                "支承有效内径。",
                mapping=("bearing", "bearing_d_inner"),
                default="11",
            ),
            FieldSpec(
                "bearing.bearing_d_outer",
                "支承外径 DKm,o",
                "mm",
                "支承有效外径。",
                mapping=("bearing", "bearing_d_outer"),
                default="18",
            ),
        ],
    },
    {
        "id": "introduction",
        "title": "14.6 Load Introduction",
        "subtitle": "载荷导入与安全系数",
        "fields": [
            FieldSpec(
                "stiffness.load_introduction_factor_n",
                "载荷导入系数 n",
                "-",
                "修正外载导入比例。轴向端部导入通常取 1。",
                mapping=("stiffness", "load_introduction_factor_n"),
                default="1.0",
            ),
            FieldSpec(
                "introduction.position",
                "载荷导入位置",
                "-",
                "对应手册 14.6。用于记录导入方式。",
                widget_type="choice",
                options=("Head", "Nut", "Middle", "Distributed"),
                default="Head",
            ),
            FieldSpec(
                "checks.yield_safety_operating",
                "服役屈服安全系数 S_F",
                "-",
                "服役轴向应力允许值：Rp0.2 / S_F。",
                mapping=("checks", "yield_safety_operating"),
                default="1.1",
            ),
            FieldSpec(
                "introduction.eccentric_clamp",
                "夹紧偏心 e_clamp",
                "mm",
                "首版暂不参与偏心校核，仅记录。",
                default="0",
            ),
            FieldSpec(
                "introduction.eccentric_load",
                "载荷偏心 e_load",
                "mm",
                "首版暂不参与偏心校核，仅记录。",
                default="0",
            ),
        ],
    },
]


CHECK_LABELS = {
    "assembly_von_mises_ok": "装配等效应力校核（VDI R4）",
    "operating_axial_ok": "服役轴向应力校核（VDI R5）",
    "residual_clamp_ok": "残余夹紧力校核（VDI R3）",
    "additional_load_ok": "附加载荷能力参考估算 ⚠",
}


class BoltPage(QWidget):
    """VDI 2230 bolt page with chapter navigation and readable results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
        self._field_widgets: dict[str, QWidget] = {}
        self._field_specs: dict[str, FieldSpec] = {}
        self._widget_hints: dict[QWidget, str] = {}
        self._check_badges: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        header = QFrame(self)
        header.setObjectName("Card")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        header_layout.setSpacing(6)
        title = QLabel("螺栓连接 · VDI 2230 (Chapter 14 布局)", header)
        title.setObjectName("SectionTitle")
        hint = QLabel(
            "章节和参数组织参考 eAssistant Chapter 14。结果区采用工程可读说明，不展示 JSON。",
            header,
        )
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(hint)
        root.addWidget(header)

        actions = QFrame(self)
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        self.btn_load_1 = QPushButton("加载样例 1", actions)
        self.btn_load_2 = QPushButton("加载样例 2", actions)
        self.btn_calculate = QPushButton("执行校核", actions)
        self.btn_calculate.setObjectName("PrimaryButton")
        self.btn_clear = QPushButton("清空参数", actions)
        self.btn_save = QPushButton("导出结果说明", actions)
        actions_layout.addWidget(self.btn_load_1)
        actions_layout.addWidget(self.btn_load_2)
        actions_layout.addWidget(self.btn_calculate)
        actions_layout.addWidget(self.btn_clear)
        actions_layout.addWidget(self.btn_save)
        actions_layout.addStretch(1)
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
        nav_layout.addWidget(self.chapter_list, 1)
        content.addWidget(nav_card, 0)

        self.chapter_stack = QStackedWidget(self)
        content.addWidget(self.chapter_stack, 1)

        self._build_chapter_pages()
        self._build_diagram_page()
        self._build_results_page()

        footer = QFrame(self)
        footer.setObjectName("Card")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(16, 10, 16, 10)
        footer_layout.setSpacing(6)
        self.overall_badge = QLabel("等待计算", footer)
        self.overall_badge.setObjectName("WaitBadge")
        self.info_label = QLabel("选择左侧章节填写参数；聚焦字段可查看说明。", footer)
        self.info_label.setObjectName("SectionHint")
        self.info_label.setWordWrap(True)
        footer_layout.addWidget(self.overall_badge, 0, Qt.AlignmentFlag.AlignLeft)
        footer_layout.addWidget(self.info_label)
        root.addWidget(footer)

        self.chapter_list.currentRowChanged.connect(self.chapter_stack.setCurrentIndex)
        self.chapter_list.setCurrentRow(0)

        self.btn_load_1.clicked.connect(lambda: self._load_sample("input_case_01.json"))
        self.btn_load_2.clicked.connect(lambda: self._load_sample("input_case_02.json"))
        self.btn_calculate.clicked.connect(self._calculate)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_save.clicked.connect(self._save_report)

        self._apply_defaults()
        self._load_sample("input_case_01.json")

    def eventFilter(self, watched, event):  # noqa: N802
        if watched in self._widget_hints and event.type() in (QEvent.Type.FocusIn, QEvent.Type.Enter):
            self.info_label.setText(self._widget_hints[watched])
        return super().eventFilter(watched, event)

    def _build_chapter_pages(self) -> None:
        for chapter in CHAPTERS:
            item = QListWidgetItem(f"{chapter['title']}")
            self.chapter_list.addItem(item)
            page = self._create_chapter_page(chapter["title"], chapter["subtitle"], chapter["fields"])
            self.chapter_stack.addWidget(page)

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
            editor.setPlaceholderText("请输入数值")
            if spec.default:
                editor.setText(spec.default)

        editor.setToolTip(spec.hint)
        editor.installEventFilter(self)
        self._widget_hints[editor] = f"{spec.label}: {spec.hint}"
        self._field_widgets[spec.field_id] = editor
        self._field_specs[spec.field_id] = spec
        return editor

    def _build_diagram_page(self) -> None:
        self.chapter_list.addItem(QListWidgetItem("14.7 Joint Diagram"))
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("14.7 Joint Diagram", page)
        title.setObjectName("SectionTitle")
        hint = QLabel(
            "夹紧示意图展示 FM/FA/FK 关系。图形用于工程沟通，不替代详细结构校核。",
            page,
        )
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)

        self.diagram_widget = ClampingDiagramWidget(page)
        legend = QLabel("符号说明：FM=装配预紧力，FA=工作外载，FK=残余夹紧力。", page)
        legend.setObjectName("SectionHint")
        legend.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(self.diagram_widget, 1)
        layout.addWidget(legend)
        self.chapter_stack.addWidget(page)

    def _build_results_page(self) -> None:
        self.chapter_list.addItem(QListWidgetItem("14.8~14.10 Results & Messages"))
        page = QFrame(self)
        page.setObjectName("Card")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("14.8 / 14.9 / 14.10 结果、消息与提示", page)
        title.setObjectName("SectionTitle")
        hint = QLabel("结果采用工程文字说明与分项状态展示，适合非程序员阅读。", page)
        hint.setObjectName("SectionHint")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        summary_card = QFrame(page)
        summary_card.setObjectName("SubCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(6)

        self.result_title = QLabel("尚未执行计算", summary_card)
        self.result_title.setObjectName("SubSectionTitle")
        self.result_summary = QLabel("填写参数并点击“执行校核”后，这里显示可读结论。", summary_card)
        self.result_summary.setObjectName("SectionHint")
        self.result_summary.setWordWrap(True)
        summary_layout.addWidget(self.result_title)
        summary_layout.addWidget(self.result_summary)
        layout.addWidget(summary_card)

        checks_card = QFrame(page)
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
            checks_layout.addWidget(name, row, 0)
            checks_layout.addWidget(status, row, 1)
            self._check_badges[key] = status
            row += 1
        layout.addWidget(checks_card)

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

        msg_card = QFrame(page)
        msg_card.setObjectName("SubCard")
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setContentsMargins(12, 10, 12, 10)
        msg_layout.setSpacing(6)
        msg_title = QLabel("消息与建议", msg_card)
        msg_title.setObjectName("SubSectionTitle")
        self.message_box = QPlainTextEdit(msg_card)
        self.message_box.setReadOnly(True)
        self.message_box.setMaximumHeight(170)
        msg_layout.addWidget(msg_title)
        msg_layout.addWidget(self.message_box)
        layout.addWidget(msg_card)

        layout.addStretch(1)
        self.chapter_stack.addWidget(page)

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

    def _set_badge(self, label: QLabel, text: str, is_pass: bool) -> None:
        label.setText(text)
        label.setObjectName("PassBadge" if is_pass else "FailBadge")
        label.style().unpolish(label)
        label.style().polish(label)

    def _load_sample(self, filename: str) -> None:
        sample_path = EXAMPLES_DIR / filename
        if not sample_path.exists():
            QMessageBox.warning(self, "样例不存在", f"未找到样例文件: {sample_path}")
            return
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        self._apply_defaults()
        for spec in self._field_specs.values():
            if spec.mapping is None:
                continue
            sec, key = spec.mapping
            if sec not in data or key not in data[sec]:
                continue
            widget = self._field_widgets[spec.field_id]
            value = str(data[sec][key])
            if spec.widget_type == "choice":
                idx = widget.findText(value)  # type: ignore[attr-defined]
                if idx >= 0:
                    widget.setCurrentIndex(idx)  # type: ignore[attr-defined]
            else:
                widget.setText(value)  # type: ignore[attr-defined]

        fa_val = data.get("loads", {}).get("FA_max", 0)
        fq_val = data.get("loads", {}).get("FQ_max", 0)
        case_widget = self._field_widgets.get("operating.setup_case")
        if isinstance(case_widget, QComboBox):
            if fa_val > 0 and fq_val > 0:
                case_widget.setCurrentText("轴向+横向")
            elif fa_val > 0:
                case_widget.setCurrentText("轴向载荷")
            elif fq_val > 0:
                case_widget.setCurrentText("横向载荷")

        self.info_label.setText(f"已加载样例：{filename}。可直接切换章节核对参数。")

    def _clear(self) -> None:
        self._apply_defaults()
        self._last_payload = None
        self._last_result = None
        self.result_title.setText("尚未执行计算")
        self.result_summary.setText("填写参数并点击“执行校核”后，这里显示可读结论。")
        self.metrics_text.setText("尚无结果。")
        self.message_box.clear()
        for badge in self._check_badges.values():
            self._set_badge(badge, "待计算", False)
        self.overall_badge.setText("等待计算")
        self.overall_badge.setObjectName("WaitBadge")
        self.overall_badge.style().unpolish(self.overall_badge)
        self.overall_badge.style().polish(self.overall_badge)
        self.diagram_widget.set_forces(0.0, 0.0, 0.0)
        self.info_label.setText("参数已重置为默认值。")

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
            if not raw:
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
            result = calculate_vdi2230_core(payload)
        except InputError as exc:
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        self._last_payload = payload
        self._last_result = result
        self._render_result(payload, result)
        # Jump to result chapter after run.
        self.chapter_list.setCurrentRow(self.chapter_stack.count() - 1)

    def _render_result(self, payload: dict[str, Any], result: dict[str, Any]) -> None:
        overall = bool(result.get("overall_pass"))
        checks = result.get("checks", {})

        title = "校核通过" if overall else "校核不通过"
        summary = (
            "该工况满足当前模型下全部分项要求。"
            if overall
            else "该工况存在未满足项，请查看下方分项状态与调整建议。"
        )
        self.result_title.setText(title)
        self.result_summary.setText(summary)
        self._set_badge(self.overall_badge, "总体通过" if overall else "总体不通过", overall)

        for key, badge in self._check_badges.items():
            is_pass = bool(checks.get(key, False))
            self._set_badge(badge, "通过" if is_pass else "不通过", is_pass)

        inter = result["intermediate"]
        torque = result["torque"]
        force = result["forces"]
        stresses = result["stresses_mpa"]
        fa_max = payload.get("loads", {}).get("FA_max", 0.0)

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
            f"• 服役轴向应力: {stresses['sigma_ax_work']:.1f} MPa  /  允许 {stresses['sigma_allow_work']:.1f} MPa"
            f"  [{_ratio(stresses['sigma_ax_work'], stresses['sigma_allow_work'])}]",
            f"• 附加载荷参考: FA,max = {fa_max:.1f} N  /  参考上限 {force['FA_perm_N']:.1f} N  (⚠ 参考估算，非 VDI 标准项)",
        ]
        self.metrics_text.setText("\n".join(metric_lines))

        messages = []
        for warning in result.get("warnings", []):
            messages.append(f"[警告] {warning}")
        messages.extend(self._build_recommendations(result))
        messages.append("[说明] 本版本校核范围：装配强度(R4)、服役强度(R5)、残余夹紧力(R3)。"
                        "支承面压强、螺纹脱扣、疲劳校核等尚未覆盖。")
        self.message_box.setPlainText("\n".join(messages))

        self.diagram_widget.set_forces(inter["FMmin_N"], fa_max, force["F_K_residual_N"])

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
        if not checks.get("additional_load_ok", True):
            recs.append("[建议] 附加载荷超限：可提高 As、降低 n 或减少轴向外载。")
        if not recs:
            recs.append("[建议] 当前工况满足全部校核。建议保留 10% 以上工程裕量。")
        return recs

    def _save_report(self) -> None:
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行校核计算。")
            return

        default_path = EXAMPLES_DIR / "bolt_check_report.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出结果说明",
            str(default_path),
            "Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return

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
                "关键结果:",
                f"- FMmin: {inter['FMmin_N']:.2f} N",
                f"- FMmax: {inter['FMmax_N']:.2f} N",
                f"- MAmin: {torque['MA_min_Nm']:.3f} N·m",
                f"- MAmax: {torque['MA_max_Nm']:.3f} N·m",
                f"- FK_residual: {forces['F_K_residual_N']:.2f} N",
                f"- FK_required: {inter['F_K_required_N']:.2f} N",
                f"- FA_perm: {forces['FA_perm_N']:.2f} N",
                f"- sigma_vm_assembly: {stresses['sigma_vm_assembly']:.2f} MPa",
                f"- sigma_ax_work: {stresses['sigma_ax_work']:.2f} MPa",
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

        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        self.info_label.setText(f"结果说明已导出: {out_path}")

