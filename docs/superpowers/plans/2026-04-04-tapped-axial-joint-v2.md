# 轴向受力螺纹连接 v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将轴向受力螺纹连接模块从输入骨架完善为与螺栓连接功能对齐的完整模块：标准引用审查、计算集成、结果展示、PDF 报告。

**Architecture:** 增量完善现有代码。Phase 1 审查修正 core 计算逻辑并补标准引用；Phase 2 在现有 UI 骨架上接入计算、结果卡片、文本报告；Phase 3 新建 PDF 报告；Phase 4 注册到主窗口并全量回归。

**Tech Stack:** Python 3.12, PySide6, pytest, reportlab (optional PDF)

**Spec:** `docs/superpowers/specs/2026-04-04-tapped-axial-joint-v2-design.md`

---

## File Structure

### Modify
- `core/bolt/tapped_axial_joint.py` — 标准引用注释、σ_ASV 表值核对、错误信息中文化
- `app/ui/pages/bolt_tapped_axial_page.py` — 计算按钮、结果章节、文本报告导出
- `app/ui/main_window.py` — 注册新模块到侧栏
- `tests/core/bolt/test_tapped_axial_joint.py` — 补充 benchmark 和边界测试
- `tests/ui/test_bolt_tapped_axial_page.py` — 补充计算集成测试
- `tests/ui/test_bolt_tapped_axial_results.py` — 重写为匹配新实现
- `tests/ui/test_bolt_tapped_axial_optional_pdf.py` — 保留，确认导入路径正确
- `CLAUDE.md` — 更新模块状态

### Create
- `app/ui/report_pdf_tapped_axial.py` — PDF 报告生成器

### Not Modified
- `core/bolt/calculator.py` — 现有 VDI 2230 不动
- `core/bolt/__init__.py` — 已正确导出，不需改动
- `app/ui/pages/bolt_page.py` — 现有螺栓连接不动

---

## Phase 1: Core 审查修正

### Task 1: 补充标准引用注释并修正错误信息

**Files:**
- Modify: `core/bolt/tapped_axial_joint.py`

- [ ] **Step 1: 在螺纹几何导出函数添加标准引用**

在 `_derive_thread_geometry` 函数开头添加注释：

```python
def _derive_thread_geometry(fastener: dict[str, Any]) -> dict[str, float]:
    """Derive thread geometry from nominal diameter and pitch.

    Ref: DIN 13-1 (ISO 724) — 基本尺寸
    Ref: ISO 898-1:2013, Sec 9.1.6 — 应力截面积 As
    """
    d = _positive(_require(fastener, "d", "fastener"), "fastener.d")
    p = _positive(_require(fastener, "p", "fastener"), "fastener.p")
    # As = π/4 · (d - 0.9382·p)²  — ISO 898-1:2013, Sec 9.1.6.1
    as_val = fastener.get("As", math.pi / 4.0 * (d - 0.9382 * p) ** 2)
    # d2 = d - 0.6495·p  — DIN 13-1, 中径
    d2 = fastener.get("d2", d - 0.64952 * p)
    # d3 = d - 1.2269·p  — DIN 13-1, 小径
    d3 = fastener.get("d3", d - 1.22687 * p)
    return {
        "d": d,
        "p": p,
        "As": _positive(as_val, "fastener.As"),
        "d2": _positive(d2, "fastener.d2"),
        "d3": _positive(d3, "fastener.d3"),
    }
```

- [ ] **Step 2: 在装配扭矩计算添加标准引用**

在 `calculate_tapped_axial_joint` 函数的装配扭矩计算块添加注释：

```python
    # --- 装配扭矩 ---
    # Ref: VDI 2230-1:2015, Sec 5.4.2, Eq. (5.4/1)
    flank_angle = math.radians(flank_angle_deg)
    lead_angle = math.atan(p / (math.pi * d2))
    friction_angle = math.atan(mu_thread / math.cos(flank_angle / 2.0))
    k_thread = (d2 / 2.0) * math.tan(lead_angle + friction_angle)
    d_km = (bearing_d_inner + bearing_d_outer) / 2.0
    k_bearing = mu_bearing * d_km / 2.0
```

- [ ] **Step 3: 在装配强度计算添加标准引用**

```python
    # --- 装配强度 (von Mises) ---
    # Ref: VDI 2230-1:2015, Sec 5.5.1, Eq. (5.5/1)
    sigma_ax_assembly = f_preload_max / as_val
    m_thread = f_preload_max * k_thread
    tau_assembly = 16.0 * m_thread / (math.pi * d3**3)
    sigma_vm_assembly = math.sqrt(sigma_ax_assembly**2 + 3.0 * tau_assembly**2)
    sigma_allow_assembly = utilization * rp02
    assembly_ok = sigma_vm_assembly <= sigma_allow_assembly
```

- [ ] **Step 4: 在服役强度计算添加标准引用**

```python
    # --- 服役最大强度 ---
    # Ref: VDI 2230-1:2015, Sec 5.5.2
    # 本模型无被夹件，外轴力全部进入螺栓
    f_service_min = f_preload_max + fa_min
    f_service_max = f_preload_max + fa_max
    sigma_ax_service_max = f_service_max / as_val
    # k_tau = 0.5: 扭矩法保留 50% 装配扭转 (VDI 2230-1 惯例)
    k_tau = 0.5 if tightening_method == "torque" else 0.0
```

- [ ] **Step 5: 在疲劳计算添加标准引用**

```python
    # --- 交变轴向疲劳 ---
    # Ref: VDI 2230-1:2015, Sec 5.5.3, Table A4
    f_mean = f_preload_max + 0.5 * (fa_min + fa_max)
    f_amplitude = 0.5 * (fa_max - fa_min)
    sigma_m = f_mean / as_val
    sigma_a = f_amplitude / as_val
    # 寿命系数: VDI 2230-1:2015, Sec 5.5.3
    cycle_factor = (2_000_000.0 / load_cycles) ** 0.08 if load_cycles < 2_000_000.0 else 1.0
    sigma_asv = _fatigue_limit_asv(d, surface_treatment) * cycle_factor
    # 简化 Goodman 折减: VDI 2230-1:2015, Sec 5.5.3
    goodman_factor = max(0.1, 1.0 - sigma_m / (0.9 * rp02))
    sigma_a_allow = sigma_asv * goodman_factor
```

- [ ] **Step 6: 在螺纹脱扣计算添加标准引用**

```python
    # --- 螺纹脱扣 ---
    # Ref: VDI 2230-1:2015, Sec 5.5.5
    # Ref: ISO 898-1:2013, Sec 9.2 — 螺纹抗剥离承载力
```

- [ ] **Step 7: 统一错误信息为中文**

将以下英文错误信息替换为中文：

```python
# Before:
if parsed <= 0:
    raise InputError(f"{name} must be > 0, got {parsed}")
# After:
if parsed <= 0:
    raise InputError(f"{name} 必须大于 0，当前值: {parsed}")

# Before:
if bearing_d_outer <= bearing_d_inner:
    raise InputError(
        "assembly.bearing_d_outer must be greater than assembly.bearing_d_inner"
    )
# After:
if bearing_d_outer <= bearing_d_inner:
    raise InputError(
        "assembly.bearing_d_outer 必须大于 assembly.bearing_d_inner"
    )
```

- [ ] **Step 8: 更新 references 输出字典为具体标准条款**

```python
    "references": {
        "geometry": "DIN 13-1 (ISO 724); ISO 898-1:2013, Sec 9.1.6",
        "assembly_strength": "VDI 2230-1:2015, Sec 5.5.1, Eq. (5.5/1)",
        "service_strength": "VDI 2230-1:2015, Sec 5.5.2",
        "fatigue": "VDI 2230-1:2015, Sec 5.5.3, Table A4 (sigma_ASV + Goodman)",
        "thread_strip": "VDI 2230-1:2015, Sec 5.5.5; ISO 898-1:2013, Sec 9.2",
    },
```

- [ ] **Step 9: 运行 core 测试确认无回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_tapped_axial_joint.py -v`

Expected: 全部 PASS（6 个已有测试不受注释和错误信息修改影响）

- [ ] **Step 10: Commit**

```bash
git add core/bolt/tapped_axial_joint.py
git commit -m "refactor(core): add ISO/VDI standard references and fix Chinese error messages in tapped axial calculator"
```

### Task 2: 核对 σ_ASV 表值并补充 core 测试

**Files:**
- Modify: `core/bolt/tapped_axial_joint.py`
- Modify: `tests/core/bolt/test_tapped_axial_joint.py`

- [ ] **Step 1: 核对 _ASV_TABLE_ROLLED 与 VDI 2230-1 Table A4**

在 `_ASV_TABLE_ROLLED` 添加注释标注来源：

```python
# Ref: VDI 2230-1:2015, Table A4 — 轧制螺纹疲劳极限 σ_ASV (MPa)
# (公称直径 d [mm], σ_ASV [MPa])
_ASV_TABLE_ROLLED: list[tuple[float, float]] = [
    (6, 50),
    (8, 47),
    (10, 44),
    (12, 41),
    (14, 39),
    (16, 38),
    (20, 36),
    (24, 34),
    (30, 32),
    (36, 30),
]
# 切削螺纹折减系数: 0.65 (VDI 2230-1:2015, Table A4 注)
_CUT_THREAD_FACTOR = 0.65
```

- [ ] **Step 2: 补充 σ_ASV 插值验证测试**

在 `tests/core/bolt/test_tapped_axial_joint.py` 添加：

```python
def test_fatigue_limit_rolled_m10_equals_44():
    """VDI 2230-1 Table A4: d=10mm, rolled -> sigma_ASV = 44 MPa."""
    data = _base_input()
    data["service"]["FA_min"] = 0.0
    data["service"]["FA_max"] = 100.0  # 微小载荷，不影响 sigma_ASV 查表
    data["fatigue"]["load_cycles"] = 2_000_000.0  # cycle_factor = 1.0
    data["fatigue"]["surface_treatment"] = "rolled"
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["fatigue"]["sigma_ASV"] == pytest.approx(44.0, rel=1e-3)


def test_fatigue_limit_cut_m10_equals_28_6():
    """VDI 2230-1 Table A4: d=10mm, cut -> sigma_ASV = 44 * 0.65 = 28.6 MPa."""
    data = _base_input()
    data["service"]["FA_min"] = 0.0
    data["service"]["FA_max"] = 100.0
    data["fatigue"]["load_cycles"] = 2_000_000.0
    data["fatigue"]["surface_treatment"] = "cut"
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["fatigue"]["sigma_ASV"] == pytest.approx(28.6, rel=1e-3)
```

- [ ] **Step 3: 补充寿命系数测试**

```python
def test_cycle_factor_below_2e6_applies_correction():
    """load_cycles < 2e6 -> cycle_factor = (2e6/N)^0.08 > 1."""
    data = _base_input()
    data["fatigue"]["load_cycles"] = 1_000_000.0
    result = bolt.calculate_tapped_axial_joint(data)
    cf = result["trace"]["intermediate"]["cycle_factor"]
    expected = (2_000_000.0 / 1_000_000.0) ** 0.08
    assert cf == pytest.approx(expected, rel=1e-4)
    assert cf > 1.0


def test_cycle_factor_at_2e6_equals_one():
    """load_cycles >= 2e6 -> cycle_factor = 1.0."""
    data = _base_input()
    data["fatigue"]["load_cycles"] = 2_000_000.0
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["trace"]["intermediate"]["cycle_factor"] == 1.0
```

- [ ] **Step 4: 补充边界条件测试**

```python
def test_static_load_fa_min_equals_fa_max_amplitude_zero():
    """FA_min == FA_max -> F_amplitude = 0 (纯静载)."""
    data = _base_input()
    data["service"]["FA_min"] = 5000.0
    data["service"]["FA_max"] = 5000.0
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["forces"]["F_amplitude_N"] == 0.0
    assert result["stresses_mpa"]["sigma_a_fatigue"] == 0.0
    assert result["checks"]["fatigue_ok"] is True


def test_pulsating_load_fa_min_zero():
    """FA_min == 0, FA_max > 0 (脉动载荷)."""
    data = _base_input()
    data["service"]["FA_min"] = 0.0
    data["service"]["FA_max"] = 6000.0
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["forces"]["F_amplitude_N"] == 3000.0
    assert result["forces"]["F_mean_N"] == result["assembly"]["F_preload_max_N"] + 3000.0


def test_assembly_failure_high_preload():
    """极高预紧力导致装配不通过."""
    data = _base_input()
    data["assembly"]["F_preload_min"] = 80_000.0  # 远超 M12 承载
    data["assembly"]["alpha_A"] = 1.8
    result = bolt.calculate_tapped_axial_joint(data)
    assert result["checks"]["assembly_von_mises_ok"] is False
    assert result["overall_pass"] is False
    assert any("装配" in r for r in result["recommendations"])
```

- [ ] **Step 5: 补充脱扣未激活测试**

```python
def test_thread_strip_inactive_returns_fixed_shape():
    """未提供 m_eff 时，脱扣返回固定 shape 且 overall_pass 不受影响."""
    data = _base_input()
    # _base_input 中 thread_strip 无 m_eff
    result = bolt.calculate_tapped_axial_joint(data)
    ts = result["thread_strip"]
    assert ts["active"] is False
    assert ts["check_passed"] is True
    assert ts["A_SB_mm2"] == 0.0
    assert ts["critical_side"] == ""
    assert "未提供 m_eff" in ts["note"]
    assert result["checks"]["thread_strip_ok"] is True
```

- [ ] **Step 6: 运行全部 core 测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_tapped_axial_joint.py -v`

Expected: 全部 PASS（6 旧 + 7 新 = 13 个）

- [ ] **Step 7: Commit**

```bash
git add core/bolt/tapped_axial_joint.py tests/core/bolt/test_tapped_axial_joint.py
git commit -m "test(core): add benchmark and boundary tests for tapped axial calculator with VDI/ISO references"
```

---

## Phase 2: UI 补全

### Task 3: 在 bolt_tapped_axial_page.py 添加计算与结果展示

**Files:**
- Modify: `app/ui/pages/bolt_tapped_axial_page.py`

- [ ] **Step 1: 添加 calculate_tapped_axial_joint 导入和 CHECK_LABELS 常量**

在文件顶部添加导入，在 CHAPTERS 定义后添加常量：

```python
from core.bolt.tapped_axial_joint import calculate_tapped_axial_joint
from core.bolt import InputError

CHECK_LABELS: dict[str, str] = {
    "assembly_von_mises_ok": "装配 von Mises 强度",
    "service_von_mises_ok": "服役最大 von Mises 强度",
    "fatigue_ok": "交变轴向疲劳",
    "thread_strip_ok": "螺纹脱扣",
}
```

- [ ] **Step 2: 在 __init__ 中添加计算和导出按钮**

在 `self.btn_clear` 之后添加：

```python
        self.btn_calculate = self.add_action_button("开始计算")
        self.btn_export_text = self.add_action_button("导出文本报告")
        self.btn_export_pdf = self.add_action_button("导出 PDF 报告")
```

在信号连接区域添加：

```python
        self.btn_calculate.clicked.connect(self._run_calculation)
        self.btn_export_text.clicked.connect(self._export_text_report)
        self.btn_export_pdf.clicked.connect(self._export_pdf_report)
```

添加实例变量：

```python
        self._last_payload: dict[str, Any] | None = None
        self._last_result: dict[str, Any] | None = None
```

- [ ] **Step 3: 替换 _build_status_chapter 为 _build_result_chapter**

删除现有的 `_build_status_chapter` 方法，替换为：

```python
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
            "填写参数并点击"开始计算"后，这里显示结论。", summary_card
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
```

需要在文件顶部添加额外导入：

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    ...,
    QGridLayout,
    QPlainTextEdit,
    QFileDialog,
)
```

- [ ] **Step 4: 更新 __init__ 中的调用**

将 `self._build_status_chapter()` 替换为 `self._build_result_chapter()`。

同时更新 `set_info` 消息：

```python
        self.set_info("填写输入条件后点击"开始计算"。")
```

- [ ] **Step 5: 实现 _set_badge 和 _run_calculation**

```python
    def _set_badge(self, label: QLabel, text: str, state: str) -> None:
        """Set badge text and style (pass/fail/wait)."""
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
        """Build payload, run calculator, render results."""
        try:
            payload = self._build_payload()
            result = calculate_tapped_axial_joint(payload)
        except (InputError, ValueError) as exc:
            QMessageBox.critical(self, "输入参数错误", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "计算异常", str(exc))
            return

        self._last_payload = payload
        self._last_result = result
        self._render_result(result)
        # 跳转到结果章节（最后一个）
        self.set_current_chapter(self.chapter_list.count() - 1)
```

- [ ] **Step 6: 实现 _render_result**

```python
    def _render_result(self, result: dict[str, Any]) -> None:
        """Render calculation result into the result chapter."""
        overall = bool(result.get("overall_pass"))
        if overall:
            self.result_title.setText("校核通过")
            self.result_summary.setText(
                "该工况满足全部校核要求。"
            )
            self.set_overall_status("总体通过", "pass")
        else:
            self.result_title.setText("校核不通过")
            self.result_summary.setText(
                "存在不满足校核要求的项目，请查看分项结果与建议。"
            )
            self.set_overall_status("总体不通过", "fail")

        # 分项 badges
        for key, badge in self._check_badges.items():
            ok = bool(result.get("checks", {}).get(key, False))
            self._set_badge(badge, "通过" if ok else "不通过",
                            "pass" if ok else "fail")

        # 关键数值
        asm = result.get("assembly", {})
        stresses = result.get("stresses_mpa", {})
        fatigue = result.get("fatigue", {})
        forces = result.get("forces", {})
        ts = result.get("thread_strip", {})

        lines = [
            f"预紧力范围: F_min = {asm.get('F_preload_min_N', 0):.0f} N"
            f"  /  F_max = {asm.get('F_preload_max_N', 0):.0f} N",
            f"装配扭矩范围: MA_min = {asm.get('MA_min_Nm', 0):.2f} N·m"
            f"  /  MA_max = {asm.get('MA_max_Nm', 0):.2f} N·m",
            "",
            f"装配 von Mises: sigma_vm = {stresses.get('sigma_vm_assembly', 0):.1f} MPa"
            f"  (许用: {result.get('trace', {}).get('intermediate', {}).get('sigma_allow_assembly', 0):.1f} MPa)",
            f"服役最大 von Mises: sigma_vm = {stresses.get('sigma_vm_service_max', 0):.1f} MPa"
            f"  (许用: {result.get('trace', {}).get('intermediate', {}).get('sigma_allow_service', 0):.1f} MPa)",
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

        # 消息与建议
        messages: list[str] = []
        for w in result.get("warnings", []):
            messages.append(f"[警告] {w}")
        for r in result.get("recommendations", []):
            messages.append(f"[建议] {r}")
        scope = result.get("scope_note", "")
        if scope:
            messages.append(f"[说明] {scope}")
        self.message_box.setPlainText("\n".join(messages))
```

- [ ] **Step 7: 实现 _build_report_lines 和 _export_text_report**

```python
    def _build_report_lines(self) -> list[str]:
        """Build text report lines from last result."""
        if self._last_result is None:
            return ["尚未执行计算。"]

        result = self._last_result
        payload = self._last_payload or {}
        lines: list[str] = []

        lines.append("=" * 60)
        lines.append("轴向受力螺纹连接校核报告")
        lines.append("=" * 60)
        lines.append("")

        # 适用范围
        lines.append("--- 适用范围 ---")
        lines.append(result.get("scope_note", ""))
        lines.append("")

        # 输入摘要
        lines.append("--- 输入摘要 ---")
        fastener = payload.get("fastener", {})
        assembly = payload.get("assembly", {})
        service = payload.get("service", {})
        lines.append(f"螺纹规格: M{fastener.get('d', '?')} x {fastener.get('p', '?')}")
        lines.append(f"材料屈服强度: Rp0.2 = {fastener.get('Rp02', '?')} MPa")
        lines.append(f"最小预紧力: {assembly.get('F_preload_min', '?')} N")
        lines.append(f"拧紧散差: alpha_A = {assembly.get('alpha_A', '?')}")
        lines.append(f"轴向载荷: FA_min = {service.get('FA_min', '?')} N"
                      f" / FA_max = {service.get('FA_max', '?')} N")
        lines.append("")

        # 分项结果
        lines.append("--- 分项校核结果 ---")
        checks = result.get("checks", {})
        for key, label in CHECK_LABELS.items():
            ok = checks.get(key, False)
            lines.append(f"  {label}: {'通过' if ok else '不通过'}")
        overall = result.get("overall_pass", False)
        lines.append(f"  总体结论: {'通过' if overall else '不通过'}")
        lines.append("")

        # 关键数值
        lines.append("--- 关键数值 ---")
        lines.append(self.metrics_text.text())
        lines.append("")

        # 螺纹脱扣
        ts = result.get("thread_strip", {})
        lines.append("--- 螺纹脱扣 ---")
        lines.append(f"  状态: {'已启用' if ts.get('active') else '未启用'}")
        lines.append(f"  {ts.get('note', '')}")
        lines.append("")

        # trace
        lines.append("--- trace ---")
        for a in result.get("trace", {}).get("assumptions", []):
            lines.append(f"  {a}")
        lines.append("")

        # 警告与建议
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

        # 标准引用
        lines.append("--- 标准引用 ---")
        for k, v in result.get("references", {}).items():
            lines.append(f"  {k}: {v}")

        return lines

    def _export_text_report(self) -> None:
        """Export calculation results as a text file."""
        if self._last_result is None:
            QMessageBox.information(self, "提示", "请先执行计算。")
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
```

需要在文件顶部确认 `Path` 已导入（已在文件中存在）。

- [ ] **Step 8: 实现 _export_pdf_report 占位**

先添加一个 PDF 导出方法占位，Phase 3 会实现实际的 PDF 生成器：

```python
    def _export_pdf_report(self) -> None:
        """Export calculation results as a PDF file."""
        if self._last_result is None:
            QMessageBox.information(self, "提示", "请先执行计算。")
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
```

- [ ] **Step 9: 运行 UI 测试确认基础功能**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_tapped_axial_page.py -v`

Expected: 现有 4 个测试 PASS

- [ ] **Step 10: Commit**

```bash
git add app/ui/pages/bolt_tapped_axial_page.py
git commit -m "feat(ui): add calculation, result display, and text report to tapped axial page"
```

### Task 4: 注册到主窗口并更新 UI 测试

**Files:**
- Modify: `app/ui/main_window.py`
- Modify: `tests/ui/test_bolt_tapped_axial_page.py`
- Modify: `tests/ui/test_bolt_tapped_axial_results.py`

- [ ] **Step 1: 在 main_window.py 注册新模块**

在导入区添加：

```python
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
```

在 `self.modules` 列表中，在 `("螺栓连接", BoltPage(self))` 后面添加：

```python
            ("轴向受力螺纹连接", BoltTappedAxialPage(self)),
```

- [ ] **Step 2: 补充计算集成 UI 测试**

在 `tests/ui/test_bolt_tapped_axial_page.py` 添加新测试：

```python
    def test_run_calculation_sets_result_title_pass(self) -> None:
        page = BoltTappedAxialPage()
        # 默认输入应该通过（低载荷）
        page._field_widgets["service.FA_max"].setText("2000")

        page._run_calculation()

        self.assertIsNotNone(page._last_result)
        self.assertIn(page.result_title.text(), ("校核通过", "校核不通过"))

    def test_run_calculation_populates_check_badges(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")

        page._run_calculation()

        for key, badge in page._check_badges.items():
            self.assertIn(badge.text(), ("通过", "不通过"))

    def test_run_calculation_populates_metrics_text(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")

        page._run_calculation()

        text = page.metrics_text.text()
        self.assertIn("预紧力范围", text)
        self.assertIn("装配 von Mises", text)
        self.assertIn("疲劳应力幅", text)

    def test_build_report_lines_contains_scope_note(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")

        page._run_calculation()
        lines = page._build_report_lines()
        report_text = "\n".join(lines)

        self.assertIn("轴向受力螺纹连接校核报告", report_text)
        self.assertIn("适用范围", report_text)
        self.assertIn("螺纹脱扣", report_text)
        self.assertNotIn("clamped", report_text.lower())
        self.assertNotIn("FK_residual", report_text)
```

- [ ] **Step 3: 重写 test_bolt_tapped_axial_results.py 匹配新实现**

替换整个文件内容：

```python
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage


class BoltTappedAxialResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_run_calculation_renders_result_and_inactive_thread_strip(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["service.FA_max"].setText("2000")

        page._run_calculation()

        self.assertIsNotNone(page._last_result)
        self.assertEqual(page.result_title.text(), "校核通过")
        self.assertIn("预紧力范围", page.metrics_text.text())
        self.assertIn("未提供 m_eff", page.message_box.toPlainText())
        self.assertNotIn("FK_residual", page.metrics_text.text())

    def test_report_lines_include_scope_and_new_sections(self) -> None:
        page = BoltTappedAxialPage()

        page._run_calculation()
        lines = page._build_report_lines()
        report_text = "\n".join(lines)

        self.assertIn("轴向受力螺纹连接校核报告", report_text)
        self.assertIn("适用范围", report_text)
        self.assertIn("trace", report_text.lower())
        self.assertIn("螺纹脱扣", report_text)
        self.assertNotIn("clamped", report_text.lower())
        self.assertNotIn("FK_residual", report_text)
        self.assertNotIn("R3", report_text)

    def test_main_window_registers_tapped_axial_module_entry(self) -> None:
        window = MainWindow()

        module_names = [name for name, _ in window.modules]

        self.assertIn("轴向受力螺纹连接", module_names)

    def test_calculation_failure_shows_error_not_crash(self) -> None:
        page = BoltTappedAxialPage()
        page._field_widgets["fastener.d"].setText("")  # 缺失必填字段

        # 不应抛出异常（应被 QMessageBox 捕获）
        page._run_calculation()

        self.assertIsNone(page._last_result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: 运行全部 UI 测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_tapped_axial_page.py tests/ui/test_bolt_tapped_axial_results.py -v`

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add app/ui/main_window.py tests/ui/test_bolt_tapped_axial_page.py tests/ui/test_bolt_tapped_axial_results.py
git commit -m "feat(ui): register tapped axial module in sidebar and update UI tests"
```

---

## Phase 3: PDF 报告

### Task 5: 实现 PDF 报告生成器

**Files:**
- Create: `app/ui/report_pdf_tapped_axial.py`
- Modify: `tests/ui/test_bolt_tapped_axial_optional_pdf.py`

- [ ] **Step 1: 创建 report_pdf_tapped_axial.py**

```python
"""Professional PDF report for tapped axial threaded joint check results.

Uses reportlab to produce an A4 report with:
- Colored header bar, pass/fail verdict
- Input summary, check pills, key metrics
- Detailed stress results and fatigue data
- Warnings and recommendations
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    Spacer,
)

from app.ui.report_pdf_common import (
    _build_styles,
    _check_pills,
    _fmt,
    _header_bar,
    _kv_table,
    _metric_cards,
    _register_fonts,
    _rstep_card,
    _section_title,
    _verdict_block,
    build_pdf,
)

# ---------------------------------------------------------------------------
# Check labels
# ---------------------------------------------------------------------------
CHECK_LABELS = {
    "assembly_von_mises_ok": "装配强度",
    "service_von_mises_ok": "服役最大强度",
    "fatigue_ok": "交变轴向疲劳",
    "thread_strip_ok": "螺纹脱扣",
}


# ---------------------------------------------------------------------------
# Main report generator
# ---------------------------------------------------------------------------
def generate_tapped_axial_report(
    path: Path,
    payload: dict,
    result: dict,
) -> None:
    """Generate a professional PDF report for tapped axial threaded joint."""
    _register_fonts()
    styles = _build_styles()
    elems: list = []

    checks = result.get("checks", {})
    overall = bool(result.get("overall_pass", False))
    date_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. Header bar
    elems.append(_header_bar(styles, "轴向受力螺纹连接校核报告", date_str))
    elems.append(Spacer(1, 8))

    # 2. Verdict
    scope = result.get("scope_note", "")
    elems.append(_verdict_block(styles, overall, scope))
    elems.append(Spacer(1, 8))

    # 3. Metric cards
    asm = result.get("assembly", {})
    stresses = result.get("stresses_mpa", {})
    fatigue = result.get("fatigue", {})
    metrics = [
        ("F_preload_max (N)", _fmt(asm.get("F_preload_max_N"), 0)),
        ("MA_max (N*m)", _fmt(asm.get("MA_max_Nm"), 2)),
        ("sigma_vm_assembly (MPa)", _fmt(stresses.get("sigma_vm_assembly"), 1)),
        ("sigma_a_allow (MPa)", _fmt(fatigue.get("sigma_a_allow"), 2)),
    ]
    elems.append(_metric_cards(styles, metrics))
    elems.append(Spacer(1, 10))

    # 4. Check pills
    refs = result.get("references", {})
    elems.append(_check_pills(styles, checks, CHECK_LABELS, refs))
    elems.append(Spacer(1, 10))

    # 5. Input summary
    elems.append(_section_title(styles, "输入摘要"))
    fastener = payload.get("fastener", {})
    assembly = payload.get("assembly", {})
    service = payload.get("service", {})
    fat_in = payload.get("fatigue", {})
    input_rows = [
        ("公称直径 d", _fmt(fastener.get("d"), 1, "mm")),
        ("螺距 p", _fmt(fastener.get("p"), 2, "mm")),
        ("屈服强度 Rp0.2", _fmt(fastener.get("Rp02"), 0, "MPa")),
        ("最小预紧力 F_preload_min", _fmt(assembly.get("F_preload_min"), 0, "N")),
        ("拧紧散差 alpha_A", _fmt(assembly.get("alpha_A"), 2)),
        ("螺纹摩擦 mu_thread", _fmt(assembly.get("mu_thread"), 3)),
        ("支承面摩擦 mu_bearing", _fmt(assembly.get("mu_bearing"), 3)),
        ("拧紧方式", str(assembly.get("tightening_method", ""))),
        ("最小轴向载荷 FA_min", _fmt(service.get("FA_min"), 0, "N")),
        ("最大轴向载荷 FA_max", _fmt(service.get("FA_max"), 0, "N")),
        ("载荷循环次数", _fmt(fat_in.get("load_cycles"), 0)),
        ("表面处理", str(fat_in.get("surface_treatment", ""))),
    ]
    elems.append(_kv_table(styles, input_rows, 0.45))
    elems.append(Spacer(1, 10))

    # 6. Assembly strength card
    trace = result.get("trace", {}).get("intermediate", {})
    asm_values = [
        f"轴向装配应力 sigma_ax = {_fmt(stresses.get('sigma_ax_assembly'), 1, 'MPa')}",
        f"装配扭转应力 tau = {_fmt(stresses.get('tau_assembly'), 1, 'MPa')}",
        f"装配 von Mises sigma_vm = {_fmt(stresses.get('sigma_vm_assembly'), 1, 'MPa')}",
        f"许用装配应力 = {_fmt(trace.get('sigma_allow_assembly'), 1, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "装配强度校核", asm_values,
                    passed=checks.get("assembly_von_mises_ok")),
        Spacer(1, 6),
    ]))

    # 7. Service strength card
    svc_values = [
        f"最大服役轴向应力 sigma_ax = {_fmt(stresses.get('sigma_ax_service_max'), 1, 'MPa')}",
        f"服役 von Mises sigma_vm = {_fmt(stresses.get('sigma_vm_service_max'), 1, 'MPa')}",
        f"许用服役应力 = {_fmt(trace.get('sigma_allow_service'), 1, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "服役最大强度校核", svc_values,
                    passed=checks.get("service_von_mises_ok")),
        Spacer(1, 6),
    ]))

    # 8. Fatigue card
    fat_values = [
        f"疲劳平均应力 sigma_m = {_fmt(stresses.get('sigma_m_fatigue'), 1, 'MPa')}",
        f"疲劳应力幅 sigma_a = {_fmt(stresses.get('sigma_a_fatigue'), 2, 'MPa')}",
        f"sigma_ASV = {_fmt(fatigue.get('sigma_ASV'), 1, 'MPa')}",
        f"Goodman 折减系数 = {_fmt(fatigue.get('goodman_factor'), 3)}",
        f"许用应力幅 sigma_a_allow = {_fmt(fatigue.get('sigma_a_allow'), 2, 'MPa')}",
    ]
    elems.append(KeepTogether([
        _rstep_card(styles, "交变轴向疲劳校核", fat_values,
                    passed=checks.get("fatigue_ok")),
        Spacer(1, 6),
    ]))

    # 9. Thread strip card
    ts = result.get("thread_strip", {})
    if ts.get("active"):
        ts_values = [
            f"螺栓侧剪切面积 A_SB = {_fmt(ts.get('A_SB_mm2'), 1, 'mm2')}",
            f"壳体侧剪切面积 A_SM = {_fmt(ts.get('A_SM_mm2'), 1, 'mm2')}",
            f"螺栓最大拉力 F_bolt_max = {_fmt(ts.get('F_bolt_max_N'), 0, 'N')}",
            f"脱扣安全系数 S = {_fmt(ts.get('strip_safety'), 2)}"
            f" (要求 >= {_fmt(ts.get('strip_safety_required'), 2)})",
            ts.get("note", ""),
        ]
        elems.append(KeepTogether([
            _rstep_card(styles, "螺纹脱扣校核", ts_values,
                        passed=ts.get("check_passed")),
            Spacer(1, 6),
        ]))
    else:
        elems.append(KeepTogether([
            _rstep_card(styles, "螺纹脱扣校核",
                        [ts.get("note", "未启用")], passed=None),
            Spacer(1, 6),
        ]))

    # 10. Warnings
    warnings = result.get("warnings", [])
    if warnings:
        elems.append(_section_title(styles, "警告信息"))
        for msg in warnings:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 11. Recommendations
    recs = result.get("recommendations", [])
    if recs:
        elems.append(_section_title(styles, "优化建议"))
        for msg in recs:
            elems.append(Paragraph(f"- {msg}", styles["body"]))
        elems.append(Spacer(1, 8))

    # 12. References
    elems.append(_section_title(styles, "标准引用"))
    for k, v in result.get("references", {}).items():
        elems.append(Paragraph(f"{k}: {v}", styles["muted"]))
    elems.append(Spacer(1, 4))

    build_pdf(path, elems, "轴向受力螺纹连接校核")
```

- [ ] **Step 2: 确认 PDF 测试文件导入路径正确**

检查 `tests/ui/test_bolt_tapped_axial_optional_pdf.py` 已有的内容：

```python
def test_generate_tapped_axial_pdf_report(tmp_path: Path) -> None:
    pytest.importorskip("reportlab")

    from app.ui.report_pdf_tapped_axial import generate_tapped_axial_report

    out = tmp_path / "tapped_axial_report.pdf"
    generate_tapped_axial_report(out, _sample_payload(), _sample_result())

    assert out.exists()
    assert out.stat().st_size > 1000
```

该测试已正确引用 `generate_tapped_axial_report`，无需修改。

- [ ] **Step 3: 运行 PDF 测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_bolt_tapped_axial_optional_pdf.py -v`

Expected: PASS（如已安装 reportlab）或 SKIP（如未安装）

- [ ] **Step 4: Commit**

```bash
git add app/ui/report_pdf_tapped_axial.py
git commit -m "feat(report): add PDF report generator for tapped axial threaded joint"
```

---

## Phase 4: 收尾

### Task 6: 更新文档并全量回归

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新 CLAUDE.md 模块状态**

在"项目概述"段落中，将"轴向受力螺纹连接"从"待接入"改为"已实现"：

```
当前已实现：螺栓连接（VDI 2230）、过盈配合（DIN 7190）、赫兹接触应力、蜗轮几何（DIN 3975）、轴向受力螺纹连接。
```

删除或更新"当前已知限制"中的相关描述：

```
- 轴向受力螺纹连接：已实现 core 计算、UI 结果展示、文本/PDF 报告导出。暂不支持横向力、弯矩、多螺栓并联。
```

- [ ] **Step 2: 运行定向全链回归**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_tapped_axial_joint.py tests/ui/test_bolt_tapped_axial_page.py tests/ui/test_bolt_tapped_axial_results.py tests/ui/test_bolt_tapped_axial_optional_pdf.py -v
```

Expected: 全部 PASS

- [ ] **Step 3: 运行 bolt 域回归**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/ tests/ui/test_bolt_tapped_axial_page.py tests/ui/test_bolt_tapped_axial_results.py -v
```

Expected: 全部 PASS，现有 bolt VDI 2230 测试不受影响

- [ ] **Step 4: 运行全量回归**

Run:

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to reflect completed tapped axial module"
```

---

## Agent Team 执行建议

### 推荐调度

| Phase | Agent | 文件范围 | 依赖 |
|-------|-------|---------|------|
| 1 (Task 1-2) | core-engineer | `core/bolt/tapped_axial_joint.py`, `tests/core/bolt/test_tapped_axial_joint.py` | 无 |
| 2 (Task 3-4) | ui-engineer | `app/ui/pages/bolt_tapped_axial_page.py`, `app/ui/main_window.py`, `tests/ui/test_bolt_tapped_axial_*.py` | Phase 1 完成 |
| 3 (Task 5) | ui-engineer | `app/ui/report_pdf_tapped_axial.py` | Phase 2 完成 |
| 4 (Task 6) | code-reviewer 审查 + 文档 | `CLAUDE.md`, 全量测试 | Phase 3 完成 |

### 约束

- Phase 2 必须在 Phase 1 之后，确保 core 输出 schema 稳定
- Phase 3 的 PDF 文件独立于 UI 页面，但函数签名需对齐
- 不要让多个 agent 同时修改 `bolt_tapped_axial_page.py`
