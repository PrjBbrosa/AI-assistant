# core/ 数值上界巡检（R-6）

核查时间：2026-07-07

核查命令：

```bash
rg -n "_positive\(|_positive_int\(|_in_closed_interval\(" core --glob "*.py"
rg -n "_positive\(|_positive_int\(|_in_closed_interval\(" core --glob "*.py" | rg -v "def _" | wc -l
```

非定义处调用点：158。下表按相邻调用点和相同物理语义分组；每个 `_positive`、`_positive_int`、`_in_closed_interval` 调用点均被所在行段覆盖。同类区间 helper（例如 `_nu`、`_in_open_interval`）作为已有上界证据一并备注。

| 文件:行 | 字段 | 物理含义 | 上界需要? | 现状 | 结论/建议 |
|---|---|---|---|---|---|
| `core/bolt/calculator.py:49-51` | `fastener.As/d2/d3` | d/p 派生螺纹面积和直径 | 不需要通用上界 | 正值 + 一致性校验 | 无上界(物理开放量) |
| `core/bolt/calculator.py:67-78` | `stiffness.bolt_compliance/clamped_compliance/bolt_stiffness/clamped_stiffness/E_bolt` | 柔度、刚度、材料模量 | 不需要通用上界 | 正值 | 无上界(物理开放量) |
| `core/bolt/calculator.py:87-104` | `clamped.layers[].l_K`、`clamped.total_thickness`、`E_clamped` | 被夹件层厚与模量 | 不需要通用上界 | 正值；层数 1~10 | 无上界(物理开放量) |
| `core/bolt/calculator.py:133-138` | `stiffness.load_introduction_factor_n` | 载荷导入系数 n | 需要 `0 < n <= 1` | P0 Task 1 已补 n > 1 拦截 | 已拦截 |
| `core/bolt/calculator.py:242-254` | `fastener.d/p/Rp02`、`tightening.alpha_A/mu_thread/mu_bearing/utilization` | 螺纹、强度、拧紧散差、摩擦、利用率 | 部分需要上界 | `alpha_A >= 1`；摩擦 `<= 1`；utilization `<= 1` | 已拦截 |
| `core/bolt/calculator.py:260-273` | `loads.FA_max/FQ_max/seal_force_required/embed_loss/thermal_force_loss`、`operating.load_cycles` | 外载、损失、循环次数 | 不需要通用上界 | 非负/正值 | 无上界(物理开放量) |
| `core/bolt/calculator.py:274-279` | `loads.slip_friction_coefficient`、`loads.friction_interfaces` | 防滑摩擦系数、摩擦界面数 | 摩擦系数需要上界；界面数应为正整数 | 摩擦系数 `<= 1`；界面数仅正值 | `slip_friction_coefficient` 已拦截；`friction_interfaces` 建议加上界(P-next) |
| `core/bolt/calculator.py:281-290` | `bearing.bearing_d_inner/outer` | 支承直径 | 需要相对关系 | 外径必须大于内径 | 已拦截 |
| `core/bolt/calculator.py:430-433` | `loads.FM_min_input` | 校核模式输入预紧力 | 不需要通用上界 | 正值 | 无上界(物理开放量) |
| `core/bolt/calculator.py:468-475` | `checks.yield_safety_operating` | 服役屈服安全系数要求 | 需要下限 `>= 1` | 已要求 `>= 1` | 已拦截 |
| `core/bolt/calculator.py:527-536` | `thread_strip.m_eff/tau_BS/tau_BM` | 旋合长度、剪切强度 | 不需要通用上界 | 正值；缺 tau_BM 拒绝 | 无上界(物理开放量) |
| `core/bolt/calculator.py:538-539` | `thread_strip.C1/C3` | 脱扣面积修正系数/有效比例 | 需要 `0 < C <= 1` | 仅正值 | 建议加上界(P-next) |
| `core/bolt/calculator.py:561-564` | `thread_strip.safety_required` | 脱扣安全系数要求 | 需要 `>= 1` | 仅正值 | 建议加上界(P-next) |
| `core/bolt/tapped_axial_joint.py:77-86` | `fastener.d/p/As/d2/d3` | d/p 派生螺纹几何 | 不需要通用上界 | 正值 + 一致性校验 | 无上界(物理开放量) |
| `core/bolt/tapped_axial_joint.py:128-146` | `Rp02`、`F_preload_min`、`alpha_A`、`mu_thread/mu_bearing` | 材料强度、预紧力、散差、摩擦 | 摩擦/散差需要边界 | `alpha_A >= 1`；摩擦 `<= 1` | 已拦截 |
| `core/bolt/tapped_axial_joint.py:148-166` | `bearing_d_inner/outer`、`thread_flank_angle_deg` | 支承直径、螺纹牙型角 | 直径需相对关系；角度可设工程范围 | 外径必须大于内径；牙型角仅正值 | 直径已拦截；牙型角建议加上界(P-next) |
| `core/bolt/tapped_axial_joint.py:173-184` | `utilization`、`FA_min/FA_max`、`load_cycles` | 利用率、服役载荷、循环次数 | 利用率需要 `<= 1`；载荷需相对关系 | utilization `<= 1`；`FA_min <= FA_max` | 已拦截 |
| `core/bolt/tapped_axial_joint.py:187-194` | `checks.yield_safety_operating` | 服役屈服安全系数要求 | 需要 `>= 1` | 已要求 `>= 1` | 已拦截 |
| `core/bolt/tapped_axial_joint.py:274-278` | `thread_strip.m_eff/tau_BS/tau_BM` | 旋合长度、剪切强度 | 不需要通用上界 | 正值；缺 tau_BM 拒绝 | 无上界(物理开放量) |
| `core/bolt/tapped_axial_joint.py:279-282` | `thread_strip.safety_required` | 脱扣安全系数要求 | 需要 `>= 1` | 仅正值 | 建议加上界(P-next) |
| `core/bolt/compliance_model.py:20-23` | `d/p/l_K/E_bolt` | 螺栓柔度几何和模量 | 不需要通用上界 | 正值 | 无上界(物理开放量) |
| `core/bolt/compliance_model.py:66-79` | `d_h/D_A/D_w/l_K/E_clamped` | 被夹件圆柱/锥台几何 | 需要相对几何关系 | cone 分支校验 `D_w > d_h` 和 `D_A > d_h`；cylinder 未显式校验 | cylinder 建议加上界(P-next) |
| `core/bolt/compliance_model.py:98-104` | `D_outer/D_inner/l_K/E_clamped` | 套筒模型几何和模量 | 需要 `D_outer > D_inner` | 仅正值 | 建议加上界(P-next) |
| `core/interference/calculator.py:64-78` | `shaft_d_mm/shaft_inner_d_mm/hub_outer_d_mm/fit_length_mm` | 轴、轮毂和配合长度 | 需要相对几何关系 | `shaft_inner_d_mm < d`；`hub_outer_d_mm > d` | 已拦截 |
| `core/interference/calculator.py:80-99` | `shaft_e_mpa/hub_e_mpa/yield`、`shaft_nu/hub_nu` | 模量、屈服、泊松比 | 泊松比需要 `< 0.5` | `_in_open_interval(0,0.5)` | 已拦截 |
| `core/interference/calculator.py:101-122` | `delta_min/max`、`roughness.rz_*`、`smoothing_factor` | 过盈量、粗糙度、压平比例 | 压平系数需要 `<= 1`；过盈需相对关系 | `delta_max >= delta_min`；smoothing `<= 1` | 已拦截 |
| `core/interference/calculator.py:140-157` | `friction.mu_torque/mu_axial/mu_assembly` | 摩擦系数 | 需要 `0 < mu < 1` | `_in_open_interval(0,1)` | 已拦截 |
| `core/interference/calculator.py:159-178` | `torque/axial/radial/bending_required` | 载荷需求 | 不需要通用上界 | 非负 | 无上界(物理开放量) |
| `core/interference/calculator.py:179-182` | `loads.application_factor_ka` | 工况放大系数 | 需要 `>= 1` | 仅正值 | 建议加上界(P-next) |
| `core/interference/calculator.py:189-190` | `checks.slip_safety_min/stress_safety_min` | 最小安全系数要求 | 需要 `>= 1` | 仅正值；P1 R-12 已列入实施 | 需修复(已纳入P1) |
| `core/interference/calculator.py:192` | `options.curve_points` | 曲线采样数 | 需要运行上界 | `_in_closed_interval(11,201)` | 已拦截 |
| `core/interference/assembly.py:50-58` | context 尺寸、过盈、压力、面积 | 装配派生量 | 不需要通用上界 | 正值/非负 | 无上界(物理开放量) |
| `core/interference/assembly.py:59-61` | context `mu_assembly/mu_torque/mu_axial` | 摩擦系数 | 需要 `0 < mu < 1` | `_open_interval(0,1)` | 已拦截 |
| `core/interference/assembly.py:100-114` | `clearance_um`、`alpha_hub/shaft` | 热装间隙与热膨胀系数 | 不需要通用上界 | 非负/正值；温度限制另有逻辑 | 无上界(物理开放量) |
| `core/worm/calculator.py:76-83` | `geometry.z1/z2` | 蜗杆头数、蜗轮齿数 | `z1` 需要常规上界；两者需整数 | P0 Task 2 已补 `z1 <= 6`；二者整数校验 | 已拦截 |
| `core/worm/calculator.py:84-97` | `module_mm/center_distance_mm/diameter_factor_q/lead_angle_deg` | 模数、中心距、直径系数、导程角 | 导程角需工程上界；中心距需 LC 容差 | lead angle `<= 45`；P0 Task 3 已补 LC 中心距容差拒绝 | 已拦截 |
| `core/worm/calculator.py:100-107` | `operating.input_torque_nm/speed_rpm/application_factor/torque_ripple_percent` | 扭矩、转速、工况系数、转矩波动 | 系数/百分比需要边界 | 扭矩/转速正值；系数/百分比仅正值/非负 | `application_factor >= 1`、`0 <= ripple <= 100` 建议加上界(P-next) |
| `core/worm/calculator.py:147-149` | `worm_e_mpa/wheel_e_mpa` | 材料模量 | 不需要通用上界 | 正值；泊松比由 `_nu` 限定 | 无上界(物理开放量) |
| `core/worm/calculator.py:153-156` | `x1/x2` | 变位系数 | 需要工程区间 | `-0.5..1.0` | 已拦截 |
| `core/worm/calculator.py:187-192` | `worm_face_width_mm/wheel_face_width_mm` | 齿宽 | 不需要通用上界 | 正值 | 无上界(物理开放量) |
| `core/worm/calculator.py:203-216` | `advanced.friction_override` | 摩擦覆盖值 | 需要工程上界 | 覆盖值 `0.01..0.30`；润滑修正后钳位 `<= 0.50` | 已拦截 |
| `core/worm/calculator.py:221-228` | `advanced.normal_pressure_angle_deg` | 法向压力角 | 需要工程范围 | P0 Task 2 已补 `[5,35] deg` | 已拦截 |
| `core/worm/calculator.py:397-406` | `center_distance_delta_mm`（由中心距正值派生） | LC 接触模型适用容差 | 需要硬拒绝 | P0 Task 3：`abs(delta) <= max(5% a_th, 2mm)` | 已拦截 |
| `core/worm/calculator.py:441-448` | `dynamic_factor_kv/kha/khb` | 载荷放大系数 | 需要 `>= 1` | 仅正值 | 建议加上界(P-next) |
| `core/worm/calculator.py:450-456` | `allowable_contact/root_stress_mpa` | 许用应力 | 不需要通用上界 | 正值 | 无上界(物理开放量) |
| `core/worm/calculator.py:458-464` | `required_contact/root_safety` | 最小安全系数要求 | 需要 `>= 1` | 仅正值 | 建议加上界(P-next) |
| `core/worm/calculator.py:494-501` | `lead_angle_calc_rad + phi_prime_force_rad` | 力分解定义域 | 需要 `< 90 deg` 防线 | P0 Task 2 已补 `>= 89 deg` 拒绝 | 已拦截 |
| `core/spline/calculator.py:59-63` | `module_mm/tooth_count/engagement_length_mm` | 花键模数、齿数、啮合长度 | 齿数需整数；其余开放 | `_positive_int` 校验正整数；尺寸正值 | 已拦截/无上界 |
| `core/spline/calculator.py:67-72` | `spline.k_alpha/p_allowable_mpa` | 载荷分布系数、许用承压 | 系数建议 `>= 1` | `k_alpha` 仅正值 | `k_alpha` 建议加上界(P-next)；许用承压无上界 |
| `core/spline/calculator.py:160-163` | `smooth_fit.fit_length_mm` | 光滑段配合长度 | 不需要通用上界 | 正值；退刀槽后有效长度 >0 | 无上界(物理开放量) |
| `core/spline/calculator.py:238-247` | `torque_required_nm/application_factor_ka/flank_safety_min` | 扭矩、工况系数、齿面安全系数 | 系数/安全系数需下限 | 仅正值 | `application_factor_ka >= 1`、`flank_safety_min >= 1` 建议加上界(P-next) |
| `core/spline/calculator.py:258-269` | `axial_force_required_n/slip_safety_min/stress_safety_min` | 轴向力、光滑段安全系数 | 安全系数需 `>= 1` | 轴向力非负；安全系数仅正值 | 安全系数建议加上界(P-next) |
| `core/hertz/calculator.py:35,106-107` | `geometry.r1_mm/r2_mm` | 曲率半径，0 表示平面 | 不需要通用上界 | 非负；等效曲率必须 >0 | 无上界(物理开放量) |
| `core/hertz/calculator.py:113-116` | `e1/e2`、`nu1/nu2` | 模量、泊松比 | 泊松比需要 `<0.5` | `_nu(0,0.5)` | 已拦截 |
| `core/hertz/calculator.py:119-130` | `normal_force_n/allowable_p0_mpa/length_mm` | 法向力、许用接触压、线接触长度 | 不需要通用上界 | 正值 | 无上界(物理开放量) |
| `core/hertz/calculator.py:153-156` | `curve_points/curve_force_scale` | 曲线采样和力倍率 | 需要运行上界 | 虽非 `_in_closed_interval`，已有钳位 `11..201`、`1.05..2.0` | 已拦截 |
| `core/buffer/calculator.py:389-392` | `force_scale/stroke_scale/noise_tolerance_n` | 曲线缩放与噪声容差 | 可加运行保护上界 | 正值/非负 | 建议加上界(P-next) |
| `core/buffer/calculator.py:394-396` | `time_samples` | 时域采样点 | 需要运行上界 | 仅 `>= 8` | 建议加上界(P-next) |
| `core/buffer/calculator.py:417-426` | `mass_kg/initial_velocity/available_stroke/allowable_peak_force_n` | 冲击质量、速度、行程、允许峰值力 | 不需要通用上界 | 正值 | 无上界(物理开放量) |

## 后续建议汇总

本批已关闭 P0 的三处非保守/崩溃风险：螺栓 `load_introduction_factor_n`、蜗轮 `z1/normal_pressure_angle/gamma+phi'`、蜗轮 LC 中心距容差。P1 已计划关闭过盈模块安全系数阈值 `< 1` 的问题。

建议后续单独立项时优先看这些系数类输入：

1. 安全系数目标：`thread_strip.safety_required`、spline 安全系数、worm required safety。
2. 载荷放大系数：bolt friction interface 计数、interference/spline/worm application/load factors。
3. 比例或修正系数：bolt thread strip `C1/C3`、spline `k_alpha`、buffer 缩放/采样。
4. 几何相对关系：bolt compliance cylinder/sleeve 分支的外径/内径关系。
