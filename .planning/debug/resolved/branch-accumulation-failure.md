---
status: resolved
trigger: "Double branch(0.5) not accumulating to |1>"
created: 2026-02-20T00:00:00Z
updated: 2026-02-26T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED AND FIXED -- gates_are_inverse() in gate.c was missing negation check for Ry/Rx/Rz rotation gates
test: Ran test_double_branch_accumulates and full test_branch_superposition.py suite
expecting: All 31 tests pass
next_action: Archive session

## Symptoms

expected: Two branch(0.5) calls = Ry(pi/2) + Ry(pi/2) = Ry(pi) = flip |0> to |1>, P(1) > 0.95
actual: P(1) = 0.0000 -- qubit remains in |0>
errors: "Double branch(0.5) should give |1>, got P(1)=0.0000"
reproduction: Run test_double_branch_accumulates in TestBranchAccumulation class
started: Test is newly written for Phase 76

## Eliminated

- hypothesis: Second branch() overwrites _start_layer/_end_layer causing uncomputation of first Ry
  evidence: _start_layer/_end_layer ARE overwritten, but uncomputation only happens in __del__/_do_uncompute, which is not called before to_openqasm(). The qbool x is still alive when QASM is exported. This is a real issue for uncomputation tracking but NOT the cause of P(1)=0.0.
  timestamp: 2026-02-20T00:00:30Z

- hypothesis: QASM export filters or merges gates
  evidence: circuit_to_qasm_string() in circuit_output.c iterates all layers and gates without filtering. It faithfully exports whatever is in the circuit data structure. The bug is upstream.
  timestamp: 2026-02-20T00:00:40Z

## Evidence

- timestamp: 2026-02-20T00:00:10Z
  checked: branch() method in qint.pyx (lines 519-598)
  found: branch() computes theta = 2*arcsin(sqrt(prob)), calls emit_ry() for each qubit. For prob=0.5, theta=pi/2. Two calls emit two separate Ry(pi/2) via emit_ry(). Layer tracking (_start_layer/_end_layer) is overwritten on second call, but this only affects uncomputation, not gate emission.
  implication: The branch() method itself correctly emits two Ry gates. The issue is downstream in how gates are stored.

- timestamp: 2026-02-20T00:00:20Z
  checked: emit_ry() in _gates.pyx (lines 33-53)
  found: emit_ry() creates a gate_t, calls ry() to initialize it, then calls add_gate(circ, &g). No caching, no deduplication at this level.
  implication: Each branch(0.5) call does reach add_gate() with a valid Ry(pi/2) gate.

- timestamp: 2026-02-20T00:00:30Z
  checked: add_gate() in optimizer.c (lines 163-215)
  found: add_gate() contains gate optimization logic. It calls colliding_gates() to find gates on the same qubit in the previous layer, then calls gates_are_inverse() to check if the new gate is the inverse of the existing gate. If so, it calls merge_gates() which REMOVES BOTH gates from the circuit (lines 198-200).
  implication: The optimizer is the gatekeeper for all gates entering the circuit. If it incorrectly identifies two gates as inverses, it will cancel them.

- timestamp: 2026-02-20T00:00:40Z
  checked: gates_are_inverse() in gate.c (lines 526-555)
  found: "SMOKING GUN" -- For non-P rotation gates (Ry, Rx, Rz), the inverse check is `G1->GateValue != G2->GateValue`. If both gates have the SAME angle (e.g., pi/2), this condition is FALSE, causing the function to return TRUE (incorrectly claiming they are inverses). The P gate has correct logic: `G1->GateValue != -G2->GateValue` (checks negated angle). Ry/Rx/Rz LACK this negation check.
  implication: Two Ry(pi/2) gates on the same qubit are wrongly identified as inverses and cancelled by the optimizer, resulting in zero gates and P(1)=0.0.

- timestamp: 2026-02-20T00:00:45Z
  checked: Self-inverse gate correctness
  found: X*X=I, H*H=I, Z*Z=I -- these are all self-inverse, so the "same GateValue = inverse" logic is accidentally correct for them (GateValue is 0 for these gates). The bug only manifests for rotation gates with nonzero angles.
  implication: Existing tests for X, H, Z gates would not catch this bug. Only rotation gates (Ry, Rx, Rz) with repeated application expose it.

- timestamp: 2026-02-20T00:00:50Z
  checked: Secondary issue -- _start_layer/_end_layer overwrite in branch()
  found: The second call to branch() overwrites self._start_layer and self._end_layer (qint.pyx lines 594-595). This means _do_uncompute() would only reverse the SECOND Ry gate's layer range, not the first. However, since both gates are cancelled by the optimizer, the circuit has zero gates and this secondary issue is masked.
  implication: Even if the primary bug is fixed, the layer tracking overwrite is a secondary bug that would cause incorrect uncomputation when branch() is called multiple times. The fix for branch() should accumulate layer ranges rather than overwrite them.

- timestamp: 2026-02-26T00:00:00Z
  checked: Fix verification -- gates_are_inverse() now includes Ry/Rx/Rz in negation check (commit 250bb56)
  found: Line 544 of gate.c now reads `if (G1->Gate == P || G1->Gate == Ry || G1->Gate == Rx || G1->Gate == Rz)`. The fix was already applied. test_double_branch_accumulates PASSES with P(1) > 0.95. Full suite of 31 tests in test_branch_superposition.py all pass with zero failures.
  implication: Root cause is confirmed fixed. Two Ry(pi/2) gates now correctly accumulate to Ry(pi) instead of being cancelled.

## Resolution

root_cause: gates_are_inverse() in c_backend/src/gate.c (line 544) incorrectly treated rotation gates (Ry, Rx, Rz) with identical angles as inverses. The check `G1->GateValue != G2->GateValue` returned false when both angles were equal (e.g., pi/2), causing the function to return true. The optimizer's add_gate() then cancelled both gates via merge_gates(), leaving zero gates in the circuit. The correct inverse check for rotation gates verifies NEGATED angles: Ry(theta)^{-1} = Ry(-theta), NOT Ry(theta).
fix: Extended the P-gate negation condition in gates_are_inverse() (line 544) to include Ry, Rx, and Rz gates. Changed `if (G1->Gate == P)` to `if (G1->Gate == P || G1->Gate == Ry || G1->Gate == Rx || G1->Gate == Rz)`. This was applied in commit 250bb56.
verification: All 31 tests in test_branch_superposition.py pass, including test_double_branch_accumulates (P(1) > 0.95). Verified on 2026-02-26.
files_changed: [c_backend/src/gate.c]
