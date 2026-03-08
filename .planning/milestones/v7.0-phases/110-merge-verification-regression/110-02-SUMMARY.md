---
phase: 110-merge-verification-regression
plan: 02
subsystem: testing
tags: [pytest, parametrize, monkeypatch, opt-level, regression]

# Dependency graph
requires:
  - phase: 109-selective-sequence-merging
    provides: "opt=2 merge pipeline, CompiledFunc opt parameter"
provides:
  - "opt_level pytest fixture parametrized over [1, 2, 3]"
  - "All compile/merge tests verified at opt=1, opt=2, opt=3"
affects: [110-merge-verification-regression]

# Tech tracking
tech-stack:
  added: []
  patterns: ["monkeypatch ql.compile at function level to inject opt defaults"]

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_compile.py
    - tests/python/test_merge.py

key-decisions:
  - "Patch ql.compile() function rather than CompiledFunc.__init__ to distinguish user-explicit opt= from defaults"
  - "Skip opt=2 injection for parametric=True calls to avoid ValueError by design"

patterns-established:
  - "opt_level fixture: monkeypatches ql.compile defaults, leaves explicit opt= untouched"

requirements-completed: [MERGE-04]

# Metrics
duration: 8min
completed: 2026-03-06
---

# Phase 110 Plan 02: Opt-Level Regression Summary

**opt_level pytest fixture parametrizing all 147 compile/merge tests across opt=1, opt=2, opt=3 with zero new failures**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-06T22:05:27Z
- **Completed:** 2026-03-06T22:13:29Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created opt_level fixture in conftest.py that monkeypatches ql.compile to inject opt level
- Wired 118 compile tests to run at all 3 opt levels (354 invocations, 309 pass, 45 pre-existing failures)
- Wired 29 merge tests to run at all 3 opt levels (87 invocations, all pass)
- Full regression: 441 invocations, 396 pass, 45 fail (all pre-existing, consistent across opt levels)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add opt_level conftest fixture and wire into test_compile.py** - `b1ce56e` (feat)
2. **Task 2: Wire opt_level into test_merge.py and verify full regression** - `b80680d` (feat)

## Files Created/Modified
- `tests/conftest.py` - Added opt_level fixture parametrized over [1, 2, 3], monkeypatches ql.compile defaults
- `tests/test_compile.py` - Added pytestmark usefixtures("opt_level") for module-wide parametrization
- `tests/python/test_merge.py` - Added pytestmark usefixtures("opt_level") for module-wide parametrization

## Decisions Made
- Patched ql.compile() function level instead of CompiledFunc.__init__ -- the compile() wrapper always passes all kwargs explicitly to CompiledFunc, making __init__-level patching unable to distinguish user-set vs default opt values
- Skip opt=2 injection when parametric=True to avoid triggering the intentional ValueError guard from Phase 109

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Changed monkeypatch target from CompiledFunc.__init__ to ql.compile()**
- **Found during:** Task 2 (wiring test_merge.py)
- **Issue:** The compile() wrapper always passes opt= explicitly to CompiledFunc.__init__, so the __init__-level patch could not distinguish user-explicit `opt=1` from the default. This caused tests with explicit `@ql.compile(opt=1)` in test_merge.py to be incorrectly overridden.
- **Fix:** Monkeypatch the `ql.compile` function itself, which receives `opt` as a keyword argument only when the user explicitly passes it.
- **Files modified:** tests/conftest.py
- **Verification:** All 29 merge tests pass at all 3 opt levels; no false overrides of explicit opt= values
- **Committed in:** b80680d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential correctness fix for the fixture implementation. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All compile and merge tests verified at opt=1, opt=2, and opt=3
- 15 pre-existing test failures documented and consistent across all opt levels
- Ready for any additional verification plans in Phase 110

---
*Phase: 110-merge-verification-regression*
*Completed: 2026-03-06*
