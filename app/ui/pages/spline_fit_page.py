"""Spline interference-fit module page with chapter-style workflow."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.pages.base_chapter_page import BaseChapterPage
from core.spline.calculator import InputError, calculate_spline_fit


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

MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "45钢": {"e_mpa": 210000.0, "nu": 0.30},
    "40Cr": {"e_mpa": 210000.0, "nu": 0.29},
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29},
    "自定义": None,
}

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

CHAPTERS: list[dict[str, Any]] = [
    {
        "title": "校核目标",
        "subtitle": "选择校核模式、安全系数与工况系数。",
        "fields": [
            FieldSpec(
                "mode", "校核模式", "-",
                "仅花键：只校核齿面承压；联合：同时校核光滑段圆柱过盈。",
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
                "同时放大场景 A 和场景 B 的设计载荷。",
                mapping=("loads", "application_factor_ka"),
                default="1.25", placeholder="建议 1.0~2.25",
            ),
        ],
    },
    {
        "title": "花键几何",
        "subtitle": "渐开线花键 (DIN 5480) 参数，alpha=30 deg 固定。",
        "fields": [
            FieldSpec(
                "spline.module_mm", "模数 m", "mm",
                "渐开线花键模数。",
                mapping=("spline", "module_mm"),
                default="2.0", placeholder="例如 1.25, 2.0",
            ),
            FieldSpec(
                "spline.tooth_count", "齿数 z", "-",
                "花键齿数，最小 6。",
                mapping=("spline", "tooth_count"),
                default="20", placeholder="例如 20, 30",
            ),
            FieldSpec(
                "spline.engagement_length_mm", "有效啮合长度 L", "mm",
                "花键齿面轴向有效接触长度。",
                mapping=("spline", "engagement_length_mm"),
                default="30.0", placeholder="例如 30",
            ),
            FieldSpec(
                "spline.k_alpha", "载荷分布系数 K_alpha", "-",
                "过盈配合取 1.0~1.2；间隙配合取 1.5~2.0。",
                mapping=("spline", "k_alpha"),
                default="1.0", placeholder="过盈配合建议 1.0",
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
                "花键到光滑段过渡处退刀槽宽度，自动从配合长度中扣除。",
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
        "subtitle": "场景 A（齿面承压）+ 场景 B（光滑段过盈）独立校核结果。",
        "fields": [],
    },
]

MODE_MAP: dict[str, str] = {"仅花键": "spline_only", "联合": "combined"}


class SplineFitPage(BaseChapterPage):
    """Spline interference-fit page with chapter navigation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "花键过盈配合",
            "渐开线花键 (DIN 5480) 齿面承压 + 光滑段圆柱过盈 (DIN 7190)",
            parent,
        )

        self._widgets: dict[str, QWidget] = {}
        self._field_cards: dict[str, QWidget] = {}
        self._result_labels: dict[str, QLabel] = {}

        calc_btn = self.add_action_button("计算", primary=True)
        calc_btn.clicked.connect(self._on_calculate)

        for chapter in CHAPTERS:
            page = self._build_chapter_page(chapter)
            self.add_chapter(chapter["title"], page)

        self.set_current_chapter(0)

        mode_combo = self._widgets.get("mode")
        if isinstance(mode_combo, QComboBox):
            mode_combo.currentTextChanged.connect(self._on_mode_changed)
            self._on_mode_changed(mode_combo.currentText())

        # Connect load condition to auto-fill p_zul
        lc_combo = self._widgets.get("spline.load_condition")
        if isinstance(lc_combo, QComboBox):
            lc_combo.currentTextChanged.connect(self._on_load_condition_changed)

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
        for scenario, title in [("a", "场景 A - 齿面承压"), ("b", "场景 B - 光滑段过盈")]:
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

    def _on_mode_changed(self, text: str) -> None:
        is_combined = (text == "联合")
        for fid in SMOOTH_FIT_FIELD_IDS:
            card = self._field_cards.get(fid)
            if card:
                card.setVisible(is_combined)
        for fid in ("checks.slip_safety_min", "checks.stress_safety_min"):
            card = self._field_cards.get(fid)
            if card:
                card.setVisible(is_combined)

    def _on_load_condition_changed(self, text: str) -> None:
        p_zul = LOAD_CONDITION_P_ZUL.get(text)
        if p_zul is not None:
            w = self._widgets.get("spline.p_allowable_mpa")
            if isinstance(w, QLineEdit):
                w.setText(str(p_zul))

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
                try:
                    payload[section][key] = float(raw)
                except ValueError:
                    payload[section][key] = raw
        return payload

    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_spline_fit(payload)
        except (InputError, Exception) as exc:
            self.set_overall_status(f"输入错误: {exc}", "fail")
            self.set_info(str(exc))
            return

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
            f"齿面压力 p = {a['flank_pressure_mpa']:.1f} MPa, "
            f"许用 p_zul = {a['p_allowable_mpa']:.0f} MPa, "
            f"安全系数 S = {a['flank_safety']:.2f}"
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
        else:
            b_badge.setText("未启用")
            b_badge.setObjectName("WaitBadge")
            b_badge.style().unpolish(b_badge)
            b_badge.style().polish(b_badge)
            b_detail.setText("仅花键模式，光滑段过盈校核已跳过。")

        if result["overall_pass"]:
            self.set_overall_status("ALL PASS", "pass")
        else:
            self.set_overall_status("FAIL", "fail")

        msgs = result.get("messages", [])
        self.set_info("\n".join(msgs) if msgs else "校核完成。")
