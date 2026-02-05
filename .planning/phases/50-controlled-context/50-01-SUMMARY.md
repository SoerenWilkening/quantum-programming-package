# Phase 50 Plan 01: Controlled Context Support Summary

**One-liner:** Controlled variant derivation, cache key extension, and control qubit remapping for compiled functions inside `with qbool:` blocks.

## Results

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Add controlled context detection, cache key extension, and controlled variant derivation | 43f2046 | Done |

## What Was Done

### Controlled Context Detection
- `CompiledFunc.__call__()` now calls `_get_controlled()` at entry to detect whether the function is being called inside a `with qbool:` block.
- The control count (0 or 1) is included in every cache key, ensuring uncontrolled and controlled variants never collide.

### Cache Key Extension
- Default cache key changed from `(classical_args, widths)` to `(classical_args, widths, control_count)`.
- Custom `key` functions are wrapped: `(user_key_result, control_count)` to automatically include control state.

### Eager Compilation of Both Variants
- On first call (cache miss), `_capture_and_cache_both()` captures the uncontrolled variant, then derives the controlled variant using `_derive_controlled_block()`.
- Both variants are cached immediately, so subsequent calls in either context hit the cache.
- If first call is inside a `with` block, controlled state is temporarily disabled for capture, then restored.

### Controlled Variant Derivation
- `_derive_controlled_gates()` transforms each gate by incrementing `num_controls` by 1 and prepending the control virtual qubit index to `controls`.
- `_derive_controlled_block()` creates a new `CompiledBlock` with `total_virtual_qubits + 1` and `control_virtual_idx` set to the placeholder index.
- Fallback: if derivation fails (e.g., future gate types), silently re-captures in controlled mode.

### Control Qubit Remapping in Replay
- `_replay()` checks `block.control_virtual_idx` during ancilla allocation.
- If set, maps the control virtual index to `_get_control_bool().qubits[63]` (the actual control qubit) instead of allocating a fresh ancilla.

### Test Updates
- Two tests (`test_replay_uses_optimized_gates`, `test_uncomputation_replay_uses_optimized_sequence`) updated to check per-block gate counts instead of cross-variant sum from `optimized_gates` property.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertions for optimized_gates property**
- **Found during:** Task 1 verification
- **Issue:** `optimized_gates` property sums gate counts across ALL cache entries. With 2 entries (uncontrolled + controlled), the total doubled, breaking assertions that compared replay gate count to `optimized_gates`.
- **Fix:** Changed tests to check against the specific uncontrolled block's gate count via `add_one._cache[unctrl_key].gates`.
- **Files modified:** `tests/test_compile.py`
- **Commit:** 43f2046

## Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | First call inside `with` block executes uncontrolled body | Gates already emitted to circuit cannot be retroactively controlled; accepted trade-off documented in docstring |
| 2 | Control virtual index = uncontrolled total_virtual_qubits | Places control qubit at the end of virtual index space, avoiding collision with parameter and ancilla indices |
| 3 | Save/restore `_list_of_controls` alongside `_controlled` and `_control_bool` | Prevents corruption of nested `with` block state during temporary uncontrolled capture |

## Verification

- `python3 -c "import quantum_language as ql"` -- imports cleanly
- `pytest tests/test_compile.py -x -q` -- 36/36 tests pass
- Manual verification: first call creates 2 cache entries (uncontrolled key `((), (4,), 0)` and controlled key `((), (4,), 1)`) with correct gate counts and `control_virtual_idx`

## Key Files

### Created
None

### Modified
- `src/quantum_language/compile.py` -- controlled context detection, cache key extension, `_derive_controlled_gates()`, `_derive_controlled_block()`, `_capture_and_cache_both()`, `_replay()` control qubit remapping
- `tests/test_compile.py` -- updated 2 test assertions for per-block gate counts

## Duration

~3 minutes (16:03 - 16:06 UTC)

---
*Phase: 50-controlled-context, Plan: 01, Completed: 2026-02-04*
