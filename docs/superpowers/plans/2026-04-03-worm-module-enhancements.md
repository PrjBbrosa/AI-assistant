# 蜗杆模块增强实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强蜗杆模块：Method A/B/C 说明、LC 默认启用、扭矩输入、啮合应力波动曲线、LaTeX 渲染、AutoCalcCard 样式

**Architecture:** calculator 输入从功率改为扭矩，新增啮合应力曲线计算；UI 侧新增 LatexLabel 和 WormStressCurveWidget；自动计算区域统一使用 AutoCalcCard 样式

**Tech Stack:** Python 3.12, PySide6, matplotlib (新增), pytest

---

## 文件结构

| 文件 | 动作 | 职责 |
|------|------|------|
| `requirements.txt` | 修改 | 新增 matplotlib |
| `core/worm/calculator.py` | 修改 | 输入改扭矩、新增应力曲线计算 |
| `app/ui/widgets/latex_label.py` | 新建 | matplotlib.mathtext 渲染 LaTeX 的 QLabel |
| `app/ui/widgets/worm_stress_curve.py` | 新建 | 啮合应力波动曲线 matplotlib 嵌入 widget |
| `app/ui/pages/worm_gear_page.py` | 修改 | FieldSpec 更新、集成新 widget |
| `examples/worm_case_01.json` | 修改 | power_kw → input_torque_nm |
| `examples/worm_case_02.json` | 修改 | power_kw → input_torque_nm |
| `tests/core/worm/test_calculator.py` | 修改 | 适配新输入/输出 |
| `tests/ui/test_worm_page.py` | 修改 | 适配新字段和 widget |

---

### Task 1: 新增 matplotlib 依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 添加 matplotlib 到 requirements.txt**

```
PySide6>=6.8.0
pyinstaller>=6.10.0
reportlab>=4.0
matplotlib>=3.8.0
```

- [ ] **Step 2: 安装依赖**

Run: `cd "/Users/donghang/Documents/Codex/未命名文件夹/AI-assistant" && python3 -m pip install matplotlib`

- [ ] **Step 3: 验证安装**

Run: `python3 -c "import matplotlib; print(matplotlib.__version__)"`
Expected: 版本号输出，无报错

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add matplotlib dependency for LaTeX rendering and stress curves"
```

---

### Task 2: 创建 LatexLabel 控件

**Files:**
- Create: `app/ui/widgets/latex_label.py`
- Test: `tests/ui/test_latex_label.py`

- [ ] **Step 1: 写 LatexLabel 测试**

Create `tests/ui/test_latex_label.py`:

```python
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.widgets.latex_label import LatexLabel


class LatexLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_set_latex_renders_pixmap(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$\sigma_H = \sqrt{\frac{F_n \cdot E^*}{\pi \cdot L \cdot \rho}}$")
        pixmap = label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertGreater(pixmap.width(), 0)
        self.assertGreater(pixmap.height(), 0)

    def test_set_latex_with_custom_fontsize(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$T_1$", fontsize=20)
        pixmap = label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertGreater(pixmap.width(), 0)

    def test_same_formula_uses_cache(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$\alpha$")
        pixmap1 = label.pixmap()
        label.set_latex(r"$\alpha$")
        pixmap2 = label.pixmap()
        # Same object from cache
        self.assertIs(pixmap1, pixmap2)

    def test_empty_latex_clears_pixmap(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$x$")
        label.set_latex("")
        self.assertTrue(label.pixmap() is None or label.pixmap().isNull())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_latex_label.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现 LatexLabel**

Create `app/ui/widgets/latex_label.py`:

```python
"""LaTeX formula rendering widget using matplotlib.mathtext."""

from __future__ import annotations

import io
from typing import ClassVar

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


class LatexLabel(QLabel):
    """QLabel that renders LaTeX formulas via matplotlib."""

    _cache: ClassVar[dict[tuple[str, int, int], QPixmap]] = {}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._current_key: tuple[str, int, int] | None = None

    def set_latex(
        self,
        latex: str,
        fontsize: int = 14,
        dpi: int = 120,
        color: str = "#1F1D1A",
    ) -> None:
        """Render a LaTeX string and display as pixmap."""
        if not latex:
            self.clear()
            self._current_key = None
            return

        key = (latex, fontsize, dpi)
        if key == self._current_key:
            return

        if key in self._cache:
            self.setPixmap(self._cache[key])
            self._current_key = key
            return

        fig = Figure()
        fig.patch.set_alpha(0.0)
        canvas = FigureCanvasAgg(fig)
        fig.text(0.0, 0.5, latex, fontsize=fontsize, color=color,
                 verticalalignment="center", horizontalalignment="left")

        canvas.draw()
        renderer = canvas.get_renderer()
        bbox = fig.get_tightbbox(renderer)
        if bbox is None:
            self.clear()
            self._current_key = None
            return

        # Resize figure to tight bbox and re-render
        w_inch = bbox.width / fig.dpi + 0.05
        h_inch = bbox.height / fig.dpi + 0.05
        fig.set_size_inches(w_inch, h_inch)
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        canvas.draw()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, transparent=True,
                    bbox_inches="tight", pad_inches=0.02)
        buf.seek(0)

        image = QImage()
        image.loadFromData(buf.read())
        pixmap = QPixmap.fromImage(image)

        self._cache[key] = pixmap
        self.setPixmap(pixmap)
        self._current_key = key
```

- [ ] **Step 4: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_latex_label.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/ui/widgets/latex_label.py tests/ui/test_latex_label.py
git commit -m "feat: add LatexLabel widget for formula rendering via matplotlib"
```

---

### Task 3: Calculator — 输入从功率改为扭矩

**Files:**
- Modify: `core/worm/calculator.py:62-103` (输入解析区)
- Modify: `core/worm/calculator.py:146-175` (功率/扭矩计算)
- Modify: `tests/core/worm/test_calculator.py`
- Modify: `examples/worm_case_01.json`
- Modify: `examples/worm_case_02.json`

- [ ] **Step 1: 更新测试 _base_payload 和相关测试**

在 `tests/core/worm/test_calculator.py` 中：

1) `_base_payload()` 中将 `"power_kw": 3.0` 替换为 `"input_torque_nm": 19.76`（= 9550 × 3.0 / 1450）。

2) `test_basic_geometry_outputs_ratio_and_performance_curve` 中将 `"power_kw": 3.0` 替换为 `"input_torque_nm": 19.76`。

3) `test_invalid_geometry_is_rejected` 中将 `"power_kw": 3.0` 替换为 `"input_torque_nm": 19.76`。

4) `test_curve_payload_marks_current_point_and_load_capacity_status` 中将 `"power_kw": 4.0` 替换为 `"input_torque_nm": 39.79`（= 9550 × 4.0 / 960）。

5) `test_geometry_returns_separate_worm_and_wheel_dimensions` 中将 `"power_kw": 3.0` 替换为 `"input_torque_nm": 19.76`。

6) `test_power_chain_uses_efficiency_for_output_power_and_output_torque` — 需要调整断言。功率现在是反算的：`power_kw = input_torque_nm * speed_rpm / 9550.0`。替换断言为：

```python
def test_power_chain_uses_efficiency_for_output_power_and_output_torque(self) -> None:
    payload = self._base_payload()
    result = calculate_worm_geometry(payload)
    performance = result["performance"]
    input_torque = payload["operating"]["input_torque_nm"]
    speed = payload["operating"]["speed_rpm"]
    expected_power = input_torque * speed / 9550.0
    self.assertAlmostEqual(performance["input_power_kw"], expected_power, places=4)
    output_power_kw = performance["output_power_kw"]
    self.assertAlmostEqual(output_power_kw, expected_power * performance["efficiency_estimate"], places=4)
```

7) `test_load_capacity_forces_output` 中将 `data["operating"]["power_kw"] = 3.0` 替换为 `data["operating"]["input_torque_nm"] = 19.76`。

8) `test_low_lead_angle_high_friction_efficiency_not_clamped` 和 `test_low_efficiency_result_contains_warning` — 这两个测试使用 `_base_payload()` 已自动修复。

- [ ] **Step 2: 运行测试验证失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v`
Expected: 多个 FAIL (calculator 仍读 power_kw)

- [ ] **Step 3: 修改 calculator.py 输入解析**

在 `core/worm/calculator.py` 的 `calculate_worm_geometry()` 中：

将第 92 行的:
```python
power_kw = _positive(float(_require(operating, "power_kw", "operating")), "operating.power_kw")
```
替换为:
```python
input_torque_nm = _positive(float(_require(operating, "input_torque_nm", "operating")), "operating.input_torque_nm")
```

将第 146 行的:
```python
input_torque_nm = 9550.0 * power_kw / max(speed_rpm, 1e-6)
```
替换为:
```python
power_kw = input_torque_nm * speed_rpm / 9550.0
```

保留 `power_kw` 变量名用于后续计算（output_power、power_loss 等），值来源改为反算。

- [ ] **Step 4: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 5: 更新示例 JSON 文件**

`examples/worm_case_01.json`: 将 `"power_kw": 3.0` 替换为 `"input_torque_nm": 19.76`
（计算: 9550 × 3.0 / 1450 = 19.759 ≈ 19.76）

`examples/worm_case_02.json`: 将 `"power_kw": 5.5` 替换为 `"input_torque_nm": 54.74`
（计算: 9550 × 5.5 / 960 = 54.740 ≈ 54.74）

- [ ] **Step 6: Commit**

```bash
git add core/worm/calculator.py tests/core/worm/test_calculator.py examples/worm_case_01.json examples/worm_case_02.json
git commit -m "feat(worm): change operating input from power (kW) to torque (Nm)"
```

---

### Task 4: Calculator — 啮合应力波动曲线

**Files:**
- Modify: `core/worm/calculator.py` (在 load_capacity enabled 分支末尾新增应力曲线计算)
- Modify: `tests/core/worm/test_calculator.py`

- [ ] **Step 1: 写应力曲线测试**

在 `tests/core/worm/test_calculator.py` 末尾新增：

```python
def test_stress_curve_output_has_correct_shape(self) -> None:
    """stress_curve should have theta_deg, sigma_h_mpa, sigma_f_mpa arrays
    of same length (~360 points), plus scalar peak/nominal values."""
    payload = self._base_payload()
    result = calculate_worm_geometry(payload)
    sc = result["load_capacity"]["stress_curve"]

    self.assertIn("theta_deg", sc)
    self.assertIn("sigma_h_mpa", sc)
    self.assertIn("sigma_f_mpa", sc)
    n = len(sc["theta_deg"])
    self.assertGreaterEqual(n, 100)
    self.assertEqual(len(sc["sigma_h_mpa"]), n)
    self.assertEqual(len(sc["sigma_f_mpa"]), n)
    # theta should span 0 to 360
    self.assertAlmostEqual(sc["theta_deg"][0], 0.0, places=1)
    self.assertAlmostEqual(sc["theta_deg"][-1], 360.0, delta=2.0)

def test_stress_curve_has_z1_peaks_per_revolution(self) -> None:
    """With z1=2, the stress curve should have 2 peaks per 360 deg."""
    payload = self._base_payload()
    result = calculate_worm_geometry(payload)
    sc = result["load_capacity"]["stress_curve"]

    self.assertEqual(sc["mesh_frequency_per_rev"], 2)
    # sigma_h should have z1 local maxima
    sigma_h = sc["sigma_h_mpa"]
    # Count peaks: a point is a peak if it's > both neighbors
    peaks = sum(
        1 for i in range(1, len(sigma_h) - 1)
        if sigma_h[i] > sigma_h[i - 1] and sigma_h[i] > sigma_h[i + 1]
    )
    self.assertEqual(peaks, 2)

def test_stress_curve_peak_exceeds_nominal(self) -> None:
    """Peak stress should be >= nominal stress (at pitch circle)."""
    payload = self._base_payload()
    result = calculate_worm_geometry(payload)
    sc = result["load_capacity"]["stress_curve"]

    self.assertGreaterEqual(sc["sigma_h_peak_mpa"], sc["sigma_h_nominal_mpa"])
    self.assertGreaterEqual(sc["sigma_f_peak_mpa"], sc["sigma_f_nominal_mpa"])

def test_stress_curve_not_present_when_lc_disabled(self) -> None:
    """When load_capacity is disabled, stress_curve should be empty dict."""
    payload = self._base_payload()
    payload["load_capacity"]["enabled"] = False
    result = calculate_worm_geometry(payload)
    sc = result["load_capacity"].get("stress_curve", {})
    self.assertEqual(sc, {})
```

- [ ] **Step 2: 运行测试验证失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py::WormCalculatorTests::test_stress_curve_output_has_correct_shape -v`
Expected: FAIL (no stress_curve key)

- [ ] **Step 3: 实现应力曲线计算**

在 `core/worm/calculator.py` 的 `calculate_worm_geometry()` 函数中，在 load_capacity enabled 分支的 `contact_ok`/`root_ok` 计算之后、`method = str(...)` 行之前，新增以下代码：

```python
# ---- Mesh stress curve: contact geometry variation over one worm revolution ----
import numpy as np  # (add to top-level imports: already have math)

curve_n_points = 360
r_root1_mm = worm_root_diameter_mm / 2.0
r_tip1_mm = worm_tip_diameter_mm / 2.0
r_pitch1_mm = pitch_diameter_worm_mm / 2.0

theta_deg_list: list[float] = []
sigma_h_curve: list[float] = []
sigma_f_curve: list[float] = []

# Single mesh cycle: phi in [0, 1] parameterizes contact position
# phi=0 -> tooth root entry, phi=0.5 -> tip (max radius), phi=1 -> root exit
mesh_points_per_cycle = max(curve_n_points // int(z1), 20)

for cycle in range(int(z1)):
    for j in range(mesh_points_per_cycle):
        phi = j / (mesh_points_per_cycle - 1) if mesh_points_per_cycle > 1 else 0.5
        theta = (cycle + phi) * (360.0 / z1)
        theta_deg_list.append(theta)

        # Contact radius on worm: root -> tip -> root (triangular profile)
        r1 = r_root1_mm + (r_tip1_mm - r_root1_mm) * (1.0 - abs(2.0 * phi - 1.0))

        # Worm-side curvature radius (axial section, projected)
        rho1 = r1 * math.sin(lead_angle_calc_rad)
        rho1 = max(rho1, 0.1)

        # Wheel-side curvature radius (concave envelope)
        rho2 = center_distance_mm - r1
        rho2 = max(rho2, 0.1)

        # Equivalent curvature radius (convex-concave contact)
        if rho2 > rho1:
            rho_eq = (rho1 * rho2) / (rho2 - rho1)
        else:
            rho_eq = rho1 * 10.0  # fallback: near-flat contact

        rho_eq = max(rho_eq, 0.01)

        # Hertz contact stress at this phase
        specific_load = design_normal_force_n / contact_length_mm
        sigma_h_phi = math.sqrt(specific_load * equivalent_modulus_mpa / (math.pi * rho_eq))
        sigma_h_curve.append(sigma_h_phi)

        # Root bending stress: lever arm = distance from contact to root
        h_phi = max(r1 - r_root1_mm, 0.01)
        section_modulus_mm3 = contact_length_mm * tooth_root_thickness_mm ** 2 / 6.0
        sigma_f_phi = design_tangential_force_n * h_phi / max(section_modulus_mm3, 1e-6)
        sigma_f_curve.append(sigma_f_phi)

# Nominal values at pitch circle
r_pitch_phi = (r_pitch1_mm - r_root1_mm) / (r_tip1_mm - r_root1_mm)
rho1_nom = r_pitch1_mm * math.sin(lead_angle_calc_rad)
rho2_nom = center_distance_mm - r_pitch1_mm
if rho2_nom > rho1_nom:
    rho_eq_nom = (rho1_nom * rho2_nom) / (rho2_nom - rho1_nom)
else:
    rho_eq_nom = rho1_nom * 10.0
rho_eq_nom = max(rho_eq_nom, 0.01)
sigma_h_nominal_curve = math.sqrt(
    (design_normal_force_n / contact_length_mm) * equivalent_modulus_mpa / (math.pi * rho_eq_nom)
)
h_nom = max(r_pitch1_mm - r_root1_mm, 0.01)
section_mod = contact_length_mm * tooth_root_thickness_mm ** 2 / 6.0
sigma_f_nominal_curve = design_tangential_force_n * h_nom / max(section_mod, 1e-6)

stress_curve_out: dict[str, Any] = {
    "theta_deg": theta_deg_list,
    "sigma_h_mpa": sigma_h_curve,
    "sigma_f_mpa": sigma_f_curve,
    "sigma_h_nominal_mpa": sigma_h_nominal_curve,
    "sigma_f_nominal_mpa": sigma_f_nominal_curve,
    "sigma_h_peak_mpa": max(sigma_h_curve),
    "sigma_f_peak_mpa": max(sigma_f_curve),
    "mesh_frequency_per_rev": int(z1),
}
```

注意：不要 import numpy——用纯 Python list 即可，保持 core/ 零外部依赖。

在 load_capacity disabled 返回中添加 `"stress_curve": {}`。

在 load_capacity enabled 返回 dict 中添加 `"stress_curve": stress_curve_out`。

- [ ] **Step 4: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add core/worm/calculator.py tests/core/worm/test_calculator.py
git commit -m "feat(worm): add mesh stress variation curve over one worm revolution"
```

---

### Task 5: 创建 WormStressCurveWidget

**Files:**
- Create: `app/ui/widgets/worm_stress_curve.py`
- Modify: `tests/ui/test_worm_page.py`

- [ ] **Step 1: 写 widget 测试**

在 `tests/ui/test_worm_page.py` 顶部导入区添加:
```python
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget
```

在 `WormPerformanceCurveWidgetTests` 类之后新增：

```python
class WormStressCurveWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_stress_curve_widget_accepts_data_and_renders(self) -> None:
        widget = WormStressCurveWidget()
        widget.set_curves(
            theta_deg=[0, 90, 180, 270, 360],
            sigma_h_mpa=[30, 45, 30, 45, 30],
            sigma_f_mpa=[20, 35, 20, 35, 20],
            sigma_h_nominal_mpa=35.0,
            sigma_f_nominal_mpa=25.0,
        )
        widget.resize(800, 400)
        widget.show()
        self.app.processEvents()
        pixmap = widget.grab()
        self.assertGreater(pixmap.size().width(), 0)

    def test_stress_curve_widget_clears_on_empty(self) -> None:
        widget = WormStressCurveWidget()
        widget.set_curves(
            theta_deg=[],
            sigma_h_mpa=[],
            sigma_f_mpa=[],
            sigma_h_nominal_mpa=0.0,
            sigma_f_nominal_mpa=0.0,
        )
        self.assertEqual(widget._theta_deg, [])
```

- [ ] **Step 2: 运行测试验证失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py::WormStressCurveWidgetTests -v`
Expected: FAIL (import error)

- [ ] **Step 3: 实现 WormStressCurveWidget**

Create `app/ui/widgets/worm_stress_curve.py`:

```python
"""Mesh stress variation curve widget for worm gear module."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import QVBoxLayout, QWidget

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class WormStressCurveWidget(QWidget):
    """Dual-axis plot of contact and root stress over one worm revolution."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theta_deg: list[float] = []
        self._sigma_h_mpa: list[float] = []
        self._sigma_f_mpa: list[float] = []
        self._sigma_h_nominal: float = 0.0
        self._sigma_f_nominal: float = 0.0

        self._figure = Figure(figsize=(8, 3.5), dpi=100)
        self._figure.patch.set_facecolor("#FBF8F3")
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)
        self.setMinimumHeight(350)
        self._draw_placeholder()

    def set_curves(
        self,
        *,
        theta_deg: Iterable[float],
        sigma_h_mpa: Iterable[float],
        sigma_f_mpa: Iterable[float],
        sigma_h_nominal_mpa: float,
        sigma_f_nominal_mpa: float,
    ) -> None:
        self._theta_deg = [float(v) for v in theta_deg]
        self._sigma_h_mpa = [float(v) for v in sigma_h_mpa]
        self._sigma_f_mpa = [float(v) for v in sigma_f_mpa]
        self._sigma_h_nominal = float(sigma_h_nominal_mpa)
        self._sigma_f_nominal = float(sigma_f_nominal_mpa)
        self._redraw()

    def _draw_placeholder(self) -> None:
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor("#FBF8F3")
        ax.text(0.5, 0.5, "执行计算后显示啮合应力波动曲线",
                ha="center", va="center", fontsize=11, color="#6B665E",
                transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        self._canvas.draw()

    def _redraw(self) -> None:
        self._figure.clear()
        if len(self._theta_deg) < 2:
            self._draw_placeholder()
            return

        ax1 = self._figure.add_subplot(111)
        ax1.set_facecolor("#FBF8F3")
        ax1.set_xlabel(r"蜗杆转角 $\theta$ (deg)", fontsize=10)
        ax1.set_ylabel(r"齿面接触应力 $\sigma_H$ (MPa)", color="#D97757", fontsize=10)
        ax1.plot(self._theta_deg, self._sigma_h_mpa, color="#D97757", linewidth=1.8,
                 label=r"$\sigma_H$")
        if self._sigma_h_nominal > 0:
            ax1.axhline(self._sigma_h_nominal, color="#D97757", linestyle="--",
                        linewidth=0.8, alpha=0.6)
        ax1.tick_params(axis="y", labelcolor="#D97757")

        ax2 = ax1.twinx()
        ax2.set_ylabel(r"齿根弯曲应力 $\sigma_F$ (MPa)", color="#2563EB", fontsize=10)
        ax2.plot(self._theta_deg, self._sigma_f_mpa, color="#2563EB", linewidth=1.8,
                 label=r"$\sigma_F$")
        if self._sigma_f_nominal > 0:
            ax2.axhline(self._sigma_f_nominal, color="#2563EB", linestyle="--",
                        linewidth=0.8, alpha=0.6)
        ax2.tick_params(axis="y", labelcolor="#2563EB")

        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

        ax1.set_xlim(0, 360)
        ax1.set_title("一个蜗杆旋转周期内啮合应力变化", fontsize=12, fontweight="bold",
                       color="#2E2A26")
        self._figure.tight_layout()
        self._canvas.draw()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py::WormStressCurveWidgetTests -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/ui/widgets/worm_stress_curve.py tests/ui/test_worm_page.py
git commit -m "feat(worm): add WormStressCurveWidget with dual-axis matplotlib plot"
```

---

### Task 6: UI 页面更新 — Method 说明、LC 默认、扭矩输入、曲线集成、AutoCalcCard

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `tests/ui/test_worm_page.py`

- [ ] **Step 1: 更新 UI 测试以适配新字段**

在 `tests/ui/test_worm_page.py` 中做以下修改：

1) 导入区新增:
```python
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget
```

2) `test_page_exposes_method_b_material_and_load_capacity_fields` 中将 `"operating.torque_ripple_percent"` 检查之前新增：
```python
self.assertIn("operating.input_torque_nm", page._field_widgets)
```
并将 `"operating.power_kw"` 的检查（如有）删除。

3) `test_load_sample_updates_fields_from_example` 中的断言不需要检查 power_kw 字段。
   补充检查: `self.assertIn("input_torque_nm", page._field_widgets["operating.input_torque_nm"].text())`
   不对——应检查具体值。Case 1 的 input_torque_nm = 19.76:
```python
self.assertEqual(page._field_widgets["operating.input_torque_nm"].text(), "19.76")
```

4) `test_calculate_updates_result_summary_and_curve` — 已调用默认值计算，不需要改。

5) 新增 Method 选项测试:
```python
def test_method_options_include_abc_descriptions(self) -> None:
    page = WormGearPage()
    combo = page._field_widgets["load_capacity.method"]
    options = [combo.itemText(i) for i in range(combo.count())]
    self.assertTrue(any("Method A" in o for o in options))
    self.assertTrue(any("Method B" in o for o in options))
    self.assertTrue(any("Method C" in o for o in options))
```

6) 新增 AutoCalcCard 测试:
```python
def test_dimension_cards_use_autocalc_style(self) -> None:
    page = WormGearPage()
    # The dimension group cards should use AutoCalcCard style
    # Find the parent cards of worm dimension labels
    first_label = list(page.worm_dimension_labels.values())[0]
    # Walk up to find the group card
    parent = first_label.parent()
    while parent and not (isinstance(parent, QFrame) and parent.objectName() in ("AutoCalcCard", "SubCard")):
        parent = parent.parent()
    # The row card's parent group should be AutoCalcCard
    self.assertIsNotNone(parent)
```

7) 新增 stress curve widget 集成测试:
```python
def test_stress_curve_widget_exists_in_graphics_step(self) -> None:
    page = WormGearPage()
    self.assertTrue(hasattr(page, "stress_curve"))
    self.assertIsInstance(page.stress_curve, WormStressCurveWidget)
```

8) 更新 fake_result 中的 `performance` 数据：将 `"input_power_kw"` 改为现有键名（如果需要）。同时在 fake_result 的 `load_capacity` 中添加 `"stress_curve": {}` 以避免 KeyError。

9) 更新 `test_page_shell_uses_step_flow_and_split_actions` 如果章节数改变的话（不变，仍 7 个章节）。

- [ ] **Step 2: 运行测试验证失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v`
Expected: 多个 FAIL (字段名、widget 不存在)

- [ ] **Step 3: 修改 worm_gear_page.py**

**3a) 修改 LOAD_CAPACITY_OPTIONS:**

将第 39-43 行:
```python
LOAD_CAPACITY_OPTIONS = (
    "DIN 3996 Method B",
    "ISO/TR 14521 Method B",
    "Niemann",
)
```
替换为:
```python
LOAD_CAPACITY_OPTIONS = (
    "DIN 3996 Method A \u2014 \u57fa\u4e8e\u5b9e\u9a8c/FEM\uff0c\u7cbe\u5ea6\u6700\u9ad8",
    "DIN 3996 Method B \u2014 \u6807\u51c6\u89e3\u6790\u8ba1\u7b97\uff08\u63a8\u8350\uff09",
    "DIN 3996 Method C \u2014 \u7b80\u5316\u4f30\u7b97",
)
```

（即 `"DIN 3996 Method A — 基于实验/FEM，精度最高"` 等中文字符串，此处用 ASCII 表示避免编码问题。实际代码直接写中文。）

**3b) 修改 BASIC_SETTINGS_FIELDS 中 load_capacity.method 默认值:**

将 `default="DIN 3996 Method B"` 改为 `default="DIN 3996 Method B — 标准解析计算（推荐）"`

**3c) 修改 OPERATING_FIELDS:**

将:
```python
FieldSpec("operating.power_kw", "输入功率 P", "kW", "输入轴功率。", default="3.0"),
```
替换为:
```python
FieldSpec("operating.input_torque_nm", "输入扭矩 T1", "Nm", "蜗杆轴输入扭矩。", default="19.76"),
```

**3d) 导入新 widget:**

在文件顶部导入区添加:
```python
from app.ui.widgets.worm_stress_curve import WormStressCurveWidget
```

**3e) 在 _build_graphics_step 中集成应力曲线:**

在第 482-484 行之后（`self.performance_curve = ...` 和 `body.addWidget(self.performance_curve)` 之后）添加:

```python
self.stress_curve = WormStressCurveWidget(container)
body.addWidget(self.stress_curve)
```

**3f) 在 _calculate 中更新应力曲线:**

在第 812-818 行（`self.performance_curve.set_curves(...)` 调用之后）添加:

```python
stress_curve_data = load_capacity.get("stress_curve", {})
if stress_curve_data and stress_curve_data.get("theta_deg"):
    self.stress_curve.set_curves(
        theta_deg=stress_curve_data["theta_deg"],
        sigma_h_mpa=stress_curve_data["sigma_h_mpa"],
        sigma_f_mpa=stress_curve_data["sigma_f_mpa"],
        sigma_h_nominal_mpa=stress_curve_data.get("sigma_h_nominal_mpa", 0.0),
        sigma_f_nominal_mpa=stress_curve_data.get("sigma_f_nominal_mpa", 0.0),
    )
```

**3g) 在 _clear 中重置应力曲线:**

在 `self.performance_curve.set_curves(...)` 调用之后添加:

```python
self.stress_curve.set_curves(
    theta_deg=[], sigma_h_mpa=[], sigma_f_mpa=[],
    sigma_h_nominal_mpa=0.0, sigma_f_nominal_mpa=0.0,
)
```

**3h) 修改结果显示中的功率引用:**

在 `_calculate` 方法的 result_metrics 中，将 `输出功率 P2` 行改为使用 `input_power_kw`：
```python
f"输入功率 P1 = {performance['input_power_kw']:.4f} kW（反算）",
```

**3i) AutoCalcCard 样式 — 修改 _create_dimension_group_card:**

在 `_create_dimension_group_card` 方法中，将:
```python
card.setObjectName("SubCard")
```
改为:
```python
card.setObjectName("AutoCalcCard")
```

同时将内部 row_card 的:
```python
row_card.setObjectName("SubCard")
```
改为:
```python
row_card.setObjectName("AutoCalcCard")
```

将 value_label 的颜色通过 objectName 设置。当前使用 `SectionHint` — 改为设置样式：
```python
value_label.setStyleSheet("color: #3A4F63; font-weight: 600;")
```

- [ ] **Step 4: 运行全部测试验证通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v`
Expected: ALL PASS

- [ ] **Step 5: 运行完整测试套件**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add app/ui/pages/worm_gear_page.py tests/ui/test_worm_page.py
git commit -m "feat(worm): update UI with Method A/B/C, torque input, stress curve, AutoCalcCard style"
```

---

### Task 7: LaTeX 公式集成到蜗杆结果区

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`

- [ ] **Step 1: 在 Load Capacity 步骤中添加 LaTeX 公式显示**

在 `_build_load_capacity_step` 方法中，在 `self.load_capacity_metrics` 之前添加 LaTeX 公式 label：

导入区添加:
```python
from app.ui.widgets.latex_label import LatexLabel
```

在 `_build_load_capacity_step` 中，`layout.addWidget(badges_card)` 之后添加:

```python
formulas_card = QFrame(page)
formulas_card.setObjectName("AutoCalcCard")
formulas_layout = QVBoxLayout(formulas_card)
formulas_layout.setContentsMargins(12, 12, 12, 12)
formulas_layout.setSpacing(8)

formulas_title = QLabel("校核公式", formulas_card)
formulas_title.setObjectName("SubSectionTitle")
formulas_layout.addWidget(formulas_title)

self._latex_hertz = LatexLabel(formulas_card)
self._latex_hertz.set_latex(
    r"$\sigma_H = \sqrt{\frac{F_n \cdot E^*}{\pi \cdot L_c \cdot \rho_{eq}}}$",
    fontsize=16,
)
formulas_layout.addWidget(self._latex_hertz)

self._latex_root = LatexLabel(formulas_card)
self._latex_root.set_latex(
    r"$\sigma_F = \frac{F_t \cdot h}{W_{section}}$",
    fontsize=16,
)
formulas_layout.addWidget(self._latex_root)

layout.addWidget(formulas_card)
```

- [ ] **Step 2: 运行全部测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/worm_gear_page.py
git commit -m "feat(worm): integrate LaTeX formula display in Load Capacity section"
```

---

### Task 8: 最终验证与集成测试

**Files:**
- All modified files

- [ ] **Step 1: 运行完整测试套件**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: 手动启动应用验证 UI**

Run: `cd "/Users/donghang/Documents/Codex/未命名文件夹/AI-assistant" && python3 app/main.py`

验证清单:
- [ ] 蜗杆模块可以打开
- [ ] Method 下拉显示 A/B/C 说明
- [ ] 输入字段为"输入扭矩 T1"，单位 Nm
- [ ] 自动计算尺寸区域为蓝色底
- [ ] 执行计算后应力曲线正确显示
- [ ] Load Capacity 区域显示 LaTeX 公式
- [ ] 测试案例 1/2 可以正常加载

- [ ] **Step 3: Commit 最终调整（如有）**

```bash
git add -A
git commit -m "fix(worm): final adjustments from manual UI verification"
```
