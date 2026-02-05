---
phase: 20-modes-and-control
plan: 02
subsystem: api
tags: [python, cython, uncomputation, memory-management]

# Dependency graph
requires:
  - phase: 20-01
    provides: Mode-aware __del__ with _keep_flag placeholder check
  - phase: 18-uncomputation-integration
    provides: Core uncomputation infrastructure (_do_uncompute, uncompute methods)
provides:
  - keep() method for opt-out of automatic uncomputation
  - User control over qbool lifetime beyond normal scope
  - Explicit documentation of keep() vs uncompute() interaction
affects: [documentation, user-guides, future-scope-control-features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "keep() for permanent opt-out of automatic uncomputation"
    - "Explicit uncompute() always works regardless of keep() flag"

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pyx
    - python-backend/qint_operations.pxi

key-decisions:
  - "keep() is permanent (flag never cleared automatically) - simplest implementation"
  - "keep() only affects __del__, not explicit uncompute() - gives user full control"
  - "keep() returns None (no chaining) - follows Python convention for methods with side effects"

patterns-established:
  - "Warning to stderr for keep() on already-uncomputed qbool (not an error)"

# Metrics
duration: 3min
completed: 2026-01-28
---

# Phase 20 Plan 02: Uncomputation Opt-Out Summary

**keep() method for opt-out of automatic uncomputation, enabling safe return of qbools from functions**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-01-28T19:09:20Z
- **Completed:** 2026-01-28T19:12:39Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented keep() method that prevents automatic uncomputation in __del__
- Documented that explicit uncompute() still works after keep() (user has full control)
- Added warning when keep() called on already-uncomputed qbool

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _keep_flag attribute and keep() method** - `0c48c44` (feat)
2. **Task 2: Verify keep() does not prevent explicit uncompute** - `af42be7` (docs)

## Files Created/Modified
- `python-backend/quantum_language.pyx` - Added _keep_flag cdef attribute, initialized in both __init__ branches
- `python-backend/qint_operations.pxi` - Added keep() method with warning on uncomputed qbool, documented uncompute() behavior

## Decisions Made

**1. keep() is permanent (flag never cleared automatically)**
- Rationale: Simplest implementation avoids complex scope tracking
- User can call uncompute() explicitly when ready to clean up
- Matches plan's design decision per CONTEXT.md

**2. keep() only affects __del__, not explicit uncompute()**
- Rationale: Gives users full control - automatic behavior opt-out doesn't prevent manual cleanup
- Design pattern: "opt-out of automation, not control removal"
- Added explicit comment in uncompute() to document this decision

**3. keep() returns None (no chaining)**
- Rationale: Follows Python convention for methods with side effects only
- Prevents confusion about what would be returned

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation straightforward, __del__ check already in place from Plan 20-01.

## Next Phase Readiness

All Phase 20 scope control features complete:
- Plan 20-01: Mode-aware uncomputation (eager vs lazy)
- Plan 20-02: User opt-out via keep() method

Ready for:
- User documentation of uncomputation modes
- Integration testing of complex scope scenarios
- Future enhancements (e.g., scope-aware keep() if needed)

**No blockers.** Phase 20 complete.

---
*Phase: 20-modes-and-control*
*Completed: 2026-01-28*
