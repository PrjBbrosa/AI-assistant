# 压力-载荷曲线采样参数（curve_points / curve_force_scale）

**一句话**：控制结果可视化的 F→p0 曲线的点数和横轴范围；仅影响绘图，不影响 p0 数值本身。

**怎么理解**：

赫兹公式 p0 是载荷 F 的显式函数：线接触 p0 ∝ √F，点接触 p0 ∝ F^(1/3)。为了直观展示"如果载荷增加到 1.3 / 1.5 / 2 倍，p0 会高到哪里"，工具在 `[0, F × 倍率]` 区间内等步长采样并计算每个点的 p0，在结果页画一条曲线。

两个可调参数：

- **采样点数 `curve_points`**：在 `[0, F·scale]` 区间采样多少个等距点；有效范围 11–201，默认 41
- **载荷上限倍率 `curve_force_scale`**：曲线终点载荷相对设计载荷 F 的比值；有效范围 1.05–2.0，默认 1.30

**本工具实现** —— 钳位行为（`core/hertz/calculator.py:153-156`、`178-185`）：

```python
_curve_points_raw = int(float(options.get("curve_points", 41)))
curve_points = max(11, min(201, _curve_points_raw))

_force_scale_raw = float(options.get("curve_force_scale", 1.30))
force_scale = max(1.05, min(2.0, _force_scale_raw))
```

**超出范围时**：
- `curve_points < 11` → 强制钳位到 11，追加 warning："curve_points 已钳位至 11（原输入 X）"
- `curve_points > 201` → 钳位到 201，同上
- `curve_force_scale < 1.05` → 钳位到 1.05（因为 1.0 意味着曲线只有起点 = 设计点，毫无意义）
- `curve_force_scale > 2.0` → 钳位到 2.0（过大的比例会把曲线拉得很稀疏，反而看不清设计点附近）

被钳位的生效值回显在 `result["options"]` 中，UI / 报告据此展示曲线。

**采样节点生成**（`calculator.py:159-162`）：

```python
for i in range(curve_points):
    f_i = normal_force * force_scale * i / (curve_points - 1)
    f_i = max(f_i, 1e-6)   # 防止 i=0 时 f=0 引发除零
```

所以 i = 0 时 f ≈ 0（但用 1e-6 防止除零），i = curve_points - 1 时 f = F × scale。每个 f_i 都按当前模式（线 / 点）代回赫兹公式得到 p0_i。

**曲线形状解读**：

| 模式 | p0 ∝ | 曲线形状 | 载荷翻倍 p0 增加 |
| ---- | ---- | -------- | ---------------- |
| 线接触 | √F | 根号型（凹向下） | +41% |
| 点接触 | F^(1/3) | 立方根型（更平缓） | +26% |

曲线上会标注"设计点"（当前 F 对应的 p0），方便对比其他载荷。若曲线在 F × scale 处仍低于 [p0]，说明有较大载荷裕量；若曲线在设计点之后快速穿越 [p0] 线，说明工况对载荷敏感。

**典型使用**：

- 想看"如果极限工况瞬间载荷涨 50%" → 设 scale = 1.5
- 想看"是否接近线性关系（对比 √F / F^(1/3)）" → 提高 curve_points 到 101 或更多
- 默认 (41, 1.30) 已适用绝大多数常规设计复核

**常见坑**：

- **以为调大 curve_points 能让 p0 计算更精确**：p0 的精度由赫兹公式本身决定，曲线仅用于可视化；采样密度不影响关键结论
- **把 scale 当成"安全系数"填**：scale 只是曲线横轴上限倍率，与校核 PASS/FAIL 无关
- **填 scale = 1.0 期望"只画设计点"**：代码会钳位到 1.05 并给 warning；若只想要单点，直接看结果页 metrics 即可
- **填 curve_points 为小数（如 "50.5"）**：代码用 `int(float(...))` 截断为 50，不是四舍五入

**出处**：本参数为工具自身的绘图选项，不对应任何工程标准。
