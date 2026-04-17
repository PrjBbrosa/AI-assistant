# 蜗杆模块产线校核级修复工作总结（2026-04-17）

## 目标

把蜗杆模块从"几何预览工具"提升为"塑料蜗轮产线校核工具"，闭环 2026-04-16 产线评审提出的 22 个问题（W26-01 ~ W26-22）。

## 范围

- **覆盖材料副**：钢蜗杆 + 塑料蜗轮（PA66 / PA66+GF30 / POM / PA46 / PEEK）
- **不覆盖**：钢-青铜副、钢-钢副、Method C（FEA）
- **引用标准**：DIN 3975（几何）、DIN 3996 Method B（承载/热/寿命）、ISO 14521

## 执行方式

三波串行 + 每波内三路并行（core-engineer / ui-engineer / test-engineer），每波收尾由 codex:codex-rescue 审查把关，审查通过才 commit。

## 提交链

| Commit | 波次 | 内容 |
| --- | --- | --- |
| `251cdb1` | Wave 0 | 血洗 Bug：力分解公式、Method 联动、热容量独立公式、装饰参数清理 |
| `f5ca72c` | Wave 1 | 塑料工程完备：材料库、温湿度降额、DIN 3996 寿命/磨损、x1/x2 变位范围 |
| `39d9c13` | Wave 2 | 体验与报告：节流预览、AutoCalcCard 巡检、脏状态、PDF 对齐、examples 刷新 |

## 关键修复

### Wave 0（力学核心）

- **力分解公式纠正**：旧版 F_n 被放大约 10 倍。重新推导为
  - F_a2 = F_t2 · tan(γ + φ')
  - F_r = F_t2 · tan(α_n) / cos(γ)
  - F_n = F_t2 / (cos(α_n) · cos(γ))
  - η = tan(γ) / tan(γ + φ')
- 热容量公式从 "power_loss × fudge" 改为独立 DIN 3996 公式
- 齿根厚度按 π·m·cos(α_n)/2 修正
- Method 下拉、handedness、lubrication 接入 calculator（此前纯装饰）
- `geometry_consistent` 放宽：非标 q 不再直接 fail

### Wave 1（塑料工程）

- 新增 `core/worm/materials.py`：PlasticMaterial dataclass + PLASTIC_MATERIALS 库
- 温度降额：每 +10°C 乘材料系数；湿度降额：0~50% RH 线性插值（PA 系列明显，PEEK/POM 几乎无）
- DIN 3996 Method B 疲劳寿命 N_L = (σ_Hlim/σ_H)^6 · 1e7 循环
- 磨损速率 + 到 0.3 mm 寿命 + 滑动速度
- x1/x2 变位范围校核（-0.5 ~ 1.0）
- UI 温湿度字段 editingFinished 联动重新降额回填

### Wave 2（体验与报告）

- QTimer 300ms 合并按键，避免每次击键全量计算
- AutoCalcCard 样式覆盖所有派生字段（蜗杆/蜗轮 e·ν + 两路许用应力）
- `_mark_results_dirty / _fresh`：输入变更 → 导出按钮禁用 + "结果已过期"红字
- PDF 对齐新字段：力分解、peak/nominal、寿命磨损、温湿度工况
- 三个真实示例：PA66+GF30 / POM / PEEK，中心距与几何自洽、材料字段回归正确段

## Codex 审查记录

- **Wave 0 review**：发现 Unicode 智能引号 + 测试断言过弱，已修复
- **Wave 1 review**：发现 apply_derate 缺默认参数、GF30 湿度系数需收紧、UI 未按当前温湿度降额，已修复
- **Wave 2 review**：发现蜗轮侧 AutoCalcCard 切换未对称（蜗杆侧已做），已补对称处理

## 验收

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/ -q` → **426 passed**
- 新增测试：`tests/core/worm/test_materials.py`（6 例）、`tests/core/worm/test_examples.py`（3 例）、塑料材料自动填充 5 例、节流/脏状态 2 例
- 手算验证：m=4 / z1=1 / z2=40 / q=10 / T2=500 N·m 下
  - F_a = 962.8 N ✓
  - F_n = 6683.5 N ✓
  - η = 0.6493 ✓

## 未覆盖 / 后续事项

- Method C (FEA) 仅提示未实现
- 钢-青铜副材料库（本次明确排除）
- 示例 `worm_case_01.json` 载入后 z1="1"（整数字符串）而非 "1.0" —— calculator 无影响，UI 显示一致

## 文档链路

- Review 报告：`docs/reports/2026-04-16-worm-module-production-review.md`
- Spec：`docs/superpowers/specs/2026-04-17-worm-production-calibration-fix-design.md`
- Plan：`docs/superpowers/plans/2026-04-17-worm-production-calibration-fix.md`
- 本总结：`docs/reports/2026-04-17-worm-production-calibration-summary.md`
