# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.5 Bug Fixes & Exhaustive Verification -- Phase 32 complete

## Current Position

Phase: 32 of 33 (Bitwise Verification)
Plan: 2 of 2 (COMPLETE)
Status: Phase 32 executed -- gaps found (3/5 must-haves verified, BUG-BIT-01 blocks CQ + mixed-width)
Last activity: 2026-02-01 -- Phase 32 verification: gaps_found

Progress: [████████░░] 54%

## Performance Metrics

**Velocity:**
- Total plans completed: 112 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 26)
- Average duration: ~10 min/plan
- Total execution time: ~18.8 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 6 | Complete (2026-01-30) |
| v1.5 Bug Fixes & Verification | 28-33 | TBD | In progress |

## Accumulated Context

### Decisions

Milestone decisions archived. See PROJECT.md Key Decisions table for full history.

**Recent (Phase 32):**

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 32-01 | gc.collect() + keepalive refs in verify_circuit | Bitwise ops use uncomputation GC; qint destructors inject gates into new circuit |
| 32-01 | Non-strict xfail for CQ tests (b != max_val) | BUG-BIT-01 failure pattern too complex to predict exactly |
| 32-02 | Non-strict xfail for all mixed-width tests | Some AND cases accidentally pass; strict would cause xpass failures |
| 32-02 | BUG-BIT-01 covers both allocation and logic bugs | Same root cause: width-extension code in C backend |
| 32-02 | Skip (not xfail) for degenerate circuit preservation | CQ ops with classical 0 legitimately produce smaller circuits |

### Blockers/Concerns

**Known C backend bugs (v1.5 targets):**
- **BUG-05 (FULLY FIXED):** circuit() now properly frees old circuit and resets all Python globals. Fixed in plan 29-15.
- **BUG-04 (FULLY FIXED):** All 7 QFT addition tests pass deterministically.
- **BUG-03 (FULLY FIXED):** QQ_mul rewrote with correct CCP decomposition and qubit mapping. 5/5 multiplication tests pass. Fixed in plan 29-17.
- **BUG-01 (FULLY FIXED):** All 5 subtraction tests pass.
- **BUG-02 (FULLY FIXED):** All 6 comparison tests pass. Three root causes fixed: MSB index, GC gate reversal, unsigned overflow. Fixed in plan 29-16.

**New bugs discovered (Phase 30):**
- **BUG-06 (_reduce_mod result corruption):** When modular result is 0, output is N-2; larger moduli have widespread failures. Affects all qint_mod operations.
- **BUG-07 (subtraction extraction instability):** qint_mod subtraction circuit layout varies by input, making position-based result extraction unreliable.
- **BUG-DIV-01 (comparison overflow in restoring division):** When divisor<<bit_pos >= 2^width, comparison produces wrong results. Affects widths >= 2.
- **BUG-DIV-02 (MSB comparison leak in division):** For values >= 2^(w-1), comparison ancillae from MSB iteration leak into LSB iteration. Affects a//1 for large a.

**New bugs discovered (Phase 31):**
- **BUG-CMP-01 (Equality Inversion):** eq/ne operators return inverted results for ALL inputs at ALL widths. Both QQ and CQ. 488 xfailed tests document this.
- **BUG-CMP-02 (Ordering Comparison Error):** lt/gt/le/ge produce incorrect results for specific (a,b) pairs where operands span MSB boundary.
- **BUG-CMP-03 (Circuit Size Explosion):** gt/le circuits exceed simulation memory at widths >= 7.

**New bugs discovered (Phase 32):**
- **BUG-BIT-01 (CQ Bitwise Result Layout + Mixed-width broken):** CQ bitwise ops allocate result qubits only per set bit of classical operand, not full width. Also, all mixed-width AND/OR/XOR produce incorrect results. Root cause in C backend LogicOperations width-extension code.

## Session Continuity

Last session: 2026-02-01
Stopped at: Phase 32 gaps_found -- 3/5 must-haves verified, BUG-BIT-01 blocks CQ + mixed-width
Resume file: None
Resume action: /gsd:plan-phase 32 --gaps to close BUG-BIT-01 gaps, or proceed to Phase 33

---
*State updated: 2026-02-01 after 32-01 execution (Phase 32 complete)*
