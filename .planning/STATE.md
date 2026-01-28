# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-28)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** Phase 20 in progress — Modes and Control

## Current Position

Phase: 20 of 20 (Modes and Control)
Plan: 1 of 2 in current phase (complete)
Status: Phase 20 in progress
Last activity: 2026-01-28 — Completed 20-01-PLAN.md (option API and mode-aware uncomputation)

Progress: [█████████░] 96% (phases 1-19 complete, phase 20 plan 1/2 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 61 (v1.0: 41, v1.1: 13, v1.2: 7)
- Average duration: ~6 min/plan
- Total execution time: ~6.1 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 7/8 | In progress |

**Recent Trend:**
- v1.1: 13 plans in 1 day (accelerated delivery)
- v1.2 Phase 16: 2 plans in 15 min total (infrastructure + tests)
- v1.2 Phase 17: 1 plan in 11 min (C reverse gate generation)
- v1.2 Phase 18: 2 plans in 25 min total (core infrastructure + integration)
- v1.2 Phase 19: 1 plan in 9 min (context manager integration)
- v1.2 Phase 20-01: 1 plan in 5.5 min (option API and mode-aware uncomputation)

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v1.2 work:

- v1.2 Phase 20-01: Mode captured at creation time — prevents retroactive mode changes, each qbool has immutable behavior
- v1.2 Phase 20-01: Eager mode immediate uncomputation — minimizes peak qubit count by freeing on GC regardless of scope
- v1.2 Phase 20-01: Lazy mode scope-based uncomputation — minimizes gates by keeping intermediates alive within scope
- v1.2 Phase 20-01: _uncompute_mode made public — enables testing and debugging access to mode flag
- v1.2 Phase 19-01: Uncompute before restore — uncomputation happens BEFORE restoring control state for quantum correctness
- v1.2 Phase 19-01: LIFO order via _creation_order — sort scope_qbools by _creation_order descending
- v1.2 Phase 19-01: Skip already-uncomputed in __exit__ — allows early explicit uncompute (though refcount prevents it)
- v1.2 Phase 19-01: Condition survives own block — not registered in scope it controls (lower creation_scope)
- v1.2 Phase 19-01: Registration constraints — only register when scope_stack non-empty, scope > 0, creation_scope matches
- v1.2 Phase 18-02: Refcount threshold of 2 (self + getrefcount) for explicit uncompute validation
- v1.2 Phase 18-02: Guards added to all 11 quantum operations for defense in depth
- v1.2 Phase 18-01: Layer tracking placement — start_layer captured before operation, end_layer before return
- v1.2 Phase 18-01: LIFO cascade order — dependencies sorted by _creation_order descending for correct reversal
- v1.2 Phase 18-01: Error handling in __del__ — suppress exceptions, print warnings (Python best practice)
- v1.2 Phase 17-01: Empty range handling — start >= end returns silently (no-op, correct behavior)
- v1.2 Phase 17-01: Append vs replace — reversed gates appended to circuit (not replaced)
- v1.2 Phase 17-01: Layer tracking — exposed circuit_s.used_layer to Python for instruction boundaries
- v1.2 Phase 16-02: Test file location decision — replaced tic-tac-toe example in python-backend/test.py with comprehensive test suite
- v1.2 Phase 16-01: Weak references for dependency storage — prevents circular reference memory leaks
- v1.2 Phase 16-01: Creation order cycle prevention — assert parent._creation_order < self._creation_order at add-time
- v1.2 Phase 16-01: Track only quantum operands — classical int operands don't need uncomputation tracking
- v1.2 Phase 16-01: Unidirectional child→parent tracking — defer bidirectional to Phase 20 if needed
- v1.1: Stateless C backend — enables Python-level dependency tracking (v1.2 foundation)
- v1.0: Circuit compilation model — uncomputation appends reverse gates to circuit
- v1.0: Centralized qubit allocator — uncomputation integrates with existing ownership tracking

### Pending Todos

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 002 | Refactor quantum_language.pyx into smaller .pxi files | 2026-01-28 | 7178414 | [002-refactor-quantum-language-pyx-and-the-px](./quick/002-refactor-quantum-language-pyx-and-the-px/) |
| 003 | Revisit refactoring: consolidate operations, extract utility methods and circuit class | 2026-01-28 | f5f5f16 | [003-revisit-refactoring-quantum-language-pyx](./quick/003-revisit-refactoring-quantum-language-pyx/) |

### Blockers/Concerns

**From Phase 19 execution:**
- Nested `with` statements require quantum-quantum AND operation (NotImplementedError at line 809)
- This affects future quantum control flow but doesn't block Phase 20
- Single-level contexts work correctly, nested AND can be added separately

**Known pre-existing issues:**
- Multiplication tests segfault at certain widths (C backend issue, tracked)
- Nested quantum conditionals require quantum-quantum AND implementation

**Known limitations (acceptable by design):**
- qint_mod * qint_mod raises NotImplementedError
- apply_merge() placeholder for phase rotation merging
- Explicit uncompute inside `with` block fails refcount check (scope_stack reference) — use scope-based cleanup instead

## Session Continuity

Last session: 2026-01-28
Stopped at: Completed 20-01-PLAN.md (option API and mode-aware uncomputation)
Resume file: None (Phase 20 plan 1 complete, plan 2 pending)

---

## v1.2 Milestone Context

**Goal:** Automatically uncompute intermediate qubits when their lifetime ends

**Phases:**
- Phase 16: Dependency tracking infrastructure (4 requirements) — COMPLETE
- Phase 17: C reverse gate generation (2 requirements) — COMPLETE
- Phase 18: Basic uncomputation integration (3 requirements) — COMPLETE
- Phase 19: Context manager integration for `with` (2 requirements) — COMPLETE
- Phase 20: Modes and user control (6 requirements) — IN PROGRESS (1/2 plans complete)

**Research completed:** 2026-01-28 (HIGH confidence, Python weakref + C adjoint pattern validated)

**Phase 16 completed:** 2026-01-28 (2 plans: infrastructure + test suite)
**Phase 17 completed:** 2026-01-28 (1 plan: C reverse gate generation)
**Phase 18 completed:** 2026-01-28 (2 plans: core infrastructure + integration/tests)
**Phase 19 completed:** 2026-01-28 (1 plan: context manager integration)
**Phase 20-01 completed:** 2026-01-28 (option API and mode-aware uncomputation)

**Next action:** Execute Phase 20-02 for .keep() and .uncompute() enhancements
