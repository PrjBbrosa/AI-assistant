# 过盈配合公开 Benchmark 差异说明（2026-03-19）

## 目的

说明本仓库中的过盈配合示例、公开 eAssistant / DIN 7190 案例，以及当前实现边界之间的差异，避免把“相似案例”误读成“一对一数值复现”。

## 当前实现边界

当前仓库中的过盈配合主模型当前支持：

- 实心轴
- 空心轴
- 厚壁轮毂
- 线弹性
- 均匀接触压力
- 常摩擦系数
- 弯矩附加压强按 `QW=0` 保守简化
- 不把离心力 / 转速耦合进主校核
- 不把服役温度耦合进主校核

说明：
- DIN 7190 / 同类工具的理论能力并不止于此。
- 本说明只强调“当前仓库实现边界”，不是标准边界。

## eAssistant 公共案例为什么不能直接拿来做一对一 benchmark

eAssistant 公共 `Presssitz_en.pdf` 案例虽然与本仓库示例在以下参数上非常接近：

- `d = 50 mm`
- `L = 20 mm`
- `D = 95 mm`
- `T = 80 Nm`
- `F = 125 N`
- `KA = 1.2`
- 推荐 fit：`H7/s6`

但它还包含当前实现尚未纳入主模型的条件，例如：

- `speed = 2000 min^-1`
- `operating temperature = 25 °C`

因此：

- eAssistant 公共案例的数值结果不能直接当成当前仓库的严格 benchmark。
- 如果要做真正的一对一复现，至少需要：
  - 转速 / 离心力耦合
  - 服役温度耦合

## 对本仓库示例文件的解释

`examples/interference_case_01.json` 应理解为：

- 一个用于演示优选配合、装配流程和 Step 5 fretting 评估的工程示例
- 而不是 eAssistant 公共案例的等价复现

## 使用建议

- 若目标是检查当前实现是否“逻辑自洽”，应优先看：
  - 本仓库 tests
  - `docs/review/2026-03-18-interference-fit-deep-review.md`
- 若目标是和外部工具做一对一数值对比，必须先确认：
  - 几何边界是否一致
  - 是否包含空心轴
  - 是否包含温度 / 转速 / 更完整接触假设

## 关联文档

- `docs/review/2026-03-18-interference-fit-deep-review.md`
- `docs/superpowers/specs/2026-03-19-interference-fit-fretting-step-design.md`
