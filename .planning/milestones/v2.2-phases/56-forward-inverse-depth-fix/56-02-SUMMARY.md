---
phase: 56-forward-inverse-depth-fix
plan: 02
subsystem: testing
tags: [depth, layer_floor, compile, regression-tests, circuit-optimization]

# Dependency graph
requires:
  - phase: 56-forward-inverse-depth-fix
    plan: 01
    provides: Diagnostic tests confirming forward/adjoint depth equality
provides:
  - Permanent regression tests for forward/adjoint depth parity
  - Documentation of layer_floor depth behavior in compile.py
  - Verified depth equality holds for uncontrolled, multiwidth, and controlled variants
affects: [performance-optimization, compile-changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Depth regression test pattern: warm cache before measuring"
    - "Cache clearing awareness in circuit tests"

key-files:
  created: []
  modified:
    - src/quantum_language/compile.py
    - tests/test_compile.py

key-decisions:
  - "No code fix needed - forward/adjoint depth equality already guaranteed by design"
  - "ql.circuit() clears compilation cache - tests must warm cache before measuring"
  - "Added documentation to _replay() explaining depth behavior"

patterns-established:
  - "DEPTH-PARITY regression suite: test_forward_adjoint_depth_equal, multiwidth, controlled"
  - "Cache warming pattern: populate both forward and adjoint caches on same circuit"

# Metrics
duration: 8min
completed: 2026-02-05
---

# Phase 56 Plan 02: Depth Fix Implementation Summary

**Verified forward/adjoint depth equality (no fix needed), converted diagnostics to permanent regression tests, documented layer_floor behavior**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-05T14:03:43Z
- **Completed:** 2026-02-05T14:11:32Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Verified that forward/adjoint depth equality is already guaranteed by the layer_floor constraint in _replay()
- Converted diagnostic tests to permanent DEPTH-PARITY regression test suite
- Added comprehensive documentation explaining why forward/adjoint depths are equal
- Discovered and documented that ql.circuit() clears compilation cache (affects test design)

## Task Commits

Each task was committed atomically:

1. **Task 1: Document Depth Equality in compile.py** - `ec3bbc1` (docs)
2. **Task 2: Convert to Permanent Regression Tests** - `0c6fa35` (test)
3. **Task 3: Verify No Regression** - No commit (verification only)

## Files Created/Modified

- `src/quantum_language/compile.py` - Added documentation of layer_floor depth behavior
- `tests/test_compile.py` - Replaced DEPTH-DIAG section with DEPTH-PARITY regression suite

## Decisions Made

1. **No code fix needed** - Plan 01 diagnostics proved forward/adjoint depth equality already exists. The layer_floor constraint in _replay() ensures both paths produce identical circuit depth.

2. **Cache clearing affects test design** - Discovered that ql.circuit() clears the compilation cache. Tests must warm both forward and adjoint caches on the same circuit before measuring depth equality.

3. **Four regression tests established:**
   - test_forward_adjoint_depth_equal: Primary depth parity test (width 8)
   - test_forward_adjoint_depth_equal_multiwidth: Tests widths 4, 8, 16
   - test_controlled_depth_parity: Tests controlled variants
   - test_depth_capture_vs_replay: Tests capture/replay consistency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed test pattern for cache behavior**
- **Found during:** Task 2 (test conversion)
- **Issue:** Tests were clearing circuit between cache population and depth measurement, which also clears the cache
- **Fix:** Redesigned tests to warm both forward and adjoint caches on the same circuit before measuring
- **Files modified:** tests/test_compile.py
- **Verification:** All 4 regression tests pass
- **Committed in:** 0c6fa35 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Test pattern adjustment necessary to correctly measure depth with warm caches. No scope creep.

## Issues Encountered

- Initial tests showed forward/adjoint depth discrepancy (46 vs 24 gates), but this was due to cache miss causing capture+replay double execution
- Root cause: ql.circuit() clears compilation cache, so adjoint path was triggering a fresh capture
- Solution: Warm both caches before measuring, keep all operations on same circuit

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Forward/adjoint depth parity is verified and regression-tested
- Phase 56 success criteria met: "f(x) produces circuit depth equal to f.inverse(x)"
- The capture vs replay depth difference (when capture can parallelize) is a separate concern
- All 110 compile tests pass (no regression)

---
*Phase: 56-forward-inverse-depth-fix*
*Completed: 2026-02-05*
