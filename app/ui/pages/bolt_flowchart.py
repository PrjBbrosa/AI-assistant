"""VDI 2230 校核链路流程图导航和 R 步骤详情页。"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)


R_STEPS: list[dict[str, Any]] = [
    {"id": "r0", "title": "R0 输入汇总",  "has_check": False,
     "summary_key": "r0_summary"},
    {"id": "r1", "title": "R1 预紧力",    "has_check": False,
     "summary_key": "r1_summary"},
    {"id": "r2", "title": "R2 扭矩",      "has_check": False,
     "summary_key": "r2_summary"},
    {"id": "r3", "title": "R3 残余夹紧",  "has_check": True,
     "check_key": "residual_clamp_ok", "summary_key": "r3_summary"},
    {"id": "r4", "title": "R4 装配应力",  "has_check": True,
     "check_key": "assembly_von_mises_ok", "summary_key": "r4_summary"},
    {"id": "r5", "title": "R5 服役应力",  "has_check": True,
     "check_key": "operating_axial_ok", "summary_key": "r5_summary"},
    {"id": "r6", "title": "R6 疲劳",      "has_check": True,
     "check_key": "fatigue_ok", "visibility": "fatigue",
     "summary_key": "r6_summary"},
    {"id": "r7", "title": "R7 支承面",    "has_check": True,
     "check_key": "bearing_pressure_ok", "summary_key": "r7_summary"},
]


R_STEP_FIELDS: dict[str, list[str]] = {
    "r0": ["fastener.d", "fastener.p", "fastener.As", "fastener.d2",
            "fastener.d3", "fastener.Rp02",
            "tightening.mu_thread", "tightening.mu_bearing",
            "stiffness.bolt_compliance", "stiffness.bolt_stiffness",
            "stiffness.clamped_compliance", "stiffness.clamped_stiffness",
            "stiffness.load_introduction_factor_n",
            "loads.FA_max", "loads.FQ_max",
            "tightening.alpha_A", "tightening.utilization",
            "options.calculation_mode", "options.check_level"],
    "r1": ["loads.seal_force_required", "loads.FQ_max",
            "loads.slip_friction_coefficient", "loads.friction_interfaces",
            "loads.FA_max", "intermediate.phi_n",
            "loads.embed_loss", "loads.thermal_force_loss"],
    "r2": ["fastener.d2", "fastener.p",
            "tightening.mu_thread", "tightening.mu_bearing",
            "bearing.bearing_d_inner", "bearing.bearing_d_outer",
            "tightening.prevailing_torque"],
    "r3": ["intermediate.FM_min", "loads.embed_loss",
            "loads.thermal_force_loss", "intermediate.phi_n",
            "loads.FA_max", "intermediate.FK_req"],
    "r4": ["intermediate.FM_max", "fastener.As", "fastener.d3",
            "tightening.utilization", "fastener.Rp02"],
    "r5": ["intermediate.FM_max", "intermediate.phi_n", "loads.FA_max",
            "fastener.As", "fastener.Rp02", "checks.yield_safety_operating"],
    "r6": ["intermediate.phi_n", "loads.FA_max", "fastener.As",
            "intermediate.FM_max", "fastener.Rp02", "operating.load_cycles"],
    "r7": ["intermediate.FM_max", "bearing.bearing_d_inner",
            "bearing.bearing_d_outer", "bearing.p_G_allow"],
}


class FlowNodeWidget(QFrame):
    """流程图中的单个校核步骤节点。"""
    clicked = Signal(int)

    def __init__(self, index: int, step: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self._index = index
        self._step = step
        self.setObjectName("SubCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        self.title_label = QLabel(step["title"], self)
        self.title_label.setObjectName("SubSectionTitle")
        top_row.addWidget(self.title_label)
        top_row.addStretch(1)

        self.badge = QLabel("—", self)
        self.badge.setObjectName("WaitBadge")
        if step["has_check"]:
            top_row.addWidget(self.badge)
        layout.addLayout(top_row)

        self.summary_label = QLabel("—", self)
        self.summary_label.setObjectName("SectionHint")
        layout.addWidget(self.summary_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self._index)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().polish(self)


class FlowchartNavWidget(QWidget):
    """左侧校核链路流程图导航。"""
    node_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._nodes: list[FlowNodeWidget] = []
        self._arrows_for_index: dict[int, QLabel] = {}
        self._selected_index = 0

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll)
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(0)

        for i, step in enumerate(R_STEPS):
            if i > 0:
                arrow = QLabel("↓", container)
                arrow.setObjectName("SectionHint")
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._layout.addWidget(arrow)
                self._arrows_for_index[i] = arrow

            node = FlowNodeWidget(i, step, container)
            node.clicked.connect(self._on_node_clicked)
            self._layout.addWidget(node)
            self._nodes.append(node)

        self._layout.addStretch(1)
        scroll.setWidget(container)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        self._nodes[0].set_selected(True)

    def _on_node_clicked(self, index: int) -> None:
        for i, n in enumerate(self._nodes):
            n.set_selected(i == index)
        self._selected_index = index
        self.node_clicked.emit(index)

    def update_from_result(self, result: dict[str, Any]) -> None:
        """计算后更新所有节点的摘要值和 Badge。"""
        checks = result.get("checks", {})
        calc_mode = result.get("calculation_mode", "design")
        inter = result.get("intermediate", {})
        torque = result.get("torque", {})
        stresses = result.get("stresses_mpa", {})
        forces = result.get("forces", {})
        fatigue = result.get("fatigue", {})

        summaries = {
            0: f"φ={inter.get('phi', 0):.4f}  φn={inter.get('phi_n', 0):.4f}",
            1: f"FM_min={inter.get('FMmin_N', 0):,.0f} N  FM_max={inter.get('FMmax_N', 0):,.0f} N",
            2: f"MA={torque.get('MA_min_Nm', 0):.1f}~{torque.get('MA_max_Nm', 0):.1f} N·m",
            3: f"FK_res={forces.get('F_K_residual_N', 0):,.0f} N  FK_req={inter.get('F_K_required_N', 0):,.0f} N",
            4: f"σ_vm={stresses.get('sigma_vm_assembly', 0):.0f} ≤ {stresses.get('sigma_allow_assembly', 0):.0f} MPa",
            5: f"σ_ax={stresses.get('sigma_ax_work', 0):.0f} ≤ {stresses.get('sigma_allow_work', 0):.0f} MPa",
            6: f"σ_a={fatigue.get('sigma_a', 0):.1f} ≤ {fatigue.get('sigma_a_allow', 0):.1f} MPa",
            7: f"p_B={stresses.get('p_bearing', 0):.0f} ≤ {stresses.get('p_G_allow', 0):.0f} MPa"
               if "p_bearing" in stresses else "未设置许用压强",
        }

        for i, node in enumerate(self._nodes):
            node.summary_label.setText(summaries.get(i, "—"))
            step = R_STEPS[i]
            if not step["has_check"]:
                continue
            check_key = step["check_key"]
            if check_key == "residual_clamp_ok" and calc_mode == "design":
                node.badge.setObjectName("PassBadge")
                node.badge.setText("通过（自动满足）")
            elif check_key not in checks:
                node.badge.setObjectName("WaitBadge")
                node.badge.setText("已跳过")
            elif checks[check_key]:
                node.badge.setObjectName("PassBadge")
                node.badge.setText("通过")
            else:
                node.badge.setObjectName("FailBadge")
                node.badge.setText("不通过")
            node.badge.style().polish(node.badge)

    def set_r6_visible(self, visible: bool) -> None:
        """根据校核层级控制 R6 疲劳节点可见性。"""
        r6_index = 6
        self._nodes[r6_index].setVisible(visible)
        if r6_index in self._arrows_for_index:
            self._arrows_for_index[r6_index].setVisible(visible)


# 中间值字段的显示名称和单位映射
_INTERMEDIATE_LABELS: dict[str, tuple[str, str]] = {
    "intermediate.phi_n": ("φn (载荷导入系数)", "-"),
    "intermediate.FM_min": ("FM,min (最小预紧力)", "N"),
    "intermediate.FM_max": ("FM,max (最大预紧力)", "N"),
    "intermediate.FK_req": ("FK,req (所需夹紧力)", "N"),
}

_INTER_KEY_MAP: dict[str, str] = {
    "intermediate.phi_n": "phi_n",
    "intermediate.FM_min": "FMmin_N",
    "intermediate.FM_max": "FMmax_N",
    "intermediate.FK_req": "F_K_required_N",
}


class RStepDetailPage(QFrame):
    """R 步骤详情页：输入回显 + 计算过程 + 校核结论。"""

    def __init__(self, step: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self._step = step
        self.setObjectName("Card")

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(14, 12, 14, 12)
        page_layout.setSpacing(10)

        title = QLabel(step["title"], self)
        title.setObjectName("SectionTitle")
        page_layout.addWidget(title)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget(scroll)
        self._content_layout = QVBoxLayout(container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)

        # 区块 1：输入回显
        self._input_card = QFrame(container)
        self._input_card.setObjectName("SubCard")
        self._input_layout = QGridLayout(self._input_card)
        self._input_layout.setContentsMargins(12, 10, 12, 10)
        self._input_layout.setHorizontalSpacing(16)
        self._input_layout.setVerticalSpacing(6)
        self._input_labels: dict[str, QLabel] = {}
        self._content_layout.addWidget(self._input_card)

        hint = QLabel("切换到「输入步骤」可修改参数", container)
        hint.setObjectName("SectionHint")
        self._content_layout.addWidget(hint)

        # 区块 2：计算过程
        self._calc_card = QFrame(container)
        self._calc_card.setObjectName("SubCard")
        calc_layout = QVBoxLayout(self._calc_card)
        calc_layout.setContentsMargins(12, 10, 12, 10)
        calc_title = QLabel("计算过程", self._calc_card)
        calc_title.setObjectName("SubSectionTitle")
        calc_layout.addWidget(calc_title)
        self._calc_text = QLabel("—", self._calc_card)
        self._calc_text.setObjectName("SectionHint")
        self._calc_text.setWordWrap(True)
        self._calc_text.setStyleSheet(
            'font-family: "Menlo", "Consolas", "Courier New", monospace; font-size: 12px;'
        )
        calc_layout.addWidget(self._calc_text)
        self._content_layout.addWidget(self._calc_card)

        # 区块 3：校核结论
        if step["has_check"]:
            self._result_card = QFrame(container)
            self._result_card.setObjectName("SubCard")
            result_layout = QHBoxLayout(self._result_card)
            result_layout.setContentsMargins(12, 10, 12, 10)
            result_title = QLabel("校核结论", self._result_card)
            result_title.setObjectName("SubSectionTitle")
            result_layout.addWidget(result_title)
            self._result_badge = QLabel("等待计算", self._result_card)
            self._result_badge.setObjectName("WaitBadge")
            result_layout.addWidget(self._result_badge)
            result_layout.addStretch(1)
            self._content_layout.addWidget(self._result_card)

        self._content_layout.addStretch(1)
        scroll.setWidget(container)
        page_layout.addWidget(scroll, 1)

    def build_input_echo(self, field_specs: dict[str, Any],
                         field_widgets: dict[str, Any],
                         result: dict[str, Any] | None = None) -> None:
        """构建输入回显区。"""
        step_id = self._step["id"]
        field_ids = R_STEP_FIELDS.get(step_id, [])
        row = 0
        inter = (result or {}).get("intermediate", {})
        for fid in field_ids:
            if fid.startswith("intermediate."):
                label_text, unit = _INTERMEDIATE_LABELS.get(fid, (fid, ""))
                name_label = QLabel(label_text, self._input_card)
                name_label.setObjectName("SubSectionTitle")
                val = inter.get(_INTER_KEY_MAP.get(fid, ""), 0)
                value_text = f"{val:,.2f}" if val else "—"
                val_label = QLabel(value_text, self._input_card)
                val_label.setObjectName("SectionHint")
                unit_label = QLabel(unit, self._input_card)
                unit_label.setObjectName("UnitLabel")
                self._input_layout.addWidget(name_label, row, 0)
                self._input_layout.addWidget(val_label, row, 1)
                self._input_layout.addWidget(unit_label, row, 2)
                self._input_labels[fid] = val_label
                row += 1
                continue
            spec = field_specs.get(fid)
            widget = field_widgets.get(fid)
            if not spec:
                continue
            name_label = QLabel(spec.label, self._input_card)
            name_label.setObjectName("SubSectionTitle")
            value_text = "—"
            if widget:
                if isinstance(widget, QLineEdit):
                    value_text = widget.text() or "—"
                elif isinstance(widget, QComboBox):
                    value_text = widget.currentText() or "—"
            val_label = QLabel(value_text, self._input_card)
            val_label.setObjectName("SectionHint")
            unit_label = QLabel(spec.unit if spec.unit != "-" else "", self._input_card)
            unit_label.setObjectName("UnitLabel")
            self._input_layout.addWidget(name_label, row, 0)
            self._input_layout.addWidget(val_label, row, 1)
            self._input_layout.addWidget(unit_label, row, 2)
            self._input_labels[fid] = val_label
            row += 1

    def update_from_result(self, result: dict[str, Any],
                           field_widgets: dict[str, Any]) -> None:
        """计算后刷新回显值、计算过程文本和校核结论。"""
        for fid, label in self._input_labels.items():
            if fid.startswith("intermediate."):
                inter = result.get("intermediate", {})
                val = inter.get(_INTER_KEY_MAP.get(fid, ""), 0)
                label.setText(f"{val:,.2f}" if val else "—")
                continue
            widget = field_widgets.get(fid)
            if widget:
                if isinstance(widget, QLineEdit):
                    label.setText(widget.text() or "—")
                elif isinstance(widget, QComboBox):
                    label.setText(widget.currentText() or "—")

        calc_text = self._format_calc_text(result)
        self._calc_text.setText(calc_text)

        if self._step["has_check"]:
            self._update_badge(result)

    def _format_calc_text(self, result: dict[str, Any]) -> str:
        step_id = self._step["id"]
        inter = result.get("intermediate", {})
        torque = result.get("torque", {})
        stresses = result.get("stresses_mpa", {})
        forces = result.get("forces", {})
        fatigue = result.get("fatigue", {})

        if step_id == "r0":
            return (
                f"As = {result.get('derived_geometry_mm', {}).get('As', 0):.2f} mm²\n"
                f"d2 = {result.get('derived_geometry_mm', {}).get('d2', 0):.3f} mm\n"
                f"d3 = {result.get('derived_geometry_mm', {}).get('d3', 0):.3f} mm\n"
                f"φ  = δp/(δs+δp) = {inter.get('phi', 0):.4f}\n"
                f"φn = n × φ = {inter.get('phi_n', 0):.4f}"
            )
        if step_id == "r1":
            return (
                f"FK,slip = FQ/(μT×qF) = {inter.get('F_slip_required_N', 0):,.0f} N\n"
                f"FK,req  = max(FK,seal, FK,slip) = {inter.get('F_K_required_N', 0):,.0f} N\n"
                f"FM,min  = FK,req + (1-φn)×FA + FZ + Fth\n"
                f"        = {inter.get('FMmin_N', 0):,.0f} N\n"
                f"FM,max  = αA × FM,min = {inter.get('FMmax_N', 0):,.0f} N"
            )
        if step_id == "r2":
            return (
                f"导程角 λ = {inter.get('lead_angle_deg', 0):.2f}°\n"
                f"摩擦角 ρ' = {inter.get('friction_angle_deg', 0):.2f}°\n"
                f"MA,min = {torque.get('MA_min_Nm', 0):.2f} N·m\n"
                f"MA,max = {torque.get('MA_max_Nm', 0):.2f} N·m"
            )
        if step_id == "r3":
            return (
                f"FK,res = FM,min - FZ - Fth - (1-φn)×FA\n"
                f"       = {forces.get('F_K_residual_N', 0):,.0f} N\n"
                f"FK,req = {inter.get('F_K_required_N', 0):,.0f} N\n"
                f"判据: FK,res ≥ FK,req"
            )
        if step_id == "r4":
            return (
                f"σ_ax   = FM,max/As = {stresses.get('sigma_ax_assembly', 0):.1f} MPa\n"
                f"τ      = 16×M_thread/(π×d3³) = {stresses.get('tau_assembly', 0):.1f} MPa\n"
                f"σ_vm   = √(σ²+3τ²) = {stresses.get('sigma_vm_assembly', 0):.1f} MPa\n"
                f"σ_allow = ν×Rp0.2 = {stresses.get('sigma_allow_assembly', 0):.1f} MPa\n"
                f"判据: σ_vm ≤ σ_allow"
            )
        if step_id == "r5":
            return (
                f"F_bolt_max = FM,max + φn×FA = {forces.get('F_bolt_work_max_N', 0):,.0f} N\n"
                f"σ_ax_work  = F_bolt_max/As = {stresses.get('sigma_ax_work', 0):.1f} MPa\n"
                f"σ_allow    = Rp0.2/SF = {stresses.get('sigma_allow_work', 0):.1f} MPa\n"
                f"判据: σ_ax ≤ σ_allow"
            )
        if step_id == "r6":
            return (
                f"σ_a      = φn×FA/(2×As) = {fatigue.get('sigma_a', 0):.2f} MPa\n"
                f"σ_m      = (FM,max+0.5×φn×FA)/As = {fatigue.get('sigma_m', 0):.1f} MPa\n"
                f"σ_a_allow = {fatigue.get('sigma_a_allow', 0):.2f} MPa\n"
                f"判据: σ_a ≤ σ_a_allow（简化 Goodman）"
            )
        if step_id == "r7":
            if "p_bearing" not in stresses:
                return "未设置许用压强 p_G_allow，R7 已跳过。"
            return (
                f"A_bearing = π/4×(DKo²-DKi²) = {stresses.get('A_bearing_mm2', 0):.1f} mm²\n"
                f"p_B       = FM,max/A_bearing = {stresses.get('p_bearing', 0):.1f} MPa\n"
                f"p_allow   = {stresses.get('p_G_allow', 0):.0f} MPa\n"
                f"判据: p_B ≤ p_allow"
            )
        return "—"

    def _update_badge(self, result: dict[str, Any]) -> None:
        checks = result.get("checks", {})
        calc_mode = result.get("calculation_mode", "design")
        check_key = self._step["check_key"]

        if check_key == "residual_clamp_ok" and calc_mode == "design":
            self._result_badge.setObjectName("PassBadge")
            self._result_badge.setText("通过（设计模式自动满足）")
        elif check_key not in checks:
            self._result_badge.setObjectName("WaitBadge")
            self._result_badge.setText("已跳过")
        elif checks[check_key]:
            self._result_badge.setObjectName("PassBadge")
            self._result_badge.setText("通过")
        else:
            self._result_badge.setObjectName("FailBadge")
            self._result_badge.setText("不通过")
        self._result_badge.style().polish(self._result_badge)
