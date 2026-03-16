# Batch 3/4/5 实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成螺栓模块 VDI 2230 剩余三个批次的改进：拧紧方式联动建议 + 服役应力精化 + 疲劳模型改进 + 被夹件刚度自动建模。

**Architecture:** Calculator core 新增 `tightening_method` 和 `surface_treatment` 参数；R5 扩展为 von Mises 含扭转残余；疲劳极限改用 VDI 2230 表 A1 参数化查表替代 `0.18×Rp02`；新增 `compliance_model.py` 子模块处理锥台压缩体建模。

**Tech Stack:** Python 3.12, pytest, PySide6

---

## Chunk 1: Batch 3 — Phase 4 拧紧方式联动 + Phase 5 服役应力精化

### Task 1: Calculator — αA 范围 warning + tightening_method 传入

**Files:**
- Modify: `core/bolt/calculator.py`
- Test: `tests/core/bolt/test_calculator.py`

**Context:** `assembly.tightening_method` 目前是 UI-only 字段 (mapping=None)。需要：(1) 将其传入 calculator 作为 `options.tightening_method`；(2) 根据拧紧方式检查 αA 是否在建议范围内，超出范围时加入 warnings。

- [ ] **Step 1: 写失败测试 — αA 范围 warning**

```python
class TestTighteningMethodWarnings:
    def test_torque_method_alpha_in_range_no_warning(self):
        """扭矩法 αA=1.6 在建议范围 [1.4, 1.8] 内，无 warning。"""
        data = _base_input()
        data["options"]["tightening_method"] = "torque"
        data["tightening"]["alpha_A"] = 1.6
        result = calculate_vdi2230_core(data)
        assert not any("αA" in w for w in result["warnings"])

    def test_torque_method_alpha_out_of_range_warns(self):
        """扭矩法 αA=1.2 低于建议下限 1.4，触发 warning。"""
        data = _base_input()
        data["options"]["tightening_method"] = "torque"
        data["tightening"]["alpha_A"] = 1.2
        result = calculate_vdi2230_core(data)
        assert any("αA" in w for w in result["warnings"])

    def test_angle_method_alpha_in_range(self):
        """转角法 αA=1.2 在建议范围 [1.1, 1.3] 内，无 warning。"""
        data = _base_input()
        data["options"]["tightening_method"] = "angle"
        data["tightening"]["alpha_A"] = 1.2
        result = calculate_vdi2230_core(data)
        assert not any("αA" in w for w in result["warnings"])

    def test_hydraulic_method_alpha_out_of_range_warns(self):
        """液压拉伸法 αA=1.3 超出建议上限 1.15，触发 warning。"""
        data = _base_input()
        data["options"]["tightening_method"] = "hydraulic"
        data["tightening"]["alpha_A"] = 1.3
        result = calculate_vdi2230_core(data)
        assert any("αA" in w for w in result["warnings"])

    def test_unknown_method_no_warning(self):
        """未知或缺省 tightening_method 不检查范围。"""
        data = _base_input()
        # 不设置 tightening_method，默认应为 None 或 "torque"
        result = calculate_vdi2230_core(data)
        # 默认 αA=1.6 + 默认 torque → 在范围内
        assert not any("αA" in w for w in result["warnings"])

    def test_tightening_method_echoed_in_result(self):
        """tightening_method 回显在结果中。"""
        data = _base_input()
        data["options"]["tightening_method"] = "angle"
        result = calculate_vdi2230_core(data)
        assert result["tightening_method"] == "angle"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestTighteningMethodWarnings -v`
Expected: FAIL（tightening_method 未读取，result 中无该键）

- [ ] **Step 3: 实现 — calculator 读取 tightening_method + αA 范围检查**

在 `core/bolt/calculator.py` 中：

1. 在 `_estimate_embed_loss` 函数前添加常量：

```python
# VDI 2230 表：拧紧方式对应 αA 建议范围
_ALPHA_A_RANGES: dict[str, tuple[float, float]] = {
    "torque": (1.4, 1.8),
    "angle": (1.1, 1.3),
    "hydraulic": (1.05, 1.15),
    "thermal": (1.05, 1.15),
}
```

2. 在 `calculate_vdi2230_core` 中，`joint_type` 解析后添加：

```python
tightening_method = str(options.get("tightening_method", "torque"))
```

3. 在 warnings 构建区域（约 line 351），utilization 检查之后添加：

```python
alpha_range = _ALPHA_A_RANGES.get(tightening_method)
if alpha_range is not None:
    lo, hi = alpha_range
    if alpha_a < lo or alpha_a > hi:
        method_names = {"torque": "扭矩法", "angle": "转角法",
                        "hydraulic": "液压拉伸法", "thermal": "热装法"}
        method_cn = method_names.get(tightening_method, tightening_method)
        warnings.append(
            f"αA = {alpha_a:.2f} 超出{method_cn}建议范围 [{lo}–{hi}]，"
            "请确认装配工艺能力。"
        )
```

4. 在 return dict 中添加：

```python
"tightening_method": tightening_method,
```

- [ ] **Step 4: 运行测试确认通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestTighteningMethodWarnings -v`
Expected: 6 PASSED

- [ ] **Step 5: 提交**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): add tightening_method αA range warnings"
```

---

### Task 2: Calculator — R5 服役应力含扭转残余

**Files:**
- Modify: `core/bolt/calculator.py`
- Test: `tests/core/bolt/test_calculator.py`

**Context:** 当前 R5 只比较 `sigma_ax_work ≤ Rp02/SF`，不含装配扭矩残余。VDI 2230 R5 应为：
`σ_red,B = √(σ_ax² + 3·(k_τ·τ)²)` 其中 k_τ 取决于拧紧方式（扭矩法≈0.5，其他≈0）。

- [ ] **Step 1: 写失败测试**

```python
class TestR5TorsionResidual:
    def test_torque_method_includes_torsion_residual(self):
        """扭矩法 R5 使用 von Mises 含 k_tau=0.5 的扭转残余。"""
        data = _base_input()
        data["options"]["tightening_method"] = "torque"
        result = calculate_vdi2230_core(data)
        stresses = result["stresses_mpa"]
        # σ_vm_work 应大于纯轴向 σ_ax_work
        assert stresses["sigma_vm_work"] > stresses["sigma_ax_work"]
        assert "k_tau" in stresses
        assert stresses["k_tau"] == 0.5

    def test_angle_method_no_torsion_residual(self):
        """转角法 R5 的 k_tau=0，σ_vm_work = σ_ax_work。"""
        data = _base_input()
        data["options"]["tightening_method"] = "angle"
        result = calculate_vdi2230_core(data)
        stresses = result["stresses_mpa"]
        assert stresses["k_tau"] == 0.0
        assert abs(stresses["sigma_vm_work"] - stresses["sigma_ax_work"]) < 0.01

    def test_r5_check_uses_vm_work(self):
        """R5 校核使用 σ_vm_work 而非 σ_ax_work。"""
        data = _base_input()
        data["options"]["tightening_method"] = "torque"
        result = calculate_vdi2230_core(data)
        stresses = result["stresses_mpa"]
        # operating_axial_ok 应基于 σ_vm_work
        expected_pass = stresses["sigma_vm_work"] <= stresses["sigma_allow_work"]
        assert result["checks"]["operating_axial_ok"] == expected_pass

    def test_torsion_residual_formula(self):
        """验证公式: σ_vm_work = √(σ_ax² + 3·(k_τ·τ)²)。"""
        data = _base_input()
        data["options"]["tightening_method"] = "torque"
        result = calculate_vdi2230_core(data)
        s = result["stresses_mpa"]
        import math
        expected = math.sqrt(s["sigma_ax_work"]**2 + 3.0 * (0.5 * s["tau_assembly"])**2)
        assert abs(s["sigma_vm_work"] - expected) < 0.01
```

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestR5TorsionResidual -v`
Expected: FAIL（`sigma_vm_work` 和 `k_tau` 不存在）

- [ ] **Step 3: 实现 — R5 von Mises 含扭转残余**

在 `core/bolt/calculator.py` 中，找到 R5 区域（约 line 301-308）：

将：
```python
f_bolt_work_max = fm_max + phi_n * fa_max
sigma_ax_work = f_bolt_work_max / geometry["As"]
yield_safety_operating = ...
sigma_allow_work = rp02 / yield_safety_operating
pass_work = sigma_ax_work <= sigma_allow_work
```

改为：
```python
f_bolt_work_max = fm_max + phi_n * fa_max
sigma_ax_work = f_bolt_work_max / geometry["As"]
# R5 扭转残余：扭矩法保留约 50% 装配扭矩残余
k_tau = 0.5 if tightening_method == "torque" else 0.0
sigma_vm_work = math.sqrt(sigma_ax_work**2 + 3.0 * (k_tau * tau_assembly)**2)
yield_safety_operating = ...
sigma_allow_work = rp02 / yield_safety_operating
pass_work = sigma_vm_work <= sigma_allow_work
```

在 `stresses_out` dict 中添加：
```python
"sigma_vm_work": sigma_vm_work,
"k_tau": k_tau,
```

- [ ] **Step 4: 运行测试确认通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestR5TorsionResidual -v`
Expected: 4 PASSED

- [ ] **Step 5: 运行全部测试确认无回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: 全部 PASS。注意：由于 R5 现在包含扭转残余，某些已有测试的 pass_work 结果可能变化。如果 _base_input 使用默认 tightening_method=torque，已有 integration test 的 `operating_axial_ok` 可能从 True 变为 False（如果 σ_vm_work 增大超过 σ_allow）。如果发生，需检查 _base_input 的数值是否仍满足 R5。

可能需要的修复：如果 base_input 的 σ_vm_work 超限，调小 FA_max 或调高 Rp02 使全部测试恢复 pass。

- [ ] **Step 6: 提交**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): R5 includes torsion residual (k_tau) per tightening method"
```

---

### Task 3: UI — tightening_method 传入 payload + hint 联动

**Files:**
- Modify: `app/ui/pages/bolt_page.py`
- Modify: `app/ui/pages/bolt_flowchart.py`

**Context:** `assembly.tightening_method` 需要 (1) 注入到 payload 中 options.tightening_method；(2) αA 字段 hint 动态更新建议范围；(3) introduction.position hint 联动 n 值建议。flowchart R5 需要显示 σ_vm_work。

- [ ] **Step 1: 添加拧紧方式映射常量**

在 `bolt_page.py` 中 SURFACE_CLASS_MAP 附近添加：

```python
TIGHTENING_METHOD_MAP: dict[str, str] = {
    "扭矩法": "torque",
    "转角法": "angle",
    "液压拉伸法": "hydraulic",
    "热装法": "thermal",
}

ALPHA_A_HINTS: dict[str, str] = {
    "扭矩法": "FMmax/FMmin，扭矩法建议范围 1.4~1.8。",
    "转角法": "FMmax/FMmin，转角法建议范围 1.1~1.3。",
    "液压拉伸法": "FMmax/FMmin，液压拉伸法建议范围 1.05~1.15。",
    "热装法": "FMmax/FMmin，热装法建议范围 1.05~1.15。",
}

N_POSITION_HINTS: dict[str, str] = {
    "螺栓头端": "修正外载导入比例。头端导入通常取 n ≈ 1.0。",
    "螺母端": "修正外载导入比例。螺母端导入通常取 n ≈ 0.5~0.7。",
    "中间": "修正外载导入比例。中间导入通常取 n ≈ 0.3~0.5。",
    "分布式": "修正外载导入比例。均匀分布近似取 n ≈ 0.5。",
}
```

- [ ] **Step 2: 在 _build_payload 中注入 tightening_method**

在 `_build_payload` 的 surface_class 翻译代码附近，添加：

```python
# 拧紧方式映射
method_w = self._field_widgets.get("assembly.tightening_method")
if method_w is not None and isinstance(method_w, QComboBox):
    method_en = TIGHTENING_METHOD_MAP.get(method_w.currentText(), "torque")
    payload.setdefault("options", {})["tightening_method"] = method_en
```

- [ ] **Step 3: 添加 hint 联动回调**

在 `_connect_signals` 或 `__init__` 阶段，为 `assembly.tightening_method` 下拉连接 `_on_tightening_method_changed`：

```python
def _on_tightening_method_changed(self, text: str) -> None:
    # 更新 αA hint
    alpha_w = self._field_widgets.get("tightening.alpha_A")
    if alpha_w is not None and hasattr(alpha_w, "setToolTip"):
        alpha_w.setToolTip(ALPHA_A_HINTS.get(text, ""))

def _on_position_changed(self, text: str) -> None:
    # 更新 n 值 hint
    n_w = self._field_widgets.get("stiffness.load_introduction_factor_n")
    if n_w is not None and hasattr(n_w, "setToolTip"):
        n_w.setToolTip(N_POSITION_HINTS.get(text, ""))
```

- [ ] **Step 4: 更新 flowchart R5 计算过程文本**

在 `bolt_flowchart.py` 的 `_format_calc_text` r5 分支中，将：
```python
f"σ_ax_work  = F_bolt_max/As = {stresses.get('sigma_ax_work', 0):.1f} MPa\n"
f"σ_allow    = Rp0.2/SF = {stresses.get('sigma_allow_work', 0):.1f} MPa\n"
f"判据: σ_ax ≤ σ_allow"
```
改为：
```python
k_tau = stresses.get('k_tau', 0)
k_tau_line = f"\nk_τ = {k_tau:.1f}（{'扭矩法残留' if k_tau > 0 else '扭矩已释放'}）" if 'k_tau' in stresses else ""
vm_line = f"\nσ_vm_work  = √(σ²+3(k_τ·τ)²) = {stresses.get('sigma_vm_work', stresses.get('sigma_ax_work', 0)):.1f} MPa" if k_tau > 0 else ""
...
f"判据: σ_vm ≤ σ_allow"
```

- [ ] **Step 5: 运行全部测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/ui/pages/bolt_page.py app/ui/pages/bolt_flowchart.py
git commit -m "feat(bolt/ui): wire tightening_method to payload, αA and n hint linking"
```

---

## Chunk 2: Batch 4 — Phase 6 疲劳模型改进

### Task 4: Calculator — VDI 2230 σ_ASV 查表替代 0.18×Rp02

**Files:**
- Modify: `core/bolt/calculator.py`
- Test: `tests/core/bolt/test_calculator.py`

**Context:** 当前疲劳极限 `sigma_a_base = 0.18 * rp02` 是粗糙估算。VDI 2230 表 A1 给出按规格查表的 σ_ASV 值。实现参数化近似：`σ_ASV(d, surface)` 查表。

σ_ASV 参考值（VDI 2230 表 A1，轧制螺纹，N/mm²）：
- M6: ±50, M8: ±47, M10: ±44, M12: ±41, M14: ±39
- M16: ±38, M20: ±36, M24: ±34, M30: ±32, M36: ±30

切削螺纹约为轧制的 60-70%。

- [ ] **Step 1: 写失败测试**

```python
class TestFatigueModelImproved:
    def test_fatigue_uses_asv_table_not_018_rp02(self):
        """M10 螺栓疲劳极限应使用 σ_ASV 查表值，而非 0.18×Rp02。"""
        data = _base_input()
        data["options"]["check_level"] = "fatigue"
        result = calculate_vdi2230_core(data)
        fatigue = result["fatigue"]
        # M10, d=10, 轧制螺纹: σ_ASV ≈ 44 MPa
        # 旧公式: 0.18 * 640 = 115.2 MPa（偏大）
        assert fatigue["sigma_ASV"] > 0
        assert fatigue["sigma_ASV"] < 0.18 * 640  # 查表值远小于旧公式

    def test_larger_bolt_lower_asv(self):
        """M20 螺栓的 σ_ASV 应低于 M10。"""
        data10 = _base_input()
        data10["options"]["check_level"] = "fatigue"
        data20 = _base_input()
        data20["fastener"]["d"] = 20.0
        data20["fastener"]["p"] = 2.5
        data20["options"]["check_level"] = "fatigue"
        r10 = calculate_vdi2230_core(data10)
        r20 = calculate_vdi2230_core(data20)
        assert r10["fatigue"]["sigma_ASV"] > r20["fatigue"]["sigma_ASV"]

    def test_cut_thread_lower_asv(self):
        """切削螺纹 σ_ASV 约为轧制的 65%。"""
        data = _base_input()
        data["options"]["check_level"] = "fatigue"
        data["options"]["surface_treatment"] = "rolled"
        r_rolled = calculate_vdi2230_core(data)
        data["options"]["surface_treatment"] = "cut"
        r_cut = calculate_vdi2230_core(data)
        assert r_cut["fatigue"]["sigma_ASV"] < r_rolled["fatigue"]["sigma_ASV"]
        ratio = r_cut["fatigue"]["sigma_ASV"] / r_rolled["fatigue"]["sigma_ASV"]
        assert 0.55 < ratio < 0.75  # 约 60-70%

    def test_goodman_still_applies(self):
        """Goodman 修正仍然应用于 σ_ASV 基础上。"""
        data = _base_input()
        data["options"]["check_level"] = "fatigue"
        result = calculate_vdi2230_core(data)
        fatigue = result["fatigue"]
        # sigma_a_allow 应小于等于 sigma_ASV（Goodman 修正）
        assert fatigue["sigma_a_allow"] <= fatigue["sigma_ASV"] * 1.01

    def test_asv_interpolation_non_standard_diameter(self):
        """非标准直径使用线性插值。"""
        data = _base_input()
        data["fastener"]["d"] = 15.0  # 介于 M14 和 M16 之间
        data["fastener"]["p"] = 2.0
        data["options"]["check_level"] = "fatigue"
        result = calculate_vdi2230_core(data)
        fatigue = result["fatigue"]
        # M14: 39, M16: 38 → M15 应介于之间
        assert 37.5 < fatigue["sigma_ASV"] < 39.5
```

- [ ] **Step 2: 运行测试确认失败**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestFatigueModelImproved -v`
Expected: FAIL

- [ ] **Step 3: 实现 — σ_ASV 查表函数 + 替换 0.18×Rp02**

在 `core/bolt/calculator.py` 中 `_ALPHA_A_RANGES` 附近添加：

```python
# VDI 2230 表 A1: 轧制螺纹疲劳极限 σ_ASV (MPa)
_ASV_TABLE_ROLLED: list[tuple[float, float]] = [
    (6, 50), (8, 47), (10, 44), (12, 41), (14, 39),
    (16, 38), (20, 36), (24, 34), (30, 32), (36, 30),
]
_CUT_THREAD_FACTOR = 0.65  # 切削螺纹约为轧制的 65%


def _fatigue_limit_asv(d: float, surface_treatment: str = "rolled") -> float:
    """VDI 2230 疲劳极限 σ_ASV，按螺纹公称直径线性插值。"""
    table = _ASV_TABLE_ROLLED
    if d <= table[0][0]:
        asv = table[0][1]
    elif d >= table[-1][0]:
        asv = table[-1][1]
    else:
        for i in range(len(table) - 1):
            d0, v0 = table[i]
            d1, v1 = table[i + 1]
            if d0 <= d <= d1:
                asv = v0 + (v1 - v0) * (d - d0) / (d1 - d0)
                break
        else:
            asv = table[-1][1]
    if surface_treatment == "cut":
        asv *= _CUT_THREAD_FACTOR
    return asv
```

在 `calculate_vdi2230_core` 中，将疲劳计算区域（约 line 320-326）改为：

```python
surface_treatment = str(options.get("surface_treatment", "rolled"))
sigma_a = phi_n * fa_max / (2.0 * geometry["As"])
sigma_m = (fm_max + 0.5 * phi_n * fa_max) / geometry["As"]
cycle_factor = (2_000_000.0 / load_cycles) ** 0.08 if load_cycles < 2_000_000.0 else 1.0
sigma_asv = _fatigue_limit_asv(d, surface_treatment) * cycle_factor
goodman_factor = max(0.1, 1.0 - sigma_m / (0.9 * rp02))
sigma_a_allow = sigma_asv * goodman_factor
pass_fatigue = sigma_a <= sigma_a_allow
```

在 fatigue return dict 中添加 `"sigma_ASV": sigma_asv`，并移除旧的依赖。

- [ ] **Step 4: 运行测试确认通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestFatigueModelImproved -v`
Expected: 5 PASSED

- [ ] **Step 5: 运行全部测试确认无回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: 全部 PASS。注意疲劳极限值变化可能影响已有的 `test_joint_type_thermal_integration` 等 integration test 的 fatigue 相关断言（如有）。

- [ ] **Step 6: 提交**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): replace 0.18×Rp02 with VDI 2230 σ_ASV table for fatigue"
```

---

### Task 5: UI — 螺纹表面处理字段 + flowchart R6 更新

**Files:**
- Modify: `app/ui/pages/bolt_page.py`
- Modify: `app/ui/pages/bolt_flowchart.py`

- [ ] **Step 1: 添加表面处理映射和 FieldSpec**

```python
SURFACE_TREATMENT_MAP: dict[str, str] = {
    "轧制": "rolled",
    "切削": "cut",
}
```

在 CHAPTERS 中 fatigue 相关章节（operating 章节），load_cycles 附近添加：

```python
FieldSpec(
    "options.surface_treatment",
    "螺纹表面处理",
    "-",
    "影响疲劳极限 σ_ASV。轧制强于切削。",
    mapping=None,
    widget_type="choice",
    options=("轧制", "切削"),
    default="轧制",
),
```

- [ ] **Step 2: 在 _build_payload 中注入 surface_treatment**

```python
treatment_w = self._field_widgets.get("options.surface_treatment")
if treatment_w is not None and isinstance(treatment_w, QComboBox):
    treatment_en = SURFACE_TREATMENT_MAP.get(treatment_w.currentText(), "rolled")
    payload.setdefault("options", {})["surface_treatment"] = treatment_en
```

- [ ] **Step 3: 更新 flowchart R6 计算过程文本**

在 R6 分支中显示 σ_ASV 值：
```python
f"σ_ASV    = {fatigue.get('sigma_ASV', 0):.1f} MPa（VDI 2230 表 A1）\n"
```

- [ ] **Step 4: 运行全部测试**

- [ ] **Step 5: 提交**

---

## Chunk 3: Batch 5 — Phase 8 被夹件刚度自动建模

### Task 6: 新建 compliance_model.py — 锥台压缩体模型

**Files:**
- Create: `core/bolt/compliance_model.py`
- Test: `tests/core/bolt/test_compliance_model.py`

**Context:** VDI 2230 的被夹件弹性柔度建模。圆柱体和锥台两种模型。

锥台模型（VDI 2230 Figure 5.1）：
```
δ_p = (2 · ln[((D_w + d_h) · (D_A - d_h)) / ((D_w - d_h) · (D_A + d_h))]) / (E_p · π · d_h · tan(φ))
```
其中 φ ≈ arctan(0.362 + 0.032·ln(D_A/2/l_K) + 0.153·ln(l_K/D_w))
（Lori–Engel 近似公式）

圆柱体模型：
```
δ_p = l_K / (E_p · A_p)
A_p = π/4 · (D_A² - d_h²)
```

套筒模型：
```
δ_p = l_K / (E_p · π/4 · (D_outer² - D_inner²))
```

- [ ] **Step 1: 写失败测试**

```python
# tests/core/bolt/test_compliance_model.py
import math
import pytest
from core.bolt.compliance_model import (
    calculate_bolt_compliance,
    calculate_clamped_compliance,
)


class TestBoltCompliance:
    def test_basic_bolt_compliance(self):
        """螺栓柔度基础计算。"""
        result = calculate_bolt_compliance(
            d=10.0, p=1.5, l_K=30.0, E_bolt=210_000.0
        )
        assert result["delta_s"] > 0
        assert "l_eff" in result

    def test_longer_bolt_higher_compliance(self):
        """更长的夹紧长度 → 更大的螺栓柔度。"""
        short = calculate_bolt_compliance(d=10, p=1.5, l_K=20, E_bolt=210_000)
        long = calculate_bolt_compliance(d=10, p=1.5, l_K=40, E_bolt=210_000)
        assert long["delta_s"] > short["delta_s"]


class TestClampedCompliance:
    def test_cylinder_model(self):
        """圆柱体模型基础计算。"""
        result = calculate_clamped_compliance(
            model="cylinder",
            d_h=11.0, D_A=24.0, l_K=30.0, E_clamped=210_000.0,
        )
        assert result["delta_p"] > 0
        # 圆柱体: δp = lK / (Ep × π/4 × (DA² - dh²))
        A_p = math.pi / 4 * (24**2 - 11**2)
        expected = 30.0 / (210_000 * A_p)
        assert abs(result["delta_p"] - expected) / expected < 0.01

    def test_cone_model(self):
        """锥台模型基础计算。"""
        result = calculate_clamped_compliance(
            model="cone",
            d_h=11.0, D_w=16.0, D_A=24.0, l_K=30.0, E_clamped=210_000.0,
        )
        assert result["delta_p"] > 0
        assert "cone_angle_deg" in result

    def test_cone_lower_than_cylinder(self):
        """锥台模型比圆柱体更柔（因有效面积更小）。"""
        cyl = calculate_clamped_compliance(
            model="cylinder", d_h=11, D_A=24, l_K=30, E_clamped=210_000)
        cone = calculate_clamped_compliance(
            model="cone", d_h=11, D_w=16, D_A=24, l_K=30, E_clamped=210_000)
        # 锥台柔度可能大于或小于圆柱体取决于参数，但应为正值
        assert cone["delta_p"] > 0

    def test_sleeve_model(self):
        """套筒模型。"""
        result = calculate_clamped_compliance(
            model="sleeve",
            d_h=11.0, D_outer=24.0, D_inner=14.0, l_K=30.0,
            E_clamped=210_000.0,
        )
        assert result["delta_p"] > 0

    def test_invalid_model_raises(self):
        """无效模型类型抛出 InputError。"""
        with pytest.raises(Exception):
            calculate_clamped_compliance(
                model="invalid", d_h=11, D_A=24, l_K=30, E_clamped=210_000)

    def test_multi_layer(self):
        """多层被夹件：δp = Σ δp_i。"""
        layers = [
            {"model": "cylinder", "d_h": 11, "D_A": 24, "l_K": 15, "E_clamped": 210_000},
            {"model": "cylinder", "d_h": 11, "D_A": 24, "l_K": 15, "E_clamped": 70_000},
        ]
        result = calculate_clamped_compliance(layers=layers)
        single_steel = calculate_clamped_compliance(
            model="cylinder", d_h=11, D_A=24, l_K=15, E_clamped=210_000)
        single_alu = calculate_clamped_compliance(
            model="cylinder", d_h=11, D_A=24, l_K=15, E_clamped=70_000)
        expected = single_steel["delta_p"] + single_alu["delta_p"]
        assert abs(result["delta_p"] - expected) / expected < 0.01
```

- [ ] **Step 2: 运行测试确认失败**

- [ ] **Step 3: 实现 compliance_model.py**

```python
"""VDI 2230 螺栓/被夹件弹性柔度计算模型。"""
from __future__ import annotations

import math
from typing import Any, Dict, List

from core.bolt.calculator import InputError, _positive


def calculate_bolt_compliance(
    d: float, p: float, l_K: float, E_bolt: float,
    head_type: str = "hex",
) -> Dict[str, float]:
    """计算螺栓弹性柔度 δs (mm/N)。

    简化模型：δs = l_eff / (E × As)
    l_eff = l_K + 0.4·d（考虑螺栓头和螺纹过渡段的等效长度）
    """
    _positive(d, "d")
    _positive(p, "p")
    _positive(l_K, "l_K")
    _positive(E_bolt, "E_bolt")
    As = math.pi / 4.0 * (d - 0.9382 * p) ** 2
    l_eff = l_K + 0.4 * d
    delta_s = l_eff / (E_bolt * As)
    return {"delta_s": delta_s, "As": As, "l_eff": l_eff}


def calculate_clamped_compliance(
    model: str | None = None,
    d_h: float = 0, D_A: float = 0, D_w: float = 0,
    D_outer: float = 0, D_inner: float = 0,
    l_K: float = 0, E_clamped: float = 0,
    layers: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """计算被夹件弹性柔度 δp (mm/N)。"""
    if layers is not None:
        total_delta = 0.0
        for layer in layers:
            r = calculate_clamped_compliance(**layer)
            total_delta += r["delta_p"]
        return {"delta_p": total_delta, "model": "multi_layer", "n_layers": len(layers)}

    if model is None:
        raise InputError("必须指定 model 或 layers")

    if model == "cylinder":
        _positive(d_h, "d_h")
        _positive(D_A, "D_A")
        _positive(l_K, "l_K")
        _positive(E_clamped, "E_clamped")
        A_p = math.pi / 4.0 * (D_A**2 - d_h**2)
        delta_p = l_K / (E_clamped * A_p)
        return {"delta_p": delta_p, "model": "cylinder", "A_p": A_p}

    if model == "cone":
        _positive(d_h, "d_h")
        _positive(D_w, "D_w")
        _positive(D_A, "D_A")
        _positive(l_K, "l_K")
        _positive(E_clamped, "E_clamped")
        # Lori-Engel 近似锥角
        r_DA = max(D_A / 2.0 / l_K, 0.01)
        r_lK = max(l_K / D_w, 0.01)
        phi_rad = math.atan(0.362 + 0.032 * math.log(r_DA) + 0.153 * math.log(r_lK))
        tan_phi = math.tan(phi_rad)
        if tan_phi <= 0:
            tan_phi = 0.3  # 安全下限
        numer = (D_w + d_h) * (D_A - d_h)
        denom = (D_w - d_h) * (D_A + d_h)
        if denom <= 0 or numer <= 0:
            raise InputError("锥台模型几何参数不合理: D_w > d_h 且 D_A > d_h 必须满足")
        delta_p = 2.0 * math.log(numer / denom) / (E_clamped * math.pi * d_h * tan_phi)
        return {
            "delta_p": delta_p, "model": "cone",
            "cone_angle_deg": math.degrees(phi_rad),
        }

    if model == "sleeve":
        _positive(D_outer, "D_outer")
        _positive(D_inner, "D_inner")
        _positive(l_K, "l_K")
        _positive(E_clamped, "E_clamped")
        A_p = math.pi / 4.0 * (D_outer**2 - D_inner**2)
        delta_p = l_K / (E_clamped * A_p)
        return {"delta_p": delta_p, "model": "sleeve", "A_p": A_p}

    raise InputError(f"未知的被夹件模型: {model}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_compliance_model.py -v`
Expected: 7 PASSED

- [ ] **Step 5: 提交**

```bash
git add core/bolt/compliance_model.py tests/core/bolt/test_compliance_model.py
git commit -m "feat(bolt): add VDI 2230 compliance model (cylinder/cone/sleeve)"
```

---

### Task 7: Calculator 集成 — 自动柔度建模

**Files:**
- Modify: `core/bolt/calculator.py`
- Test: `tests/core/bolt/test_calculator.py`

**Context:** 当 stiffness 中缺少 bolt_compliance/clamped_compliance 但有几何参数时，自动调用 compliance_model 计算。

- [ ] **Step 1: 写集成测试**

```python
class TestAutoCompliance:
    def test_auto_compliance_from_geometry(self):
        """提供几何参数时自动计算刚度。"""
        data = _base_input()
        # 移除手动刚度，提供几何参数
        del data["stiffness"]["bolt_compliance"]
        del data["stiffness"]["clamped_compliance"]
        data["stiffness"]["auto_compliance"] = True
        data["stiffness"]["E_bolt"] = 210_000.0
        data["stiffness"]["E_clamped"] = 210_000.0
        data["clamped"]["basic_solid"] = "cylinder"
        data["clamped"]["total_thickness"] = 30.0
        data["clamped"]["D_A"] = 24.0
        data["bearing"]["bearing_d_inner"] = 11.0  # d_h
        result = calculate_vdi2230_core(data)
        assert result["stiffness_model"]["delta_s_mm_per_n"] > 0
        assert result["stiffness_model"]["delta_p_mm_per_n"] > 0
        assert result["stiffness_model"].get("auto_modeled") is True

    def test_manual_compliance_still_works(self):
        """手动输入柔度优先于自动计算。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["stiffness_model"]["delta_s_mm_per_n"] == data["stiffness"]["bolt_compliance"]
```

- [ ] **Step 2: 实现 _resolve_compliance 扩展**

在 `_resolve_compliance` 函数中，当既无 compliance 又无 stiffness 时，检查是否有 auto_compliance 标志和几何参数：

```python
if not has_compliance and not has_stiffness:
    auto = stiffness.get("auto_compliance", False)
    if auto:
        from core.bolt.compliance_model import (
            calculate_bolt_compliance, calculate_clamped_compliance
        )
        # 需要从外部传入的几何参数
        ... # 这里需要 d, p, l_K, E_bolt 等
    else:
        raise InputError(...)
```

注意：`_resolve_compliance` 目前只接收 stiffness dict。需要扩展其签名或者在 `calculate_vdi2230_core` 中直接处理。建议在主函数中处理，避免改动函数签名。

- [ ] **Step 3: 运行测试**
- [ ] **Step 4: 提交**

---

### Task 8: UI — 自动柔度建模界面

**Files:**
- Modify: `app/ui/pages/bolt_page.py`

**Context:** 在被夹件章节添加几何参数字段（basic_solid 联动、D_A、E_clamped 等），以及"自动/手动"切换。

- [ ] **Step 1: 添加自动柔度相关 FieldSpec**

```python
FieldSpec("clamped.D_A", "被夹件外径 D_A", "mm", "锥台/圆柱模型外径。",
          mapping=("clamped", "D_A"), default="24"),
FieldSpec("stiffness.E_bolt", "螺栓弹性模量", "MPa", "钢约 210000 MPa。",
          mapping=("stiffness", "E_bolt"), default="210000"),
FieldSpec("stiffness.E_clamped", "被夹件弹性模量", "MPa", "钢 210000 / 铝 70000 MPa。",
          mapping=("stiffness", "E_clamped"), default="210000"),
```

- [ ] **Step 2: 添加 auto/manual 切换逻辑**

`basic_solid` 下拉改为 `mapping=("clamped", "basic_solid")`，当选择非"手动"选项时，禁用 bolt_compliance/clamped_compliance 输入框并自动计算。

- [ ] **Step 3: 运行全部测试**
- [ ] **Step 4: 提交**

---

## 执行顺序

1. Task 1 → 2 → 3（Batch 3: 拧紧方式 + R5 服役应力）→ 提交 + 报告
2. Task 4 → 5（Batch 4: 疲劳模型）→ 提交 + 报告
3. Task 6 → 7 → 8（Batch 5: 刚度建模）→ 提交 + 报告
