---
phase: 112-compile-infrastructure-optimization
plan: 01
subsystem: infra
tags: [numpy, call-graph, overlap-detection, profiling, benchmarks]

# Dependency graph
requires:
  - phase: 107-111
    provides: "call_graph.py with frozenset-based overlap detection"
provides:
  - "DAGNode with _qubit_array (numpy) alongside frozenset qubit_set"
  - "numpy intersect1d overlap detection in build_overlap_edges, parallel_groups, merge_groups"
  - "BASELINE profiling benchmarks for qubit_set construction and overlap detection"
affects: [112-02, compile-performance, chess-walk-circuits]

# Tech tracking
tech-stack:
  added: [numpy (in call_graph.py overlap path)]
  patterns: [dual-storage DAGNode (frozenset + numpy array), numpy intersect1d for set overlap]

key-files:
  created: []
  modified:
    - src/quantum_language/call_graph.py
    - src/quantum_language/compile.py
    - tests/python/test_compile_performance.py

key-decisions:
  - "Keep frozenset qubit_set for backward compatibility; _qubit_array is supplementary"
  - "Use np.intp dtype for qubit arrays (platform-native integer)"
  - "Bitmask computation stays as Python int loop (>64 qubit support requires arbitrary precision)"

patterns-established:
  - "Dual-storage pattern: frozenset for API compatibility, numpy array for fast computation"

requirements-completed: [COMP-02, COMP-03]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 112 Plan 01: Profiling Baseline & Numpy Overlap Migration Summary

**DAGNode dual-storage with numpy _qubit_array and np.intersect1d overlap detection, plus COMP-03 baseline benchmarks**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T12:46:02Z
- **Completed:** 2026-03-08T12:49:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added qubit_set construction and overlap detection baseline benchmarks to test_compile_performance.py
- Migrated all three overlap methods (build_overlap_edges, parallel_groups, merge_groups) from frozenset intersection to np.intersect1d
- Added _qubit_array to DAGNode with dual-storage pattern preserving backward compatibility
- Updated compile.py finalization path to maintain _qubit_array consistency
- All 163 call_graph + merge tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend profiling benchmarks with qubit_set and overlap micro-benchmarks** - `5d0120c` (feat)
2. **Task 2: Migrate call_graph.py to numpy overlap detection with dual-storage DAGNode** - `be1ef19` (feat)

## Files Created/Modified
- `tests/python/test_compile_performance.py` - Added BASELINE benchmarks for qubit_set construction and overlap detection
- `src/quantum_language/call_graph.py` - Added numpy import, _qubit_array to DAGNode, np.intersect1d in overlap methods
- `src/quantum_language/compile.py` - Added _qubit_array update in capture finalization path

## Decisions Made
- Kept frozenset qubit_set attribute unchanged for backward compatibility -- _qubit_array is supplementary
- Used np.intp dtype for qubit arrays (platform-native signed integer, matches numpy indexing)
- Bitmask computation remains Python int loop (numpy cannot handle >64-bit arbitrary precision integers)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Numpy overlap detection is active and verified with zero regressions
- Baseline benchmarks captured for future comparison after further optimizations
- Ready for 112-02 (additional compile infrastructure work)

---
*Phase: 112-compile-infrastructure-optimization*
*Completed: 2026-03-08*
