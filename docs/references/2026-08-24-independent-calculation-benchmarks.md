# 独立计算基准登记表（2026-08-24）

## 目的与证据边界

本文件记录 `tests/core/test_independent_references.py` 中七类 calculator 的独立基准。期望值来自公开资料中的固定算例，或从公开公式进行的独立手算；不从本软件输出反抄。

这些基准是针对关键物理不变量的 sanity check，不等同于完整 VDI、DIN、ISO 签发验证。特别是蜗轮承载能力和花键强度当前只覆盖简化模型的基础输入输出关系。

## A. 外部独立 benchmark

本节只把外部资料或独立手算支持的物理量称为“独立基准”。同一测试中顺带检查的软件 verdict 仍属于内部 contract，不代表外部资料验证了整个模块。

| ID | Calculator | 独立来源 | 输入与独立计算 | 固定期望 | 测试容差 | 适用边界 |
|---|---|---|---|---:|---:|---|
| BOLT-REF-01 | `calculate_vdi2230_core` | NASA RP-1228 *Fastener Design Manual*，外载荷在螺栓和被夹件弹簧之间分配 | `Fi=10000 N`、`Fe=1000 N`、螺栓/被夹件柔度 `2/3 um/kN`。`kb/(kb+kc)=delta_p/(delta_s+delta_p)=0.6`，故 `Fb=Fi+0.6Fe` | `phi=0.6`；`Fb=10600 N` | `1e-12`；`1e-9 N` | 连接未分离、线弹性、载荷导入系数为 1；不是完整 VDI 2230 验证 |
| TAP-REF-01 | `calculate_tapped_axial_joint` | NASA Lewis 公共课程资料中的 metric thread tensile area；NASA RP-1228 的轴向载荷静力关系 | M8x1.25：`As=pi/4*(8-0.9382*1.25)^2=36.6085 mm2`。无被夹件纯轴向模型中 `Fmax=1.6*8000+1200=14000 N`，`sigma=F/As` | `Fmax=14000 N`；`sigma=382.43 MPa` | `1e-9 N`；`0.02 MPa` | 只验证纯轴向静力叠加和名义拉应力；不验证横向力、弯矩、疲劳谱或完整脱扣模型 |
| INT-REF-01 | `calculate_interference_fit` | Portland State University `Strength-PE-Hormoz.pdf`，Problem S14 | 实心钢轴/钢套：配合直径 `40 mm`、轴径 `40.026 mm`、套外径 `80 mm`、`E=205 GPa`、径向过盈 `0.013 mm`。公开题目答案为界面压力约 `50 MPa` | `p≈50 MPa` | `±0.5 MPa`；来源只给约两位有效数字，不主张更高精度 | 同材料、长圆柱、均匀压力、小过盈、无粗糙度压平；不覆盖端部和塑性效应 |
| HERTZ-REF-01 | `calculate_hertz_contact` | MIT 2.75 Topic 9 *Hertz Contact: Line Contact* | 圆柱对平面：`F=12000 N`、`L=20 mm`、`R=30 mm`、`E1=E2=210000 MPa`、`nu1=.29`、`nu2=.30`。先算 `E'=[(1-nu1^2)/E1+(1-nu2^2)/E2]^-1=115011.775 MPa`；再由 `b=sqrt(4(F/L)R/(pi E'))`、`p0=2(F/L)/(pi b)` | `b=0.446396 mm`；`p0=855.680 MPa` | `1e-6 mm`；`0.002 MPa` | 平行轴、弹性、光滑、无边缘效应、外线接触；不覆盖塑性和内接触 |
| WORM-REF-01 | `calculate_worm_geometry` | KHK Gears *Calculation of Gear Dimensions* 的轴向模数蜗杆副关系 | `m=4 mm`、`q=10`、`z1=1`、`z2=40`、`n1=1500 rpm`。`d1=qm=40 mm`，`d2=mz2=160 mm`，`i=z2/z1=40`，`n2=n1/i=37.5 rpm`，`a=(d1+d2)/2=100 mm` | `d1=40 mm`；`d2=160 mm`；`i=40`；`n2=37.5 rpm`；`a=100 mm` | `1e-12` | 只验证几何与理想运动学；不验证效率、温升、材料降额或 DIN 3996 承载能力 |
| SPL-REF-01 | `calculate_spline_fit` | 公开论文 *Fatigue damage in spline couplings* 的平均齿面压力关系；UPC 公开论文的 `F=T/r` 与承压面积推导 | `Tdesign=50*1.25=62.5 N.m`、`k=1.3`、`z=10`、`h=(14.75-12.5)/2=1.125 mm`、`dm=(14.75+12.5)/2=13.625 mm`、`L=40 mm`。`p=2Tdesign*k/(z*h*dm*L)` | `p=26.5036 MPa` | `0.0001 MPa` | 均匀平均齿面承压简化模型；不证明 DIN 5480 公差几何、齿根、轮毂胀裂、磨损或 DIN 6892 完整性 |
| BUF-REF-01 | `calculate_buffer_energy` | OpenStax *University Physics Volume 1*，功—能定理和 `K=mv^2/2` | `m=2 kg`、`v=1 m/s`，初始能量 `1 J`。线性曲线从 `(0 mm,0 N)` 到 `(10 mm,1000 N)`，即 `k=100 N/mm`；总容量为三角形面积 `5 J`。令 `0.5*k*x^2*0.001=1 J` | `x=sqrt(20)=4.472135955 mm`；`F=447.2135955 N` | `1e-9` | 准静态、线性、水平单次冲击、无应变率/重力/时间域动力学；只验证能量积分和反解 |

### 外部 benchmark 可执行索引

| ID | pytest node id | 同节点的量纲缩放检查 |
|---|---|---|
| BOLT-REF-01 | `tests/core/test_independent_references.py::test_bolt_calculator_matches_two_spring_external_load_sharing` | 固定刚度比时，外载增量加倍，螺栓附加载荷加倍 |
| TAP-REF-01 | `tests/core/test_independent_references.py::test_tapped_axial_calculator_matches_direct_force_superposition` | `FA_max` 减半，外载引起的轴力/应力增量减半 |
| INT-REF-01 | `tests/core/test_independent_references.py::test_interference_calculator_matches_published_shaft_collar_problem` | 线弹性下过盈量减半，界面压力减半 |
| HERTZ-REF-01 | `tests/core/test_independent_references.py::test_hertz_calculator_matches_mit_line_contact_equations` | 线接触载荷乘 4，半宽和峰值压力均乘 2 |
| WORM-REF-01 | `tests/core/test_independent_references.py::test_worm_calculator_matches_public_gear_geometry_kinematics` | 模数减半，直径/中心距减半；传动比和转速比不变 |
| SPL-REF-01 | `tests/core/test_independent_references.py::test_spline_calculator_matches_independent_flank_bearing_formula` | 扭矩加倍，平均齿面压力加倍 |
| BUF-REF-01 | `tests/core/test_independent_references.py::test_buffer_calculator_matches_work_energy_for_linear_force_curve` | 速度乘 `sqrt(2)`，能量加倍，线性弹簧压缩量/峰值力乘 `sqrt(2)` |

## B. 内部 contract matrix

下表登记的是公开 calculator 的可执行行为契约，用于满足每模块至少 2 个正常通过、2 个正常失败、关键边界和量纲缩放的门禁。它们验证 verdict、边界和单调关系，但期望来自软件已声明的内部契约；**不得与 A 节的外部独立基准等同**。这里的“失败”是 calculator 正常返回的 fail/check-false，不用输入异常代替。

| 模块 | 2 个正常通过工况 | 2 个正常失败工况 | 关键边界 | 量纲/单调缩放 |
|---|---|---|---|---|
| VDI 2230 螺栓 | `tests/core/bolt/test_calculator.py::TestOverallStatus::test_full_r7_r8_inputs_can_reach_pass`；`tests/core/bolt/test_calculator.py::TestBearingPressureR7::test_r7_pass_when_pressure_below_limit` | `tests/core/bolt/test_calculator.py::TestCalculationMode::test_verify_mode_with_insufficient_preload`；`tests/core/bolt/test_calculator.py::TestBearingPressureR7::test_r7_fail_when_pressure_above_limit` | `tests/core/bolt/test_calculator.py::TestLoadIntroductionFactorBound::test_n_equal_one_unchanged` 与 `tests/core/bolt/test_calculator.py::TestLoadIntroductionFactorBound::test_n_slightly_above_one_rejected` | BOLT-REF-01 外载线性分配；`tests/core/bolt/test_calculator.py::TestFatigueModelImproved::test_larger_bolt_lower_asv` |
| 轴向受力螺纹 | TAP-REF-01 的基准与半载两个 pass 工况；`tests/core/bolt/test_tapped_axial_joint.py::test_static_load_fa_min_equals_fa_max_amplitude_zero` | `tests/core/bolt/test_tapped_axial_joint.py::test_assembly_failure_high_preload`；`tests/core/bolt/test_tapped_axial_joint.py::test_high_mean_stress_fails_fatigue_low_goodman` | `tests/core/bolt/test_tapped_axial_joint.py::test_cycle_factor_at_2e6_equals_one` 与 `tests/core/bolt/test_tapped_axial_joint.py::test_cycle_factor_below_2e6_applies_correction` | TAP-REF-01 的轴力/应力线性叠加 |
| 过盈配合 | `tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_nominal_case_outputs_pressure_torque_and_curve`；`tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_fretting_can_be_high_risk_without_changing_base_overall_pass` | `tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_combined_torque_and_axial_usage_can_fail_overall_even_if_single_checks_pass`；`tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_slip_safety_factor_increases_required_interference_and_can_exhaust_fit_window` | `tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_safety_requirement_accepts_one_as_minimum` 与 `tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_safety_requirement_rejects_slip_safety_below_one` | INT-REF-01 过盈—压力线性；`tests/core/interference/test_calculator.py::InterferenceFitCalculatorTests::test_application_factor_increases_required_interference` |
| 赫兹接触 | `tests/core/test_independent_references.py::test_hertz_independent_threshold_contract_matrix[pass-1000]`；`tests/core/test_independent_references.py::test_hertz_independent_threshold_contract_matrix[pass-900]` | `tests/core/test_independent_references.py::test_hertz_independent_threshold_contract_matrix[fail-800]`；`tests/core/test_independent_references.py::test_hertz_independent_threshold_contract_matrix[fail-500]` | `tests/core/hertz/test_calculator.py::test_nu_valid_boundaries`、`tests/core/hertz/test_calculator.py::test_nu_zero_rejected`、`tests/core/hertz/test_calculator.py::test_nu_half_rejected` | HERTZ-REF-01 的 `b,p0 ∝ sqrt(F)` |
| 蜗轮蜗杆 | `tests/core/test_independent_references.py::test_worm_internal_pass_fail_contract_matrix[pass-exact]`；`tests/core/test_independent_references.py::test_worm_internal_pass_fail_contract_matrix[pass-inside-geometry-boundary]` | `tests/core/test_independent_references.py::test_worm_internal_pass_fail_contract_matrix[fail-outside-geometry-boundary]`；`tests/core/test_independent_references.py::test_worm_internal_pass_fail_contract_matrix[fail-low-allowables]` | 上述几何一致性 `0.49°/0.51°` 跨界；`tests/core/worm/test_calculator.py::test_z1_above_6_rejected` | WORM-REF-01 模数长度缩放与速比不变量；`tests/core/worm/test_calculator.py::test_lubrication_dry_increases_friction` |
| 花键连接 | SPL-REF-01；`tests/core/spline/test_calculator.py::TestScenarioA::test_nominal_case_passes` | `tests/core/spline/test_calculator.py::TestScenarioA::test_high_torque_fails`；`tests/core/spline/test_calculator.py::TestScenarioB::test_overall_pass_requires_both` | `tests/core/spline/test_calculator.py::TestScenarioA::test_zero_torque_raises`；`tests/core/spline/test_calculator.py::TestScenarioA::test_non_integer_tooth_count_raises` | SPL-REF-01 扭矩—齿面压力线性；`tests/core/spline/test_calculator.py::TestScenarioB::test_relief_groove_reduces_effective_length` |
| 缓冲块 | `tests/core/buffer/test_calculator.py::CalculateBufferEnergyEndToEndTests::test_overall_pass_true_for_clean_case`；`tests/core/buffer/test_calculator.py::ReboundAndCheckTests::test_checks_non_bottom_out` | `tests/core/buffer/test_calculator.py::CalculateBufferEnergyEndToEndTests::test_bottom_out_schema_is_conservative`；`tests/core/buffer/test_calculator.py::ReboundAndCheckTests::test_checks_peak_force_exceeds` | `tests/core/buffer/test_calculator.py::ImpactSolveTests::test_bottom_out_marks_unknown_peak`；`tests/core/buffer/test_calculator.py::CurveNormalizationTests::test_rejects_negative_force` | BUF-REF-01 的 `E∝v²` 和线性弹簧 `x,F∝sqrt(E)`；`tests/core/buffer/test_calculator.py::CurveNormalizationTests::test_applies_scales` |

执行命令：

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/core/test_independent_references.py tests/core/bolt tests/core/interference tests/core/hertz tests/core/worm tests/core/spline tests/core/buffer -q
```

## 公开来源

1. NASA, Richard T. Barrett, *Fastener Design Manual*, NASA-RP-1228: <https://ntrs.nasa.gov/api/citations/19900009424/downloads/19900009424.pdf>
2. NASA Lewis Research Center, metric thread tensile area formula `A=pi/4*(D-0.9382P)^2`: <https://ntrs.nasa.gov/api/citations/20110016427/downloads/20110016427.pdf>
3. Portland State University, *Strength of Materials and Failure Theories*, Problem S14: <https://web.cecs.pdx.edu/~far/me437/Fall%202014/Strength/Strength-PE-Hormoz.pdf>
4. MIT 2.75, *FUNdaMENTALs Topic 9 — Hertz Contact: Line Contact*: <https://stuff.mit.edu/afs/athena/course/2/2.75/fundamentals/FUNdaMENTALs%20Book%20pdf/FUNdaMENTALs%20Topic%209.PDF>
5. KHK Gears, *Calculation of Gear Dimensions*: <https://khkgears.net/gear-knowledge/gear-technical-reference/calculation-gear-dimensions/>
6. Curà, Mura and Adamo, *Fatigue damage in spline couplings: numerical simulations and experimental validation*, Procedia Structural Integrity 5 (2017), open access, formula for mean spline tooth pressure: <https://www.sciencedirect.com/science/article/pii/S2452321617302536>
7. UPC Commons, spline force and bearing-area derivation: <https://upcommons.upc.edu/server/api/core/bitstreams/ce5c263a-fbb1-41b9-a8f5-3be59a0f4118/content>
8. OpenStax, *University Physics Volume 1*, work-energy equations: <https://openstax.org/books/university-physics-volume-1/pages/7-key-equations>

## 尚未关闭的外部校准缺口

- 螺栓：尚缺完整 VDI 2230 官方算例或有授权的商业软件交叉结果，尤其是 R3-R8 组合工况、热载荷和疲劳谱。
- 轴向受力螺纹：尚缺独立螺纹脱扣和疲劳实验/标准算例。
- 过盈：当前固定题只覆盖同材料实心轴；空心轴、异种材料、微动和装配温度仍缺独立数据。
- 赫兹：只覆盖外线接触；点接触可再加入公开球—平面算例。
- 蜗轮：当前只覆盖几何和运动学，不能为 DIN 3996 Method B 风格承载结果背书。
- 花键：当前只覆盖名义齿面平均压力，不能为 DIN 5480 / DIN 6892 完整校核背书。
- 缓冲块：当前只覆盖解析线性曲线；真实橡胶曲线、应变率和时域响应需要试验数据校准。
