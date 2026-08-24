# Cloud Porcelain 前景验收记录

- 日期：2026-08-25
- 分支：`codex/cloud-porcelain-visual-system`
- 本报告对应 Wave 8（全量验证 / 合同再冻结 / 文档归档）
- 产品结论：**PARTIAL / NEEDS FOREGROUND ACCEPTANCE**
- 不得按 spec §16 声称“达到云瓷 HTML 渲染效果”或项目 COMPLETE。

各节证据独立记录，互不替代：focused 绿不能代替七模块 UI；七模块 UI 不能代替全量；offscreen 不能代替 macOS 前景；macOS 不能代替 Windows；parity 数字不能代替用户截图签字。

---

## 1. 实现状态（W0–W7 commits）

分支无 upstream，以下 SHA 均为本地提交，未 push。`git diff --name-only -- core` 在 W8 验证时为空。

| Wave | 状态（该 wave 当时记录） | SHA | 说明 |
|---|---|---|---|
| W0 基线冻结 | COMPLETE | `76ddb3c406d178027602ba4c92b624bc2fcc23a3` | HEAD 当时为 `feat: add consistent beginner guides`。focused 34 passed；全量 1214 passed / 32 subtests / 0 failed。产品树无 W0 写入。 |
| W1 token + 静态画布 | COMPLETE | `61d10cba0f92a75af5930800db60084ac5e8966e` `785010973db714f0d36e50e62706e0ea18591b12` | `refactor: centralize cloud-porcelain design tokens`；`feat: add static cloud canvas and glass surfaces` |
| W2 主 shell | COMPLETE | `50b1980a60ae90886bfc616e036baf83d223ae91` | `feat: restyle main shell with floating sidebar` |
| W3 章节头 / overflow | COMPLETE | `5eb606bf790c780d37a40547c466952364a15dee` | `feat: unify chapter header navigation and action overflow` |
| W4 控件 / popup chrome | COMPLETE | `127ba1666366488fe55516e2425da31fe92280c9` | `feat: apply cloud controls and popup chrome`。`help_button.py` 已在此提交，W8 工作区不再 dirty。 |
| W5A 四模块表面 | COMPLETE | `4b9730ecc0a61990c6f0f8d264df9749404fe342` | `style: migrate hertz tapped spline and interference surfaces` |
| W5B 蜗轮/缓冲/螺栓图 | COMPLETE | `ac2e5d9ab34c4c778f7cfb6a368b235ae8326504` | `style: migrate worm buffer and bolt diagrams` |
| W6 状态矩阵测试 | COMPLETE | `4a57f22fa6f0afabee0f33a33ebed4510f6bb9ef` | `test: cover stale error dpi and render parity states` |
| W7 几何 / HTML parity | PARTIAL | `07ab1a2692f13317cc923000051af3eabb08e97e` | `test: add cloud-porcelain render geometry matrix`。Windows 与用户截图签字仍未验证，故该 wave 不得 COMPLETE。 |
| W8 本报告 | 验证 + 文档 | 见第 9 节 | 本提交只归档验收文档与已批准 spec/plan/HTML。 |
| W8+ P1 follow-up | PARTIAL | 见第 9 节本提交 | 独立 status badge objectName；轴向螺纹结果章 QScrollArea。Windows / 用户签字仍未验证。 |

W8 未改 `core/**`。未放宽测试。未把项目标为 COMPLETE。

独立 review P1.1 / P1.2 已在产品页处理：`badge_object_name` 把 `incomplete` → `IncompleteBadge`、`reference_only` → `RefBadge`、`not_checked`/`wait` → `WaitBadge`（未知值不得映射为 PassBadge）；轴向螺纹结果章用 `QScrollArea` 包住，避免 `ModelScopeBanner` 画进章节导航。这不改变 calculator 状态，也不代替第 5、6 节前景。

---

## 2. Focused tests

命令（cwd=`/Users/donghang/Documents/Codex/AI-assistant`，`.venv/bin/python`，`TMPDIR=/tmp QT_QPA_PLATFORM=offscreen PYTHONPATH=.`）：

```
git diff --check
rg -n 'QColor\(|#[0-9A-Fa-f]{6}' app/ui/pages app/ui/widgets --glob '*.py'

python -m pytest \
  tests/ui/test_design_tokens.py \
  tests/ui/test_cloud_canvas.py \
  tests/ui/test_cloud_shell_geometry.py \
  tests/ui/test_cloud_porcelain_render_contract.py \
  tests/ui/test_theme.py \
  tests/ui/test_main_window.py \
  tests/ui/test_base_chapter_page.py \
  tests/ui/test_module_workflow_smoke.py \
  tests/ui/test_render_exception_guard.py \
  tests/ui/test_export_dirty_tracking.py \
  tests/ui/test_field_mapping_contract.py \
  tests/ui/test_result_source_contract.py \
  tests/ui/test_stale_and_status_matrix.py \
  tests/ui/test_action_overflow.py \
  tests/ui/test_chapter_delegate.py \
  tests/ui/test_cloud_component_gallery.py -q --tb=line
```

原始输出：`/tmp/cloud-porcelain-baseline/w8-focused.txt`

| 项 | 实测 |
|---|---|
| `git diff --check` | exit 0 |
| 硬编码色 grep | 7 行，均为白墨/白填或 token 变量包装的 `QColor(...)`，不是旧暖米色 `#FBF8F3` / `#EEE7DE` / `#D97757` |
| pytest | **172 passed** in 13.56s |
| failed / skipped | 0 / 0 |
| EXIT | 0 |

本计数只覆盖上列 16 个测试文件，不能代替第 3、4 节。

---

## 3. 七模块 UI tests

命令：

```
python -m pytest \
  tests/ui/test_bolt_page.py \
  tests/ui/test_bolt_tapped_axial_page.py \
  tests/ui/test_bolt_tapped_axial_results.py \
  tests/ui/test_interference_page.py \
  tests/ui/test_spline_fit_page.py \
  tests/ui/test_worm_page.py \
  tests/ui/test_worm_stress_curve.py \
  tests/ui/test_hertz_page.py \
  tests/ui/test_buffer_energy_page.py -q --tb=line
```

原始输出：`/tmp/cloud-porcelain-baseline/w8-modules.txt`

| 项 | 实测 |
|---|---|
| pytest | **249 passed, 27 subtests passed** in 7.23s |
| failed / skipped | 0 / 0 |
| EXIT | 0 |

这是 offscreen UI 页面测试，不是 macOS/Windows 前景，也不是用户视觉签字。

---

## 4. 全量 tests

命令：

```
TMPDIR=/tmp QT_QPA_PLATFORM=offscreen PYTHONPATH=. \
  .venv/bin/python -m pytest tests/ -q --tb=line
```

原始输出：`/tmp/cloud-porcelain-baseline/w8-full.txt`

| 项 | W0 基线 | W8 实测 |
|---|---|---|
| passed | 1214 | **1349** |
| subtests passed | 32 | **32** |
| failed | 0 | **0** |
| skipped | 未报告 | 未报告（pytest 摘要未列出 skipped） |
| 时长 | 34.78s | 49.48s |
| EXIT | 0 | 0 |

相对 W0 多 135 个 passed，来自 W1–W7 新增视觉/状态/几何测试，不是把旧断言放宽。本计数不能代替第 5、6 节前景。

---

## 5. macOS 前景（实际拍到 vs 未验证）

本环境是 macOS。W8 **没有重跑** cocoa 捕获；下列文件是 W0 / W2 / W7 已存在的真实抓取，不是本 wave 新拍。

### 已捕获

W0 cocoa（Studio Display 2560×1440，dpr=2.0）：

- `/tmp/cloud-porcelain-baseline/screenshots/macos-fg/main-1180x720-initial.png`（logical 1180×720，pixmap 2360×1386）
- `/tmp/cloud-porcelain-baseline/screenshots/macos-fg/main-1400x860-initial.png`（logical 1400×860，pixmap 2800×1666）

W2 cocoa：

- `/tmp/cloud-porcelain-baseline/screenshots/w2-macos-fg/w2-1400x860-bolt-cocoa.png`

W7 cocoa（platformName=cocoa，dpr=2.0，非阻塞 `show` + `grab`，无 `exec()` 对话框）：

| 镜头 | 路径 | 逻辑 grab |
|---|---|---|
| 1400×860 shell | `screenshots/w7-macos-fg/w7-1400x860-shell.png` | 2800×1662 |
| bolt 输入 | `screenshots/w7-macos-fg/w7-1400x860-bolt-input.png` | 2800×1662 |
| bolt sample 结果 | `screenshots/w7-macos-fg/w7-1400x860-bolt-result.png` | 2800×1662 |
| splitter min 212 | `screenshots/w7-macos-fg/w7-1400x860-splitter-min.png` | width=212 |
| splitter max 280 | `screenshots/w7-macos-fg/w7-1400x860-splitter-max.png` | width=280 |

日志：`/tmp/cloud-porcelain-baseline/screenshots/w7-macos-fg/macos-fg-log.txt`

Offscreen 七模块 input/result、gallery、popup、diagram 在 W7 已拍到 `screenshots/w7-offscreen/`（35 PNG）。offscreen 不是前景。

### 未验证（macOS 前景）

- 其余六模块（轴向螺纹、过盈、花键、蜗轮、赫兹、缓冲）的 cocoa 输入页与结果页
- 全部控件 hover / focus / pressed 交互态
- 原生 `QFileDialog` / `QFontDialog` / `QColorDialog`
- 长内容滚动、popup z-order、失焦关闭的真实合成
- **用户对 1400×860 shell / 输入 / 结果 / popup 截图的签字**

因此 macOS 前景 = **PARTIAL**，不是通过。

---

## 6. Windows 前景

**未验证。**

本机是 macOS，未跑 Windows 100% / 125% / 150% / 200% smoke，未拍 Windows 截图，未测 DPI 缩放。不得用 macOS 或 offscreen 结果代替。

---

## 7. HTML parity（W7-PARITY 数字）

- 权威表：`/tmp/cloud-porcelain-baseline/W7-PARITY.md`
- 机器表：`/tmp/cloud-porcelain-baseline/w7-parity.json`

测量对象：1400×860 Qt central widget vs spec（spec 优先于 HTML：侧栏 228 vs HTML 226）。CIEDE2000 已实现。HTML overlay 只作对齐辅助，不是像素相等门。

Totals：**PASS=26 FAIL=0** other=0 of 26.

| Item | Spec | Measured | Verdict |
|---|---|---|---|
| shell outer margin | 12 px | L12 T12 R12 B12 | PASS |
| sidebar width | 228 px（HTML 226 不是 spec） | 228 px | PASS |
| sidebar min/max | 212–280 | min=212 max=280 | PASS |
| sidebar–workspace gap | 12 px | 12 px | PASS |
| sidebar radius | 22 px | QSS 22 px；弧外像素 = canvas_base | PASS |
| chapter header min height | ~78 px | min=80 actual=90 | PASS |
| workspace chrome height | 36–40 px | 36 px | PASS |
| chapter/content gap (bolt) | 4 px 网格 | 12 px | PASS |
| chapter/content gap (hertz) | splitter handle 4 | 4 px | PASS |
| BrandTile fill | accent `#C76C4D` | rgb(199,108,77) ΔE2000=0.00 | PASS |
| PrimaryButton fill | accent_action `#B75D40`（不是 `#C76C4D`） | rgb(183,93,64) ΔE2000=0.00 | PASS |
| glass 5 samples | ΔE2000 ≤3 | 0.00 / 0.53 / 1.11 / 0.82 / 1.79 | PASS |
| selected module | accent_soft，不是绿 ready-dot | dist(soft)=0.0 dist(green)=251.9 | PASS |
| stress-field | 静态，不跟随鼠标 | 存在；无 QTimer / mouseMoveEvent | PASS |
| solid tokens in QSS | secondary / pass / fail / accent* | present | PASS |

本表是 offscreen 几何/色差，不能代替第 5 节用户签字或第 6 节 Windows。

---

## 8. 计算 / 报告 contract diff

- 再冻结脚本：`/tmp/cloud-porcelain-baseline/scripts/capture_contracts.py`（W8 副本只改输出目录）
- W8 文件：`/tmp/cloud-porcelain-baseline/contracts-w8/`（34 variant JSON + `_index.json`，与 W0 文件名一致）
- 对比键：`payload`、`core_result`、`page_last_result`、`report_lines`
- `report_lines` 去掉易变前缀 `软件版本:` / `生成时间:`

原始 diff：`/tmp/cloud-porcelain-baseline/w8-contract-diff.txt`

| 项 | 结果 |
|---|---|
| W0 files | 35 |
| W8 files | 35 |
| ONLY IN W0 / ONLY IN W8 | 无 |
| files with key diffs | **0** |
| total mismatch paths | **0** |
| VERDICT | **EMPTY** |
| `git diff --name-only -- core` | **空** |

`app/ui` 自 W0 以来的 diff 中，公式符号命中均为既有曲线数组改色或 paint-state getter（如 `_allowable_peak_n` 暴露），没有新的工程判据、阈值或 calculator 调用。buffer-default 在无导入曲线时仍无法构建 payload，与 W0 相同（contract 写入 error）。

EMPTY 合同不能代替前景或用户签字。

---

## 9. Git commit / push 状态

- 分支：`codex/cloud-porcelain-visual-system`
- 无 upstream（`fatal: no upstream configured`）
- **未 push**
- W8 验证前 HEAD：`07ab1a2692f13317cc923000051af3eabb08e97e`
- 本 docs 提交 SHA：见提交后 `git rev-parse HEAD`（本文件写入时尚未生成；以仓库 log 为准）

本提交显式文件：

- `docs/reports/2026-08-25-cloud-porcelain-acceptance.md`
- `docs/superpowers/specs/2026-08-25-cloud-porcelain-visual-system-spec.md`
- `docs/superpowers/plans/2026-08-25-cloud-porcelain-visual-system-plan.md`
- `docs/ui-mockups/claude-glass-theme-options.html`

未提交（按工作区纪律保留）：`.venv`、`.claude` 删除、`CLAUDE.md`、2026-08-23 质量文档脏 hunk、其它历史未跟踪 reports、`docs/ui-mockups/buffer-energy-ui-options.html`、`docs/worm_*.html`、`.agents`、tmp 等。

---

## 10. Spec §16 Definition of Done

任何一项 未验证 / PARTIAL 时，项目不得标 COMPLETE。

| # | 条件 | 判定 | 独立证据 |
|---|---|---|---|
| 1 | 用户确认 1400×860 shell、输入页、结果页和 popup 前景截图 | **未验证** | 无用户签字记录 |
| 2 | 云瓷 token、几何和主要状态满足 spec 容差 | **PASS** | 第 7 节 26/26；第 2 节 172 passed |
| 3 | 七个模块都完成输入页与结果页检查 | **PARTIAL** | 第 3 节 offscreen 七模块测试绿；cocoa 仅 bolt shell/input/result；其余六模块前景未拍 |
| 4 | macOS 前景通过；Windows 100/125/150% 至少正式 smoke | **PARTIAL** / **未验证** | 第 5 节 macOS 子集；第 6 节 Windows 未跑 |
| 5 | payload、calculator result、report lines 与冻结基线一致 | **PASS** | 第 8 节 EMPTY；core diff 空 |
| 6 | pass/fail/incomplete/not_checked/reference_only/stale/render-error 均有独立正确视觉 | **PARTIAL** | P1.1：产品页徽标 objectName 已按状态独立映射（incomplete≠WaitBadge，reference_only≠WaitBadge）。stale/render-error 仍由 W6 覆盖。Windows / 用户签字未验证；部分模块 incomplete 单元格仍未 live-driven |
| 7 | 输入变化、渲染失败、加载/清空不留下旧成功结果或可导出状态 | **PASS** | `test_stale_and_status_matrix` / `test_export_dirty_tracking` / `test_render_exception_guard` 含于第 2、4 节 |
| 8 | 自绘图和 matplotlib 只改视觉，不改数据/限值/工作点/判定 | **PASS** | 第 8 节 EMPTY；W5A/W5B 未改 `_build_payload` / calculate / `_build_report_lines` |
| 9 | 相关测试和全量测试通过，没有放宽旧断言 | **PASS** | 第 2–4 节 0 failed；相对 W0 +135 passed |
| 10 | MainWindow、页面导航和滚动满足性能预算 | **未验证** | W8 未测 `apply_theme` P95≤15ms、MainWindow 构造 P95&lt;350ms、首次导航 P95&lt;150ms |
| 11 | 无未经批准的 `core/`、报告内容、帮助工程结论或保存格式改动 | **PASS** | `git diff --name-only -- core` 空；本提交仅 docs |
| 12 | 最终 diff 只含批准的视觉系统范围，并保留原有无关改动 | **PASS** | 第 9 节显式文件列表；无关 dirty 未回退 |

**项目状态：PARTIAL / NEEDS FOREGROUND ACCEPTANCE。不是 COMPLETE。**
