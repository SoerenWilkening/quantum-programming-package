# Phase 48 Plan 02: Compile Decorator Implementation Summary

**Completed:** 2026-02-04
**Duration:** ~10 min
**Status:** Complete

## One-Liner

Python-level `@ql.compile` decorator with gate capture on first call, virtual qubit mapping, LRU cache, and replay with qubit remapping on subsequent calls.

## What Was Done

### Task 1: Create compile.py with CompiledFunc, CompiledBlock, and virtual qubit mapping
- Created `compile.py` (~450 lines) with full capture-replay system
- `compile()` function supports `@ql.compile`, `@ql.compile()`, `@ql.compile(max_cache=N)` forms
- `CompiledFunc` wraps decorated functions: classifies args, builds cache key, dispatches to capture or replay
- `CompiledBlock` stores virtualised gate sequences with param ranges, ancilla count, return info
- `_build_virtual_mapping()` maps real qubit indices to virtual namespace (params first, then ancillas)
- `_build_return_qint()` constructs usable qint from replay-mapped qubits with ownership metadata
- In-place modification detection: `return_is_param_index` avoids unnecessary qint construction
- Cache invalidation: weak reference registry, hook fires on `ql.circuit()` via `_register_cache_clear_hook`
- Layer floor save/restore during replay prevents gate reordering
- **Commit:** `c15ad69`

### Task 2: Wire compile into __init__.py and create comprehensive test suite
- Added `from .compile import compile` and `'compile'` to `__all__` in `__init__.py`
- Made `qubits`, `allocated_qubits`, `allocated_start` public in `qint.pxd` (needed for Python-level access)
- Rebuilt Cython extensions with public attribute changes
- Created `test_compile.py` with 22 tests covering all 5 success criteria:
  - SC1: First call matches undecorated gate count (2 tests)
  - SC2: Replay onto new qubits without re-execution (3 tests)
  - SC3: Return value usable in subsequent operations (3 tests)
  - SC4: Different widths/classical args trigger re-capture (3 tests)
  - SC5: `ql.circuit()` invalidates compilation cache (2 tests)
  - Additional: decorator forms, cache eviction, clear_cache, in-place modification, exception handling, metadata preservation (9 tests)
- All 22 tests pass; 100 tests pass across draw_data, copy, and compile suites (no regressions)
- **Commit:** `eb8da4d`

## Files Modified

| File | Changes |
|------|---------|
| `src/quantum_language/compile.py` | NEW: Complete compile decorator module (~450 LOC) |
| `src/quantum_language/__init__.py` | Add `compile` import and `__all__` entry |
| `src/quantum_language/qint.pxd` | Make `qubits`, `allocated_qubits`, `allocated_start` public |
| `tests/test_compile.py` | NEW: 22 tests covering all success criteria (~400 LOC) |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Make qint.qubits public via `cdef public` | compile.py needs Python-level access to qubit indices for virtual mapping; cleanest approach vs adding accessor methods |
| Use set comprehension for replay target checking | Ruff linter requires comprehension over `set(generator)` pattern |
| In-place detection via qubit index overlap | Compare return value's qubit indices with each parameter's; if match found, return caller's qint directly on replay |
| OrderedDict for LRU cache with move_to_end | Standard Python pattern; cache hits move entry to end, eviction removes oldest (FIFO end) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Made qint attributes public for Python access**
- **Found during:** Task 1 verification
- **Issue:** `qubits`, `allocated_qubits`, `allocated_start` are `cdef object` in qint.pxd -- not accessible from pure Python code (compile.py)
- **Fix:** Changed to `cdef public object qubits`, `cdef public bint allocated_qubits`, `cdef public unsigned int allocated_start`
- **Files modified:** `src/quantum_language/qint.pxd`
- **Commit:** `eb8da4d` (included in Task 2 commit)

**2. [Rule 2 - Missing Critical] Removed unused import (inspect)**
- **Found during:** Linter pre-commit hook
- **Issue:** Plan specified `import inspect` for signature binding, but implementation uses simpler arg classification
- **Fix:** Removed unused import (ruff auto-fixed)
- **Files modified:** `src/quantum_language/compile.py`

## Verification Results

- All 22 compile tests pass
- 100 tests pass across test_compile, test_draw_data, test_copy (no regressions)
- End-to-end smoke test verified: capture on first call, replay on second call, cache invalidation on circuit reset
- Gate counts match between capture and replay
- Different widths produce different gate counts and separate cache entries
- Replay return values are usable in subsequent quantum operations

## Next Phase Readiness

Phase 48 is complete. All success criteria are met:
1. First call produces same circuit as undecorated version
2. Second call replays gates onto new qubits without re-executing function body
3. Returned qint is usable in subsequent quantum operations
4. Different classical params or qint widths trigger re-capture
5. `ql.circuit()` invalidates all compilation caches

Phase 49 (Optimization & Uncomputation) can proceed. Key considerations:
- `@ql.compile` functions currently work with `qubit_saving_mode=False` (default)
- Eager uncomputation interaction needs investigation in Phase 49
- Controlled context requires re-capture (not post-hoc control), deferred to Phase 50
