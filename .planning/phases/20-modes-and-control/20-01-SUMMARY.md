---
phase: 20-modes-and-control
plan: 01
subsystem: uncomputation
tags: [python, cython, quantum-resource-management, mode-switching, memory-optimization]

# Dependency graph
requires:
  - phase: 18-basic-uncomputation
    provides: "_do_uncompute(), __del__ infrastructure, _is_uncomputed flag"
  - phase: 19-context-manager-integration
    provides: "scope_stack for lazy mode scope checking, creation_scope tracking"
provides:
  - "ql.option('qubit_saving', bool) API for mode control"
  - "_uncompute_mode per-qbool mode capture at creation"
  - "Mode-aware __del__ with distinct eager/lazy behavior"
affects: [20-02-keep-and-explicit-uncompute, user-facing-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level option API (NumPy-style get/set overloading)"
    - "Per-instance mode capture (immutable after creation)"
    - "Mode-based conditional uncomputation in __del__"

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pyx
    - python-backend/qint_operations.pxi

key-decisions:
  - "Mode flag captured at qbool creation time (not retroactive)"
  - "Eager mode: immediate uncomputation when GC runs"
  - "Lazy mode: scope-based uncomputation (current <= creation_scope)"
  - "_uncompute_mode made public for testing/debugging access"

patterns-established:
  - "Global option function with get/set overloading: option(key, value=None)"
  - "Mode capture in both __init__ branches (create_new=True/False)"
  - "Mode-aware __del__ with distinct behavior branches"

# Metrics
duration: 5.5min
completed: 2026-01-28
---

# Phase 20 Plan 01: Modes and Control Summary

**Module-level option API with per-qbool mode capture enabling user control over lazy (gate-minimizing) vs eager (qubit-minimizing) uncomputation strategies**

## Performance

- **Duration:** 5.5 min
- **Started:** 2026-01-28T19:00:31Z
- **Completed:** 2026-01-28T19:06:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `ql.option('qubit_saving', bool)` API for global mode control with validation
- Per-qbool mode capture at creation prevents retroactive mode changes
- Mode-aware `__del__` with DISTINCT behavior: eager (immediate) vs lazy (scope-checked)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add module-level option API** - `02e4e57` (feat)
2. **Task 2: Add per-qbool mode capture and mode-aware __del__** - `4cba7c8` (feat)

## Files Created/Modified
- `python-backend/quantum_language.pyx` - Added _qubit_saving_mode global, option() function, _uncompute_mode attribute, mode capture in __init__
- `python-backend/qint_operations.pxi` - Modified __del__ to check mode and conditionally uncompute (eager: always, lazy: scope-checked)

## Decisions Made

**1. Mode captured at creation time (not retroactive)**
- **Rationale:** Prevents mid-computation mode changes from breaking existing qbools. Each qbool has predictable behavior for its entire lifetime.
- **Implementation:** `self._uncompute_mode = _qubit_saving_mode` in both __init__ branches.

**2. Eager mode: immediate uncomputation**
- **Rationale:** Minimizes peak qubit count by freeing qubits as soon as GC runs, regardless of scope boundaries.
- **Implementation:** `if self._uncompute_mode: self._do_uncompute(from_del=True)`

**3. Lazy mode: scope-based uncomputation**
- **Rationale:** Minimizes gate count by keeping intermediates alive within scope, enabling gate sharing and reducing reversal overhead.
- **Implementation:** Check `current_scope_depth.get() <= self.creation_scope` before calling `_do_uncompute()`.

**4. _uncompute_mode made public (cdef public bint)**
- **Rationale:** Enables testing and debugging. Users can verify mode capture worked correctly.
- **Implementation:** Changed from `cdef bint` to `cdef public bint`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Issue 1: _uncompute_mode not accessible from Python**
- **Problem:** Initial implementation used `cdef bint` (private), tests couldn't access attribute.
- **Resolution:** Changed to `cdef public bint` to enable Python access for testing.
- **Impact:** Required rebuild, no logic changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 02:**
- Mode API complete and tested
- Mode capture working correctly (per-qbool immutability verified)
- __del__ has placeholder for _keep_flag (will be implemented in Plan 02)
- No blockers

**Known limitations:**
- .keep() method not yet implemented (placeholder check exists in __del__)
- Mode-aware behavior relies on Python GC timing (non-deterministic)

**Success criteria met:**
- MODE-01: Default lazy mode (qubit_saving=False) ✓
- MODE-02: Eager mode option (`ql.option('qubit_saving', True)`) ✓
- MODE-03: Per-circuit mode switching via per-qbool mode capture ✓

---
*Phase: 20-modes-and-control*
*Completed: 2026-01-28*
