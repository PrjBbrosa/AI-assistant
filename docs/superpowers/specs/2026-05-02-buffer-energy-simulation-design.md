# 缓冲块吸能仿真设计规格

**日期**: 2026-05-02  
**模块**: 缓冲块吸能仿真（新增独立 section / 独立页面）  
**范围**: `core/buffer/`, `app/ui/pages/`, `app/ui/widgets/`, `examples/`, `tests/`

## Goal

新增一个用于单次冲击场景的缓冲块吸能仿真 section。用户导入缓冲块测试得到的加载 / 卸载力-位移曲线（CSV 或 XLSX），输入质量、初速度、可用行程和峰值力限制后，工具用能量法输出最大压缩量、峰值输出力、吸收能量、耗散能量、回弹能量和估算回弹速度，并在能量解之上由能量守恒反推近似的位移 / 速度 / 加速度 / 反力时间历程。

该 section 不要求用户提供弹簧刚度 `k` 或阻尼系数 `c`。缓冲块模型以测试曲线为准，阻尼只作为由滞回面积推导出的等效耗能指标展示，避免把单一粘性阻尼系数误当成材料常数。时域响应曲线是基于准静态 F-x 曲线反推的时间映射，不含应变率效应，仅供选型阶段的波形参考。

## Problem Statement

实际对象是缓冲块，而不是理想线性质量-弹簧-阻尼器。用户目前能提供的数据是加载和卸载两条 `F-x` 曲线，没有 `F-t`、`x-t` 或速度历史。

在这种数据边界下：

- 可以可靠计算加载曲线面积、卸载曲线面积和滞回耗散能量。
- 可以通过初始动能 `E0 = 0.5 * m * v0^2` 与加载能量积分反推出最大压缩量。
- 可以读取最大压缩位置处的加载力作为峰值输出力估算。
- 可以用卸载能量估算回弹速度。
- 可以由能量守恒 `v(x) = sqrt(2(E0 − E_load(x))/m)` 反推时间映射 `t(x)`，得到近似的 `x(t)` / `v(t)` / `a(t)` / `F(t)` 曲线。
- 不能唯一识别真实粘性阻尼系数 `c`，也不应把 `c` 作为主输入或主要结果。
- 反推得到的时间历程不含应变率效应，仅是准静态曲线在时间轴上的重排，不能替代真正的时域动力学仿真。

因此第一版应以“单次冲击 + 滞回曲线能量法”为核心，并在其上提供由能量守恒衍生的近似时域响应曲线，而不是做通用动力学积分平台。

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
  - 峰值输出力（触底时标记为不可判定）
  - 平均反力 `F_avg = absorbed_energy / max_compression`
  - 是否触底（`bottom_out`）、是否超行程、是否超过允许峰值力
  - 加载吸收能量
  - 卸载回弹能量
  - 工况下耗散能量（吸收 − 回弹）
  - 测试曲线整体滞回能量
  - 吸能比例
  - 估算回弹速度
  - 曲线派生指标：最大测试行程、最大测试力、等效刚度、局部刚度范围
  - 由能量守恒反推的近似时间历程：`x(t)`、`v(t)`、`a(t)`、`F(t)` 以及总接触时长 `duration_s`
- 章节式页面、输入条件保存 / 加载、结果说明导出。
- core、曲线导入、UI smoke 和报告文本测试。

### Out of Scope

- 多次循环、热累积、疲劳、永久变形衰减。
- 基于时间域的真实阻尼拟合（`c` 不被识别）。
- 非线性微分方程时域积分（不基于真实 ODE 求解，仅由能量守恒反推时间映射）。
- 应变率效应、橡胶/泡沫的速率敏感本构。
- 摩擦接触、导轨摩擦、重力做功、外力时程（默认水平冲击或重力相对动能可忽略）。
- 多个缓冲块空间并联 / 串联的装配级模型。
- 材料本构拟合或橡胶超弹性参数识别。
- 图片曲线自动识别。第一版只接受 CSV / XLSX 数据文件。

## Design Principles

- **测试曲线优先**：缓冲块本体行为以用户导入的加载 / 卸载 `F-x` 曲线为准。
- **能量解释优先**：面向用户展示能量守恒和滞回耗能，而不是伪造单一 `k/c`。
- **导入格式宽容但字段语义严格**：允许 CSV / XLSX、宽表 / 长表，但字段含义必须明确。
- **core 与 UI 分离**：曲线解析、积分、冲击反推放在 core；UI 只负责导入、参数收集、结果展示和报告。
- **限制显式化**：页面和报告都必须说明结果基于准静态或已测 `F-x` 曲线，速度效应只能通过不同测试曲线或倍率间接表达；时域曲线是由能量守恒反推的映射，不含应变率效应。
- **渐进扩展**：第一版完成单次冲击能量法 + 由能量守恒反推的近似时间历程；后续如有真实 `F-t` / `x-t` 数据再扩展真实时域动力学。

## Candidate Approaches

### Approach A: F-x 滞回曲线能量法（推荐）

做法：导入加载 / 卸载 `F-x` 曲线，积分得到能量曲线。用初始动能与加载能量相交点确定最大压缩量，再从卸载曲线估算回弹能量与回弹速度。

优点：

- 与用户现有数据完全匹配。
- 保留缓冲块非线性刚度和滞回吸能特性。
- 结果物理解释清晰。
- 不需要引入不可靠的单一阻尼系数。
- 可以零额外假设地由能量守恒反推近似 `x(t)` / `v(t)` / `a(t)` / `F(t)`，向用户提供波形示意。

缺点：

- 反推时间历程不含应变率效应，不是真实时域仿真。
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

采用 **Approach A：F-x 滞回曲线能量法 + 能量守恒时域反推**。

第一版页面命名为 **缓冲块吸能仿真**。它面向单次冲击选型：给定质量、速度、行程限制和峰值力限制，判断当前缓冲块曲线是否足够吸能、峰值力和回弹是否可接受，并提供由能量守恒反推的近似响应时程，便于评估冲击波形和接触时长。

## User Experience

### Entry Placement

在 `MainWindow` 左侧模块导航中新增独立入口：

- `缓冲块吸能仿真`

该入口与赫兹应力、过盈配合、蜗轮蜗杆等模块并列。页面不挂靠在现有弹簧、材料或标准库入口下。

### Chapter Layout

页面继续基于 `BaseChapterPage` 构建，左侧仍保留步骤式导航，但第 4 章必须采用 **方案 A 工作台总览**：一屏同时展示关键指标、F-x 曲线、总体结论、模型边界和参数对比摘要，避免结果被完全拆散到多个章节。

章节建议为：

1. `测试曲线导入`
2. `曲线检查与能量`
3. `单次冲击工况`
4. `吸能结果`
5. `响应时程`
6. `参数对比`
7. `结果说明 / 导出`

其中：

- `吸能结果` 是主工作台页面，不是纯文本结果页。
- `响应时程` 是时域曲线的详细页；`吸能结果` 中只保留接触时长和响应页入口级摘要。
- `参数对比` 是完整对比表页；`吸能结果` 右侧 rail 中只显示 3-5 行高信号摘要。

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
        "force_scale": float,            # 力倍率，默认 1.0
        "stroke_scale": float,           # 行程倍率，默认 1.0
        "noise_tolerance_n": float,      # 卸载力局部高于加载力时的容差阈值（N），默认 5.0
        "time_samples": int,             # 时域反推总采样点数（压缩+回弹），默认 200
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
        "curve_hysteresis_energy_j": float,           # 整条测试曲线的滞回面积
        "energy_absorption_ratio": float,             # curve_hysteresis / loading_energy
        "equivalent_stiffness_n_per_mm": float,       # peak_loading_force / max_stroke
        "tangent_stiffness_min_n_per_mm": float,      # 加载曲线相邻点差分极小值
        "tangent_stiffness_max_n_per_mm": float,      # 加载曲线相邻点差分极大值
    },
    "impact": {
        "initial_energy_j": float,
        "available_energy_capacity_j": float,
        "max_compression_mm": float,
        "peak_force_n": Optional[float],              # 触底时为 None
        "peak_force_status": str,                     # "ok" | "exceeds_limit" | "bottom_out_unknown"
        "average_force_n": float,                     # absorbed_energy / max_compression
        "absorbed_energy_j": float,
        "rebound_energy_j": float,
        "impact_dissipated_energy_j": float,          # absorbed - rebound（实际工况下耗散）
        "estimated_rebound_velocity_m_s": float,
        "bottom_out": bool,                           # E0 是否超过曲线在可用行程内的容量
    },
    "checks": {
        "stroke_ok": bool,                            # bottom_out 时强制 False
        "peak_force_ok": Optional[bool],              # bottom_out 时为 None（不可判定）
        "energy_capacity_ok": bool,
    },
    "overall_pass": bool,                             # 任一 check 为 False 或 None 则整体不通过
    "curves": {
        "loading_x_mm": list[float],
        "loading_force_n": list[float],
        "unloading_x_mm": list[float],
        "unloading_force_n": list[float],
        "loading_energy_x_mm": list[float],
        "loading_energy_j": list[float],
    },
    "time_response": Optional[{
        "duration_s": float,                          # 总接触时长（压缩 + 回弹）
        "compression_duration_s": float,              # 0 → x_max 的时间
        "rebound_duration_s": float,                  # x_max → 0 的时间
        "time_s": list[float],
        "displacement_mm": list[float],
        "velocity_m_s": list[float],                  # 压缩段为正，回弹段为负
        "acceleration_m_s2": list[float],
        "force_n": list[float],
    }],                                               # 触底或反推失败时为 None / 仅压缩段
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
- 相同位移的重复点合并为平均力（位移差小于 `1e-6 mm` 视为重复）。
- 若加载曲线起点不是 `(0, 0)`，补充 `(0, 0)` 点并给 warning。
- 若卸载曲线缺少 `x=0`，补充 `(0, 0)` 点并给 warning。
- 若卸载曲线最大位移小于加载曲线最大位移，补一个 `(x_load_max, F_load_max)` 点（假设卸载从加载顶点开始）并给 warning。
- 若任一卸载点的力比同位移加载力高出 `noise_tolerance_n`（默认 5 N），给 warning；若超过 `5 × noise_tolerance_n` 则抛 `InputError`，因为这违反耗散假设。
- 所有插值（能量积分、能量反求位移、时域反推）统一使用线性插值。

### Curve-derived Indicators

- `equivalent_stiffness_n_per_mm = peak_loading_force_n / max_stroke_mm`
- 切线刚度由加载曲线相邻两点差分得到：`k_i = (F[i+1] - F[i]) / (x[i+1] - x[i])`，取这些值的最小值与最大值作为 `tangent_stiffness_min/max`。差分时跳过位移变化小于 `1e-6 mm` 的点对。

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

若 `E0 <= available_energy_capacity_j`（未触底）：

- `max_compression_mm = x_at_E0`（线性插值求解 `E_load(x) = E0`）
- `peak_force_n = F_loading(x_at_E0)`
- `absorbed_energy_j = E0`
- `bottom_out = False`
- `energy_capacity_ok = True`
- `peak_force_status = "ok"` 或 `"exceeds_limit"`，取决于是否超过 `allowable_peak_force_n`

若 `E0 > available_energy_capacity_j`（触底）：

- `max_compression_mm = effective_stroke_mm`
- `peak_force_n = None`（触底后真实冲击峰值未知，不输出数值）
- `peak_force_status = "bottom_out_unknown"`
- `absorbed_energy_j = available_energy_capacity_j`
- `bottom_out = True`
- `energy_capacity_ok = False`
- `stroke_ok = False`（即使位移恰好等于可用行程，触底语义上仍判 False）
- `peak_force_ok = None`（不可判定）
- warning：输入动能超过可用行程内吸能容量；测试曲线无法表达触底后的接触刚化，真实冲击峰值会显著高于曲线末端力。

平均反力：

```text
average_force_n = absorbed_energy_j * 1000 / max_compression_mm
```

（`absorbed_energy_j` 单位 J、`max_compression_mm` 单位 mm，结果单位 N。触底时仍按公式计算，但需附 warning。）

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

**简化假设（必须写入 `assumptions` 段）**：当 `x_max` 小于测试卸载曲线起点时，本工具假设“卸载曲线形状只与位移有关”，直接对测试卸载曲线在 `[0, x_max]` 区间积分。物理上更浅压缩深度的真实卸载支路可能更陡或更软，本工具不修正这一差异。

触底情况下（`bottom_out = True`），仍按 `[0, effective_stroke]` 积分给出 `rebound_energy_j`，但需在 warning 中标记“触底回弹仅供参考”。

### Time-domain Reconstruction

由能量守恒反推近似时间历程，零额外动力学假设。本节实现放在 `core/buffer/time_response.py`。

**压缩段**（`x: 0 → x_max`，速度方向为正）：

```text
v_compress(x) = sqrt( max(0, 2 * (E0 - E_load(x)) / mass_kg) )
a_compress(x) = F_loading(x) / mass_kg
t_compress(x) = ∫_0^x  (1e-3 dx') / v_compress(x')      # mm → m
```

**回弹段**（`x: x_max → 0`，速度方向为负）：

```text
E_rebound_at(x) = ∫_x^x_max F_unloading(x') dx'         # 卸载已释放的能量
v_rebound(x)    = -sqrt( max(0, 2 * E_rebound_at(x) / mass_kg) )
a_rebound(x)    = -F_unloading(x) / mass_kg
```

**奇点处理**：

- `x = x_max` 处 `v = 0`，`dt = dx/v` 发散。在最后一段 `[x_max - Δ, x_max]` 改用恒加速度近似 `Δt ≈ sqrt(2 · Δ_m / a(x_max))`，其中 `Δ_m = Δ · 1e-3`。
- 卸载段从 `x_max` 出发同样处理。
- 数值积分采用累计梯形：`Δt_i = (1e-3 · Δx_i) · (1/v_i + 1/v_{i+1}) / 2`，并跳过 `v < ε` 的奇点段（用上述恒加速度近似替代）。

**采样**：

- 压缩段在 `[0, x_max]` 上等距采 `time_samples / 2` 个 `x` 点。
- 回弹段在 `[x_max, 0]` 上等距采 `time_samples / 2` 个 `x` 点。
- 把两段对应的 `t`、`v`、`a`、`F` 拼接成单调递增时间序列。

**输出**：

- `compression_duration_s = t_compress(x_max)`
- `rebound_duration_s = |t_rebound(0)|`（以 `x_max` 时刻为零点）
- `duration_s = compression_duration_s + rebound_duration_s`
- 时间序列字段同 Output Schema。

**异常路径**：

- 触底情况下，仅输出压缩段 `[0, effective_stroke]`，末端 `velocity_m_s` 保留非零值（动能未释放完），`rebound_*` 段置空，warning 中说明“触底后时域响应未建模”。
- 反推过程中若出现 `NaN` / `Inf`（例如 `E0 < E_load(0)` 之类的异常），返回 `time_response = None` 并给 warning。

### Checks

未触底（`bottom_out = False`）：

```text
stroke_ok          = max_compression_mm <= available_stroke_mm
peak_force_ok      = peak_force_n <= allowable_peak_force_n
energy_capacity_ok = True
overall_pass       = stroke_ok and peak_force_ok
```

触底（`bottom_out = True`）：

```text
stroke_ok          = False              # 触底语义上判 False
peak_force_ok      = None               # 不可判定
energy_capacity_ok = False
overall_pass       = False
```

若 `available_stroke_mm` 大于测试曲线最大行程，仍只能用测试曲线最大行程作为有效容量，并给 warning：测试曲线未覆盖全部可用行程。`energy_capacity_ok` 不允许基于未知曲线外推通过。

## UI Result Presentation

### Persistent Disclaimer Banner

结果页顶部常驻一条暖色警示横幅（warning 样式）：

> 本工具基于准静态 F-x 曲线的单次冲击能量法。回弹速度与时域响应均为反推估算值，不含应变率效应，不能替代真实时域仿真。

### Scheme A Workbench Overview

`吸能结果` 章节使用方案 A 的工作台布局，视觉上分为三列：

1. 左侧窄列：显示计算顺序摘要和当前数据状态（曲线文件、点数、格式、warning 数量）。这列复用 `BaseChapterPage` 左侧步骤语义，不再额外创建第二套复杂导航。
2. 中央主列：
   - 顶部四个关键指标卡：初始动能、最大压缩量、峰值输出力、估算回弹速度。
   - 中部 `BufferEnergyCurveWidget`：显示加载/卸载 F-x 滞回、最大压缩点、可用行程线和允许峰值力线。
   - 底部能量条：加载能量、工况耗散能量、接触时长。
3. 右侧 rail：
   - 总体结论卡：通过 / 不通过 / 触底不可判定。
   - 模型边界卡：准静态曲线、应变率缺失、触底峰值未知等说明。
   - 参数对比摘要表：默认展示 `0.8F`、`1.0F`、`1.2F`、`1.2S` 等高信号行，完整 3x3 扫描仍在 `参数对比` 章节。

该工作台需要在一次计算后完成更新，用户不必切换到多个章节才能判断当前缓冲块是否可用。

### Curve Panel

新增 `BufferEnergyCurveWidget`：

- 绘制加载曲线和卸载曲线。
- 标出最大压缩点。
- 标出可用行程线。
- 标出允许峰值力线。
- 显示滞回面积的简化填充。
- 触底时把 `[effective_stroke, available_stroke]` 区段标为红色阴影，提示曲线外推区域。

### Response Curve Panel

新增 `BufferResponseCurveWidget`，展示时域反推结果：

- 多曲线视图：`x(t)`、`v(t)`、`a(t)`、`F(t)`，通过 tab 或下拉切换。
- 标出最大压缩点（`v=0`）和接触结束点。
- 顶部显示 `compression_duration_s` / `rebound_duration_s` / `duration_s`。
- 触底场景下仅显示压缩段，末端用红色虚线标注"触底，速度未归零"。

两个 widget 都使用现有项目风格的 `QPainter` 自绘，避免为单个曲线控件额外扩大 matplotlib 使用面。

### Result Cards

`吸能结果` 工作台包含：

- 总体结论：通过 / 不通过 / 超出曲线容量
- 关键结果值：
  - 初始动能
  - 最大压缩量
  - 峰值输出力（触底时显示「触底，未知」）
  - 平均反力
  - 吸收能量
  - 工况耗散能量（实际工况下 absorbed − rebound）
  - 回弹能量
  - 估算回弹速度
  - 接触时长 `duration_s`
- 分项校核（badge）：
  - 行程校核
  - 峰值力校核（触底时显示「不可判定」灰色）
  - 曲线能量容量校核
- 消息与建议：
  - 若触底：建议增大行程、换更高吸能曲线或降低冲击速度
  - 若峰值力过高：建议更软曲线或增加可用行程
  - 若回弹速度高：建议更高滞回耗能缓冲块
- 右侧 rail 参数对比摘要：只显示少量最重要组合，完整表格在 `参数对比` 章节。

### Parameter Comparison

第一版支持轻量参数对比：

- 力倍率：例如 `0.8, 1.0, 1.2`
- 行程倍率：例如 `0.8, 1.0, 1.2`

结果以表格展示：

- `force_scale`
- `stroke_scale`
- `max_compression_mm`
- `peak_force_n`
- `bottom_out`
- `energy_capacity_ok`
- `stroke_ok`
- `peak_force_ok`
- `estimated_rebound_velocity_m_s`
- `duration_s`

## File Changes

预计实现涉及：

- 新增 `core/buffer/__init__.py`
- 新增 `core/buffer/calculator.py`（能量法主流程 + checks）
- 新增 `core/buffer/curve_import.py`（CSV 解析；XLSX 解析中 `openpyxl` 必须懒加载，仅在 `.xlsx` 路径下 `import`，避免影响应用启动时间）
- 新增 `core/buffer/time_response.py`（能量守恒反推 `x(t)/v(t)/a(t)/F(t)`）
- 新增 `app/ui/pages/buffer_energy_page.py`
- 新增 `app/ui/widgets/buffer_energy_curve.py`（F-x 曲线 + 滞回面积 + 标注）
- 新增 `app/ui/widgets/buffer_response_curve.py`（时域响应曲线 widget）
- 修改 `app/ui/main_window.py` 注册新模块
- 新增 `examples/buffer_energy_case_01.csv`
- 新增 `examples/buffer_energy_case_02.xlsx`
- 新增 `examples/buffer_energy_input_conditions.json`
- 修改 `requirements.txt` 增加 `openpyxl>=3.1`
- 新增 `tests/core/buffer/__init__.py`
- 新增 `tests/core/buffer/test_calculator.py`
- 新增 `tests/core/buffer/test_curve_import.py`
- 新增 `tests/core/buffer/test_time_response.py`
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
- 卸载力局部超过加载力 ≤ `noise_tolerance_n` 给 warning；超过 `5 × noise_tolerance_n` 抛 `InputError`
- 卸载曲线总面积大于加载曲线面积时给 warning；若超出 10% 阻断计算
- 时域反推中若 `compression_duration_s` 不收敛（NaN / Inf），返回 `time_response = None` 并给 warning，不阻断主结果

## Testing Strategy

### Core Tests

- 梯形积分单位换算正确（1 N · 1 mm = 0.001 J）。
- 用简单三角曲线验证加载 / 卸载能量。
- 初始动能小于容量时能插值得到正确压缩量。
- 初始动能超过容量时返回 `bottom_out=True`、`peak_force_n=None`、`peak_force_status="bottom_out_unknown"`、`stroke_ok=False`、`peak_force_ok=None`。
- 可用行程小于曲线最大行程时按可用行程容量判定。
- 卸载能量正确截断到 `x_max`。
- 回弹速度公式正确。
- 峰值力校核和行程校核独立生效。
- 平均反力 `F_avg = absorbed_energy * 1000 / max_compression` 正确。
- 切线刚度极值由相邻点差分得到，跳过 `Δx < 1e-6` 的点对。
- `curve_hysteresis_energy_j` 与 `impact_dissipated_energy_j` 字段语义独立、数值不同。

### Time-response Tests

- 线性弹簧曲线（`F = k·x`）下，`compression_duration_s` 接近解析值 `0.5π · sqrt(m/k_SI)`（容差 5%）。
- 时间历程满足能量守恒：`0.5·m·v(t)² + E_load(x(t)) ≈ E0`（容差 1%）。
- 触底情况下 `time_response.rebound_*` 段为空、warning 包含触底说明。
- `v(t)` 在最大压缩点穿过零、回弹段单调负向。
- `F(t)` 在压缩段与 `F_loading(x(t))` 一致；回弹段与 `F_unloading(x(t))` 一致。

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
- 结果页包含最大压缩、峰值力、吸收能量、回弹速度、接触时长。
- 分项 badge 从待计算更新为通过 / 不通过 / 不可判定。
- 触底场景下 `BufferResponseCurveWidget` 仅显示压缩段且不崩溃。
- 时域曲线 widget 可在 `x` / `v` / `a` / `F` 四种变量间切换。
- 常驻免责横幅可见。
- 导入错误通过 message box 展示，不会让页面崩溃。

## Documentation and Report

结果说明和报告必须包含：

- “本工具基于加载 / 卸载 F-x 曲线的单次冲击能量法。”
- “未使用时间域数据，不能唯一识别真实粘性阻尼系数 c。”
- “回弹速度为基于卸载曲线能量的估算值。”
- “若输入动能超过曲线容量，本工具将 `peak_force_n` 标记为不可判定；触底后的真实冲击峰值显著高于曲线末端力。”
- “时域响应曲线（x(t)/v(t)/a(t)/F(t)）为由能量守恒反推的近似映射，不含应变率效应，不能替代真实时域动力学仿真。”
- “假设水平冲击或重力做功相对动能可忽略；垂直跌落工况需把 `m·g·x_max` 加入 `E0`，本版本暂不自动处理。”
- “卸载段简化假设：测试卸载曲线形状只与位移有关；当工况最大压缩小于测试最大压缩时，仍按测试卸载曲线在 `[0, x_max]` 段积分。”

## Acceptance Criteria

- 用户可以导入 CSV 或 XLSX 的加载 / 卸载曲线。
- 用户可以输入质量和初速度并执行单次冲击仿真。
- 结果能明确回答：
  - 缓冲块是否有足够能量容量
  - 是否触底（`bottom_out`）、是否超过可用行程
  - 峰值输出力是多少（触底时明确标记为不可判定）
  - 平均反力是多少
  - 吸收 / 工况耗散 / 回弹能量分别是多少
  - 估算回弹速度是多少
  - 接触时长是多少
- 结果页能展示由能量守恒反推的近似时域响应曲线 `x(t)`、`v(t)`、`a(t)`、`F(t)`，并附常驻免责声明。
- UI 不要求用户输入 `k` 或 `c`。
- 所有核心计算（含时域反推）有单元测试覆盖。
- 页面与现有 `BaseChapterPage` 模块风格一致。
- `openpyxl` 仅在用户实际打开 `.xlsx` 时才被 import，不影响应用启动时间。
