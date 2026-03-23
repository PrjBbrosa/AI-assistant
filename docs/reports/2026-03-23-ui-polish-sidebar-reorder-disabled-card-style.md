# UI 优化：侧栏重排、螺栓标签清理、全局禁用字段淡蓝样式统一

**Date:** 2026-03-23
**Branch:** `main`
**Commits:** 尚未提交（全部为 unstaged 修改）
**Total Lines:** 136 行净增 / 43 行净删，涉及 9 个文件

---

## 1. Objectives

本次工作包含三组 UI 改进：

1. **螺栓模块标签清理**：移除侧栏和校核结果中的 "(R8)" 标注，在计算模式下方增加 FK_req 和 FM_min 的中文详细解释，降低新手理解门槛。
2. **侧栏模块重排**：将"花键过盈配合"与"赫兹应力"对调位置，使功能分组更贴合实际工程使用频率。
3. **全局禁用字段样式统一**：将所有页面中"因选项关闭而不可输入"的字段，从原来的隐藏 (`setVisible(false)`) 或仅 `setReadOnly` 改为统一的淡蓝色 AutoCalcCard 样式块，保持 UI 布局稳定性，明确告知用户字段存在但当前不参与计算。

## 2. Deliverables

### 2.1 螺栓模块标签清理

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/pages/bolt_page.py` | 2768 | 移除 R8 标注；计算模式下方增加 FK_req/FM_min 解释文案 |

### 2.2 侧栏重排

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/main_window.py` | 112 | 花键(原5)↔赫兹(原3) 位置对调 |

### 2.3 禁用字段样式统一

| File | Lines | Description |
|------|-------|-------------|
| `app/ui/theme.py` | 317 | 新增 AutoCalcCard 下 QComboBox 样式规则 |
| `app/ui/pages/interference_fit_page.py` | 1972 | 新增 `_set_card_disabled()` + fretting 联动 + 装配/配合模式卡片样式切换 |
| `app/ui/pages/hertz_contact_page.py` | 844 | 点接触模式下线接触字段从隐藏改为淡蓝禁用 |
| `app/ui/pages/spline_fit_page.py` | 689 | 仅花键模式下光面配合字段从隐藏改为淡蓝禁用 |
| `app/ui/pages/worm_gear_page.py` | 886 | LC 关闭时参数卡片从隐藏改为淡蓝禁用 |

### 2.4 Tests

| File | Lines | Tests |
|------|-------|-------|
| `tests/ui/test_spline_fit_page.py` | 82 | 更新 `test_mode_switch_disables_smooth_fields` 检查 objectName 而非 isHidden |
| `tests/ui/test_worm_page.py` | 249 | 更新 `test_load_capacity_disabled_shows_autocalc_style` / `_subcard_style` |

## 3. Commit History

尚未提交，所有改动为 unstaged 状态。

## 4. Key Technical Decisions

1. **选择 AutoCalcCard 而非 DisabledSubCard**：AutoCalcCard 的淡蓝色 (#EDF1F5) 在视觉上更温和，与"自动计算/不可编辑"的语义一致；DisabledSubCard 的灰色虚线边框暗示"功能未实现"，语义不符。
2. **`_set_card_disabled()` 在每个页面各自实现而非提取到基类**：因为各页面的 widget 字典命名不同（`_field_widgets` vs `_widgets`），且 base_chapter_page 不管理字段级别逻辑。避免过度抽象。
3. **蜗轮 LC 参数采用整体卡片变色而非逐字段**：LC 参数是一组紧密相关的 7 个字段，整体禁用/启用比逐个切换更直观。通过遍历子 QFrame 统一设置 objectName。
4. **保留校核指南中的 R8 引用**：校核指南和结果说明中的 "R8" 是 VDI 2230 标准术语上下文，对照标准时有参考价值，不应删除。仅从侧栏导航和校核名称中移除。
5. **theme.py 新增 QComboBox 样式**：原 AutoCalcCard 只有 QLineEdit 样式，下拉框在禁用状态下无对应样式导致视觉不一致。

## 5. Known Limitations

1. `_set_card_disabled()` 在三个页面中重复实现（interference_fit, hertz, spline），代码相同。未来如有第四个页面需要同样模式，应考虑提取到 BaseChapterPage 或 mixin。
2. 蜗轮页面的 LC 参数禁用逻辑直接内联在 `_on_lc_enabled_changed` 中，未使用通用 `_set_card_disabled`，因其操作的是 group card 而非单个 field card。
3. 螺栓页面中仍有大量字段通过 `setVisible(False)` 隐藏（多层字段、自定义螺纹字段、柔度手动模式字段），这些是"整段不相关"的场景，隐藏比禁用更合适，暂未改动。

## 6. Reflection

### What went well
- 全局审计一次性覆盖了 5 个页面的条件字段逻辑，确保了跨模块的一致体验
- 利用 Qt 的 `style().unpolish() / polish()` 机制实现运行时动态切换 objectName 样式，无需重建 widget
- 测试一次通过 275/275，无需额外修复（除了一个因重构遗漏的变量引用 bug，发现并修复后全部通过）

### What could be improved
- 初次修改 `_sync_fit_mode_fields` 时遗漏了 `preferred` 变量的引用更新，导致 NameError。重构删除局部变量时应全文搜索其引用。
- `_set_card_disabled()` 重复代码可以通过 mixin 或工具函数消除

### Recurring Issues
- None identified.

## 7. Next Steps

| Phase/Item | Scope |
|------------|-------|
| 螺栓模块条件字段审计 | 评估多层/自定义螺纹/手动柔度字段是否也适合淡蓝禁用（而非隐藏） |
| 提取 `_set_card_disabled` 到基类 | 如再有新模块需要此模式，统一到 BaseChapterPage |
| 输入条件持久化覆盖 | 花键模块尚缺 input persistence |
