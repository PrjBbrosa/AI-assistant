# 载荷与附加载荷章节

本章节用于**输入需要过盈连接传递或抵抗的载荷**：传递扭矩 T_req、轴向力 F_req、径向力 F_r,req、弯矩 M_b,req。工况系数 KA（在"校核目标"章节）会把名义载荷放大到设计载荷，再进行能力与张口缝校核。

## 为什么要填这些

- **扭矩 T_req** 是最常见的需求；过盈连接靠摩擦力 × 半径生成扭矩容量。
- **轴向力 F_req** 用于校核抗窜动；与扭矩不同支线。
- **径向力 F_r,req** 与 **弯矩 M_b,req** 进入**张口缝校核**：它们会让接触面局部压力趋零，即使扭矩能力充足也可能丢夹紧。

填 0 表示该支线无需求；校核时该项按"无限安全"处理（只要 p_min ≥ 0 即可）。

## 输入 / 产出

**输入**：
- T_req（N·m）：服役阶段最大传递扭矩需求
- F_req（N）：抗轴向窜动需求
- F_r,req（N）：外部径向力需求
- M_b,req（N·m）：外部弯矩需求

**产出给下一步**：
- 设计载荷 = KA × 需求载荷
- 需求接触压力 p_req,T、p_req,Ax、p_req,comb、p_gap
- 与 p_min 比对得到 PASS / FAIL

## 核心校核公式（本工具实现）

```
T_design = KA · T_req                              [T: N·m]
F_design = KA · F_req                              [F: N]
F_r,design = KA · F_r,req                          [N]
M_b,design = KA · M_b,req                          [N·m]

扭矩容量      T_cap     = μ_T · p_min · π·d·L · (d/2) / 1000    [T: N·m, p: MPa, d,L: mm]
轴向容量      F_cap     = μ_Ax · p_min · π·d·L                  [F: N]
扭矩安全系数  S_torque  = T_cap / T_design
轴向安全系数  S_axial   = F_cap / F_design
联合作用使用度 u_comb   = sqrt( (T_design/T_cap)² + (F_design/F_cap)² )
联合作用安全系数 S_comb = 1 / u_comb

张口缝附加压强：
  p_radial  = F_r,design / (d · L)                              [F: N, d,L: mm → p: MPa]
  p_bending = 2.25 · M_b,design · 1000 / (d · L²)               [M: N·m, d,L: mm → p: MPa]
  p_gap     = p_radial + p_bending
PASS 判据：p_min ≥ p_gap
```

**说明**：`p_bending` 的系数 2.25 是取 QW = 0 的保守简化（不是 DIN 标准公式的完整形式）；真实应力分布会因轮毂刚度不同而在系数 1.5~3.0 之间变化，本工具取上界 2.25 保守估算。**Cannot verify against original DIN standard**。

## 联合作用校核的工程含义

扭矩与轴向力同时作用时，摩擦力矢量合成：
- 若只看扭矩能力通过、轴向能力通过，仍可能联合作用失败（两个分量都接近边界时，矢量合成超过 1/S_slip,min）。
- 本工具按 RSS（均方根）合成，是过盈配合的经典做法。
- 建议不要让任何单项使用度超过 0.8，给另一分量留余量。

## 张口缝的工程含义

**什么是张口缝**：径向力或弯矩让接触面某个角度上压力归零，甚至微观分离。一旦分离：
1. 摩擦力消失 → 扭矩 / 轴向容量局部失效
2. 端部应力集中 → 疲劳萌生
3. 加速 fretting corrosion

本工具的张口缝判据是"最小过盈端的平均接触压力 p_min 仍能覆盖附加压强 p_gap"。实际分布可能比平均值更严酷，建议留 20~30% 工程裕量。

## 常见坑

- **把反复载荷当稳态 T_req**：真实工况里 T 峰值可能远高于 T_rms；请按**峰值** × KA 填，不要按均值。
- **忘填径向力**：伞齿轮、链轮、皮带轮有显著径向分力；不填会让张口缝校核失效。
- **弯矩单位混淆**：本字段 N·m，不是 N·mm；填错会让 p_bending 差 1000 倍。
- **KA 重复计入**：设计载荷 = KA × 需求；不要在 T_req 里先乘 1.5 当冲击系数，再在 KA 里填 1.5，双重放大后虚高。

## 参考标准

- DIN 7190-1 联合作用与张口缝相关章节
- Niemann / Winter 过盈配合章节中关于 M_b / F_r 附加压强的保守近似

> Cannot verify against original DIN standard —— 本章节所述的张口缝公式系数 2.25、联合作用 RSS 合成方法来自公开教科书整理；**未查证 DIN 7190-1 原文**，故不给出精确节号 / 表号。
