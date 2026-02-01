# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-01)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.6 Array & Comparison Fixes

## Current Position

Phase: 35 of 36 (Comparison Bug Fixes)
Plan: 2 of 2 in current phase
Status: Plan 35-02 complete (with regressions)
Last activity: 2026-02-01 — Completed 35-02-PLAN.md

Progress: [████░░░░░░] 40% (v1.6: 3/5 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 122 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 3)
- Average duration: ~12 min/plan
- Total execution time: ~20.7 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 6 | Complete (2026-01-30) |
| v1.5 Bug Fixes & Verification | 28-33 | 33 | Complete (2026-02-01) |
| v1.6 Array & Comparison Fixes | 34-36 | 5 | In Progress |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

**Recent (v1.6):**
- Positional value + keyword width pattern for qint constructor calls in arrays (34-01)
- Comparison results persist without auto-uncompute (matches Phase 29-16 pattern) (35-01)
- MSB-first qubit ordering for C backend comparison operations (35-01)
- Widened (n+1)-bit comparison applied to __lt__ (35-02)
- Right-aligned storage means index [63] is always MSB (35-02)

### Blockers/Concerns

**v1.6 targets (3 phases, 5 plans):**
- ✓ BUG-ARRAY-INIT: Fixed in 34-01 (qint constructor parameter swap)
- ✓ Array element-wise ops: Fixed by BUG-ARRAY-INIT resolution (9 tests pass)
- ✓ BUG-CMP-01: Fixed in 35-01 (dual-bug: GC gate reversal + bit-order reversal, 488 tests now pass)
- ⚠ BUG-CMP-02: Attempted fix in 35-02 (widened __lt__) but introduced regressions (signed/unsigned issue)
- ✓ BUG-CMP-03: Confirmed as non-issue (linear circuit growth, not exponential)

**Critical issue discovered:**
- Signed/unsigned interpretation mismatch in widened comparisons
- qint docstring says signed range [-2^(w-1), 2^(w-1)-1]
- Test oracle expects unsigned comparison
- 44 new test failures at MSB boundary
- Requires resolution before Phase 36 (test cleanup)

**Deferred to future milestone:**
- BUG-DIV-01, BUG-MOD-REDUCE, BUG-COND-MUL-01

## Session Continuity

Last session: 2026-02-01
Stopped at: Completed 35-02-PLAN.md (Phase 35 complete with regressions)
Resume file: None
Resume action: Create Phase 35-03 to fix signed/unsigned issue before Phase 36

---
*State updated: 2026-02-01 after 35-02 execution*
