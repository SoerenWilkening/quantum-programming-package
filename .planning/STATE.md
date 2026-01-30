# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-30)

**Core value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.
**Current focus:** v1.4 OpenQASM Export & Verification

## Current Position

Phase: Phase 25 (C Backend OpenQASM Export)
Plan: 02 of 2 (in phase)
Status: Phase complete
Last activity: 2026-01-30 — Completed 25-02-PLAN.md

Progress: [██░░░░░░░░] 2%

## Performance Metrics

**Velocity:**
- Total plans completed: 82 (v1.0: 41, v1.1: 13, v1.2: 10, v1.3: 16, v1.4: 2)
- Average duration: ~8 min/plan
- Total execution time: ~10.8 hours

**By Milestone:**

| Milestone | Phases | Plans | Status |
|-----------|--------|-------|--------|
| v1.0 MVP | 1-10 | 41 | Complete (2026-01-27) |
| v1.1 QPU State | 11-15 | 13 | Complete (2026-01-28) |
| v1.2 Uncomputation | 16-20 | 10 | Complete (2026-01-28) |
| v1.3 Package & Array | 21-24 | 16 | Complete (2026-01-29) |
| v1.4 OpenQASM Export | 25-27 | 2/TBD | In progress (started 2026-01-30) |

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
| 22-01 | Flattened storage with shape metadata | Arrays store elements as 1D list with shape tuple - simplifies access and matches NumPy internal representation |
| 22-01 | Width inference using bit_length() with INTEGERSIZE floor | Auto-detect bit width from max value, always use at least INTEGERSIZE=8 bits - minimizes qubits while preventing over-narrow types |
| 22-01 | Virtual Sequence registration instead of inheritance | Cython extension types cannot inherit from Python ABCs - use Sequence.register(qarray) for protocol compliance |
| 22-02 | Single int on multi-dimensional array returns row view | NumPy compatibility - arr[0] on 2D array returns first row, not flattened element |
| 22-02 | View arrays created via qarray.__new__() | Manual cdef attribute initialization required for Cython extension types |
| 22-02 | Multi-dimensional indexing uses _multi_to_flat | Row-major index calculation converts (i,j) coordinates to flat index using strides |
| 22-03 | Keyword-only parameters for width/dtype/dim | NumPy-style API design using * to force keyword-only parameters - prevents positional argument confusion |
| 22-03 | Homogeneity enforcement for qarray | Arrays must contain only qint OR only qbool, not both - simplifies element access and dtype is array-level property |
| 22-03 | NumPy dtype.itemsize for width inference | Use dtype.itemsize * 8 (bytes to bits) for width calculation - direct mapping from NumPy types |
| 22-03 | dim/data mutual exclusivity | Specifying both raises ValueError - dimension-based creates zeros, data-based uses values (ambiguous semantics) |
| 22-04 | Iteration yields flattened elements in row-major order | NumPy compatibility and matches internal storage - consistent with __len__ returning flattened size |
| 22-04 | Repr format: ql.array<qint:8, shape=(3,)>[1, 2, 3] | Compact type info + data - shows width (crucial for circuit analysis), shape, and values for debugging |
| 22-04 | Truncation threshold 6 elements per dimension | NumPy-style first 3 and last 3 - prevents repr overflow while showing boundary values |
| 22-04 | Cython cast syntax for cdef attribute access | (<qint>elem).value accesses C-level attributes from Python-typed containers - required for _elements list |
| 22-05 | array() wrapper returns qarray objects | Complete transition from legacy list-based arrays to qarray class - provides shape metadata, indexing, and NumPy compatibility |
| 22-05 | qarray exported in __all__ | Enables type checking with isinstance(arr, ql.qarray) and type hints with ql.qarray |
| 22-05 | Tests verify types not values | qint objects are quantum variables - values only known after measurement, tests validate type correctness and behaviors |
| 23-01 | Use operator overloading (& \| ^) for reductions | Leverage existing qint/qbool operators instead of custom reduction logic - maintains consistency |
| 23-01 | Dual reduction algorithms (tree and linear) | Tree for O(log n) depth (default), linear for qubit-saving mode - different use cases prioritize speed vs space |
| 23-01 | Empty arrays raise ValueError | No sensible default for quantum reductions - match NumPy behavior |
| 23-01 | Single-element arrays return element directly | Optimize trivial case without reduction overhead |
| 23-02 | qbool reductions return qint | qbool inherits from qint, operators return parent type - maintains type system consistency |
| 23-02 | Module-level reduction functions shadow builtins | ql.all/any/parity shadow Python builtins but only in ql namespace - users call ql.all(arr) not bare all(arr) |
| 23-02 | No module-level sum() function | Avoids shadowing Python's built-in sum() - Python sum(arr) works via iteration + __radd__ |
| 24-01 | Use property accessors for cross-instance cdef attribute access | Cython extension types can't directly access each other's cdef attributes without type casting - use other.shape not other._shape |
| 24-01 | Cython type casting for _elements access | List comprehensions need other._elements access - requires cdef qarray other_arr then <qarray>other cast |
| 24-01 | Comparison operators set result dtype to qbool | Comparisons return boolean arrays per NumPy convention - pass result_dtype=qbool to set _dtype and _width=1 |
| 25-01 | Use %.17g precision for rotation angle export | Preserves full double precision while avoiding trailing zeros and exponential notation |
| 25-01 | Normalize angles to [0, 2π) before OpenQASM export | Ensures consistent output regardless of internal angle storage |
| 25-01 | Measurement syntax: 'c[i] = measure q[i];' | OpenQASM 3.0 assignment syntax more explicit than arrow syntax |
| 25-01 | Duplicate gate_get_control() as _get_control_qubit() | Avoid adding header dependencies while providing large_control access |
| 25-01 | Dynamic buffer: 512 + (gates * 100) bytes, doubles on overflow | 512 bytes for header, 100/gate handles ctrl(n) @ syntax |
| 25-02 | Delegate old circuit_to_opanqasm() to circuit_to_openqasm() | Backward compatibility while fixing all bugs via delegation pattern |
| 25-02 | circuit_to_openqasm() reuses circuit_to_qasm_string() | File export composes string export + file write - eliminates code duplication |
| 25-02 | File export calls string export then writes result | Single source of truth for QASM generation ensures consistency |

Additional decisions logged in PROJECT.md Key Decisions table.

### Pending Todos

None.

### Blockers/Concerns

**Known pre-existing issues:**
- Multiplication tests segfault at certain widths (C backend issue, tracked)
- Nested quantum conditionals require quantum-quantum AND implementation
- Some tests fail with MemoryError due to cumulative qubit allocation across test suite
- Circuit allocator errors in some test combinations
- Build system: pip install -e . fails with absolute path error in setup.py (code works, tests pass)

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
| 007 | Merge Backend/ and Execution/ into c_backend/ | 2026-01-29 | 729c57f | [007-merge-backend-and-execution-folders](./quick/007-merge-backend-and-execution-folders/) |
| 008 | Update milestone audit to mark resolved gaps | 2026-01-29 | 7bcde24 | [008-update-milestone-audit-resolved-gaps](./quick/008-update-milestone-audit-resolved-gaps/) |
| 009 | Compile package in-place and create demo | 2026-01-29 | 5f6e801 | [009-compile-the-package-inplace-and-create-a](./quick/009-compile-the-package-inplace-and-create-a/) |

## Session Continuity

Last session: 2026-01-30 13:40:47 UTC
Stopped at: Completed 25-02-PLAN.md
Resume file: None

---
*State updated: 2026-01-30 after plan 25-02 completion*
