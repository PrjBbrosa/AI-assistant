# Local Engineering Assistant

本项目是一个基于 PySide6 的本地桌面机械计算工具，当前聚焦“可上手、可复核、可导出”的工程计算流程。

当前侧栏模块如下：

- `螺栓连接`：VDI 2230 核心链路
- `过盈配合`：DIN 7190 增强版，支持实心轴/空心轴、优选配合、偏差换算、装配流程、Fretting 风险评估
- `花键连接校核`：花键齿面承压简化预校核 + 光滑段圆柱过盈
- `赫兹应力`：线接触/点接触快速计算
- `蜗轮蜗杆设计`：DIN 3975 几何与基础性能 + Method B 最小负载能力子集
- `材料与标准库`：当前为占位页，尚未实现

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
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\main.py
```

如果 `.venv` 已经存在，可以跳过第一行。

## 桌面端交互方式

桌面端采用顺序步骤式工程表单，不需要手写 JSON。当前支持：

- 按模块逐步填写输入参数
- 直接加载测试案例
- 保存/加载输入条件 JSON（花键模块除外）
- 执行校核并查看总体结论、分项结果和提示
- 导出可读报告
- 查看模块图示、压入力曲线或性能曲线

## 模块完成度概览

| 模块 | 当前状态 | 说明 |
|------|----------|------|
| 螺栓连接 | `已可用` | 核心链路已完成，但还不是完整 VDI 2230 |
| 过盈配合 | `已可用` | 主链路较完整，但 `service temperature / speed / centrifugal force / stepped geometry` 未并入 |
| 花键连接校核 | `部分完成` | 更适合作为简化预校核，不是正式 `DIN 5480 / DIN 6892` 签发模块 |
| 赫兹应力 | `首版可用` | 适合快速接触应力估算 |
| 蜗轮蜗杆设计 | `部分完成` | 目前还是 `DIN 3996 / ISO/TS 14521` 之前的最小工程子集 |
| 材料与标准库 | `未完成` | 当前仅占位 |

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

输出目录位于 `dist\LocalEngineeringAssistant\`。
