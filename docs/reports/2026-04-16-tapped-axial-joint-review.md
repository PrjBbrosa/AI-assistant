# 轴向受力螺纹连接模块 — 代码审查报告

- 日期：2026-04-16
- 审查者：Codex GPT-5.4（adversarial-review 模式）
- 主会话：Claude Code（Opus 4.6）
- 审查基线：`72cc1df`（模块引入前）
- 目标分支：`main`（已同步至 `origin/main` `545e8f8`）
- Job ID：`b035qrvzh`

## 1. 审查范围

仅聚焦"轴向受力螺纹连接"（tapped axial threaded joint）模块，其他模块的差异（worm、字体系统、主题 css、spline、hertz、report_export 等）只扫描边界耦合，不做主评。

已扫描文件：

- `core/bolt/tapped_axial_joint.py`（核心计算）
- `core/bolt/__init__.py`（导出）
- `app/ui/pages/bolt_tapped_axial_page.py`（UI 页面）
- `app/ui/report_export.py` 与 `app/ui/report_pdf_tapped_axial.py`（文本/PDF 报告分支）
- `examples/tapped_axial_joint_case_01.json` / `case_02.json`
- `tests/core/bolt/test_tapped_axial_joint.py`
- `tests/ui/test_bolt_tapped_axial_page.py`、`test_bolt_tapped_axial_results.py`、`test_bolt_tapped_axial_optional_pdf.py`
- 参考设计文档 `docs/superpowers/specs/2026-04-04-tapped-axial-joint-v2-design.md`

Codex 还运行了多轮 Python 代码实测（含 `QT_QPA_PLATFORM=offscreen` 的 UI 验证）来复现问题。

## 2. 总体裁定

`needs-attention` — **不建议发版**。

模块整体设计思路清晰（与 VDI 2230 夹紧连接并列、不复用 clamped-parts 主链），PDF 缺依赖时的降级路径可用，外部模块对它的耦合风险也已排除。但模块内部存在 4 个实质性风险，其中 1 个为 **critical**（疲劳判定非保守），其余 3 个会导致 UI/报告层输出与工程意图不一致的结果，均需要在发版前修复。

## 3. 关键发现

### 3.1 🔴 critical — Goodman 折减被 0.1 下限抬高，导致高平均应力工况仍可能判定疲劳通过

**位置**：`core/bolt/tapped_axial_joint.py:244-248`

**现象**：
```python
goodman_factor = max(0.1, ...)
```
当原始 Goodman 因子低于 `0.1` 时，`max(0.1, x)` 会把许用应力幅**反向抬高**，使疲劳许用比公式结果更宽松。

**复现**：
- 输入：`d=10, p=1.5, Rp02=640, F_preload_min=33 kN, alpha_A=1, mu_thread=mu_bearing=0.05, tightening_method=angle`
- 原始 Goodman 因子 ≈ `0.0105`
- 代码强制为 `0.1` → `fatigue_ok=True`，全部分项仍为绿灯

**工程影响**：
高预紧/高平均应力工况下，本应触发疲劳不通过的连接会被错判为通过。这是非保守判定，对现场失效风险有直接影响。

**建议修法**：
- 去掉 `max(0.1, ...)` 下限；
- 当原始 Goodman 因子 `<= 0` 时直接判 `fatigue_ok=False`，并在 `messages` 里说明原因；
- 补一条"高平均应力"回归测试，断言在上述输入下 `fatigue_ok=False`。

---

### 3.2 🟠 high — 页面把旧的 As/d2/d3 与新的 d/p 混用，产生静默错误结果

**位置**：`app/ui/pages/bolt_tapped_axial_page.py:417-459`

**现象**：
- `_build_payload()` 无条件把 `fastener.As/d2/d3`（若非空）送入计算；
- `_apply_input_data()` 会把示例或历史输入里的这些值完整回填到 UI；
- 示例 JSON 本身就带 `As/d2/d3`。
- 用户修改 `d` 或 `p` 时，页面不联动清空或重算 `As/d2/d3`。

**复现**：
- 把 `examples/tapped_axial_joint_case_01.json` 的 `d` 从 8 改到 10；
- 计算后 `sigma_ASV` 与内螺纹面积确实切到新规格；
- 但 `As/d2/d3` 仍保持旧值 `36.6 / 7.188 / 6.466`；
- 结果链条变成"新规格 + 旧截面"的混算。

**工程影响**：
任何来自示例/保存 JSON 的输入，一旦用户改规格，截面就会"残留"，结果看似计算成功但物理不一致。对一个以日常工程验算为目标的工具，这是容易误伤用户的静默错误。

**建议修法**（二选一或叠加）：
1. 把 `As/d2/d3` 改成只读 `AutoCalcCard` 字段，始终随 `d/p` 自动重算；
2. 如果保留手工覆盖入口，在 `_on_calculate` 前对三者进行"与当前 d/p 是否一致"的校验，超过容差直接阻断计算并提示用户。

---

### 3.3 🟠 high — 未提供啮合长度时，螺纹脱扣被当作"通过"并计入 overall_pass

**位置**：`core/bolt/tapped_axial_joint.py:257-350`

**现象**：
- 当 `thread_strip.m_eff` 为空时，代码把脱扣校核标记为 `inactive`；
- 但同时把 `thread_strip_ok` 设为 `True`；
- 末尾 `overall_pass = all(checks_out.values())` 仍返回 `True`。

**UI 默认**：
`m_eff` 为空。**最常见路径**是：tapped joint 完全未做脱扣校核，但绿灯通过。

**工程影响**：
对螺纹孔连接而言，脱扣是主要失效模式之一而非次要校核项。"未校核"被等同于"通过"属于严重的语义错位。

**建议修法**：
- 把 inactive 状态拆为独立的第三态（例如 `thread_strip_status = "not_checked"`），不要把 `thread_strip_ok` 置 `True`；
- `overall_pass` 的合成逻辑改为 `all(check == "pass" for check in active_checks) and no_missing_required_checks`；
- 更稳妥的做法：对 tapped joint 强制要求 `m_eff` 和对手件强度输入；
- UI 在结果页明确显示"螺纹脱扣未校核"徽标，而不是默认绿色 PASS。

---

### 3.4 🟡 medium — 报告导出会在当前输入已改变后继续输出旧计算结果

**位置**：`app/ui/pages/bolt_tapped_axial_page.py:658-699`

**现象**：
- 导出文本/PDF 只检查 `_last_result is None`；
- 页面在字段修改、加载输入、执行 `_clear()` 后都未失效 `_last_payload` / `_last_result`；
- `_clear()` 把状态重置为"等待计算"，进一步掩盖缓存仍存在。

**复现**：
- 用户执行一次计算；
- 修改任意参数或点"清空参数"；
- 点"导出报告"，仍能输出上一次的结果。

**工程影响**：
报告与当前可见输入不一致，属于合规性与质量追溯风险，尤其在把 PDF 报告作为签发凭据时更严重。

**建议修法**：
- `_on_inputs_changed` / `_apply_input_data` / `_clear` 都立即将 `_last_payload` 和 `_last_result` 置为 `None`；
- 导出前二次校验：重新构建当前 payload，与 `_last_payload` 深比较，不一致时要求重新计算；
- 导出按钮根据缓存有效性启用/禁用，视觉上杜绝误点。

## 4. 扫描范围外的观察

- worm / theme / spline / hertz / report_export 未对本模块构成阻塞耦合；
- PDF 缺 reportlab 依赖时的文本回退路径看起来可用，但回退后仍受 §3.4 的旧结果问题影响。

## 5. 建议修复顺序

1. §3.1 fatigue Goodman 分支（critical，非保守判定）；
2. §3.2 As/d2/d3 自动派生 + 缓存统一失效（与 §3.4 合并实现）；
3. §3.3 脱扣未校核的语义重定义；
4. §3.4 报告缓存失效与 payload 一致性校验；
5. 回归测试：高均值疲劳、规格变更后的几何一致性、输入变更后的导出失效三条失败路径。

详细步骤见配套执行计划 `docs/plans/2026-04-16-tapped-axial-joint-fixes.md`。

## 6. 附录

### 6.1 审查元数据

| 项 | 值 |
|----|-----|
| 审查方式 | `codex-companion adversarial-review --scope branch --base 72cc1df` |
| 审查时长 | 后台异步，数分钟 |
| Codex 模型 | GPT-5.4 |
| 输出文件 | `/tmp/.../tasks/b035qrvzh.output` |

### 6.2 相关设计文档

- `docs/superpowers/specs/2026-03-25-tapped-axial-joint-design.md`
- `docs/superpowers/specs/2026-04-04-tapped-axial-joint-v2-design.md`
- `docs/superpowers/plans/2026-03-25-tapped-axial-threaded-joint.md`
