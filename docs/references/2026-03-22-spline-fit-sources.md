# 花键模块公开来源与 benchmark 记录

## 1. 使用边界

本文件只记录当前仓库可公开引用的来源，用于：

- 给花键模块的几何输入建立最小可追溯基线
- 说明为什么不能再把 `d = m * z` 视为 DIN 5480 标准几何
- 给 10~15 mm 小直径花键准备公开 benchmark

它**不能替代** DIN 5480 / DIN 5466 / DIN 6892 标准正文。

## 2. 公开来源

### 2.1 DIN Media 标准入口

- 标准：DIN 5480-1
- 页面：https://www.dinmedia.de/de/norm/din-5480-1/81839056
- 用途：
  - 确认 DIN 5480 是 “Involute splines based on reference diameters”
  - 确认旧版 `DIN 5480-1:2006-03` 已被 `DIN 5480-1:2025-10` 替代

### 2.2 GWJ eAssistant Handbook

- 页面：https://www.eassistant.eu/fileadmin/dokumente/eassistant/etc/HTMLHandbuch/en/eAssistantHandbch17.html
- 用途：
  - 公开说明 involute spline 的输入组织方式与强度链
  - 明确 share factor / load peaks / support factor / hardness factor / safety 都会进入计算
  - 说明几何与强度并不是单靠 `m` 和 `z` 就能完全定义

### 2.3 FVA Workbench Module Description

- 页面：https://doc.fva-service.de/module_description/FVA-Workbench%20Module%20Q3-24.pdf
- 用途：
  - 公开说明几何按 `DIN 5480 Part 1 (2006)`
  - 载荷能力按 `DIN 5466 Part 1 (2000)`，并包含 `FVA 591` 扩展
  - 证明正式工程链不止当前仓库里的单一承压式

### 2.4 Mädler 公开目录与产品页

- 轴目录 PDF：https://smarthost.maedler.de/datenblaetter/K43_534.pdf
- 毂目录 PDF：https://smarthost.maedler.de/datenblaetter/K43_535.pdf
- 毂产品页：https://www.maedler.de/article/64821500
- 用途：
  - 给 10~15 mm 小规格 DIN 5480 花键提供公开、真实的几何样例
  - 可作为 Stage B 的 geometry benchmark

## 3. 当前公开 benchmark

### Benchmark A: W / N 15 x 1.25 x 10

公开来源：

- 轴：Mädler 目录 PDF `K43_534.pdf`
- 毂：Mädler 产品页 `64821500`

当前用于仓库的显式几何输入：

- `module_mm = 1.25`
- `tooth_count = 10`
- `reference_diameter_mm = 15.0`
- `tip_diameter_shaft_mm = 14.75`
- `root_diameter_shaft_mm = 12.1`
- `tip_diameter_hub_mm = 12.5`

说明：

- 这是 10~15 mm 范围内可以公开拿到的真实小规格样例
- 它足以证明 `d = m * z = 12.5 mm` 不能直接替代 DIN 5480 的参考直径 `15 mm`
- 当前仓库已用这组数据作为场景 A 的首个公开 geometry benchmark

### Benchmark B: W14x0.8x16

公开来源：

- 工业接口页：https://toolsearch.exsysautomation.com/halter/halter/en?id=9431

说明：

- 该页面证明 14 mm 级别的 DIN 5480 小规格接口在工业场景中真实存在
- 但它没有像 Mädler 那样公开完整尺寸表
- 因此目前只作为“小直径工业存在性”证据，不作为精确 geometry benchmark

## 4. 对代码实现的约束

- 未提供显式参考尺寸时，不得再把几何结果标记成标准几何
- 近似模式必须显式标记，并且只允许用于 `simplified_precheck`
- 在拿到付费标准正文、商业工具报告或企业内部图纸之前，不把场景 A 升格成“正式工程校核”
