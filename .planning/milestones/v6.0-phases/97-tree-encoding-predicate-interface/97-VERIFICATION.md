---
phase: 97-tree-encoding-predicate-interface
status: passed
verified: 2026-03-02
requirements_verified: [TREE-01, TREE-02, TREE-03, PRED-01, PRED-02, PRED-03]
requirements_total: 6
requirements_passed: 6
---

# Phase 97: Tree Encoding & Predicate Interface - Verification

## Phase Goal

**Goal**: Users can create a QuantumBacktrackingTree with correct register layout and define accept/reject predicates that are validated before circuit construction

**Status: PASSED**

## Success Criteria Verification

### SC1: QWalkTree instantiation with correct registers
**Status: PASSED**
- `QWalkTree(max_depth=2, branching=2)` allocates height register of width 3 (max_depth+1) and 2 branch registers of width 1 each
- `QWalkTree(max_depth=3, branching=3)` allocates height register of width 4 and 3 branch registers of width 2 each
- Per-level branching `[2,3]` allocates branch widths [1, 2]
- Verified via tests: `test_binary_tree_registers`, `test_ternary_tree_registers`, `test_per_level_branching`

### SC2: Resource estimator with qubit budget enforcement
**Status: PASSED**
- `tree.total_qubits` returns correct count (e.g., 5 for depth=2, branching=2)
- `_check_qubit_budget()` raises ValueError when total > max_qubits
- Budget check is simulation-time only; large trees can be constructed
- Verified via tests: `test_budget_check_raises`, `test_budget_check_passes`, `test_very_large_tree_construction`

### SC3: Root state preparation verified via statevector
**Status: PASSED**
- Height qubit for max_depth set to |1> via emit_x at construction
- Qiskit statevector simulation confirms amplitude 1.0 at root basis state, 0.0 elsewhere
- Verified via test: `test_root_state_statevector`

### SC4: Predicate callable with mutual exclusion validation
**Status: PASSED**
- Predicate receives TreeNode with .depth (height register) and .branch_values (branch registers)
- Returns (is_accept, is_reject) as tuple of two qbools
- Mutual exclusion validated at construction: (True, True) raises ValueError
- Verified via tests: `test_mutual_exclusion_violation`, `test_predicate_receives_tree_node`

### SC5: Predicate uncomputation via @ql.compile
**Status: PASSED**
- @ql.compile decorated predicates detected (`_predicate_is_compiled = True`)
- `uncompute_predicate()` calls .adjoint() for compiled predicates
- Raw callables skip uncomputation (no-op)
- Predicate called at scope depth 0 to avoid LIFO interference
- Verified via tests: `test_uncompute_predicate_compiled`, `test_uncompute_predicate_raw_is_noop`

## Requirements Traceability

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| TREE-01 | QWalkTree with one-hot height register and branch registers | PASSED | walk.py QWalkTree class, 12 encoding tests |
| TREE-02 | Resource estimator with qubit count and budget enforcement | PASSED | total_qubits property, _check_qubit_budget(), 4 budget tests |
| TREE-03 | Node initialization with root state preparation | PASSED | Root state via emit_x, statevector verification test |
| PRED-01 | Accept/reject predicate interface with two qbools | PASSED | _validate_predicate(), 6 interface tests |
| PRED-02 | Predicate mutual exclusion validation | PASSED | .measure()-based check, 3 validation tests |
| PRED-03 | Predicate uncomputation via @ql.compile | PASSED | adjoint-based uncompute, 4 compiled predicate tests |

**Coverage: 6/6 requirements passed (100%)**

## Test Results

```
tests/python/test_walk_tree.py: 18 passed
tests/python/test_walk_predicate.py: 14 passed
Total: 32 passed, 0 failed
```

## Gaps

None identified.

---
*Phase: 97-tree-encoding-predicate-interface*
*Verified: 2026-03-02*
