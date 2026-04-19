# 脱扣目标安全系数（S_strip,req）

**一句话**：螺纹脱扣校核（R8 风格）要求的最小安全系数：实际 `S_strip = min(F_strip_B, F_strip_M) / F_bolt_max` 必须 ≥ 这个设计目标，否则脱扣校核判 FAIL。典型 1.25。

**怎么理解**：

螺纹脱扣校核比较"螺纹承载能力"与"螺栓最大拉力"：

```
S_strip = min(F_strip_B, F_strip_M) / F_bolt_max     [N / N → 无量纲]
```

其中：
- `F_strip_B`：外螺纹（螺栓侧）剪切承载力 [N]
- `F_strip_M`：内螺纹（螺母/壳体侧）剪切承载力 [N]
- `F_bolt_max = F_preload_max + FA_max`：服役最大螺栓拉力 [N]

S_strip,req 是**设计要求下限**。实际 S_strip ≥ S_strip,req 才算通过。`core/bolt/tapped_axial_joint.py:335` 实现判据。

## 典型值

| 使用场景 | 推荐 S_strip,req |
|---|---|
| 普通工业连接（室温、钢-钢） | 1.25 |
| 一般轻载（家电、钣金） | 1.1 – 1.2 |
| 重要连接（车辆底盘、压力容器） | 1.5 |
| 高温 / 高振动 / 腐蚀工况 | 1.5 – 2.0 |
| 安全关键（飞行器、起重） | 2.0 或更高（另走航空/起重规范） |

本工具 UI 默认 1.5（偏保守），也常见教材/VDI 取 1.25。具体值按行业规范（如 VDI 2230-1、ISO 898-2、DIN 6892 内部一致性）。

## 为什么需要 > 1

螺纹剪切面积 A_SB、A_SM 的计算使用经验系数 C1 ≈ 0.75、C3 ≈ 0.58；螺纹受载分布本身是非均匀的（开头几扣承载最大、末尾几乎不承载）；内螺纹剪切强度 τ_BM 本身是近似值（常取 `0.6·Rp0.2`）。这些近似叠加起来，S_strip,req 的 **0.25** 余量就是吸收这些不确定性。

更高的 S_strip,req（1.5、2.0）额外吸收：

- 温度变化引起的材料强度下降
- 螺纹加工质量偏差（粗糙度、配合）
- 装配过程引起的磕碰、腐蚀
- 长期振动带来的微滑移磨损

## 边界检查

`core/bolt/tapped_axial_joint.py:322-325` 用 `_positive(..., "thread_strip.safety_required")` 要求 > 0。实际常见值都 ≥ 1.0；填 < 1.0 时工具仍接受但相当于"只要不脱扣即可"，已丧失工程保守性。

## 与整体校核的关系

脱扣校核是**四项分项**之一：装配 von Mises、服役 von Mises、疲劳、脱扣。每一项独立判 PASS/FAIL，`overall_status` 综合：

- **任一 FAIL** → overall = `fail`
- **全部 PASS** → overall = `pass`
- **有项 `not_checked`（m_eff 留空）** → overall = `incomplete`

降低 S_strip,req 让脱扣"勉强过"，不会让整体过——其他三项仍按各自许用判决。**不要用调低 S_strip,req 换 PASS**，应检查 m_eff、τ_BM、螺栓强度等实际参数。

## 常见误用

- **S_strip,req < 1.0**：等同"只要没脱扣都算合格"，在工程上几乎无意义。
- **把 S_strip,req 提到 3+**：除非有明确安全规范要求，否则会造成过设计（更大螺纹规格、更深啮合）。先确认工况是否真正需要如此保守。
- **把"设计目标"和"实际安全系数"混淆**：UI 显示 `S = x.xx (要求: >= y.yy)`，左侧是实际、右侧是 S_strip,req。实际 > 要求才通过。
- **忽略内/外螺纹临界侧**：S_strip 取两者最小值；UI 会标出"临界侧：螺栓侧"或"壳体侧"，针对性改进（加深 m_eff、换材料、提高强度）才有效。

## 相关

- 有效啮合长度 m_eff → `terms/bolt_thread_engagement`
- 内/外螺纹剪切强度 τ_BM / τ_BS → `terms/bolt_thread_strip_tau`
- 脱扣"未校核"语义 → 本模块 `_section_thread_strip.md`

**出处**：VDI 2230-1:2015（R8 螺纹剪切相关章节）；ISO 898-2（螺母剪切强度）

> Cannot verify against original VDI / ISO standard —— 安全系数推荐值整理自公开工程文献；**未查证 VDI 2230-1:2015 / ISO 898-2 原文**，精确取值请以相应标准或行业规范为准。本工具判据实现于 `core/bolt/tapped_axial_joint.py:335`。
