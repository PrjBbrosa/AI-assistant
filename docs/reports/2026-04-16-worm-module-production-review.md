# Worm 模块生产级 review 报告

**日期:** 2026-04-16
**审查人:** Claude Code (承接 Codex 调度失败后的主会话)
**目标定位:** 判断蜗杆副模块是否可以用于**实际生产校核**（不是教学/预估算）
**前次 review:** `docs/reports/2026-04-03-hertz-worm-review.md`

---

## 1. 审查目标

评估当前 `core/worm/` + `app/ui/pages/worm_gear_page.py` 是否达到"给蜗杆减速箱签字放行"所需的最低工程可信度。具体关注：

1. 计算结果能否直接作为设计结论使用？数值是否可信？
2. UI 是否诚实地表达模型边界、不误导用户？
3. 测试能否锁住关键公式、发现回归？
4. 与公开标准（DIN 3975 / DIN 3996 / ISO 14521）的差距有多大？

## 2. 审查范围

- `core/worm/calculator.py` (575 行)
- `app/ui/pages/worm_gear_page.py` (1015 行)
- `app/ui/widgets/worm_geometry_overview.py` / `worm_performance_curve.py` / `worm_stress_curve.py`
- `app/ui/report_pdf_worm.py`
- `tests/core/worm/test_calculator.py` / `tests/ui/test_worm_page.py` / `tests/ui/test_worm_stress_curve.py`
- `examples/worm_case_01.json` / `worm_case_02.json`

## 3. 审查方法

### 3.1 静态审查

逐段对照 DIN 3975 几何公式、力系平衡、Hertz 线接触、Lewis 弯曲应力，识别公式偏差、单位链、常数硬编码、输入验证、警告传递、UI 映射。

### 3.2 动态验证

1. 跑完整测试：

   ```
   QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/core/worm/ \
       tests/ui/test_worm_page.py tests/ui/test_worm_stress_curve.py -q
   → 69 passed, 615 warnings in 1.36s
   ```

2. 用 `worm_case_01.json` 跑计算并手算对照力分解；对 q=13 非标准值、ripple=150%、method dropdown、handedness 等做针对性复现。

---

## 4. 问题清单

| ID | 区域 | 严重度 | 问题摘要 | 位置 |
|----|------|--------|----------|------|
| **W26-01** | 核心计算 | **严重 / 高** | 力分解使用 `sin(γ)` 代替 `cos(γ)`，Fn 高估 `cot(γ)` 倍（γ=11°时 5×），σH 高估 `√cot(γ)`（2.24×） | `core/worm/calculator.py:363-371` |
| **W26-02** | 核心计算 | **严重 / 高** | `axial_force_wheel = Ft_wheel/tan(γ)` 公式错误，正确应为 `Ft_wheel·tan(γ+φ)`；γ=11° 时高估 **12.7×** | `core/worm/calculator.py:370` |
| **W26-03** | 核心计算 | **严重 / 高** | `radial_force_wheel = Ft·tan(α)/sin(γ)` 错误，正确应为 `Ft·tan(α)/cos(γ)`；γ=11° 高估 5× | `core/worm/calculator.py:366, 371` |
| W26-04 | UI / 业务 | 高 | Method A / B / C 下拉对计算**没有任何影响**（三者输出完全相同），assumption 承认"仅作标记" | `core/worm/calculator.py:488-502`, `worm_gear_page.py:41-45` |
| W26-05 | UI 语义 | 高 | `geometry_consistent` 把"q 不在推荐序列"这种**非标注警告**归为"不一致"，q=13 直接触发"总体不通过" | `core/worm/calculator.py:185-186, 559-562` |
| W26-06 | 核心计算 | 高 | 齿根应力采用经验矩形截面悬臂梁（`s=1.25m` 固定，`h=2.2m` 作力臂），非 Lewis/ISO 6336，对 PA66 案例报 σF=254 MPa 明显不合理 | `core/worm/calculator.py:383, 390-393` |
| W26-07 | 核心计算 | 高 | `design_force_factor = K_A·K_v·K_Hα·K_Hβ` **同时**用于齿面和齿根应力；DIN 标准要求齿根独立的 K_Fα/K_Fβ | `core/worm/calculator.py:349, 373-378` |
| W26-08 | UI 数据 | 中 | 塑料蜗轮材料库仅含 `PA66 / PA66+GF30` 两项；**POM、PEEK、PA46、PA66+MoS2、PA66+CF 等常见工程塑料缺失**；许用应力未注明环境温度/湿度来源 | `core/worm/calculator.py:41-55`, `worm_gear_page.py:127-138` |
| W26-09 | UI / 数据 | 中 | `handedness`、`lubrication` 写入 payload 但 calculator 不读取，属于**死输入**，用户修改无任何效果 | `worm_gear_page.py:97-105, 150-158` |
| W26-10 | UI 欺骗 | 中 | 性能曲线第 2、3 条（"损失功率"与"损失功率 (热负荷)"）值完全相同，无物理区分；UI 让用户误以为这是两个独立指标 | `core/worm/calculator.py:173-176, 214-218`, `worm_performance_curve.py:69-72` |
| W26-11 | UI 占位 | 中 | 应力曲线使用"三角齿廓"构造一周 360 点，不对应任何真实蜗杆型式 (ZA/ZI/ZN/ZK)，易被误读为疲劳脉动谱 | `core/worm/calculator.py:409-475`, `worm_stress_curve.py:64-97` |
| W26-12 | UI 占位 | 中 | 几何总览仍是纯占位图（仅接收 title/note 字符串，固定画"右旋示意"），2026-04-03 review 要求的联动未实施 | `worm_geometry_overview.py:14-145`, `worm_gear_page.py:860-863` |
| W26-13 | 核心计算 | 中 | 扭矩波动 RMS 公式 `T·√(1+0.5r²)` 是假设正弦脉动的一阶近似；`ripple ≥ 100%` 时 `output_torque_min_nm` 静默钳位 0，未给警告 | `core/worm/calculator.py:353-356` |
| W26-14 | 核心计算 | 中 | `equivalent_radius = 1/((2/d1)+(2/d2))` 把蜗轮也当作凸圆柱，未考虑蜗轮齿面**凹面**带来的曲率放大；DIN 3996 采用带 Y_ε 包角修正的曲率 | `core/worm/calculator.py:382` |
| W26-15 | 核心计算 | 中 | `contact_length_mm = min(b1, b2)` 取整齿宽，未考虑蜗轮包角 (2β) 下只有 2–3 齿啮合，实际接触线长度偏大 | `core/worm/calculator.py:381` |
| W26-16 | UI / 体验 | 中 | `_refresh_derived_geometry_preview()` 每次键入都跑完整 `calculate_worm_geometry`（含 360 点应力曲线），LC 启用时有明显卡顿 | `worm_gear_page.py:743-753` |
| W26-17 | UI / 按钮 | 低 | 参数变更后"导出报告"按钮**仍可用**，可能导出与当前输入不一致的旧结果；与 tapped_axial 模块规范不一致 | `worm_gear_page.py:917-942` |
| W26-18 | UI / 导出 | 低 | `_export_report` 的 PDF 分支用 `except Exception` 静默回退为 txt，用户不知为何没拿到 PDF | `worm_gear_page.py:931-939` |
| W26-19 | 测试 | 中 | 缺少力分解数值基准测试；`test_load_capacity_outputs_forces_and_design_force` 只校验 `>0`，不会捕获 W26-01..03 这种量级错误 | `tests/core/worm/test_calculator.py:203-213` |
| W26-20 | 测试 | 低 | 无与公开标准参考例（如 Niemann 书 §24、DIN 3975-2 算例）对照的基准测试；69 个 pass 均来自内部一致性 | `tests/core/worm/` |
| W26-21 | 核心计算 | 低 | 输入允许 `ripple_percent > 100%` 而无错误或警告（除 min 被钳位到 0 外没有保护） | `core/worm/calculator.py:98-102` |
| W26-22 | 文档 | 低 | CLAUDE.md 写"DIN 3996 负载能力校核未实现"，但代码里已给出 σHm、σF 并打 PASS/FAIL 徽章，描述与实际行为脱节 | `CLAUDE.md:71` |

---

## 5. 详细发现

### 5.1 W26-01 / 02 / 03 — 力分解公式系统性错误

**严重度：严重**

#### 现象

`core/worm/calculator.py:363-371`：

```python
sin_gamma = max(math.sin(lead_angle_calc_rad), 1e-6)
cos_alpha_n = max(math.cos(normal_pressure_angle_rad), 1e-6)
tan_gamma = max(math.tan(lead_angle_calc_rad), 1e-6)
radial_factor = math.tan(normal_pressure_angle_rad) / sin_gamma
normal_force_n  = tangential_force_wheel_n / (cos_alpha_n * sin_gamma)   # ←应为 cos_gamma
axial_force_wheel_n  = tangential_force_wheel_n / tan_gamma              # ←方向完全错
radial_force_wheel_n = tangential_force_wheel_n * radial_factor          # ←应除 cos_gamma
```

#### 正确的蜗杆力系（教材/Niemann §24 / Dudley's Handbook）

蜗杆轴线与蜗轮轴线正交；分度圆啮合点处的几何对应关系：

- 蜗杆切向方向 ≡ 蜗轮轴向方向  → `F_t1 = F_a2`
- 蜗杆轴向方向 ≡ 蜗轮切向方向  → `F_a1 = F_t2`
- 径向方向通用

理想无摩擦时，齿面法向力 `F_n` 的投影：

- `F_t1 = F_n · cos(α_n) · sin(γ)`
- `F_a1 = F_n · cos(α_n) · cos(γ)`   ← 注意：与轴向对应的是 **cos(γ)**
- `F_r  = F_n · sin(α_n)`

因此：

- `F_t2 = F_a1 = F_n · cos(α_n) · cos(γ)`  ⇒  **`F_n = F_t2 / (cos(α_n) · cos(γ))`**
- `F_a2 = F_t1 = F_t2 · tan(γ+φ)` （含摩擦，理想 φ=0 时化为 `F_t2·tan(γ)`）
- `F_r  = F_t2 · sin(α_n) / (cos(α_n) · cos(γ)) = F_t2 · tan(α_n) / cos(γ)`

#### 数值对比（使用 `worm_case_01.json`：γ=11.31°，T1=19.76 Nm，T2=200.5 Nm）

| 量 | 正确值 | 代码输出 | 倍数 |
|----|--------|----------|------|
| `F_n` | 2720 N | **13600 N** | **× 5.00 = cot(γ)** |
| `F_a2` | 988 N (=F_t1) | **12532 N** | **× 12.68 ≈ cot²(γ)** |
| `F_r`  | 930 N | **4651 N** | **× 5.00 = cot(γ)** |
| `σ_Hm_peak`(∝√F_n) | ~78 MPa | **174.7 MPa** | **× 2.24 = √cot(γ)** |

误差随 γ 减小而放大：γ=5° 时 cot=11.4，√cot=3.4；γ=2° 时 cot=28.6，√cot=5.4。**越低导程角（常见的自锁/低速工况），错得越厉害。**

#### 影响

- 所有含力的输出均不可信：`forces`、`contact.sigma_hm_*`、`root.sigma_f_*`、`safety_factor_*`、`stress_curve`。
- 即使当前示例 case_01 报 `SH_peak=0.24` / `SF_peak=0.20` 看似"不通过"，也是错因叠加（力错 + 截面模型错），**无法作为工程判断依据**。
- PDF 报告、应力曲线、齿面/齿根徽章全都传播该错误。

#### 复现

```python
from core.worm.calculator import calculate_worm_geometry
import json
r = calculate_worm_geometry(json.load(open("examples/worm_case_01.json")))
print(r["load_capacity"]["forces"]["normal_force_n"])      # 13600.4
print(r["load_capacity"]["forces"]["axial_force_wheel_n"]) # 12532.0
```

#### 建议修复

把三处公式改为：

```python
cos_gamma = max(math.cos(lead_angle_calc_rad), 1e-6)
normal_force_n       = tangential_force_wheel_n / (cos_alpha_n * cos_gamma)
axial_force_wheel_n  = tangential_force_wheel_n * math.tan(lead_angle_calc_rad + math.atan(friction_mu))
radial_force_wheel_n = tangential_force_wheel_n * math.tan(normal_pressure_angle_rad) / cos_gamma
```

并在测试中加入**数值基准**（见 §8）：γ=11.31° 时 F_n 应 ≈ 2720 N、F_a2 应 ≈ 988 N，量级级别锁死。

---

### 5.2 W26-04 — Method A / B / C 下拉完全是装饰

**严重度：高**

#### 现象

UI 下拉 (`worm_gear_page.py:41-45`)：

```python
LOAD_CAPACITY_OPTIONS = (
    "DIN 3996 Method A -- 基于实验/FEM，精度最高",
    "DIN 3996 Method B -- 标准解析计算（推荐）",
    "DIN 3996 Method C -- 简化估算",
)
```

calculator 只把 method 字符串原样传回：

```python
method = str(load_capacity.get("method", "DIN 3996 Method B"))
# ...
"status": f"{method} 最小子集校核通过…"
```

实测同一输入下 A / B / C 输出的 `sigma_hm_peak_mpa` 完全相同（174.688）。

#### 影响

对生产使用者这是**严重误导**：用户选 Method A 以为得到"FEM 级精度结果"，实际只是换了一个字符串。assumption 里确实写了"仅作标记"，但默认读者不会翻到 assumptions 就相信选项描述。

#### 建议修复

三选一：

1. 删除下拉，只保留一个"Method B 最小子集"说明；
2. 保留下拉但把文案改成"方案标注（不影响计算）"；
3. 真的落地 DIN 3996 Method B 的 ZM / ZE / ZH / ZV / ZS 五大因子（这是真正做生产校核的方向，参考 §6 生产可用性评估）。

---

### 5.3 W26-05 — `geometry_consistent` 把"非标准 q"当作"不一致"

**严重度：高**

#### 现象

`core/worm/calculator.py:185-186`：

```python
if diameter_factor_q not in STANDARD_Q_VALUES:
    geometry_warnings.append(...)
```

`checks["geometry_consistent"] = not geometry_warnings`，总体徽章 (`worm_gear_page.py:897-898`) 会因此给出"总体不通过"。

#### 复现

q=13（DIN 3975-2 推荐序列内的"次优"值，但在工程实践中常用以得到合适的中心距）：

```
geom consistent warnings = ['直径系数 q=13.0 不在 DIN 标准推荐序列内。']
checks = {'geometry_consistent': False, 'contact_ok': False, 'root_ok': False}
```

UI 徽章：几何一致性 = 不通过。

#### 影响

"标准推荐性"和"几何自洽性"被混为一谈。几何自洽 = `d1=q·m` / `a=m(q+z2)/2` / `γ=atan(z1/q)` 这类代数关系成立；q 是否在推荐序列是**工艺/成本偏好**，不是自洽性问题。把它当作"不通过"会逼迫用户选次优的 q 值。

#### 建议修复

- 把 q 非标准降为**提示** (info)，保留在 warnings 列表，但**不**污染 `geometry_consistent`。
- `geometry_consistent` 仅在 `lead_angle_delta > 0.5°` 或 `center_distance_delta > max(0.25m, 0.5)` 时为 False。

---

### 5.4 W26-06 / 07 — 齿根应力模型严重简化且使用错误的 K 因子

**严重度：高**

#### 现象

```python
# calculator.py:383, 390-393
tooth_root_thickness_mm = max(1.25 * module_mm, 1e-6)  # 固定 s=1.25m
def _root_stress(tangential_force_value_n):
    section_modulus_mm3 = contact_length_mm * tooth_root_thickness_mm**2 / 6.0
    bending_moment_nmm = tangential_force_value_n * tooth_height_mm   # h=2.2m
    return bending_moment_nmm / section_modulus_mm3
```

且设计力使用了**齿面系数集**：

```python
design_force_factor = K_A · K_v · K_Hα · K_Hβ     # 只适用于齿面接触
design_tangential_force_n = tangential_force_wheel_n * design_force_factor
sigma_f = design_tangential_force_n * h / W       # 齿根应力也用齿面系数集
```

#### 标准做法

Lewis / ISO 6336 / DIN 3996 齿根弯曲：

```
σ_F = (F_t / (b · m)) · Y_F · Y_S · Y_ε · Y_β · (K_A · K_v · K_Fα · K_Fβ)
```

- `Y_F`：形状因子，与 z、x、α、m_x 相关，通常 2.2–3.5；
- `Y_S`：应力修正（齿根圆角）；
- `Y_ε`：重合度修正；
- **K_Fα、K_Fβ ≠ K_Hα、K_Hβ**（齿面/齿根的载荷分布不同）。

#### 数值对比

case_01 (Ft2_design=2753 N / b=28 / s=5 / h=8.8)：

- 代码：`σF = 6·2753·8.8/(28·25) = 207 MPa`（测试显示 σF=254 MPa，含 peak ripple 放大）
- 若用 Lewis 近似（Y=0.35）：`σF = F_t/(b·m·Y) = 2753/(28·4·0.35) = 70 MPa`
- 比值 ≈ 3×

PA66 许用 σ_FP=55 MPa，代码给出 SF≈0.2，Lewis 给出 SF≈0.8。**两种模型得到的工程结论完全不同**，且代码的模型偏差足以让一切**都**通不过校核。

#### 影响

对塑料蜗轮（最可能用这个工具的场景），当前 σ_F 输出**系统性过大约 3 倍**，会迫使用户把工况/扭矩降到实际不需要的保守值。

#### 建议修复

- 短期：把 h 改为 `≈ m·(1.0+x2)`（Lewis 切点高度），s 改为 `≈ 1.5m·cos(γ)`；或直接调用已有的 `core.spline.calculator` 的 Lewis 风格齿根模型保持一致。
- 中期：引入 YF / YS 查表（按 z2_equiv = z2/cos³(γ)）；
- 长期：接入 DIN 3996 根弯曲模块并单独暴露 K_Fα / K_Fβ 输入。

---

### 5.5 W26-08 — 塑料蜗轮材料库覆盖不全 + 环境依赖未体现

**严重度：中（产品定位为钢-塑料蜗轮副）**

#### 现象

```python
MATERIAL_ELASTIC_HINTS = {"37CrS4":..., "PA66":..., "PA66+GF30":...}
MATERIAL_ALLOWABLE_HINTS = {"PA66": {"contact_mpa":42, "root_mpa":55},
                            "PA66+GF30": {"contact_mpa":58, "root_mpa":70}}
MATERIAL_FRICTION_HINTS = {("37CrS4","PA66"):0.18, ("37CrS4","PA66+GF30"):0.22}
```

UI 下拉只有 `PA66`、`PA66+GF30` 两种蜗轮材料。许用应力硬编码，无来源注释、无温度/湿度依赖。

#### 影响（在钢-塑料蜗轮副的定位内）

1. **材料覆盖不足**：塑料蜗轮常见的 `POM`、`PA46`、`PA66+MoS2`（自润滑）、`PA66+CF`（碳纤增强）、`PEEK` 等均未覆盖；用户选择受限。
2. **环境依赖不显式**：PA66 吸水后刚度下降 30-50%、许用应力下降 20-40%；代码中的 42/55 MPa 是"常温干态"经验值（assumption 里有一句"常温干态"，但 UI 上完全看不到）。生产用户未注意到这一点，就会按"干态值"设计然后在潮湿环境下出故障。
3. **摩擦系数来源不明**：0.18 / 0.22 这两个值没有引用文献，且塑料蜗轮 μ 强烈依赖 PV 值（接触压力 × 滑动速度），固定值只是粗估。
4. **GF30 vs 纯 PA66 应力上移 40% (42→58 MPa) 是否合理**：实际测试中玻纤增强会大幅提高接触应力许用值，但同时让齿根弯曲**更脆**，疲劳性能下降；代码把 GF30 的 root_mpa 从 55 拉到 70 与公开文献趋势相反（文献中 GF30 的断裂应变下降、疲劳极限通常低于纯料）。**这条数据存疑**。

#### 建议修复

优先级：
- **P1**：给 `MATERIAL_ALLOWABLE_HINTS` 的每条数据加引用/出处注释；UI 在许用应力字段 hint 中注明"常温干态，湿态请自行折减"；核对 GF30 的 root_mpa 数据来源。
- **P2**：扩充到至少以下塑料蜗轮材料（并标注温度上限）：

| 蜗轮材料 | 温度上限 | μ (对 37CrS4) | σ_HP (MPa, 干) | σ_FP (MPa, 干) |
|----------|----------|--------------|----------------|----------------|
| PA66 (纯) | 100 °C | 0.18 | 42 | 55 |
| PA66+GF30 | 120 °C | 0.22 | 58 | 待核 (可能 ≤55) |
| PA66+MoS2 | 100 °C | 0.12 (自润滑) | 40 | 50 |
| POM (Delrin) | 90 °C | 0.15 | 50 | 70 |
| PA46 | 150 °C | 0.20 | 55 | 65 |
| PEEK | 200 °C | 0.25 | 80 | 120 |

- **P3**：引入湿度折减系数 f_humid（干 = 1.0，湿 ≤ 0.7）、温度折减 f_temp（使用温度/温度上限 < 0.5 ⇒ 1.0；> 0.8 ⇒ 0.7），作为 advanced 输入。

---

### 5.6 W26-09 — `handedness` / `lubrication` 是死字段

**严重度：中**

#### 现象

`_build_payload` 把 `geometry.handedness` 和 `operating.lubrication` 写入 payload，calculator 只在保留 `inputs_echo` 时回传，**不参与任何计算**。

实测：左旋 vs 右旋、油浴 vs 强制润滑，结果完全相同。

#### 影响

- 用户感觉这些字段"被考虑进去了"，实际上没有。
- 对旋转方向实际上影响的是：轴向力方向、自锁判定、推力轴承选型——**完整工程校核需要用到 handedness**；当前模块至少应在结果中提示"旋向仅用于记录，未进入力方向判定"。
- 润滑方式影响 μ 估算和热容量——**应至少驱动默认摩擦系数或热平衡**。

#### 建议修复

- 立即：在字段 hint 中显式写"仅用于记录，不进入计算"；
- 中期：让 `lubrication` 驱动默认 μ（油浴 × 0.04–0.07，飞溅 × 0.07–0.12），让 `handedness` 驱动 F_a 符号和推力轴承选型建议。

---

### 5.7 W26-10 — 两条性能曲线完全相同

**严重度：中**

#### 现象

`calculator.py:174-176`:

```python
power_loss_kw = power_kw - output_power_kw
thermal_capacity_kw = power_loss_kw       # 等号赋值
```

UI `worm_performance_curve.py:69-72` 画三张图：`efficiency` / `power_loss_kw` / `thermal_capacity_kw (热负荷)`。第二和第三张图数据**完全相等**。测试验证：`thermal_capacity_kw == power_loss_kw`。

#### 影响

- 用户以为"损失功率"和"热负荷"是两个独立指标——实际没有任何区别；
- `thermal_capacity_kw` 字面上是"箱体允许散热功率"，但实际算的是"发热功率 = 损失功率"。**概念混淆**。

#### 建议修复

- 要么删掉第三张图；
- 要么真的算热容量（箱体表面积 × 传热系数 × ΔT_油温），才叫"热容量"。

---

### 5.8 W26-11 — 应力曲线的物理含义站不住

**严重度：中**

#### 现象

`calculator.py:422-460` 的"一周 360° × 360 点应力曲线"基于：

```python
phase = (theta % (360/z1)) / (360/z1)
r1 = r_root + (r_tip - r_root) * (1 - |2·phase-1|)   # 三角形齿廓
rho1 = r1 · sin(γ)
rho2 = a - r1
rho_eq = rho1·rho2/(rho2-rho1)                        # 凸-凹等效曲率
sigma_h(theta) = sqrt(F_n·E*/(π·L·rho_eq))
```

这构造出一个"三角齿廓"应力脉动波形——但：

1. 真实蜗杆型号 ZA / ZI / ZN / ZK 齿廓各不相同，没有一个是三角形；
2. 蜗轮一颗齿在啮合窗口内只参与 2-3 个位置，不会在蜗杆一周内产生 z1 个完整峰；
3. 用户看到这条曲线很容易拿去估算"疲劳循环次数"——这是**严重错误**。

#### 测试行为

`tests/core/worm/test_calculator.py:539-549` 确实检查"一周内应有 z1 个峰"——但这只锁住了**人为构造的三角波形**本身，并不证明物理正确。

#### 建议修复

- 标题改为"示意：一转内啮合几何周期估算"（当前叫"一个蜗杆旋转周期内啮合应力变化"会让用户当真）；
- 在 UI 图下方加显著说明"非真实载荷谱，不可用于疲劳评估"；
- 长期：若要真实用于疲劳评估，需导入 DIN 3996 的 YS_eff 有效应力集中因子、蜗轮一齿一次啮合的弯矩时序。

---

### 5.9 W26-12 — 几何总览 widget 仍未接入真实数据

**严重度：中**

#### 现象

`worm_geometry_overview.py:14-145` 仍只有 `set_display_state(title, note)` 接口；`_calculate()` 里：

```python
self.geometry_overview.set_display_state(
    "几何总览",
    f"i={geometry['ratio']:.2f}，a={geometry['center_distance_mm']:.1f} mm，gamma={geometry['lead_angle_deg']:.1f} deg",
)
```

只传了文字摘要，widget 内部绘制的矩形/圆/"右旋示意"完全写死。

2026-04-03 review W-04 已指出此问题，至今**未修**。

#### 影响

图形不能作为工程复核工具，只是装饰。左旋输入仍画右旋、变位对齿顶齿根圆的影响不可视化、中心距变化不联动。

#### 建议修复

- 最小改动：`set_display_state(title, note, *, d1=None, d2=None, a=None, gamma_deg=None, handedness=None)`；按实际尺寸比例绘制蜗杆矩形和蜗轮圆。
- 进一步：画 DIN 3975 标准的蜗杆副剖面（齿顶/齿根圆、分度圆、齿根角）。

---

### 5.10 W26-13 — 扭矩波动 RMS 是假设正弦的玩具公式 + min 钳位

**严重度：中**

#### 现象

```python
output_torque_rms_nm = output_torque_nm * math.sqrt(1.0 + 0.5 * ripple_ratio**2)
output_torque_min_nm = max(0.0, output_torque_nm * (1.0 - ripple_ratio))
```

- RMS 公式等价于"扭矩 = T_nom·(1 + r·sin(ωt))"的 RMS，系数 0.5 来自 `<sin²>=0.5`；
- 对电机 PWM 脉动、冲击载荷、启动/堵转根本不适用；
- ripple > 100% 时 min_nm 被静默钳位 0，RMS 公式仍当正弦算，没有警告。

实测 ripple=150%：min=0, peak=501.3, rms=292.3（基于 T2_nom=200.5）——数值"看起来合理"，但物理意义已崩溃。

#### 建议修复

- 输入 ripple > 80% 时抛警告"脉动已超正弦假设有效范围"；
- 在 assumptions 中写明"RMS 仅对正弦扭矩脉动有效"。

---

### 5.11 W26-14 / 15 — Hertz 等效半径与接触长度过于简化

**严重度：中**

- `rho_eq = 1/((2/d1)+(2/d2))`：把蜗轮当凸圆柱，忽略**凹面（蜗轮是用蜗杆展成的，齿面是凹的）**；DIN 3996 的 ρ_red 用 (d_m1/2)·sin(γ_m)·(1 + ρ_2/ρ_1)^-1 带包角修正。
- `L_c = min(b1, b2)`：全齿宽；蜗轮只有 2β_max ≈ 60° 包角、实际只有 2–3 齿啮合，有效接触线长度 l_bm 通常是 0.6–0.8 · b2。

两者都让 σ_H 偏**乐观**（反过来部分抵消 W26-01 的高估），但 "正负相抵"不是工程上可接受的稳态，实际结果依赖 γ 具体值。

#### 建议修复

中短期内加 assumption 说明；长期补 DIN 3996 Method B 的完整 ZM/ZH/ZE/Zε 因子。

---

### 5.12 W26-16 — 实时预览性能

**严重度：中**

#### 现象

`_refresh_derived_geometry_preview` 在每次 `textChanged` / `currentTextChanged` 时跑 `calculate_worm_geometry`，**包含 LC 启用时的 360 点应力曲线 + 25 点性能曲线**。

#### 影响

键入中心距时可感知的 UI 卡顿（用户每按一键，跑一次 9 次三角函数 · 360 循环）。

#### 建议修复

- 拆出 `calculate_worm_preview_geometry()` 只返回 `geometry` 段；
- 或给预览加 50ms 防抖 `QTimer.singleShot(50, ...)`。

---

### 5.13 W26-17 / 18 — 导出按钮状态与静默回退

**严重度：低**

- 参数变更后"导出报告"仍可点，会导出**旧结果**；tapped_axial 模块的规范是"任何输入变化即禁用导出直到重算"——应保持一致。
- `_export_report` 用 `except Exception` 吞掉 reportlab 错误，静默写 txt，用户完全不知道为何想要的 PDF 变成 txt。

#### 建议修复

```python
# 监听所有输入变化，禁用 btn_save
def _on_any_input_changed(self):
    self.btn_save.setEnabled(False)
# 在 _calculate 成功后启用
self.btn_save.setEnabled(True)
```

PDF 失败时应至少 `logging.exception(...)` 并 QMessageBox 告知"PDF 生成失败，已回退 txt"。

---

### 5.14 W26-19 / 20 — 测试锁得太浅

**严重度：中**

`tests/core/worm/test_calculator.py:203-213`：

```python
def test_load_capacity_outputs_forces_and_design_force(self):
    forces = result["load_capacity"]["forces"]
    self.assertGreater(forces["tangential_force_wheel_n"], 0.0)
    self.assertGreater(forces["axial_force_wheel_n"], 0.0)   # 12532 ≫ 988，依然 >0
    self.assertGreater(forces["radial_force_wheel_n"], 0.0)
    self.assertGreater(forces["normal_force_n"], 0.0)
```

所有力只校验 `>0`，完全抓不住 5×–13× 量级的公式错误。W26-01..03 的严重 bug 能被 69 个"全绿"测试掩盖，就是这个原因。

#### 建议测试补充

```python
def test_wheel_axial_force_equals_worm_tangential(self):
    """F_a2 = F_t1 = 2*T1/d1"""
    payload = self._base_payload()   # T1=19.76, d1=40
    r = calculate_worm_geometry(payload)
    Fa2 = r["load_capacity"]["forces"]["axial_force_wheel_n"]
    self.assertAlmostEqual(Fa2, 2*19.76*1000/40, delta=50)   # 988 N

def test_normal_force_from_wheel_tangential(self):
    """F_n = F_t2 / (cos α_n · cos γ_m)"""
    payload = self._base_payload()
    r = calculate_worm_geometry(payload)
    Ft2 = r["load_capacity"]["forces"]["tangential_force_wheel_n"]
    gamma = math.atan(2/10)
    expect = Ft2 / (math.cos(math.radians(20)) * math.cos(gamma))
    self.assertAlmostEqual(r["load_capacity"]["forces"]["normal_force_n"], expect, delta=expect*0.02)
```

---

## 6. 生产可用性总评

### 6.1 与标准的差距

| 维度 | 当前实现 | 生产校核最低要求 | 差距 |
|------|----------|-----------------|------|
| DIN 3975 几何 | 基本正确（d1/d2/a/γ/变位） | ✓ | **小** |
| 力分解 | **公式错误** (W26-01..03) | 正确的 F_n / F_a / F_r | **严重** |
| DIN 3996 齿面接触 | 线接触 Hertz 简版 | 含 Z_M / Z_H / Z_E / Z_v / Z_s 等 5+ 因子 | 大 |
| DIN 3996 齿根弯曲 | 矩形梁，K_Fα=K_Hα | Lewis / ISO 6336 + K_Fα/K_Fβ | 大 |
| 胶合、磨损寿命 | 未实现 | DIN 3996 Method B (4 种失效模式) | 完全缺失 |
| 材料库 (钢-塑料定位内) | 1 钢 × 2 塑料 (PA66/GF30) | 再补 POM / PA46 / PEEK + 湿度/温度折减 | 中 |
| 包角 / 重合度 | 未考虑 | 需计算 ε_β、z2_eff | 缺失 |
| 热平衡 | 直接 = 损失 | Q_gen vs Q_rej(A·h·ΔT) | 缺失 |
| 推力轴承选型 | 无 | F_a1 / F_a2 驱动轴承推力等级 | 缺失 |

### 6.2 分级结论

**✅ 目前适合用作：**
- **几何初算**（d1 / d2 / a_th / γ / 变位对齿顶齿根影响）——公式正确，可信；
- **方案对比**（输入不同 q、m、z1/z2 看几何与效率变化）——**前提**是用户只关注几何和相对效率，不看齿面/齿根应力数字。

**⚠️ 勉强用作（需人工复核）：**
- **效率估算**：公式正确，摩擦系数查表范围合理；但仅适用于 37CrS4+PA66 配对，其他材料组合的 μ 是 fallback 0.20，粗估可以，定量不行。
- **扭矩波动与 RMS**：仅在正弦脉动假设下可信。

**❌ 绝对不可用作：**
- **齿面接触应力 σ_H 的数值结论** —— 受 W26-01 影响，整体高估 2.2×。
- **齿根弯曲应力 σ_F 的数值结论** —— 受 W26-06 + W26-07 影响，整体高估 ~3×。
- **安全系数 SH / SF 签字放行** —— 不能作为设计结论。
- **应力曲线导出的疲劳循环判断** —— 曲线物理含义错误 (W26-11)。
- **脉动载荷、非正弦扭矩的疲劳校核** —— RMS 公式不适用。
- **湿态 / 高温工况下的 PA66 蜗轮** —— 当前许用应力未做环境折减。
- **齿胶合、磨损寿命评估** —— 模块未实现这两个 DIN 3996 必检失效模式。

### 6.3 与 2026-04-03 Review 的修复对照

| 旧 ID | 2026-04-03 描述 | 当前状态 |
|-------|------------------|---------|
| W-01 | 效率硬钳位 0.30 | ✅ 已修，改为上限 0.98 + 低效率 warning |
| W-02 | 总体通过忽略几何一致 | ✅ 已修，`overall_lc_ok` 含 `geometry_consistent`（副作用见 W26-05） |
| W-03 | LC 关闭显示 0.000 | ✅ 已修，UI 显示"未启用" |
| W-04 | 几何总览占位图 | ❌ **未修**（参见 W26-12） |
| W-05 | d2 文案脱节 | ✅ 已修，hint 改为 "由 d2 = z2 × m" |

W-04 至今未动，新发现 W26-01..03 的力系 bug 则是前次 review 漏掉的更严重问题。

---

## 7. 优先级修复建议

### P0（立即修，否则报告数字不可信）

1. **W26-01 / 02 / 03** — 力分解使用 cos(γ) 而非 sin(γ)，F_a2 用 `tan(γ+φ)`。
2. **W26-19** — 给力分解增加数值基准测试（锁死 F_n ≈ 2720、F_a2 ≈ 988 N）。
3. **W26-05** — q 非标准不再污染 `geometry_consistent`。

### P1（中期，提升真实性）

4. **W26-06 / 07** — 引入 Lewis Y_F 或 ISO 6336 YF/YS；分离齿根 K_Fα / K_Fβ 输入。
5. **W26-08** — 核对 PA66+GF30 的 root_mpa=70 数据来源；给 UI 许用应力字段加"常温干态"注释；后续扩充 POM / PA46 / PEEK。
6. **W26-04** — Method A/B/C 下拉：删除或落地真实区分；短期至少改文案。
7. **W26-10 / 11** — 性能曲线删掉重复的"热负荷"；应力曲线加"非真实载荷谱"警示。
8. **W26-12** — 几何总览接入真实 d1/d2/a/γ/handedness。
9. **W26-17 / 18** — 导出按钮变更时禁用 + PDF 失败显式提示。

### P2（长期，补齐 DIN 3996）

10. 落地 DIN 3996 Method B 的 Z_M / Z_H / Z_E / Z_v / Z_s 五大接触因子。
11. 实现胶合 (scuffing) 与磨损寿命 (wear) 两种失效模式。
12. 增加 ρ_red 包角修正、有效接触线长度 l_bm、热平衡 Q_gen vs Q_rej。
13. 与 Niemann §24 或 DIN 3975-2 Annex A 算例做基准对照测试。
14. `lubrication` 驱动默认 μ，`handedness` 驱动 F_a 符号与轴承选型建议。

---

## 8. 建议补充的测试用例

### 核心计算

```python
def test_wheel_axial_equals_worm_tangential(self):
    """F_a2 = F_t1 = 2*T1/d1 = 988 N"""
    r = calculate_worm_geometry(self._base_payload())
    Fa2 = r["load_capacity"]["forces"]["axial_force_wheel_n"]
    self.assertAlmostEqual(Fa2, 988.0, delta=20)

def test_normal_force_uses_cos_gamma(self):
    """F_n = F_t2 / (cos α_n · cos γ) ≈ 2720 N"""
    r = calculate_worm_geometry(self._base_payload())
    self.assertAlmostEqual(
        r["load_capacity"]["forces"]["normal_force_n"], 2720, delta=80)

def test_radial_force_uses_cos_gamma(self):
    r = calculate_worm_geometry(self._base_payload())
    self.assertAlmostEqual(
        r["load_capacity"]["forces"]["radial_force_wheel_n"], 930, delta=30)

def test_non_standard_q_warns_but_not_inconsistent(self):
    payload = self._base_payload(); payload["geometry"]["diameter_factor_q"] = 13.0
    # 重新计算配套 center_distance/lead_angle 保持自洽
    payload["geometry"]["center_distance_mm"] = (4*(13+40))/2
    payload["geometry"]["lead_angle_deg"] = math.degrees(math.atan(2/13))
    r = calculate_worm_geometry(payload)
    self.assertTrue(r["load_capacity"]["checks"]["geometry_consistent"])   # q 非标不应设为 False

def test_handedness_does_not_change_numerical_result(self):
    p = self._base_payload()
    p["geometry"]["handedness"] = "右旋"; r1 = calculate_worm_geometry(p)
    p["geometry"]["handedness"] = "左旋"; r2 = calculate_worm_geometry(p)
    # 显式锁住"当前实现确实不用 handedness"这一事实，修改后该测试应同步更新
    self.assertEqual(r1["load_capacity"]["forces"], r2["load_capacity"]["forces"])
```

### UI

```python
def test_method_dropdown_is_decorative_only(self):
    """短期内锁住"当前 Method 选择不影响计算"这一现状，提醒后续实现时更新。"""
    page = WormGearPage()
    page._field_widgets["load_capacity.method"].setCurrentText("DIN 3996 Method A -- ...")
    page._calculate(); s1 = page._last_result["load_capacity"]["contact"]["sigma_hm_peak_mpa"]
    page._field_widgets["load_capacity.method"].setCurrentText("DIN 3996 Method C -- ...")
    page._calculate(); s2 = page._last_result["load_capacity"]["contact"]["sigma_hm_peak_mpa"]
    self.assertAlmostEqual(s1, s2)

def test_export_button_disabled_after_input_change(self):
    page = WormGearPage(); page._calculate()
    self.assertTrue(page.btn_save.isEnabled())
    page._field_widgets["geometry.module_mm"].setText("5.0")
    self.assertFalse(page.btn_save.isEnabled())
```

### 基准

- 引入一个 `tests/core/worm/test_niemann_benchmark.py`，对照 Niemann §24.4 或任意公开蜗杆手册算例（如 SEW / Renold / Mitsubishi 工程手册）锁死几何 + 力 + σ_H 量级。

---

## 9. 结语

本次 review 把 2026-04-03 review 后的状态又扫了一遍，并做了**数值级**对照。结论可以一句话概括：

> **当前 Worm 模块的几何部分可信，但从"力分解 → 应力 → 安全系数 → PASS/FAIL 徽章"整条链条存在系统性量级错误 (W26-01..03 + W26-06..07)，不能作为生产校核签字的依据。**

修复 W26-01..03 只需改三行公式、加两条断言测试，工作量小但收益最大——应作为最高优先级 P0 处理。

其他项（材料库扩充、DIN 3996 Method B 落地、几何总览联动）属于"让这个工具真的成为生产工具"的中长期路线图，而不是 quick fix。

---

## 执行摘要（≤ 200 字）

Worm 模块当前**只能用作几何初算与方案对比**，不能用于最终设计放行。69 个测试全绿但掩盖了严重 bug：**力分解公式把 cos(γ) 写成 sin(γ)**（calculator.py:367-371），导致法向力 Fn 高估 cot(γ) 倍（γ=11°时 5×）、蜗轮轴向力高估近 13×、Hertz 齿面应力高估 2.24×，齿根模型又在系数层再高估 3×。Method A/B/C 下拉对计算无影响、q=13 非标准被误判"不通过"、材料库仅覆盖 PA66 一类、应力曲线物理含义错误、几何总览仍是占位图。P0 必修三项力学公式 + 对应基准测试；P1 扩材料库、分离齿根 K 因子、删或落地 Method 区分；P2 才是完整 DIN 3996 落地。
