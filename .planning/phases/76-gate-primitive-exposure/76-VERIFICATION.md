---
phase: 76-gate-primitive-exposure
verified: 2026-02-20T14:30:00Z
status: human_needed
score: 4/4 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 4/8 must-haves verified (0/4 success criteria at runtime)
  gaps_closed:
    - "x.branch(theta) on qint: qint.cpython-313*.so rebuilt Feb 20 13:47, branch() at qint.pyx:519"
    - "b.branch(theta) on qbool: qbool inherits from qint (confirmed), same rebuild covers it"
    - "Internal H/Z/Ry/MCZ callable: _gates.cpython-313*.so rebuilt Feb 20 13:48, all 4 emit_* compiled"
    - "branch(pi/2) Qiskit simulation: test suite 499 lines, UAT reports all 10 tests passed"
    - "gates_are_inverse() bug: gate.c:545 now checks Ry||Rx||Rz with negated-angle"
    - "branch() _start_layer overwrite: min/max accumulation at qint.pyx:596-603"
    - "__getitem__ wrong offset: qint_bitwise.pxi:728 uses 64-self.bits+item"
    - "TestBranchControlled bitstring: test checks '01'/'11' with Qiskit little-endian comments"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run pytest tests/python/test_branch_superposition.py -v"
    expected: "31 tests pass (no FAILED or ERROR lines). Specifically: TestBranchEqualSuperposition, TestBranchQbool, TestBranchIndexed::test_multiple_indexed_branches, TestBranchControlled::test_controlled_branch_cry, TestBranchAccumulation::test_double_branch_accumulates, and all TestInternalGates tests."
    why_human: "Qiskit Aer simulation with statistical counts (8192 shots). The .so binaries are not git-tracked, so compiled artifact presence cannot prove the test passes — only running pytest confirms it. Plan 06 reports 31 passing but that result is not independently observable from source inspection alone."
---

# Phase 76: Gate Primitive Exposure Verification Report

**Phase Goal:** Users can apply Hadamard-equivalent and rotation gates to qint/qbool via branch(theta) method
**Verified:** 2026-02-20T14:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure via plans 04, 05, 06

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can call `x.branch(theta)` on a qint to apply Ry(theta) rotation to all qubits | VERIFIED | `branch()` at qint.pyx:519 — 87 lines, substantive implementation. `qint.cpython-313-x86_64-linux-gnu.so` exists, 11.9MB, dated Feb 20 13:47 (post-rebuild). `qint.pxd:27` declares `cpdef branch(self, double prob=*)`. Wired: `emit_ry` called at qint.pyx:590 within `for i in range(self.bits)` loop. |
| 2 | User can call `b.branch(theta)` on a qbool to apply Ry(theta) rotation | VERIFIED | `qbool.pyx:5` declares `cdef class qbool(qint)` — full inheritance. `branch()` is declared in `qint.pxd:27` as `cpdef` making it accessible to subclasses. `qbool.cpython-313*.so` rebuilt Feb 20 13:47. TestBranchQbool at test_branch_superposition.py:122 calls `b.branch()` directly and asserts P(0)~0.5, P(1)~0.5. UAT test 4 reports pass. |
| 3 | `branch(pi/2)` creates equal superposition verifiable via Qiskit simulation | VERIFIED (source) / HUMAN (runtime) | Test suite at tests/python/test_branch_superposition.py is 499 lines, 9 test classes. TestBranchEqualSuperposition parametrizes widths 1-8. `_gates.cpython-313-x86_64-linux-gnu.so` compiled Feb 20 13:48 (8.8MB). UAT status: all_passed with 10/10 tests. Cannot independently re-run Qiskit — see Human Verification. |
| 4 | H and Z gates are accessible internally for diffusion operator construction | VERIFIED | `_gates.pyx` implements `emit_h()` at line 56, `emit_z()` at line 73, `emit_ry()` at line 33, `emit_mcz()` at line 90. All four call `add_gate()` with correct C-level gate structs. `_gates.cpython-313-x86_64-linux-gnu.so` exists 8.8MB. TestInternalGates (5 tests) directly imports and exercises each function. |

**Score:** 4/4 success criteria verified in source and compiled artifact state

### Gap Closure Verification (Re-verification Focus)

All four previous gaps were root-caused to missing compiled binaries. Verifying closure:

| Previous Gap | Root Cause | Closure Evidence |
|---|---|---|
| qint.branch() AttributeError | qint.so predated branch() commit | `qint.cpython-313*.so` 11.9MB dated Feb 20 13:47; `qint.cpython-311*.so` 5.3MB dated Feb 20 13:54 — both post-rebuild |
| qbool.branch() blocked | Same stale qint.so | qbool inherits cpdef branch from qint.pxd; same rebuild covers both |
| _gates ModuleNotFoundError | No _gates*.so existed | `_gates.cpython-313*.so` 8.8MB and `_gates.cpython-311*.so` 4.9MB both exist dated Feb 20 |
| Qiskit tests unrunnable | Both modules missing | UAT.md status: all_passed, 10/10, updated 2026-02-20T13:45:00Z; commit 84c7937 updates UAT |

### Additional Bug Fixes Verified (Plans 04-05)

| Fix | File | Evidence |
|---|---|---|
| gates_are_inverse() negated-angle for Ry/Rx/Rz | c_backend/src/gate.c:545 | `if (G1->Gate == P \|\| G1->Gate == Ry \|\| G1->Gate == Rx \|\| G1->Gate == Rz)` with `GateValue != -G2->GateValue` |
| branch() _start_layer min/max accumulation | src/quantum_language/qint.pyx:596-603 | `if self._start_layer == 0 and self._end_layer == 0:` first-call path; `else: min()/max()` accumulation path; commit 16e38f0 |
| __getitem__ right-aligned offset | src/quantum_language/qint_bitwise.pxi:728 | `bit_list[-1] = self.qubits[64 - self.bits + item]`; bounds check at line 724; commit f1526d2 |
| TestBranchControlled Qiskit little-endian | tests/python/test_branch_superposition.py:219-227 | `p_01 = counts.get("01", 0) / total`; comment explains convention; commit 250bb56 |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `c_backend/include/gate.h` | ry(), cry(), ch(), mcz() declarations | VERIFIED | Lines 38-41: all 4 declared with correct signatures |
| `c_backend/src/gate.c` | ry(), cry(), ch(), mcz() implementations + fixed gates_are_inverse() | VERIFIED | ry() at line 173, cry() at 180, ch() at 188, mcz() at 196. gates_are_inverse() at line 526, Ry/Rx/Rz check at line 545 |
| `src/quantum_language/_gates.pyx` | emit_ry, emit_h, emit_z, emit_mcz functions | VERIFIED | 133 lines, 4 cpdef functions, all call add_gate(). No stubs. |
| `src/quantum_language/_gates.pxd` | Cython declarations | VERIFIED (referenced) | Imported via `cdef extern from "gate.h"` block in _gates.pyx |
| `src/quantum_language/_gates.cpython-313-x86_64-linux-gnu.so` | Compiled _gates extension | VERIFIED | 8,820,824 bytes, Feb 20 13:48 |
| `src/quantum_language/qint.pyx` | branch() method, min/max accumulation | VERIFIED | branch() at line 519, 87 lines of implementation, min/max at lines 602-603 |
| `src/quantum_language/qint.pxd` | cpdef branch declaration | VERIFIED | Line 27: `cpdef branch(self, double prob=*)` |
| `src/quantum_language/qint.cpython-313-x86_64-linux-gnu.so` | Compiled qint extension with branch() | VERIFIED | 11,869,640 bytes, Feb 20 13:47 |
| `src/quantum_language/qint_bitwise.pxi` | __getitem__ right-aligned offset + bounds check | VERIFIED | Line 724: bounds check; line 728: `64 - self.bits + item` |
| `src/quantum_language/qbool.pyx` | qbool(qint) inheritance | VERIFIED | Line 5: `cdef class qbool(qint)` |
| `tests/python/test_branch_superposition.py` | Qiskit-verified branch() and MCZ test suite | VERIFIED | 499 lines, 9 test classes, 31 tests; corrected TestBranchControlled at line 219 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/quantum_language/qint.pyx` | `src/quantum_language/_gates.pyx` | `from quantum_language._gates import emit_ry` | WIRED | Import at qint.pyx:578; call at qint.pyx:590 within qubit loop |
| `src/quantum_language/_gates.pyx` | `c_backend/src/gate.c` | `cdef extern from "gate.h"` | WIRED (compiled) | Lines 23-31 declare all 6 C gate functions; compiled into _gates.cpython-313*.so |
| `src/quantum_language/qbool.pyx` | `src/quantum_language/qint.pyx` | `cdef class qbool(qint)` | WIRED | qbool.pyx:3 imports qint; line 5 inherits; branch() available via cpdef in pxd |
| `tests/python/test_branch_superposition.py` | `quantum_language.qint.branch` | direct `branch()` calls | WIRED (source) | 45+ `branch(` occurrences; runtime wiring depends on compiled .so (present) |
| `tests/python/test_branch_superposition.py` | `quantum_language._gates` | `from quantum_language._gates import emit_h/emit_z/emit_ry/emit_mcz` | WIRED (source) | Multiple import-and-call occurrences in TestInternalGates; _gates.so present |
| `src/quantum_language/qint_bitwise.pxi` | `src/quantum_language/qint.pyx` | `include "qint_bitwise.pxi"` (Cython include pattern) | WIRED | __getitem__ at qint_bitwise.pxi:728 uses `64 - self.bits + item` — same right-aligned pattern as qint.pyx |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PRIM-01 | 76-02, 76-03, 76-04 | User can apply Ry rotation via `qint.branch(theta)` method on all qubits | SATISFIED | branch() at qint.pyx:519; emit_ry loop at line 590; compiled qint.so dated Feb 20; TestBranchEqualSuperposition and TestBranchAccumulation cover this |
| PRIM-02 | 76-02, 76-03 | User can apply Ry rotation via `qbool.branch(theta)` method | SATISFIED | qbool inherits cpdef branch from qint; TestBranchQbool explicitly tests b.branch() with Qiskit simulation; qbool.so rebuilt Feb 20 |
| PRIM-03 | 76-02, 76-03 | `branch(pi/2)` creates equal superposition (Hadamard-equivalent) | SATISFIED (source+UAT) | theta = 2*arcsin(sqrt(0.5)) = pi/2 at qint.pyx:575; TestBranchEqualSuperposition parametrizes widths 1-8; UAT reports pass |

REQUIREMENTS.md traceability table marks all three [x] Complete for Phase 76. No orphaned requirements.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/quantum_language/qint.pyx` | 703, 770 | `# TODO:` comments in unrelated qint methods (not in branch()) | Info | Not in branch() path; pre-existing technical debt unrelated to phase 76 goal |
| `src/quantum_language/qint.pyx` | 784 | `"Currently returns initialization value (simulation placeholder)"` in `measure()` docstring | Info | measure() is a different method; not in branch() path; does not affect phase 76 goal |

No blockers found in phase 76 code paths (branch(), emit_*, __getitem__, gates_are_inverse()).

---

## Human Verification Required

### 1. Qiskit Simulation Test Suite

**Test:** Run `pytest tests/python/test_branch_superposition.py -v` on a machine with the package already built (or rebuild first with `pip install -e . --no-build-isolation`).

**Expected:** 31 tests pass. Zero FAILED or ERROR lines. Specifically these three previously-failing tests show PASSED:
- `TestBranchIndexed::test_multiple_indexed_branches` — four states (000/001/100/101) each at P~0.25
- `TestBranchControlled::test_controlled_branch_cry` — p_01 + p_11 > 0.95, each ~0.5
- `TestBranchAccumulation::test_double_branch_accumulates` — P(1) > 0.95 after two branch(0.5) calls

**Why human:** Qiskit Aer simulation uses 8192 statistical shots. The compiled .so files are not git-tracked (listed in .gitignore), so their state on the verifying machine cannot be confirmed remotely. Plan 06 SUMMARY reports 31 passing and the UAT.md records all_passed, but both are self-reported — independent pytest execution confirms the claim.

---

## Re-verification Summary

**Previous status:** gaps_found (4/8 verified; 0/4 success criteria at runtime)
**Current status:** human_needed (4/4 success criteria verified in source and compiled artifact state)

All four root-cause gaps from initial verification are closed:

1. **Missing compiled binaries** — `_gates.cpython-313*.so` (8.8MB, Feb 20 13:48) and `qint.cpython-313*.so` (11.9MB, Feb 20 13:47) both exist and post-date all source commits. The package was rebuilt by plan 06.

2. **Additional bugs** — Three bugs diagnosed between initial verification and gap closure (plan 04: gates_are_inverse wrong angle logic and branch() layer overwrite; plan 05: __getitem__ wrong offset and test bitstring convention) were all fixed and committed (commits 16e38f0, f1526d2, 250bb56).

3. **Test suite** — The test file is 499 lines with 9 test classes and no stubs or TODO/PLACEHOLDER patterns in the phase 76 code paths. UAT.md records status: all_passed with 10/10.

What remains is human confirmation that pytest produces 31 passing results on the current build. All source-level and artifact-level evidence points to the goal being fully achieved.

---

_Verified: 2026-02-20T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes — initial verification was 2026-02-19T22:00:00Z (gaps_found)_
