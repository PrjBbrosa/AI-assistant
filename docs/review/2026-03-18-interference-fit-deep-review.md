# 过盈配合章节深度审查（2026-03-18）

## 审查范围

- UI 章节页：`app/ui/pages/interference_fit_page.py`
- Core 计算：`core/interference/calculator.py`
- 配合换算：`core/interference/fit_selection.py`
- 装配细节：`core/interference/assembly.py`
- 测试：`tests/core/interference/*`、`tests/ui/test_interference_page.py`
- 示例：`examples/interference_case_01.json`、`examples/interference_case_02.json`
- 外部对照：
  - eAssistant handbook / example
  - eAssistant ISO 286 tolerance fit calculator handbook
  - MITCalc brochure capability description
  - RoyMech thick cylinder / interference-fit formula page

## 结论摘要

- 当前过盈配合章节的主判定链路基本自洽，未发现类似“UI 字段存在但完全未参与计算”的高危接线 bug。
- Core 结果层已经正确暴露了 `combined_ok`、`p_req,T / p_req,Ax / p_req,comb / p_gap`、装配 trace、fit source 和 repeated-load trace。
- 当前主要风险不在主公式是否完全失真，而在：
  - 原始 `inputs` JSON 回灌到 UI 时会被辅助选择器覆盖
  - 示例与公开 DIN 7190 经典案例之间存在模型边界差异，但当前文案不足以阻止误读
  - 优选配合能力与外部工具相比明显收窄，且边界测试还不够细

## Findings

### 1. Medium: raw payload 加载到 UI 时会被默认选择器覆盖，无法忠实恢复原始计算输入

- 位置：
  - `app/ui/pages/interference_fit_page.py:886-908`
  - `app/ui/pages/interference_fit_page.py:915-925`
  - `app/ui/pages/interference_fit_page.py:1382-1419`
- 现象：
  - `_apply_input_data()` 先把 `inputs` 中的数值写入控件。
  - 随后调用 `_sync_material_inputs()`、`_sync_roughness_factor()`、`_sync_fit_mode_fields()`、`_sync_assembly_fields()`。
  - 如果输入文件没有 `ui_state`，则材料、粗糙度 profile、assembly mode、repeated-load mode 都会回到默认选项，并覆盖掉原始 `inputs` 中的自定义数值或模式。
- 复现证据：
  - headless 复现中，原始输入中的
    - `shaft_e_mpa=199999`
    - `shaft_nu=0.271`
    - `hub_e_mpa=188888`
    - `hub_nu=0.255`
    - `smoothing_factor=0.67`
    - `assembly.method=force_fit`
    - `advanced.repeated_load_mode=on`
  - 加载后被恢复成：
    - `materials.shaft_material=45钢`
    - `shaft_e_mpa=210000`
    - `shaft_nu=0.30`
    - `hub_e_mpa=210000`
    - `hub_nu=0.30`
    - `roughness.profile=DIN 7190-1:2017（k=0.4）`
    - `assembly.method=manual_only`
    - `advanced.repeated_load_mode=off`
- 影响：
  - 通过 UI “加载输入条件”时，只要来源是 raw calculator payload 而不是带 `ui_state` 的表单快照，页面就会静默篡改输入语义。
  - 这会影响外部案例复核、CLI/核心 JSON 回灌、以及后续报告追溯可信度。
- 判断：
  - 这是 UI 恢复语义缺口，不影响纯 core 计算，但会影响“章节可复核性”。

### 2. Medium: 示例案例与 eAssistant 公开 DIN 7190 经典案例高度相似，但当前模型边界不同，容易被误当成“同案同算”

- 本地示例 `examples/interference_case_01.json` 使用：
  - `d=50 mm`
  - `L=20 mm`
  - `D=95 mm`
  - `T=80 Nm`
  - `F=125 N`
  - `KA=1.2`
  - `mu_T = mu_Ax = 0.15`
  - `fit = H7/s6 -> 18~59 um`
- eAssistant 公开案例也使用同一组核心尺寸与载荷，但额外包含：
  - `inner diameter shaft = 30 mm`
  - `speed = 2000 min^-1`
  - `operating temperature = 25°C`
  - surface handling based on its DIN 7190 workflow
- 当前实现明确限定为：
  - 实心轴
  - 不考虑离心力
  - 不考虑服役温度导致的直径变化
  - 弯矩按 `QW=0` 保守简化
- 对比结果：
  - eAssistant 示例文档给出的自动定扭矩结果约为 `83.60 Nm`
  - 本地 solid-shaft 近似下，以相近输入复算得到的 `torque_min` 约为：
    - `217.02 Nm`（`k=0.4`，Rz=6.3/6.0）
    - `131.41~135.39 Nm`（`k=0.8`，接近旧版 DIN 粗糙度处理）
- 判断：
  - 这更像“示例和公开案例边界不一致”而不是公式 bug。
  - 但如果继续沿用这组相近数字做展示，用户很容易把当前示例误解为“已经复现了 eAssistant/DIN 7190 公共案例”。
- 建议：
  - 把 `interference_case_01.json` 明确标注为“adapted solid-shaft case”。
  - 或单独新增 `public_benchmark_notes.md`，说明与 eAssistant 公共案例的差异来源。

### 3. Medium: 优选配合仅为极小子集，当前测试尚不足以证明边界行为完全可靠

- 位置：
  - `core/interference/fit_selection.py:7-53`
  - `core/interference/fit_selection.py:94-147`
- 当前只支持：
  - `H7/p6`
  - `H7/s6`
  - `H7/u6`
  - 名义直径 `6~50 mm`
- 与外部工具对比：
  - eAssistant 的 tolerance fit calculator 按 handbook 描述，支持 DIN ISO 286 全部 IT classes，并支持 fit search；在搜索窗口 `18~59 um` 时会推荐 preferred fits。
  - MITCalc 说明也明确将 force fits/shrink fits 与 `ISO 286 + DIN 7190` 联合支持，而非 3 个固定代号。
- 当前测试仅锁定了：
  - `H7/s6 @ 50 mm -> 18/59 um`
  - 超范围直径会报错
- 尚未锁定：
  - 所有 band 交界点（10/18/24/30/40/50 mm）的选带行为
  - `H7/p6`、`H7/u6` 在多个 band 的正确性
  - UI/报告是否在所有路径都足够强调“curated subset”
- 判断：
  - 这是能力遗漏和边界测试不足，不是主计算 bug。

### 4. Low: 设计文档边界落后于当前实现，章节说明存在维护性风险

- 位置：
  - `docs/plans/2026-03-08-interference-fit-din7190-core-design.md`
- 文档仍写“不纳入”：
  - ISO 286 配合推荐
  - 热装温差
  - repeated load / fretting
- 但代码和 UI 已实现这些能力。
- 影响：
  - 后续维护或再次审查时，容易误判“代码超范围”或“章节文档缺项”。

## 未发现的高危问题

- 未发现 `combined_ok`、`gaping_ok`、`fit_range_ok` 与总判定脱节。
- 未发现 fit source / assembly trace / repeated-load trace 完全缺失于结果或导出报告。
- 未发现 `assembly.method`、`advanced.repeated_load_mode` 在正常 UI 操作路径下不生效。

## 本地复核结果

- 运行：
  - `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/core/interference/test_calculator.py tests/core/interference/test_fit_selection.py tests/core/interference/test_assembly.py tests/ui/test_interference_page.py -q`
- 结果：
  - `33 passed`

## 外部对照摘要

### eAssistant public DIN 7190 example

- 来源：`https://www.eassistant.eu/fileadmin/dokumente/eassistant/pdf/Hilfe/Beispiel/Presssitz_en.pdf`
- 可提取文本显示：
  - `d=50 mm`
  - `L=20 mm`
  - `D=95 mm`
  - `inner diameter shaft=30 mm`
  - `T=80 Nm`
  - `F=125 N`
  - `speed=2000 min^-1`
  - `operating factor=1.2`
  - 推荐 fit：`H7/s6`
  - 自动定扭矩结果约 `83.60 Nm`
- 结论：
  - 本工具不能把它当成一对一 benchmark，因为模型边界不同。

### eAssistant ISO 286 tolerance fit calculator

- 来源：`https://www.eassistant.eu/fileadmin/dokumente/eassistant/etc/HTMLHandbuch/en/eAssistantHandbch25.html`
- handbook 明确说明：
  - 支持 DIN ISO 286 tolerance system 与 all IT classes
  - 可按 `18~59 um` interference search fits
  - preferred fits 只是搜索的一种过滤方式，不是完整能力边界
- 结论：
  - 当前项目的 `fit_selection.py` 只能算“受限可追溯 starter subset”。

### MITCalc

- 来源：`https://mitcalc.com/download/Brochure_EN_ver_1_73.pdf`
- brochure 说明其 force couplings of shafts with hubs 支持：
  - force fits / shrink fits
  - additional radial force + bending moment
  - specific service temperature
  - standards: `ANSI B4.1, ISO 286, DIN 7190`
- 结论：
  - 当前项目在“service temperature / broader fit system / more complete shaft-hub variants”上仍明显收窄。

### RoyMech

- 来源：`https://www.roymech.co.uk/Useful_Tables/Mechanics/Cylinders.html`
- 页面给出的理论边界与当前项目更接近：
  - thick walled cylinder
  - press fit / shrink fit
  - solid shaft simplification
- 结论：
  - 当前 `calculator.py` 的基础厚壁圆筒思路与这类公开公式基线一致，主风险不在“完全脱离经典公式”，而在能力边界与案例解释。

## 建议优先级

1. 优先修复 raw payload 回灌覆盖问题，至少做到：
   - 如果加载的是 raw inputs，则不要静默覆盖已有数值
   - 若必须依赖 `ui_state`，需要明确报提示而不是默认回退
2. 给示例和报告补充“benchmark disclaimer”：
   - 明确 `examples/interference_case_01.json` 不是 eAssistant 公共案例的等价复现
3. 为 `fit_selection` 增加边界回归测试：
   - 每个 band 交界直径
   - 每个 fit family 至少 2 个 band
4. 更新设计文档，避免后续审查继续被陈旧范围说明干扰
