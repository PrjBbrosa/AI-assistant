# Interference Roughness Warning Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在过盈配合页面的“摩擦与粗糙度”章节内增加固定提醒框，突出说明批量生产压入散差与粗糙度/机加工状态的关系。

**Architecture:** 在 `InterferenceFitPage` 的通用章节渲染逻辑中，为“摩擦与粗糙度”章节插入一个专用提醒卡片 helper；主题样式放在 `theme.py`；测试从 UI 层锁定 widget 与核心文案，不改动计算逻辑。

**Tech Stack:** Python 3、PySide6、`unittest`、项目内 Markdown 文档。

---

## 文件结构映射

- Modify: `app/ui/pages/interference_fit_page.py`
  - 在粗糙度章节中插入专用提醒卡片并暴露测试可访问引用。
- Modify: `app/ui/theme.py`
  - 新增提醒卡片样式。
- Modify: `tests/ui/test_interference_page.py`
  - 先写失败测试，再锁定提醒框存在和文案内容。

## Chunk 1: TDD 锁定 UI 行为

### Task 1: 写失败测试

**Files:**
- Modify: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 新增提醒框存在性测试**

  断言页面创建后存在专用提醒框引用，且 object name 为专用警示卡片。

- [ ] **Step 2: 新增提醒文案测试**

  断言提醒文案包含：
  - `批量生产`
  - `压入散差`
  - `有效过盈`
  - `波纹度`
  - `润滑`

- [ ] **Step 3: 运行定向测试并确认先失败**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -q`

  Expected:
  - 新测试失败
  - 失败原因集中在提醒框尚未实现

## Chunk 2: 最小实现

### Task 2: 实现提醒框与样式

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `app/ui/theme.py`
- Test: `tests/ui/test_interference_page.py`

- [ ] **Step 1: 在页面中新增提醒框 helper**

  创建专用 helper 构建提醒卡片，标题与正文按 spec 固定输出。

- [ ] **Step 2: 将 helper 插入“摩擦与粗糙度”章节**

  在字段卡片之后插入提醒框，并保存 `self.roughness_warning_box` 与 `self.roughness_warning_text` 供测试使用。

- [ ] **Step 3: 在主题中新增提醒框样式**

  使用明显区别于普通 `SubCard` 的视觉样式。

- [ ] **Step 4: 运行定向 UI 测试**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -q`

  Expected:
  - 所有 UI 测试通过

## Chunk 3: 回归验证

### Task 3: 跑过盈配合核心 + UI 回归

**Files:**
- Verify only

- [ ] **Step 1: 运行过盈配合相关回归**

  Run: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/interference/test_calculator.py tests/core/interference/test_fit_selection.py tests/core/interference/test_assembly.py tests/core/interference/test_fretting.py tests/ui/test_interference_page.py -q`

  Expected:
  - 全部通过
