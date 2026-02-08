---
phase: 58-hardcoded-sequences-1-8
plan: 02
subsystem: c-backend
tags: [performance, sequences, static-allocation, QFT-addition, routing]

dependency_graph:
  requires:
    - 58-01 (1-4 bit sequences and dispatch helpers)
  provides:
    - Static QQ_add sequences for widths 5-8
    - Static cQQ_add sequences for widths 5-8
    - Unified dispatch functions for all widths 1-8
    - IntegerAddition.c routing to hardcoded sequences
  affects:
    - 58-03 (integration testing)

tech_stack:
  added: []
  patterns:
    - Const cast for API compatibility with static sequences
    - Unified dispatch pattern (1-4 and 5-8 split)
    - Python-based C code generation for reproducibility

file_tracking:
  key_files:
    created:
      - c_backend/src/sequences/add_seq_5_8.c (6351 lines)
      - scripts/generate_seq_5_8.py
    modified:
      - c_backend/src/IntegerAddition.c
      - setup.py

decisions:
  - id: SEQ-04
    choice: Generate C code via Python script for 5-8 bit sequences
    reason: Large file size (6351 lines) makes manual editing error-prone; script ensures reproducibility
  - id: SEQ-05
    choice: Use const cast in IntegerAddition.c for hardcoded return
    reason: API returns non-const sequence_t* but hardcoded are const; cast is safe because static lifetime

metrics:
  duration: ~8 min
  completed: 2026-02-05
---

# Phase 58 Plan 02: 5-8 Bit Sequences and Routing Summary

Complete hardcoded sequences for widths 5-8 and integrate routing in IntegerAddition.c to use pre-computed sequences for all widths 1-8.

## One-liner

Static QQ_add and cQQ_add sequences for widths 5-8 with unified dispatch routing in IntegerAddition.c.

## What Was Built

### Task 1: add_seq_5_8.c (6351 lines)

Created comprehensive static gate arrays for widths 5-8:

**QQ_add sequences:**
- Width 5: 35 layers (optimized from theoretical 23)
- Width 6: 43 layers (optimized from theoretical 28)
- Width 7: 51 layers (optimized from theoretical 33)
- Width 8: 58 layers (optimized from theoretical 38)

**cQQ_add sequences:**
- Width 5: 53 layers
- Width 6: 71 layers
- Width 7: 90 layers
- Width 8: 110 layers

**Dispatch functions:**
- `get_hardcoded_QQ_add_5_8(bits)` - static helper for 5-8
- `get_hardcoded_cQQ_add_5_8(bits)` - static helper for 5-8
- `get_hardcoded_QQ_add(bits)` - PUBLIC unified dispatch for 1-8
- `get_hardcoded_cQQ_add(bits)` - PUBLIC unified dispatch for 1-8

### Task 2: IntegerAddition.c Routing

Modified QQ_add() and cQQ_add() to check hardcoded sequences first:

```c
// Use hardcoded sequences for widths 1-8
if (bits <= HARDCODED_MAX_WIDTH) {
    const sequence_t *hardcoded = get_hardcoded_QQ_add(bits);
    if (hardcoded != NULL) {
        return (sequence_t *)hardcoded;
    }
}
// Fall back to dynamic generation for widths > 8
```

### Task 3: Build Configuration

Added `add_seq_5_8.c` to setup.py c_sources list.

## Key Implementation Details

### Code Generation Approach

Created `scripts/generate_seq_5_8.py` to generate the C code:
- Follows exact same gate pattern as dynamic generation in IntegerAddition.c
- Applies layer optimization (merging non-overlapping gates)
- Outputs complete C file with proper formatting

### Const Safety

The const cast in IntegerAddition.c is safe because:
1. Static sequences have program lifetime (never freed)
2. Caller should never free or modify returned sequences
3. Cast needed only because existing API returns non-const

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| c4f9ffe | feat | Implement hardcoded QQ_add and cQQ_add for widths 5-8 |
| aa8f4ed | feat | Route QQ_add and cQQ_add to hardcoded sequences for widths 1-8 |
| 816c8d6 | chore | Add add_seq_5_8.c to build configuration |

## Verification

1. Source files exist: add_seq_1_4.c and add_seq_5_8.c
2. IntegerAddition.c includes sequences.h
3. Routing logic implemented for both QQ_add and cQQ_add
4. Package builds successfully
5. All 888 addition tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**For 58-03:**
- All hardcoded sequences (1-8 bit) are in place
- Routing is active for both QQ_add and cQQ_add
- Ready for integration testing and performance validation

## Performance Impact

Widths 1-8 now use pre-computed static sequences, eliminating:
- malloc/calloc calls for sequence allocation
- QFT/IQFT gate generation loops
- Cache lookup overhead (direct return from static memory)

This benefits the most common integer operations in quantum programs.
