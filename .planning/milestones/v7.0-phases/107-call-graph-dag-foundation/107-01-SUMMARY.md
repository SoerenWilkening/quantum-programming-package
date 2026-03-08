---
phase: 107-call-graph-dag-foundation
plan: 01
subsystem: compile
tags: [rustworkx, numpy, dag, bitmask, call-graph, connected-components]

# Dependency graph
requires: []
provides:
  - CallGraphDAG class with rustworkx PyDAG backend
  - DAGNode with __slots__ and pre-computed np.uint64 bitmask
  - NumPy vectorized bitmask overlap edge computation
  - Parallel group detection via connected components
  - Builder stack for nested call context tracking
affects: [107-02-compile-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [numpy-bitmask-overlap, byte-lut-popcount, builder-stack-context]

key-files:
  created:
    - src/quantum_language/call_graph.py
    - tests/python/test_call_graph.py
  modified: []

key-decisions:
  - "Used __slots__ on DAGNode for memory efficiency"
  - "Module-level _POPCOUNT_LUT computed once at import for vectorized popcount"
  - "build_overlap_edges skips parent-child call edges to avoid double-counting"
  - "parallel_groups builds separate undirected PyGraph for clean component detection"

patterns-established:
  - "Bitmask overlap: np.uint64 bitmask per node, bitwise AND + byte LUT popcount for pairwise overlap"
  - "Builder stack: module-level list of (CallGraphDAG, parent_index) tuples, mirrors _capture_depth pattern"

requirements-completed: [CGRAPH-01, CGRAPH-02, CGRAPH-03]

# Metrics
duration: 2min
completed: 2026-03-05
---

# Phase 107 Plan 01: Call Graph DAG Foundation Summary

**CallGraphDAG module with rustworkx PyDAG, NumPy bitmask overlap computation, parallel group detection, and builder stack for nested call tracking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-05T20:31:29Z
- **Completed:** 2026-03-05T20:33:47Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files created:** 2

## Accomplishments
- DAGNode stores func_name, qubit_set (frozenset), gate_count, cache_key, and pre-computed np.uint64 bitmask
- CallGraphDAG wraps rustworkx PyDAG with add_node (with optional parent_index for hierarchical call edges)
- build_overlap_edges uses NumPy bitmask AND + byte LUT popcount; skips existing call edges
- parallel_groups returns connected components of undirected overlap graph via rx.connected_components
- Builder stack (push/pop/current_dag_context) manages nested compilation context
- 32 unit tests covering all components and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `df2012c` (test)
2. **Task 1 GREEN: Implementation** - `1f022d2` (feat)

## Files Created/Modified
- `src/quantum_language/call_graph.py` - CallGraphDAG, DAGNode, _popcount_array, builder stack functions (277 lines)
- `tests/python/test_call_graph.py` - 32 unit tests across 6 test classes (307 lines)

## Decisions Made
- Used `__slots__` on DAGNode for memory efficiency (no per-instance __dict__)
- Module-level `_POPCOUNT_LUT` (256-byte array) computed once at import time
- `build_overlap_edges` tracks existing call-edge pairs and skips them to avoid double-counting
- `parallel_groups` constructs a fresh undirected `rx.PyGraph` rather than projecting the directed DAG
- `pop_dag_context` returns `None` on empty stack (safe for unguarded calls)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- call_graph.py module is self-contained and fully tested
- Ready for Plan 02 to wire into compile.py (add opt parameter, intercept __call__ for DAG node recording)
- No changes to existing files were made

## Self-Check: PASSED

- FOUND: src/quantum_language/call_graph.py
- FOUND: tests/python/test_call_graph.py
- FOUND: df2012c (test commit)
- FOUND: 1f022d2 (feat commit)

---
*Phase: 107-call-graph-dag-foundation*
*Completed: 2026-03-05*
