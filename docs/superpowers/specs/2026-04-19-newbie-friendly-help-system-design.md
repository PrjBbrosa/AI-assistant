---
title: 新手友好化 · 工程知识帮助系统
date: 2026-04-19
status: design
owner: 主会话
---

# 新手友好化 · 工程知识帮助系统（Design）

## 1. 背景

当前 6 个校核模块（bolt_vdi / bolt_tapped_axial / interference / hertz / worm / spline）的 UI 页面里，专业术语密集，"工作一两年的机械工程师"也普遍存在理解门槛。典型问题：

- 蜗轮 "基本设置" 板块使用 "Load Capacity 骨架状态"、"Method B 最小子集" 等开发内部语言，直接流到 UI。
- "变位系数 x"、"KHbeta"、"许用齿面应力" 等专业术语无上下文提示。
- 每个校核方法（VDI 2230 / DIN 3996 Method B / DIN 7190 等）缺少高层概念解释。

## 2. 目标

建立一套"工程知识帮助系统"：

- **主目标 (B)**：为每个专业术语、每个校核方法提供"打开即懂"的中文通俗解释 + 公式 + 典型值 + 出处。
- **辅助目标 (A)**：将各 section 的 subtitle 从"开发者视角"重写为"本章节在做什么" 的新手引导文案。全屏 walkthrough 暂不纳入本 spec。
- 范围：全部 6 个校核模块。
- 不改动 `core/` 任何计算逻辑。
- 不引入新的第三方依赖。

## 3. 非目标

- 不做 LaTeX 实时渲染；复杂公式先用纯文本形式（`tan γ = z₁ / q`），后续可用项目已有的 `LatexLabel` 扩展。
- 不做全屏新手模式开关 / walkthrough 动画（留作后续独立 spec）。
- 不做图片 / 示意图资产（留作后续迭代）。
- 不改变现有 `FieldSpec` 已用字段的语义。

## 4. 架构

### 4.1 分层

```
内容层（docs/help/）                 Markdown 文件池
    ↓
数据层（HelpProvider）               索引 + 懒加载 + 缓存
    ↓
组件层（HelpPopover / HelpButton）   Qt 组件
    ↓
注入层（FieldSpec / base_chapter_page）  "?" 按钮挂到字段 / 章节
```

### 4.2 目录结构

```
docs/help/
  GUIDELINES.md                  # 规范文档（Stage 0 骨架 → Stage 1 完善 → Stage 7 终稿）
  terms/                         # 术语池（全局共享，所有模块可引用）
    elastic_modulus.md
    profile_shift.md
    khbeta.md
    ...
  modules/                       # 模块 / 方法概念文
    worm/
      _section_basic.md          # section 级文章（"_section_" 前缀）
      _section_load_capacity.md
      din3996_method_b.md
    bolt_vdi/
      vdi2230_overview.md
      ...
    ...
  assets/                        # 图片资产目录（暂留空）
```

### 4.3 命名约定

- 术语文件：`terms/<snake_case>.md`，例：`profile_shift.md`、`khbeta.md`
- 模块文章：`modules/<module_key>/<snake_case_title>.md`
- section 级文章：`modules/<module_key>/_section_<section_id>.md`（"_section_" 前缀区分）
- `FieldSpec.help_ref` 格式：不含 `.md` 后缀，例 `terms/profile_shift`、`modules/worm/din3996_method_b`

## 5. UI 组件

### 5.1 `HelpButton(QToolButton)`

- 显示 "?" 文字按钮（纯样式，不引入图片资源）
- `objectName = "HelpButton"`，样式在 `theme.py` 定义：
  - 默认：背景 `#E3E3DE`、文字 `#5F5E5B`、圆角 8px、16×16
  - hover：背景 `#EED9CF`、文字 `#D97757`
- 嵌入位置：字段 label 行尾 / section 标题栏末端
- 点击触发对应 `HelpPopover` 弹出

### 5.2 `HelpPopover(QDialog)`

- 无模态：`WindowModality.NonModal`
- `FramelessWindowHint` + 阴影；尺寸 460×520，内容超出启用 QScrollArea
- 顶部：标题（来自 Markdown 首行 `# ` 标题）+ 右上关闭 ×
- 正文：`QTextBrowser.setMarkdown(body_md)`（PySide6 原生支持）
- 关闭：Esc 键 / 点击外部
- 定位：触发按钮右下偏移 +8px；靠近屏幕边缘时翻转方向避免溢出

### 5.3 `HelpProvider`（单例）

- 启动时扫描 `docs/help/`，建立 `{ref → absolute_path}` 索引
- `get(ref: str) -> HelpEntry(title, body_md)`：按 ref 读文件；`title` 取首个 `# ` 标题；`body_md` 为剩余内容
- 容错：ref 不存在时返回占位 `HelpEntry("帮助内容缺失", "ref=<ref>")`，不抛异常（配合测试/运行期排错）
- 懒加载：首次请求时读文件；后续缓存 `HelpEntry`
- PyInstaller 兼容：支持 `sys._MEIPASS` 资源路径

## 6. FieldSpec / Page 扩展

### 6.1 FieldSpec 新增字段

```python
@dataclass(frozen=True)
class FieldSpec:
    ...
    help_ref: str = ""
```

- `help_ref != ""` 时，UI 构建该字段在 label 右侧插入 `HelpButton`
- 默认空字符串：保持现有行为，不插入按钮
- 注意：各 page.py 目前都自己定义了 `FieldSpec`（未集中），Stage 0 维持现状，在每个 page.py 里同步新增

### 6.2 base_chapter_page 扩展

```python
def add_chapter(self, title: str, widget: QWidget, *, help_ref: str | None = None) -> None: ...
```

- `help_ref` 非 None 时在章节标题右侧注入 `HelpButton`

### 6.3 section 级引导文案（A 辅助目标）

各 page 在 `_create_form_page(title, subtitle, fields)` 的 `subtitle` 参数里，将原先"开发者视角"的描述重写为新手导向的"本章节在做什么"。例：

- 改前：`"定义本版标准边界和 Load Capacity 骨架状态。"`
- 改后：`"设置校核范围和选项：是否启用齿面/齿根负载能力校核、使用哪个计算方法。"`

subtitle 文案统一在 GUIDELINES.md 列表登记，避免各 agent 自行发挥导致风格漂移。

## 7. Markdown 内容模板（深度 2）

### 7.1 术语文章模板

```markdown
# 术语名（符号）

**一句话**：xxx

**怎么理解**：2–3 段通俗解释

**公式**：（可选，纯文本公式）

**典型值**：范围 + 常见选择场景

**出处**：DIN/VDI/ISO 条款编号
```

### 7.2 section 概念文模板

```markdown
# 本章节是什么

## 为什么要填这些
## 输入 / 产出
## 方法差异（如有 Method A/B/C 或类似选项）
## 参考标准
```

### 7.3 模块方法总览文模板

用于核心方法（VDI 2230 / DIN 3996 Method B / DIN 7190 等）：

```markdown
# 方法名（标准编号）

## 一图总览
## 解决什么问题
## 核心流程（3–5 步）
## 本模块实现的范围 / 不实现的范围
## 常见误用
## 参考文献
```

## 8. 实施计划（串行 + 每阶段 codex adversarial review）

### Stage 0：基础设施（~0.5 天）

- 新增文件：
  - `app/ui/help_provider.py`
  - `app/ui/widgets/help_popover.py`
  - `app/ui/widgets/help_button.py`
  - `docs/help/GUIDELINES.md`（骨架版本）
- 修改文件：
  - `app/ui/pages/base_chapter_page.py`（add_chapter 扩展 help_ref 参数）
  - `app/ui/theme.py`（HelpButton 样式）
  - 6 个 page.py 中 `FieldSpec` 类加 `help_ref: str = ""` 字段
- 新增测试：
  - `tests/ui/test_help_provider.py`
  - `tests/ui/test_help_popover.py`
- 验收：全部 headless 测试通过，现有测试未破坏

### Stage 0.5：codex adversarial review Stage 0 → 优化 → lessons

- 调用 `codex:codex-rescue` agent（以 adversarial reviewer 身份，见 9.1）
- review 范围：组件接口、样式一致性、错误处理、测试覆盖、PyInstaller 兼容
- 按反馈直接修完
- lessons 落位：`.claude/lessons/ui-lessons.md`、`.claude/lessons/review-lessons.md`

### Stage 1：蜗杆 pilot + 规范固化（~1.5 天）

- 改 `app/ui/pages/worm_gear_page.py`：
  - 每个 FieldSpec 填 `help_ref`（只给"新手不懂的专业术语"；普通字段留空）
  - `add_chapter()` 调用处填 `help_ref` 指向 `modules/worm/_section_*`
  - 所有 section 的 subtitle 重写为"本章节在做什么"（A 目标）
- 写 `docs/help/modules/worm/`：
  - section 文章：`_section_basic`、`_section_geometry`、`_section_material`、`_section_operating`、`_section_advanced`、`_section_load_capacity`
  - 方法总览：`din3975_geometry_overview.md`、`din3996_method_b.md`
- 写 `docs/help/terms/` 首批（蜗杆用到的专业术语，实际清单以代码扫描为准）：
  - 示例：`elastic_modulus`、`profile_shift`、`lead_angle`、`diameter_factor_q`、`application_factor_ka`、`dynamic_factor_kv`、`kh_alpha`、`kh_beta`、`allowable_contact_stress`、`allowable_root_stress`、`handedness`、`lubrication_factor` 等
- 主会话扫描其他 5 个模块 FieldSpec，建立**全项目候选术语 master list**（记入 `GUIDELINES.md` 附录）：术语 ID、首次出现模块、建议优先级
- 补完 `docs/help/GUIDELINES.md`：文风、公式写法、术语命名规则、模板检查表、subtitle 重写风格

### Stage 1.5：codex adversarial review Stage 1 → 优化 → lessons（规范定型关键点）

- review 重点：
  1. 深度 2 模板是否真能让新手看懂（主观 + 结构）
  2. GUIDELINES 是否可操作、无歧义
  3. 蜗杆术语命名是否有跨模块重名 / 概念重叠风险
  4. `help_ref` 覆盖度是否恰当
- 直接按反馈修完
- 新建 `.claude/lessons/help-content-lessons.md`，记录：文风踩坑、术语定义边界、模板漏项、典型值写法等
- 更新 `ui-lessons.md` 与 `review-lessons.md`

### Stage 2–6：其余 5 模块（各 ~0.5–1 天 + 0.2 天 review）

**串行顺序**：bolt_vdi → bolt_tapped_axial → interference → hertz → spline

选择理由：

- VDI 2230（bolt_vdi）最核心也最复杂，对规范压力测试最强，先做
- tapped_axial 与 vdi 概念重叠最多，紧随其后最大化术语池复用
- interference / hertz 单一校核、规模中等
- spline 模块已充分成熟，放最后

每个 Stage N 单模块流程（N ∈ {2,3,4,5,6}）：

1. 按 Stage 1 沉淀的规范实施（page `help_ref` 填充 + `modules/<module>/*.md` 编写 + `terms/` 增量补充）
2. smoke 测试通过
3. codex adversarial review（通过 `codex:codex-rescue` 调用）→ 直接修完
4. 新经验写入 `help-content-lessons.md` / `ui-lessons.md` / `review-lessons.md`

### Stage 7：终审（~0.5 天）

- 跨模块术语一致性扫描（同一概念不同命名 / 同一命名不同含义）
- 死链扫描：有 `help_ref` 但 md 不存在 / 有 md 但没被引用
- 全量 UI smoke：6 个模块随机点击 10+ 个 "?" 确认正常
- GUIDELINES.md 定稿

## 9. review 与 lessons 机制

### 9.1 review agent 与 adversarial 风格

每个 Stage 结束调用 `codex:codex-rescue` agent，要求它以 **adversarial reviewer**（对抗性评审）身份，而非鼓励式点头。具体要求在 prompt 中明确：

- 主动挑刺：故意找漏洞、盲点、边界情况、未覆盖的失败模式
- 质疑设计假设：对 spec 的每个关键决定都提出"为什么不是另一种"
- 挑战公式正确性：蜗杆 Method B 相关公式、典型值范围、出处条款编号都要对照原始标准查证（查不到标准时明确标注"无法核实"）
- 挑战文风一致性：多个术语文章风格是否统一、是否真能让新手看懂
- 禁止空评价：不允许 "looks good to me" / "no issues found" 这种声明，必须至少列出三个潜在风险或改进点；确实无严重问题时明确陈述"我按 X 个维度各自检查了 Y 项，具体结果如下"
- 优先级标注：P0（必修）/ P1（建议修）/ P2（可选）

### 9.2 review 输入（主会话维护一套 prompt 模板）

- 当前 Stage 目标
- 改动文件清单 + diff
- GUIDELINES.md 最新内容
- 要求检查维度（组件 / 内容 / 规范合规 / 未覆盖风险）

### 9.3 优化与再 review

- 严重问题（P0）修完后二次调用 adversarial review 确认
- 轻微问题（文风微调、typo）直接修完，不必二次 check

### 9.4 lessons 落位

| 维度 | 文件 |
|------|------|
| UI 组件 / Qt 行为 | `.claude/lessons/ui-lessons.md` |
| review 方法论 / review patterns | `.claude/lessons/review-lessons.md` |
| help 内容撰写 / 术语定义 / 模板 | `.claude/lessons/help-content-lessons.md`（新建） |

每次 Stage 结束必须显式检查是否有新 lessons；没有也要在 Stage 小结中注明"无新 lesson"。

## 10. 测试策略

- `tests/ui/test_help_provider.py`：索引构建、ref 查找、缺失 ref 容错、缓存一致性
- `tests/ui/test_help_popover.py`：弹出 / Esc 关闭 / 外部点击关闭 / setMarkdown 渲染
- 6 个 `tests/ui/test_<module>_page.py` 各补一条 smoke：至少一个 `help_ref != ""` 的字段能触发 `HelpPopover` 显示
- 全部 headless（`QT_QPA_PLATFORM=offscreen`）
- 不引入新依赖（QTextBrowser / QDialog 均为 PySide6 原生）

## 11. 风险与边界

- **不改 core/**
- **QTextBrowser 公式能力有限**：公式用纯文本；复杂场景可内嵌 `LatexLabel`（留扩展点，不在本 spec 强求）
- **Qt 对齐风险**：插入 HelpButton 可能影响现有 SubCard / AutoCalcCard 的视觉对齐；Stage 0 组件先做 headless layout 测试
- **资源路径**：PyInstaller 打包后 `docs/help/` 需要正确包含；HelpProvider 支持 `sys._MEIPASS`
- **术语命名歧义**：由 Stage 1.5 review 强制检查；一旦发现重名或概念分裂立即统一
- **规范漂移**：每个 Stage 都以 GUIDELINES.md 为准；任何偏离必须回写规范

## 12. 估时总表

| Stage | 工期（天） | 累计 |
|-------|-----------|------|
| 0 + 0.5 | 0.5 | 0.5 |
| 1 + 1.5 | 1.5 | 2.0 |
| 2（bolt_vdi） | 1.0 | 3.0 |
| 3（bolt_tapped_axial） | 0.8 | 3.8 |
| 4（interference） | 0.8 | 4.6 |
| 5（hertz） | 0.8 | 5.4 |
| 6（spline） | 0.8 | 6.2 |
| 7 终审 | 0.5 | 6.7 |

合计：约 **6.5–7 天墙钟**（连续工作估算，含 review + 优化）

## 13. 成功判据

- [ ] 6 个模块 UI 上所有"专业术语"字段旁都有 "?" 按钮，点击弹出深度 2 内容
- [ ] 6 个模块每个 section 的 subtitle 已重写为新手可读风格
- [ ] 6 个模块每个 section 旁都有 section 级 "?"
- [ ] `docs/help/` 目录结构完整，无死链
- [ ] `docs/help/GUIDELINES.md` 定稿
- [ ] 测试套件全绿（含新增 help 相关测试）
- [ ] 7 次 codex adversarial review（Stage 0.5 + 6 个模块 stage）均有简短 summary 留痕（存进 `docs/reports/` 或对应 lessons 文件）
- [ ] 3 个 lessons 文件（ui / review / help-content）均有实际内容
