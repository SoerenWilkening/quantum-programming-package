# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v4.1 Quality & Efficiency -- Phase 83 (Tech Debt Cleanup)

## Current Position

Phase: 83 of 89 (Tech Debt Cleanup) -- COMPLETE
Plan: 2 of 2 in current phase (all plans complete)
Status: Phase 83 complete, ready for Phase 84
Last activity: 2026-02-23 -- Completed 83-01 (QPU removal & preprocessor drift hook)

Progress: [============                                      ] 2/8 phases (v4.1)

## Performance Metrics

**Velocity:**
- Total plans completed: 253 (v1.0-v4.1)
- Average duration: ~13 min/plan
- Total execution time: ~40.8 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0-v2.3 | 1-64 | 166 | Complete |
| v3.0 Fault-Tolerant | 65-75 | 35 | Complete (2026-02-18) |
| v4.0 Grover's Algorithm | 76-81 | 18 | Complete (2026-02-22) |
| v4.1 Quality & Efficiency | 82-89 | 4 | In progress |

**v4.1 Plan Details:**

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 82 | 01 | 21min | 3 | 7 |
| 82 | 02 | 324min | 1 | 2 |
| 83 | 01 | 49min | 2 | 28 |
| 83 | 02 | 39min | 2 | 3 |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

**Phase 82-01:**
- pyproject.toml is single source of truth for dependencies (removed install_requires/extras_require from setup.py)
- pytest-cov in dev extras; sim_backend.py with lazy cached import guards
- QUANTUM_COVERAGE env var separate from QUANTUM_PROFILE

**Phase 82-02:**
- Python-level coverage baseline (not Cython linetrace) due to extreme overhead (~100x slowdown)
- Segfault-causing array/qarray tests excluded from coverage runs (known Phase 87 bug)
- Incremental batch coverage collection to avoid segfault data loss
- Baseline: 48.2% coverage, top priorities: compile.py (314 missing), draw.py (200 missing, 0%)

**Phase 83-01:**
- Used git add -f in sync-and-stage hook since preprocessed .pyx files are in .gitignore
- Pre-commit hook returns 0 always (auto-fix pattern) -- fixes drift and stages result rather than blocking
- QPU.h was just a thin wrapper around circuit.h; removal is safe and reduces confusion

**Phase 83-02:**
- Vulture found zero dead code at >=80% confidence; all 60% findings confirmed false positives (used from .pyx files, tests, or public API)
- Active generator scripts already had comprehensive docstrings and argparse; no changes needed
- Deprecation pattern: docstring notice + warnings.warn() after imports

### Blockers/Concerns

**Carry forward (all addressed in v4.1 phases):**
- BUG-CQQ-QFT -> Phase 86 (root cause, must fix before BUG-QFT-DIV)
- BUG-WIDTH-ADD -> Phase 86 (root cause)
- BUG-QFT-DIV -> Phase 86 (compound bug, resolves after root causes)
- BUG-DIV-02 -> Phase 86 (MSB comparison leak)
- BUG-COND-MUL-01 -> Phase 87 (scope/lifecycle, after QFT stable)
- BUG-MOD-REDUCE -> Phase 87 (may defer -- needs Beauregard redesign)
- 32-bit segfault -> Phase 87 (MAXLAYERINSEQUENCE fix)

### Research Flags

- Phase 86 (QFT Bug Fixes): HIGH risk -- CCP rotation audit needed
- Phase 87 (BUG-MOD-REDUCE): HIGH risk if attempted -- algorithm redesign
- Phase 85 (Optimizer): MEDIUM risk -- golden-master capture first

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 83-01-PLAN.md (Phase 83 complete)
Resume action: `/gsd:execute-phase 84` (next phase)

---
*State updated: 2026-02-23 -- Completed Phase 83 (tech debt cleanup) -- 2 plans complete*
