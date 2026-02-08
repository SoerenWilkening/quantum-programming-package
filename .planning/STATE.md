# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-08)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v2.3 Hardcoding Right-Sizing milestone COMPLETE. Phase 64 regression verification passed -- no performance regression, zero new test failures.

## Current Position

Phase: 64 of 64 (Regression Verification)
Plan: 1 of 1 in current phase
Status: Phase complete -- v2.3 milestone complete
Last activity: 2026-02-08 -- Completed 64-01-PLAN.md (regression verification with PASS verdict)

Progress: [██████████] 100% (4/4 plans across 3 phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 181 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 6, v1.5: 33, v1.6: 5, v1.7: 2 + 2 phase-level docs, v1.8: 7, v1.9: 7, v2.0: 8, v2.1: 6, v2.2: 22, v2.3: 4)
- Average duration: ~13 min/plan
- Total execution time: ~27.1 hours

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

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.
Recent: "Profile before optimizing" principle from v2.2 carries forward -- this milestone is measurement-first.
- Subprocess isolation for first-call benchmarks (C caches are per-process, non-resettable)
- In-process measurement for cached dispatch comparison (cache behavior is the target)
- Width 8 vs 17 for hardcoded vs dynamic dispatch comparison
- Multiplication recommendation: "investigate" (48x addition cost, CQ_mul not cached, but binary size concern)
- Bitwise recommendation: "skip" (max 288us, trivial generation)
- Division recommendation: "skip" (Python-level loop cost, not C sequence generation)
- Break-even: 3,533 cached calls or 550 first calls to recoup 192ms import overhead
- **KEEP all addition widths 1-16 hardcoded** (Phase 63 decision, data-driven from Phase 62 benchmarks)
- **Segmented optimization** (QFT/middle/IQFT optimized independently) to enable shared layer arrays
- **Packed QFT layout** from _generate_qft_layers() for shared static const arrays
- **Const vs mutable separation** for sharing: static const arrays for QQ/cQQ, init helpers for CQ/cCQ
- **15% regression tolerance** for timing benchmarks (accounts for ~8% stdev observed in Phase 62)
- **System noise identification** via contradictory results on identical code paths (Q_and vs Q_or)
- **Binary size reduced 11.1%** (17.2MB -> 15.3MB) from shared QFT/IQFT -- compiler did not fully deduplicate before

### Blockers/Concerns

**Carry forward:**
- BUG-DIV-02: MSB comparison leak in division
- BUG-MOD-REDUCE: _reduce_mod result corruption (needs different circuit structure)
- BUG-COND-MUL-01: Controlled multiplication corruption (not yet investigated)
- BUG-WIDTH-ADD: Mixed-width QFT addition off-by-one (discovered in v1.8)
- 32-bit multiplication segfault (buffer overflow in C backend, discovered in Phase 61)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 014 | cQQ_add qubit layout fix | 2026-02-05 | abbd87f | [014-cqq-add-hardcoded-or-not-doesn-t-seem-to](./quick/014-cqq-add-hardcoded-or-not-doesn-t-seem-to/) |
| 015 | Fix cQQ_add algorithm bugs | 2026-02-06 | c891a32 | [015-fix-cqq-add-algorithm-bugs](./quick/015-fix-cqq-add-algorithm-bugs/) |

## Session Continuity

Last session: 2026-02-08
Stopped at: Completed Phase 64 plan 01 (regression verification) -- v2.3 milestone complete
Resume file: N/A -- milestone complete
Resume action: Plan next milestone or release v2.3

---
*State updated: 2026-02-08 -- Completed 64-01 regression verification (v2.3 Hardcoding Right-Sizing milestone complete)*
