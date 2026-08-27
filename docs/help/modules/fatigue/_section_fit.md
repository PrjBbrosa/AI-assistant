# P-S-N 拟合

首版模型为 `log10(N)=a-b*log10(Sa,eq)+epsilon`，其中 `epsilon` 服从均值为零、标准差为 `s` 的正态分布。

主方法在似然函数中分别使用断裂概率密度和 runout 存活概率。MRR/Johnson 和仅断裂 OLS 只作为对照。全 runout 只形成寿命下限；高 runout 级与相邻失效级最多形成疲劳强度区间证据。

**出处**：ISO 12107:2012
