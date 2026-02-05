# Phase 44: Array Mutability - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

In-place augmented assignment for qarray elements via indexing (`qarray[i] += x`, `qarray[i, j] -= x`, etc.). Users can modify existing qarray elements without allocating new element qubits. Whole-array augmented assignment (`qarray_a += qarray_b`) and quantum indexing (QRAM) are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Operator coverage
- Support ALL augmented operators that qint supports: `+=`, `-=`, `*=`, `//=`, `<<=`, `>>=`, `&=`, `|=`, `^=`
- Truly in-place operations (modify element qubits directly): `+=`, `-=`, `^=`
- Ancilla+swap operations (compute on ancilla, swap into element slot): `*=`, `//=`, `<<=`, `>>=`, `&=`, `|=`
- After swap, ancilla holding old value is released dirty (no uncomputation)

### Operand types & widths
- Classical int operands use classical control (parameterize quantum circuit directly, no temporary qint)
- Mixed bit widths: match existing qint operator behavior (whatever the standalone op does)
- qbool operands: match existing qint operator behavior (whatever qint does when given qbool)

### Error handling
- Out-of-bounds index: raise IndexError
- Unsupported operator (e.g., `**=`): raise NotImplementedError
- `x = qarray[i]; x += 1` modifies local copy only, NOT the array element — only `qarray[i] += 1` modifies in-place
- Overflow: match existing qint behavior (modular arithmetic expected)

### Multi-dimensional semantics
- Multi-dim indexing depth: match existing qarray `__getitem__` depth support
- Slice-based augmented assignment supported: `qarray[1:3] += x`
  - Single scalar x: broadcast to each element in slice
  - Array operand x: element-wise, lengths must match
- Index type: classical integers only (no quantum indices)

### Claude's Discretion
- `__setitem__` implementation strategy (how to intercept augmented assignment in Cython)
- Internal dispatch mechanism for routing operators
- Temporary qubit management details for ancilla+swap pattern

</decisions>

<specifics>
## Specific Ideas

- `+=` and `-=` use QFT-based addition/subtraction directly on the element's qubits (truly in-place)
- `^=` is truly in-place via CNOT
- All other ops compute result on ancilla register, then SWAP qubits into the element's slot, then release ancilla dirty
- Classical int operands should parameterize the circuit directly (classical control), not be loaded into temporary qint

</specifics>

<deferred>
## Deferred Ideas

- Quantum indexing (`qarray[qint_index] += x`) — future phase, requires QRAM-style implementation
- Whole-array augmented assignment (`qarray_a += qarray_b`) — separate capability

</deferred>

---

*Phase: 44-array-mutability*
*Context gathered: 2026-02-03*
