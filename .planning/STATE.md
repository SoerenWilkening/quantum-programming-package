# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-29)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.3 Package Structure & ql.array - Phase 21 (Package Restructuring)

## Current Position

Phase: 21 of 24 (Package Restructuring)
Plan: 5 of 5 complete (21-01, 21-02, 21-03, 21-04, 21-05 done)
Status: Phase complete
Last activity: 2026-01-29 — Completed 21-05-PLAN.md (Test import migration)

Progress: [███.......] 11%

## Performance Metrics

**Velocity:**
- Total plans completed: 67 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 3)
- Average duration: ~6 min/plan
- Total execution time: ~6.7 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | TBD | In progress |

## Accumulated Context

### Decisions

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 21-01 | Accessor functions for global state | Cython cdef module variables cannot be cimported across modules |
| 21-01 | array() requires explicit dtype in _core | Function references qint/qbool which don't exist until full package import |
| 21-01 | Empty __init__.pxd for package cimport | Enables `from quantum_language cimport ...` syntax |
| 21-02 | Keep all operations in qint.pyx | RESEARCH.md permits large files for cohesion; splitting would break logical grouping |
| 21-02 | Use accessor functions for global state | Clean cross-module state access without cdef variable duplication |
| 21-03 | Re-export pattern for state subpackage | Simpler than separate qpu.pyx/uncompute.pyx - avoids cdef global state duplication |
| 21-03 | array() wrapper in __init__.py | Injects default dtype=qint - avoids circular import between _core and qint |
| 21-03 | Dual access pattern for state functions | Both ql.circuit_stats() and ql.state.circuit_stats() work - user preference |
| 21-04 | Include "." in include_dirs | Enables cimport to find .pxd files in package structure |
| 21-04 | Legacy fallback in setup.py | Smooth transition while Wave 2 completes - auto-switches when src/ exists |
| 21-04 | Package data includes .pxd files | Enables external projects to cimport quantum_language modules |
| 21-05 | pytest.ini pythonpath = src | Centralized PYTHONPATH config for src-layout packages - cleaner than sys.path in tests |
| 21-05 | Export AVAILABLE_PASSES from __init__.py | Required for circuit.optimize() API - users need pass names |

Additional decisions logged in PROJECT.md Key Decisions table.

### Pending Todos

None.

### Blockers/Concerns

**Known pre-existing issues:**
- Multiplication tests segfault at certain widths (C backend issue, tracked)
- Nested quantum conditionals require quantum-quantum AND implementation
- Some tests fail with MemoryError due to cumulative qubit allocation across test suite
- Circuit allocator errors in some test combinations

**Known limitations (acceptable by design):**
- qint_mod * qint_mod raises NotImplementedError
- apply_merge() placeholder for phase rotation merging

## Session Continuity

Last session: 2026-01-29
Stopped at: Completed 21-05-PLAN.md (Test import migration) - Phase 21 complete
Resume file: None

---
*State updated: 2026-01-29 after 21-05 execution*
