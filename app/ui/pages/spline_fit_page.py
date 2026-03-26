"""Spline interference-fit module page with chapter-style workflow."""

from __future__ import annotations

import datetime as dt
import importlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.base_chapter_page import BaseChapterPage
from app.ui.widgets.press_force_curve import PressForceCurveWidget
from core.spline.calculator import InputError, calculate_spline_fit
from core.spline.din5480_table import all_designations, lookup_by_designation


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


LOAD_CONDITION_OPTIONS: tuple[str, ...] = (
    "固定连接，静载，调质钢",
    "固定连接，静载，渗碳淬火",
    "固定连接，脉动载荷，调质钢",
    "固定连接，脉动载荷，渗碳淬火",
    "自定义",
)
LOAD_CONDITION_P_ZUL: dict[str, float] = {
    "固定连接，静载，调质钢": 100.0,
    "固定连接，静载，渗碳淬火": 150.0,
    "固定连接，脉动载荷，调质钢": 60.0,
    "固定连接，脉动载荷，渗碳淬火": 80.0,
}
GEOMETRY_MODE_OPTIONS: tuple[str, ...] = (
    "公开/图纸尺寸",
    "近似推导（仅预估）",
)
GEOMETRY_MODE_MAP: dict[str, str] = {
    "公开/图纸尺寸": "reference_dimensions",
    "近似推导（仅预估）": "approximate",
}

MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "45钢": {"e_mpa": 210000.0, "nu": 0.30},
    "40Cr": {"e_mpa": 210000.0, "nu": 0.29},
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29},
    "自定义": None,
}

SPLINE_SCOPE_DISCLAIMER = (
    "当前仅提供齿面平均承压的简化预校核，"
    "不替代 DIN 5480（渐开线花键尺寸标准）/ DIN 6892（花键连接承载能力标准）的完整工程校核。"
)

SMOOTH_FIT_FIELD_IDS: list[str] = [
    "smooth_fit.shaft_d_mm", "smooth_fit.shaft_inner_d_mm",
    "smooth_fit.hub_outer_d_mm", "smooth_fit.fit_length_mm",
    "smooth_fit.relief_groove_width_mm",
    "smooth_fit.delta_min_um", "smooth_fit.delta_max_um",
    "smooth_materials.shaft_material", "smooth_materials.shaft_e_mpa",
    "smooth_materials.shaft_nu", "smooth_materials.shaft_yield_mpa",
    "smooth_materials.hub_material", "smooth_materials.hub_e_mpa",
    "smooth_materials.hub_nu", "smooth_materials.hub_yield_mpa",
    "smooth_friction.mu_torque", "smooth_friction.mu_axial",
    "smooth_friction.mu_assembly",
    "smooth_roughness.shaft_rz_um", "smooth_roughness.hub_rz_um",
]

_STANDARD_GEOMETRY_FIELD_IDS: list[str] = [
    "spline.module_mm", "spline.tooth_count", "spline.reference_diameter_mm",
    "spline.tip_diameter_shaft_mm", "spline.root_diameter_shaft_mm",
    "spline.tip_diameter_hub_mm",
]

CHAPTERS: list[dict[str, Any]] = [
    {
        "title": "校核目标",
        "subtitle": "选择校核模式、安全系数与工况系数。",
        "fields": [
            FieldSpec(
                "mode", "校核模式", "-",
                "仅花键：只校核花键齿面承压（场景 A）；联合：同时校核花键轴光滑段与轮毂孔的圆柱过盈配合（场景 B）。",
                widget_type="choice",
                options=("仅花键", "联合"),
                default="联合",
            ),
            FieldSpec(
                "checks.flank_safety_min", "齿面最小安全系数 S_flank,min", "-",
                "场景 A 齿面承压校核使用的最小安全系数。",
                mapping=("checks", "flank_safety_min"),
                default="1.30", placeholder="建议 1.2~1.5",
            ),
            FieldSpec(
                "checks.slip_safety_min", "防滑最小安全系数 S_slip,min", "-",
                "场景 B 光滑段防滑校核使用的最小安全系数。",
                mapping=("checks", "slip_safety_min"),
                default="1.50", placeholder="建议 1.2~2.0",
            ),
            FieldSpec(
                "checks.stress_safety_min", "材料最小安全系数 S_sigma,min", "-",
                "场景 B 轴/轮毂应力校核使用的最小安全系数。",
                mapping=("checks", "stress_safety_min"),
                default="1.20", placeholder="建议 1.1~1.8",
            ),
            FieldSpec(
                "loads.application_factor_ka", "工况系数 KA", "-",
                "考虑驱动/负载特性引起的动态过载，同时放大场景 A 和 B 的设计载荷。电机驱动约 1.0~1.25，内燃机约 1.25~1.75。",
                mapping=("loads", "application_factor_ka"),
                default="1.25", placeholder="建议 1.0~2.25",
            ),
        ],
    },
    {
        "title": "花键几何",
        "subtitle": "渐开线花键 (DIN 5480) 优先使用公开目录/图纸尺寸；近似模式仅用于预估。",
        "fields": [
            FieldSpec(
                "spline.standard_designation", "标准花键规格", "-",
                "选择 DIN 5480 标准规格后自动填充几何尺寸；选'自定义'手动输入。",
                widget_type="choice",
                options=tuple(all_designations()) + ("自定义",),
                default="自定义",
            ),
            FieldSpec(
                "spline.geometry_mode", "几何输入模式", "-",
                "优先使用公开目录、图纸或实测尺寸；近似模式只适合简化预校核。",
                mapping=("spline", "geometry_mode"),
                widget_type="choice",
                options=GEOMETRY_MODE_OPTIONS,
                default="公开/图纸尺寸",
            ),
            FieldSpec(
                "spline.module_mm", "模数 m", "mm",
                "渐开线花键模数。",
                mapping=("spline", "module_mm"),
                default="1.25", placeholder="例如 0.8, 1.25",
            ),
            FieldSpec(
                "spline.tooth_count", "齿数 z", "-",
                "花键齿数，最小 6。",
                mapping=("spline", "tooth_count"),
                default="10", placeholder="例如 10, 16",
            ),
            FieldSpec(
                "spline.reference_diameter_mm", "参考直径 d_B", "mm",
                "DIN 5480 花键的基本尺寸参考直径。例如 '外花键 W 15x1.25x10' 表示 d_B=15mm, m=1.25, z=10。",
                mapping=("spline", "reference_diameter_mm"),
                default="15.0", placeholder="例如 15",
            ),
            FieldSpec(
                "spline.tip_diameter_shaft_mm", "轴齿顶圆 d_a1", "mm",
                "优先使用目录或图纸尺寸。公开样例 W15x1.25x10 约为 14.75 mm。",
                mapping=("spline", "tip_diameter_shaft_mm"),
                default="14.75", placeholder="例如 14.75",
            ),
            FieldSpec(
                "spline.root_diameter_shaft_mm", "轴齿根圆 d_f1", "mm",
                "优先使用目录或图纸尺寸。公开样例 W15x1.25x10 约为 12.1 mm。",
                mapping=("spline", "root_diameter_shaft_mm"),
                default="12.1", placeholder="例如 12.1",
            ),
            FieldSpec(
                "spline.tip_diameter_hub_mm", "内花键齿顶圆 d_a2", "mm",
                "优先使用目录或图纸尺寸。公开样例 N15x1.25x10 约为 12.5 mm。",
                mapping=("spline", "tip_diameter_hub_mm"),
                default="12.5", placeholder="例如 12.5",
            ),
            FieldSpec(
                "spline.engagement_length_mm", "有效啮合长度 L", "mm",
                "花键齿面轴向有效接触长度。",
                mapping=("spline", "engagement_length_mm"),
                default="40.0", placeholder="例如 25, 40",
            ),
            FieldSpec(
                "spline.k_alpha", "载荷分布系数 K_alpha", "-",
                "齿面载荷分布不均匀的修正系数。过盈固定连接约 1.0~1.3，滑移连接约 1.5~2.0。",
                mapping=("spline", "k_alpha"),
                default="1.3", placeholder="例如 1.1~2.0",
            ),
            FieldSpec(
                "spline.load_condition", "载荷工况", "-",
                "选择后自动填充许用齿面压力；切到自定义手工输入。",
                widget_type="choice",
                options=LOAD_CONDITION_OPTIONS,
                default="固定连接，静载，调质钢",
            ),
            FieldSpec(
                "spline.p_allowable_mpa", "许用齿面压力 p_zul", "MPa",
                "取决于材料状态和载荷类型。",
                mapping=("spline", "p_allowable_mpa"),
                default="100.0", placeholder="例如 60~200",
            ),
        ],
    },
    {
        "title": "光滑段过盈",
        "subtitle": "花键轴光滑段压入圆柱孔的 DIN 7190 圆柱过盈参数。仅花键模式下跳过此步。",
        "fields": [
            FieldSpec(
                "smooth_fit.shaft_d_mm", "配合直径 d", "mm",
                "光滑段轴径。",
                mapping=("smooth_fit", "shaft_d_mm"),
                default="40.0", placeholder="例如 40",
            ),
            FieldSpec(
                "smooth_fit.shaft_inner_d_mm", "轴内径 d_i", "mm",
                "0 表示实心轴。",
                mapping=("smooth_fit", "shaft_inner_d_mm"),
                default="0.0", placeholder="实心轴填 0",
            ),
            FieldSpec(
                "smooth_fit.hub_outer_d_mm", "轮毂外径 D", "mm",
                "轮毂外圆直径。",
                mapping=("smooth_fit", "hub_outer_d_mm"),
                default="80.0", placeholder="例如 80",
            ),
            FieldSpec(
                "smooth_fit.fit_length_mm", "名义配合长度 L", "mm",
                "轴向名义接触长度（含退刀槽，计算时自动扣除）。",
                mapping=("smooth_fit", "fit_length_mm"),
                default="45.0", placeholder="例如 45",
            ),
            FieldSpec(
                "smooth_fit.relief_groove_width_mm", "退刀槽宽度", "mm",
                "花键齿根与光滑段之间的让刀凹槽宽度，用于加工退刀。计算时自动从配合长度中扣除。",
                mapping=("smooth_fit", "relief_groove_width_mm"),
                default="3.0", placeholder="例如 2~5",
            ),
            FieldSpec(
                "smooth_fit.delta_min_um", "最小过盈量 delta_min", "um",
                "直径值。", mapping=("smooth_fit", "delta_min_um"),
                default="20.0", placeholder="例如 20",
            ),
            FieldSpec(
                "smooth_fit.delta_max_um", "最大过盈量 delta_max", "um",
                "直径值。", mapping=("smooth_fit", "delta_max_um"),
                default="45.0", placeholder="例如 45",
            ),
            FieldSpec(
                "smooth_materials.shaft_material", "轴材料", "-",
                "选择后自动填充 E 与 nu。",
                widget_type="choice",
                options=tuple(MATERIAL_LIBRARY.keys()),
                default="45钢",
            ),
            FieldSpec(
                "smooth_materials.shaft_e_mpa", "轴弹性模量 E_s", "MPa",
                "", mapping=("smooth_materials", "shaft_e_mpa"),
                default="210000", placeholder="例如 210000",
            ),
            FieldSpec(
                "smooth_materials.shaft_nu", "轴泊松比 nu_s", "-",
                "", mapping=("smooth_materials", "shaft_nu"),
                default="0.30",
            ),
            FieldSpec(
                "smooth_materials.shaft_yield_mpa", "轴屈服强度 Re_s", "MPa",
                "", mapping=("smooth_materials", "shaft_yield_mpa"),
                default="600",
            ),
            FieldSpec(
                "smooth_materials.hub_material", "轮毂材料", "-",
                "",
                widget_type="choice",
                options=tuple(MATERIAL_LIBRARY.keys()),
                default="45钢",
            ),
            FieldSpec(
                "smooth_materials.hub_e_mpa", "轮毂弹性模量 E_h", "MPa",
                "", mapping=("smooth_materials", "hub_e_mpa"),
                default="210000",
            ),
            FieldSpec(
                "smooth_materials.hub_nu", "轮毂泊松比 nu_h", "-",
                "", mapping=("smooth_materials", "hub_nu"),
                default="0.30",
            ),
            FieldSpec(
                "smooth_materials.hub_yield_mpa", "轮毂屈服强度 Re_h", "MPa",
                "", mapping=("smooth_materials", "hub_yield_mpa"),
                default="320",
            ),
            FieldSpec(
                "smooth_friction.mu_torque", "摩擦系数 mu_T（扭矩）", "-",
                "", mapping=("smooth_friction", "mu_torque"),
                default="0.14",
            ),
            FieldSpec(
                "smooth_friction.mu_axial", "摩擦系数 mu_ax（轴向）", "-",
                "", mapping=("smooth_friction", "mu_axial"),
                default="0.14",
            ),
            FieldSpec(
                "smooth_friction.mu_assembly", "装配摩擦系数 mu_M", "-",
                "", mapping=("smooth_friction", "mu_assembly"),
                default="0.12",
            ),
            FieldSpec(
                "smooth_roughness.shaft_rz_um", "轴 Rz", "um",
                "", mapping=("smooth_roughness", "shaft_rz_um"),
                default="6.3",
            ),
            FieldSpec(
                "smooth_roughness.hub_rz_um", "轮毂 Rz", "um",
                "", mapping=("smooth_roughness", "hub_rz_um"),
                default="6.3",
            ),
        ],
    },
    {
        "title": "载荷工况",
        "subtitle": "输入设计扭矩和轴向力（两场景共用）。",
        "fields": [
            FieldSpec(
                "loads.torque_required_nm", "名义扭矩 T", "N*m",
                "两场景共用的名义扭矩。",
                mapping=("loads", "torque_required_nm"),
                default="500.0", placeholder="例如 500",
            ),
            FieldSpec(
                "loads.axial_force_required_n", "轴向力 F_ax", "N",
                "仅场景 B 使用。",
                mapping=("loads", "axial_force_required_n"),
                default="0.0", placeholder="例如 0",
            ),
        ],
    },
    {
        "title": "计算结果",
        "subtitle": "场景 A（简化预校核）+ 场景 B（光滑段过盈）独立校核结果。",
        "fields": [],
    },
]

MODE_MAP: dict[str, str] = {"仅花键": "spline_only", "联合": "combined"}


class SplineFitPage(BaseChapterPage):
    """Spline interference-fit page with chapter navigation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "花键连接校核",
            "花键齿面承压（简化预校核）+ 光滑段圆柱过盈 (DIN 7190)",
            parent,
        )

        self._widgets: dict[str, QWidget] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._result_labels: dict[str, QLabel] = {}

        self._last_result: dict | None = None
        self._last_payload: dict | None = None
        self.curve_widget: PressForceCurveWidget | None = None

        calc_btn = self.add_action_button("计算", primary=True)
        calc_btn.clicked.connect(self._on_calculate)

        export_btn = self.add_action_button("导出报告")
        export_btn.clicked.connect(self._save_report)

        for chapter in CHAPTERS:
            page = self._build_chapter_page(chapter)
            self.add_chapter(chapter["title"], page)

        self.set_current_chapter(0)

        mode_combo = self._widgets.get("mode")
        if isinstance(mode_combo, QComboBox):
            mode_combo.currentTextChanged.connect(self._on_mode_changed)
            self._on_mode_changed(mode_combo.currentText())

        std_combo = self._widgets.get("spline.standard_designation")
        if isinstance(std_combo, QComboBox):
            std_combo.currentTextChanged.connect(self._on_standard_designation_changed)

        # Connect load condition to auto-fill p_zul
        lc_combo = self._widgets.get("spline.load_condition")
        if isinstance(lc_combo, QComboBox):
            lc_combo.currentTextChanged.connect(self._on_load_condition_changed)
            self._on_load_condition_changed(lc_combo.currentText())

        shaft_material_combo = self._widgets.get("smooth_materials.shaft_material")
        if isinstance(shaft_material_combo, QComboBox):
            shaft_material_combo.currentTextChanged.connect(
                lambda text: self._on_material_changed("smooth_materials.shaft", text)
            )
            self._on_material_changed("smooth_materials.shaft", shaft_material_combo.currentText())

        hub_material_combo = self._widgets.get("smooth_materials.hub_material")
        if isinstance(hub_material_combo, QComboBox):
            hub_material_combo.currentTextChanged.connect(
                lambda text: self._on_material_changed("smooth_materials.hub", text)
            )
            self._on_material_changed("smooth_materials.hub", hub_material_combo.currentText())

        self.set_info(SPLINE_SCOPE_DISCLAIMER)

    def _build_chapter_page(self, chapter: dict) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        if chapter["title"] == "计算结果":
            self._build_result_chapter(layout)
        else:
            sub = QLabel(chapter.get("subtitle", ""))
            sub.setObjectName("SectionHint")
            sub.setWordWrap(True)
            layout.addWidget(sub)
            for spec in chapter["fields"]:
                card = self._build_field_card(spec)
                layout.addWidget(card)
                self._field_cards[spec.field_id] = card

        layout.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    def _build_field_card(self, spec: FieldSpec) -> QFrame:
        card = QFrame()
        card.setObjectName("SubCard")
        grid = QGridLayout(card)
        grid.setContentsMargins(8, 6, 8, 6)
        label_text = f"{spec.label} [{spec.unit}]" if spec.unit != "-" else spec.label
        label = QLabel(label_text)
        grid.addWidget(label, 0, 0)

        if spec.widget_type == "choice":
            w = QComboBox()
            w.addItems(spec.options)
            if spec.default:
                idx = w.findText(spec.default)
                if idx >= 0:
                    w.setCurrentIndex(idx)
        else:
            w = QLineEdit()
            w.setText(spec.default)
            w.setPlaceholderText(spec.placeholder)
        grid.addWidget(w, 0, 1)

        if spec.hint:
            hint = QLabel(spec.hint)
            hint.setObjectName("SectionHint")
            hint.setWordWrap(True)
            grid.addWidget(hint, 1, 0, 1, 2)

        self._widgets[spec.field_id] = w
        return card

    def _build_result_chapter(self, layout: QVBoxLayout) -> None:
        disclaimer = QLabel(SPLINE_SCOPE_DISCLAIMER)
        disclaimer.setObjectName("SectionHint")
        disclaimer.setWordWrap(True)
        layout.addWidget(disclaimer)

        for scenario, title in [
            ("a", "场景 A - 花键齿面承压（简化）"),
            ("b", "场景 B - 光滑段圆柱过盈"),
        ]:
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            title_lbl = QLabel(title)
            title_lbl.setObjectName("SectionTitle")
            card_layout.addWidget(title_lbl)
            badge = QLabel("等待计算")
            badge.setObjectName("WaitBadge")
            card_layout.addWidget(badge)
            detail = QLabel("")
            detail.setWordWrap(True)
            card_layout.addWidget(detail)
            self._result_labels[f"{scenario}_badge"] = badge
            self._result_labels[f"{scenario}_detail"] = detail
            layout.addWidget(card)

        self.curve_widget = PressForceCurveWidget()
        self.curve_widget.setVisible(False)
        layout.addWidget(self.curve_widget)

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
        widget = self._widgets.get(field_id)
        if isinstance(widget, QLineEdit):
            widget.setReadOnly(disabled)
        elif isinstance(widget, QComboBox):
            widget.setEnabled(not disabled)

    def _on_mode_changed(self, text: str) -> None:
        is_combined = (text == "联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            self._set_card_disabled(fid, not is_combined)
        for fid in ("checks.slip_safety_min", "checks.stress_safety_min"):
            self._set_card_disabled(fid, not is_combined)
        # 模式切换后重新触发材料联动以刷新 AutoCalcCard 样式
        if is_combined:
            shaft_mat = self._widgets.get("smooth_materials.shaft_material")
            if isinstance(shaft_mat, QComboBox):
                self._on_material_changed("smooth_materials.shaft", shaft_mat.currentText())
            hub_mat = self._widgets.get("smooth_materials.hub_material")
            if isinstance(hub_mat, QComboBox):
                self._on_material_changed("smooth_materials.hub", hub_mat.currentText())
        if self.curve_widget is not None:
            self.curve_widget.setVisible(False)

    def _on_standard_designation_changed(self, text: str) -> None:
        is_standard = (text != "自定义")
        if is_standard:
            record = lookup_by_designation(text)
            if record is None:
                return
            field_map = {
                "spline.module_mm": str(record["module_mm"]),
                "spline.tooth_count": str(record["tooth_count"]),
                "spline.reference_diameter_mm": str(record["reference_diameter_mm"]),
                "spline.tip_diameter_shaft_mm": str(record["tip_diameter_shaft_mm"]),
                "spline.root_diameter_shaft_mm": str(record["root_diameter_shaft_mm"]),
                "spline.tip_diameter_hub_mm": str(record["tip_diameter_hub_mm"]),
            }
            for fid, value in field_map.items():
                w = self._widgets.get(fid)
                if isinstance(w, QLineEdit):
                    w.setText(value)
            # 切换 geometry_mode 到"公开/图纸尺寸"
            geo_combo = self._widgets.get("spline.geometry_mode")
            if isinstance(geo_combo, QComboBox):
                idx = geo_combo.findText("公开/图纸尺寸")
                if idx >= 0:
                    geo_combo.setCurrentIndex(idx)
        # AutoCalcCard 样式
        for fid in _STANDARD_GEOMETRY_FIELD_IDS:
            self._set_card_disabled(fid, is_standard)
        self._set_card_disabled("spline.geometry_mode", is_standard)

    def _on_load_condition_changed(self, text: str) -> None:
        p_zul = LOAD_CONDITION_P_ZUL.get(text)
        if p_zul is not None:
            w = self._widgets.get("spline.p_allowable_mpa")
            if isinstance(w, QLineEdit):
                w.setText(str(p_zul))
            self._set_card_disabled("spline.p_allowable_mpa", True)
        else:
            # "自定义"
            self._set_card_disabled("spline.p_allowable_mpa", False)

    def _on_material_changed(self, field_prefix: str, material_name: str) -> None:
        material = MATERIAL_LIBRARY.get(material_name)
        e_fid = f"{field_prefix}_e_mpa"
        nu_fid = f"{field_prefix}_nu"
        if material is None:
            # "自定义"：恢复可编辑（仅联合模式下生效）
            if MODE_MAP.get(self._get_value("mode")) == "combined":
                self._set_card_disabled(e_fid, False)
                self._set_card_disabled(nu_fid, False)
            return
        # 非自定义：自动填充 + 蓝色样式
        e_widget = self._widgets.get(e_fid)
        nu_widget = self._widgets.get(nu_fid)
        if isinstance(e_widget, QLineEdit):
            e_widget.setText(str(material["e_mpa"]))
        if isinstance(nu_widget, QLineEdit):
            nu_widget.setText(str(material["nu"]))
        self._set_card_disabled(e_fid, True)
        self._set_card_disabled(nu_fid, True)

    def _get_value(self, field_id: str) -> str:
        w = self._widgets.get(field_id)
        if isinstance(w, QComboBox):
            return w.currentText()
        if isinstance(w, QLineEdit):
            return w.text().strip()
        return ""

    def _build_payload(self) -> dict:
        mode_text = self._get_value("mode")
        mode = MODE_MAP.get(mode_text, "spline_only")

        payload: dict[str, Any] = {"mode": mode, "spline": {}, "loads": {}, "checks": {}}
        for chapter in CHAPTERS:
            for spec in chapter["fields"]:
                if spec.mapping is None:
                    continue
                section, key = spec.mapping
                if section not in payload:
                    payload[section] = {}
                raw = self._get_value(spec.field_id)
                if not raw:
                    continue
                if spec.field_id == "spline.geometry_mode":
                    payload[section][key] = GEOMETRY_MODE_MAP.get(raw, "approximate")
                    continue
                try:
                    payload[section][key] = float(raw)
                except ValueError:
                    payload[section][key] = raw
        return payload

    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_spline_fit(payload)
        except InputError as exc:
            self.set_overall_status(f"输入错误: {exc}", "fail")
            self.set_info(str(exc))
            return
        except Exception as exc:
            self.set_overall_status(f"内部错误: {exc}", "fail")
            self.set_info(f"计算过程中出现意外错误，请检查输入或联系开发者。\n{exc}")
            return

        self._last_payload = payload
        self._last_result = result
        self._display_result(result)

    def _display_result(self, result: dict) -> None:
        a = result["scenario_a"]
        a_badge = self._result_labels["a_badge"]
        a_detail = self._result_labels["a_detail"]
        if a["flank_ok"]:
            a_badge.setText("PASS")
            a_badge.setObjectName("PassBadge")
        else:
            a_badge.setText("FAIL")
            a_badge.setObjectName("FailBadge")
        a_badge.style().unpolish(a_badge)
        a_badge.style().polish(a_badge)
        a_detail.setText(
            f"参考直径 d_B = {a['geometry']['reference_diameter_mm']:.2f} mm, "
            f"齿面压力 p = {a['flank_pressure_mpa']:.1f} MPa, "
            f"许用 p_zul = {a['p_allowable_mpa']:.0f} MPa, "
            f"安全系数 S = {a['flank_safety']:.2f}, "
            f"结果级别 = {'简化预校核' if a['overall_verdict_level'] == 'simplified_precheck' else a['overall_verdict_level']}"
        )

        b_badge = self._result_labels["b_badge"]
        b_detail = self._result_labels["b_detail"]
        if "scenario_b" in result:
            b = result["scenario_b"]
            if b["overall_pass"]:
                b_badge.setText("PASS")
                b_badge.setObjectName("PassBadge")
            else:
                b_badge.setText("FAIL")
                b_badge.setObjectName("FailBadge")
            b_badge.style().unpolish(b_badge)
            b_badge.style().polish(b_badge)
            b_detail.setText(
                f"接触压力 p_min = {b['pressure_mpa']['p_min']:.1f} MPa, "
                f"打滑扭矩 T_min = {b['capacity']['torque_min_nm']:.1f} N*m, "
                f"有效长度 = {b['effective_fit_length_mm']:.1f} mm"
            )
            curve = b["press_force_curve"]
            self.curve_widget.set_curve(
                curve["interference_um"],
                curve["force_n"],
                curve["delta_min_um"],
                curve["delta_max_um"],
                curve.get("delta_required_um", 0.0),
            )
            self.curve_widget.setVisible(True)
        else:
            b_badge.setText("未启用")
            b_badge.setObjectName("WaitBadge")
            b_badge.style().unpolish(b_badge)
            b_badge.style().polish(b_badge)
            b_detail.setText("仅花键模式，光滑段过盈校核已跳过。")
            self.curve_widget.setVisible(False)

        if result["overall_pass"]:
            status_text = "PRECHECK PASS" if result.get("overall_verdict_level") == "simplified_precheck" else "ALL PASS"
            self.set_overall_status(status_text, "pass")
        else:
            status_text = "PRECHECK FAIL" if result.get("overall_verdict_level") == "simplified_precheck" else "FAIL"
            self.set_overall_status(status_text, "fail")

        msgs = result.get("messages", [])
        self.set_info("\n".join(msgs) if msgs else "校核完成。")

    def _save_report(self) -> None:
        # Recalculate from current UI inputs to ensure exported data is up-to-date
        self._on_calculate()
        if self._last_result is None or self._last_payload is None:
            QMessageBox.information(self, "无结果", "请先执行计算。")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出校核报告", "spline_report.pdf",
            "PDF Files (*.pdf);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return
        out_path = Path(file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = out_path.suffix.lower()
        if suffix == ".pdf":
            try:
                mod = importlib.import_module("app.ui.report_pdf_spline")
                mod.generate_spline_report(out_path, self._last_payload, self._last_result)
            except Exception as pdf_exc:
                out_path = out_path.with_suffix(".txt")
                out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
                self.set_info(f"PDF 生成失败（{pdf_exc}），已回退为文本格式: {out_path}")
                return
        else:
            out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
        self.set_info(f"报告已导出: {out_path}")

    def _build_report_lines(self) -> list[str]:
        assert self._last_result is not None
        result = self._last_result
        a = result["scenario_a"]
        loads = result.get("loads", {})
        lines = [
            "花键连接校核报告",
            f"生成时间: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"模式: {result.get('mode', 'spline_only')}",
            f"总体结论: {'通过' if result['overall_pass'] else '不通过'}",
            f"结果级别: {result.get('overall_verdict_level', '')}",
            "",
            "=== 场景 A: 花键齿面承压 ===",
            f"参考直径 d_B = {a['geometry']['reference_diameter_mm']:.2f} mm",
            f"有效齿高 h_w = {a['geometry']['effective_tooth_height_mm']:.2f} mm",
            f"平均直径 d_m = {a['geometry']['mean_diameter_mm']:.2f} mm",
            f"齿面压力 p = {a['flank_pressure_mpa']:.2f} MPa",
            f"许用齿面压力 p_zul = {a['p_allowable_mpa']:.1f} MPa",
            f"安全系数 S = {a['flank_safety']:.2f}",
            f"扭矩容量 T_cap = {a['torque_capacity_nm']:.1f} N*m",
            f"设计扭矩 T_d = {loads.get('torque_design_nm', 0):.1f} N*m",
            f"结果: {'通过' if a['flank_ok'] else '不通过'}",
        ]
        b = result.get("scenario_b")
        if b is not None:
            bp = b["pressure_mpa"]
            cap = b["capacity"]
            sf = b["safety"]
            lines.extend([
                "",
                "=== 场景 B: 光滑段圆柱过盈 ===",
                f"有效配合长度 = {b['effective_fit_length_mm']:.1f} mm",
                f"面压 p_min/mean/max = {bp['p_min']:.2f} / {bp['p_mean']:.2f} / {bp['p_max']:.2f} MPa",
                f"扭矩容量 min/mean/max = {cap['torque_min_nm']:.1f} / {cap['torque_mean_nm']:.1f} / {cap['torque_max_nm']:.1f} N*m",
                f"扭矩安全系数 = {sf['torque_sf']:.2f}",
                f"联合安全系数 = {sf['combined_sf']:.2f}",
                f"结果: {'通过' if b['overall_pass'] else '不通过'}",
            ])
        return lines
