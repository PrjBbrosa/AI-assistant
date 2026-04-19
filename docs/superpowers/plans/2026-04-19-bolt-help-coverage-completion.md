# Bolt Help Coverage Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire help buttons for the remaining 35 `FieldSpec` entries in `app/ui/pages/bolt_page.py` so the VDI 2230 bolt module has 100% field-level help coverage.

**Architecture:** Two batches: **A-class** (13 fields) reuses existing term md files — only `help_ref=` arg added to `FieldSpec(...)`. **B-class** (22 fields) requires writing new term md files matching the style of existing `docs/help/terms/bolt_*.md` (title, 一句话, 怎么理解, sections, 出处 line). All wiring additions are mirrored in `tests/ui/test_bolt_help_wiring.py::EXPECTED_FIELD_HELP_REFS`.

**Tech Stack:** Python 3.12, PySide6 FieldSpec dataclass, Markdown help content, pytest wiring guard tests. No Qt rewrite, no help system changes.

**Scope check:** Single subsystem (bolt help content), focused on content authoring + config. Appropriate for a single plan.

---

## File Structure

**Modify:**
- `app/ui/pages/bolt_page.py` — add `help_ref="..."` arg to 35 existing `FieldSpec(...)` calls (30 inline + 5 inside `_make_layer_fields(n)`; the latter contains 3 distinct semantic fields that need help)
- `tests/ui/test_bolt_help_wiring.py` — extend `EXPECTED_FIELD_HELP_REFS` dict (+30 entries; 5 layer fields omitted from explicit parametrization because they are dynamically generated, but will be covered by the "md exists" guard test via `_all_field_specs()`)

**Create (22 new md files):**
- `docs/help/terms/bolt_joint_type.md`
- `docs/help/terms/bolt_clamped_solid_type.md`
- `docs/help/terms/bolt_clamped_part_count.md`
- `docs/help/terms/bolt_clamp_length_lk.md`
- `docs/help/terms/bolt_equivalent_outer_da.md`
- `docs/help/terms/bolt_layer_thickness.md`
- `docs/help/terms/bolt_layer_outer_da.md`
- `docs/help/terms/bolt_layer_material.md`
- `docs/help/terms/bolt_bolt_material.md`
- `docs/help/terms/bolt_clamped_material.md`
- `docs/help/terms/bolt_bearing_material.md`
- `docs/help/terms/bolt_surface_treatment.md`
- `docs/help/terms/bolt_friction_interfaces.md`
- `docs/help/terms/bolt_slip_friction_coefficient.md`
- `docs/help/terms/bolt_eccentric_clamp.md`
- `docs/help/terms/bolt_eccentric_load.md`
- `docs/help/terms/bolt_thread_flank_angle.md`
- `docs/help/terms/bolt_prevailing_torque.md`
- `docs/help/terms/bolt_setup_case.md`
- `docs/help/terms/bolt_load_cycles.md`
- `docs/help/terms/bolt_strip_safety_required.md`
- `docs/help/terms/bolt_custom_part_count.md`

**Reference template** (follow exactly; copy from `docs/help/terms/bolt_yield_strength.md`):

```markdown
# <中文标题>（<符号/英文>）

**一句话**：<一句概括，~30 字>。

**怎么理解**：<3-5 行通俗解释，建立直觉>。

## <章节 1：值从哪来 / 如何确定>

- ...

## <章节 2：典型值 / 参考表>

| ... | ... |
|---|---|

## <章节 3：影响了什么校核 / 在公式中的位置>

```
公式：...
```

## 常见误用

- **误用 1**：...
- **误用 2**：...

**出处**：<GB/T, ISO, VDI, DIN 等标准引用>
```

---

## Task 1: A-class wiring (13 fields, no new md)

**Files:**
- Modify: `app/ui/pages/bolt_page.py` (13 `FieldSpec(...)` calls at lines 154, 172, 244, 251, 312, 320, 381, 570, 631, 649, 657, 665, 690)
- Modify: `tests/ui/test_bolt_help_wiring.py` (extend `EXPECTED_FIELD_HELP_REFS`)

- [ ] **Step 1: Update the test first (TDD)**

Edit `tests/ui/test_bolt_help_wiring.py`. Add these entries to `EXPECTED_FIELD_HELP_REFS`:

```python
    # A-class additions (reuse existing md)
    "fastener.d2": "terms/bolt_stress_area",
    "fastener.d3": "terms/bolt_stress_area",
    "bearing.bearing_d_inner": "terms/bolt_bearing_pressure_allowable",
    "bearing.bearing_d_outer": "terms/bolt_bearing_pressure_allowable",
    "clamped.surface_class": "terms/bolt_embed_loss",
    "loads.FQ_max": "terms/bolt_axial_load_fa",
    "operating.alpha_bolt": "terms/bolt_thermal_loss",
    "operating.alpha_parts": "terms/bolt_thermal_loss",
    "operating.temp_bolt": "terms/bolt_thermal_loss",
    "operating.temp_parts": "terms/bolt_thermal_loss",
    "introduction.position": "terms/bolt_load_intro_factor",
```

Note: 2 of the 13 A-class fields are the layer fields `E` and `alpha` in `_make_layer_fields` and are dynamically generated (field_ids like `clamped.layer_1.E`). Because the test uses `parametrize(EXPECTED_FIELD_HELP_REFS.items())`, we list only the 11 concrete static field_ids here. The layer fields' correctness is covered by `test_all_field_help_refs_point_to_existing_markdown` (every set `help_ref` must have an existing md — which is true for `terms/elastic_modulus` and `terms/bolt_thermal_loss`).

- [ ] **Step 2: Run test to verify it fails**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: the 11 new parametrized assertions FAIL with `expected help_ref='...', got ''`.

- [ ] **Step 3: Add `help_ref=` to each `FieldSpec` in `bolt_page.py`**

Open `app/ui/pages/bolt_page.py` and add `help_ref="..."` to the following `FieldSpec(...)` blocks. For each, insert the kwarg as the last argument (after `default=...` or wherever fits syntactically):

| Line | field_id | Add kwarg |
|---|---|---|
| 154 | `clamped.layer_<n>.E` (in `_make_layer_fields`) | `help_ref="terms/elastic_modulus"` |
| 172 | `clamped.layer_<n>.alpha` (in `_make_layer_fields`) | `help_ref="terms/bolt_thermal_loss"` |
| 244 | `fastener.d2` | `help_ref="terms/bolt_stress_area"` |
| 251 | `fastener.d3` | `help_ref="terms/bolt_stress_area"` |
| 312 | `bearing.bearing_d_inner` | `help_ref="terms/bolt_bearing_pressure_allowable"` |
| 320 | `bearing.bearing_d_outer` | `help_ref="terms/bolt_bearing_pressure_allowable"` |
| 381 | `clamped.surface_class` | `help_ref="terms/bolt_embed_loss"` |
| 570 | `loads.FQ_max` | `help_ref="terms/bolt_axial_load_fa"` |
| 631 | `operating.alpha_bolt` | `help_ref="terms/bolt_thermal_loss"` |
| 649 | `operating.alpha_parts` | `help_ref="terms/bolt_thermal_loss"` |
| 657 | `operating.temp_bolt` | `help_ref="terms/bolt_thermal_loss"` |
| 665 | `operating.temp_parts` | `help_ref="terms/bolt_thermal_loss"` |
| 690 | `introduction.position` | `help_ref="terms/bolt_load_intro_factor"` |

- [ ] **Step 4: Run test to verify it passes**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: all PASS (including the orphan test, since A-class reuses already-referenced md).

- [ ] **Step 5: Run full UI suite (no regression)**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/ -q
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add app/ui/pages/bolt_page.py tests/ui/test_bolt_help_wiring.py
git commit -m "feat(bolt-help): wire A-class field helps to existing md"
```

---

## Task 2: B-class batch 1 — Connection geometry (7 md + wiring)

**Files:**
- Create: `docs/help/terms/bolt_joint_type.md`, `bolt_clamped_solid_type.md`, `bolt_clamped_part_count.md`, `bolt_custom_part_count.md`, `bolt_clamp_length_lk.md`, `bolt_equivalent_outer_da.md`
- Modify: `app/ui/pages/bolt_page.py` (add `help_ref=` to 6 FieldSpecs at lines 196, 348, 358, 368, 391, 399)
- Modify: `tests/ui/test_bolt_help_wiring.py` (extend `EXPECTED_FIELD_HELP_REFS`)

- [ ] **Step 1: Write md files**

Each md must be ≥ 40 lines, with title + 一句话 + 怎么理解 + at least 2 `##` sections + `**出处**` line. Follow the template at the top of this plan.

**`docs/help/terms/bolt_joint_type.md`** — topic: 连接形式（通孔 DSV / 螺纹孔 ESV）

Key points to cover:
- 一句话：DSV（Durchsteckverbindung，通孔）螺栓头 + 螺母夹紧；ESV（Einschraubverbindung，螺纹孔）螺栓直接拧入基体。
- 区别影响：支承面数量、扭矩校核中 μK 作用位置、ESV 需额外校核螺纹脱扣
- 选型准则：基体够厚 + 不便使用螺母 → ESV；薄板 / 可维护拆卸 → DSV
- 常见误用：ESV 把 μK 当成双支承面计算，或 DSV 忘记上下支承面都算 μK
- 出处：VDI 2230:2015 §3.2, GB/T 16823.1

**`docs/help/terms/bolt_clamped_solid_type.md`** — topic: 基础实体类型（圆柱体 / 锥台）

Key points:
- 一句话：确定被夹件的刚度/顺度计算采用哪种解析模型（VDI 2230 §5.1.2）
- 圆柱体：统一外径 DA，整个夹紧长度一根圆柱；适用均匀被夹件（单层或多层但材料相近）
- 锥台：螺栓头支承处从 DKm,o 起以 30°-50° 锥角扩散到 D_lim；适用薄板多层复杂几何
- 选型准则：DA ≤ DKm,o + lK → 圆柱；DA 较大且材料均匀 → 锥台
- 出处：VDI 2230:2015 §5.1.2 Figure 5.1, GB/T 13806-2008

**`docs/help/terms/bolt_clamped_part_count.md`** — topic: 被夹件数量

Key points:
- 一句话：参与夹紧的独立零件层数，决定多层柔度叠加项数与界面沉陷损失层数
- 层数影响：沉陷损失 FZ 每层 + 每层厚度/材料不同 → 柔度链变长
- 默认 1 层（单一被夹件）；垫圈、间隔套算独立层
- 输入与 custom_count 配合：choice 模式固定 1/2/3/4；custom 模式支持 1-8
- 出处：VDI 2230:2015 §5.1.2.4 Table 5.4, GB/T 5279

**`docs/help/terms/bolt_custom_part_count.md`** — topic: 自定义层数（1-8）

Key points:
- 一句话：在 part_count=自定义 时，指定被夹件精确层数（1-8）
- 超过 8 层建议改用等效圆柱模型 + 一个 DA；真实 8+ 层工程极少
- 输入校验：非整数 / >8 会被 InputError 拒绝
- 出处：VDI 2230:2015 §5.1.2.4

**`docs/help/terms/bolt_clamp_length_lk.md`** — topic: 总夹紧长度 lK

Key points:
- 一句话：被夹件总厚度之和，即螺栓预紧力在轴向作用的有效长度
- 计算方式：Σ layer.thickness（所有层厚度相加），ESV 还要加有效螺纹啮合长度修正
- 影响校核：螺栓柔度 δS = lK/(E·AS)；夹紧锥高、界面沉陷
- 常见误用：把"螺栓总长"填成 lK（lK 只算被夹件，不含螺栓头/螺母/伸出段）
- 出处：VDI 2230:2015 §5.1.2.2 Eq. 5.1, DIN ISO 898-1

**`docs/help/terms/bolt_equivalent_outer_da.md`** — topic: 被夹件等效外径 DA

Key points:
- 一句话：把不规则被夹件近似为圆柱体时的直径，VDI 2230 圆柱模型输入
- 典型值：DKm,o（支承外径）的 1.5-3 倍；图 5.1 给出几何推导
- DA ≥ DKm,o + lK → 圆柱模型适用；否则改用锥台模型
- 影响：被夹件刚度 KP = E·π·(DA²-dh²)/(4·lK)；DA 偏大 → KP 偏大 → 柔度偏小
- 常见误用：直接填零件整体最大尺寸，忽略锥台扩散区限制
- 出处：VDI 2230:2015 §5.1.2 Eq. 5.4, Figure 5.1

- [ ] **Step 2: Add entries to `tests/ui/test_bolt_help_wiring.py::EXPECTED_FIELD_HELP_REFS`**

```python
    # B-class batch 1: geometry
    "elements.joint_type": "terms/bolt_joint_type",
    "clamped.basic_solid": "terms/bolt_clamped_solid_type",
    "clamped.part_count": "terms/bolt_clamped_part_count",
    "clamped.custom_count": "terms/bolt_custom_part_count",
    "clamped.total_thickness": "terms/bolt_clamp_length_lk",
    "clamped.D_A": "terms/bolt_equivalent_outer_da",
```

- [ ] **Step 3: Add `help_ref=` to the 6 FieldSpecs in `bolt_page.py`**

| Line | field_id | help_ref |
|---|---|---|
| 196 | `elements.joint_type` | `"terms/bolt_joint_type"` |
| 348 | `clamped.basic_solid` | `"terms/bolt_clamped_solid_type"` |
| 358 | `clamped.part_count` | `"terms/bolt_clamped_part_count"` |
| 368 | `clamped.custom_count` | `"terms/bolt_custom_part_count"` |
| 391 | `clamped.total_thickness` | `"terms/bolt_clamp_length_lk"` |
| 399 | `clamped.D_A` | `"terms/bolt_equivalent_outer_da"` |

- [ ] **Step 4: Run test**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: all PASS (6 new + 21 prior = 27 wiring asserts; the orphan-md test passes because every new md is referenced).

- [ ] **Step 5: Commit**

```bash
git add docs/help/terms/bolt_joint_type.md docs/help/terms/bolt_clamped_solid_type.md docs/help/terms/bolt_clamped_part_count.md docs/help/terms/bolt_custom_part_count.md docs/help/terms/bolt_clamp_length_lk.md docs/help/terms/bolt_equivalent_outer_da.md app/ui/pages/bolt_page.py tests/ui/test_bolt_help_wiring.py
git commit -m "feat(bolt-help): connection geometry term md + wiring"
```

---

## Task 3: B-class batch 2 — Layer parameters (3 md + wiring inside `_make_layer_fields`)

**Files:**
- Create: `docs/help/terms/bolt_layer_thickness.md`, `bolt_layer_outer_da.md`, `bolt_layer_material.md`
- Modify: `app/ui/pages/bolt_page.py::_make_layer_fields` (add `help_ref=` to 3 FieldSpecs at lines 138, 146, 162)

- [ ] **Step 1: Write md files**

**`docs/help/terms/bolt_layer_thickness.md`**

- 一句话：第 n 层被夹件的厚度，与其他层 thickness 求和得到 lK
- 如何量：从装配图标注读出；多层混合材料时逐层独立
- 影响：柔度链 Σ(li/(E_i·A_i))；越薄柔度贡献越小
- 常见误用：把螺栓有效螺纹长度算进 layer.thickness；ESV 模式下螺纹咬合段单独处理
- 出处：VDI 2230:2015 §5.1.2.3

**`docs/help/terms/bolt_layer_outer_da.md`**

- 一句话：第 n 层被夹件外径，用于计算该层的有效承载面积
- 层内各向异性：若某层显著比邻层粗，可能触发锥台断面分段
- 默认 = DA；仅在"逐层独立外径"场景下逐层填
- 出处：VDI 2230:2015 §5.1.2.5

**`docs/help/terms/bolt_layer_material.md`**

- 一句话：第 n 层材料选择，自动填入 α（热膨胀系数）并可推导 E
- 下拉：钢（α ≈ 11.5e-6 /K, E ≈ 210000 MPa）、铝合金（α ≈ 23.5e-6, E ≈ 70000）、铸铁（α ≈ 10, E ≈ 100000-130000）、不锈钢（α ≈ 17, E ≈ 193000）、自定义
- 常见误用：把"混合材料总效应"填成一个材料；应该逐层独立
- 出处：GB/T 1220 / ISO 3506（材料与力学性能）, VDI 2230:2015 Table 5.4

- [ ] **Step 2: Update `EXPECTED_FIELD_HELP_REFS`** — add note comment only (no parametrized entries since field_ids are dynamic):

```python
    # layer fields use _make_layer_fields and dynamic field_ids
    # (clamped.layer_1.thickness, clamped.layer_2.thickness, ...)
    # Coverage verified by test_all_field_help_refs_point_to_existing_markdown.
```

- [ ] **Step 3: Add `help_ref=` inside `_make_layer_fields`**

In `app/ui/pages/bolt_page.py`, edit the 3 FieldSpec calls inside `_make_layer_fields(n)`:

| Line | field | help_ref |
|---|---|---|
| 138 | layer thickness | `"terms/bolt_layer_thickness"` |
| 146 | layer D_A | `"terms/bolt_layer_outer_da"` |
| 162 | layer material | `"terms/bolt_layer_material"` |

- [ ] **Step 4: Run tests**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: all PASS. The orphan guard now protects 3 more term files.

- [ ] **Step 5: Commit**

```bash
git add docs/help/terms/bolt_layer_thickness.md docs/help/terms/bolt_layer_outer_da.md docs/help/terms/bolt_layer_material.md app/ui/pages/bolt_page.py tests/ui/test_bolt_help_wiring.py
git commit -m "feat(bolt-help): layer parameter term md + wiring"
```

---

## Task 4: B-class batch 3 — Materials (4 md + wiring)

**Files:**
- Create: `docs/help/terms/bolt_bolt_material.md`, `bolt_clamped_material.md`, `bolt_bearing_material.md`, `bolt_surface_treatment.md`
- Modify: `app/ui/pages/bolt_page.py` at lines 328, 611, 621, 639
- Modify: `tests/ui/test_bolt_help_wiring.py`

- [ ] **Step 1: Write md files**

**`bolt_bolt_material.md`** — 螺栓材料选择

- 一句话：下拉选择螺栓母材类别，自动填入 α_bolt 与推导 Rp0.2 / E
- 典型类别：碳钢调质（8.8-10.9）、合金钢调质（12.9）、不锈钢 A2-70/A4-80、铝合金、钛合金
- 影响：α_bolt → 热膨胀损失 FZ,T；Rp0.2 → 屈服校核 allowable
- 常见误用：选 8.8 级但手填 α=20e-6（不锈钢的值）
- 出处：GB/T 3098.1 / ISO 898-1 Table 4

**`bolt_clamped_material.md`** — 被夹件总体材料（单层模式）

- 一句话：单层被夹件的材料选择，决定 E_clamped 与 α_parts
- 与 layer_material 关系：单层时用这个全局字段；多层时各层独立
- 典型：同 bolt_material 类别列表，再加铸铁（热膨胀低、刚度中）
- 出处：VDI 2230:2015 Table 5.4

**`bolt_bearing_material.md`** — 支承面材料

- 一句话：螺栓头/螺母下方接触件的材料，影响支承接触应力 p_G 的 allowable 上限
- 与 bearing.p_G_allow 关系：选定材料自动填入推荐 p_G,allow；自定义可覆盖
- 典型：钢（1300-2000 MPa）、铝（400-600）、铸铁（900-1200）、软木/垫圈（视型号）
- 常见误用：用螺栓本身的 Rp0.2 当 p_G,allow（p_G,allow 是被支承件的硬度相关值，不是螺栓的）
- 出处：VDI 2230:2015 §5.5.1 Table 5.10

**`bolt_surface_treatment.md`** — 螺纹表面处理

- 一句话：螺纹表面涂层/润滑状态，影响 μG（螺纹摩擦系数）默认取值
- 下拉：黑色氧化 / 镀锌 / 达克罗 / 磷化 / Molykote 润滑 / 干燥无润滑 / 自定义
- 选定后联动 tightening.mu_thread 的默认值（可被手填覆盖）
- 出处：VDI 2230:2015 Table A7, GB/T 3098.4

- [ ] **Step 2: Update test**

Append to `EXPECTED_FIELD_HELP_REFS`:

```python
    # B-class batch 3: materials
    "bearing.bearing_material": "terms/bolt_bearing_material",
    "options.surface_treatment": "terms/bolt_surface_treatment",
    "operating.bolt_material": "terms/bolt_bolt_material",
    "operating.clamped_material": "terms/bolt_clamped_material",
```

- [ ] **Step 3: Add `help_ref=` in `bolt_page.py`**

| Line | field_id | help_ref |
|---|---|---|
| 328 | `bearing.bearing_material` | `"terms/bolt_bearing_material"` |
| 611 | `options.surface_treatment` | `"terms/bolt_surface_treatment"` |
| 621 | `operating.bolt_material` | `"terms/bolt_bolt_material"` |
| 639 | `operating.clamped_material` | `"terms/bolt_clamped_material"` |

- [ ] **Step 4: Run tests**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/help/terms/bolt_bolt_material.md docs/help/terms/bolt_clamped_material.md docs/help/terms/bolt_bearing_material.md docs/help/terms/bolt_surface_treatment.md app/ui/pages/bolt_page.py tests/ui/test_bolt_help_wiring.py
git commit -m "feat(bolt-help): material term md + wiring"
```

---

## Task 5: B-class batch 4 — Transverse loads & eccentric (4 md + wiring)

**Files:**
- Create: `docs/help/terms/bolt_friction_interfaces.md`, `bolt_slip_friction_coefficient.md`, `bolt_eccentric_clamp.md`, `bolt_eccentric_load.md`
- Modify: `app/ui/pages/bolt_page.py` at lines 587, 595, 708, 716
- Modify: `tests/ui/test_bolt_help_wiring.py`

- [ ] **Step 1: Write md files**

**`bolt_friction_interfaces.md`** — 摩擦面数 qF

- 一句话：横向载荷 FQ 传递路径上由螺栓压紧的摩擦界面数量，决定防滑校核中的有效摩擦力
- 典型值：1（两件直接接触）、2（两侧对称夹持）、3+（多层叠片）
- 防滑校核：FQ_max ≤ μT · qF · FK,R / S_T
- 常见误用：3 件叠加填 2（只算中间一个界面漏了）；螺栓头下螺母面算成摩擦面（不是）
- 出处：VDI 2230:2015 §5.5.4 Eq. 5.45

**`bolt_slip_friction_coefficient.md`** — 防滑摩擦系数 μT

- 一句话：被夹件-被夹件界面的静摩擦系数，支配横向载荷防滑校核
- 典型值：干燥钢/钢 0.1-0.2、涂漆 0.05-0.1、镀层 0.15-0.3、滚花/喷丸 0.3-0.5
- 与 μG、μK 区别：μT 是 part-part 界面，μG 是螺纹、μK 是螺栓头/螺母支承
- 保守原则：取区间下限
- 出处：VDI 2230:2015 Table A8, GB/T 11601

**`bolt_eccentric_clamp.md`** — 夹紧偏心 e_clamp

- 一句话：螺栓轴线到被夹件"夹紧中心"（刚度中心）的距离，引起被夹件弯矩负担不均
- 计算：由装配图几何直接量；对称夹紧 e_clamp = 0
- 影响：弯曲柔度增量 δP,M = f(e_clamp²)；载荷导入因子 n 的基础
- 常见误用：把"螺栓到零件边缘距离"填成 e_clamp（应该是到"夹紧中心"）
- 出处：VDI 2230:2015 §5.1.3 Figure 5.9, Eq. 5.18

**`bolt_eccentric_load.md`** — 载荷偏心 e_load

- 一句话：外部轴向载荷 FA 作用线到螺栓轴线的距离，决定螺栓附加弯矩幅值
- 计算：由载荷几何/工况定义；对中载荷 e_load = 0
- 影响：附加弯矩 MB = FA · e_load；叠加到螺栓应力上
- 常见误用：和 e_clamp 搞混；两者独立（一个是刚度中心位移，一个是力作用点位移）
- 出处：VDI 2230:2015 §5.1.3 Figure 5.9, Eq. 5.19

- [ ] **Step 2: Update test**

```python
    # B-class batch 4: transverse & eccentric
    "loads.friction_interfaces": "terms/bolt_friction_interfaces",
    "loads.slip_friction_coefficient": "terms/bolt_slip_friction_coefficient",
    "introduction.eccentric_clamp": "terms/bolt_eccentric_clamp",
    "introduction.eccentric_load": "terms/bolt_eccentric_load",
```

- [ ] **Step 3: Add `help_ref=` in page.py**

| Line | field_id | help_ref |
|---|---|---|
| 587 | `loads.friction_interfaces` | `"terms/bolt_friction_interfaces"` |
| 595 | `loads.slip_friction_coefficient` | `"terms/bolt_slip_friction_coefficient"` |
| 708 | `introduction.eccentric_clamp` | `"terms/bolt_eccentric_clamp"` |
| 716 | `introduction.eccentric_load` | `"terms/bolt_eccentric_load"` |

- [ ] **Step 4: Run tests**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/help/terms/bolt_friction_interfaces.md docs/help/terms/bolt_slip_friction_coefficient.md docs/help/terms/bolt_eccentric_clamp.md docs/help/terms/bolt_eccentric_load.md app/ui/pages/bolt_page.py tests/ui/test_bolt_help_wiring.py
git commit -m "feat(bolt-help): transverse load & eccentric term md + wiring"
```

---

## Task 6: B-class batch 5 — Tightening & operating misc (5 md + wiring)

**Files:**
- Create: `docs/help/terms/bolt_thread_flank_angle.md`, `bolt_prevailing_torque.md`, `bolt_setup_case.md`, `bolt_load_cycles.md`, `bolt_strip_safety_required.md`
- Modify: `app/ui/pages/bolt_page.py` at lines 304, 510, 553, 603, 760
- Modify: `tests/ui/test_bolt_help_wiring.py`

- [ ] **Step 1: Write md files**

**`bolt_thread_flank_angle.md`** — 牙型角

- 一句话：螺纹牙侧与螺纹轴法面的夹角；公制螺纹标准 60°
- 进入公式：扭矩系数 K ~ (p/(π·d2) + μG/cos(α/2) + μK·rK/d2) 中的 cos(α/2)
- 典型值：公制 60°、UN 60°、梯形 30°、方形 0°
- 常见误用：把"牙型半角"（30°）填成牙型角
- 出处：GB/T 196 / ISO 68, VDI 2230:2015 Eq. 5.24

**`bolt_prevailing_torque.md`** — 附加防松扭矩 MA,prev

- 一句话：防松元件（锁紧螺母、尼龙圈）产生的与预紧无关的基础摩擦扭矩
- 取值：来自供应商规格书（Nyloc M10 约 2-6 N·m，螺纹锁固胶视牌号 1-15 N·m）
- 影响：装配扭矩 MA = MG + MK + MA,prev；不计会高估预紧力
- 常见误用：普通螺母（无防松）填非零值；或螺母自带防松但漏填
- 出处：VDI 2230:2015 §5.4.3, DIN 267-28

**`bolt_setup_case.md`** — 工况类型（静态/动态/疲劳）

- 一句话：工况下拉，决定 S_F（屈服安全）、S_D（疲劳安全）默认取值与是否做疲劳校核
- 选项：静态只需 R4/R5；脉动疲劳需 R6；交变疲劳需 R6 + Goodman；高温长期需考虑蠕变
- 与 load_cycles 联动：静态 ND 无关；疲劳 ND < 1e5 有限寿命，ND ≥ 2e6 无限寿命
- 出处：VDI 2230:2015 §3.3, GB/T 3077

**`bolt_load_cycles.md`** — 载荷循环次数 ND

- 一句话：预期服役期内 FA 从 min 到 max 的循环次数，区分有限寿命与无限寿命疲劳校核
- 典型：起重机 1e5-1e6、发动机曲轴 1e8-1e9、压力容器 1e4
- 影响：ND < 2e6 用 S-N 曲线；≥ 2e6 用 σA,ASV（100% 滚压螺栓）或 σA,SV
- 常见误用：把"工作小时数"填成 ND（要换算成实际载荷循环）
- 出处：VDI 2230:2015 §5.5.2.2 Figure 5.14

**`bolt_strip_safety_required.md`** — 脱扣安全系数要求

- 一句话：螺纹脱扣校核目标安全系数 S_BS,req；实际 S_BS = F_B / F_max 必须 ≥ 该值
- 典型值：常规场景 1.25；关键连接（压力容器、航空）1.5-2.0
- 与 m_eff（有效啮合长度）联动：m_eff 不够 → F_B 不够 → S_BS < required → 失效
- 常见误用：默认 1.0（等同无安全裕度）；忽略 ESV 螺纹孔脱扣
- 出处：VDI 2230:2015 §5.5.5, DIN EN ISO 898-2

- [ ] **Step 2: Update test**

```python
    # B-class batch 5: tightening & operating
    "tightening.thread_flank_angle_deg": "terms/bolt_thread_flank_angle",
    "tightening.prevailing_torque": "terms/bolt_prevailing_torque",
    "operating.setup_case": "terms/bolt_setup_case",
    "operating.load_cycles": "terms/bolt_load_cycles",
    "thread_strip.safety_required": "terms/bolt_strip_safety_required",
```

- [ ] **Step 3: Add `help_ref=` in page.py**

| Line | field_id | help_ref |
|---|---|---|
| 304 | `tightening.thread_flank_angle_deg` | `"terms/bolt_thread_flank_angle"` |
| 510 | `tightening.prevailing_torque` | `"terms/bolt_prevailing_torque"` |
| 553 | `operating.setup_case` | `"terms/bolt_setup_case"` |
| 603 | `operating.load_cycles` | `"terms/bolt_load_cycles"` |
| 760 | `thread_strip.safety_required` | `"terms/bolt_strip_safety_required"` |

- [ ] **Step 4: Run tests**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ui/test_bolt_help_wiring.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/help/terms/bolt_thread_flank_angle.md docs/help/terms/bolt_prevailing_torque.md docs/help/terms/bolt_setup_case.md docs/help/terms/bolt_load_cycles.md docs/help/terms/bolt_strip_safety_required.md app/ui/pages/bolt_page.py tests/ui/test_bolt_help_wiring.py
git commit -m "feat(bolt-help): tightening & operating term md + wiring"
```

---

## Task 7: Full-suite regression + coverage audit

- [ ] **Step 1: Re-run the coverage audit script**

Run this inline script and confirm 0 missing:

```bash
/Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 <<'PY'
import ast
from pathlib import Path

tree = ast.parse(Path("app/ui/pages/bolt_page.py").read_text(encoding="utf-8"))
specs_total = 0
specs_with_help = 0
missing = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "FieldSpec":
        specs_total += 1
        has_hr = any(kw.arg == "help_ref" for kw in node.keywords)
        if has_hr:
            specs_with_help += 1
        else:
            fid = node.args[0].value if node.args and isinstance(node.args[0], ast.Constant) else "?"
            missing.append((fid, node.lineno))
print(f"Total FieldSpec: {specs_total}")
print(f"With help_ref: {specs_with_help}")
print(f"Missing: {len(missing)}")
for fid, line in missing:
    print(f"  L{line}: {fid}")
PY
```

Expected output: `Missing: 0`.

- [ ] **Step 2: Full test suite**

```bash
find . -name __pycache__ -exec rm -rf {} + 2>/dev/null
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ -v 2>&1 | tail -20
```

Expected: all pass. Specifically `tests/ui/test_bolt_help_wiring.py` has 27+ parametrized wiring tests + 2 orphan/existence guards all green.

- [ ] **Step 3: Manual spot check (skip if time-constrained)**

Launch app, open bolt (VDI) module, open a few chapters, click 3-5 `?` buttons across different chapters to verify no popover opens to "帮助内容缺失".

- [ ] **Step 4: Commit (if anything adjusted during spot check)**

If no further changes: this task has no commit; proceed.

---

## Task 8: Codex adversarial review

- [ ] **Step 1: Dispatch Codex rescue reviewer**

Use `codex:rescue` to have Codex CLI independently review all new md content and wiring. Codex will be asked to be adversarial: look for factual errors, incorrect standard references, incorrect formulas, misleading phrasing, and any orphaned file/missing wiring.

Prompt to Codex (the subagent dispatching to codex will wrap this appropriately):

> "Please adversarially review the commits since main branch on `feat/help-popover-redesign` continuation branch (or whichever branch name applies). Focus areas:
>
> 1. **Technical correctness of each new `docs/help/terms/bolt_*.md` file**: Are the formulas right? Standard references (VDI, GB/T, ISO, DIN) actually containing what's cited? Typical value ranges realistic for VDI 2230 context?
> 2. **Wiring completeness**: Does `app/ui/pages/bolt_page.py` have `help_ref=` on every FieldSpec? Does `tests/ui/test_bolt_help_wiring.py::EXPECTED_FIELD_HELP_REFS` match the actual FieldSpec set exactly? Any orphaned md files (exist but unreferenced)?
> 3. **Consistency with existing bolt_*.md files**: Style (section structure, tone, depth)? Terminology consistent (e.g., always μG not μ_G)?
> 4. **Common误用 section quality**: Are the误用 cases realistic failure modes users would actually hit?
>
> Return findings categorized as Critical / Important / Minor. Be specific: cite file:line and quote the problematic text."

- [ ] **Step 2: Apply fixes for every Critical and Important finding**

For each finding the reviewer surfaces, dispatch a fix subagent (or apply directly if trivial):
- Critical (factual error, broken wiring): fix immediately
- Important (unclear phrasing, imprecise value range, missing edge case): fix
- Minor (style nit, punctuation): fix if cheap, defer otherwise

- [ ] **Step 3: Re-run full test suite after each fix**

```bash
QT_QPA_PLATFORM=offscreen /Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python3 -m pytest tests/ -q
```

- [ ] **Step 4: Commit fixes**

```bash
git add <affected files>
git commit -m "fix(bolt-help): address Codex review findings — <short summary>"
```

- [ ] **Step 5: Optional second adversarial pass** (only if first pass surfaced many issues)

---

## Non-goals (explicitly deferred)

- Chapter-level md content (all 6 chapters already have md at `modules/bolt_vdi/_section_*.md` — not modified here)
- Other modules (interference, hertz, spline, worm) help coverage — out of scope
- Translating existing md to English / other languages
- Adding help search / index UI
- Writing any new calculator logic
