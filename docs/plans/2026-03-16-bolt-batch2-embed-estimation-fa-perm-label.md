# Batch 2: 嵌入损失经验估算 + 附加载荷标注修正 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据 VDI 2230 表 5.4/1 提供嵌入损失参考值（用户可覆盖），并将附加载荷能力估算从正式校核项降级为参考信息，不再影响 overall_pass。

**Architecture:** Calculator 新增 `_estimate_embed_loss()` 辅助函数，当 `embed_loss == 0` 且表面粗糙度信息可用时自动估算（模式与热损失自动估算一致）。`additional_load_ok` 从 `checks_out` 移至独立 `references` 字典，不参与 `overall_pass` 判定。UI 新增表面粗糙度下拉，结果展示增强。

**Tech Stack:** Python 3.12, PySide6, pytest

**Existing test runner:** `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`

**Existing test file:** `tests/core/bolt/test_calculator.py` — 28 tests across 6 classes + `_base_input()` helper.

**Key conventions:**
- Calculator: `calculate_vdi2230_core(data: dict) -> dict`，纯 Python，无 Qt
- UI fields: `FieldSpec(field_id, label, unit, hint, mapping, widget_type, options, default, disabled)`
- `mapping=None` → UI-only; `mapping=("section", "key")` → included in payload
- Auto-estimation pattern (see thermal): when user input is 0, auto-fill from derived params, set `*_auto_estimated: bool` flag
- `_build_payload()` builds dict; `_render_result()` displays output

**Physical formulas:**
```
嵌入损失公式 (VDI 2230 §5.4.2):
  f_Z = f_z_per_interface × n_interfaces    [μm]
  F_Z = f_Z × 1e-3 / (δ_S + δ_P)           [N]

界面数:
  螺纹孔(tapped): n_interfaces = part_count + 1  (头端 + part间 + 螺纹底)
  通孔(through):   n_interfaces = part_count + 2  (头端 + part间 + 螺母端 + 螺纹)

典型单界面嵌入量 (VDI 2230 表 5.4/1 简化):
  粗糙 (Ra ≈ 6.3 μm): f_z ≈ 3.0 μm
  中等 (Ra ≈ 3.2 μm): f_z ≈ 2.5 μm
  精细 (Ra ≈ 1.6 μm): f_z ≈ 1.0 μm
```

---

## Chunk 1: Calculator — 嵌入损失估算 + 附加载荷降级

### Task 1: Calculator — 嵌入损失自动估算

**Files:**
- Modify: `core/bolt/calculator.py:123` (embed_loss reading) + `core/bolt/calculator.py:205` (after thermal section)
- Test: `tests/core/bolt/test_calculator.py`

**Context:** 当前 `embed_loss` 完全由用户手动输入（line 123）。新增自动估算逻辑：当 `embed_loss == 0` 且 `clamped.surface_class` 可用时，根据 `joint_type`、`part_count`、`surface_class` 和刚度自动计算。模式与热损失自动估算（line 173-203）完全平行。

- [ ] **Step 1: Write failing tests**

在 `tests/core/bolt/test_calculator.py` 末尾添加：

```python
class TestEmbedEstimation:
    def test_embed_auto_when_zero_and_surface_class_provided(self):
        """embed_loss=0 + surface_class → 自动估算。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 1, "surface_class": "medium"}
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is True
        assert embed["embed_auto_value_N"] > 0
        assert embed["embed_interfaces"] == 2  # tapped, 1 part → 1+1=2

    def test_embed_manual_value_preserved(self):
        """embed_loss > 0 → 不自动估算，保持用户值。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 800.0
        data["clamped"] = {"part_count": 1, "surface_class": "medium"}
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is False
        assert embed["embed_auto_value_N"] == 0.0

    def test_embed_skipped_without_surface_class(self):
        """无 surface_class → 不估算。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        # no surface_class in clamped
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is False

    def test_embed_through_joint_more_interfaces(self):
        """通孔连接比螺纹孔连接多 1 个界面。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 2, "surface_class": "medium"}
        # tapped: 2+1=3 interfaces
        result_tapped = calculate_vdi2230_core(data)
        # through: 2+2=4 interfaces
        data["options"] = {"joint_type": "through"}
        result_through = calculate_vdi2230_core(data)
        assert result_tapped["embed_estimation"]["embed_interfaces"] == 3
        assert result_through["embed_estimation"]["embed_interfaces"] == 4
        assert result_through["embed_estimation"]["embed_auto_value_N"] > \
               result_tapped["embed_estimation"]["embed_auto_value_N"]

    def test_embed_rougher_surface_higher_loss(self):
        """粗糙表面嵌入损失更大。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 1, "surface_class": "rough"}
        result_rough = calculate_vdi2230_core(data)
        data["clamped"]["surface_class"] = "fine"
        result_fine = calculate_vdi2230_core(data)
        assert result_rough["embed_estimation"]["embed_auto_value_N"] > \
               result_fine["embed_estimation"]["embed_auto_value_N"]

    def test_embed_formula_correctness(self):
        """验证公式: F_Z = f_z_per_if × n_if × 1e-3 / (δs + δp)。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 1, "surface_class": "medium"}
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        delta_s = data["stiffness"]["bolt_compliance"]
        delta_p = data["stiffness"]["clamped_compliance"]
        expected = 2.5 * 2 * 1e-3 / (delta_s + delta_p)  # medium=2.5μm, 2 interfaces
        assert abs(embed["embed_auto_value_N"] - expected) < 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestEmbedEstimation -v`
Expected: 6 FAILED (KeyError on `result["embed_estimation"]`)

- [ ] **Step 3: Implement embed loss estimation**

In `core/bolt/calculator.py`, after the `_resolve_compliance` function (line 71), add:

```python
# VDI 2230 表 5.4/1 简化：典型单界面嵌入量 (μm)
_EMBED_FZ_PER_INTERFACE: dict[str, float] = {
    "rough": 3.0,    # Ra ≈ 6.3 μm
    "medium": 2.5,   # Ra ≈ 3.2 μm
    "fine": 1.0,     # Ra ≈ 1.6 μm
}


def _estimate_embed_loss(
    joint_type: str,
    part_count: int,
    surface_class: str,
    delta_s: float,
    delta_p: float,
) -> dict[str, Any]:
    """根据 VDI 2230 表 5.4/1 估算嵌入损失。

    Returns dict with embed_auto_estimated, embed_auto_value_N,
    embed_interfaces, embed_fz_per_if_um.
    """
    fz_per_if = _EMBED_FZ_PER_INTERFACE.get(surface_class)
    if fz_per_if is None:
        return {
            "embed_auto_estimated": False,
            "embed_auto_value_N": 0.0,
            "embed_interfaces": 0,
            "embed_fz_per_if_um": 0.0,
        }
    if joint_type == "through":
        n_interfaces = part_count + 2
    else:
        n_interfaces = part_count + 1
    fz_total_mm = fz_per_if * n_interfaces * 1e-3
    f_z = fz_total_mm / (delta_s + delta_p)
    return {
        "embed_auto_estimated": True,
        "embed_auto_value_N": f_z,
        "embed_interfaces": n_interfaces,
        "embed_fz_per_if_um": fz_per_if,
    }
```

In `calculate_vdi2230_core`, after the thermal section (after line 203) and before `f_slip_required` (line 205), add embed estimation:

```python
    # ------------------------------------------------------------------
    # 嵌入损失自动估算 (VDI 2230 §5.4.2)
    # ------------------------------------------------------------------
    part_count = int(clamped.get("part_count", 1))
    surface_class = clamped.get("surface_class")
    embed_estimation: dict[str, Any]
    if embed_loss == 0.0 and surface_class is not None:
        embed_estimation = _estimate_embed_loss(
            joint_type, part_count, str(surface_class), delta_s, delta_p
        )
        if embed_estimation["embed_auto_estimated"]:
            embed_loss = embed_estimation["embed_auto_value_N"]
    else:
        embed_estimation = {
            "embed_auto_estimated": False,
            "embed_auto_value_N": 0.0,
            "embed_interfaces": 0,
            "embed_fz_per_if_um": 0.0,
        }
```

In the return dict (around line 365), add after the `"clamped_info"` entry:

```python
        "embed_estimation": embed_estimation,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestEmbedEstimation -v`
Expected: 6 PASSED

- [ ] **Step 5: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All 64 pass (existing tests unaffected — embed_estimation is a new output key, not breaking)

- [ ] **Step 6: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): add VDI 2230 embed loss auto-estimation"
```

---

### Task 2: Calculator — 附加载荷从正式校核降级为参考

**Files:**
- Modify: `core/bolt/calculator.py:299-303` (checks_out construction)
- Modify: `core/bolt/calculator.py:345-349` (forces output)
- Modify: `core/bolt/calculator.py:378` (overall_pass)
- Test: `tests/core/bolt/test_calculator.py`

**Context:** 当前 `additional_load_ok` 在 `checks_out` 字典中，参与 `overall_pass = all(checks_out.values())` 计算。Phase 7 要求将其降级为参考信息——移入独立字段，不影响 overall_pass。

- [ ] **Step 1: Write failing tests**

```python
class TestAdditionalLoadReference:
    def test_additional_load_not_in_checks(self):
        """additional_load_ok 不再出现在 checks 字典中。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert "additional_load_ok" not in result["checks"]

    def test_additional_load_in_references(self):
        """附加载荷信息出现在 references 字典中。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        ref = result["references"]
        assert "additional_load_ok" in ref
        assert "FA_perm_N" in ref
        assert ref["is_reference"] is True

    def test_overall_pass_ignores_additional_load(self):
        """overall_pass 不受附加载荷估算影响 — 正式校核全过即 overall_pass=True。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        # 正式校核全部通过 → overall_pass 为 True
        assert result["overall_pass"] is True
        # additional_load_ok 不在 checks 中，无论其值如何都不影响 overall_pass
        assert "additional_load_ok" not in result["checks"]
        assert "additional_load_ok" in result["references"]

    def test_fa_perm_value_unchanged(self):
        """FA_perm 计算值不变。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        ref = result["references"]
        phi_n = result["intermediate"]["phi_n"]
        rp02 = data["fastener"]["Rp02"]
        as_val = result["derived_geometry_mm"]["As"]
        expected = 0.1 * rp02 * as_val / phi_n
        assert abs(ref["FA_perm_N"] - expected) < 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestAdditionalLoadReference -v`
Expected: 4 FAILED

- [ ] **Step 3: Implement additional_load separation**

In `core/bolt/calculator.py`, modify `checks_out` (around line 299) to remove `additional_load_ok`:

```python
    checks_out = {
        "assembly_von_mises_ok": pass_assembly,
        "operating_axial_ok": pass_work,
        "residual_clamp_ok": pass_residual,
    }
```

Modify `forces` dict (around line 345) to remove `FA_perm_N`:

```python
        "forces": {
            "F_bolt_work_max_N": f_bolt_work_max,
            "F_K_residual_N": f_k_residual,
        },
```

Add a new `references` dict in the return (after `"forces"`):

```python
        "references": {
            "additional_load_ok": pass_additional,
            "FA_perm_N": f_a_perm,
            "is_reference": True,
            "note": "附加载荷能力为参考估算（基于 10% Rp0.2 裕量），非 VDI 2230 正式校核项",
        },
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestAdditionalLoadReference -v`
Expected: 4 PASSED

- [ ] **Step 5: Verify no existing tests break**

Confirmed by grep: no existing test in `test_calculator.py` references `forces["FA_perm_N"]` or `checks["additional_load_ok"]`. All 28 existing tests should pass unchanged.

UI code in `bolt_page.py` references `force['FA_perm_N']` (line 1653, 1762) and `checks.get("additional_load_ok")` (line 1703) — these will be fixed in Task 4.

- [ ] **Step 6: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: Some UI tests MAY fail if they reference `forces["FA_perm_N"]`. If so, those will be fixed in Task 4 alongside the UI changes. Calculator tests should all pass.

- [ ] **Step 7: Commit**

```bash
git add core/bolt/calculator.py tests/core/bolt/test_calculator.py
git commit -m "feat(bolt): move additional_load to references, not affecting overall_pass"
```

---

## Chunk 2: UI — 表面粗糙度 + 展示更新

### Task 3: UI — 新增表面粗糙度字段 + 嵌入损失 hint 更新

**Files:**
- Modify: `app/ui/pages/bolt_page.py` — CHAPTERS loads section, add surface_class field
- Modify: `app/ui/pages/bolt_page.py` — embed_loss FieldSpec hint update
- Modify: `app/ui/pages/bolt_page.py` — THERMAL_FIELD_IDS 附近新增 EMBED_FIELD_IDS

**Context:** 新增 `clamped.surface_class` 下拉选择（粗糙/中等/精细），默认"中等"。此字段在所有校核层级都可见（嵌入损失不是温度相关功能）。同时更新 `embed_loss` 的 hint 说明自动估算逻辑。

- [ ] **Step 1: Add surface_class constant mapping**

In `app/ui/pages/bolt_page.py`, after `THERMAL_EXPANSION_PRESETS` (around line 576), add:

```python
SURFACE_CLASS_MAP: dict[str, str] = {
    "粗糙 (Ra≈6.3μm)": "rough",
    "中等 (Ra≈3.2μm)": "medium",
    "精细 (Ra≈1.6μm)": "fine",
}
```

- [ ] **Step 2: Add surface_class FieldSpec to clamped chapter**

In CHAPTERS, in the `"clamped"` chapter `"fields"` list, after the `clamped.part_count` field (line 270), add:

```python
            FieldSpec(
                "clamped.surface_class",
                "接触面粗糙度",
                "-",
                "用于嵌入损失自动估算。选择后当嵌入损失 FZ=0 时自动计算参考值。",
                mapping=("clamped", "surface_class"),
                widget_type="choice",
                options=("粗糙 (Ra≈6.3μm)", "中等 (Ra≈3.2μm)", "精细 (Ra≈1.6μm)"),
                default="中等 (Ra≈3.2μm)",
            ),
```

- [ ] **Step 3: Update _build_payload to translate surface_class**

In `_build_payload`, after the `joint_type` injection block, add:

```python
        sc_widget = self._field_widgets.get("clamped.surface_class")
        if sc_widget and isinstance(sc_widget, QComboBox):
            sc_text = sc_widget.currentText()
            payload.setdefault("clamped", {})["surface_class"] = SURFACE_CLASS_MAP.get(sc_text, "medium")
```

- [ ] **Step 4: Update embed_loss FieldSpec hint**

Change the `loads.embed_loss` FieldSpec hint (around line 353) to:

```python
                "接触表面压平导致的预紧力损失。填 0 时若已选择接触面粗糙度，"
                "将按 VDI 2230 表 5.4/1 自动估算。",
```

- [ ] **Step 5: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): add surface_class dropdown for embed loss estimation"
```

---

### Task 4: UI — 结果展示更新（embed info + additional_load 降级）

**Files:**
- Modify: `app/ui/pages/bolt_page.py` — `_render_result` method
- Modify: `app/ui/pages/bolt_page.py` — `_build_recommendations` method
- Modify: `app/ui/pages/bolt_page.py` — `_build_report_lines` method
- Modify: `app/ui/pages/bolt_page.py` — `CHECK_LABELS` dict

**Context:** Two changes in one task:
1. When embed auto-estimation is active, show the estimated value and interface count in metrics
2. `additional_load_ok` moved from `checks` to `references` — update all UI code that reads it

- [ ] **Step 1: Update _render_result for references and embed info**

In `_render_result`, the line that reads `force['FA_perm_N']` (around line 1653):

Replace:
```python
            f"• 附加载荷参考: FA,max = {fa_max:.1f} N  /  参考上限 {force['FA_perm_N']:.1f} N  (⚠ 参考估算，非 VDI 标准项)",
```

With:
```python
            f"• 附加载荷参考: FA,max = {fa_max:.1f} N  /  参考上限 {result.get('references', {}).get('FA_perm_N', 0):.1f} N  (⚠ 参考估算，非 VDI 标准项)",
```

After the thermal metric line block, add embed estimation info:

```python
        embed_est = result.get("embed_estimation", {})
        if embed_est.get("embed_auto_estimated"):
            metric_lines.append(
                f"• 嵌入损失估算: FZ = {embed_est['embed_auto_value_N']:.0f} N"
                f"  ({embed_est['embed_interfaces']} 个界面 × {embed_est['embed_fz_per_if_um']:.1f} μm)"
            )
```

- [ ] **Step 2: Update _build_recommendations for references**

In `_build_recommendations` (around line 1703), change:

```python
        if not checks.get("additional_load_ok", True):
            recs.append("[建议] 附加载荷超限：可提高 As、降低 n 或减少轴向外载。")
```

To:

```python
        refs = result.get("references", {})
        if not refs.get("additional_load_ok", True):
            recs.append("[参考] 附加载荷超限（参考估算）：可提高 As、降低 n 或减少轴向外载。")
```

- [ ] **Step 3: Update _build_report_lines for references**

In `_build_report_lines` (around line 1762), change:

```python
                f"- FA_perm: {forces['FA_perm_N']:.2f} N",
```

To:

```python
                f"- FA_perm: {result.get('references', {}).get('FA_perm_N', 0):.2f} N (参考估算)",
```

- [ ] **Step 4: Update CHECK_LABELS and add reference badge handling**

In `CHECK_LABELS` dict (around line 544), update the `additional_load_ok` label to mark it as reference (keep the key, just change text):

```python
CHECK_LABELS = {
    "assembly_von_mises_ok": "装配等效应力校核（VDI R4）",
    "operating_axial_ok": "服役轴向应力校核（VDI R5）",
    "residual_clamp_ok": "残余夹紧力校核（VDI R3）",
    "additional_load_ok": "附加载荷能力估算 ⚠ 参考",
    "thermal_loss_ok": "温度损失影响校核",
    "fatigue_ok": "疲劳校核（简化 Goodman）",
    "bearing_pressure_ok": "支承面压强校核（R7）",
}
```

Why keep it in CHECK_LABELS: the badge widget is created during UI construction from this dict. Removing the key would lose the widget entirely. We keep the key but relabel it as "参考".

In `_render_result`, the existing badge loop will set `additional_load_ok` to "已跳过" (WaitBadge) because it's no longer in `result["checks"]`. We override this after the loop by reading from `result["references"]` instead:

```python
        # 附加载荷参考 badge（从 references 读取，不在 checks 中）
        ref_badge = self._check_badges.get("additional_load_ok")
        if ref_badge:
            refs = result.get("references", {})
            ref_pass = refs.get("additional_load_ok", True)
            self._set_badge(ref_badge, "通过" if ref_pass else "超限（仅参考）", ref_pass)
```

- [ ] **Step 6: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add app/ui/pages/bolt_page.py
git commit -m "feat(bolt/ui): embed estimation display + additional_load as reference"
```

---

### Task 5: Flowchart — R1 嵌入损失信息展示

**Files:**
- Modify: `app/ui/pages/bolt_flowchart.py:449-456` (_format_calc_text for r1)

**Context:** R1 详情页展示 FM_min 推导过程。当使用了嵌入损失自动估算时，在 R1 公式下方显示估算参数。

- [ ] **Step 1: Update R1 _format_calc_text**

In `app/ui/pages/bolt_flowchart.py`, update the `r1` block in `_format_calc_text`:

```python
        if step_id == "r1":
            embed_est = result.get("embed_estimation", {})
            embed_note = ""
            if embed_est.get("embed_auto_estimated"):
                embed_note = (
                    f"\n\n嵌入损失估算: {embed_est['embed_interfaces']} 界面"
                    f" × {embed_est['embed_fz_per_if_um']:.1f} μm"
                    f" → FZ = {embed_est['embed_auto_value_N']:.0f} N"
                )
            return (
                f"FK,slip = FQ/(μT×qF) = {inter.get('F_slip_required_N', 0):,.0f} N\n"
                f"FK,req  = max(FK,seal, FK,slip) = {inter.get('F_K_required_N', 0):,.0f} N\n"
                f"FM,min  = FK,req + (1-φn)×FA + FZ + Fth\n"
                f"        = {inter.get('FMmin_N', 0):,.0f} N\n"
                f"FM,max  = αA × FM,min = {inter.get('FMmax_N', 0):,.0f} N"
                f"{embed_note}"
            )
```

- [ ] **Step 2: Run full test suite**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add app/ui/pages/bolt_flowchart.py
git commit -m "feat(bolt/ui): show embed estimation details in R1 flowchart step"
```

---

### Task 6: 集成测试 + 示例 JSON 更新

**Files:**
- Test: `tests/core/bolt/test_calculator.py`
- Modify: `examples/input_case_01.json`
- Modify: `examples/input_case_02.json`

- [ ] **Step 1: Write integration test**

```python
class TestBatch2Integration:
    def test_embed_estimation_with_thermal_full_chain(self):
        """嵌入损失估算 + 热估算 + R7 全链路。"""
        data = _base_input()
        data["options"] = {
            "check_level": "thermal",
            "joint_type": "tapped",
        }
        data["loads"]["embed_loss"] = 0
        data["loads"]["thermal_force_loss"] = 0
        data["clamped"] = {
            "part_count": 2,
            "surface_class": "medium",
            "total_thickness": 25.0,
        }
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 23.0e-6,
        }
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        # embed estimation activated
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is True
        assert embed["embed_interfaces"] == 3  # tapped, 2 parts
        # thermal auto estimation activated
        assert result["thermal"]["thermal_auto_estimated"] is True
        # additional_load is reference, not in checks
        assert "additional_load_ok" not in result["checks"]
        assert "additional_load_ok" in result["references"]
        # overall_pass based only on formal checks
        assert isinstance(result["overall_pass"], bool)

    def test_manual_embed_overrides_estimation(self):
        """手动嵌入损失 > 0 时不使用自动估算。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 1500.0
        data["clamped"] = {"part_count": 1, "surface_class": "rough"}
        result = calculate_vdi2230_core(data)
        assert result["embed_estimation"]["embed_auto_estimated"] is False
        # FM_min 中使用的是手动值 1500，而非估算值
        inter = result["intermediate"]
        phi_n = inter["phi_n"]
        fa = data["loads"]["FA_max"]
        # basic check_level (default) → thermal_effective = 0.0
        expected_fmmin = inter["F_K_required_N"] + (1 - phi_n) * fa + 1500.0 + 0.0
        assert abs(inter["FMmin_N"] - expected_fmmin) < 1.0
```

- [ ] **Step 2: Run integration tests**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py::TestBatch2Integration -v`
Expected: 2 PASSED

- [ ] **Step 3: Update example JSON files**

In `examples/input_case_01.json`, add to the `"clamped"` section (create if absent):
```json
  "clamped": {
    "surface_class": "medium",
    "part_count": 1,
    "total_thickness": 20
  },
```

In `examples/input_case_02.json`, same addition.

Note: If `"clamped"` section already exists in the JSON, merge into it. If not, add it before `"checks"`.

- [ ] **Step 4: Run full test suite one final time**

Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v`
Expected: All pass (64 existing + ~12 new = ~76 total)

- [ ] **Step 5: Commit**

```bash
git add tests/core/bolt/test_calculator.py examples/
git commit -m "test(bolt): integration tests for embed estimation + additional_load reference"
```
