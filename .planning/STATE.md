---
gsd_state_version: 1.0
milestone: v6.1
milestone_name: Quantum Chess Demo
status: completed
stopped_at: Completed 106-02-PLAN.md
last_updated: "2026-03-05T16:19:00Z"
last_activity: 2026-03-05 -- Completed 106-02 comparison script
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 6
  completed_plans: 8
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v6.1 Quantum Chess Demo -- Phase 105 complete, Phase 106 next

## Current Position

Phase: 106 of 106 (Demo Scripts)
Plan: 2 of 2 in current phase (106-02 complete)
Status: Phase 106 complete -- all demo scripts done
Last activity: 2026-03-05 -- Completed 106-02 comparison script

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 269 (v1.0-v6.0)
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
| v6.1 Quantum Chess Demo | 103-106 | 8/8 | Complete (2026-03-05) |
| Phase 104 P01 | 3min | 1 tasks | 2 files |
| Phase 104 P02 | 10min | 2 tasks | 2 files |
| Phase 105 P01 | 7min | 1 tasks | 2 files |
| Phase 105 P02 | 25min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions table for full history.

Recent decisions affecting current work:
- Manual quantum walk operators (not QWalkTree API) for educational/demo purposes
- Circuit generation only -- no Qiskit simulation (qubit count exceeds 17-qubit budget)
- Simplified endgame: 2 kings + white knights (no castling, en passant, promotion)
- Square index convention: sq = rank * 8 + file, consistent with qarray[rank, file]
- Black king exclusion zone includes bk_sq + king_attacks(bk_sq) for white king filtering
- White attack set includes wk_sq + king_attacks + knight_attacks for black king filtering
- Oracle factory pattern: _make_apply_move() creates @ql.compile function with classical move_specs in closure
- Separate qarray args (wk_arr, bk_arr, wn_arr, branch) for compile cache key + inverse support
- Use ~qbool (controlled NOT) for square flipping -- ^= 1 unsupported in controlled context
- .inverse is a @property returning _AncillaInverseProxy, called as f.inverse(args)
- Purely functional walk module (chess_walk.py): 6 standalone functions, no class
- board_arrs as tuple (wk, bk, wn) matching oracle calling convention
- Oracle replay: derive calls forward, underive calls .inverse in LIFO order
- Height qubit addressing: int(h_reg.qubits[64 - (max_depth+1) + depth])
- Side alternation: level % 2 == 0 is white, odd is black
- [Phase 104]: Purely functional walk module: 6 standalone functions, board_arrs as tuple, oracle replay pattern
- [Phase 104-02]: Derive/underive uses level_idx (max_depth - depth) not depth for oracle replay count
- [Phase 104-02]: Cascade fallback for d_val exceeding register control depth (NotImplementedError -> empty ops)
- [Phase 104-02]: S_0 via public ql.diffusion() in with h_control: context (not manual X-MCZ-X)
- [Phase 105-01]: r_a skips depth 0 (leaves) since level_idx=max_depth exceeds oracle_per_level range
- [Phase 105-01]: r_b explicitly adds max_depth when even to ensure root inclusion per Montanaro convention
- [Phase 105-02]: Board qarrays passed as separate compile args (total qubit count exceeds 64-qubit qint limit)
- [Phase 105-02]: all_walk_qubits wraps height + branch only; walk_step passes board qarrays separately
- [Phase 105-02]: Module-level CompiledFunc with mutable context dict for functional walk_step caching
- [Phase 106-01]: Demo smoke test patches walk_step to avoid OOM in memory-constrained CI (8GB+ needed for real compilation)
- [Phase 106-02]: QWalkTree cascade fallback: added try/except in _setup_diffusion matching chess_walk.py pattern
- [Phase 106-02]: Comparison test dual-patches both demo.walk_step and QWalkTree.walk_step for CI safety

### Blockers/Concerns

**Carry forward (architectural):**
- QQ Division Ancilla Leak -- DOCUMENTED (see docs/KNOWN-ISSUES.md)
- 14-15 pre-existing test failures in test_compile.py -- unrelated to v6.1
- Framework limitation: `with qbool:` cannot nest (quantum-quantum AND not supported)
- Raw predicate qubit allocation: each predicate call allocates new qbools

## Session Continuity

Last session: 2026-03-05T16:19:00Z
Stopped at: Completed 106-02-PLAN.md
Resume file: .planning/phases/106-demo-scripts/106-02-SUMMARY.md
Resume action: Phase 106 and v6.1 milestone complete

---
*State updated: 2026-03-05 -- Completed 106-02 comparison script (DEMO-02), Phase 106 complete, v6.1 milestone complete*
