# 花键连接校核模块 — 代码审查报告

- 日期：2026-04-16
- 审查者：Claude Code（Opus 4.6，主会话）
- 审查对象：工作区当前版本（含未提交改动）
- 目标分支：`main`（已同步至 `origin/main` `545e8f8`）

## 1. 审查范围

- `core/spline/calculator.py` — 场景 A 齿面承压 + 场景 B 光滑段过盈委托 DIN 7190
- `core/spline/geometry.py` — 渐开线花键几何推导
- `core/spline/din5480_table.py` — DIN 5480 catalog 查表
- `app/ui/pages/spline_fit_page.py` — UI 页面
- `app/ui/report_pdf_spline.py` — PDF 报告
- `examples/spline_case_01.json`、`spline_case_02.json`
- `tests/core/spline/test_calculator.py`、`test_geometry.py`
- `tests/ui/test_spline_fit_page.py`

## 2. 总体裁定

**整体 7/10**：

- 场景 B 委托 DIN 7190 很稳健，`ka` 预乘 + 委托 `ka=1.0` 的双层约定清晰，测试 `test_scenario_b_keeps_outer_design_load_trace` 验证到位；
- 场景 A 的简化定位清楚，`overall_verdict_level = "simplified_precheck"` 贯穿结果字典、UI 徽标、报告文本；
- UI 章节拆分合理（校核目标 → 花键几何 → 光滑段过盈 → 载荷工况 → 计算结果 共 5 步），AutoCalcCard / SubCard 切换逻辑覆盖到位；
- 但**近似几何公式与 DIN 5480 标准相矛盾**，是发版前必修的阻塞级问题；材料下拉未联动屈服强度也会让结果偏乐观；其余为体验与注释不严谨等次要缺陷。

## 3. 阻塞 / 重要发现

### 3.1 🔴 blocking — 近似几何公式给出的花键拓扑与 DIN 5480 相反

**位置**：`core/spline/geometry.py:85-88`

```python
d = m * z                       # 参考直径
d_a1 = m * (z + 1.0)            # 外花键齿顶圆 → d_a1 > d
d_f1 = m * (z - 1.25)           # 外花键齿根圆
d_a2 = m * (z - 1.0)            # 内花键齿顶圆
```

**问题**：
- DIN 5480 外花键 `d_a1` 实际应 **小于** `d_B`（从 `din5480_table.py` 可证实：W 25x1.25x18 实测 `d_a1=24.75 < d_B=25.0`）；
- 显式模式 `geometry.py:60` 明确校验 `d_f1 < d_a2 < d_a1 < d`；
- 近似公式推出的顺序是 `d_f1 < d_a2 < d < d_a1`，与显式校验完全相反；
- 实际上这是 20° 普通渐开线齿轮的推导，不是 30° 花键。

**工程影响**：
以 `m=1.25` 为例：
- 近似模式：`h_w = (d_a1 - d_a2)/2 = m = 1.25 mm`；
- 显式模式（同规格）：`h_w ≈ 1.125 mm`；
- 承压 `p_flank = 2T·K_α / (z·h_w·d_m·L)` 会因此系统性偏低约 10%，安全系数被虚高。

**建议**：
- 修正近似公式，使用 DIN 5480-2 表 1 的齿顶高系数（`d_a1 ≈ d - 0.1·m`，`d_a2 ≈ d - m + 0.1·m`，`d_f1 ≈ d - 2.2·m`）；
- 或者直接**移除近似模式**，强制用户选择 DIN 5480 标准目录或手工填入显式尺寸。考虑到模块定位是"简化预校核"，后者更稳妥。

### 3.2 🟠 important — `k_alpha` 语义与默认值不一致

**位置**：`core/spline/calculator.py:52` 默认 `1.0` vs `app/ui/pages/spline_fit_page.py:216` 默认 `1.3`

**问题**：
- Calculator 默认与 UI 默认不同，同一个函数经 UI 调用与被 JSON 脚本直接调用得到的结果会不同；
- UI hint 说"过盈固定连接约 1.0~1.3，滑移连接约 1.5~2.0"，偏向"承载不均匀系数"；但代码只作为单一修正因子放在 `p_flank` 分子；
- DIN 6892-1 真实需要 `K_1`（齿向）·`K_2`（齿面）·`K_3`（温度）多个系数，当前合并为一个入参容易误用。

**建议**：
- 将 calculator 默认改为 `1.3`，与 UI 对齐；
- hint 补"齿向+齿面载荷分布合成保守上限，未分解为 DIN 6892 的 K_1/K_2/K_3"；
- 在 calculator 注释明确"当前是 simplified_precheck，k_alpha 是合成系数"。

### 3.3 🟠 important — 材料下拉不同步屈服强度

**位置**：`app/ui/pages/spline_fit_page.py:82-86`（MATERIAL_LIBRARY）与 `_on_material_changed:655-662`

**问题**：
- `MATERIAL_LIBRARY` 只登记 `e_mpa` 和 `nu`，不含 `yield_mpa`；
- `_on_material_changed` 只自动填 E 和 ν，不填 `yield_mpa`；
- 选"45 钢"后 `shaft_yield_mpa` 仍保留默认 `600 MPa`（45 钢正火≈355，调质≈530）——偏向 42CrMo；
- 场景 B 里轴应力安全系数 `sigma_sf = Re / σ_max` 会被系统性高估。

**建议**：
- 扩展 `MATERIAL_LIBRARY`：

```python
MATERIAL_LIBRARY = {
    "45钢": {"e_mpa": 210000.0, "nu": 0.30, "yield_mpa": 355.0},
    "40Cr": {"e_mpa": 210000.0, "nu": 0.29, "yield_mpa": 785.0},
    "42CrMo": {"e_mpa": 210000.0, "nu": 0.29, "yield_mpa": 930.0},
    "自定义": None,
}
```

- `_on_material_changed` 同步填充并锁定 `yield_mpa` 字段；
- 切回"自定义"时解除锁定。

## 4. 重要但非阻塞

### 4.1 🟡 场景 A 缺扭矩容量安全系数字段

**位置**：`core/spline/calculator.py:101-120`

`scenario_a` 返回 `flank_safety = p_zul/p_flank` 和 `torque_capacity_nm`，但没有返回 `torque_capacity_sf = T_cap / T_design`。两者在数学上等价，但工程读者常用后者判断。建议在结果字典里补 `torque_capacity_sf` 字段，UI 和报告同步展示。

### 4.2 🟡 DIN 5480 catalog 数据来源注释不严谨

**位置**：`core/spline/din5480_table.py:1-6`

注释写 "d_a1 = d_B - 0.1*m (公差带 e 偏移近似)"，但同时默认压力角是 30°（正好是 DIN 5480 标准齿形）。"公差带 e 偏移" 与 "齿顶高系数 h_a*" 是两个概念，注释把它们混在一起。

建议重写为：

```python
"""DIN 5480 involute spline catalog —— 常用 W 15~50 规格。

数据来源：DIN 5480-2:2015 表 1，30° 压力角系列。
- 齿顶高系数 h_a* = 0.45（外花键），h_a* = 0.55（内花键）
- 齿根高系数 h_f* ≈ 0.60~0.75（视倒角而定）
- 给出 d_a1、d_f1、d_a2 为标准名义值；实际工程应以采购件实测或目录值为准。
"""
```

### 4.3 🟡 `K_A` 与 `k_alpha` 双乘叠加的语义易被误读

**位置**：`core/spline/calculator.py:85, 214`

- L214：`torque_design_nm = torque_required_nm * ka`
- L85：`p_flank = (2 * T_design * k_alpha) / (...)`

数学等价于 `p = 2·T·K_A·K_α / (...)`，但分两步乘入。读者容易以为代码漏乘其中之一。建议在 L85 上方加一行注释：

```python
# ka 已在 torque_design_nm 层预乘，这里仅乘 k_alpha（齿面载荷分布）
```

## 5. 可选改进

### 5.1 UI 下拉切回"自定义"时字段数值保留

**位置**：`app/ui/pages/spline_fit_page.py:592-624`

选了标准规格（如 W 25x1.25x18）后再切"自定义"，7 个字段解除 AutoCalcCard 锁定，但数值仍保留上次标准值，用户以为在输入新值其实还是旧标准值。

**建议**：切回"自定义"时把 `module_mm / tooth_count / reference_diameter_mm / tip_diameter_shaft_mm / root_diameter_shaft_mm / tip_diameter_hub_mm` 恢复到 FieldSpec 的 `default`；或者保留值但在结果页顶部加一个 `"当前几何沿用上次标准值"` 的提示条。

### 5.2 多处 hint 为空

`spline_fit_page.py:285, 291, 306, 313, 317, 322, 327, 332, 337, 342` 这些 FieldSpec 的 `hint=""`。建议补背景提示，比如：

- E：`"钢 E ≈ 210 GPa，铝 E ≈ 70 GPa"`
- μ：`"钢-钢油润滑 ≈ 0.10，干配合 ≈ 0.14"`
- Rz：`"精磨 Rz ≈ 3.2~6.3 μm，磨削 ≈ 1.6~3.2 μm"`

### 5.3 `din5480_table.py` 缺单元测试

目录 `tests/core/spline/` 下没有 `test_din5480_table.py`。catalog 本身没有单元测试，只靠 UI 测试 `test_standard_designation_autofills_geometry` 间接覆盖。

**建议**补 1 个测试文件，验证：
- `lookup_by_designation("W 25x1.25x18")` 返回的 dict 字段齐全；
- 所有条目的 `d_f1 < d_a2 < d_a1 < d_B` 单调关系；
- `all_designations()` 不含重复项。

### 5.4 `spline_only` 模式下仍带 `smooth_*` 字段进 payload

**位置**：`app/ui/pages/spline_fit_page.py:813-835`

`_build_payload` 不区分模式，禁用的 `smooth_*` 字段值仍会被注入 payload（calculator 虽会忽略）。保存输入条件 JSON 时会多出一堆无用数据。

**建议**：`_build_payload` 开头读取 `mode`，若是 `spline_only` 则只收集 `spline` / `loads` / `checks` 三节。

## 6. 引用关系与风格检查

| 项 | 结果 |
|----|------|
| `core/spline/calculator.py` → `core/spline/geometry.py` | ✓ |
| 场景 B 运行时 lazy import `core.interference.calculator` | ✓（避免循环） |
| `app/ui/pages/spline_fit_page.py` → `core.spline.*` | ✓（无反向） |
| `core → app` 反向导入 | 无 ✓ |
| Unicode 智能引号 U+201C/U+201D | 无 ✓ |
| DIN 7190 委托时 `ka=1.0 + 预乘` 约定清晰 | ✓ |
| PDF 模块 `app/ui/report_pdf_spline.py` 存在 + 文本回退 | ✓ |

## 7. 选项有意义性总览

| 章节 | 选项数 | 有意义？ | 备注 |
|------|--------|---------|------|
| 校核目标 | 5 | ✓ | mode + 3 SF + KA 完整 |
| 花键几何 | 11 | 基本 ✓ | load_condition 预设仅 4 种偏少；近似几何公式与 DIN 5480 冲突（见 §3.1） |
| 光滑段过盈 | 21 | ✓ | `yield_mpa` 未随材料联动（见 §3.3） |
| 载荷工况 | 2 | ✓ | axial_force 在仅花键模式下有明确禁用提示 |
| 计算结果 | 0 | ✓ | badge + detail + 压入力曲线 + 消息框 |

## 8. 建议修复顺序

1. §3.1 修正近似几何公式或移除近似模式（blocking，影响所有 approximate 用户）；
2. §3.3 材料下拉联动屈服强度（important，影响 45 钢案例正确性）；
3. §3.2 对齐 k_alpha 默认值 + 注释；
4. §4.1 + §4.2 + §4.3 重要注释与字段补齐；
5. §5.1 ~ §5.4 体验与测试完善。

详细步骤见配套执行计划 `docs/plans/2026-04-16-spline-fit-fixes.md`。

## 9. 参考

- DIN 5480-2:2015 表 1（压力角 30° 渐开线花键，齿顶高系数 h_a*）
- DIN 6892-1（花键连接承载能力计算）
- 设计文档：`docs/superpowers/plans/2026-03-29-spline-workflow-alignment.md`
- 设计文档：`docs/superpowers/specs/2026-03-29-spline-workflow-alignment-design.md`
- 之前的修复报告：`docs/reports/2026-03-25-spline-review-fixes-and-enhancements.md`
