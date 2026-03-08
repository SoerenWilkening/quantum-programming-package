---
phase: 108-call-graph-analysis-visualization
plan: 01
subsystem: compile-infrastructure
tags: [call-graph, dag, depth, t-count, aggregate, rustworkx]

requires:
  - phase: 107-call-graph-dag-foundation
    provides: "CallGraphDAG, DAGNode, parallel_groups, builder stack, compile.py DAG wiring"
provides:
  - "_compute_depth ASAP scheduling helper"
  - "_compute_t_count dual-formula helper"
  - "DAGNode with depth and t_count slots"
  - "CallGraphDAG.aggregate() returning gates/depth/qubits/t_count dict"
affects: [108-02, 109, 110]

tech-stack:
  added: []
  patterns: ["ASAP qubit occupancy scheduling for depth", "dual T-count formula (direct T or 7*CCX fallback)", "critical-path depth via sum of per-group max"]

key-files:
  created: []
  modified:
    - src/quantum_language/call_graph.py
    - src/quantum_language/compile.py
    - tests/python/test_call_graph.py

key-decisions:
  - "ASAP scheduling for depth: track per-qubit occupancy, each gate uses max(occupied qubits)+1"
  - "Dual T-count formula: prefer direct T/TDG count, fallback to 7*CCX when no T gates present"
  - "Critical-path depth in aggregate: sum of per-group max depths from parallel_groups()"

patterns-established:
  - "Per-node stat helpers as module-level functions (_compute_depth, _compute_t_count)"
  - "Stats computed eagerly at DAGNode creation time during compile"

requirements-completed: [CGRAPH-04, CGRAPH-05]

duration: 4min
completed: 2026-03-06
---

# Phase 108 Plan 01: Per-Node Stats & Aggregate Metrics Summary

**Per-node depth/T-count via ASAP scheduling and dual formula, plus aggregate() with critical-path depth across parallel groups**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-06T16:59:11Z
- **Completed:** 2026-03-06T17:03:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added _compute_depth helper using ASAP qubit occupancy scheduling for per-node circuit depth
- Added _compute_t_count helper with dual formula (direct T/TDG count or 7*CCX fallback)
- Extended DAGNode with depth and t_count slots, wired into all 3 add_node sites + placeholder update in compile.py
- Added aggregate() method returning gates/depth/qubits/t_count dict with critical-path depth
- Tests grew from 43 to 62 (19 new tests covering depth, t_count, and aggregate)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add depth/t_count to DAGNode and wire into compile.py**
   - `e00b438` (test: failing tests for depth, t_count, compute helpers)
   - `5b04cee` (feat: implement depth/t_count helpers, DAGNode extension, compile.py wiring)

2. **Task 2: Add aggregate() method to CallGraphDAG**
   - `d57ace4` (test: failing tests for aggregate method)
   - `611fee3` (feat: implement aggregate with critical-path depth)

## Files Created/Modified
- `src/quantum_language/call_graph.py` - Added _compute_depth, _compute_t_count helpers; extended DAGNode slots; added aggregate() method
- `src/quantum_language/compile.py` - Updated imports; all 3 add_node sites + placeholder update pass depth/t_count
- `tests/python/test_call_graph.py` - 19 new tests: TestComputeDepth (5), TestComputeTCount (4), TestDAGNode depth/t_count (2), TestAggregate (6), integration depth/t_count (2)

## Decisions Made
- ASAP scheduling for depth: track per-qubit occupancy dict, each gate occupies max(occupied qubits for that gate)+1
- Dual T-count: direct T_GATE(10)/TDG_GATE(11) count preferred; 7*CCX fallback only when t_direct==0
- Critical-path depth in aggregate: parallel_groups() determines independent groups, depth = sum of max(node.depth) within each group

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DAGNode has full per-node stats (gate_count, depth, t_count, qubit_set)
- aggregate() provides graph-wide metrics
- Ready for 108-02: DOT visualization and compilation report

---
*Phase: 108-call-graph-analysis-visualization*
*Completed: 2026-03-06*
