# 螺栓模块 P0 修复 + 校核链路流程图 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复螺栓 VDI 2230 校核的 P0 问题（phi_n 硬阻断、R3 双模式、R7 支承面），并新增按校核逻辑导航的流程图视图。

**Architecture:** Core 层 calculator.py 新增计算模式分支、phi_n 硬阻断和 R7 校核。UI 层 bolt_page.py 新增双 Tab 导航和计算模式联动。新建 bolt_flowchart.py 封装流程图导航和 R 详情页。

**Tech Stack:** Python 3.12, PySide6, pytest

**Spec:** `docs/plans/2026-03-16-bolt-p0-fixes-and-flowchart-design.md`

---

## File Structure

| 文件 | 职责 |
|------|------|
| `core/bolt/calculator.py` | 修改：phi_n 硬阻断 + calculation_mode 分支 + R7 支承面压强 |
| `app/ui/pages/bolt_page.py` | 修改：双 Tab 导航组装 + 计算模式/材料联动 + FM_min_input/p_G_allow 字段 |
| `app/ui/pages/bolt_flowchart.py` | **新建**：FlowchartNavWidget + RStepDetailPage + 常量 |
| `app/ui/theme.py` | 修改：流程图节点选中态样式 |
| `tests/core/bolt/test_calculator.py` | **新建**：calculator 核心测试 |
| `examples/input_case_01.json` | 修改：新增 bearing.p_G_allow |
| `examples/input_case_02.json` | 修改：同上 |

---

## Chunk 1: Core 层 — phi_n 硬阻断 + R7 支承面 + 计算模式

### Task 1: phi_n >= 1 硬阻断 + 测试

**Files:**
- Modify: `core/bolt/calculator.py:146-147` (插入硬阻断), `core/bolt/calculator.py:255-258` (删除软警告)
- Create: `tests/core/bolt/__init__.py`, `tests/core/bolt/test_calculator.py`

- [ ] **Step 1: 创建测试文件和 phi_n 硬阻断测试**

```python
# tests/core/bolt/test_calculator.py
"""VDI 2230 bolt calculator tests."""
import math
import pytest
from core.bolt.calculator import InputError, calculate_vdi2230_core


def _base_input() -> dict:
    """最小可用输入（基于 input_case_02.json，已知全部通过）。"""
    return {
        "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
        "tightening": {
            "alpha_A": 1.5, "mu_thread": 0.1, "mu_bearing": 0.12,
            "utilization": 0.85, "thread_flank_angle_deg": 60.0,
        },
        "loads": {
            "FA_max": 6000.0, "FQ_max": 600.0, "embed_loss": 600.0,
            "thermal_force_loss": 300.0, "slip_friction_coefficient": 0.2,
            "friction_interfaces": 1.0,
        },
        "stiffness": {
            "bolt_compliance": 1.8e-06, "clamped_compliance": 2.4e-06,
            "load_introduction_factor_n": 1.0,
        },
        "bearing": {"bearing_d_inner": 13.0, "bearing_d_outer": 22.0},
        "checks": {"yield_safety_operating": 1.15},
    }


class TestPhiNHardBlock:
    def test_phi_n_ge_1_raises_input_error(self):
        data = _base_input()
        # n=2.0 使 phi_n = 2.0 * delta_p/(delta_s+delta_p) > 1
        data["stiffness"]["load_introduction_factor_n"] = 2.0
        with pytest.raises(InputError, match="phi_n"):
            calculate_vdi2230_core(data)

    def test_phi_n_below_1_passes(self):
        data = _base_input()
        data["stiffness"]["load_introduction_factor_n"] = 1.0
        result = calculate_vdi2230_core(data)
        assert result["intermediate"]["phi_n"] < 1.0

    def test_phi_n_warning_removed_from_output(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        for w in result.get("warnings", []):
            assert "phi_n" not in w.lower()
```

- [ ] **Step 2: 创建 `tests/core/bolt/__init__.py`，运行测试确认失败**

```bash
touch tests/core/bolt/__init__.py
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py -v
```
预期：`test_phi_n_ge_1_raises_input_error` FAIL（当前仅 warning 不 raise），其余可能 PASS。

- [ ] **Step 3: 实现 phi_n 硬阻断**

在 `core/bolt/calculator.py` 中：
1. 在 `phi_n = n * phi`（当前第 146 行）之后插入：
```python
if phi_n >= 1.0:
    raise InputError(
        f"载荷分配系数 phi_n = {phi_n:.3f} >= 1，外载全部进入螺栓，无物理意义。"
        "请检查刚度模型（δs/δp）与载荷导入系数 n。"
    )
```
2. 删除 warnings 列表中 `phi_n >= 1.0` 的软警告代码（第 255-258 行）。

- [ ] **Step 4: 运行测试确认全部通过**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py -v
```
预期：3 tests PASS。

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
预期：所有 36+ tests PASS。

- [ ] **Step 6: 提交**

```bash
git add core/bolt/calculator.py tests/core/bolt/
git commit -m "feat(bolt): hard-block phi_n >= 1 with InputError

Replace soft warning with hard InputError when phi_n >= 1.0,
as subsequent formulas have no physical meaning in this range.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 支承面压强校核 R7 + 测试

**Files:**
- Modify: `core/bolt/calculator.py`
- Modify: `tests/core/bolt/test_calculator.py`
- Modify: `examples/input_case_01.json`, `examples/input_case_02.json`

- [ ] **Step 1: 编写 R7 测试**

追加到 `tests/core/bolt/test_calculator.py`：

```python
class TestBearingPressureR7:
    def test_r7_pass_when_pressure_below_limit(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        assert "bearing_pressure_ok" in result["checks"]
        assert result["checks"]["bearing_pressure_ok"] is True
        assert result["stresses_mpa"]["p_bearing"] > 0
        assert result["stresses_mpa"]["A_bearing_mm2"] > 0

    def test_r7_fail_when_pressure_above_limit(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 1.0  # 极低许用值
        result = calculate_vdi2230_core(data)
        assert result["checks"]["bearing_pressure_ok"] is False
        assert result["overall_pass"] is False

    def test_r7_skipped_when_p_g_allow_missing(self):
        data = _base_input()
        # 不设置 p_G_allow
        result = calculate_vdi2230_core(data)
        assert "bearing_pressure_ok" not in result["checks"]

    def test_r7_skipped_when_p_g_allow_zero(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 0.0
        result = calculate_vdi2230_core(data)
        assert "bearing_pressure_ok" not in result["checks"]

    def test_r7_formula_correctness(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        d_inner = data["bearing"]["bearing_d_inner"]
        d_outer = data["bearing"]["bearing_d_outer"]
        a_expected = math.pi / 4.0 * (d_outer**2 - d_inner**2)
        fm_max = result["intermediate"]["FMmax_N"]
        p_expected = fm_max / a_expected
        assert abs(result["stresses_mpa"]["A_bearing_mm2"] - a_expected) < 0.1
        assert abs(result["stresses_mpa"]["p_bearing"] - p_expected) < 0.1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestBearingPressureR7 -v
```
预期：5 tests FAIL（`bearing_pressure_ok` 不存在、`stresses_mpa` 无 `p_bearing` 等）。

- [ ] **Step 3: 实现 R7 支承面压强校核**

在 `core/bolt/calculator.py` 中，在 `checks_out` 字典构建之前（当前 `pass_additional` 计算之后），插入：

```python
# --- R7 支承面压强校核 ---
p_g_allow = float(bearing.get("p_G_allow", 0.0))
r7_active = p_g_allow > 0
if r7_active:
    a_bearing = math.pi / 4.0 * (bearing_d_outer**2 - bearing_d_inner**2)
    p_bearing = fm_max / a_bearing
    pass_bearing = p_bearing <= p_g_allow
```

在 `checks_out` 字典中有条件添加：
```python
if r7_active:
    checks_out["bearing_pressure_ok"] = pass_bearing
```

在 `stresses_mpa` 输出中有条件添加：
```python
# 在 return dict 的 stresses_mpa 节内
if r7_active:
    stresses_out["p_bearing"] = p_bearing
    stresses_out["p_G_allow"] = p_g_allow
    stresses_out["A_bearing_mm2"] = a_bearing
```

注意：需要先将 `stresses_mpa` 从内联 dict 改为变量 `stresses_out`，然后在 return 前有条件扩展。

- [ ] **Step 4: 运行测试确认通过**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py -v
```
预期：所有 tests PASS。

- [ ] **Step 5: 更新测试案例 JSON**

在 `examples/input_case_01.json` 和 `examples/input_case_02.json` 的 `bearing` section 中新增：
```json
"p_G_allow": 700.0
```

- [ ] **Step 6: 运行全量测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **Step 7: 提交**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py examples/
git commit -m "feat(bolt): add bearing surface pressure check R7

Optional R7 check: p_bearing = FM_max / A_bearing <= p_G_allow.
Skipped when p_G_allow is missing or zero (backward compatible).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: 设计/校核双模式 + 测试

**Files:**
- Modify: `core/bolt/calculator.py`
- Modify: `tests/core/bolt/test_calculator.py`

- [ ] **Step 1: 编写计算模式测试**

追加到 `tests/core/bolt/test_calculator.py`：

```python
class TestCalculationMode:
    def test_default_mode_is_design(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["calculation_mode"] == "design"
        assert result["r3_note"] is not None

    def test_design_mode_r3_always_true(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["checks"]["residual_clamp_ok"] is True

    def test_verify_mode_with_sufficient_preload(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        # 先用设计模式计算出 FM_min，然后用更大的值做校核
        design_result = calculate_vdi2230_core(_base_input())
        fm_min_design = design_result["intermediate"]["FMmin_N"]
        data["loads"]["FM_min_input"] = fm_min_design * 1.2  # 120% 裕量
        result = calculate_vdi2230_core(data)
        assert result["calculation_mode"] == "verify"
        assert result["checks"]["residual_clamp_ok"] is True

    def test_verify_mode_with_insufficient_preload(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        data["loads"]["FM_min_input"] = 100.0  # 远低于需求
        result = calculate_vdi2230_core(data)
        assert result["checks"]["residual_clamp_ok"] is False
        assert result["overall_pass"] is False

    def test_verify_mode_requires_fm_min_input(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        # 不提供 FM_min_input
        with pytest.raises(InputError, match="FM_min_input"):
            calculate_vdi2230_core(data)

    def test_verify_mode_fm_min_used_for_torque_and_stress(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        fm_input = 20000.0
        data["loads"]["FM_min_input"] = fm_input
        result = calculate_vdi2230_core(data)
        assert abs(result["intermediate"]["FMmin_N"] - fm_input) < 1e-6
        assert abs(result["intermediate"]["FMmax_N"] - fm_input * data["tightening"]["alpha_A"]) < 1.0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestCalculationMode -v
```
预期：多数 FAIL（`calculation_mode` 字段不存在、verify 模式未实现）。

- [ ] **Step 3: 实现计算模式分支**

在 `core/bolt/calculator.py` 的 `calculate_vdi2230_core` 函数中：

1. 在 `check_level` 解析后，添加 `calculation_mode` 解析：
```python
calculation_mode = str(options.get("calculation_mode", "design"))
if calculation_mode not in {"design", "verify"}:
    raise InputError(f"options.calculation_mode 无效：{calculation_mode}")
```

2. 将 FM_min 计算替换为模式分支：
```python
if calculation_mode == "verify":
    fm_min_input = _positive(
        float(_require(loads, "FM_min_input", "loads")),
        "loads.FM_min_input",
    )
    fm_min = fm_min_input
    r3_note = "校核模式：独立验证已知预紧力是否满足残余夹紧需求"
else:
    fm_min = f_k_required + (1.0 - phi_n) * fa_max + embed_loss + thermal_effective
    r3_note = "设计模式下 FM_min 由 FK_req 反推，R3 自动满足"
```

3. R3 校核根据模式：
```python
if calculation_mode == "verify":
    f_k_residual = fm_min - embed_loss - thermal_effective - (1.0 - phi_n) * fa_max
    pass_residual = f_k_residual >= f_k_required
else:
    f_k_residual = f_k_required  # 设计模式下恒等
    pass_residual = True
```

4. 输出新增 `calculation_mode` 和 `r3_note`。

- [ ] **Step 4: 运行测试确认通过**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py -v
```
预期：全部 PASS。

- [ ] **Step 5: 运行全量测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **Step 6: 提交**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): add design/verify calculation modes for R3

Design mode (default): FM_min derived from FK_req, R3 auto-satisfied.
Verify mode: user inputs known FM_min, R3 independently checked.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 2: UI 层 — 新增字段 + 联动 + 主题

### Task 4: 主题样式 + 新 UI 字段（FM_min_input、支承面材料）

**Files:**
- Modify: `app/ui/theme.py`
- Modify: `app/ui/pages/bolt_page.py`

- [ ] **Step 1: 在 theme.py 新增流程图节点选中态样式**

在 `QFrame#DisabledSubCard` 样式块之后添加：
```css
QFrame#SubCard[selected="true"] {
    border: 2px solid #D97757;
    background-color: #FBF3EE;
}
```

- [ ] **Step 2: 在 bolt_page.py 添加新常量和 FieldSpec**

在文件顶部常量区域添加：
```python
VERIFY_MODE_FIELD_IDS: set[str] = {"loads.FM_min_input"}
BEARING_MATERIAL_PRESETS: dict[str, str] = {"钢": "700", "铝合金": "300"}

CALC_MODES: tuple[tuple[str, str], ...] = (
    ("设计模式（反推 FM_min）", "design"),
    ("校核模式（输入已知 FM_min）", "verify"),
)
```

在"装配属性"章节 CHAPTERS 定义中，`thermal_force_loss` 字段后追加：
```python
FieldSpec(
    "loads.FM_min_input", "已知最小预紧力 FM,min", "N",
    "校核模式：输入已有设计的最小预紧力值，跳过反推直接校核。",
    mapping=("loads", "FM_min_input"), default="",
),
```

在"连接件与螺纹"章节 CHAPTERS 定义中，`bearing_d_outer` 字段后追加：
```python
FieldSpec(
    "bearing.bearing_material", "支承面材料", "-",
    "选择支承面材料以自动填入许用压强。",
    mapping=None, widget_type="choice",
    options=("钢", "铝合金", "自定义"), default="钢",
),
FieldSpec(
    "bearing.p_G_allow", "许用支承面压强 p_G", "MPa",
    "支承面许用面压强度。钢约 700 MPa，铝合金约 300 MPa。",
    mapping=("bearing", "p_G_allow"), default="700",
),
```

CHECK_LABELS 新增：
```python
"bearing_pressure_ok": "支承面压强校核（R7）",
```

- [ ] **Step 3: 添加计算模式下拉框和联动方法**

在 `__init__` 中：
1. 创建 `self.calc_mode_combo = QComboBox()`，填充 `CALC_MODES`。
2. 在 `_create_level_page()` 中，在校核层级下拉框下方添加计算模式卡片。
3. 连接 `calc_mode_combo.currentIndexChanged` 到 `_apply_calculation_mode_visibility`。

在 `_create_level_page()` 中，在校核层级下拉框下方添加计算模式卡片：
```python
# ---- 计算模式 ----
mode_card = QFrame(level_page)
mode_card.setObjectName("SubCard")
mode_layout = QVBoxLayout(mode_card)
mode_layout.setContentsMargins(12, 10, 12, 10)
mode_title = QLabel("计算模式", mode_card)
mode_title.setObjectName("SubSectionTitle")
mode_layout.addWidget(mode_title)
self.calc_mode_combo = QComboBox(mode_card)
self.calc_mode_combo.addItem("设计模式 — 由 FK_req 反推 FM_min", "design")
self.calc_mode_combo.addItem("校核模式 — 使用已知 FM_min", "verify")
mode_layout.addWidget(self.calc_mode_combo)
self.mode_desc_label = QLabel("设计模式：由 FK_req 反推 FM_min，R3 自动满足。", mode_card)
self.mode_desc_label.setObjectName("SectionHint")
self.mode_desc_label.setWordWrap(True)
mode_layout.addWidget(self.mode_desc_label)
# 将 mode_card 添加到 level_page 的布局中
level_layout.addWidget(mode_card)
```

新增方法：
```python
def _apply_calculation_mode_visibility(self, *_args) -> None:
    mode = self.calc_mode_combo.currentData() or "design"
    show_verify = mode == "verify"
    for field_id, card in self._field_cards.items():
        if field_id in VERIFY_MODE_FIELD_IDS:
            card.setVisible(show_verify)
    # 更新模式说明
    if mode == "verify":
        self.mode_desc_label.setText(
            "校核模式：跳过 FM_min 反推，直接用已知预紧力做校核。\n"
            "请在「步骤 3. 装配属性」中填写已知 FM,min 值。"
        )
    else:
        self.mode_desc_label.setText(
            "设计模式：由 FK_req 反推 FM_min，R3 自动满足。"
        )
```

**重要**：在 `_apply_check_level_visibility` 方法中，`else` 分支（非 THERMAL/FATIGUE 字段）会将所有其他字段强制 `setVisible(True)`。这会覆盖计算模式对 `FM_min_input` 的隐藏。
修复方式——在 `_apply_check_level_visibility` 的 `else` 分支中排除 VERIFY_MODE_FIELD_IDS：
```python
# 原逻辑 else 分支
else:
    if field_id in VERIFY_MODE_FIELD_IDS:
        pass  # 由 _apply_calculation_mode_visibility 控制
    else:
        card.setVisible(True)
```
并在 `_apply_check_level_visibility` 末尾调用 `self._apply_calculation_mode_visibility()` 确保两者联动。

新增材料联动方法：
```python
def _on_bearing_material_changed(self, text: str) -> None:
    preset = BEARING_MATERIAL_PRESETS.get(text)
    editor = self._field_widgets.get("bearing.p_G_allow")
    if editor and isinstance(editor, QLineEdit):
        if preset:
            editor.setText(preset)
        else:
            editor.clear()
            editor.setFocus()
```

在 `__init__` 中连接信号：`bearing.bearing_material` widget 的 `currentTextChanged` → `_on_bearing_material_changed`。

- [ ] **Step 4: 修改 `_build_payload` 传入 calculation_mode**

在 `_build_payload()` 末尾，将 `check_level` 和 `calculation_mode` 加入 payload：
```python
payload.setdefault("options", {})["check_level"] = self._current_check_level()
payload["options"]["calculation_mode"] = self.calc_mode_combo.currentData() or "design"
```

- [ ] **Step 5: 修改 `_render_result` 处理 R3/R7 Badge 特殊逻辑**

在 `_render_result()` 中，**替换**现有 badge 渲染循环为遍历 `self._check_badges`（而非 `checks.items()`），以正确处理 R7 跳过和 R3 设计模式：
```python
for key, badge in self._check_badges.items():
    if key == "residual_clamp_ok" and result.get("calculation_mode") == "design":
        self._set_badge(badge, "通过（设计模式自动满足）", True)
    elif key not in checks:
        # R7 未设置许用压强时 bearing_pressure_ok 不在 checks 中
        badge.setObjectName("WaitBadge")
        badge.setText("已跳过")
        badge.style().polish(badge)
    else:
        self._set_badge(badge, "通过" if checks[key] else "不通过", checks[key])
```

**注意**：此处还需更新 scope_note 文案——因为 R7 已实现，从 "支承面压强、螺纹脱扣与完整疲劳谱仍未覆盖" 中移除 "支承面压强"：
```python
# 原 bolt_page.py 约 1183 行的 scope_note
scope_note = "注意：螺纹脱扣与完整疲劳谱仍未覆盖。"
```

- [ ] **Step 6: 运行全量测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **Step 7: 手动启动应用验证 UI**

```bash
python3 app/main.py
```
验证：
1. 校核层级设置页显示计算模式下拉框
2. 切换校核模式 → FM_min_input 字段出现在装配属性章节
3. 连接件章节显示支承面材料下拉框 + 许用压强
4. 选择铝合金 → 许用压强自动变为 300

- [ ] **Step 8: 提交**

```bash
git add app/ui/theme.py app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): add calculation mode, bearing material fields

- Calculation mode combo (design/verify) in level settings page
- FM_min_input field (hidden in design mode)
- Bearing material dropdown with p_G_allow auto-fill
- R3/R7 badge special rendering logic
- Flowchart node selected state in theme

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 3: 校核链路流程图导航

### Task 5: FlowchartNavWidget — 左侧流程图导航

**Files:**
- Create: `app/ui/pages/bolt_flowchart.py`

- [ ] **Step 1: 创建 bolt_flowchart.py 骨架和常量**

```python
"""VDI 2230 校核链路流程图导航和 R 步骤详情页。"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
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
```

- [ ] **Step 2: 实现 FlowNodeWidget（可点击节点）**

```python
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
```

- [ ] **Step 3: 实现 FlowchartNavWidget**

```python
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
```

- [ ] **Step 4: 运行语法检查**

```bash
python3 -c "import py_compile; py_compile.compile('app/ui/pages/bolt_flowchart.py', doraise=True); print('OK')"
```
预期：OK。

- [ ] **Step 5: 提交**

```bash
git add app/ui/pages/bolt_flowchart.py
git commit -m "feat(bolt/ui): add FlowchartNavWidget for verification chain

New bolt_flowchart.py with:
- R_STEPS / R_STEP_FIELDS constants
- FlowNodeWidget (clickable node with badge)
- FlowchartNavWidget (scrollable vertical flow)
- update_from_result() for post-calculation refresh

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: RStepDetailPage — R 步骤详情页（只读）

**Files:**
- Modify: `app/ui/pages/bolt_flowchart.py`

- [ ] **Step 1: 实现 RStepDetailPage 类**

在 `bolt_flowchart.py` 末尾追加：

```python
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

    # 中间值字段的显示名称和单位映射
    _INTERMEDIATE_LABELS: dict[str, tuple[str, str]] = {
        "intermediate.phi_n": ("φn (载荷导入系数)", "-"),
        "intermediate.FM_min": ("FM,min (最小预紧力)", "N"),
        "intermediate.FM_max": ("FM,max (最大预紧力)", "N"),
        "intermediate.FK_req": ("FK,req (所需夹紧力)", "N"),
    }

    def build_input_echo(self, field_specs: dict[str, Any],
                         field_widgets: dict[str, Any],
                         result: dict[str, Any] | None = None) -> None:
        """构建输入回显区。
        对于 field_specs 中存在的字段从 widget 读取；
        对于 intermediate.* 前缀的字段从 result 中读取。"""
        step_id = self._step["id"]
        field_ids = R_STEP_FIELDS.get(step_id, [])
        row = 0
        inter = (result or {}).get("intermediate", {})
        # 中间值 key 映射：intermediate.FM_min -> FMmin_N
        _INTER_KEY_MAP = {
            "intermediate.phi_n": "phi_n",
            "intermediate.FM_min": "FMmin_N",
            "intermediate.FM_max": "FMmax_N",
            "intermediate.FK_req": "F_K_required_N",
        }
        for fid in field_ids:
            if fid.startswith("intermediate."):
                label_text, unit = self._INTERMEDIATE_LABELS.get(fid, (fid, ""))
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
                from PySide6.QtWidgets import QLineEdit, QComboBox
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
        # 刷新输入回显值
        for fid, label in self._input_labels.items():
            widget = field_widgets.get(fid)
            if widget:
                from PySide6.QtWidgets import QLineEdit, QComboBox
                if isinstance(widget, QLineEdit):
                    label.setText(widget.text() or "—")
                elif isinstance(widget, QComboBox):
                    label.setText(widget.currentText() or "—")

        # 更新计算过程文本
        calc_text = self._format_calc_text(result)
        self._calc_text.setText(calc_text)

        # 更新校核结论
        if self._step["has_check"]:
            self._update_badge(result)

    def _format_calc_text(self, result: dict[str, Any]) -> str:
        """根据 R 步骤 id 格式化计算过程文本。"""
        step_id = self._step["id"]
        inter = result.get("intermediate", {})
        torque = result.get("torque", {})
        stresses = result.get("stresses_mpa", {})
        forces = result.get("forces", {})
        fatigue = result.get("fatigue", {})
        thermal = result.get("thermal", {})

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
```

- [ ] **Step 2: 语法检查**

```bash
python3 -c "import py_compile; py_compile.compile('app/ui/pages/bolt_flowchart.py', doraise=True); print('OK')"
```

- [ ] **Step 3: 提交**

```bash
git add app/ui/pages/bolt_flowchart.py
git commit -m "feat(bolt/ui): add RStepDetailPage for R-step detail views

Read-only detail pages showing input echo, calculation steps,
and check verdict for each R0-R7 verification step.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: 在 BoltPage 中集成双 Tab 导航

**Files:**
- Modify: `app/ui/pages/bolt_page.py`

- [ ] **Step 1: 在 BoltPage 中引入 bolt_flowchart 并构建双 Tab 导航**

在 `bolt_page.py` 顶部 import 区新增：
```python
from app.ui.pages.bolt_flowchart import (
    FlowchartNavWidget, RStepDetailPage, R_STEPS,
)
```

修改 `__init__` 中左侧导航区域构建逻辑：

1. 在 `nav_layout` 中 `nav_title` 之后、`chapter_list` 之前，插入 tab 按钮和 `QStackedWidget`：
```python
# Tab 按钮
tab_bar = QHBoxLayout()
self.btn_input_tab = QPushButton("输入步骤", nav_card)
self.btn_input_tab.setObjectName("PrimaryButton")
self.btn_flow_tab = QPushButton("校核链路", nav_card)
tab_bar.addWidget(self.btn_input_tab)
tab_bar.addWidget(self.btn_flow_tab)
nav_layout.addLayout(tab_bar)

# 导航堆叠
self.nav_stack = QStackedWidget(nav_card)
self.nav_stack.addWidget(self.chapter_list)  # page 0
self.flowchart_nav = FlowchartNavWidget(nav_card)
self.nav_stack.addWidget(self.flowchart_nav)  # page 1
nav_layout.addWidget(self.nav_stack, 1)
```
移除原来直接 `nav_layout.addWidget(self.chapter_list, 1)`。

2. 构建 R 详情页并追加到 `chapter_stack`：
```python
self._r_pages: list[RStepDetailPage] = []
self._r_page_start_index = self.chapter_stack.count()
for step in R_STEPS:
    r_page = RStepDetailPage(step, self)
    self.chapter_stack.addWidget(r_page)
    self._r_pages.append(r_page)
```

3. 连接信号：
```python
self.btn_input_tab.clicked.connect(lambda: self._switch_nav_tab(0))
self.btn_flow_tab.clicked.connect(lambda: self._switch_nav_tab(1))
self.flowchart_nav.node_clicked.connect(self._on_flow_node_clicked)
```

- [ ] **Step 2: 实现 Tab 切换和节点点击方法**

```python
def _switch_nav_tab(self, tab_index: int) -> None:
    self.nav_stack.setCurrentIndex(tab_index)
    if tab_index == 0:
        self.btn_input_tab.setObjectName("PrimaryButton")
        self.btn_flow_tab.setObjectName("")
        # 恢复输入步骤当前选中页
        row = self.chapter_list.currentRow()
        if row >= 0:
            self.chapter_stack.setCurrentIndex(row)
    else:
        self.btn_flow_tab.setObjectName("PrimaryButton")
        self.btn_input_tab.setObjectName("")
        # 恢复流程图当前选中页
        self._on_flow_node_clicked(self.flowchart_nav._selected_index)
    self.btn_input_tab.style().polish(self.btn_input_tab)
    self.btn_flow_tab.style().polish(self.btn_flow_tab)

def _on_flow_node_clicked(self, r_index: int) -> None:
    self.chapter_stack.setCurrentIndex(self._r_page_start_index + r_index)
```

- [ ] **Step 3: 修改 `_calculate()` 以更新流程图和 R 详情页**

在 `_calculate()` 成功计算后（`self._last_result = result` 之后），追加：
```python
# 更新流程图导航节点
self.flowchart_nav.update_from_result(result)
# 更新 R 详情页
for r_page in self._r_pages:
    r_page.build_input_echo(self._field_specs, self._field_widgets, result)
    r_page.update_from_result(result, self._field_widgets)
```

- [ ] **Step 4: 在 `_apply_check_level_visibility` 中联动 R6 节点可见性**

在现有方法末尾追加：
```python
self.flowchart_nav.set_r6_visible(show_fatigue)
```

- [ ] **Step 5: 运行全量测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **Step 6: 手动启动应用验证**

```bash
python3 app/main.py
```
验证：
1. 左侧显示"输入步骤"和"校核链路"两个 tab
2. 点击"校核链路"→ 显示 R0-R7 流程图节点
3. 点击节点 → 右侧显示对应 R 详情页
4. 执行校核 → 流程图节点更新数值和 Badge，R 详情页刷新
5. 切换校核层级 → R6 节点在 basic/thermal 下隐藏

- [ ] **Step 7: 提交**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): integrate dual-tab nav with flowchart

- Left sidebar: 'Input Steps' / 'Verification Chain' tab switch
- Click R-node -> shows corresponding RStepDetailPage
- Calculation updates both flowchart badges and R detail pages
- R6 visibility synced with check level

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Chunk 4: 收尾 — 测试案例更新 + 全量验证

### Task 8: 更新测试案例 + 最终验证

**Files:**
- Modify: `examples/input_case_01.json`, `examples/input_case_02.json`

- [ ] **Step 1: 确认输入测试案例已更新**

确认 Task 2 Step 5 已将 `"p_G_allow": 700.0` 添加到两个 input JSON。如未执行则补充。

- [ ] **Step 2: 运行 CLI 生成新的输出**

```bash
python3 src/vdi2230_tool.py --input examples/input_case_01.json --output examples/output_case_01.json
python3 src/vdi2230_tool.py --input examples/input_case_02.json --output examples/output_case_02.json
```

- [ ] **Step 3: 检查输出中新增字段存在**

验证 output JSON 包含：
- `calculation_mode: "design"`
- `r3_note`
- `checks.bearing_pressure_ok`
- `stresses_mpa.p_bearing`

- [ ] **Step 4: 运行全量测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
预期：全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add examples/
git commit -m "chore: update test case JSONs with R7 bearing pressure

Add p_G_allow to input cases, regenerate output cases with
new fields: calculation_mode, r3_note, bearing_pressure_ok.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
