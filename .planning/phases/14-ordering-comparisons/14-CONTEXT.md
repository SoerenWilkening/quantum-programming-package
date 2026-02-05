# Phase 14: Ordering Comparisons - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `<=`, `>=`, `<`, and `>` operators for qint using in-place subtraction/addition without temporary qint allocation. Comparisons use two's complement signed interpretation. Both qint-int and qint-qint operand combinations supported.

</domain>

<decisions>
## Implementation Decisions

### Comparison Semantics
- Support both qint-int and qint-qint operand combinations
- Both operands preserved after comparison (subtract-add-back pattern)
- Reversed operand order (e.g., `5 <= qint`) supported via `__ge__` reflection
- Different bit widths allowed — zero-extend smaller operand

### All Four Operators
- Implement `__le__`, `__ge__`, `__lt__`, `__gt__` in this phase
- All use the same in-place subtract-check-add-back pattern
- Consistent behavior across all ordering operators

### In-place Pattern
- Compute `a - b` in-place
- Check MSB for sign (two's complement) AND check if result is zero
- For `a <= b`: true if (a - b) is negative OR equal to zero
- For `a < b`: true if (a - b) is negative
- Add back after comparison to restore both operands
- Python-level implementation only (no C-level CQ_* functions needed)

### Two's Complement Interpretation
- qint uses two's complement representation
- Comparisons are signed — MSB is sign bit
- Negative values are valid operands

### Edge Cases
- Self-comparison (a <= a): optimize, return True directly (no gates)
- Out-of-range classical value (e.g., 4-bit qint <= 100): return True (always less)
- Classical value out of range for `>=`: return False (always greater)

### Claude's Discretion
- Exact implementation of MSB + zero check combination
- How to handle mixed bit-width zero-extension efficiently
- Test coverage breadth

</decisions>

<specifics>
## Specific Ideas

- Use same subtract-add-back pattern established in Phase 13 for equality
- MSB sign inspection combined with non-zero check for ordering determination

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-ordering-comparisons*
*Context gathered: 2026-01-27*
