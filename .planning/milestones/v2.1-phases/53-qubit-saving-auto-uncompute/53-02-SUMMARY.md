---
phase: 53-qubit-saving-auto-uncompute
plan: 02
subsystem: testing
tags: [compile, qubit-saving, auto-uncompute, ancilla, test, pytest]

requires:
  - phase: 53-01
    provides: auto-uncompute implementation in compile.py
provides:
  - INV-07 test coverage for all auto-uncompute scenarios
affects: []

tech-stack:
  added: []
  patterns:
    - "complex_fn pattern (two allocations) to create distinct temp vs return qubits"
    - "circuit_stats total_deallocations to verify auto-uncompute firing"

key-files:
  created: []
  modified:
    - tests/test_compile.py

key-decisions:
  - "Used complex_fn (temp + result allocations) instead of simple copy to ensure temp qubits exist for auto-uncompute"
  - "Verified deallocation via total_deallocations stat rather than current_in_use (more reliable for non-contiguous qubits)"

patterns-established:
  - "ql.option('qubit_saving', True) after ql.circuit() for auto-uncompute tests"
  - "Check record._auto_uncomputed flag for auto-uncompute verification"

duration: 8min
completed: 2026-02-04
---

# Phase 53 Plan 02: Auto-Uncompute Test Coverage Summary

**10 INV-07 tests covering auto-uncompute: basic firing, return preservation, qubit reuse, f.inverse after uncompute, None return, in-place skip, mode off, cache key, replay path, controlled context**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-04T22:49:44Z
- **Completed:** 2026-02-04T22:58:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- 10 new test functions covering all INV-07 auto-uncompute scenarios
- All 92 tests pass (82 existing + 10 new)
- Coverage of both capture and replay paths for auto-uncompute
- Edge cases: None return, in-place functions, controlled context, cache key separation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add INV-07 auto-uncompute tests** - `b55fc2e` (test)

## Files Created/Modified
- `tests/test_compile.py` - Added 10 test functions in AUTOUNCOMP section for INV-07

## Decisions Made
- Used `complex_fn` pattern (two qint allocations: temp + result) instead of simple `temp += x; return temp` because the simple pattern creates no temp qubits distinct from return qubits, so auto-uncompute has nothing to deallocate
- Verified deallocation via `total_deallocations` stat instead of `current_in_use` because the allocator's in-use count can be non-intuitive with non-contiguous qubit deallocation
- Used `result += b` (quantum-quantum addition) instead of `result += 1` (classical) for the preserves_return_value test because QFT addition with small classical values may not emit visible layers

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 53 complete: auto-uncompute implementation (plan 01) + comprehensive tests (plan 02)
- Ready for phase 54 or next milestone

---
*Phase: 53-qubit-saving-auto-uncompute*
*Completed: 2026-02-04*
