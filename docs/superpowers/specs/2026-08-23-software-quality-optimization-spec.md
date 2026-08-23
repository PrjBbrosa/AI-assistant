# Local Engineering Assistant 软件质量优化 Spec

- 日期：2026-08-23
- 状态：Draft for implementation
- 来源：`docs/reports/2026-08-23-full-software-quality-review.md`

## 1. 目标

在不夸大标准覆盖范围的前提下，把软件提升为“结果可信、输入高自动化、界面精致、运行稳定、发布可复现”的工程预校核工具。

本 spec 的第一优先级不是增加更多公式，而是建立一个不能被异常门槛、减载系数、非有限数或错配材料绕过的可信计算合同。

## 2. 非目标

- 不在一个版本中把所有模块升级为完整 DIN/VDI/ISO 签发实现。
- 不一次性重写全部页面或替换 PySide6。
- 不把经验默认或目录值包装成权威标准值。
- 不为了统一架构而改变已验证公式结果。
- 不在没有标准原文证据时新增精确条号、表号或完整标准声明。

## 3. 全局质量合同

### Q-01 结论可信合同

任何 `PASS` 必须同时满足：

1. 所有参与判定的输入均为有限数。
2. 所有物理几何关系合法。
3. 所有要求型安全系数 `>= 1.0`。
4. 所有定义为放大/分布的载荷系数 `>= 1.0`。
5. 必需检查均已执行；缺输入时为 `incomplete/not_checked`，不能被 `all([])` 或默认真值吞掉。
6. 模式和枚举已明确验证，不允许静默降级。
7. 简化模型只产生“预校核”级结论，不能展示为正式标准签发。

### Q-02 数值入口合同

所有公开 calculator 使用共享验证 API：

```python
require_mapping(data, "data")
section(data, "loads")
finite_float(value, name)
positive_float(value, name, allow_zero=False)
bounded_float(value, name, min_value=..., max_value=..., inclusive=...)
enum_value(value, name, allowed={...})
```

要求：

- `bool` 不得被当作数字接受。
- `NaN/+Inf/-Inf` 一律拒绝。
- 错误统一为模块 `InputError`，包含稳定字段路径和当前值。
- UI 约束用于提前反馈，不能代替 core 防线。
- CLI、保存输入和直接 API 调用得到相同合法域。

### Q-03 结果状态合同

统一状态：

- `pass`：所有必需正式/预校核检查通过。
- `fail`：至少一个必需检查失败。
- `incomplete`：必需输入或必需检查缺失。
- `not_checked`：该检查因条件不适用或用户未启用而未执行。
- `reference_only`：参考估算，不进入总体判定。

每个 check 必须含：`id`、`label_zh`、`status`、`actual`、`limit`、`unit`、`model_level`、`message`、`source_kind`。

### Q-04 输入来源合同

字段和值应能标识来源：

- `user`：用户手填。
- `preset`：软件内置材料/等级/目录值。
- `derived`：由其他输入公式派生。
- `recommended`：基于工况的建议值，用户可覆盖。
- `imported`：从输入条件或数据文件加载。

报告必须显示关键强度、许用值、安全门槛和载荷系数的来源。

## 4. P0 计算与接线要求

### CALC-S01 安全系数下限

适用字段至少包括：

- 螺栓与轴向螺纹 `thread_strip.safety_required`。
- 花键 `checks.flank_safety_min`。
- 蜗轮 `required_contact_safety/required_root_safety`。
- 已有过盈 `slip_safety_min/stress_safety_min` 保持同一合同。

验收：

- `<1`：core 抛 `InputError`，UI 就地红色提示，计算按钮不能产生结果。
- `=1`：允许，但 UI 显示“最低理论门槛”提示。
- `>1`：正常计算。
- 覆盖 direct core、UI payload、保存/加载输入三条路径。

### CALC-S02 载荷放大系数

`KA/KV/KHα/KHβ` 及语义为放大/分布的同类字段必须 `>=1`。

如业务确有 `0~1` 的载荷参与比例，新增明确字段，例如 `load_share_ratio`，并限定 `0<ratio<=1`；不得用放大系数表达。

验收：任何工况不能通过把放大系数从 1 降到 0.1 而由 FAIL 变 PASS。

### CALC-S03 有限数

将有限数验证覆盖赫兹、过盈、蜗轮、缓冲块、螺栓、花键和轴向螺纹所有标量。

验收：对每个 calculator 参数化注入 `nan/inf/-inf`；无原始异常、无结果对象、无导出可用状态。

### CALC-S04 自动柔度几何

要求：

- cylinder：`D_A > d_h > 0`。
- sleeve：`D_outer > D_inner > 0`。
- cone：保持并补齐全部直径关系。
- multi-layer：每层独立验证；禁止空层列表。
- 所有返回值：`area>0`、`delta>0` 且有限。
- 完整螺栓计算：`0 < phi <= 1` 且 `0 < phi_n < 1`。

验收：所有负面积、负柔度、零面积和非法载荷分配均在进入主公式前被拒绝。

### INPUT-S01 轴向螺纹材料等级单一事实源

UI 选项变更契约：

- `8.8 → Rp0.2=640 MPa`。
- `10.9 → Rp0.2=900 MPa`。
- `12.9 → Rp0.2=1080 MPa`。
- 以上数值需由当前项目材料表统一提供；如材料表采用不同值，以表为准并有测试。
- 预设等级下 `Rp0.2` 只读、卡片显示自动填充来源。
- 增加 `自定义`，此时允许编辑，必须填写材料来源或显示“用户值”。
- 加载旧文件时：grade 与 Rp0.2 不一致则显示迁移确认，不静默覆盖。

## 5. P1 输入自动化与模型要求

### INPUT-S02 共享 FieldSchema

最小数据结构：

```python
@dataclass(frozen=True)
class FieldSchema:
    field_id: str
    label: str
    unit: str
    value_type: Literal["float", "int", "enum", "text", "bool"]
    required: bool
    min_value: float | None
    max_value: float | None
    min_inclusive: bool
    max_inclusive: bool
    finite: bool
    options: tuple[str, ...]
    default: Any
    mapping: tuple[str, str] | None
    source_kind: str
    visible_when: Condition | None
    required_when: Condition | None
    help_ref: str | None
```

Schema 驱动：控件、即时验证、payload、保存/加载、必填标记、范围提示和字段合同测试。

迁移顺序：轴向螺纹 → 赫兹 → 花键 → 蜗轮 → 过盈 → 主螺栓 → 缓冲块。每次只迁移一个页面，保持结果不变。

### AUTO-S01 工程自动化等级

每个自动填值必须满足：

- 用户看得到来源和是否可覆盖。
- 上游变化会立即使所有下游值、结果和导出失效。
- 不适用字段从 payload 移除，而不是仅隐藏。
- 自动值不能覆盖用户自定义，除非用户确认切换回预设。
- 报告记录最终值、来源和被覆盖状态。

### MODEL-S01 模型范围

每个模块结果头部显示：

- 模型等级：正式子集 / 简化预校核 / 快速估算。
- 覆盖工况。
- 明确未覆盖项。
- 当前输入是否处于适用范围。

赫兹首版明确“只支持外接触/正曲率”；内接触另立功能 spec。

### MODEL-S02 独立基准矩阵

每个模块至少包含：

- 2 个正常通过工况。
- 2 个正常失败工况。
- 1 个标准/教科书/经确认商业软件的独立参考工况。
- 关键边界和量纲缩放关系。
- 允许误差、来源和模型差异解释。

禁止只用当前 calculator 生成预期值后再断言自身正确。

## 6. UI 品质要求

### UI-S01 支持尺寸

选择并公告一种策略：

- 推荐基线：最小支持 `1180×720`；低于此尺寸不允许继续缩小。
- 若坚持 `900×620`，必须实现折叠侧栏、动作 overflow 和响应式标题。

任何支持尺寸下：

- 关键模块名、标题和按钮不得截字。
- 非内容控件不得出现水平滚动条。
- 主操作始终可见。
- 结果状态不与 footer 重复争夺主层级。

### UI-S02 视觉 token

把以下内容收敛为统一 token：8 pt spacing grid、卡片内边距、圆角、边框、按钮高度、icon size、状态色、字体层级、正文行高、数字字体、focus ring。

验收截图至少覆盖：正常/hover/focus/pressed/disabled/error/read-only/auto-filled。

### UI-S03 光学对齐

视觉验收不是只比 QWidget geometry，还要检查：

- 图标视觉中心与文字基线。
- 短标签和长标签的左边缘与重心。
- 按钮文字在实色底上的光学垂直居中。
- 状态胶囊文字与图标的视觉重量。
- 圆角卡片四角像素无底色漏边。
- 单位列和数值列按基线对齐。

差异以真实目标平台截图为准，offscreen 只做预检。

### UI-S04 状态与语言

- 中文为主语言：`预校核通过/预校核不通过/负载能力`。
- 符号和标准缩写保留英文，但提供中文解释。
- 正式失败、警告、参考超限、未校核使用不同图标与语义颜色。
- 页面只保留一个主总体状态；footer 只显示运行/保存/错误信息。

### UI-S05 可访问性

- 所有 icon-only 控件 hit area ≥28×28，推荐 32×32。
- Tab 顺序符合页面阅读顺序。
- focus 可见且对比度足够。
- 状态不能只靠红绿区分。
- 200% 缩放下不截字。
- tooltip 不是唯一帮助载体。

## 7. 性能与架构要求

### PERF-S01 性能预算

在发布构建、目标 Windows 机器记录：

- 冷启动到窗口可交互：P95 < 1.5 s。
- 热启动到窗口可交互：P95 < 0.8 s。
- 源码环境 MainWindow 构造：P95 < 350 ms。
- 普通页面首次导航：P95 < 150 ms。
- 蜗轮页面首次导航：优化后 P95 < 180 ms。
- 单次样例计算+首屏结果：P95 < 100 ms。
- UI 主线程单次阻塞 >100 ms 必须有进度或异步策略。

### PERF-S02 图表懒加载

matplotlib 仅在应力曲线真正首次可见或首次有数据时导入并创建。打开蜗轮概览/几何页不得加载 canvas。

### ARCH-S01 渐进解耦

目标层次：

```text
Page shell
  -> FieldSchema + form renderer
  -> Page controller / dependency rules
  -> calculator adapter
  -> ResultViewModel
  -> result renderer + report renderer
```

要求：

- calculator 仍为纯函数。
- 一个页面迁移完成前不强迫其他页面同步重写。
- ResultViewModel 成为 UI 与报告的同一事实源，避免结果页和导出漂移。
- 不用 service locator 或全局 mutable state 替代现有清晰依赖。

### ARCH-S02 文件规模护栏

不设置机械的行数门禁，但新功能不得继续堆入已超过 1000 行的页面类；新增职责优先进入 schema/controller/presenter/helper，并由测试覆盖。

## 8. 导出与发布要求

### EXPORT-S01 原子导出

- 同目录临时文件写入。
- 完成后验证文件存在、非空，DOCX 可打开 zip，PDF 有有效 header。
- 原子替换最终路径。
- 失败时不保留半成品；旧有效文件不被破坏。

### EXPORT-S02 报告追溯

报告包含：软件版本/commit、生成时间和时区、模块与模型等级、输入摘要及来源、安全门槛、总体和分项状态、未校核项、警告、假设、输入文件 hash。

### RELEASE-S01 可复现环境

- 增加 constraints/lock，并定义更新流程。
- CI 运行 core、offscreen UI、report、文档链接、`git diff --check`。
- Windows runner 构建 PyInstaller 产物并做 smoke。
- 发布前生成版本化检查单和已知限制。

## 9. Definition of Done

“软件质量优化”完成必须同时满足：

1. 本 review 的 P0 全部关闭，且反例测试先红后绿。
2. 全量测试通过，不通过放宽旧断言掩盖问题。
3. 每个模块至少一组独立来源基准。
4. 支持尺寸截图矩阵通过；Windows 前景 smoke 通过。
5. 启动和页面导航满足性能预算。
6. UI、结果、TXT/PDF/DOCX 对同一结论和警告完全一致。
7. README、用户指南、模型范围和当前能力一致。
8. 工作区只包含本次批准范围内的变更。

