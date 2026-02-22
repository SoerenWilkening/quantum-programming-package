---
status: complete
phase: 78-diffusion-operator
source: 78-01-SUMMARY.md, 78-02-SUMMARY.md, 78-03-SUMMARY.md
started: 2026-02-21T00:00:00Z
updated: 2026-02-21T00:08:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Diffusion test suite passes (22 tests)
expected: Run `pytest tests/python/test_diffusion.py -v` — all 22 tests pass (12 diffusion operator + 10 phase property tests)
result: pass

### 2. ql.diffusion() produces X-MCZ-X QASM pattern
expected: Calling `ql.diffusion(x)` on a 3-qubit qint produces QASM with 6 X gates sandwiching a multi-controlled Z gate, using exactly 3 qubits (zero ancilla)
result: pass

### 3. Statevector S_0 reflection correct
expected: After `x.branch(); ql.diffusion(x)` on a 2-qubit register, Qiskit statevector shows |00> amplitude has opposite sign from |01>, |10>, |11> — confirming S_0 reflection
result: pass

### 4. x.phase += theta syntax works on qint
expected: `x.phase += 3.14` compiles without error. Outside a controlled context, no gates are emitted (global phase is unobservable). Inside `with flag:`, a P(theta) gate is emitted on the control qubit.
result: pass

### 5. Manual S_0 path: with x == 0: x.phase += pi
expected: `with x == 0: x.phase += math.pi` produces the same S_0 reflection as `ql.diffusion(x)` — verified by Qiskit statevector showing |00> negative, all others positive. QASM contains a visible P gate (not self-controlled CP).
result: pass

### 6. Multi-register and qarray diffusion
expected: `ql.diffusion(x, y)` on 2-qubit + 1-qubit registers produces 3-qubit diffusion (6 X gates + MCZ). `ql.diffusion(arr)` on a 2-element qbool qarray produces 2-qubit diffusion (4 X gates + CZ).
result: pass

### 7. ql.diffusion accessible from top-level namespace
expected: `import quantum_language as ql; ql.diffusion` resolves without ImportError. The function is listed in `ql.__all__`.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
