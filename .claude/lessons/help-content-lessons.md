# Help Content 撰写经验

> 每次撰写 / 审稿帮助文章后，将教训追加到此文件。写 help 内容前必读。

<!-- 格式：
## YYYY-MM-DD 简短标题
- **错误**: 描述犯了什么错
- **正确做法**: 应该怎么做
- **原因**: 为什么这样做是对的
-->

## 2026-04-19 文档不能与 calculator 实际行为脱节

- **错误**：`_section_basic.md` 写"选择 Method A 或 C 不会改变计算结果"，但 `core/worm/calculator.py:399` 对 Method C 直接抛 `InputError`，Method A 还会把效率 ×0.92、齿面应力 ×0.95。文档与实现不一致，对新手是最严重的欺骗。
- **正确做法**：写涉及方法选项 / 开关类字段的说明时，必须先 grep `core/<module>/calculator.py` 里该字段的分支代码，把"选 X 会怎样"精确写清；不是凭标准定义想象。
- **原因**：帮助系统的读者不会去查源码，他们相信文档。文档撒谎的成本在 100% 由读者承担。

## 2026-04-19 公式必须显式带单位

- **错误**：`_section_operating.md` 原文写 `Ft1 = 2·T1/d1`、`vs = π·d1·n1 / (60·cos γ)`，没标单位。但 calculator 用 `2000·T/d`（因为 T 是 N·m、d 是 mm）和 `/60000`（因为 d 是 mm 要换 m）。新手照抄公式会错一个数量级。
- **正确做法**：每条公式后面加 `[T: N·m, d: mm → Ft: N]` 这种方括号单位标注；尤其涉及 SI 单位和工程混用（N·m vs N·mm、kW vs W）时绝不能省。GUIDELINES §5 已把此列为 P0 门槛。
- **原因**：公式本身没有单位信息，单位约定藏在隐含约束里。一旦文档和代码的单位约定不同，结果就差 1000 倍。

## 2026-04-19 术语命名默认加模块族前缀

- **错误**：Stage 1 初稿把 `terms/application_factor_ka`、`terms/pressure_angle`、`terms/lubrication`、`terms/profile_shift` 命名成通用名，打算给 interference / spline / bolt 共用。但内容全是齿轮 / 蜗轮语义，KA 在不同齿型族查表依据不同，pressure_angle 在螺纹 / 花键语义差异大。后续模块复用会踩雷。
- **正确做法**：术语命名**默认加模块族前缀** (`gear_*` / `worm_*` / `bolt_*` / `spline_*`)。只有真正跨模块通用、语义不变的基础物理量（弹性模量 E、泊松比 ν、模数 m）才不加前缀。GUIDELINES §8.1 已把此定成硬约定。
- **原因**：先通用再拆分，重命名工作量 = 1 次 + N 处 help_ref 更新 + 测试更新 + GUIDELINES 表修改；先加前缀再发现真通用，只需合并 / 别名。风险完全不对称。

## 2026-04-19 无法核对标准时必须显式声明

- **错误**：Stage 1 初稿在 `din3996_method_b.md` 引用 `DIN 3996:2019 §5（Method B）及附录 KA/Kv 取值表`，但实际作者从未打开过 DIN 3996 原文。精确条号让读者误以为这是权威出处，读者可能据此写设计依据。
- **正确做法**：GUIDELINES §5.1 场景 B —— 未查过原文的必须写 `Cannot verify against original DIN standard`；禁止写精确条号（精确到节 / 附录）；只能写笼统的"参考 DIN 3996 的 Method B 框架"。更严：若代码是简化近似，必须写"Method B 风格"而非"已实现 Method B"。
- **原因**：工程文档的权威性来自出处可追溯。精确到条号的伪引用比没有引用更糟 —— 前者主动误导读者。

## 2026-04-19 符号要先解释再写公式

- **错误**：`allowable_contact_stress.md` 直接写 `σHP = σH,lim · ZN · ZL · ZR · ZX / SH`，假设读者知道每个 Z 因子是什么。工作 1-2 年的机械工程师（目标读者）可能不知道 ZL 是润滑因子、ZR 是粗糙度因子。
- **正确做法**：P0 术语在展示符号压缩公式前，必须用中文把每个字母的工程含义讲清（ZN 寿命修正、ZL 润滑油膜修正、ZR 齿面粗糙度修正、ZX 尺寸修正...）。按"字母表 → 压缩公式 → 工程取值经验"的顺序，而不是反过来。
- **原因**：压缩公式是"懂的人复习用"，不是"不懂的人学习用"。帮助弹窗是给不懂的人看的，要先降低理解门槛再给密集信息。

## 2026-04-19 单篇字数上限要跟内容类型走

- **错误**：Stage 1 初版 GUIDELINES §5 写"高于 800 字应考虑拆篇"。但 Round 1 review 要求所有符号都必须先解释，`allowable_contact_stress.md` 有 ZN/ZL/ZR/ZX/SH 5 个系数要逐个展开，修完后变成 1560 字。如果死守 800 字上限，只能回到 "堆压缩公式" 的开发者视角。
- **正确做法**：术语常规区间 400–800 字；P0 系数族术语（ZN 族、YN 族）允许 1000–1500 字；超过 1500 字才考虑拆篇。GUIDELINES §5 已放宽。
- **原因**：帮助系统的约束是"一次读完能做决策"，不是"字数最短"。系数族展开是一次性成本，拆篇反而增加读者的跳转代价。

## 2026-04-19 adversarial review 必须用不同人格（或不同子代理）

- **错误**：Stage 0 最初让主会话自己 review 自己的 Stage 0 产出，出了 3 个 P0 漏检（chapter_stack API 契约、popover anchor lifecycle、测试 fixture 污染 production 树）。
- **正确做法**：每个 Stage 末尾调用独立的 `codex:codex-rescue` 子代理做 adversarial review，prompt 里明确"拉满严厉度，禁止空评价，P0 宁多勿少"。Stage 1 确认有效：Round 1 挖出 6 条 P0（真实问题），Round 2 又挖出 P0-D 的"Cannot verify + 精确条号共存"自相矛盾，这是主会话修 P0 时自己刚弄出来的。
- **原因**：Claude 对自己的输出天然有"这看起来挺好"的偏置；换个评审人格 / 模型能打破这个偏置。成本仅是一次 codex 调用（约 5-10 分钟），收益是整个 Stage 的质量下限。

## 2026-04-19 Stage 2（bolt VDI 2230） — "读过的 lesson ≠ 吸收的 lesson"

Stage 2 adversarial review Round 1 挖出 5 条 P0，其中 2 条（L1 doc-vs-calc、L4 精确条款号）是 Stage 1 lessons 里已经明写过的。主会话自以为读了 lessons 文件，但实际写作时**又违反**。这是 Stage 2 最大教训：

### 错误：只"提及" lessons，不"对照" lessons

- **错误**：Stage 2 开始前主会话"阅读了" lessons 文件，但写作时凭印象执行，没有逐条回看。结果 L4（禁止精确 §/表）被直接违反 10+ 次（`§5.3`、`§5.4.2`、`§5.5.5`、`表 A.5`、`表 5.4/1` 等）。
- **正确做法**：把 lessons 转成**可执行检查清单**。写完每个 section / term，逐条过一遍：
  1. grep `§[0-9]\|表 [A-Z]\.[0-9]\|附录 [A-Z]` —— L4 检查
  2. 核对术语文里每个"本工具实现"的公式 vs `core/<module>/calculator.py` —— L1 检查
  3. 检查术语命名是否有模块族前缀 —— L3 检查
- **原因**：Lessons 不是一次性"读完"就吸收的知识。写作过程中会有大量"凭感觉"的决策，那些决策本来就是 lessons 提醒你别做的事。必须把 lessons 变成**写完强制跑的 linter**。

### 错误：文档比代码更细致 —— 把设想当实现描述

- **错误**：`bolt_embed_loss.md` 写了 VDI 原表（螺纹 / 头下方 / 板板分别给 μm 值），再给一个 10.5 μm 算例 "本工具按此估算"。但代码只用一个常数 × 界面数，比 VDI 原表粗糙得多。这不是"简化"，是"文档主动给读者错的印象"。
- **正确做法**：描述"本工具实现"的段落**只能**写代码真正做的事。VDI 原表可作为"进阶参考"单列，但要明说"本工具未实现"。写前对着 `_estimate_embed_loss` 函数源码逐行抄一遍再扩展解释。
- **原因**：新手读助手文档是为了"理解我在用什么工具"，不是学标准原文。写得比代码"更高端"会让用户用 VDI 原表手算一次、然后与工具输出对不上，最后质疑工具。

### 错误：文档写"流失"时没想清楚物理方向

- **错误**：`bolt_thermal_loss.md` 原版用"ΔL 可正可负、Fth 可正可负"的有向模型描述。但 `calculator.py:337-391` 始终取 `abs()`，把所有温差变化都当成损失。文档的"方向符号约定"是作者想象中的模型，不是代码实现。
- **正确做法**：代码用 `abs()` 的保守做法是**合理工程选择**（R3 校核按最坏情况），但必须在文档里**显式说明**：本工具为保守起见忽略正向增益，只计损失 → 并解释这种近似什么时候会低估裕度（而非风险）。
- **原因**：工程上的"近似"可以保守也可以激进，新手没有判断力区分。必须把近似方向告诉他们，否则他们会用错（比如依赖一个物理上存在但工具忽略的增益）。

### 错误：help_ref wiring 会漏网，靠人工对照不可靠

- **错误**：`loads.seal_force_required` 已有专属术语 `bolt_seal_clamp_force`，但 FieldSpec 的 `help_ref` 没填。原因是写 UI 时对着 "29 个字段清单" 手工勾选，漏了一个。
- **正确做法**：test_bolt_help_wiring.py 已有"每个 help_ref 指向的 md 必须存在"的守护测试；应再加一个反向测试：**每个已写的 terms/bolt_*.md 是否有至少一个字段指向它**。这样术语孤岛会被立刻发现。
- **原因**：文档完成后的 wiring 阶段最容易漏。反向守卫测试能把"术语写了但没人用"的失效暴露出来。

### 错误：5 个 P0 独立 commit 时要防"一条修掉、另一条新造"

- **错误**：修 P0-1 时一次改了 23 个文件（批量替换精确条款号），若不小心会顺手改坏别的位置。
- **正确做法**：批量替换后必须重新 grep 一遍看残留；最后一次 commit 前跑完整 regression 测试（`pytest tests/ui/test_<module>_page.py tests/ui/test_<module>_help_wiring.py tests/core/<module>/` 全量）。Stage 2 实际跑了 167 passed，有效捕捉。
- **原因**：大规模替换风险是"改错地方"或"未改全"。grep 残留扫描 + regression 测试是最便宜的双重保险。

### 错误："跳过校核项" 被误写成 "标 incomplete"（P0-4 专项）

- **错误**：bolt 的 R8 螺纹脱扣在 `core/bolt/calculator.py:512,620-621` 里对 `m_eff` 空值只是**把 `thread_strip_ok` 从 `checks_out` 里省掉**，不设 "incomplete" 标志，`overall_pass = all(checks_out.values())` 对缺失 key 视而不见 → 整体仍可 PASS。但 Stage 2 初版文档里多处写"留空则标 incomplete，不会给 PASS 绿灯"。这会让用户误以为工具在替他们把关。
- **正确做法**：描述"跳过"语义时必须区分三种状态：**显式不通过** (key 存在且 False) / **显式通过** (key 存在且 True) / **根本没校** (key 不存在)。第三种不是 "incomplete" 也不是 "pass"，是工具默默让过。必须在文档中直白告诉用户"UI 不会警告你漏校"。
- **原因**：工程工具的沉默失败比直接错误更危险。新手以为"工具没报错 = 连接合格"，实际是"工具没校这一项"。帮助文档的职责之一就是暴露这种静默的 skip，而不是把它美化成 incomplete。

### 错误：写了术语却没 wiring （术语孤岛 → 需要反向守卫测试）

- **错误**：Stage 2 写了 `terms/bolt_seal_clamp_force.md`，但 `loads.seal_force_required` 字段忘了加 `help_ref` → 用户点不到文章。正向测试（"help_ref 指向的 md 存在"）无法捕捉这种反向失效。
- **正确做法**：在 `test_<module>_help_wiring.py` 加反向守卫：遍历 `docs/help/terms/<module>_*.md`，每篇必须至少被一个 FieldSpec 或 CHAPTER 引用，否则算孤岛→失败。Stage 2 已加 `test_no_orphan_bolt_term_files`。后续模块照抄此模式。
- **原因**：双向守卫测试把"术语 ↔ 字段"当成外键约束处理。任何一端改动都会暴露不一致，避免"写了但没人用" 或 "指了但没写"两种对偶失效。

## 2026-04-19 Stages 3/4/5/6 批量 review — 14 P0 的共性教训

4 个模块的 Stage N.5 adversarial review 合计挖出 **14 P0**，其中 12 条属于 L1 (doc-vs-calc 漂移) 或 L6 (公式单位缺失)。这两条 lesson 已经写过 3 遍了，agents 仍然违反。**必须把 lesson 转成写作流程里的强制步骤，而不是写完再 review 捡漏**。

### 错误：数值示例直接抄教科书，没用 calculator 回算

- **错误**：Stage 5 `hertz_contact_length.md` / `hertz_equivalent_modulus.md` 各写一张 "敏感度 / 典型值" 表，数值与 `core/hertz/calculator.py` 实际算出的差 5~10 倍。Stage 6 `spline_tip_root_diameter.md` 把 `W 20×2×8` 的 h_w 写成 0.5m，实际 catalog 是 1.05m（0.525m/m）。用户照抄这些数字会得到严重错误的设计值。
- **正确做法**：**任何数值示例表写出来前，必须**用 `python3 -c "..."` 或类似临时脚本跑一遍 calculator 实现，把计算结果原样抄进表。不能靠心算、不能靠教科书推导——calculator 本身就是权威。若 calculator 和教科书不一致，**以 calculator 为准并在旁注 "本工具实现与标准教科书差异"**。
- **原因**：文档的职责是"告诉用户工具在做什么"。数值示例是最容易被用户原封照抄的内容。一个数字错了，整张表作废、整篇术语的可信度崩塌。写前跑 calculator 的成本是 30 秒，写完被 review 挖出来返工成本是 30 分钟。

### 错误：简化实现被描述成完整标准

- **错误**：Stage 4 fretting 评分规则在文档里写成"单个 slip_reserve_bonus 0..3"，实际 calculator 有 torque_reserve + combined_reserve 两个独立加分项，max_score = 14 而非 11。Stage 6 DIN 5480 的 5% warning 被写成"通常代表填错"，但内置 catalog 标准条目（如 `W 15×1.25×10`）本身就会触发这个 warning（m·z=12.5 vs d_B=15 偏差 20%）。Stage 3 overview 把 "允许用户覆盖 As/d2/d3" 写成描述，实际 calculator 始终用 d/p 派生值做计算，只做一致性校验。
- **正确做法**：涉及 "scoring rule / threshold / override" 这类"你以为你懂、但实现可能不一样"的场景，**必须**把对应的 calculator 源码贴到 diff 对照窗口，逐行对照确认。尤其是 scoring / warning 判据，工程师脑子里容易自动脑补 "这应该是 max 还是 sum"、"这个 threshold 触发是错误还是正常"——不能凭感觉，要看源码。
- **原因**：工具的简化 / 近似行为是用户最想知道的（这决定什么时候能信工具）。**文档比实现"更精致"或"更简单"都是误导**。

### 错误：物理方向 / 保守性判断写反

- **错误**：Stage 5 `hertz_contact_length.md:62` 写 "工程取齿宽作 L 是偏保守估计（L 偏大 → p0 偏低 → 安全裕度偏乐观）"——括号里明明已经说"安全裕度偏乐观"（即不保守），外面却说"偏保守"。Stage 3 `_section_fatigue_output.md` 说 "σ_a_allow=0 除非 σ_a 也恰为 0 才通过"，实际 calculator 逻辑 `fatigue_ok = (goodman > 0) AND (σ_a ≤ σ_a_allow)`，goodman=0 时无论 σ_a 多少都 FAIL。
- **正确做法**：涉及"保守 / 乐观"、"增大 / 减小"、"必然通过 / 必然失败"这类带物理方向的判断，**必须**写前做"极端值思维实验"：把参数推到极大 / 极小分别看代码输出，对照文档结论。Stage 1 P0-F 已经挖过类似问题（Method A/C），仍然复发。
- **原因**：方向错误比数值错误更危险——数值错误至少还是错在一个数量级内，方向错误会让用户的"直觉校核"完全失效（以为偏保守其实偏乐观 = 设计裕度虚高）。

### 错误：守卫测试只断言"至少 1 个"，抓不到字段级按钮丢失

- **错误**：Stages 3/4/5/6 的 `test_*_help_wiring.py` 都 copy 了 Stage 2 的 `len(help_buttons) >= 1` 断言。章节级按钮存在 + 字段级按钮全丢的回归场景，测试仍 pass。
- **正确做法**：断言改为**精确数**：按章节期望 "1 (章节级) + N (该章节带 help_ref 的 FieldSpec 数)" 个按钮。Stage 2 的教训本来已经标了"test 过宽"，但后续 Stages 没吸收。**后续模块新加 help_wiring 测试前，必须先读 Stage 2 review 里的 P1-3 条目**。
- **原因**：守卫测试的价值是"发现真实的回归"，"至少 1 个"等价于 "几乎不会失败的 smoke"。用精确数做断言几乎没有额外成本（已经从 CHAPTERS / FieldSpec 里数得出来），但覆盖能力指数级提升。

### 错误：lessons 文件被当成 "背景阅读" 而非 "写作检查清单"

- **错误**：Stage 2.5 已经把"必须把 lessons 转成写完强制跑的 linter"这条写进了 lessons。Stage 3/4/5/6 agents 读了 lessons 但仍然没做最基本的 grep 检查（`§[0-9]` / `表 [A-Z]\.[0-9]`）和 calculator 对照。结果 14 条 P0 里 12 条是这两类。
- **正确做法**：**Stage N 启动时的"必读"步骤必须扩展成"必跑"步骤**。每个 section 或 term 写完后，立即运行 3 条检查：
  1. `grep '§[0-9]\|表 [A-Z]\.[0-9]\|附录 [A-Z]' <新文件>` 应 0 命中
  2. 每个公式逐条检查 `[x: unit → y: unit]` 标注
  3. 每个 "本工具实现" / 数值示例要在 calculator 源码里找到对应行，逐字抄（而非凭记忆写）
  然后才进入下一个术语。
- **原因**：人类和 LLM 对"读过的规则"都有强烈的"自以为已吸收"偏差。强制可执行检查才能真正把规则变成行为。这是**本轮最大的流程教训**——应该升级为 CI pre-commit hook 或至少写入 plan 模板 Step B-D 的硬性前置。

### 错误：大型模块（Stage 4 interference 24 术语）被当作"标准模块"处理，一次 review 挖不干净

- **错误**：Stage 4 interference 是所有 stage 里最大的（24 术语，3432 行 diff）。Round 1 review 挖出 4 P0 + 4 P1 + 2 P2。但 review agent 自己也提到"仍有可能漏挖"；修完 Round 1 后我们还没跑 Round 2 就直接合并（context 预算紧张）。如果真要合规，应该触发 Round 2（P0 > 3）。
- **正确做法**：对**规模显著大于基线（bolt Stage 2）** 的模块，Stage N.5 Round 1 一律视为"挖一半"，默认必须 Round 2。或者在写作阶段就拆批（比如 Stage 4 应该在 Step D 分 3 批、每批 8 术语分别 review）。
- **原因**：单轮 review 的认知带宽有限，挖出 4 P0 意味着还没触达问题底。Stage 1.5 Round 2 也曾再挖出 P0-D 残留和 P0-E 新 lesson。大型模块不做 Round 2 就是赌运气。
