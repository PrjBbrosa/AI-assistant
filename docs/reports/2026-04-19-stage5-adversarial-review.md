# Stage 5 Adversarial Review (hertz 赫兹接触应力)
Date: 2026-04-19
Reviewer: Codex (adversarial mode)
Scope: Stage 5 hertz 帮助内容、page wiring、guard tests

## 评审依据
- `/tmp/stage5-review.diff` — 已找到并通读 1457 行
- `.claude/lessons/help-content-lessons.md` — 已通读 101 行
- `docs/help/GUIDELINES.md` — 已通读 191 行
- `core/hertz/calculator.py` — 已通读 229 行（唯一实现基准）
- `docs/reports/2026-04-19-stage2-adversarial-review.md` — 已通读 63 行
- `docs/help/modules/hertz/_section_*.md` — 4 篇全部通读
- `docs/help/modules/hertz/hertz_contact_overview.md` — 通读
- `docs/help/terms/hertz_*.md` — 9 篇全部通读
- `app/ui/pages/hertz_contact_page.py` — 通读 916 行
- `tests/ui/test_hertz_help_wiring.py` — 通读 155 行

---

## P0 严重问题（必须修复才能 merge）

### [P0-1] `hertz_contact_length` 的敏感度表整表数值与实现严重不符
- 位置: `docs/help/terms/hertz_contact_length.md:53-57`
- 证据: `| 10 | 1200 | ≈ 0.0736 | ≈ 10375 |`、`| 20 | 600 | ≈ 0.0520 | ≈ 7336 |`、`| 40 | 300 | ≈ 0.0368 | ≈ 5188 |`
- 对照: `core/hertz/calculator.py:139-143` — `load_per_length = normal_force / length_mm`、`semi_width = math.sqrt((4.0 * load_per_length * r_eq) / (math.pi * e_eq))`、`p0 = (2.0 * load_per_length) / (math.pi * semi_width)`。按此代码对同一工况回算，L=10/20/40 mm 应分别约为 `b=0.6303/0.4457/0.3151 mm`、`p0=1212/857/606 MPa`，不是文中所列值。
- 建议: 重算并替换整张表。若示例对应别的输入，必须把完整输入一并改明。

### [P0-2] `hertz_equivalent_modulus` 的数值示例表大半与公式不符
- 位置: `docs/help/terms/hertz_equivalent_modulus.md:24-28`
- 证据: `| 钢-铝 | ... | ≈ 56706 |`、`| 钢-铸铁 | ... | ≈ 79867 |`、`| 钢-PA66 | ... | ≈ 2989 |`、`| 钢-青铜 | ... | ≈ 69028 |`
- 对照: `core/hertz/calculator.py:118` — `e_eq = 1.0 / (((1.0 - nu1 * nu1) / e1) + ((1.0 - nu2 * nu2) / e2))`。按此式回算，上述四行应约为 `58605`、`82622`、`3517`、`81231 MPa`；只有"钢-钢 ≈115385"基本对上。
- 建议: 逐行按 `calculator.py:118` 重算。若想采用别的材料常数，先把 E/ν 行内参数改对，再给结果。

### [P0-3] "取齿宽作保守上界" 被写成"偏保守估计"，方向反了
- 位置: `docs/help/terms/hertz_contact_length.md:62`
- 证据: `工程设计取齿宽是偏**保守**估计（L 偏大 → p0 偏低 → 安全裕度偏乐观）。`
- 对照: `calculator.py:139-143`，`q = F/L`，L 偏大 → `p0` 偏低 → 安全裕度偏乐观。括号内容已自我说明这不是保守，是**偏乐观/不保守**。
- 建议: 把"偏保守"改成"偏乐观/不保守"，同时明确说明：若实际接触线短于齿宽，真实 `p0` 会高于本工具结果。

---

## P1 重要问题

### [P1-1] 默认 `[p0]=1500 MPa` 的材料归因与同页表格自相矛盾
- 位置: `docs/help/terms/hertz_allowable_pressure.md:41-48`
- 证据: `| 调质合金钢（42CrMo、40Cr） | 700~1100 |`；后文又写：`工具 UI 默认 [p0] = 1500 MPa，对应调质合金钢齿轮齿面的中间值`
- 对照: `core/hertz/calculator.py:120-123` — `float(checks.get("allowable_p0_mpa", 1500.0))`，代码只提供裸默认值 `1500`，并无材料语义绑定。
- 影响: 会把"占位默认值"误包装成"调质钢中间值"，又与同页 700~1100 MPa 表格冲突，用户容易错误沿用默认值。
- 建议: 二选一修正 —— 要么把 1500 改述为"占位默认 / 需重填"，要么把材料归因改成更接近表面硬化齿面的示例并补来源。

### [P1-2] 安全系数推荐表的分档数值未被锚定到任何具体来源
- 位置: `docs/help/terms/hertz_safety_factor.md:26-33`
- 证据: `| 静态单次加载 | 1.0~1.1 |`、`| 稳定工况齿轮/轴承 | 1.2~1.5 |`、`| 振动/频繁启停工况 | 1.5~2.0 |`、`| 关键/安全部件 | 2.0+ |`
- 对照: `calculator.py:175-176` 实际只实现了 `S<1` fail 和 `S<1.2` warning 两层。代码并不知道 1.5~2.0 或 2.0+ 这些分档。
- 影响: 用户容易把表误读成"标准支持的硬门槛"或"工具内置判据"，实则均为无来源的经验数。
- 建议: 给每档补到明确的命名参考（如 ISO 281、DIN 3990）；若无法找到，把表头改为"经验建议（非工具判据）"并注明来源待补。

---

## P2 小问题 / 建议
- `app/ui/pages/hertz_contact_page.py:226-233` 的 `loads.normal_force_n` 没有字段级 `help_ref`；它是直接决定 `p0` 的核心输入，建议补独立术语并把 `tests/ui/test_hertz_help_wiring.py` 一起纳入守护。
- Stage 5 文档里未找到对 Stage 1 `din3996_method_b.md` 的显式链接，也未系统说明 Hertz 局部接触与 interference/Lamé 全周向压力的边界，跨模块认知仍偏弱。
- `_section_loads.md:10` 的 `Ka 1.2~2.5`、`hertz_contact_overview.md:89` 的粗糙度 `3~5 倍` 这类经验数值，来源仍可再收紧。

---

## 赫兹理论维度
线接触与点接触两套公式族区分得比较清楚，且主公式与 `core/hertz/calculator.py:138-148` 一致。四个基本假设也明确写出：光滑、无摩擦、小变形、线弹性，外加半无限空间前提。失效/不适用警告基本齐全，覆盖了塑性、粗糙表面、薄壁、动载、椭圆接触和凹面等场景。允许应力示例范围整体合理。**真正的问题是来源和默认值归因不够严谨，以及两张数值示例表直接错误。**

---

## 跨模块耦合
未发现 Stage 5 对 Stage 1 `din3996_method_b.md` 的显式引用或跳转。也未发现对"赫兹 = 局部点/线接触压力"与"Lamé/interference = 全圆周过盈接触压力"这一关键边界的正面解释；当前只有零散的"蜗轮齿沟""过盈压装检查"提法，读者需要自己推断模块分工。

---

## 总体判断
**Round 2 必要**。当前至少有两张数值示例表（`hertz_contact_length`、`hertz_equivalent_modulus`）和一处保守性判断（`hertz_contact_length:62`）直接违背 `calculator.py` 的数学行为，属于会把用户教错的内容错误。先修正这三条 P0，再收紧默认值归因与安全系数来源（P1），才适合 merge。
