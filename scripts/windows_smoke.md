# Windows desktop smoke

GitHub Actions 的 Windows runner 会执行 PyInstaller onedir 构建、校验 `build-info.json` 并启动 EXE 10 秒，覆盖“能构建且不会立即退出”的浅层门禁。它不操作真实桌面 UI，也不替代本清单的七模块人工验收。七个计算页的 offscreen 工作流 smoke 见 `tests/ui/test_module_workflow_smoke.py`。

只有对应 CI run 实际通过时，才能声称该提交通过了自动 Windows 浅层 smoke；本地未运行不能据此声称 Windows 已通过。

在本机 Windows 上按下列步骤做一次手工验收，并记下日期、构建版本、git SHA 和结果。任一步失败都不要把本次构建当成可发布。

## 1. 构建 exe

在仓库根目录：

```powershell
scripts\build_exe.bat
```

或：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

脚本实际写出路径由 `scripts/build_exe.ps1` 决定，默认是 `dist/releases/<version>/LocalEngineeringAssistant/`。以终端打印的 `Build completed:` 路径为准。

确认：

- 构建命令退出码为 0
- 产物目录里存在可启动的 `LocalEngineeringAssistant.exe`（onedir）或同名单文件 exe（若使用 `-OneFile`）
- `build-info.json` 中的 `version`、`build_id`、`git_commit` 和 `git_dirty` 与本次构建一致；onedir 文件位于应用目录，onefile 文件位于 exe 同目录

## 2. 启动

- 从产物目录启动 exe（不要只靠开发态 `python app\main.py` 代替本次打包验收）
- 主窗口能出来，侧栏可见 7 个计算模块 +「材料与标准库（即将推出）」占位项
- 最小窗口约为 `1180×720`，不要在启动后立即崩、白屏或无法点侧栏

## 3. 七个计算模块各走一遍最小路径

对下列每个模块重复：切到该页 → 加载测试案例/样例 → 执行校核或计算 → 确认有可见结果（不是半成功残留）→ 保存输入条件 → 导出三种格式。

| 模块 | 建议样例 | 计算动作 |
|------|----------|----------|
| 螺栓连接 | `examples/input_case_01.json` 或页内「测试案例 1」 | 执行校核 |
| 轴向受力螺纹连接 | `examples/tapped_axial_joint_case_01.json` 或「测试案例 1」 | 执行校核 |
| 过盈配合 | `examples/interference_case_01.json` 或「测试案例 1」 | 执行校核 |
| 花键连接校核 | `examples/spline_case_01.json` 或「测试案例 1」 | 执行校核 |
| 赫兹应力 | `examples/hertz_case_01.json` 或「测试案例 1」 | 执行校核 |
| 蜗轮蜗杆设计 | `examples/worm_case_01.json` 或「测试案例 1」 | 执行计算 |
| 缓冲块吸能仿真 | `examples/buffer_energy_input_conditions.json`；曲线可用 `examples/buffer_energy_case_01.csv` | 导入曲线后执行仿真 |

材料与标准库是占位页，不要求计算、保存或导出。

每模块还要确认：

- **保存输入**：能写出 JSON（通常到 `saved_inputs/` 或你选择的路径），再加载回来表单不丢关键字段
- **导出三种格式**：PDF、Word（`.docx`）、文本（`.txt`）。导出对话框过滤器为 `PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt)`。三种都要真正写出非空文件；PDF 能打开、DOCX 能当 Word 打开、TXT 能读到中文结果
- 改任一输入后，导出按钮应立即失效，直到重新计算成功

## 4. 记录模板

```text
日期:
机器 / Windows 版本:
git SHA:
构建命令:
产物路径:
启动: pass / fail
螺栓连接: 加载 / 计算 / 保存 / PDF / DOCX / TXT
轴向受力螺纹连接: 加载 / 计算 / 保存 / PDF / DOCX / TXT
过盈配合: 加载 / 计算 / 保存 / PDF / DOCX / TXT
花键连接校核: 加载 / 计算 / 保存 / PDF / DOCX / TXT
赫兹应力: 加载 / 计算 / 保存 / PDF / DOCX / TXT
蜗轮蜗杆设计: 加载 / 计算 / 保存 / PDF / DOCX / TXT
缓冲块吸能仿真: 加载 / 计算 / 保存 / PDF / DOCX / TXT
阻塞问题:
```
