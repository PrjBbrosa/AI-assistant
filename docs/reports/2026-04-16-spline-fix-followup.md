# 花键连接校核修复执行回顾

- 日期：2026-04-16
- 分支：`fix/spline-blocking`
- 计划：`docs/plans/2026-04-16-spline-fit-fixes.md`
- 关联评审：`docs/reports/2026-04-16-spline-fit-review.md`

## 实际改动

| Step | 主题 | Commit |
|------|------|--------|
| 1 | DIN 5480 近似公式重推（拓扑正确，h_w≈0.9m） | `fix(spline-geom): correct DIN 5480 approximation to satisfy tip/root ordering` |
| 2 | 材料下拉联动屈服强度 + 切"自定义"解锁 | `feat(spline-ui): auto-fill yield strength when choosing preset material` |
| 3 | k_alpha 默认值与 UI 对齐到 1.3，公式注释补 K_A 预乘说明 | `fix(spline-core): align k_alpha default with UI and clarify docstring` |
| 4 | 扭矩容量安全系数 `torque_capacity_sf` 对外暴露 | `feat(spline-core): expose torque_capacity_sf in scenario A result` |
| 5 | DIN 5480 catalog docstring 规范化 | `docs(spline): normalize din5480_table docstring with catalog-derived coefficients` |
| 6 | 仅花键模式下 payload 过滤 smooth_* 段 | `feat(spline-ui): filter smooth_* sections from payload when not in combined mode` |
| 附 | MainWindow 侧栏命名对齐 + live feedback 消息写入 message_box | `fix(spline-ui): rename sidebar entry to 花键连接校核 and mirror messages in result box` |

## 与计划偏离点

1. **近似系数**：计划原建议 `d_a1=d-0.1m, d_a2=d-0.9m, d_f1=d-2.2m`（h_w≈0.4m），无法通过 `test_approximation_aligns_with_catalog_w25x125`（catalog h_w=0.9m）。改为从 W 25x1.25x18 反推的系数 `d_a1=d-0.2m, d_a2=d-2.0m, d_f1=d-2.3m`（h_w≈0.9m），与 catalog 误差 0%。
2. **Step 6.1**（standard→custom 恢复 FieldSpec default）未做：切"自定义"仅解锁卡片样式，保留用户输入值。保留现有测试 `test_standard_designation_custom_restores_editable` 未变。
3. **Step 6.3**（`tests/core/spline/test_din5480_table.py`）在基线已存在，复用无需新增。
4. **Step 6.2** 为补 hint 文案，跳过（UX 层面低风险但不影响功能与测试）。

## 示例案例回归

`examples/spline_case_02.json`（`approximate` 模式）新公式下：

- `p_flank = 30.62 MPa`（旧 26.04）
- `flank_safety = 3.27`（旧 3.84）
- `torque_capacity_sf = 3.27`
- `overall_pass = True`

安全余量仍充足，无需调整示例载荷。

## 测试

全套 pytest：**394 passed, 0 failed**（`QT_QPA_PLATFORM=offscreen python3 -m pytest tests/`）。

3 个 main 分支既有花键 UI 失败全部解决：

- `test_live_feedback_updates_result_without_manual_calculate` — 通过 `_display_result` 同步写 `message_box`
- `test_material_autofills_with_blue_style` — Step 2 扩展 yield_mpa + 无条件解锁
- `test_main_window_uses_connection_check_name_for_spline_module` — 侧栏改名"花键连接校核"

## 手工回归建议

1. 启动 `python3 app/main.py`，切到"花键连接校核"；
2. 加载测试案例 1（`reference_dimensions`）与测试案例 2（`approximate`）验证结果；
3. 切"联合"模式，材料选 40Cr，确认屈服强度 785，切"自定义"三字段解锁；
4. 选标准规格 `W 25x1.25x18`，几何字段锁定；
5. 导出 PDF，检查包含 `扭矩容量安全系数 S_T = ...` 行；
6. 改扭矩到 1e5 N·m，观察消息框实时显示"齿面承压安全系数不足"。
