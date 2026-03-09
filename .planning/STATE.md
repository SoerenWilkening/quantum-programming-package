---
gsd_state_version: 1.0
milestone: v8.0
milestone_name: Quantum Chess Walk Rewrite
status: completed
stopped_at: Completed 116-02-PLAN.md
last_updated: "2026-03-09T13:36:22.580Z"
last_activity: 2026-03-09 -- Completed 116-02 (demo rewrite and tests)
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-08)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v8.0 Quantum Chess Walk Rewrite -- Phase 116

## Current Position

Phase: 116 of 116 (Walk Integration & Demo)
Plan: 2 of 2 complete
Status: complete
Last activity: 2026-03-09 -- Completed 116-02 (demo rewrite and tests)

Progress: [##########] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 287 (v1.0-v7.0)
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
| v7.0 Compile Infrastructure | 107-111 | 10 | Complete (2026-03-08) |
| v8.0 Chess Walk Rewrite | 112-116 | TBD | Ready to plan |
| Phase 113 P01 | 4min | 1 tasks | 2 files |
| Phase 113 P03 | 7min | 2 tasks | 3 files |
| Phase 114 P01 | 15min | 1 tasks | 2 files |
| Phase 114 P02 | 8min | 1 tasks | 2 files |
| Phase 116 P01 | 4min | 2 tasks | 2 files |
| Phase 116 P02 | 2min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

Recent decisions affecting current work:
- Chess walk must evaluate move legality in superposition (not classical pre-filtering)
- Knights + Kings move types for v8.0 (non-sliding pieces only)
- All predicates must use standard ql constructs -- no raw gate emission for application logic
- Diffusion must use arithmetic counting circuit (not O(2^d_max) enumeration)
- Compile infrastructure qubit_set operations to use numpy
- DAGNode dual-storage: frozenset qubit_set for API compat, numpy _qubit_array for fast overlap
- Bitmask stays Python int (>64 qubit arbitrary precision), only overlap uses numpy
- Numpy qubit_set construction shows negligible perf difference at current sizes, justified by architectural consistency
- _build_qubit_set_numpy centralizes all qubit set construction in compile.py
- No edge-of-board filtering in move table -- quantum predicate handles legality
- 8 entries per piece in move table (knights and kings both have 8 offsets)
- [Phase 113]: No edge-of-board filtering in move table -- quantum predicate handles legality
- [Phase 113]: counting_diffusion_core extracted as shared module-level function in walk.py
- [Phase 113]: counting_diffusion_core extracted as shared module-level function in walk.py for chess_walk.py integration
- [Phase 114]: Used .adjoint() instead of .inverse() for ancilla-free predicate reversal
- [Phase 114]: Nested with qbool raises NotImplementedError; use & operator for Toffoli AND instead
- [Phase 114]: Per-source friendly_flag ancilla avoids & operator ancilla-reuse interference in loops
- [Phase 115]: Per-position attack_flag accumulation instead of per-attacker enemy_flag to avoid & operator ancilla overflow on large attack tables
- [Phase 115]: Nested @ql.compile calls work for sub-predicate composition -- no need to inline sub-predicate logic
- [Phase 115]: Combined 2x2 predicate uses 34 qubits -- circuit-build-only testing + separate AND composition verification
- [Phase 116]: One combined predicate per move table entry, not per level (piece_type varies within white levels)
- [Phase 116]: Offset-based oracle enumerates all 64 source squares per branch value with classical off-board filtering
- [Phase 116]: walk_step uses inline @ql_compile with explicit args, no closure/mutable-dict pattern
- [Phase 116]: MAX_DEPTH=2 for depth-2 walk (white move + black response)

### Blockers/Concerns

**Carry forward (architectural):**
- 14-15 pre-existing test failures in test_compile.py -- unrelated to v8.0
- Diffusion combinatorial explosion is a hard blocker for large branching (Phase 113 addresses)
- MAXLAYERINSEQUENCE (300K) may be exceeded by chess circuits -- assess in Phase 113
- Nested `with qbool:` limitation requires flat Toffoli-AND predicate design

## Session Continuity

Last session: 2026-03-09T13:33:40.863Z
Stopped at: Completed 116-02-PLAN.md
Resume file: None
Resume action: v8.0 milestone complete

---
*State updated: 2026-03-08 -- 113-03 complete (chess_walk.py shared counting diffusion)*
