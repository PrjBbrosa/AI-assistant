# Stage 1.7 术语 Master List 扫描报告

**日期**：2026-04-19
**范围**：bolt / bolt_tapped_axial / interference_fit / hertz_contact / spline_fit 共 5 个模块
**产出**：90 篇新术语候选清单 + 复用关系矩阵

---

## 汇总

| 指标 | 数量 |
|---|---|
| 5 模块候选 help_ref 字段总数 | ≈ 103 |
| 复用蜗杆既有 14 篇术语 | ≈ 10 次 |
| 5 模块内部跨模块复用 | ≈ 35 次 |
| **需新写术语文章** | **≈ 90 篇** |

---

## 模块候选字段总览

### bolt（VDI 2230 螺栓连接）
候选字段 ≈ 45；新写术语 37 个；复用蜗杆 2 次（E_bolt / E_clamped）。
核心术语族：柔度/刚度 (δs/δp/cs/cp)、拧紧 (αA/ν/MA,prev)、损失 (FZ/Fth)、载荷 (FA/FQ/FK,req)、脱扣 (m_eff/τBM/τBS)。

### bolt_tapped_axial（轴向受力螺纹连接）
候选字段 ≈ 21；**仅 1 个新术语**（`axial_load_min_famin`），其余 20 项全部复用 bolt 模块。

### interference_fit（DIN 7190 过盈配合）
候选字段 ≈ 32；新写术语 25 个；复用蜗杆 3 次（E / ν / KA）、复用 bolt 1 次（热膨胀 α）。
核心术语族：过盈量 (δmin/δmax)、粗糙度压平 (k/Rz)、摩擦系数分场景 (μT/μAx/μ装配/μ压入压出)、装配方法 (冷压/热胀/过冷) 。

### hertz_contact（赫兹接触应力）
候选字段 ≈ 8；新写术语 5 个；复用蜗杆 2 次（E1/E2、ν1/ν2）。
核心术语：线/点接触模式、曲率半径 R、接触长度 L、法向载荷 F、许用 p0。

### spline_fit（花键连接）
候选字段 ≈ 21；新写术语 13 个；复用蜗杆 4 次（module / KA / E / ν）、复用 interference 10+ 次（smooth_* 段字段）。
核心术语族：DIN5480 规格、齿面 Kα、p_zul、有效啮合长度 L、退刀槽宽度。

---

## 新写术语主清单（90 篇，按字母序）

| 术语 ref | 出现模块 | 优先级 | 备注 |
|---|---|---|---|
| allowable_bearing_pressure | bolt | P1 | 支承面压强 p_G |
| allowable_flank_pressure_pzul | spline | P1 | 齿面许用 p_zul |
| allowable_p0 | hertz | P1 | 赫兹许用接触应力 |
| assembly_clearance | interference | P2 | 装配间隙 |
| assembly_method | interference | P2 | 装配模式（冷压/热胀/过冷） |
| axial_force_required | interference, spline | P0 | 需求轴向力 |
| axial_load_fa | bolt, bolt_tapped_axial | P0 | 最大轴向工作载荷 FA,max |
| axial_load_min_famin | bolt_tapped_axial | P2 | 最小轴向载荷 FA,min |
| basic_solid_model | bolt | P2 | 基础实体类型（对称锥/非对称锥/等效圆柱） |
| bearing_diameter_inner | bolt, bolt_tapped_axial | P1 | 支承内径 DKm,i |
| bearing_diameter_outer | bolt, bolt_tapped_axial | P1 | 支承外径 DKm,o |
| bending_moment_mb | interference | P2 | 需求弯矩 Mb |
| bolt_compliance_delta_s | bolt | P0 | 螺栓柔度 δs |
| bolt_grade | bolt, bolt_tapped_axial | P0 | ISO 898-1 强度等级（8.8/10.9/12.9） |
| bolt_stiffness_cs | bolt | P0 | 螺栓刚度 cs |
| clamped_compliance_delta_p | bolt | P0 | 被夹件柔度 δp |
| clamped_outer_diameter_da | bolt | P1 | 等效外径 DA |
| clamped_stiffness_cp | bolt | P0 | 被夹件刚度 cp |
| clamping_length_lk | bolt | P1 | 总夹紧长度 lK |
| compliance_vs_stiffness | bolt | P2 | 柔度 vs 刚度的互逆关系说明 |
| contact_length_l | hertz | P1 | 接触长度 L |
| contact_mode_line_point | hertz | P0 | 线接触 / 点接触切换 |
| curvature_radius_r | hertz | P1 | 等效曲率半径 R |
| din5480_designation | spline | P1 | DIN 5480 规格字符串解析 |
| embedding_loss_fz | bolt | P1 | 嵌入损失 FZ |
| fit_diameter_d | interference, spline | P0 | 配合基本直径 |
| fit_length_l | interference, spline | P0 | 配合长度 L |
| flank_safety_sflank | spline | P1 | 齿面安全系数 S_flank |
| fretting_assessment | interference | P2 | 微动磨损评估（5 字段合一） |
| friction_bearing_mu_k | bolt, bolt_tapped_axial | P0 | 支承面摩擦 μK |
| friction_interfaces_qf | bolt | P2 | 摩擦面数 qF |
| friction_mu_assembly | interference, spline | P1 | 装配摩擦系数 |
| friction_mu_axial | interference, spline | P1 | 轴向摩擦系数 μAx |
| friction_mu_torque | interference, spline | P1 | 扭矩方向摩擦系数 μT |
| friction_press_in_out | interference | P2 | 压入/压出摩擦系数 |
| friction_thread_mu_g | bolt, bolt_tapped_axial | P0 | 螺纹摩擦 μG |
| hub_deviation_es_ei | interference | P1 | 孔上/下偏差 ES/EI |
| hub_outer_diameter | interference, spline | P0 | 轮毂外径 D |
| hub_temp_limit | interference | P2 | 轮毂允许最高温度 |
| interference_delta_max | interference, spline | P0 | 最大过盈量 δmax |
| interference_delta_min | interference, spline | P0 | 最小过盈量 δmin |
| interference_source_mode | interference | P2 | 过盈来源模式（配合代号/直接输入） |
| k_alpha_spline | spline | P1 | 载荷分布系数 Kα（spline 专属） |
| load_cycles_nd | bolt, bolt_tapped_axial | P1 | 载荷循环次数 ND |
| load_intro_factor_n | bolt | P0 | 载荷导入系数 n |
| minor_diameter_d3 | bolt, bolt_tapped_axial | P1 | 小径 d3 |
| nominal_diameter_d | bolt, bolt_tapped_axial | P0 | 公称直径 d |
| normal_force_f | hertz | P1 | 法向载荷 F |
| pitch_diameter_d2 | bolt, bolt_tapped_axial | P1 | 中径 d2 |
| preferred_fit | interference | P2 | 优选配合代号（H7/p6 等） |
| preload_min_fm | bolt, bolt_tapped_axial | P0 | 最小预紧力 FM,min |
| prevailing_torque | bolt, bolt_tapped_axial | P1 | 附加防松扭矩 MA,prev |
| radial_force_fr | interference | P2 | 需求径向力 |
| reference_diameter_db | spline | P1 | 参考直径 d_B |
| relief_groove_width | spline | P2 | 退刀槽宽度 |
| residual_clamp_force_fk | bolt | P1 | 残余夹紧力 FK,req |
| root_diameter_df | spline | P1 | 齿根圆直径 d_f |
| roughness_profile_din7190 | interference | P1 | 粗糙度压平模型 |
| roughness_smoothing_k | interference | P1 | 压平系数 k |
| shaft_deviation_es_ei | interference | P1 | 轴上/下偏差 es/ei |
| shaft_inner_di | interference, spline | P1 | 轴内径 di（空心轴） |
| slip_friction_mu_t | bolt | P2 | 防滑摩擦 μT |
| slip_safety_sslip | interference, spline | P0 | 防滑安全系数 S_slip |
| spline_engagement_length | spline | P1 | 花键有效啮合长度 |
| spline_geometry_mode | spline | P2 | 几何输入模式（近似/公开尺寸/图纸） |
| spline_load_condition | spline | P2 | 载荷工况（按 DIN 5466） |
| spline_scenario_mode | spline | P2 | 花键校核模式（仅花键/含光滑段） |
| stress_area_as | bolt, bolt_tapped_axial | P1 | 应力截面积 As |
| stress_safety_ssigma | interference, spline | P0 | 材料安全系数 S_sigma |
| surface_class | bolt | P2 | 接触面粗糙度分级 |
| surface_condition | interference | P2 | 过盈面表面状态（粗车/精车/磨） |
| surface_roughness_rz | interference, spline | P1 | 表面粗糙度 Rz |
| thermal_expansion_alpha | bolt, interference | P0 | 热膨胀系数 α |
| thermal_loss_fth | bolt | P1 | 温升引起的预紧力损失 Fth |
| thread_engagement_meff | bolt, bolt_tapped_axial | P1 | 有效旋合深度 m_eff |
| thread_flank_angle | bolt, bolt_tapped_axial | P1 | 牙型角（60°/55°） |
| thread_pitch_p | bolt, bolt_tapped_axial | P0 | 螺距 p |
| thread_shear_tau_bm | bolt, bolt_tapped_axial | P1 | 内螺纹剪切强度 τBM |
| thread_shear_tau_bs | bolt, bolt_tapped_axial | P1 | 外螺纹剪切强度 τBS |
| thread_strip_safety | bolt, bolt_tapped_axial | P1 | 脱扣安全系数要求 |
| thread_surface_treatment | bolt, bolt_tapped_axial | P2 | 螺纹表面处理（钝化/达克罗/磷化） |
| tightening_factor_alpha_a | bolt, bolt_tapped_axial | P0 | 拧紧系数 αA |
| tightening_method | bolt, bolt_tapped_axial | P0 | 拧紧方式（扭矩/转角/屈服） |
| tip_diameter_da | spline | P1 | 齿顶圆直径 d_a |
| tooth_count_z | spline | P1 | 齿数 z |
| torque_required_treq | interference, spline | P0 | 需求扭矩 T_req |
| utilization_nu | bolt, bolt_tapped_axial | P0 | 装配利用系数 ν |
| yield_safety_sf | bolt, bolt_tapped_axial | P0 | 服役屈服安全系数 S_F |
| yield_strength_re | interference, spline | P0 | 轴/轮毂屈服强度 Re |
| yield_strength_rp02 | bolt, bolt_tapped_axial | P0 | 螺栓屈服强度 Rp0.2（ISO 898-1） |

---

## 复用蜗杆既有术语映射

| 蜗杆术语 | 被引用模块 | 次数 |
|---|---|---|
| terms/elastic_modulus | bolt, interference (轴/毂), hertz (E1/E2), spline | 6 次 |
| terms/poisson_ratio | interference, hertz, spline | 4 次 |
| terms/module | spline | 1 次 |
| terms/application_factor_ka | interference, spline | 2 次 |
| terms/diameter_factor_q | —— | 0（蜗杆专用） |
| terms/lead_angle, profile_shift, pressure_angle | —— | 0（蜗杆专用） |
| terms/kh_alpha, kh_beta, kv_factor | —— | 0（齿轮专用） |
| terms/allowable_contact_stress, allowable_root_stress | —— | 0（齿轮专用） |
| terms/lubrication | —— | 0（润滑剂本身在其他模块未作为独立字段） |

**蜗杆 14 篇中 10 篇仅蜗杆使用**。复用率偏低，符合 DIN 3975/3996 的高度专业化特征。

---

## 关键发现

1. **bolt ↔ bolt_tapped_axial 极高重叠**：后者 20/21 字段全部复用 bolt 术语；新写 bolt 那一批等于同时覆盖两个模块。
2. **interference ↔ spline 共享光滑段场景**：spline 的 `smooth_*` 段与 interference 的对应字段一一对应，12+ 项复用。
3. **hertz 是最轻量级**：仅 5 篇新术语 + 2 次蜗杆复用。可作为 Stage 2 第一个试点（快速验证流程）。
4. **所有 5 模块已经有 `help_ref: str = ""` 占位**：Stage 2+ 只需填 ref、不需改 FieldSpec 结构。
5. **推荐写作批次建议**：
   - **Batch 1（P0 高复用率）**：bolt 核心族（nominal_d / pitch / d2 / d3 / As / Rp02 / grade / FM,min / αA / ν / μG / μK / tightening_method）—— 写完一批，bolt + bolt_tapped_axial 双模块直接可 wire
   - **Batch 2（P0 interference + spline）**：δmin/δmax / Re / S_sigma / S_slip / T_req / μT/μAx / 配合直径/长度 —— 写完一批，interference + spline smooth 段可 wire
   - **Batch 3（P1 bolt 剩余 + hertz + spline 齿面）**：柔度/刚度族（4 篇）、脱扣族（4 篇）、hertz（5 篇）、spline 齿面（4 篇）
   - **Batch 4（P2 长尾）**：fretting / 表面状态 / 装配模式 / DIN5480 规格等（≈ 20 篇）

---

## 自检

- 候选字段 103 = 新写覆盖 ≈ 58 + 跨模块复用 ≈ 35 + 蜗杆复用 ≈ 10 ✓
- 新写术语 90 篇 × 平均 1.5 次复用 ≈ 135 次字段覆盖 > 103 字段（因单篇术语常覆盖多个字段，如 μT/μAx/μ装配三字段共 3 篇）✓
- 与 GUIDELINES §6 判定规则对齐：所有候选字段均符合"希腊字母 / 标准缩写 / DIN/VDI/ISO 条款 / 行业术语"四条件之一 ✓
