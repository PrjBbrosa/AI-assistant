# 轴向受力螺纹连接模块设计文档 v2

日期: 2026-04-04
模块: 轴向受力螺纹连接（侧栏独立模块）
基于: 2026-03-25 v1 设计文档增量完善

## Goal

将已有的轴向受力螺纹连接模块从"输入骨架 + 未接入计算"状态，完善为与螺栓连接（VDI 2230）功能对齐的完整模块。包括：标准引用审查、UI 结果展示、PDF 报告导出。

## Problem Statement

当前状态：
- `core/bolt/tapped_axial_joint.py` 计算逻辑基本完整，但标准引用模糊，部分错误信息为英文
- `app/ui/pages/bolt_tapped_axial_page.py` 仅有输入骨架，无计算按钮、无结果展示
- 模块未注册到 `main_window.py` 侧栏
- 无 PDF 报告功能

## Scope

### In Scope

- Core 计算逻辑标准引用审查与修正
- UI 计算集成：计算按钮、结果卡片、分项校核、数值展示、警告建议
- 文本报告导出
- PDF 报告导出
- 主窗口侧栏注册
- 测试补全
- 输入条件保存/加载（已有，保留）

### Out of Scope

- 横向力、防滑移、弯矩、偏心
- 夹紧力示意图（不适用于本工况）
- 现有 VDI 2230 螺栓连接模块的重构
- 完整 bearing pressure 子模型
- 多螺栓并联分载

## Design

### 1. Core 计算逻辑审查与标准引用

在现有 `calculate_tapped_axial_joint()` 基础上增量修正，不改变函数签名和输出 schema。

#### 标准对照表

| 计算块 | 对应标准 | 审查要点 |
|--------|---------|---------|
| 螺纹几何 (As, d2, d3) | DIN 13-1, ISO 898-1 Sec 9 | 公式正确，补注释引用 |
| 预紧力范围 F_max = α_A × F_min | VDI 2230-1:2015 Sec 5.4.1, Table A8 | α_A 范围表核对 |
| 装配扭矩 | VDI 2230-1:2015 Sec 5.4.2, Eq. (5.4/1) | 公式正确，补注释 |
| 装配 von Mises | VDI 2230-1:2015 Sec 5.5.1, Eq. (5.5/1) | 公式正确，补注释 |
| 服役强度 (k_tau=0.5) | VDI 2230-1:2015 Sec 5.5.2 | k_tau=0.5 是 VDI 惯例，补注释 |
| 疲劳 σ_ASV 表 | VDI 2230-1:2015 Table A4 | 核对表值是否一致 |
| Goodman 折减 | VDI 2230-1:2015 Sec 5.5.3 | 简化 Goodman，标注为 VDI 近似 |
| 寿命系数 (2e6/N)^0.08 | VDI 2230-1:2015 Sec 5.5.3 | 确认指数出处 |
| 螺纹脱扣 C1/C3 | VDI 2230-1:2015 Sec 5.5.5, ISO 898-1 Sec 9.2 | C1/C3 默认值标注 |

#### 需要修正的点

1. `_ASV_TABLE_ROLLED` 表值与 VDI 2230-1 Table A4 逐项核对，偏差处修正
2. 部分 `InputError` 消息用英文（如 `"must be > 0"`），统一改中文
3. 每个计算块添加 `# Ref: VDI 2230-1:2015, Sec X.X, Eq. (X.X/X)` 格式注释
4. `references` 输出字典中补充具体标准条款号

#### 不改动的部分

- 函数签名 `calculate_tapped_axial_joint(data: dict) -> dict`
- 输出 schema 结构
- 输入 schema 结构

### 2. UI 页面补全

在现有 `bolt_tapped_axial_page.py` 骨架上添加。

#### 2.1 计算按钮

- 在 action buttons 区域添加"开始计算"按钮
- 点击流程：`_build_payload()` -> `calculate_tapped_axial_joint(payload)` -> `_render_result(result)`
- 捕获 `InputError`，用 `QMessageBox` 展示中文错误

#### 2.2 结果章节

替换现有"状态占位"章节，包含：

**总体判定卡片：**
- Pass/Fail badge + 总体结论文字
- 使用 `set_overall_status()` 方法

**分项校核卡片（4 项）：**
- 装配 von Mises 强度
- 服役最大 von Mises 强度
- 交变轴向疲劳
- 螺纹脱扣
- 每项一个 PassBadge/FailBadge/WaitBadge

**关键数值卡片（网格布局）：**
- 预紧力范围 (F_preload_min / F_preload_max)
- 装配扭矩范围 (MA_min / MA_max)
- 装配/服役 von Mises 应力
- 疲劳：许用应力幅 vs 实际应力幅
- 脱扣安全系数（如启用）

**警告与建议卡片：**
- 直接消费 core 返回的 `warnings` + `recommendations`

#### 2.3 文本报告导出

- 添加"导出文本报告"按钮
- 输出内容：scope_note、输入摘要、分项结果、建议

#### 2.4 样式规则

- PassBadge/FailBadge/WaitBadge 样式（与螺栓连接一致）
- 自动填充字段（d2, d3, As 自动导出时）使用 AutoCalcCard 蓝色样式
- 结果卡片使用 SubCard 样式

#### 2.5 主窗口注册

在 `main_window.py` 的 `self.modules` 列表中添加：
```python
("轴向受力螺纹连接", BoltTappedAxialPage(self))
```

### 3. PDF 报告

新建 `app/ui/report_pdf_tapped_axial.py`。

#### 报告结构

1. **标题页**：轴向受力螺纹连接校核报告
2. **适用范围声明**：突出显示 scope_note
3. **输入摘要表**：螺纹规格、材料、预紧参数、载荷范围、疲劳参数
4. **分项校核结果**：4 个 pill 状态（装配强度、服役最大强度、疲劳、螺纹脱扣）
5. **详细计算结果**：各块关键数值
6. **警告与建议**：消费 core 的 warnings + recommendations

#### 依赖处理

- 使用 reportlab（可选依赖）
- 复用 report_pdf_common.py 公共组件
- 未安装 reportlab 时按钮灰显或点击提示

#### 不包含

- 不引用 clamped、FK_residual、R3-R8 等夹紧连接语义
- 不包含夹紧力示意图

### 4. 测试策略

#### Core 测试（扩展 tests/core/bolt/test_tapped_axial_joint.py）

现有 6 个基础测试，补充：
- 标准引用值验证：手算 benchmark，`pytest.approx(rel=1e-3)`
- 边界条件：FA_min == FA_max（静载）、FA_min == 0（脉动）、装配不通过
- 脱扣未激活：确认固定 shape 返回
- 表面处理影响：rolled vs cut
- 寿命系数：load_cycles < 2e6 和 >= 2e6

#### UI 测试（扩展 tests/ui/test_bolt_tapped_axial_page.py）

现有 4 个基础测试，补充：
- 计算集成：点击计算后结果 badge 状态正确
- 结果卡片内容：关键数值 label 存在
- 文本报告导出：内容包含 scope_note

#### PDF 测试（tests/ui/test_bolt_tapped_axial_optional_pdf.py）

- `pytest.importorskip("reportlab")` smoke test
- 验证文件生成且大小 > 0

### 5. Agent Team 执行策略

#### 文件归属与执行顺序

```
Phase 1: Core 审查修正（core-engineer）
  core/bolt/tapped_axial_joint.py — 标准引用注释、表值核对、错误信息中文化
  core/bolt/__init__.py — 确认导出
  tests/core/bolt/test_tapped_axial_joint.py — 补充 benchmark 测试

Phase 2: UI 补全 + 测试（ui-engineer，依赖 Phase 1）
  app/ui/pages/bolt_tapped_axial_page.py — 计算按钮、结果卡片、文本导出
  app/ui/main_window.py — 注册模块
  tests/ui/test_bolt_tapped_axial_page.py — 补充结果展示测试

Phase 3: PDF 报告（ui-engineer，依赖 Phase 2）
  app/ui/report_pdf_tapped_axial.py — 新建
  tests/ui/test_bolt_tapped_axial_optional_pdf.py — smoke test

Phase 4: 收尾（code-reviewer + 文档）
  code-reviewer 审查全部变更
  examples/ — 确认示例可跑通
  CLAUDE.md — 更新模块状态
  全量回归测试
```

#### 串行原因

- Phase 1 锁定 core 输出 schema 后 Phase 2/3 才能正确消费
- bolt_tapped_axial_page.py 单文件不能多 agent 同时改
- Phase 3 PDF 依赖 Phase 2 的结果渲染模式

## Files Affected

### 修改
- `core/bolt/tapped_axial_joint.py` — 标准引用、表值修正、错误信息中文化
- `core/bolt/__init__.py` — 确认导出
- `app/ui/pages/bolt_tapped_axial_page.py` — 计算集成、结果展示、文本导出
- `app/ui/main_window.py` — 注册新模块
- `tests/core/bolt/test_tapped_axial_joint.py` — 补充测试
- `tests/ui/test_bolt_tapped_axial_page.py` — 补充测试
- `CLAUDE.md` — 更新模块状态

### 新建
- `app/ui/report_pdf_tapped_axial.py` — PDF 报告
- `tests/ui/test_bolt_tapped_axial_optional_pdf.py` — PDF smoke test（已有骨架）

### 不改动
- `core/bolt/calculator.py` — 现有 VDI 2230 不动
- `app/ui/pages/bolt_page.py` — 现有螺栓连接不动
