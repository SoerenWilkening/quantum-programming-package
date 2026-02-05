---
phase: 05-variable-width-integers
plan: 02
subsystem: backend-arithmetic
tags: [c, addition, variable-width, qft-arithmetic, cython]

# Dependency graph
requires:
  - phase: 05-01
    provides: quantum_int_t with width field, QINT(circ, width)
provides:
  - QQ_add(int bits) generates variable-width addition circuits
  - cQQ_add(int bits) generates variable-width controlled addition circuits
  - Width-parameterized precompiled caching for 1-64 bit widths
  - Python bindings pass self.bits to parameterized functions
affects:
  - 05-03 (Python bindings for variable-width arithmetic)
  - 06-advanced-arithmetic

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Width-parameterized precompiled caches: precompiled_XX_add_width[65]"
    - "Bounds validation: bits < 1 || bits > 64 returns NULL"
    - "Legacy globals maintained for backward compat"

key-files:
  created: []
  modified:
    - Backend/include/Integer.h
    - Backend/src/IntegerAddition.c
    - python-backend/quantum_language.pxd
    - python-backend/quantum_language.pyx

key-decisions:
  - "QQ_add(int bits) signature replaces QQ_add(void)"
  - "cQQ_add(int bits) signature replaces cQQ_add(void)"
  - "precompiled_QQ_add_width[65] array caches by width (index 0 unused)"
  - "Legacy globals auto-populated when bits == INTEGERSIZE"
  - "Qubit layout: [0, bits-1] target, [bits, 2*bits-1] control"

patterns-established:
  - "Width-parameterized arithmetic: all QFT-based ops accept bits parameter"
  - "Cache-per-width strategy for precompiled sequences"

# Metrics
duration: 6min
completed: 2026-01-26
---

# Phase 5 Plan 2: Width-Aware Arithmetic Summary

**Parameterized QQ_add and cQQ_add to accept bits parameter for variable-width quantum addition**

## Performance

- **Duration:** 6 min
- **Started:** 2026-01-26T14:22:33Z
- **Completed:** 2026-01-26T14:28:55Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- QQ_add(int bits) generates correct addition circuits for any width 1-64
- cQQ_add(int bits) generates correct controlled addition circuits
- Precompiled caching works for all widths via precompiled_QQ_add_width[65]
- Layer count scales correctly: 5*bits-2 for QQ_add
- Python bindings updated to pass self.bits to parameterized functions
- All 59 tests pass

## Task Commits

Tasks 1 and 2 were committed together due to compile-time interdependency:

1. **Tasks 1+2: Parameterize QQ_add and cQQ_add** - `3d0e156` (feat)
   - QQ_add(int bits) with bounds check and caching
   - cQQ_add(int bits) with bounds check and caching
   - precompiled_QQ_add_width[65] and precompiled_cQQ_add_width[65] arrays
   - Legacy globals maintained for backward compat

2. **Task 3: Update Python bindings** - `5440813` (feat)
   - .pxd declarations updated
   - .pyx callers pass self.bits

## Files Created/Modified

- `Backend/include/Integer.h` - Updated function signatures, added precompiled width arrays
- `Backend/src/IntegerAddition.c` - Parameterized QQ_add and cQQ_add implementations
- `python-backend/quantum_language.pxd` - Updated extern declarations
- `python-backend/quantum_language.pyx` - Updated caller sites with self.bits

## Key Changes

### QQ_add(int bits)
```c
// Qubit layout:
// - Qubits [0, bits-1]: First operand (target, modified in place)
// - Qubits [bits, 2*bits-1]: Second operand (control)
sequence_t *QQ_add(int bits) {
    if (bits < 1 || bits > 64) return NULL;
    if (precompiled_QQ_add_width[bits] != NULL)
        return precompiled_QQ_add_width[bits];
    // ... generates 5*bits-2 layers ...
    precompiled_QQ_add_width[bits] = add;
    if (bits == INTEGERSIZE) precompiled_QQ_add = add;
    return add;
}
```

### cQQ_add(int bits)
```c
// Qubit layout:
// - Qubits [0, bits-1]: First operand (target)
// - Qubits [bits, 2*bits-1]: Second operand (control)
// - Qubit [3*bits-1]: Conditional control qubit
sequence_t *cQQ_add(int bits) {
    if (bits < 1 || bits > 64) return NULL;
    // ... width-parameterized implementation ...
}
```

## Decisions Made

1. **Single bits parameter:** Both operands must be same width (matched addition)
2. **Cache array size 65:** Index 0 unused, indices 1-64 valid for convenient indexing
3. **Backward compat via legacy globals:** precompiled_QQ_add/cQQ_add populated when bits == INTEGERSIZE
4. **Python uses self.bits:** Each qint instance knows its own width

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Virtual environment symlinks broken (pre-existing) - tests run with system Python
- Pre-commit hooks passed without issues

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Width-aware arithmetic foundation complete
- Ready for 05-03: Python bindings update (remaining operations)
- All arithmetic operations now use parameterized widths
- Full test suite verified passing

---
*Phase: 05-variable-width-integers*
*Completed: 2026-01-26*
