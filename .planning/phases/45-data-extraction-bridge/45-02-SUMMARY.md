---
phase: 45-data-extraction-bridge
plan: 02
subsystem: testing
tags: [draw_data, integration-tests, qubit-compaction, scale-testing]
dependency-graph:
  requires: [45-01]
  provides: [draw_data-tests, phase-45-validation]
  affects: [46, 47]
tech-stack:
  patterns: [pytest-fixture-based-testing, integration-testing]
key-files:
  created:
    - tests/test_draw_data.py
metrics:
  duration: ~5 min
  completed: 2026-02-03
---

# Phase 45 Plan 02: draw_data() Integration Tests Summary

**Eight integration tests validating full C-to-Python draw_data() pipeline including qubit compaction, control extraction, gate types, and 200+ qubit scale.**

## What Was Done

### Task 1: Core integration tests

Created `tests/test_draw_data.py` with 8 tests covering all Phase 45 success criteria:

1. **test_draw_data_empty_circuit** - Empty circuit returns valid dict with empty gates list
2. **test_draw_data_basic_structure** - Validates all required keys (num_layers, num_qubits, gates, qubit_map) and per-gate keys (layer, target, type, angle, controls), bounds-checks all indices
3. **test_draw_data_gate_types** - Verifies gate type integers map to valid Standardgate_t enum values (0-9)
4. **test_draw_data_qubit_compaction** - Confirms dense 0-based sequential indices after compaction, all targets and controls in [0, num_qubits)
5. **test_draw_data_qubit_map** - Validates qubit_map length equals num_qubits, values are sorted ascending non-negative integers
6. **test_draw_data_controlled_gates** - Addition produces CNOT/Toffoli gates; verifies non-empty controls lists with valid indices, target not in controls
7. **test_draw_data_angles** - QFT-based addition produces P/R gates; validates angles are finite floats (not NaN, not Inf)
8. **test_draw_data_scale_200_qubits** - 52 qint variables of width 4 (208 qubits); completes without crash/segfault, validates structure at scale

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Use `_` prefix for side-effect-only variables | Satisfies ruff F841 linter while keeping qint allocations that add gates to circuit |
| Initialize with value=-1 for scale test | Sets all bits, ensuring every qubit has gates and survives compaction |
| Use addition for controlled gate tests | QFT addition internally generates CNOT/Toffoli gates, most reliable way to get controls |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scale test qubit count assertion**
- **Found during:** Task 1 verification
- **Issue:** Original approach (50 vars * width=4, values i%16) only produced 97 compacted qubits because many bit positions had value 0 and were unused
- **Fix:** Changed to 52 vars * width=4 initialized to -1 (all bits set), guaranteeing 208 qubits all with X gates
- **Files modified:** tests/test_draw_data.py
- **Commit:** b0214be

## Verification Results

- All 8 tests pass: `python3 -m pytest tests/test_draw_data.py -v` -- 8 passed in 0.07s
- 200+ qubit scale test completes without crash (208 qubits)
- No regressions in existing test suite (pre-existing segfault in test_api_coverage.py is unrelated)
- All qubit indices verified dense and sequential via bounds checking

## Next Phase Readiness

Phase 45 success criteria fully validated by these tests. Ready for Phase 46 (pixel-art renderer).
