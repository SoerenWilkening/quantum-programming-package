---
phase: 97-tree-encoding-predicate-interface
plan: 01
subsystem: quantum-walk
tags: [montanaro, backtracking, tree-encoding, one-hot, qint, statevector]

requires:
  - phase: none
    provides: first phase of v6.0

provides:
  - QWalkTree class with one-hot height register and per-level branch registers
  - TreeNode wrapper for predicate evaluation interface
  - Automatic root state preparation
  - Simulation-time qubit budget enforcement
  - Top-level QWalkTree export from quantum_language

affects: [97-02-predicate-interface, 98-local-diffusion, 99-walk-operators, 100-variable-branching, 101-detection-demo]

tech-stack:
  added: []
  patterns: [one-hot-height-encoding, per-level-branch-registers, emit_x-root-prep]

key-files:
  created:
    - src/quantum_language/walk.py
    - tests/python/test_walk_tree.py
  modified:
    - src/quantum_language/__init__.py

key-decisions:
  - "Root height qubit is MSB of height register (qubits[63]), set via emit_x at construction"
  - "Branch registers are plain Python list of qint (not qarray) for independent per-level access"
  - "Qubit budget check is simulation-time only (_check_qubit_budget method), not construction-time"
  - "TreeNode uses __slots__ for lightweight state wrapping"

patterns-established:
  - "QWalkTree constructor: allocate registers eagerly, prepare root state automatically"
  - "Branch width calculation: max(1, ceil(log2(branching))) handles branching=1 edge case"

requirements-completed: [TREE-01, TREE-02, TREE-03]

duration: 8min
completed: 2026-03-02
---

# Plan 97-01: QWalkTree Class + Tree Encoding Summary

**QWalkTree class with one-hot height register, per-level branch registers, automatic root state prep, and 18 passing tests including Qiskit statevector verification**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-02
- **Completed:** 2026-03-02
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- QWalkTree class allocates one-hot height register (max_depth+1 qubits) and per-level branch registers with correct widths
- Root state automatically prepared at construction (height qubit for max_depth set to |1>)
- TreeNode accessor wraps registers for predicate evaluation interface
- Simulation-time qubit budget enforcement via _check_qubit_budget()
- 18 tests covering register dimensions, root statevector, budget enforcement, edge cases

## Task Commits

1. **Task 1: Create QWalkTree and TreeNode classes** - `6578949` (feat)
2. **Task 2: Create tree encoding tests** - `6578949` (included in same commit)

## Files Created/Modified
- `src/quantum_language/walk.py` - QWalkTree and TreeNode classes with tree encoding
- `src/quantum_language/__init__.py` - Added QWalkTree import and __all__ entry
- `tests/python/test_walk_tree.py` - 18 tests for register allocation, root state, budget

## Decisions Made
- Root height qubit at qubits[63] (MSB) set via emit_x -- follows right-aligned qint convention
- Branch registers as plain list of qint rather than qarray -- per research recommendation for independent per-level access
- Budget enforcement is simulation-time only -- constructor allows any size tree

## Deviations from Plan
None - plan executed as specified

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- QWalkTree class ready for predicate interface (Plan 97-02)
- TreeNode._max_depth stored for predicate validation
- _predicate slot ready for validation in Plan 97-02

---
*Phase: 97-tree-encoding-predicate-interface*
*Completed: 2026-03-02*
