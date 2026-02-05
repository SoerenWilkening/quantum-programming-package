# Phase 6: Bit Operations - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add bitwise operations (AND, OR, XOR, NOT) for quantum integers with Python operator overloading. Operations must respect variable-width integers and generate circuits with reasonable depth.

</domain>

<decisions>
## Implementation Decisions

### Operation Semantics
- Binary operations (a & b, a | b, a ^ b) return NEW qint, preserving both operands
- Support qint & classical_int using binary representation of int (like CQ_add pattern, no qint wrapper)
- NOT (~qint) is bitwise inversion (flip every qubit), not logical NOT
- Augmented assignment supported (a &= b, a |= b, a ^= b) - requires ancilla, then swap qubit indices

### Width Handling
- Mixed-width operations use LARGER width (8-bit & 16-bit -> 16-bit result, smaller operand zero-extended)
- qint & classical_int: infer width from classical value (may widen result)
- NOT preserves input width (~qint(8) returns 8-bit)
- NO overflow warning for classical truncation in bitwise ops (silent truncation)

### Circuit Strategy
- AND/OR use Toffoli gates (one per bit pair), requires ancilla for output
- Ancilla qubits come from circuit allocator (track ownership per Phase 3 patterns)
- XOR: in-place (^=) uses CNOT directly; out-of-place (^) copies first then CNOTs
- NOT: in-place X gates applied directly to qubits (mutates the qint)

### Controlled Variants
- All operations have controlled versions: cAND, cOR, cXOR, cNOT
- Single control qubit only (no multi-control)
- Control must be qbool type (type safety)
- Python context manager syntax: `with ctrl: a & b` makes operations controlled

### Claude's Discretion
- Exact ancilla cleanup strategy after AND/OR operations
- Gate ordering for optimal circuit depth
- Internal naming conventions for C functions

</decisions>

<specifics>
## Specific Ideas

- Follow CQ_add pattern for classical-quantum operations: use binary representation directly, don't create qint for classical value
- Augmented assignment (a &= b) should swap qubit indices after operation completes to maintain variable binding

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 06-bit-operations*
*Context gathered: 2026-01-26*
