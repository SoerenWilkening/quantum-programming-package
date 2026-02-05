# Phase 13: Equality Comparison - Context

**Gathered:** 2026-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement efficient equality comparison for qint == int and qint == qint using the refactored CQ_equal_width functions from Phase 12. Returns a quantum boolean (qbool) that can be used as a control for subsequent operations. Ordering comparisons (<=, >=) are Phase 14.

</domain>

<decisions>
## Implementation Decisions

### Result Representation
- Allocate a new result qubit for each comparison (holds |1⟩ if equal, |0⟩ if not)
- Result qubit is auto-managed by the qint system (freed when associated qint is freed)
- Multiple comparisons can be active simultaneously on the same qint (each allocates new qubit)
- Track computation for automatic uncomputation support

### Operator Behavior
- `==` returns a quantum boolean object (qbool) wrapping the result qubit
- qbool raises error if used in classical boolean context (no implicit measurement)
- qbool integrates with existing `with qbool:` framework for controlled operations
- Implement `!=` (__ne__) alongside `==` — returns qbool with opposite sense (X gate on == result)

### Width Mismatch Handling
- Auto-extend smaller qint to match larger (conceptual, not physical allocation)
- Missing high bits treated as |0⟩ in comparison logic
- For qint == classical_int overflow: return "definitely not equal" result (result qubit stays |0⟩)
- Error on negative classical values (qint is unsigned)

### qint == qint Approach
- Use (a - b) == 0 pattern: compute a -= b in-place, compare to 0, then a += b to restore
- Both operands preserved after comparison (add-back uncompute)
- Self-comparison (a == a) optimized: detect same qint, return result qubit set to |1⟩ directly

### Claude's Discretion
- Exact qbool class implementation details
- How uncomputation tracking integrates with existing memory management
- Internal gate sequence construction

</decisions>

<specifics>
## Specific Ideas

- qbool should work with existing `with qbool:` controlled operation framework
- In-place subtract then add-back approach for qint == qint avoids temp allocation

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-equality-comparison*
*Context gathered: 2026-01-27*
