---
phase: 100-variable-branching
plan: 01
subsystem: quantum-walk
tags: [variable-branching, diffusion, predicate-evaluation, conditional-rotation]

requires:
  - phase: 99-walk-operators
    plan: 02
    provides: R_A(), R_B(), walk_step() on QWalkTree
provides:
  - Variable branching local diffusion via _variable_diffusion()
  - Precomputed angle tables for d=1..d_max (_variable_angles, _variable_root_angles)
  - Fast-path auto-detection (_use_variable_branching property)
  - Multi-controlled Ry and cascade helper functions
  - Full backward compatibility with Phase 97-99
affects: [100-02-tests, 101-detection-demo]

tech-stack:
  added: [itertools]
  patterns: [multi-controlled V-gate decomposition, validity ancilla pattern matching]

key-files:
  created: []
  modified: [src/quantum_language/walk.py]

key-decisions:
  - "Fast-path dispatch: predicate is None -> existing uniform path, zero overhead"
  - "Validity ancilla semantics: validity[i]=|1> means child i is valid (NOT rejected)"
  - "Pattern matching via X-flip sandwich on validity ancillae for each d(x) combination"
  - "Multi-controlled Ry uses recursive V-gate decomposition for 3+ controls"
  - "S_0 reflection is independent of d(x) - operates on full local subspace"
  - "Each predicate call allocates new qbools - compiled predicates needed for qubit efficiency"

patterns-established:
  - "_emit_multi_controlled_ry: recursive V-gate decomposition for arbitrary control count"
  - "_emit_cascade_multi_controlled: cascade ops with additional multi-qubit controls"
  - "Evaluate-store-diffuse-uncompute pattern for predicate-based variable branching"

requirements-completed: [DIFF-04]

duration: 15min
completed: 2026-03-02
---

# Phase 100 Plan 01: Variable Branching Implementation Summary

**Variable branching local diffusion with predicate evaluation, conditional angle dispatch, and fast-path auto-detection**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-02
- **Completed:** 2026-03-02
- **Tasks:** 2 (combined into single commit)
- **Files modified:** 1

## Accomplishments
- Added 406 lines to walk.py implementing variable branching support
- _variable_diffusion() evaluates predicate on each potential child, stores validity in ancilla qbools, dispatches conditional Ry rotations based on pattern matching
- Precomputed angle tables (_variable_angles, _variable_root_angles) for all d=1..d_max at construction time
- Fast-path auto-detection: trees without predicate use existing uniform path with zero overhead
- Multi-controlled helper functions (_emit_multi_controlled_ry, _emit_multi_controlled_x, _emit_cascade_multi_controlled) using recursive V-gate decomposition
- All 82 existing Phase 97-99 tests pass unchanged (full backward compatibility)

## Task Commits

1. **Tasks 1-2: Variable branching implementation** - `e844c61` (feat)

## Files Created/Modified
- `src/quantum_language/walk.py` - +406 lines: variable branching diffusion, helper functions, angle tables

## Decisions Made
- Validity ancilla semantics: validity[i]=|1> means valid (NOT rejected). Computed via CNOT from reject + X flip.
- Pattern matching: for each possible d(x) value, iterate all combinations of d(x) valid children among d_max, use X-flip sandwich to match the pattern, then multi-controlled rotation.
- S_0 reflection is unchanged from uniform case - operates on full local subspace (branch_reg + h[depth-1]), independent of d(x). Invalid children get zero amplitude from conditional rotation.
- Each raw predicate call allocates new qbools. For qubit-efficient testing, compiled predicates (@ql.compile) should be used.

## Deviations from Plan

None - implementation follows plan structure.

## Issues Encountered

**Qubit growth with raw predicates:** Each predicate evaluation allocates 2 new qbools (accept, reject). For binary branching with 2 children, each diffusion call adds 2 validity + 8 predicate qbools = 10 extra qubits. This means D_x^2 = I reflection tests need compiled predicates to stay within 17-qubit budget. This is by design - the framework's qubit allocation is permanent.

## User Setup Required
None

## Next Phase Readiness
- Variable branching implementation ready for statevector verification tests (100-02)
- Tests should use compiled predicates for qubit efficiency
- Binary tree depth=2 is the primary test tree (5 tree qubits + overhead within 17)

---
*Phase: 100-variable-branching*
*Completed: 2026-03-02*
