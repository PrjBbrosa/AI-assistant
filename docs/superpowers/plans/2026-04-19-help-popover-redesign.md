# Help Popover Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current fixed-size frameless help popover with a polished floating card that supports resize, drag, pin, rich markdown styling, category badge and source footer — matching the approved mockup at `docs/help_popover_mockup.html`.

**Architecture:** Keep the existing `HelpPopover` as the single entry point. Extend `HelpEntry` with `category` and `source`. Rebuild the popover layout with header (category + title + pin + close) / body (QTextBrowser with document CSS) / footer (source) / QSizeGrip. Persist size via QSettings. All styles live in `app/ui/theme.py` via objectName selectors.

**Tech Stack:** PySide6 (Qt6) · QDialog + `Qt.Tool` + `Qt.FramelessWindowHint` · QTextBrowser document CSS · QGraphicsDropShadowEffect · QPropertyAnimation · QSettings · pytest (`QT_QPA_PLATFORM=offscreen`).

---

## File Structure

**Modify:**
- `app/ui/help_provider.py` — extend `HelpEntry` with `category`/`source`, add category inference, strip source line during parse
- `app/ui/widgets/help_popover.py` — full rebuild of layout; preserve public API (`show_for`, `title_text`, `body_markdown`)
- `app/ui/theme.py` — add QSS for new objectNames
- `tests/fixtures/help/terms/_sample.md` — unchanged, already has `**出处**：` line we can exercise

**Create:**
- `tests/ui/test_help_popover_chrome.py` — new tests for resize/drag/pin/category/source/CSS
- `tests/ui/test_help_provider_category_source.py` — new tests for parser extensions

**Keep unchanged:**
- `app/ui/widgets/help_button.py` (the `?` button and its callsite signature)
- All `*_help_wiring.py` tests
- All help-content markdown under `docs/help/`

---

## Task 1: Extend `HelpEntry` with category and source fields

**Files:**
- Modify: `app/ui/help_provider.py`
- Test: `tests/ui/test_help_provider_category_source.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/ui/test_help_provider_category_source.py`:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest

from app.ui.help_provider import HelpEntry, HelpProvider, _parse, infer_category


def test_help_entry_defaults_category_source_to_none():
    entry = HelpEntry(title="T", body_md="B")
    assert entry.category is None
    assert entry.source is None


def test_parse_extracts_source_from_trailing_line():
    md = (
        "# 示例\n\n"
        "**一句话**：测试。\n\n"
        "正文。\n\n"
        "**出处**：GB/T 228.1-2010\n"
    )
    entry = _parse(md, "terms/x")
    assert entry.title == "示例"
    assert entry.source == "GB/T 228.1-2010"
    assert "**出处**" not in entry.body_md
    assert entry.body_md.endswith("正文。")


def test_parse_source_missing_leaves_none():
    md = "# 示例\n\n正文，没有出处。\n"
    entry = _parse(md, "terms/x")
    assert entry.source is None
    assert "正文" in entry.body_md


def test_parse_source_variants_cn_and_en():
    for line in ("**出处**：A", "出处：A", "**Source**: A", "Source: A"):
        md = f"# T\n\n正文。\n\n{line}\n"
        entry = _parse(md, "ref")
        assert entry.source == "A", f"failed for: {line}"


def test_infer_category_from_ref_prefixes():
    cases = {
        "terms/bolt_yield_strength": "螺栓 · 术语",
        "terms/interference_fit": "过盈 · 术语",
        "terms/hertz_pressure": "赫兹 · 术语",
        "terms/spline_pitch": "花键 · 术语",
        "terms/worm_lead_angle": "蜗轮 · 术语",
        "terms/unknown_topic": "通用 · 术语",
        "modules/bolt_vdi/chapter1": "螺栓 · 章节",
        "modules/bolt_tapped_axial/chapter1": "螺纹连接 · 章节",
        "modules/hertz/chapter1": "赫兹 · 章节",
        "modules/interference/chapter1": "过盈 · 章节",
        "modules/spline/chapter1": "花键 · 章节",
        "modules/worm/chapter1": "蜗轮 · 章节",
    }
    for ref, expected in cases.items():
        assert infer_category(ref) == expected, f"failed for ref={ref}"


def test_provider_get_populates_category_from_ref(tmp_path):
    (tmp_path / "terms").mkdir()
    (tmp_path / "terms" / "bolt_xx.md").write_text(
        "# 示例\n\n正文。\n\n**出处**：internal\n", encoding="utf-8"
    )
    provider = HelpProvider(root=tmp_path)
    entry = provider.get("terms/bolt_xx")
    assert entry.category == "螺栓 · 术语"
    assert entry.source == "internal"
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_provider_category_source.py -v
```

Expected: all FAIL (ImportError on `infer_category`; `HelpEntry` signature mismatch).

- [ ] **Step 3: Implement the extensions**

Rewrite `app/ui/help_provider.py`:

```python
"""Markdown 帮助内容的索引与加载。"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class HelpEntry:
    title: str
    body_md: str
    category: Optional[str] = None
    source: Optional[str] = None


def _default_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "docs" / "help"
    return Path(__file__).resolve().parents[2] / "docs" / "help"


# 用于 category 推断的两级映射
_MODULE_CATEGORY: Dict[str, str] = {
    "bolt_vdi": "螺栓 · 章节",
    "bolt_tapped_axial": "螺纹连接 · 章节",
    "hertz": "赫兹 · 章节",
    "interference": "过盈 · 章节",
    "spline": "花键 · 章节",
    "worm": "蜗轮 · 章节",
}

_TERM_PREFIX_CATEGORY: Dict[str, str] = {
    "bolt_": "螺栓 · 术语",
    "interference_": "过盈 · 术语",
    "hertz_": "赫兹 · 术语",
    "spline_": "花键 · 术语",
    "worm_": "蜗轮 · 术语",
}


def infer_category(ref: str) -> Optional[str]:
    """按 ref 路径推断所属模块/类别。"""
    parts = ref.split("/")
    if len(parts) >= 2 and parts[0] == "modules":
        return _MODULE_CATEGORY.get(parts[1])
    if len(parts) == 2 and parts[0] == "terms":
        name = parts[1]
        for prefix, cat in _TERM_PREFIX_CATEGORY.items():
            if name.startswith(prefix):
                return cat
        return "通用 · 术语"
    return None


# 匹配 "**出处**：...", "出处：...", "**Source**: ...", "Source: ..."
_SOURCE_RE = re.compile(
    r"^\s*(?:\*\*)?(?:出处|Source)(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
)


def _extract_source(lines: list[str]) -> tuple[list[str], Optional[str]]:
    """从 body 末尾剥离出处行；返回 (剩余行, 出处文本或 None)。"""
    # 从末尾向上找第一个非空行；若匹配 source 模式则剥离
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        m = _SOURCE_RE.match(stripped)
        if m:
            # 剥离这一行及其后的空行
            return lines[:i], m.group(1).strip()
        break
    return lines, None


def _parse(md_text: str, ref: str) -> HelpEntry:
    lines = md_text.splitlines()
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break
    body_lines = lines[body_start:]
    body_lines, source = _extract_source(body_lines)
    body = "\n".join(body_lines).strip()
    if not title:
        title = f"(无标题) {ref}"
    return HelpEntry(
        title=title,
        body_md=body,
        category=infer_category(ref),
        source=source,
    )


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
                category=infer_category(ref),
                source=None,
            )
        else:
            text = path.read_text(encoding="utf-8")
            entry = _parse(text, ref)
        self._cache[ref] = entry
        return entry
```

- [ ] **Step 4: Run new tests + existing provider tests, verify all pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_provider_category_source.py tests/ui/test_help_provider.py -v
```

Expected: all PASS. The existing `test_help_provider.py` must still pass (adding optional fields with defaults is backward-compatible).

- [ ] **Step 5: Commit**

```bash
git add app/ui/help_provider.py tests/ui/test_help_provider_category_source.py
git commit -m "feat(help): extend HelpEntry with category and source"
```

---

## Task 2: Add theme QSS for popover chrome

**Files:**
- Modify: `app/ui/theme.py`
- Test: deferred to Task 3 (visual styles are exercised by widget construction tests)

- [ ] **Step 1: Locate the theme stylesheet** — `app/ui/theme.py`. Find the block that currently contains `QToolButton#HelpButton { ... }` (around line 317). New rules go immediately after that block.

- [ ] **Step 2: Insert the new QSS block**

Append these rules to the stylesheet string in `theme.py`, after the existing `QToolButton#HelpButton` rules:

```css
/* ===== HelpPopover ===== */
QFrame#HelpPopoverRoot {
    background: #FFFFFF;
    border: 1px solid #F0ECE4;
    border-radius: 14px;
}
QFrame#HelpPopoverHeader {
    background: #FFFDFB;
    border-bottom: 1px solid #F0ECE4;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}
QFrame#HelpPopoverFooter {
    background: #FBF8F4;
    border-top: 1px solid #F0ECE4;
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
}
QLabel#HelpPopoverCategory {
    color: #D97757;
    background: #FAF1EC;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
}
QLabel#HelpPopoverTitle {
    color: #2F2E2C;
    font-size: 15px;
    font-weight: 600;
}
QLabel#HelpPopoverSource {
    color: #8A8782;
    font-size: 11px;
}
QToolButton#HelpPopoverIconBtn {
    background: transparent;
    border: none;
    color: #8A8782;
    padding: 4px;
    border-radius: 6px;
}
QToolButton#HelpPopoverIconBtn:hover {
    background: #F0ECE4;
    color: #2F2E2C;
}
QToolButton#HelpPopoverIconBtn[pinned="true"] {
    background: #FAF1EC;
    color: #D97757;
}
QTextBrowser#HelpPopoverBody {
    background: #FFFFFF;
    border: none;
    padding: 4px 6px;
}
```

- [ ] **Step 3: Commit the theme change alone**

```bash
git add app/ui/theme.py
git commit -m "feat(theme): add QSS for HelpPopover chrome"
```

This keeps the diff reviewable. Task 3 will exercise these selectors.

---

## Task 3: Rebuild `HelpPopover` layout — header/body/footer/sizegrip

**Files:**
- Modify: `app/ui/widgets/help_popover.py`
- Test: `tests/ui/test_help_popover_chrome.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/ui/test_help_popover_chrome.py`:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QSizeGrip, QTextBrowser, QLabel

from app.ui.help_provider import HelpProvider
from app.ui.widgets.help_popover import HelpPopover


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def fixture_help_provider():
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "help"
    original = HelpProvider._instance
    HelpProvider._instance = HelpProvider(root=fixture_root)
    try:
        yield HelpProvider._instance
    finally:
        HelpProvider._instance = original


def test_popover_has_named_chrome_widgets(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    # Root frame + header + footer + body all exist with expected objectNames
    assert popover.findChild(QWidget, "HelpPopoverRoot") is not None
    assert popover.findChild(QWidget, "HelpPopoverHeader") is not None
    assert popover.findChild(QWidget, "HelpPopoverFooter") is not None
    body = popover.findChild(QTextBrowser, "HelpPopoverBody")
    assert body is not None
    popover.close()


def test_popover_has_size_grip_for_resizing(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.findChild(QSizeGrip) is not None
    popover.close()


def test_popover_default_size_is_520_640(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.size().width() == 520
    assert popover.size().height() == 640
    popover.close()


def test_popover_minimum_size(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.minimumWidth() == 380
    assert popover.minimumHeight() == 320
    popover.close()


def test_popover_shows_category_and_source_when_available(app, fixture_help_provider):
    # _sample.md has "**出处**：internal fixture" → source visible, category from ref
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    cat = popover.findChild(QLabel, "HelpPopoverCategory")
    src = popover.findChild(QLabel, "HelpPopoverSource")
    assert cat is not None and cat.isVisible()
    assert cat.text() == "通用 · 术语"  # _sample has no known prefix
    assert src is not None and src.isVisible()
    assert "internal fixture" in src.text()
    popover.close()


def test_popover_hides_category_and_footer_when_missing(app):
    # A missing ref has no source; its category falls back based on ref path
    anchor = QWidget()
    popover = HelpPopover.show_for("missing/ref_totally_unknown", anchor=anchor)
    cat = popover.findChild(QLabel, "HelpPopoverCategory")
    src_label = popover.findChild(QLabel, "HelpPopoverSource")
    footer = popover.findChild(QWidget, "HelpPopoverFooter")
    # No category can be inferred for "missing/" prefix → hidden
    assert cat is not None and not cat.isVisible()
    # No source → footer hidden
    assert footer is not None and not footer.isVisible()
    popover.close()


def test_popover_preserves_public_api(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert "示例术语" in popover.title_text()
    assert "仅供自测" in popover.body_markdown()
    popover.close()
```

- [ ] **Step 2: Run the failing tests**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover_chrome.py -v
```

Expected: all FAIL (no new widgets yet).

- [ ] **Step 3: Rewrite `help_popover.py`**

Replace the full contents of `app/ui/widgets/help_popover.py` with:

```python
"""Markdown 帮助内容的弹出窗口。"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QKeyEvent, QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizeGrip,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.help_provider import HelpEntry, HelpProvider


_DOC_CSS = """
h2 { color: #2F2E2C; font-size: 14px; margin-top: 18px; margin-bottom: 8px; }
h3 { color: #2F2E2C; font-size: 13px; margin-top: 14px; margin-bottom: 6px; }
p  { color: #2F2E2C; margin: 0 0 10px 0; }
code { background: #F4EFE8; color: #8A4A2E; padding: 1px 4px; }
pre { background: #FAF7F4; border-left: 3px solid #D97757; padding: 8px 10px; }
table { border: 1px solid #E6E1DA; }
th { background: #FAF1EC; color: #2F2E2C; padding: 4px 8px; border: 1px solid #E6E1DA; }
td { padding: 4px 8px; border: 1px solid #F0ECE4; }
blockquote { background: #FBF8F4; color: #5F5E5B; border-left: 3px solid #8A8782;
             padding: 6px 10px; margin: 0 0 10px 0; }
ul, ol { margin: 0 0 10px 18px; }
"""


def _anchor_is_valid(widget: Optional[QWidget]) -> bool:
    if widget is None:
        return False
    try:
        _ = widget.objectName()
        return True
    except RuntimeError:
        return False


class _HeaderFrame(QFrame):
    """头部栏：承担拖动窗口的职责。"""

    def __init__(self, parent: "HelpPopover") -> None:
        super().__init__(parent)
        self._popover = parent
        self._drag_offset: Optional[QPoint] = None
        self.setObjectName("HelpPopoverHeader")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._popover.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self._popover.move(new_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None:
            self._drag_offset = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class HelpPopover(QDialog):
    """精致悬浮卡片：可缩放、可拖动、带分类与出处。"""

    _current: Optional["HelpPopover"] = None
    _DEFAULT_SIZE = QSize(520, 640)
    _MIN_SIZE = QSize(380, 320)

    def __init__(
        self,
        entry: HelpEntry,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(False)
        self.setMinimumSize(self._MIN_SIZE)
        self.resize(self._DEFAULT_SIZE)

        # 外层 root frame（承载圆角 + 阴影）
        self._root = QFrame(self)
        self._root.setObjectName("HelpPopoverRoot")

        shadow = QGraphicsDropShadowEffect(self._root)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.black)
        self._root.setGraphicsEffect(shadow)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 14)
        root_layout.addWidget(self._root)

        # ----- Header -----
        self._header = _HeaderFrame(self)
        self._category_label = QLabel()
        self._category_label.setObjectName("HelpPopoverCategory")
        self._title_label = QLabel()
        self._title_label.setObjectName("HelpPopoverTitle")
        self._title_label.setWordWrap(True)

        self._pin_btn = QToolButton()
        self._pin_btn.setObjectName("HelpPopoverIconBtn")
        self._pin_btn.setText("📌")
        self._pin_btn.setCheckable(True)
        self._pin_btn.setCursor(Qt.PointingHandCursor)
        self._pin_btn.setToolTip("固定：禁止点外面关闭")
        self._pin_btn.toggled.connect(self._on_pin_toggled)

        close_btn = QToolButton()
        close_btn.setObjectName("HelpPopoverIconBtn")
        close_btn.setText("×")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("关闭 (Esc)")
        close_btn.clicked.connect(self.close)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(4)
        cat_row = QHBoxLayout()
        cat_row.setContentsMargins(0, 0, 0, 0)
        cat_row.addWidget(self._category_label)
        cat_row.addStretch(1)
        title_col.addLayout(cat_row)
        title_col.addWidget(self._title_label)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(18, 12, 12, 12)
        header_layout.setSpacing(8)
        header_layout.addLayout(title_col, 1)
        header_layout.addWidget(self._pin_btn)
        header_layout.addWidget(close_btn)

        # ----- Body -----
        self._browser = QTextBrowser()
        self._browser.setObjectName("HelpPopoverBody")
        self._browser.setOpenExternalLinks(True)
        self._browser.document().setDefaultStyleSheet(_DOC_CSS)

        # ----- Footer -----
        self._footer = QFrame()
        self._footer.setObjectName("HelpPopoverFooter")
        self._source_label = QLabel()
        self._source_label.setObjectName("HelpPopoverSource")
        self._source_label.setWordWrap(True)
        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(18, 8, 18, 10)
        prefix = QLabel("出处：")
        prefix.setObjectName("HelpPopoverSource")
        footer_layout.addWidget(prefix)
        footer_layout.addWidget(self._source_label, 1)
        # SizeGrip 放在 footer 右端
        self._size_grip = QSizeGrip(self._footer)
        footer_layout.addWidget(self._size_grip, 0, Qt.AlignRight | Qt.AlignBottom)

        # ----- Assemble root -----
        inner = QVBoxLayout(self._root)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)
        inner.addWidget(self._header)
        inner.addWidget(self._browser, 1)
        inner.addWidget(self._footer)

        self._apply_entry(entry)

    def _apply_entry(self, entry: HelpEntry) -> None:
        self._title_label.setText(entry.title)
        if entry.category:
            self._category_label.setText(entry.category)
            self._category_label.setVisible(True)
        else:
            self._category_label.setVisible(False)
        self._browser.setMarkdown(entry.body_md)
        if entry.source:
            self._source_label.setText(entry.source)
            self._footer.setVisible(True)
        else:
            self._footer.setVisible(False)

    def _on_pin_toggled(self, checked: bool) -> None:
        self._pin_btn.setProperty("pinned", "true" if checked else "false")
        # 刷新 QSS 属性选择器
        self._pin_btn.style().unpolish(self._pin_btn)
        self._pin_btn.style().polish(self._pin_btn)
        self._pin_btn.setToolTip(
            "已固定：点击取消" if checked else "固定：禁止点外面关闭"
        )

    def is_pinned(self) -> bool:
        return self._pin_btn.isChecked()

    @classmethod
    def show_for(
        cls,
        help_ref: str,
        anchor: QWidget,
    ) -> "HelpPopover":
        try:
            if cls._current is not None and cls._current.isVisible():
                cls._current.close()
        except RuntimeError:
            pass
        cls._current = None

        entry = HelpProvider.instance().get(help_ref)
        anchor_valid = _anchor_is_valid(anchor)
        parent_widget: Optional[QWidget] = anchor.window() if anchor_valid else None
        popover = cls(entry=entry, parent=parent_widget)
        cls._current = popover

        w, h = popover.width(), popover.height()
        if anchor_valid:
            anchor_rect = anchor.rect()
            top_left_global = anchor.mapToGlobal(
                QPoint(anchor_rect.right(), anchor_rect.bottom())
            )
            target = top_left_global + QPoint(8, 8)
            screen_geom = anchor.screen().availableGeometry()
        else:
            target = QCursor.pos() + QPoint(8, 8)
            primary = QApplication.primaryScreen()
            screen_geom = (
                primary.availableGeometry() if primary is not None
                else QRect(0, 0, 1920, 1080)
            )

        if target.x() + w > screen_geom.right():
            target.setX(screen_geom.right() - w - 8)
        if target.y() + h > screen_geom.bottom():
            target.setY(screen_geom.bottom() - h - 8)

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

- [ ] **Step 4: Run the new chrome tests + existing popover tests**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover_chrome.py tests/ui/test_help_popover.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full ui test suite to catch regressions**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/ -v
```

Expected: everything green. If `test_bolt_help_wiring.py` or similar breaks due to API change, check whether the wiring tests import `HelpPopover` directly — they should only touch `HelpButton`.

- [ ] **Step 6: Commit**

```bash
git add app/ui/widgets/help_popover.py tests/ui/test_help_popover_chrome.py
git commit -m "feat(help): rebuild HelpPopover with chrome, pin, sizegrip"
```

---

## Task 4: Persist popover size across sessions

**Files:**
- Modify: `app/ui/widgets/help_popover.py`
- Test: extend `tests/ui/test_help_popover_chrome.py`

- [ ] **Step 1: Add an autouse QSettings-isolation fixture** at the top of `tests/ui/test_help_popover_chrome.py` (after the existing `fixture_help_provider`). This guarantees every test in this file uses a tmp settings file, including the earlier default-size test from Task 3:

```python
from PySide6.QtCore import QSettings, QSize


@pytest.fixture(autouse=True)
def _isolate_popover_settings(tmp_path, monkeypatch):
    """Every test in this file gets a fresh QSettings file."""
    path = tmp_path / "help_popover_settings.ini"
    monkeypatch.setattr(
        "app.ui.widgets.help_popover._settings",
        lambda: QSettings(str(path), QSettings.IniFormat),
    )
    yield
```

- [ ] **Step 2: Write the failing persistence tests**

Append to `tests/ui/test_help_popover_chrome.py`:

```python
def test_popover_size_is_persisted_via_qsettings(app, fixture_help_provider):
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    popover.resize(612, 700)
    popover.close()  # save on close

    popover2 = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover2.size() == QSize(612, 700)
    popover2.close()


def test_popover_first_open_uses_default_size(app, fixture_help_provider):
    # autouse fixture gives us a pristine settings file
    anchor = QWidget()
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.size() == QSize(520, 640)
    popover.close()
```

- [ ] **Step 3: Run failing tests**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover_chrome.py -v -k persist
```

Expected: FAIL (no `_settings` attr yet).

- [ ] **Step 4: Add settings helper and wire it**

In `app/ui/widgets/help_popover.py`:

Add near the top, after the `_DOC_CSS` constant:

```python
from PySide6.QtCore import QSettings

_SIZE_KEY = "help_popover/size"


def _settings() -> QSettings:
    return QSettings("AI-assistant", "help_popover")
```

In `HelpPopover.__init__`, after `self.resize(self._DEFAULT_SIZE)`:

```python
        saved = _settings().value(_SIZE_KEY)
        if isinstance(saved, QSize) and saved.isValid():
            # clamp to min
            w = max(self._MIN_SIZE.width(), saved.width())
            h = max(self._MIN_SIZE.height(), saved.height())
            self.resize(w, h)
```

Override `closeEvent`:

```python
    def closeEvent(self, event) -> None:
        _settings().setValue(_SIZE_KEY, self.size())
        super().closeEvent(event)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover_chrome.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/ui/widgets/help_popover.py tests/ui/test_help_popover_chrome.py
git commit -m "feat(help): persist popover size via QSettings"
```

---

## Task 5: Header drag-to-move behavior (manual smoke)

The drag logic is already implemented in `_HeaderFrame` (Task 3). Writing an automated Qt mouse-event test for frameless drag is brittle across platforms. This task is a manual smoke check.

- [ ] **Step 1: Manual smoke**

```bash
python3 app/main.py
```

In the running app: open any module with a `?` button → click it → drag the popover header with the mouse → confirm the window follows the cursor. Press ESC → confirm it closes. Click `×` → same. Resize from bottom-right via the grip.

- [ ] **Step 2: Note manual verification in commit** (no code change; skip commit if nothing to record)

If any defect surfaces during smoke, open a micro-task: patch, add a regression test, commit.

---

## Task 6: Pin blocks outside-click close

**Files:**
- Modify: `app/ui/widgets/help_popover.py`
- Test: extend `tests/ui/test_help_popover_chrome.py`

> **Background:** We switched away from `Qt.Popup` (which auto-closed on outside clicks) to `Qt.Tool`. This means outside-click close must be re-implemented manually, and the pin button must gate it.

- [ ] **Step 1: Write the failing test**

Append to `tests/ui/test_help_popover_chrome.py`:

```python
def test_unpinned_popover_closes_on_focus_out(app, fixture_help_provider):
    parent = QWidget()
    parent.show()
    anchor = QWidget(parent)
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    assert popover.isVisible()
    assert not popover.is_pinned()

    # Simulate user clicking back on parent → popover loses activation
    parent.activateWindow()
    app.processEvents()
    popover._on_app_focus_changed(popover, parent)  # direct invocation for test

    assert not popover.isVisible()
    parent.close()


def test_pinned_popover_stays_on_focus_out(app, fixture_help_provider):
    parent = QWidget()
    parent.show()
    anchor = QWidget(parent)
    popover = HelpPopover.show_for("terms/_sample", anchor=anchor)
    popover._pin_btn.setChecked(True)  # pin it

    popover._on_app_focus_changed(popover, parent)

    assert popover.isVisible()
    popover.close()
    parent.close()
```

- [ ] **Step 2: Run failing tests**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover_chrome.py -v -k pinned
```

Expected: FAIL.

- [ ] **Step 3: Implement focus-out close**

In `app/ui/widgets/help_popover.py`, inside `HelpPopover.__init__` after the layout assembly:

```python
        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)
```

Add the method on `HelpPopover`:

```python
    def _on_app_focus_changed(self, old: Optional[QWidget], new: Optional[QWidget]) -> None:
        if self.is_pinned():
            return
        if new is None:
            return
        # If new focus is inside the popover tree, keep open
        w: Optional[QWidget] = new
        while w is not None:
            if w is self:
                return
            w = w.parentWidget()
        self.close()
```

And disconnect on close to avoid callbacks on destroyed widgets:

```python
    def closeEvent(self, event) -> None:
        try:
            QApplication.instance().focusChanged.disconnect(self._on_app_focus_changed)
        except (RuntimeError, TypeError):
            pass
        _settings().setValue(_SIZE_KEY, self.size())
        super().closeEvent(event)
```

- [ ] **Step 4: Run new tests + full ui suite**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/ -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/ui/widgets/help_popover.py tests/ui/test_help_popover_chrome.py
git commit -m "feat(help): pin toggle gates outside-click close"
```

---

## Task 7: Fade-in open animation

**Files:**
- Modify: `app/ui/widgets/help_popover.py`
- Test: smoke only (animation timing is brittle in headless)

- [ ] **Step 1: Add animation**

In `help_popover.py`, import at the top:

```python
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
```

In `show_for`, right before `popover.show()`, replace the single `show()` call with:

```python
        popover.setWindowOpacity(0.0)
        popover.show()
        anim = QPropertyAnimation(popover, b"windowOpacity", popover)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_help_popover.py tests/ui/test_help_popover_chrome.py -v
```

Expected: all PASS. (Tests inspect final state, not animation frames.)

- [ ] **Step 3: Commit**

```bash
git add app/ui/widgets/help_popover.py
git commit -m "feat(help): fade-in animation on open"
```

---

## Task 8: Full regression run + manual QA pass

- [ ] **Step 1: Clean caches, run full test suite**

```bash
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```

Expected: all green.

- [ ] **Step 2: Manual QA checklist**

Launch `python3 app/main.py` and verify each item below against one of the modules that uses help buttons (螺栓 / 过盈 / 赫兹 / 花键 / 蜗轮 / 轴向受力螺纹)。

- [ ] 点 `?` → 弹窗淡入出现在按钮右下方
- [ ] 标题 + 分类徽章（如"螺栓 · 术语"）显示
- [ ] 正文表格有完整边框 + 表头浅粉底
- [ ] 代码块有左侧主色边
- [ ] 行内 `code` 有浅米底
- [ ] blockquote 有左灰边
- [ ] 底部 footer 显示"出处：..."（当 md 含出处时）
- [ ] 拖头部可移动窗口
- [ ] 拖右下角 size grip 可缩放
- [ ] 关闭再开，尺寸保留
- [ ] 未 pin 时点窗口外 → 关闭
- [ ] pin 后点窗口外 → 不关闭
- [ ] ESC / × 任何时候都能关闭
- [ ] 长文档（Rp0.2）可以顺畅滚动阅读

- [ ] **Step 3: If QA passes without changes, no commit needed.** If a defect surfaces, open a micro-task and fix before merge.

---

## Out of Scope (explicitly deferred)

- Multi-popover coexistence
- Search / term index
- Replacing QTextBrowser markdown rendering
- Keyboard shortcuts beyond ESC
- Minimize-to-tray
- Animated content-swap when clicking a different `?` with a popover already open (current behavior: close + reopen)
