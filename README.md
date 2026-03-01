# Local Engineering Assistant (Desktop, VDI 2230 Core)

本项目提供一个本地桌面版机械计算框架（PySide6），当前已实现“螺栓连接”模块（VDI 2230 核心链路），其余模块预留入口。

## 文档
- 计算说明：`docs/vdi2230-calculation-spec.md`
- 设计文档：`docs/plans/2026-03-01-vdi2230-bolt-tool-design.md`
- 平台路线图：`docs/plans/2026-03-01-personal-eassistant-roadmap.md`

## 本地运行（PyCharm / 终端）

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

启动桌面应用：

```bash
python3 app/main.py
```

桌面端当前交互为**Chapter 14 风格章节表单**（非 JSON 文本输入），支持：
- 加载样例参数到表单
- 直接执行校核
- 查看非程序员可读的分项结果与总体通过/不通过
- 查看螺栓夹紧示意图（FM/FA/FK）
- 导出可读报告（txt）

## CLI 快速开始（保留）

```bash
python3 src/vdi2230_tool.py --input examples/input_case_01.json
```

保存结果到文件：

```bash
python3 src/vdi2230_tool.py \
  --input examples/input_case_01.json \
  --output examples/output_case_01.json
```

运行第二个样例（通过工况）：

```bash
python3 src/vdi2230_tool.py \
  --input examples/input_case_02.json \
  --output examples/output_case_02.json
```

## 输入结构
输入为 JSON，主要分为以下节点：
- `fastener`: 螺栓几何与材料强度
- `tightening`: 拧紧系数、摩擦系数、利用系数
- `loads`: 轴向/横向载荷、嵌入与热损失
- `stiffness`: 刚度或顺从度模型
- `bearing`: 支承面有效直径
- `checks`: 校核安全系数

详细字段和公式见计算说明文档。

## 当前范围
- 已覆盖：`FMmin/FMmax`、载荷分配、扭矩估算、装配与服役应力校核、防滑/残余夹紧力校核。
- 未覆盖：VDI 2230 全部特例和全疲劳谱。

## 打包为 .exe（Windows）

1. 在项目根目录创建虚拟环境并安装依赖。
2. 运行：

```bat
scripts\build_exe.bat
```

输出目录：`dist\LocalEngineeringAssistant\`
