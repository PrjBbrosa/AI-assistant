---
title: 蜗杆模块产线校核级修复
date: 2026-04-17
review_source: docs/reports/2026-04-16-worm-module-production-review.md
scope: 塑料蜗轮（POM、PA66+GF30、PA46、PEEK 等）+ 钢蜗杆
---

# 蜗杆模块产线校核级修复设计

## 1. 背景

基于 `docs/reports/2026-04-16-worm-module-production-review.md` 识别的 22 个问题（W26-01 ~ W26-22），将蜗杆模块从"几何预览工具"提升为"塑料蜗轮产线校核工具"。最关键的是：

- Wave 0 的 W26-01 力分解系统性错误 → F_n 高估 5×、F_a 高估 13×、σ_H 高估 2.24×，当前结果不能用于任何工程判定。
- Method A/B/C 下拉、热容量、handedness、lubrication 是装饰件/死输入，误导使用者。
- 测试用 `> 0` 判据，量级错误被放行。

## 2. 目标

- 计算结果可用于塑料蜗轮设计校核（PA66、POM、PA66+GF30、PA46、PEEK）。
- UI 不再有装饰性控件，所有输入都真正影响结果。
- 测试覆盖力学量级、自锁/效率/热负荷关键分支。
- 性能曲线、几何总览、PDF 报告呈现真实计算值。

## 3. 三波修复策略

### Wave 0 — 血洗 Bug（P0）

| ID | 问题 | 位置 |
|---|---|---|
| W26-01 | 力分解公式错误 | core/worm/calculator.py:363-371 |
| W26-02 | Method A/B/C 下拉无效 | worm_gear_page.py:41-45, calculator.py:488-502 |
| W26-03 | thermal_capacity_kw == power_loss_kw | calculator.py:174-176 |
| W26-04 | 齿根 s=1.25m / h=2.2m 硬编码 | calculator.py:383, 390-393 |
| W26-05 | geometry_consistent 把非标 q 误判 | calculator.py:185-186 |
| W26-06 | handedness / lubrication 是死输入 | worm_gear_page.py:97-158, calculator.py |
| W26-07 | 测试只检 `>0`，漏量级错 | tests/core/worm/test_calculator.py |
| W26-19 | 几何总览 widget 静态占位 | widgets/worm_geometry_overview.py |

**关键修复**：

- **力分解**（F_t 已知，从蜗轮切向力推其他）：
  ```
  F_t2 = 2·T2/d2
  F_a2 = F_t2 · tan(γ + φ')       # 不是 / tan(γ)
  F_r  = F_t2 · tan(α_n) / cos(γ) # 不是 / sin(γ)
  F_n  = F_t2 / (cos(α_n) · cos(γ)) # 不是 / sin(γ)
  ```
  其中 φ' = atan(μ / cos(α_n)) 为当量摩擦角。
- **Method B** 暂按 DIN 3996 简化版实现（Wave 1 展开）。Wave 0 先让下拉与计算联动：Method A 走手册系数、Method B 走 DIN 3996 简化、Method C 拒绝并提示未实现。
- **热容量**单独公式：Q_th = k·A·ΔT（k 塑料按 12-18 W/m²K，A 按箱体简化）。
- **齿根 s、h** 改按 DIN 3975 公式：s_Ft2 ≈ π·m_n·cos(α_n)/2，h_F ≈ m·(2.2 - x2)（初版），参数化。
- **handedness / lubrication**：要么删，要么进入 effective_coefficient_of_friction 和 F_r 方向计算。
- **几何总览**改为接受 `d1, d2, a, γ, z1, z2, direction` 动态绘制。

### Wave 1 — 塑料蜗轮工程完备（P1）

| ID | 问题 |
|---|---|
| W26-08 | 塑料材料库缺失（POM、PA46、PEEK + 温湿度降额） |
| W26-09 | DIN 3996 Method B 正确实现 |
| W26-10 | 自锁条件 / 导程角 UI 提示 |
| W26-11 | 变位系数 x1、x2 |
| W26-12 | 磨损寿命（DIN 3996 K9） |
| W26-13 | 塑料实测效率 vs 理论效率 |
| W26-14 | 输入校验边界扩充（m、q、z1 合理范围） |
| W26-20 | 性能曲线图 2/3 重复数据 |

**关键内容**：

- 新建 `core/worm/materials.py`：PA66/PA66+GF30/POM/PA46/PEEK 的 σ_Hlim、σ_Flim、E、ν、温度降额曲线（-20~+80℃）、湿度吸水降额（PA 系列）。
- DIN 3996 Method B：接触应力 σ_HM、齿根应力 σ_FM、寿命 N_L、磨损 J 的手册系数实装。
- UI：效率卡新增 "γ=X° / φ'=Y° / 自锁=是/否" 文字行；性能曲线第 3 张图改为 "油温升" 或 "磨损速率"。

### Wave 2 — 体验与报告（P2）

| ID | 问题 |
|---|---|
| W26-15 | PDF 报告字段对齐真实计算 |
| W26-16 | 输入条件保存/加载 |
| W26-17 | AutoCalcCard 样式一致性 |
| W26-18 | 章节脏状态提示 |
| W26-21 | derived_geometry_preview 每敲击全量算 |
| W26-22 | examples/ JSON 用例刷新 |

## 4. 实施方法

### 4.1 并行划分（每波 3 路）

| Agent | 文件域 | 禁止跨界 |
|---|---|---|
| core-engineer | `core/worm/*.py` | 不改 UI |
| ui-engineer | `app/ui/pages/worm_gear_page.py`, `app/ui/widgets/worm_*.py` | 不改 core |
| test-engineer | `tests/core/worm/*.py`, `tests/ui/test_worm_page.py` | 不改产品代码 |

主会话在波内：并行 dispatch 3 个 agent；波结束汇总后 dispatch codex review；review 通过后 commit 并进入下一波。

### 4.2 Codex review 判据（每波）

- 无力学量级错（手算对比 1 组典型 Case）
- `QT_QPA_PLATFORM=offscreen pytest tests/ -v` 全通过
- UI 任何输入变更即 disable 导出按钮
- 装饰性控件全部落实到计算
- 符合 CLAUDE.md 编码规范（中文 UI、AutoCalcCard 样式、_positive/_require 校验）

### 4.3 迭代循环

```
Wave N 启动 →
  3 agents parallel →
  主会话汇总 →
  codex review →
    ├─ 通过 → git commit → Wave N+1
    └─ 有问题 → 分派对应 agent 修 → re-review
```

## 5. 验证

### 5.1 手算对照（Wave 0 结束）

Case：m=4mm, z1=1, z2=40, q=10, α_n=20°, μ=0.05, T2=500N·m

- d2 = 160 mm, F_t2 = 6250 N
- γ = atan(1/10) = 5.71°, φ' = atan(0.05/cos20°) = 3.05°
- F_a2 = F_t2 · tan(γ+φ') = 6250 · tan(8.76°) = 963 N
- F_r = F_t2 · tan(20°)/cos(5.71°) = 6250·0.364/0.995 = 2286 N
- F_n = F_t2 / (cos(20°)·cos(5.71°)) = 6250/0.937 = 6670 N
- η ≈ tan(γ)/tan(γ+φ') = 0.658

UI 和 core 必须复现这些数（rel 1e-3）。

### 5.2 回归

- 69 个旧测试全过
- 新增 ≥ 15 个测试：力分解、自锁、效率、热负荷、塑料材料降额、Method B 分支

## 6. 风险与回避

| 风险 | 对策 |
|---|---|
| DIN 3996 Method B 复杂度高，Wave 1 单波难完成 | Method B 先做塑料-钢副；钢-钢副延后 |
| 塑料材料降额数据源不统一 | 标注每个 σlim 的来源（DIN 3996、POM 厂商 PDS、文献） |
| Codex review 反复不通过阻塞进度 | 每轮 review 最多 2 次；第 3 次仍不通过则升级人工 review |
| 并行 agent 编辑冲突 | 严格按文件域划分，agent 不允许跨域 |

## 7. 交付物

- `core/worm/calculator.py` 修正力学 + Method B
- `core/worm/materials.py` 新建塑料材料库
- `app/ui/pages/worm_gear_page.py` 无装饰控件
- `app/ui/widgets/worm_geometry_overview.py` 动态几何
- `app/ui/widgets/worm_performance_curve.py` 三图不同源
- `tests/core/worm/test_calculator.py` 覆盖力学量级与分支
- `tests/ui/test_worm_page.py` 覆盖脏状态与联动
- `examples/worm_case_*.json` 更新为产线典型案例
- 3 次 Codex review 通过记录（写入 `docs/reports/2026-04-17-worm-fix-wave-N-review.md`）

## 8. 不做的事

- 非塑料蜗轮材料库（钢-青铜副）不做
- 多工况/谱载不做
- 有限元/CAE 耦合不做
- 三维几何参数化（齿廓渐开线精确曲线）不做
