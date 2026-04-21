# Windows 启动性能优化方案

- **日期**: 2026-04-21
- **作者**: Claude(基于源码扫描)
- **状态**: 草案,待 review
- **目标**: 双击 exe 到主窗口可交互,从当前估计 **5-10 s** 降到 **< 1.5 s**

---

## 一、背景

当前桌面入口 `app/main.py` + `app/ui/main_window.py` 在启动时做了几件重活:

1. `configure_matplotlib_fonts()` 在 `QApplication` 构造之前,matplotlib 完整 import 阻塞窗口显示。
2. `MainWindow.__init__` 一次性实例化全部 6 个 page(`BoltPage` 2886 行、`WormGearPage` 1349 行等),其中 WormGearPage 会构造 3 个 matplotlib 画板。
3. `icons.py::brand_mark_pixmap(180)` 对 512×512 图像做 Python 级像素循环(262,144 次 `pixelColor/setPixelColor`)。
4. 未发现 `*.spec` / `build/` / `dist/`,推测当前使用 `pyinstaller --onefile` 默认命令,Windows 上每次启动都要解压到 `%TEMP%` 几秒。

## 二、瓶颈与收益估计

| # | 瓶颈点 | 证据位置 | 当前耗时 | 优化后 | 工作量 | 风险 |
|---|---|---|---|---|---|---|
| 1 | `--onefile` 解压开销 | 无 spec 文件 | 3-8 s | < 1 s | 1 h | 低 |
| 2 | matplotlib 在启动路径 eager import | `main.py:22`、`worm_stress_curve.py:9-12`、`latex_label.py:12-15` | 300-800 ms | 首屏 0 | 0.5 d | 低-中 |
| 3 | 6 pages 全部 eager 构造 | `main_window.py:64-78` | 400-1000 ms | ~100 ms | 0.5-1 d | 中 |
| 4 | `brand_mark_pixmap` 像素循环 | `icons.py:67-80` | 150-400 ms | < 10 ms | 20 min | 低 |
| 5 | font 配置阻塞 window.show | `main.py:22-33` | 感知 100-200 ms | 0(splash 已显示) | 10 min | 低 |

**合计感知启动时间**: ~5-10 s → < 1.5 s

## 三、优化方案(按 ROI 排序)

### 方案 A — `--onefile` 改 `--onedir` + 剪裁 Qt 插件

**改动**: 新增 `build.spec`(进仓库),不改源码。

**关键步骤**:
1. 生成初始 spec: `pyinstaller --onedir --windowed --name AI-Assistant app/main.py`
2. 手动编辑 spec,在 `Analysis(..., excludes=[...])` 加入确认不用的模块:
   - `PySide6.QtWebEngineWidgets`、`PySide6.QtWebEngineCore`、`PySide6.QtMultimedia`、`PySide6.QtQml`、`PySide6.QtQuick`、`PySide6.QtNetwork`(除非 reportlab 需要)
   - `tkinter`、`unittest`、`test`
3. `matplotlib` 后端只保留 `Agg`、`qtagg`,其他 backend 通过 `excludes` 剔除。
4. 确认 `assets/assistant_icon.ico` 和 `assistant_icon.png` 通过 `datas=[...]` 显式打包。
5. 发布打包为文件夹后,用 Inno Setup 做标准 Windows 安装包(脚本进仓库 `packaging/installer.iss`)。

**验证**:
- 冷启动时间用 `Measure-Command { .\AI-Assistant.exe }` 粗测 3 次取均值。
- 文件夹大小对比 `--onefile` 版(预期持平或略小)。
- 每个模块点进去能看到图表、报告能导出。

**回滚**: 保留旧的 onefile 打包命令,spec 可并存。

**风险点**:
- `excludes` 过激会导致运行时 ImportError。上线前必须在干净 Windows 机器上跑完六个模块的 smoke test。
- PyInstaller 对 `matplotlib` 的 hooks 偶尔漏资源文件,需要 `--collect-data matplotlib` 兜底。

---

### 方案 B — brand_mark 预生成 PNG

**改动**: 源码 + 新增资源文件。

**关键步骤**:
1. 写一次性脚本 `tools/bake_brand_mark.py`,读取 `assistant_icon.png`,执行当前 `icons.py::brand_mark_pixmap` 的色彩映射逻辑,输出 `app/assets/assistant_icon_sidebar.png`(已映射成暖色调)。
2. `icons.py::brand_mark_pixmap(size)` 改为直接 `QPixmap("assistant_icon_sidebar.png").scaled(size, ...)`,删掉像素循环。
3. 缓存逻辑可保留(仍按 size 缓存 scaled 结果)。

**验证**:
- 侧栏底部 brand mark 视觉与改前完全一致(像素差 < 1%)。
- 冷启动 `MainWindow.__init__` 用 `time.perf_counter` 打点对比。

**回滚**: 保留旧像素循环函数 `_brand_mark_pixmap_legacy`,必要时切回。

**风险**: 极低。纯资源 + 函数实现替换,行为一致。

---

### 方案 C — matplotlib 延迟 import

**改动**: 源码。

**关键步骤**:
1. `app/main.py` 删掉 `from app.ui.fonts import configure_matplotlib_fonts` 的顶层调用,改为在第一次需要 matplotlib 的 widget 构造前调用(或 `WormGearPage` / `LatexLabel` / `WormStressCurveWidget` 的 `__init__` 首次触发时调用,配合已有的 `_MPL_CONFIGURED` 单次标志)。
2. `app/ui/widgets/latex_label.py`、`worm_stress_curve.py` 的 `import matplotlib` 从模块顶层移入类 `__init__` 或首次使用的方法内。
3. `configure_matplotlib_fonts()` 内部的 `import matplotlib` 已经是局部的,无需改。
4. 保持 `matplotlib.use("Agg")` 在 import 之后立刻执行,避免 backend 初始化顺序问题。

**验证**:
- `python3 -c "import time; t=time.perf_counter(); from app.ui.main_window import MainWindow; print(time.perf_counter()-t)"` 对比改前改后。
- headless 测试 `QT_QPA_PLATFORM=offscreen pytest tests/ -v` 全部通过。
- 打开蜗轮页,三张图正常渲染、中文不乱码。

**回滚**: `git revert` 单 commit。

**风险**: 中。matplotlib backend 首次调用的线程/GIL 交互比较敏感,必须在 Qt 主线程触发。不要把 configure 放 `QThread` 或 `QTimer.singleShot(0, ...)` 里调画图逻辑。

---

### 方案 D — 6 pages 惰性实例化

**改动**: 源码(`main_window.py` 架构重构)。

**关键步骤**:
1. 定义 `PageFactory = Tuple[str, Callable[[], QWidget]]`,把 `self.modules` 改成 factory 列表而非实例列表。
2. `QStackedWidget` 初始只放 6 个空的 `QWidget` 占位。
3. `currentRowChanged` 回调里判断该 index 是否已构造,未构造则 lazy import + 实例化 + `stack.removeWidget(placeholder)` + `stack.insertWidget(index, real_page)`。
4. 默认首屏 = 螺栓连接,启动时立即构造 `BoltPage`,其余 5 个保持占位。

**验证**:
- 启动后立即看到 BoltPage 可交互,切换到其他模块首次有 < 300 ms 构造延迟(可接受)。
- 所有 page 的输入条件保存/加载仍正常(它们在 `__init__` 里读取 `saved_inputs/`,只要构造时刻推迟即可,语义不变)。
- 6 个模块切来切去、回到已构造页不重建。

**回滚**: `git revert`。

**风险**: 中。需要确认哪些 page 在 `__init__` 里注册了全局信号或依赖其他 page 的状态(目前扫描未发现跨 page 依赖,但需要复核 `input_condition_store` 的用法)。

---

### 方案 E — Splash Screen + 提前 window.show

**改动**: 源码(`main.py`)。

**关键步骤**:
1. `QApplication` 构造后立刻 `QSplashScreen(QPixmap("assistant_icon.png"))`,`splash.show()`。
2. `apply_theme` / `configure_matplotlib_fonts` / 字体设置全部放 splash 之后执行。
3. `MainWindow()` 构造完成后 `splash.finish(window)`。

**验证**: 用户点击图标 < 300 ms 即可看到 splash,主观感受"秒开"。

**回滚**: 删除 splash 几行即可。

**风险**: 低。纯 UI 增强。

---

## 四、建议实施顺序

| 阶段 | 内容 | 预计耗时 | 能否独立验证 |
|---|---|---|---|
| Phase 1 | 方案 B(brand_mark 预生成) + 方案 E(splash) | 1-2 h | 能 |
| Phase 2 | 方案 C(matplotlib 延迟 import) | 0.5 d | 能 |
| Phase 3 | 方案 A(onedir 打包) | 1 d(含打安装包) | 能,需 Windows 机器 |
| Phase 4 | 方案 D(pages 惰性) | 0.5-1 d | 能 |

每个 Phase 独立 commit,独立验证,独立可回滚。不建议一次性合并。

## 五、统一验证清单

每个 Phase 合并前必须全部通过:

- [ ] `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ -v` 全绿
- [ ] `python3 app/main.py` 本地能启动,6 个模块均能点开
- [ ] 螺栓模块加载 `examples/input_case_01.json` 计算通过
- [ ] 蜗轮模块图表正常渲染,中文不乱码
- [ ] 赫兹模块能导出 PDF 报告
- [ ] 启动耗时打点(`time.perf_counter` 从 `main()` 到 `window.show()` 返回)记录在 commit message
- [ ] (仅 Phase 3)在 Windows 虚拟机或实机上跑打包后的 exe

## 六、不做什么

以下项经评估 ROI 低或风险高,**本轮不动**:

- 不做 Nuitka / cx_Freeze 切换(PyInstaller 够用,切换成本高)。
- 不改 Python 版本(保持 3.12)。
- 不引入 `concurrent.futures` 做并行 page 构造(Qt widget 必须主线程构造)。
- 不预编译 .pyc(PyInstaller 已经处理)。
- 不做 AOT / mypyc(matplotlib/PySide6 兼容性未验证)。

## 七、需要用户决定的点

1. **是否接受从 onefile 切到 onedir 发布形态**? onedir 是文件夹,发布需要搭配 Inno Setup 安装包。如果坚持单文件分发,方案 A 退化为"减少 hidden imports 和 datas",收益会从 3-8 s 降到 1-2 s。
2. **Splash 图是否需要专门设计**? 直接用 `assistant_icon.png` 放大即可,还是要做一张带应用名的启动图?
3. **目标 Windows 版本**? Windows 10 / 11 差别不大;Windows 7 上 PySide6 6.8 已不支持,若需兼容要退回 6.5。

---

_本文档为规划性质,未改动任何代码或配置。实施时逐阶段创建对应 commit / PR。_
