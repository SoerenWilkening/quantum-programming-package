---
phase: 99-walk-operators
plan: 01
subsystem: quantum-walk
tags: [walk-operators, montanaro, ql-compile, disjointness]

requires:
  - phase: 98-local-diffusion-operator
    provides: local_diffusion(depth) with height-controlled dispatch
provides:
  - R_A() method for even-depth reflections
  - R_B() method for odd-depth + root reflections
  - walk_step() compiled walk operator U = R_B * R_A
  - verify_disjointness() structural correctness check
  - _all_qubits_register() helper for compile wrapping
affects: [99-02, 100-variable-branching, 101-detection-demo]

tech-stack:
  added: []
  patterns: [all-qubits-register compile pattern, parity-controlled depth loop]

key-files:
  created: []
  modified: [src/quantum_language/walk.py]

key-decisions:
  - "Pass all tree qubits as compile argument via _all_qubits_register() to avoid forward-call tracking conflicts"
  - "R_A excludes root even when max_depth is even (Montanaro convention)"
  - "Disjointness checked at construction time as defensive assertion"

patterns-established:
  - "All-qubits-register pattern: bundle all tree qubits into a single qint for @ql.compile wrapping to avoid ancilla tracking conflicts with nested compiled operations"

requirements-completed: [WALK-01, WALK-02, WALK-03, WALK-04, WALK-05]

duration: 8min
completed: 2026-03-02
---

# Phase 99 Plan 01: Walk Operators Summary

**R_A, R_B, walk_step (compiled), and verify_disjointness on QWalkTree with all-qubits compile pattern**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-02
- **Completed:** 2026-03-02
- **Tasks:** 3 (combined into single commit)
- **Files modified:** 1

## Accomplishments
- R_A iterates even depths (0,2,...) excluding root, calling local_diffusion
- R_B iterates odd depths (1,3,...) plus root, with correct max_depth parity handling
- walk_step compiles U = R_B * R_A lazily via @ql.compile with total_qubits cache key
- verify_disjointness returns height control qubit sets with disjoint=True for all valid trees
- Construction-time disjointness validation provides fail-fast error

## Task Commits

1. **Tasks 1-3: R_A, R_B, verify_disjointness, walk_step** - `edc069e` (feat)

## Files Created/Modified
- `src/quantum_language/walk.py` - Added R_A(), R_B(), verify_disjointness(), _all_qubits_register(), walk_step() methods + __init__ changes

## Decisions Made
- Used _all_qubits_register() to pass all tree qubits as the compile argument, preventing forward-call tracking from blocking repeated walk_step() calls. The issue: local_diffusion uses height-control qubits via `with h_ctrl:` which get captured as internal qubits by @ql.compile.
- R_A excludes root regardless of max_depth parity per Montanaro convention
- Disjointness checks height control qubits only (not all touched qubits) since adjacent-depth operators share child height qubits but are controlled on different primary height qubits

## Deviations from Plan

### Auto-fixed Issues

**1. Compile forward-call tracking conflict**
- **Found during:** Task 3 (walk_step implementation)
- **Issue:** Calling walk_step() twice on the same tree caused ValueError because @ql.compile's forward-call tracking detected uninverted ancilla allocation from height control qubits captured during local_diffusion
- **Fix:** Created _all_qubits_register() to bundle all tree qubits into a single qint argument, so no qubits are treated as internal ancillas
- **Files modified:** src/quantum_language/walk.py
- **Verification:** walk_step() callable multiple times; controlled variant works via `with qbool:`
- **Committed in:** edc069e

---

**Total deviations:** 1 auto-fixed (compile infrastructure adaptation)
**Impact on plan:** Essential fix for walk_step to be usable in detection loop (Phase 101). No scope creep.

## Issues Encountered
None beyond the compile wrapping deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Walk operators ready for statevector testing (Plan 99-02)
- walk_step() callable multiple times for detection loop
- Controlled variant works for phase estimation

---
*Phase: 99-walk-operators*
*Completed: 2026-03-02*
