# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v3.0 Fault-Tolerant Arithmetic -- Phase 66 CDKM Ripple-Carry Adder

## Current Position

Phase: 66 of 72 (CDKM Ripple-Carry Adder) -- COMPLETE
Plan: 3 of 3 in current phase
Status: Phase 66 fully complete (including CQ gap closure), ready for Phase 67
Last activity: 2026-02-14 -- Completed 66-03 (CQ Toffoli gap closure)

Progress: [########________________] 23% (v3.0 phases -- 7/~24 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 188 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 22, v2.3: 4, v3.0: 7)
- Average duration: ~13 min/plan
- Total execution time: ~27.8 hours

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
| v3.0 Fault-Tolerant Arithmetic | 65-72 | TBD | In progress |

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

## Session Continuity

Last session: 2026-02-14
Stopped at: Completed 66-03-PLAN.md (CQ Toffoli gap closure)
Resume file: N/A
Resume action: Plan Phase 67 (controlled Toffoli operations)

---
*State updated: 2026-02-14 -- 66-03 complete (CQ Toffoli gap closure via temp-register QQ approach, BUG-CQ-TOFFOLI resolved)*
