---
phase: 99-walk-operators
type: verification
date: 2026-03-02
status: PASSED
---

# Phase 99: Walk Operators -- Verification

## Phase Goal

Implement walk operators R_A, R_B, composed walk step U = R_B * R_A, @ql.compile wrapping, and qubit disjointness validation on QWalkTree.

## Requirements Verification

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| WALK-01 | R_A applies even-depth reflections, excluding root | PASS | R_A loops even depths (0,2,...), skips max_depth. 3 tests in TestRAOperator confirm via statevector. |
| WALK-02 | R_B applies odd-depth reflections plus root | PASS | R_B loops odd depths + root (even max_depth handled). 4 tests in TestRBOperator confirm. |
| WALK-03 | walk_step composes U = R_B * R_A | PASS | walk_step calls R_A then R_B. 6 tests in TestWalkStep verify composition, non-identity, norm. |
| WALK-04 | walk_step compiled with lazy @ql.compile | PASS | First call captures, subsequent replay. _all_qubits_register() avoids ancilla tracking. 6 tests in TestWalkStepCompiled. |
| WALK-05 | verify_disjointness validates R_A/R_B separation | PASS | Height control qubit sets disjoint for all valid trees. Construction-time validation. 6 tests in TestDisjointness. |

## Artifact Verification

| Artifact | Expected | Actual | Status |
|----------|----------|--------|--------|
| src/quantum_language/walk.py | R_A, R_B, walk_step, verify_disjointness, _all_qubits_register | All present | PASS |
| tests/python/test_walk_operators.py | >= 15 tests | 25 tests, 530 lines | PASS |

## Test Results

```
tests/python/test_walk_operators.py: 25 passed
tests/python/test_walk_tree.py + test_walk_predicate.py + test_walk_diffusion.py: 57 passed
Total walk tests: 82 passed, 0 failed
```

## Key Decisions Validated

1. **_all_qubits_register() pattern**: Essential for @ql.compile to avoid forward-call tracking conflicts with height-controlled local_diffusion. Without this, walk_step cannot be called twice.
2. **Root always in R_B**: Montanaro convention correctly implemented -- R_A excludes root regardless of max_depth parity.
3. **Height qubit disjointness**: Checking primary height control qubits (not all physically touched qubits) correctly identifies the disjoint partition.

## Plans Completed

| Plan | Description | Status | Commit |
|------|-------------|--------|--------|
| 99-01 | R_A, R_B, walk_step, verify_disjointness implementation | Complete | edc069e |
| 99-02 | Statevector verification tests (25 tests) | Complete | 47d63de |

## Regression Check

No regression on Phase 97/98 tests. All 82 walk tests pass.

## Verdict

**PASSED** -- All 5 requirements verified. Walk operators ready for Phase 100 (Variable Branching) and Phase 101 (Detection Demo).
