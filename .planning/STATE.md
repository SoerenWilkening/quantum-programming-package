# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v4.1 Quality & Efficiency -- Phase 86 (QFT Bug Fixes) COMPLETE

## Current Position

Phase: 86 of 89 (QFT Bug Fixes) -- COMPLETE
Plan: 3 of 3 in current phase (all plans complete)
Status: Phase 86 complete. BUG-04 (mixed-width addition) fixed, BUG-05 (cQQ_add rotation) fixed, BUG-06/BUG-08 (division ancilla leak) investigated and deferred.
Last activity: 2026-02-24 -- Completed 86-03 (division ancilla leak investigation)

Progress: [========================                          ] 5/8 phases (v4.1)

## Performance Metrics

**Velocity:**
- Total plans completed: 258 (v1.0-v4.1)
- Average duration: ~13 min/plan
- Total execution time: ~43.3 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0-v2.3 | 1-64 | 166 | Complete |
| v3.0 Fault-Tolerant | 65-75 | 35 | Complete (2026-02-18) |
| v4.0 Grover's Algorithm | 76-81 | 18 | Complete (2026-02-22) |
| v4.1 Quality & Efficiency | 82-89 | 12 | In progress |

**v4.1 Plan Details:**

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 82 | 01 | 21min | 3 | 7 |
| 82 | 02 | 324min | 1 | 2 |
| 83 | 01 | 49min | 2 | 28 |
| 83 | 02 | 39min | 2 | 3 |
| 84 | 01 | 45min | 2 | 9 |
| 84 | 02 | 60min | 2 | 12 |
| 85 | 01 | 12min | 2 | 23 |
| 85 | 02 | 10min | 2 | 3 |
| 85 | 03 | 8min | 2 | 3 |
| 86 | 01 | 15min | 2 | 2 |
| 86 | 02 | 15min | 2 | 1 |
| 86 | 03 | 120min | 2 | 2 |

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

**Phase 84-01:**
- Only entry-point functions (called from Python) get validated wrappers; internal C-to-C calls remain unwrapped for zero overhead
- Buffer limit set at 384 matching qubit_array allocation size (4*64 + 2*64 = QV_MAX_QUBIT_SLOTS)
- Arithmetic operations use C hot-path functions with stack arrays, no qubit_array bounds checks needed

**Phase 84-02:**
- unusedFunction/staticFunction cppcheck findings are false positives due to Cython cross-language calls -- suppressed
- Printf format specifiers changed %d -> %u for qubit_t/num_t (unsigned int typedefs)
- const-correctness applied to circuit_stats.c but NOT circuit_output.h to avoid cascading Cython changes
- clang-tidy: misc-include-cleaner and bugprone-narrowing-conversions excluded (noisy, no actionable fixes)

**Phase 85-01:**
- Fixed ++i to --i in smallest_layer_below_comp (PERF-01); also fixed boundary condition (< 0 to <= 0)
- Used ql.option('fault_tolerant', True/False) for arithmetic mode switching (not set_arithmetic_mode)
- Golden-master pattern: 20 circuit snapshots as JSON, parametrized verification tests
- Verified zero regressions: all pre-existing failures remain, no new failures introduced

**Phase 85-02:**
- Binary search in smallest_layer_below_comp: O(log L) replaces O(L) linear scan
- Debug fallback verified correctness, then removed (zero runtime cost)
- Benchmarks at 100-10K operations documented in docs/optimizer_benchmark_results.md

**Phase 85-03:**
- Stack-allocated gate_t in inject_remapped_gates eliminates per-gate malloc/free
- 36% overall compile replay speedup (before: 342.9us, after: 218.6us for medium workload)
- Profiling shows 93% of replay time is Python overhead; C inject is only 7%
- Further optimization would require Cython-level _replay (larger scope)

**Phase 86-01:**
- Zero-extend narrower operand at Python level before C dispatch (not modify C QQ_add)
- Applied to __add__, __radd__, __sub__, __rsub__ for QQ path; CQ path unaffected

**Phase 86-02:**
- Source qubit mapping in cQQ_add corrected to match QQ_add convention
- Only hot_path_cadd_qqq needed fixing; QQ_add already correct

**Phase 86-03:**
- BUG-06 deep fix deferred: widened comparison temps have operation_type=None, creation_scope=0
- Four approaches attempted (layer tracking, cascade deps, algorithm rewrite, separate ancilla) -- all failed
- Known-failing sets updated: KNOWN_DIV_MSB_LEAK (14 cases), KNOWN_MOD_MSB_LEAK (80 cases)
- Root cause: uncomputation architecture cannot handle orphan temporaries from operators returning derived results

### Blockers/Concerns

**Resolved in Phase 86:**
- BUG-CQQ-QFT -> FIXED (86-02: cQQ_add source qubit mapping)
- BUG-WIDTH-ADD -> FIXED (86-01: zero-extend narrower operand)

**Carry forward:**
- BUG-DIV-02/BUG-QFT-DIV -> Deferred from Phase 86 (requires uncomputation architecture redesign)
- BUG-COND-MUL-01 -> Phase 87 (scope/lifecycle, after QFT stable)
- BUG-MOD-REDUCE -> Phase 87 (may defer -- needs Beauregard redesign)
- 32-bit segfault -> Phase 87 (MAXLAYERINSEQUENCE fix)

### Research Flags

- Phase 87 (BUG-MOD-REDUCE): HIGH risk if attempted -- algorithm redesign
- Phase 87 (BUG-DIV-02): Requires uncomputation architecture changes (deferred from Phase 86)

## Session Continuity

Last session: 2026-02-24
Stopped at: Phase 86 complete. Ready for Phase 87 (Scope & Segfault Fixes).
Resume action: Plan and execute Phase 87

---
*State updated: 2026-02-24 -- Completed Phase 86 (QFT bug fixes) -- 3 plans complete (BUG-04 fixed, BUG-05 fixed, BUG-06/BUG-08 deferred)*
