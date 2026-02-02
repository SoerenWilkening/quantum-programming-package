# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.8 Phase 42 - Quantum Copy Foundation (plan 01 complete)

## Current Position

Phase: 42 of 44 (Quantum Copy Foundation)
Plan: 1 of 1 in current phase
Status: Phase complete
Last activity: 2026-02-02 - Completed 42-01-PLAN.md (copy primitives)

Progress: [####################] 50% (2/4 phases in v1.8)

## Performance Metrics

**Velocity:**
- Total plans completed: 131 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 3)
- Average duration: ~13 min/plan
- Total execution time: ~23.2 hours

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
| v1.8 Copy, Mutability & Uncomp Fix | 41-44 | 3/TBD | In progress |

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

### Blockers/Concerns

**Deferred from v1.7 (carry forward to future milestone):**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)

**Known limitations (not bugs):**
- Dirty ancilla in gt/le comparisons (by design, 2 xfail preserved)
- 4 pre-existing uncomputation test failures (lt/ge ancilla, compound and/or OOM) -- root cause: circuit optimizer parallelizes gates into shared layers, making used_layer unreliable for gate boundary tracking
- Future improvement: replace layer-based tracking with instruction-counter-based tracking

## Session Continuity

Last session: 2026-02-02 22:43 UTC
Stopped at: Completed 42-01-PLAN.md (Quantum Copy Foundation complete)
Resume file: None
Resume action: Plan Phase 43 (Copy-Aware Binary Operations)

---
*State updated: 2026-02-02 -- Phase 42 plan 01 (copy primitives) complete*
