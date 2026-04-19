# Stage 1 Adversarial Review — Round 2 (P0 修复复核)
Date: 2026-04-19
Reviewer: codex-rescue (adversarial mode, round 2)
Scope: 验证 Round 1 的 6 条 P0 修复是否实质性落地，并挑新问题

## Round 1 P0 对账清单

### P0-A — PASS
证据: `docs/help/terms/allowable_contact_stress.md:15-20`、`allowable_root_stress.md:15-20` 都补了"各符号含义"；`gear_pressure_angle.md:11-18` 先解释 ZA/ZN/ZI/ZK；`docs/help/modules/worm/_section_load_capacity.md:7-20` 先讲失效模式与 KA/Kv/KHα/KHβ；`_section_geometry.md:7-26` 先逐个解释 m/z1/z2/q/γ/x/b。

### P0-B — PASS
证据: `docs/help/modules/worm/_section_basic.md:27-31` 明写 "Method A…效率 ×0.92、齿面接触应力 ×0.95""Method C…未实现"；与 `core/worm/calculator.py:399-401,504-511` 一致。

### P0-C — PASS
证据: `docs/help/modules/worm/_section_operating.md:9-15,27-34` 使用 `Ft2 = 2000·T2 / d2`、`vs = π·d1·n1 / (60000·cos γ)`、`Ft1 = Fa2 = Ft2·tan(γ + φ')`、`Fn = Ft2 / (cos αn · cos γ)`；与 `core/worm/calculator.py:441-468,524-526` 对齐。

### P0-D — PARTIAL
证据: `docs/help/modules/worm/din3996_method_b.md:34-51` 已改成"不是完整的 DIN 3996:2019 Method B 实现""Method B 风格的工程简化估算器"；`_section_load_capacity.md:32-40` 也改成"非完整 DIN 3996 Method B 公式链"。

但 `din3996_method_b.md:51` 已写 `Cannot verify against original DIN standard`，同页 `:61` 却仍写 `DIN 3996:2019 … §5 (Method B)`。

剩余风险: 仍有"未核原文却给精确条号"的伪权威风险；需要 follow-up 修正。

### P0-E — PASS
证据: `docs/help/GUIDELINES.md:62-83` 新增 A/B/C 三种出处场景、强制 `Cannot verify...`、并明确禁止"未查原文却写精确条号"；`GUIDELINES.md:174` 已把该规则并入 P0 门槛。

### P0-F — PASS
证据: `docs/help/GUIDELINES.md:120-139` 已改为 `gear_profile_shift / gear_pressure_angle / gear_application_factor_ka / worm_lubrication_mode`；`app/ui/pages/worm_gear_page.py:110,116,159,170,183` 与 `tests/ui/test_worm_help_wiring.py:27-35` 全部改成新 `help_ref`。

---

## Round 2 专属刺点

1. **修复是否引入新问题**
`din3996_method_b.md:51,61` 出现"Cannot verify + 精确 §5"自冲突；`docs/help/terms/worm_lubrication_mode.md:1-25` 文件已专名化，但正文仍是泛化"齿轮、蜗轮、轴承"口径。

2. **Cannot verify 标注是否滥用**
未见滥用；现有标注都贴在标准/实现边界处，如 `_section_basic.md:31`、`_section_operating.md:42`、`_section_load_capacity.md:40`。问题是个别条目与精确条号并存（即上面 P0-D 的残余）。

3. **GUIDELINES §8.1 前缀约定是否清晰**
清晰。`GUIDELINES.md:122-139` 已定义 `gear_* / worm_* / bolt_* / spline_*`，且写明"拿不准默认加前缀"。

4. **修复后文章是否仍 400–600 字**
否。`wc -m` 显示：`allowable_contact_stress` 1560 字、`allowable_root_stress` 1463 字、`gear_pressure_angle` 1072 字；已超过 `GUIDELINES.md:59` 的">800 应考虑拆篇"上限。属 P1，不是本轮主阻断。

5. **是否有新 P0**
无新增独立 P0；但 P0-D 尚未完全收口。

---

## 总体判断

**Stage 2 是否可以启动：CONDITIONAL**

条件：先修 `/docs/help/modules/worm/din3996_method_b.md:61` 的"精确条号与 Cannot verify 共存"矛盾（删除或模糊化该条号引用），P0-D 才算真正 PASS，否则该文件违反 GUIDELINES §5.1 的兜底规则本身。
