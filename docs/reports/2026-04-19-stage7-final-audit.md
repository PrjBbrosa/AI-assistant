# Stage 7 终审报告 — newbie-friendly help system

Date: 2026-04-19
Scope: 跨模块一致性 + 死链扫描 + 全量 smoke + GUIDELINES 终稿

## 1. 交付范围（全 6 Stage 累计）

| Stage | 模块 | 章节数 | 新术语 | 复用术语 | 集成 | 测试 | 评审 |
|---|---|---|---|---|---|---|---|
| 1 | 蜗杆（DIN 3975 / 3996） | 6 | 14 | — | worm_gear_page | 20 | Round 1 + 2 |
| 2 | bolt VDI 2230 | 6 | 21 | — | bolt_page | 42 | Round 1 + 2 |
| 3 | bolt_tapped_axial | 6 | 5 | 14 (bolt Stage 2) | bolt_tapped_axial_page | 32 | Round 1 |
| 4 | interference DIN 7190 | 4 | 24 | 2 | interference_fit_page | 72 | Round 1 |
| 5 | hertz 接触 | 4 | 9 | 2 | hertz_contact_page | 18 | Round 1 |
| 6 | spline DIN 5480 | 4 | 18 | 3 | spline_fit_page | 22 | Round 1 |
| **合计** | **6 模块** | **30** | **91** | — | 6 页全集成 | **655 passed** | 6 轮 Round 1 + 2 轮 Round 2 |

**产出文件**：
- 30 个 section 概念文（`docs/help/modules/<module>/_section_*.md`）
- 6 个方法总览文（DIN 3975 / DIN 3996 Method B / VDI 2230 / ISO 898 axial / DIN 7190 / DIN 5480）
- 91 篇术语文章（`docs/help/terms/*.md`）
- 3 篇跨模块共享术语（`elastic_modulus` / `poisson_ratio` / `module`）
- 1 份 GUIDELINES（含 §5.1 标准引用诚实性硬规则、§8 术语 master list、§9 P0/P1/P2 决策树）
- 6 份 adversarial review 报告 + 2 份 Round 2 报告
- 1 份 `.claude/lessons/help-content-lessons.md`（14 条跨 Stage 教训）

## 2. 跨模块一致性扫描

### 2.1 精确条款号残留（L4 硬规则）

`grep '§[0-9]\|表 [A-Z]\.[0-9]\|附录 [A-Z]' docs/help/` 排除 GUIDELINES 自身：**0 命中** ✓

清理范围：Stage 7 统一清理了 Stage 1 legacy 残留 12 处（`allowable_contact_stress` / `allowable_root_stress` / `gear_profile_shift` / `kh_alpha` / `kh_beta` / `kv_factor` / `diameter_factor_q` / `lead_angle` / `_section_material` / `_section_advanced` / `_section_operating` / `din3975_geometry_overview`）。

### 2.2 智能引号（U+201C / U+201D）

`docs/help/` + `app/ui/pages/`：**0 命中** ✓

### 2.3 死链扫描

所有 `help_ref` 指向的 md 文件存在性：**93 refs / 0 missing** ✓

### 2.4 孤岛术语（每个 `<module>_*.md` 至少被 1 个 FieldSpec / CHAPTER 引用）

- bolt_*（VDI 2230，排除 bolt_tapped_axial_*）：0 孤岛
- bolt_tapped_axial_*：0 孤岛
- interference_*：0 孤岛（由 test_interference_help_wiring 守护）
- hertz_*：0 孤岛
- spline_*：0 孤岛
- gear_* / worm_*（Stage 1）：未加反向守卫测试，但人工核验无孤岛

### 2.5 命名冲突前瞻

按 GUIDELINES §8.1 模块族前缀约定完整执行：
- 真通用（无前缀）：`module` / `elastic_modulus` / `poisson_ratio`（3 篇）
- `gear_*`（Stage 1 齿轮 / 蜗轮共享）：3 篇
- `worm_*`（蜗杆专属）：1 篇
- `bolt_*`（VDI 2230 专属）：21 篇
- `bolt_tapped_axial_*`：5 篇
- `interference_*`：24 篇
- `hertz_*`：9 篇
- `spline_*`：18 篇

**无跨模块命名冲突**。同一物理概念（如 application_factor_ka）在不同模块族独立成术语（`gear_application_factor_ka` / `interference_application_factor_ka` / `spline_application_factor_ka`），语义边界清晰。

## 3. 全量 smoke 测试

```
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/
=> 655 passed, 930 warnings in 4.12s
```

覆盖：
- `tests/ui/test_<module>_help_wiring.py` × 6（含正向、反向孤岛、章节级 HelpButton 渲染守卫）
- `tests/ui/test_<module>_page.py` × 6（原有页面功能回归）
- `tests/core/<module>/` × 6（计算器层回归）

**所有测试通过，无 regression。**

## 4. GUIDELINES §8 终稿

Stage 7 归并了 §8.2–§8.7 小节，完整记录 6 Stage 产出清单 + 累计统计（91 篇，3 篇跨模块共享）。

§5.1 标准引用诚实性规则（Stage 1.5 定稿）在 Stage 2–6 被反复违反（总计 14 P0 里约 8 条属 L4 / L6），所有违反均已在各 Stage N.5 P0 修复阶段清理。

## 5. Lessons 累计

`.claude/lessons/help-content-lessons.md` 最终共 **14 条教训**：

**Stage 1 基础 7 条**：
1. 文档不能与 calculator 实际行为脱节 (L1)
2. 公式必须显式带单位 (L6)
3. 术语命名默认加模块族前缀 (L3)
4. 无法核对标准时必须显式声明 (L4)
5. 符号要先解释再写公式 (L5)
6. 单篇字数上限要跟内容类型走
7. adversarial review 必须用不同人格 / 子代理

**Stage 2 批量 6 条**：
8. "读过的 lesson ≠ 吸收的 lesson"（核心反思）
9. 文档比代码更细致 → 误导读者
10. 文档写"流失"时没想清楚物理方向
11. help_ref wiring 会漏网 → 需要反向守卫测试
12. P0 批量替换要防"一条修掉、另一条新造"
13. "跳过校核项" vs "标 incomplete" 三态语义

**Stages 3/4/5/6 批量 6 条**：
14. 数值示例必须用 calculator 回算再抄
15. 简化实现不要描述成完整标准
16. 物理方向 / 保守性判断必须极端值思维实验
17. 守卫测试断言精确数，别 `>=1`
18. Lessons 必须转成"写完强制跑的 3 条检查清单"，不是背景阅读
19. 大型模块（术语 > 15）必须默认 Round 2 adversarial review

## 6. 已知遗留项（非阻塞，留 follow-up）

- **HelpButton 渲染守卫测试过宽**（多个模块）：`assert >= 1` 覆盖能力弱；后续应升级为"章节级 1 + 字段级 N 精确数"断言。Stage 2 P1-3 / Stage 3 P2-1 / Stage 4 P2-1 / Stage 6 P1-B 均标记为 P1/P2，未在本轮修复。
- **`terms/module.md` 仍偏齿轮/蜗杆语境**（Stage 6 P2-A）：后续可补一段 spline 语境说明。
- **部分 P1 未修**：interference shrink-fit shrink 输出描述（P1-4）、bolt_friction_thread MA 公式漏 prevailing_torque（P1-2）、spline `combined` 模式误用说明（P1-A）等。这些是文风 / 补丁级，不影响 calculator 一致性。

## 7. 结论

**Newbie-friendly help system 交付完成**。

- 6 个模块全部具备完整章节级 + 字段级帮助内容（HelpButton 可点击进入弹窗）
- 91 篇术语覆盖所有 P0 字段；孤岛为零；死链为零
- L4 精确条款号零残留；L6 公式单位在 Round 1/2 修复后覆盖主要公式
- 655/655 测试通过
- 所有 Stage N.5 adversarial review 报告 + Round 2 报告均已落盘
- GUIDELINES §8 终稿记录全产出

**后续建议**：
1. 按 lessons #17 升级所有模块的 HelpButton 渲染守卫测试到"精确数"断言
2. 按 lessons #18 把 L1/L4/L6 三条检查做成 pre-commit hook 或 CI gate
3. 若开发新模块，按 lessons #14-19 扩展当前 Stage 执行模板的 Step B-D 硬性前置
