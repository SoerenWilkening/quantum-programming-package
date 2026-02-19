---
phase: 76-gate-primitive-exposure
plan: 01
subsystem: backend
tags: [cython, c-backend, gates, ry, mcz, grover]

# Dependency graph
requires: []
provides:
  - ry(), cry(), ch(), mcz() C gate functions
  - _gates.pyx module with emit_ry(), emit_h(), emit_z(), emit_mcz()
  - Foundation layer for branch() method
affects: [77-oracle-scope, 78-diffusion-operator]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Gate functions follow existing pattern (gate_t* g, qubit_t target, ...)
    - emit_* functions handle controlled context automatically
    - MCZ uses large_control heap array for n_controls > MAXCONTROLS

key-files:
  created:
    - src/quantum_language/_gates.pyx
    - src/quantum_language/_gates.pxd
  modified:
    - c_backend/include/gate.h
    - c_backend/src/gate.c

key-decisions:
  - "MCZ implemented in Phase 76 as foundation for Phase 78 diffusion"
  - "emit_* functions auto-handle controlled context (CRy/CH/CZ when inside qbool context)"

patterns-established:
  - "Gate primitives: C function + Cython cpdef emit_* wrapper pattern"
  - "Multi-controlled gates: use large_control heap array for n > MAXCONTROLS"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 76 Plan 01: Gate Primitive Exposure Summary

**Ry/CRy/CH/MCZ gate primitives in C backend with _gates.pyx Cython emission layer for Grover's algorithm**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T21:06:07Z
- **Completed:** 2026-02-19T21:11:04Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added ry(), cry(), ch() gate creation functions to C backend
- Created _gates.pyx module with emit_ry(), emit_h(), emit_z() internal functions
- Added mcz() C function and emit_mcz() Python wrapper for multi-controlled Z
- emit_* functions automatically handle controlled context (emit CRy instead of Ry when inside `with qbool:` block)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ry(), cry(), ch() to C backend** - `47b37ab` (feat)
2. **Task 2: Create _gates.pyx module** - `6075ddb` (feat)
3. **Task 3: Add MCZ gate and emit_mcz()** - `4bae694` (feat)

## Files Created/Modified
- `c_backend/include/gate.h` - Added ry(), cry(), ch(), mcz() declarations
- `c_backend/src/gate.c` - Added ry(), cry(), ch(), mcz() implementations
- `src/quantum_language/_gates.pxd` - Cython declarations for gate functions
- `src/quantum_language/_gates.pyx` - emit_ry(), emit_h(), emit_z(), emit_mcz() functions

## Decisions Made
- MCZ follows existing mcx pattern (inline Control array for small n, heap large_control for n > MAXCONTROLS)
- emit_* functions import qint locally to avoid circular import issues
- Controlled context handling done in Python layer, not C layer

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Execution environment lacked C compiler (gcc/clang) - compilation could not be verified in this session
- Virtual environment was stale (path mismatch) - worked around with system packages

## Next Phase Readiness
- Gate primitives ready for branch() implementation (Phase 77+)
- emit_mcz() ready for diffusion operator (Phase 78)
- Build should be verified on next session with C compiler available

## Self-Check: PASSED

All files and commits verified:
- c_backend/include/gate.h: FOUND
- c_backend/src/gate.c: FOUND
- src/quantum_language/_gates.pyx: FOUND
- src/quantum_language/_gates.pxd: FOUND
- Commit 47b37ab: FOUND
- Commit 6075ddb: FOUND
- Commit 4bae694: FOUND

---
*Phase: 76-gate-primitive-exposure*
*Completed: 2026-02-19*
