---
phase: quick
plan: 010
subsystem: quantum-types
tags: [refactor, cython, qarray, modularity]
dependency-graph:
  requires: [quick-004]
  provides: ["_qarray_utils.py helper module", "slimmer qarray.pyx"]
  affects: []
tech-stack:
  added: []
  patterns: ["Pure-Python helper extraction from Cython modules"]
key-files:
  created:
    - src/quantum_language/_qarray_utils.py
  modified:
    - src/quantum_language/qarray.pyx
    - src/quantum_language/qint.pyx
decisions:
  - id: Q010-D1
    description: "Mirror INTEGERSIZE as constant in _qarray_utils.py instead of importing from _core"
    rationale: "INTEGERSIZE is declared as `cdef int` in _core.pxd, making it C-level only and not importable at Python level"
    alternatives: ["Add Python-level export wrapper in _core.pyx", "Pass INTEGERSIZE as parameter"]
metrics:
  duration: ~5 min
  completed: 2026-02-03
---

# Quick Task 010: Split qarray Helpers into Module - Summary

**One-liner:** Extracted 5 pure-Python helpers from qarray.pyx into _qarray_utils.py, reducing qarray.pyx from 1115 to 973 lines.

## What Was Done

Extracted standalone helper functions from `qarray.pyx` into a new `_qarray_utils.py` module:

- `_infer_width(values, default_width=8)` - Infer bit width from values
- `_detect_shape(data)` - Detect shape from nested lists
- `_flatten(data)` - Flatten nested list to 1D
- `_reduce_tree(elements, op)` - O(log n) depth tree reduction
- `_reduce_linear(elements, op)` - O(n) depth linear reduction

These functions are pure Python (no cdef/cimport) and were extracted verbatim.

Added explanatory comment to `qint.pyx` documenting why it cannot be split (Cython cdef class limitation, confirmed in quick-004).

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 4364090 | refactor | Extract qarray helper functions to _qarray_utils.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] INTEGERSIZE not Python-importable from _core**

- **Found during:** Task 1 verification
- **Issue:** `INTEGERSIZE` is declared as `cdef int` in `_core.pxd`, which makes it C-level only. The Python-level assignment in `_core.pyx` is shadowed by the `.pxd` declaration, preventing `from ._core import INTEGERSIZE`.
- **Fix:** Mirrored `INTEGERSIZE = 8` as a constant directly in `_qarray_utils.py` with a comment explaining why and noting it must stay in sync with `_core.pyx`.
- **Files modified:** `src/quantum_language/_qarray_utils.py`

## Verification Results

- `_qarray_utils.py` contains exactly 5 functions (confirmed)
- `qarray.pyx` imports these instead of defining inline (confirmed)
- `qarray.pyx` reduced from 1115 to 973 lines (-142 lines) (confirmed)
- `qint.pyx` has explanatory comment (confirmed)
- All 146 qarray tests pass, 6 skipped (identical to baseline)
- `pip install -e .` / `setup.py build_ext --inplace` compiles without errors (confirmed)
- Import verification: `from quantum_language.qarray import qarray` and `from quantum_language._qarray_utils import _infer_width, _detect_shape` both succeed
