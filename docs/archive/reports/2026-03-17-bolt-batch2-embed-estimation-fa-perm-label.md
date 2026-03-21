# Batch 2: 嵌入损失经验估算 + 附加载荷标注修正 — 完成报告

**Date:** 2026-03-17
**Branch:** `main`
**Commits:** 1 (`8509250`)
**Total Lines Changed:** ~290 insertions, ~7 deletions across 7 文件（不含计划文档）
**Test Count:** 40 bolt calculator tests（从 28 → 40），全套 76 tests PASS

---

## 1. Objectives

实现螺栓模块 VDI 2230 §5.4.2 嵌入损失经验估算：当用户未手动填写嵌入损失且选择了表面粗糙度等级时，计算器自动根据界面数量和表面粗糙度估算嵌入损失 F_Z。同时将附加载荷能力估算（FA_perm）从正式校核项降级为参考信息，不再影响 overall_pass 判定。

## 2. Deliverables

### 2.1 Calculator Core (`core/bolt/calculator.py`)

| 改动 | 行数 | 描述 |
|------|------|------|
| `_EMBED_FZ_PER_INTERFACE` 常量 | +5 | rough=3.0μm, medium=2.5μm, fine=1.0μm 参考值 |
| `_estimate_embed_loss()` 辅助函数 | +18 | VDI 2230 §5.4.2 公式: F_Z = fz × n_if × 1e-3 / (δs + δp) |
| 嵌入估算集成块 | +15 | embed_loss=0 且有 surface_class 时自动激活估算 |
| additional_load 降级 | +12 | 从 checks_out 移出，新增 references 字典 |
| **文件总计** | **448 行** | — |

### 2.2 UI Layer

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/pages/bolt_page.py` | 1816 | SURFACE_CLASS_MAP + 表面粗糙度下拉 + CHECK_LABELS 参考标签 + _render_result/_build_recommendations/_build_report_lines 适配 references |
| `app/ui/pages/bolt_flowchart.py` | 533 | R1 计算过程新增嵌入损失自动估算详情显示 |

### 2.3 Tests

| File | Lines | Tests |
|------|-------|-------|
| `tests/core/bolt/test_calculator.py` | 453 | 40 tests — TestEmbedEstimation(6), TestAdditionalLoadReference(4), TestBatch2Integration(2), 加上 Batch 1 的 28 tests |

### 2.4 Example Data

| File | Lines | Description |
|------|-------|-------------|
| `examples/input_case_01.json` | 49 | 新增 `clamped.surface_class` + `clamped.part_count` |
| `examples/input_case_02.json` | 49 | 同上 |

## 3. Commit History

| Commit | Message |
|--------|---------|
| `8509250` | feat(bolt): embed loss estimation + additional_load as reference |

## 4. Key Technical Decisions

1. **嵌入估算为"软填充"模式**：仅当 `embed_loss == 0.0` 且 `surface_class is not None` 时自动估算。用户一旦手动输入 embed_loss > 0，完全跳过估算。这保证了手动值的绝对优先权。

2. **界面数量公式**：螺纹孔 `n_interfaces = part_count + 1`，通孔 `n_interfaces = part_count + 2`（多一个螺母/垫圈界面）。直接复用 Batch 1 的 joint_type 字段。

3. **additional_load 降级为 references 而非删除**：FA_perm 是有用的参考信息（"螺栓还能承受多少额外载荷"），但它基于 10% Rp0.2 裕量假设，不是 VDI 2230 正式校核项。保留在 references 字典中，UI 以"⚠ 参考"标签展示，不参与 overall_pass。

4. **CHECK_LABELS 保留 additional_load_ok 键**：badge widget 的创建依赖 CHECK_LABELS 字典的键。如果删除键，badge 控件不会被创建，后续就无法显示参考状态。因此保留键但改标签为"附加载荷能力估算 ⚠ 参考"，在渲染时从 references 字典读取结果。

5. **表面粗糙度参考值保守取值**：采用 VDI 2230 §5.4.2 表格的典型值（rough=3.0, medium=2.5, fine=1.0 μm/界面），而非提供连续输入。对工程估算场景足够，避免用户输入任意值导致误差放大。

## 5. Known Limitations

1. **嵌入损失估算不区分螺栓/被夹件材料**：VDI 2230 完整表格考虑材料硬度影响，当前仅按表面粗糙度分级。留待后续材料数据库扩展。
2. **part_count 字段 UI 暂无独立验证**：默认值 1，无最大值限制。极端值（如 part_count=100）会产生不合理的估算。
3. **报告导出中的 additional_load 行**：显示"超限（仅参考）"而非"不通过"，但 PDF 导出格式未测试。
4. **flowchart R1 嵌入估算显示**：仅在自动估算激活时显示，手动输入时不显示估算参数（符合预期但可能让用户困惑为什么没有估算信息）。

## 6. Reflection

### What went well
- 计划文档质量高：经过 plan-document-reviewer 审查修复了 4 个 MAJOR 问题后，执行阶段几乎零偏差
- TDD 流程顺畅：12 个新测试全部一次通过，无需调试
- references 字典的设计解决了"保留有用信息但不影响校核结论"的矛盾

### What could be improved
- **单次提交粒度偏大**：6 个 Task 的改动合并为一次提交，不利于 git bisect 追踪问题。应在每个 Task 完成后单独提交
- **计划中 UI 部分的行号引用**：bolt_page.py 在 Batch 1 后已达 1777 行，计划中的行号引用多处过时，执行时需要重新搜索定位

## 7. Next Steps

| Phase/Batch | Scope |
|-------------|-------|
| **Batch 3** (Phase 4 + Phase 5) | 拧紧方法提示（力矩/角度/屈服）+ 服役应力细化（含剪切） |
| **Batch 4** (Phase 6) | 疲劳模型改进（FKN 法替代简化 Goodman） |
| **Batch 5** (Phase 8) | 被夹件弹性柔度自动建模（VDI 2230 锥模型） |
