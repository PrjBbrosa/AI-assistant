# 新手友好化 · 工程知识帮助系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 6 个校核模块中为所有专业术语与校核方法提供"?"按钮弹出的 Markdown 帮助内容，不改 `core/` 计算逻辑。

**Architecture:** 内容以 Markdown 存于 `docs/help/`；`HelpProvider` 单例负责索引和懒加载；`HelpPopover`（基于 `QTextBrowser.setMarkdown`）负责渲染；"?" 按钮通过 `FieldSpec.help_ref`（字段级）和 `base_chapter_page.add_chapter(help_ref=...)`（章节级）注入。实施顺序：基础设施 → 蜗杆 pilot（规范固化）→ 其他 5 模块串行 → 终审，每阶段后接 codex adversarial review。

**Tech Stack:** Python 3.12, PySide6 (QToolButton / QDialog / QTextBrowser), pytest (headless via `QT_QPA_PLATFORM=offscreen`).

**Reference:** 必读 spec `docs/superpowers/specs/2026-04-19-newbie-friendly-help-system-design.md`（架构、模板、Stage 划分细节）

---

## How to Resume (冷启动续跑指南)

新 session 接手时**顺序做这 3 件事**：

1. 读 `CLAUDE.md`（自动加载）+ 本 plan 顶部至 "How to Resume" 节
2. 扫本文件勾选进度：找到第一个未勾选的 `- [ ]` 任务，那就是起点
3. 读该 Stage "前置阅读清单"；如 Stage ≥ 2，还要读：
   - `.claude/lessons/help-content-lessons.md`
   - `.claude/lessons/ui-lessons.md`
   - `.claude/lessons/review-lessons.md`
   - `docs/help/GUIDELINES.md`

每个 Stage 末尾有 "Stage 完成判据"，全部满足才能推进到下一 Stage。

---

## File Structure Map

### 创建（新文件）
| 路径 | 职责 |
|------|------|
| `app/ui/help_provider.py` | 单例，扫描 `docs/help/` 构建 ref→path 索引，懒加载 + 缓存 |
| `app/ui/widgets/help_popover.py` | `HelpPopover(QDialog)`，460x520 无模态弹窗，渲染 Markdown |
| `app/ui/widgets/help_button.py` | `HelpButton(QToolButton)`，16x16 "?" 按钮 |
| `tests/ui/test_help_provider.py` | HelpProvider 单元测试 |
| `tests/ui/test_help_popover.py` | HelpPopover + HelpButton 交互测试 |
| `docs/help/GUIDELINES.md` | 内容规范文档（Stage 0 骨架 → Stage 1 完善 → Stage 7 终稿）|
| `docs/help/terms/*.md` | 术语池（首批 Stage 1 写蜗杆相关，后续按需增量）|
| `docs/help/modules/<module>/*.md` | 模块概念文（每模块一目录）|
| `.claude/lessons/help-content-lessons.md` | 内容撰写经验（Stage 1.5 新建）|

### 修改（现有文件）
| 路径 | 改动要点 |
|------|--------|
| `app/ui/pages/base_chapter_page.py` | `add_chapter` 新增 `help_ref` 关键字参数 |
| `app/ui/theme.py` | 新增 `#HelpButton` QSS |
| `app/ui/pages/worm_gear_page.py` | `FieldSpec` 加 `help_ref` 字段；填充；subtitle 重写 |
| `app/ui/pages/bolt_page.py` | 同上 |
| `app/ui/pages/bolt_tapped_axial_page.py` | 同上 |
| `app/ui/pages/interference_fit_page.py` | 同上 |
| `app/ui/pages/hertz_contact_page.py` | 同上 |
| `app/ui/pages/spline_fit_page.py` | 同上 |

---

## Stage 0: 基础设施（~0.5 天）

**前置阅读**：spec §4, §5, §6, §10

### Task 0.1: HelpProvider 及其测试（TDD）

**Files:**
- Create: `app/ui/help_provider.py`
- Create: `tests/ui/test_help_provider.py`
- Create: `docs/help/terms/_sample.md`（测试夹具）

- [ ] **Step 1: 先创建测试夹具**

文件：`docs/help/terms/_sample.md`
```markdown
# 示例术语（S）

**一句话**：仅供自测。

**怎么理解**：HelpProvider 单元测试用，切勿删除。

**出处**：internal fixture
```

- [ ] **Step 2: 写失败测试 —— 基础加载**

文件：`tests/ui/test_help_provider.py`
```python
import pytest
from pathlib import Path
from app.ui.help_provider import HelpProvider, HelpEntry


@pytest.fixture
def provider():
    root = Path(__file__).resolve().parents[2] / "docs" / "help"
    return HelpProvider(root=root)


def test_provider_loads_existing_term(provider):
    entry = provider.get("terms/_sample")
    assert isinstance(entry, HelpEntry)
    assert entry.title == "示例术语（S）"
    assert "仅供自测" in entry.body_md


def test_provider_missing_ref_returns_placeholder(provider):
    entry = provider.get("terms/does_not_exist")
    assert entry.title.startswith("帮助内容缺失")
    assert "does_not_exist" in entry.body_md


def test_provider_cache_returns_same_entry(provider):
    first = provider.get("terms/_sample")
    second = provider.get("terms/_sample")
    assert first is second  # 同对象即命中缓存
```

- [ ] **Step 3: 运行测试确认失败**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_provider.py -v
```

预期：`ImportError: cannot import name 'HelpProvider' from 'app.ui.help_provider'`

- [ ] **Step 4: 实现 HelpProvider**

文件：`app/ui/help_provider.py`
```python
"""Markdown 帮助内容的索引与加载。"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class HelpEntry:
    title: str
    body_md: str


def _default_root() -> Path:
    # PyInstaller 兼容：打包后 docs 随 _MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "docs" / "help"
    return Path(__file__).resolve().parents[2] / "docs" / "help"


def _parse(md_text: str, ref: str) -> HelpEntry:
    lines = md_text.splitlines()
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    if not title:
        title = f"(无标题) {ref}"
    return HelpEntry(title=title, body_md=body)


class HelpProvider:
    """单例：按 ref 懒加载 Markdown 帮助内容。"""

    _instance: Optional["HelpProvider"] = None

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = root or _default_root()
        self._index: Dict[str, Path] = {}
        self._cache: Dict[str, HelpEntry] = {}
        self._build_index()

    @classmethod
    def instance(cls) -> "HelpProvider":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _build_index(self) -> None:
        if not self._root.exists():
            return
        for md_path in self._root.rglob("*.md"):
            rel = md_path.relative_to(self._root).with_suffix("")
            ref = str(rel).replace("\\", "/")
            # GUIDELINES.md 等顶层文件不纳入 ref 索引
            if "/" not in ref:
                continue
            self._index[ref] = md_path

    def get(self, ref: str) -> HelpEntry:
        if ref in self._cache:
            return self._cache[ref]
        path = self._index.get(ref)
        if path is None:
            entry = HelpEntry(
                title=f"帮助内容缺失：{ref}",
                body_md=f"未找到 ref=`{ref}` 对应的帮助文件。",
            )
        else:
            text = path.read_text(encoding="utf-8")
            entry = _parse(text, ref)
        self._cache[ref] = entry
        return entry
```

- [ ] **Step 5: 运行测试确认通过**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_provider.py -v
```

预期：3 passed

- [ ] **Step 6: commit**

```bash
git add app/ui/help_provider.py tests/ui/test_help_provider.py docs/help/terms/_sample.md
git commit -m "feat(help): add HelpProvider with Markdown indexing and caching"
```

---

### Task 0.2: HelpButton（含 theme.py 样式）

**Files:**
- Create: `app/ui/widgets/help_button.py`
- Modify: `app/ui/theme.py`（追加 HelpButton QSS）

- [ ] **Step 1: 读 theme.py 现状**

```bash
wc -l app/ui/theme.py
```

定位文件末尾，找到 QSS 字符串的结尾。

- [ ] **Step 2: 在 theme.py 末尾追加 HelpButton 样式**

在全局 QSS 字符串里追加：
```css
QToolButton#HelpButton {
    background: #E3E3DE;
    color: #5F5E5B;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
    padding: 0;
    margin-left: 4px;
}
QToolButton#HelpButton:hover {
    background: #EED9CF;
    color: #D97757;
}
```

具体位置：找到已有的 `QPushButton` 或 `Card` 相关样式块，紧接其后加入。

- [ ] **Step 3: 创建 HelpButton 类**

文件：`app/ui/widgets/help_button.py`
```python
"""显示 '?' 的小按钮，触发 HelpPopover。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget


class HelpButton(QToolButton):
    """16x16 的 '?' 按钮，objectName='HelpButton' 由 theme.py 提供样式。"""

    def __init__(self, help_ref: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("HelpButton")
        self.setText("?")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击查看帮助")
        self._help_ref = help_ref
        self.clicked.connect(self._on_click)

    @property
    def help_ref(self) -> str:
        return self._help_ref

    def _on_click(self) -> None:
        # 导入放在方法内部避免循环导入
        from app.ui.widgets.help_popover import HelpPopover
        popover = HelpPopover.show_for(self._help_ref, anchor=self)
        # HelpPopover 自管理生命周期
        _ = popover
```

- [ ] **Step 4: 冒烟测试（延后到 Task 0.3 一起）**

此任务无独立测试。

- [ ] **Step 5: commit**

```bash
git add app/ui/widgets/help_button.py app/ui/theme.py
git commit -m "feat(help): add HelpButton widget with theme styling"
```

---

### Task 0.3: HelpPopover 及其测试（TDD）

**Files:**
- Create: `app/ui/widgets/help_popover.py`
- Create: `tests/ui/test_help_popover.py`

- [ ] **Step 1: 写失败测试**

文件：`tests/ui/test_help_popover.py`
```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

from app.ui.widgets.help_button import HelpButton
from app.ui.widgets.help_popover import HelpPopover


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_popover_opens_with_title_and_body(app):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.isVisible()
    assert "示例术语" in popover.windowTitle() or "示例术语" in popover.title_text()
    assert "仅供自测" in popover.body_markdown()
    popover.close()


def test_popover_missing_ref_shows_placeholder(app):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/definitely_missing", anchor=anchor)
    assert popover.isVisible()
    assert "缺失" in popover.title_text()
    popover.close()


def test_help_button_objectname(app):
    btn = HelpButton("terms/_sample")
    assert btn.objectName() == "HelpButton"
    assert btn.text() == "?"
    assert btn.help_ref == "terms/_sample"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover.py -v
```

预期：ImportError for HelpPopover

- [ ] **Step 3: 实现 HelpPopover**

文件：`app/ui/widgets/help_popover.py`
```python
"""Markdown 帮助内容的弹出窗口。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from app.ui.help_provider import HelpProvider


class HelpPopover(QDialog):
    """460x520 无模态 Markdown 弹窗。"""

    _current: Optional["HelpPopover"] = None

    def __init__(
        self,
        title: str,
        body_md: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(False)
        self.setFixedSize(460, 520)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("HelpPopoverTitle")
        self._title_label.setWordWrap(True)

        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)

        header = QHBoxLayout()
        header.setContentsMargins(12, 10, 12, 6)
        header.addWidget(self._title_label, 1)
        header.addWidget(close_btn, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setMarkdown(body_md)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self._browser, 1)

    @classmethod
    def show_for(
        cls,
        help_ref: str,
        anchor: QWidget,
    ) -> "HelpPopover":
        # 同时只允许一个实例
        if cls._current is not None and cls._current.isVisible():
            cls._current.close()

        entry = HelpProvider.instance().get(help_ref)
        popover = cls(title=entry.title, body_md=entry.body_md, parent=anchor.window())
        cls._current = popover

        # 定位：锚点右下偏移 +8，屏幕边界翻转
        anchor_rect = anchor.rect()
        top_left_global = anchor.mapToGlobal(QPoint(anchor_rect.right(), anchor_rect.bottom()))
        target = top_left_global + QPoint(8, 8)

        screen = anchor.screen().availableGeometry()
        w, h = popover.width(), popover.height()
        if target.x() + w > screen.right():
            target.setX(screen.right() - w - 8)
        if target.y() + h > screen.bottom():
            target.setY(screen.bottom() - h - 8)

        popover.move(target)
        popover.show()
        return popover

    def title_text(self) -> str:
        return self._title_label.text()

    def body_markdown(self) -> str:
        return self._browser.toMarkdown()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover.py -v
```

预期：3 passed

- [ ] **Step 5: commit**

```bash
git add app/ui/widgets/help_popover.py tests/ui/test_help_popover.py
git commit -m "feat(help): add HelpPopover QDialog with Markdown rendering"
```

---

### Task 0.4: FieldSpec 新增 help_ref 字段（6 个 page）

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`
- Modify: `app/ui/pages/bolt_page.py`
- Modify: `app/ui/pages/bolt_tapped_axial_page.py`
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `app/ui/pages/hertz_contact_page.py`
- Modify: `app/ui/pages/spline_fit_page.py`

- [ ] **Step 1: 读每个 page 的 FieldSpec 类定义位置**

```bash
grep -n "class FieldSpec" app/ui/pages/*.py
```

记录行号，每个 page 的 FieldSpec 都要改。

- [ ] **Step 2: 在每个 FieldSpec 类里加 help_ref 字段**

示例（worm_gear_page.py 已有字段）：
```python
@dataclass(frozen=True)
class FieldSpec:
    field_id: str
    label: str
    unit: str
    hint: str
    widget_type: str = "number"
    options: tuple[str, ...] = ()
    default: str = ""
    placeholder: str = ""
    help_ref: str = ""      # <-- 新增
    ...
```

对其余 5 个 page 做同样的修改。**注意**：各 page 的 FieldSpec 定义字段顺序略有不同，`help_ref: str = ""` 放在所有非 default 字段之后、属性方法之前即可。

- [ ] **Step 3: 运行所有现有测试确保未破坏**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

预期：所有 tests pass（新增字段有默认值，旧测试不受影响）。

- [ ] **Step 4: commit**

```bash
git add app/ui/pages/*.py
git commit -m "feat(help): add help_ref field to FieldSpec across 6 pages"
```

---

### Task 0.5: base_chapter_page 扩展 add_chapter(help_ref=None)

**Files:**
- Modify: `app/ui/pages/base_chapter_page.py`

- [ ] **Step 1: 读 base_chapter_page 现状**

```bash
grep -n "def add_chapter" app/ui/pages/base_chapter_page.py
```

读该方法现有实现（连带标题布局区域）。

- [ ] **Step 2: 修改 add_chapter 签名加 help_ref 参数**

在方法签名加 `*, help_ref: str | None = None`。在章节标题 label 所在行附近，如果 `help_ref` 非 None，插入 HelpButton：

```python
from app.ui.widgets.help_button import HelpButton

def add_chapter(self, title: str, widget: QWidget, *, help_ref: str | None = None) -> None:
    # ... 现有标题 label 构建 ...
    header_layout = QHBoxLayout()  # 若现有实现已有 layout，直接复用
    header_layout.addWidget(title_label, 1)
    if help_ref:
        help_btn = HelpButton(help_ref, parent=self)
        header_layout.addWidget(help_btn, 0)
    # ... 现有 widget 加入 ...
```

**注意**：实际代码需根据 `add_chapter` 现有实现做最小侵入改造；如果原实现是用 `QVBoxLayout` 加单个 label 后直接 addWidget，需要先把 label 放入 QHBoxLayout，再整体放进 QVBoxLayout。

- [ ] **Step 3: 运行现有测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/ -v
```

预期：全部 pass（help_ref 默认 None 不会改变现有行为）。

- [ ] **Step 4: commit**

```bash
git add app/ui/pages/base_chapter_page.py
git commit -m "feat(help): add help_ref kwarg to base_chapter_page.add_chapter"
```

---

### Task 0.6: GUIDELINES.md 骨架

**Files:**
- Create: `docs/help/GUIDELINES.md`

- [ ] **Step 1: 写骨架文件**

文件：`docs/help/GUIDELINES.md`
```markdown
# 工程知识帮助系统 · 撰写规范

> 本文件 Stage 0 骨架 → Stage 1（蜗杆 pilot 结束时）完善 → Stage 7 终稿

## 1. 文件命名

- 术语：`docs/help/terms/<snake_case>.md`，例 `profile_shift.md`
- 模块章节概念文：`docs/help/modules/<module_key>/_section_<section_id>.md`
- 模块方法总览：`docs/help/modules/<module_key>/<snake_case_title>.md`
- `FieldSpec.help_ref` 格式：无 `.md` 后缀，例 `terms/profile_shift`

## 2. 术语文章模板（深度 2）

```markdown
# 术语名（符号）

**一句话**：xxx

**怎么理解**：2-3 段通俗解释

**公式**：（可选，纯文本公式）

**典型值**：范围 + 常见选择场景

**出处**：DIN/VDI/ISO 条款编号
```

## 3. section 概念文模板

```markdown
# 本章节是什么

## 为什么要填这些
## 输入 / 产出
## 方法差异（如有）
## 参考标准
```

## 4. 方法总览模板

```markdown
# 方法名（标准编号）

## 一图总览
## 解决什么问题
## 核心流程（3-5 步）
## 本模块实现的范围 / 不实现的范围
## 常见误用
## 参考文献
```

## 5. 文风约定

- 目标读者：工作 1-2 年机械工程师，懂基本力学，不熟 DIN/VDI 细节
- 避免："显然"、"容易看出"等假设读者已懂的措辞
- 公式：纯文本形式，如 `tan γ = z₁ / q`；不用 LaTeX
- 典型值：必须给"常用数值范围 + 选什么场景用什么"，不要只写单个数
- 出处：必须标 DIN/VDI/ISO 条款编号，无法确认时写"无公开权威出处"

## 6. 哪些字段需要 help_ref

**必须加（专业术语）**：
- 出现希腊字母的字段（γ、α、σ、β、φ...）
- 出现英文缩写或标准缩写的字段（KHbeta、KHalpha、Kv、KA...）
- 引用 DIN/VDI/ISO 条款的字段
- "变位系数"、"导程角"、"齿宽"等行业术语

**不必加**：
- 纯输入项目备注 / 描述字段
- "长度"、"温度"等通用物理量（单位已自解释）
- 只影响展示的开关字段

## 7. section subtitle 重写风格

**改前**：「定义本版标准边界和 Load Capacity 骨架状态。」
**改后**：「设置校核范围和选项：是否启用齿面 / 齿根负载能力校核、使用哪个计算方法。」

原则：
- 禁止使用"本版"、"骨架"、"最小子集"等开发内部语言
- 第一句话说"这一块在做什么"（动作 + 对象）
- 第二句话说"选项有哪些 / 影响什么"

## 8. 术语 Master List（Stage 1 填充）

_此节由 Stage 1.7 主会话扫描全项目后填充，列出 6 个模块所有候选术语及首次出现位置，用于后续模块优先复用。_

## 9. codex adversarial review 输入清单

主会话每次调用 codex-rescue 时提交：
- 当前 Stage 目标
- 改动文件清单 + git diff
- 本文件最新内容
- 要求检查维度（组件 / 内容 / 规范合规 / 未覆盖风险）
- 要求 P0/P1/P2 分级 + 禁止空评价
```

- [ ] **Step 2: commit**

```bash
git add docs/help/GUIDELINES.md
git commit -m "docs(help): add GUIDELINES skeleton for help content authoring"
```

---

### Task 0.7: Stage 0 最终 smoke + 验收

- [ ] **Step 1: 清除 pycache**

```bash
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 2: 全量测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

预期：全部 pass，无回归。

- [ ] **Step 3: 手动 smoke —— 启动 app 确认无异常**

```bash
python3 app/main.py
```

操作：打开每个模块页面，确认页面正常渲染（现阶段还没有 "?" 按钮出现）。关闭即可。

### Stage 0 完成判据
- [ ] HelpProvider + HelpPopover + HelpButton 三件套已创建
- [ ] 6 个 FieldSpec 都已加 help_ref 字段
- [ ] base_chapter_page.add_chapter 支持 help_ref 关键字参数
- [ ] theme.py 包含 HelpButton 样式
- [ ] docs/help/GUIDELINES.md 骨架已存在
- [ ] 新增 2 个测试文件全部通过
- [ ] 现有全量测试无回归
- [ ] 所有改动已通过至少 6 个 commit 推进

---

## Stage 0.5: codex adversarial review（Stage 0 基础设施）

**前置阅读**：spec §9

### Task 0.5.1: 准备 review 包

- [ ] **Step 1: 生成 Stage 0 改动 diff**

```bash
git log --oneline e0ad8fa..HEAD
git diff e0ad8fa..HEAD > /tmp/stage0-review.diff
wc -l /tmp/stage0-review.diff
```

（`e0ad8fa` 为 spec commit hash，用作 Stage 0 起点基线）

- [ ] **Step 2: 准备 review 提示词**

保存到 `/tmp/stage0-review-prompt.md`：
```markdown
你是一名严格的 adversarial code reviewer，目标是帮主会话找出 Stage 0 基础设施的所有漏洞。

**上下文**：
- spec: docs/superpowers/specs/2026-04-19-newbie-friendly-help-system-design.md
- 规范：docs/help/GUIDELINES.md

**Stage 0 目标**：实现 HelpProvider / HelpPopover / HelpButton + FieldSpec.help_ref + base_chapter_page.add_chapter(help_ref=None)。

**本次 review 的输入**：
（贴入 /tmp/stage0-review.diff 内容）

**review 维度**：
1. 组件接口：HelpProvider 的 ref 命名约定能否支持未来 modules/ 下的复杂路径？缓存策略是否存在内存泄漏风险？
2. 样式一致性：HelpButton QSS 是否与现有 AutoCalcCard / SubCard 视觉风格匹配？
3. 错误处理：HelpPopover 在连续点击多个 "?" 时的行为（是否重叠、是否内存泄漏）？
4. 测试覆盖：现有 3 个测试是否覆盖了（a）索引扫描（b）Markdown 解析（c）缓存命中（d）Provider 单例与多实例冲突（e）Popover 被外部点击关闭？
5. PyInstaller 兼容：`_default_root` 在 frozen 模式下路径推断是否正确？docs/help/ 是否需要加入 spec 文件中？
6. 命名一致性：help_ref / help_ref / help-ref 有没有混用？

**输出要求**：
- 禁止"looks good to me"或"no issues found"等空评价
- 至少列出 3 个潜在风险或改进点
- 每条问题标注 P0（必修）/ P1（建议修）/ P2（可选）
- 问题描述要具体到文件+行号+改动建议
```

### Task 0.5.2: 调用 codex:codex-rescue 执行 review

- [ ] **Step 1: Agent 调用**

使用 Agent 工具：
- `subagent_type`: `codex:codex-rescue`
- `description`: "Adversarial review Stage 0"
- `prompt`: 读 `/tmp/stage0-review-prompt.md` 内容 + 嵌入 diff

- [ ] **Step 2: 保存 review 输出**

保存 codex 返回到 `docs/reports/2026-04-19-stage0-adversarial-review.md`。

### Task 0.5.3: 分类并修复

- [ ] **Step 1: 整理 review 输出，列出所有 P0**
- [ ] **Step 2: 按 P0 清单逐个修复**，每修一个 commit 一次
- [ ] **Step 3: 如 P0 严重（≥3 条），二次调用 codex-rescue review 修复后的代码**
- [ ] **Step 4: P1 项酌情修复；P2 记入 backlog（`docs/reports/2026-04-19-stage0-adversarial-review.md` 末尾）**

### Task 0.5.4: Lessons 沉淀

- [ ] **Step 1: 更新 `.claude/lessons/ui-lessons.md`**

在文件末尾追加（如文件不存在则读现状；如果已有记录保留）：
```markdown
## 2026-04-19 HelpProvider/HelpPopover 组件设计

- **错误**: （填 review 发现的具体问题）
- **正确做法**: （填修复方案）
- **原因**: （填为什么）
```

- [ ] **Step 2: 更新 `.claude/lessons/review-lessons.md`**

记录本次 review 过程发现的 meta-pattern（如 codex 哪些维度挑不出问题、提示词需要加强的地方）。

- [ ] **Step 3: commit**

```bash
git add .claude/lessons/*.md docs/reports/2026-04-19-stage0-adversarial-review.md
git commit -m "docs(help): capture Stage 0 adversarial review lessons"
```

### Stage 0.5 完成判据
- [ ] codex adversarial review 已执行
- [ ] review 报告存为 `docs/reports/2026-04-19-stage0-adversarial-review.md`
- [ ] 所有 P0 问题已修复并测试通过
- [ ] `.claude/lessons/ui-lessons.md` 和 `.claude/lessons/review-lessons.md` 均有新条目

---

## Stage 1: 蜗杆 pilot + 规范固化（~1.5 天）

**前置阅读**：
- spec §6.3, §7, §8 Stage 1
- `docs/help/GUIDELINES.md`（Stage 0 骨架）
- `app/ui/pages/worm_gear_page.py` 全文

### Task 1.1: 扫描蜗杆字段，列出术语候选

- [ ] **Step 1: 列出所有 FieldSpec**

```bash
grep -n "FieldSpec(" app/ui/pages/worm_gear_page.py
```

- [ ] **Step 2: 手工分类每个字段**

创建临时工作文档 `/tmp/worm-fields-classification.md`：

| field_id | 是否专业术语 | 建议 help_ref |
|----------|-------------|--------------|
| meta.note | 否 | - |
| load_capacity.enabled | 否 | - |
| load_capacity.method | 是（涉及 Method A/B/C） | `modules/worm/din3996_method_b` |
| geometry.z1 | 否（简单概念）| - |
| geometry.module_mm | 是 | `terms/module` |
| geometry.diameter_factor_q | 是 | `terms/diameter_factor_q` |
| geometry.lead_angle_deg | 是 | `terms/lead_angle` |
| geometry.worm_face_width_mm | 否 | - |
| geometry.x1 | 是（变位系数）| `terms/profile_shift` |
| geometry.z2 | 否 | - |
| geometry.wheel_face_width_mm | 否 | - |
| geometry.x2 | 是 | `terms/profile_shift` |
| geometry.center_distance_mm | 否 | - |
| materials.worm_material | 否 | - |
| materials.wheel_material | 否 | - |
| materials.handedness | 否 | - |
| materials.lubrication | 是（术语）| `terms/lubrication` |
| materials.worm_e_mpa | 是 | `terms/elastic_modulus` |
| materials.worm_nu | 是 | `terms/poisson_ratio` |
| materials.wheel_e_mpa | 是 | `terms/elastic_modulus` |
| materials.wheel_nu | 是 | `terms/poisson_ratio` |
| operating.input_torque_nm | 否 | - |
| operating.speed_rpm | 否 | - |
| operating.application_factor | 是 | `terms/application_factor_ka` |
| operating.torque_ripple_percent | 否 | - |
| advanced.friction_override | 否 | - |
| advanced.normal_pressure_angle_deg | 是 | `terms/pressure_angle` |
| advanced.operating_temp_c | 否 | - |
| advanced.humidity_rh | 否 | - |
| load_capacity.allowable_contact_stress_mpa | 是 | `terms/allowable_contact_stress` |
| load_capacity.allowable_root_stress_mpa | 是 | `terms/allowable_root_stress` |
| load_capacity.dynamic_factor_kv | 是 | `terms/kv_factor` |
| load_capacity.transverse_load_factor_kha | 是 | `terms/kh_alpha` |
| load_capacity.face_load_factor_khb | 是 | `terms/kh_beta` |
| load_capacity.required_contact_safety | 否 | - |
| load_capacity.required_root_safety | 否 | - |

（表格是 Stage 1 的产出，以上为参考初稿；实际执行时根据 grep 输出严格对照。）

### Task 1.2: 编写蜗杆模块的 section 概念文（6 篇）

**Files:**
- Create: `docs/help/modules/worm/_section_basic.md`
- Create: `docs/help/modules/worm/_section_geometry.md`
- Create: `docs/help/modules/worm/_section_material.md`
- Create: `docs/help/modules/worm/_section_operating.md`
- Create: `docs/help/modules/worm/_section_advanced.md`
- Create: `docs/help/modules/worm/_section_load_capacity.md`

- [ ] **Step 1-6: 按模板逐一写 6 篇 section 概念文**

每篇遵循 GUIDELINES §3 模板。字数目标每篇 300-500 字。写作要点：
- 本章节在做什么（1 段）
- 为什么要填这些（1 段，说明对整体校核的作用）
- 输入 / 产出（列表）
- 方法差异（若有，如 Load Capacity 的 Method A/B/C）
- 参考标准（DIN/VDI 条款）

示例：`docs/help/modules/worm/_section_basic.md`
```markdown
# 基本设置章节

本章节用于**选择校核方法和范围**，决定后面要不要做齿面/齿根负载能力校核、用哪套算法。

## 为什么要填这些

蜗轮校核有两层：几何校核（必做，DIN 3975）和负载能力校核（可选，DIN 3996）。
小功率 / 短寿命场景可能只需几何校核；长寿命或高负载场景就必须开启负载能力校核。
这一步的选择会影响后续是否显示 Load Capacity 章节、是否要求填写许用应力等参数。

## 输入 / 产出

**输入**：
- 是否启用负载能力校核
- 选用哪个 DIN 3996 Method（A / B / C）

**产出**：
- 页面布局模式（是否展示 Load Capacity 章节）
- 计算流程分支

## 方法差异

DIN 3996 定义了 A/B/C 三种方法：
- **Method A**：详细数值法，按接触线逐段积分；需要蜗轮完整表面粗糙度、材料疲劳曲线等，数据需求高。
- **Method B**：解析简化法（推荐）；基于单点应力估算 + 经验因子；本模块当前实现。
- **Method C**：粗算法；用于初步方案比较。

本模块在"当前版本"仅 Method B 落地；选择 A/C 不会真正改变计算，仅作日志/导出标记。

## 参考标准

- DIN 3975-1:2017 蜗轮几何
- DIN 3996:2019 蜗轮负载能力
```

对剩余 5 个 section 用同样模板写。

- [ ] **Step 7: commit**

```bash
git add docs/help/modules/worm/_section_*.md
git commit -m "docs(help): add worm section concept articles"
```

### Task 1.3: 编写蜗杆模块的方法总览文

**Files:**
- Create: `docs/help/modules/worm/din3975_geometry_overview.md`
- Create: `docs/help/modules/worm/din3996_method_b.md`

- [ ] **Step 1: 写 `din3975_geometry_overview.md`**

按 GUIDELINES §4 模板（方法总览）撰写。内容要点：
- 一图总览：蜗杆（螺旋体）+ 蜗轮（齿轮）+ 中心距 a + 模数 m
- 解决什么问题：给定 z1/z2/m/q/x1/x2，求蜗杆蜗轮尺寸
- 核心流程（5 步）：输入几何参数 → 派生导程角 / 齿距 → 求蜗轮分度圆、齿顶圆、齿根圆 → 求中心距自洽 → 校核啮合条件
- 本模块范围：DIN 3975-1（几何）；不包括 DIN 3975-2（公差）
- 常见误用：q 和 d_1 的关系；变位系数 x1=x2=0 只是初始选择而非强制
- 参考：DIN 3975-1:2017

- [ ] **Step 2: 写 `din3996_method_b.md`**

按方法总览模板撰写。内容要点：
- 一图总览：输入扭矩 → 法向力分解 → 齿面/齿根应力 → 安全系数
- 解决什么问题：给定几何 + 材料 + 工况，判断能否承受长期运转
- 核心流程（5 步）：工况系数 KA → 动载 Kv / 齿向 KH → 齿面应力 σ_H → 齿根应力 σ_F → 安全系数比较
- 本模块范围：Method B 单点解析；输出安全系数与许用值比
- 不实现：Method A 积分法；实时磨损累积
- 常见误用：KH_alpha 与 KH_beta 混淆；许用应力选单向工况还是双向
- 参考：DIN 3996:2019 §5 Method B

- [ ] **Step 3: commit**

```bash
git add docs/help/modules/worm/din3975_geometry_overview.md docs/help/modules/worm/din3996_method_b.md
git commit -m "docs(help): add worm DIN 3975 / DIN 3996 Method B overviews"
```

### Task 1.4: 编写术语池首批（蜗杆用到）

**Files:**
- Create: `docs/help/terms/module.md`
- Create: `docs/help/terms/diameter_factor_q.md`
- Create: `docs/help/terms/lead_angle.md`
- Create: `docs/help/terms/profile_shift.md`
- Create: `docs/help/terms/lubrication.md`
- Create: `docs/help/terms/elastic_modulus.md`
- Create: `docs/help/terms/poisson_ratio.md`
- Create: `docs/help/terms/application_factor_ka.md`
- Create: `docs/help/terms/pressure_angle.md`
- Create: `docs/help/terms/allowable_contact_stress.md`
- Create: `docs/help/terms/allowable_root_stress.md`
- Create: `docs/help/terms/kv_factor.md`
- Create: `docs/help/terms/kh_alpha.md`
- Create: `docs/help/terms/kh_beta.md`

- [ ] **Step 1-14: 按模板写每个术语文章**

每篇遵循 GUIDELINES §2 模板。字数目标每篇 300-500 字。写作要点：
- 一句话解释（准确、新手易懂）
- 通俗解释（2-3 段，与工程场景挂钩）
- 公式（纯文本，如 `tan γ = z₁ / q`）
- 典型值 + 选择场景
- 出处

示例：`docs/help/terms/lead_angle.md`
```markdown
# 导程角（γ）

**一句话**：蜗杆每转一圈螺旋上升的角度，决定蜗杆"陡峭程度"与传动效率。

**怎么理解**：γ 越大，蜗杆越"陡"，推动蜗轮越省力，传动效率越高，但自锁能力下降；
γ 越小（< 5°），蜗杆接近"水平螺纹"，蜗轮几乎推不动蜗杆回转（自锁），适合需要防倒转的场景（电动窗帘、吊装提升机）。

**公式**：`tan γ = z₁ / q`

其中 `z₁` 为蜗杆头数，`q` 为直径系数。

**典型值**：
- 单头蜗杆（z₁=1）：γ 通常 3°–6°，常用于低速大传动比、要求自锁的场合
- 多头蜗杆（z₁=2–4）：γ 通常 15°–25°，用于中高速、非自锁、效率优先的传动

**出处**：DIN 3975-1:2017 §4.3（几何定义）
```

对其余 13 个术语用同样模板写。每写 3-4 个 commit 一次，避免单 commit 过大。

### Task 1.5: 填充 worm_gear_page.py 的 help_ref

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`

- [ ] **Step 1: 按 Task 1.1 的分类表填 FieldSpec 的 help_ref**

对每个"是专业术语"的字段，在 FieldSpec 构造里追加 `help_ref="..."` 参数。

示例：
```python
FieldSpec(
    "geometry.lead_angle_deg", "导程角 γ", "deg",
    hint="蜗杆一圈螺旋上升相对周长的角度，决定效率与自锁。",
    default="11.31",
    help_ref="terms/lead_angle",
)
```

- [ ] **Step 2: 找到 `add_chapter` 调用位置，加 help_ref**

```bash
grep -n "add_chapter\|self.add_chapter" app/ui/pages/worm_gear_page.py
```

给每个调用加 `help_ref="modules/worm/_section_<id>"`：

示例：
```python
self.add_chapter("基本设置", scroll, help_ref="modules/worm/_section_basic")
self.add_chapter("几何", scroll2, help_ref="modules/worm/_section_geometry")
# ... 类似对其他章节
```

（注：现有代码 Task 1.1 扫描时应确认章节 ID 和名字）

- [ ] **Step 3: 运行蜗杆页面测试**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_page.py -v
```

预期：所有测试 pass。

- [ ] **Step 4: 手动 smoke 蜗杆页面**

```bash
python3 app/main.py
```

打开蜗杆模块，确认：
- 每个 section 标题旁有 "?" 按钮
- 专业术语字段右侧有 "?" 按钮
- 点击后 Popover 弹出、正确显示 Markdown
- 点外部 / Esc 可关闭
- 点不同按钮时前一个 Popover 自动关闭

- [ ] **Step 5: commit**

```bash
git add app/ui/pages/worm_gear_page.py
git commit -m "feat(help): wire help_ref on all worm page terms and sections"
```

### Task 1.6: 重写蜗杆页面所有 section 的 subtitle

**Files:**
- Modify: `app/ui/pages/worm_gear_page.py`

- [ ] **Step 1: 找到所有 `_create_form_page(title, subtitle, ...)` 调用**

```bash
grep -n "_create_form_page\|subtitle=" app/ui/pages/worm_gear_page.py
```

- [ ] **Step 2: 按 GUIDELINES §7 改写 subtitle**

示例改动：
- 「定义本版标准边界和 Load Capacity 骨架状态。」
  → 「设置校核范围和选项：是否启用齿面/齿根负载能力校核、使用哪个计算方法。」
- 「保留材料牌号，同时显式暴露 Method B 最小子集所需的弹性参数。」
  → 「选择蜗杆/蜗轮材料。选中塑料蜗轮后会自动带入弹性模量和许用应力；也可手动覆盖。」

对所有 section 的 subtitle 做同样改写，涵盖所有蜗杆页面章节。

- [ ] **Step 3: smoke 确认视觉**

```bash
python3 app/main.py
```

打开蜗杆页，目视确认 subtitle 更易懂。

- [ ] **Step 4: commit**

```bash
git add app/ui/pages/worm_gear_page.py
git commit -m "refactor(worm-ui): rewrite section subtitles for newbie readability"
```

### Task 1.7: 扫描其他 5 模块 FieldSpec，建立候选术语 master list

- [ ] **Step 1: 列出所有其他 page 的 FieldSpec**

```bash
for f in bolt_page bolt_tapped_axial_page interference_fit_page hertz_contact_page spline_fit_page; do
  echo "=== $f ==="
  grep -n "FieldSpec(" app/ui/pages/${f}.py
done
```

- [ ] **Step 2: 手工构建候选术语清单**

写入 `docs/help/GUIDELINES.md` §8（Stage 0 骨架里预留的位置），格式：

```markdown
| 术语 | 首次出现模块 | 建议 help_ref | 优先级 |
|------|-------------|--------------|--------|
| 导程角 | worm | terms/lead_angle | 高 |
| 预紧力 | bolt_vdi | terms/preload_force | 高 |
| 屈服强度 | bolt_vdi, spline | terms/yield_strength | 高 |
| 接触应力 | hertz, interference | terms/contact_stress | 高 |
| ...  | | | |
```

（实际术语清单按扫描结果严谨填写，预计 30-50 个）

- [ ] **Step 3: commit**

```bash
git add docs/help/GUIDELINES.md
git commit -m "docs(help): populate term master list from 5-module scan"
```

### Task 1.8: 完善 GUIDELINES.md 定稿蜗杆版本

**Files:**
- Modify: `docs/help/GUIDELINES.md`

- [ ] **Step 1: 基于蜗杆 pilot 的实际落地，补充规范内容**

在 GUIDELINES.md 的各节（§1-§7）基础上，补充：
- §5 文风：新增 2-3 个蜗杆 pilot 中踩到的坑（如"避免用 x 代指变位系数时与无量纲符号 x 混淆"）
- §6 哪些字段加 help_ref：基于蜗杆实操经验补充具体判据
- §7 subtitle 风格：补充更多改前/改后示例

- [ ] **Step 2: commit**

```bash
git add docs/help/GUIDELINES.md
git commit -m "docs(help): refine GUIDELINES after worm pilot experience"
```

### Task 1.9: Stage 1 最终 smoke

- [ ] **Step 1: 全量测试**

```bash
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

预期：全 pass。

- [ ] **Step 2: 手动全页面 smoke**

```bash
python3 app/main.py
```

至少随机点 5 个术语 "?"、所有 section "?" 各 1 次，确认弹窗内容合理、布局无溢出。

### Stage 1 完成判据
- [ ] 蜗杆 page 所有"专业术语"字段都有 help_ref
- [ ] 蜗杆 page 所有 section 都有 section 级 help_ref
- [ ] 蜗杆 page 所有 section 的 subtitle 已重写
- [ ] 6 篇 section 概念文 + 2 篇方法总览 + 14 篇术语文章已写
- [ ] `docs/help/GUIDELINES.md` 蜗杆版补充完成
- [ ] 候选术语 master list 已填入 GUIDELINES §8
- [ ] 全量测试通过，手动 smoke 无问题

---

## Stage 1.5: codex adversarial review（蜗杆 pilot + 规范）

**前置阅读**：spec §9 / Stage 0.5 的 review prompt 结构

### Task 1.5.1: 准备 review 包

- [ ] **Step 1: 生成 Stage 1 diff**

```bash
git log --oneline <Stage 0.5 最后 commit>..HEAD
git diff <Stage 0.5 最后 commit>..HEAD > /tmp/stage1-review.diff
```

- [ ] **Step 2: 准备 adversarial prompt**

在 `/tmp/stage1-review-prompt.md` 里写：
```markdown
你是 adversarial reviewer。Stage 1 蜗杆 pilot 是后续 5 个模块的模板，请使劲挑刺。

**输入**：
- spec: docs/superpowers/specs/2026-04-19-newbie-friendly-help-system-design.md
- GUIDELINES: docs/help/GUIDELINES.md
- diff: 贴 /tmp/stage1-review.diff
- 所有 Markdown 内容: docs/help/modules/worm/*.md + docs/help/terms/*.md

**review 维度**：

1. **内容可懂性**：挑选 3 篇术语文，假装自己是工作 1 年的机械工程师，能否只读这一页就"懂"？具体指出哪几句话是开发者/专家视角而非新手视角。
2. **公式正确性**：蜗杆 tan γ = z₁ / q、DIN 3996 Method B 的应力公式（如有引用）都要比对原始 DIN 条款；如无法核实明确标注"无法验证"。
3. **典型值可信度**：每个术语的"典型值"范围是否合理？是否有 CN/DE 惯例差异？
4. **规范（GUIDELINES）可操作性**：后续 5 个模块的人/agent 完全按 GUIDELINES 能独立产出同等质量文章吗？哪些条款模糊？
5. **术语命名前瞻**：`terms/elastic_modulus`、`terms/profile_shift` 等名字在其他模块复用时会不会冲突？（如螺栓的"弹性模量"与蜗轮的"弹性模量"是否应合为一篇）
6. **help_ref 覆盖**：蜗杆页是否有遗漏的专业术语？是否有字段加了 help_ref 但其实不需要？
7. **subtitle 重写风格**：是否真的脱离了开发视角？还是只是改得更长？

**输出要求**：
- 禁止空评价；至少 5 条问题
- P0 / P1 / P2 优先级
- 问题 → 文件 → 行号 → 改动建议
```

### Task 1.5.2: 调用 codex:codex-rescue

- [ ] **Step 1: 执行 Agent**

`codex:codex-rescue` + 上面的 prompt + diff 内嵌

- [ ] **Step 2: 保存输出**到 `docs/reports/2026-04-19-stage1-adversarial-review.md`

### Task 1.5.3: 分类并修复

- [ ] **Step 1: 整理 review 输出，列出 P0 / P1 / P2**
- [ ] **Step 2: P0 全部修复**（每条 commit 一次）
- [ ] **Step 3: 若 P0 > 3 条，二次调用 review 验证修复**
- [ ] **Step 4: P1 评估后酌情修**

### Task 1.5.4: 新建 help-content-lessons.md + 更新其他 lessons

**Files:**
- Create: `.claude/lessons/help-content-lessons.md`
- Modify: `.claude/lessons/ui-lessons.md`
- Modify: `.claude/lessons/review-lessons.md`

- [ ] **Step 1: 新建 help-content-lessons.md**

文件：`.claude/lessons/help-content-lessons.md`
```markdown
# Help Content 撰写经验

## 2026-04-19 蜗杆 pilot 第一轮 adversarial review 收获

### [每条一个小节，例如]
- **错误**: 「典型值」只写单个数值，没有给场景判据
- **正确做法**: 「单头蜗杆：γ 3-6°，用于需要自锁；多头：γ 15-25°，用于效率优先」
- **原因**: 新手需要"怎么选"而不是"标准值是多少"

...（其他条目）
```

- [ ] **Step 2: 更新 ui-lessons.md、review-lessons.md**

记录本次的 UI / review 相关经验。

- [ ] **Step 3: commit**

```bash
git add .claude/lessons/*.md docs/reports/2026-04-19-stage1-adversarial-review.md
git commit -m "docs(help): capture Stage 1 lessons - pilot review findings"
```

### Stage 1.5 完成判据
- [ ] review 报告已存盘
- [ ] 所有 P0 修复完毕
- [ ] `.claude/lessons/help-content-lessons.md` 已创建且包含实质内容
- [ ] GUIDELINES 因 review 发现的问题做了同步修订
- [ ] 术语命名冲突 / 覆盖遗漏 / 文风偏差等前瞻性风险已处理

---

## 模块 Stage 执行模板（Stage 2-6 通用）

> Stage 2-6 每个模块都按下列 9 步模板执行。把 `<module>` 替换为具体模块键，`<MODULE_TITLE>` 为中文名。

### 执行模板（Template）

**前置阅读（每次新 session 必读）**：
- `.claude/lessons/help-content-lessons.md`
- `.claude/lessons/ui-lessons.md`
- `.claude/lessons/review-lessons.md`
- `docs/help/GUIDELINES.md`
- `app/ui/pages/<module>_page.py` 全文

**Step A: 扫描 FieldSpec 与章节**
```bash
grep -n "FieldSpec(\|add_chapter\|_create_form_page" app/ui/pages/<module>_page.py
```
填字段分类表（参考 Task 1.1）。

**Step B: 写 section 概念文**
按每个章节在 `docs/help/modules/<module>/_section_<id>.md` 写一篇（模板 GUIDELINES §3）。

**Step C: 写方法总览文（如有）**
模块若引用核心方法（VDI 2230、DIN 7190、赫兹接触理论等）则写一篇方法总览（模板 GUIDELINES §4）；小模块（interference/hertz）可能只需 1 篇。

**Step D: 增量写术语文章**
先查 `docs/help/terms/` 已有哪些；未存在的才新建。写作模板 GUIDELINES §2。

**Step E: 填 page.py 的 help_ref**
按字段分类表给每个 FieldSpec 加 `help_ref`，给 `add_chapter` 调用加 section 级 `help_ref`。

**Step F: 重写 subtitle**
所有 `_create_form_page(title, subtitle, ...)` 的 subtitle 按 GUIDELINES §7 改写。

**Step G: smoke**
```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_<module>_page.py -v
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
python3 app/main.py  # 手动 smoke
```

**Step H: 模块 commit**
```bash
git add app/ui/pages/<module>_page.py docs/help/modules/<module>/ docs/help/terms/
git commit -m "feat(help): newbie-friendly help on <module> page"
```

**Step I: codex adversarial review（子 Stage N.5）**
1. 生成 diff → `/tmp/stage<N>-review.diff`
2. 复用 Stage 1.5 的 prompt 模板（替换模块名 + review 维度）
3. 调用 `codex:codex-rescue` → 保存到 `docs/reports/2026-04-19-stage<N>-adversarial-review.md`
4. P0 修复（commit 一次一条）
5. 追加 lessons 到 `.claude/lessons/help-content-lessons.md`（**必须**写"无新 lesson"或有实质内容）
6. commit lessons

**Stage N 完成判据**（每个模块适用）：
- [ ] 模块 page 所有专业术语字段都有 help_ref
- [ ] 模块 page 所有 section 都有 section 级 help_ref
- [ ] 所有 section 的 subtitle 已重写
- [ ] 模块概念文 / 方法总览文已写
- [ ] 新增术语文章已写；已存在术语已复用
- [ ] codex adversarial review 完成，P0 全修
- [ ] lessons 更新（或明确标注"无新 lesson"）

---

## Stage 2: bolt_vdi（VDI 2230，~1 天）

**前置阅读**：模块 Stage 执行模板 + spec Stage 2-6 部分

- [ ] **应用模板 Step A**：扫描 `app/ui/pages/bolt_page.py`（对应 VDI 2230）
- [ ] **应用模板 Step B**：写 section 概念文。bolt_page 章节众多（阶段式），每个章节一篇；预计 ~8 篇
- [ ] **应用模板 Step C**：写 `docs/help/modules/bolt_vdi/vdi2230_overview.md` 方法总览
- [ ] **应用模板 Step D**：术语增量。VDI 2230 专有术语：`preload_force`（预紧力 Fm）、`tightening_factor_alpha_A`（拧紧系数 αA）、`thread_strip_safety`（螺纹脱扣安全）、`working_load_factor_phi_n`（载荷因数 ΦN）、`fatigue_goodman`（Goodman 疲劳）、`yield_strength`（屈服强度 Rp0.2）、`tensile_strength`（抗拉 Rm）、`friction_coefficient_mu_K`（头部摩擦）、`friction_coefficient_mu_G`（螺纹摩擦）、`clamped_parts_cylindrical_model`（夹紧体圆柱模型）等。预计新增 12-18 篇
- [ ] **应用模板 Step E**：填 bolt_page.py 的 help_ref
- [ ] **应用模板 Step F**：重写 subtitle
- [ ] **应用模板 Step G**：smoke
- [ ] **应用模板 Step H**：commit
- [ ] **应用模板 Step I**：codex adversarial review + lessons

---

## Stage 3: bolt_tapped_axial（~0.8 天）

- [ ] **应用模板 Step A**：扫描 `app/ui/pages/bolt_tapped_axial_page.py`
- [ ] **应用模板 Step B**：写 section 概念文
- [ ] **应用模板 Step C**：方法总览 `docs/help/modules/bolt_tapped_axial/iso898_overview.md`
- [ ] **应用模板 Step D**：术语增量。与 VDI 2230 共享大量术语（预紧力、屈服、疲劳），只需补 tapped joint 特有的：`effective_thread_engagement`（有效螺纹啮合 m_eff）、`axial_stress_alternating`（轴向交变应力 σ_ax）、`thread_strip_not_checked`（脱扣未校核状态）等。预计新增 5-8 篇
- [ ] **应用模板 Step E**：填 help_ref
- [ ] **应用模板 Step F**：重写 subtitle
- [ ] **应用模板 Step G**：smoke
- [ ] **应用模板 Step H**：commit
- [ ] **应用模板 Step I**：codex adversarial review + lessons

---

## Stage 4: interference（DIN 7190 过盈配合，~0.8 天）

- [ ] **应用模板 Step A**：扫描 `app/ui/pages/interference_fit_page.py`
- [ ] **应用模板 Step B**：写 section 概念文
- [ ] **应用模板 Step C**：`docs/help/modules/interference/din7190_overview.md`
- [ ] **应用模板 Step D**：特有术语：`interference_amount`（过盈量 Δ）、`radial_contact_pressure`（径向接触压力 p）、`press_in_force`（压入力 F_press）、`fretting_risk`（微动疲劳）、`hollow_shaft_coefficient`（空心轴系数 Q）、`surface_roughness_derating`（表面粗糙度折减）。预计新增 6-10 篇
- [ ] **应用模板 Step E-I**：同模板

---

## Stage 5: hertz（赫兹接触，~0.8 天）

- [ ] **应用模板 Step A**：扫描 `app/ui/pages/hertz_contact_page.py`
- [ ] **应用模板 Step B**：写 section 概念文
- [ ] **应用模板 Step C**：`docs/help/modules/hertz/hertz_contact_theory.md`
- [ ] **应用模板 Step D**：特有术语：`equivalent_elastic_modulus`（等效 E*）、`contact_type_point_line`（点接触 / 线接触）、`max_contact_pressure`（最大接触压力 p_max）、`contact_area_ellipse`（接触椭圆）、`shear_stress_depth`（最大剪应力深度）。预计新增 4-8 篇
- [ ] **应用模板 Step E-I**：同模板

---

## Stage 6: spline（DIN 5480 花键，~0.8 天）

- [ ] **应用模板 Step A**：扫描 `app/ui/pages/spline_fit_page.py`
- [ ] **应用模板 Step B**：写 section 概念文
- [ ] **应用模板 Step C**：`docs/help/modules/spline/din5480_overview.md` + `din6892_overview.md`
- [ ] **应用模板 Step D**：特有术语：`flank_load_factor`（齿面载荷系数）、`torque_capacity_sf`（扭矩容量安全系数）、`k_alpha_combined`（合成系数 kα）、`catalog_vs_drawing_mode`（catalog 模式 vs 图纸模式）、`h_w_effective_engagement_height`（有效啮合高度）。预计新增 5-8 篇
- [ ] **应用模板 Step E-I**：同模板

---

## Stage 7: 终审（~0.5 天）

**前置阅读**：spec §8 Stage 7 + 所有 lessons 文件

### Task 7.1: 跨模块术语一致性扫描

- [ ] **Step 1: 列出所有 terms/*.md**

```bash
ls docs/help/terms/*.md | wc -l
ls docs/help/terms/*.md
```

- [ ] **Step 2: 扫概念重叠**

对每对可能重叠的术语手工比对。例如：
- `elastic_modulus` vs 各模块是否引用 → 应只有一个文件
- `yield_strength` 是否跨 bolt / spline 共用
- `friction_coefficient_*` 多个变体是否真的必要

若发现重复，合并并 grep 更新所有引用点。

### Task 7.2: 死链扫描

- [ ] **Step 1: 收集所有 help_ref 值**

```bash
grep -rh "help_ref=" app/ui/pages/ | grep -oE 'help_ref="[^"]+"' | sort -u > /tmp/all-help-refs.txt
```

- [ ] **Step 2: 对照每个 ref 验证 md 文件存在**

```bash
while read -r line; do
  ref=$(echo "$line" | sed 's/help_ref="//;s/"//')
  path="docs/help/${ref}.md"
  if [ ! -f "$path" ]; then
    echo "缺失: $ref → $path"
  fi
done < /tmp/all-help-refs.txt
```

预期：无输出（所有 ref 都有对应 md）。

- [ ] **Step 3: 找出未被引用的孤立 md**

```bash
for md in $(find docs/help/terms docs/help/modules -name "*.md"); do
  ref="${md#docs/help/}"
  ref="${ref%.md}"
  if ! grep -q "help_ref=\"${ref}\"" app/ui/pages/*.py; then
    echo "未引用: $ref"
  fi
done
```

孤立 md 可能是 section 级的 _section_*（这类会被 add_chapter 引用，需另查）。逐个人工判断；真正孤立的删除或记为"后续文档用"。

### Task 7.3: 全量 UI smoke

- [ ] **Step 1: 每模块随机 10 个 "?"**

```bash
python3 app/main.py
```

6 个模块 × 每个随机 10 次点击 = 60 次弹窗验证。重点看：
- Popover 位置不溢出屏幕
- Markdown 渲染正确（标题、列表、行内代码）
- 关闭机制工作
- 视觉对齐不崩

- [ ] **Step 2: 全量 pytest**

```bash
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

预期：全 pass。

### Task 7.4: GUIDELINES.md 终稿

- [ ] **Step 1: 通读 GUIDELINES.md 并按 Stage 2-6 经验补充**

重点补充：
- 术语命名冲突处理规则（以先来者为准 or 统一合并）
- 每个模块的术语增量规模经验（用于估算新模块）
- Popover 对齐视觉最佳实践
- codex adversarial review prompt 的迭代版本

- [ ] **Step 2: 在开头标注"终稿，2026-XX-XX"**

- [ ] **Step 3: commit**

```bash
git add docs/help/GUIDELINES.md
git commit -m "docs(help): GUIDELINES.md final version after 6 modules"
```

### Task 7.5: Stage 7 report

**Files:**
- Create: `docs/reports/2026-04-XX-newbie-friendly-help-system-summary.md`

- [ ] **Step 1: 写总结报告**

内容大纲：
- 7 个 Stage 的实际工时 vs 估时
- 总术语数、总概念文数、总行 Markdown
- 7 次 codex adversarial review 的 P0 问题共多少条
- 最有价值的 3 条 lessons
- 遗留 P1/P2 backlog 列表

- [ ] **Step 2: commit**

```bash
git add docs/reports/2026-04-XX-newbie-friendly-help-system-summary.md
git commit -m "docs(help): add implementation summary report"
```

### Stage 7 完成判据
- [ ] 无死链
- [ ] 无跨模块术语冲突
- [ ] 全量 UI smoke 无异常
- [ ] pytest 全绿
- [ ] GUIDELINES.md 标注终稿
- [ ] 总结报告已提交

---

## 总体成功判据（对照 spec §13）

- [ ] 6 个模块 UI 上所有"专业术语"字段旁都有 "?" 按钮
- [ ] 6 个模块每个 section 的 subtitle 已重写为新手风格
- [ ] 6 个模块每个 section 旁都有 section 级 "?"
- [ ] `docs/help/` 目录结构完整，无死链
- [ ] `docs/help/GUIDELINES.md` 定稿
- [ ] 测试套件全绿（含新增 help 测试）
- [ ] 7 次 codex adversarial review 留痕于 `docs/reports/`
- [ ] `.claude/lessons/{ui,review,help-content}-lessons.md` 均有实质内容

---

## 附：commit message 风格参考

沿用项目习惯（见 `git log --oneline`）：
- `feat(help): ...` —— 新功能
- `docs(help): ...` —— 纯文档
- `fix(help): ...` —— bug 修复
- `refactor(<module>-ui): ...` —— 既有模块的 UI 重构（如 subtitle 改写）
- `test(help): ...` —— 仅测试变更

Co-Authored-By 行保留项目已有的 `Claude Opus 4.7 <noreply@anthropic.com>`。
