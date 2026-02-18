# Phase 7: Extended Arithmetic - Context

**Gathered:** 2026-01-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete multiplication and add division, modulo, and modular arithmetic operations for variable-width quantum integers. Includes comparison operators (>, <, ==, >=, <=) returning qbool results.

</domain>

<decisions>
## Implementation Decisions

### Comparison Operators
- Return type is qbool (quantum boolean for further quantum operations)
- Support classical-quantum comparisons both directions (qint < int and int < qint)
- Optimized equality circuit for == (dedicated simpler circuit, not subtraction-based)
- Mixed-width comparisons zero-extend the smaller operand (8-bit vs 16-bit treated as 16-bit comparison)
- Result qbool allocated as ancilla from circuit allocator

### Division Semantics
- Implement via repeated subtraction/comparison at Python level (per arXiv:1809.09732 approach)
- No new C primitives needed — use existing add, subtract, compare operations
- Division by zero raises Python exception before circuit generation
- Both divmod(a, b) returning (quotient, remainder) tuple AND separate // and % operators
- Classical divisor supported (a // 5 works, enables optimizations)

### Modular Arithmetic API
- New qint_mod type that carries modulus N
- Modulus N is classical only (Python int, known at circuit generation time)
- Supported operations: modular add, subtract, multiply
- Mixed operands allowed: qint_mod + qint works, result is qint_mod
- Operations between qint_mod values require matching N

### Multiplication Result Width
- Result width is max of operand widths (8-bit * 16-bit = 16-bit)
- Silent modular wrap on overflow (like C unsigned arithmetic)
- Classical * quantum supported both directions (int * qint and qint * int)
- In-place *= supported but allocates new qubits (qubit reference swap pattern like bitwise ops)

### Claude's Discretion
- Specific circuit implementations for comparison operators
- Whether to use QFT-based or ripple-carry approaches
- Internal ancilla management for intermediate computations
- Optimization of classical-quantum operations

</decisions>

<specifics>
## Specific Ideas

- "Division via repeated subtraction/comparison at Python level" — reference arXiv:1809.09732 and existing old_div pattern
- qint_mod type should feel natural: `x = qint_mod(5, N=17)` then `x + y` just works

</specifics>

<deferred>
## Deferred Ideas

- Modular exponentiation — more complex, consider for future phase
- Quantum modulus N (where N itself is a qint) — significantly more complex circuits

</deferred>

---

*Phase: 07-extended-arithmetic*
*Context gathered: 2026-01-26*
