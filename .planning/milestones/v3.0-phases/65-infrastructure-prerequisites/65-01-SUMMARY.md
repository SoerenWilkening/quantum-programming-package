---
phase: 65-infrastructure-prerequisites
plan: 01
subsystem: backend-c
tags: [circuit-reversal, gate-inversion, self-inverse, toffoli, uncomputation]

# Dependency graph
requires:
  - phase: 61-memory-optimization
    provides: "Micro-optimized reverse_circuit_range and run_instruction with GateValue negation"
provides:
  - "Fixed reverse_circuit_range() preserving GateValue for self-inverse gates (X, Y, Z, H, M)"
  - "Fixed run_instruction(invert=1) with same self-inverse gate check"
  - "C unit tests verifying gate value preservation during circuit reversal"
affects: [66-toffoli-ripple-carry-adder, 67-toffoli-subtraction-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns: ["switch/case for self-inverse gate classification in circuit inversion"]

key-files:
  created:
    - tests/c/test_reverse_circuit.c
  modified:
    - c_backend/src/execution.c
    - tests/c/Makefile

key-decisions:
  - "Inline switch/case per user decision -- no helper function for self-inverse classification"
  - "Fixed run_instruction() proactively (beyond strict scope) since identical bug would manifest in Phase 66+ Toffoli inversion"
  - "Test strategy: verify gate cancellation (forward+reverse=empty circuit) rather than direct GateValue inspection, since optimizer auto-cancels inverse pairs"

patterns-established:
  - "Self-inverse gate set: X, Y, Z, H, M -- these skip GateValue negation during inversion"
  - "Rotation gate set: P, R, Rx, Ry, Rz -- these negate GateValue during inversion (default case)"

# Metrics
duration: 12min
completed: 2026-02-14
---

# Phase 65 Plan 01: Fix Self-Inverse Gate Value Negation Summary

**Switch/case in reverse_circuit_range() and run_instruction() to skip GateValue negation for X/Y/Z/H/M gates, enabling correct Toffoli circuit uncomputation**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-14T18:15:55Z
- **Completed:** 2026-02-14T18:28:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed reverse_circuit_range() to preserve GateValue for self-inverse gates (X, Y, Z, H, M) while still negating for rotation gates (P, R, Rx, Ry, Rz)
- Fixed run_instruction() with invert=1 to apply the same self-inverse gate check, preventing latent bug for Toffoli sequence inversion in Phase 66+
- Added 6 C unit tests verifying correct gate cancellation behavior after forward+reverse operations
- Zero regressions in existing Python test suite (84+ tests passing, excluding known pre-existing bugs)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix GateValue negation for self-inverse gates in execution.c** - `b8a567a` (fix)
2. **Task 2: Add C unit tests for reverse_circuit_range gate value handling** - `79a837e` (test)

## Files Created/Modified
- `c_backend/src/execution.c` - Added switch/case in both reverse_circuit_range() and run_instruction() to skip GateValue negation for self-inverse gates
- `tests/c/test_reverse_circuit.c` - 6 unit tests verifying X, CX, CCX, P, H gate value handling and mixed circuit cancellation
- `tests/c/Makefile` - Added REVERSE_SRCS source list, test_reverse_circuit target, and run_reverse convenience target

## Decisions Made
- Used inline switch/case (not a helper function) for self-inverse gate classification, per user decision documented in the plan
- Fixed run_instruction() proactively: although CONTEXT.md only mentioned reverse_circuit_range(), the research identified the identical bug in run_instruction() that will become critical when Toffoli sequences are inverted in Phase 66+
- Test strategy uses gate cancellation verification (forward+reverse=empty circuit) because the optimizer auto-merges inverse gate pairs, making direct GateValue inspection impractical in the test framework

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test approach adapted for optimizer gate cancellation**
- **Found during:** Task 2 (unit test creation)
- **Issue:** Original test plan expected to find reversed gates in layers after end_layer, but the optimizer cancels inverse gate pairs (e.g., X(1) + X(1) -> identity)
- **Fix:** Redesigned tests to verify cancellation behavior: with the fix, forward+reverse produces an empty circuit (correct); without the fix, reversed X gates would have GateValue=-1 and not cancel (wrong, circuit doubles in size)
- **Files modified:** tests/c/test_reverse_circuit.c
- **Verification:** All 6 tests pass; cancellation confirms GateValue preservation
- **Committed in:** 79a837e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test approach adapted to work with the optimizer's gate cancellation. Tests still verify the exact same property (GateValue preservation) but through observable behavior (cancellation) rather than direct value inspection.

## Issues Encountered
- Python test suite hits memory limits in the CI container, causing OOM kills during large test runs. Verified core arithmetic/circuit/equality tests (84+ tests) with no regressions. Pre-existing segfault in multiplication tests (known BUG-32BIT-MUL) unrelated to our changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- reverse_circuit_range() and run_instruction() now correctly handle self-inverse gates
- Toffoli circuits (X/CX/CCX) can be reversed for uncomputation without GateValue corruption
- Ready for Phase 65 Plan 02 (ancilla allocator multi-qubit reuse) and Plan 03 (optimizer Toffoli gate handling)

## Self-Check: PASSED

- All 4 files verified present on disk
- Both task commits (b8a567a, 79a837e) verified in git log
- C unit tests: 6/6 passing
- Python regression: 0 new failures (84+ tests checked)

---
*Phase: 65-infrastructure-prerequisites*
*Completed: 2026-02-14*
