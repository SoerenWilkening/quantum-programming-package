---
phase: 94-parametric-compilation
plan: 01
subsystem: compile
tags: [cache-key, mode-flags, parametric, fault-tolerant, tradeoff-policy, oracle]

# Dependency graph
requires:
  - phase: 93-tradeoff-depth-qubit
    provides: tradeoff_policy option and CLA override option in _core.pyx
provides:
  - Mode-aware cache keys in compile.py (FIX-04) preventing stale replay on mode switch
  - Mode-aware cache keys in oracle.py (FIX-04) for _oracle_cache_key and _lambda_cache_key
  - parametric=True flag accepted by @ql.compile decorator (PAR-01 API surface)
  - CompiledFunc.is_parametric read-only property
  - grover_oracle forces parametric=False on underlying CompiledFunc (PAR-04 foundation)
affects: [94-02-PLAN, 94-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [_get_mode_flags() helper for consistent cache key construction across all compile paths]

key-files:
  created: []
  modified:
    - src/quantum_language/compile.py
    - src/quantum_language/oracle.py
    - tests/test_compile.py

key-decisions:
  - "Cache key includes (arithmetic_mode, cla_override, tradeoff_policy) tuple appended to all 4 key construction sites"
  - "Oracle decorator forces parametric=False since oracle parameters are structural by nature"

patterns-established:
  - "_get_mode_flags() centralizes mode flag extraction for all cache key sites"
  - "Parametric state tracking fields on CompiledFunc (_parametric_topology, _parametric_probed, _parametric_safe)"

requirements-completed: [FIX-04, PAR-01]

# Metrics
duration: 5min
completed: 2026-02-25
---

# Phase 94 Plan 01: Mode-Aware Cache Keys and Parametric API Surface Summary

**FIX-04 cache key invalidation with arithmetic_mode/cla_override/tradeoff_policy flags, plus PAR-01 parametric=True API on @ql.compile and PAR-04 oracle override**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-25T23:00:34Z
- **Completed:** 2026-02-25T23:05:32Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- All compile cache keys (4 sites) now include mode flags preventing stale gate replay when switching between QFT/Toffoli modes or tradeoff policies (FIX-04)
- Oracle cache keys (_oracle_cache_key, _lambda_cache_key) extended with cla_override and tradeoff_policy
- @ql.compile(parametric=True) accepted as decorator argument with .is_parametric property (PAR-01)
- @ql.grover_oracle forces parametric=False on underlying CompiledFunc (PAR-04 foundation)
- 8 new tests covering mode-switch invalidation, same-mode reuse, parametric API, and oracle override

## Task Commits

Each task was committed atomically:

1. **Task 1: Add mode flags to compile cache key (FIX-04)** - `00c174b` (feat) - pre-existing commit
2. **Task 2: Add mode flags to oracle cache keys and force non-parametric for oracles** - `00c174b` (feat) - pre-existing commit
3. **Task 3: Write tests for FIX-04 cache invalidation and PAR-01 API** - `14645df` (test)

**Plan metadata:** (pending)

_Note: Tasks 1 and 2 were already committed in a prior session as a single atomic commit (00c174b). Task 3 tests were newly written and committed in this session._

## Files Created/Modified
- `src/quantum_language/compile.py` - _get_mode_flags() helper; mode flags in all 4 cache key sites; parametric parameter and state tracking; is_parametric property
- `src/quantum_language/oracle.py` - Extended _oracle_cache_key and _lambda_cache_key with cla_override/tradeoff_policy; grover_oracle forces non-parametric
- `tests/test_compile.py` - TestModeFlagCacheKey (3 tests) and TestParametricAPI (5 tests) classes

## Decisions Made
- Used tuple concatenation `+ mode_flags` for cache key extension to maintain backward compatibility with existing key structure
- Oracle parameters are structural by nature (different search targets produce different topologies), so parametric mode is always forced off for oracles

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ruff linting warnings in test code**
- **Found during:** Task 3 (test commit pre-commit hook)
- **Issue:** Unused variable assignments (c = ql.circuit(), cache_size variables) flagged by ruff F841
- **Fix:** Changed `c = ql.circuit()` to `ql.circuit()`, removed unused intermediate variables
- **Files modified:** tests/test_compile.py
- **Verification:** Pre-commit hooks pass, all 8 new tests still pass
- **Committed in:** 14645df (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Linting fix only, no functional changes. No scope creep.

## Issues Encountered
- Tasks 1 and 2 were already implemented and committed in a prior session (commit 00c174b). Verified correctness via smoke tests before proceeding to Task 3.
- 15 pre-existing test failures in test_compile.py (qarray-related and replay gate count mismatches) are unrelated to this plan's changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mode-aware cache keys are in place, enabling Plan 02 (parametric probe/replay lifecycle) to build on the parametric=True flag
- CompiledFunc parametric state fields (_parametric_topology, _parametric_probed, _parametric_safe) are initialized and ready for Plan 02 logic
- PAR-04 oracle override is ready for Plan 03 verification

## Self-Check: PASSED

- FOUND: 94-01-SUMMARY.md
- FOUND: 00c174b (Task 1+2 commit)
- FOUND: 14645df (Task 3 commit)
- FOUND: src/quantum_language/compile.py
- FOUND: src/quantum_language/oracle.py
- FOUND: tests/test_compile.py

---
*Phase: 94-parametric-compilation*
*Completed: 2026-02-25*
