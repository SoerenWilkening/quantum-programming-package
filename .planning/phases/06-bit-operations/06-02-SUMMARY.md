---
phase: 06-bit-operations
plan: 02
subsystem: backend
tags: [quantum, bitwise, and, or, toffoli, cnot, c]

# Dependency graph
requires:
  - phase: 05-variable-width-integers
    provides: width-parameterized pattern (QQ_add, CQ_add)
  - phase: 06-01
    provides: Q_not, cQ_not, Q_xor, cQ_xor patterns
provides:
  - Q_and(bits): quantum-quantum AND with Toffoli gates
  - CQ_and(bits, value): classical-quantum AND with CNOT
  - Q_or(bits): quantum-quantum OR with 3-layer pattern
  - CQ_or(bits, value): classical-quantum OR with X/CNOT
affects: [06-03 python bindings, 06-04 shift operations]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "3-layer OR: CNOT A, CNOT B, Toffoli A&B"
    - "Classical-quantum pattern: gate per bit based on classical value"

key-files:
  created: []
  modified:
    - Backend/src/LogicOperations.c
    - Backend/include/LogicOperations.h

key-decisions:
  - "Q_and uses single layer of parallel Toffoli gates"
  - "Q_or uses A XOR B XOR (A AND B) = A OR B identity"
  - "CQ_and: CNOT for 1s, skip for 0s (0 AND x = 0)"
  - "CQ_or: X for 1s (1 OR x = 1), CNOT for 0s (0 OR x = x)"

patterns-established:
  - "Qubit layout: [output, operandA, operandB] for binary ops"
  - "Width-parameterized naming: Q_ for quantum-quantum, CQ_ for classical-quantum"

# Metrics
duration: 6min
completed: 2026-01-26
---

# Phase 6 Plan 02: AND and OR Operations Summary

**Width-parameterized AND and OR operations using Toffoli (CCX) and CNOT gates with proper ancilla qubit layout**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-26T16:32:18Z
- **Completed:** 2026-01-26T16:38:42Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Implemented Q_and(bits) with parallel Toffoli gates for quantum-quantum AND
- Implemented Q_or(bits) with 3-layer CNOT+Toffoli pattern (A XOR B XOR (A AND B))
- Implemented CQ_and and CQ_or for classical-quantum operations
- All functions handle 1-64 bit widths with proper bounds checking

## Task Commits

Each task was committed atomically:

1. **Task 1: Q_and and CQ_and** - `04ffe0a` (bundled with 06-01 XOR commit)
2. **Task 2: Q_or and CQ_or** - `6a9413a` (feat)

## Files Created/Modified
- `Backend/src/LogicOperations.c` - Added Q_and, CQ_and, Q_or, CQ_or functions
- `Backend/include/LogicOperations.h` - Added function declarations

## Decisions Made

1. **Q_and single layer**: All Toffoli gates operate on independent qubits, so they can be applied in parallel (O(1) depth)

2. **Q_or uses mathematical identity**: Instead of De Morgan's law (~(~A & ~B)), uses A XOR B XOR (A AND B) which equals A OR B. This requires only 3 layers vs potentially more with NOT gates.

3. **CQ_and skip 0 bits**: When classical bit is 0, no gate needed because 0 AND x = 0 (output stays |0>)

4. **CQ_or differentiated gates**:
   - Classical 1: Apply X gate (1 OR x = 1, so set output to |1>)
   - Classical 0: Apply CNOT (0 OR x = x, so copy quantum bit)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 1 was bundled into a prior commit (04ffe0a) due to linter auto-formatting which also applied the changes. This is a deviation in commit structure but not in functionality.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All four width-parameterized AND/OR functions ready for Python bindings
- Pattern established: output ancilla at [0:bits], operand A at [bits:2*bits], operand B at [2*bits:3*bits]
- Ready for 06-03 (Python operator overloading)

---
*Phase: 06-bit-operations*
*Completed: 2026-01-26*
