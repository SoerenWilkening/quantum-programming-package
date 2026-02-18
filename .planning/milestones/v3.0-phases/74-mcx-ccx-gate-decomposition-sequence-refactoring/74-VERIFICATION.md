---
phase: 74-mcx-ccx-gate-decomposition-sequence-refactoring
verified: 2026-02-17T21:00:00Z
status: gaps_found
score: 16/17 must-haves verified
gaps:
  - truth: "MCX gate purity tests actually verify the circuit built by each test"
    status: partial
    reason: "_get_mcx_count() in test_mcx_decomposition.py calls ql.circuit().gate_counts which creates a NEW empty circuit (all-zero counts), making all 23 purity assertions trivially pass regardless of actual output. The 74-05 summary explicitly flagged this as unfixed. test_decomposed_sequences.py correctly stores a circuit reference and genuinely tests purity."
    artifacts:
      - path: "tests/python/test_mcx_decomposition.py"
        issue: "Lines 22-25: _get_mcx_count() calls ql.circuit().gate_counts (fresh empty circuit), so assert _get_mcx_count() == 0 is always True. 23 tests appear to pass but verify nothing about actual MCX gate counts."
    missing:
      - "Fix _get_mcx_count() to store the circuit reference before building operations: pattern should be c = ql.circuit(); ... build operation ...; gc = c.gate_counts; return gc.get('other', 0)"
      - "Or inline the assertion in each test using the stored circuit reference (matching test_decomposed_sequences.py pattern)"
---

# Phase 74: MCX/CCX Gate Decomposition and Sequence Refactoring Verification Report

**Phase Goal:** All MCX gates (3+ controls) are automatically decomposed into CCX/CX/X gates, with an opt-in `toffoli_decompose` option to further decompose CCX into Clifford+T. Sequences containing CCX gates get dedicated fast-path functions. Large C files are refactored for maintainability.

**Verified:** 2026-02-17T21:00:00Z
**Status:** gaps_found
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | ToffoliAddition.c replaced by 3 focused modules (CDKM/CLA/Helpers) | VERIFIED | File deleted; CDKM 812L, CLA 1033L, Helpers 151L all exist |
| 2 | hot_path_add.c slimmed with Toffoli dispatch extracted | VERIFIED | hot_path_add_toffoli.c exists at 427 lines; summary says hot_path_add.c went from 530 to 145 lines |
| 3 | T_GATE and TDG_GATE integrated as valid gate enum values | VERIFIED | types.h enum confirmed; t_gate/tdg_gate in gate.c; QASM outputs "t"/"tdg"; counting in circuit_stats.c |
| 4 | ql.option('toffoli_decompose') API works | VERIFIED | _core.pyx lines 234-239 implement get/set; toffoli_decompose field in circuit_t confirmed |
| 5 | gate_counts exposes T_gates/Tdg_gates, not MCX | VERIFIED | circuit_stats.h has t_gates/tdg_gates (no mcx_gates); _core.pyx gate_counts dict has T_gates/Tdg_gates keys |
| 6 | T-count is exact (actual T+Tdg) when decompose on, estimated (7*CCX) otherwise | VERIFIED | Dual formula in circuit_stats.c confirmed |
| 7 | T and Tdg recognized as inverses | VERIFIED | gates_are_inverse() special case for T_GATE/TDG_GATE at gate.c lines 485-487 |
| 8 | MCX emission points replaced with AND-ancilla CCX decomposition in CDKM | VERIFIED | 44 occurrences of and_anc in ToffoliAdditionCDKM.c; emit_cMAJ_decomposed/emit_cUMA_decomposed patterns |
| 9 | MCX emission points replaced in CLA adder | VERIFIED | 15 occurrences of and_anc in ToffoliAdditionCLA.c |
| 10 | MCX emission points replaced in ToffoliMultiplication.c | VERIFIED | 54 occurrences of and_anc in ToffoliMultiplication.c; emit_ccx_or_clifford_t multiplexer present |
| 11 | MCX emission points replaced in IntegerComparison.c | VERIFIED | 11 occurrences of and_anc in IntegerComparison.c |
| 12 | MCX gate purity test suite exists with meaningful assertions | PARTIAL | test_mcx_decomposition.py (315 lines, 23 tests) exists BUT all tests are trivially passing -- _get_mcx_count() creates a fresh empty circuit so assertions always pass |
| 13 | CCX->Clifford+T decomposition helper implemented | VERIFIED | emit_ccx_clifford_t() and emit_ccx_clifford_t_seq() in gate.c (546, 625); declared in gate.h (61, 76) |
| 14 | CCX->Clifford+T integrated into inline multiplication paths | VERIFIED | emit_ccx_or_clifford_t multiplexer in ToffoliMultiplication.c reads circ->toffoli_decompose |
| 15 | Hardcoded MCX-decomposed cQQ sequences exist for widths 1-8 | VERIFIED | 9 files (toffoli_decomp_seq_1.c through _8.c + dispatch); zero 3+ control gates in any file |
| 16 | Decomposed sequences dispatched from toffoli_cQQ_add() | VERIFIED | ToffoliAdditionCDKM.c line 630 calls get_hardcoded_toffoli_decomp_cQQ_add(bits) |
| 17 | Correct qubit layout for AND-ancilla in hot_path_add_toffoli.c | VERIFIED | Lines 195-197: carry at [2*bits], ext_ctrl at [2*bits+1], AND-ancilla at [2*bits+2]; allocates 2 ancilla |

**Score:** 16/17 truths verified (1 partial)

### Required Artifacts

| Artifact | Min Lines | Status | Details |
|----------|-----------|--------|---------|
| `c_backend/src/ToffoliAdditionCDKM.c` | 500 | VERIFIED | 812 lines; contains and_anc (44x) |
| `c_backend/src/ToffoliAdditionCLA.c` | 600 | VERIFIED | 1033 lines; contains and_anc (15x) |
| `c_backend/src/ToffoliAdditionHelpers.c` | 50 | VERIFIED | 151 lines |
| `c_backend/include/toffoli_addition_internal.h` | - | VERIFIED | 60 lines; contains bk_merge_t |
| `c_backend/src/hot_path_add_toffoli.c` | 100 | VERIFIED | 427 lines |
| `c_backend/include/types.h` | - | VERIFIED | T_GATE, TDG_GATE in Standardgate_t enum |
| `c_backend/src/gate.c` | - | VERIFIED | t_gate(), tdg_gate(), emit_ccx_clifford_t(), emit_ccx_clifford_t_seq() |
| `c_backend/src/circuit_stats.c` | - | VERIFIED | T_GATE/TDG_GATE counted; dual t_count formula |
| `c_backend/src/circuit_output.c` | - | VERIFIED | QASM "t"/"tdg" at lines 380-384 |
| `c_backend/include/circuit.h` | - | VERIFIED | toffoli_decompose field at line 83 |
| `src/quantum_language/_core.pyx` | - | VERIFIED | toffoli_decompose option; T_gates/Tdg_gates in gate_counts |
| `c_backend/include/gate.h` | - | VERIFIED | emit_ccx_clifford_t declared (lines 61, 76) |
| `c_backend/src/ToffoliMultiplication.c` | - | VERIFIED | emit_ccx_or_clifford_t multiplexer; and_anc (54x) |
| `c_backend/src/IntegerComparison.c` | - | VERIFIED | and_anc (11x) |
| `scripts/generate_toffoli_decomp_seq.py` | 200 | VERIFIED | 613 lines |
| `c_backend/src/sequences/toffoli_decomp_seq_dispatch.c` | - | VERIFIED | 90 lines; get_hardcoded_toffoli_decomp_cQQ_add() dispatch |
| `c_backend/include/toffoli_sequences.h` | - | VERIFIED | get_hardcoded_toffoli_decomp_cQQ_add declared (line 93) |
| `tests/python/test_mcx_decomposition.py` | 80 | STUB | 315 lines, 23 test functions, but ALL trivially passing (broken _get_mcx_count helper) |
| `tests/python/test_clifford_t_decomposition.py` | 80 | VERIFIED | 387 lines, 19 tests |
| `tests/python/test_decomposed_sequences.py` | 60 | VERIFIED | 277 lines, 13 parametrized test functions (~94 parametrized cases); correct circuit reference pattern |
| `c_backend/src/sequences/toffoli_decomp_seq_1.c` through `_8.c` | - | VERIFIED | 8 files exist; zero NumControls >= 3 in any file; large_control = NULL everywhere |
| `c_backend/src/ToffoliAddition.c` | DELETED | VERIFIED | File does not exist |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ToffoliAdditionCDKM.c` | `toffoli_addition_internal.h` | `#include` | VERIFIED | Line 26: `#include "toffoli_addition_internal.h"` |
| `ToffoliAdditionCLA.c` | `toffoli_addition_internal.h` | `#include` | VERIFIED | Line 22: `#include "toffoli_addition_internal.h"` |
| `setup.py` | `ToffoliAdditionCDKM.c` | source file list | VERIFIED | Line 43: ToffoliAdditionCDKM referenced |
| `setup.py` | `ToffoliAddition.c` (removed) | source file list | VERIFIED | No match for ToffoliAddition.c in setup.py |
| `circuit_stats.c` | `types.h` | switch on g->Gate | VERIFIED | `case T_GATE:` at line 63 |
| `circuit_output.c` | `types.h` | switch on g->Gate | VERIFIED | `case T_GATE:` at lines 155, 253, 380 |
| `_core.pyx` | `circuit.h` | circuit_t field access | VERIFIED | `.toffoli_decompose` accessed at lines 236, 239 |
| `ToffoliAdditionCDKM.c` | `toffoli_decomp_seq_dispatch.c` | get_hardcoded_toffoli_decomp_cQQ_add | VERIFIED | Line 630 calls function |
| `toffoli_decomp_seq_dispatch.c` | `toffoli_decomp_seq_1.c` | dispatch by width | VERIFIED | Lines 57-90 in dispatch; function toffoli_decomp_cQQ_add_seq_1 pattern |
| `setup.py` | `toffoli_decomp_seq_1.c` | build source list | VERIFIED | Lines 54-57: loop adds toffoli_decomp_seq_{1..8}.c |
| `ToffoliMultiplication.c` | `gate.c` | emit_ccx_clifford_t call | VERIFIED | Line 85: `emit_ccx_clifford_t(circ, target, ctrl1, ctrl2)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status |
|-------------|------------|-------------|--------|
| INF-03 | Plans 01, 03, 05 | Large C file refactoring and sequence infrastructure | SATISFIED |
| INF-04 | Plans 02, 04 | Gate infrastructure (T/Tdg), toffoli_decompose option, CCX->Clifford+T | SATISFIED |

### Anti-Patterns Found

| File | Lines | Pattern | Severity | Impact |
|------|-------|---------|----------|--------|
| `tests/python/test_mcx_decomposition.py` | 22-25 | `gc = ql.circuit().gate_counts` in `_get_mcx_count()` creates a fresh empty circuit; `other == 0` is always True | WARNING | All 23 MCX purity tests pass vacuously; do not actually verify that MCX gates are absent from operations. The 74-05 summary explicitly identified this as "pre-existing trivially-passing tests" left unfixed. test_decomposed_sequences.py (Plan 05) tests the same operations correctly. |

### Human Verification Required

#### 1. Build and Run Full Test Suite

**Test:** `pip3 install -e . && python3 -m pytest tests/python/ -v --timeout=120`
**Expected:** All tests pass with zero regressions (650+ total). Specifically test_decomposed_sequences.py (94 parametrized cases) and test_clifford_t_decomposition.py (19 tests) should pass.
**Why human:** Build requires compilation; timeout constraints prevent automated execution in this verification context. The 74-01 summary notes build environment memory constraints required targeted test runs rather than full suite.

#### 2. Verify MCX Absence at Runtime (Controlled Addition)

**Test:** `python3 -c "import quantum_language as ql; c = ql.circuit(); ql.option('fault_tolerant', True); a = ql.qint(1, width=3); b = ql.qint(1, width=3); ctrl = ql.qbool(True);
from contextlib import contextmanager; [ctrl.__enter__(), a.__iadd__(b), ctrl.__exit__(None, None, None)]; gc = c.gate_counts; print('other (MCX):', gc.get('other', 0)); assert gc.get('other', 0) == 0"`
**Expected:** `other (MCX): 0` -- no MCX gates in controlled addition output.
**Why human:** test_mcx_decomposition.py does not actually verify this; the C code audit shows and_anc patterns are present but runtime confirmation is needed.

#### 3. Verify CCX->Clifford+T Decomposes to T/Tdg Gates

**Test:** `python3 -c "import quantum_language as ql; c = ql.circuit(); ql.option('fault_tolerant', True); ql.option('toffoli_decompose', True); a = ql.qint(2, 3); b = ql.qint(3, 3); r = a * b; gc = c.gate_counts; print(gc); assert gc.get('T_gates', 0) > 0"`
**Expected:** T_gates > 0 and Tdg_gates > 0 with CCX = 0 for multiplication inline path.
**Why human:** test_clifford_t_decomposition.py tests this; confirming it still passes after all Plan 03-05 changes is important.

## Gaps Summary

The phase is substantively complete. All 5 plans were executed with all major artifacts created and wired correctly:

- Plan 01 (file split): ToffoliAddition.c correctly replaced by 3 focused modules + 1 internal header + hot_path dispatch extraction. All build configuration updated.
- Plan 02 (gate infrastructure): T_GATE/TDG_GATE fully integrated across enum, gate primitives, counting, QASM export, inverse recognition, and Python API. MCX removed from gate_counts.
- Plan 03 (MCX decomposition): AND-ancilla patterns structurally present across all 4 arithmetic files (CDKM/CLA/Multiplication/Comparison). 120+ and_anc references across codebase confirm decomposition is wired.
- Plan 04 (Clifford+T): emit_ccx_clifford_t() and emit_ccx_clifford_t_seq() implemented; integrated into ToffoliMultiplication.c inline paths via emit_ccx_or_clifford_t multiplexer.
- Plan 05 (hardcoded sequences): 8 MCX-free static const sequence files + dispatch + generation script all wired into toffoli_cQQ_add(). No 3+ control gates in any generated file.

**One gap found:** test_mcx_decomposition.py (Plan 03) has a broken test helper (`_get_mcx_count()`) that creates a fresh empty circuit instead of reading the circuit built by the test. All 23 purity assertions in this file pass vacuously and provide no meaningful verification of MCX absence. This was acknowledged in the 74-05 summary but left unfixed. The test_decomposed_sequences.py (Plan 05) correctly fills this gap for the cQQ addition path, but the other operations (cCQ addition, controlled CLA, controlled multiplication, equality comparison) remain unverified at runtime.

The structural code audit (and_anc references, no 3+ control NumControls in sequence files, emit_ccx_or_clifford_t multiplexer) gives high confidence the goal is met. The gap is in test quality, not in the implementation itself.

---
_Verified: 2026-02-17T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
