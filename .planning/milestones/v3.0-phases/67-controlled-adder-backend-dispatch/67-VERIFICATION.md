---
phase: 67-controlled-adder-backend-dispatch
verified: 2026-02-14T23:45:00Z
status: passed
score: 5/5
re_verification: false
---

# Phase 67: Controlled Adder & Backend Dispatch Verification Report

**Phase Goal:** Users can switch all addition/subtraction to Toffoli-based circuits via `ql.option('fault_tolerant', True)` with controlled variants for quantum conditionals

**Verified:** 2026-02-14T23:45:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                      | Status     | Evidence                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | -------------------------------------------------------------------------------------------------- |
| 1   | `cQQ_add_toffoli(bits)` performs addition conditioned on control qubit using CCX/CX/X gates, verified for widths 1-4                      | ✓ VERIFIED | 14 tests pass (control=1 and control=0), gate purity verified                                     |
| 2   | `cCQ_add_toffoli(bits, val)` performs classical-quantum addition conditioned on control qubit, verified for widths 1-4                    | ✓ VERIFIED | 14 tests pass (control=1 and control=0), gate purity verified                                     |
| 3   | `ql.option('fault_tolerant', True)` causes `a += b` to emit CCX/CX/X gates; `False` restores QFT with CP/H gates                          | ✓ VERIFIED | Default mode test: no H/CP gates. QFT opt-in test: H/rotation gates present                        |
| 4   | Hot-path C dispatch checks fault_tolerant flag and routes to correct sequence generator without qubit layout collisions                   | ✓ VERIFIED | hot_path_add.c lines 51-149 (QQ) and 202-284 (CQ) handle both modes, all tests pass               |
| 5   | Toffoli-based arithmetic is default; QFT available via explicit `ql.option('fault_tolerant', False)`                                      | ✓ VERIFIED | init_circuit() sets ARITH_TOFFOLI (circuit_allocations.c:18), default mode test confirms           |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                                     | Expected                                                                          | Status     | Details                                                          |
| -------------------------------------------- | --------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------- |
| `c_backend/src/ToffoliAddition.c`            | toffoli_cQQ_add, toffoli_cCQ_add, emit_cMAJ, emit_cUMA, large_control cleanup   | ✓ VERIFIED | 8 refs to toffoli_cQQ_add, 2 to toffoli_cCQ_add, 5 emit_cMAJ    |
| `c_backend/include/toffoli_arithmetic_ops.h` | Public declarations for cQQ_add and cCQ_add                                       | ✓ VERIFIED | Lines 82, 110 declare both functions                             |
| `c_backend/src/hot_path_add.c`               | Controlled Toffoli dispatch in QQ and CQ paths, no QFT fallback                   | ✓ VERIFIED | Lines 55-96 (cQQ), 205-245 (cCQ), 0 "fall back to QFT" comments |
| `src/quantum_language/_core.pxd`             | Cython declarations for toffoli_cQQ_add and toffoli_cCQ_add                       | ✓ VERIFIED | Lines 42-43 declare both functions                               |
| `tests/test_toffoli_addition.py`             | Exhaustive controlled tests for widths 1-4, default mode tests                    | ✓ VERIFIED | 28 new tests, TestDefaultModeToffoli class, 72 total pass        |
| `c_backend/src/circuit_allocations.c`        | Default arithmetic_mode = ARITH_TOFFOLI                                           | ✓ VERIFIED | Line 18: `circ->arithmetic_mode = ARITH_TOFFOLI;`                |

### Key Link Verification

| From                                                | To                                  | Via                                                 | Status     | Details                                                      |
| --------------------------------------------------- | ----------------------------------- | --------------------------------------------------- | ---------- | ------------------------------------------------------------ |
| ToffoliAddition.c:toffoli_cQQ_add                   | emit_cMAJ                           | MAJ/UMA chain with external control                 | ✓ WIRED    | emit_cMAJ called in forward sweep (controlled path)          |
| ToffoliAddition.c:toffoli_cCQ_add                   | toffoli_cQQ_add                     | Controlled CQ uses controlled QQ core for CDKM      | ✓ WIRED    | cCQ implementation uses cQQ pattern (CX-init + cQQ + cleanup)|
| ToffoliAddition.c:toffoli_sequence_free             | gate_t.large_control                | Iterates gates and frees large_control for MCX      | ✓ WIRED    | 3 refs to large_control in free function                    |
| hot_path_add.c:hot_path_add_qq                      | ToffoliAddition.c:toffoli_cQQ_add   | Controlled Toffoli dispatch                         | ✓ WIRED    | Lines 65, 89 call toffoli_cQQ_add                            |
| hot_path_add.c:hot_path_add_cq                      | ToffoliAddition.c:toffoli_cCQ_add   | Controlled Toffoli dispatch                         | ✓ WIRED    | Lines 212, 237 call toffoli_cCQ_add                          |
| test_toffoli_addition.py                            | _core.pyx:option('fault_tolerant')  | Tests verify default is Toffoli and QFT opt-in works| ✓ WIRED    | fault_tolerant=False appears 10 times in test file           |
| circuit_allocations.c:init_circuit                  | types.h:ARITH_TOFFOLI               | Default mode assignment                             | ✓ WIRED    | Line 18 sets arithmetic_mode to ARITH_TOFFOLI                |

### Requirements Coverage

Phase 67 maps to requirements ADD-03, ADD-04, DSP-01, DSP-02, DSP-03 from ROADMAP.md.

All requirements satisfied through the 5 verified truths above:
- ADD-03 (controlled QQ addition): Truth 1
- ADD-04 (controlled CQ addition): Truth 2
- DSP-01 (backend dispatch): Truth 4
- DSP-02 (mode switching): Truth 3
- DSP-03 (default mode): Truth 5

**Status:** ✓ ALL SATISFIED

### Anti-Patterns Found

No blocking anti-patterns detected.

**Checked files:**
- c_backend/src/ToffoliAddition.c
- c_backend/src/hot_path_add.c
- c_backend/src/circuit_allocations.c
- tests/test_toffoli_addition.py

**Findings:**
- 0 TODO/FIXME/PLACEHOLDER comments
- 0 stub implementations (all `return NULL` are proper error handling for malloc failures and bounds checks)
- 0 orphaned artifacts (all functions called and wired)
- 0 gate type leaks (default mode verified to emit only CCX/CX/X gates)

### Human Verification Required

None. All success criteria are programmatically verifiable and have been verified through:
- Exhaustive testing (widths 1-4, all input pairs, both control=0 and control=1)
- Gate purity checks (QASM string parsing confirms gate types)
- Regression testing (72 Toffoli tests + 165 hardcoded sequence tests pass)
- Mode switching verification (default mode and QFT opt-in tests)

### Test Results Summary

**Total tests run:** 237 tests
- test_toffoli_addition.py: 72 passed (14 new controlled tests + existing)
- test_hardcoded_sequences.py: 165 passed (QFT opt-in added)
- Warnings: expected (qint width truncation warnings)
- Failures: 0
- Errors: 0

**Controlled Toffoli Tests:**
- TestControlledToffoliQQAddition: 14 tests (add control-active/inactive widths 1-4, sub widths 1-3, gate purity)
- TestControlledToffoliCQAddition: 14 tests (add control-active/inactive widths 1-4, sub widths 1-3, gate purity)
- TestDefaultModeToffoli: 2 tests (default is Toffoli, QFT opt-in)

**Gate Type Verification:**
```
Default mode (Toffoli):
  Has H gates: False
  Has CP gates: False
  Has CCX gates: True
  Has CX gates: True

QFT opt-in mode:
  Has H gates: True
  Has rotation gates: True
```

**Controlled Addition Verification:**
```
Controlled addition (default Toffoli):
  Has H gates: False
  Has CP gates: False
  Has CCX gates: True
  Has CX gates: True
```

---

_Verified: 2026-02-14T23:45:00Z_
_Verifier: Claude (gsd-verifier)_
