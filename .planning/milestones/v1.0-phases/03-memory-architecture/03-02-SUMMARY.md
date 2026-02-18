---
phase: 03-memory-architecture
plan: 02
subsystem: backend-memory
tags: [c, memory-management, quantum-types, qint, qbool, ownership]

# Dependency graph
requires:
  - phase: 03-01
    provides: Centralized qubit allocator module with lifecycle and statistics
provides:
  - QINT/QBOOL allocate qubits through circuit's allocator
  - free_element returns qubits to allocator pool
  - DEBUG_OWNERSHIP tracking for quantum integer instances
  - Graceful allocation failure handling (NULL return)
affects: [03-03-leak-elimination, python-bindings, future-quantum-types]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Borrow semantics: quantum types hold references to circuit-owned qubits
    - Allocation failure returns NULL (enables error propagation)
    - DEBUG_OWNERSHIP counter-based tagging for debugging

key-files:
  created: []
  modified:
    - Backend/src/Integer.c
    - Backend/include/Integer.h

key-decisions:
  - "QINT/QBOOL use allocator_alloc() with is_ancilla=true flag"
  - "free_element determines width from MSB to return correct qubit count"
  - "Backward compat tracking maintained (decrement by 1 quirk documented)"
  - "Allocation failures return NULL instead of crashing"

patterns-established:
  - "Quantum types borrow qubits from circuit's allocator"
  - "Check both circ and circ->allocator for NULL before allocation"
  - "Free quantum_int_t on allocation failure (cleanup-on-error)"
  - "DEBUG_OWNERSHIP uses static counters for per-type instance tracking"

# Metrics
duration: 2min
completed: 2026-01-26
---

# Phase 03 Plan 02: QINT/QBOOL Allocator Integration Summary

**QINT and QBOOL allocate qubits through centralized allocator with ownership tracking and graceful failure handling**

## Performance

- **Duration:** 2 min 13 sec
- **Started:** 2026-01-26T11:34:36Z
- **Completed:** 2026-01-26T11:36:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- QINT() allocates INTEGERSIZE qubits via allocator_alloc()
- QBOOL() allocates 1 qubit via allocator_alloc()
- free_element() returns qubits to allocator via allocator_free()
- DEBUG_OWNERSHIP tracks qint/qbool instances with per-type counters
- All 59 characterization tests pass (backward compatibility maintained)

## Task Commits

Each task was committed atomically:

1. **Task 1: Update QINT and QBOOL to use allocator** - `ff08edb` (feat)
2. **Task 2: Verify backward compatibility and run tests** - `ec23797` (test)

## Files Created/Modified
- `Backend/src/Integer.c` - QINT/QBOOL use allocator_alloc(), free_element uses allocator_free()
- `Backend/include/Integer.h` - Added comment noting allocator integration and ownership semantics

## Decisions Made

**1. QINT/QBOOL use is_ancilla=true flag**
- Both QINT and QBOOL are ancilla qubits (helper qubits for computation)
- Enables ancilla_allocations stat tracking in allocator
- Matches semantic meaning of these quantum integer types

**2. free_element determines width from MSB**
- QBOOL has MSB=INTEGERSIZE-1 (1 qubit allocated)
- QINT has MSB=0 (INTEGERSIZE qubits allocated)
- Enables correct allocator_free(start, width) call

**3. Backward compat tracking maintained with documented quirk**
- Original code decrements ancilla/used_qubit_indices by 1 regardless of width
- This appears to be a bug (QINT should decrement by INTEGERSIZE)
- Maintained existing behavior to avoid test failures during migration
- Documented with TODO for Phase 3 cleanup

**4. NULL check for both circ and circ->allocator**
- Defensive programming: verify circuit and allocator exist before use
- Prevents segfault if allocator creation failed during circuit init
- Returns NULL to propagate error to caller

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Pre-commit hook formatting**
- clang-format reformatted Integer.c after initial commit attempt
- Re-staged formatted file and committed successfully
- No functional impact, just stylistic formatting

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 3 Plan 3 (Leak Elimination):**
- QINT/QBOOL now allocate through circuit's allocator
- Qubits returned to allocator on free_element()
- DEBUG_OWNERSHIP infrastructure in place (can track live allocations)
- Backward compat tracking still exists (ready for removal in Plan 3)

**Verified backward compatibility:**
- All 59 characterization tests pass
- Python bindings continue to work (they don't use QINT/QBOOL directly)
- Existing circuit statistics (ancilla/used_qubit_indices) still tracked

**Established borrow semantics:**
- Quantum types hold references to circuit-owned qubits
- Circuit controls qubit lifecycle through allocator
- Enables future qubit reuse optimizations

**No blockers** - allocator integration complete, ready for leak elimination phase.

---
*Phase: 03-memory-architecture*
*Completed: 2026-01-26*
