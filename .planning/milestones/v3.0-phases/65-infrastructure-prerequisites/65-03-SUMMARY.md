---
phase: 65-infrastructure-prerequisites
plan: 03
subsystem: infra
tags: [allocator, debug, ancilla, lifecycle, assertions, testing]

# Dependency graph
requires:
  - phase: 65-02
    provides: "Block-based qubit allocator with freed_blocks array, coalescing, first-fit search"
provides:
  - "DEBUG-guarded per-qubit ancilla bitmap in qubit_allocator_t"
  - "Ancilla leak detection at allocator_destroy() with per-qubit identification"
  - "C debug test target (test_allocator_block_debug) compiled with -DDEBUG"
  - "Python integration test for ancilla block lifecycle through Cython bindings"
affects: [66-toffoli-adder, 67-carry-lookahead, 68-multiplication]

# Tech tracking
tech-stack:
  added: []
  patterns: ["#ifdef DEBUG for ancilla tracking (separate from DEBUG_OWNERSHIP)", "assert(0 && msg) for leak detection in destroy"]

key-files:
  created:
    - tests/python/test_ancilla_lifecycle.py
  modified:
    - c_backend/include/qubit_allocator.h
    - c_backend/src/qubit_allocator.c
    - tests/c/test_allocator_block.c
    - tests/c/Makefile

key-decisions:
  - "Use #ifdef DEBUG (not DEBUG_OWNERSHIP) for ancilla tracking -- enables independent control"
  - "Ancilla map uses dynamic bool array with doubling expansion (matches allocator capacity pattern)"

patterns-established:
  - "Debug ancilla tracking: allocator marks ancilla in alloc, clears in free, asserts in destroy"
  - "C debug tests compiled with -DDEBUG via separate Makefile target"

# Metrics
duration: 23min
completed: 2026-02-14
---

# Phase 65 Plan 03: Ancilla Lifecycle Assertions Summary

**DEBUG-mode per-qubit ancilla bitmap with leak detection at destroy and C/Python test coverage**

## Performance

- **Duration:** 23 min
- **Started:** 2026-02-14T18:43:06Z
- **Completed:** 2026-02-14T19:07:05Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added per-qubit ancilla bitmap (is_ancilla_map) with dynamic expansion under #ifdef DEBUG
- Leak detection in allocator_destroy() prints leaked qubit indices and asserts
- 3 new C debug tests verify no false positives on correct ancilla usage
- 5 Python integration tests verify end-to-end allocator works through real quantum operations
- All debug code compiles out in release builds (zero overhead)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DEBUG-mode ancilla tracking and leak detection** - `f7293b5` (feat)
2. **Task 2: Add C debug tests and Python integration test** - `a53a124` (test)

## Files Created/Modified
- `c_backend/include/qubit_allocator.h` - Added #ifdef DEBUG ancilla tracking fields to qubit_allocator_t
- `c_backend/src/qubit_allocator.c` - Ancilla marking in alloc, clearing in free, leak detection in destroy
- `tests/c/test_allocator_block.c` - 3 new ancilla lifecycle tests (tests 11-13)
- `tests/c/Makefile` - Added test_allocator_block_debug target with -DDEBUG
- `tests/python/test_ancilla_lifecycle.py` - 5 integration tests for ancilla block lifecycle

## Decisions Made
- Used #ifdef DEBUG (not DEBUG_OWNERSHIP) for ancilla tracking to enable independent control of these two debug features
- Ancilla map uses dynamic bool array with power-of-2 expansion, capped at ALLOCATOR_MAX_QUBITS

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed Python test API to match actual quantum_language interface**
- **Found during:** Task 2 (Python integration test)
- **Issue:** Plan specified ql.Environment() and a.measure() which don't exist in the API
- **Fix:** Changed to use ql.qint() directly (no Environment needed), a.width instead of a.bits, and isinstance checks instead of measure()
- **Files modified:** tests/python/test_ancilla_lifecycle.py
- **Verification:** All 5 Python tests pass
- **Committed in:** a53a124 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** API mismatch in plan's Python test code required adaptation to actual interface. No scope creep.

## Issues Encountered
- Pre-existing segfault in 32-bit multiplication test (known BUG from Phase 61, not caused by our changes)
- Pre-existing test failures in test_qint_default_width, test_array_2d, test_array_creates_list_of_qint (all verified as pre-existing by testing on stashed state)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 65 infrastructure prerequisites complete: self-inverse gate fix (65-01), block-based allocator (65-02), ancilla leak detection (65-03)
- Ready for Phase 66 (Toffoli ripple-carry adder implementation)
- Known concern: optimizer gate cancellation rules designed for QFT may need disabling for Toffoli initially

## Self-Check: PASSED

All 6 files verified present. Both commit hashes (f7293b5, a53a124) verified in git log. Must-have artifact patterns confirmed: is_ancilla_map in header, ancilla_outstanding in source (5 occurrences), test_ancilla in C tests (9 occurrences), TestAncillaBlockLifecycle in Python tests.

---
*Phase: 65-infrastructure-prerequisites*
*Completed: 2026-02-14*
