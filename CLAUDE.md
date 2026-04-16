# CLAUDE.md — Local Engineering Assistant

## 项目概述
本地桌面机械设计计算工具，基于 PySide6 构建。提供工程校核表单界面，面向个人/小团队日常设计验算。
当前已实现：螺栓连接（VDI 2230）、过盈配合（DIN 7190）、赫兹接触应力、蜗轮几何（DIN 3975）、轴向受力螺纹连接。

## 技术栈
- **语言**: Python 3.12
- **GUI**: PySide6 (Qt6)
- **打包**: PyInstaller（Windows .exe）
- **测试**: pytest（headless 测试需 `QT_QPA_PLATFORM=offscreen`）
- **依赖**: `requirements.txt`（仅 PySide6 + PyInstaller）

## 项目结构
```
core/                  # 纯计算逻辑，不依赖 Qt
  bolt/calculator.py       # VDI 2230 核心校核
  bolt/tapped_axial_joint.py  # 轴向受力螺纹连接
  interference/calculator.py  # 圆柱面过盈配合
  hertz/calculator.py      # 赫兹接触应力
  worm/calculator.py       # DIN 3975 蜗轮几何
app/
  main.py              # 桌面入口
  ui/
    main_window.py     # 主窗口 + 侧栏模块列表
    theme.py           # 暖中性色调全局样式表
    input_condition_store.py  # 输入条件保存/加载通用逻辑
    pages/             # 各模块 UI 页面
      bolt_page.py         # 螺栓连接（章节式步骤表单）
      bolt_tapped_axial_page.py  # 轴向受力螺纹连接
      interference_fit_page.py
      hertz_contact_page.py
      worm_gear_page.py
      base_chapter_page.py  # 章节页基类
      placeholder_page.py   # 占位页
    widgets/           # 可复用绘图控件
      clamping_diagram.py    # 螺栓夹紧示意 + 螺纹力三角
      hertz_input_diagram.py
      press_force_curve.py
      worm_geometry_overview.py
      worm_performance_curve.py
docs/                  # 计算说明与设计文档
  vdi2230-calculation-spec.md
  plans/               # 按日期命名的设计/实现方案
examples/              # 输入/输出 JSON 测试案例
tests/                 # pytest 测试
```

## 架构约定
1. **计算与 UI 严格分离**: `core/` 模块是纯 Python 计算，函数签名为 `calculate_xxx(data: dict) -> dict`，输入输出均为 JSON 可序列化字典。不引入 Qt 依赖。
2. **每模块一个 calculator**: `core/<module>/calculator.py` 包含 `InputError` 异常类、`_require`/`_positive` 验证辅助函数、主计算函数。
3. **UI 页面模式**: 每个模块页面在 `app/ui/pages/` 下，使用 `FieldSpec` 数据类描述字段元信息（id、label、unit、hint、mapping、widget_type、default）。`mapping` 为 `(section, key)` 元组时，该字段参与计算 payload 构建；为 `None` 时仅用于 UI 记录或占位。
4. **暖色调主题**: 全局 QSS 在 `theme.py`，使用 `#F7F5F2` 背景 / `#D97757` 主色 / `#EED9CF` 选中色。ObjectName 驱动样式（Card、SubCard、PassBadge、FailBadge 等）。
5. **自动填充字段蓝色标识**: 凡由下拉联动、查表、材料选择等逻辑自动填充的输入字段，必须使用 `AutoCalcCard` 样式（蓝灰色背景 `#EDF1F5`，蓝灰文字 `#3A4F63`），与手动输入的 `SubCard` 区分。所有模块（螺栓、过盈、花键等）保持一致。通过 `card.setObjectName("AutoCalcCard")` + `style().unpolish/polish` 切换样式，`QLineEdit` 设为 `setReadOnly(True)`，`QComboBox` 设为 `setEnabled(False)`。
6. **输入条件持久化**: 通过 `input_condition_store.py` 统一保存/加载 JSON 文件到 `saved_inputs/` 目录。

## Claude 工作流程
- **对话语言以中文为主**，包括回复、汇报、提问均使用中文；代码和变量名保持英文。
- 实现新功能或重大修改前，使用 `superpowers:brainstorming` 探索需求和设计。
- 多步骤任务先用 `superpowers:writing-plans` 制定计划，再用 `superpowers:executing-plans` 执行。
- 遇到 bug/测试失败时，使用 `superpowers:systematic-debugging` 而非直觉修复。
- 新功能开发使用 `superpowers:test-driven-development`，先写测试再写实现。
- 声称完成前，使用 `superpowers:verification-before-completion` 确认测试通过。

## Agent Team 经验积累
- **经验文件位置**: `.claude/lessons/` 目录，按角色分文件（`core-lessons.md`、`ui-lessons.md`、`test-lessons.md`、`review-lessons.md`）。
- **写入时机**: 当用户纠正错误、指出问题、或确认非显而易见的做法时，主会话（编排者）负责将教训写入对应的 lessons 文件。
- **写入格式**:
  ```
  ## YYYY-MM-DD 简短标题
  - **错误**: 描述犯了什么错
  - **正确做法**: 应该怎么做
  - **原因**: 为什么这样做是对的
  ```
- **读取时机**: 每个 agent 启动时自动读取自己的 lessons 文件，确保历史教训不会遗忘。
- **跨角色教训**: 如果一个错误涉及多个角色（如 UI 错误同时需要 reviewer 关注），同时写入相关的所有 lessons 文件。

## 开发规范
- 错误信息与 UI 文本使用**中文**。
- 代码注释在必要时使用中文（解释工程公式背景）。
- 变量命名遵循公式符号习惯（如 `fm_min`, `phi_n`, `sigma_ax`），保持与 VDI/DIN 标准一致性。
- 新增校核项时，先在 `core/` 写纯函数逻辑并添加 pytest 测试，再在 `pages/` 接入 UI。
- 使用 `_positive()` / `_require()` 做输入边界检查，抛出 `InputError`，UI 层统一 `try/except` 展示。
- 单位约定：力=N、长度=mm、应力=MPa、扭矩=N·m（内部可用 N·mm）、角度=弧度（UI 显示度数）。

## 运行方式
```bash
# 安装依赖
python3 -m pip install -r requirements.txt

# 启动桌面应用
python3 app/main.py

# 运行测试
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v

# CLI 模式（保留）
python3 src/vdi2230_tool.py --input examples/input_case_01.json
```

## 当前已知限制
- 螺栓模块：未覆盖螺纹脱扣、完整疲劳谱（FKN 法）、偏心弯矩。
- 螺栓模块：多层被夹件统一圆柱体模型（不支持逐层锥体/套筒选择），锥台模型仅适用对称夹紧体。
- 轴向受力螺纹连接：已实现 core 计算（含 ISO/VDI 标准引用）、UI 结果展示、文本/PDF 报告导出。暂不支持横向力、弯矩、多螺栓并联。
  - `As/d2/d3` 始终由 `d/p` 按 ISO 898-1 公式派生；若用户输入与派生值相对偏差 > 1% 会抛 `InputError`，UI 层把这三个字段锁定为 `AutoCalcCard` 只读。
  - 未提供 `thread_strip.m_eff` 时螺纹脱扣标记为"未校核"（`status="not_checked"`），`overall_status` 会保持 `incomplete`，不再给出虚假的绿灯 PASS。
  - 疲劳 Goodman 折减没有人为下限；`σ_m ≥ 0.9·Rp0.2` 直接判疲劳不通过。
  - 任意输入变更、加载输入、清空页面后，"导出报告"按钮会立即失效，直到重新执行计算后才允许导出。
- 蜗轮模块：DIN 3996 负载能力校核未实现。
- 花键模块：
  - 近似几何已按 DIN 5480-2:2015 catalog 重新推导（d_a1=d-0.2m, d_a2=d-2.0m, d_f1=d-2.3m；h_w≈0.9m）。仍仅供简化预校核，正式校核应走公开/图纸尺寸模式。
  - `scenario_a` 返回新增 `torque_capacity_sf = T_cap/T_design`（与 flank_safety 等价，方便从扭矩视角解读）。
  - 材料下拉 45钢/40Cr/42CrMo 选中后自动填充 E / ν / 屈服强度，切"自定义"一并解锁。
  - k_alpha 默认值 1.3（DIN 6892 K_1·K_2·K_3 的保守合成上限），与 UI FieldSpec.default 一致。
  - `_build_payload` 在"仅花键"模式下不再向 calculator 传递 smooth_* 段。

## 开发注意事项
- **禁止 Unicode 智能引号**: Python 代码中严禁出现 `"` `"` (U+201C/U+201D)，仅使用 ASCII 引号 `"` `'`。含中文字符串时尤其注意。
- **测试目录需 `__init__.py`**: `tests/` 下每个子目录必须有 `__init__.py`，否则 pytest 会因同名模块冲突报 import 错误。
- **并行 Agent 避免编辑同一文件**: 多 Agent 并行时，分配不同文件范围，避免同时写入同一文件导致冲突。
- **清除 pycache**: 测试 import 异常时先 `find . -name __pycache__ -exec rm -rf {} +`。
