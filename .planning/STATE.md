# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v3.0 Fault-Tolerant Arithmetic -- Phase 74 complete (5/5 plans). Milestone v3.0 complete.

## Current Position

Phase: 74 of 74 (MCX/CCX Gate Decomposition & Sequence Refactoring)
Plan: 5 of 5 complete
Status: Phase 74 complete. All 5 plans executed (waves 1-3 done). v3.0 Fault-Tolerant Arithmetic milestone complete.
Last activity: 2026-02-17 -- Completed 74-05 (hardcoded MCX-decomposed cQQ sequences)

Progress: [########################] 100% (v3.0 phases -- 32/32 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 213 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 22, v2.3: 4, v3.0: 32)
- Average duration: ~13 min/plan
- Total execution time: ~33.9 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 6 | Complete (2026-01-30) |
| v1.5 Bug Fixes & Verification | 28-33 | 33 | Complete (2026-02-01) |
| v1.6 Array & Comparison Fixes | 34-36 | 5 | Complete (2026-02-02) |
| v1.7 Bug Fixes & Array Optimization | 37, 40 | 2 | Complete (2026-02-02) |
| v1.8 Copy, Mutability & Uncomp Fix | 41-44 | 7 | Complete (2026-02-03) |
| v1.9 Pixel-Art Circuit Visualization | 45-47 | 7 | Complete (2026-02-03) |
| v2.0 Function Compilation | 48-51 | 8 | Complete (2026-02-04) |
| v2.1 Compile Enhancements | 52-54 | 6 | Complete (2026-02-05) |
| v2.2 Performance Optimization | 55-61 | 22 | Complete (2026-02-08) |
| v2.3 Hardcoding Right-Sizing | 62-64 | 4 | Complete (2026-02-08) |
| v3.0 Fault-Tolerant Arithmetic | 65-74 | 32 | Complete (2026-02-17) |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.
Recent (v2.3): Keep all addition widths 1-16 hardcoded (data-driven), shared QFT/IQFT factoring, multiplication "investigate" for future.
v3.0: Toffoli arithmetic as default (DSP-03), RCA before CLA, division via existing Python-level composition.
Phase 65-01: Inline switch/case for self-inverse gate classification (no helper function). Fixed run_instruction() proactively for Phase 66+ Toffoli inversion.
Phase 65-02: Block free-list uses sorted array with first-fit allocation and adjacent-block coalescing. No defragmentation -- fresh alloc when no block fits.
Phase 65-03: #ifdef DEBUG ancilla bitmap uses separate guard from DEBUG_OWNERSHIP for independent control. Dynamic bool array with doubling expansion.
Phase 66-01: Separate Toffoli QQ cache (not shared with QFT). CQ sequences fresh per call, freed by caller. Controlled ops fall back to QFT. ARITH_QFT=0 for backward-compatible default.
Phase 66-02: CDKM stores sum in b-register, so hot_path_add_qq swaps self/other for Toffoli path. CQ Toffoli MAJ/UMA simplification has bugs (xfail tests document them). Inline cast for fault_tolerant option (no cdef in elif).
Phase 66-03: CQ Toffoli uses temp-register QQ approach (X-init temp to classical value, run proven QQ CDKM adder, X-cleanup). CQ now requires 2*N+1 qubits (N temp + N self + 1 carry). BUG-CQ-TOFFOLI resolved.
Phase 67-01: Controlled CDKM adder (cQQ/cCQ) uses CCX + MCX(3 controls) pattern. Control qubit at 2*bits+1 (not 2*bits). CX-based controlled temp init/cleanup for cCQ. toffoli_sequence_free now handles large_control cleanup.
Phase 67-02: Controlled Toffoli dispatch wired into hot_path_add.c (no QFT fallback). Fixed MCX use-after-free: run_instruction transfers large_control ownership to circuit, free_circuit cleans up. 70 Toffoli tests pass.
Phase 67-03: ARITH_TOFFOLI is now the default arithmetic mode (1-line change in init_circuit). QFT available via ql.option('fault_tolerant', False). All QFT tests updated with explicit opt-in. 72 Toffoli + 165 hardcoded sequence tests pass.
Phase 68-01: Toffoli schoolbook multiplication via shift-and-add loop calling CDKM adders. QQ uses controlled adders per multiplier bit; CQ uses uncontrolled adders for set classical bits. Controlled mul falls through to QFT (Phase 69 scope). Fixed test_mul.py and test_add.py for Toffoli default mode (explicit QFT opt-in).
Phase 68-02: Exhaustive Toffoli multiplication verification at widths 1-3 (QQ and CQ). Custom result extraction: QQ at [2*width..3*width-1], CQ at [width..2*width-1]. Gate purity confirmed (no QFT gates). Default operator dispatch verified.
Phase 69-01: Controlled Toffoli multiplication uses AND-ancilla pattern for cQQ (CCX compute AND, cQQ_add, CCX uncompute) and direct cQQ_add with ext_ctrl for cCQ. Width 1 uses MCX(3 controls). Carry+AND ancilla reused per loop iteration. hot_path_mul.c now routes all controlled+Toffoli to new functions.
Phase 69-02: BUG-COND-MUL-01 root-caused: scope cleanup in __exit__ calls _do_uncompute on out-of-place mul results created inside with-blocks, reversing all gates. C backend is correct. Workaround: current_scope_depth.set(0) during multiplication. All 12 controlled mul tests pass with workaround.
Phase 69-03: Toffoli division/modulo verification with MCX-to-basis-gate transpilation for MPS compatibility. Toffoli div failures differ from QFT (width 3 even values with div=1). Modulo widely broken (BUG-MOD-REDUCE). Controlled division blocked by missing controlled XOR. Gate purity confirmed. Used allocated_start for result extraction.
Phase 70-01: Cross-backend equivalence tests for addition/subtraction (Toffoli vs QFT) at widths 1-8. Discovered BUG-CQQ-QFT: QFT controlled QQ in-place addition produces incorrect results at width 2+ (CCP rotation angle errors). Used in-place cQQ (qa += qb) instead of out-of-place due to missing controlled XOR. Widths 7-8 marked slow.
Phase 70-02: Cross-backend equivalence tests for multiplication (widths 1-6) and division/modulo (widths 2-6). Multiplication QQ/CQ match at all widths; controlled mul xfail at width 2+ (BUG-CQQ-QFT). Discovered BUG-QFT-DIV: QFT division/modulo is pervasively broken at all tested widths (first explicit QFT division testing since Phase 67-03). MPS required for both backends in division tests (34+ qubit QFT circuits). 87 total cross-backend test cases.
Phase 71-01: CLA infrastructure (cla_override field, option plumbing, dispatch in hot_path_add.c with CLA_THRESHOLD=4). BK CLA algorithm deferred -- in-place quantum CLA ancilla uncomputation is fundamentally impossible with single prefix tree pass. toffoli_QQ_add_bk() returns NULL, silent fallback to RCA. 13 CLA smoke tests pass via fallback.
Phase 71-02: KS QQ + BK/KS CQ CLA adder stubs all return NULL (same uncomputation impossibility). qubit_saving field in circuit_t for BK vs KS variant selection. CQ CLA dispatch with temp-register approach and goto-based RCA fallback. 22 exhaustive CLA tests pass via RCA fallback.
Phase 71-03: Controlled CLA stubs (cQQ/cCQ x BK/KS) all return NULL. Controlled CLA dispatch in both QQ and CQ hot_path_add paths with silent RCA fallback. ext_ctrl placed after CLA ancilla in qubit layout. 18 controlled CLA tests + 22 existing = 40 total CLA tests pass.
Phase 71-04: Comprehensive CLA verification suite: CLA vs RCA equivalence at widths 1-6 (QQ/CQ/sub), depth comparison xfail (CLA deferred), gate purity, mixed-width, multiplication propagation, ancilla cleanup via statevector. 40 verification tests (32 pass + 4 xfail + 4 slow). Phase 71 complete.
Phase 71-05 (gap closure): BK CLA algorithm implementation with 6-phase compute-copy-uncompute pattern. Forward-only (carry-copy ancilla NOT uncomputed; subtraction uses RCA fallback via !invert guard). CLA_THRESHOLD lowered from 4 to 2. Ancilla count uses actual merge count from bk_compute_merges(). 18 exhaustive BK tests (16 pass + 2 xfail). All 40 existing CLA tests still pass.
Phase 71-06 (gap closure): BK CQ/cQQ/cCQ CLA adders via sequence-copy pattern. CQ: X-init temp + copy QQ gates + X-cleanup. cQQ: inject ext_ctrl into every gate (X->CX, CX->CCX, CCX->MCX). cCQ: CX-init + copy cQQ gates + CX-cleanup. Fixed depth measurement: ql.circuit() creates new circuit, must store reference. BK depth ~50% less than RCA (width 8: 19 vs 35). Phase 71 gap closure complete.
Phase 72-01: Toffoli hardcoded sequence generation. QQ as static const (CX/CCX max 2 controls), cQQ as dynamic init with caching (MCX needs large_control). Separate toffoli_sequences.h header. 8 per-width C files + dispatch for widths 1-8. Generation script: scripts/generate_toffoli_seq.py (856 lines).
Phase 72-03: AND-ancilla MCX decomposition for QQ multiplication. Each MCX(3-control) in controlled CDKM adder decomposed into 3 CCX via AND-ancilla. Inline gate emission (not cached sequences) for decomposed controlled addition. gate_counts_t now separates CCX (2 controls) from MCX (3+ controls). Python gate_counts dict exposes 'MCX' and 'T' keys. 20 new tests + 21 existing = 41 multiplication tests pass.
Phase 72-02: Hardcoded Toffoli CDKM sequences wired into ToffoliAddition.c dispatch for widths 1-8. Lookup between cache check and dynamic generation (first call: hardcoded hit -> cache store; subsequent: cache hit). 9 Toffoli C files added to setup.py. 17 tests: T-count reporting (T=7*(CCX+MCX)), QQ correctness at widths 1-4, gate purity, controlled QQ, subtraction. Phase 72 complete.
Phase 73-01: Inline CQ/cCQ CDKM + BK CLA generators with classical-bit gate simplification. CQ: skip MAJ at bit=0 (carry=|0>), fold X-init at bit=1. cCQ: CX-init + standard cMAJ at bit=1, skip at bit=0. BK CLA Phase F must be inlined (temp=|0> after Phase E makes copied CX a NOP). 39 exhaustive tests + 89 existing pass. BK Phase F bug found during testing and auto-fixed (Rule 1).
Phase 73-02: Hardcoded CQ/cCQ increment (value=1) sequences for widths 1-8. CQ uses static const (no MCX), cCQ uses dynamic init with caching (MCX needs large_control). copy_hardcoded_sequence() deep-copies static to caller-owned memory. Early-return in toffoli_CQ_add/toffoli_cCQ_add for value=1. 14 new tests + 128 existing = 142 Toffoli tests pass. Phase 73 complete.
Phase 74-01: ToffoliAddition.c (1968 lines) split into ToffoliAdditionCDKM.c (778), ToffoliAdditionCLA.c (934), ToffoliAdditionHelpers.c (151) + toffoli_addition_internal.h (60). Split by algorithm (CDKM vs CLA), not operation type. Toffoli dispatch extracted from hot_path_add.c (530->145 lines) into hot_path_add_toffoli.c (414 lines). Pure refactoring, zero logic changes.
Phase 74-02: T_GATE/TDG_GATE enum values, gate primitives (t_gate/tdg_gate), inverse recognition (T/Tdg as mutual inverses). toffoli_decompose field in circuit_t with Python API. Replaced mcx_gates with t_gates/tdg_gates in gate_counts_t. Dual T-count formula: actual when T present, 7*CCX estimate otherwise. QASM exports "t"/"tdg". Updated 4 test files (removed MCX references). 90+ tests pass.
Phase 74-03: AND-ancilla MCX decomposition for all 9 MCX emission points. CDKM: emit_cMAJ/emit_cUMA get and_anc param, MCX(3)->3 CCX (5 layers instead of 3). CLA: emit_mcx3_seq/emit_mcx_recursive_seq helpers. Multiplication: cmul_qq width-1 MCX(3)->3 CCX. Comparison: recursive AND-ancilla decomposition for CQ_equal_width (bits>=3) and cCQ_equal_width (bits>=2). Python qint_comparison.pxi allocates AND-ancilla via circuit allocator. Hardcoded cQQ/cCQ sequences bypassed (contain MCX). 23 MCX purity tests confirm zero MCX gates in all Toffoli-mode output.
Phase 74-04: CCX->Clifford+T decomposition via emit_ccx_clifford_t() helper (15-gate exact sequence: 2H+4T+3Tdg+6CX per CCX). Integrated into all inline emission paths in ToffoliMultiplication.c via emit_ccx_or_clifford_t multiplexer. Only inline circuit-based paths decomposed; cached sequence paths defer to Plan 05. T-count exact when decompose=on (T = T_gates + Tdg_gates, no estimates). 19-test suite with equivalence testing pattern (on/off produce same results). 4:3 T/Tdg ratio verified.
Phase 74-05: MCX-decomposed hardcoded cQQ sequences for widths 1-8 via AND-ancilla pattern (MCX(3)->3 CCX). Static const arrays with max 2 controls per gate. Generation script: scripts/generate_toffoli_decomp_seq.py. Dispatch wired into toffoli_cQQ_add() in ToffoliAdditionCDKM.c. 94-test suite: purity (zero MCX), CCX presence, T-count=7*CCX, controlled/uncontrolled equivalence, subtraction, CQ purity. Phase 74 complete. v3.0 milestone complete.

### Roadmap Evolution

- Phase 73 added: Toffoli CQ/cCQ Classical-Bit Gate Reduction
- Phase 74 added: MCX/CCX Gate Decomposition & Sequence Refactoring

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication scope auto-uncomputation (root-caused in 69-02: __exit__ scope cleanup reverses out-of-place mul results; workaround: scope-depth trick)
- BUG-CQQ-QFT: QFT controlled QQ in-place addition (CCP decomposition) incorrect at width 2+ (discovered in Phase 70-01). Also affects controlled multiplication (confirmed in Phase 70-02).
- BUG-QFT-DIV: QFT division/modulo is pervasively broken at all tested widths (discovered in Phase 70-02). Width 2: 8/9 cases wrong. Width 3: 26/36 cases wrong. First explicit QFT division test since Phase 67-03 made Toffoli default. QFT quantum division/modulo also broken.
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one (discovered in v1.8)
- 32-bit multiplication segfault (buffer overflow in C backend, discovered in Phase 61)

**v3.0 specific:**
- ~~reverse_circuit_range() negates GateValue for self-inverse gates~~ -- FIXED in 65-01 (b8a567a)
- ~~allocator_alloc() only reuses freed ancilla for count=1~~ -- FIXED in 65-02 (11fb70d)
- Optimizer gate cancellation rules designed for QFT -- may need disabling for Toffoli initially
- ~~BUG-CQ-TOFFOLI: CQ Toffoli MAJ/UMA simplification in ToffoliAddition.c produces incorrect results for widths 2+~~ -- FIXED in 66-03 (911e442, c313bbe) via temp-register QQ approach
- ~~MCX use-after-free in run_instruction (garbage qubit indices for 3+ control gates)~~ -- FIXED in 67-02 (cf5b6b6) via circuit ownership transfer

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed 74-05-PLAN.md (hardcoded MCX-decomposed cQQ sequences). Phase 74 complete (5/5 plans). v3.0 Fault-Tolerant Arithmetic milestone complete.
Resume action: Start next milestone or run /gsd:audit-milestone to verify v3.0 completeness.

---
*State updated: 2026-02-17 -- Phase 74 plan 05 complete (MCX-decomposed hardcoded cQQ sequences for widths 1-8). Phase 74 complete. v3.0 milestone complete.*
