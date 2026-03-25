# 花键配合模块 Review 修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复花键模块 d_m 公式错误，改进 UI 文字新手友好性，增强代码健壮性和测试覆盖。

**Architecture:** 四步顺序修改：公式修复 → UI 文字 → 异常处理 → 边界测试。每步一次 commit，每步后全量测试。

**Tech Stack:** Python 3.12, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-03-25-spline-module-review-fixes-design.md`

---

### Task 0: 确认绿色基线

**Files:**
- 无文件修改

- [ ] **Step 1: 运行全量花键测试确认当前状态全绿**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: 所有测试 PASS

---

### Task 1: 修复 d_m 公式 + 同步更新测试

**Files:**
- Modify: `core/spline/geometry.py:91`
- Modify: `tests/core/spline/test_geometry.py:19,39`
- Modify: `tests/core/spline/test_calculator.py:92,106`
- Test: `tests/core/spline/test_geometry.py`, `tests/core/spline/test_calculator.py`

- [ ] **Step 1: 修改 geometry.py 中的 d_m 公式**

```python
# core/spline/geometry.py L91
# 旧:
d_m = (d_a1 + d_f1) / 2.0         # 平均直径
# 新:
d_m = (d_a1 + d_a2) / 2.0         # 平均直径（接触区中心）
```

- [ ] **Step 2: 更新 test_geometry.py 中的 d_m 断言值**

```python
# tests/core/spline/test_geometry.py

# L19 (test_basic_m2_z20):
# 旧: assert r["mean_diameter_mm"] == pytest.approx(39.75)
# 新 (d_a1=42.0, d_a2=38.0 → (42+38)/2 = 40.0):
assert r["mean_diameter_mm"] == pytest.approx(40.0)

# L39 (test_public_catalog_w15_x_1_25_x_10_geometry):
# 旧: assert r["mean_diameter_mm"] == pytest.approx(13.425)
# 新 (d_a1=14.75, d_a2=12.5 → (14.75+12.5)/2 = 13.625):
assert r["mean_diameter_mm"] == pytest.approx(13.625)
```

- [ ] **Step 3: 更新 test_calculator.py 中的 d_m 常量**

```python
# tests/core/spline/test_calculator.py

# L92 (test_flank_pressure_formula):
# 旧: d_m = 39.75
# 新:
d_m = 40.0

# L106 (test_torque_capacity_formula):
# 旧: d_m = 39.75
# 新:
d_m = 40.0
```

- [ ] **Step 4: 运行测试确认全绿**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add core/spline/geometry.py tests/core/spline/test_geometry.py tests/core/spline/test_calculator.py
git commit -m "fix(spline): correct d_m formula to use contact zone center (d_a1+d_a2)/2"
```

---

### Task 2: UI 文字改进（7 处）

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py:72-75,98,123,155,185,234,590`

- [ ] **Step 1: 修改 SPLINE_SCOPE_DISCLAIMER (L72-75)**

```python
# 旧:
SPLINE_SCOPE_DISCLAIMER = (
    "花键部分当前仅提供齿面平均承压的简化预校核，"
    "不替代 DIN 5480 / DIN 6892 工程校核。"
)
# 新:
SPLINE_SCOPE_DISCLAIMER = (
    "当前仅提供齿面平均承压的简化预校核，"
    "不替代 DIN 5480（渐开线花键尺寸标准）/ DIN 6892（花键连接承载能力标准）的完整工程校核。"
)
```

- [ ] **Step 2: 修改校核模式 hint (L98)**

```python
# 旧:
"仅花键：只校核齿面承压；联合：同时校核光滑段圆柱过盈。",
# 新:
"仅花键：只校核花键齿面承压（场景 A）；联合：同时校核花键轴光滑段与轮毂孔的圆柱过盈配合（场景 B）。",
```

- [ ] **Step 3: 修改 KA hint (L123)**

```python
# 旧:
"同时放大场景 A 和场景 B 的设计载荷。",
# 新:
"考虑驱动/负载特性引起的动态过载，同时放大场景 A 和 B 的设计载荷。电机驱动约 1.0~1.25，内燃机约 1.25~1.75。",
```

- [ ] **Step 4: 修改参考直径 hint (L155)**

```python
# 旧:
"DIN 5480 基于参考直径；公开样例可用 W/N 15 x 1.25 x 10。",
# 新:
"DIN 5480 花键的基本尺寸参考直径。例如 '外花键 W 15x1.25x10' 表示 d_B=15mm, m=1.25, z=10。",
```

- [ ] **Step 5: 修改 K_alpha hint (L185)**

```python
# 旧:
"Niemann 推荐值与公差/磨合有关；轻滑移配合通常高于过盈固定连接。",
# 新:
"齿面载荷分布不均匀的修正系数。过盈固定连接约 1.0~1.3，滑移连接约 1.5~2.0。",
```

- [ ] **Step 6: 修改退刀槽 hint (L234)**

```python
# 旧:
"花键到光滑段过渡处退刀槽宽度，自动从配合长度中扣除。",
# 新:
"花键齿根与光滑段之间的让刀凹槽宽度，用于加工退刀。计算时自动从配合长度中扣除。",
```

- [ ] **Step 7: 结果页 verdict_level 中文化 (L590)**

```python
# 旧:
f"结果级别 = {a['overall_verdict_level']}"
# 新:
f"结果级别 = {{'simplified_precheck': '简化预校核'}.get(a['overall_verdict_level'], a['overall_verdict_level'])}"
```

- [ ] **Step 8: 运行 UI 测试确认不回归**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_spline_fit_page.py -v`
Expected: 所有测试 PASS

注意: `test_page_shows_engineering_scope_disclaimer` 断言 `"简化预校核"` 和 `"不替代 DIN 5480 / DIN 6892 工程校核"`。新文字仍包含 "简化预校核"，但 "不替代 DIN 5480 / DIN 6892 工程校核" 变成了 "不替代 DIN 5480（渐开线花键尺寸标准）/ DIN 6892（花键连接承载能力标准）的完整工程校核"。测试用 `any("不替代 DIN 5480 / DIN 6892 工程校核" in text ...)` 做子串匹配，新文字不再包含该精确子串。**需同步更新测试断言**。

- [ ] **Step 9: 修复 test_page_shows_engineering_scope_disclaimer 断言**

```python
# tests/ui/test_spline_fit_page.py L34
# 旧:
assert any("不替代 DIN 5480 / DIN 6892 工程校核" in text for text in texts)
# 新:
assert any("不替代 DIN 5480" in text and "DIN 6892" in text for text in texts)
```

- [ ] **Step 10: 重新运行全量测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: 所有测试 PASS

- [ ] **Step 11: Commit**

```bash
git add app/ui/pages/spline_fit_page.py tests/ui/test_spline_fit_page.py
git commit -m "docs(spline): improve UI hints for beginner friendliness and localize verdict level"
```

---

### Task 3: 代码健壮性（异常处理 + PDF 降级）

**Files:**
- Modify: `app/ui/pages/spline_fit_page.py:560-567,640-649`

- [ ] **Step 1: 拆分异常处理 (L560-567)**

```python
# 旧:
    def _on_calculate(self) -> None:
        try:
            payload = self._build_payload()
            result = calculate_spline_fit(payload)
        except (InputError, Exception) as exc:
            self.set_overall_status(f"输入错误: {exc}", "fail")
            self.set_info(str(exc))
            return

# 新:
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
```

- [ ] **Step 2: PDF 降级提示 (L640-649)**

```python
# 旧:
        if suffix == ".pdf":
            try:
                mod = importlib.import_module("app.ui.report_pdf_spline")
                mod.generate_spline_report(out_path, self._last_payload, self._last_result)
            except Exception:
                out_path = out_path.with_suffix(".txt")
                out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
        else:
            out_path.write_text("\n".join(self._build_report_lines()), encoding="utf-8")
        self.set_info(f"报告已导出: {out_path}")

# 新:
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
```

- [ ] **Step 3: 运行全量测试**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: 所有测试 PASS

- [ ] **Step 4: Commit**

```bash
git add app/ui/pages/spline_fit_page.py
git commit -m "fix(spline): separate InputError from generic Exception, add PDF fallback notice"
```

---

### Task 4: 补充边界测试（6 个新用例）

**Files:**
- Modify: `tests/core/spline/test_geometry.py`
- Modify: `tests/core/spline/test_calculator.py`

- [ ] **Step 1: 在 test_geometry.py 末尾追加 2 个测试**

```python
    def test_partial_explicit_geometry_raises(self):
        """Providing only some explicit dimensions should raise GeometryError."""
        with pytest.raises(GeometryError, match="显式花键几何输入不完整"):
            derive_involute_geometry(
                module_mm=1.25,
                tooth_count=10,
                reference_diameter_mm=15.0,
                # 缺少 tip_diameter_shaft_mm, root_diameter_shaft_mm, tip_diameter_hub_mm
            )

    def test_pressure_angle_out_of_range_raises(self):
        with pytest.raises(GeometryError, match="压力角"):
            derive_involute_geometry(
                module_mm=2.0,
                tooth_count=20,
                allow_approximation=True,
                pressure_angle_deg=60.0,
            )
```

- [ ] **Step 2: 运行 geometry 测试确认新增 PASS**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_geometry.py -v`
Expected: 所有测试 PASS（包括 2 个新增）

- [ ] **Step 3: 在 test_calculator.py 的 TestScenarioA 类末尾追加 2 个测试**

```python
    def test_invalid_geometry_mode_raises(self):
        case = make_scenario_a_case()
        case["spline"]["geometry_mode"] = "invalid"
        with pytest.raises(InputError, match="geometry_mode"):
            calculate_spline_fit(case)

    def test_zero_torque_raises(self):
        case = make_scenario_a_case()
        case["loads"]["torque_required_nm"] = 0.0
        with pytest.raises(InputError, match="torque_required_nm"):
            calculate_spline_fit(case)
```

- [ ] **Step 4: 在 test_calculator.py 的 TestScenarioB 类末尾追加 2 个测试**

```python
    def test_negative_relief_groove_raises(self):
        case = make_combined_case()
        case["smooth_fit"]["relief_groove_width_mm"] = -1.0
        with pytest.raises(InputError, match="不能为负数"):
            calculate_spline_fit(case)

    def test_relief_groove_exceeds_length_raises(self):
        case = make_combined_case()
        case["smooth_fit"]["relief_groove_width_mm"] = 50.0  # >= fit_length_mm (45.0)
        with pytest.raises(InputError, match="有效配合长度"):
            calculate_spline_fit(case)
```

- [ ] **Step 5: 运行全量测试确认全绿**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/ tests/ui/test_spline_fit_page.py -v`
Expected: 所有测试 PASS（包括 6 个新增）

- [ ] **Step 6: Commit**

```bash
git add tests/core/spline/test_geometry.py tests/core/spline/test_calculator.py
git commit -m "test(spline): add 6 boundary condition tests for geometry and calculator"
```
