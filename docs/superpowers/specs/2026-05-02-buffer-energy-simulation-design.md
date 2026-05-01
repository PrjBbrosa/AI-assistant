# 缓冲块吸能仿真设计规格

**日期**: 2026-05-02  
**模块**: 缓冲块吸能仿真（新增独立 section / 独立页面）  
**范围**: `core/buffer/`, `app/ui/pages/`, `app/ui/widgets/`, `examples/`, `tests/`

## Goal

新增一个用于单次冲击场景的缓冲块吸能仿真 section。用户导入缓冲块测试得到的加载 / 卸载力-位移曲线（CSV 或 XLSX），输入质量、初速度、可用行程和峰值力限制后，工具用能量法输出最大压缩量、峰值输出力、吸收能量、耗散能量、回弹能量和估算回弹速度。

该 section 不要求用户提供弹簧刚度 `k` 或阻尼系数 `c`。缓冲块模型以测试曲线为准，阻尼只作为由滞回面积推导出的等效耗能指标展示，避免把单一粘性阻尼系数误当成材料常数。

## Problem Statement

实际对象是缓冲块，而不是理想线性质量-弹簧-阻尼器。用户目前能提供的数据是加载和卸载两条 `F-x` 曲线，没有 `F-t`、`x-t` 或速度历史。

在这种数据边界下：

- 可以可靠计算加载曲线面积、卸载曲线面积和滞回耗散能量。
- 可以通过初始动能 `E0 = 0.5 * m * v0^2` 与加载能量积分反推出最大压缩量。
- 可以读取最大压缩位置处的加载力作为峰值输出力估算。
- 可以用卸载能量估算回弹速度。
- 不能唯一识别真实粘性阻尼系数 `c`，也不应把 `c` 作为主输入或主要结果。

因此第一版应以“单次冲击 + 滞回曲线能量法”为核心，而不是做通用动力学积分平台。

## Scope

### In Scope

- 单次冲击工况。
- 用户导入 CSV 或 XLSX 曲线文件。
- 支持加载曲线和卸载曲线。
- 支持两种曲线表格形态：
  - 宽表：`x_mm`, `loading_force_n`, `unloading_force_n`
- 长表：`branch`, `x_mm`, `force_n`，其中 `branch` 支持 `loading` / `unloading`，也支持中文值 `加载` / `卸载`
- 曲线校验、清洗和插值：
  - 位移单位 mm，力单位 N
  - 力值非负
  - 位移点可排序，重复点按同一位移合并
  - 加载 / 卸载曲线都转换为位移升序数组
  - 卸载力不得系统性高于加载力；允许局部小噪声并给 warning
- 梯形积分计算能量。
- 冲击工况输入：
  - 质量 `mass_kg`
  - 初始速度 `initial_velocity_m_s`
  - 可用行程 `available_stroke_mm`
  - 允许峰值力 `allowable_peak_force_n`
  - 曲线力倍率 `force_scale`
  - 曲线行程倍率 `stroke_scale`
- 输出：
  - 初始动能
  - 最大压缩量
  - 峰值输出力
  - 是否超行程 / 触底
  - 是否超过允许峰值力
  - 加载吸收能量
  - 卸载回弹能量
  - 滞回耗散能量
  - 吸能比例
  - 估算回弹速度
  - 曲线派生指标：最大测试行程、最大测试力、等效刚度、局部刚度范围
- 章节式页面、输入条件保存 / 加载、结果说明导出。
- core、曲线导入、UI smoke 和报告文本测试。

### Out of Scope

- 多次循环、热累积、疲劳、永久变形衰减。
- 基于时间域的真实阻尼拟合。
- 非线性微分方程时域积分。
- 摩擦接触、导轨摩擦、重力、外力时程。
- 多个缓冲块空间并联 / 串联的装配级模型。
- 材料本构拟合或橡胶超弹性参数识别。
- 图片曲线自动识别。第一版只接受 CSV / XLSX 数据文件。

## Design Principles

- **测试曲线优先**：缓冲块本体行为以用户导入的加载 / 卸载 `F-x` 曲线为准。
- **能量解释优先**：面向用户展示能量守恒和滞回耗能，而不是伪造单一 `k/c`。
- **导入格式宽容但字段语义严格**：允许 CSV / XLSX、宽表 / 长表，但字段含义必须明确。
- **core 与 UI 分离**：曲线解析、积分、冲击反推放在 core；UI 只负责导入、参数收集、结果展示和报告。
- **限制显式化**：页面和报告都必须说明结果基于准静态或已测 `F-x` 曲线，速度效应只能通过不同测试曲线或倍率间接表达。
- **渐进扩展**：第一版先完成单次冲击能量法，后续如有 `F-t` / `x-t` 数据再扩展时域动力学。

## Candidate Approaches

### Approach A: F-x 滞回曲线能量法（推荐）

做法：导入加载 / 卸载 `F-x` 曲线，积分得到能量曲线。用初始动能与加载能量相交点确定最大压缩量，再从卸载曲线估算回弹能量与回弹速度。

优点：

- 与用户现有数据完全匹配。
- 保留缓冲块非线性刚度和滞回吸能特性。
- 结果物理解释清晰。
- 不需要引入不可靠的单一阻尼系数。

缺点：

- 不能输出真实时间历程。
- 无法从单条准静态曲线精确表达速度效应。

### Approach B: 等效线性 `k/c` 模型

做法：用曲线拟合一个等效刚度 `k_eq` 和等效阻尼 `c_eq`，再按质量-弹簧-阻尼模型计算。

优点：

- 形式简单，用户熟悉。
- 可以输出类似传统动力学的时间响应。

缺点：

- 会丢失缓冲块非线性和滞回曲线形状。
- 只有 `F-x` 时无法唯一识别 `c`。
- 容易给用户造成“阻尼参数已被真实识别”的误解。

### Approach C: 非线性时域积分

做法：把加载和卸载曲线作为非线性力模型，按速度方向切换曲线并积分运动方程。

优点：

- 后续可扩展到更完整的动力学仿真。
- 可以产生时间序列输出。

缺点：

- 只有 `F-x` 曲线时路径切换和耗能分配需要额外假设。
- 第一版复杂度高，验证成本高。

## Recommended Approach

采用 **Approach A：F-x 滞回曲线能量法**。

第一版页面命名为 **缓冲块吸能仿真**。它面向单次冲击选型：给定质量、速度、行程限制和峰值力限制，判断当前缓冲块曲线是否足够吸能，以及峰值力和回弹是否可接受。

## User Experience

### Entry Placement

在 `MainWindow` 左侧模块导航中新增独立入口：

- `缓冲块吸能仿真`

该入口与赫兹应力、过盈配合、蜗轮蜗杆等模块并列。页面不挂靠在现有弹簧、材料或标准库入口下。

### Chapter Layout

页面继续基于 `BaseChapterPage` 构建，章节建议为：

1. `测试曲线导入`
2. `曲线检查与能量`
3. `单次冲击工况`
4. `吸能结果`
5. `参数对比`
6. `结果说明 / 导出`

### Actions

顶部动作区：

- `导入曲线文件`
- `保存输入条件`
- `加载输入条件`
- `执行仿真`
- `清空参数`
- `导出结果说明`
- `测试案例 1`
- `测试案例 2`

### Curve Import UX

用户点击 `导入曲线文件` 后，通过文件选择器选择 `.csv` 或 `.xlsx`。

CSV：

- 使用 UTF-8 / UTF-8-SIG 优先解析。
- 第一行必须是表头。
- 分隔符第一版支持逗号，必要时可自动兼容制表符。

XLSX：

- 第一版读取第一个工作表。
- 第一行必须是表头。
- 实现计划中应新增轻量依赖 `openpyxl>=3.1`，不引入 `pandas`。

宽表格式：

```csv
x_mm,loading_force_n,unloading_force_n
0,0,0
5,800,300
10,1800,900
```

长表格式：

```csv
branch,x_mm,force_n
loading,0,0
loading,5,800
loading,10,1800
unloading,10,900
unloading,5,300
unloading,0,0
```

字段别名第一版可支持少量中英文常见表头：

- 位移：`x_mm`, `displacement_mm`, `位移_mm`
- 加载力：`loading_force_n`, `force_loading_n`, `加载力_n`
- 卸载力：`unloading_force_n`, `force_unloading_n`, `卸载力_n`
- 分支：`branch`, `phase`, `曲线`；字段值支持 `loading`, `load`, `加载`, `压缩`, `unloading`, `unload`, `卸载`, `回弹`
- 力：`force_n`, `力_n`

导入后页面显示：

- 文件名
- 行数
- 识别到的格式：宽表 / 长表
- 加载点数和卸载点数
- 最大行程
- 最大加载力
- warning 列表

## Core API

新增 `core/buffer/calculator.py`。

### Input Payload

```python
{
    "curve": {
        "loading": [{"x_mm": float, "force_n": float}, ...],
        "unloading": [{"x_mm": float, "force_n": float}, ...],
    },
    "impact": {
        "mass_kg": float,
        "initial_velocity_m_s": float,
        "available_stroke_mm": float,
        "allowable_peak_force_n": float,
    },
    "options": {
        "force_scale": float,
        "stroke_scale": float,
        "noise_tolerance_n": float,
    },
}
```

### Output Schema

```python
{
    "inputs_echo": dict,
    "curve_summary": {
        "max_stroke_mm": float,
        "peak_loading_force_n": float,
        "loading_energy_j": float,
        "unloading_energy_j": float,
        "dissipated_energy_j": float,
        "energy_absorption_ratio": float,
        "equivalent_stiffness_n_per_mm": float,
        "tangent_stiffness_min_n_per_mm": float,
        "tangent_stiffness_max_n_per_mm": float,
    },
    "impact": {
        "initial_energy_j": float,
        "available_energy_capacity_j": float,
        "max_compression_mm": float,
        "peak_force_n": float,
        "absorbed_energy_j": float,
        "rebound_energy_j": float,
        "dissipated_energy_j": float,
        "estimated_rebound_velocity_m_s": float,
    },
    "checks": {
        "stroke_ok": bool,
        "peak_force_ok": bool,
        "energy_capacity_ok": bool,
    },
    "overall_pass": bool,
    "curves": {
        "loading_x_mm": list[float],
        "loading_force_n": list[float],
        "unloading_x_mm": list[float],
        "unloading_force_n": list[float],
        "loading_energy_x_mm": list[float],
        "loading_energy_j": list[float],
    },
    "warnings": list[str],
    "assumptions": list[str],
}
```

## Calculation Details

### Unit Conversion

曲线积分时使用：

```text
1 N * 1 mm = 0.001 J
```

### Curve Normalization

- 将位移和力转换为 float。
- 应用倍率：
  - `x_scaled = x_mm * stroke_scale`
  - `force_scaled = force_n * force_scale`
- 加载和卸载曲线分别按 `x_scaled` 升序排序。
- 相同位移的重复点合并为平均力。
- 若加载曲线起点不是 `(0, 0)`，在不改变原数据的前提下补充一个用于积分的 `(0, 0)` 点并给 warning。
- 若卸载曲线缺少 `x=0`，补充 `(0, 0)` 点并给 warning。

### Energy Integration

加载累计能量：

```text
E_load[i] = sum(0.5 * (F[i-1] + F[i]) * (x[i] - x[i-1]) * 0.001)
```

卸载总能量同样按升序 `x` 的曲线面积计算。若卸载曲线来自实际回程降序数据，归一化后仍用升序面积。

滞回耗散：

```text
E_diss = max(0, E_load_total - E_unload_total)
```

吸能比例：

```text
absorption_ratio = E_diss / E_load_total
```

### Impact Solve

初始能量：

```text
E0 = 0.5 * mass_kg * initial_velocity_m_s^2
```

先按可用行程截断加载曲线容量：

```text
effective_stroke_mm = min(available_stroke_mm, max_stroke_mm)
available_energy_capacity_j = E_load(effective_stroke_mm)
```

若 `E0 <= available_energy_capacity_j`，在加载能量曲线上插值求解 `E_load(x) = E0`：

- `max_compression_mm = x_at_E0`
- `peak_force_n = F_loading(x_at_E0)`
- `absorbed_energy_j = E0`
- `energy_capacity_ok = True`

若 `E0 > available_energy_capacity_j`：

- `max_compression_mm = effective_stroke_mm`
- `peak_force_n = F_loading(effective_stroke_mm)`
- `absorbed_energy_j = available_energy_capacity_j`
- `energy_capacity_ok = False`
- warning：输入动能超过可用行程内吸能容量，结果表示触底前可吸收能力，不代表真实触底冲击峰值。

### Rebound Estimate

回弹能量按最大压缩量截断卸载曲线面积：

```text
E_rebound = ∫_0^x_max F_unloading(x) dx
```

估算回弹速度：

```text
v_rebound = sqrt(2 * E_rebound / mass_kg)
```

本结果命名为“估算回弹速度”，页面和报告需声明它来自卸载曲线能量，不是时间域仿真结果。

### Checks

```text
stroke_ok = max_compression_mm <= available_stroke_mm
peak_force_ok = peak_force_n <= allowable_peak_force_n
energy_capacity_ok = E0 <= available_energy_capacity_j
overall_pass = stroke_ok and peak_force_ok and energy_capacity_ok
```

若 `available_stroke_mm` 大于测试曲线最大行程，仍只能用测试曲线最大行程作为有效容量，并给 warning：测试曲线未覆盖全部可用行程。只要求解出的最大压缩量未超过可用行程，`stroke_ok` 可以通过；但 `energy_capacity_ok` 不允许基于未知曲线外推通过。

## UI Result Presentation

### Curve Panel

新增 `BufferEnergyCurveWidget`：

- 绘制加载曲线和卸载曲线。
- 标出最大压缩点。
- 标出可用行程线。
- 标出允许峰值力线。
- 显示滞回面积的简化填充。

第一版可使用现有项目风格的 `QPainter` 自绘，避免为单个曲线控件额外扩大 matplotlib 使用面。

### Result Cards

结果页包含：

- 总体结论：通过 / 不通过 / 超出曲线容量
- 关键结果值：
  - 初始动能
  - 最大压缩量
  - 峰值输出力
  - 吸收能量
  - 滞回耗散能量
  - 回弹能量
  - 估算回弹速度
- 分项校核：
  - 行程校核
  - 峰值力校核
  - 曲线能量容量校核
- 消息与建议：
  - 若触底：建议增大行程、换更高吸能曲线或降低冲击速度
  - 若峰值力过高：建议更软曲线或增加可用行程
  - 若回弹速度高：建议更高滞回耗能缓冲块

### Parameter Comparison

第一版支持轻量参数对比：

- 力倍率：例如 `0.8, 1.0, 1.2`
- 行程倍率：例如 `0.8, 1.0, 1.2`

结果以表格展示：

- `force_scale`
- `stroke_scale`
- `max_compression_mm`
- `peak_force_n`
- `energy_capacity_ok`
- `stroke_ok`
- `peak_force_ok`
- `estimated_rebound_velocity_m_s`

## File Changes

预计实现涉及：

- 新增 `core/buffer/__init__.py`
- 新增 `core/buffer/calculator.py`
- 新增 `core/buffer/curve_import.py`
- 新增 `app/ui/pages/buffer_energy_page.py`
- 新增 `app/ui/widgets/buffer_energy_curve.py`
- 修改 `app/ui/main_window.py` 注册新模块
- 新增 `examples/buffer_energy_case_01.csv`
- 新增 `examples/buffer_energy_case_02.xlsx`
- 新增 `examples/buffer_energy_input_conditions.json`
- 修改 `requirements.txt` 增加 `openpyxl>=3.1`
- 新增 `tests/core/buffer/test_calculator.py`
- 新增 `tests/core/buffer/test_curve_import.py`
- 新增 `tests/ui/test_buffer_energy_page.py`

## Error Handling

导入错误使用用户可理解的中文消息：

- 文件类型不支持：只支持 `.csv` / `.xlsx`
- 缺少表头
- 未识别到位移列
- 未识别到加载曲线
- 未识别到卸载曲线
- 位移或力不是数字
- 质量、初速度、行程、峰值力必须为正
- 加载曲线总能量为 0
- 卸载曲线面积大于加载曲线面积时给 warning；若超出容差过多，阻断计算

## Testing Strategy

### Core Tests

- 梯形积分单位换算正确。
- 用简单三角曲线验证加载 / 卸载能量。
- 初始动能小于容量时能插值得到正确压缩量。
- 初始动能超过容量时返回 `energy_capacity_ok=False`。
- 可用行程小于曲线最大行程时按可用行程容量判定。
- 卸载能量正确截断到 `x_max`。
- 回弹速度公式正确。
- 峰值力校核和行程校核独立生效。

### Import Tests

- CSV 宽表解析成功。
- CSV 长表解析成功。
- XLSX 宽表解析成功。
- XLSX 长表解析成功。
- 常见中文表头别名解析成功。
- 缺列、非数字、空文件、无卸载曲线给出 `InputError`。

### UI Tests

- 页面可构造。
- 加载测试案例后执行仿真不抛异常。
- 结果页包含最大压缩、峰值力、吸收能量、回弹速度。
- 分项 badge 从待计算更新为通过 / 不通过。
- 导入错误通过 message box 展示，不会让页面崩溃。

## Documentation and Report

结果说明和报告必须包含：

- “本工具基于加载 / 卸载 F-x 曲线的单次冲击能量法。”
- “未使用时间域数据，不能唯一识别真实粘性阻尼系数 c。”
- “回弹速度为基于卸载曲线能量的估算值。”
- “若输入动能超过曲线容量，峰值力不代表触底后的真实冲击峰值。”

## Acceptance Criteria

- 用户可以导入 CSV 或 XLSX 的加载 / 卸载曲线。
- 用户可以输入质量和初速度并执行单次冲击仿真。
- 结果能明确回答：
  - 缓冲块是否有足够能量容量
  - 是否超过可用行程
  - 峰值输出力是多少
  - 吸收 / 耗散 / 回弹能量分别是多少
  - 估算回弹速度是多少
- UI 不要求用户输入 `k` 或 `c`。
- 所有核心计算有单元测试覆盖。
- 页面与现有 `BaseChapterPage` 模块风格一致。
