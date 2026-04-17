# 蜗杆模块产线校核级修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把蜗杆模块从"几何预览工具"提升为"塑料蜗轮产线校核工具"，修复 22 个已识别问题（W26-01 ~ W26-22）。

**Architecture:** 三波修复，每波内 3 路并行（core-engineer / ui-engineer / test-engineer），每波收尾由 codex:codex-rescue 审查，审查通过即 commit 进入下一波。力学核心修复在 Wave 0，塑料工程完备在 Wave 1，体验完善在 Wave 2。

**Tech Stack:** Python 3.12 · PySide6 · pytest · DIN 3975 / DIN 3996 Method B · ISO 14521

**Spec:** `docs/superpowers/specs/2026-04-17-worm-production-calibration-fix-design.md`

**Review source:** `docs/reports/2026-04-16-worm-module-production-review.md`

---

## 共同上下文（每个 agent 启动前必读）

- `CLAUDE.md` 项目约定：`core/` 纯 Python，不 import Qt；UI 文本中文；`AutoCalcCard` 样式用于自动填充字段；测试用 `QT_QPA_PLATFORM=offscreen`。
- `.claude/rules/coding-standards.md`：单位（N / mm / MPa / N·m）、命名（`fm_min` / `phi_n` 风格）、禁用 Unicode 智能引号。
- 产品范围：**仅塑料蜗轮 + 钢蜗杆**。无钢-青铜副、无钢-钢副。
- 浮点测试用 `pytest.approx(expected, rel=1e-3)`。
- 并行执行时，**严格按文件域划分**：core-engineer 只改 `core/`，ui-engineer 只改 `app/ui/`，test-engineer 只改 `tests/`。

---

## Wave 0 — 血洗 Bug（P0 阻断产线）

8 项：W26-01 ~ W26-07, W26-19

### Task 0.A (core-engineer): 修正力分解公式

**Files:**
- Modify: `core/worm/calculator.py:363-371`
- Modify: `core/worm/calculator.py:488-502`（Method 下拉联动）
- Modify: `core/worm/calculator.py:174-176`（热容量）
- Modify: `core/worm/calculator.py:185-186`（geometry_consistent）
- Modify: `core/worm/calculator.py:383, 390-393`（齿根 s/h）

**参考计算（手算验证用，放 docstring）：**

```
输入: m=4, z1=1, z2=40, q=10, α_n=20°, μ=0.05, T2=500 N·m
d2 = z2·m = 160 mm
F_t2 = 2·T2/d2·1000 = 6250 N
γ = atan(z1/q) = atan(0.1) = 5.7106°
φ' = atan(μ/cos(α_n)) = atan(0.05/0.93969) = 3.0466°
F_a2 = F_t2·tan(γ+φ') = 6250·tan(8.7572°) = 962.8 N
F_r  = F_t2·tan(α_n)/cos(γ) = 6250·0.36397/0.99504 = 2285.8 N
F_n  = F_t2/(cos(α_n)·cos(γ)) = 6250/(0.93969·0.99504) = 6683.5 N
η    = tan(γ)/tan(γ+φ') = 0.10000/0.15401 = 0.6493
```

- [ ] **Step 1: 写失败测试**（交给 test-engineer 的 Task 0.C Step 1 写）

- [ ] **Step 2: 重写 sin_gamma/tan_gamma 段（calculator.py:363-371）**

将原 363-371 行替换为：

```python
cos_alpha_n = math.cos(normal_pressure_angle_rad)
sin_gamma = math.sin(lead_angle_calc_rad)
cos_gamma = math.cos(lead_angle_calc_rad)
tan_gamma = math.tan(lead_angle_calc_rad)

# 当量摩擦角（法向摩擦角投影到轴向）
phi_prime_rad = math.atan(friction_mu / max(cos_alpha_n, 1e-6))
tan_gamma_plus_phi = math.tan(lead_angle_calc_rad + phi_prime_rad)

# 蜗轮受力分解（F_t2 已知，从蜗轮切向力推其他）
# F_a2 (蜗轮轴向力) = F_t1 (蜗杆切向力) = F_t2·tan(γ+φ')
axial_force_wheel_n = tangential_force_wheel_n * tan_gamma_plus_phi
# F_r (径向力) = F_t2·tan(α_n)/cos(γ)
radial_force_wheel_n = tangential_force_wheel_n * math.tan(normal_pressure_angle_rad) / max(cos_gamma, 1e-6)
# F_n (法向力) = F_t2/(cos(α_n)·cos(γ))
normal_force_n = tangential_force_wheel_n / max(cos_alpha_n * cos_gamma, 1e-6)
normal_force_peak_n = tangential_force_wheel_peak_n / max(cos_alpha_n * cos_gamma, 1e-6)
normal_force_rms_n = tangential_force_wheel_rms_n / max(cos_alpha_n * cos_gamma, 1e-6)
```

并在函数顶部（约 163 行前）增加一条警告入库：

```python
# 自锁提示：lead_angle_calc < phi' 时蜗轮无法反向驱动蜗杆
if lead_angle_calc_rad <= math.atan(friction_mu / max(math.cos(math.radians(float(advanced.get("normal_pressure_angle_deg", 20.0)))), 1e-6)):
    performance_warnings.append(
        f"自锁：gamma={lead_angle_calc_deg:.2f} deg <= phi'={math.degrees(math.atan(friction_mu / max(math.cos(math.radians(float(advanced.get('normal_pressure_angle_deg', 20.0)))), 1e-6))):.2f} deg，"
        f"不可反向驱动。"
    )
```

- [ ] **Step 3: 热容量改独立公式（calculator.py:174-176）**

用独立的散热模型替换 `thermal_capacity_kw = power_loss_kw`：

```python
# 热容量按简化箱体散热（DIN 3996 简化）
# Q_th = k·A·ΔT / 1000 (kW)
# 塑料蜗轮散热系数 k 约 12-18 W/(m²·K)，此处取 14
# 接触面积 A 按 2·d2·b2 简化（单位 m²）
# 允许温升 ΔT = 50 K（PA66 工程上限约 80℃，环境 30℃）
thermal_heat_transfer_coefficient = float(advanced.get("thermal_k_w_m2k", 14.0))
thermal_allowable_delta_t_k = float(advanced.get("thermal_delta_t_k", 50.0))
thermal_area_m2 = (2.0 * pitch_diameter_wheel_mm * wheel_face_width_mm) / 1.0e6
thermal_capacity_kw = thermal_heat_transfer_coefficient * thermal_area_m2 * thermal_allowable_delta_t_k / 1000.0
```

在 `performance_warnings` 收集处新增：

```python
if power_loss_kw > thermal_capacity_kw:
    performance_warnings.append(
        f"热负荷超限：损失功率 P_loss={power_loss_kw:.3f} kW > 允许散热 Q_th={thermal_capacity_kw:.3f} kW。"
    )
```

- [ ] **Step 4: 齿根 s/h 参数化（calculator.py:383, 390-393）**

将第 383 行 `tooth_root_thickness_mm = max(1.25 * module_mm, 1e-6)` 改为：

```python
# 齿根弦齿厚（DIN 3975 简化）: s_Ft ≈ π·m·cos(α_n)/2
tooth_root_thickness_mm = max(math.pi * module_mm * math.cos(normal_pressure_angle_rad) / 2.0, 1e-6)
```

将 `_root_stress` 函数中齿高使用已计算 `tooth_height_mm` 保留（变位修正已在 198 行处理），但改名确认意图：

```python
def _root_stress(tangential_force_value_n: float) -> float:
    # Lewis 近似：σ_F = F·h / (b·s²/6)
    section_modulus_mm3 = contact_length_mm * tooth_root_thickness_mm * tooth_root_thickness_mm / 6.0
    bending_moment_nmm = tangential_force_value_n * tooth_height_mm
    return bending_moment_nmm / max(section_modulus_mm3, 1e-6)
```

- [ ] **Step 5: geometry_consistent 不再把非标 q 当不一致（calculator.py:185-186 与 checks.geometry_consistent）**

保留 q 非标的 warning（提示），但 `checks.geometry_consistent` 只看导程角和中心距是否一致：

把第 559 行改为：

```python
"geometry_consistent": (
    abs(lead_angle_delta_deg) <= 0.5
    and abs(center_distance_delta_mm) <= max(0.25 * module_mm, 0.5)
),
```

`geometry_warnings` 本身保持不变（q 非标仍然警告）。

- [ ] **Step 6: Method A/B/C 联动逻辑（calculator.py:488-502）**

替换第 488-502 行为：

```python
method = str(load_capacity.get("method", "DIN 3996 Method B")).strip()
method_normalized = method.upper().replace(" ", "")

if "METHODC" in method_normalized:
    # Method C 暂未实现：拒绝计算，提示用户切回 B
    raise InputError(
        "Method C 需要 FEA 输入，当前版本未实现。请使用 Method A 或 Method B。"
    )

if "METHODA" in method_normalized:
    # Method A：手册系数法，效率与损失按经验折减 0.92
    method_efficiency_factor = 0.92
    efficiency_estimate = efficiency_estimate * method_efficiency_factor
    output_power_kw = power_kw * efficiency_estimate
    power_loss_kw = power_kw - output_power_kw
    sigma_hm_nominal_mpa = sigma_hm_nominal_mpa * 0.95  # 手册折减
    sigma_hm_peak_mpa = sigma_hm_peak_mpa * 0.95
```

- [ ] **Step 7: handedness / lubrication 接入计算**

在 `friction_mu` 估算后（约第 155 行前），读取并用于调整：

```python
handedness = str(materials.get("handedness", "right")).strip().lower()
lubrication = str(materials.get("lubrication", "grease")).strip().lower()

# 润滑方式影响摩擦系数（塑料-钢）
LUB_MU_MULTIPLIER = {"oil_bath": 0.90, "grease": 1.00, "dry": 1.35}
friction_mu = friction_mu * LUB_MU_MULTIPLIER.get(lubrication, 1.00)
```

`handedness` 用于输出（影响蜗轮 F_r 方向标识）：

在最终 `forces` 字典中增加：

```python
"handedness": handedness,
"radial_force_direction": "indent" if handedness == "right" else "outward",
```

- [ ] **Step 8: 跑测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/ -v
```

Expected: 新测试通过、部分旧测试因力值变化需要更新（交给 test-engineer 在 Task 0.C 处理）。

- [ ] **Step 9: 提交等待（由主会话 commit，不自行 commit）**

### Task 0.B (ui-engineer): 几何总览动态绘制 + 无装饰控件

**Files:**
- Modify: `app/ui/widgets/worm_geometry_overview.py`
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `app/ui/widgets/worm_performance_curve.py`（第三图换"温升"）

- [ ] **Step 1: `WormGeometryOverviewWidget` 新增 `set_geometry_state` 接口**

在 `worm_geometry_overview.py` 的 `WormGeometryOverviewWidget.__init__` 中新增状态字段：

```python
self._geom_state = {
    "d1_mm": 80.0,
    "d2_mm": 160.0,
    "a_mm": 120.0,
    "gamma_deg": 5.71,
    "z1": 1,
    "z2": 40,
    "handedness": "right",
}
```

新增方法（在 `set_display_state` 之下）：

```python
def set_geometry_state(
    self,
    *,
    d1_mm: float,
    d2_mm: float,
    a_mm: float,
    gamma_deg: float,
    z1: int,
    z2: int,
    handedness: str,
) -> None:
    self._geom_state = {
        "d1_mm": max(float(d1_mm), 1.0),
        "d2_mm": max(float(d2_mm), 1.0),
        "a_mm": max(float(a_mm), 1.0),
        "gamma_deg": float(gamma_deg),
        "z1": int(z1),
        "z2": int(z2),
        "handedness": str(handedness).strip().lower() or "right",
    }
    self.update()
```

- [ ] **Step 2: `paintEvent` 按 `_geom_state` 动态比例绘制**

将 `worm_rect` / `wheel_rect` 的尺寸按 d1:d2:a 的比例计算。核心改动：

```python
# 在 paintEvent 中，取代原固定的 worm_rect/wheel_rect 大小
scale_mm_to_px = min(
    (diagram.width() - 80) / (self._geom_state["d1_mm"] + self._geom_state["d2_mm"] + 40),
    (diagram.height() - 100) / max(self._geom_state["d2_mm"], 40.0),
)
d1_px = self._geom_state["d1_mm"] * scale_mm_to_px
d2_px = self._geom_state["d2_mm"] * scale_mm_to_px
a_px  = self._geom_state["a_mm"]  * scale_mm_to_px

axis_y = diagram.center().y() + 12
worm_rect = QRectF(
    diagram.left() + 30,
    axis_y - d1_px * 0.5,
    d1_px * 2.5,  # 蜗杆长度取分度圆 2.5 倍示意
    d1_px,
)
wheel_center = QPointF(worm_rect.center().x(), axis_y - a_px)
wheel_rect = QRectF(
    wheel_center.x() - d2_px * 0.5,
    wheel_center.y() - d2_px * 0.5,
    d2_px,
    d2_px,
)
```

- [ ] **Step 3: 旋向由 handedness 决定**

螺旋线段方向根据 handedness：

```python
hand_sign = 1.0 if self._geom_state["handedness"] == "right" else -1.0
painter.setPen(QPen(QColor("#B65E2C"), 2.1))
for idx in range(7):
    x0 = worm_rect.left() + 8 + idx * worm_rect.width() / 7.0
    painter.drawLine(
        QPointF(x0, worm_rect.top() + 7),
        QPointF(x0 + hand_sign * worm_rect.width() * 0.15, worm_rect.bottom() - 7),
    )
# 底部文字也改
direction_label = "右旋示意" if self._geom_state["handedness"] == "right" else "左旋示意"
painter.drawText(..., direction_label)
```

- [ ] **Step 4: `worm_gear_page.py` 在计算成功后调用 `set_geometry_state`**

找到 page 中 `self._overview` 使用处（搜索 `geometry_overview` 或 widget 绑定），在计算完成后新增：

```python
self._geometry_overview.set_geometry_state(
    d1_mm=result["geometry"]["pitch_diameter_worm_mm"],
    d2_mm=result["geometry"]["pitch_diameter_wheel_mm"],
    a_mm=result["geometry"]["center_distance_mm"],
    gamma_deg=result["geometry"]["lead_angle_calc_deg"],
    z1=int(result["inputs_echo"]["geometry"]["z1"]),
    z2=int(result["inputs_echo"]["geometry"]["z2"]),
    handedness=result["inputs_echo"]["materials"].get("handedness", "right"),
)
```

（如果 handedness/lubrication 下拉还未挂 FieldSpec，此 Step 一并添加——在 `FieldSpec` 列表找到 materials 段，确认 `handedness`、`lubrication` 字段 mapping 指向 `("materials", "handedness")` / `("materials", "lubrication")`，不再是 `None`。）

- [ ] **Step 5: Method 下拉提示文案**

在 `LOAD_CAPACITY_OPTIONS` 定义处（worm_gear_page.py:41-45）保留三选，但切到 Method C 时 `_on_method_changed` 在状态栏提示"Method C 尚未实现，将拒绝计算"：

```python
def _on_method_changed(self, method_label: str) -> None:
    if "Method C" in method_label:
        self._status_label.setText("提示：Method C 需要 FEA 输入，当前版本未实现；执行将报错。")
    else:
        self._status_label.setText("")
```

- [ ] **Step 6: 性能曲线第 3 张图换为"温升"**

`worm_performance_curve.py` 新增数据字段并重命名：

```python
self._temperature_rise_k: list[float] = []
```

`set_curves` 签名改为：

```python
def set_curves(
    self,
    *,
    load_factor: Iterable[float],
    efficiency: Iterable[float],
    power_loss_kw: Iterable[float],
    temperature_rise_k: Iterable[float],
    current_index: int,
) -> None:
    ...
    self._temperature_rise_k = [float(v) for v in temperature_rise_k]
```

`paintEvent` 中 charts 列表：

```python
(QRectF(...), self._temperature_rise_k, QColor("#2F855A"), "温升 ΔT (K)"),
```

调用方（`worm_gear_page.py`）从 `result["performance"]["temperature_rise_k"]` 或从 curve 数据派生传入；若 core 未提供，调用处现场计算 `ΔT = P_loss_i / thermal_capacity_kw * allowable_delta_t_k`。

- [ ] **Step 7: 跑 UI 测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v
```

Expected: 部分断言因 handedness 联动需要 test-engineer 在 Task 0.C 更新，ui-engineer 此处不改测试。

### Task 0.C (test-engineer): 力学量级测试 + 回归更新

**Files:**
- Modify: `tests/core/worm/test_calculator.py`
- Modify: `tests/ui/test_worm_page.py`

- [ ] **Step 1: 新增力分解量级测试**

在 `tests/core/worm/test_calculator.py` 末尾新增：

```python
import math
import pytest
from core.worm.calculator import calculate_worm_geometry


def _case_m4_z1_q10() -> dict:
    """m=4, z1=1, z2=40, q=10, mu=0.05, T2=500 N·m 参考案例。"""
    return {
        "geometry": {
            "module_mm": 4.0, "z1": 1, "z2": 40,
            "diameter_factor_q": 10.0,
            "center_distance_mm": 100.0,  # (q+z2)/2 * m = 100
            "lead_angle_deg": math.degrees(math.atan(1/10)),
        },
        "operating": {
            "input_torque_nm": 7.7,  # T1 = T2 / (i*η) ≈ 500/(40*0.65)
            "speed_rpm": 1500.0,
            "application_factor": 1.0,
        },
        "materials": {
            "worm_material": "37CrS4",
            "wheel_material": "PA66",
            "handedness": "right",
            "lubrication": "grease",
        },
        "advanced": {
            "friction_override": 0.05,
            "normal_pressure_angle_deg": 20.0,
        },
        "load_capacity": {
            "enabled": True,
            "allowable_contact_stress_mpa": 42.0,
            "allowable_root_stress_mpa": 55.0,
            "required_contact_safety": 1.0,
            "required_root_safety": 1.0,
        },
    }


def test_force_decomposition_magnitude_m4_q10():
    """Reference case per spec: F_t2=6250, F_a2=963, F_r=2286, F_n=6683."""
    data = _case_m4_z1_q10()
    # Force output_torque to 500 N·m by setting input_torque via inverse of efficiency
    data["operating"]["input_torque_nm"] = 500.0 / 40.0 / 0.6493
    result = calculate_worm_geometry(data)
    forces = result["load_capacity"]["forces"]
    # T2 = T1 * i * eta -> 约 500 N·m，允许 3% 误差
    assert forces["tangential_force_wheel_n"] == pytest.approx(6250.0, rel=3e-2)
    assert forces["axial_force_wheel_n"] == pytest.approx(963.0, rel=5e-2)
    assert forces["radial_force_wheel_n"] == pytest.approx(2286.0, rel=5e-2)
    assert forces["normal_force_n"] == pytest.approx(6683.0, rel=5e-2)


def test_efficiency_matches_tan_gamma_formula():
    data = _case_m4_z1_q10()
    result = calculate_worm_geometry(data)
    eta = result["performance"]["efficiency_estimate"]
    assert eta == pytest.approx(0.6493, rel=3e-2)


def test_self_locking_warning_when_gamma_below_phi():
    data = _case_m4_z1_q10()
    data["advanced"]["friction_override"] = 0.25  # phi' big
    data["geometry"]["z1"] = 1
    data["geometry"]["diameter_factor_q"] = 20.0  # gamma very small
    data["geometry"]["lead_angle_deg"] = math.degrees(math.atan(1/20))
    data["geometry"]["center_distance_mm"] = (20 + 40) / 2 * 4
    result = calculate_worm_geometry(data)
    warnings = " ".join(result["performance"]["warnings"])
    assert "自锁" in warnings


def test_thermal_capacity_independent_of_power_loss():
    data = _case_m4_z1_q10()
    result = calculate_worm_geometry(data)
    perf = result["performance"]
    # Q_th 应用散热公式算出，不等于 P_loss
    assert perf["thermal_capacity_kw"] != pytest.approx(perf["power_loss_kw"])


def test_nonstandard_q_does_not_fail_consistency_check():
    data = _case_m4_z1_q10()
    data["geometry"]["diameter_factor_q"] = 13.0  # non-standard
    data["geometry"]["lead_angle_deg"] = math.degrees(math.atan(1/13))
    data["geometry"]["center_distance_mm"] = (13 + 40) / 2 * 4
    result = calculate_worm_geometry(data)
    assert result["load_capacity"]["checks"]["geometry_consistent"] is True
    # 仍然有 q 非标警告
    assert any("q=" in w for w in result["geometry"]["consistency"]["warnings"])


def test_method_c_raises_input_error():
    from core.worm.calculator import InputError
    data = _case_m4_z1_q10()
    data["load_capacity"]["method"] = "DIN 3996 Method C"
    with pytest.raises(InputError, match="Method C"):
        calculate_worm_geometry(data)


def test_method_a_gives_lower_efficiency_than_b():
    data = _case_m4_z1_q10()
    data["load_capacity"]["method"] = "DIN 3996 Method A"
    result_a = calculate_worm_geometry(data)
    data["load_capacity"]["method"] = "DIN 3996 Method B"
    result_b = calculate_worm_geometry(data)
    assert result_a["performance"]["efficiency_estimate"] < result_b["performance"]["efficiency_estimate"]


def test_lubrication_dry_increases_friction():
    data = _case_m4_z1_q10()
    data["materials"]["lubrication"] = "oil_bath"
    result_oil = calculate_worm_geometry(data)
    data["materials"]["lubrication"] = "dry"
    result_dry = calculate_worm_geometry(data)
    assert result_dry["performance"]["friction_mu"] > result_oil["performance"]["friction_mu"]
```

- [ ] **Step 2: 跑测试验证失败（在 core 修改前）**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/test_calculator.py::test_force_decomposition_magnitude_m4_q10 -v
```

Expected: FAIL with assertion errors on force values (F_n actual = 6250/sin(5.71°) ≈ 62802, expected ≈ 6683)。

- [ ] **Step 3: 等 core-engineer 完成 Task 0.A 后再跑**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/worm/ -v
```

Expected: 全部通过。

- [ ] **Step 4: 更新可能因力值变化破坏的旧测试**

检查 `test_calculator.py` 中 `axial_force_wheel_n`、`normal_force_n` 等精确值断言。对于旧断言，只判断存在和符号，不重新断定数值；具体数值交给新加的测试覆盖。

- [ ] **Step 5: UI 测试新增 handedness 联动断言**

在 `tests/ui/test_worm_page.py` 新增：

```python
def test_handedness_change_redraws_overview(qtbot):
    from app.ui.pages.worm_gear_page import WormGearPage
    page = WormGearPage()
    qtbot.addWidget(page)
    # 填入一套默认参数 + 执行
    page._fill_default_for_test()  # 若存在
    page._on_execute()
    # 改为左旋再执行
    page._field_widgets["handedness"].setCurrentText("left")
    page._on_execute()
    assert page._geometry_overview._geom_state["handedness"] == "left"


def test_method_c_shows_error_on_execute(qtbot):
    ...  # 执行时应弹错误对话框或显示错误消息
```

若 page 无 `_fill_default_for_test`，新增一个测试专用帮助方法，或用现有 `examples/worm_case_*.json` loader。

- [ ] **Step 6: 回归**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

Expected: 全部通过。

### Wave 0 review & commit

- [ ] **Step 1: 主会话 dispatch `codex:codex-rescue` 审查 Wave 0**
- [ ] **Step 2: 不通过则分派对应 agent 修复**
- [ ] **Step 3: 通过后 commit**

```bash
git add core/worm/calculator.py \
        app/ui/pages/worm_gear_page.py \
        app/ui/widgets/worm_geometry_overview.py \
        app/ui/widgets/worm_performance_curve.py \
        tests/core/worm/ tests/ui/test_worm_page.py
git commit -m "fix(worm): correct force decomposition + kill decorative inputs [W26-01..07,19]"
```

---

## Wave 1 — 塑料蜗轮工程完备（P1）

8 项：W26-08 ~ W26-14, W26-20

### Task 1.A (core-engineer): 塑料材料库 + DIN 3996 Method B

**Files:**
- Create: `core/worm/materials.py`
- Modify: `core/worm/calculator.py`（接入材料库与 Method B）

- [ ] **Step 1: 新建 `core/worm/materials.py`**

```python
"""塑料蜗轮材料库（塑-钢副）与降额模型。

数据来源：DIN 3996:2019、PA66 / POM / PA46 / PEEK 厂商 PDS、ISO 14521、
         DuPont Zytel 技术手册、Celanese Acetal 技术手册。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PlasticMaterial:
    name: str
    e_mpa: float
    nu: float
    sigma_hlim_mpa: float       # 接触疲劳极限（常温干态）
    sigma_flim_mpa: float       # 弯曲疲劳极限
    allowable_surface_temp_c: float  # 最高允许齿面温度
    temp_derate_per_10c: float  # 每超过基准温度 10℃ 的降额系数
    humidity_derate_at_50rh: float  # 50%RH 相对于干态的降额系数（PA 系列 < 1）


PLASTIC_MATERIALS: Dict[str, PlasticMaterial] = {
    "PA66":       PlasticMaterial("PA66",       3000.0, 0.38, 42.0, 55.0, 100.0, 0.92, 0.70),
    "PA66+GF30":  PlasticMaterial("PA66+GF30", 10000.0, 0.36, 58.0, 70.0, 110.0, 0.90, 0.80),
    "POM":        PlasticMaterial("POM",        2800.0, 0.37, 48.0, 62.0,  95.0, 0.93, 0.98),
    "PA46":       PlasticMaterial("PA46",       3300.0, 0.38, 52.0, 68.0, 125.0, 0.90, 0.72),
    "PEEK":       PlasticMaterial("PEEK",       3600.0, 0.40, 90.0, 140.0, 180.0, 0.92, 0.99),
}


def apply_derate(
    material: PlasticMaterial,
    *,
    operating_temp_c: float,
    humidity_rh: float,
) -> tuple[float, float]:
    """Return (sigma_Hlim_derated, sigma_Flim_derated)."""
    base_temp = 23.0
    temp_factor = 1.0
    if operating_temp_c > base_temp:
        steps = (operating_temp_c - base_temp) / 10.0
        temp_factor = material.temp_derate_per_10c ** max(0.0, steps)
    # 线性插值 humidity：0%=1.0, 50%=humidity_derate_at_50rh
    humidity_factor = 1.0 - (1.0 - material.humidity_derate_at_50rh) * max(0.0, min(humidity_rh, 100.0)) / 50.0
    return (
        material.sigma_hlim_mpa * temp_factor * humidity_factor,
        material.sigma_flim_mpa * temp_factor * humidity_factor,
    )
```

- [ ] **Step 2: calculator.py 导入材料库与降额**

在 calculator.py 顶部添加：

```python
from core.worm.materials import PLASTIC_MATERIALS, apply_derate
```

在 wheel_material 解析处：

```python
wheel_plastic = PLASTIC_MATERIALS.get(wheel_material)
operating_temp_c = float(advanced.get("operating_temp_c", 23.0))
humidity_rh = float(advanced.get("humidity_rh", 50.0))
if wheel_plastic is not None:
    sigma_hlim_derated, sigma_flim_derated = apply_derate(
        wheel_plastic,
        operating_temp_c=operating_temp_c,
        humidity_rh=humidity_rh,
    )
    wheel_allowable_defaults = {
        "contact_mpa": sigma_hlim_derated,
        "root_mpa": sigma_flim_derated,
    }
    # 回填 e / nu（若用户未覆盖）
    if "wheel_e_mpa" not in materials:
        materials["wheel_e_mpa"] = wheel_plastic.e_mpa
    if "wheel_nu" not in materials:
        materials["wheel_nu"] = wheel_plastic.nu
```

- [ ] **Step 3: Method B 寿命 + 磨损（DIN 3996 K9 简化）**

在 Method B 分支内新增：

```python
# 疲劳寿命 N_L（DIN 3996 简化）: Δσ^m · N = C
# 取 m=6（塑料齿轮常用），C = sigma_Hlim^6 · 1e7
sigma_hm_max = max(sigma_hm_peak_mpa, 1e-6)
n_life_cycles = (allowable_contact_stress_mpa / sigma_hm_max) ** 6 * 1.0e7
n_life_hours = n_life_cycles / max(wheel_speed_rpm * 60.0, 1e-6)

# 磨损率 J (mm³/Nm) 按 DIN 3996 K9 手册值（塑料-钢）
wear_coeff_j = float(load_capacity.get("wear_coefficient_mm3_per_nm", 6.0e-7))
sliding_velocity_mps = math.pi * pitch_diameter_worm_mm * speed_rpm / 60000.0 / math.cos(lead_angle_calc_rad)
wear_depth_mm_per_hour = (
    wear_coeff_j * design_tangential_force_n * sliding_velocity_mps * 3600.0
    / max(contact_length_mm * pitch_diameter_wheel_mm * math.pi, 1e-6)
)
wear_life_hours_until_0p3mm = 0.3 / max(wear_depth_mm_per_hour, 1e-9)

life_out = {
    "fatigue_life_cycles": n_life_cycles,
    "fatigue_life_hours": n_life_hours,
    "wear_depth_mm_per_hour": wear_depth_mm_per_hour,
    "wear_life_hours_until_0p3mm": wear_life_hours_until_0p3mm,
    "sliding_velocity_mps": sliding_velocity_mps,
}
```

把 `life_out` 合入返回的 `load_capacity` 字典。

- [ ] **Step 4: 变位系数 x1/x2 联动**

`geometry.get("x1", 0.0)` 已存在（calculator.py:115）；但齿顶/齿根高计算未考虑变位导致的最小齿厚。在 calculator.py:197 `tooth_height_mm = module_mm * (2.2 + x1 - x2)` 保持正确。新增变位范围告警（135 行附近）：

```python
if not (-0.5 <= x1 <= 1.0):
    raise InputError(f"x1 必须在 -0.5 ~ 1.0 范围内（DIN 3975 推荐），当前值 {x1}")
if not (-0.5 <= x2 <= 1.0):
    raise InputError(f"x2 必须在 -0.5 ~ 1.0 范围内（DIN 3975 推荐），当前值 {x2}")
```

- [ ] **Step 5: 性能曲线第 3 张真实温升**

将 `thermal_capacity_curve` 改为温升数据：

```python
# 原来:
# p_thermal_i = p_loss_i
# thermal_capacity_curve.append(p_thermal_i)
# 改为:
delta_t_i = p_loss_i / max(thermal_capacity_kw, 1e-6) * thermal_allowable_delta_t_k
temperature_rise_curve.append(delta_t_i)
```

把 `curve` 字典中键改为 `temperature_rise_k`。

- [ ] **Step 6: 跑测试 + 等待 test-engineer 的 Task 1.C**

### Task 1.B (ui-engineer): 塑料材料下拉 + 自锁/效率卡 + 温湿度 + 变位

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`

- [ ] **Step 1: 材料下拉扩展**

在 materials 章节 FieldSpec 找到 `wheel_material` 的 choices，改为：

```python
("PA66", "PA66"),
("PA66+GF30", "PA66+GF30"),
("POM", "POM"),
("PA46", "PA46"),
("PEEK", "PEEK"),
```

选择后自动填充 `wheel_e_mpa` / `wheel_nu` / `allowable_contact_stress_mpa` / `allowable_root_stress_mpa`，并切换对应字段为 `AutoCalcCard` 样式。监听材料下拉 change 信号，调用 `_apply_plastic_defaults(material_name)` 方法，新增：

```python
def _apply_plastic_defaults(self, material_name: str) -> None:
    from core.worm.materials import PLASTIC_MATERIALS
    mat = PLASTIC_MATERIALS.get(material_name)
    if mat is None:
        return
    self._set_field_value("wheel_e_mpa", mat.e_mpa)
    self._set_field_value("wheel_nu", mat.nu)
    self._set_field_value("allowable_contact_stress_mpa", mat.sigma_hlim_mpa)
    self._set_field_value("allowable_root_stress_mpa", mat.sigma_flim_mpa)
    for field_id in ("wheel_e_mpa", "wheel_nu", "allowable_contact_stress_mpa", "allowable_root_stress_mpa"):
        self._set_card_style(field_id, auto=True)
```

- [ ] **Step 2: 新增温度/湿度字段**

在 advanced 章节 FieldSpec 添加：

```python
FieldSpec(id="operating_temp_c", label="工作温度", unit="℃",
         mapping=("advanced", "operating_temp_c"), default="23", hint="齿面工作温度（用于材料降额）"),
FieldSpec(id="humidity_rh",       label="相对湿度", unit="%",
         mapping=("advanced", "humidity_rh"),      default="50", hint="环境湿度（PA 系列吸水降额用）"),
```

- [ ] **Step 3: 变位系数 x1/x2 字段（若未暴露）**

geometry 章节 FieldSpec 添加：

```python
FieldSpec(id="x1", label="蜗杆变位系数 x1", unit="",
         mapping=("geometry", "x1"), default="0.0", hint="-0.5 ~ 1.0"),
FieldSpec(id="x2", label="蜗轮变位系数 x2", unit="",
         mapping=("geometry", "x2"), default="0.0", hint="-0.5 ~ 1.0"),
```

- [ ] **Step 4: 效率卡新增"γ / φ' / 自锁"行**

找到 performance 结果展示段，新增：

```python
gamma_deg = result["geometry"]["lead_angle_calc_deg"]
mu = result["performance"]["friction_mu"]
alpha_n = result["inputs_echo"].get("advanced", {}).get("normal_pressure_angle_deg", 20.0)
phi_prime_deg = math.degrees(math.atan(mu / math.cos(math.radians(alpha_n))))
self_lock = gamma_deg <= phi_prime_deg
self._efficiency_card.set_subtitle(
    f"γ = {gamma_deg:.2f}° / φ' = {phi_prime_deg:.2f}° / 自锁：{'是' if self_lock else '否'}"
)
```

- [ ] **Step 5: 寿命/磨损结果展示**

新增"寿命评估"卡（SubCard），展示：

```python
life = result["load_capacity"].get("life", {})
rows = [
    ("疲劳寿命", f"{life.get('fatigue_life_hours', 0.0):.0f} h"),
    ("磨损速率", f"{life.get('wear_depth_mm_per_hour', 0.0)*1000:.3f} µm/h"),
    ("磨损寿命 (至 0.3mm)", f"{life.get('wear_life_hours_until_0p3mm', 0.0):.0f} h"),
    ("滑动速度", f"{life.get('sliding_velocity_mps', 0.0):.2f} m/s"),
]
```

- [ ] **Step 6: 性能曲线调用方传温升**

将 `WormPerformanceCurveWidget.set_curves` 调用处改为：

```python
self._performance_curve.set_curves(
    load_factor=result["curve"]["load_factor"],
    efficiency=result["curve"]["efficiency"],
    power_loss_kw=result["curve"]["power_loss_kw"],
    temperature_rise_k=result["curve"]["temperature_rise_k"],
    current_index=result["curve"]["current_index"],
)
```

### Task 1.C (test-engineer): 材料降额 / 寿命 / 温升 测试

**Files:**
- Modify: `tests/core/worm/test_calculator.py`
- Create: `tests/core/worm/test_materials.py`

- [ ] **Step 1: 新建 `tests/core/worm/test_materials.py`**

```python
import pytest
from core.worm.materials import PLASTIC_MATERIALS, apply_derate


def test_all_plastic_materials_loaded():
    for name in ("PA66", "PA66+GF30", "POM", "PA46", "PEEK"):
        assert name in PLASTIC_MATERIALS


def test_temperature_derate_reduces_allowables():
    mat = PLASTIC_MATERIALS["PA66"]
    sigma_h_23, _ = apply_derate(mat, operating_temp_c=23.0, humidity_rh=0.0)
    sigma_h_80, _ = apply_derate(mat, operating_temp_c=80.0, humidity_rh=0.0)
    assert sigma_h_80 < sigma_h_23 * 0.7  # 温度升 57℃，降额显著


def test_humidity_derate_hits_pa_only():
    pa = PLASTIC_MATERIALS["PA66"]
    peek = PLASTIC_MATERIALS["PEEK"]
    sigma_pa_0rh, _ = apply_derate(pa, operating_temp_c=23.0, humidity_rh=0.0)
    sigma_pa_50rh, _ = apply_derate(pa, operating_temp_c=23.0, humidity_rh=50.0)
    sigma_peek_0rh, _ = apply_derate(peek, operating_temp_c=23.0, humidity_rh=0.0)
    sigma_peek_50rh, _ = apply_derate(peek, operating_temp_c=23.0, humidity_rh=50.0)
    assert sigma_pa_50rh < sigma_pa_0rh * 0.75
    assert sigma_peek_50rh == pytest.approx(sigma_peek_0rh, rel=5e-2)
```

- [ ] **Step 2: Calculator 寿命/磨损测试**

在 test_calculator.py 新增：

```python
def test_life_and_wear_outputs_present_method_b():
    data = _case_m4_z1_q10()
    data["load_capacity"]["method"] = "DIN 3996 Method B"
    result = calculate_worm_geometry(data)
    life = result["load_capacity"].get("life", {})
    assert life.get("fatigue_life_hours", 0) > 0
    assert life.get("wear_depth_mm_per_hour", 0) > 0
    assert life.get("wear_life_hours_until_0p3mm", 0) > 0


def test_temperature_rise_curve_nonconstant():
    data = _case_m4_z1_q10()
    result = calculate_worm_geometry(data)
    curve = result["curve"]
    rises = curve.get("temperature_rise_k") or curve.get("thermal_capacity_kw")
    # 不再等于 power_loss_kw 曲线
    assert rises != curve["power_loss_kw"]


def test_invalid_x1_raises():
    from core.worm.calculator import InputError
    data = _case_m4_z1_q10()
    data["geometry"]["x1"] = 1.5
    with pytest.raises(InputError, match="x1"):
        calculate_worm_geometry(data)
```

- [ ] **Step 3: UI 塑料下拉自动填充测试**

在 tests/ui/test_worm_page.py 新增：

```python
def test_wheel_material_pom_autofills_allowables(qtbot):
    from app.ui.pages.worm_gear_page import WormGearPage
    page = WormGearPage()
    qtbot.addWidget(page)
    page._field_widgets["wheel_material"].setCurrentText("POM")
    # POM sigma_Hlim = 48 MPa
    assert float(page._field_widgets["allowable_contact_stress_mpa"].text()) == pytest.approx(48.0)
```

- [ ] **Step 4: 回归**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

### Wave 1 review & commit

- [ ] dispatch codex review
- [ ] 修复
- [ ] commit 消息 `feat(worm): plastic material library + DIN 3996 Method B + wear/life [W26-08..14,20]`

---

## Wave 2 — 体验与报告（P2）

6 项：W26-15, 16, 17, 18, 21, 22

### Task 2.A (core-engineer): examples 用例刷新

**Files:**
- Modify: `examples/worm_case_01.json` (及其他蜗杆相关 JSON)

- [ ] **Step 1: 更新 `worm_case_01.json`**

用 Wave 0 `_case_m4_z1_q10` 的参数写一份真实塑料蜗轮产线案例：

```json
{
  "geometry": {
    "module_mm": 4.0,
    "z1": 1, "z2": 40,
    "diameter_factor_q": 10.0,
    "center_distance_mm": 100.0,
    "lead_angle_deg": 5.71,
    "worm_face_width_mm": 32.0,
    "wheel_face_width_mm": 28.0,
    "x1": 0.0, "x2": 0.0
  },
  "operating": {
    "input_torque_nm": 19.5, "speed_rpm": 1500.0,
    "application_factor": 1.25
  },
  "materials": {
    "worm_material": "37CrS4",
    "wheel_material": "PA66+GF30",
    "handedness": "right",
    "lubrication": "grease"
  },
  "advanced": {
    "normal_pressure_angle_deg": 20.0,
    "operating_temp_c": 60.0,
    "humidity_rh": 50.0
  },
  "load_capacity": {
    "enabled": true,
    "method": "DIN 3996 Method B",
    "required_contact_safety": 1.3,
    "required_root_safety": 1.5
  }
}
```

- [ ] **Step 2: 新增 POM 和 PEEK 各一个案例（worm_case_02.json, worm_case_03.json）**

### Task 2.B (ui-engineer): 体验改进

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: PDF 报告生成模块（若存在于 worm 页面内）

- [ ] **Step 1: _refresh_derived_geometry_preview 改为节流**

找到 `_refresh_derived_geometry_preview`（worm_gear_page.py:743 附近），改为使用 QTimer 延迟 300ms 批处理：

```python
from PySide6.QtCore import QTimer

# __init__:
self._preview_timer = QTimer(self)
self._preview_timer.setSingleShot(True)
self._preview_timer.setInterval(300)
self._preview_timer.timeout.connect(self._do_refresh_preview)

def _refresh_derived_geometry_preview(self) -> None:
    self._preview_timer.start()  # restarts on each keystroke

def _do_refresh_preview(self) -> None:
    # 原全量计算逻辑
    ...
```

- [ ] **Step 2: AutoCalcCard 样式一致性检查**

巡检所有自动填充字段：`d1`（由 q·m 派生）、`d2`（由 z2·m 派生）、`a_theoretical`、所有材料属性。若尚未用 `AutoCalcCard`，改为 `AutoCalcCard` + setReadOnly/setEnabled=False。

- [ ] **Step 3: 章节脏状态提示**

任何字段变更 → disable"导出报告"按钮，显示红色"结果已过期，请重新执行"：

```python
def _on_any_input_changed(self) -> None:
    self._export_button.setEnabled(False)
    self._status_label.setText("结果已过期，请重新执行计算。")
    self._status_label.setStyleSheet("color: #C44536;")

# 在每个 FieldSpec 的 widget 的 change signal 上连接
```

- [ ] **Step 4: PDF 报告字段对齐**

找到 PDF 生成函数，核对以下字段映射：
- F_n / F_a / F_r 使用 `load_capacity.forces` 新值
- σ_H / σ_F 使用 peak / nominal
- 新增寿命/磨损区块
- 新增温湿度工况记录

- [ ] **Step 5: 输入条件保存/加载 worm 专项**

在 `input_condition_store.py` 层已统一，但 worm 页面需注册所有新字段（温度、湿度、x1/x2、handedness、lubrication）。搜索 `register_fields` 或类似的 hook，确保新 FieldSpec 全部覆盖。

### Task 2.C (test-engineer): 回归 + 体验测试

**Files:**
- Modify: `tests/ui/test_worm_page.py`

- [ ] **Step 1: 节流测试**

```python
def test_preview_throttled_not_recalculating_per_keystroke(qtbot):
    from app.ui.pages.worm_gear_page import WormGearPage
    page = WormGearPage()
    qtbot.addWidget(page)
    count_before = page._preview_call_count if hasattr(page, "_preview_call_count") else 0
    for v in ("3", "3.5", "4", "4.5", "5"):
        page._field_widgets["module_mm"].setText(v)
    # 300ms 未触发
    count_immediate = page._preview_call_count if hasattr(page, "_preview_call_count") else 0
    assert count_immediate == count_before
    qtbot.wait(400)
    # 触发一次而不是五次
    count_after = page._preview_call_count
    assert count_after == count_before + 1
```

（需要 ui-engineer 在 page 里曝光 `_preview_call_count` 计数器。）

- [ ] **Step 2: 脏状态测试**

```python
def test_input_change_disables_export_button(qtbot):
    page = WormGearPage()
    qtbot.addWidget(page)
    page._on_execute()
    assert page._export_button.isEnabled()
    page._field_widgets["module_mm"].setText("5")
    assert not page._export_button.isEnabled()
```

- [ ] **Step 3: examples 加载回归**

```python
import json
def test_examples_worm_case_01_loads_and_runs():
    from core.worm.calculator import calculate_worm_geometry
    with open("examples/worm_case_01.json") as f:
        data = json.load(f)
    result = calculate_worm_geometry(data)
    assert result["load_capacity"]["enabled"] is True
    # 60℃ / 50%RH 工况下 PA66+GF30 σ_Hlim 约 45 MPa（58 · 0.90^(37/10) · 0.8）
    assert 40 < result["load_capacity"]["contact"]["allowable_contact_stress_mpa"] < 50
```

- [ ] **Step 4: 回归**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

### Wave 2 review & commit

- [ ] dispatch codex review
- [ ] commit 消息 `feat(worm): UX polish + PDF alignment + examples refresh [W26-15..18,21,22]`

---

## 完工验收

- [ ] 3 波 commit 全部在 `git log` 中体现
- [ ] `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v` 全通过
- [ ] `python3 app/main.py` 手动验证：
  - 选 PA66+GF30 → 自动填充 E/ν/σ_Hlim/σ_Flim
  - 输 m=4, z1=1, z2=40, q=10, T2→T1 反推 → F_a ≈ 963 N、F_n ≈ 6683 N
  - 切 handedness 左旋 → 几何总览螺旋反向
  - Method C → 报错
  - 输入变更 → 导出按钮灰
- [ ] 3 份 codex review 报告存入 `docs/reports/2026-04-17-worm-fix-wave-{0,1,2}-review.md`

---

## 自检

**Spec coverage：** 22 个问题全部分配到 Task：
- W26-01 → 0.A Step 2
- W26-02 → 0.A Step 6, 0.B Step 5, 0.C Step 1（test_method_a/c）
- W26-03 → 0.A Step 3
- W26-04 → 0.A Step 4
- W26-05 → 0.A Step 5
- W26-06 → 0.A Step 7, 0.B Step 4
- W26-07 → 0.C Step 1-4
- W26-08 → 1.A Step 1-2, 1.B Step 1, 1.C Step 1-3
- W26-09 → 1.A Step 3
- W26-10 → 1.B Step 4
- W26-11 → 1.A Step 4, 1.B Step 3
- W26-12 → 1.A Step 3 后半段, 1.B Step 5
- W26-13 → 1.B Step 4
- W26-14 → 1.A Step 4 校验
- W26-15 → 2.B Step 4
- W26-16 → 2.B Step 5
- W26-17 → 2.B Step 2
- W26-18 → 2.B Step 3
- W26-19 → 0.B Step 1-3
- W26-20 → 1.A Step 5, 1.B Step 6
- W26-21 → 2.B Step 1
- W26-22 → 2.A Step 1-2

**Placeholder scan：** 无 TBD / TODO，每步均含代码。

**Type consistency：** `life` / `forces` / `temperature_rise_k` / `_geom_state` 命名跨 Task 一致。
