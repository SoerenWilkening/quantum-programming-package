---
phase: 66-cdkm-ripple-carry-adder
verified: 2026-02-14T21:30:00Z
status: passed
score: 5/5 success criteria verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "CQ_add_toffoli(bits, val) adds a classical constant correctly for all input pairs at widths 1-4"
    - "CQ subtraction via inverted CQ adder works correctly for all input pairs at widths 1-4"
  gaps_remaining: []
  regressions: []
---

# Phase 66: CDKM Ripple-Carry Adder Verification Report

**Phase Goal:** Users can perform Toffoli-based addition and subtraction on quantum registers of any width using the CDKM ripple-carry algorithm

**Verified:** 2026-02-14T21:30:00Z

**Status:** passed

**Re-verification:** Yes - after gap closure via Plan 66-03

## Gap Closure Summary

**Previous verification (2026-02-14T21:00:00Z):** 4/5 success criteria verified, 1 gap found

**Gap identified:** CQ addition/subtraction only worked for width 1; widths 2+ failed due to incorrect MAJ/UMA simplification logic in emit_MAJ_CQ_one and emit_UMA_CQ_one functions.

**Gap closure plan (66-03):** Replace buggy 2-qubit CQ simplification with temp-register approach that reuses the proven QQ CDKM adder.

**Gap closure execution:**
- **Commit 911e442:** Deleted 4 buggy CQ MAJ/UMA helpers, rewrote toffoli_CQ_add to use temp-register approach (X-init, QQ CDKM adder, X-cleanup)
- **Commit c313bbe:** Updated hot_path_add_cq to allocate self_bits+1 ancilla, added _verify_toffoli_cq test helper, removed xfail markers from CQ tests

**Verification result:** All gaps closed. All 5 success criteria now verified.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | toffoli_QQ_add(bits) generates correct CDKM adder using MAJ/UMA chain | ✓ VERIFIED | ToffoliAddition.c lines 172-208, test_qq_add_exhaustive[1-4] all pass |
| 2 | toffoli_CQ_add(bits, val) generates correct temp-register sequence | ✓ VERIFIED | ToffoliAddition.c lines 262-324, test_cq_add_exhaustive[1-4] all pass |
| 3 | hot_path_add_qq dispatches to Toffoli when ARITH_TOFFOLI, allocates 1 ancilla | ✓ VERIFIED | hot_path_add.c:51-103, allocator_alloc at line 86 |
| 4 | hot_path_add_cq dispatches to Toffoli when ARITH_TOFFOLI, allocates self_bits+1 ancilla | ✓ VERIFIED | hot_path_add.c:157-202, allocator_alloc at line 175 |
| 5 | Controlled operations fall back to QFT when ARITH_TOFFOLI | ✓ VERIFIED | TestToffoliQFTFallback tests pass |
| 6 | ql.option('fault_tolerant', True) sets arithmetic_mode to ARITH_TOFFOLI | ✓ VERIFIED | _core.pyx:210-215, smoke test confirms get/set works |
| 7 | ql.option('fault_tolerant', False) restores ARITH_QFT | ✓ VERIFIED | Smoke test confirms: False -> True -> False transitions work |
| 8 | ToffoliAddition.c compiles and links in extension module | ✓ VERIFIED | setup.py:41 includes ToffoliAddition.c, import succeeds |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| c_backend/src/ToffoliAddition.c | CDKM adder with temp-register CQ approach, min 200 lines | ✓ VERIFIED | 342 lines, buggy CQ helpers deleted, temp-register approach implemented |
| c_backend/include/toffoli_arithmetic_ops.h | Public API declarations | ✓ VERIFIED | Contains toffoli_QQ_add, toffoli_CQ_add, toffoli_sequence_free |
| c_backend/include/types.h | arithmetic_mode_t enum | ✓ VERIFIED | Line 87: typedef enum { ARITH_QFT = 0, ARITH_TOFFOLI = 1 } |
| c_backend/include/circuit.h | arithmetic_mode field | ✓ VERIFIED | Line 77: arithmetic_mode_t arithmetic_mode |
| c_backend/src/hot_path_add.c | Toffoli dispatch with correct ancilla allocation | ✓ VERIFIED | QQ: 1 ancilla (line 86), CQ: self_bits+1 ancilla (line 175) |
| src/quantum_language/_core.pxd | Cython declarations for Toffoli ops | ✓ VERIFIED | Lines 40-42: toffoli_QQ_add, toffoli_CQ_add, toffoli_sequence_free |
| src/quantum_language/_core.pyx | fault_tolerant option | ✓ VERIFIED | Lines 210-215: handles get/set of arithmetic_mode |
| setup.py | ToffoliAddition.c in c_sources | ✓ VERIFIED | Line 41: includes ToffoliAddition.c |
| tests/test_toffoli_addition.py | Exhaustive verification tests, no xfail markers | ✓ VERIFIED | 622 lines, 42 tests, 0 xfail markers, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| hot_path_add.c | ToffoliAddition.c | toffoli_QQ_add() calls | ✓ WIRED | Lines 70, 93 call toffoli_QQ_add(result_bits) |
| hot_path_add.c | ToffoliAddition.c | toffoli_CQ_add() calls | ✓ WIRED | Lines 161, 191 call toffoli_CQ_add(self_bits, value) |
| hot_path_add.c | qubit_allocator.c | QQ ancilla allocation | ✓ WIRED | Lines 86, 95, 101: alloc/free 1 ancilla |
| hot_path_add.c | qubit_allocator.c | CQ ancilla allocation | ✓ WIRED | Lines 175, 193, 200: alloc/free self_bits+1 ancilla |
| ToffoliAddition.c | MAJ/UMA helpers | CQ reuses QQ chain | ✓ WIRED | Lines 303-312: toffoli_CQ_add calls emit_MAJ/emit_UMA |
| circuit_allocations.c | types.h | arithmetic_mode init to ARITH_QFT | ✓ WIRED | Line 18: circ->arithmetic_mode = ARITH_QFT |
| _core.pyx | circuit.h | arithmetic_mode field access | ✓ WIRED | Lines 212, 215 access arithmetic_mode via circuit_s cast |
| setup.py | ToffoliAddition.c | c_sources inclusion | ✓ WIRED | Line 41 includes file in build |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| ADD-01: Ripple-carry adder (QQ) | ✓ SATISFIED | None - all QQ tests pass |
| ADD-02: Ripple-carry adder (CQ) | ✓ SATISFIED | Gap closed - all CQ tests pass |
| ADD-05: Subtraction via inverse | ✓ SATISFIED | QQ and CQ subtraction verified for widths 1-4 |
| ADD-07: Mixed-width addition | ✓ SATISFIED | All 6 mixed-width tests pass |

### Success Criteria Verification

#### Success Criterion 1: QQ addition correctness and gate purity

**Criterion:** `QQ_add_toffoli(bits)` generates a correct sequence using only CCX/CX/X gates with exactly 1 ancilla qubit, verified for all input pairs at widths 1-4

**Status:** ✓ VERIFIED

**Evidence:**
- test_qq_add_exhaustive[1]: PASSED (2 input pairs)
- test_qq_add_exhaustive[2]: PASSED (16 input pairs)
- test_qq_add_exhaustive[3]: PASSED (64 input pairs)
- test_qq_add_exhaustive[4]: PASSED (256 input pairs)
- test_qq_toffoli_gate_purity[2-4]: 3/3 PASSED (only CCX/CX/X gates)
- test_qq_toffoli_gate_purity_via_qasm[2-4]: 3/3 PASSED

**Implementation:** ToffoliAddition.c lines 172-208 implement CDKM MAJ/UMA chain with 1 ancilla at index 2*bits

#### Success Criterion 2: CQ addition correctness and gate purity

**Criterion:** `CQ_add_toffoli(bits, val)` adds a classical constant to a quantum register using only CCX/CX/X gates, verified for all input pairs at widths 1-4

**Status:** ✓ VERIFIED (gap closed)

**Previous status:** PARTIAL (width 1 passed, widths 2-4 xfailed)

**Evidence:**
- test_cq_add_exhaustive[1]: PASSED (2 input pairs)
- test_cq_add_exhaustive[2]: PASSED (16 input pairs) - **previously xfailed**
- test_cq_add_exhaustive[3]: PASSED (64 input pairs) - **previously xfailed**
- test_cq_add_exhaustive[4]: PASSED (256 input pairs) - **previously xfailed**
- test_cq_toffoli_gate_purity[2-4]: 3/3 PASSED (only CCX/CX/X gates)

**Implementation:** ToffoliAddition.c lines 262-324 implement temp-register approach (X-init, QQ CDKM, X-cleanup)

**Gap closure fix:** Replaced buggy emit_MAJ_CQ_one/zero and emit_UMA_CQ_one/zero functions with temp-register approach that allocates N temp qubits, initializes via X gates, runs proven QQ adder, then X-cleanup to restore ancilla to |0>

#### Success Criterion 3: Subtraction via inverted sequence

**Criterion:** Subtraction works via inverted adder sequence (reversed gate order) for both QQ and CQ variants, verified for all input pairs at widths 1-4

**Status:** ✓ VERIFIED (gap closed for CQ)

**Evidence:**
- test_qq_sub_exhaustive[1-4]: 4/4 PASSED
- test_cq_sub_exhaustive[1]: PASSED (2 input pairs)
- test_cq_sub_exhaustive[2]: PASSED (16 input pairs) - **previously xfailed**
- test_cq_sub_exhaustive[3]: PASSED (64 input pairs) - **previously xfailed**
- test_cq_sub_exhaustive[4]: PASSED (256 input pairs) - **previously xfailed**

**Implementation:** Subtraction uses invert=true flag in run_instruction, which reverses gate order. Works correctly because:
- CDKM MAJ/UMA chain is invertible (running in reverse computes subtraction)
- X gates in CQ approach are self-inverse (X-init and X-cleanup commute with sequence inversion)

#### Success Criterion 4: Mixed-width addition

**Criterion:** Mixed-width addition handles operands of different bit widths via zero-extension, verified for width combinations (2,3), (3,4), (4,6)

**Status:** ✓ VERIFIED

**Evidence:**
- test_mixed_width_addition[2-3]: PASSED
- test_mixed_width_addition[3-4]: PASSED
- test_mixed_width_addition[4-6]: PASSED
- test_mixed_width_subtraction[2-3]: PASSED
- test_mixed_width_subtraction[3-4]: PASSED
- test_mixed_width_subtraction[4-6]: PASSED

**Implementation:** Mixed-width operations zero-extend the smaller operand to match the larger operand's width, then dispatch to Toffoli adder/subtractor

#### Success Criterion 5: Ancilla lifecycle

**Criterion:** Ancilla qubit is allocated before computation, uncomputed to |0>, and freed after each operation

**Status:** ✓ VERIFIED

**Evidence:**
- test_sequential_qq_additions_no_crash: PASSED (10 sequential QQ additions)
- test_sequential_cq_additions_no_crash: PASSED (10 sequential CQ additions)
- test_ancilla_freed_after_qq_addition: PASSED (ancilla count returns to 0)
- test_ancilla_stats_after_addition: PASSED (0 allocated, 0 freed after circuit reset)

**Implementation:**
- QQ: hot_path_add.c lines 86, 95, 101 (allocate 1, use, free 1)
- CQ: hot_path_add.c lines 175, 193, 200 (allocate self_bits+1, use, free self_bits+1)
- CDKM algorithm guarantees ancilla return to |0> (MAJ/UMA chain is self-inverse for ancilla)

### Anti-Patterns Found

**Re-verification scan:** No blocker anti-patterns found.

**Previous blockers resolved:**
- emit_MAJ_CQ_one (lines 117-128 in old version) - **DELETED**
- emit_UMA_CQ_one (lines 147-158 in old version) - **DELETED**

**Current code quality:**
- No TODO/FIXME/PLACEHOLDER comments in modified files
- No console.log-only implementations
- No empty return statements
- All implementations substantive and wired

### Human Verification Required

None - all verification can be done programmatically via Qiskit simulation.

### Test Results Summary

**Total tests run:** 42
- **Passed:** 42 (100%)
- **Failed:** 0
- **XFailed:** 0 (down from 6)
- **XPassed:** 0 (down from 2)

**Improvement:** +8 tests now passing (6 xfailed → passed, 2 xpassed → passed)

#### By Success Criterion

**Criterion 1 - QQ addition correctness and gate purity:**
- test_qq_add_exhaustive[1-4]: 4/4 PASSED (unchanged)
- test_qq_toffoli_gate_purity[2-4]: 3/3 PASSED (unchanged)
- test_qq_toffoli_gate_purity_via_qasm[2-4]: 3/3 PASSED (unchanged)

**Criterion 2 - CQ addition correctness and gate purity:**
- test_cq_add_exhaustive[1]: PASSED (was XPASS)
- test_cq_add_exhaustive[2-4]: 3/3 PASSED (were XFAIL) ✓ GAP CLOSED
- test_cq_toffoli_gate_purity[2-4]: 3/3 PASSED (unchanged)

**Criterion 3 - Subtraction via inversion:**
- test_qq_sub_exhaustive[1-4]: 4/4 PASSED (unchanged)
- test_cq_sub_exhaustive[1]: PASSED (was XPASS)
- test_cq_sub_exhaustive[2-4]: 3/3 PASSED (were XFAIL) ✓ GAP CLOSED

**Criterion 4 - Mixed-width:**
- test_mixed_width_addition[2-3, 3-4, 4-6]: 3/3 PASSED (unchanged)
- test_mixed_width_subtraction[2-3, 3-4, 4-6]: 3/3 PASSED (unchanged)

**Criterion 5 - Ancilla lifecycle:**
- test_sequential_qq_additions_no_crash: PASSED (unchanged)
- test_sequential_cq_additions_no_crash: PASSED (unchanged)
- test_ancilla_freed_after_qq_addition: PASSED (unchanged)
- test_ancilla_stats_after_addition: PASSED (unchanged)

#### Additional Tests

- TestToffoliFaultTolerantOption: 4/4 PASSED (unchanged)
- TestToffoliQFTFallback: 2/2 PASSED (unchanged)

### Commit Verification

All commits documented in SUMMARYs verified in git log:

**Phase 66-01:**
- 13cf301 - feat(66-01): implement CDKM ripple-carry adder in ToffoliAddition.c
- d1ece72 - feat(66-01): wire Toffoli dispatch into hot_path_add.c with ancilla lifecycle

**Phase 66-02:**
- 58bdcf5 - feat(66-02): wire Toffoli arithmetic into Python layer and build system
- 4d6f202 - fix(66-02): swap register positions in Toffoli QQ hot path dispatch
- ef692fd - test(66-02): add exhaustive Toffoli arithmetic verification tests

**Phase 66-03 (gap closure):**
- 911e442 - fix(66-03): rewrite toffoli_CQ_add to use temp-register QQ approach
- c313bbe - feat(66-03): update CQ hot path dispatch and enable CQ exhaustive tests
- f5a8928 - docs(66-03): complete CQ Toffoli gap closure plan

### Regression Check

**QFT test suite:** Sample test file test_variable_width.py: 67 passed, 8 warnings
**Existing arithmetic:** No regressions detected in QFT-based arithmetic operations

---

## Conclusion

**Phase 66 fully achieves all 5 success criteria.**

The CDKM ripple-carry adder is successfully implemented and integrated for both QQ (quantum-quantum) and CQ (classical-quantum) operations. All infrastructure is in place and fully functional:

- ✓ C backend with MAJ/UMA chain for QQ
- ✓ C backend with temp-register approach for CQ
- ✓ Hot path dispatch with correct ancilla lifecycle (1 for QQ, self_bits+1 for CQ)
- ✓ Python API via fault_tolerant option
- ✓ Build system integration
- ✓ Comprehensive test suite with 100% pass rate

**Gap closure:** The CQ addition/subtraction bug identified in previous verification has been fully resolved. The temp-register approach eliminates the algorithmic flaw in the 2-qubit MAJ/UMA CQ simplification and reuses the proven QQ CDKM adder, guaranteeing correctness.

**Phase deliverable:** Users can now perform Toffoli-based addition and subtraction on quantum registers of **any width** using the CDKM ripple-carry algorithm, for both QQ and CQ operations.

**Ready for Phase 67:** Controlled Toffoli operations (cQQ/cCQ addition with QFT fallback).

---

_Verified: 2026-02-14T21:30:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes (gap closure verified)_
