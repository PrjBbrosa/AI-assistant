# AGENTS.md - Local Engineering Assistant

本文件是 Codex 在本仓库的当前项目级工作协议。它记录长期有效的工程约定、验证边界和历史教训；不要把旧 agent 配置或计划文档当作当前事实，所有结论以本地文件、代码、测试和实际运行结果为准。

## 适用范围与权威顺序

- 直接用户指令优先；用户说"先分析"、"别直接改"、"review"、"先确认"时，先保持只读，直到获得明确批准。
- 本文件约束整个 `/Users/donghang/Documents/Codex/AI-assistant` 仓库；更深层的 `AGENTS.md` 或用户指定的 spec/plan 可补充更窄规则。
- `CLAUDE.md` 保留给 Claude 兼容和历史追溯；修改长期项目事实时，必要时同步 `README.md`、`CLAUDE.md`、相关 `docs/`，避免说明文件漂移。
- `.claude/lessons/` 是有价值的历史教训库；高风险 core/UI/review/help 工作前按需读取相关文件。不要要求每个会话无条件读取全部 lessons。
- `.claude/agents/`、`.codex/agents/`、`.agents/skills/`、`.claude/skills/`、`.claude/rules/` 属于旧设置或迁移残留，部分路径已过时；除非用户明确要求，不把它们作为当前权威，也不要清理或删除。
- 仓库里存在很多未跟踪和带 ` 2` 后缀的文件；默认视为用户或其他 agent 的工作痕迹。没有明确要求时，不删除、不重命名、不顺手整理。

## 项目概述

本项目是基于 PySide6 的本地桌面机械设计计算工具，面向个人/小团队日常工程预校核、报告输出和可追溯计算说明。

当前主要模块：

- 螺栓连接：VDI 2230 核心链路。
- 轴向受力螺纹连接：纯轴向拉载荷的内螺纹连接校核。
- 过盈配合：DIN 7190，含实心/空心轴、配合选择、装配、微动风险等扩展。
- 赫兹应力：线接触/点接触快速估算。
- 蜗轮蜗杆设计：DIN 3975 几何与基础性能，含 DIN 3996 Method B 风格最小负载能力子集。
- 花键连接校核：DIN 5480 / DIN 6892 风格的简化预校核，加光滑段过盈链路。
- 缓冲块吸能仿真：曲线导入、吸能计算和时域响应展示。
- 材料与标准库：仍是占位或局部能力，不按完整数据库承诺。

## 技术栈

- 语言：Python 3.12
- GUI：PySide6 / Qt6
- 打包：PyInstaller（Windows `.exe`）
- 测试：pytest；headless UI 测试使用 `QT_QPA_PLATFORM=offscreen`
- 依赖：`requirements.txt`，当前包含 PySide6、PyInstaller、reportlab、matplotlib、openpyxl

## 主要结构

```text
core/                    # 纯计算逻辑，不依赖 Qt
  bolt/                  # VDI 2230、轴向螺纹、共享螺纹几何
  interference/          # DIN 7190、装配、配合选择、fretting
  hertz/                 # 赫兹接触应力
  worm/                  # DIN 3975 / Method B 风格蜗轮蜗杆计算
  spline/                # 花键几何与承载预校核
  buffer/                # 缓冲块吸能与曲线导入
app/
  main.py                # 桌面入口
  ui/
    main_window.py
    theme.py
    input_condition_store.py
    help_provider.py
    report_export.py
    report_pdf*.py
    pages/               # 各模块页面
    widgets/             # 图示、曲线、弹窗等控件
docs/                    # 用户文档、设计、计划、报告
examples/                # 输入/输出案例
tests/                   # pytest 测试
```

## 工作方式

- 默认使用中文沟通；代码、变量名、标准符号保持英文或公式惯例。
- 先给结论、风险或阻塞点，再给证据。不要用模糊乐观语气掩盖未验证状态。
- 在声明代码、计划、分支、测试、文件或 bug 事实前，先读真实本地文件或运行命令。
- 明确区分证据类型：代码推断、pytest、headless Qt、真实桌面 UI、截图、PDF/报告输出、历史记忆不是同一种证明。
- 新功能、公式变更、跨模块行为、报告/导出链路变更，先形成简短设计或计划；小 bug 可直接修，但要先复现或定位。
- 遇到 bug/测试失败，先复现、缩小范围、找根因，再修。不要凭直觉改到测试刚好变绿。
- 当前可用的 Codex skills / tools 按运行环境使用；不要在文档中硬编码某个旧 skill 路径为必须存在。

## 历史错误沉淀的硬规则

- **不要把文档或计划当实现**：帮助文档、计划、README 只说明意图；实际行为必须回到 `core/`、`app/ui/`、测试和运行输出核对。
- **写 plan 前先 grep 消费点**：凡是总体状态、报告结论、建议文案、导出字段、`overall_status`、`help_ref` 等跨出口概念，先 grep 全仓找 UI 徽章、文本报告、富 PDF、CLI、测试、帮助文档的所有消费者，再列入任务。不要只修最先看到的一行。
- **测试绿不等于用户链路绿**：core 字段新增后，必须同步验证 UI 渲染、报告行、富 PDF 和示例路径。按钮点击、报告导出、可见状态残留是独立风险。
- **"没校核" 不能显示 PASS**：可选或条件性校核缺输入时返回 `not_checked` / `incomplete`，不能被 `all(checks)` 静默吞掉。
- **禁止为了数字好看而钳位工程判据**：疲劳、强度、效率、寿命等公式不要加人为下限掩盖危险工况；边界工况该 fail 就 fail，该 warning 就 warning。
- **近似公式必须说明保守方向**：跨规格近似要覆盖 catalog 边界样本，不能只用一个有利样本。文档必须说明近似可能偏保守还是偏乐观。
- **帮助内容必须对齐代码**：写方法、选项、公式、数值例子前先查实际 calculator 和 UI 处理逻辑；数值示例优先用当前 calculator 回算，不凭记忆或标准想象。
- **标准引用要诚实**：未核对原文时，不写精确条号、表号、附录号；使用"Method B 风格最小子集"这类口径，避免把简化实现描述成完整 DIN/ISO 校核。
- **Qt 生命周期要保守**：slot、classmethod、延迟回调里的 QWidget 参数可能已被 C++ 层销毁；访问前做有效性探测或异常保护。
- **渲染失败要清屏**：计算成功后如果 UI 渲染、报告预览或二级图表失败，必须清理所有用户可见结果面并禁用导出，不能留下半成功界面。
- **输入变更后导出立即失效**：任何输入、加载条件、清空页面都会使旧结果失效；重新计算成功后才允许导出。
- **旧路径和工具状态会漂移**：旧 agent/skill 中的绝对路径可能错误；使用前先验证当前 cwd、`.venv`、`requirements.txt`、命令是否存在。
- **Codex/网络错误不要误判为仓库 bug**：`backend-api/codex/responses`、stream reconnect、证书错误等优先按客户端/网络/代理问题分类；保留 git 状态和测试状态即可，不把 repo 乱改成"修复网络"。

## 架构约定

1. `core/` 是纯 Python 计算层，不 import Qt，不读写 UI 状态，输入输出必须 JSON 可序列化。
2. Calculator 入口保持 `calculate_xxx(data: dict) -> dict` 风格，配套 `InputError`、`_require()`、`_positive()` 等验证辅助。
3. UI 页面使用 `FieldSpec` 描述字段。`mapping=(section, key)` 的字段进入 payload；`mapping=None` 仅用于展示、记录或占位。
4. UI payload 必须按当前 mode 收敛。隐藏、禁用或当前 mode 无关的字段不应混入 calculator 输入。
5. 自动填充、查表、材料选择、标准规格联动字段使用 `AutoCalcCard`，与手动输入的 `SubCard` 区分；`QLineEdit` 设为只读，`QComboBox` 设为禁用或受控。
6. 全局暖中性主题在 `app/ui/theme.py`，优先使用 objectName 驱动样式，不在局部页面发散新色系。
7. 输入条件保存/加载走 `input_condition_store.py`，写入 `saved_inputs/`；导出走统一 report helper 或各模块富 PDF helper。

## 开发规范

- UI 文本、错误消息、报告文案使用中文。
- 公式变量遵循标准符号习惯，例如 `fm_min`、`phi_n`、`sigma_ax`、`d_a1`、`p_flank`。
- 单位约定：力=N，长度=mm，应力=MPa，扭矩=N·m（内部可用 N·mm），角度=弧度（UI 显示度数）。
- Python 代码禁止 Unicode 智能引号 U+201C / U+201D，只用 ASCII `"` 和 `'`。
- 新增计算项先写 core 测试，再接 UI。涉及报告或帮助时，同时加消费链测试。
- 新测试目录必须带 `__init__.py`，避免 pytest 同名模块冲突。
- Headless UI 显隐断言用 `isHidden()`，不要用 `isVisible()` 判断 offscreen 下的真实显示。
- 遇到 import file mismatch 或奇怪 import 异常，先清理 `__pycache__` 后重跑。

## 验证协议

常用命令：

```bash
python3 -m pip install -r requirements.txt
python3 app/main.py
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -v
python3 src/vdi2230_tool.py --input examples/input_case_01.json
```

选择验证范围时按风险决定：

- core 公式或边界：跑对应 `tests/core/<module>/`，补边界样本。
- UI 字段、mode、渲染：跑对应 `tests/ui/test_<module>_page.py`，必要时做最小 `_calculate()` smoke。
- 报告导出：验证文本报告、PDF helper、富 PDF、异常失败路径。
- 帮助内容：跑 help wiring 测试，并检查孤岛术语和死链。
- 完成前至少跑 `git diff --check`；涉及多模块或共享 helper 时扩大到相关全套测试。

如果测试或 live 验证没跑，最终汇报要明确说"未验证"和原因。

## Review 规则

- review 先列发现，按严重程度排序，给出 `file:line`、用户影响和建议修复方向。
- 重点看非保守计算、伪 PASS、报告/导出误导、UI 状态残留、测试断言放宽、文档与代码漂移。
- 看到测试期望被放宽、白名单扩大、阈值变松，要追问这是契约变化还是掩盖 bug。
- 模块级 review 至少包含一次端到端路径：加载默认/样例、执行校核、查看结果、导出报告或构建报告行。
- 二次 review 不能只看测试绿，要复查用户可见残留和上一轮每个 P0/P1 的实际修复状态。

## Git 与工作区

- 可能存在脏工作区；只处理本任务相关文件，绝不回退、删除、格式化无关改动。
- 提交前先看 `git status --short` 和 `git diff --name-only`，只 stage 相关文件。
- 不运行 `git reset --hard`、`git checkout --`、批量 clean、删除分支或清理生成物，除非用户明确要求。
- 用户说 `commit and push` 时，先做轻量 hygiene：`git status`、changed-file review、`git diff --check`、相关测试，然后提交推送。

## 当前已知限制

- 螺栓模块不是完整 VDI 2230：仍未覆盖完整螺纹脱扣、完整疲劳谱（FKN 法）、偏心弯矩等。
- 螺栓模块使用 `overall_status` 三态；缺输入或未覆盖校核不能给虚假 PASS。
- 螺栓夹紧体仍有简化模型限制，多层被夹件不等同于完整逐层锥体/套筒模型。
- 全部模块的导出按钮在输入变更、加载输入、清空页面后必须失效，直到重新计算。
- 轴向受力螺纹连接暂不支持横向力、弯矩、多螺栓并联；`As/d2/d3` 始终由 `d/p` 派生，用户值偏差超过 1% 抛 `InputError`。
- 轴向受力螺纹连接缺少 `thread_strip.m_eff` 时，螺纹脱扣为"未校核"，总体状态为 `incomplete`。
- Goodman 疲劳折减不设人为下限；高平均应力工况直接失败或提示。
- 过盈模块空心轴 von Mises 判定取内孔壁与配合面较大值。
- 蜗轮模块已有 Method B 风格最小工程子集、塑料材料降额、寿命/磨损估算；它不是完整 DIN 3996 / ISO/TS 14521，Method C 当前拒绝计算。
- 蜗轮接触应力判定链与应力曲线应保持同一凸-凹曲率模型；不要让展示和判定使用不同物理点。
- 花键模块是简化预校核，不替代完整 DIN 5480 / DIN 6892 签发校核；近似几何必须保持保守方向并提示适用边界。

## 跨平台 UI 约定

- OS 级对话框保持原生：`QFileDialog`、`QFontDialog`、`QColorDialog` 不强制 Qt 自绘，不加 `DontUseNativeDialog`。
- 应用内对话框、设置、导出选项走 Qt 自绘并继承 `theme.py`。
- 帮助弹窗、frameless popup、可拖拽/可缩放控件要验证真实几何、可见把手、圆角和失焦关闭行为。
