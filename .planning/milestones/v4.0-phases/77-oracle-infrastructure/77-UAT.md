---
status: complete
phase: 77-oracle-infrastructure
source: 77-01-SUMMARY.md, 77-02-SUMMARY.md
started: 2026-02-20T17:00:00Z
updated: 2026-02-20T17:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Oracle Decorator Available as ql.grover_oracle
expected: `import quantum_language as ql` succeeds and `ql.grover_oracle` is a callable decorator. Using it as `@ql.grover_oracle`, `@ql.grover_oracle()`, or `@ql.grover_oracle(validate=False)` all work without import errors.
result: pass

### 2. Compute-Phase-Uncompute Validation
expected: An oracle function that does NOT follow compute-phase-uncompute ordering raises a validation error at circuit generation time. A correctly ordered oracle passes validation silently.
result: pass

### 3. Ancilla Delta Enforcement
expected: An oracle function that allocates ancilla qubits but doesn't deallocate them raises an error. An oracle with zero ancilla delta (all ancillas properly cleaned up) passes.
result: skipped
reason: User satisfied from Test 2 verification

### 4. Bit-Flip Auto-Wrapping (Phase Kickback)
expected: Using `@ql.grover_oracle(bit_flip=True)` wraps the oracle function with X-H-oracle-H-X phase kickback gates automatically.
result: skipped
reason: User satisfied from manual review

### 5. Oracle Caching
expected: Calling the same oracle function multiple times returns a cached circuit. Changing arithmetic mode or qubit width produces a cache miss.
result: skipped
reason: User satisfied from manual review

### 6. emit_x Gate Primitive
expected: The `emit_x` C-level gate primitive was added to `_gates.pyx` and the package compiles successfully.
result: skipped
reason: User satisfied from manual review

### 7. Oracle Test Suite Passes
expected: Running `pytest tests/python/test_oracle.py -v` executes all 37 oracle tests and they all pass.
result: skipped
reason: User satisfied from manual review

### 8. No Regressions in Existing Tests
expected: Running `pytest tests/python/ -v` shows that all pre-existing tests still pass.
result: skipped
reason: User satisfied from manual review

## Summary

total: 8
passed: 2
issues: 0
pending: 0
skipped: 6

## Gaps

[none yet]
