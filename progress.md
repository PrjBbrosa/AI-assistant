# Progress Log

## Session: 2026-03-22

### Phase 18: Spline Fit Engineering Hardening Execution
- **Status:** in_progress
- Actions taken:
  - 在隔离 worktree `/.worktrees/spline-fit-hardening` 中执行整改
  - 完成 Stage A / Task 1：文案降级、UI disclaimer、历史报告补充说明
  - 完成 Stage A / Task 2：场景 B warning 上浮、材料联动、整数齿数校验、设计载荷 trace
  - 开始为 Stage B 搜索公开权威来源，确认几何与强度链需要依赖 DIN Media + eAssistant + FVA + 标准件目录组合
  - 完成 Stage B 第一轮落地：
    - 引入 `reference_dimensions` 与 `approximate` 两种几何模式
    - 用公开小规格样例 `W/N 15 x 1.25 x 10` 建立 geometry benchmark
    - 在 UI 中新增参考直径与显式尺寸输入
    - 将场景 A verdict 语义降级为 `simplified_precheck`
    - 新增公开来源文档与样例 JSON
  - 运行 spline 定向回归：`34 passed`
  - 运行 `examples/spline_case_01.json` smoke：`overall_pass=True`, `overall_verdict_level=simplified_precheck`
  - 运行全仓回归：`235 passed`
  - 完成复审结论：模块定位更新为“可追溯的 simplified precheck”，不升格为正式工程校核候选
- Files created/modified:
  - app/ui/pages/spline_fit_page.py (updated)
  - core/spline/calculator.py (updated)
  - core/spline/geometry.py (updated)
  - tests/ui/test_spline_fit_page.py (updated)
  - tests/core/spline/test_calculator.py (updated)
  - tests/core/spline/test_geometry.py (updated)
  - docs/reports/2026-03-22-spline-interference-fit-module.md (updated)
  - docs/references/2026-03-22-spline-fit-sources.md (created)
  - examples/spline_case_01.json (created)
  - examples/spline_case_02.json (created)
  - findings.md (updated)
  - task_plan.md (updated)
  - progress.md (updated)

### Phase 16: Worm Load-Capacity Upgrade
- **Status:** complete
- **Started:** 2026-03-22
- Actions taken:
  - 审查蜗杆模块页面、calculator、样例和测试，确认当前范围仅为 `DIN 3975` 几何与基础性能
  - 识别出功率链路不闭合、几何一致性缺失、关键字段未入模和 Load Capacity 占位四类高风险问题
  - 在隔离 worktree `/.worktrees/worm-load-capacity` 中建立执行环境，避免影响主工作区未提交改动
  - 运行蜗杆模块基线回归：`19 passed`
  - 编写蜗杆模块升级 design spec 与 implementation plan
  - 通过 TDD 修复功率链路，并接入 `friction_override`
  - 新增 Method B 最小子集：载荷、齿面应力、齿根应力、扭矩波动和安全系数
  - 扩展 UI 字段、Load Capacity 页面、结果摘要和样例
  - 运行蜗杆 + UI + hertz 定向回归：`30 passed`
- Files created/modified:
  - docs/superpowers/specs/2026-03-22-worm-load-capacity-design.md (created)
  - docs/superpowers/plans/2026-03-22-worm-load-capacity.md (created)
  - core/worm/calculator.py (updated)
  - app/ui/pages/worm_gear_page.py (updated)
  - tests/core/worm/test_calculator.py (updated)
  - tests/ui/test_worm_page.py (updated)
  - examples/worm_case_01.json (updated)
  - examples/worm_case_02.json (updated)
  - README.md (updated)
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)

## Session: 2026-03-01

### Phase 1: Requirements & Discovery
- **Status:** in_progress
- **Started:** 2026-03-01
- Actions taken:
  - 读取并确认需使用 brainstorming 与 planning-with-files 技能
  - 检查仓库目录，确认为空
  - 初始化 task_plan.md / findings.md / progress.md
  - 检索并整理 VDI 2230 公开可引用资料（VDI 官方页、eAssistant、PCB 白皮书）
  - 收敛首版实现范围为 VDI 2230 核心链路（R1-R8）
- Files created/modified:
  - task_plan.md (created)
  - findings.md (created, updated)
  - progress.md (created, updated)

### Phase 2: Planning & Structure
- **Status:** complete
- Actions taken:
  - 编写设计文档，比较 3 种实现路径并确定 Python CLI 方案
  - 定义输入模型（fastener/tightening/loads/stiffness/bearing/checks）
  - 明确首版范围边界（R1-R8 核心链路）与未覆盖项
- Files created/modified:
  - docs/plans/2026-03-01-vdi2230-bolt-tool-design.md (created)
  - task_plan.md (updated)

### Phase 3: Implementation
- **Status:** complete
- Actions taken:
  - 编写中文计算说明文档，定义公式、变量、单位与判定条件
  - 实现 Python CLI：输入校验、几何推导、核心计算、结果输出
  - 增加两个样例输入（失败工况 / 通过工况）与 README 使用说明
- Files created/modified:
  - docs/vdi2230-calculation-spec.md (created)
  - src/vdi2230_tool.py (created)
  - examples/input_case_01.json (created)
  - examples/input_case_02.json (created)
  - README.md (created)

### Phase 4: Testing & Verification
- **Status:** complete
- Actions taken:
  - 运行样例工况 1，验证输出结构及失败判定路径
  - 运行样例工况 2，验证通过路径
  - 修复浮点比较导致的残余夹紧力伪失败（加入容差）
- Files created/modified:
  - src/vdi2230_tool.py (updated)
  - examples/output_case_01.json (created)
  - examples/output_case_02.json (created)

### Phase 5: Delivery
- **Status:** complete
- Actions taken:
  - 按用户新目标输出“个人版 eAssistant 风格平台”实施路线图
  - 明确“平台骨架先行、螺栓模块先落地、其余模块先占位”的执行策略
- Files created/modified:
  - docs/plans/2026-03-01-personal-eassistant-roadmap.md (created)

### Phase 6: Desktop Framework Implementation
- **Status:** complete
- Actions taken:
  - 重构计算内核到 `core/bolt/calculator.py`，保持 CLI 与 GUI 共用
  - 搭建 PySide6 桌面壳：左侧 6 模块导航 + 右侧页面容器
  - 实现“螺栓连接”页面：样例加载、JSON 输入、执行计算、分项判定、结果保存
  - 实现 Claude 风格主题（暖灰底、橙色强调、卡片化布局）
  - 增加 `requirements.txt` 和 `scripts/build_exe.bat` 打包脚本
  - 更新 README 与桌面路线图
- Files created/modified:
  - core/__init__.py (created)
  - core/bolt/__init__.py (created)
  - core/bolt/calculator.py (created)
  - app/main.py (created)
  - app/ui/theme.py (created)
  - app/ui/main_window.py (created)
  - app/ui/pages/bolt_page.py (created)
  - app/ui/pages/placeholder_page.py (created)
  - src/vdi2230_tool.py (updated)
  - requirements.txt (created)
  - scripts/build_exe.bat (created)
  - README.md (updated)
  - docs/plans/2026-03-01-personal-eassistant-roadmap.md (updated)

### Phase 7: Bolt Form UX Upgrade
- **Status:** complete
- Actions taken:
  - 将螺栓页输入从 JSON 文本改为全量结构化表单
  - 全部字段显式展示（fastener/tightening/loads/stiffness/bearing/checks）
  - 保留样例加载、执行校核、结果保存与分项判定摘要
  - 扩展主题样式（输入框、子卡片、单位标签）保证一致视觉
- Files created/modified:
  - app/ui/pages/bolt_page.py (rewritten)
  - app/ui/theme.py (updated)
  - README.md (updated)
  - task_plan.md (updated)

### Phase 8: eAssistant Chapter-Style UI Alignment
- **Status:** complete
- Actions taken:
  - 读取 eAssistant Chapter 14 页面，按 14.2~14.10 重构螺栓页面章节导航
  - 参数按章节重排，并为每个参数增加说明文本与 tooltip
  - 新增螺栓夹紧示意图组件（FM/FA/FK）
  - 结果区改为可读卡片（总体结论、分项状态、关键结果值、建议）
  - 新增“导出结果说明”文本报告，替代 JSON 面向终端用户输出
- Files created/modified:
  - app/ui/pages/bolt_page.py (rewritten, chapter-style)
  - app/ui/widgets/clamping_diagram.py (created)
  - app/ui/widgets/__init__.py (created)
  - app/ui/theme.py (updated)
  - README.md (updated)
  - task_plan.md (updated)
  - findings.md (updated)

## Session: 2026-03-16

### Phase 9: Interference-Fit DIN 7190 Gap Closure
- **Status:** complete
- **Started:** 2026-03-16
- **Completed:** 2026-03-17
- Actions taken (planning):
  - 读取当前 `core/interference/calculator.py`、`app/ui/pages/interference_fit_page.py` 与相关测试，梳理字段到 payload 到结论的映射关系
  - 提取并审阅附件 `eAssistantHandb_en - fit.pdf` 第 14 章内容，对照 DIN 7190 / eAssistant 的输入项、结果项和说明项
  - 确认用户本轮明确排除 `centrifugal force` 与 `stepped hub geometry`
  - 识别并记录 P0/P1 问题：安全系数未进入需求过盈、联合作用未进入总判定、`fit_range_ok` 语义偏乐观、若干参数缺少来源追溯
  - 编写正式实施计划
- Actions taken (implementation — Chunk 1: Correctness):
  - 修正 `slip_safety_min` 参与 `p_required` 和 `delta_required` 计算
  - 将 `combined_ok`（扭矩+轴向联合作用）纳入 `overall_pass`
  - 收紧 `p_required` 取 torque/axial/combined/gap 的 max
  - UI 展示 combined check 结果和 demand breakdown
  - `curve_points` 标注为纯绘图选项
- Actions taken (implementation — Chunk 2: Fit Selection & Assembly):
  - 创建 `core/interference/fit_selection.py`：ISO 286 优选配合 (H7/p6, H7/s6, H7/u6) + 用户偏差换算
  - 创建 `core/interference/assembly.py`：shrink_fit（热装温度）+ force_fit（压入/压出力）+ manual_only
  - 集成到 calculator 和 UI 页面
- Actions taken (implementation — Chunk 3: Repeated Load, Traceability & Close-out):
  - 在 calculator 中增加 `repeated_load_mode` 开关与适用性检查（l/d > 0.25, 同模量, 无弯矩）
  - 报告追溯：material preset、roughness profile、fit source、assembly method 全链路
  - 更新 examples 示例文件覆盖 tolerance-derived + assembly mode + preset trace
  - 更新 README.md 过盈配合章节
- Verification:
  - 33 interference-specific tests pass
  - 131 total repository tests pass (zero failures)
- Files created/modified:
  - core/interference/calculator.py (major update)
  - core/interference/fit_selection.py (created)
  - core/interference/assembly.py (created)
  - core/interference/__init__.py (updated)
  - app/ui/pages/interference_fit_page.py (major update)
  - tests/core/interference/test_calculator.py (expanded to 15 tests)
  - tests/core/interference/test_fit_selection.py (created, 5 tests)
  - tests/core/interference/test_assembly.py (created, 3 tests)
  - tests/ui/test_interference_page.py (expanded to 13 tests)
  - examples/interference_case_01.json (updated with assembly/fit metadata)
  - examples/interference_case_02.json (updated with assembly/fit metadata)
  - README.md (updated)
  - docs/superpowers/plans/2026-03-16-interference-fit-gap-closure.md (created)
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)

## Session: 2026-03-17

### Phase 10: Bolt Page Deep Review & Remediation Planning
- **Status:** in_progress
- **Started:** 2026-03-17
- Actions taken:
  - 读取并交叉比对 `bolt_page.py` 的字段定义、payload 构建、结果渲染与 `calculator.py` 的实际判据
  - 对 `bolt_flowchart.py` 的流程图摘要、输入回显和重复渲染行为做 headless 验证
  - 用脚本复现并记录以下问题：
    - R5 页面/报告展示值与正式判据不一致
    - 自定义热膨胀系数缺失时静默回退为钢默认值
    - 输入条件 snapshot round-trip 对标准螺距会崩溃
    - `calculation_mode` 和多项 choice 状态不会恢复
    - 多层自定义 `alpha` 空值抛原生 `ValueError`
    - R 步骤详情页重复计算后控件翻倍
  - 编写正式审查报告与 superpowers 后续执行计划
- Files created/modified:
  - docs/review/2026-03-17-bolt-page-deep-review.md (created)
  - docs/superpowers/plans/2026-03-17-bolt-page-review-followup.md (created)
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Case 01 严苛工况 | `python3 src/vdi2230_tool.py --input examples/input_case_01.json` | 至少部分校核失败 | 装配/服役/附加载荷失败，残余夹紧力通过 | ✓ |
| Case 02 温和工况 | `python3 src/vdi2230_tool.py --input examples/input_case_02.json` | 全部校核通过 | 全部校核通过，`overall_pass=true` | ✓ |
| 语法检查 | `python3 -m py_compile src/vdi2230_tool.py` | 无报错 | 无报错 | ✓ |
| 桌面框架语法检查 | `python3 -m py_compile app/main.py app/ui/main_window.py app/ui/theme.py app/ui/pages/bolt_page.py` | 无报错 | 无报错 | ✓ |
| 桌面框架冒烟测试 | `QT_QPA_PLATFORM=offscreen` 启动并自动退出 | 可启动 | `GUI_SMOKE_OK` | ✓ |
| 表单版语法回归 | `python3 -m py_compile app/ui/pages/bolt_page.py` | 无报错 | 无报错 | ✓ |
| 表单版 GUI 冒烟 | `QT_QPA_PLATFORM=offscreen` 启动新界面并退出 | 可启动 | `GUI_SMOKE_OK` | ✓ |
| Chapter版语法回归 | `python3 -m py_compile app/ui/pages/bolt_page.py app/ui/widgets/clamping_diagram.py` | 无报错 | 无报错 | ✓ |
| Chapter版 GUI 冒烟 | `QT_QPA_PLATFORM=offscreen` 启动并退出 | 可启动 | `GUI_SMOKE_OK` | ✓ |
| 过盈配合核心/UI回归 | `python3 -m unittest tests.core.interference.test_calculator tests.ui.test_interference_page -v` | 全部通过 | 10 tests OK | ✓ |
| 螺栓 core/UI 子集回归 | `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py tests/core/bolt/test_compliance_model.py tests/ui/test_input_condition_store.py -q` | 全部通过 | 76 tests OK | ✓ |
| 螺栓页 snapshot 回灌复现 | headless `BoltPage` + `_capture_input_snapshot()` / `_apply_input_data()` | 应能 round-trip | `ValueError: could not convert string to float: '1.5（粗牙）'` | ✗ |
| 螺栓页 calc mode 持久化复现 | headless `BoltPage` 切换 `verify` 后保存/恢复 | 应恢复为 `verify` | 未持久化，恢复后仍为 `design` | ✗ |
| 螺栓页 raw payload choice 恢复复现 | 直接 `_apply_input_data(raw_payload)` | 应恢复 choice 状态 | `joint_type/basic_solid/surface_class/tightening_method/surface_treatment` 全部回到默认值 | ✗ |
| 多层自定义 alpha 校验复现 | 双层 + 第一层材料“自定义”且 `alpha` 留空 | 应给出字段级 `InputError` | 原生 `ValueError: could not convert string to float: ''` | ✗ |
| R 步骤详情页重复渲染复现 | 同一页面重复执行 `_calculate()` | 控件数应稳定 | `54 -> 108`，发生重复堆积 | ✗ |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-03-01 | 残余夹紧力边界值因浮点误差被判失败 | 1 | 在比较中加入工程容差 `residual_tol` |
| 2026-03-16 | `apply_patch` 首次更新 `task_plan.md` 因上下文不匹配失败 | 1 | 先读取带行号的当前文件，再按精确上下文重打补丁 |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 9 complete, Phase 10 in_progress |
| Where am I going? | Phase 10: 螺栓页深度审查后续修复 |
| What's the goal? | 修复螺栓页 save/load round-trip、热参数验证、R5 结果语义、流程图重复渲染 |
| What have I learned? | Phase 9 所有 core+UI+test 工作已完成（33 interference tests, 131 total pass），仅文档收尾遗漏 |
| What have I done? | Phase 9: 正确性修正+ISO 286 配合选择+装配流程+重复载荷+追溯，全部实现并验证 |

## Session: 2026-03-18

### Phase 11: Interference-Fit Chapter Deep Review
- **Status:** complete
- **Started:** 2026-03-18
- Actions taken:
  - 读取并应用 `using-superpowers` 与 `planning-with-files` 技能
  - 检查既有规划文件并切换到“过盈配合深度审查”上下文
  - 记录本轮目标：核对过盈配合章节的 bug、遗漏、逻辑问题，并对照 DIN 7190 / 同类工具案例
  - 检测到仓库存在未提交的螺栓相关修改，本轮不触碰这些文件
  - 首轮审读 `interference` 设计文档与 `calculator.py`，发现设计文档的范围说明已落后于当前实现（fit selection / assembly / repeated load 已实现）
  - 继续审读 `fit_selection.py`、`assembly.py`、`interference_fit_page.py`，确认 UI 已暴露这些能力，且 repeated-load 不并入基础 verdict
  - 开始检查 `tests/core/interference/*` 的断言边界，标记出尚未锁定的风险点（公差带边界、热装冷却项、报告提示语义）
  - 读通 `InterferenceFitPage` 的 payload / render / report 链路与 UI 测试，暂未发现明显“字段未接线”问题，当前风险更偏向边界覆盖与章节说明精度
  - 复现并确认 raw payload -> UI 回灌会被默认选择器覆盖（材料、粗糙度、assembly mode、repeated-load mode）
  - 运行过盈配合专项回归：`33 passed`
  - 对照 eAssistant public DIN 7190 example、eAssistant ISO 286 handbook、MITCalc brochure、RoyMech 公式页完成外部审查
  - 输出正式审查报告 `docs/review/2026-03-18-interference-fit-deep-review.md`
- Files created/modified:
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)
  - docs/review/2026-03-18-interference-fit-deep-review.md (created)

## Session: 2026-03-19

### Phase 12: Interference-Fit Fretting Step Planning
- **Status:** complete
- **Started:** 2026-03-19
- Actions taken:
  - 读取并应用 `brainstorming`、`writing-plans`、`planning-with-files` 技能
  - 用户确认 fretting 按“过盈配合第 5 步增强模块”规划，不做独立页面
  - 用户确认首版 fretting 只输出风险等级与建议，不并入主 verdict
  - 回读当前 `repeated_load / fretting` 代码与测试，确认当前基线仍是 lightweight advanced block
  - 与用户逐段确认 fretting 设计：模块定位、输入与判级、页面结构与集成方式
  - 写出 fretting 正式 spec：`docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md`
  - 写出 fretting implementation plan：`docs/superpowers/plans/2026-03-19-interference-fit-fretting-step.md`
- Files created/modified:
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)
  - docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md (created)
  - docs/superpowers/plans/2026-03-19-interference-fit-fretting-step.md (created)

### Phase 13: Interference-Fit Fretting Step Implementation
- **Status:** complete
- **Started:** 2026-03-19
- **Completed:** 2026-03-19
- Actions taken:
  - 按 TDD 先新增 `tests/core/interference/test_fretting.py`，确认 RED：`core.interference.fretting` 不存在
  - 实现 `core/interference/fretting.py`，输出结构化 Step 5 结果：适用性、风险等级、驱动因素、建议、可信度、notes
  - 在 `core/interference/calculator.py` 中接入新 `fretting` 结果块，并保留 legacy `advanced.repeated_load_mode` 兼容
  - 新增 calculator 集成测试，锁定：
    - fretting 结果存在
    - fretting 不改变 `overall_pass`
    - legacy advanced 开关仍可启用 fretting
  - 升级 `app/ui/pages/interference_fit_page.py`：
    - 用 `Fretting 风险评估` Step 5 替换旧“高级校核”
    - 接入 `fretting.*` payload
    - 支持 legacy load 映射
    - 报告与结果区新增 Step 5 fretting 段落
  - 更新 `examples/interference_case_01.json` 和 `README.md`
- Verification:
  - `python3 -m pytest tests/core/interference/test_fretting.py tests/core/interference/test_calculator.py -q` -> pass
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py -q` -> pass
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/interference/test_fretting.py tests/core/interference/test_calculator.py tests/core/interference/test_fit_selection.py tests/core/interference/test_assembly.py tests/ui/test_interference_page.py -q` -> `41 passed`
  - manual smoke:
    - disabled
    - high-risk while base verdict still pass
    - legacy-switch
    - not-applicable
- Files created/modified:
  - core/interference/fretting.py (created)
  - core/interference/calculator.py (updated)
  - core/interference/__init__.py (updated)
  - tests/core/interference/test_fretting.py (created)
  - tests/core/interference/test_calculator.py (updated)
  - app/ui/pages/interference_fit_page.py (updated)
  - tests/ui/test_interference_page.py (updated)
  - examples/interference_case_01.json (updated)
  - README.md (updated)
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)

### Phase 14: Interference-Fit Closeout
- **Status:** complete
- **Started:** 2026-03-19
- **Completed:** 2026-03-19
- Actions taken:
  - 为 `InterferenceFitPage._apply_input_data()` 增加 raw payload 恢复语义：
    - 缺少 `ui_state` 时，从原始 `materials` / `roughness` / `assembly` / `fit_selection` / `fretting` 输入反推 UI 选择器
    - 无法匹配预设时保留 `自定义`，避免静默覆盖原始输入
  - 新增 UI 回归测试，锁定 custom raw inputs round-trip 行为
  - 为 `fit_selection` 增加公差带边界回归测试，覆盖 `H7/s6` 与 `H7/u6` 的代表 band
  - 新增公开 benchmark 差异说明文档
  - 给历史设计文档与深度审查文档补充当前状态说明，避免继续误读范围边界
- Verification:
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_interference_page.py::InterferenceFitPageTests::test_apply_input_data_preserves_custom_raw_inputs_without_ui_state -q` -> pass
  - `python3 -m pytest tests/core/interference/test_fit_selection.py -q` -> `7 passed`
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest -q` -> `176 passed`
- Files created/modified:
  - app/ui/pages/interference_fit_page.py (updated)
  - tests/ui/test_interference_page.py (updated)
  - tests/core/interference/test_fit_selection.py (updated)
  - docs/references/2026-03-19-interference-public-benchmark-notes.md (created)
  - docs/plans/2026-03-08-interference-fit-din7190-core-design.md (updated)
  - docs/review/2026-03-18-interference-fit-deep-review.md (updated)
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)

### Phase 15: Interference-Fit Hollow-Shaft Support
- **Status:** complete
- **Started:** 2026-03-19
- **Completed:** 2026-03-19
- Actions taken:
  - 读取并应用 `brainstorming`、`test-driven-development`、`writing-plans`、`executing-plans` 技能
  - 结合当前过盈配合主链路与 eAssistant handbook 边界，确定空心轴支持首版只扩展主模型，不同步扩展 speed / service temperature / stepped geometry
  - 写出空心轴 design spec：`docs/superpowers/specs/2026-03-19-interference-fit-hollow-shaft-design.md`
  - 写出空心轴 implementation plan：`docs/superpowers/plans/2026-03-19-interference-fit-hollow-shaft.md`
  - 按 TDD 先新增 RED 测试，锁定：
    - 空心轴降低接触压力和承载能力
    - `shaft_inner_d_mm >= shaft_d_mm` 报错
    - 空心轴下 repeated-load 不适用
    - UI 新字段 / payload / 报告语义
  - 在 `core/interference/calculator.py` 中新增：
    - `geometry.shaft_inner_d_mm`
    - 空心轴柔度放大因子
    - 空心轴轴侧应力系数
    - 空心轴下 repeated-load / fretting applicability 降级
  - 在 `app/ui/pages/interference_fit_page.py` 中新增轴内径字段，并更新标题、副标题、hint、结果区和报告
  - 更新 README 与 benchmark 差异说明
- Verification:
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/interference/test_calculator.py tests/ui/test_interference_page.py -q` -> `35 passed`
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/interference/test_fretting.py tests/core/interference/test_calculator.py tests/core/interference/test_fit_selection.py tests/core/interference/test_assembly.py tests/ui/test_interference_page.py -q` -> `48 passed`
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest -q` -> `180 passed`
- Files created/modified:
  - task_plan.md (updated)
  - findings.md (updated)
  - progress.md (updated)
  - docs/superpowers/specs/2026-03-19-interference-fit-hollow-shaft-design.md (created)
  - docs/superpowers/plans/2026-03-19-interference-fit-hollow-shaft.md (created)
  - core/interference/calculator.py (updated)
  - core/interference/fretting.py (updated)
  - app/ui/pages/interference_fit_page.py (updated)
  - tests/core/interference/test_calculator.py (updated)
  - tests/ui/test_interference_page.py (updated)
  - README.md (updated)
  - docs/references/2026-03-19-interference-public-benchmark-notes.md (updated)
