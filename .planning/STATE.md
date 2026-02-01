# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.5 Bug Fixes & Exhaustive Verification -- Phase 33 COMPLETE

## Current Position

Phase: 33 of 33 (Advanced Feature Verification) -- COMPLETE
Plan: 3 of 3
Status: Phase 33 complete. Array verification done (5 pass, 7 xfail, 2 xpass). All VADV plans executed.
Last activity: 2026-02-01 -- Completed 33-03-PLAN.md (array verification)

Progress: [██████████] 58%

## Performance Metrics

**Velocity:**
- Total plans completed: 117 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 31)
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

**Recent (Phase 33):**

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 33-02 | Remove eq/ne xfail from conditional tests | BUG-CMP-01 does not affect conditional gating -- qbool controls with-block correctly |
| 33-02 | Document BUG-COND-MUL-01 as new bug | cCQ_mul corrupts result register; needs C backend fix |
| 33-02 | Keep all condition values in [0,3] for width=3 | Avoids BUG-CMP-02 MSB boundary issues |
| 33-01 | Separate result correctness from ancilla cleanup for comparisons | gt/le use widened temps leaving ancilla dirty by design |
| 33-01 | Use width=3 for all uncomputation tests | 2-bit signed range too narrow for meaningful tests |
| 33-01 | Verify input preservation as part of uncomputation check | Ensures uncomputation does not corrupt input operands |
| 33-03 | Non-strict xfail for all array tests | BUG-ARRAY-INIT blocks correct initialization; some single-element cases accidentally pass |
| 33-03 | Added manual sanity tests alongside array tests | Proves underlying operations work when array init bug is absent |

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
- **BUG-BIT-01 (FIXED in 32-03):** CQ bit ordering mismatch (MSB/LSB) and mixed-width padding allocation order. Same-width CQ: 2418/2418 pass. QQ mixed-width: all pass. CQ mixed-width: design limitation (plain int has no width metadata).

**New bugs discovered (Phase 33):**
- **BUG-COND-MUL-01 (Controlled Multiplication Corruption):** cCQ_mul produces 0 for both True and False conditional branches, corrupting the result register entirely. Controlled add/sub work correctly.

**New bugs discovered (Phase 33 - arrays):**
- **BUG-ARRAY-INIT (Array Constructor Bug):** `ql.array([values], width=w)` passes `self._width` as VALUE to `qint()` instead of as width parameter. All elements get quantum value = width, ignoring user data. Fix: `q = qint(value, width=self._width)` in qarray.pyx line 303.

**Key findings (Phase 33):**
- BUG-CMP-01 (eq/ne inversion) does NOT affect conditional gating. The qbool produced by eq/ne correctly controls `with` blocks despite returning inverted comparison values.
- Arithmetic uncomputation (EAGER mode) works fully: correct results, preserved inputs, clean ancilla for add/sub/mul.
- Comparison uncomputation partial: gt/le leave ancilla dirty (widened temporaries). lt/ge clean up fully.
- eq/ne unexpectedly pass with uncomputation enabled (xpass, non-strict).
- Array operations (sum, AND, OR, element-wise) work correctly when qints are constructed manually; only the array constructor is broken.

## Session Continuity

Last session: 2026-02-01
Stopped at: Completed 33-03-PLAN.md (final plan of final phase)
Resume file: None
Resume action: Phase 33 complete. All v1.5 verification phases done.

---
*State updated: 2026-02-01 after 33-03 execution (Array Verification complete)*
