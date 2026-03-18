# 螺栓校核页面深度审查报告

**日期：** 2026-03-17  
**范围：** `app/ui/pages/bolt_page.py`、`app/ui/pages/bolt_flowchart.py`、`app/ui/input_condition_store.py`、`core/bolt/calculator.py`、相关测试与样例  
**审查重点：** 页面前后逻辑、参数引用链、工况覆盖、无效代码、后续优化方向

---

## 一、验证方式

### 1.1 自动化验证

已运行：

```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest \
  tests/core/bolt/test_calculator.py \
  tests/core/bolt/test_compliance_model.py \
  tests/ui/test_input_condition_store.py -q
```

结果：`76 passed in 0.13s`

### 1.2 额外复现脚本

为确认 UI 与展示层问题，额外用 headless `BoltPage()` 做了以下复现：

- 输入条件快照保存后再回灌，标准螺距会触发 `ValueError: could not convert string to float: '1.5（粗牙）'`
- 切到“校核模式”后保存/回灌，`calculation_mode` 不会被持久化
- 直接加载 raw payload 时，`joint_type/basic_solid/surface_class/tightening_method/surface_treatment` 不会恢复到 UI 选择器
- 单层热工况中选择“自定义材料”但不填 `alpha` 时，core 会回退成钢的默认热膨胀系数并算出 `thermal_auto_value_N = 0`
- 多层热工况中某层 `alpha` 留空时，页面层会抛原生 `ValueError`
- 同一页面重复执行 `_calculate()` 后，流程图详情页输入回显控件数量会持续增长
- 扭矩法工况下，R5 正式判据已用 `sigma_vm_work`，但结果区仍展示 `sigma_ax_work`

---

## 二、结论摘要

- 核心计算链路已明显优于 2026-03-01 版本，R3/R4/R5、温度损失、简化疲劳、可选 R7 都已经接入。
- 当前最危险的问题不在 core 主公式，而在“UI 状态持久化”和“结果展示语义”两层。
- 现有单测主要覆盖了 calculator 正向链路，对 `bolt_page.py` 和 `bolt_flowchart.py` 的 UI 级回归几乎没有覆盖。

---

## 三、主要问题

### 3.1 R5 展示值与正式判据不一致【严重度：高】

- **位置：**
  - `core/bolt/calculator.py:404`
  - `core/bolt/calculator.py:410`
  - `app/ui/pages/bolt_page.py:2065`
  - `app/ui/pages/bolt_page.py:2190`
- **现象：**
  - core 已用 `sigma_vm_work` 做 R5 判定
  - 页面关键结果与导出报告仍写 `sigma_ax_work`
- **影响：**
  - 扭矩法下可能出现“正式校核失败，但页面显示 87% 利用率”的误导
- **复现证据：**
  - 构造工况 `alpha_A=1.8`、`mu_thread=0.4`、`FA_max=40000N`、`tightening_method=torque`
  - core 结果：
    - `sigma_ax_work = 714.333 MPa`
    - `sigma_vm_work = 867.096 MPa`
    - `sigma_allow_work = 817.391 MPa`
    - `operating_axial_ok = False`
  - 页面摘要仍显示：
    - `服役轴向应力: 714.3 MPa / 允许 817.4 MPa [87.4%]`
- **建议：**
  - 页面和报告统一改为展示 `sigma_vm_work`
  - 若需保留 `sigma_ax_work`，应仅作为中间值展示，不应放在分项判据摘要位置

### 3.2 自定义热膨胀系数留空会静默回退为钢默认值【严重度：高】

- **位置：**
  - `app/ui/pages/bolt_page.py:1273`
  - `app/ui/pages/bolt_page.py:1287`
  - `core/bolt/calculator.py:294`
  - `core/bolt/calculator.py:295`
  - `core/bolt/calculator.py:296`
- **现象：**
  - UI 选“自定义”会清空 `alpha`
  - payload 不再带 `alpha_bolt/alpha_parts`
  - core 使用 `_ALPHA_STEEL_DEFAULT = 11.5e-6`
- **影响：**
  - 热损失自动估算会在错误前提下运行
  - 铝壳体等热失配工况可能被低估甚至算成 0
- **复现证据：**
  - `check_level=thermal`、`temp_bolt=120`、`temp_parts=20`
  - UI 中将 `operating.bolt_material` 和 `operating.clamped_material` 均切到“自定义”
  - payload 中 `operating` 仅剩 `load_cycles/temp_bolt/temp_parts`
  - core 输出：
    - `alpha_bolt_used = 1.15e-05`
    - `alpha_parts_used = 1.15e-05`
    - `thermal_auto_value_N = 0.0`
- **建议：**
  - 自定义材料场景下把 `alpha` 作为必填
  - core 取消此处静默钢默认值回退，缺值时应跳过自动估算并给出明确提示

### 3.3 输入条件保存/加载链路默认就会崩溃【严重度：高】

- **位置：**
  - `app/ui/input_condition_store.py:21`
  - `app/ui/pages/bolt_page.py:1660`
  - `app/ui/pages/bolt_page.py:1699`
  - `app/ui/pages/bolt_page.py:1703`
  - `app/ui/pages/bolt_page.py:1826`
- **现象：**
  - `build_form_snapshot()` 保存的是界面显示文本
  - 对于标准螺距，下拉项会存成 `1.5（粗牙）`
  - `_apply_input_data()` 再按数值恢复时直接 `float(text)`，从而崩溃
- **复现证据：**
  - `page._capture_input_snapshot()` 输出：
    - `{'d': 'M10', 'p': '1.5（粗牙）', ...}`
  - 对同一快照执行 `page._apply_input_data(snap)`：
    - `ValueError: could not convert string to float: '1.5（粗牙）'`
- **影响：**
  - “保存输入条件 / 加载输入条件”对螺栓页面不可靠
  - 用户最常用的标准规格场景反而最容易触发
- **建议：**
  - 螺栓页快照应存规范化值：`d=10`、`p=1.5`
  - 加载端应兼容文本标签和数值两种格式
  - `load_input_conditions()` 路径应捕获这类格式错误并转成用户可读提示

### 3.4 关键 UI 状态不会被保存，也不会从 raw payload 恢复【严重度：中高】

- **位置：**
  - `app/ui/pages/bolt_page.py:1660`
  - `app/ui/pages/bolt_page.py:1664`
  - `app/ui/pages/bolt_page.py:1765`
  - `app/ui/pages/bolt_page.py:1892`
  - `app/ui/pages/bolt_page.py:1898`
  - `app/ui/pages/bolt_page.py:1904`
  - `app/ui/pages/bolt_page.py:1917`
  - `app/ui/pages/bolt_page.py:1921`
- **现象：**
  - 快照只额外保存了 `check_level`
  - `calculation_mode` 不保存
  - raw payload 中的 `options.joint_type`、`options.tightening_method`、`options.surface_treatment`
    以及 `clamped.basic_solid`、`clamped.surface_class` 不会恢复到 UI 选择器
- **复现证据：**
  - 把 `calc_mode_combo` 切到 `verify` 后保存快照，`ui_state` 中没有 `calculation_mode`
  - 给 `_apply_input_data()` 传入 raw payload：
    - `joint_type=through`
    - `calculation_mode=verify`
    - `basic_solid=cone`
    - `surface_class=fine`
    - `tightening_method=angle`
    - `surface_treatment=cut`
  - 回显结果仍是默认：
    - `螺纹孔连接 / design / 圆柱体 / 中等 / 扭矩法 / 轧制`
- **影响：**
  - 页面状态与真实 payload 脱节
  - 从外部 JSON 加载时，用户会以为当前工况已恢复，实际上不是
- **建议：**
  - 明确区分“持久化输入值”和“UI 选择器状态”
  - 为 choice 字段增加正反向编码/解码层

### 3.5 多层自定义热参数绕过统一校验，直接抛原生异常【严重度：中】

- **位置：**
  - `app/ui/pages/bolt_page.py:1936`
  - `app/ui/pages/bolt_page.py:1944`
  - `app/ui/pages/bolt_page.py:1988`
- **现象：**
  - 多层 `alpha` 直接 `float(alpha_w.text().strip())`
  - 留空后抛的是原生 `ValueError`
- **复现证据：**
  - 双层被夹件、`check_level=thermal`
  - 第一层材料切到“自定义”但不填 `alpha`
  - `_build_payload()` 抛出：
    - `ValueError: could not convert string to float: ''`
- **影响：**
  - 用户得到的是“计算异常”，不是字段级输入提示
  - 与页面其余字段统一的 `InputError` 体验不一致
- **建议：**
  - 多层字段走统一的字段解析与错误封装
  - 明确报出“第 N 层热膨胀系数不能为空”

### 3.6 流程图详情页每次计算都会重复堆积控件【严重度：中】

- **位置：**
  - `app/ui/pages/bolt_page.py:2007`
  - `app/ui/pages/bolt_flowchart.py:364`
- **现象：**
  - 每次 `_calculate()` 后都再次调用 `build_input_echo()`
  - 但 `build_input_echo()` 不清理旧控件
- **复现证据：**
  - `R0` 页输入布局控件数：
    - 初始：`0`
    - 第 1 次计算后：`54`
    - 第 2 次计算后：`108`
- **影响：**
  - 重复内容堆积
  - 页面越算越长、越算越慢
- **建议：**
  - 首次构建后只更新 label
  - 或在重建前清空 `_input_layout`

### 3.7 动态提示与实际说明栏不同步，存在陈旧/无效配置【严重度：低】

- **位置：**
  - `app/ui/pages/bolt_page.py:1383`
  - `app/ui/pages/bolt_page.py:1389`
  - `app/ui/pages/bolt_flowchart.py:13`
  - `app/ui/pages/bolt_page.py:429`
- **现象：**
  - `_on_tightening_method_changed()` 和 `_on_position_changed()` 只更新 `tooltip`
  - `self._widget_hints` 未同步，底部说明栏仍显示旧文案
  - `summary_key` 配置没有实际读取路径
  - `tightening_method` 字段说明仍写“首版用于记录，不参与算法分支”，但现在已经参与 R5 和 warning
- **影响：**
  - 用户看到的帮助信息与实际逻辑不一致
  - 留有无效配置，增加维护噪音
- **建议：**
  - 动态提示统一更新 `tooltip + _widget_hints`
  - 删除未用配置或真正接入
  - 修正文案，避免把真实参与计算的字段写成“仅记录”

---

## 四、参数引用与前后逻辑检查

### 4.1 已正确接入计算的关键链路

- `joint_type`：参与 core 输出说明、嵌入界面数、R7 注释
- `tightening_method`：参与 `k_tau` 和 αA 范围 warning
- `surface_treatment`：参与疲劳 `sigma_ASV`
- `basic_solid` / `auto_compliance` / `D_A` / `E_bolt` / `E_clamped`：参与自动柔度建模
- `surface_class`：参与嵌入损失自动估算
- `part_count` / `layers` / `layer_thermals`：参与多层柔度与多层热损失

### 4.2 仍属于“UI 记录”或“仅提示”的字段

- `operating.setup_case`
- `introduction.position`
- `bearing.bearing_material`
- `fastener.grade`
- `operating.bolt_material`
- `operating.clamped_material`
- `clamped.layer_n.material`
- `introduction.eccentric_clamp`
- `introduction.eccentric_load`

说明：

- 其中材料类 choice 并非直接进入 payload，而是通过联动把 `Rp02` 或 `alpha` 写入数值字段
- `introduction.position` 目前只影响提示文案，不影响 `n`
- 偏心字段仍为占位禁用状态

---

## 五、工况覆盖情况

### 5.1 当前已覆盖

- 常规链路：R3 / R4 / R5
- 可选：R7 支承面压强
- 热损失：单层与多层简化估算
- 疲劳：简化 Goodman + `sigma_ASV` 查表
- 柔度：手动顺从度、手动刚度、自动建模、单层/多层

### 5.2 当前未覆盖或只做了简化

- 偏心/弯矩工况
- 螺纹脱扣强度
- 完整疲劳谱和更复杂载荷历程
- 通孔连接双侧不同支承几何
- 热工况下更完整的材料/边界校验

结论：

- 从“能算”角度已经具备主干链路
- 从“工程可放心复用”角度，仍需先修复 UI 状态、输入持久化和 R5 展示语义问题

---

## 六、无效代码与可优化点

### 6.1 可判定为无效或低价值残留

- `app/ui/pages/bolt_flowchart.py` 中 `summary_key`
- `app/ui/pages/bolt_page.py` 中已失真的“仅记录/不参与算法”文案

### 6.2 可立即优化

- 为 `bolt_page.py` 增加 headless UI 测试
- 将 choice 字段的持久化改成规范值，而不是显示文本
- 多层字段统一纳入 `InputError` 封装
- R5 摘要与报告统一使用等效应力语义
- 流程图详情页改成“构建一次 + 更新多次”

---

## 七、建议修复顺序

1. 修复 R5 摘要/报告引用错误，避免错误结论对外输出
2. 修复输入条件保存/加载链路，先打通标准工况 round-trip
3. 修复自定义热膨胀系数校验，去掉静默钢默认值回退
4. 修复多层自定义参数异常类型，统一到 `InputError`
5. 修复流程图详情页重复渲染
6. 补齐 `tests/ui/test_bolt_page.py`，把以上问题固化成回归测试

---

## 八、审查结论

螺栓页面当前最大的风险不是公式主链，而是“页面状态/展示语义/输入持久化”三者没有完全对齐。  
如果先修完本报告中的前 4 项问题，再补 UI 回归测试，当前模块的可信度会明显上一个台阶。
