# 螺栓模块计算完整性优化计划

## 背景

对 `core/bolt/calculator.py` 与 `app/ui/pages/bolt_page.py` 的全面审查发现：
- **7 个 UI 参数**采集了但未参与计算（A 类）
- **7 处计算逻辑**仅匹配单一假设或使用过度简化模型（B 类）

参数间存在显著耦合关系，不能逐个孤立修复。本计划按**耦合链路**分阶段推进。

---

## 参数耦合关系图

```
joint_type ─┬─→ 扭矩模型 k_bearing（单侧/双侧）─→ MA_min/MA_max → R4 装配应力
            ├─→ R7 支承面压强（单侧/双侧）
            ├─→ 嵌入损失界面数 → embed_loss → FMmin → 全部校核
            └─→ part_count 默认建议

basic_solid ─→ δp 自动建模（锥台/圆柱）─→ phi → phi_n → 全部校核
part_count  ─→ 嵌入界面数 → embed_loss
total_thickness ─→ δp 建模 + 热损失估算

tightening_method ─→ αA 合理范围校验/建议
introduction.position ─→ n 取值建议

材料热膨胀系数 ─→ 热损失 Fth → FMmin → 全部校核
```

核心传递链：**任何影响 FMmin 的改动都会级联影响 FMmax → 扭矩 → R4 → R5 → R3 → R7**。

---

## 阶段划分

### Phase 1：连接形式接入计算（A1 + B2 + B3）

**优先级：P0** — 影响面最广，当前默认螺纹孔连接但计算逻辑完全不区分。

**目标**：`joint_type` 从 UI-only 变为参与计算的核心参数。

**改动范围**：

#### 1.1 UI 层：joint_type 传入 payload
- `bolt_page.py`：`elements.joint_type` 的 `mapping` 从 `None` 改为 `("options", "joint_type")`
- 或在 `_build_payload` 中手动注入到 `options.joint_type`（避免改 section 结构）

#### 1.2 Calculator：读取 joint_type 并分支

**扭矩模型（B2）**：
```python
joint_type = options.get("joint_type", "tapped")  # tapped=螺纹孔, through=通孔

# 通孔连接：头端和螺母端可能有不同 Dkm
# 简化处理：两端使用相同 Dkm（当前已有参数），但扭矩公式需区分
# 螺纹孔连接：只有头端支承面扭矩，螺纹段的摩擦在 k_thread 中已覆盖
# → 实际上 VDI 2230 扭矩公式 MA = F*(k_thread + k_bearing) 对两种连接通用
# → 区别在于 k_bearing 的 Dkm：螺纹孔只有头端，通孔取头端和螺母端的平均
```

实际影响：当前公式 `k_bearing = mu_bearing * Dkm / 2` 用的是单个 Dkm，对两种连接形式在 VDI 2230 简化模型中差异不大（螺纹孔的螺纹端摩擦已被 k_thread 覆盖）。**主要区别在 R7**。

**R7 支承面压强（B3）**：
```python
if joint_type == "through":
    # 通孔连接：需校核两侧（头端 + 螺母端）
    # 当前只有一组 bearing_d_inner/outer → 按同一参数校核两侧（保守）
    # 未来可扩展为 head_d_inner/outer + nut_d_inner/outer
    pass  # 当前逻辑不变，但在报告中注明"两侧均需满足"
else:
    # 螺纹孔连接：只校核头端
    pass  # 当前逻辑不变，报告注明"仅螺栓头端"
```

**输出区分**：在 `r7_note`、`scope_note` 中注明连接形式。

#### 1.3 嵌入损失界面数提示（不自动覆盖用户输入）

螺纹孔连接：嵌入界面数 = part_count + 1（头端）
通孔连接：嵌入界面数 = part_count + 2（头端 + 螺母端）

在 UI 的 `embed_loss` 字段 hint 中动态提示，不强制修改用户值。

#### 1.4 测试

- `test_through_bolt_joint_type_echoed_in_result`
- `test_tapped_joint_r7_note_says_head_side_only`
- `test_through_joint_r7_note_says_both_sides`

**文件改动**：
- `core/bolt/calculator.py`：读取 joint_type，R7 输出加 note
- `app/ui/pages/bolt_page.py`：mapping 改为传入 payload
- `tests/core/bolt/test_calculator.py`：新增测试

---

### Phase 2：嵌入损失经验估算（A3 + B1）

**优先级：P1** — 当前 embed_loss 完全依赖用户手动输入，新手很难估算。

**目标**：根据 VDI 2230 表 5.4/1 提供嵌入损失参考值，用户可选择使用或覆盖。

**前置依赖**：Phase 1（需要 joint_type 确定界面数）

**改动范围**：

#### 2.1 嵌入损失经验公式
VDI 2230 按表面粗糙度和界面数给出参考值：
```
f_Z ≈ 单界面嵌入量（μm） × 界面数
F_Z = f_Z / (δs + δp)

典型单界面嵌入量：
- 轧制表面（Ra ≈ 6.3）: 3~4 μm
- 切削表面（Ra ≈ 3.2）: 2~3 μm
- 磨削表面（Ra ≈ 1.6）: 1~1.5 μm
```

#### 2.2 UI 改动
- 新增 `clamped.surface_roughness` 选择字段（粗/中/精 或 Ra 值）
- `embed_loss` 旁增加「自动估算」按钮或联动，将经验值填入
- 用户仍可手动覆盖

#### 2.3 Calculator 改动
- 新增 `_estimate_embed_loss()` 辅助函数
- 当 `embed_loss` 为 0 或缺省时，自动使用估算值（类似热损失的逻辑）

**文件改动**：
- `core/bolt/calculator.py`：新增估算函数
- `app/ui/pages/bolt_page.py`：新增表面粗糙度字段
- `tests/core/bolt/test_calculator.py`：嵌入损失估算测试

---

### Phase 3：热膨胀材料参数暴露（B6）

**优先级：P1** — 当前硬编码钢的热膨胀系数，铝壳体+钢螺栓的常见工况算出来是错的。

**目标**：允许用户选择材料或输入热膨胀系数。

**前置依赖**：无

**改动范围**：

#### 3.1 UI 新增字段
```python
# 工况数据章节新增
FieldSpec("operating.bolt_material", "螺栓材料", "-",
          "影响热膨胀系数。",
          widget_type="choice",
          options=("钢", "不锈钢", "自定义"), default="钢")
FieldSpec("operating.clamped_material", "被夹件/基体材料", "-",
          "影响热膨胀系数。",
          widget_type="choice",
          options=("钢", "铝合金", "铸铁", "自定义"), default="钢")
FieldSpec("operating.alpha_bolt", "螺栓热膨胀系数", "1/K",
          "自定义模式可手动输入。", default="11.5e-6")
FieldSpec("operating.alpha_parts", "被夹件热膨胀系数", "1/K",
          "自定义模式可手动输入。", default="11.5e-6")
```

#### 3.2 材料预设表
```python
THERMAL_EXPANSION_TABLE = {
    "钢":     11.5e-6,
    "不锈钢": 16.0e-6,
    "铝合金": 23.0e-6,
    "铸铁":   10.5e-6,
}
```

#### 3.3 Calculator 改动
- 移除硬编码 `_ALPHA_STEEL_DEFAULT`
- 从 `operating.alpha_bolt` / `operating.alpha_parts` 读取（已有 fallback 逻辑）

**文件改动**：
- `app/ui/pages/bolt_page.py`：新增材料选择字段 + 联动
- `core/bolt/calculator.py`：移除默认值硬编码
- `tests/core/bolt/test_calculator.py`：铝壳体热损失测试

---

### Phase 4：拧紧方式与载荷导入联动建议（A6 + A7）

**优先级：P2** — 不影响计算正确性，但提升用户体验和防错。

**目标**：拧紧方式联动 αA 范围校验；载荷导入位置联动 n 值建议。

**前置依赖**：无

**改动范围**：

#### 4.1 αA 范围建议
```python
ALPHA_A_RANGES = {
    "扭矩法":     (1.4, 1.8),
    "转角法":     (1.1, 1.3),
    "液压拉伸法": (1.05, 1.15),
    "热装法":     (1.05, 1.15),
}
```
- Calculator：不硬拦截，但在 warnings 中提示超出建议范围
- UI：hint 文本随拧紧方式动态更新

#### 4.2 载荷导入系数 n 建议
```python
N_SUGGESTIONS = {
    "螺栓头端": "n ≈ 1.0（载荷在头端导入）",
    "螺母端":   "n ≈ 0.5~0.7",
    "中间":     "n ≈ 0.3~0.5",
    "分布式":   "n ≈ 0.5（均匀分布近似）",
}
```
- 仅更新 hint 文本，不自动修改 n 值

**文件改动**：
- `core/bolt/calculator.py`：αA 范围 warning
- `app/ui/pages/bolt_page.py`：hint 联动

---

### Phase 5：服役应力精化（B4）

**优先级：P2** — 当前 R5 不含扭转残余，偏非保守。

**目标**：R5 中加入装配残余扭矩对服役阶段的影响。

**前置依赖**：无

**改动范围**：

VDI 2230 在 R5 中考虑：
```
σ_red,B = sqrt(σ_ax_work² + 3·(k_τ·τ_assembly)²)

其中 k_τ 为扭矩残留系数：
- 拧紧后未卸载：k_τ ≈ 0.5（常用简化值）
- 转角法/液压拉伸：k_τ ≈ 0（扭矩基本释放）
```

#### 5.1 Calculator 改动
```python
# k_tau 取决于拧紧方式
k_tau = 0.5 if tightening_method == "torque" else 0.0
sigma_vm_work = sqrt(sigma_ax_work**2 + 3*(k_tau*tau_assembly)**2)
```

#### 5.2 需要 tightening_method 传入 Calculator
- 需 Phase 4 的 A6 改动先完成（或同步进行）

**文件改动**：
- `core/bolt/calculator.py`：R5 公式扩展
- `tests/core/bolt/test_calculator.py`：服役等效应力测试

---

### Phase 6：疲劳模型改进（B5）

**优先级：P2** — 当前 `0.18 * Rp02` 是粗糙估算，与螺纹等级/表面处理无关。

**目标**：引入 VDI 2230 的 σ_ASV 查表或参数化模型。

**前置依赖**：无

**改动范围**：

VDI 2230 疲劳极限 σ_ASV 取决于：
- 螺纹规格（d）
- 表面处理（轧制/切削）
- 强度等级

简化参数化：
```python
# VDI 2230 表 A1 的参数化近似
# σ_ASV ≈ (50 + 0.1·Rp02) / (d^0.1) — 工程近似
# 或直接查表：M8→±45 MPa, M10→±42, M12→±40, M16→±38, M20→±36 ...
```

#### 6.1 UI 新增字段
```python
FieldSpec("fatigue.surface_treatment", "螺纹表面处理", "-",
          "影响疲劳极限 σ_ASV。",
          widget_type="choice",
          options=("轧制", "切削"), default="轧制")
```

#### 6.2 Calculator 改动
- 新增 `_fatigue_limit_ASV(d, rp02, surface)` 查表/插值函数
- 替换 `0.18 * rp02`

**文件改动**：
- `core/bolt/calculator.py`：疲劳极限函数
- `app/ui/pages/bolt_page.py`：新增表面处理字段
- `tests/core/bolt/test_calculator.py`：疲劳极限测试

---

### Phase 7：附加载荷标注修正（B7）

**优先级：P2** — 纯文案/展示问题，不影响计算。

**目标**：将 FA_perm 从"校核项"降级为"参考估算"，UI 明确标注。

**改动范围**：

- `bolt_page.py`：CHECK_LABELS 中 `additional_load_ok` 加 `⚠ 参考值` 标注（当前已有 ⚠）
- `bolt_flowchart.py`：R_STEPS 中对应节点标为非正式校核
- Calculator：输出中加 `"is_reference": True` 标记

**文件改动**：影响面小，可随时穿插执行。

---

### Phase 8：被夹件刚度自动建模（A2）

**优先级：P3** — 改动量最大，涉及全新的几何建模子模块。

**目标**：根据 basic_solid 类型 + 几何参数自动计算 δp，取代手动输入。

**前置依赖**：Phase 1（joint_type 影响压缩体模型）

**改动范围**：

VDI 2230 的锥台压缩体模型：
```
圆柱体：δp = lK / (Ep · Ap)
锥体：  δp 按 VDI 2230 Fig. 5.1 的等效压缩锥公式
        锥角 φ ≈ arctan(Dw/(2·lK)) 的函数
套筒：  δp = lK / (Ep · π/4 · (D_outer² - D_inner²))
混合：  多段串联 δp = Σ δp_i
```

#### 8.1 新增模块
- `core/bolt/compliance_model.py`：纯几何计算，不依赖 Qt
  - `calculate_bolt_compliance(d, p, l_K, E_bolt, ...)`
  - `calculate_clamped_compliance(solid_type, geometry_params, E_clamped, ...)`

#### 8.2 UI 改动
- 被夹紧件章节增加几何参数（通孔直径、外径、弹性模量）
- 顺从度字段改为「自动计算/手动输入」切换
- basic_solid 联动显示对应几何参数子集

#### 8.3 这是最复杂的改动
- 需要全新的计算子模块
- UI 交互逻辑复杂（联动显隐多组字段）
- 建议作为独立特性分支开发

**文件改动**：
- 新建 `core/bolt/compliance_model.py`
- `core/bolt/calculator.py`：集成自动刚度
- `app/ui/pages/bolt_page.py`：大量 UI 改动
- `tests/core/bolt/test_compliance_model.py`：新模块测试

---

## 执行顺序与依赖关系

```
Phase 1 (P0) ──→ Phase 2 (P1) ──→ Phase 8 (P3)
    连接形式        嵌入损失          刚度建模
                      ↑
Phase 3 (P1) ──────┘  （可并行）
    热膨胀材料

Phase 4 (P2) ──→ Phase 5 (P2)
    拧紧方式建议      服役应力精化

Phase 6 (P2)     Phase 7 (P2)
    疲劳改进         附加载荷标注
    （独立）         （独立，随时可做）
```

**推荐执行批次**：
1. **第一批**：Phase 1 + Phase 3（连接形式 + 热膨胀材料，P0+P1，改动量适中）
2. **第二批**：Phase 2 + Phase 7（嵌入损失 + 附加载荷标注，P1+P2）
3. **第三批**：Phase 4 + Phase 5（拧紧方式 + 服役应力，P2，有依赖关系捆绑做）
4. **第四批**：Phase 6（疲劳改进，P2，独立）
5. **第五批**：Phase 8（刚度自动建模，P3，最复杂，单独分支）

---

## 审查问题清单索引

### A 类：UI 采集但未参与计算

| ID | 参数 | 阶段 |
|----|------|------|
| A1 | `elements.joint_type` 连接形式 | Phase 1 |
| A2 | `clamped.basic_solid` 基础实体类型 | Phase 8 |
| A3 | `clamped.part_count` 被夹件数量 | Phase 2 |
| A4 | `bearing.bearing_material` 支承面材料 | 已通过 UI 联动解决，报告回显待补 |
| A5 | `fastener.grade` 强度等级 | 已通过 UI 联动解决，报告回显待补 |
| A6 | `assembly.tightening_method` 拧紧方式 | Phase 4 |
| A7 | `introduction.position` 载荷导入位置 | Phase 4 |

### B 类：计算逻辑单一假设

| ID | 问题 | 阶段 |
|----|------|------|
| B1 | 嵌入损失完全手动 | Phase 2 |
| B2 | 扭矩模型不区分连接形式 | Phase 1 |
| B3 | R7 只校核单侧 | Phase 1 |
| B4 | R5 不含扭转残余 | Phase 5 |
| B5 | 疲劳用 0.18·Rp02 | Phase 6 |
| B6 | 热膨胀硬编码钢 | Phase 3 |
| B7 | FA_perm 展示为正式校核 | Phase 7 |
