# 螺栓模块 P0 修复 + 校核链路流程图设计

**日期**: 2026-03-16
**范围**: core/bolt/calculator.py, app/ui/pages/bolt_page.py, app/ui/pages/bolt_flowchart.py (新建), app/ui/theme.py

## 背景

VDI 2230 审查发现以下问题：
- P0-1: R3 残余夹紧力校核恒通过（FM_min 由 FK_req 反推）
- P0-2: phi_n >= 1 时仅警告不阻断，后续公式无物理意义
- P1-1: 支承面压强校核缺失（参数已在 UI 采集）

同时，用户提出左侧步骤导航按数据分类编排，不反映 VDI 2230 校核逻辑流程，需要新增按校核逻辑导航的流程图视图。

---

## 一、Core 层改动（calculator.py）

### 1.1 phi_n >= 1 硬阻断

在 `phi_n = n * phi` 之后，`phi_n >= 1.0` 时 raise InputError：

```python
if phi_n >= 1.0:
    raise InputError(
        f"载荷分配系数 phi_n = {phi_n:.3f} >= 1，外载全部进入螺栓，无物理意义。"
        "请检查刚度模型（δs/δp）与载荷导入系数 n。"
    )
```

删除 warnings 列表中对应的 `phi_n >= 1.0` 软警告代码（calculator.py 第 255-258 行），因为硬阻断在更早位置执行，该代码已不可达。

### 1.2 计算模式：设计模式 + 校核模式

新增 `options.calculation_mode`，取值 `"design"`（默认）或 `"verify"`。

**向后兼容声明**：`calculation_mode` 缺失时默认 `"design"`，计算逻辑与现有实现完全一致，输出仅新增 `calculation_mode` 和 `r3_note` 字段，不改变现有字段值。

**设计模式**（现有逻辑）：
- `FM_min = FK_req + (1 - phi_n) * FA + FZ + Fth`
- `FM_max = alpha_A * FM_min`
- R3：`checks_out["residual_clamp_ok"] = True`（设计模式下数学上恒满足）
- `r3_note = "设计模式下 FM_min 由 FK_req 反推，R3 自动满足"`

**校核模式**：
- 从 `loads.FM_min_input` 读取用户输入的已知预紧力（_require + _positive 验证）
- `FM_min = FM_min_input`（跳过反推）
- `FM_max = alpha_A * FM_min`（alpha_A 仍然需要，两种模式都使用）
- R3 独立校核：`FK_residual = FM_min - FZ - Fth - (1 - phi_n) * FA`，与 FK_req 比较
- `checks_out["residual_clamp_ok"] = f_k_residual >= f_k_required`
- `r3_note = "校核模式：独立验证已知预紧力是否满足残余夹紧需求"`

**两种模式共用的参数**：alpha_A、utilization、mu_thread、mu_bearing 等在两种模式下都参与计算（alpha_A 用于 FM_max，utilization 用于 R4），不做隐藏。

输出新增字段：
- `calculation_mode`: "design" | "verify"
- `r3_note`: 说明字符串

### 1.3 支承面压强校核 R7

```python
p_g_allow = float(bearing.get("p_G_allow", 0.0))
if p_g_allow > 0:
    a_bearing = math.pi / 4.0 * (bearing_d_outer**2 - bearing_d_inner**2)
    p_bearing = fm_max / a_bearing
    pass_bearing = p_bearing <= p_g_allow
    checks_out["bearing_pressure_ok"] = pass_bearing
```

**向后兼容**：当 `p_G_allow` 缺失或为 0 时，R7 校核跳过——不加入 `checks_out`，不影响 `overall_pass`，旧 JSON 正常工作。仅当 `p_G_allow > 0` 时才计算并参与 `overall_pass`。

新增输入：
- `bearing.p_G_allow`: 许用支承面压强 (MPa)，可选字段

材料预设值（仅用于 UI 联动，不传入 Core）：
| 材料     | 默认 p_G_allow |
|----------|---------------|
| 钢       | 700 MPa       |
| 铝合金   | 300 MPa       |
| 自定义   | 用户输入      |

输出新增（仅当 R7 激活时）：
- `stresses_mpa.p_bearing`: 实际支承面压强
- `stresses_mpa.p_G_allow`: 许用值
- `stresses_mpa.A_bearing_mm2`: 支承面面积
- `checks.bearing_pressure_ok`: bool

---

## 二、UI 层改动（bolt_page.py + bolt_flowchart.py）

### 2.1 文件拆分

bolt_page.py 当前已 ~1280 行，本次新增流程图逻辑预估 400-600 行。为维护性考虑，将流程图导航 widget 和 R 详情页构建逻辑拆分为独立模块：

- `app/ui/pages/bolt_flowchart.py`（新建）：包含 `FlowchartNavWidget`（左侧流程图导航）和 `RStepDetailPage`（右侧 R 详情页）
- `app/ui/pages/bolt_page.py`（修改）：引入 bolt_flowchart，组装双 Tab 导航

### 2.2 左侧导航改为双 Tab

左侧 `nav_card` 结构改为：

```
nav_card
├── nav_title ("章节导航")
├── tab_buttons (QHBoxLayout)
│   ├── btn_input_tab ("输入步骤")    ← QPushButton，切换样式
│   └── btn_flow_tab  ("校核链路")
└── nav_stack (QStackedWidget)
    ├── page 0: chapter_list (现有 QListWidget#ChapterList)
    └── page 1: flowchart_nav (FlowchartNavWidget)
```

两个 tab 按钮切换 `nav_stack` 的页面。选中态用主色 `#D97757` 底色，未选中用普通按钮样式。

右侧 `chapter_stack` 扩展，在现有步骤页面之后追加 R0-R7 详情页面。

映射关系：
- "输入步骤" tab 的列表项 → 右侧步骤页面（现有，index 0~N）
- "校核链路" tab 的节点点击 → 右侧 R 详情页面（新增，index N+1~N+8）

切换 tab 时自动跳转到对应 tab 中当前选中项的右侧页面。

### 2.3 FlowchartNavWidget（bolt_flowchart.py）

`QScrollArea` 内垂直排列 R0-R7 节点。

每个节点为 `QFrame#SubCard`（选中时通过 `setProperty("selected", True)` + `style().polish()` 切换为高亮边框 `#D97757`）：

```
┌───────────────────────┐
│ R1 预紧力         ✓   │  ← 标题 QLabel + Badge QLabel 同行
│ FM_min = 12,345 N     │  ← 摘要值 QLabel
└───────────────────────┘
         ↓                  ← QLabel "↓"，居中，SectionHint 样式
┌───────────────────────┐
│ R2 扭矩               │
│ MA = 28.5~39.9 N·m    │
└───────────────────────┘
```

**点击信号**：每个节点 QFrame 重写 `mousePressEvent`，发出 `node_clicked(r_index: int)` 信号。BoltPage 连接此信号到 `chapter_stack.setCurrentIndex(N + 1 + r_index)`。

计算前所有摘要值显示"—"，Badge 为 WaitBadge。

**节点可见性规则**：
- R6：在 basic/thermal 层级下用 `setVisible(False)` 隐藏（仅 fatigue 层级可见）
- R7：始终可见。当 `p_G_allow` 未设置时，计算后 Badge 显示 WaitBadge + "未设置许用压强，已跳过"；当 `p_G_allow > 0` 时正常显示 Pass/Fail

节点数据结构：

```python
R_STEPS = [
    {"id": "r0", "title": "R0 输入汇总",  "has_check": False},
    {"id": "r1", "title": "R1 预紧力",    "has_check": False},
    {"id": "r2", "title": "R2 扭矩",      "has_check": False},
    {"id": "r3", "title": "R3 残余夹紧",  "has_check": True, "check_key": "residual_clamp_ok"},
    {"id": "r4", "title": "R4 装配应力",  "has_check": True, "check_key": "assembly_von_mises_ok"},
    {"id": "r5", "title": "R5 服役应力",  "has_check": True, "check_key": "operating_axial_ok"},
    {"id": "r6", "title": "R6 疲劳",      "has_check": True, "check_key": "fatigue_ok",
     "visibility": "fatigue"},
    {"id": "r7", "title": "R7 支承面",    "has_check": True, "check_key": "bearing_pressure_ok"},
]
```

R0/R1/R2 为纯信息节点（`has_check: False`），不显示 Pass/Fail Badge，只显示数值摘要。

**R3 Badge 特殊逻辑**：设计模式下 Core 返回 `residual_clamp_ok = True`，但流程图节点和结果页均显示 PassBadge + 附注"(设计模式自动满足)"，而非 WaitBadge。理由：True 意味着 R3 确实满足（数学上正确），附注说明原因，避免用户误以为 R3 被跳过。

**R7 Badge 特殊逻辑**：当计算结果的 `checks` 中不含 `bearing_pressure_ok` 时（p_G_allow 未设置），显示 WaitBadge + "未设置许用压强，已跳过"。

### 2.4 RStepDetailPage（bolt_flowchart.py）

每个 R 详情页为 `QFrame#Card`，内含 `QScrollArea`，三个区块：

**区块 1 — 输入回显**：`SubCard` 中用 `QGridLayout` 排列 QLabel 对（参数名 + 当前值，只读）。
底部提示："切换到「输入步骤」可修改参数"。

**区块 2 — 计算过程**：`SubCard` 中用 QLabel（等宽字体 `Menlo` / `Consolas`）逐行展示公式和中间步骤。

示例（R3 校核模式）：
```
FK,res = FM,min - FZ - Fth - (1 - φn) × FA
      = 25000 - 1200 - 800 - (1 - 0.36) × 12000
      = 15320 N

FK,req = max(FK,seal, FQ / (μT × qF))
      = max(3000, 2000 / (0.15 × 1))
      = 13333 N

FK,res = 15320 N ≥ FK,req = 13333 N  →  通过
```

示例（R7 支承面）：
```
A_bearing = π/4 × (DKo² - DKi²)
         = π/4 × (17.2² - 10.5²)
         = 145.8 mm²

p_B = FM,max / A_bearing
    = 17283 / 145.8
    = 118.5 MPa

p_allow = 700 MPa（钢）

p_B = 118.5 MPa ≤ p_allow = 700 MPa  →  通过
```

**区块 3 — 校核结论**：判据一句话 + PassBadge/FailBadge/WaitBadge。
R3 设计模式下显示 WaitBadge + "设计模式下 FM_min 由 FK_req 反推，R3 自动满足"。

各 R 页面回显的输入字段：

| R 步骤 | 回显字段（field_id 或中间值） |
|--------|---------|
| R0 输入汇总 | fastener.d, fastener.p, fastener.As, fastener.d2, fastener.d3, fastener.Rp02, tightening.mu_thread, tightening.mu_bearing, stiffness.bolt_compliance/bolt_stiffness, stiffness.clamped_compliance/clamped_stiffness, stiffness.load_introduction_factor_n, loads.FA_max, loads.FQ_max, tightening.alpha_A, tightening.utilization, options.calculation_mode, options.check_level |
| R1 预紧力 | loads.seal_force_required, loads.FQ_max, loads.slip_friction_coefficient, loads.friction_interfaces, loads.FA_max, 中间值 phi_n, loads.embed_loss, loads.thermal_force_loss |
| R2 扭矩 | fastener.d2, fastener.p, tightening.mu_thread, tightening.mu_bearing, bearing.bearing_d_inner, bearing.bearing_d_outer, tightening.prevailing_torque |
| R3 残余夹紧 | 中间值 FM_min, loads.embed_loss, loads.thermal_force_loss, 中间值 phi_n, loads.FA_max, 中间值 FK_req |
| R4 装配应力 | 中间值 FM_max, fastener.As, fastener.d3, tightening.utilization, fastener.Rp02 |
| R5 服役应力 | 中间值 FM_max, 中间值 phi_n, loads.FA_max, fastener.As, fastener.Rp02, checks.yield_safety_operating |
| R6 疲劳 | 中间值 phi_n, loads.FA_max, fastener.As, 中间值 FM_max, fastener.Rp02, operating.load_cycles |
| R7 支承面 | 中间值 FM_max, bearing.bearing_d_inner, bearing.bearing_d_outer, bearing.p_G_allow |

此映射定义为独立常量 `R_STEP_FIELDS`。

数据填充：`_calculate()` 成功后调用 `_update_flowchart(result)` 和 `_update_r_pages(result)`。

### 2.5 校核层级设置页——新增计算模式

在"步骤 1. 校核层级设置"页面，校核层级下拉框下方新增：

```
计算模式：[设计模式（反推 FM_min）▼]
```

选项：
- 设计模式（反推 FM_min）
- 校核模式（输入已知 FM_min）

模式联动——新增 `_apply_calculation_mode_visibility()` 方法（独立于现有的 `_apply_check_level_visibility`）：

```python
VERIFY_MODE_FIELD_IDS = {"loads.FM_min_input"}
```

- 设计模式：隐藏 `VERIFY_MODE_FIELD_IDS` 中的字段
- 校核模式：显示 `VERIFY_MODE_FIELD_IDS` 中的字段

注意：`alpha_A` 和 `utilization` 在两种模式下均保持可见（alpha_A 用于 FM_max = αA × FM_min，utilization 用于 R4 装配应力校核）。

**UI 引导**：切换到校核模式时，`level_desc_label` 更新为包含提示"请在「步骤 3. 装配属性」中填写已知 FM,min 值"。同理，切回设计模式时恢复原有层级说明文字。

### 2.6 装配属性章节——新增 FM_min_input 字段

在"装配属性"章节末尾（`thermal_force_loss` 之后）新增：

```python
FieldSpec(
    "loads.FM_min_input",
    "已知最小预紧力 FM,min",
    "N",
    "校核模式：输入已有设计的最小预紧力值，跳过反推直接校核。",
    mapping=("loads", "FM_min_input"),
    default="",
),
```

默认隐藏（设计模式），切换到校核模式时显示。

### 2.7 连接件章节——新增支承面材料

在 `bearing_d_outer` 之后新增两个 FieldSpec：

```python
FieldSpec(
    "bearing.bearing_material",
    "支承面材料",
    "-",
    "选择支承面材料以自动填入许用压强。",
    mapping=None,  # 仅用于 UI 联动，不传入 Core
    widget_type="choice",
    options=("钢", "铝合金", "自定义"),
    default="钢",
),
FieldSpec(
    "bearing.p_G_allow",
    "许用支承面压强 p_G",
    "MPa",
    "支承面许用面压强度。钢约 700 MPa，铝合金约 300 MPa。",
    mapping=("bearing", "p_G_allow"),
    default="700",
),
```

材料选择联动逻辑（在 `__init__` 中连接信号）：

```python
BEARING_MATERIAL_PRESETS = {"钢": "700", "铝合金": "300"}

def _on_bearing_material_changed(self, text: str) -> None:
    preset = BEARING_MATERIAL_PRESETS.get(text)
    editor = self._field_widgets.get("bearing.p_G_allow")
    if editor and isinstance(editor, QLineEdit):
        if preset:
            editor.setText(preset)
        else:  # "自定义"
            editor.clear()
            editor.setFocus()
```

当用户选"自定义"后手动输入值，再切回"钢"时，预设值会覆盖用户值（因为预设是确定的标准值）。

### 2.8 结果页更新

CHECK_LABELS 新增：
```python
"bearing_pressure_ok": "支承面压强校核（R7）",
```

R3 和 R7 的 Badge 显示需要在 `_render_result()` 中添加特殊逻辑：

```python
# _render_result() 中的特殊处理伪代码
for key, badge in self._check_badges.items():
    if key == "residual_clamp_ok" and result["calculation_mode"] == "design":
        # 设计模式：R3 数学上满足，显示 PassBadge + 附注
        self._set_badge(badge, "通过（设计模式自动满足）", True)
    elif key == "bearing_pressure_ok" and key not in result["checks"]:
        # R7 未激活：p_G_allow 未设置
        badge.setObjectName("WaitBadge")
        badge.setText("已跳过")
        badge.style().polish(badge)
    else:
        is_pass = result["checks"].get(key, False)
        self._set_badge(badge, "通过" if is_pass else "不通过", is_pass)
```

R3 结果页 Badge 行为（与流程图节点一致）：
- 设计模式：PassBadge + "(设计模式自动满足)"
- 校核模式：正常 PassBadge / FailBadge

---

## 三、主题改动（theme.py）

新增流程图节点选中态样式：

```css
QFrame#SubCard[selected="true"] {
    border: 2px solid #D97757;
    background-color: #FBF3EE;
}
```

复用现有样式：SubCard、PassBadge、FailBadge、WaitBadge、DisabledSubCard。

---

## 四、为将来删除步骤页预留

设计约束：

1. **`R_STEP_FIELDS`** 定义为独立常量（在 bolt_flowchart.py 中），字段到 R 页面的归属映射不硬编码。
2. **`_build_r_input_echo()`** 独立方法构建回显区，将来只需将 QLabel 替换为 QLineEdit + 注册到 `_field_widgets`。
3. **`_build_payload()`** 只依赖 `_field_widgets` 字典，不关心字段在哪个页面。
4. **`_field_widgets` 注册**集中在 `_create_editor()` 中，不依赖步骤页的存在。

---

## 五、改动文件清单

| 文件 | 改动内容 |
|------|---------|
| `core/bolt/calculator.py` | phi_n 硬阻断 + calculation_mode 分支 + R3 标注 + R7 支承面压强 |
| `app/ui/pages/bolt_page.py` | 左侧双 Tab 组装 + 计算模式联动 + 材料联动 + 引入 bolt_flowchart |
| `app/ui/pages/bolt_flowchart.py` | **新建**：FlowchartNavWidget + RStepDetailPage + R_STEPS/R_STEP_FIELDS 常量 |
| `app/ui/theme.py` | 流程图节点选中态样式 |
| `examples/input_case_01.json` | 新增 `bearing.p_G_allow` 字段（可选） |
| `examples/input_case_02.json` | 同上 |
| `examples/output_case_01.json` | 更新输出结构（新增 calculation_mode, r3_note, R7 相关字段） |
| `examples/output_case_02.json` | 同上 |
