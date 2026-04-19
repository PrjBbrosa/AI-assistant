# Stage 1 Adversarial Review Report
Date: 2026-04-19
Reviewer: codex-rescue (adversarial mode)
Scope: Stage 1 蜗杆 pilot + GUIDELINES 定稿

Summary: Stage 1 has multiple template-level defects that will multiply into later modules: Method A/C behavior is documented incorrectly, `_section_operating.md` contains unit-wrong formulas, several files claim DIN 3996 fidelity beyond the calculator, and the reusable term pool already hides gear-only assumptions behind generic filenames.

## 1. Content Comprehensibility
Sampled term files: `allowable_contact_stress.md`, `allowable_root_stress.md`, `pressure_angle.md`. Sampled section files: `_section_load_capacity.md`, `_section_geometry.md`.

### [P0] Sampled Articles Still Assume Expert Shorthand
- **Problem**: The sampled help content is not reliably newbie-friendly. It drops readers straight into symbol stacks and standard shorthand without first explaining what each factor means in plain Chinese.
- **Location**: `docs/help/terms/allowable_contact_stress.md:7-9`; `docs/help/terms/allowable_root_stress.md:7-9`; `docs/help/terms/pressure_angle.md:11-13`; `docs/help/modules/worm/_section_load_capacity.md:7-17`; `docs/help/modules/worm/_section_geometry.md:7-9`
- **Evidence**: The articles use raw expressions like `σHP = σH,lim · ZN · ZL · ZR · ZX / SH`, `σFP = σF,lim · YN · YX · Yδ · YRrelT / SF`, and `ZA/ZN/ZI/ZK 不同齿形蜗杆...`; the load-capacity section introduces `σH / σF / KHα / KHβ` as if the reader already knows every symbol.
- **Recommendation**: For P0 terms, explain each symbol in words before showing the compressed formula. For section pages, start with "when you change this field, what happens" and move coefficient names to a second sentence or a small glossary line.

## 2. Formula Correctness
Internal cross-checks were done against `core/worm/calculator.py`. Cannot verify against original DIN standard; any DIN-conformance claim still needs human verification against the actual standard text.

### [P0] `_section_basic.md` Describes Method A/C Behavior Incorrectly
- **Problem**: The basic-section help says choosing Method A or C will not change calculation results. That is false for the current implementation.
- **Location**: `docs/help/modules/worm/_section_basic.md:27-31`; `app/ui/pages/worm_gear_page.py:51-55`; `core/worm/calculator.py:399-401,504-511,716-726`
- **Evidence**: `_section_basic.md` says `选择 A 或 C 在当前实现中不会改变计算结果`; the calculator rejects Method C outright and applies a Method-A-specific efficiency/contact-stress adjustment.
- **Recommendation**: Rewrite the section to match reality exactly: Method B is the default path, Method A applies a simplified alternate treatment, Method C is currently unavailable and should either be disabled in the UI or labeled as unsupported.

### [P0] `_section_operating.md` Contains Unit-Wrong and Direction-Wrong Formulas
- **Problem**: The operating section's formulas do not match the implemented equations, and at least two are dimensionally wrong if the page inputs are used as documented.
- **Location**: `docs/help/modules/worm/_section_operating.md:7,20-24`; `core/worm/calculator.py:441-468,524-526`
- **Evidence**: The doc says `Ft1 = 2·T1/d1` and `vs = π·d1·n1 / (60·cos γ)`, but the calculator uses `2000.0 * torque / diameter_mm` and `/60000.0 / cos(gamma)` for mm-based diameters. The doc also says `Ft2 = Ft1·tan(γ + ρ')`, while the code comments and equations use `F_t1 = F_a2 = F_t2·tan(γ + φ')`.
- **Recommendation**: Rewrite the formulas with explicit units. If `T` is in `N·m` and `d` is in `mm`, include the `2000/d` and `60000` conversions. Also fix the force-direction relation so the help page matches the implemented force decomposition.

### [P0] Method-B Docs Overclaim DIN 3996 Fidelity Relative to the Code
- **Problem**: The Stage 1 docs present the page as if it implements DIN 3996 Method B directly, but the calculator explicitly says it is only a simplified "Method B style" subset with Hertz-line-contact and cantilever-beam approximations. Cannot verify against original DIN standard.
- **Location**: `docs/help/modules/worm/din3996_method_b.md:34-50`; `docs/help/modules/worm/_section_load_capacity.md:20-22`; `core/worm/calculator.py:58-60,479-493,716-726`
- **Evidence**: `din3996_method_b.md` says `已实现：Method B 单点解析法...钢-青铜、钢-塑料常见材料副的许用应力库`, while the code assumptions say `不是完整 DIN 3996 / ISO/TS 14521`, `齿面应力采用线接触 Hertz 近似`, `齿根应力采用等效悬臂梁近似`; the built-in material allowables are only for `PA66` and `PA66+GF30`.
- **Recommendation**: Stop presenting this as implemented DIN 3996 Method B. Either relabel it consistently as a project-specific simplified estimator, or rewrite the docs around the actual implemented equations and add the exact sentence `Cannot verify against original DIN standard` wherever primary-standard verification has not been done.

Minor note: `d1 = q·m` and `tan γ = z1/q` do match `core/worm/calculator.py:153-158`. The Stage 1 materials handle profile shift by keeping `d2 = z2·m` and adding `(x1+x2)·m` to center distance; cannot verify against original DIN standard whether that terminology matches DIN 3975's reference/operating-diameter definitions.

## 3. Typical Value Credibility

### [P1] Typical-Value Sections Mix Incompatible Contexts and Omit Scope Boundaries
- **Problem**: The allowable-stress term pages mix worm-wheel values, generic gear values, and the current plastic-only pilot context in one list, without telling the user which rows are actually relevant to this page. This looks suspicious and needs scoping, even if some raw numbers may be plausible.
- **Location**: `docs/help/terms/allowable_contact_stress.md:15-23`; `docs/help/terms/allowable_root_stress.md:15-24`; `app/ui/pages/worm_gear_page.py:134-140,201-202`
- **Evidence**: The help attached to `许用齿面应力` / `许用齿根应力` lists bronze worm-wheel values, carburized-steel gear values, and plastic values together, while the current UI only offers plastic wheel materials (`PA66`, `PA66+GF30`, `POM`, `PA46`, `PEEK`).
- **Recommendation**: Split "current worm pilot usable values" from "generic background values", and explicitly label which table applies to the current module. If CN/DE material-grade or lubricant-series differences are intentionally omitted, say so explicitly instead of leaving the reader to infer.

## 4. GUIDELINES Operability

### [P0] `GUIDELINES.md` Does Not Give a Safe Workflow for Standards You Cannot Open
- **Problem**: The guidelines require authoritative DIN/VDI/ISO clause citations for P0 content, but they do not define what an agent must do when the original standard is unavailable or when the implementation is only DIN-inspired. That gap is exactly how false authority gets written.
- **Location**: `docs/help/GUIDELINES.md:58-60,117-138,149-153`
- **Evidence**: The file says `出处：必须标 DIN/VDI/ISO 条款编号，无法确认时写"无公开权威出处"` and later says `P0 单篇质量门槛 ... 必须有 DIN/VDI/ISO 条款出处`, but never says how to label implementation-only formulas, paywalled standards, or unverifiable clause numbers.
- **Recommendation**: Add a mandatory source-truthfulness rule: if the original standard was not inspected, the article must say `Cannot verify against original DIN standard`. Also add a separate rule for "implementation description" versus "standard description", so later stages cannot blur the two.

## 5. Term Naming Foresight

### [P0] Generic Filenames Already Hide Gear-Only Semantics
- **Problem**: Several generic-looking term names are not actually generic. If they are reused as planned, later modules will inherit worm/gear assumptions under names that look module-neutral.
- **Location**: `docs/help/GUIDELINES.md:99-103`; `docs/help/terms/application_factor_ka.md:3-21`; `docs/help/terms/pressure_angle.md:11-24`; `docs/help/terms/lubrication.md:9-25`; `docs/help/terms/profile_shift.md:15-17`
- **Evidence**: `GUIDELINES.md` marks `terms/application_factor_ka` as reusable in interference/spline, but the article defines KA as multiplying `齿轮名义载荷` and points to DIN 3990 / ISO 6336 gear tables. `pressure_angle.md` is mostly involute/worm-gear language (`ZA/ZN/ZI/ZK`). `lubrication.md` is named generically but all ranges are worm sliding-speed rules.
- **Recommendation**: Rename or split now, before five more modules inherit this debt. Examples: `gear_application_factor_ka`, `gear_pressure_angle`, `worm_lubrication_mode`, `gear_profile_shift`. If you want true cross-module reuse, rewrite them as neutral umbrella pages with scoped subsections per module family.

## 6. Help_ref Coverage

### [P1] Coverage Has Both Missing Help and Wrong Help Targets
- **Problem**: Several conclusion-critical inputs still have no help, `_section_advanced.md` is orphaned, and some attached help pages explain a different context from the page field they are attached to.
- **Location**: `docs/help/GUIDELINES.md:64-79`; `app/ui/pages/worm_gear_page.py:120,176-183,203-207,299-330,571-576`; `docs/help/modules/worm/_section_advanced.md:1-26`; `docs/help/terms/kh_alpha.md:21`; `docs/help/terms/kh_beta.md:11,21`
- **Evidence**: `geometry.center_distance_mm`, `advanced.friction_override`, `load_capacity.required_contact_safety`, and `load_capacity.required_root_safety` have no `help_ref` even though §6 says core inputs affecting conclusions should have one. `_section_advanced.md` exists but nothing points to `modules/worm/_section_advanced`. `kh_alpha.md` / `kh_beta.md` themselves say worm-gear checks usually do not input these separately, yet the worm page requires manual entry for them.
- **Recommendation**: Add help for center distance, friction coefficient override, and target safety factors; either wire the advanced-section doc into the geometry page or delete it; replace `terms/kh_alpha` and `terms/kh_beta` with worm-page-specific explanations of why this pilot asks the user for manual override coefficients.

## 7. Subtitle Rewrite Style

### [P1] The Subtitles Are Longer, but Still Sound Like Implementation Notes
- **Problem**: The rewritten subtitles are less cryptic than before, but several still read like spec text or field inventories rather than user-goal language.
- **Location**: `app/ui/pages/worm_gear_page.py:303,317,326,373,573`
- **Evidence**: Examples include `选用 DIN 3996 的哪一种方法`, `自动带入弹性模量和许用应力`, `这些值直接影响齿面应力与动载系数 Kv 的计算`, `派生尺寸（分度圆、齿顶/齿根圆）`, and `基于 DIN 3996 Method B / ISO 14521`.
- **Recommendation**: Rewrite them around what the user is deciding and why it matters now. Keep standards and coefficient names secondary. The target tone is "what you are choosing here" and "what changes if you choose wrong", not "which internal formula family this page uses".

## P0 Summary
- Sampled term and section articles still assume expert shorthand instead of explaining symbols in newbie language. (`docs/help/terms/allowable_contact_stress.md`, `allowable_root_stress.md`, `pressure_angle.md`; `_section_load_capacity.md`, `_section_geometry.md`)
- `_section_basic.md` states that Method A/C do not change results, but Method C is rejected by the calculator and Method A changes outputs. (`docs/help/modules/worm/_section_basic.md:27-31`)
- `_section_operating.md` contains force/speed formulas that do not match the implemented equations or units. (`docs/help/modules/worm/_section_operating.md:7,20-24`)
- The Method-B docs overclaim DIN 3996 fidelity relative to the actual simplified calculator; human DIN verification is still required. (`docs/help/modules/worm/din3996_method_b.md:34-50`)
- `GUIDELINES.md` has no safe rule for unverifiable standards or implementation-only formulas, which invites false authority in later modules. (`docs/help/GUIDELINES.md:58-60,117-138,149-153`)
- Several generic term filenames already hide gear-only semantics and will break reuse across later modules. (`docs/help/terms/application_factor_ka.md`, `pressure_angle.md`, `lubrication.md`, `profile_shift.md`)

---

Test note: `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/ui/test_worm_help_wiring.py -q` could not be run because `pytest` is not installed in this environment.
