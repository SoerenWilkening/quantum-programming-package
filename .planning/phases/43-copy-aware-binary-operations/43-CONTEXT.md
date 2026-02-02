# Phase 43: Copy-Aware Binary Operations - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Binary operations on qint and qarray preserve quantum state by using quantum copy instead of classical value initialization. The `.copy()` and `.copy_onto()` primitives from Phase 42 are used internally. In-place augmented assignment (`+=`, `-=`, etc.) is deferred to Phase 44.

</domain>

<decisions>
## Implementation Decisions

### Operation scope
- All arithmetic ops: `+`, `-`, `*`, `//`, `%`
- All bitwise ops: `&`, `|`, `^`, `~`, `<<`, `>>`
- Unary ops: `__neg__`, `__abs__`
- Comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`) are **excluded** — they return qbool, different pattern
- In-place ops (`__iadd__`, etc.) are **deferred to Phase 44**

### Operand handling
- For `qint op qint`: quantum-copy one operand into fresh qubits as the result base, then apply the other operand's operation onto it. Only one copy needed — not both operands.
- For `qint op int` and `int op qint`: always quantum-copy the qint operand into the result, then apply the classical int value.
- Reverse ops (`__radd__`, `__rsub__`, etc.) follow the same rule: quantum-copy the qint operand.
- Original operands must be unmodified after any binary operation.

### qarray behavior
- `qarray op qarray`: copy all elements of the left array into the result, then apply right array elements onto the result. Both source arrays preserved.
- Scalar broadcast (`qarray + int`, `qarray + qint`): copy each element into the result, then apply the scalar operation.
- qarray supports the same full set of operations as qint — all arithmetic + bitwise + unary, element-wise.
- Length mismatch between two qarrays raises `ValueError` — strict and explicit, no truncation or padding.

### Claude's Discretion
- Which operand to use as the copy base (left vs right) for each specific operation
- Internal optimization: whether to skip copy when the operand is already a temporary
- Test structure and parametrization approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The key invariant is: after any binary op, the original operands' quantum state must be intact and the result must contain CNOT gates (not classical reinitialization).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. In-place operations are already scoped to Phase 44.

</deferred>

---

*Phase: 43-copy-aware-binary-operations*
*Context gathered: 2026-02-02*
