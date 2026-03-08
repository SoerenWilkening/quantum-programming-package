---
phase: 107-call-graph-dag-foundation
plan: 02
subsystem: compile
tags: [call-graph, dag, compile-decorator, opt-parameter, rustworkx]

# Dependency graph
requires:
  - phase: 107-01
    provides: CallGraphDAG, DAGNode, builder stack in call_graph.py
provides:
  - opt parameter on @ql.compile (opt=1 builds DAG, opt=3 legacy)
  - call_graph property on CompiledFunc exposing DAG
  - CallGraphDAG export from quantum_language package
  - 11 integration tests covering DAG building with real circuits
affects: [108-merge-optimizer, 109-scheduler, 110-verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [top-level DAG push/pop in __call__, placeholder node update in _capture_inner, _call_inner refactor for try/finally]

key-files:
  created: []
  modified:
    - src/quantum_language/compile.py
    - src/quantum_language/__init__.py
    - tests/python/test_call_graph.py

key-decisions:
  - "DAG context managed via _call_inner refactor: __call__ handles push/pop in try/finally, _call_inner has the execution logic"
  - "Capture path uses placeholder node updated after block finalization for accurate qubit/gate data"
  - "Replay path records DAG node directly (no nesting since function body not re-executed)"
  - "opt parameter NOT included in cache key -- DAG building is observational only"

patterns-established:
  - "opt parameter pattern: opt=1 default builds DAG, opt=3 skips all DAG overhead"
  - "Top-level DAG detection: check current_dag_context() == None to determine if fresh DAG needed"

requirements-completed: [CAPI-01, CAPI-03, CAPI-04]

# Metrics
duration: 30min
completed: 2026-03-05
---

# Phase 107 Plan 02: Compile DAG Integration Summary

**Wired CallGraphDAG into @ql.compile via opt parameter with full backward compat and 43 passing tests**

## Performance

- **Duration:** 30 min
- **Started:** 2026-03-05T20:35:53Z
- **Completed:** 2026-03-05T21:05:57Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added opt parameter to compile() decorator (opt=1 builds DAG, opt=3 legacy behavior)
- Wired DAG context management into __call__ with proper push/pop lifecycle for nested call tracking
- Exported CallGraphDAG from quantum_language package for user-facing API
- 43 total tests passing (32 unit + 11 integration) with full backward compatibility

## Task Commits

Each task was committed atomically:

1. **Task 1: Add opt parameter and wire DAG building** - `19f33d3` (feat)
2. **Task 2: Integration tests for DAG building** - `906a067` (test)
3. **Task 3: Export CallGraphDAG from __init__.py** - `11213d7` (feat)

## Files Created/Modified
- `src/quantum_language/compile.py` - Added opt parameter, DAG context management in __call__/_call_inner/_capture_inner, call_graph property
- `src/quantum_language/__init__.py` - Added CallGraphDAG import and __all__ entry
- `tests/python/test_call_graph.py` - Added 11 integration tests for compile+DAG interaction

## Decisions Made
- Refactored __call__ into __call__ + _call_inner to cleanly wrap DAG try/finally around all execution paths
- Used placeholder node approach in _capture_inner: add empty node before function body, update with real data after capture completes
- Replay path records nodes directly in _call_inner since no nesting occurs (function body not re-executed)
- Parametric path also records DAG nodes for completeness

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed circuit() API calls in tests**
- **Found during:** Task 2 (integration tests)
- **Issue:** Plan used ql.circuit(4) but API takes no positional args
- **Fix:** Changed to ql.circuit() and qint(val, width=N)
- **Files modified:** tests/python/test_call_graph.py
- **Verification:** All 43 tests pass
- **Committed in:** 906a067 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test fixture fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CallGraphDAG fully integrated into compile decorator
- DAG available via .call_graph property after any @ql.compile(opt=1) call
- Ready for Phase 108 (merge optimizer) which will consume DAG parallel_groups

## Self-Check: PASSED

All created/modified files verified present. All 3 task commits verified in git log.

---
*Phase: 107-call-graph-dag-foundation*
*Completed: 2026-03-05*
