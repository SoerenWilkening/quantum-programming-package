# Phase 45 Plan 01: Data Extraction Bridge Summary

**One-liner:** C `circuit_to_draw_data()` with qubit compaction and Cython `draw_data()` bridge returning structured Python dict

## What Was Done

### Task 1: C extraction function and free function
- Added `draw_data_t` struct typedef in `circuit_output.h` with parallel arrays for gate layer, target, type, angle, controls
- Implemented `circuit_to_draw_data()` in `circuit_output.c`:
  - Qubit compaction: sparse allocation indices remapped to dense sequential rows
  - Two-pass approach: first counts total controls, then fills arrays (avoids realloc)
  - Handles `large_control` path for gates with 3+ controls via existing `_get_control_qubit()` helper
  - NULL circuit returns NULL; empty circuit (0 gates) returns valid struct with populated qubit_map
  - All malloc results checked; allocation failure safely cleans up
- Implemented `free_draw_data()` with NULL safety on all array members
- **Commit:** `aaa258d`

### Task 2: Cython bridge and draw_data() method
- Added `draw_data_t` extern declarations to `_core.pxd` inside existing `circuit_output.h` block
- Added `draw_data()` method to `circuit` class in `_core.pyx`:
  - Returns dict with keys: `num_layers`, `num_qubits`, `gates`, `qubit_map`
  - Each gate dict contains: `layer`, `target`, `type`, `angle`, `controls`
  - `try/finally` ensures `free_draw_data()` always called (no memory leaks)
  - Uses `<circuit_t*>_circuit` cast pattern consistent with existing methods
- **Commit:** `6e9d398`

## Verification Results

1. C code compiles without errors or warnings (related to circuit_output.c)
2. Empty circuit: returns `{'num_layers': 0, 'num_qubits': 0, 'gates': [], 'qubit_map': []}`
3. Simple circuit (qint(5, width=4)): 1 layer, 2 qubits, 2 gates with correct compaction
4. Complex circuit (4-bit addition): 19 layers, 12 qubits, 38 gates, 26 controlled gates
5. All gate target and control indices verified < num_qubits (compaction correct)
6. qubit_map length equals num_qubits in all cases

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use `circ->used_occupation_indices_per_qubit[q] != 0` for used-qubit detection | Matches pattern from `circuit_visualize()` and `print_circuit()` |
| Iterate `q <= circ->used_qubits` (inclusive) | `used_qubits` is max index not count, consistent with existing code |
| Two-pass control counting | Avoids realloc complexity, single allocation for ctrl_qubits |
| `calloc` for draw_data_t | Ensures all pointer fields start NULL for safe free_draw_data on partial allocation failure |

## Key Files

### Created
- None (all modifications to existing files)

### Modified
- `c_backend/include/circuit_output.h` - Added draw_data_t typedef and function declarations
- `c_backend/src/circuit_output.c` - Added circuit_to_draw_data() and free_draw_data() implementations
- `src/quantum_language/_core.pxd` - Added Cython extern declarations for draw_data API
- `src/quantum_language/_core.pyx` - Added draw_data() method to circuit class

## Metrics

- **Duration:** ~5 minutes
- **Tasks:** 2/2 completed
- **Commits:** 2 task commits

## Next Phase Readiness

Phase 46 (pixel-art renderer) can now call `circuit.draw_data()` to get structured gate data. The dict format provides everything needed for rendering:
- `num_layers` and `num_qubits` define grid dimensions
- `gates` list provides per-gate positioning and type information
- `qubit_map` enables display of original qubit indices on row labels
- All qubit indices are compacted (dense) for direct use as array indices
