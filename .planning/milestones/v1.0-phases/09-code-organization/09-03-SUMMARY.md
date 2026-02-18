---
phase: 09-code-organization
plan: 03
subsystem: backend-headers
completed: 2026-01-27
duration: 3 min

requires:
  - phase: 06-bitwise-operations
    reason: Width-parameterized bitwise operations implementation
  - plan: 09-01
    reason: Module separation pattern established
  - plan: 09-02
    reason: Header extraction pattern for comparison_ops.h

provides:
  - artifact: Backend/include/bitwise_ops.h
    type: header
    api: Width-parameterized bitwise operations module
  - artifact: Backend/include/LogicOperations.h
    type: wrapper-header
    api: Legacy qbool operations + bitwise_ops.h include

affects:
  - phase: 10
    artifact: Module documentation
    reason: Complete modular header structure for public API

tech-stack:
  added:
    - component: bitwise_ops.h
      purpose: Width-parameterized bitwise operations module (NOT, XOR, AND, OR)

decisions:
  - context: Separation of width-parameterized vs legacy operations
    decision: Create dedicated bitwise_ops.h, keep LogicOperations.h as backward compat wrapper
    rationale: Clean separation of modern (variable-width) from legacy (INTEGERSIZE) operations
    alternatives: Single header with all operations mixed
    trade-offs: Two headers to maintain, but clear organization and migration path

key-files:
  created:
    - Backend/include/bitwise_ops.h: Width-parameterized bitwise operations header (106 lines)
  modified:
    - Backend/include/LogicOperations.h: Converted to wrapper with legacy operations only

tags:
  - c-backend
  - module-separation
  - header-organization
  - bitwise-operations
---

# Phase 9 Plan 3: Bitwise Operations Module Header Summary

**One-liner:** Extracted width-parameterized bitwise operations (Q_not, Q_xor, Q_and, Q_or with controlled variants) into dedicated bitwise_ops.h header, leaving LogicOperations.h as backward compatibility wrapper for legacy qbool operations.

## What Was Built

Created a clean separation between modern width-parameterized bitwise operations and legacy fixed-width operations.

### Task 1: Create bitwise_ops.h header (Commit: de62d1a)

**Created:** `Backend/include/bitwise_ops.h` (106 lines)

**Operations included:**
- **NOT operations:** Q_not (parallel X gates, O(1)), cQ_not (sequential CX, O(bits))
- **XOR operations:** Q_xor (parallel CNOT, O(1)), cQ_xor (Toffoli, O(bits))
- **AND operations:** Q_and (parallel Toffoli, O(1)), CQ_and (classical-quantum)
- **OR operations:** Q_or (3-layer XOR+AND, O(3)), CQ_or (classical-quantum)

**Documentation added:**
- Circuit depth complexity for each operation
- Qubit layout specifications
- OWNERSHIP comments (cached vs caller-owned sequences)
- Dependencies: types.h, stdint.h

**Pattern:** Matches arithmetic_ops.h and comparison_ops.h structure from plans 09-01 and 09-02.

### Task 2: Update LogicOperations.h as wrapper (Commit: d477e52)

**Modified:** `Backend/include/LogicOperations.h`

**Changes:**
1. Added `#include "bitwise_ops.h"` as first dependency
2. Removed width-parameterized declarations:
   - Q_not, cQ_not, Q_xor, cQ_xor, Q_and, CQ_and, Q_or, CQ_or
3. Kept legacy operations:
   - Control flow: void_seq, jmp_seq, branch_seq, cbranch_seq
   - Legacy qbool: q_not_seq, cq_not_seq, and_seq, q_and_seq, etc.
4. Added header documentation explaining organization

**Result:** LogicOperations.h now serves as backward compatibility wrapper that includes bitwise_ops.h and provides legacy INTEGERSIZE-based operations.

### Task 3: Verify compilation and run tests

**Build verification:**
- Rebuilt Cython extension successfully: `python3 setup.py build_ext --inplace`
- No compilation errors

**Test results:**
- All 88 Phase 6 bitwise tests passed
- Test file: `tests/python/test_phase6_bitwise.py`
- Test time: 0.21 seconds
- No regressions detected

**Verified:**
- LogicOperations.c includes LogicOperations.h (which now includes bitwise_ops.h)
- Header include chain works correctly
- All width-parameterized bitwise operations accessible
- Backward compatibility maintained for legacy operations

## Architecture Impact

### Module Organization

**Before:**
```
LogicOperations.h (1325 lines of implementation)
├── Width-parameterized bitwise ops (Q_not, Q_xor, Q_and, Q_or)
├── Legacy qbool operations (q_not_seq, q_and_seq, etc.)
└── Control flow (branch_seq, void_seq, jmp_seq)
```

**After:**
```
bitwise_ops.h (new, 106 lines)
├── Q_not, cQ_not (NOT operations)
├── Q_xor, cQ_xor (XOR operations)
├── Q_and, CQ_and (AND operations)
└── Q_or, CQ_or (OR operations)

LogicOperations.h (wrapper, 55 lines)
├── #include "bitwise_ops.h"
├── Legacy qbool operations
└── Control flow sequences
```

### Benefits

1. **Clear separation:** Width-parameterized (1-64 bits) vs legacy (INTEGERSIZE only)
2. **Migration path:** New code uses bitwise_ops.h, old code continues to work
3. **Documentation:** Each operation documented with circuit depth, qubit layout, ownership
4. **Consistency:** Follows same pattern as arithmetic_ops.h and comparison_ops.h
5. **Maintainability:** Focused headers easier to understand and modify

## Testing

### Phase 6 Bitwise Test Suite

**Coverage:**
- 88 tests total, all passing
- Test categories:
  - BITOP-01: NOT operations (4 tests)
  - BITOP-02: XOR operations (8 tests)
  - BITOP-03: AND operations (12 tests)
  - BITOP-04: OR operations (12 tests)
  - BITOP-05: Python operator overloading (16 tests)
  - Backward compatibility (4 tests)
  - Edge cases (8 tests)
  - Chained operations (8 tests)
  - Success criteria verification (4 tests)
  - Mixed width and in-place operations (12 tests)

**No regressions:** All operations work exactly as before despite header reorganization.

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

### Decision 1: Two-header structure (bitwise_ops.h + LogicOperations.h)

**Context:** LogicOperations.c contains 1325 lines mixing width-parameterized and legacy operations.

**Decision:** Create dedicated bitwise_ops.h for modern operations, keep LogicOperations.h as wrapper.

**Rationale:**
- Clear separation of concerns (variable-width vs fixed-width)
- Backward compatibility via include
- Matches pattern from plans 09-01 (arithmetic_ops.h) and 09-02 (comparison_ops.h)
- Easy migration: new code uses bitwise_ops.h, old code unchanged

**Trade-offs:**
- Two headers to maintain (bitwise_ops.h + LogicOperations.h)
- Include hierarchy slightly deeper
- **Benefit:** Clear organization, explicit migration path, focused documentation

### Decision 2: Documentation depth for bitwise operations

**Context:** Bitwise operations have varying circuit depths and qubit layouts.

**Decision:** Document O(1) vs O(bits) depth, qubit layout, and ownership for every operation.

**Rationale:**
- Users need to understand performance characteristics
- Qubit layout essential for correct usage
- Ownership prevents memory leaks

**Result:** Each operation has complete documentation:
```c
// Q_xor: Bitwise XOR using parallel CNOT gates
// Qubit layout: [0, bits-1] = target A (result), [bits, 2*bits-1] = operand B
// Circuit depth: O(1) - all CNOT gates in parallel
// Result: A := A XOR B (in-place on A)
// OWNERSHIP: Returns cached sequence - DO NOT FREE
sequence_t *Q_xor(int bits);
```

## Next Phase Readiness

### Ready for 09-04

**Blockers:** None

**Concerns:** None

**Status:** ✅ All verification checks passed, tests passing, no regressions.

### Dependencies Resolved

- ✅ Phase 6 bitwise operations implementation complete
- ✅ Module separation pattern established (09-01, 09-02)
- ✅ Header extraction pattern proven

### Enables

- **Plan 09-04:** Continue header extraction for remaining modules
- **Phase 10:** Clean public API with modular headers for documentation

## Files Changed

### Created

| File | Lines | Purpose |
|------|-------|---------|
| Backend/include/bitwise_ops.h | 106 | Width-parameterized bitwise operations module |

### Modified

| File | Changes | Purpose |
|------|---------|---------|
| Backend/include/LogicOperations.h | +22, -20 | Converted to wrapper, includes bitwise_ops.h |

### Verification

| Check | Result |
|-------|--------|
| bitwise_ops.h exists | ✅ Pass |
| LogicOperations.h includes bitwise_ops.h | ✅ Pass (4 references) |
| bitwise_ops.h has width-parameterized ops | ✅ Pass (4 Q_* functions) |
| LogicOperations.h has no width-parameterized ops | ✅ Pass (0 Q_* functions) |
| All Phase 6 bitwise tests pass | ✅ Pass (88/88) |
| Cython extension builds | ✅ Pass |

## Performance

**Execution time:** 3 minutes
- Task 1 (create header): ~1 min
- Task 2 (update wrapper): ~1 min
- Task 3 (verify + test): ~1 min

**Test performance:** 88 tests in 0.21 seconds (unchanged from before)

## Success Criteria

All success criteria met:

- ✅ bitwise_ops.h exists with width-parameterized bitwise operations
- ✅ LogicOperations.h includes bitwise_ops.h, only contains legacy declarations
- ✅ Cython extension builds successfully
- ✅ All existing bitwise tests pass unchanged (88 tests)

## Lessons Learned

### What Worked Well

1. **Pattern reuse:** Following arithmetic_ops.h and comparison_ops.h patterns made implementation straightforward
2. **Documentation-first:** Writing comprehensive comments in header prevented confusion
3. **Test-driven verification:** 88 existing tests caught any issues immediately
4. **Backward compatibility:** Include pattern means no code changes needed elsewhere

### What Could Be Improved

- None for this plan - execution was clean

## Commits

| Commit | Type | Description | Files |
|--------|------|-------------|-------|
| de62d1a | feat | Create bitwise_ops.h header | Backend/include/bitwise_ops.h |
| d477e52 | refactor | Update LogicOperations.h as wrapper | Backend/include/LogicOperations.h |

**Note:** No Task 3 commit needed - verification only, no code changes required.
