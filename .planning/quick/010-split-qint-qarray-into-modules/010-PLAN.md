---
phase: quick
plan: 010
type: execute
wave: 1
depends_on: []
files_modified:
  - src/quantum_language/qarray.pyx
  - src/quantum_language/_qarray_utils.py
autonomous: true

must_haves:
  truths:
    - "All existing tests pass after refactoring"
    - "qarray public API unchanged (imports, class, methods)"
    - "qarray.pyx is shorter and focused on the cdef class"
  artifacts:
    - path: "src/quantum_language/_qarray_utils.py"
      provides: "Extracted helper functions for qarray"
      contains: "_infer_width"
    - path: "src/quantum_language/qarray.pyx"
      provides: "Quantum array cdef class (slimmed down)"
      contains: "cdef class qarray"
  key_links:
    - from: "src/quantum_language/qarray.pyx"
      to: "src/quantum_language/_qarray_utils.py"
      via: "Python import"
      pattern: "from ._qarray_utils import"
---

<objective>
Extract free helper functions from qarray.pyx into a separate pure-Python module, reducing qarray.pyx to focus on the cdef class definition only.

Purpose: qarray.pyx (1115 lines) has ~160 lines of standalone helper functions that are pure Python (no cdef/C types). Extracting them improves readability and separates concerns. qint.pyx (2792 lines) CANNOT be split because Cython forbids splitting `cdef class` bodies across files (confirmed in quick-004).

Output: _qarray_utils.py with extracted helpers, slimmer qarray.pyx, all tests passing.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@src/quantum_language/qarray.pyx
@src/quantum_language/qarray.pxd
@src/quantum_language/__init__.py
@.planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extract qarray helper functions to _qarray_utils.py</name>
  <files>
    src/quantum_language/_qarray_utils.py
    src/quantum_language/qarray.pyx
  </files>
  <action>
1. Create `src/quantum_language/_qarray_utils.py` containing these five functions extracted verbatim from qarray.pyx:
   - `_infer_width(values, default_width=8)` (lines 17-37)
   - `_detect_shape(data)` (lines 40-76)
   - `_flatten(data)` (lines 79-99)
   - `_reduce_tree(elements, op)` (lines 102-134)
   - `_reduce_linear(elements, op)` (lines 137-157)

   These are all pure Python functions with no Cython types. They only reference `INTEGERSIZE` from `_core`, so `_qarray_utils.py` needs: `from ._core import INTEGERSIZE` (Python-level import, not cimport).

2. In `qarray.pyx`, remove the five extracted function definitions (lines 17-157) and replace with:
   ```
   from ._qarray_utils import _infer_width, _detect_shape, _flatten, _reduce_tree, _reduce_linear
   ```
   Keep the existing `from ._core cimport INTEGERSIZE` in qarray.pyx since the cdef class body still uses INTEGERSIZE directly (line 216).
   Keep the existing `from ._core import _get_qubit_saving_mode` since the class methods use it.

3. Do NOT modify qint.pyx. It cannot be split (Cython limitation, confirmed in quick-004). Add a comment at the top of qint.pyx noting this:
   ```python
   # NOTE: This file is intentionally large (~2800 lines). Cython cdef classes
   # cannot be split across files (no include/mixin support in cdef class bodies).
   # See .planning/quick/004-consolidate-qint-pxi-includes-to-remove-/004-SUMMARY.md
   ```
  </action>
  <verify>
Run `cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum\ Programming\ Language/Quantum_Assembly && pip install -e . 2>&1 | tail -5` to verify Cython compilation succeeds.

Then run `python -c "from quantum_language.qarray import qarray; from quantum_language._qarray_utils import _infer_width, _detect_shape; print('imports OK')"` to verify module is importable.
  </verify>
  <done>
_qarray_utils.py exists with 5 extracted functions. qarray.pyx imports from _qarray_utils instead of defining them inline. Cython compilation succeeds.
  </done>
</task>

<task type="auto">
  <name>Task 2: Verify all tests pass</name>
  <files>
    (no files modified -- verification only)
  </files>
  <action>
Run the full test suite to confirm no regressions from the refactoring. Focus especially on:
- `tests/test_qarray.py` (core qarray tests)
- `tests/test_qarray_elementwise.py` (element-wise operations)
- `tests/test_qarray_reductions.py` (all/any/parity/sum using the extracted _reduce_tree/_reduce_linear)
- `tests/test_qarray_mutability.py` (mutation tests)

If any test fails, fix the import or extraction issue. Common pitfalls:
- `_get_qubit_saving_mode` must stay importable in qarray.pyx (it's used in `all()`, `any()`, `parity()`, `sum()` methods)
- `INTEGERSIZE` needs both `cimport` (for cdef class C-level access) and the Python-level availability via `_qarray_utils.py`
  </action>
  <verify>
Run `cd /Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum\ Programming\ Language/Quantum_Assembly && python -m pytest tests/test_qarray*.py -v 2>&1 | tail -20` to see qarray-specific test results.

Then run `python -m pytest tests/ -x -q 2>&1 | tail -10` for full suite.
  </verify>
  <done>
All qarray tests pass. Full test suite shows no regressions (same pass/fail count as before refactoring).
  </done>
</task>

</tasks>

<verification>
- `_qarray_utils.py` contains exactly 5 functions: `_infer_width`, `_detect_shape`, `_flatten`, `_reduce_tree`, `_reduce_linear`
- `qarray.pyx` imports these functions instead of defining them
- `qarray.pyx` is ~160 lines shorter (from ~1115 to ~960)
- `qint.pyx` has explanatory comment about why it cannot be split
- All tests pass
- `pip install -e .` compiles without errors
</verification>

<success_criteria>
qarray.pyx reduced by extracting pure-Python helpers. All tests pass. qint.pyx documented as intentionally monolithic (Cython limitation).
</success_criteria>

<output>
After completion, create `.planning/quick/010-split-qint-qarray-into-modules/010-SUMMARY.md`
</output>
