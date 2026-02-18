# Phase 24: Element-wise Operations - Context

**Gathered:** 2026-01-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement element-wise arithmetic, bitwise, and comparison operators between quantum arrays of equal shape, with scalar broadcasting and in-place variants. Broadcasting beyond scalars (shape broadcasting) is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Scalar broadcasting
- Scalar operands supported for all operations: `arr + 5`, `arr * 3`, `arr > 5`
- Both Python int and single qint scalars accepted: `arr + 5` and `arr + q` both work
- Only scalar broadcasting — no shape broadcasting (e.g., (3,1) + (1,4) is NOT supported)
- Shapes must match exactly for array-array operations; scalar is the only exception
- Scalar int is auto-converted to qint with width matching the array's element width

### Result width rules
- Result width is max of input widths: `8-bit + 16-bit = 16-bit`
- No automatic width expansion for overflow: `8-bit + 8-bit = 8-bit` (wraps modularly)
- qbool promoted to qint(width=1) for mixed-type bitwise operations
- Mixed dtype result is always qint (qint dominates over qbool)

### Comparison result type
- All six comparison operators supported: `<`, `<=`, `>`, `>=`, `==`, `!=`
- Comparisons return qbool array (not qint 0/1)
- Scalar comparisons supported: `arr > 5` broadcasts like arithmetic
- qbool array comparisons supported: `bool_arr == other_bool_arr` returns qbool array

### In-place mutation semantics
- True in-place mutation: `A += B` modifies A's quantum elements via gates, no new array allocated
- In-place supported for arithmetic and bitwise only: `+=`, `-=`, `*=`, `&=`, `|=`, `^=`
- No in-place comparison operators (semantically meaningless)
- In-place scalar operations supported: `A += 5` adds 5 to every element in-place

### Claude's Discretion
- Width mismatch behavior for in-place operations (error vs widen A)
- Internal dispatch pattern (single method vs per-operator methods)
- Error message formatting for shape mismatches
- Operator method organization within qarray.pyx

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing qint operator patterns and NumPy element-wise semantics where applicable.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-element-wise-operations*
*Context gathered: 2026-01-29*
