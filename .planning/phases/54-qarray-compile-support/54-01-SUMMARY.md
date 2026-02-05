---
phase: 54-qarray-compile-support
plan: 01
subsystem: compile
tags: [qarray, compile, decorator, capture, replay, caching]

# Dependency graph
requires:
  - phase: 48-51 (Function Compilation)
    provides: CompiledFunc, CompiledBlock, gate capture/replay infrastructure
  - phase: 22-25 (qarray Implementation)
    provides: qarray cdef class with _elements, _shape, iteration support
provides:
  - qarray argument support in @ql.compile decorated functions
  - Unified qubit extraction for qint and qarray arguments
  - qarray return value construction during replay
  - Cache key differentiation by array length
affects: [compile-inverse, compile-adjoint, qubit-saving, auto-uncompute]

# Tech tracking
tech-stack:
  added: []
  patterns: [unified_qubit_extraction, iteration_protocol_for_cdef]

key-files:
  created: []
  modified:
    - src/quantum_language/compile.py

key-decisions:
  - "Use iteration protocol (for elem in arr) to access qarray elements from Python, avoiding cdef attribute access"
  - "Cache key uses ('arr', length) tuple to distinguish qarray from qint widths"
  - "Store return_type and _return_qarray_element_widths in CompiledBlock for replay reconstruction"

patterns-established:
  - "_get_quantum_arg_qubit_indices(): unified qubit extraction pattern for qint/qarray"
  - "_get_quantum_arg_width(): unified width calculation pattern for qint/qarray"
  - "qarray._create_view() for reconstructing qarray from element list"

# Metrics
duration: 6min
completed: 2026-02-05
---

# Phase 54 Plan 01: qarray Compile Support Summary

**qarray arguments and return values fully supported in @ql.compile with cache key differentiation by array length, unified qubit extraction, and replay-time width validation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-05T09:49:41Z
- **Completed:** 2026-02-05T09:55:20Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- qarray arguments recognized and validated in _classify_args() with empty/stale checks
- Unified qubit extraction functions handle both qint and qarray uniformly
- qarray return values correctly constructed during replay with element width preservation
- Replay validates total qubit count matches cached block (width mismatch error)
- Cache keys differentiate arrays by length for correct caching behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add qarray detection and qubit extraction** - `32f3dc1` (feat)
2. **Task 2: Update capture, replay, and cache key handling** - `e96c53a` (feat)
3. **Task 3: Add qarray return value construction** - `48508c0` (feat)

## Files Created/Modified
- `src/quantum_language/compile.py` - Added qarray support throughout capture/replay infrastructure

## Decisions Made
- **Iteration protocol for cdef access:** Used `for elem in arr` instead of `arr._elements` since `_elements` is a cdef attribute inaccessible from pure Python. The qarray supports `__iter__()` which internally accesses `_elements`.
- **Cache key format:** Used `('arr', len(arr))` tuple to distinguish qarray from qint width integers in the widths list. This makes cache keys hashable and unambiguous.
- **Element widths stored in block:** Added `_return_qarray_element_widths` to CompiledBlock to enable correct qarray reconstruction during replay without needing the original qarray reference.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Changed _elements access to iteration protocol**
- **Found during:** Task 1 (qarray detection)
- **Issue:** Plan specified accessing `arr._elements` directly, but this is a cdef attribute not accessible from Python code
- **Fix:** Changed all `arr._elements` access to use `for elem in arr` iteration protocol
- **Files modified:** src/quantum_language/compile.py
- **Verification:** Tests pass, qarray iteration works correctly
- **Committed in:** 32f3dc1 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required fix for cdef attribute access pattern. No scope creep.

## Issues Encountered
None - once the cdef access pattern was fixed, all implementation proceeded as planned.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- qarray compile support complete
- Ready for plan 54-02 (qarray compile tests) if planned
- Integration with qubit_saving mode and auto-uncompute works via existing infrastructure (return_type properly tracked)

---
*Phase: 54-qarray-compile-support*
*Completed: 2026-02-05*
