---
phase: 14-ordering-comparisons
plan: 01
subsystem: python-binding
tags: [cython, comparison, qbool, ordering, less-than, greater-than]

# Dependency graph
requires:
  - phase: 13-equality-comparison
    provides: Subtract-add-back pattern and operand preservation technique
provides:
  - qint < int/qint comparison using in-place subtract-MSB-add-back pattern
  - qint > int/qint comparison using in-place pattern or delegate to <=
  - qint <= int/qint comparison using in-place subtract-MSB-OR-zero-add-back pattern
  - qint >= int/qint comparison using NOT(self < other)
  - Self-comparison optimizations for all four operators
  - Overflow handling for out-of-range classical values
affects: [14-ordering-comparisons-tests, future-phases-using-comparisons]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - In-place subtract-add-back pattern extended to ordering comparisons
    - MSB inspection for two's complement sign determination
    - Self-comparison optimization (a < a = False, a <= a = True)

key-files:
  created: []
  modified:
    - python-backend/quantum_language.pyx

key-decisions:
  - "Use in-place subtract-add-back pattern for all ordering operators"
  - "Check MSB (sign bit) for negative detection in two's complement"
  - "Combine MSB check with zero check for <= (negative OR zero)"
  - "Delegate __gt__ int operand to NOT(self <= other) for efficiency"
  - "Optimize self-comparisons to return directly without gates"

patterns-established:
  - "Ordering comparison pattern: self -= other, check MSB, self += other"
  - "MSB extraction: self[64 - self.bits] for right-aligned storage"
  - "OR combination: result ^= is_negative; temp ^= is_zero; result |= temp"

# Metrics
duration: 2min
completed: 2026-01-27
---

# Phase 14 Plan 01: Refactor Ordering Comparisons Summary

**All four ordering comparison operators (<, >, <=, >=) refactored to use in-place subtract-add-back pattern without temporary qint allocation, preserving both operands**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-27T21:36:58Z
- **Completed:** 2026-01-27T21:39:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Eliminated all temporary qint allocations from ordering comparison operators
- All four operators preserve both operands after comparison
- Self-comparison optimizations reduce gate count for identity cases
- Classical overflow handling provides early returns for out-of-range values
- Phase 13 equality tests pass (29/29) - no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor __lt__ to use in-place subtract-MSB-add-back pattern** - `a5bce11` (refactor)
2. **Task 2: Refactor __gt__, __le__, __ge__ to use in-place patterns** - `4c111f5` (refactor)
3. **Task 3: Verify operand preservation and run existing tests** - `df25d1c` (test)

## Files Created/Modified
- `python-backend/quantum_language.pyx` - Refactored __lt__, __gt__, __le__, __ge__ methods to eliminate temporary qint allocation

## Decisions Made

**1. Use in-place subtract-add-back pattern for all ordering operators**
- Rationale: Eliminates qubit allocation overhead, follows Phase 13 pattern
- Impact: Consistent memory-efficient implementation across all comparisons

**2. Check MSB (sign bit) for negative detection in two's complement**
- Rationale: Two's complement representation uses MSB as sign bit
- Impact: Direct sign inspection without additional gates

**3. Combine MSB check with zero check for <= operator**
- Rationale: a <= b means (a - b) is negative OR zero
- Impact: Uses Phase 13's zero-check via self == 0, then ORs with MSB

**4. Delegate __gt__ int operand to NOT(self <= other)**
- Rationale: More efficient than implementing separate subtract-check logic
- Impact: Reduces code duplication, maintains consistency

**5. Optimize self-comparisons to return directly without gates**
- Rationale: Identity comparisons have known results (x < x = False, x <= x = True)
- Impact: Zero gate overhead for self-comparison cases

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - refactoring followed established patterns from Phase 13.

## Next Phase Readiness

- All four ordering comparison operators working without temporary allocations
- Ready for Phase 14-02: Ordering comparison tests
- Operand preservation verified for both qint-qint and qint-int cases
- No known blockers or concerns

---
*Phase: 14-ordering-comparisons*
*Completed: 2026-01-27*
