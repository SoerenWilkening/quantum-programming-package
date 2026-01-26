---
phase: 08-circuit-optimization
plan: 03
subsystem: visualization
tags: [circuit-viz, debugging, ascii-art, horizontal-layout]
requires: [circuit-data-structures]
provides: [circuit_visualize-function, visualize-method]
affects: [future-debugging-workflows]
tech-stack:
  added: []
  patterns: [horizontal-circuit-layout, compact-gate-symbols]
key-files:
  created:
    - none
  modified:
    - Backend/include/circuit_output.h
    - Backend/src/circuit_output.c
    - python-backend/quantum_language.pxd
    - python-backend/quantum_language.pyx
decisions:
  - title: Horizontal orientation for circuit display
    rationale: Time flows left-to-right (conventional), qubits as rows easier to read than vertical
    alternatives: Vertical layout (time top-to-bottom)
    impact: User-facing visualization format
  - title: Compact gate symbols (single chars)
    rationale: Fits more layers on screen, cleaner ASCII art
    alternatives: Full gate names (too wide)
    impact: Display density and readability
  - title: 60-layer display limit
    rationale: Beyond 60 layers becomes unreadable in terminal
    alternatives: Scrolling, pagination (more complex)
    impact: Very wide circuits truncated
metrics:
  duration: 5 minutes
  completed: 2026-01-26
---

# Phase 8 Plan 3: Circuit Visualization Enhancement Summary

**One-liner:** Horizontal circuit layout with compact gate symbols (H, X, @, |) for debugging quantum circuits

## What Was Built

Enhanced text-based circuit visualization providing clear horizontal layout:
- Qubits as rows, layers as columns (time flows left-to-right)
- Compact symbols: H, X, Z, P, M for gates; @ for controls; | for vertical connections; + for CNOT target
- Layer numbers on top (every 5 layers labeled)
- Qubit indices on left (q0, q1, ...)
- Truncation at 60 layers for very wide circuits

### Implementation Details

**C Function (circuit_visualize):**
- NULL-safe (handles NULL circuit pointer)
- Empty-circuit aware (prints message instead of empty grid)
- Iterates over layers (columns) and qubits (rows)
- Uses existing `min_qubit`/`max_qubit` helpers to detect vertical connections
- Prints "---" for idle wires, symbols for gates, "@" for controls, "|" for connections

**Python Binding:**
- Added `circuit_visualize` declaration to `quantum_language.pxd`
- Added `visualize()` method to `circuit` class in `quantum_language.pyx`
- Method prints to stdout (no return value)
- Includes docstring with usage example

### Example Output

```
Circuit: 30 gates, 18 layers, 12 qubits

     0              5              10             15
q4   --------------------------------------- @ ------------
q5   --------------------------------- @  @  | ------------
q6   --------------------------- @  @  @  |  | ------------
q7   --------------------- @  @  @  @  |  |  | ------------
q8    H  P  P  P --------- |  |  |  P  P  P  P  P  P  P  H
q9   --- @  H  P  P ------ |  |  P  P  P  P  P  H  |  @ ---
q10  ------ @  @  H  P --- |  P  P  P  H  |  @  |  @ ------
q11  --------- @  @  @  H  P  H --- @ --- @ --- @ ---------
```

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| 1 | (c9a9dfc, already done) | Add circuit_visualize function declaration |
| 2 | 53a91e3 | Implement circuit_visualize function |
| 3 | 0f745b6 | Add Python binding for circuit.visualize() |

## Deviations from Plan

None - plan executed exactly as written.

All tasks completed as specified:
- Task 1: Declaration already existed from prior work (c9a9dfc)
- Task 2: Implementation added with horizontal layout, compact symbols, vertical connections
- Task 3: Python bindings added, tested successfully

## Technical Notes

### Gate Symbol Choices

- Single-char symbols where possible: H, X, Z, Y, P, M
- Multi-char for controls: @ (control qubit)
- CNOT target: + (when X gate has controls)
- Vertical connection: | (wire passing between control and target)
- Idle wire: --- (3 chars for alignment)

### Layout Algorithm

For each layer (column):
1. Check `gate_index_of_layer_and_qubits[layer][qubit]`
2. If gate exists and qubit is target → print gate symbol
3. If gate exists and qubit is control → print "@"
4. If no gate but qubit is between min/max qubit of a gate → print "|"
5. Otherwise → print "---"

### Display Width Limit

Circuits with >60 layers show warning: "(showing first 60 of N layers)"
Rationale: Beyond 60 layers, terminal width becomes limiting factor

## Testing

**Manual verification:**
```python
from quantum_language import circuit, qint
c = circuit()
a = qint(7, width=4)
b = qint(5, width=4)
result = a + b
c.visualize()  # Shows 30 gates, 18 layers, 12 qubits
```

**Tests:**
- NULL circuit → prints "Circuit is NULL"
- Empty circuit → prints "(empty circuit)"
- Actual circuit → displays horizontal layout with symbols

## Next Phase Readiness

**Ready for 08-04 (next plan):** Yes

**Blockers:** None

**Concerns:** None

**Integration points:**
- `circuit.visualize()` method now available for debugging in all subsequent phases
- Can be used to verify optimization effects (compare before/after)
- Useful for educational/demo purposes

## Dependencies

**Required from prior phases:**
- Circuit data structure (layers, gates, qubit indexing)
- `min_qubit`/`max_qubit` helper functions from gate.h
- Python binding infrastructure (Cython)

**Provides for future phases:**
- Debugging tool for circuit optimization (08-04, 08-05)
- Visualization for testing correctness
- User-facing method for circuit inspection

## Lessons Learned

1. **Horizontal layout is superior** - More intuitive than vertical (matches conventional circuit diagrams)
2. **Compact symbols essential** - Full gate names would make display too wide
3. **Truncation necessary** - Very wide circuits need graceful handling
4. **Layer number headers useful** - Every 5 layers labeled helps count depth
5. **NULL safety important** - Visualization function should never crash
