# 蜗杆模块增强设计规格

**日期**: 2026-04-03
**范围**: core/worm/calculator.py, app/ui/pages/worm_gear_page.py, 新增 widget

## 1. Method A/B/C 说明文案

### 需求
在校核方法下拉选项中增加 DIN 3996 三种方法的简要说明，帮助用户理解当前选择。

### 设计
修改 `worm_gear_page.py` 中 `LOAD_CAPACITY_OPTIONS` 的选项文案：

- `"DIN 3996 Method A — 基于实验/FEM，精度最高"`
- `"DIN 3996 Method B — 标准解析计算（推荐）"`
- `"DIN 3996 Method C — 简化估算"`

calculator 端 `method` 字段原样透传存储，不影响计算逻辑（当前版本三种方法计算逻辑相同，仅作标记）。

## 2. Load Capacity 默认启用

### 需求
Load Capacity 功能默认开启，不需要用户手动切换。

### 设计
- UI 侧：`BASIC_SETTINGS_FIELDS` 中 `load_capacity.enabled` 的 `default` 保持 `"启用"`（当前已是）
- Calculator 侧：`_build_payload` 中确保 `enabled` 字段正确传递为布尔值 `True`
- 确认 `_on_lc_enabled_changed` 在初始化时正确触发，Load Capacity 参数面板可见

## 3. 输入从功率 kW 改为扭矩 Nm

### 需求
工况输入从功率 (kW) 改为蜗杆输入扭矩 (Nm)，更符合工程习惯。

### UI 变更
`OPERATING_FIELDS` 中：
- 删除 `FieldSpec("operating.power_kw", "输入功率 P", "kW", ...)`
- 新增 `FieldSpec("operating.input_torque_nm", "输入扭矩 T1", "Nm", "蜗杆轴输入扭矩。", default="20.0")`
- 保留 `operating.speed_rpm`

### Calculator 变更
`calculate_worm_geometry()` 中：
- 输入改为读取 `operating.input_torque_nm`
- 功率反算：`power_kw = input_torque_nm * speed_rpm / 9550.0`
- 所有下游使用 `power_kw` 的地方保持不变（变量名可保留，值来源改为反算）
- `performance` 输出中增加 `input_torque_nm` 字段（已有），`input_power_kw` 改为反算值
- 性能曲线的 load_factor 仍基于扭矩缩放

### 示例 JSON 更新
`worm_case_01.json` / `worm_case_02.json` 中 `operating.power_kw` → `operating.input_torque_nm`，数值换算。

## 4. 啮合应力波动曲线（详细方案）

### 需求
在一个蜗杆旋转周期内，展示齿面接触应力和齿根弯曲应力随蜗杆转角的变化曲线。波动来源于啮合几何——接触点沿齿高方向移动导致等效曲率半径和力臂变化。

### 物理模型

#### 啮合周期
- 蜗杆每转一圈产生 z1 个啮合周期
- 单个啮合周期对应蜗杆转角 Δθ = 2π/z1
- 在每个周期内，啮合相位 φ 从 0（齿顶进入）→ 0.5（分度圆）→ 1.0（齿根退出）

#### 接触位置参数化
以啮合相位 φ ∈ [0, 1] 参数化接触点沿齿高方向的位置：

- 接触点距蜗杆轴心的距离：
  `r1(φ) = r_root1 + (r_tip1 - r_root1) × (1 - |2φ - 1|)`
  即从齿根 → 齿顶 → 齿根的对称运动

- 蜗杆侧接触曲率半径：
  `ρ1(φ) = r1(φ) × sin(γ)` （γ = 导程角）

- 蜗轮侧接触曲率半径：
  蜗轮为凹面包络，曲率半径近似：
  `ρ2(φ) = a - r1(φ)` （a = 中心距）
  等效曲率半径：`ρ_eq(φ) = ρ1(φ) × ρ2(φ) / (ρ2(φ) - ρ1(φ))`
  （凹-凸接触，取差值）

#### 齿面接触应力
在每个相位点，用 Hertz 线接触公式：
```
σ_H(φ) = sqrt( F_n × E_eq / (π × L_c × ρ_eq(φ)) )
```
其中：
- F_n = 法向设计力（含载荷系数）
- E_eq = 等效弹性模量
- L_c = 接触长度（取 min(b1, b2)，简化为常数）
- ρ_eq(φ) = 随相位变化的等效曲率半径

#### 齿根弯曲应力
力臂随接触位置变化：
```
h(φ) = r1(φ) - r_root1
σ_F(φ) = F_t × h(φ) / W_section
```
其中：
- F_t = 切向设计力
- h(φ) = 接触点到齿根的径向距离
- W_section = 齿根截面模量（常数）

#### 完整旋转曲线
将单个啮合周期的应力曲线沿 θ 方向重复 z1 次，覆盖 0 ~ 360°。

### Calculator 输出
在 `load_capacity` 结果中新增 `stress_curve` 字段：
```python
"stress_curve": {
    "theta_deg": [...],          # 蜗杆转角, 0~360, ~360个点
    "sigma_h_mpa": [...],        # 齿面接触应力
    "sigma_f_mpa": [...],        # 齿根弯曲应力
    "sigma_h_nominal_mpa": ...,  # 名义接触应力（分度圆处）
    "sigma_f_nominal_mpa": ...,  # 名义齿根应力（分度圆处）
    "sigma_h_peak_mpa": ...,     # 峰值接触应力
    "sigma_f_peak_mpa": ...,     # 峰值齿根应力
    "mesh_frequency_per_rev": z1,
}
```

### 新增 Widget
`app/ui/widgets/worm_stress_curve.py`:
- 使用 matplotlib 嵌入 PySide6（`FigureCanvasQTAgg`）
- 双 Y 轴：左轴齿面接触应力（MPa），右轴齿根弯曲应力（MPa）
- X 轴：蜗杆转角 0~360°
- 标注名义值（水平虚线）和峰值点
- 颜色与项目主题一致（primary `#D97757`）

### UI 集成
在"图表总览"章节中新增一个应力波动曲线图，位于现有性能曲线下方。仅当 Load Capacity 启用时显示。

## 5. LaTeX 公式渲染

### 需求
工具内所有显示公式的地方渲染为 LaTeX，后续所有模块统一执行。

### 依赖
`requirements.txt` 新增 `matplotlib`。

### 新增模块
`app/ui/widgets/latex_label.py`:

```python
class LatexLabel(QLabel):
    """使用 matplotlib.mathtext 渲染 LaTeX 公式为 QPixmap 的 QLabel。"""

    def set_latex(self, latex: str, fontsize: int = 14, dpi: int = 120) -> None:
        """渲染 LaTeX 字符串并设置为 label 的 pixmap。"""
        ...
```

实现要点：
- 使用 `matplotlib.mathtext.MathTextParser("bitmap")` 渲染
- 支持设置字号、DPI、前景色/背景色
- 背景透明，适配项目主题色
- 缓存已渲染的公式（避免重复渲染）

### 应用场景（本次）
- 蜗杆模块结果区域：Hertz 接触应力公式、齿根弯曲应力公式
- 应力曲线图标题/图例中的公式符号
- 后续其他模块复用 LatexLabel 控件

### 应用范围（后续）
所有模块中出现工程公式的地方统一使用 LatexLabel 渲染。本次先在蜗杆模块落地，建立模式。

## 6. AutoCalcCard 蓝色底一致性

### 需求
所有自动计算/不可编辑的字段使用 AutoCalcCard 样式（蓝灰底 `#EDF1F5`），与手动输入的 SubCard 区分。

### 蜗杆模块需要标蓝的字段
- 蜗杆自动计算尺寸区域（分度圆直径、齿顶/齿根圆直径、导程、轴向齿距、圆周速度）
- 蜗轮自动计算尺寸区域（同上）
- 导程角字段（当 z1/q 确定后可推导，但当前允许手动输入用于比较，暂保持可编辑）

### 实现
- 自动计算尺寸区域的 dimension group card 使用 `setObjectName("AutoCalcCard")`
- 确保 QLabel 显示值的文字颜色为 `#3A4F63`

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `core/worm/calculator.py` | 修改 | 输入改扭矩、应力曲线计算、输出结构 |
| `app/ui/pages/worm_gear_page.py` | 修改 | FieldSpec、Method说明、默认值、曲线集成 |
| `app/ui/widgets/latex_label.py` | 新增 | LaTeX 公式渲染控件 |
| `app/ui/widgets/worm_stress_curve.py` | 新增 | 啮合应力波动曲线 widget |
| `requirements.txt` | 修改 | 新增 matplotlib |
| `examples/worm_case_*.json` | 修改 | power_kw → input_torque_nm |
| `tests/core/worm/test_calculator.py` | 修改 | 适配新输入/输出结构 |
| `tests/ui/test_worm_page.py` | 修改 | 适配新字段 |
