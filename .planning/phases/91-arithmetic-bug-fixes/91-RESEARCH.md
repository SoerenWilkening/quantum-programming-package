# Phase 91: Arithmetic Bug Fixes - Research

**Researched:** 2026-02-24
**Domain:** Quantum arithmetic circuit correctness (division, modulo, modular reduction)
**Confidence:** HIGH

## Summary

Phase 91 fixes three related bugs in the quantum arithmetic subsystem: BUG-DIV-02 (division MSB comparison temporary leak), BUG-QFT-DIV (QFT division/modulo incorrectness, replaced by classical-gate divmod), and BUG-MOD-REDUCE (modular reduction orphan qubits in `_reduce_mod`). All three bugs share a root cause pattern: comparison operations (`>=`) inside division/modulo loops create widened temporary qint registers (comp_width = bits+1) whose qubits leak because the uncomputation mechanism does not cascade-free temporaries with `operation_type=None` and `creation_scope=0`.

The user has decided on a full-rewrite approach at the C level for division (restoring division algorithm producing both quotient and remainder) and a C-level modular reduction using classical gates (Toffoli/CNOT). The existing QFT division and modulo code will be deleted entirely and replaced by the new classical-gate divmod. The broken Python `_reduce_mod` in `qint_mod.pyx` will also be deleted and replaced by the C-level implementation.

**Primary recommendation:** Implement a C-level restoring divmod circuit that handles both classical and quantum divisors, with proper ancilla management (allocate + free within the operation). Replace QFT division/modulo entirely. Implement C-level modular reduction using the new Toffoli arithmetic primitives. Delete all broken Python-level division/modulo/reduction code.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Modular reduction: Implement at C level (not Python)
- Use classical-gate-based addition internally (Toffoli/CNOT)
- Support arbitrary moduli N (including even values and powers of 2)
- Classical N is the primary implementation; quantum N (N in superposition) is a stretch goal
- Bounded ancilla acceptable: up to n persistent ancillae per call (n = register width)
- Ancilla count hidden from Python callers -- internal management only
- Fully reversible (supports adjoint/inverse)
- Include single-control variant (one control qubit) for modular exponentiation
- Include debug-mode assertions that verify ancilla state before uncomputation (disabled in release)
- Delete the broken Python-level `_reduce_mod` entirely once C implementation is ready -- no fallback
- Division: Full rewrite at C level (not a patch)
- Restoring division algorithm
- Divmod output: single operation produces both quotient and remainder
- Support quantum divisor (divisor in superposition)
- Division by zero produces all-ones (quotient = max value) as sentinel
- Include debug-mode assertions for uncomputation verification
- Include single-control variant
- Build on existing C arithmetic primitives; optimize for least cycles (circuit depth)
- QFT division replacement: Replace QFT division entirely with new classical-gate-based divmod
- Delete all QFT division code entirely (git history preserves it)
- QFT modulo also replaced: modulo = divmod remainder, delete QFT modulo code
- Expose new Python divmod API function
- Keep old `divide()` and `modulo()` Python functions as wrappers around new divmod for backwards compatibility
- Only division and modulo QFT operations are in scope -- other QFT arithmetic operations stay untouched
- Benchmark before removal: compare old QFT vs new classical-gate divmod (metrics: gate count, circuit depth, ancilla usage, T-gate count; widths 2-4)
- Exhaustive testing: all input combinations for widths 2-4 via Qiskit simulation
- Reversibility tests: run operation then its inverse, verify return to initial state
- Before/after `circuit_stats()['current_in_use']` assertion per operation
- Run arithmetic-related test suite for zero-regression check (not full test suite)

### Claude's Discretion
- Composition strategy for C-level modular reduction (standalone function vs composed from primitives)
- Specific classical-gate adder variant (ripple-carry, CLA, etc.) -- pick what fits existing codebase
- C-level API design for modular reduction (single `mod_reduce` vs separate `mod_add`/`mod_subtract`)
- Temp file handling and benchmark file location
- Exact ancilla budget optimization within the n-qubit bound

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIX-01 | Division correctly uncomputes MSB comparison temporaries (BUG-DIV-02) | C-level restoring divmod eliminates Python-level comparison temporary leak entirely by managing all ancillae internally |
| FIX-02 | QFT division/modulo produces correct results for all tested widths (BUG-QFT-DIV) | QFT division replaced entirely by classical-gate divmod; correctness verified exhaustively for widths 2-4 |
| FIX-03 | Modular reduction produces correct (a+b) mod N without orphan qubits (BUG-MOD-REDUCE) | C-level modular reduction with internal ancilla management replaces broken Python `_reduce_mod` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| C backend (c_backend/) | Current | Quantum circuit gate sequences | Project's own C backend generates optimized gate sequences |
| Cython (_core.pyx, qint.pyx) | Current | Python-C bridge | Project uses Cython for Python API to C backend binding |
| Toffoli arithmetic (ToffoliAdditionCDKM.c) | Current | CDKM ripple-carry adder | Already proven correct; divmod and mod_reduce will compose from these |
| qubit_allocator.c | Current | Ancilla allocation/deallocation | Used by multiplication; divmod will use same pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Qiskit + Aer | Current | Simulation verification | Exhaustive testing of all input combinations |
| pytest | Current | Test framework | All verification tests |

## Architecture Patterns

### Existing C Arithmetic Pattern (follow for divmod)
The project has a well-established pattern for C-level arithmetic:

1. **Sequence-based operations** (e.g., `toffoli_QQ_add`): Return `sequence_t*` with gate layers. Cached for width-only variants, caller-frees for value-dependent variants.
2. **Direct-emit operations** (e.g., `toffoli_mul_qq`): Take `circuit_t*` and qubit arrays, emit gates directly. Used when the operation requires dynamic ancilla allocation.

Divmod and modular reduction should use the **direct-emit pattern** (like multiplication) because they need dynamic ancilla allocation via `allocator_alloc`/`allocator_free`.

### Qubit Layout Convention
```
C function receives physical qubit indices via arrays.
Python (Cython) maps logical qint qubits to physical indices using
qubits[64-bits+i] (right-aligned 64-element array).
Ancillae are allocated via circuit_get_allocator() + allocator_alloc().
```

### Controlled Operation Pattern
The project uses two patterns for controlled operations:
1. **AND-ancilla pattern** (multiplication): CCX(and_anc, ctrl, other_bit), use and_anc as control, CCX again to uncompute. Used when composing controlled additions.
2. **ext_ctrl parameter** (toffoli_cQQ_add): Control qubit injected into every gate of the sequence.

For divmod, use the AND-ancilla pattern at the loop level (same as multiplication does).

### Python-level Division/Modulo Dispatch
Currently in `qint_division.pxi`:
- `__floordiv__` handles classical and quantum divisors
- `__mod__` handles classical and quantum divisors
- `__divmod__` handles both

After Phase 91: These will call a new C-level divmod function (via Cython), similar to how multiplication calls `toffoli_mul_qq`/`toffoli_mul_cq`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Addition within divmod | Custom adder | `toffoli_QQ_add` / `toffoli_CQ_add` | Already proven correct, cached |
| Comparison within divmod | Custom comparator | Subtraction + MSB check (widened) | Standard quantum comparison, but manage ancillae properly |
| Ancilla allocation | Manual index tracking | `allocator_alloc` / `allocator_free` | Used by multiplication, handles fragmentation |
| Controlled addition | Custom controlled gates | `toffoli_cQQ_add` / `toffoli_cCQ_add` | Already have AND-ancilla decomposition |

## Common Pitfalls

### Pitfall 1: Comparison Temporary Leak (the actual bug)
**What goes wrong:** The `>=` operator in the division loop creates widened temporary qints (comp_width = bits+1) via `qint(0, width=comp_width)`. These temps allocate qubits but are never freed because uncomputation doesn't cascade to temporaries with `operation_type=None`.
**Why it happens:** Python-level division composes high-level operations (`>=`, `with`, `-=`, `+=`) that each independently allocate/use qubits. The comparison allocates widened temps, but the uncomputation mechanism only reverses gates -- it doesn't free the underlying qubit allocations.
**How to avoid:** C-level divmod manages all ancillae explicitly: allocate before the loop, use throughout, free after the loop. No Python-level temporaries involved.
**Warning signs:** `circuit_stats()['current_in_use']` growing with each division operation.

### Pitfall 2: Restoring Division Correctness
**What goes wrong:** Non-restoring division algorithms can leave the remainder register in an incorrect state.
**Why it happens:** If a trial subtraction makes the remainder negative but isn't properly undone, subsequent iterations work with wrong values.
**How to avoid:** Use restoring division: trial subtract, check sign (MSB of widened result), conditionally add back. The quotient bit is set based on the sign check result.
**Warning signs:** Incorrect quotient/remainder for large dividends or small divisors.

### Pitfall 3: Modular Reduction Iteration Count
**What goes wrong:** `_reduce_mod` uses `max_subtractions.bit_length()` iterations which is insufficient for some inputs, or the comparison within reduction itself leaks.
**Why it happens:** The number of conditional subtractions needed depends on the input value range and modulus. Too few iterations leave values unreduced; the comparison within each iteration compounds the ancilla leak problem.
**How to avoid:** C-level implementation: for modular reduction of an n-bit value mod N, at most one conditional subtraction is needed if the input is known to be in [0, 2N). For general input from addition (a+b where a,b < N), the sum is at most 2N-2, so a single conditional subtraction suffices.
**Warning signs:** Results consistently off by N or 2N.

### Pitfall 4: Qubit Array Bounds
**What goes wrong:** The global `qubit_array` in Cython has a fixed size. Complex operations with many ancillae can overflow it.
**Why it happens:** Division with quantum divisor at width 4 can need 30+ qubits total.
**How to avoid:** C-level operations use their own qubit mapping, not the global Cython `qubit_array`. Pass physical qubit indices directly.
**Warning signs:** Segfault or corrupt gate targets in QASM output.

### Pitfall 5: 17-Qubit Simulation Limit
**What goes wrong:** Tests with too many qubits fail or hang during Qiskit simulation.
**Why it happens:** Project constraint: max 17 qubits for statevector simulation; MPS supports more but is slower.
**How to avoid:** Use MPS simulator with transpilation for tests exceeding 17 qubits. Division at width 4 with quantum divisor needs ~30+ qubits, so use MPS. Width 2-3 classical divisor should stay under 17 qubits.
**Warning signs:** Simulation hangs or memory errors.

## Code Examples

### Existing Toffoli Multiplication Pattern (direct-emit, to follow for divmod)
```c
// From ToffoliMultiplication.c -- the pattern divmod should follow
void toffoli_mul_qq(circuit_t *circ, const unsigned int *ret_qubits, int ret_bits,
                    const unsigned int *self_qubits, int self_bits,
                    const unsigned int *other_qubits, int other_bits) {
    qubit_allocator_t *alloc = circuit_get_allocator((circuit_s *)circ);
    // Allocate carry ancilla
    unsigned int carry = allocator_alloc(alloc, 1, true);

    // ... loop over multiplier bits, using controlled adders ...

    // Free ancilla
    allocator_free(alloc, carry, 1);
}
```

### Existing Comparison Pattern (what's broken -- for reference)
```python
# From qint_comparison.pxi -- the >= that leaks
def __lt__(self, other):
    # Creates widened temps that leak:
    comp_width = max(self.bits, other.bits) + 1
    temp_self = qint(0, width=comp_width)    # LEAKS
    temp_other = qint(0, width=comp_width)   # LEAKS
    # ... subtract and check MSB ...
```

### Restoring Division Algorithm (for C implementation)
```
// Pseudocode for restoring division: dividend / divisor = quotient, remainder
// Input: dividend (n bits), divisor (n bits, or classical)
// Output: quotient (n bits), remainder (n bits)
// Ancilla: comparison result (1 bit), carry (1 bit), widened temps (~n bits)

remainder = dividend  // Copy via CNOT
for bit_pos = n-1 downto 0:
    trial_value = divisor << bit_pos  // Classical shift if classical divisor
    // Compare: remainder >= trial_value
    // This is where the bug was -- must manage ancillae properly
    sign_bit = compute_comparison(remainder, trial_value)
    // Conditional subtraction + quotient bit set
    controlled_subtract(remainder, trial_value, sign_bit)
    controlled_set_bit(quotient, bit_pos, sign_bit)
    // Uncompute comparison ancillae
    uncompute_comparison(sign_bit)
```

## Open Questions

1. **Quantum divisor circuit depth**
   - What we know: Quantum divisor division requires `2^n` iterations in the current implementation (repeated subtraction). This is exponential.
   - What's unclear: Whether the restoring division algorithm can be adapted for quantum divisors efficiently.
   - Recommendation: For quantum divisors, use the same restoring division loop structure but with quantum-quantum comparison and controlled subtraction. The circuit will be large but correct. Width 2 is feasible (4 iterations); width 3 (8 iterations) may be at simulation limits.

2. **Modular reduction ancilla budget**
   - What we know: For inputs in [0, 2N-2] (result of a+b where a,b < N), a single conditional subtraction of N suffices.
   - What's unclear: Whether the user expects the mod_reduce to handle arbitrary inputs (not just a+b results).
   - Recommendation: Implement for the common case (input < 2N), which covers addition/subtraction results. Document the input range assumption.

3. **Benchmark file location**
   - What we know: User wants benchmark results saved to a file.
   - What's unclear: Exact location.
   - Recommendation: Save to `benchmarks/divmod_benchmark.md` alongside existing benchmark files.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `qint_division.pxi`, `qint_mod.pyx`, `qint_comparison.pxi` -- direct reading of buggy code
- Codebase analysis: `ToffoliAdditionCDKM.c`, `ToffoliMultiplication.c` -- established C-level patterns
- Codebase analysis: `test_div.py`, `test_mod.py`, `test_toffoli_division.py`, `test_modular.py` -- known failure sets
- Codebase analysis: `qubit_allocator.c`, `circuit_stats.c` -- ancilla management infrastructure

### Secondary (MEDIUM confidence)
- Quantum arithmetic textbook knowledge: Restoring division algorithm, Beauregard modular reduction

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all components exist in codebase, well-understood
- Architecture: HIGH - following established multiplication pattern
- Pitfalls: HIGH - bugs are well-documented with known-failure test sets

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable internal codebase)
