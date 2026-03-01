# Findings & Decisions

## Requirements
- 产出一份完整的 VDI 2230 计算说明文档（中文）
- 基于 VDI 2230 开发螺栓校核工具
- 工具需可运行、可复核，给出输入输出和示例

## Research Findings
- 仓库为空目录，需要从零搭建项目结构
- 需收集 VDI 2230 的公开可引用资料来支撑公式与流程
- VDI 2230 官方覆盖范围：Part 1 为高负荷螺栓连接系统计算，Part 2 为多螺栓连接，Part 3 为同轴压缩载荷（来源：VDI 官方页面）
- eAssistant 对 VDI 2230 的摘要给出核心关系：`FMmax = alpha_A * FMmin`，并列出 `FMmin` 由防滑、密封、分离、嵌入损失等条件共同决定
- PCB 白皮书按 VDI 2230 列出 R1-R10 计算流程与关键校核项（例如最小预紧力、最大允许附加载荷、疲劳校核），可作为流程框架参考
- 夹紧力与附加载荷分配采用经典弹簧模型（VDI 2230 同源方法）：`phi = delta_p / (delta_s + delta_p)`，附加载荷进入螺栓为 `phi * FA`
- 装配阶段可通过“轴向 + 扭转载荷”进行当量应力校核：`sigma_v = sqrt(sigma^2 + 3*tau^2)`，与材料屈服强度利用系数比较
- 用户确认交付形态为本地桌面版本（PyCharm 运行），并预留 `.exe` 封装路径
- 桌面框架模块入口固定为：螺栓连接、轴连接、轴承、蜗轮、弹簧、材料与标准库
- 用户要求界面按 eAssistant Chapter 14 的章节结构与参数组织方式重排
- 用户要求结果展示改为非 JSON 的工程可读格式，并要求增加螺栓夹紧图

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 Python 实现首版计算引擎 | 便于快速构建数值计算与示例验证 |
| 文档与代码同仓库交付 | 便于追溯公式与实现一致性 |
| 首版范围聚焦 VDI 2230 核心校核链路（R1-R8） | 在空仓库内优先交付可运行、可复核版本 |
| 输入参数同时支持“顺从度”和“刚度” | 兼顾标准建模与工程现场常见输入习惯 |
| 框架改为 PySide6 本地桌面壳 | 满足用户本地使用和 exe 打包目标 |
| 保留 CLI 同时新增 GUI | 兼顾批处理与交互式工程校核 |
| 螺栓页面改为 Chapter 14 导航布局 | 与用户参考页面的信息架构保持一致 |
| 参数全部带说明（hint + tooltip） | 面向非程序员用户，降低误填风险 |
| 结果输出改为“结论 + 分项 + 建议 + 报告导出” | 使结果可直接用于工程沟通 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| 无现成代码和样例 | 从标准流程拆解并自建示例数据 |

## Resources
- /Users/donghang/.agents/skills/brainstorming/SKILL.md
- /Users/donghang/.agents/skills/planning-with-files/SKILL.md
- https://www.vdi.de/richtlinien/details/vdi-2230-blatt-1-systematic-calculation-of-high-duty-bolted-joints-joints-with-one-cylindrical-bolt
- https://www.eassistant.eu/fileadmin/dokumente/eassistant/etc/HTMLHandbuch/en/eAssistantHandbch14.html
- https://www.pcbloadtorque.com/pdf/14.6.13%20-%20VDI%202230%20Systematic%20Calculation%20of%20High%20Duty%20Bolted%20Joints.pdf
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/main.py
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/ui/main_window.py
- /Users/donghang/Documents/Codex/bolt tightening calculator/scripts/build_exe.bat
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/ui/pages/bolt_page.py
- /Users/donghang/Documents/Codex/bolt tightening calculator/app/ui/widgets/clamping_diagram.py

## Visual/Browser Findings
- 已完成 VDI 官方页面、eAssistant 手册页面和 PCB 白皮书检索，确认了实现所需的主流程和核心方程
