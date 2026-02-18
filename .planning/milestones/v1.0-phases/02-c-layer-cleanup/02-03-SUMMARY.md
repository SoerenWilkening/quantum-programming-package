---
phase: 02-c-layer-cleanup
plan: 03
subsystem: backend
tags: [c, memory-management, ownership-documentation, global-state-elimination]

# Dependency graph
requires:
  - phase: 02-02
    provides: NULL check coverage for all allocations
provides:
  - No global circuit variable - all functions accept explicit circuit_t* parameter
  - Memory ownership documented at every allocation point (27 OWNERSHIP comments)
  - Cython bindings work correctly with updated C signatures
affects: [03-memory-architecture, 04-module-separation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Explicit context passing via circuit_t* parameter"
    - "OWNERSHIP comments document memory responsibilities"
    - "Cached vs owned sequence distinction clearly documented"

key-files:
  created: []
  modified:
    - Backend/include/QPU.h
    - Backend/include/Integer.h
    - Backend/src/QPU.c
    - Backend/src/Integer.c
    - Backend/src/circuit_allocations.c
    - Backend/src/IntegerAddition.c
    - Backend/src/IntegerMultiplication.c
    - Backend/src/IntegerComparison.c
    - Backend/src/LogicOperations.c
    - Backend/src/gate.c
    - python-backend/quantum_language.cpython-313-x86_64-linux-gnu.so

key-decisions:
  - "Kept instruction_list and QPU_state as globals (stateless sequence generation)"
  - "Python bindings don't use QINT/QBOOL/free_element - manage qubits directly"

patterns-established:
  - "OWNERSHIP: Caller owns returned X* - document at every allocation function"
  - "OWNERSHIP: Returns cached sequence - DO NOT FREE - for precompiled sequences"
  - "OWNERSHIP: Modifies and returns passed X* - for in-place modification functions"

# Metrics
duration: 5min
completed: 2026-01-26
---

# Phase 2 Plan 3: Global State Elimination Summary

**Eliminated global circuit variable and documented memory ownership across C backend with 27 OWNERSHIP comments, enabling explicit context passing and future memory cleanup**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-26T16:18:34Z
- **Completed:** 2026-01-26T16:23:53Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments
- Removed global circuit variable from Backend - all circuit-modifying functions now accept explicit circuit_t* parameter
- Added 27 OWNERSHIP comments documenting memory responsibilities at every allocation point
- Updated QINT(), QBOOL(), free_element() signatures to accept circuit_t* parameter with NULL checks
- Documented cached vs owned sequence distinction across Integer operations
- All 59 characterization tests pass - no behavioral regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Update function signatures to accept circuit_t* parameter** - `a80fcc1` (refactor)
2. **Task 2: Update all callers and add ownership documentation** - `2d6f53a` (docs)
3. **Task 3: Update Cython bindings and verify tests pass** - `6ec3fd8` (build)

## Files Created/Modified
- `Backend/include/QPU.h` - Removed extern circuit_t *circuit declaration
- `Backend/include/Integer.h` - Updated QINT(), QBOOL(), free_element() signatures
- `Backend/src/QPU.c` - Removed global circuit variable definition
- `Backend/src/Integer.c` - Updated implementations with circuit_t* parameter and OWNERSHIP comments
- `Backend/src/circuit_allocations.c` - Added OWNERSHIP comment to init_circuit()
- `Backend/src/IntegerAddition.c` - Documented cached (QQ_add, CQ_add, cCQ_add, cQQ_add) vs owned (P_add, cP_add) sequences
- `Backend/src/IntegerMultiplication.c` - Documented cached (QQ_mul, cQQ_mul) vs owned (CQ_mul, cCQ_mul) sequences
- `Backend/src/IntegerComparison.c` - Documented owned sequences (CQ_equal, cCQ_equal)
- `Backend/src/LogicOperations.c` - Documented owned sequences and classical-only operations
- `Backend/src/gate.c` - Documented QFT/QFT_inverse modify and return passed sequence
- `python-backend/quantum_language.cpython-313-x86_64-linux-gnu.so` - Rebuilt with updated C signatures

## Decisions Made

**Kept instruction_list and QPU_state as globals:**
- These are used for stateless sequence generation (reading register values)
- They don't modify circuit state, only guide gate sequence construction
- Will be addressed in Phase 4 (Module Separation) when separating compilation from execution

**Python bindings don't need QINT/QBOOL updates:**
- Bindings manage quantum integers through own qubit tracking (numpy arrays)
- Already have module-level _circuit variable that's passed to run_instruction()
- Don't call QINT(), QBOOL(), or free_element() directly from Cython layer

**OWNERSHIP documentation patterns:**
- "Caller owns returned X*" - for allocation functions
- "Returns cached sequence - DO NOT FREE" - for precompiled sequences
- "Modifies and returns passed X*" - for in-place modification (QFT, QFT_inverse)
- "No sequence returned" - for classical-only operations

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - signature changes compiled cleanly, tests passed on first run.

## Next Phase Readiness

**Ready for Phase 3 (Memory Architecture):**
- Explicit circuit context enables proper resource tracking
- Ownership documentation identifies every allocation point
- No global state prevents correct cleanup

**Foundation complete for:**
- Phase 4 (Module Separation) - Can separate compilation/execution contexts
- Proper free_circuit() implementation - Know what needs freeing

---
*Phase: 02-c-layer-cleanup*
*Completed: 2026-01-26*
