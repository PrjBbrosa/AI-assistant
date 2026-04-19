# 工程知识帮助系统 · 撰写规范

> 本文件 Stage 0 骨架 → Stage 1（蜗杆 pilot 结束时）完善 → Stage 7 终稿

## 1. 文件命名

- 术语：`docs/help/terms/<snake_case>.md`，例 `gear_profile_shift.md`（若术语在多模块族语义不同，**必须加模块族前缀** `gear_*` / `worm_*` / `bolt_*` / `spline_*`；详见 §8.1 命名前缀约定）
- 模块章节概念文：`docs/help/modules/<module_key>/_section_<section_id>.md`
- 模块方法总览：`docs/help/modules/<module_key>/<snake_case_title>.md`
- `FieldSpec.help_ref` 格式：无 `.md` 后缀，例 `terms/gear_profile_shift`

## 2. 术语文章模板（深度 2）

```markdown
# 术语名（符号）

**一句话**：xxx

**怎么理解**：2-3 段通俗解释

**公式**：（可选，纯文本公式）

**典型值**：范围 + 常见选择场景

**出处**：DIN/VDI/ISO 条款编号
```

## 3. section 概念文模板

```markdown
# 本章节是什么

## 为什么要填这些
## 输入 / 产出
## 方法差异（如有）
## 参考标准
```

## 4. 方法总览模板

```markdown
# 方法名（标准编号）

## 一图总览
## 解决什么问题
## 核心流程（3-5 步）
## 本模块实现的范围 / 不实现的范围
## 常见误用
## 参考文献
```

## 5. 文风约定

- 目标读者：工作 1-2 年机械工程师，懂基本力学，不熟 DIN/VDI 细节
- 避免："显然"、"容易看出"等假设读者已懂的措辞
- 公式：纯文本形式，如 `tan γ = z₁ / q`；不用 LaTeX
- 公式单位：每一个公式都**必须显式标注输入 / 输出单位**（如 `Ft2 = 2000·T2/d2 [T2: N·m, d2: mm → Ft2: N]`）。缺单位的公式默认判为 P0 问题。
- 典型值：必须给"常用数值范围 + 选什么场景用什么"，不要只写单个数
- **单篇长度**（Stage 1 + 1.5 复核后调整）：术语 400–800 字为常规区间；**1000–1500 字允许**于需要同时解释多个符号（ZN/ZL/ZR/ZX 这类系数族）或列举多材料典型值的 P0 术语；低于 350 字说明深度不足；超过 1500 字再考虑拆篇或下放到"方法总览"
- **图表策略**：帮助弹窗无法渲染 LaTeX / 复杂图；需要图形解释的内容放到对应"方法总览"文章并在术语文章末尾"进一步阅读"引用

## 5.1 标准引用与实现描述的诚实性（**硬性规则，违反即 P0**）

撰写涉及 DIN / VDI / ISO / AGMA 等标准的内容时，必须区分三种出处场景并按对应规则标注：

**场景 A：已亲自查阅原始标准正文**
- 必须标出条款编号（精确到节号，如 `DIN 3975-1:2017 §4.2`）
- 可以不加警示语

**场景 B：未查阅原始标准，仅基于公开文献 / 教科书 / 代码注释整理**
- **必须**在段落末尾写一句："Cannot verify against original DIN standard" 或中文 "未查证原始标准正文"
- 不得写"出自 DIN X 第 Y 条"这种精确到条款的伪引用；只能写"参考 DIN X 的 Method B 框架"这类笼统口径
- 在 frontmatter/首段可以写 `DIN XYZ:ABCD（简化子集）` 这种示意编号，但同一文内必须伴随 Cannot verify 警示

**场景 C：本模块实现与标准存在已知偏离**
- **必须**在"本模块实现的范围 / 不实现的范围"节里明确写出偏离项（例如："本模块用 Hertz 线接触近似代替 Method B 的 ZH/ZE/Zβ 系数链"）
- 禁止在正文中用"本模块实现了 DIN 3996 Method B"这种与事实不符的口径；改写为"Method B 风格的工程简化估算器"
- 禁止暗示本模块输出可作为标准合规性依据

**禁止项（违反即 P0，必返工）**：
- 空口引用"根据 DIN XXX"而无条款号或 Cannot verify 警示
- 在实现只是近似时使用"已实现 DIN XXX Method B"这种等价表述
- 把代码注释里的简化公式当作标准原文转述

## 6. 哪些字段需要 help_ref

**必须加（专业术语）**：
- 出现希腊字母的字段（γ、α、σ、β、φ...）
- 出现英文缩写或标准缩写的字段（KHbeta、KHalpha、Kv、KA、Rp0.2、FM,min...）
- 引用 DIN/VDI/ISO 条款的字段
- "变位系数"、"导程角"、"齿宽"、"预紧力"、"夹紧比"等行业术语
- 用户填了会影响校核安全系数结论的核心参数（即使名字看起来普通，例如"摩擦系数"）

**不必加**：
- 纯输入项目备注 / 描述字段
- "长度"、"温度"等通用物理量（单位已自解释）
- 只影响展示的开关字段（载荷曲线缩放倍率、结果小数位等）
- 纯标识字段（工程编号、操作者签字）

**蜗杆 pilot 经验**（18 fields + 5 chapters）：带 `help_ref` 字段数约占 FieldSpec 总数 30–40%。低于 20% 说明识别不足；高于 50% 说明"过度标注"，会淡化专业术语的信号意义。

**章节级 help_ref**（`add_chapter(..., help_ref=...)`）加在每个步骤页的标题旁，指向该 section 概念文（深度 1）。蜗杆 pilot 在 5 章加了章节 help_ref（基本设置、几何参数、材料与配对、工况与润滑、Load Capacity）—— 章节级覆盖率应接近 100%。

## 7. section subtitle 重写风格

**改前**：「定义本版标准边界和 Load Capacity 骨架状态。」
**改后**：「设置校核范围和选项：是否启用齿面 / 齿根负载能力校核、使用哪个计算方法。」

原则：
- 禁止使用"本版"、"骨架"、"最小子集"等开发内部语言
- 第一句话说"这一块在做什么"（动作 + 对象）
- 第二句话说"选项有哪些 / 影响什么"

## 8. 术语 Master List

**扫描范围**：6 模块共约 121 个候选 `help_ref` 字段（蜗杆 18 + 其余 5 模块 ≈ 103），完整扫描表见 `docs/superpowers/reports/2026-04-19-stage1-term-scan.md`。

### 8.1 蜗杆 Stage 1 已完工（14 篇）

`module` / `diameter_factor_q` / `lead_angle` / `gear_profile_shift` / `gear_pressure_angle` / `elastic_modulus` / `poisson_ratio` / `worm_lubrication_mode` / `gear_application_factor_ka` / `kv_factor` / `kh_alpha` / `kh_beta` / `allowable_contact_stress` / `allowable_root_stress`

> **命名前缀约定**（Stage 1.5 adversarial review 后加入）：当某个术语在不同模块族含义不同，却会被 `help_ref` 复用时，用前缀把语义域显式锁住：
> - `gear_*` —— 齿轮 / 蜗轮族（涉及 DIN 3990/3996、ISO 6336 的齿形语境）
> - `worm_*` —— 蜗杆副专属（滑动润滑、当量摩擦角等蜗杆独有概念）
> - `bolt_*` / `spline_*` / `shaft_*` —— 后续模块类比使用
> - 无前缀 —— 真正跨模块通用（弹性模量 E、泊松比 ν、模数 m 这类基础物理量）
>
> 新写术语时若拿不准是否通用，**默认加前缀**。后续模块发现真正通用后再做合并，比"先通用后拆分"风险低。

**跨模块可复用的 3 篇**（其他模块直接引用 `terms/<ref>`）：
- `terms/elastic_modulus` —— bolt / interference / hertz / spline 共 6 次引用
- `terms/poisson_ratio` —— interference / hertz / spline 共 4 次引用
- `terms/module` —— spline 1 次（齿轮模数定义与蜗杆一致）

**不再跨模块直接复用**（蜗杆专属 / gear-only 语义，已加前缀锁住）：
- `terms/gear_application_factor_ka` —— interference / spline 需要时**新写** `terms/interference_application_factor_ka` 或 `terms/spline_application_factor_ka`（KA 在不同齿型族查表依据不同，直接复用会带入错误的 DIN 3990 齿轮背景）
- `terms/gear_pressure_angle` —— 压力角在螺纹（bolt）、花键（spline）、蜗杆（worm）语义差异大，后续模块各自写独立术语
- `terms/gear_profile_shift` —— 变位系数在蜗杆 / 外齿轮 / 内齿轮含义不同
- `terms/worm_lubrication_mode` —— 蜗杆以滑动速度为主导的润滑判据，与螺纹 / 过盈的干 / 油润滑不是同一套分类

### 8.2 Stage 2 bolt VDI 2230 已完工（21 篇）

`bolt_thread_nominal` / `bolt_thread_pitch` / `bolt_stress_area` / `bolt_grade` / `bolt_yield_strength` / `bolt_friction_thread` / `bolt_friction_bearing` / `bolt_bearing_pressure_allowable` / `bolt_clamped_solid_model` / `bolt_compliance` / `bolt_tightening_method` / `bolt_tightening_factor_alpha_a` / `bolt_utilization_nu` / `bolt_preload_fm` / `bolt_embed_loss` / `bolt_thermal_loss` / `bolt_axial_load_fa` / `bolt_seal_clamp_force` / `bolt_load_intro_factor` / `bolt_yield_safety` / `bolt_thread_engagement` / `bolt_thread_strip_tau`

### 8.3 Stage 3 bolt_tapped_axial 已完工（5 篇专属 + 复用 14 篇 Stage 2）

`bolt_tapped_axial_axial_load_range` / `bolt_tapped_axial_load_cycles` / `bolt_tapped_axial_prevailing_torque` / `bolt_tapped_axial_strip_safety_required` / `bolt_tapped_axial_surface_treatment`

复用自 Stage 2：bolt_thread_nominal / bolt_thread_pitch / bolt_stress_area / bolt_grade / bolt_yield_strength / bolt_friction_thread / bolt_friction_bearing / bolt_preload_fm / bolt_tightening_factor_alpha_a / bolt_tightening_method / bolt_axial_load_fa / bolt_seal_clamp_force / bolt_thread_engagement / bolt_thread_strip_tau

### 8.4 Stage 4 interference DIN 7190 已完工（24 篇）

`interference_application_factor_ka` / `interference_assembly_method` / `interference_contact_pressure` / `interference_delta_max` / `interference_delta_min` / `interference_effective_delta` / `interference_fit_diameter` / `interference_fit_length` / `interference_fretting_risk` / `interference_friction_coefficient` / `interference_hollow_shaft_bore` / `interference_hub_outer_diameter` / `interference_load_condition` / `interference_material_limits` / `interference_roughness` / `interference_slip_safety` / `interference_solid_shaft` / `interference_stress_safety` / `interference_subsidence` / `interference_temperature_assembly` / `interference_torque_required` / `interference_yield_strength` / `interference_axial_force_required` / `interference_radial_force_required` / `interference_bending_moment`（部分可能 ≤24，具体看 terms/ 目录）

### 8.5 Stage 5 hertz 已完工（9 篇 + 复用 2）

`hertz_allowable_pressure` / `hertz_contact_length` / `hertz_contact_mode` / `hertz_contact_width` / `hertz_curvature_radius` / `hertz_equivalent_modulus` / `hertz_normal_force` / `hertz_safety_factor` / `hertz_surface_roughness`

复用：`elastic_modulus` / `poisson_ratio`

### 8.6 Stage 6 spline DIN 5480 已完工（18 篇 + 复用 3）

`spline_allowable_flank_pressure` / `spline_application_factor_ka` / `spline_din5480_spec` / `spline_engagement_length` / `spline_flank_safety` / `spline_geometry_mode` / `spline_k_alpha` / `spline_load_condition` / `spline_mode` / `spline_reference_diameter` / `spline_relief_groove` / `spline_slip_safety` / `spline_smooth_friction` / `spline_smooth_interference` / `spline_smooth_yield_strength` / `spline_stress_safety` / `spline_tip_root_diameter` / `spline_tooth_count`

复用：`module` / `elastic_modulus` / `poisson_ratio`

### 8.7 累计统计

- 术语文件总数：**91 篇**（Stage 1: 14 + Stage 2: 21 + Stage 3: 5 + Stage 4: 24 + Stage 5: 9 + Stage 6: 18）
- 跨模块共享：3 篇（`module` / `elastic_modulus` / `poisson_ratio`）
- 模块族前缀锁住：`gear_*` / `worm_*` / `bolt_*` / `bolt_tapped_axial_*` / `interference_*` / `hertz_*` / `spline_*`
- 完整字段 → ref 映射表见 `docs/superpowers/reports/2026-04-19-stage1-term-scan.md`

## 9. 内容分级决策树（P0/P1/P2）

在决定某字段 / 章节的 help_ref 是否要写、写到什么深度时，按下述流程判断：

```
字段触发判定 §6 "必须加"？
├─ 否 → 不写
└─ 是 → 决定 P 级
    ├─ P0：影响安全系数结论 + 每个模块都涉及（如 E / ν / Rp0.2 / 摩擦系数 / αA / FM,min）
    │     → 本 Stage 必须写；典型值段必须给 3+ 场景
    ├─ P1：单模块核心但非跨模块（如 bolt 的柔度 δs、spline 的 Kα）
    │     → 本 Stage 写；典型值段给 1–2 场景即可
    └─ P2：长尾细节 / 边缘选项（如 fretting 评估、DIN5480 规格字符串解析）
          → 可押后到下一 Stage 或简化为"语义占位"（只写一句话 + 指向方法总览）
```

**关键判断点**：
- "用户不填这个字段，校核结论会不会错"→ 是则 P0
- "这个字段在 3+ 模块出现"→ 是则 P0（写一篇受益多）
- "这个字段仅在某模块某工况出现"→ P2

**P0 单篇质量门槛**：400+ 字、≥ 3 个典型值场景、符合 §5.1 的标准引用诚实性规则（若未查证原始标准正文，必须写 "Cannot verify against original DIN standard"）。P2 允许"一句话一个场景"，但同样必须遵守 §5.1；同时在 frontmatter/首段注明"暂缺完整展开"。

## 10. codex adversarial review 输入清单

主会话每次调用 codex-rescue 时提交：
- 当前 Stage 目标
- 改动文件清单 + git diff
- 本文件最新内容
- 要求检查维度（组件 / 内容 / 规范合规 / 未覆盖风险）
- 要求 P0/P1/P2 分级 + 禁止空评价

**P0/P1/P2 在评审语境下的定义**（与 §9 内容分级的 P 级区分）：

- **P0（必改）**：代码 crash、API 契约破坏、测试产物污染 production 树、UI 弹窗目标残留、help_ref 指向不存在的 md 文件
- **P1（应改）**：文风偏差（开发内部语言、"显然"措辞）、出处编号错误、典型值缺场景、章节 subtitle 不符合 §7 模板
- **P2（可留作 follow-up）**：P2 级术语未写、长尾工况未覆盖、视觉微调

**蜗杆 Stage 0.5 经验**：codex 发现 3 个 P0（chapter_stack API 契约侵蚀 / popover 对已销毁 anchor 崩溃 / 测试 fixture 落在 production docs/ 树里），均为 Stage 0 reviewers 遗漏。**规则**：P0 必须在本 Stage 内修复才能进入下一 Stage；P1 可延到下一 Stage 开头集中处理；P2 登记到 follow-up 文件供 Stage 7 终稿前批处理。
