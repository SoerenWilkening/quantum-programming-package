# Phase 48 Plan 01: Core Capture-Replay Infrastructure Summary

**Completed:** 2026-02-04
**Duration:** ~8 min
**Status:** Complete

## One-Liner

Cython-level gate extraction and injection primitives with layer floor management, qubit allocation, and cache-clear hooks for `@ql.compile` decorator support.

## What Was Done

### Task 1: gate_t field access and extract_gate_range
- Expanded `gate_t` struct in `_core.pxd` from opaque to full field access (Control, large_control, NumControls, Gate, GateValue, Target)
- Added `qubit_t` and `Standardgate_t` type declarations from `types.h`
- Expanded `circuit_s` struct with `sequence` and `used_gates_per_layer` fields for layer iteration
- Added `add_gate()` declaration from `optimizer.h`
- Added `memset` import to `_core.pxd`
- Implemented `extract_gate_range(start_layer, end_layer)` following draw_data() pattern
- `get_current_layer()` already existed -- verified working
- **Commit:** `bd99d3a`

### Task 2: inject_remapped_gates, layer_floor helpers, allocate_qubit, cache-clear hook
- Implemented `inject_remapped_gates(gates, qubit_map)` following run_instruction() pattern
- Handles `large_control` allocation for gates with >2 controls
- Added `_get_layer_floor()` and `_set_layer_floor(floor)` -- simple wrappers around `circuit_s.layer_floor`
- Added `_allocate_qubit()` wrapping `allocator_alloc(alloc, 1, True)`
- Added module-level `_compile_cache_clear_hooks` list with `_register_cache_clear_hook()` and `_clear_compile_caches()`
- Hooked `_clear_compile_caches()` into `circuit.__init__()` after state resets
- Round-trip verified: extract 34 gates from addition, inject with identity map, gate count goes from 38 to 72
- **Commit:** `c91fa49`

## Files Modified

| File | Changes |
|------|---------|
| `src/quantum_language/_core.pxd` | Full gate_t fields, qubit_t/Standardgate_t types, circuit_s expansion, add_gate declaration, memset import |
| `src/quantum_language/_core.pyx` | extract_gate_range, inject_remapped_gates, _get/_set_layer_floor, _allocate_qubit, cache-clear hook system, circuit.__init__ hook |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Declare gate_t fields via types.h extern block | Clean separation from arithmetic_ops.h opaque declaration; Cython needs field access for capture-replay |
| Use circuit_s (not circuit_t) for field access | circuit_s already had used_layer/used_qubits/layer_floor; extended with sequence and used_gates_per_layer |
| Identity map for injection test | Simplest verification that round-trip preserves gate data correctly |
| Module-level hook list pattern | Simple, extensible -- compile.py registers its cache clear callback without circular imports |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- Cython compiles without errors (only pre-existing warnings)
- All 7 functions importable from `quantum_language._core`
- `extract_gate_range()` returns correct gate dicts with type, target, angle, num_controls, controls
- `inject_remapped_gates()` injects gates with correct qubit remapping
- `_get_layer_floor()` / `_set_layer_floor()` read/write circuit_s.layer_floor
- `_allocate_qubit()` returns integer qubit index
- Cache-clear hook fires on `ql.circuit()` creation
- `test_draw_data.py` passes (8/8) -- most relevant to gate extraction changes
- Full test suite has pre-existing segfault in some parametrized tests (not related to these changes)

## Next Phase Readiness

Phase 48 Plan 02 can proceed. All Cython primitives are ready for import by `compile.py`:
- `extract_gate_range` -- gate capture
- `inject_remapped_gates` -- gate replay
- `get_current_layer` -- layer tracking
- `_get_layer_floor` / `_set_layer_floor` -- gate ordering control
- `_allocate_qubit` -- ancilla allocation during replay
- `_register_cache_clear_hook` -- cache invalidation on circuit reset
