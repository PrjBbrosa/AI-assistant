# 过盈配合粗糙度修正依据（DIN/ISO）

## 1) 本版采用的修正模型
- 有效过盈：`U_w = U_o - s`
- 粗糙度压平量：`s = k * (Rz_s + Rz_h)`
- 其中：
  - `U_o` 为输入（几何）过盈量
  - `U_w` 为参与压力计算的有效过盈量
  - `Rz_s/Rz_h` 分别为轴与轮毂表面粗糙度（Rz）
  - `k` 为压平系数

## 2) 参数与版本选择
- `k = 0.4`：对应 DIN 7190-1:2017 的版本说明（新版本）
- `k = 0.8`：对应旧版 DIN 7190（如 2001 版）传统处理
- 工具实现为可切换：
  - `DIN 7190-1:2017（k=0.4）`
  - `DIN 7190:2001（k=0.8）`
  - `自定义 k`

## 3) 粗糙度参数输入建议
- 优先输入 `Rz`（检测报告/图纸若给出 Rz）
- 若只有 `Ra`，可按 DIN 7190 相关手册中的参考区间换算到 Rz（工程近似）
- 本版未自动强制 Ra→Rz 换算，避免引入单一经验比值造成误差

## 4) 相关摩擦参数参考
- 过盈配合的静摩擦系数/压装摩擦系数建议值按 DIN 7190 相关范围取值，并结合润滑与材料配对修正
- 本工具保留 `mu_static` 与 `mu_assembly` 分离输入（与 DIN 7190 工程用法一致）

## 5) 主要来源链接
- eAssistant Handbook, Chapter 15（Interference fit）  
  https://www.eassistant.eu/fileadmin/dokumente/eassistant/etc/HTMLHandbuch/en/eAssistantHandbch15.html
- DIN 7190-1:2017 产品页（含与旧版差异说明）  
  https://www.dinmedia.de/en/standard/din-7190-1/253031296
- DIN 7190:2001 产品页（旧版）  
  https://www.dinmedia.de/en/standard/din-7190/34068655
- ISO 21920-2:2021（现行表面纹理轮廓参数体系）  
  https://www.iso.org/standard/67066.html
- ISO 4287:1997（历史版本，已被 ISO 21920 系列取代）  
  https://www.iso.org/standard/10132.html
