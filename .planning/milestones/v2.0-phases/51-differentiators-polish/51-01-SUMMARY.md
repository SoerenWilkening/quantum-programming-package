# Phase 51 Plan 01: Inverse Generation, Debug Mode & Nesting Depth Summary

**One-liner:** Added `.inverse()` adjoint replay, `debug=True` stderr introspection, and `_capture_depth` nesting limit to `@ql.compile`

## What Was Done

### Task 1: Inverse Generation and _InverseCompiledFunc
- Added `_NON_REVERSIBLE` constant (measurement gates cannot be inverted)
- Added `_adjoint_gate()` helper: negates rotation angles, raises `ValueError` on measurement
- Added `_inverse_gate_list()`: reverses gate order and adjoints each gate
- Added `_InverseCompiledFunc` class: lightweight wrapper with own inverted block cache
- Added `.inverse()` method to `CompiledFunc` (lazy cached)
- `.inverse().inverse()` returns the original `CompiledFunc` (round-trip correctness)
- `@ql.compile(inverse=True)` eagerly creates the inverse wrapper at decoration time
- Commit: `f102039`

### Task 2: Debug Mode and Nesting Depth Limit
- Added `debug=True` parameter to `CompiledFunc.__init__` and `compile()` decorator
- When `debug=True`, each call prints to stderr: `[ql.compile] func_name: HIT/MISS | original=N -> optimized=M gates | cache_entries=K`
- Added `.stats` property: returns dict with `cache_hit`, `original_gate_count`, `optimized_gate_count`, `cache_size`, `total_hits`, `total_misses` when `debug=True`; returns `None` when `debug=False` (zero overhead)
- Added module-level `_capture_depth` counter and `_MAX_CAPTURE_DEPTH = 16`
- `_capture()` raises `RecursionError` when nesting depth exceeded
- `_capture_depth` reset to 0 in `_clear_all_caches()` on circuit reset
- Commit: `89cdf5a`

## Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | `_InverseCompiledFunc` does NOT inherit from `CompiledFunc` | Lightweight wrapper pattern; avoids complexity of full compilation machinery |
| 2 | Inverse blocks maintain own cache (`_inv_cache`) separate from original | Prevents side effects on original's cache; clean separation of concerns |
| 3 | Debug stats only tracked when `debug=True` | Zero overhead for production use |
| 4 | Nesting depth implemented via global counter with try/finally | Simple, thread-unsafe but adequate for single-threaded quantum simulation |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Re-added `import sys` after ruff removal**
- **Found during:** Task 2
- **Issue:** `import sys` added in Task 1 was removed by ruff linter (unused at that point)
- **Fix:** Re-added `import sys` in Task 2 when it became used by debug mode
- **Files modified:** `src/quantum_language/compile.py`

## Verification Results

- All 43 existing compile tests pass (no regressions)
- `_adjoint_gate` correctly negates rotation angles and raises on measurement
- `_inverse_gate_list` correctly reverses and adjoints gate sequences
- `.inverse()` returns `_InverseCompiledFunc` that replays adjoint gates
- `.inverse().inverse()` returns original `CompiledFunc`
- `@ql.compile(inverse=True)` eagerly creates inverse wrapper
- `debug=True` prints to stderr and populates `.stats` dict
- `.stats` returns `None` when `debug=False`
- `_MAX_CAPTURE_DEPTH = 16` exists at module level

## Key Files

### Modified
- `src/quantum_language/compile.py` -- inverse generation, debug mode, nesting depth limit

## Duration

~4 minutes
