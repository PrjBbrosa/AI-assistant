# 过盈配合模块 DIN 7190 核心增强设计

## 0. 状态更新（2026-03-19）

本文件保留 2026-03-08 这一轮“核心增强设计”的原始决策背景，但其中部分范围说明已经落后于当前实现。

截至 2026-03-19，当前仓库已经额外实现：

- ISO 286 受限子集优选配合与偏差换算
- `manual_only / shrink_fit / force_fit` 装配流程
- Step 5 `fretting` 风险评估（风险等级与建议，不并入基础 verdict）
- 输入来源追溯与报告展示

截至 2026-03-19，当前仓库仍未纳入主模型：

- 离心力 / 转速耦合
- 服役温度耦合
- 阶梯轴 / 阶梯轮毂
- 更完整的 ISO 286 公差库

阅读建议：

- 若要了解当前实现边界，以代码、测试和以下文档为准：
  - `docs/review/2026-03-18-interference-fit-deep-review.md`
  - `docs/references/2026-03-19-interference-public-benchmark-notes.md`
  - `docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md`
- 下文第 1~8 节可视为当时的设计快照，而不是当前功能清单。

## 1. 目标

- 在现有圆柱面过盈配合模块基础上，补齐本轮需要的 `DIN 7190` 核心能力。
- 优化文档、输入项、结果组织和消息提示，使模块表达与附件第 14 章保持一致的工程语义。
- 保持实现边界清晰：本轮只覆盖核心圆柱面校核，不扩展到阶梯轮毂、离心力、配合公差搜索和热装温差计算。

## 2. 本轮范围

### 2.1 纳入范围

- 工况系数 `KA`
- 需求载荷设计值换算
- 径向力 `Fr` 与弯矩 `Mb` 的附加接触压强
- 张口缝避免校核 `p_min >= p_r + p_b`
- 最小/平均/最大过盈三组结果
- 服役摩擦系数拆分：
  - `mu_torque`
  - `mu_axial`
- 粗糙度压平修正继续保留
- 页面章节、结果区、导出报告文案重写
- 旧输入 `mu_static` 兼容迁移

### 2.2 不纳入范围

- 阶梯轮毂/阶梯轴
- 离心力与转速影响
- ISO 286 公差带搜索与配合推荐
- 热装温差、装拆温度计算
- 微动腐蚀/反复载荷专用校核
- 更复杂的弹塑性修正

## 3. 删除与替换

### 3.1 删除的 UI 字段

- `process.assembly_method`
- `process.temp_delta_c`

删除原因：这两个字段在现有实现中仅做记录，不参与计算。本轮不实现热装章节，继续保留会造成能力误导。

### 3.2 降级或移除的结果项

- `combined_ok` 不再作为主校核项
- 现有 `pressure_ok` 不再单独作为 badge 展示，合并进需求过盈与张口缝相关结论

### 3.3 保留兼容

- 旧输入文件中的 `friction.mu_static` 继续兼容
- 若未提供 `mu_torque` / `mu_axial`，则默认：
  - `mu_torque = mu_static`
  - `mu_axial = mu_static`

## 4. 输入模型

### 4.1 校核目标

- `checks.slip_safety_min`
- `checks.stress_safety_min`
- `loads.application_factor_ka`
- `options.curve_points`

### 4.2 几何与过盈

- `geometry.shaft_d_mm`
- `geometry.hub_outer_d_mm`
- `geometry.fit_length_mm`
- `fit.delta_min_um`
- `fit.delta_max_um`

### 4.3 材料参数

- `materials.shaft_e_mpa`
- `materials.shaft_nu`
- `materials.shaft_yield_mpa`
- `materials.hub_e_mpa`
- `materials.hub_nu`
- `materials.hub_yield_mpa`

### 4.4 载荷与附加载荷

- `loads.torque_required_nm`
- `loads.axial_force_required_n`
- `loads.radial_force_required_n`
- `loads.bending_moment_required_nm`

### 4.5 摩擦与粗糙度

- `friction.mu_torque`
- `friction.mu_axial`
- `friction.mu_assembly`
- `roughness.shaft_rz_um`
- `roughness.hub_rz_um`
- `roughness.smoothing_factor`

## 5. 计算模型

### 5.1 基本假设

- 实心轴 + 厚壁轮毂
- 线弹性
- 接触压力沿圆周均匀
- 摩擦系数为常数
- 粗糙度压平采用有效过盈修正
- 不考虑离心力、温度场和阶梯几何引起的附加柔度变化

### 5.2 设计载荷

- `T_d = KA * T_req`
- `F_a,d = KA * F_a,req`
- `F_r,d = KA * F_r,req`
- `M_b,d = KA * M_b,req`

### 5.3 粗糙度压平

- `s = k * (Rz_s + Rz_h)`
- `delta_eff = max(0, delta - s)`

### 5.4 三组过盈结果

- `delta_min`
- `delta_mean = (delta_min + delta_max) / 2`
- `delta_max`

对三组输入过盈分别计算：

- `delta_eff`
- `p`
- `T_cap`
- `F_ax_cap`
- `F_press`
- 应力与安全系数

### 5.5 附加载荷与张口缝

- `p_r = F_r,d / (d * L)`
- `p_b` 采用附件第 14 章对应弯矩附加压强的保守简化

由于附件抽取文本中 `QW` 未给出明确上下文定义，本轮按保守处理等效取 `QW = 0`，即不引入可能导致结果偏乐观的修正。

- `p_gap = p_r + p_b`
- 张口缝避免条件：`p_min >= p_gap`

### 5.6 需求最小过盈

先由传递需求反算所需压力：

- `p_req_torque`
- `p_req_axial`
- `p_req_transmission = max(p_req_torque, p_req_axial)`

再与张口缝需求比较：

- `p_required = max(p_req_transmission, p_gap)`

最后反算：

- `delta_required_eff`
- `delta_required`

### 5.7 应力

继续沿用当前圆柱面厚壁轮毂近似模型，输出：

- `shaft_vm`
- `hub_vm`
- `hub_hoop_inner`

本轮不重写应力理论，只重组结果表达方式。

## 6. 结果模型

### 6.1 主校核项

- `torque_ok`
- `axial_ok`
- `gaping_ok`
- `fit_range_ok`
- `shaft_stress_ok`
- `hub_stress_ok`

### 6.2 关键结果

- 最小/平均/最大过盈
- 最小/平均/最大接触压力
- 最小/平均/最大扭矩能力
- 最小/平均/最大轴向能力
- 最小/平均/最大压入力
- `p_r`
- `p_b`
- `p_gap`
- `delta_required`

### 6.3 消息策略

- 当 `gaping_ok = False` 时，优先提示张口缝风险
- 当 `fit_range_ok = False` 时，提示最大过盈不足以覆盖需求
- 当轮毂应力更危险时，提示优先调整轮毂外径或材料
- 明确说明本轮未实现的高级能力，避免误导

## 7. UI 设计

### 7.1 章节结构

1. 校核目标
2. 几何与过盈
3. 材料参数
4. 载荷与附加载荷
5. 摩擦与粗糙度
6. 压入力曲线图
7. 校核结果与消息

### 7.2 结果区调整

- badge 区显示新的主校核项
- 关键结果区改为最小/平均/最大三组结果
- 增加附加载荷说明：
  - `p_r`
  - `p_b`
  - `p_gap`
- 导出报告与页面结果保持一致

## 8. 测试策略

### 8.1 核心单测

- `KA` 增大时，`delta_required` 增大
- `Fr` / `Mb` 可生成 `p_r` / `p_b`
- 张口缝条件不满足时，`gaping_ok = False`
- 旧 `mu_static` 输入仍兼容
- 最小/平均/最大结果单调合理
- 非法几何与粗糙度边界继续报错

### 8.2 UI 验证

- 页面可正常加载升级后的样例
- 删除字段不会残留在界面
- 结果与导出报告一致

## 9. 参考依据

- 附件 `eAssistantHandb_en - fit.pdf` 第 14 章
- `DIN 7190` 核心流程
- 现有项目文档 `docs/references/2026-03-05-interference-roughness-sources.md`
