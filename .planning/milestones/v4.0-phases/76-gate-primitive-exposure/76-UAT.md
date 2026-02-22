---
status: all_passed
phase: 76-gate-primitive-exposure
source: 76-01-SUMMARY.md, 76-02-SUMMARY.md, 76-03-SUMMARY.md, 76-04-SUMMARY.md, 76-05-SUMMARY.md, 76-06-SUMMARY.md
started: 2026-02-20T10:00:00Z
updated: 2026-02-20T13:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Build and Import
expected: Package builds with C compiler and imports without error.
result: pass

### 2. branch(0.5) Equal Superposition
expected: branch(0.5) creates equal superposition for widths 1-8.
result: pass (all 8 parametrized widths pass)

### 3. branch() Probability Values
expected: branch() works with probabilities 0, 0.3, 0.5, 0.7, 1.0.
result: pass

### 4. qbool.branch() Method
expected: qbool (1-qubit type) supports branch() inherited from qint.
result: pass

### 5. Indexed branch (x[i].branch())
expected: Can target specific qubit for superposition via indexing. x[0].branch(0.5) only affects qubit 0.
result: pass (fixed in plan 05: __getitem__ right-aligned offset)

### 6. Controlled branch (inside with block)
expected: branch() inside a with qbool block emits CRy instead of plain Ry. Control=|1> should activate target.
result: pass (fixed in plan 05: Qiskit little-endian bitstring convention in test)

### 7. branch() Validation
expected: branch(-0.1) and branch(1.5) raise ValueError.
result: pass

### 8. @ql.compile Integration
expected: branch() works inside @ql.compile decorated functions.
result: pass

### 9. Branch Accumulation
expected: Two branch(0.5) calls should accumulate to give |1> with high probability (Ry(pi/2) + Ry(pi/2) = Ry(pi) = |1>).
result: pass (fixed in plans 04: gates_are_inverse negated-angle check + layer accumulation)

### 10. Internal Gate Emission
expected: Internal gate emission functions (emit_h, emit_z, emit_ry) work correctly.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

All three gaps resolved by plans 04 and 05, verified by plan 06 rebuild:

- truth: "Indexed branch x[i].branch(0.5) only affects targeted qubit"
  status: resolved (plan 05)
  fix: "__getitem__ uses right-aligned offset 64-self.bits+item"

- truth: "Controlled branch emits CRy when inside with qbool block, activating target when control=|1>"
  status: resolved (plan 05)
  fix: "Test corrected to Qiskit little-endian bitstrings '01'/'11'"

- truth: "Two branch(0.5) calls accumulate: Ry(pi/2)+Ry(pi/2)=Ry(pi) giving |1>"
  status: resolved (plan 04)
  fix: "gates_are_inverse negated-angle check + _start_layer min/max accumulation"
