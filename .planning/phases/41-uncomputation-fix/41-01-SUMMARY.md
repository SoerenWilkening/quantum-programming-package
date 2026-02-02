---
phase: 41-uncomputation-fix
plan: 01
subsystem: uncomputation
tags: [cython, layer-tracking, uncomputation, __del__, scope]
requires: [phase-19-scoped-uncomputation, phase-29-comparison-fixes]
provides: [layer-tracking-on-all-operations, fixed-lazy-uncomputation-scope]
affects: [phase-42-quantum-copy, phase-43-array-mutability]
tech-stack:
  added: []
  patterns: [layer-tracking-on-result-qints, scope-based-lazy-uncomputation]
key-files:
  created: []
  modified:
    - src/quantum_language/qint.pyx
    - src/quantum_language/qint_arithmetic.pxi
    - src/quantum_language/qint_division.pxi
decisions:
  - id: D41-01-1
    summary: "Keep inline implementations in qint.pyx instead of using include directives"
    reason: "Cython 3.0.11 does not allow include directives inside cdef class bodies"
  - id: D41-01-2
    summary: "Use strict < instead of <= for LAZY mode scope comparison in __del__"
    reason: "Prevents scope-0 (top-level) qints from auto-uncomputing on GC"
  - id: D41-01-3
    summary: "Do not add layer tracking to __lt__ and __gt__ (widened-temp comparisons)"
    reason: "Widened temps self-uncompute via GC; setting layer tracking would double-reverse gates"
metrics:
  duration: ~45 min
  completed: 2026-02-02
---

# Phase 41 Plan 01: Layer Tracking Integration Summary

**One-liner:** Added layer tracking to arithmetic/comparison/division ops in qint.pyx and fixed LAZY uncomputation scope condition from <= to <

## What Was Done

### Task 1: Add layer tracking to arithmetic and division .pxi files (3551193)
Added `_start_layer`/`_end_layer`/`operation_type`/`add_dependency` tracking to:
- `qint_arithmetic.pxi`: `__add__`, `__radd__`, `__sub__`, `__mul__`, `__rmul__` (5 methods)
- `qint_division.pxi`: `__floordiv__`, `__mod__`, `__divmod__` (classical + quantum paths)
- Reverse division ops (`__rfloordiv__`, etc.) delegate to forward ops, inheriting tracking

### Task 2: Add layer tracking to inline qint.pyx operations (b4d288e, 3ad7073)
Originally planned to replace inline code with `include` directives for .pxi files, but Cython 3.0.11 does not allow `include` inside `cdef class` bodies. Instead:

1. Added layer tracking directly to inline implementations in qint.pyx:
   - Arithmetic: `__add__`, `__radd__`, `__sub__`, `__mul__`, `__rmul__`
   - Comparison: `__eq__` (both qint==qint and qint==int paths)
   - Division: `__floordiv__`, `__mod__`, `__divmod__` (classical + quantum paths)

2. Discovered and fixed critical regression: layer tracking on results caused `_do_uncompute()` to fire on GC for ALL results (including scope-0 top-level qints), producing 975 arithmetic + 240 comparison test failures.

3. Root cause: `__del__` LAZY mode condition `current <= self.creation_scope` triggers for scope-0 qints (where both current and creation_scope are 0). Fixed by changing to `current < self.creation_scope` so only qints created inside `with` blocks (scope > 0) auto-uncompute when their scope exits.

4. Removed layer tracking from `__lt__` and `__gt__` because they use widened (n+1)-bit temporaries that self-uncompute via GC; adding layer tracking would double-reverse those gates.

### Task 3: Test verification
All test suites verified with no regressions:
- Arithmetic (add, sub, mul): 2048 passed
- Comparison: 1515 passed
- Bitwise: 2418 passed
- Division: 91 passed, 9 XPASS(strict) (pre-existing known bugs)
- Uncomputation: 14 passed, 2 xfailed, 4 failed (all pre-existing)

Pre-existing failures unchanged:
- `lt_1v3_w3`, `ge_2v2_w3`: dirty ancilla from widened-temp comparisons (Phase 35 scope)
- `compound_and`, `compound_or`: OOM (pre-existing)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Cython include directive not allowed inside cdef class**
- **Found during:** Task 2
- **Issue:** `include "qint_arithmetic.pxi"` inside `cdef class qint` produces "include statement not allowed here" error in Cython 3.0.11
- **Fix:** Abandoned include approach; added layer tracking directly to inline implementations in qint.pyx
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** b4d288e

**2. [Rule 1 - Bug] LAZY mode scope condition causes mass regression**
- **Found during:** Task 2 testing
- **Issue:** `current <= self.creation_scope` in `__del__` LAZY mode triggers for scope-0 qints, causing all results with layer tracking to uncompute on GC (975 arithmetic + 240 comparison failures)
- **Fix:** Changed to `current < self.creation_scope` so only with-block-internal qints auto-uncompute
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** 3ad7073

**3. [Rule 1 - Bug] Double-reversal from layer tracking on widened-temp comparisons**
- **Found during:** Task 2 testing
- **Issue:** `__lt__` and `__gt__` use widened (n+1)-bit temps that self-uncompute via GC. Adding layer tracking to the result causes those gates to be reversed twice.
- **Fix:** Removed layer tracking from `__lt__` and `__gt__`; they rely on widened temps' own GC cleanup
- **Files modified:** src/quantum_language/qint.pyx
- **Commit:** 3ad7073

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D41-01-1 | Keep inline implementations in qint.pyx | Cython 3.0.11 does not allow include inside cdef class |
| D41-01-2 | Strict < for LAZY scope comparison | Prevents scope-0 auto-uncompute; only with-block qints uncompute |
| D41-01-3 | No layer tracking on lt/gt | Widened temps self-clean; tracking would double-reverse |

## Commits

| Hash | Message |
|------|---------|
| 3551193 | feat(41-01): add layer tracking to arithmetic and division .pxi files |
| b4d288e | feat(41-01): add layer tracking to all operations in qint.pyx for uncomputation |
| 3ad7073 | fix(41-01): fix LAZY uncomputation scope condition and remove lt/gt layer tracking |

## Next Phase Readiness

- The .pxi files now have layer tracking but are NOT included via include directives (Cython limitation). They remain as reference implementations.
- The inline qint.pyx code is the authoritative implementation with layer tracking.
- The 4 pre-existing uncomputation test failures remain and are outside scope of this plan.
- Phase 42 (quantum copy) and Phase 43 (array mutability) can proceed; the layer tracking foundation is in place.
