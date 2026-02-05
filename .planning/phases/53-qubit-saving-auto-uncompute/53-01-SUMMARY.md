---
phase: 53-qubit-saving-auto-uncompute
plan: 01
subsystem: compiler
tags: [compile, qubit-saving, auto-uncompute, ancilla, adjoint]

# Dependency graph
requires:
  - phase: 52-ancilla-tracking-inverse-reuse
    provides: AncillaRecord, _AncillaInverseProxy, forward call tracking
provides:
  - Cache key includes qubit_saving mode for recompilation on mode change
  - _function_modifies_inputs helper for input side-effect detection
  - _partition_ancillas helper for return vs temp qubit classification
  - _auto_uncompute method on CompiledFunc for automatic temp ancilla cleanup
  - Modified _AncillaInverseProxy with reduced gate set after auto-uncompute
affects: [53-02 (tests), future qubit optimization phases]

# Tech tracking
tech-stack:
  added: []
  patterns: [auto-uncompute-after-forward-call, ancilla-partitioning, reduced-adjoint-gates]

key-files:
  created: []
  modified: [src/quantum_language/compile.py, tests/test_compile.py]

key-decisions:
  - "Auto-uncompute triggers in __call__ after both replay and capture paths"
  - "_auto_uncomputed flag on AncillaRecord enables reduced adjoint in f.inverse()"
  - "Functions modifying inputs skip auto-uncompute (detected via _function_modifies_inputs)"
  - "Cache key includes qubit_saving mode so mode change triggers recompilation"

patterns-established:
  - "Ancilla partitioning: _partition_ancillas splits return vs temp using block.return_qubit_range"
  - "Lazy caching of _modifies_inputs on CompiledBlock via __slots__"

# Metrics
duration: 3min
completed: 2026-02-04
---

# Phase 53 Plan 01: Auto-Uncompute Implementation Summary

**Auto-uncompute of temp ancilla qubits in compiled functions when qubit_saving mode is active, with cache key extension and modified inverse proxy for post-uncompute adjoint**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-04T22:43:00Z
- **Completed:** 2026-02-04T22:46:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Cache key now includes qubit_saving mode, triggering recompilation when mode changes
- Input side-effect detection prevents auto-uncompute on functions that modify inputs
- Auto-uncompute partitions ancillas into return and temp, uncomputes only temp qubits
- f.inverse() uses reduced gate set after auto-uncompute (only return-qubit gates)

## Task Commits

Each task was committed atomically:

1. **Task 1: Cache key extension and input side-effect detection** - `2c46cea` (feat)
2. **Task 2: Auto-uncompute logic and modified inverse proxy** - `053ccf7` (feat)

## Files Created/Modified
- `src/quantum_language/compile.py` - Added _get_qubit_saving_mode import, cache key extension, _function_modifies_inputs, _partition_ancillas, _auto_uncompute method, modified _AncillaInverseProxy
- `tests/test_compile.py` - Updated hardcoded cache key tuples to include qubit_saving=False element

## Decisions Made
- Auto-uncompute triggers in __call__ after both replay and capture paths, using the already-computed qubit_saving variable from cache key construction
- _auto_uncomputed flag on AncillaRecord enables _AncillaInverseProxy to use reduced gate set (return-only gates)
- Functions that modify inputs are detected via _function_modifies_inputs (checks if any gate targets parameter-range virtual qubits)
- When no return qubits exist, the forward call record is removed entirely after auto-uncompute

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated hardcoded cache keys in test file**
- **Found during:** Task 1
- **Issue:** Tests constructed cache keys directly as `((), (4,), 0)` without the new qubit_saving element, causing KeyError
- **Fix:** Updated all 8 hardcoded cache key tuples in test_compile.py to include `False` (default qubit_saving value)
- **Files modified:** tests/test_compile.py
- **Verification:** All 82 tests pass
- **Committed in:** 2c46cea (Task 1 commit)

**2. [Rule 2 - Missing Critical] Updated _InverseCompiledFunc cache key**
- **Found during:** Task 1
- **Issue:** _InverseCompiledFunc.__call__ also constructs cache keys matching CompiledFunc format; missing qubit_saving would cause cache misses
- **Fix:** Added qubit_saving to _InverseCompiledFunc cache key construction
- **Files modified:** src/quantum_language/compile.py
- **Committed in:** 2c46cea (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Auto-uncompute implementation complete, ready for Phase 53 Plan 02 (tests)
- All existing compile tests pass (82/82)
- New functionality only activates when qubit_saving mode is True (no default behavior change)

---
*Phase: 53-qubit-saving-auto-uncompute*
*Completed: 2026-02-04*
