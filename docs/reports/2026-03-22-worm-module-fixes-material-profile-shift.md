# Worm Module Comprehensive Fix Report

**Date:** 2026-03-22
**Branch:** `feat/worm-module-fixes` (merged to `main`)
**Commits:** 7 (`8db0fbc` ~ `ede3ec9`)
**Total Lines:** 2247 lines across 7 files

---

## 1. Objectives

对蜗杆模块（DIN 3975）进行全面代码审查后发现 21 个问题，覆盖计算逻辑、UI 联动、输入验证和文档假设。同时根据用户实际工况需求：引入变位系数 x1/x2（塑料蜗轮需要大变位）、将材料从青铜配对替换为钢-塑料配对（37CrS4 / PA66 / PA66+GF30）。

上一次蜗杆报告（worm-load-capacity-merge）中的风险项"当前蜗杆实现仍是最小工程子集"依然成立但已补充了完整的 assumptions 列表。

## 2. Deliverables

### 2.1 Core Calculator

| File | Lines | Description |
|------|-------|-------------|
| `core/worm/calculator.py` | 478 | 材料表替换、变位系数 x1/x2、d2=z2*m 标准定义、热容量=损失功率、导程角自洽 atan(z1/q)、enabled 守卫、整数/范围校验、8 条 assumptions |

### 2.2 UI Page

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/pages/worm_gear_page.py` | 846 | 材料下拉更新、_on_material_changed 联动 E/nu/许用应力/摩擦 placeholder、x1/x2 字段、LC 启用/关闭控制、enabled:false 加载修复、导出报告按钮、method hint 标注 |
| `app/ui/widgets/worm_performance_curve.py` | 126 | 热功率标签改为"损失功率 (热负荷)" |
| `app/ui/widgets/worm_tolerance_overview.py` | - | 已删除（公差页面移除） |

### 2.3 Tests

| File | Lines | Tests |
|------|-------|-------|
| `tests/core/worm/test_calculator.py` | 452 | 29 tests: 变位系数几何、材料表、d2 标准定义、热容量、导程角自洽、enabled stub、整数/范围校验、assumptions |
| `tests/ui/test_worm_page.py` | 249 | 23 tests: 材料联动、LC 显隐、enabled:false 加载、导出报告、章节计数 |

### 2.4 Example Data

| File | Lines | Description |
|------|-------|-------------|
| `examples/worm_case_01.json` | 48 | 37CrS4/PA66，x1=0, x2=0，标准案例 |
| `examples/worm_case_02.json` | 48 | 37CrS4/PA66+GF30，x1=0.2, x2=0.8，大变位案例 |

## 3. Commit History

| Commit | Message |
|--------|---------|
| `8db0fbc` | feat(worm): replace materials with 37CrS4/PA66, add profile shift x1/x2, fix d2 derivation |
| `7a7e8a2` | fix(worm): thermal=loss, lead angle uses atan(z1/q), enabled flag guards LC |
| `4dfeb41` | fix(worm): add integer/range validation, update assumptions for ZK/plastic |
| `4edde52` | feat(worm): material linkage, profile shift fields, dropdown update to 37CrS4/PA66 |
| `ab53016` | fix(worm): LC enable/disable toggle, enabled:false load fix, method hint update |
| `c5ef193` | feat(worm): connect export report button, relabel thermal curve to loss power |
| `ede3ec9` | chore(worm): update example JSON for 37CrS4/PA66 materials and profile shift |

## 4. Key Technical Decisions

1. **d2 = z2 * m（标准分度圆）替代 d2 = 2a - d1（中心距反推）**：引入变位系数后，蜗轮分度圆直径应保持标准定义，中心距偏差仅用于一致性校验。力/应力计算基于参考圆。

2. **导程角：下游使用 atan(z1/q) 推导值，用户输入仅作对比**：避免用户输入不自洽的导程角传播到效率和力的计算中。输出中 `lead_angle_deg` 保持为推导值（向后兼容），新增 `lead_angle_input_deg` 保留用户原始输入。

3. **齿高公式 h = m*(2.2 + x1 - x2)**：代表蜗杆齿顶深入蜗轮齿根的深度（蜗杆 addendum + 蜗轮 dedendum），用于悬臂梁齿根应力的弯矩臂。

4. **材料联动信号时序**：`_on_material_changed()` 在 `_apply_defaults()` 之后连接，`_apply_input_data()` 中 blockSignals 防止加载保存数据时触发级联更新。

5. **LC enabled 守卫前置**：当 `enabled=False` 时在读取 LC 参数字段之前提前返回 stub，使得禁用模式不要求这些字段存在。

6. **公差页面直接移除**：而非保留为"仅记录项"。公差计算尚未实现，保留空壳反而误导用户。

## 5. Known Limitations

1. 等效曲率半径仍基于分度圆简化，未考虑蜗轮凹面修正
2. 接触长度取 min(b1, b2)，未考虑包角影响
3. 齿根应力为等效悬臂梁近似，无 DIN 3996 标准系数 (Y_F, Y_S, Y_epsilon)
4. 三个校核方法选项（DIN 3996 / ISO 14521 / Niemann）计算逻辑相同，仅作标记
5. 许用应力默认值为常温干态经验值，PA66 在高温/吸湿条件下需大幅降额
6. 摩擦系数经验值范围 0.01-0.30，塑料蜗轮实际摩擦可能受速度/温度/润滑剂显著影响
7. tooth_root_thickness_mm 未随变位系数调整（保持 1.25m）

## 6. Reflection

### What went well
- Brainstorming → Design Spec → Plan → Subagent Execution 的完整流程高效：spec 经过 2 轮 review、plan 经过 1 轮 review，实现阶段 8 个 Task 无一阻塞
- 每个 Task 都有 spec compliance review，确保实现不偏离设计
- Task 粒度合理（calculator 3 个 + UI 4 个 + data 1 个），每个 Task 独立可测试
- 全量 249 测试始终保持绿色，无回归

### What could be improved
- Task-by-task 执行的中间态存在不一致（Task 1 改了 calculator 材料，但 UI 到 Task 5 才更新下拉框），如果用户在中间运行应用会看到错误的回退值。可以考虑把材料相关改动合并为一个跨 calculator/UI 的 Task
- Code quality review 只在 Task 1 做了完整版，Task 2-7 跳过了以节省时间。对于关键模块应该坚持每个 Task 都做

### Recurring Issues
- 上一份报告提到"如果 feature 最终一定要回到 main，可以更早安排合并窗口"——本次使用了 feature branch + fast-forward merge 模式，执行顺畅，该问题未复现

## 7. Next Steps

| Phase/Item | Scope |
|------------|-------|
| DIN 3996 完整实现 | 标准系数 (Y_F, Y_S, K_v, K_Hbeta 等) 替代当前近似公式 |
| 温度/吸湿修正 | PA66 许用应力需根据实际温度和含水率降额 |
| 蜗杆副效率曲线精细化 | 基于实测摩擦数据替代经验公式 |
| 输入条件持久化 | 蜗杆模块接入 input_condition_store 的保存/加载功能 |
| 矩形花键模块 | spline 模块 memory 中标记为 missing |
