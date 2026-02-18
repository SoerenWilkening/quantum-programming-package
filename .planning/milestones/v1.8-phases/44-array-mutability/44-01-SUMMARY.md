---
phase: 44
plan: 01
subsystem: quantum-array-mutability
tags: [qint, qarray, in-place-operators, setitem, augmented-assignment]
depends_on:
  requires: [42, 43]
  provides: ["qint __ilshift__/__irshift__/__ifloordiv__", "qarray __setitem__", "qarray __ilshift__/__irshift__/__ifloordiv__"]
  affects: [44-02]
tech-stack:
  added: []
  patterns: ["ancilla+swap for in-place operators"]
key-files:
  created: []
  modified: ["src/quantum_language/qint.pyx", "src/quantum_language/qarray.pyx", "tests/test_qarray.py"]
decisions: []
metrics:
  duration: "5 min"
  completed: "2026-02-03"
---

# Phase 44 Plan 01: Array Mutability - In-Place Operators and Setitem Summary

**One-liner:** Added 3 missing qint in-place operators and implemented qarray.__setitem__ to enable augmented assignment on array elements.

## What Was Done

### Task 1: Add __ilshift__, __irshift__, __ifloordiv__ to qint
- Added `__ilshift__` after `__lshift__` using the established ancilla+swap pattern
- Added `__irshift__` after `__rshift__` using the same pattern
- Added `__ifloordiv__` after `__floordiv__` using the same pattern
- All three follow the `__imul__` pattern: compute out-of-place result, then swap qubit references so `self` holds the result

### Task 2: Implement qarray.__setitem__ and missing in-place wrappers
- Replaced the TypeError-raising `__setitem__` with a working implementation supporting:
  - Integer index (with negative index support and bounds checking)
  - Slice index (with qarray or scalar broadcast assignment)
  - Tuple index for multi-dimensional arrays (integer-only keys)
- Added `__ilshift__`, `__irshift__`, `__ifloordiv__` wrappers to qarray delegating to `_inplace_binary_op`
- Updated existing test `test_setitem_raises` to `test_setitem_works` and added `test_setitem_out_of_bounds`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test expecting TypeError from __setitem__**
- **Found during:** Task 2 verification
- **Issue:** `test_setitem_raises` expected `__setitem__` to raise TypeError, but we intentionally made it work
- **Fix:** Replaced with `test_setitem_works` (verifies assignment works) and `test_setitem_out_of_bounds` (verifies IndexError)
- **Files modified:** tests/test_qarray.py
- **Commit:** ea5171d

## Verification

- Build: Cython extension compiles without errors
- All augmented assignment operators work on array elements: +=, -=, *=, //=, <<=, >>=, &=, |=, ^=
- Whole-array in-place operators work: <<=, >>=, //=
- Existing tests: 90 passed, 5 skipped, 0 failures

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | ce66f15 | feat(44-01): add __ilshift__, __irshift__, __ifloordiv__ to qint |
| 2 | ea5171d | feat(44-01): implement qarray.__setitem__ and add missing in-place wrappers |

## Next Phase Readiness

Plan 44-02 can proceed. All in-place operators and __setitem__ are in place, enabling full augmented assignment patterns on qarray elements.
