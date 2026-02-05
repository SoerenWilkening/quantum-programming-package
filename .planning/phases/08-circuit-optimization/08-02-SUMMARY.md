---
phase: 08-circuit-optimization
plan: 02
subsystem: python-api
tags: [python, cython, statistics, api-design]

dependencies:
  requires: ["08-01"]
  provides: ["circuit.gate_count", "circuit.depth", "circuit.qubit_count", "circuit.gate_counts"]
  affects: ["08-05"]

tech-stack:
  added: []
  patterns: ["property-based-api", "on-demand-computation"]

key-files:
  created: ["tests/python/test_phase8_circuit.py"]
  modified: ["python-backend/quantum_language.pxd", "python-backend/quantum_language.pyx"]

decisions:
  - "circuit.gate_count, circuit.depth, circuit.qubit_count, circuit.gate_counts as @property methods"
  - "gate_counts returns dict with keys: X, Y, Z, H, P, CNOT, CCX, other"
  - "On-demand computation (no caching) per CONTEXT.md design"
  - "Cast to circuit_s* matches forward declaration pattern from existing code"

metrics:
  duration: "3 min"
  completed: "2026-01-26"
---

# Phase 8 Plan 2: Python Circuit Statistics API

**One-liner:** Python properties expose circuit metrics (gate_count, depth, qubit_count, gate_counts) via on-demand C function calls

## What Was Built

Exposed circuit statistics through Python API as read-only properties on the `circuit` class. Users can now query circuit metrics programmatically without OpenQASM parsing or visualization analysis.

### Implementation Details

**Cython Declarations (quantum_language.pxd):**
- Declared `gate_counts_t` struct with 8 gate type counters
- Declared 4 C statistics functions with `circuit_s*` forward declaration pattern
- Functions: `circuit_gate_count()`, `circuit_depth()`, `circuit_qubit_count()`, `circuit_gate_counts()`

**Python Properties (quantum_language.pyx):**
- `circuit.gate_count` → total gates (int)
- `circuit.depth` → number of layers (int)
- `circuit.qubit_count` → qubits used (int)
- `circuit.gate_counts` → gate breakdown (dict)
- All properties use `<circuit_s*>_circuit` cast to match C signatures
- Dict keys: 'X', 'Y', 'Z', 'H', 'P', 'CNOT', 'CCX', 'other'

**On-demand computation:**
- No caching at Python level (per CONTEXT.md)
- Each property access calls C function
- C layer computes from circuit fields (circ->used, circ->used_layer, etc.)

### Test Coverage

Created `test_phase8_circuit.py` with 6 tests:
1. Property existence and type checking (gate_count, depth, qubit_count, gate_counts)
2. Statistics increase after operations
3. Gate counts breakdown matches total

All tests pass. No regressions in Phase 8 API.

## Technical Decisions

### Why properties instead of methods?
Read-only metrics feel more natural as properties (e.g., `circuit.depth` vs `circuit.get_depth()`). Follows Python convention for computed attributes.

### Why no caching?
CONTEXT.md specifies on-demand computation. Circuit is actively modified during quantum operations, so cached values would be stale. Each access recomputes from current circuit state.

### Why circuit_s* instead of circuit_t*?
Matches existing Cython pattern from `qubit_allocator.h` declarations. Forward declaration `struct circuit_s` enables Cython to reference opaque struct before full definition.

## Deviations from Plan

None - plan executed exactly as written.

## How to Use

```python
from quantum_language import circuit, qint

# Create circuit and perform operations
c = circuit()
a = qint(5, width=8)
b = qint(3, width=8)
result = a + b

# Query statistics
print(f"Gates: {c.gate_count}")
print(f"Depth: {c.depth}")
print(f"Qubits: {c.qubit_count}")
print(f"Breakdown: {c.gate_counts}")

# Example output:
# Gates: 127
# Depth: 18
# Qubits: 16
# Breakdown: {'X': 0, 'Y': 0, 'Z': 0, 'H': 24, 'P': 12, 'CNOT': 91, 'CCX': 0, 'other': 0}
```

## Success Criteria Met

- [x] circuit class has gate_count, depth, qubit_count, gate_counts properties
- [x] All properties accessible without errors
- [x] gate_counts returns dict with expected keys (X, Y, Z, H, P, CNOT, CCX, other)
- [x] Statistics increase after operations
- [x] Full build and test suite pass

## Commits

- `3bac7c8` - feat(08-02): add Cython declarations for circuit stats functions
- `cf85bd3` - feat(08-02): add circuit statistics properties to Python API
- `2732d9f` - test(08-02): add circuit statistics API tests

## Integration Notes

**For Phase 8 Plan 5 (Optimization):**
- Statistics API enables before/after optimization comparison
- Users can query `circuit.gate_count` before and after `circuit.optimize()` to verify improvement
- Gate breakdown shows which gate types were reduced

**Current limitations:**
- Statistics computed from global `_circuit` singleton
- Multiple circuit instances would share statistics (known limitation from existing architecture)
- Future work: per-instance circuit tracking

## Next Phase Readiness

Phase 8 Plan 3 (Circuit visualization enhancement) and Plan 5 (Optimization) can now reference statistics API. No blockers.

**Statistics API provides:**
- Programmatic access to circuit metrics
- Foundation for optimization verification
- Debugging tool for algorithm developers

Ready for Plan 5 to build optimization that returns new circuit with reduced gate_count.
