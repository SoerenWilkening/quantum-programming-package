---
status: resolved
trigger: "Indexed branch x[i].branch() not targeting correct qubit — test_multiple_indexed_branches fails"
created: 2026-02-20T00:00:00Z
updated: 2026-02-26T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED and FIXED — __getitem__ used raw index into 64-element array instead of right-aligned offset
test: pytest tests/python/test_branch_superposition.py -v (all 31 tests)
expecting: all pass
next_action: archive session

## Symptoms

expected: x[0].branch(0.5) and x[2].branch(0.5) on 3-qubit qint yield P=0.25 for |000>
actual: P=1.0 for |000> — branch calls have NO effect
errors: AssertionError in test_multiple_indexed_branches
reproduction: run pytest tests/python/test_branch_superposition.py::TestBranchIndexed::test_multiple_indexed_branches
started: introduced with __getitem__ implementation

## Eliminated

- hypothesis: branch() method itself has wrong qubit targeting
  evidence: branch() correctly uses self_offset = 64 - self.bits for right-aligned storage (qint.pyx line 588-590)
  timestamp: 2026-02-20

- hypothesis: emit_ry() silently drops gates for invalid qubit indices
  evidence: emit_ry() in _gates.pyx unconditionally calls ry() or cry() C function and add_gate() — no validation, just emits to wrong target
  timestamp: 2026-02-20

- hypothesis: qbool created by __getitem__ loses connection to parent circuit
  evidence: qbool(create_new=False, bit_list=...) correctly initializes with bits=1 and inherits branch() from qint; the problem is the qubit INDEX in bit_list, not the circuit connection
  timestamp: 2026-02-20

## Evidence

- timestamp: 2026-02-20
  checked: qint.__init__ qubit storage layout (qint.pyx lines 224-226)
  found: Qubits are RIGHT-ALIGNED in 64-element array. For width=3, qubits stored at indices [61]=start, [62]=start+1, [63]=start+2. Indices [0] through [60] are UNINITIALIZED (np.ndarray without zeroing).
  implication: Any access to self.qubits[i] where i < (64-width) reads uninitialized memory

- timestamp: 2026-02-20
  checked: qint.__getitem__ implementation (qint_bitwise.pxi lines 704-728)
  found: Line 726 does `bit_list[-1] = self.qubits[item]` where item is the user's logical index (0=LSB). For x[0], this accesses self.qubits[0], which is UNINITIALIZED — not the LSB qubit.
  implication: The returned qbool contains a garbage qubit index at position 63

- timestamp: 2026-02-20
  checked: qint.branch() qubit access pattern (qint.pyx lines 587-590)
  found: branch() correctly accounts for right-aligned storage: self_offset = 64 - self.bits, then accesses self.qubits[self_offset + i]. For the qbool returned by __getitem__ (bits=1), this reads self.qubits[63] which contains the garbage value from step above.
  implication: emit_ry targets a garbage qubit index — the Ry gate goes to wrong/nonexistent qubit

- timestamp: 2026-02-20
  checked: Allocator initial state (qubit_allocator.c line 43)
  found: next_qubit starts at 0. First 3-qubit alloc gets qubits 0,1,2. np.ndarray(64) is uninitialized, so self.qubits[0] could be any value (often 0 from OS-zeroed pages, sometimes garbage).
  implication: If self.qubits[0] happens to be 0, the Ry targets qubit 0 which IS part of the qint — but it's the physical qubit at position 61 (LSB), NOT what the user intended if they said x[2]. For x[0] it might accidentally work sometimes, but x[2] would also target garbage.

- timestamp: 2026-02-20
  checked: The specific test scenario (test_multiple_indexed_branches)
  found: Test does x[0].branch(0.5) then x[2].branch(0.5). Both __getitem__ calls read self.qubits[0] and self.qubits[2] respectively — both indices are in the UNINITIALIZED zone (< 64-3=61). The Ry gates target whatever garbage values are there, having zero effect on the actual allocated qubits.
  implication: Explains why P(000) = 1.0 — no gates actually affect the 3 allocated qubits

## Resolution

root_cause: |
  **qint.__getitem__ does not account for right-aligned qubit storage.**

  In `src/quantum_language/qint_bitwise.pxi` line 726:
  ```python
  bit_list[-1] = self.qubits[item]
  ```
  This accesses `self.qubits[item]` using the raw logical index (0, 1, 2, etc.).
  But qubits are stored RIGHT-ALIGNED in the 64-element array at indices
  `[64-width]` through `[63]`. For a 3-qubit qint, the LSB (index 0) is at
  `self.qubits[61]`, not `self.qubits[0]`.

  The correct line should be:
  ```python
  bit_list[-1] = self.qubits[64 - self.bits + item]
  ```

  This matches the same right-aligned offset pattern used by `branch()` itself
  (qint.pyx line 588: `self_offset = 64 - self.bits`).

fix: |
  Changed `self.qubits[item]` to `self.qubits[64 - self.bits + item]` in
  `__getitem__` (qint_bitwise.pxi line 752). This applies the same right-aligned
  offset that `branch()` and other methods use. Fix was applied in commit f1526d2
  ("fix(76-05): correct __getitem__ right-aligned offset in qint_bitwise.pxi").

verification: |
  - test_indexed_branch_single_qubit: PASSED (x[0].branch(0.5) on 4-qubit qint)
  - test_multiple_indexed_branches: PASSED (x[0] and x[2] branch on 3-qubit qint, P=0.25 each)
  - Full test_branch_superposition.py: 31/31 PASSED (no regressions)
  - Current code at line 752: `bit_list[-1] = self.qubits[64 - self.bits + item]` -- confirmed correct

files_changed:
  - src/quantum_language/qint_bitwise.pxi (line 752, __getitem__ offset fix)
