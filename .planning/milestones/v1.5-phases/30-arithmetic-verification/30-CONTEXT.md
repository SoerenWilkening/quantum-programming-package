# Phase 30: Arithmetic Verification - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Exhaustively verify all arithmetic operations through the full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check). Operations: addition, subtraction, multiplication, floor division, modulo, and modular arithmetic (qint_mod). This phase verifies correctness — it does not fix bugs or add features.

</domain>

<decisions>
## Implementation Decisions

### Coverage strategy
- Exhaustive testing at 1-4 bit widths for add, subtract, div, mod (all input pairs)
- Multiplication exhaustive at 1-3 bits, sampled at 4-5 bits (larger circuits)
- Larger widths (5-8 bits): boundary values (0, 1, max-1, max) plus ~10 random pairs per width
- Operations tested in priority order: add -> subtract -> multiply -> div -> mod -> modular arithmetic
- Stop testing an operation category on persistent failure, continue to next category

### Operation variants
- Addition: QQ_add and CQ_add variants
- Subtraction: QQ and CQ variants (via addition with invert flag)
- Multiplication: QQ_mul and CQ_mul variants
- Floor division: classical divisors only (quantum divisors have exponential complexity — skip)
- Modulo: classical divisors only (same rationale as division)
- Modular arithmetic: qint_mod add, sub, mul with classical modulus N (mul limited to qint_mod * int)

### Failure handling
- Continue collecting all failures within an operation before moving to next
- Standard pytest output with parameterized test IDs — failures show expected vs actual per case
- One test file per operation category: test_add.py, test_sub.py, test_mul.py, test_div.py, test_mod.py, test_modular.py
- Reuse Phase 28 verification framework (conftest fixtures and helpers) as-is

### Overflow & edge cases
- All arithmetic uses unsigned wrap (mod 2^n) for overflow and underflow
- Subtraction underflow wraps: e.g., 3-7 on 4 bits = 12
- Skip division-by-zero test cases (undefined in quantum context)
- qint_mod tests verify both correctness AND that results are properly reduced (result < N)

### Claude's Discretion
- Exact random seed / sample selection for representative tests at larger widths
- Test file internal organization (fixture usage, helper functions)
- Whether to add any framework helpers for modular arithmetic if existing ones don't cover it

</decisions>

<specifics>
## Specific Ideas

- Priority ordering matches dependency chain: addition is foundational, subtraction uses addition, multiplication builds on both
- Division/modulo are Python-only (no C backend) — still verify through full OpenQASM pipeline
- qint_mod * qint_mod raises NotImplementedError — test should verify that error, not treat it as a failure

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-arithmetic-verification*
*Context gathered: 2026-01-31*
