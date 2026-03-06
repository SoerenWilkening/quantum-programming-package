---
gsd_state_version: 1.0
milestone: v7.0
milestone_name: Compile Infrastructure
status: in-progress
stopped_at: Completed 109-02 merge pipeline wiring
last_updated: "2026-03-06T21:10:53Z"
last_activity: 2026-03-06 -- Completed 109-02 opt=2 merge pipeline wiring (29 merge tests)
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-05)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v7.0 Compile Infrastructure -- Phase 107 ready to plan

## Current Position

Phase: 109 of 110 (Selective Sequence Merging)
Plan: 2 of 3
Status: 109-02 Complete
Last activity: 2026-03-06 -- Completed 109-02 opt=2 merge pipeline wiring (29 merge tests, 115 related tests)

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 277 (v1.0-v6.1)
- Average duration: ~13 min/plan
- Total execution time: ~45.7 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0-v2.3 | 1-64 | 166 | Complete |
| v3.0 Fault-Tolerant | 65-75 | 35 | Complete (2026-02-18) |
| v4.0 Grover's Algorithm | 76-81 | 18 | Complete (2026-02-22) |
| v4.1 Quality & Efficiency | 82-89 | 21 | Complete (2026-02-24) |
| v5.0 Advanced Arithmetic | 90-96 | 19 | Shipped (2026-02-26) |
| v6.0 Quantum Walk | 97-102 | 11 | Shipped (2026-03-03) |
| v6.1 Quantum Chess Demo | 103-106 | 8 | Complete (2026-03-05) |
| v7.0 Compile Infrastructure | 107-110 | TBD | Ready to plan |
| Phase 108 P01 | 4min | 2 tasks | 3 files |
| Phase 108 P02 | 4min | 2 tasks | 2 files |
| Phase 109 P01 | 3min | 2 tasks | 3 files |
| Phase 109 P02 | 4min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

Recent decisions affecting current work:
- Call graph DAG lives in Python (compile-time structure, not hot path)
- opt_flag=1 builds DAG alongside normal expansion (no C backend changes)
- rustworkx PyDAG for graph primitives, NumPy bitmasks for qubit overlap
- Sparse circuit arrays deferred to v8.0 (independent C-level track)
- DAGNode uses __slots__ + pre-computed np.uint64 bitmask for fast overlap
- build_overlap_edges skips parent-child call edges to avoid double-counting
- parallel_groups uses separate undirected PyGraph for clean component detection
- __call__ refactored into __call__ + _call_inner for clean DAG try/finally
- Capture path uses placeholder node updated after block finalization
- opt parameter NOT in cache key (DAG building is observational only)
- ASAP scheduling for depth: per-qubit occupancy tracking, each gate occupies max(occupied qubits)+1
- Dual T-count formula: direct T/TDG count preferred, 7*CCX fallback when no T gates
- Critical-path depth in aggregate: sum of per-group max depths from parallel_groups()
- DOT cluster subgraphs only rendered when >1 parallel group
- Fixed-width report columns: Name 20 chars left-aligned, numeric 8 chars right-aligned
- merge_groups reuses parallel_groups pattern with threshold filter and singleton exclusion
- _merge_and_optimize wraps _optimize_gate_list with virtual-to-physical qubit remapping
- parametric+opt=2 guard raises ValueError immediately at construction time
- DAG node _block_ref/_v2r_ref for direct block access during merge (avoids cache_key placeholder issue)
- _apply_merge runs after build_overlap_edges in __call__ finally block when opt==2
- Merged blocks keyed by frozenset of node indices for O(1) group lookup

### Blockers/Concerns

**Carry forward (architectural):**
- 14-15 pre-existing test failures in test_compile.py -- unrelated to v7.0
- Phase kickback: control qubits are NOT read-only (must track all qubits as dependencies)
- Merge can silently corrupt quantum states -- dedicated verification phase (110) addresses this

## Session Continuity

Last session: 2026-03-06T21:10:53Z
Stopped at: Completed 109-02 merge pipeline wiring
Resume file: .planning/phases/109-selective-sequence-merging/109-02-SUMMARY.md
Resume action: Execute 109-03

---
*State updated: 2026-03-06 -- 109-02 merge pipeline wiring complete (29 merge tests, 115 related tests)*
