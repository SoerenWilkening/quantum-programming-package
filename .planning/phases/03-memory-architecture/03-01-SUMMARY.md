---
phase: 03-memory-architecture
plan: 01
subsystem: backend-memory
tags: [c, memory-management, allocation, statistics, debugging]

# Dependency graph
requires:
  - phase: 02-c-layer-cleanup
    provides: NULL checks, OWNERSHIP comments, cleanup-on-error pattern
provides:
  - Centralized qubit allocator module (qubit_allocator.h/.c)
  - Allocator lifecycle integrated with circuit_t
  - Statistics tracking (peak, total, current, ancilla)
  - Hard-coded limit (8192) prevents runaway allocation
  - Python binding accessor (circuit_get_allocator)
affects: [03-02-ownership-tracking, 03-03-leak-elimination, python-bindings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Allocator pattern with auto-expansion and freed stack for reuse
    - DEBUG_OWNERSHIP conditional compilation for debugging
    - circuit_get_allocator() accessor for opaque struct access

key-files:
  created:
    - Backend/include/qubit_allocator.h
    - Backend/src/qubit_allocator.c
  modified:
    - Backend/include/QPU.h
    - Backend/src/circuit_allocations.c
    - CMakeLists.txt

key-decisions:
  - "Hard-coded ALLOCATOR_MAX_QUBITS limit (8192) prevents runaway allocation"
  - "Freed stack only reuses single-qubit allocations initially"
  - "DEBUG_OWNERSHIP as conditional compilation flag for ownership tracking"
  - "circuit_get_allocator() accessor enables Python bindings for opaque circuit_t"

patterns-established:
  - "Allocator auto-expands capacity (doubles, up to max) on demand"
  - "Statistics tracked automatically on every alloc/free call"
  - "Allocator destroyed before other circuit cleanup in free_circuit()"

# Metrics
duration: 5min
completed: 2026-01-26
---

# Phase 03 Plan 01: Qubit Allocator Foundation Summary

**Centralized qubit allocator with auto-expansion, statistics tracking, and ownership debugging support**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-26T11:18:46Z
- **Completed:** 2026-01-26T11:24:01Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Created qubit_allocator module with complete API (lifecycle, alloc, free, stats)
- Integrated allocator into circuit_t lifecycle (created in init, destroyed in free)
- All 59 characterization tests pass (backward compatibility maintained)
- Statistics tracking for peak/total/current/ancilla allocations
- DEBUG_OWNERSHIP conditional compilation for future ownership tracking

## Task Commits

Each task was committed atomically:

1. **Task 1: Create qubit_allocator module** - `5998ec5` (feat)
2. **Task 2: Integrate allocator into circuit_t** - `4e97aa6` (feat)
3. **Task 3: Update CMake build** - `5c85c03` (build)

## Files Created/Modified
- `Backend/include/qubit_allocator.h` - Allocator API with stats and DEBUG_OWNERSHIP support
- `Backend/src/qubit_allocator.c` - Implementation with auto-expansion and freed stack
- `Backend/include/QPU.h` - Added allocator field to circuit_t (kept qubit_indices for compatibility)
- `Backend/src/circuit_allocations.c` - Create/destroy allocator in circuit lifecycle
- `CMakeLists.txt` - Added qubit_allocator.c to build

## Decisions Made

**1. Hard-coded ALLOCATOR_MAX_QUBITS limit (8192)**
- Prevents runaway allocation bugs
- Can be increased if legitimate use cases exceed limit
- Explicit failure ((qubit_t)-1) on overflow

**2. Freed stack only reuses single-qubit allocations initially**
- Simplified implementation for Plan 1
- Multi-qubit reuse can be added in future if needed
- Tracked in freed_stack for future optimization

**3. DEBUG_OWNERSHIP conditional compilation**
- Zero runtime overhead in production builds
- Enables ownership tracking for debugging memory leaks
- Prepared for Plan 2 (ownership tracking implementation)

**4. circuit_get_allocator() accessor for Python bindings**
- circuit_t is opaque in Cython (incomplete type)
- Accessor allows Python code to get allocator pointer
- Follows C API design pattern for opaque structs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing allocator_destroy() in init_circuit() error paths**
- **Found during:** Task 2 (Integrating allocator into circuit_t)
- **Issue:** init_circuit() creates allocator early, but cleanup-on-error paths didn't destroy it - causes memory leak on init failure
- **Fix:** Added allocator_destroy(circ->allocator) to all 8 error return paths in init_circuit()
- **Files modified:** Backend/src/circuit_allocations.c
- **Verification:** Compiled successfully, follows cleanup-on-error pattern from Phase 2
- **Committed in:** 4e97aa6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug - memory leak on error path)
**Impact on plan:** Critical bug fix following Phase 2 cleanup-on-error pattern. No scope creep.

## Issues Encountered
None - plan executed smoothly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 3 Plan 2:**
- Allocator module established and tested
- circuit_t owns allocator (created/destroyed with circuit)
- Statistics infrastructure in place
- DEBUG_OWNERSHIP hooks ready for implementation

**Backward compatibility:**
- All 59 characterization tests pass
- qubit_indices/ancilla still exist (TODO for Plan 2 migration)
- Allocator not yet used by QINT/QBOOL (Plan 2 work)

**No blockers** - foundation complete, ready for ownership tracking migration.

---
*Phase: 03-memory-architecture*
*Completed: 2026-01-26*
