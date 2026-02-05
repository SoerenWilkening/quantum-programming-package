---
phase: 09-code-organization
plan: 02
subsystem: backend-headers
tags: [c-refactor, module-separation, comparison-ops, backward-compat]

requires:
  - "Phase 7 comparison operations"
  - "CODE-04 reorganization pattern (arithmetic_ops.h, bitwise_ops.h)"

provides:
  - comparison_ops.h: Comparison operations module header
  - IntegerComparison.h: Backward compatibility wrapper

affects:
  - "Future phases using comparison operations"
  - "Module dependency documentation (module_deps.md)"

tech-stack:
  added: []
  patterns:
    - "Dedicated module headers with zero external dependencies"
    - "Backward compatibility wrapper pattern"
    - "OWNERSHIP comment documentation"

key-files:
  created:
    - Backend/include/comparison_ops.h
  modified:
    - Backend/include/IntegerComparison.h
    - Backend/src/IntegerComparison.c

decisions:
  - slug: comparison-ops-header
    what: Created comparison_ops.h following arithmetic_ops.h pattern
    why: CODE-04 compliance requires dedicated module headers
    impact: Establishes clear module boundaries for comparison operations
    date: 2026-01-27

  - slug: integercomparison-wrapper
    what: Converted IntegerComparison.h to thin backward compatibility wrapper
    why: Preserves existing includes while promoting new structure
    impact: Zero breaking changes, gradual migration path
    date: 2026-01-27

  - slug: direct-include-in-c
    what: Updated IntegerComparison.c to directly include comparison_ops.h
    why: Clearer dependency chain, explicit about what's needed
    impact: More maintainable code, easier to trace dependencies
    date: 2026-01-27

metrics:
  duration: 373  # 6.2 minutes
  completed: 2026-01-27
---

# Phase 09 Plan 02: Comparison Operations Module Header Summary

**One-liner:** Created comparison_ops.h consolidating comparison function declarations with IntegerComparison.h as backward compatibility wrapper.

## What Was Built

Created a dedicated comparison operations module header following the CODE-04 reorganization pattern established by arithmetic_ops.h and bitwise_ops.h.

**comparison_ops.h structure:**
- Header guard: `QUANTUM_COMPARISON_OPS_H`
- Dependencies: types.h (for sequence_t), stdint.h (for int64_t)
- Legacy INTEGERSIZE functions: `CC_equal()`, `CQ_equal()`, `cCQ_equal()`
- Width-parameterized functions: `QQ_equal(int bits)`, `QQ_less_than(int bits)`
- Classical-quantum functions: `CQ_equal_width(int bits, int64_t value)`, `CQ_less_than(int bits, int64_t value)`
- OWNERSHIP comments document memory responsibilities
- 74 lines with clear documentation

**IntegerComparison.h transformation:**
- Reduced from 56 to 14 lines (75% reduction)
- Now includes comparison_ops.h
- Documents backward compatibility purpose
- Preserves header guard for existing code

**IntegerComparison.c update:**
- Changed from `#include "IntegerComparison.h"` to `#include "comparison_ops.h"`
- Direct dependency on new module header
- Gets types.h transitively

## Tasks Completed

| Task | Description | Files | Verification |
|------|-------------|-------|--------------|
| 1 | Create comparison_ops.h header | Backend/include/comparison_ops.h | File exists with all comparison declarations |
| 2 | Update IntegerComparison.h as wrapper | Backend/include/IntegerComparison.h | 14 lines, includes comparison_ops.h |
| 3 | Update IntegerComparison.c includes | Backend/src/IntegerComparison.c | Compiles successfully, tests pass |

## Technical Implementation

**Module header pattern:**
```c
#ifndef QUANTUM_COMPARISON_OPS_H
#define QUANTUM_COMPARISON_OPS_H

#include "types.h"
#include <stdint.h>

// Legacy operations
sequence_t *CC_equal();
sequence_t *CQ_equal();
sequence_t *cCQ_equal();

// Width-parameterized operations
sequence_t *QQ_equal(int bits);
sequence_t *QQ_less_than(int bits);
sequence_t *CQ_equal_width(int bits, int64_t value);
sequence_t *CQ_less_than(int bits, int64_t value);

#endif
```

**Backward compatibility wrapper pattern:**
```c
#ifndef CQ_BACKEND_IMPROVED_INTEGERCOMPARISON_H
#define CQ_BACKEND_IMPROVED_INTEGERCOMPARISON_H

#include "comparison_ops.h"

#endif
```

## Test Results

**Comparison operations test suite:**
- 7/7 tests passed
- Test coverage: equality, less-than, greater-than, less-equal, greater-equal, mixed widths, int comparisons
- Zero test modifications required
- Compilation successful with new header structure

**Tests verified:**
```
test_phase7_arithmetic.py::TestComparisonOperations::test_equal_same_width PASSED
test_phase7_arithmetic.py::TestComparisonOperations::test_less_than PASSED
test_phase7_arithmetic.py::TestComparisonOperations::test_greater_than PASSED
test_phase7_arithmetic.py::TestComparisonOperations::test_less_equal PASSED
test_phase7_arithmetic.py::TestComparisonOperations::test_greater_equal PASSED
test_phase7_arithmetic.py::TestComparisonOperations::test_comparison_mixed_widths PASSED
test_phase7_arithmetic.py::TestComparisonOperations::test_comparison_with_int PASSED
```

## Deviations from Plan

None - plan executed exactly as written.

## Commits

1. `11e310f` - feat(09-02): create comparison_ops.h module header
   - New header consolidates all comparison function declarations
   - 74 lines with OWNERSHIP comments and documentation

2. `bfdf9b1` - refactor(09-02): convert IntegerComparison.h to backward compat wrapper
   - Reduced from 56 to 14 lines (thin wrapper pattern)
   - Includes comparison_ops.h
   - Preserves backward compatibility

3. `46d32c5` - refactor(09-02): update IntegerComparison.c to use comparison_ops.h
   - Changed include from IntegerComparison.h to comparison_ops.h
   - Direct dependency on new module header
   - All tests pass after rebuild

## Code Quality Metrics

**Lines of code:**
- comparison_ops.h: 74 lines (new)
- IntegerComparison.h: 14 lines (was 56, reduced 75%)
- IntegerComparison.c: 309 lines (1 line changed)

**Compilation:**
- Build time: ~30 seconds
- Warnings: Pre-existing only (signed/unsigned comparison in other files)
- Errors: 0

**Test coverage:**
- Comparison operations: 7 tests, all passing
- Backward compatibility: Verified via existing test suite

## Dependencies

**Before this plan:**
```
IntegerComparison.h (56 lines)
  └── types.h
IntegerComparison.c
  └── IntegerComparison.h
```

**After this plan:**
```
comparison_ops.h (74 lines)
  └── types.h

IntegerComparison.h (14 lines, wrapper)
  └── comparison_ops.h

IntegerComparison.c
  └── comparison_ops.h
```

## Module Characteristics

**comparison_ops.h:**
- **Purpose:** Comparison operations module header
- **Dependencies:** types.h, stdint.h
- **Exports:** 7 comparison function declarations
- **OWNERSHIP:** Documented for all functions
- **Pattern:** Matches arithmetic_ops.h, bitwise_ops.h structure

**IntegerComparison.h:**
- **Purpose:** Backward compatibility wrapper
- **Status:** Deprecated for new code
- **Migration:** Include comparison_ops.h directly
- **Breaking changes:** None

## Next Phase Readiness

**CODE-04 Compliance Status:**
- ✅ comparison_ops.h created
- ✅ IntegerComparison.h converted to wrapper
- ✅ All comparison tests pass
- ✅ Compilation successful

**Ready for:**
- Plan 09-04: Update module_deps.md with comparison_ops.h
- Future phases using comparison operations can include comparison_ops.h directly

**No blockers or concerns.**

## Lessons Learned

**What worked well:**
1. Following established pattern (arithmetic_ops.h) made implementation straightforward
2. Backward compatibility wrapper enabled zero-breaking-changes migration
3. Direct include in .c file clarifies dependencies
4. OWNERSHIP comments copied from original header maintain documentation quality

**Pattern refinements:**
- Consistent header naming: `*_ops.h` for operation modules
- Thin wrappers preserve compatibility during refactoring
- Module headers depend only on types.h (minimal dependencies)

**Reusable approach:**
- This pattern can be applied to remaining legacy headers (Integer.h, etc.)
- Backward compatibility wrapper pattern works well for gradual migration
- Direct .c includes make dependency chain explicit

## Performance Impact

**Compilation time:** No measurable change (header structure similar)
**Runtime:** Zero impact (same function declarations)
**Memory:** Zero impact (header-only changes)

## Documentation Updates Needed

- [ ] Update module_deps.md with comparison_ops.h entry (Plan 09-04 or later)
- [ ] Add comparison_ops.h to Backend/include/README if one exists
- [ ] Document backward compatibility status in migration guide

---

**Phase 09 Plan 02: COMPLETE**
Duration: 6.2 minutes | 3 commits | 0 deviations | 7 tests passing
