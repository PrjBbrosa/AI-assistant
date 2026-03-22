# Findings & Decisions

## Requirements
- 产出一份完整的 VDI 2230 计算说明文档（中文）
- 基于 VDI 2230 开发螺栓校核工具
- 工具需可运行、可复核，给出输入输出和示例

## Research Findings
- 仓库为空目录，需要从零搭建项目结构
- 需收集 VDI 2230 的公开可引用资料来支撑公式与流程
- VDI 2230 官方覆盖范围：Part 1 为高负荷螺栓连接系统计算，Part 2 为多螺栓连接，Part 3 为同轴压缩载荷（来源：VDI 官方页面）
- eAssistant 对 VDI 2230 的摘要给出核心关系：`FMmax = alpha_A * FMmin`，并列出 `FMmin` 由防滑、密封、分离、嵌入损失等条件共同决定
- PCB 白皮书按 VDI 2230 列出 R1-R10 计算流程与关键校核项（例如最小预紧力、最大允许附加载荷、疲劳校核），可作为流程框架参考
- 夹紧力与附加载荷分配采用经典弹簧模型（VDI 2230 同源方法）：`phi = delta_p / (delta_s + delta_p)`，附加载荷进入螺栓为 `phi * FA`
- 装配阶段可通过“轴向 + 扭转载荷”进行当量应力校核：`sigma_v = sqrt(sigma^2 + 3*tau^2)`，与材料屈服强度利用系数比较
- 用户确认交付形态为本地桌面版本（PyCharm 运行），并预留 `.exe` 封装路径
- 桌面框架模块入口固定为：螺栓连接、轴连接、轴承、蜗轮、弹簧、材料与标准库
- 用户要求界面按 eAssistant Chapter 14 的章节结构与参数组织方式重排
- 用户要求结果展示改为非 JSON 的工程可读格式，并要求增加螺栓夹紧图

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 Python 实现首版计算引擎 | 便于快速构建数值计算与示例验证 |
| 文档与代码同仓库交付 | 便于追溯公式与实现一致性 |
| 首版范围聚焦 VDI 2230 核心校核链路（R1-R8） | 在空仓库内优先交付可运行、可复核版本 |
| 输入参数同时支持“顺从度”和“刚度” | 兼顾标准建模与工程现场常见输入习惯 |
| 框架改为 PySide6 本地桌面壳 | 满足用户本地使用和 exe 打包目标 |
| 保留 CLI 同时新增 GUI | 兼顾批处理与交互式工程校核 |
| 螺栓页面改为 Chapter 14 导航布局 | 与用户参考页面的信息架构保持一致 |
| 参数全部带说明（hint + tooltip） | 面向非程序员用户，降低误填风险 |
| 结果输出改为“结论 + 分项 + 建议 + 报告导出” | 使结果可直接用于工程沟通 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 无现成代码和样例 | 从标准流程拆解并自建示例数据 |

## Resources
- /Users/donghang/.agents/skills/brainstorming/SKILL.md
- /Users/donghang/.agents/skills/planning-with-files/SKILL.md
- https://www.vdi.de/richtlinien/details/vdi-2230-blatt-1-systematic-calculation-of-high-duty-bolted-joints-joints-with-one-cylindrical-bolt
- https://www.eassistant.eu/fileadmin/dokumente/eassistant/etc/HTMLHandbuch/en/eAssistantHandbch14.html
- https://www.pcbloadtorque.com/pdf/14.6.13%20-%20VDI%202230%20Systematic%20Calculation%20of%20High%20Duty%20Bolted%20Joints.pdf
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/main.py
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/ui/main_window.py
- /Users/donghang/Documents/Codex/bolt tightening calculator/scripts/build_exe.bat
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/ui/pages/bolt_page.py
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/ui/widgets/clamping_diagram.py

## Visual/Browser Findings
- 已完成 VDI 官方页面、eAssistant 手册页面和 PCB 白皮书检索，确认了实现所需的主流程和核心方程

## 2026-03-22 Worm Module Review Findings

### Current State
- 仓库文档和页面文案都明确：蜗杆模块当前只实现了 `DIN 3975` 几何与基础性能首版，`DIN 3996` / `ISO/TS 14521` 负载能力尚未实现
- `Load Capacity` 页面是结构占位，不输出真实齿面/齿根校核结果
- `tests/core/worm/test_calculator.py` 与 `tests/ui/test_worm_page.py` 主要覆盖页面结构与基础几何返回，不覆盖物理链路一致性

### High-Severity Gaps
- 功率链路不闭合：输入功率、效率、输出扭矩三者不一致
- 几何约束未闭合：`z1 / q / gamma / a` 可以明显不自洽，但系统只给偏差量，不阻断也不警告
- 多个关键字段未入模：`worm_face_width_mm`、`wheel_face_width_mm`、`application_factor`、`friction_override`
- 样例工况本身几何不自洽，仍能正常出结果

### Planned Upgrade Boundary
- 本轮不做完整 `DIN 3996` / `ISO/TS 14521`
- 本轮做 `Method B` 风格最小子集：
  - 几何一致性 warning
  - 功率/扭矩闭环
  - 齿面应力
  - 齿根应力
  - 扭矩波动
  - 安全系数

### Source Notes
- `ISO/TS 14521:2020` 官方预览可确认标准覆盖 `pitting / tooth breakage / temperature` 以及符号：
  - `σHm` mean contact stress
  - `τF` tooth-root shear stress
  - `SH / SF / ST` safety factors
- 公开研究论文表明：
  - worm gear 的状态量仍围绕 mean Hertzian contact stress、coefficient of friction、sliding velocity 等量组织
  - `CuSn12Ni2` 接触强度数据可作为工程初始默认值参考，但不应替代显式输入

### Implementation Notes
- `core/worm/calculator.py` 现已输出：
  - `performance.input_power_kw / output_power_kw / input_torque_nm / output_torque_nm`
  - `load_capacity.forces`
  - `load_capacity.contact`
  - `load_capacity.root`
  - `load_capacity.torque_ripple`
- `friction_override` 已真正进入效率和损失功率计算
- `application_factor` 与 `Kv / KHalpha / KHbeta` 已进入设计载荷
- UI 已显式暴露：
  - 材料弹性参数
  - 扭矩波动
  - 法向压力角
  - 许用齿面/齿根应力
  - 载荷系数与目标安全系数

### Remaining Limitations
- 仍非完整 `DIN 3996 / ISO/TS 14521`
- 齿面应力为线接触 Hertz 近似
- 齿根应力为等效悬臂梁近似
- 当前样例更偏“结构化演示 / 边界工况”，不代表标准 benchmark 全通过工况

## 2026-03-16 Interference-Fit Review Findings

### Scope Confirmed
- 本轮继续保留当前圆柱面模型边界：`实心轴 + 厚壁轮毂 + 线弹性 + 常摩擦`
- 用户明确排除：
  - `centrifugal force`
  - `stepped hub geometry`
- 用户要求纳入梳理与后续执行的方向：
  - 正确性修正（安全系数、联合作用、结论语义）
  - ISO 286 配合/公差搜索
  - shrink/force fit 装配章节
  - repeated load / fretting corrosion
  - 结果与报告的可追溯性

### High-Severity Gaps (已修复)
- ~~`delta_required` / `fit_range_ok` 当前未纳入 `checks.slip_safety_min`~~ → 已修正，`slip_safety_min` 参与 p_required 计算
- ~~扭矩与轴向力联合作用未进入总判定~~ → 已修正，`combined_ok` 进入 `overall_pass` 且 UI 展示
- ~~`fit_range_ok` 语义偏乐观~~ → 已收紧，`p_required` 取 torque/axial/combined/gap 的 max

### UI / Payload Semantics
- 以下字段是“辅助选择器”，并不直接进入 calculator：
  - `materials.shaft_material`
  - `materials.hub_material`
  - `roughness.profile`
- `options.curve_points` 只影响压入力曲线的离散点数，不影响任何校核通过/不通过结论
- 报告中目前缺少参数来源追溯，无法看出材料/粗糙度/配合范围来自：
  - 手工输入
  - 预设库
  - 标准版本

### eAssistant / DIN 7190 Capability Mapping
- 已被当前实现覆盖：
  - `KA` 工况系数
  - `p_min >= p_r + p_b` 张口缝条件
  - `Uw = U - k(RzA + RzI)` 粗糙度压平
  - min/mean/max 结果组织
  - 服役摩擦与装配摩擦拆分
- Phase 9 已实现（2026-03-17 验证通过，131 tests all pass）：
  - ISO 286 配合/公差搜索与推荐（`fit_selection.py`，优选配合 + 偏差换算）
  - shrink fit 温差/装配间隙（`assembly.py`，热装温度计算 + 间隙模式）
  - force fit 压入/压出摩擦与装配工艺说明（`assembly.py`，独立压入/压出摩擦系数）
  - repeated load / fretting corrosion（calculator 内 `repeated_load_mode` + applicability gate）
  - 结果与报告的输入来源追溯（material/profile/fit source/assembly method 全链路追溯）
- 尚未覆盖且本轮明确排除：
  - centrifugal force / speed
  - stepped hub / stepped shaft geometry

### Verification Notes
- 已运行 `python3 -m unittest tests.core.interference.test_calculator tests.ui.test_interference_page -v`
- 结果：10 个测试全部通过
- 额外手动验证发现：
  - 存在 `torque_ok=True`、`axial_ok=True`、但 `combined_ok=False` 的输入组合
  - 存在 `torque_ok=False`、但 `fit_range_ok=True` 的输入组合

## 2026-03-17 Bolt Page Deep Review Findings

### Scope Confirmed
- 重点审查对象：
  - `app/ui/pages/bolt_page.py`
  - `app/ui/pages/bolt_flowchart.py`
  - `app/ui/input_condition_store.py`
  - `core/bolt/calculator.py`
- 审查重点：
  - 页面前后逻辑是否一致
  - 参数是否真正进入 payload / calculator
  - 工况覆盖边界是否明确
  - 是否存在无效配置、陈旧文案和 UI-only 虚拟参数

### High-Severity Findings
- R5 正式判据已用 `sigma_vm_work`，但页面摘要和导出报告仍显示 `sigma_ax_work`，会把扭矩法失败工况伪装成“低利用率”
- 自定义热膨胀系数留空时，core 会静默回退成钢默认值 `11.5e-6`，热损失估算可能被错误压成 0
- 螺栓页输入条件快照保存的是显示文本，标准螺距如 `1.5（粗牙）` 回灌时会直接触发 `ValueError`

### Medium-Severity Findings
- `calculation_mode` 不会被保存到输入条件快照中，恢复后页面总会回到 `design`
- raw payload 中的 `joint_type/basic_solid/surface_class/tightening_method/surface_treatment` 不会恢复到 UI choice 控件
- 多层热参数 `alpha` 留空时，页面层直接抛原生 `ValueError`，没有转成字段级 `InputError`
- 流程图详情页在重复计算时会重复堆叠输入回显控件

### Low-Severity / Cleanup Findings
- `summary_key` 配置未使用
- `tightening_method` 字段说明仍写“仅记录，不参与算法分支”，与当前实现不符
- 动态 tooltip 已更新，但底部说明栏依赖的 `_widget_hints` 没有同步更新

### Coverage Assessment
- 已覆盖：
  - R3/R4/R5
  - 温度损失
  - 简化 Goodman 疲劳
  - 可选 R7 支承面压强
  - 单层/多层柔度建模
- 尚未覆盖或仅保留占位：
  - 偏心/弯矩工况
  - 螺纹脱扣
  - 完整疲劳谱
  - 通孔双侧不同支承几何

### Verification Notes
- 已运行：
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/bolt/test_calculator.py tests/core/bolt/test_compliance_model.py tests/ui/test_input_condition_store.py -q`
- 结果：
  - `76 passed`
- 额外 headless 复现确认：
  - snapshot round-trip 会因 `1.5（粗牙）` 崩溃
  - `calculation_mode` 快照恢复失败
  - raw payload choice 状态恢复失败
  - 自定义热参数会静默回退成钢默认值
  - 多层自定义 alpha 空值会抛原生 `ValueError`
  - 重复计算会让 R 步骤详情页输入控件数量从 `54 -> 108`

## 2026-03-18 Interference-Fit Deep Review Working Notes

### Review Goal
- 详细审查“过盈配合”章节（文档、UI、calculator、示例、测试）
- 确认是否存在：
  - 公式 bug
  - 章节遗漏
  - 逻辑错误 / 结果语义问题
  - 与 DIN 7190 / 经典工具案例不一致的地方

### Planned Comparison Baselines
- 本地基线：
  - `core/interference/calculator.py`
  - `core/interference/fit_selection.py`
  - `core/interference/assembly.py`
  - `app/ui/pages/interference_fit_page.py`
  - `tests/core/interference/*`
  - `tests/ui/test_interference_page.py`
- 外部基线：
  - DIN 7190 / ISO 286 相关公开可得资料
  - eAssistant interference fit handbook pages
  - 其他工程校核工具（优先选公开说明较全、能看到公式或案例的工具）

### Early Local Findings
- `docs/plans/2026-03-08-interference-fit-din7190-core-design.md` 的范围说明已落后于当前实现：
  - 文档仍写“暂不扩展” `ISO 286` 配合推荐、热装温差、重复载荷
  - 但当前 `core/interference/` 已包含 `fit_selection.py`、`assembly.py`、`repeated_load`
- 这意味着“章节设计文档 / 实际功能 / 用户可见说明”之间存在同步风险，需要继续核对 UI 页面和 README 是否已经同步
- 当前 `InterferenceFitPage` 的章节结构已经扩展为：
  - 过盈来源模式（直接输入 / 优选配合 / 偏差换算）
  - 装配流程（manual_only / shrink_fit / force_fit）
  - 高级校核（repeated-load / fretting）
- 当前 UI 文案把 `advanced.repeated_load_mode` 明确标成“不参与基础 DIN verdict”，这一点与 `calculator.py` 中 `overall_pass` 的实现一致
- `fit_selection.py` 当前只实现了 `H7/p6`、`H7/s6`、`H7/u6` 且直径范围仅 `6~50 mm` 的 curated subset；这是可控实现，但需要重点检查：
  - UI / README 是否充分提醒“不是完整 ISO 286 数据库”
  - 对外比较时不能把它表述成“完整标准搜索”

### Coverage Observations In Progress
- `tests/core/interference/test_calculator.py` 已覆盖：
  - 基本压力/能力输出
  - 粗糙度影响
  - `KA` 与 `slip_safety_min` 对需求过盈的影响
  - `combined_ok` 进入总判定
  - `force_fit` / `repeated_load` 基本分支
- 但暂未从当前已读部分看到以下明确断言：
  - `p_required` 由 `torque / axial / combined / gap` 取 `max` 的组成说明是否正确暴露到结果层
  - `fit_selection` 的每个公差带边界点（如 `10/18/24/30/40/50 mm`）是否都被锁定
  - `shrink_fit` 中轴冷却项对所需轮毂温度的影响是否有回归测试
  - UI 导出报告是否完整提示“curated subset / 非完整标准库”

### UI/Core Alignment Notes
- `InterferenceFitPage._build_payload()` 已把以下 UI 选择器真正落入 payload：
  - `fit.mode` -> `fit_selection` 派生并回填 `fit.delta_min/max_um`
  - `assembly.method` -> `assembly.method`
  - `advanced.repeated_load_mode` -> `advanced.repeated_load_mode`
- `InterferenceFitPage._render_result()` 与 `_build_report_lines()` 已显式展示：
  - `p_req,T / p_req,Ax / p_req,comb / p_gap`
  - `combined_ok`
  - fit source / assembly trace / repeated load trace
- 到目前为止，尚未发现“UI 字段存在但未进入计算”或“计算结果存在但 UI 完全未展示”的严重脱节
- 更可能的问题集中在：
  - 文案是否把适用范围与简化假设说透
  - 测试是否足以锁定工程边界
  - 与外部案例相比是否存在数值偏差或概念偏差

### Confirmed Review Findings
- `app/ui/pages/interference_fit_page.py` 存在 raw payload 回灌语义缺口：
  - 若输入文件只提供 `inputs` 而没有 `ui_state`，`_apply_input_data()` 之后的 `_sync_*()` 会把自定义材料、粗糙度 profile、assembly mode、repeated-load mode 覆盖回默认值
  - 这不会影响已保存的表单快照，但会影响 raw calculator payload / 外部 JSON 的 UI 复核可靠性
- 本地 `examples/interference_case_01.json` 与 eAssistant 公共 DIN 7190 案例在核心尺寸/载荷上高度相似，但边界不同：
  - eAssistant 公共案例为 `空心轴 (inner diameter = 30 mm)`，并考虑 speed / operating temperature
  - 当前工具明确是 `实心轴 + 不计离心力 + 不计服役温度`
  - 因此两者不能直接拿数值结论做一对一校核
- `fit_selection.py` 当前是“受限子集”而不是完整 ISO 286 搜索器：
  - 仅支持 `H7/p6`、`H7/s6`、`H7/u6`
  - 仅覆盖 `6~50 mm`
  - 与 eAssistant handbook / MITCalc 所示能力相比属于有意收窄实现

## 2026-03-19 Interference-Fit Closeout Findings

### 已完成的收尾修正
- raw payload 回灌语义缺口已修复：
  - `InterferenceFitPage._apply_input_data()` 现在会在缺少 `ui_state` 时，从原始输入中反推材料、粗糙度 profile、assembly mode、fit mode 和 fretting mode
  - 若与预设不匹配，则显式保持 `自定义`，不再静默覆盖原始数值
- `fit_selection` 已补 band 边界测试：
  - `H7/s6 @ 10 mm`
  - `H7/s6 @ 18 mm`
  - `H7/u6 @ 35 mm`
- 已新增公开 benchmark 差异说明：
  - `docs/references/2026-03-19-interference-public-benchmark-notes.md`
- 历史设计文档已加“状态更新”说明：
  - 防止把 2026-03-08 的设计快照误读成当前能力边界

### 当前仍然明显的局限性
- 当前主模型仍然限定为实心轴 + 厚壁轮毂
- 空心轴尚未接入主模型，因此不能与部分 DIN/eAssistant 经典案例直接一比一 benchmark
- 离心力 / 转速、服役温度、阶梯几何仍未进入主模型
- ISO 286 仍为 curated subset，不是完整公差库

## 2026-03-19 Hollow-Shaft Support Kickoff

### Scope Decision
- 用户已明确要求“直接做空心轴支持”
- 本轮按最小增量范围执行：
  - 新增 `geometry.shaft_inner_d_mm`
  - 接入主压力/能力/应力链路
  - 更新 UI / 报告 / trace
- 本轮仍不扩展：
  - speed / centrifugal
  - service temperature
  - stepped geometry

### Design Choice
- 为保持当前实心轴输出稳定，空心轴首版采用“兼容当前实心轴基线”的柔度放大方案
- `shaft_inner_d_mm = 0` 时严格退化为当前结果
- `shaft_inner_d_mm > 0` 时：
  - 轴侧柔度增大
  - 接触压力与承载能力下降
  - repeated-load block 降级为 `not applicable`

### Implementation Outcome
- `geometry.shaft_inner_d_mm` 已进入主 payload / calculator / UI / report 链路
- 当前结果层新增并使用：
  - `model.shaft_type`
  - `derived.shaft_inner_d_mm`
  - `derived.shaft_bore_ratio`
  - `derived.shaft_compliance_factor`
- 空心轴下：
  - `p_min`、`torque_min_nm` 按预期下降
  - 轴侧 von Mises 应力不再沿用实心轴常量系数
  - `repeated_load` 与简化 fretting gate 会显式返回 `not applicable`

### Updated Limitations After Phase 15
- 主模型已不再局限于实心轴，但仍然是：
  - 实心轴/空心轴
  - 厚壁轮毂
  - 无 speed / centrifugal 主耦合
  - 无 service temperature 主耦合
  - 无 stepped geometry
- 空心轴支持首版采用兼容当前实心轴基线的增量扩展，不应误解为“DIN 7190 完整统一空心轴求解器”
- 已生成正式审查报告：
  - `docs/review/2026-03-18-interference-fit-deep-review.md`

## 2026-03-19 Fretting Step Planning Notes

### Scope Confirmed
- 用户希望新增的是“过盈配合里的第 5 步 fretting 增强模块”，而不是独立通用 fretting 页面
- 首版 fretting 输出目标：
  - 给出风险等级
  - 给出工程建议
  - 不并入基础 `overall_pass` 主 verdict

### Current Local Baseline
- 当前仓库已存在一个 very-lightweight fretting/repeated-load block：
  - `advanced.repeated_load_mode`
  - 适用性 gate：`l/d > 0.25`、模量接近、无弯矩
  - 输出：`applicable`、`max_transferable_torque_nm`、`fretting_risk`
- 这更像“附加提示块”，还不是完整的 Step 5 fretting 子模块

### Planning Objective
- 先评估复杂度并提出 2~3 条实现路线
- 用户确认方向后，再写：
  - `docs/superpowers/specs/2026-03-19-...-design.md`
  - `docs/superpowers/plans/2026-03-19-...md`

### Approved Design Direction
- 推荐方案已确认：
  - fretting 作为“过盈配合第 5 步增强模块”
  - 输出 `适用性 + 风险等级 + 原因拆解 + 建议`
  - 不进入 `overall_pass`
  - 以当前 `repeated_load` 逻辑为基础，升级为正式 Step 5 结果块
- 正式 spec 已写入：
  - `docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md`
- implementation plan 已写入：
  - `docs/superpowers/plans/2026-03-19-interference-fit-fretting-step.md`

### Implementation Outcome
- 已新增 `core/interference/fretting.py`
  - 输出 `enabled / applicable / risk_level / risk_score / drivers / recommendations / confidence / notes`
- `core/interference/calculator.py` 已集成新的 `fretting` 结果块
  - 新输入优先读取 `fretting.mode`
  - legacy `advanced.repeated_load_mode` 仍可兼容触发 fretting
  - `overall_pass` 不受 fretting 影响
- `app/ui/pages/interference_fit_page.py` 已将旧“高级校核”升级为正式 `Fretting 风险评估` Step 5
  - 新增字段：
    - `fretting.mode`
    - `fretting.load_spectrum`
    - `fretting.duty_severity`
    - `fretting.surface_condition`
    - `fretting.importance_level`
  - 报告与结果区已显示 Step 5 fretting 段落，并明确说明“不改变基础 verdict”
- `examples/interference_case_01.json` 已切换为 fretting-enabled 示例
- README 已更新为 Step 5 fretting 语义

### Verification Evidence
- 已运行：
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/interference/test_fretting.py tests/core/interference/test_calculator.py tests/core/interference/test_fit_selection.py tests/core/interference/test_assembly.py tests/ui/test_interference_page.py -q`
- 结果：
  - `41 passed`
- 额外 manual smoke：
  - `disabled` -> `enabled=False`, `risk_level=not_applicable`, `overall_pass=True`
  - `high-risk` -> `enabled=True`, `applicable=True`, `risk_level=high`, `overall_pass=True`
  - `legacy-switch` -> legacy advanced 开关仍可启用 fretting
  - `not-applicable` -> `risk_level=not_applicable`, 原因会写入 notes

## 2026-03-22 Spline Fit Review Findings (Pre-Hardening Audit)

### Current State
- 模块标题与文案当前写成“花键过盈配合”，但场景 A 计算实质上只是“扭矩 -> 齿面平均承压”的简化估算
- 场景 B 复用现有圆柱面过盈链路，模型边界相对清晰
- 单元测试与 UI 测试全部通过，但主要覆盖“实现自洽”，没有对公开标准尺寸/benchmark 做对标

### High-Severity Gaps
- 场景 A 没有建立过盈量、公差、齿侧间隙、装配或接触刚度模型，不能按“花键过盈配合”理解
- `core/spline/geometry.py` 采用 `d = m * z`、`d_a1 = m * (z + 1)` 等简化推导，不符合 DIN 5480 以参考直径/变位为核心的建模方式
- `tests/core/spline/test_geometry.py` 把 `30x1.25x22` 典型规格直接断言为 `27.5 mm` 参考直径，说明当前测试在强化错误假设
- 场景 A 只做单一承压式，没有把更多失效模式和清晰的 load distribution trace 纳入输出

### Medium-Severity Gaps
- 顶层 `messages` 没有并入 `scenario_b.messages`，导致 UI fail 时解释不完整
- 材料选择提示声称会自动填充 `E` / `nu`，但当前页面没有真正连接该联动
- `tooth_count` 当前会从 float 静默截断成 int，工程输入边界不够严谨

### Recommended Strategy
- Stage A：先做“立即去风险”整改，把模块降级为“简化预校核”并补齐 trace / warning / 联动
- Stage B：再做“标准化重构”，重建 DIN 5480 风格几何输入和 benchmark 闭环
- 在 Stage B 完成前，不把该模块作为正式工程校核工具交付

### Verification Notes
- 已运行：
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline/test_geometry.py tests/core/spline/test_calculator.py tests/ui/test_spline_fit_page.py -q`
- 结果：
  - `23 passed`
- 额外脚本验证：
  - 默认 combined case 中场景 A 通过、场景 B 因最小过盈能力不足而失败
  - `scenario_b.messages` 当前存在，但不会进入 UI 顶层说明

## 2026-03-22 Spline Fit Hardening Closeout

### Resolved In This Round
- 模块标题与 UI 语义已从“花键过盈配合”降级为“花键连接校核”，并明确声明场景 A 仅为简化预校核
- 场景 B 的失败原因已并入顶层 `messages`，页面可直接看到 fail 原因
- 材料选择现已真实回填 `E` / `nu`
- `tooth_count` 非整数输入现会报错，不再静默截断
- 场景 A 已支持参考直径驱动的显式几何输入，并保留近似模式 warning
- 已加入公开小规格 benchmark：`W/N 15 x 1.25 x 10`

### Remaining Boundary
- 当前模块可作为“可追溯的简化预校核”使用，但仍不能作为正式 `DIN 5480 / DIN 6892` 工程签发校核
- 场景 A 尚未完整覆盖公差/变位解析、完整分载因子链、齿根/剪切/胀裂等失效模式

### Verification Evidence
- 定向回归：
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/spline tests/ui/test_spline_fit_page.py -q`
  - `34 passed`
- 全量回归：
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest -q`
  - `235 passed`
