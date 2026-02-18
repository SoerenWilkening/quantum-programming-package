# Phase 42: Quantum Copy Foundation - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

CNOT-based quantum state copy for qint and qbool. Users can create quantum copies via `.copy()` method. This phase builds the copy infrastructure; Phase 43 integrates it into binary operations so that `b = a + 13` auto-copies `a` behind the scenes.

</domain>

<decisions>
## Implementation Decisions

### Copy API surface
- `.copy()` method on both qint and qbool
- No parameters — always copies all qubits, same bit width as source
- qbool.copy() returns qbool (preserves type), qint.copy() returns qint
- Usable inline in expressions (returns a qint/qbool that works in arithmetic)

### Copy semantics
- CNOT entanglement (standard quantum copy, not cloning)
- `.copy()` allocates fresh qubits in |0⟩, applies CNOTs from source
- `.copy_onto(target)` also supported — XOR-copies onto existing qubits (target must be same bit width, error on mismatch)
- Copy of a copy allowed freely — no restrictions or warnings

### Qubit lifecycle
- Copies participate in scope-based automatic uncomputation
- Uncomputation reverses the CNOTs (standard inverse), then releases qubits in |0⟩
- Layer tracking set on copy (consistent with Phase 41 infrastructure)
- If source goes out of scope before copy, the copy becomes independent (no error)

### Integration with expressions
- Works inside with-blocks — copy gets uncomputed on scope exit
- Can be used inline in expressions (e.g., `a.copy() + b`)
- Primary use case: foundation for Phase 43's automatic copy in binary ops — users rarely call .copy() directly
- Tests verify computational basis states only (copy of |3⟩ gives |3⟩)

### Claude's Discretion
- Internal CNOT gate ordering and optimization
- How .copy_onto() validates target state
- Exact layer tracking implementation details
- Test structure and organization

</decisions>

<specifics>
## Specific Ideas

- "Running qint.copy() shouldn't be necessary. In b = a + 13, a copy of 'a' will be generated automatically" — .copy() is the building block, Phase 43 makes it implicit in binary ops
- .copy() is still public API for explicit copies outside arithmetic contexts

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 42-quantum-copy-foundation*
*Context gathered: 2026-02-02*
