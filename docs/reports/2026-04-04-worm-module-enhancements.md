# 蜗杆模块增强 — 工作报告

**日期**: 2026-04-04
**设计文档**: `docs/superpowers/specs/2026-04-03-worm-module-enhancements-design.md`
**实现计划**: `docs/superpowers/plans/2026-04-03-worm-module-enhancements.md`

---

## 概述

本次对蜗杆模块（DIN 3975 / DIN 3996 Method B 最小子集）进行了 6 项功能增强，涉及计算逻辑、UI 交互、公式渲染和视觉一致性。

## 完成项

### 1. Method A/B/C 说明

校核方法下拉选项增加 DIN 3996 三种方法的中文说明：

| 选项 | 说明 |
|------|------|
| DIN 3996 Method A | 基于实验/FEM，精度最高 |
| DIN 3996 Method B | 标准解析计算（推荐） |
| DIN 3996 Method C | 简化估算 |

当前版本三种方法计算逻辑相同，仅作标记用途。默认选中 Method B。

### 2. Load Capacity 默认启用

- UI 默认选"启用"（原已设置，本次确认 calculator 端正确传递 `enabled=True`）
- 校核徽章逻辑完善：几何一致性纳入总体判定，LC 未启用时显示"未启用"而非零值

### 3. 输入从功率改为扭矩

- 工况输入字段从 `power_kw`（kW）改为 `input_torque_nm`（Nm）
- Calculator 内部反算功率：$P = T_1 \times n / 9550$
- 结果区新增"输入功率 P1（反算）"显示
- 所有下游计算（效率、损失功率、性能曲线）保持不变
- 示例 JSON 已换算更新（Case 1: 19.76 Nm, Case 2: 54.74 Nm）

### 4. 啮合应力波动曲线

基于啮合几何的详细建模，计算一个蜗杆旋转周期内齿面接触应力和齿根弯曲应力的变化。

**物理模型要点：**
- 蜗杆每转一圈产生 z1 个啮合周期
- 接触点沿齿高方向移动（齿根 → 齿顶 → 齿根），三角形轮廓参数化
- 蜗杆侧曲率半径：$\rho_1(\varphi) = r_1(\varphi) \cdot \sin\gamma$
- 蜗轮侧曲率半径（凹面包络）：$\rho_2(\varphi) = a - r_1(\varphi)$
- 凸-凹接触等效曲率半径：$\rho_{eq} = \frac{\rho_1 \cdot \rho_2}{\rho_2 - \rho_1}$
- Hertz 接触应力：$\sigma_H = \sqrt{\frac{F_n \cdot E^*}{\pi \cdot L_c \cdot \rho_{eq}}}$
- 齿根弯曲应力：$\sigma_F = \frac{F_t \cdot h}{W_{section}}$

**输出：** 360 个采样点的 theta/sigma_H/sigma_F 数组，加名义值和峰值标量。

**UI Widget：** `WormStressCurveWidget` 使用 matplotlib 嵌入 PySide6，双 Y 轴显示（左轴橙色齿面应力，右轴蓝色齿根应力），带名义值虚线标注。

### 5. LaTeX 公式渲染

新建 `LatexLabel` 通用控件：
- 使用 `matplotlib` Agg 后端将 LaTeX 字符串渲染为 QPixmap
- 类级别缓存，避免重复渲染
- 支持自定义字号、DPI、颜色
- 背景透明，适配项目暖色调主题

本次在蜗杆 Load Capacity 步骤中集成了 Hertz 接触应力和齿根弯曲应力两个公式的渲染。后续其他模块可复用此控件。

### 6. AutoCalcCard 蓝色底一致性

蜗杆/蜗轮自动计算尺寸区域统一使用 `AutoCalcCard` 样式：
- 背景色 `#EDF1F5`（蓝灰）
- 数值文字颜色 `#3A4F63`，加粗
- 与手动输入的 `SubCard`（暖色 `#F6F1EA`）明确区分

## 新增依赖

| 包 | 版本 | 用途 |
|----|------|------|
| matplotlib | >=3.8.0 | LaTeX 公式渲染 + 应力曲线绘图 |

## 文件变更

| 文件 | 动作 | 行数变化 |
|------|------|----------|
| `core/worm/calculator.py` | 修改 | +103/-7 |
| `app/ui/pages/worm_gear_page.py` | 修改 | +195/-37 |
| `app/ui/widgets/latex_label.py` | 新建 | +81 |
| `app/ui/widgets/worm_stress_curve.py` | 新建 | +98 |
| `tests/core/worm/test_calculator.py` | 修改 | +151/-17 |
| `tests/ui/test_worm_page.py` | 修改 | +285/-7 |
| `tests/ui/test_latex_label.py` | 新建 | +49 |
| `tests/ui/test_worm_stress_curve.py` | 新建 | +44 |
| `examples/worm_case_01.json` | 修改 | +1/-1 |
| `examples/worm_case_02.json` | 修改 | +1/-1 |
| `requirements.txt` | 修改 | +1 |

## 测试结果

蜗杆模块相关测试：**73 通过 / 0 失败**

| 测试文件 | 测试数 | 状态 |
|----------|--------|------|
| `tests/core/worm/test_calculator.py` | 38 | 全部通过 |
| `tests/ui/test_worm_page.py` | 29 | 全部通过 |
| `tests/ui/test_worm_stress_curve.py` | 2 | 全部通过 |
| `tests/ui/test_latex_label.py` | 4 | 全部通过 |

全量测试套件 349 通过，8 个既有失败来自 spline 和 bolt_tapped_axial 模块（与本次改动无关）。

## 提交历史

| Commit | 说明 |
|--------|------|
| `bb53baa` | chore: add matplotlib dependency |
| `62645cb` | feat(worm): change operating input from power (kW) to torque (Nm) |
| `57f882e` | feat: add LatexLabel widget for formula rendering via matplotlib |
| `77c0b72` | feat(worm): add WormStressCurveWidget with dual-axis matplotlib plot |
| `150f57a` | feat(worm): add mesh stress variation curve over one worm revolution |
| `832e323` | feat(worm): update UI with Method A/B/C, torque input, stress curve, LaTeX, AutoCalcCard |

## 已知限制

1. **CJK 字体警告**: matplotlib 默认字体 DejaVu Sans 不含中文字形，曲线图中的中文标签会回退到系统字体。功能不受影响，但控制台有 UserWarning。后续可配置 matplotlib 使用系统中文字体消除警告。
2. **应力曲线物理精度**: 接触位置参数化采用三角形轮廓简化（齿根→齿顶→齿根对称运动），未考虑渐开线齿形的非线性接触轨迹。这与 Method B 最小子集的定位一致——工程估算级别。
3. **LaTeX 渲染性能**: 首次渲染公式需约 100ms（matplotlib 初始化），后续使用缓存。对桌面应用可接受。

## 后续工作

- [ ] 其他模块（螺栓、过盈配合、赫兹）统一接入 LatexLabel 渲染公式
- [ ] matplotlib 中文字体配置（消除 CJK 警告）
- [ ] DIN 3996 完整 Method B 实现（目前仍为最小子集）
