---
phase: 109-selective-sequence-merging
plan: 01
subsystem: compile
tags: [rustworkx, numpy, bitmask, overlap, optimizer, merge]

# Dependency graph
requires:
  - phase: 107-call-graph-dag-foundation
    provides: CallGraphDAG with parallel_groups and overlap edge computation
provides:
  - merge_groups(threshold) method on CallGraphDAG for merge candidate detection
  - _merge_and_optimize helper for gate concatenation in physical qubit space
  - merge_threshold parameter on CompiledFunc and compile() decorator
  - parametric+opt=2 ValueError guard
affects: [109-02, 109-03, 110-verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [threshold-filtered connected components, physical-space gate remapping]

key-files:
  created:
    - tests/python/test_merge.py
  modified:
    - src/quantum_language/call_graph.py
    - src/quantum_language/compile.py

key-decisions:
  - "merge_groups reuses parallel_groups pattern with threshold filter and singleton exclusion"
  - "_merge_and_optimize wraps _optimize_gate_list with virtual-to-physical qubit remapping"
  - "parametric+opt=2 guard raises ValueError immediately at construction time"

patterns-established:
  - "Threshold-filtered overlap: merge_groups(threshold) filters edges by popcount >= threshold"
  - "Physical-space gate remapping: v2r dict applied to target and controls before optimization"

requirements-completed: [MERGE-01, MERGE-02]

# Metrics
duration: 3min
completed: 2026-03-06
---

# Phase 109 Plan 01: Merge Infrastructure Summary

**merge_groups() for overlap-based candidate detection plus _merge_and_optimize() for physical-space gate concatenation with cross-boundary cancellation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-06T21:00:01Z
- **Completed:** 2026-03-06T21:03:38Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- merge_groups(threshold) identifies connected components of overlapping-qubit sequences filtered by minimum overlap count
- _merge_and_optimize concatenates gate lists from multiple CompiledBlocks in physical qubit space and runs the existing multi-pass optimizer
- merge_threshold parameter wired through @ql.compile decorator to CompiledFunc
- parametric+opt=2 guard prevents unsupported combination at construction time
- 17 new unit tests covering all merge infrastructure (93 total with existing tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add merge_groups(threshold) to CallGraphDAG** - `176293b` (feat)
2. **Task 2: Add _merge_and_optimize helper and merge_threshold param** - `77ce197` (feat)

_Note: Both tasks followed TDD (RED-GREEN) with linter auto-formatting on commit._

## Files Created/Modified
- `tests/python/test_merge.py` - 17 unit tests for merge_groups, _merge_and_optimize, and CompiledFunc merge params
- `src/quantum_language/call_graph.py` - Added merge_groups(threshold) method to CallGraphDAG
- `src/quantum_language/compile.py` - Added _merge_and_optimize helper, merge_threshold param, parametric+opt=2 guard

## Decisions Made
- merge_groups reuses the parallel_groups pattern (PyGraph + connected_components) with threshold filter and singleton exclusion
- _merge_and_optimize wraps existing _optimize_gate_list with virtual-to-physical qubit remapping via v2r dict
- parametric+opt=2 guard raises ValueError immediately at __init__ time (fail-fast)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- merge_groups() and _merge_and_optimize() are ready for integration in 109-02 (applying merges during compilation)
- merge_threshold parameter is wired through but not yet used in __call__ path
- _merged_blocks attribute initialized to None, ready for population in 109-02

## Self-Check: PASSED

All files exist, both commits verified, merge_groups/merge_and_optimize/merge_threshold all functional.

---
*Phase: 109-selective-sequence-merging*
*Completed: 2026-03-06*
