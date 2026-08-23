# 软件质量冻结基线（2026-08-23）

- 日期：2026-08-23
- 性质：**冻结基线**。记录本轮优化开始前的仓库事实。
- 不是验收报告：本文件 **不声称** P0 已修复，也不声称本轮计划已落地。
- 对照来源：`docs/reports/2026-08-23-full-software-quality-review.md`、`docs/superpowers/specs/2026-08-23-software-quality-optimization-spec.md`、`docs/superpowers/plans/2026-08-23-software-quality-optimization-plan.md`

## 1. 仓库与运行时

本地核对于本 worktree：

| 项 | 实测值 | 证据 |
| --- | --- | --- |
| 分支 | `main` | `git rev-parse --abbrev-ref HEAD` |
| HEAD | `f0889e97ac9ce87fd842e82e225bc038d6b6a73e`（短 SHA `f0889e9`） | `git rev-parse HEAD` |
| 最近提交 | `merge: review-fix R1-R15 — bound calc domains, close UI contract gaps, restore test speed, defer matplotlib` | `git log -1 --oneline` |
| Python | `3.12.14` | `/Users/donghang/Documents/Codex/AI-assistant/.venv/bin/python` |
| PySide6 | `6.11.0` | 同 venv `import PySide6` |
| pytest | `9.0.2` | 同 venv `import pytest`；**未**写入 `requirements.txt` |
| 依赖声明 | `requirements.txt` 仅宽下限：`PySide6>=6.8.0`、`pyinstaller>=6.10.0`、`reportlab>=4.0`、`matplotlib>=3.8.0`、`openpyxl>=3.1` | 读文件 |
| lock / constraints | **不存在** | 仓库根无 `constraints.txt` / `poetry.lock` / `uv.lock` / `Pipfile.lock` |
| CI | **不存在** | 无 `.github/workflows` 或同类配置 |

本基线记录时，工作区另有大量未跟踪文档/计划以及部分已删除跟踪文件。那些文件 **不属于** 本冻结产物。

## 2. 测试基线

- 收集：`QT_QPA_PLATFORM=offscreen .../python -m pytest tests/ --collect-only -q`
- 结果：`909 tests collected in 0.39s`
- 全量执行：本基线 **未再跑** 全量 pytest。2026-08-23 review 记录当时为 `909 passed, 10 subtests passed`；此处只把收集数冻成 909，不把历史绿测复述成当前已复跑证明。

本基线之后若有 agent 补 P0 失败测试，预期收集数会上升，且修复前这些新测试应失败。那是后续提交的事，不是本文件的修复声明。

## 3. UI 最小尺寸策略

当前实现：

- 初始尺寸 `resize(1400, 860)`，最小尺寸 `setMinimumSize(900, 620)`：`app/ui/main_window.py:67-68`
- spec `UI-S01` 推荐最小支持 `1180×720`；若坚持 `900×620` 必须做折叠侧栏/overflow/响应式标题

**本程序选定策略（本轮）**：提高最小尺寸到 **1180×720**（spec 推荐）。本 worktree **不实现** 窗口改动；由负责窗口尺寸的 sibling agent 落地。README / 用户指南在该实现合并前仍描述当前代码中的 `900×620`，不得提前写成已生效。

## 4. P0 在基线仍开放

下列条目均已在本 worktree **打开对应源码行** 核对。结论：虚假 PASS / 错配材料合同在基线代码中仍在。**不要把本文件当成 P0 已关。**

### CALC-01 安全阈值只校验 `> 0`，可把危险工况变成 PASS

| 位置 | 打开后的事实 |
| --- | --- |
| `core/worm/calculator.py:465-472` | `required_contact_safety` / `required_root_safety` 走 `_positive()` |
| `core/spline/calculator.py:245-247` | `flank_safety_min` 走 `_positive()` |
| `core/bolt/calculator.py:563-567` | `thread_strip.safety_required` 走 `_positive()` |
| `core/bolt/tapped_axial_joint.py:281-284` | 同上 |
| UI 可编辑例 | `app/ui/pages/worm_gear_page.py:213-214` 目标齿面/齿根安全系数；`app/ui/pages/bolt_page.py:860-866` 脱扣安全系数要求 |

`_positive()` 只拒绝 `<= 0`。过盈滑移/应力下限已有 `>= 1.0` 二次判断（`core/interference/calculator.py:189-192`），螺栓/轴向螺纹/花键/蜗轮安全下限没有同等合同。

### CALC-02 载荷放大系数只校验正数，可系统性低估载荷

| 位置 | 打开后的事实 |
| --- | --- |
| `core/spline/calculator.py:242-243` | `application_factor_ka` 走 `_positive()` |
| `core/interference/calculator.py:179-182` | `application_factor_ka` 走 `_positive()` |
| `core/worm/calculator.py:102-105` | `operating.application_factor` 走 `_positive()` |
| `core/worm/calculator.py:448-456` | `dynamic_factor_kv` / `transverse_load_factor_kha` / `face_load_factor_khb` 走 `_positive()` |

语义为放大/分布的 `KA/KV/KH*` 仍可输入 `0 < x < 1`。

### CALC-03 非有限数未统一拒绝

| 位置 | 打开后的事实 |
| --- | --- |
| `core/hertz/calculator.py:19-24` | `_positive()` 无 `math.isfinite()` |
| `core/interference/calculator.py:19-24` | 同上 |
| `core/worm/calculator.py:25-30` | 同上 |
| `core/buffer/calculator.py:30-35` | 同上 |

螺栓/花键已有有限数转换，模块合同不一致。`allowable_p0_mpa=inf` 一类输入在基线仍可形成无限安全系数和 `overall_pass=True`（review 探针；本文件未重跑探针）。

### CALC-04 螺栓自动柔度接受负有效截面积

| 位置 | 打开后的事实 |
| --- | --- |
| `core/bolt/compliance_model.py:65-72` | cylinder：`A_p = π/4 (D_A² - d_h²)`，无 `D_A > d_h` |
| `core/bolt/compliance_model.py:97-104` | sleeve：无 `D_outer > D_inner` |
| `core/bolt/calculator.py:74-125` | `_resolve_compliance()` 接收自动模型 `delta_p` 后不再次要求正值 |
| `core/bolt/calculator.py:304-310` | 只拒绝 `phi_n >= 1`，不拒绝 `phi_n <= 0` |

### INPUT-01 轴向螺纹强度等级与 Rp0.2 未接线

| 位置 | 打开后的事实 |
| --- | --- |
| `app/ui/pages/bolt_tapped_axial_page.py:108-119` | 同时提供可编辑 `Rp0.2` 与 `grade` 下拉 `8.8/10.9/12.9` |
| `app/ui/pages/bolt_tapped_axial_page.py:630-656` | `_refresh_thread_section()` 只从 `d/p` 派生 `As/d2/d3` |
| 全页 `grade`/`Rp02` 引用 | 除 FieldSpec 与报告回显外，**没有** grade 变化写 Rp0.2 的 handler |

预设等级不是单一事实源；标签与真正参与强度校核的屈服值可以错配。

## 5. 模块 × 输入路径 × 输出消费者矩阵

Grep 核对 calculator 入口、UI 页、examples、文本报告、PDF helper。CLI 仅螺栓保留；其余模块没有独立 CLI。材料与标准库是占位页，不进入本表。

| 模块 | Calculator 入口 | UI 页 | 样例输入 | 文本报告 | 富 PDF helper |
| --- | --- | --- | --- | --- | --- |
| 螺栓连接 | `core/bolt/calculator.py` `calculate_vdi2230_core` | `app/ui/pages/bolt_page.py` | `examples/input_case_01.json`、`examples/input_case_02.json` | `BoltPage._build_report_lines`；CLI `src/vdi2230_tool.py` 写 JSON | `app/ui/report_pdf.py` `generate_bolt_report` |
| 轴向受力螺纹连接 | `core/bolt/tapped_axial_joint.py` `calculate_tapped_axial_joint` | `app/ui/pages/bolt_tapped_axial_page.py` | `examples/tapped_axial_joint_case_01.json`、`..._02.json` | `BoltTappedAxialPage._build_report_lines` → `_export_text_report` | `app/ui/report_pdf_tapped_axial.py` `generate_tapped_axial_report` |
| 过盈配合 | `core/interference/calculator.py` `calculate_interference_fit`（装配细节另有 `assembly.calculate_assembly_detail`） | `app/ui/pages/interference_fit_page.py` | `examples/interference_case_01.json`、`..._02.json` | `InterferenceFitPage._build_report_lines` | `app/ui/report_pdf_interference.py` `generate_interference_report` |
| 花键连接校核 | `core/spline/calculator.py` `calculate_spline_fit` | `app/ui/pages/spline_fit_page.py`（已有保存/加载：约 452-474、846-879） | `examples/spline_case_01.json`、`..._02.json` | `SplineFitPage._build_report_lines` | `app/ui/report_pdf_spline.py` `generate_spline_report` |
| 蜗轮蜗杆设计 | `core/worm/calculator.py` `calculate_worm_geometry` | `app/ui/pages/worm_gear_page.py` | `examples/worm_case_01.json`、`..._02.json`、`..._03.json` | `WormGearPage._write_text_report`（无 `_build_report_lines`） | `app/ui/report_pdf_worm.py` `generate_worm_report` |
| 赫兹应力 | `core/hertz/calculator.py` `calculate_hertz_contact` | `app/ui/pages/hertz_contact_page.py` | `examples/hertz_case_01.json`、`..._02.json` | `HertzContactPage._build_report_lines` | `app/ui/report_pdf_hertz.py` `generate_hertz_report` |
| 缓冲块吸能仿真 | `core/buffer/calculator.py` `calculate_buffer_energy` | `app/ui/pages/buffer_energy_page.py` | `examples/buffer_energy_input_conditions.json`；曲线 `buffer_energy_case_01.csv`、`buffer_energy_case_02.xlsx` | `BufferEnergyPage._build_report_lines` | `app/ui/report_pdf_buffer.py` `generate_buffer_report` |

共享出口：

- 输入保存/加载：`app/ui/input_condition_store.py`，默认目录 `saved_inputs/`
- 简化 TXT/DOCX/PDF 回退：`app/ui/report_export.py`
- 桌面入口：`app/main.py`；侧栏工厂：`app/ui/main_window.py:94-103`

## 6. 基线能力诚实口径（文档侧）

冻结时 README/用户指南已确认的漂移，由本轮文档提交修复，**不表示计算 P0 已关**：

1. README 写“保存/加载输入条件 JSON（花键模块除外）”，但花键页已实现保存/加载。
2. 用户指南仍写花键没有保存/加载/测试案例按钮；代码与 `tests/ui/test_spline_fit_page.py` 相反。
3. 赫兹页/帮助未在用户可见处明确“首版只支持外接触/正曲率”。core 公式是两正曲率倒数相加；`R=0` 表示平面；负半径被 `_positive(..., allow_zero=True)` 拒绝。内接触不在本版范围。
4. 侧栏有“缓冲块吸能仿真”，README 能力表未列。
5. 不得把本仓库写成已有 CI 或 lockfile。

## 7. 本基线明确不覆盖

- 未对照 DIN/VDI/ISO 原文重推公式。
- 未在真实桌面前景重做 7 模块点击验收。
- 未跑 Windows 打包 smoke。
- 未把 P0 探针固化为失败测试（由负责 core validation 的 agent 处理）。
- 未实现 FieldSchema、共享校验器或窗口最小尺寸代码。
