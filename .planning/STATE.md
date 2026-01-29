# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-29)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.3 Package Structure & ql.array - Phase 22 (Array Class Foundation)

## Current Position

Phase: 21 of 24 (Package Restructuring) — COMPLETE
Plan: 7/7 complete (all plans done)
Status: Phase 21 verified and complete
Last activity: 2026-01-29 — Completed quick task 006 (relocated setup.py, removed python-backend/)

Progress: [██████....] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 69 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 5 → Phase 21 complete with 7 plans)
- Average duration: ~6 min/plan
- Total execution time: ~7.1 hours

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
| 21-06 | Extract methods to .pxi include files | Cython include files allow splitting cdef class across files while maintaining single compilation unit |
| 21-06 | Preserve exact implementations in .pxi | Complete method extraction with docstrings and internal calls - no imports or class declarations |
| 21-07 | Cython include pattern not viable for cdef classes | Discovered Cython 3.x limitation: include directives not supported inside cdef class definitions |
| 21-07 | Keep qint.pyx as single file | Accept ~2400 lines for cohesion - Cython include pattern proved incompatible with cdef classes |

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
- Cython include directives not supported for cdef class method injection (Cython 3.x design constraint)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 004 | Verify Cython include limitation for cdef classes | 2026-01-29 | 00a5b75 | [004-consolidate-qint-pxi](./quick/004-consolidate-qint-pxi-includes-to-remove-/) |
| 005 | Remove legacy monolithic source files | 2026-01-29 | 7baa00f | [005-remove-old-python-code](./quick/005-remove-old-python-code-if-completely-cov/) |
| 006 | Relocate setup.py to root, remove python-backend/ | 2026-01-29 | 74b3775 | [006-relocate-setup-py-remove-python-backend-](./quick/006-relocate-setup-py-remove-python-backend-/) |

## Session Continuity

Last session: 2026-01-29
Stopped at: Completed quick task 006 - relocated setup.py, removed python-backend/
Resume file: None

---
*State updated: 2026-01-29 after Phase 21 completion*
