---
phase: 03-memory-architecture
plan: 03
subsystem: python-bindings
tags: [cython, python, memory-management, qubit-allocation]

# Dependency graph
requires:
  - phase: 03-01
    provides: qubit_allocator module with circuit_get_allocator() accessor
provides:
  - Python qint/qbool classes allocate qubits through circuit's allocator
  - circuit_stats() function exposes allocation statistics to Python
  - Allocator statistics accessible for debugging and analysis
affects: [04-module-separation, 05-variable-width-integers, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cython cdef declarations must be at function start"
    - "Use circuit_get_allocator() accessor for opaque circuit_t in Python"
    - "Cast circuit_t* to circuit_s* when calling C functions with forward-declared structs"

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pxd
    - python-backend/quantum_language.pyx
    - python-backend/setup.py

key-decisions:
  - "Cast circuit_t* to circuit_s* in Cython calls to match C function signatures"
  - "Add qubit_allocator.c to setup.py sources for proper linking"
  - "Preserve backward compat tracking (_smallest_allocated_qubit, ancilla) for gradual migration"
  - "circuit_stats() uses cdef declarations at function start (Cython requirement)"

patterns-established:
  - "Python bindings use circuit_get_allocator() to access allocator from opaque circuit_t"
  - "Allocator statistics returned as Python dict for easy debugging"
  - "cdef variable declarations at function start, before any Python statements"

# Metrics
duration: 15min
completed: 2026-01-26
---

# Phase 03 Plan 03: Python Bindings Summary

**Python qint/qbool allocate qubits through circuit's allocator via circuit_get_allocator(), with statistics exposed via circuit_stats()**

## Performance

- **Duration:** 15 min
- **Started:** 2026-01-26T11:27:56Z
- **Completed:** 2026-01-26T11:42:00Z (estimated)
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Python qint/qbool classes now use circuit's centralized allocator instead of manual tracking
- circuit_stats() function exposes allocator statistics (peak_allocated, total_allocations, current_in_use, ancilla_allocations)
- All 59 characterization tests pass with allocator integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Add allocator declarations to Cython** - `cfbe3c2` (feat)
2. **Task 2: Update qint/qbool allocation to use allocator** - `0aceaa5` (feat)
3. **Task 3: Add circuit_stats() function and verify tests** - `c93bed8` (feat)

## Files Created/Modified
- `python-backend/quantum_language.pxd` - Added allocator_stats_t, qubit_allocator_t, circuit_s declarations, circuit_get_allocator()
- `python-backend/quantum_language.pyx` - Updated qint __init__/__del__ to use allocator, added circuit_stats() function, fixed cdef declarations
- `python-backend/setup.py` - Added qubit_allocator.c to sources for linking

## Decisions Made

**Cython type casting for forward-declared structs:**
- qubit_allocator.h uses `struct circuit_s*` (forward declaration) but circuit_t is an anonymous struct typedef
- Solution: Declare `circuit_s` in .pxd and cast `circuit_t*` to `circuit_s*` when calling circuit_get_allocator()
- Rationale: Avoids modifying C headers beyond plan scope, works because C implementation already casts internally

**Preserve backward compat tracking:**
- Keep _smallest_allocated_qubit and ancilla array updates during migration
- Rationale: Unknown if other code depends on these globals, gradual migration safer

**Cython cdef declaration requirements:**
- All cdef declarations must be at function start, before any Python statements
- Solution: Moved alloc and start declarations to top of __init__, __del__, circuit_stats()
- Rationale: Cython language requirement, compilation fails otherwise

**Link qubit_allocator.c in setup.py:**
- Added qubit_allocator.c to sources_circuit list
- Rationale: circuit_get_allocator symbol undefined without it

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Cython compilation error: "cdef statement not allowed here"**
- **Issue:** cdef declarations inside def functions must be at function start
- **Solution:** Moved cdef declarations to top of __init__, __del__, circuit_stats()
- **Resolution:** Compilation succeeded after reordering

**2. Type mismatch: circuit_t* vs struct circuit_s***
- **Issue:** circuit_get_allocator() expects `struct circuit_s*` but Cython has `circuit_t*`
- **Solution:** Added `circuit_s` forward declaration in .pxd, cast to `<circuit_s*>` at call sites
- **Resolution:** Compiles and links correctly, cast matches C implementation

**3. Undefined symbol: circuit_get_allocator**
- **Issue:** Function not found at link time
- **Solution:** Added qubit_allocator.c to setup.py sources
- **Resolution:** Symbol exported in .so, imports work correctly

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Phase 4 (Module Separation): Python bindings now use allocator, ready for further C layer refactoring
- Testing improvements: circuit_stats() enables validation of allocation behavior

**Notes:**
- All characterization tests pass (59/59)
- ancilla_allocations stat exposed (addresses FOUND-08 requirement)
- Backward compat tracking preserved for gradual migration
- Python GC controls deallocation timing (expected behavior)

---
*Phase: 03-memory-architecture*
*Completed: 2026-01-26*
