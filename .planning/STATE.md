# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.8 Phase 44 - Array Mutability (in progress)

## Current Position

Phase: 44 of 44 (Array Mutability)
Plan: 1 of 2 in current phase
Status: In progress
Last activity: 2026-02-03 - Completed 44-01-PLAN.md

Progress: [####################################..] 87.5% (3.5/4 phases in v1.8)

## Performance Metrics

**Velocity:**
- Total plans completed: 134 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 6)
- Average duration: ~13 min/plan
- Total execution time: ~23.4 hours

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
| v1.8 Copy, Mutability & Uncomp Fix | 41-44 | 6/TBD | In progress |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

**Phase 41 decisions:**
- D41-01-1: Keep inline implementations in qint.pyx (Cython 3.0.11 disallows include inside cdef class)
- D41-01-2: Use strict < for LAZY scope comparison (prevents scope-0 auto-uncompute)
- D41-01-3: **REVISED by 41-02** -- Layer tracking IS now set on lt/gt results (no double-reversal risk since widened temps have no layer tracking)
- D41-02-1: Revise D41-01-3: layer tracking set on lt/gt results
- D41-02-2: Keep 4 pre-existing failures as-is (root cause is architectural: layer counter vs instruction counter)

**Phase 42 decisions:**
- D42-01-1: Place copy methods after __invert__ in qint.pyx (grouped with bitwise ops)
- D42-01-2: copy_onto does not set layer tracking or dependencies on target (raw CNOT op)
- D42-01-3: qbool.copy() uses cdef cast to access qubits from qint.copy() result

**Phase 43 decisions:**
- D43-01-1: Mark mixed-width add/sub tests as xfail (pre-existing QFT off-by-one bug, not caused by copy changes)
- D43-02-1: Mark rshift shift>0 tests as xfail (pre-existing BUG-DIV-02: floordiv incorrect results)
- D43-02-2: Add shift=0 short-circuit in lshift/rshift to avoid unnecessary mul/div circuits

### Blockers/Concerns

**Deferred from v1.7 (carry forward to future milestone):**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)

**Known limitations (not bugs):**
- Dirty ancilla in gt/le comparisons (by design, 2 xfail preserved)
- 4 pre-existing uncomputation test failures (lt/ge ancilla, compound and/or OOM) -- root cause: circuit optimizer parallelizes gates into shared layers, making used_layer unreliable for gate boundary tracking
- Future improvement: replace layer-based tracking with instruction-counter-based tracking
- BUG-WIDTH-ADD: Mixed-width QFT addition/subtraction off-by-one (discovered in Phase 43, pre-existing)

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 44-01-PLAN.md (in-place operators and setitem)
Resume file: None
Resume action: Execute 44-02-PLAN.md

---
*State updated: 2026-02-03 -- Plan 44-01 complete (2/2 tasks, qint in-place ops + qarray setitem)*
