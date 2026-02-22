---
status: diagnosed
trigger: "Controlled branch CRy not activating when control=|1>"
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - Test bitstring interpretation is wrong due to Qiskit qubit ordering convention
test: Traced full qubit allocation, gate emission, QASM export, and Qiskit measurement convention
expecting: n/a - root cause confirmed
next_action: Report findings

## Symptoms

expected: When control qubit is |1>, controlled branch CRy should activate, giving >95% probability on target
actual: Only ~51% probability observed - suggesting CRy is NOT being applied (target stays in equal superposition)
errors: "Control=|1> so target should be active, assert (0.0 + 0.509765625) > 0.95"
reproduction: Run test_controlled_branch_cry in TestBranchControlled
started: Unknown

## Eliminated

- hypothesis: emit_ry() does not detect controlled context
  evidence: Code at _gates.pyx:44-49 correctly checks _get_controlled() and calls cry() with ctrl.qubits[63] as control
  timestamp: 2026-02-20

- hypothesis: cry() C function does not populate gate_t correctly
  evidence: gate.c:180-187 correctly sets Gate=Ry, NumControls=1, Control[0]=control, GateValue=angle
  timestamp: 2026-02-20

- hypothesis: QASM export does not serialize CRy correctly
  evidence: circuit_output.c:414-417 correctly emits "cry(angle) q[ctrl], q[target];" for NumControls==1 Ry gates
  timestamp: 2026-02-20

- hypothesis: __exit__ uncomputes the target qbool (removing the CRy)
  evidence: target is created at scope 0 BEFORE the with block; __exit__ only uncomputes qbools in the scope frame (scope 1). target is not registered in scope 1's frame.
  timestamp: 2026-02-20

- hypothesis: CRy is not actually being emitted (branch() does not pass through controlled context)
  evidence: branch() in qint.pyx:589-590 calls emit_ry() for each qubit; emit_ry() handles the controlled context internally. The controlled flag is set by __enter__ before branch() runs.
  timestamp: 2026-02-20

## Evidence

- timestamp: 2026-02-20
  checked: Qubit allocation order for ctrl and target
  found: ctrl = ql.qbool(True) allocates qubit index 0 (first allocation, start=0, qubits[63]=0). target = ql.qbool(False) allocates qubit index 1 (second allocation, start=1, qubits[63]=1).
  implication: ctrl is q[0] (lower index), target is q[1] (higher index). In Qiskit bitstring convention, q[0] is the RIGHTMOST bit and q[1] is the LEFTMOST bit.

- timestamp: 2026-02-20
  checked: QASM output for the test circuit
  found: The generated QASM will be: x q[0]; (set ctrl=|1>), then cry(pi/2) q[0], q[1]; (CRy controlled by q[0] on q[1])
  implication: Circuit is correct - CRy is emitted with proper control and target

- timestamp: 2026-02-20
  checked: Qiskit bitstring convention in measurement results
  found: Qiskit reports measurement results with MSB on the left. For 2 qubits, bitstring "ab" means q[1]=a, q[0]=b. So "10" means q[1]=1, q[0]=0 and "01" means q[1]=0, q[0]=1.
  implication: The test's assumption "ctrl is always 1 (MSB)" is WRONG. ctrl is q[0] which is the LSB (rightmost bit in Qiskit strings).

- timestamp: 2026-02-20
  checked: Error message decomposition
  found: Error says (0.0 + 0.509765625) > 0.95, meaning p_10=0.0 and p_11~=0.51. The missing ~49% probability is in bitstring "01" (q[1]=0, q[0]=1 = target=0, ctrl=1). Results are: ~50% "01" (ctrl=1, target=0) + ~50% "11" (ctrl=1, target=1). This IS correct CRy behavior!
  implication: The CRy gate is working correctly. ctrl is always |1> (as expected). Target is in equal superposition (as expected from CRy(pi/2)). The test just looks at the wrong bitstrings.

- timestamp: 2026-02-20
  checked: Test assertion code at test_branch_superposition.py:220-226
  found: Test checks p_10 + p_11 > 0.95 with comment "ctrl is always 1 (MSB), target can be 0 or 1". But ctrl is q[0]=LSB, so the correct check should be p_01 + p_11 > 0.95. Bitstring "10" (q[1]=1,q[0]=0) means ctrl=0 which should have ~0% probability (correct - the test gets 0.0 for p_10). Bitstring "11" captures only the half where target=1.
  implication: The test is checking the wrong bitstrings due to a Qiskit qubit ordering misunderstanding.

## Resolution

root_cause: The test_controlled_branch_cry test has a QUBIT ORDERING BUG in its assertion. The test assumes ctrl (first allocated qbool) is the MSB in Qiskit's bitstring output, but Qiskit uses little-endian convention where q[0] is the RIGHTMOST bit. Since ctrl=q[0] and target=q[1], the correct expected bitstrings are "01" (ctrl=1, target=0) and "11" (ctrl=1, target=1), NOT "10" and "11". The CRy gate itself is emitted and serialized correctly - the circuit implementation is correct. The measured p_10=0.0 + p_11=0.51 ~= 0.51 is exactly what you get when you only count half the valid states ("11" captures target=1 only, missing the "01" where target=0 but ctrl is still correctly 1).

fix: (not applied - research only mode)
  The test assertions at lines 220-226 should be changed from:
    p_10 = counts.get("10", 0) / total  # Wrong: this is q[1]=1, q[0]=0 (ctrl=0)
    p_11 = counts.get("11", 0) / total
  To:
    p_01 = counts.get("01", 0) / total  # Correct: q[1]=0, q[0]=1 (ctrl=1, target=0)
    p_11 = counts.get("11", 0) / total  # Correct: q[1]=1, q[0]=1 (ctrl=1, target=1)
  And assertions should check p_01 + p_11 > 0.95 and abs(p_01 - 0.5) < 0.05 and abs(p_11 - 0.5) < 0.05.

verification: (not applied - research only mode)
files_changed: []
