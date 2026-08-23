# Local Engineering Assistant 软件质量优化实施 Plan

- 日期：2026-08-23
- 依赖 spec：`docs/superpowers/specs/2026-08-23-software-quality-optimization-spec.md`
- 原则：先关闭虚假 PASS，再提高自动化和 UI，再做架构/发布升级

## 0. 实施规则

1. 每个阶段建立独立分支或独立提交组，不混入无关清理。
2. 计算 bug 先补失败测试，再改 core，再接 UI 和报告。
3. 每个跨出口字段必须 grep UI、文本报告、PDF、保存/加载、CLI、帮助和测试消费者。
4. offscreen 测试通过后，UI 变更仍需真实前景手势和截图验收。
5. 不把未核对标准原文的简化公式提升为完整标准声明。

## Phase 0：冻结基线与验收矩阵（0.5–1 天）

### 任务

- 记录当前 branch、HEAD、Python/Qt/依赖版本、909 测试基线。
- 将本 review 的 P0 运行探针转成 `tests/core/...` 失败测试。
- 建立模块 × 输入路径 × 输出出口矩阵。
- 决定 UI 最小支持尺寸策略：提高最小尺寸，或实现响应式布局。

### 产物

- `docs/reports/...-quality-baseline.md`。
- P0 失败测试提交，明确当前预期失败数。
- 用户确认的 UI 支持尺寸。

### Gate

- 每个 P0 都有可复现、能在修复前失败的测试。
- 不修改任何旧期望去迁就当前错误结果。

## Phase 1：P0 可信计算合同（2–4 天）

### 1.1 共享有限数和范围验证

- 新增 `core/_validation.py`。
- 统一 dict/section/finite/range/enum 入口。
- 先迁移赫兹、过盈、蜗轮、缓冲块，再统一螺栓/花键现有 helper。
- 保留模块级 `InputError` 兼容；必要时由共享错误基类派生。

### 1.2 安全阈值和放大系数

- 螺栓/轴向螺纹/花键/蜗轮安全下限 `>=1`。
- 花键/过盈/蜗轮 `KA/KV/KH* >=1`。
- 参数化测试覆盖 `<1/=1/>1/NaN/Inf`。

### 1.3 螺栓柔度几何

- 修复 cylinder/sleeve 外径-内径关系。
- 多层逐层验证。
- `_resolve_compliance()` 统一验证输出正且有限。
- 验证 `0<phi_n<1`。

### 1.4 轴向螺纹 grade 接线

- 抽取共享强度等级表。
- 预设 grade 自动填充并锁定 `Rp0.2`。
- 增加自定义材料路径和旧输入迁移提示。
- 增加 UI 联动、payload、保存/加载、报告追溯测试。

### Gate

- 所有 P0 反例由失败变为明确 `InputError`，不得只变成普通 FAIL。
- 全量测试通过。
- UI 输入非法值不能留下旧结果或可导出状态。
- 逐页 smoke：默认样例、危险样例、保存/加载、导出。

## Phase 2：P1 输入自动化与模型合同（3–6 天）

### 2.1 共享 FieldSchema MVP

- 先在轴向螺纹页实现 schema 驱动的类型、范围、有限数、枚举和条件必填。
- 保持现有布局，不同时做视觉重构。
- 将 schema 同时用于控件验证、payload 和字段合同测试。
- 评估后迁移赫兹和花键。

### 2.2 即时错误反馈

- 非法字段边框、简短原因、定位到首个错误。
- 执行按钮可点击，但执行时聚焦并解释所有错误；或在错误存在时禁用，二选一保持全局一致。
- 输入修改立即清除旧结果和导出状态。

### 2.3 自动填充来源

- grade/material/fit/mode 联动显示 `预设/派生/推荐/用户覆盖`。
- 赫兹许用应力只做“建议值+来源”，默认不把模糊材料名称自动变成权威许用值。
- 蜗轮和过盈显示材料默认值的适用温度/工况和用户覆盖状态。

### 2.4 模型等级

- 统一 `正式子集/简化预校核/快速估算/参考项`。
- 结果、报告、帮助同源展示覆盖与未覆盖项。
- 花键/蜗轮/赫兹先落地。

### Gate

- 已迁移页面没有页面私有的重复数值解析逻辑。
- 所有自动值有来源，所有用户覆盖有可见状态。
- 模式切换后 payload 不包含隐藏/无关字段。
- UI、TXT、PDF、DOCX 状态一致。

## Phase 3：P1 高品质 UI 精修（4–7 天）

### 3.1 支持尺寸修复

- 若提高最小尺寸：用内容实测确定数值并更新窗口、README 和用户指南。
- 若做响应式：侧栏折叠为图标/抽屉；次要动作进入 overflow；章节列表不得水平滚动。
- 对 7 模块跑最小/默认/大窗口截图矩阵。

### 3.2 信息层级

- 结果页统一：总体 → 关键指标 → 分项 → 追溯。
- 删除 footer 中重复总体状态。
- 将长原始追踪行折叠到“计算详情”。
- 中文主标签统一，变量符号作为副标签。

### 3.3 组件品质

- 帮助按钮 hit area 提升到 28–32 px。
- 统一按钮主次层级；每页只保留一个主行动作。
- 统一 hover/focus/pressed/disabled/error/read-only/auto-filled。
- 替换全局 QComboBox monkey patch 为应用控件或受控代理实现。

### 3.4 光学与跨平台验收

- macOS 前景检查：圆角、popup、native dialog、字体、焦点、200% 缩放。
- Windows 前景检查：DPI 100/125/150%、标题栏、combo popup、PDF dialog。
- 对标题基线、icon center、按钮文字重心和单位列做截图标注。

### Gate

- 支持尺寸内无关键截字、非内容水平滚动和隐藏主操作。
- 状态不只依赖颜色。
- 7 模块 × 关键状态截图通过人工 review。
- 前景结果与 offscreen 基线差异均有解释或修复。

## Phase 4：P2 架构和性能（4–8 天，渐进执行）

### 4.1 ResultViewModel

- 定义统一 check/status/source/model-level 数据结构。
- 先接一个小模块（赫兹），让页面和报告使用同一模型。
- 验证后按花键、蜗轮、过盈、轴向螺纹、主螺栓、缓冲块迁移。

### 4.2 页面拆分

- 不按行数硬拆；按职责拆 `schema/controller/presenter/report`。
- 新功能不得继续扩大 `bolt_page.py` 和 `interference_fit_page.py`。
- 每次拆分前后用 golden result 和 UI smoke 保持行为一致。

### 4.3 蜗轮图表懒加载

- 先写探针断言打开蜗轮概览不 import matplotlib。
- 第一次进入曲线章节或首次有结果时才创建 canvas。
- 记录构造时间和 RSS 前后对比。

### 4.4 字体与资源

- 集中字体栈，移除不存在字体引发的别名扫描。
- 检查图片/SVG/文档资源是否在打包中按需加载。

### Gate

- 源码 MainWindow 构造 P95 <350 ms。
- 普通页首次导航 P95 <150 ms；蜗轮 P95 <180 ms。
- 计算+结果首屏 P95 <100 ms。
- 重构前后样例 JSON 关键数值和状态一致。

## Phase 5：P2 发布、导出与可复现性（3–5 天）

### 5.1 依赖与 CI

- 建立 constraints/lock 和升级说明。
- CI 拆为 core、offscreen UI/report、static hygiene。
- 增加 README 能力表/实现探针，修复花键保存/加载的文档漂移。

### 5.2 原子导出与追溯

- TXT/DOCX/PDF 临时写入、验证、原子替换。
- 报告加入版本、时间、模块、模型等级、输入 hash、来源和未校核项。
- 故障注入测试：无权限、目标占用、磁盘写失败、半成品清理。

### 5.3 Windows 打包 smoke

- 干净 runner 构建 PyInstaller。
- 启动、切换 7 模块、加载样例、计算、保存输入、导出三格式。
- 记录冷/热启动和产物大小。

### Gate

- 新环境可从锁定依赖复现。
- Windows 构建和 smoke 自动通过。
- 导出失败不破坏已有文件、不留下半成品。
- README、用户指南、关于页和发布说明一致。

## Phase 6：P3 标准与产品深化（持续）

- 为每个模块建立标准/教科书/商业软件交叉基准库。
- 对过盈经验系数追溯原始来源；无法追溯则降级为显式经验模型。
- 规划赫兹内接触、蜗轮完整标准能力、花键正式几何/承载、材料与标准库。
- 材料库上线前定义版本、来源、温度范围、热处理状态和用户覆盖审计。
- “材料与标准库”未实现期间在侧栏标注占位或从稳定版隐藏。

## 推荐提交切分

1. `test: capture false-pass and nonfinite regressions`
2. `fix: enforce finite safety and load-factor domains`
3. `fix: reject nonphysical bolt compliance geometry`
4. `fix: bind tapped-joint grade to material strength`
5. `feat: add shared field validation schema pilot`
6. `fix: make supported window size layout-safe`
7. `refactor: unify result status and report contract`
8. `perf: defer worm stress chart construction`
9. `build: lock dependencies and add Windows smoke`
10. `docs: align capabilities model scope and release limits`

## 最终验收清单

- [ ] P0 反例全部被拒绝。
- [ ] 全量 pytest 通过；无放宽断言。
- [ ] 各模块独立基准矩阵通过。
- [ ] UI→payload→core→result→report 接线合同通过。
- [ ] 最小/默认/高 DPI 前景截图通过。
- [ ] macOS 开发运行 smoke 通过。
- [ ] Windows 打包 smoke 通过。
- [ ] 性能预算通过。
- [ ] 导出原子性和故障注入通过。
- [ ] README/用户指南/帮助/已知限制同步。
- [ ] 只提交本计划相关文件，保留工作区其他改动。

