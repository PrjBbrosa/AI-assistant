# 花键模块 Review 修复与三项增强 Report

**Date:** 2026-03-25
**Branch:** `main`
**Commits:** 12 (9232e42 ~ 53e3f45)
**Total Lines:** 2016 lines across 9 source/test files

---

## 1. Objectives

对花键配合模块进行全面 code review，发现并修复了 d_m 公式错误、异常处理过宽、UI 文字不友好等问题。随后实现三项功能增强：DIN 5480 标准花键尺寸查表、场景 B 压入力曲线展示、自动填充字段 AutoCalcCard 蓝色样式统一。

上一次报告（2026-03-23）中提到的"全局禁用字段样式统一"工作在本次得到进一步落实——花键模块的载荷工况、材料联动、标准规格联动现在全部使用 AutoCalcCard 蓝色样式，与螺栓、过盈配合模块保持一致。

## 2. Deliverables

### 2.1 Review 修复（计算层）

| File | Lines | Description |
|------|-------|-------------|
| `core/spline/geometry.py` | 106 | d_m 公式修正: `(d_a1+d_f1)/2` → `(d_a1+d_a2)/2` |

### 2.2 Review 修复（UI 层）

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/pages/spline_fit_page.py` | 781 | 7 处 hint 文字改进 + verdict 中文化 + 异常处理分离 + PDF 降级提示 |

### 2.3 新增功能

| File | Lines | Description |
|------|-------|-------------|
| `core/spline/din5480_table.py` | 119 | DIN 5480 标准花键目录（30 条 W 15~50，模数 0.8~2.5） |
| `app/ui/pages/spline_fit_page.py` | (同上) | 标准规格下拉框 + 压入力曲线 + AutoCalcCard 样式 |
| `app/ui/widgets/press_force_curve.py` | 209 | 已有控件，本次仅复用 |

### 2.4 Tests

| File | Lines | Tests |
|------|-------|-------|
| `tests/core/spline/test_geometry.py` | 93 | 9 tests（+2 边界） |
| `tests/core/spline/test_calculator.py` | 257 | 22 tests（+4 边界） |
| `tests/core/spline/test_din5480_table.py` | 41 | 6 tests（新增） |
| `tests/ui/test_spline_fit_page.py` | 141 | 14 tests（+5 联动+样式） |

**测试总计**: 34 → 51（+17）

## 3. Commit History

| Commit | Message |
|--------|---------|
| `9232e42` | fix(spline): correct d_m formula to use contact zone center (d_a1+d_a2)/2 |
| `4dc9934` | docs(spline): improve UI hints for beginner friendliness and localize verdict level |
| `7ea3f5f` | fix(spline): separate InputError from generic Exception, add PDF fallback notice |
| `fd128ae` | test(spline): add 6 boundary condition tests for geometry and calculator |
| `fef1da5` | docs: add spline enhancements design spec + update CLAUDE.md AutoCalcCard rule |
| `e665c7c` | docs: fix spec issues from review (curve placement, mode priority, field IDs) |
| `1fca802` | docs: fix plan issues from review (data provenance, signal duplication, hasattr) |
| `a6f3f38` | feat(spline): add DIN 5480 standard spline lookup table (W 15-50) |
| `50c4b83` | feat(spline): add DIN 5480 standard designation dropdown with auto-fill |
| `9119b1e` | feat(spline): display press force curve for scenario B |
| `53e3f45` | fix(spline): apply AutoCalcCard blue style to all auto-filled fields |

（另有 1 个中间修复 commit `abdca94` 来自螺栓/过盈模块 review 修复）

## 4. Key Technical Decisions

1. **d_m 公式选择 `(d_a1+d_a2)/2`**: h_w 有效齿高定义为 `(d_a1-d_a2)/2`，d_m 作为力臂必须取同一接触带的中心，而非外花键齿体中心 `(d_a1+d_f1)/2`。偏差约 0.6%~1.5%，在安全裕量紧张时可能影响判断。

2. **DIN 5480 查表数据采用近似公式生成**: `d_a1 ≈ d_B - 0.1m`、`d_a2 ≈ d_B - m`、`d_f1` 按标准齿根间隙。非精确标准值，已在 docstring 中注明数据溯源和使用限制。

3. **压入力曲线复用已有 PressForceCurveWidget**: 场景 B 委托 DIN 7190 计算后已返回完整的 `press_force_curve` 数据，UI 只需 5 行代码调用 `set_curve()`，零新增控件代码。

4. **AutoCalcCard 样式优先级规则**: 模式级禁用（`_on_mode_changed`）优先于自动填充级禁用（材料/工况联动）。实现方式为模式切换时重新触发材料联动以刷新样式，避免"仅花键"模式下材料切"自定义"误恢复 smooth 字段。

5. **异常处理分离 InputError/Exception**: 避免代码 bug（TypeError、KeyError 等）被当作"输入错误"展示给用户。内部错误现在有独立的提示文案。

## 5. Known Limitations

1. DIN 5480 查表数据为近似值，非标准原文精确数据——实际工程应以采购件实测或目录值为准。
2. 压入力曲线仅在场景 B（联合模式）下显示，仅花键模式无曲线。
3. 花键模块仍缺少：输入条件持久化、完整齿根弯曲/剪切校核、矩形花键支持。
4. `pressure_angle_deg` 参数仍不参与实际计算，仅作记录。
5. 材料库仅 3 种钢 + 自定义，未覆盖 20CrMnTi 等常用渗碳钢。

## 6. Reflection

### What went well
- Review → Design → Plan → Subagent 执行的完整流水线高效运转，8 个实现 commit 零回退
- Spec review 两轮共发现 12 个问题（含 3 个 critical），全部在实现前修复，避免了返工
- 委托模式的优势再次体现——场景 B 压入力曲线只需传递已有数据，5 行代码完成展示
- AutoCalcCard 样式优先级问题在 spec review 阶段就被发现并设计了解决方案

### What could be improved
- DIN 5480 查表数据应使用标准原文而非近似公式推导，后续需逐条核实
- Review 阶段发现 d_m 公式错误说明原始开发时的公式验证不够严格——应在 TDD 阶段就用手算值交叉验证

### Recurring Issues
- AutoCalcCard 蓝色样式遗漏：上次报告（2026-03-23）专门做了全局样式统一，本次 review 又发现花键模块的载荷工况和材料联动遗漏了蓝色样式。已将此规则写入 CLAUDE.md 第 5 条架构约定，避免再次遗漏。

## 7. Next Steps

| Phase/Item | Scope |
|------------|-------|
| DIN 5480 数据核实 | 逐条对照标准原文或目录验证 30 条记录的精确性 |
| 输入条件持久化 | 花键模块接入 `input_condition_store.py` |
| 材料库扩充 | 增加 20CrMnTi、GCr15 等常用钢种 |
| DIN 5480 扩展 | 覆盖模数 3~10 大规格（W 50~100） |
| 齿根弯曲/剪切校核 | DIN 5466 / DIN 6892 完整校核流程 |
