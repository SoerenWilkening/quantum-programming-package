---
status: diagnosed
trigger: "QiskitError 'No counts for experiment 0' in Phase 76 tests — 28 tests fail, 3 pass"
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - _simulate_qasm() in test_branch_superposition.py does not add measurement instructions before running Qiskit Aer
test: Compared _simulate_qasm (broken) with _simulate_and_extract from test_cross_backend.py (working)
expecting: Working function adds measurements; broken one does not
next_action: Return diagnosis

## Symptoms

expected: Tests pass -- _simulate_qasm() returns counts dict with qubit measurement results
actual: qiskit.exceptions.QiskitError: 'No counts for experiment "0"' -- 28/31 tests fail
errors: QiskitError 'No counts for experiment "0"' at result.get_counts()
reproduction: Run pytest tests/python/test_branch_superposition.py
started: After fixing ql.openqasm() -> ql.to_openqasm() naming issue

## Eliminated

## Evidence

- timestamp: 2026-02-20T00:01:00Z
  checked: c_backend/src/circuit_output.c lines 535-602 (circuit_to_qasm_string)
  found: QASM export only includes `measure` instructions if explicit M gates exist in circuit. It counts measurements first (_count_measurements), only declares `bit[N] c;` if count > 0, and only emits `c[i] = measure q[j];` for Gate == M.
  implication: The branch() method emits Ry gates only -- no measurement gates are added to the circuit. The QASM output will have no measure instructions.

- timestamp: 2026-02-20T00:02:00Z
  checked: src/quantum_language/qint.pyx lines 765-785 (qint.measure method)
  found: The measure() method is a simulation placeholder that just returns self.value. It does NOT emit a measurement gate (Gate == M) into the circuit.
  implication: There is no Python API to emit measurement gates into the circuit for QASM export.

- timestamp: 2026-02-20T00:03:00Z
  checked: tests/python/test_branch_superposition.py lines 35-41 (_simulate_qasm function)
  found: Function loads QASM via qiskit.qasm3.loads(), transpiles, runs with 8192 shots, then calls result.get_counts(). It does NOT add measurements to the loaded circuit.
  implication: Without measurements, Qiskit Aer has no classical bits to report -- get_counts() raises QiskitError.

- timestamp: 2026-02-20T00:04:00Z
  checked: tests/python/test_cross_backend.py lines 160-194 (_simulate_and_extract function)
  found: This WORKING helper has the fix: `if not circuit.cregs: circuit.measure_all()` on lines 175-176. It checks whether the loaded QASM circuit has classical registers; if not, it adds measure_all() to measure every qubit before running.
  implication: This is the established pattern in the codebase for handling QASM circuits that lack measurement instructions. The test_branch_superposition.py helper was not written with this pattern.

## Resolution

root_cause: _simulate_qasm() in test_branch_superposition.py (line 35-41) does not add measurement instructions to the Qiskit circuit before simulation. The QASM output from ql.to_openqasm() contains only gate operations (Ry, H, Z, etc.) with no measure instructions, because the C backend only emits `measure` for explicit M gates in the circuit, and branch()/emit_h()/emit_z()/emit_mcz() do not add M gates. Without measurements, Qiskit Aer's result.get_counts() has no classical data to return, raising QiskitError "No counts for experiment 0".
fix: Add `circuit.measure_all()` to _simulate_qasm() after loading the QASM, matching the pattern used in test_cross_backend.py. Specifically, after `circuit = qiskit.qasm3.loads(qasm_str)`, add `if not circuit.cregs: circuit.measure_all()`.
verification:
files_changed: []
