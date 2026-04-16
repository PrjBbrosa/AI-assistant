# 轴向受力螺纹连接 — 修复执行计划

- 日期：2026-04-16
- 关联报告：`docs/reports/2026-04-16-tapped-axial-joint-review.md`
- 基线：`main @ 545e8f8`
- 优先级目标：发版前清除 1 个 critical + 2 个 high + 1 个 medium 发现

## 总体策略

按"计算核心 → UI 链路 → 报告导出"的顺序逐条修复，每条都走 TDD：先加失败测试 → 再改实现 → 观察测试通过。修复不要相互耦合，保持每个 commit 只解决一个发现，方便回滚。

## Step 1 — 修复疲劳 Goodman 下限（critical）

**对应发现**：§3.1

### 目标
删除对 Goodman 因子的 `max(0.1, …)` 人为下限，保证在高平均应力场景下 `fatigue_ok` 按真实公式判断，并在原始因子 `<= 0` 时直接判为不通过。

### 改动点
- `core/bolt/tapped_axial_joint.py:244-248`
  - 移除 `max(0.1, ...)`；
  - 增加保护：当原始 Goodman 因子 `<= 0` 时，设 `goodman_factor=0.0`、`fatigue_ok=False`，并在 `messages` 里追加"平均应力已超出 Goodman 折减下限，疲劳不通过"。
- 结果字典里保留**原始 Goodman 因子**（不经下限裁剪），字段名可用 `goodman_factor_raw`，便于用户排查。

### 新增测试
`tests/core/bolt/test_tapped_axial_joint.py` 增加：

```python
def test_high_mean_stress_fails_fatigue():
    data = _base_input()
    data["fastener"].update({"d": 10.0, "p": 1.5, "Rp02": 640.0})
    data["tightening"].update({
        "method": "angle",
        "mu_thread": 0.05,
        "mu_bearing": 0.05,
        "alpha_A": 1.0,
    })
    data["loads"]["F_preload_min_N"] = 33000.0
    result = calculate_tapped_axial_joint(data)
    assert result["checks"]["fatigue_ok"] is False
    assert any("Goodman" in m or "疲劳" in m for m in result["messages"])
```

### 验收标准
- 新测试通过；
- 既有测试全绿（346 passed 或对应数目）；
- 手动回归：用 `examples/tapped_axial_joint_case_01.json`，该用例仍然通过（不会把正常工况误判）。

---

## Step 2 — `As/d2/d3` 自动派生 + 全局缓存失效

**对应发现**：§3.2 + §3.4（合并实现，因为共享 UI 状态管理）

### 目标
- 让 `As/d2/d3` 不再允许与 `d/p` 同时独立存在；
- 任一输入变更、加载输入、清空页面时立即失效缓存，禁用"导出报告"按钮；
- 报告导出前二次校验 payload 一致性。

### 改动点

#### 2.1 Calculator 层
`core/bolt/tapped_axial_joint.py`：
- 新建内部函数 `_derive_thread_section(d_mm, p_mm) -> dict`，按 ISO 898-1 附录 A 公式输出 `As, d2, d3`；
- 在 `calculate_tapped_axial_joint` 入口，如果 `fastener` 里同时有 `As/d2/d3` 和 `d/p`，按容差 (相对误差 1%) 校验一致性；不一致抛 `InputError("As/d2/d3 与 d/p 不一致，请清空或重新填写")`。

#### 2.2 UI 层
`app/ui/pages/bolt_tapped_axial_page.py`：
- `As`, `d2`, `d3` 的 FieldSpec 改 `AutoCalcCard`：`setReadOnly(True)` + `card.setObjectName("AutoCalcCard")`；
- 监听 `d`、`p` 的 `textChanged`，自动重算并填充 As/d2/d3；
- `_on_inputs_changed`、`_apply_input_data`、`_clear` 三处都统一清空 `_last_payload` 和 `_last_result`；
- "导出报告"按钮启用状态绑定到缓存：`btn_export.setEnabled(self._last_result is not None)`；
- 导出前再比一次 `build_payload() == self._last_payload`，不一致时弹 `QMessageBox.warning` 并中止。

### 新增/修改测试

`tests/ui/test_bolt_tapped_axial_page.py`：
```python
def test_change_d_autofills_as_d2_d3(app):
    page = BoltTappedAxialPage()
    page._widgets["fastener.d"].setText("10")
    page._widgets["fastener.p"].setText("1.5")
    app.processEvents()
    assert float(page._widgets["fastener.As"].text()) == pytest.approx(58.0, rel=1e-2)

def test_modifying_inputs_invalidates_export(app):
    page = BoltTappedAxialPage()
    page._on_calculate()
    assert page.btn_save.isEnabled()
    page._widgets["fastener.d"].setText("12")
    app.processEvents()
    assert not page.btn_save.isEnabled()

def test_clear_invalidates_cache(app):
    page = BoltTappedAxialPage()
    page._on_calculate()
    page._clear()
    assert page._last_result is None
    assert not page.btn_save.isEnabled()
```

`tests/core/bolt/test_tapped_axial_joint.py`：
```python
def test_as_d2_d3_inconsistent_with_d_p_raises():
    data = _base_input()
    data["fastener"].update({"d": 10.0, "p": 1.5, "As": 36.6, "d2": 7.188, "d3": 6.466})
    with pytest.raises(InputError, match="不一致"):
        calculate_tapped_axial_joint(data)
```

### 验收标准
- 新测试通过；
- `examples/tapped_axial_joint_case_01.json` 和 `case_02.json` 加载后仍能通过计算（因为示例 JSON 的 As/d2/d3 与 d/p 自洽）；
- 手工改 UI `d`，As/d2/d3 跟随刷新，导出按钮灰掉直到重新计算。

---

## Step 3 — 螺纹脱扣未校核的语义重定义

**对应发现**：§3.3

### 目标
- 把 `thread_strip` 拆为三态：`pass / fail / not_checked`；
- `overall_pass` 在 `not_checked` 存在时保持 `False` 或 `None`，并在 UI 上显式提示。

### 改动点

#### 3.1 Calculator 层
`core/bolt/tapped_axial_joint.py:257-350`：
```python
if thread_strip_input.get("m_eff") is None:
    thread_strip_result = {
        "status": "not_checked",
        "reason": "未提供啮合长度 m_eff",
    }
    thread_strip_ok = None  # 之前是 True
else:
    thread_strip_result = {...}  # 现有实现
    thread_strip_ok = thread_strip_result["ok"]
```
然后：
```python
active_checks = {k: v for k, v in checks_out.items() if v is not None}
overall_pass = bool(active_checks) and all(active_checks.values())
has_not_checked = any(v is None for v in checks_out.values())
```

结果字典里新增字段：
- `overall_status`: `"pass" | "fail" | "incomplete"`；
- `thread_strip.status`: `"pass" | "fail" | "not_checked"`。

#### 3.2 UI 层
- 结果页对 `thread_strip.status == "not_checked"` 显示橙色"未校核"徽标，不是绿色 PASS；
- 总体结论 `incomplete` 状态显示黄色 "CHECK INCOMPLETE"，不是绿色 PASS；
- `m_eff` 字段 hint 加"建议填入啮合长度以完成脱扣校核"。

#### 3.3 报告导出
- 文本/PDF 报告里，脱扣章节标题加状态后缀：`"螺纹脱扣校核 (未校核)"`；
- 总体结论段落也反映 `incomplete`。

### 新增测试
```python
def test_missing_m_eff_produces_incomplete_not_pass():
    data = _base_input()
    data.pop("thread_strip", None)
    result = calculate_tapped_axial_joint(data)
    assert result["thread_strip"]["status"] == "not_checked"
    assert result["overall_status"] == "incomplete"
    assert result["overall_pass"] is False

def test_m_eff_provided_runs_strip_check():
    data = _base_input()
    data.setdefault("thread_strip", {})["m_eff"] = 8.0
    result = calculate_tapped_axial_joint(data)
    assert result["thread_strip"]["status"] in ("pass", "fail")
```

UI 层再补一条 badge 颜色/徽标的断言。

### 验收标准
- 新测试通过；
- 默认示例（未填 m_eff）导出报告时总体结论显示"校核不完整"，不是"通过"。

---

## Step 4 — 报告导出的 payload 一致性校验

**对应发现**：§3.4（与 Step 2 合并）

### 目标
- 确保报告始终对应当前表单；
- 任何输入变更后，导出按钮不可用，直到重新计算。

改动点见 Step 2（`btn_save.setEnabled`、`_on_inputs_changed` 失效缓存、导出前 deep-equal 校验）。

### 额外的单独测试
```python
def test_export_requires_matching_payload(app, tmp_path):
    page = BoltTappedAxialPage()
    page._on_calculate()
    page._widgets["fastener.d"].setText("12")
    app.processEvents()
    out = tmp_path / "report.txt"
    with pytest.raises(RuntimeError, match="输入已变更"):
        page._export_report(out, fmt="text")
```

（实现可以改成 QMessageBox 警告并 return，而非抛异常；测试断言 out 不存在即可。）

---

## Step 5 — 回归验证

### 5.1 测试套件
```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v
```
目标：全绿，无新增 warning。

### 5.2 手工回归脚本
按顺序跑：

1. 启动桌面 `python3 app/main.py`；
2. 切到"轴向受力螺纹连接"；
3. 加载"测试案例 1"，确认总体通过，导出 PDF；
4. 把 `d` 改成 10，确认 As/d2/d3 自动刷新、导出按钮灰掉；
5. 点"计算"后重新导出；
6. 清空 `thread_strip.m_eff` 输入（若已填），重新计算，确认总体显示"校核不完整"；
7. 用 §3.1 复现参数（d=10, p=1.5, Rp02=640, F_preload_min=33 kN, ...）计算，确认疲劳判定为 FAIL。

## Step 6 — 文档更新

- `CLAUDE.md` 轴向受力螺纹连接模块的"当前已知限制"段补：
  - "默认未强制 `m_eff`，当未提供时脱扣校核标记为未校核而非通过"；
- `docs/user-guide.md` 轴向螺纹连接章节补：
  - "修改规格后 As/d2/d3 自动重算，若报告按钮变灰请重新计算"；
- 本计划执行完毕后，在 `docs/reports/` 下追加 `2026-04-XX-tapped-axial-joint-fix-followup.md`，记录实际修复情况、任何偏离计划的决策、以及后续遗留项。

## 风险与回退

- §3.3 的脱扣三态会改变 result 字典结构，UI 和报告都要同步改；遗漏会导致下游 KeyError。建议每个 commit 自己跑 UI 测试；
- §3.2 的 As/d2/d3 自动派生会改变现有示例 JSON 的"源真值"。需要确认两个 example JSON 仍然与公式结果自洽（相对误差 <= 1%），否则一起更新示例；
- 若时间紧迫，允许以"特性开关"的方式先落 §3.1 + §3.3 + §3.4，把 §3.2 的自动派生推迟一轮，但必须在 UI 加显式红字提示"请手动保证 As/d2/d3 与 d/p 一致"，且在 PR 描述里声明这是临时方案。

## 提交建议

每个 Step 一个独立提交：
1. `fix(bolt): remove non-conservative fatigue Goodman floor`
2. `refactor(bolt-ui): auto-derive As/d2/d3 and invalidate cache on input change`
3. `fix(bolt): distinguish thread-strip not_checked from pass`
4. `fix(bolt-ui): require matching payload before report export`（若未并入 Step 2）
5. `docs(bolt): update tapped axial joint limitations and user guide`
