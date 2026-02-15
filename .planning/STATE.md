# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v3.0 Fault-Tolerant Arithmetic -- Phase 69 plans 01 and 03 complete

## Current Position

Phase: 69 of 72 (Controlled Multiplication/Division) -- IN PROGRESS
Plan: 2 of 3 remaining (plans 01 and 03 complete, plan 02 pending)
Status: Controlled Toffoli multiplication implemented and dispatched. Plan 02 (tests) remaining.
Last activity: 2026-02-15 -- Completed 69-01 (Controlled Toffoli multiplication implementation)

Progress: [#############___________] 46% (v3.0 phases -- 15/~24 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 195 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 22, v2.3: 4, v3.0: 14)
- Average duration: ~13 min/plan
- Total execution time: ~30.2 hours

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
| v3.0 Fault-Tolerant Arithmetic | 65-72 | 12+ | In progress |

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
Phase 69-03: Toffoli division/modulo verification with MCX-to-basis-gate transpilation for MPS compatibility. Toffoli div failures differ from QFT (width 3 even values with div=1). Modulo widely broken (BUG-MOD-REDUCE). Controlled division blocked by missing controlled XOR. Gate purity confirmed. Used allocated_start for result extraction.

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one (discovered in v1.8)
- 32-bit multiplication segfault (buffer overflow in C backend, discovered in Phase 61)

**v3.0 specific:**
- ~~reverse_circuit_range() negates GateValue for self-inverse gates~~ -- FIXED in 65-01 (b8a567a)
- ~~allocator_alloc() only reuses freed ancilla for count=1~~ -- FIXED in 65-02 (11fb70d)
- Optimizer gate cancellation rules designed for QFT -- may need disabling for Toffoli initially
- ~~BUG-CQ-TOFFOLI: CQ Toffoli MAJ/UMA simplification in ToffoliAddition.c produces incorrect results for widths 2+~~ -- FIXED in 66-03 (911e442, c313bbe) via temp-register QQ approach
- ~~MCX use-after-free in run_instruction (garbage qubit indices for 3+ control gates)~~ -- FIXED in 67-02 (cf5b6b6) via circuit ownership transfer

## Session Continuity

Last session: 2026-02-15
Stopped at: Completed 69-01-PLAN.md (Controlled Toffoli multiplication implementation)
Resume file: N/A
Resume action: Execute Phase 69-02 (Controlled multiplication verification tests)

---
*State updated: 2026-02-15 -- Phase 69-01 complete (Controlled Toffoli multiplication)*
