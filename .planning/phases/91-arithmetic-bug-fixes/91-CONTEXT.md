# Phase 91: Arithmetic Bug Fixes - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix division and modular reduction to produce correct results without orphan qubits or circuit corruption. Three specific bugs: BUG-DIV-02 (division MSB uncomputation), BUG-QFT-DIV (QFT division/modulo correctness), and BUG-MOD-REDUCE (modular reduction orphan qubits). QFT division/modulo are replaced entirely by a new classical-gate-based divmod. No new arithmetic capabilities — strictly fixing and replacing broken operations.

</domain>

<decisions>
## Implementation Decisions

### Modular reduction approach
- Implement at C level (not Python)
- Use classical-gate-based addition internally (Toffoli/CNOT — Claude picks specific variant: ripple-carry, CLA, etc.)
- Support arbitrary moduli N (including even values and powers of 2)
- Classical N is the primary implementation; quantum N (N in superposition) is a stretch goal
- Bounded ancilla acceptable: up to n persistent ancillae per call (n = register width)
- Ancilla count hidden from Python callers — internal management only
- Fully reversible (supports adjoint/inverse)
- Include single-control variant (one control qubit) for use in modular exponentiation
- Include debug-mode assertions that verify ancilla state before uncomputation (disabled in release)
- Delete the broken Python-level `_reduce_mod` entirely once C implementation is ready — no fallback

### Division fix strategy
- Full rewrite at C level (not a patch)
- Restoring division algorithm
- Divmod output: single operation produces both quotient and remainder
- Support quantum divisor (divisor in superposition)
- Division by zero produces all-ones (quotient = max value) as sentinel
- Include debug-mode assertions for uncomputation verification
- Include single-control variant
- Build on existing C arithmetic primitives; optimize for least cycles (circuit depth)
- Include single-control variant for use in larger algorithms

### QFT division replacement
- Replace QFT division entirely with new classical-gate-based divmod — do not fix QFT division
- Delete all QFT division code entirely (git history preserves it)
- QFT modulo also replaced: modulo = divmod remainder, delete QFT modulo code
- Expose new Python divmod API function
- Keep old `divide()` and `modulo()` Python functions as wrappers around new divmod for backwards compatibility
- Only division and modulo QFT operations are in scope — other QFT arithmetic operations stay untouched
- Benchmark before removal: compare old QFT vs new classical-gate divmod
  - Metrics: gate count, circuit depth, ancilla usage, T-gate count
  - Widths: 2-4 only
  - Save benchmark results to a file in the repo

### Verification approach
- Exhaustive testing: all input combinations for widths 2-4 via Qiskit simulation
- Reversibility tests: run operation then its inverse, verify return to initial state
- Before/after `circuit_stats()['current_in_use']` assertion per operation (must be stable within bounded ancilla tolerance)
- Run arithmetic-related test suite for zero-regression check (not full test suite)

### Claude's Discretion
- Composition strategy for C-level modular reduction (standalone function vs composed from primitives)
- Specific classical-gate adder variant (ripple-carry, CLA, etc.) — pick what fits existing codebase
- C-level API design for modular reduction (single `mod_reduce` vs separate `mod_add`/`mod_subtract`)
- Temp file handling and benchmark file location
- Exact ancilla budget optimization within the n-qubit bound

</decisions>

<specifics>
## Specific Ideas

- "Write the C code based on the existing arithmetic operations. Algorithm should pick the fastest (least cycles) implementation as possible"
- Division by zero sentinel: all-ones (max value), not all-zeros
- Quantum divisor and quantum N are both desired but with different priority levels (quantum divisor = hard requirement, quantum N = stretch goal)
- Benchmark results should be persisted as a file, not just logged

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 91-arithmetic-bug-fixes*
*Context gathered: 2026-02-24*
