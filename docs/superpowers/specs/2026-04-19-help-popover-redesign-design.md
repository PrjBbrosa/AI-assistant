# 帮助弹窗视觉与交互重构 — 设计规格

**日期**：2026-04-19
**范围**：`app/ui/widgets/help_popover.py` 及其主题样式
**目标**：把简陋的固定尺寸帮助弹窗升级为"精致悬浮卡片"，支持缩放、更好的 Markdown 排版、保留轻盈感。

---

## 1. 背景与问题

现状 `HelpPopover`：

- `Qt.Popup | Qt.FramelessWindowHint` + `setFixedSize(460, 520)` → 不能拖动、不能缩放
- `QTextBrowser` 未配置文档级样式 → 标题、表格、代码块、blockquote 全是 Qt 默认灰白
- 头部只有纯文字标题 + `×` 按钮，没有分类/出处信息
- 对 Rp0.2 这类含多级标题、表格、代码块、注释段的长文档，可读性差

用户反馈：**弹窗太简陋、不灵动；md 格式结构差；窗口不可缩放。**

## 2. 设计决策

**方案 A — 精致悬浮卡片**（已在 `docs/help_popover_mockup.html` 验证通过）。

保留"锚定 `?` 按钮右下方打开"的轻盈交互，升级视觉与排版：

- **可缩放**：`QSizeGrip` 放右下角，记住上次尺寸
- **可拖动**：自绘头部作为拖拽把手
- **可固定**：pin 按钮切换到"不被点外面关闭"的常驻模式
- **Markdown 富样式**：QTextBrowser 注入文档级 CSS，覆盖 h2/h3/code/table/blockquote/ul/ol
- **头部增强**：分类徽章（如"螺栓 · 材料参数"）+ 标题 + pin + close
- **页脚出处**：来源信息从正文底部提升为 footer 栏

## 3. 架构

分层：

```
HelpPopover (QDialog, Qt.Tool + FramelessWindowHint)
├─ HelpPopoverHeader (自绘拖拽条 + category + title + pin + close)
├─ HelpPopoverBody   (QTextBrowser + 文档 CSS)
├─ HelpPopoverFooter (出处行)
└─ QSizeGrip         (右下角缩放把手)
```

所有子组件保留在 `help_popover.py` 内；QSS 统一写入 `app/ui/theme.py`。不引入新文件。

### 数据流

`HelpEntry` 当前只有 `title` 和 `body_md`。需扩展：

```python
@dataclass(frozen=True)
class HelpEntry:
    title: str
    body_md: str
    category: str | None    # 新增：来自 md frontmatter 或目录推断
    source: str | None      # 新增：来自 md 末尾 "**出处**" / "Source" 行
```

**category 来源**：按 md 文件所在子目录推断（`terms/` → "术语"、`modules/bolt/` → "螺栓"、`modules/interference/` → "过盈"）。首版无需 frontmatter，用路径映射表即可。

**source 来源**：`HelpProvider._parse` 扫描 body，匹配以 `**出处**：`、`**Source**:`、`出处：` 开头的最后一段，提取并从 body 里剥离。

### QSS 约定

新增 objectName：

- `HelpPopoverRoot` — 外层圆角 + 阴影（通过 `QGraphicsDropShadowEffect`）
- `HelpPopoverHeader` / `HelpPopoverFooter` — 头尾栏背景
- `HelpPopoverCategory` — 分类徽章（`#FAF1EC` 底 `#D97757` 文字）
- `HelpPopoverTitle` — 标题
- `HelpPopoverIconBtn` — pin / close 按钮（hover 底色）
- `HelpPopoverIconBtn[pinned="true"]` — pin 激活态

### 文档 CSS（注入 QTextBrowser）

QTextBrowser 支持子集 HTML/CSS。关键映射（颜色沿用主题变量）：

| Markdown 元素 | 样式 |
|---|---|
| `h2` | `color:#2F2E2C; border-bottom:1px solid #F0ECE4; padding-bottom:6px; margin-top:22px` |
| `h3` | `font-size:13.5px; margin-top:18px` |
| 行内 `code` | `background:#F4EFE8; border:1px solid #E7DFD2; color:#8A4A2E; padding:1px 6px; border-radius:4px` |
| `pre` / 代码块 | `background:#FAF7F4; border-left:3px solid #D97757; border-radius:6px; padding:10px 14px` |
| `table` | 完整边框 + `thead` 浅粉底 `#FAF1EC` + 斑马纹 `#FBF8F4` |
| `blockquote` | 左边 3px 灰边 + 浅米底 + 斜体灰字 |
| `ul/ol li` | marker 颜色主色（QTextBrowser 能力有限，若做不到则降级为默认） |

> **QTextBrowser 的 CSS 限制**：不支持 flex、`::before`、`::marker`、`border-radius` 在某些元素上无效。mockup 里的 h2 左色块和 `li::marker` 若渲染不出，降级方案：h2 改用左侧实体字符 `▍` 前缀 + 颜色；li marker 放弃染色。

## 4. 行为规格

### 打开
- 触发：`HelpButton.clicked` → `HelpPopover.show_for(ref, anchor)`
- 位置：锚点右下 +8，越界时翻转到屏幕内
- 动画：150ms 透明度淡入 + 4px 上滑（`QPropertyAnimation`）
- 焦点：弹窗获取焦点，允许 ESC 关闭

### 缩放
- 默认 **520×640**（比现在 460×520 大约 30%）
- 最小 **380×320**，最大 = 屏幕可用区 - 32px
- `QSizeGrip` 放右下角，覆盖在 footer 上
- 尺寸持久化：`QSettings` key `help_popover/size` 保存最后一次尺寸；下次打开恢复

### 拖动
- 在 `HelpPopoverHeader` 上 `mousePressEvent` / `mouseMoveEvent` / `mouseReleaseEvent` 实现移动
- 拖动中游标改为 `Qt.ClosedHandCursor`
- 位置不持久化（每次按 anchor 重新定位）

### Pin（固定）
- 默认未固定：点弹窗外区域 → 关闭（通过 `focusOutEvent` 或全局事件过滤器）
- 已固定：点外面不关、打开新的"?"也不关（但同一时刻仍只一个实例，新 `?` 替换内容；pin 状态不跨条目保留）
- 视觉：pin 按钮 `pinned=true` 时底色变主色浅调

### 关闭
- ESC / × / 点外面（未 pin）/ 新 `?` 替换

### 替换内容
- 若已打开且点了同一个 `?` → 关闭
- 若已打开且点了另一个 `?` → 当前不关，body/header 内容切换，位置重新按新 anchor 定位（动画：淡出 80ms → 换内容 → 淡入 80ms）

## 5. 边界与降级

- **QTextBrowser CSS 不支持的属性**：实测 → 降级（见"文档 CSS"章节）。实现前先写一个最小 demo 验证 h2 左色块与 table 圆角是否渲染。
- **source 行缺失**：footer 栏隐藏，body 不缩
- **category 映射缺失**：徽章不显示，标题左对齐占满
- **阴影性能**：`QGraphicsDropShadowEffect` 在低端机上可能掉帧；低优先级，若反馈卡再考虑降级为纯边框

## 6. 测试策略

保留现有 `tests/ui/` 下 help_popover 的测试不被破坏，新增：

- `test_help_popover_size_persisted`：打开 → 缩放 → 关闭 → 再开，尺寸保持
- `test_help_popover_pin_blocks_outside_click`：pin 后 `QApplication.focusChanged` 不触发关闭
- `test_help_popover_header_drag_moves_window`：模拟鼠标按下/移动/释放，校验位置变化
- `test_help_entry_parses_category_and_source`：`HelpProvider._parse` 正确提取 category（来自路径）和 source（来自 `**出处**` 段）
- `test_help_popover_body_renders_tables`：注入含 table 的 md，检查 `QTextBrowser.toHtml()` 含 `<table>` 且应用了 CSS（验证 style 属性存在）

## 7. 非目标（明确不做）

- 不支持同时打开多个弹窗（保留"一次一个"的克制）
- 不实现搜索 / 术语目录（那是 drawer 方向 B 的特性）
- 不重写 md 渲染引擎（继续用 QTextBrowser `setMarkdown()`）
- 不动 `docs/help/*.md` 内容（只改解析）
- 不做键盘快捷键（Ctrl+W 之类）
- 不做最小化到托盘

## 8. 验收标准

1. 打开任意 "?" 按钮，视觉与 `docs/help_popover_mockup.html` 对齐度 ≥ 90%（受 QTextBrowser CSS 能力限制，允许降级）
2. 拖右下角可缩放；关闭重开后尺寸保持
3. 拖头部可移动
4. pin 状态下点窗口外不关闭
5. ESC / × 任何时候都能关闭
6. footer 显示"出处"行（当 md 含出处时）
7. 头部显示分类徽章（当 category 可推断时）
8. 既有帮助按钮的调用点零改动
9. `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v` 全绿
