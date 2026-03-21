# Input Condition Actions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add persistent input-condition save/load actions to all engineering pages and split the top action bar into left-side input management controls and right-side test-case buttons.

**Architecture:** Introduce one shared UI helper for JSON input-condition persistence under the project `saved_inputs/` directory, then wire each page to that helper while keeping each page's existing payload/build and field-application logic. Extend the shared chapter-shell action bar to support left/right grouping so the two newer pages reuse the same layout, and mirror that layout in the bolt page without refactoring its full page shell.

**Tech Stack:** Python 3, PySide6, unittest

---

### Task 1: Add failing tests for shared input-condition persistence

**Files:**
- Create: `tests/ui/test_input_condition_store.py`
- Modify: none

**Step 1: Write the failing test**

```python
import json
import tempfile
import unittest
from pathlib import Path

from app.ui.input_condition_store import build_saved_inputs_dir, write_input_conditions, read_input_conditions


class InputConditionStoreTests(unittest.TestCase):
    def test_build_saved_inputs_dir_uses_project_saved_inputs_folder(self) -> None:
        root = Path('/tmp/project-root')
        self.assertEqual(build_saved_inputs_dir(root), root / 'saved_inputs')

    def test_write_and_read_input_conditions_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            out_path = out_dir / 'case.json'
            payload = {'geometry': {'d': 40.0}, 'loads': {'f': 1200.0}}

            write_input_conditions(out_path, payload)
            loaded = read_input_conditions(out_path)

            self.assertEqual(loaded, payload)
```

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: FAIL with `ModuleNotFoundError` for `app.ui.input_condition_store`

**Step 3: Write minimal implementation**

Create `app/ui/input_condition_store.py` with the tested helpers plus thin `QFileDialog` wrappers used by the pages.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_input_condition_store.py app/ui/input_condition_store.py
 git commit -m "feat: add shared input condition storage helpers"
```

### Task 2: Add shared left/right action-bar support for chapter pages

**Files:**
- Modify: `app/ui/pages/base_chapter_page.py`
- Test: `tests/ui/test_input_condition_store.py`

**Step 1: Write the failing test**

Add a small test that instantiates `BaseChapterPage`, adds one left action and one right action, and asserts they land in separate layout groups in insertion order.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: FAIL because `BaseChapterPage` has no right-group API yet

**Step 3: Write minimal implementation**

Split the action bar into left and right containers, keep stretch between them, and expose `add_action_button(..., side="left")`.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/ui/test_input_condition_store.py app/ui/pages/base_chapter_page.py
 git commit -m "refactor: support split action groups on chapter pages"
```

### Task 3: Wire save/load input actions into the interference-fit page

**Files:**
- Modify: `app/ui/pages/interference_fit_page.py`
- Modify: `app/ui/input_condition_store.py`
- Test: `tests/ui/test_input_condition_store.py`

**Step 1: Write the failing test**

Add a helper-level test if needed for dialog default directory/name handling; keep page logic thin by relying on helper behavior.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: FAIL on the new helper expectation

**Step 3: Write minimal implementation**

Add `保存输入条件` / `加载输入条件` on the left, move `测试案例 1/2` to the right, persist `_build_payload()` to JSON, and load JSON back through a shared page method that reuses current field mapping updates plus material/roughness sync.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/ui/pages/interference_fit_page.py app/ui/input_condition_store.py tests/ui/test_input_condition_store.py
 git commit -m "feat: add input condition actions to interference page"
```

### Task 4: Wire save/load input actions into the hertz-contact page

**Files:**
- Modify: `app/ui/pages/hertz_contact_page.py`
- Test: `tests/ui/test_input_condition_store.py`

**Step 1: Write the failing test**

Only add test coverage if helper behavior expands; otherwise rely on existing helper coverage and proceed with thin integration.

**Step 2: Run test to verify it fails**

Run helper tests only if changed.

**Step 3: Write minimal implementation**

Mirror the same left/right action layout and JSON save/load flow, then trigger existing material/mode/diagram refreshes after loading.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/ui/pages/hertz_contact_page.py
 git commit -m "feat: add input condition actions to hertz page"
```

### Task 5: Wire save/load input actions into the bolt page

**Files:**
- Modify: `app/ui/pages/bolt_page.py`
- Test: `tests/ui/test_input_condition_store.py`

**Step 1: Write the failing test**

Only add test coverage if new helper behavior is needed.

**Step 2: Run test to verify it fails**

Run helper tests only if changed.

**Step 3: Write minimal implementation**

Rebuild the bolt-page action row into left/right groups, add `保存输入条件` / `加载输入条件`, rename sample buttons to `测试案例 1/2`, and reuse the page's existing payload and load logic.

**Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.ui.test_input_condition_store -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/ui/pages/bolt_page.py
 git commit -m "feat: add input condition actions to bolt page"
```

### Task 6: Verify end-to-end behavior and update docs if needed

**Files:**
- Modify: `README.md`
- Verify: `tests/core/interference/test_calculator.py`
- Verify: `tests/core/hertz/test_calculator.py`
- Verify: `tests/ui/test_input_condition_store.py`

**Step 1: Run targeted tests**

Run: `python3 -m unittest tests.ui.test_input_condition_store tests.core.interference.test_calculator tests.core.hertz.test_calculator -v`
Expected: PASS

**Step 2: Update README if user-visible behavior changed materially**

Document `saved_inputs/` persistence and the renamed `测试案例` controls if warranted.

**Step 3: Smoke-check app startup if practical**

Run: `python3 app/main.py`
Expected: app opens without import/runtime errors

**Step 4: Commit**

```bash
git add README.md
 git commit -m "docs: document input condition persistence"
```
