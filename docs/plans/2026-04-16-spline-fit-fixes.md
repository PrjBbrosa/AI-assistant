# 花键连接校核 — 修复执行计划

- 日期：2026-04-16
- 关联报告：`docs/reports/2026-04-16-spline-fit-review.md`
- 基线：`main @ 545e8f8`（注意本模块有未提交 M 改动，需先就地完成或 stash 后再开展下列修复）
- 优先级目标：发版前清除 1 个 blocking + 2 个 important + 3 个 medium 发现

## 总体策略

按"几何正确性 → 物性数据联动 → 语义对齐 → 体验补齐 → 测试加固"的顺序推进。每条发现独立 commit，便于审查与回退。所有修复都应用 TDD：先补测试让当前行为暴露为失败，再改实现。

## Step 1 — 修复近似几何公式（blocking）

**对应发现**：§3.1

### 目标
让 `approximate` 模式推导出的 DIN 5480 渐开线花键几何与真实标准一致，满足 `d_f1 < d_a2 < d_a1 < d_B`。

### 改动点

`core/spline/geometry.py:85-94` 修改为 DIN 5480-2 附录 A 规定的齿顶/齿根高系数推导：

```python
elif allow_approximation:
    # DIN 5480-2 近似（30° 压力角，齿顶高系数 h_a* ≈ 0.45）
    d = m * z
    d_a1 = d - 0.1 * m           # 外花键齿顶（公差带 e 中位近似）
    d_f1 = d - 2.2 * m           # 外花键齿根
    d_a2 = d - m + 0.1 * m       # 内花键齿顶（= d - 0.9 * m）
    geometry_source = "approximation_from_module_and_tooth_count"
    approximation_used = True
    messages.append(
        "当前花键几何采用 DIN 5480 近似推导（h_a*=0.45），"
        "仅适合简化预校核。"
    )
```

若决定**移除近似模式**（更稳妥，推荐），则：
- `allow_approximation` 路径直接抛 `GeometryError`；
- `calculator.py:58-60` 删除 `approximate` 选项；
- UI `GEOMETRY_MODE_OPTIONS` 只保留 "公开/图纸尺寸" 单选（或干脆移除该下拉）；
- 必须同步更新 `test_geometry.py` 中所有 `allow_approximation=True` 的测试，以及 `test_calculator.py` 的 `make_scenario_a_case()`（目前用 `approximate` + `module_mm=2.0, tooth_count=20`）。

本计划按"修正而非移除"假设编写后续步骤；若改为移除，合并 Step 1 到 Step 2 并把示例 `spline_case_02.json` 改为 `reference_dimensions`。

### 新增/修改测试

`tests/core/spline/test_geometry.py`：

```python
def test_approximation_matches_din5480_topology():
    """Approximation must satisfy d_f1 < d_a2 < d_a1 < d_B."""
    r = derive_involute_geometry(
        module_mm=1.25, tooth_count=12, allow_approximation=True
    )
    d, d_a1, d_a2, d_f1 = (
        r["reference_diameter_mm"], r["tip_diameter_shaft_mm"],
        r["tip_diameter_hub_mm"], r["root_diameter_shaft_mm"],
    )
    assert d_f1 < d_a2 < d_a1 < d

def test_approximation_aligns_with_catalog_w25x125():
    """近似 h_w 与 catalog 实测值相对误差 <= 10%."""
    from core.spline.din5480_table import lookup_by_designation
    ref = lookup_by_designation("W 25x1.25x18")
    approx = derive_involute_geometry(
        module_mm=1.25, tooth_count=18, allow_approximation=True
    )
    h_w_ref = (ref["tip_diameter_shaft_mm"] - ref["tip_diameter_hub_mm"]) / 2
    h_w_approx = approx["effective_tooth_height_mm"]
    assert abs(h_w_approx - h_w_ref) / h_w_ref < 0.10
```

**注意**：现有 `test_basic_m2_z20` 会失败（旧公式推出 `d_a1=42, d_f1=37.5, d_a2=38`），需改为新公式期望值或删除。

### 验收标准
- 新测试通过；
- 近似模式推出的 `h_w ≈ m * 0.9`（而非 `m`）；
- `spline_case_02.json`（`approximate` 模式）重新计算结果与修正前有约 10% 差异，需人工评估是否更新 `test_nominal_case_passes` 的通过阈值。

---

## Step 2 — 材料下拉联动屈服强度

**对应发现**：§3.3

### 目标
选择 45钢/40Cr/42CrMo 时，UI 自动填入对应屈服强度并锁定；选"自定义"时解锁。

### 改动点

#### 2.1 材料库扩展
`app/ui/pages/spline_fit_page.py:82-86`：

```python
MATERIAL_LIBRARY: dict[str, dict[str, float] | None] = {
    "45钢":   {"e_mpa": 210000.0, "nu": 0.30, "yield_mpa": 355.0},
    "40Cr":  {"e_mpa": 210000.0, "nu": 0.29, "yield_mpa": 785.0},
    "42CrMo":{"e_mpa": 210000.0, "nu": 0.29, "yield_mpa": 930.0},
    "自定义": None,
}
```

屈服强度来源：GB/T 3077-2015（40Cr 调质 σ_s ≥ 785 MPa，42CrMo 调质 σ_s ≥ 930 MPa）、GB/T 699-2015（45 钢正火 σ_s ≥ 355 MPa）。若按"调质 45 钢"取 σ_s ≈ 530 MPa 则相应调整；**建议取正火值作为保守下限**。

#### 2.2 自动填充逻辑
`app/ui/pages/spline_fit_page.py:_on_material_changed`：

```python
def _on_material_changed(self, field_prefix: str, material_name: str) -> None:
    ...
    e_fid = f"{field_prefix}_e_mpa"
    nu_fid = f"{field_prefix}_nu"
    yield_fid = f"{field_prefix}_yield_mpa"
    if material is None:
        if MODE_MAP.get(self._get_value("mode")) == "combined":
            for fid in (e_fid, nu_fid, yield_fid):
                self._set_card_disabled(fid, False)
        ...
        return
    for fid, key in ((e_fid, "e_mpa"), (nu_fid, "nu"), (yield_fid, "yield_mpa")):
        widget = self._widgets.get(fid)
        if isinstance(widget, QLineEdit):
            widget.setText(str(material[key]))
        self._set_card_disabled(fid, True)
    ...
```

### 新增测试

`tests/ui/test_spline_fit_page.py`：

```python
def test_material_choice_autofills_yield_strength(app):
    page = SplineFitPage()
    shaft_material = page._widgets["smooth_materials.shaft_material"]
    shaft_yield = page._widgets["smooth_materials.shaft_yield_mpa"]

    shaft_material.setCurrentText("40Cr")
    assert shaft_yield.text() == "785.0"

    shaft_material.setCurrentText("42CrMo")
    assert shaft_yield.text() == "930.0"

    shaft_material.setCurrentText("自定义")
    assert page._field_cards["smooth_materials.shaft_yield_mpa"].objectName() == "SubCard"
```

### 验收标准
- 新测试通过；
- 既有 UI 测试 `test_material_choice_autofills_elastic_properties` 依然通过；
- 手工回归：加载测试案例，切材料，观察 yield_mpa 跟随变化。

---

## Step 3 — 对齐 k_alpha 默认值 + 注释

**对应发现**：§3.2

### 目标
- Calculator 与 UI 的 `k_alpha` 默认值一致；
- hint/注释解释清楚"合成保守上限"的含义。

### 改动点

#### 3.1 Calculator
`core/spline/calculator.py:51-53`：

```python
k_alpha = _positive(
    float(spline.get("k_alpha", 1.3)),  # 从 1.0 改为 1.3
    "spline.k_alpha",
)
```

同时在 `p_flank = ...` 行上方加注释：

```python
# p = 2·T·k_alpha / (z·h_w·d_m·L)
# K_A 已在 torque_design_nm 预乘（见 L214），此处只乘 k_alpha（齿面载荷分布合成）
# k_alpha 合成了 DIN 6892-1 的 K_1（齿向）·K_2（齿面），保守取上限
p_flank = (2.0 * T_design_nmm * k_alpha) / (z * h_w * d_m * L)
```

#### 3.2 UI hint
`app/ui/pages/spline_fit_page.py:213-216`：

```python
FieldSpec(
    "spline.k_alpha", "载荷分布系数 K_alpha", "-",
    "合成的齿向+齿面载荷分布系数（保守上限，未分解为 DIN 6892 的 K_1/K_2/K_3）。"
    "过盈固定连接约 1.0~1.3，滑移连接约 1.5~2.0。",
    mapping=("spline", "k_alpha"),
    default="1.3", placeholder="例如 1.1~2.0",
),
```

### 测试
无须新增（既有公式校验已覆盖）。需更新 `test_calculator.py::test_nominal_case_passes` 和 `test_flank_pressure_formula`：原测试 `k_alpha=1.0` 显式传入，不受 default 影响 — 无需改动。但新增一条 default 断言：

```python
def test_k_alpha_default_matches_ui():
    data = {
        "mode": "spline_only",
        "spline": {
            "geometry_mode": "reference_dimensions",
            "module_mm": 1.25, "tooth_count": 12,
            "reference_diameter_mm": 15.0,
            "tip_diameter_shaft_mm": 14.75,
            "root_diameter_shaft_mm": 12.1,
            "tip_diameter_hub_mm": 12.5,
            "engagement_length_mm": 40.0,
            "p_allowable_mpa": 100.0,
            # k_alpha 未指定，应采用默认 1.3
        },
        "loads": {"torque_required_nm": 50.0, "application_factor_ka": 1.0},
        "checks": {"flank_safety_min": 1.3},
    }
    result = calculate_spline_fit(data)
    assert result["scenario_a"]["k_alpha"] == pytest.approx(1.3)
```

### 验收标准
- 新测试通过；
- UI default 显示 "1.3"，与 calculator default 一致。

---

## Step 4 — 新增扭矩容量安全系数 `torque_capacity_sf`

**对应发现**：§4.1

### 目标
结果字典新增 `torque_capacity_sf = T_cap / T_design`，UI 与报告同步展示。

### 改动点

#### 4.1 Calculator
`core/spline/calculator.py:_calculate_scenario_a`：

```python
torque_capacity_sf = T_cap_nm / torque_design_nm if torque_design_nm > 0 else math.inf
return {
    ...
    "torque_capacity_sf": torque_capacity_sf,
    ...
}
```

#### 4.2 UI 结果页
`spline_fit_page.py:_display_result` 场景 A 的 detail 文本加一行：

```python
f"扭矩容量安全系数 S_T = {a['torque_capacity_sf']:.2f}"
```

#### 4.3 报告
`spline_fit_page.py:_build_report_lines` 场景 A 章节追加：

```python
f"扭矩容量安全系数 S_T = {a['torque_capacity_sf']:.2f}",
```

### 测试
```python
def test_torque_capacity_sf_matches_flank_sf():
    result = calculate_spline_fit(make_scenario_a_case())
    # 两者在数学上相等
    a = result["scenario_a"]
    assert a["torque_capacity_sf"] == pytest.approx(a["flank_safety"], rel=1e-6)
```

---

## Step 5 — DIN 5480 catalog 注释规范化

**对应发现**：§4.2

### 目标
`core/spline/din5480_table.py` 的 docstring 与代码一致，引用明确标准条款。

### 改动点
只改 L1-6 docstring：

```python
"""DIN 5480 involute spline catalog —— 常用 W 15~50 规格。

数据来源：DIN 5480-2:2015 表 1（30° 压力角系列）。
- 齿顶高系数 h_a* = 0.45（外花键）、h_a* = 0.55（内花键）
- 齿根高系数 h_f* ≈ 0.55~0.75（含齿根倒角）
- d_a1、d_f1、d_a2 为标准名义值；实际工程应以采购件实测或目录值为准。
"""
```

无新增测试。视具体条款号与厂商目录对齐后可进一步细化。

---

## Step 6 — 可选体验改进

### 6.1 标准规格切回"自定义"时恢复默认值
`spline_fit_page.py:_on_standard_designation_changed` 第 `else` 分支（目前缺失）加：

```python
else:
    # 切回自定义时把几何字段恢复到 FieldSpec default
    for fid in _STANDARD_GEOMETRY_FIELD_IDS:
        spec = self._field_specs.get(fid)
        w = self._widgets.get(fid)
        if spec is not None and isinstance(w, QLineEdit):
            w.setText(spec.default)
```

测试：`test_standard_designation_custom_restores_defaults`。

### 6.2 补充 hint

为 `smooth_materials.shaft_e_mpa / shaft_nu / hub_e_mpa / hub_nu / hub_yield_mpa / mu_* / shaft_rz_um / hub_rz_um` 添加背景说明，统一在 FieldSpec `hint` 参数里补。非必须，可留到下一轮。

### 6.3 `din5480_table.py` 单元测试
新建 `tests/core/spline/test_din5480_table.py`：

```python
from core.spline.din5480_table import DIN5480_CATALOG, all_designations, lookup_by_designation


def test_lookup_returns_complete_record():
    record = lookup_by_designation("W 25x1.25x18")
    assert record is not None
    for key in (
        "module_mm", "tooth_count", "reference_diameter_mm",
        "tip_diameter_shaft_mm", "root_diameter_shaft_mm", "tip_diameter_hub_mm",
    ):
        assert key in record


def test_all_designations_unique():
    names = all_designations()
    assert len(names) == len(set(names))


def test_catalog_topology_consistent():
    """每个 catalog 条目必须满足 d_f1 < d_a2 < d_a1 < d_B."""
    for entry in DIN5480_CATALOG:
        d = entry["reference_diameter_mm"]
        d_a1 = entry["tip_diameter_shaft_mm"]
        d_a2 = entry["tip_diameter_hub_mm"]
        d_f1 = entry["root_diameter_shaft_mm"]
        assert d_f1 < d_a2 < d_a1 < d, f"Topology violated for {entry['designation']}"
```

### 6.4 `_build_payload` 按模式过滤 smooth_*
```python
def _build_payload(self) -> dict:
    mode = MODE_MAP.get(self._get_value("mode"), "spline_only")
    active_sections = {"spline", "loads", "checks"}
    if mode == "combined":
        active_sections |= {"smooth_fit", "smooth_materials", "smooth_roughness", "smooth_friction"}

    payload: dict[str, Any] = {"mode": mode}
    for section in active_sections:
        payload[section] = {}
    ...
    for chapter in CHAPTERS:
        for spec in chapter["fields"]:
            if spec.mapping is None:
                continue
            section, key = spec.mapping
            if section not in active_sections:
                continue
            ...
    return payload
```

## Step 7 — 回归验证

### 7.1 测试套件
```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline tests/ui/test_spline_fit_page.py -v
```
目标：全绿，无新增 warning。

### 7.2 全套 pytest
```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
目标：346 passed（或更新后的数字）。

### 7.3 手工回归
1. 启动 `python3 app/main.py`，切到"花键连接校核"；
2. 加载测试案例 1（`reference_dimensions` 模式），计算应通过；
3. 加载测试案例 2（`approximate` 模式），观察结果变化是否与预期（由于 Step 1 修复了 h_w）；
4. 切换"联合"模式，换材料为 "40Cr"，确认 yield 自动填 785；
5. 选一个 DIN 5480 规格，再切回"自定义"，几何字段应恢复 FieldSpec default；
6. 导出 PDF 报告，验证内容包含 `S_T` 扭矩容量安全系数行。

## Step 8 — 文档与示例更新

- `README.md`：花键连接校核行的说明不变（保持"部分完成"或按本轮结论升级）；
- `CLAUDE.md`：花键模块段落补上"近似几何已按 DIN 5480 重新推导"或"已移除近似模式"；
- `examples/spline_case_02.json`：若 Step 1 修改了近似公式结果，确认示例载荷仍能通过；否则降扭矩或切 `reference_dimensions`；
- 新增 `docs/reports/2026-04-XX-spline-fix-followup.md` 记录实际修复与偏离决策。

## 风险与回退

- **Step 1** 会改变 `approximate` 模式下 h_w 数值约 10%，可能导致 `test_nominal_case_passes` 等测试在未更新阈值前失败。修复时先跑一次测试套件，把所有因公式改动失败的断言一并更新，避免混入其他改动；
- **Step 2** 修改 `MATERIAL_LIBRARY` 会影响 `test_snapshot_round_trip_preserves_ui_only_state` 等 UI 测试（如果它们对"自定义"路径敏感）。需要全量跑 UI 测试；
- **Step 6.4** 的 payload 过滤会让旧保存 JSON 里无用 smooth_* 数据在重新保存后丢失。这是预期行为，但用户若依赖该数据需要在 commit message 里明示。

## 提交建议

每个 Step 一个独立 commit：

1. `fix(spline-geom): correct DIN 5480 approximation to satisfy tip/root ordering`
2. `feat(spline-ui): auto-fill yield strength when choosing preset material`
3. `fix(spline-core): align k_alpha default with UI and clarify docstring`
4. `feat(spline-core): expose torque_capacity_sf in scenario A result`
5. `docs(spline): normalize din5480_table docstring`
6. `feat(spline-ui): restore geometry defaults when switching standard→custom`（可选）
7. `test(spline): add catalog topology unit tests and payload mode filter test`
