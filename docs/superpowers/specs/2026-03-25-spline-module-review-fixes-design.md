# 花键配合模块 Review 修复设计

**日期**: 2026-03-25
**范围**: core/spline/, app/ui/pages/spline_fit_page.py, tests/
**方案**: 单分支顺序执行（方案 A）

## 背景

对花键配合模块进行全面 review 后，发现以下四类问题：
1. d_m 平均直径公式与 h_w 有效齿高定义不一致（计算正确性）
2. UI 文字对新手不友好（7 处 hint/标注需改进）
3. 异常处理过宽、PDF 降级无提示（代码健壮性）
4. 边界条件测试缺失（测试覆盖）

## 修改清单

### Step 1: d_m 公式修复

**文件**: `core/spline/geometry.py`

**当前** (L91):
```python
d_m = (d_a1 + d_f1) / 2.0
```

**修正为**:
```python
d_m = (d_a1 + d_a2) / 2.0
```

**依据**: h_w = (d_a1 - d_a2)/2 定义的是 d_a1 到 d_a2 之间的接触带，d_m 作为力臂应取同一区间中心。Niemann/Winter 卷 I 承压公式 p = 2T*K_alpha / (z*h_w*d_m*L) 中 h_w 和 d_m 是配套量。

**受影响测试值**:

| 用例 | 旧 d_m | 新 d_m |
|------|--------|--------|
| m=2, z=20 近似 | 39.75 | 40.0 |
| W15x1.25x10 显式 | 13.425 | 13.625 |

**需同步更新的测试**:
- `tests/core/spline/test_geometry.py` — mean_diameter_mm 断言值
- `tests/core/spline/test_calculator.py` — `test_flank_pressure_formula` 和 `test_torque_capacity_formula` 中的 d_m 常量

### Step 2: UI 文字改进（新手友好性）

**文件**: `app/ui/pages/spline_fit_page.py`

共 7 处修改：

1. **校核模式 hint** (L98): 增加场景 A/B 释义
   - 改为: "仅花键：只校核花键齿面承压（场景 A）；联合：同时校核花键轴光滑段与轮毂孔的圆柱过盈配合（场景 B）。"

2. **K_alpha hint** (L185): 去掉 Niemann 术语，给出工程范围
   - 改为: "齿面载荷分布不均匀的修正系数。过盈固定连接约 1.0~1.3，滑移连接约 1.5~2.0。"

3. **KA hint** (L123): 补充物理含义和典型值
   - 改为: "考虑驱动/负载特性引起的动态过载，同时放大场景 A 和 B 的设计载荷。电机驱动约 1.0~1.25，内燃机约 1.25~1.75。"

4. **参考直径 hint** (L155): 解释花键标记法
   - 改为: "DIN 5480 花键的基本尺寸参考直径。例如 '外花键 W 15x1.25x10' 表示 d_B=15mm, m=1.25, z=10。"

5. **退刀槽 hint** (L234): 解释退刀槽物理含义
   - 改为: "花键齿根与光滑段之间的让刀凹槽宽度，用于加工退刀。计算时自动从配合长度中扣除。"

6. **SPLINE_SCOPE_DISCLAIMER** (L72): 解释 DIN 标准编号含义
   - 改为: "当前仅提供齿面平均承压的简化预校核，不替代 DIN 5480（渐开线花键尺寸标准）/ DIN 6892（花键连接承载能力标准）的完整工程校核。"

7. **结果页 verdict_level** (L590): 英文 `simplified_precheck` 映射为中文 "简化预校核"

### Step 3: 代码健壮性

**文件**: `app/ui/pages/spline_fit_page.py`

1. **异常处理分离** (L560-567): 将 `except (InputError, Exception)` 拆为两个独立的 except 块：
   - `InputError` → "输入错误: ..."
   - `Exception` → "内部错误: ... 请检查输入或联系开发者"

2. **PDF 降级提示** (L641-646): PDF 生成失败时，在 set_info 中明确告知用户 PDF 失败原因和已回退为 .txt 格式。

### Step 4: 补充边界测试

**文件**: `tests/core/spline/test_geometry.py`, `tests/core/spline/test_calculator.py`

新增 6 个测试用例：

| 测试名 | 文件 | 验证内容 |
|--------|------|----------|
| test_partial_explicit_geometry_raises | test_geometry.py | 只提供部分显式尺寸 -> GeometryError |
| test_pressure_angle_out_of_range_raises | test_geometry.py | pressure_angle=60 -> GeometryError |
| test_invalid_geometry_mode_raises | test_calculator.py | geometry_mode="invalid" -> InputError |
| test_negative_relief_groove_raises | test_calculator.py | relief_groove < 0 -> InputError |
| test_relief_groove_exceeds_length_raises | test_calculator.py | relief_groove >= fit_length -> InputError |
| test_zero_torque_gives_infinite_safety | test_calculator.py | torque=0 -> flank_sf = inf |

## 执行顺序

Step 1 → Step 2 → Step 3 → Step 4，每步完成后运行全量测试确认无回归，每步一次 commit。

## 不在此次范围内

- 材料库扩充（低优先级，后续单独处理）
- pressure_angle_deg 参与计算（需要更复杂的齿形模型）
- 输入条件持久化（已知 backlog）
- 报告导出增强
