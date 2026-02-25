# Phase 92: Modular Toffoli Arithmetic - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement fault-tolerant modular arithmetic operations (add, sub, multiply mod N) on `qint_mod` using Toffoli gates. These are Shor's algorithm building blocks. `qint_mod` is a separate type inheriting from `qint` that maintains the invariant: value is always in [0, N-1]. All operations auto-reduce results mod N. Depends on Phase 91 bug fixes (orphan-qubit pattern).

</domain>

<decisions>
## Implementation Decisions

### Operator API & Type Mixing
- `qint_mod` type "infects" results: any operation involving a `qint_mod` returns `qint_mod`
- `qint_mod + int` returns `qint_mod` (modular type always wins)
- `qint_mod + qint` returns `qint_mod` (plain qint treated like int operand)
- `qint_mod + qint_mod` with **same N**: returns `qint_mod(N)`
- `qint_mod + qint_mod` with **different N**: raises `ValueError` (mismatched moduli)
- Supported operators: `+`, `-`, `*` (and in-place `+=`, `-=`, `*=`), unary `-`
- Comparisons: inherit from `qint` as-is (==, <, >, etc.) — values always in [0, N-1] so comparisons are meaningful

### Subtraction Semantics
- True modular subtraction: result always in [0, N-1]
- When a < b: `(a - b) mod N` = `(a - b + N)`, not two's complement wrap
- Example: `qint_mod(3, N=5) - qint_mod(4, N=5)` = `qint_mod(4, N=5)` (since 3-4+5=4)
- Both quantum-quantum (qint_mod - qint_mod) and classical-quantum (qint_mod - int) supported
- Both in-place (`a -= b`) and out-of-place (`c = a - b`) supported
- Negation supported: `-qint_mod(3, N=5)` = `qint_mod(2, N=5)` (computes N - a)

### Multiplication Signature
- Classical-quantum: `qint_mod * int` via standard `*` operator (both `a * 3` and `3 * a`)
- Quantum-quantum: `qint_mod * qint_mod` also supported (same N required)
- Both in-place (`a *= c`) and out-of-place (`c = a * b`) supported
- Controlled modular multiply supported: `with flag: a *= 3` (not just controlled add)
- Multiply by 0 returns `qint_mod(0, N)` (mathematically correct, no error)

### Validation & Error Policy
- N must be >= 2 (N=0 and N=1 raise `ValueError` at construction)
- N must fit in signed 64-bit integer (N <= 2^63 - 1, matching C backend int64_t)
- Width too small for N: auto-widen to `N.bit_length()` (with warning)
- Width larger than `N.bit_length()`: allowed (user may want extra bits)
- Initial value >= N: auto-reduce classically at construction (e.g., `qint_mod(7, N=5)` holds 2)
- Qubit budget validation deferred to circuit execution (matches existing qint behavior)
- Mismatched moduli in binary operations: `ValueError`

### Claude's Discretion
- Ancilla allocation strategy for modular operations
- Internal RCA enforcement mechanism (success criteria requires RCA, not CLA)
- Modular reduction algorithm details (Beauregard conditional subtraction)
- Circuit optimization for controlled variants
- QQ modular multiply algorithm choice (repeated controlled modular addition vs other approaches)
- Warning mechanism for auto-widening (print, logging, etc.)

</decisions>

<specifics>
## Specific Ideas

- `qint_mod` is a distinct type inheriting from `qint`, not just a flag on `qint`
- The type invariant (value always in [0, N-1]) is the core design principle — every operation maintains it
- Operator overloading follows Python conventions: left operand type preference, but modular type always wins over plain types
- Controlled operations (via `with` block) should work for both addition and multiplication

</specifics>

<deferred>
## Deferred Ideas

- Modular exponentiation (`a^e mod N`) — future phase (Shor's full algorithm)
- Modular inverse (`a^-1 mod N`) — future phase
- Arbitrarily large N (beyond int64_t) — not needed for near-term simulation

</deferred>

---

*Phase: 92-modular-toffoli-arithmetic*
*Context gathered: 2026-02-25*
