# Local Engineering Assistant (Desktop, VDI 2230 Core)

本项目提供一个本地桌面版机械计算框架（PySide6），当前已实现：
- `螺栓连接`：VDI 2230 核心链路
- `过盈配合`：DIN 7190 核心增强版，已支持实心轴/空心轴主模型、联合作用、优选配合/偏差换算、装配流程，以及 Step 5 `fretting` 风险评估
- `赫兹应力`：线接触/点接触首版
- `蜗轮`：DIN 3975 几何与基础性能首版，已按蜗杆/蜗轮分组输入并提供两列自动计算尺寸，`DIN 3996` 负载能力校核仍未开始

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

桌面端当前交互为**顺序步骤式工程表单**（非 JSON 文本输入），支持：
- 保存/加载输入条件（项目内 `saved_inputs/` 目录，关闭软件后仍可继续加载）
- 加载测试案例参数到表单
- 直接执行校核
- 查看非程序员可读的分项结果与总体通过/不通过
- 过盈配合支持 `manual / preferred fit / user-defined deviations` 三种过盈来源
- 过盈配合支持 `shaft_inner_d_mm`，`0` 表示实心轴，非零表示空心轴
- 过盈配合支持 `manual_only / shrink_fit / force_fit` 三种装配模式
- 过盈配合支持 Step 5 `fretting` 风险评估：输出 applicability、风险等级、驱动因素与建议，但**不并入**基础 DIN verdict
- 当前仍未把 `service temperature / speed / centrifugal force / stepped geometry` 耦合进主模型
- 导出报告时保留材料预设、粗糙度来源、fit source、assembly mode 等追溯信息
- 查看模块图示与性能曲线（按各模块能力显示）
- 蜗轮模块支持蜗杆/蜗轮两列尺寸预览和可滚动图形页
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
