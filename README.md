# Local Engineering Assistant

本项目是一个基于 PySide6 的本地桌面机械计算工具，当前聚焦“可上手、可复核、可导出”的工程计算流程。

当前侧栏模块如下：

- `螺栓连接`：VDI 2230 核心链路
- `轴向受力螺纹连接`：螺栓拧入内螺纹对手件、无被夹件的纯轴向拉载荷校核（与 VDI 2230 夹紧连接并列）
- `过盈配合`：DIN 7190 增强版，支持实心轴/空心轴、优选配合、偏差换算、装配流程、Fretting 风险评估
- `花键连接校核`：花键齿面承压简化预校核 + 光滑段圆柱过盈
- `赫兹应力`：线接触/点接触快速估算；当前仅支持外接触 / 正曲率
- `蜗轮蜗杆设计`：DIN 3975 几何与基础性能 + Method B 最小负载能力子集
- `缓冲块吸能仿真`：曲线导入、吸能计算和时域响应展示
- `材料与标准库（即将推出）`：当前为占位页，尚未实现

## 文档

- 新手使用说明：`docs/user-guide.md`
- 螺栓计算说明：`docs/vdi2230-calculation-spec.md`
- 历史设计文档（螺栓）：`docs/archive/plans/2026-03-01-vdi2230-bolt-tool-design.md`
- 平台路线图：`docs/archive/plans/2026-03-01-personal-eassistant-roadmap.md`

如果你是第一次使用，建议先直接看 `docs/user-guide.md`。

## 本地运行

Windows / PyCharm 下推荐这样启动：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c constraints.txt
.\.venv\Scripts\python.exe app\main.py
```

如果 `.venv` 已经存在，可以跳过第一行。

`requirements.txt` 只声明下限；`constraints.txt` 钉死当前已验证可 import 的精确版本（PySide6、PyInstaller、reportlab、matplotlib、openpyxl，以及测试用的 pytest）。更新依赖时先 `pip install -r requirements.txt`，再用环境里实际安装的版本刷新 `constraints.txt` 的 `==` 行。测试额外依赖见 `requirements-dev.txt`：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt
$env:QT_QPA_PLATFORM="offscreen"
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

macOS / Linux：

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

## 持续集成

GitHub Actions 工作流在 `.github/workflows/ci.yml`：Ubuntu、`QT_QPA_PLATFORM=offscreen`，按 `requirements.txt` + `requirements-dev.txt` 并受 `constraints.txt` 约束安装，然后跑 `python -m pytest tests/ -q` 和 `git diff --check`。

Windows runner 会执行 PyInstaller onedir 构建、构建信息校验和 EXE 10 秒启动 smoke；只有对应 CI run 实际通过时，才能视为该提交通过了 Windows 浅层门禁。七模块计算、保存/加载和报告导出仍需按 `scripts/windows_smoke.md` 做真实桌面人工验收。

## 桌面端交互方式

桌面端采用顺序步骤式工程表单，不需要手写 JSON。最小支持窗口尺寸为 `1180×720`，默认启动尺寸为 `1400×860`。当前支持：

- 按模块逐步填写输入参数
- 直接加载测试案例
- 保存/加载输入条件 JSON（7 个计算模块均支持；材料与标准库占位页除外）
- 执行校核并查看总体结论、分项结果和提示
- 导出可读报告
- 查看模块图示、压入力曲线或性能曲线

## 模块完成度概览

| 模块 | 当前状态 | 说明 |
|------|----------|------|
| 螺栓连接 | `已可用` | 核心链路已完成，但还不是完整 VDI 2230 |
| 轴向受力螺纹连接 | `已可用` | core 计算、UI 结果展示、文本/PDF 报告导出已完成；暂不支持横向力、弯矩、多螺栓并联 |
| 过盈配合 | `已可用` | 主链路较完整，但 `service temperature / speed / centrifugal force / stepped geometry` 未并入 |
| 花键连接校核 | `部分完成` | 更适合作为简化预校核，不是正式 `DIN 5480 / DIN 6892` 签发模块；支持保存/加载输入和测试案例 |
| 赫兹应力 | `首版可用` | 适合快速接触应力估算；当前仅支持外接触（曲率半径 ≥ 0，两正曲率相加），内接触/负曲率不在本版范围 |
| 蜗轮蜗杆设计 | `测试中` | 目前还是 `DIN 3996 / ISO/TS 14521` 之前的最小工程子集，正在验证中 |
| 缓冲块吸能仿真 | `首版可用` | 曲线导入、吸能与时域响应；不是完整缓冲器签发模块 |
| 材料与标准库（即将推出） | `未完成` | 当前仅占位 |

更详细的上手步骤、按钮说明和未完成项，请看 `docs/user-guide.md`。

## CLI（保留）

命令行入口仍可使用，适合批处理或调试：

```powershell
.\.venv\Scripts\python.exe src\vdi2230_tool.py --input examples\input_case_01.json
```

保存结果到文件：

```powershell
.\.venv\Scripts\python.exe src\vdi2230_tool.py --input examples\input_case_01.json --output examples\output_case_01.json
```

## 打包为 `.exe`

```powershell
scripts\build_exe.bat
```

默认输出目录为 `dist\releases\<version>\LocalEngineeringAssistant\`。其中包含 `LocalEngineeringAssistant.exe` 和可人工审计的 `build-info.json`；实际路径以构建脚本打印的 `Build completed:` 为准。
