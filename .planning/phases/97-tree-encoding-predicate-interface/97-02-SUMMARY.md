---
phase: 97-tree-encoding-predicate-interface
plan: 02
subsystem: quantum-walk
tags: [predicate, qbool, mutual-exclusion, compile, uncomputation]

requires:
  - phase: 97-01
    provides: QWalkTree class with TreeNode wrapper and register allocation

provides:
  - Predicate interface for QWalkTree (callable receiving TreeNode, returning qbool tuple)
  - Mutual exclusion validation at construction time
  - Compiled predicate detection and adjoint-based uncomputation
  - Type validation for predicate return values

affects: [98-local-diffusion, 99-walk-operators, 100-variable-branching, 101-detection-demo]

tech-stack:
  added: []
  patterns: [predicate-validation-at-construction, adjoint-uncompute-for-compiled-predicates]

key-files:
  created:
    - tests/python/test_walk_predicate.py
  modified:
    - src/quantum_language/walk.py

key-decisions:
  - "Use .measure() to read qbool classical values (cdef value field is private, not accessible via int())"
  - "Use .adjoint() for compiled predicate uncomputation instead of .inverse() (inverse proxy requires matching forward-call qubit tracking, which fails with TreeNode wrapper arguments)"
  - "Predicate called at scope depth 0 to avoid LIFO scope registration of returned qbools"

patterns-established:
  - "Predicate contract: callable(TreeNode) -> (is_accept: qbool, is_reject: qbool)"
  - "Mutual exclusion checked via .measure() on computational basis state"

requirements-completed: [PRED-01, PRED-02, PRED-03]

duration: 8min
completed: 2026-03-02
---

# Plan 97-02: Predicate Interface Summary

**Predicate interface with mutual exclusion validation, compiled predicate detection, and adjoint uncomputation for QWalkTree**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-02
- **Completed:** 2026-03-02
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Predicate callable receives TreeNode and returns (is_accept, is_reject) qbool tuple
- Mutual exclusion validated at construction: (True, True) raises ValueError
- @ql.compile decorated predicates detected and support adjoint-based uncomputation
- Type checking: wrong return type/length raises TypeError
- 14 tests covering all predicate interface paths

## Task Commits

1. **Task 1: Add predicate validation to QWalkTree** - `25d5e77` (feat)
2. **Task 2: Create predicate interface tests** - `25d5e77` (included in same commit)

## Files Created/Modified
- `src/quantum_language/walk.py` - Added _validate_predicate(), uncompute_predicate(), CompiledFunc detection
- `tests/python/test_walk_predicate.py` - 14 tests for predicate interface, mutual exclusion, compiled predicates

## Decisions Made
- Used .measure() instead of int() for qbool value access -- cdef value field is private in Cython
- Used .adjoint() instead of .inverse() for compiled predicate uncomputation -- inverse proxy cannot match TreeNode wrapper arguments
- Predicate qbools stored as tree._accept and tree._reject for walk operator access

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] qbool int() conversion not supported**
- **Found during:** Task 1 (predicate validation)
- **Issue:** Plan specified `int(is_accept)` but qbool (Cython cdef class) doesn't support `__int__`
- **Fix:** Used `.measure()` method which returns the classical initialization value
- **Files modified:** src/quantum_language/walk.py
- **Verification:** All predicate tests pass
- **Committed in:** 25d5e77

**2. [Rule 3 - Blocking] .inverse() fails with TreeNode arguments**
- **Found during:** Task 1 (uncompute_predicate implementation)
- **Issue:** Plan specified `.inverse(node)` but _AncillaInverseProxy requires matching forward-call qubit tracking which fails with TreeNode wrapper
- **Fix:** Used `.adjoint(node)` instead (standalone inverse replay, no forward-call tracking needed)
- **Files modified:** src/quantum_language/walk.py
- **Verification:** test_uncompute_predicate_compiled passes
- **Committed in:** 25d5e77

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for correctness with Cython internals. No scope creep.

## Issues Encountered
None beyond the deviations noted above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 97 complete: QWalkTree with tree encoding and predicate interface ready
- Walk operators (Phase 98) can reference tree.height_register, tree.branch_registers, tree._accept, tree._reject
- uncompute_predicate() ready for walk operator cleanup

---
*Phase: 97-tree-encoding-predicate-interface*
*Completed: 2026-03-02*
