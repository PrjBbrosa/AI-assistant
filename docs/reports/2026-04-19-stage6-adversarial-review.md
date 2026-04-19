# Stage 6 Adversarial Review (spline DIN 5480 花键)
Date: 2026-04-19
Reviewer: Codex (adversarial mode)
Scope: Stage 6 spline 帮助内容、page wiring、guard tests

## P0 严重问题（必须修复才能 merge）

**[P0-A]** `spline_tip_root_diameter.md` 直接写错 catalog 数值
- **问题**: 文中把 `W 20×2×8` 写成 `h_w=0.5 mm, h_w/m=0.25`，与内置 catalog 和 `h_w=(d_a1-d_a2)/2` 实现不符，会直接误导用户对"0.5m 保守下限"的理解。
- **位置**: `docs/help/terms/spline_tip_root_diameter.md:31-38`
- **证据**: `core/spline/din5480_table.py:82-84` 给 `W 20x2x8` 的 `d_a1=18.6, d_a2=16.5`；按 `core/spline/geometry.py:110-111` 得 `h_w=(18.6-16.5)/2=1.05 mm`, `h_w/m=0.525`。真正的 0.5 下限例子是 `W 25x2.5x8`（`core/spline/din5480_table.py:98-100`）。
- **建议**: 修正该表，别再把 `W 20×2×8` 当成 0.5 下限样例。

**[P0-B]** 5% 偏差 warning 被写成"通常代表填错"，但内置 catalog 本身就会触发
- **问题**: 帮助文把 `|d-mz|/mz > 5%` 解释成"通常意味着 m 或 z 填错"，会让用户在选择工具内置标准规格后，被工具自己的 warning 反向误导。
- **位置**: `docs/help/terms/spline_reference_diameter.md:13-19,35`; 同类表述见 `docs/help/modules/spline/_section_geometry.md:45-47`
- **证据**: 标准规格下拉会自动填 `W 15x1.25x10`（`app/ui/pages/spline_fit_page.py:170-175,665-681`）；该条目在 catalog 中是 `d=15.0, m*z=12.5`（`core/spline/din5480_table.py:41-43`）；`core/spline/geometry.py:67-75` 对 >5% 一律追加 warning。
- **建议**: 文档必须明确"built-in DIN 5480 catalog 也会触发该 warning；它不是可靠的录入错误指示器"。

**[P0-C]** 多篇公式仍未按 GUIDELINES 显式标注输入/输出单位
- **问题**: Stage 6 仍违反 L6 / GUIDELINES 硬规则；多处只写 `[MPa]` 或完全不写输入单位，用户无法安全照抄。
- **位置**: `docs/help/GUIDELINES.md:56-58`；违规例子见 `docs/help/terms/spline_k_alpha.md:17-24`, `docs/help/terms/spline_tooth_count.md:9-15`, `docs/help/terms/spline_smooth_friction.md:9-12`, `docs/help/terms/spline_stress_safety.md:10-15`
- **证据**: `spline_k_alpha.md:18` 只写 `p_flank = ... [MPa]`，未标 `T`/`h_w`/`d_m`/`L` 的单位；`spline_smooth_friction.md:10-12` 三条公式完全无单位。
- **建议**: 按 GUIDELINES 统一补成 `[...]` 单位约定；涉及 `N·m→N·mm`、`μm→mm` 的地方必须写全。

---

## P1 重要问题

**[P1-A]** `联合` 模式误用说明没有忠实描述实际工具行为
- **问题**: 文中说"纯花键却选联合会 FAIL，因为相当于 L=0/δ=0"，这不是实际实现；UI 在 `联合` 模式会带着默认的 `smooth_*` 非零值进入 payload，实际是"拿一组虚构过盈段去算"，不是特定的 `L=0/δ=0` 失败机理。
- **位置**: `docs/help/terms/spline_mode.md:37-39`
- **证据**: smooth 默认值在 `app/ui/pages/spline_fit_page.py:267-307`; `combined` 时 `_build_payload` 无条件传 `smooth_fit/smooth_materials/smooth_roughness/smooth_friction`（`app/ui/pages/spline_fit_page.py:882-909`）。
- **建议**: 改写为"若真实结构没有光滑过盈段，选`联合`会得到无物理意义的场景 B 结果，应切回`仅花键`"。

**[P1-B]** 守护测试对 HelpButton 渲染校验过宽，漏不掉字段级断线
- **问题**: 章节测试只断言 `>=1` 个 `HelpButton`；哪怕只剩章节按钮、字段级按钮全丢，也仍会通过。
- **位置**: `tests/ui/test_spline_help_wiring.py:149-164`
- **证据**: 断言条件仅 `len(help_buttons) >= 1`，未与该章节字段级 `help_ref` 数量对账。
- **建议**: 按章节做"章节级 1 个 + 字段级按钮数"的精确断言，或逐字段查找。

---

## P2 轻微问题

**[P2-A]** `terms/module` 复用方向对，但文案仍偏齿轮/蜗杆语境
- **问题**: Stage 6 正确复用了 `terms/module`，没有新造 `spline_module`；但被复用文章本身仍写成"齿轮与蜗轮传动的基础尺寸单位"，对 spline 用户不够贴脸。
- **位置**: 复用点 `app/ui/pages/spline_fit_page.py:187-191`; 术语正文 `docs/help/terms/module.md:3-11`
- **证据**: 文中只谈齿轮/蜗杆，且直接写 `d = z·m`，与 spline 页面同时存在的"显式 `d_B` 可不同于 `m·z`"语境有割裂。
- **建议**: 保持复用，不要新建 `spline_module`；应在 `terms/module.md` 补一段 spline 语境说明。

---

## 总体判断

**Round 2。** 理由：有 3 条会直接误导工程判断的 P0，尤其是错误 catalog 数值（P0-A）、对 5% warning 的错误解释（P0-B）、以及公式单位硬规则未达标（P0-C）。补充说明：跨模块复用方向总体正确，`elastic_modulus` / `poisson_ratio` 已正确复用，`application_factor_ka` 已正确独立成 `terms/spline_application_factor_ka`；本轮主要问题在内容准确性与守护强度。
