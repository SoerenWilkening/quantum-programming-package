---
phase: 29-c-backend-bug-fixes
plan: 15
subsystem: circuit-lifecycle
tags: [circuit-reset, memory-management, BUG-05, cython]
dependency_graph:
  requires: []
  provides: [circuit-reset, clean-test-isolation]
  affects: [29-16, 29-17, 29-18]
tech_stack:
  added: []
  patterns: [type-check-dispatch-for-cdef-class-hierarchy]
key_files:
  created: []
  modified:
    - src/quantum_language/_core.pyx
decisions:
  - id: D29-15-1
    decision: "Use type(self) is circuit check to distinguish direct circuit() calls from subclass super().__init__()"
    rationale: "qint extends circuit; super().__init__() must NOT destroy the active circuit mid-construction"
metrics:
  duration: "~5 min"
  completed: "2026-01-31"
---

# Phase 29 Plan 15: Circuit Reset Fix Summary

**One-liner:** circuit() now frees old circuit, creates fresh one, and resets all Python globals -- fixing BUG-05 memory explosion and non-deterministic test results.

## What Was Done

### Task 1: Fix circuit() to properly reset all state on re-initialization
- Modified `circuit.__init__` to free the old C circuit via `free_circuit()` and allocate a fresh one via `init_circuit()` on every direct `circuit()` call
- Reset all Python-level global state: `_num_qubits`, `_int_counter`, `_smallest_allocated_qubit`, `_controlled`, `_control_bool`, `_list_of_controls`, `_global_creation_counter`, `_scope_stack`, and the legacy `ancilla` array
- Added `type(self) is circuit` guard to prevent subclass `super().__init__()` from destroying the active circuit (critical: `qint` extends `circuit`, so every `qint()` call triggers `circuit.__init__` via `super()`)
- Commit: `360256a`

### Task 2: Verify BUG-01 and BUG-04 still pass, and test determinism
- BUG-01: 5/5 subtraction tests pass individually
- BUG-04: 7/7 QFT addition tests pass individually
- Combined pytest run: 12/12 tests pass (proves circuit isolation between tests)
- 1*1 multiplication returns 1 deterministically across 2 consecutive circuit() calls

## Verification Results

| Criterion | Result |
|-----------|--------|
| circuit() called twice without error | PASS |
| BUG-01: 5/5 subtraction tests | PASS |
| BUG-04: 7/7 addition tests | PASS |
| Combined pytest run (12/12) | PASS |
| 1*1 multiplication deterministic | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Subclass super().__init__() destroying active circuit**
- **Found during:** Task 1
- **Issue:** `qint` extends `circuit`. When `qint.__init__` calls `super().__init__()`, the naive reset logic would free the circuit that `qint` is currently using (its local `_circuit` variable was captured before `super().__init__()` ran, becoming a dangling pointer -> segfault)
- **Fix:** Added `type(self) is circuit` check so only direct `circuit()` calls trigger reset, not subclass construction
- **Files modified:** `src/quantum_language/_core.pyx`
- **Commit:** `360256a`

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D29-15-1 | Use `type(self) is circuit` to guard reset | qint extends circuit; super().__init__() must not destroy active circuit mid-construction |

## Next Phase Readiness

BUG-05 is now fixed. This unblocks:
- Plan 29-16 (BUG-02 comparison fix) -- can now run comparison tests reliably in combined pytest
- Plan 29-17 (BUG-03 QQ_mul deeper investigation) -- deterministic results across circuit resets
- Plan 29-18 (final verification) -- all tests can run in single pytest process
