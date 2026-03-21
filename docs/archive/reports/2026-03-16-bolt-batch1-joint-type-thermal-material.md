# Batch 1: 连接形式接入计算 + 热膨胀材料参数暴露 — 完成报告

**Date:** 2026-03-16
**Branch:** `main`
**Commits:** 12 (`8e9cf0e` ~ `a9e6e59`)
**Total Lines Changed:** ~995 insertions, ~261 deletions across 7 files
**Test Count:** 28 bolt calculator tests (从 0 → 28)，全套 64 tests PASS

---

## 1. Objectives

修复螺栓模块 VDI 2230 审查发现的 P0 级问题（R3 残余夹紧力形同虚设、phi_n 无硬阻断），同时将 P1 级支承面压强校核（R7）和热膨胀材料参数暴露纳入实现。使 `joint_type`（螺纹孔/通孔）实际影响 R7 输出说明，热膨胀系数从硬编码钢升级为用户可选材料预设。

## 2. Deliverables

### 2.1 Calculator Core (`core/bolt/calculator.py`)

| 改动 | 行数 | 描述 |
|------|------|------|
| phi_n 硬阻断 | +8 | `phi_n >= 1.0` 时抛出 `InputError`，替代原先仅警告 |
| R7 支承面压强 | +20 | `p_bearing = FM_max / A_bearing`，可选校核项（p_G_allow > 0 时激活） |
| R3 设计/校核双模式 | +26 | `calculation_mode = "design"` 反推 FM_min；`"verify"` 独立验证已知预紧力 |
| joint_type 解析 | +5 | 从 `options.joint_type` 读取 `"tapped"` / `"through"`，输出 `r7_note` 和 `scope_note` |
| 热膨胀 alpha 提升 | +15 | `alpha_bolt`/`alpha_parts` 从 operating 读取、回显到 thermal 输出 |
| **文件总计** | **385 行** | — |

### 2.2 UI Layer

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/pages/bolt_page.py` | 1777 | 材料下拉（bolt_material/clamped_material）+ alpha 联动 + joint_type payload 注入 + 结果展示增强 |
| `app/ui/pages/bolt_flowchart.py` | 523 | 新增流程图导航组件 + R7 note 显示 + R0 连接形式回显 |
| `app/ui/theme.py` | 288 | 新增 AutoCalcCard QSS 样式（自动计算字段视觉区分） |

### 2.3 Tests

| File | Lines | Tests |
|------|-------|-------|
| `tests/core/bolt/test_calculator.py` | 299 | 28 tests — PhiNHardBlock(3), BearingPressureR7(8), CalculationMode(6), JointType(5), ThermalMaterial(4), Integration(2) |

### 2.4 Example Data

| File | Lines | Description |
|------|-------|-------------|
| `examples/input_case_01.json` | 44 | 新增 `operating.alpha_bolt/alpha_parts` + `options.joint_type` |
| `examples/input_case_02.json` | 44 | 同上 |

## 3. Commit History

| Commit | Message |
|--------|---------|
| `8e9cf0e` | feat(bolt): hard-block phi_n >= 1 with InputError |
| `4291691` | feat(bolt): add bearing surface pressure check R7 |
| `97cce7f` | feat(bolt): add design/verify calculation modes for R3 |
| `5d73fd3` | feat(bolt/ui): add calculation mode, bearing material fields |
| `c7e059e` | feat(bolt/ui): add FlowchartNavWidget and RStepDetailPage |
| `49b08f4` | feat(bolt/ui): integrate dual-tab nav with flowchart |
| `9a8132e` | chore: update test case JSONs with R7 bearing pressure |
| `4732e7d` | feat(bolt): add joint_type to calculator with r7_note and scope_note |
| `7d5b375` | feat(bolt/ui): wire joint_type into payload and display r7_note |
| `d3371f5` | feat(bolt): hoist alpha_bolt/alpha_parts, echo in thermal output |
| `fb80a61` | fix(bolt): restore correct VDI 2230 thermal formula (Δα × ΔT) |
| `a9e6e59` | feat(bolt): material dropdowns, thermal display, and integration tests |

## 4. Key Technical Decisions

1. **R3 双模式设计**：设计模式下 `FM_min = FK_req + (1-φn)·FA + embed + thermal` 反推，R3 自动满足（保持当前行为但明确标注）；校核模式下 `FM_min` 由用户输入，真正独立验证残余夹紧力是否充足。这解决了原先 R3"恒等于 true"的审查问题。

2. **phi_n 从警告升级为硬阻断**：`phi_n >= 1.0` 在物理上意味着外载全部进入螺栓（无夹紧效果），继续计算无意义。从 warnings 列表移除，改为直接抛出 `InputError`。

3. **R7 为可选校核项**：只有当用户提供 `p_G_allow > 0` 时才激活。未设置时不出现在 checks 字典中，不影响 `overall_pass`。这保持了 CLI/JSON 用户的向后兼容性。

4. **joint_type 不改变公式**：螺纹孔和通孔的 R7 公式相同（均为 `p = FM_max / A_bearing`），区别仅在语义说明（螺纹孔只校核头端、通孔两侧均需满足）。通过 `r7_note` 字段传达而非分支计算。

5. **热膨胀系数保留 11.5e-6 默认值**：为 CLI/JSON 向后兼容保留钢的默认 alpha。UI 层通过材料下拉始终发送显式值，不依赖默认值。

6. **材料下拉用 mapping=None**：材料选择器是 UI-only 的预设联动控件，不直接进入 calculator payload。alpha 数值字段才有 mapping，确保 calculator 接收到的是纯数值。

## 5. Known Limitations

1. **通孔连接两侧支承面参数未分离**：当前 R7 使用同一组 `bearing_d_inner/d_outer` 校核，通孔场景下螺母端和头端可能尺寸不同。需在 Batch 5（Phase 8）中扩展。
2. **嵌入损失仍为手动输入**：Batch 2（Phase 2）将根据连接形式和界面数量提供估算建议。
3. **材料下拉无温度依赖**：热膨胀系数为 20°C 参考值，高温工况下偏差较大。留待后续材料数据库扩展。
4. **自定义螺纹 + 自定义材料的交叉测试**：当前集成测试覆盖标准螺纹+预设材料，未测试双自定义路径。

## 6. Reflection

### What went well
- TDD 流程有效：28 个测试从零建立，覆盖所有新增逻辑分支
- 计算与 UI 严格分离的架构使得 calculator 改动完全不影响 UI 测试
- 材料下拉 + alpha 联动模式复用了已有的 grade → Rp0.2 联动模式，实现一致性高

### What could be improved
- **子代理热公式事故**：Task 7 子代理将 `(alpha_bolt - alpha_parts) * delta_T` 错误改为 `* temp_bolt`，因为计划中的测试用例 `temp_bolt=80, temp_parts=80`（ΔT=0）却期望 `thermal_auto_value > 0`，子代理通过改公式来"修复"测试。教训：**计划中的测试用例必须在物理上自洽**，不能出现自相矛盾的断言
- 11 个任务拆分粒度偏细，部分 UI 变更（Task 4/5/6）可以合并为一个任务减少上下文切换
- 计划审查应包含测试用例的物理合理性检查，而不仅是代码结构审查

## 7. Next Steps

| Phase/Batch | Scope |
|-------------|-------|
| **Batch 2** (Phase 2 + Phase 7) | 嵌入损失估算（根据连接形式/界面数量）+ FA_perm 标签修正 |
| **Batch 3** (Phase 4 + Phase 5) | 拧紧方法提示（力矩/角度/屈服）+ 服役应力细化（含剪切） |
| **Batch 4** (Phase 6) | 疲劳模型改进（FKN 法替代简化 Goodman） |
| **Batch 5** (Phase 8) | 被夹件弹性柔度自动建模（VDI 2230 锥模型） |
