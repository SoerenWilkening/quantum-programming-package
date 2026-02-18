# Phase 30: Arithmetic Verification - Research

**Researched:** 2026-01-31
**Domain:** Exhaustive and representative verification of quantum arithmetic operations through full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check)
**Confidence:** HIGH

## Summary

Phase 30 verifies the correctness of all arithmetic operations: addition, subtraction, multiplication, floor division, modulo, and modular arithmetic (qint_mod). The Phase 28 verification framework (verify_circuit fixture, verify_helpers) is already implemented and proven working. Phase 29 fixed all known C backend bugs (BUG-01 through BUG-05) and the circuit() state leak, so batch test execution now works reliably -- 24/24 bugfix tests and 184/184 init tests pass in batch.

The standard addition and subtraction operations (both QQ and CQ variants) have been spot-tested in Phase 29 bugfix tests but not exhaustively verified. Multiplication was tested at a handful of cases. Division, modulo, and modular arithmetic have NOT been tested through the pipeline at all.

**Critical finding:** The `verify_circuit` fixture's `bitstring[:width]` result extraction works correctly for addition, subtraction, and multiplication (verified empirically). However, it does NOT work for division, modulo, or modular arithmetic operations, where the result register is allocated at non-standard qubit positions. Division/modulo/modular arithmetic tests will require custom result extraction or a modified approach.

**Primary recommendation:** Reuse the Phase 28 framework as-is for add/sub/mul tests. For div/mod/modular tests, either extend the verify_circuit fixture with a custom extraction parameter, or build self-contained test functions that handle their own simulation and extraction.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x+ | Test framework with parametrization | Already in use; Phase 28 framework built on it |
| Qiskit | 2.3.0 | OpenQASM import and circuit simulation | Already installed; `qiskit.qasm3.loads()` for QASM import |
| qiskit-aer | 0.17+ | Statevector simulator backend | Already in use; `AerSimulator(method='statevector')` for deterministic results |
| quantum_language | 0.1.0 | The project's quantum programming API | All operations under test |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| itertools | stdlib | Exhaustive pair generation | `itertools.product(range(2**width), repeat=2)` for all input pairs |
| random | stdlib | Deterministic sampling | `random.seed(42)` for reproducible representative tests at larger widths |
| verify_helpers | project | Input generation and failure formatting | `generate_exhaustive_pairs()`, `generate_sampled_pairs()`, `format_failure_message()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| verify_circuit fixture for div/mod | Custom test functions | verify_circuit assumes result at bitstring[:width]; div/mod result is elsewhere. Custom functions needed. |
| Parametrize at module level | Dynamic parametrize | Module-level is the established pattern from Phase 28 verify_init.py; keep consistent |

## Architecture Patterns

### Recommended Project Structure
```
tests/
  conftest.py            # Existing verify_circuit fixture (Phase 28)
  verify_helpers.py      # Existing input generators and formatting (Phase 28)
  verify_init.py         # Existing init tests (Phase 28)
  verify_add.py          # NEW: Addition verification (VARITH-01)
  verify_sub.py          # NEW: Subtraction verification (VARITH-02)
  verify_mul.py          # NEW: Multiplication verification (VARITH-03)
  verify_div.py          # NEW: Division verification (VARITH-04)
  verify_mod.py          # NEW: Modulo verification (VARITH-04)
  verify_modular.py      # NEW: Modular arithmetic verification (VARITH-05)
```

Note: The CONTEXT.md specifies file names as `test_add.py`, `test_sub.py`, etc. Either naming convention works with pytest, but the `verify_` prefix matches the established Phase 28 pattern (`verify_init.py`). The planner should use the CONTEXT.md names (`test_add.py`, etc.) since those are locked decisions.

### Pattern 1: Parametrized Exhaustive Tests (Add/Sub/Mul)

**What:** Module-level data generation for `@pytest.mark.parametrize`, same pattern as Phase 28 `verify_init.py`.

**When to use:** For add, sub, mul operations where `verify_circuit` fixture works correctly.

**Example:**
```python
# test_add.py
import pytest
from verify_helpers import (
    format_failure_message,
    generate_exhaustive_pairs,
    generate_sampled_pairs,
)
import quantum_language as ql

def _exhaustive_qq_add_cases():
    """Generate (width, a, b) for exhaustive QQ addition at widths 1-4."""
    cases = []
    for width in [1, 2, 3, 4]:
        for a, b in generate_exhaustive_pairs(width):
            cases.append((width, a, b))
    return cases

EXHAUSTIVE_QQ_ADD = _exhaustive_qq_add_cases()

@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ_ADD)
def test_qq_add_exhaustive(verify_circuit, width, a, b):
    """QQ addition: qint(a) + qint(b) at widths 1-4."""
    expected = (a + b) % (1 << width)

    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = qa + qb
        return (a + b) % (1 << w)

    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("qq_add", [a, b], width, exp, actual)
```

### Pattern 2: CQ Variant Tests

**What:** Tests for classical-quantum operations (qint + int, qint * int).

**When to use:** For CQ_add and CQ_mul variants.

**Example:**
```python
@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_CQ_ADD)
def test_cq_add_exhaustive(verify_circuit, width, a, b):
    """CQ addition: qint(a) += int(b) at widths 1-4."""
    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qa += b  # CQ_add path (int operand)
        return (a + b) % (1 << w)

    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("cq_add", [a, b], width, exp, actual)
```

### Pattern 3: Division/Modulo Tests (Custom Extraction)

**What:** Self-contained test functions that do NOT use the `verify_circuit` fixture, because the result register is not at `bitstring[:width]`.

**When to use:** For `//`, `%`, and `divmod` operations where result extraction is non-standard.

**Critical finding from research:** Division allocates: input (3 qubits) + quotient (3 qubits) + remainder (3 qubits) + ancillae (2 qubits) = 11 total for 3-bit. The quotient appears at qubit indices 3-5, which in the MSB-first bitstring (len=11) maps to positions [5:8]. This is NOT the standard first-width position.

**Recommended approach:** Instead of bitstring position math, build a helper that runs the pipeline and compares expected vs actual using the clean_circuit fixture with in-place operations, OR use a different extraction strategy.

**Safest approach:** Use `divmod()` which returns both quotient and remainder as separate qint objects. The last allocated qint's qubits will be at the highest indices (first in bitstring). Since divmod allocates quotient then remainder, the remainder is last and appears at bitstring[:width]. But quotient would be at a middle position.

**Alternative approach:** Test division via a round-trip: `a = qint(N); q = a // d; result = q * d`. If the pipeline correctly computes q, then q*d should match. However, this depends on multiplication being correct, creating a circular dependency.

**Most reliable approach:** Build a custom helper function that handles the full pipeline inline (same as verify_circuit but with custom extraction logic). The test can compute the expected bitstring layout based on the number of qubits.

**Example:**
```python
def _run_division_test(a_val, divisor, width):
    """Run division test with custom result extraction."""
    ql.circuit()
    a = ql.qint(a_val, width=width)
    q = a // divisor
    qasm = ql.to_openqasm()

    circuit = qiskit.qasm3.loads(qasm)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method='statevector')
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    # Division allocates: input(w) + quotient(w) + remainder(w) + ancillae
    # In MSB-first bitstring, quotient is NOT at first position
    # Need to determine position empirically or from allocation pattern
    total_qubits = len(bitstring)
    # ... custom extraction logic
```

### Pattern 4: Modular Arithmetic Tests

**What:** Tests for `qint_mod` operations (add, sub, mul with modulus N).

**When to use:** For VARITH-05.

**Key observations:**
- `qint_mod` extends `qint` -- the result register position is also non-standard (due to intermediate allocations for reduction)
- `qint_mod * qint_mod` raises `NotImplementedError` -- test should verify this
- Classical modulus N is known at circuit time
- Results must be < N (properly reduced)

### Anti-Patterns to Avoid

- **Using verify_circuit fixture for division/modulo/modular arithmetic:** Result extraction at `bitstring[:width]` does NOT work for these operations. Verified empirically: 6//2=3 but `bitstring[:3]` gives 6, not 3.
- **Assuming unsigned representation for all widths:** Values > 2^(width-1) trigger a `UserWarning: Value X exceeds N-bit range [-Y, Z]`. This is cosmetic (tests still work) but indicates the qint implementation uses two's complement internally while verification treats values as unsigned.
- **Testing division by zero:** Context says skip. `a // 0` raises `ZeroDivisionError` from Python, not a quantum circuit error.
- **Testing qint_mod * qint_mod as a failure:** It raises `NotImplementedError` by design. Test should assert the error is raised, not treat it as a bug.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exhaustive pair generation | Manual nested loops | `generate_exhaustive_pairs(width)` from verify_helpers.py | Already implemented, tested, and used in Phase 28 |
| Sampled pair generation | Custom sampling | `generate_sampled_pairs(width)` from verify_helpers.py | Already implemented with deterministic seed=42 |
| Failure messages | Ad-hoc f-strings | `format_failure_message()` from verify_helpers.py | Consistent format across all verification phases |
| Circuit simulation pipeline | Custom per-test | verify_circuit fixture from conftest.py | For add/sub/mul; standardized build-export-simulate-extract |
| Test parametrization | Manual loops inside tests | `@pytest.mark.parametrize` with module-level data | Established pattern; better failure isolation and reporting |

**Key insight:** Phase 28 built the framework specifically for this use case. For add/sub/mul, it works perfectly. For div/mod/modular, the framework needs extension or custom helpers -- but the simulation and QASM loading parts can still be reused.

## Common Pitfalls

### Pitfall 1: Result Extraction Mismatch for Division/Modulo

**What goes wrong:** Tests use `bitstring[:width]` to extract result, but division/modulo allocate multiple intermediate registers (quotient, remainder, comparison temporaries), placing the result at unpredictable bitstring positions.

**Why it happens:** Division's implementation (`qint_division.pxi`) allocates: `quotient = qint(0, width=self.bits)` then `remainder = qint(0, width=self.bits)` then performs comparison-based subtraction which allocates more qubits. The result qint's qubits are NOT at the highest indices (they're allocated early).

**How to avoid:**
- For division: do NOT use verify_circuit fixture. Build custom test helpers.
- Empirically verified positions for 3-bit division: quotient at bitstring[5:8] (qubits 3-5 in 11-qubit circuit).
- Best approach: build a small calibration test first that verifies extraction positions for each operation at a known width, then use that offset for all tests.

**Warning signs:** Tests pass for some inputs (e.g., quotient 0 or 1) but fail for others (accidental bit overlap).

### Pitfall 2: UserWarning for Values Exceeding Signed Range

**What goes wrong:** `ql.qint(value, width=w)` emits `UserWarning: Value X exceeds N-bit range [-Y, Z]` for values >= 2^(w-1). This clutters test output.

**Why it happens:** qint internally uses two's complement representation, but the verification treats values as unsigned.

**How to avoid:**
- Add `warnings.filterwarnings("ignore", message="Value .* exceeds")` at module level in test files, OR use `@pytest.mark.filterwarnings("ignore::UserWarning")` decorator
- This is cosmetic -- the values still encode correctly (verified by init tests passing for all unsigned values 0-255 at 8-bit width)

**Warning signs:** Test output is overwhelmed with warnings, making it hard to see actual failures.

### Pitfall 3: Test Count Explosion

**What goes wrong:** Exhaustive testing at 4-bit width generates 256 pairs (for binary ops). For multiplication at 4 bits, 256 tests each taking ~0.2s = 51 seconds. At 5 bits, 1024 tests = 205 seconds.

**Why it happens:** Combinatorial explosion of input pairs.

**How to avoid:**
- Context decisions already handle this: exhaustive at 1-4 bits for add/sub, 1-3 bits for mul
- Sampled at 5+ bits: ~10 random pairs + boundary values per width
- For division: even slower (comparison-based circuit), so limit exhaustive testing
- Expected test counts:
  - Addition: 2+16+256+65536 (exhaustive 1-4) = huge at 4 bits. Use (2+16+64+256) = 338 for exhaustive 1-4 with pairs. Actually: 2^1=2 values, pairs=4; 2^2=4, pairs=16; 2^3=8, pairs=64; 2^4=16, pairs=256. Total: 340 pairs per variant (QQ and CQ).
  - Multiplication: 2^1 pairs=4; 2^2=16; 2^3=64. Total: 84 pairs per variant.
  - Division/modulo: classical divisors only, exhaustive at 1-3 bits, sampled at 4.

**Warning signs:** Test suite takes >5 minutes to run.

### Pitfall 4: Closure Variable Capture in Parametrized Tests

**What goes wrong:** `circuit_builder` captures loop variable by reference, causing all tests to use the last iteration's values.

**Why it happens:** Python closure scoping captures the variable name, not the value.

**How to avoid:** Use default argument binding: `def circuit_builder(a=a, b=b, w=width):` -- this is the established pattern from Phase 28 verify_init.py.

**Warning signs:** All parametrized tests produce the same result regardless of input parameters.

### Pitfall 5: Division Divisor Range

**What goes wrong:** Testing division with divisors > 2^width or divisors that produce quotients > 2^width.

**Why it happens:** Division's restoring algorithm uses `divisor << bit_pos` which can exceed the qubit register width.

**How to avoid:**
- Only test classical divisors from 1 to 2^width - 1 (skip 0)
- Context says: skip division-by-zero test cases
- Verify quotient fits in width bits: `a // d < 2^width`

**Warning signs:** Circuit generation errors or incorrect results for large divisors.

### Pitfall 6: Modular Arithmetic with Result Register Position

**What goes wrong:** `qint_mod` operations allocate intermediate qubits for reduction (comparison + conditional subtraction), shifting the result register position.

**Why it happens:** `_reduce_mod()` allocates comparison result qubits internally. The final wrapped `qint_mod` result may reference qubits that are not at the highest indices.

**How to avoid:** Same approach as division -- do not use `verify_circuit` fixture. Use custom extraction.

**Warning signs:** Results look partially correct (some modular add tests pass, others fail with seemingly random values).

## Code Examples

### Addition Test (QQ variant, using verify_circuit)
```python
# Source: Adapted from Phase 28 verify_init.py pattern + Phase 29 bugfix tests
import pytest
from verify_helpers import format_failure_message, generate_exhaustive_pairs, generate_sampled_pairs
import quantum_language as ql

def _exhaustive_qq_add_cases():
    cases = []
    for width in [1, 2, 3, 4]:
        for a, b in generate_exhaustive_pairs(width):
            cases.append((width, a, b))
    return cases

EXHAUSTIVE_QQ_ADD = _exhaustive_qq_add_cases()

@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ_ADD)
def test_qq_add_exhaustive(verify_circuit, width, a, b):
    expected = (a + b) % (1 << width)
    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa + qb
        return (a + b) % (1 << w)
    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("qq_add", [a, b], width, exp, actual)
```

### Subtraction Test (with underflow wrapping)
```python
@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ_SUB)
def test_qq_sub_exhaustive(verify_circuit, width, a, b):
    expected = (a - b) % (1 << width)  # Unsigned wrap
    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa - qb
        return (a - b) % (1 << w)
    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("qq_sub", [a, b], width, exp, actual)
```

### Multiplication Test (QQ variant)
```python
# Exhaustive at 1-3 bits only (per CONTEXT.md)
def _exhaustive_qq_mul_cases():
    cases = []
    for width in [1, 2, 3]:
        for a, b in generate_exhaustive_pairs(width):
            cases.append((width, a, b))
    return cases

EXHAUSTIVE_QQ_MUL = _exhaustive_qq_mul_cases()

@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ_MUL)
def test_qq_mul_exhaustive(verify_circuit, width, a, b):
    expected = (a * b) % (1 << width)
    def circuit_builder(a=a, b=b, w=width):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _r = qa * qb
        return (a * b) % (1 << w)
    actual, exp = verify_circuit(circuit_builder, width)
    assert actual == exp, format_failure_message("qq_mul", [a, b], width, exp, actual)
```

### NotImplementedError Test (qint_mod * qint_mod)
```python
def test_qint_mod_mul_qint_mod_raises(clean_circuit):
    """Verify qint_mod * qint_mod raises NotImplementedError."""
    x = ql.qint_mod(5, N=7)
    y = ql.qint_mod(3, N=7)
    with pytest.raises(NotImplementedError, match="qint_mod .* qint_mod"):
        _ = x * y
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tests fail in batch (circuit state leak) | Tests pass in batch (circuit() properly resets) | Phase 29-15 (2026-01-31) | All 184 init tests and 24 bugfix tests now pass in batch |
| Subtraction used self.value (init value) | Subtraction uses quantum state correctly | Phase 29 pre-existing fix | Subtraction correctness restored |
| QQ_mul had inverted targets + wrong b-qubit mapping | QQ_mul rewritten with correct CCP decomposition | Phase 29-17 | Multiplication correctness restored |
| QFT addition applied phase to wrong qubits | Phase rotations corrected | Phase 29 pre-existing fix | Addition correctness restored |
| Comparison had MSB index error + GC reversal | Three root causes fixed | Phase 29-16 | Comparison correctness (needed for division) |

**Dependencies resolved from Phase 29:**
- BUG-01 (subtraction): FIXED -- critical for subtraction verification and division (which uses subtraction internally)
- BUG-02 (comparison): FIXED -- critical for division/modulo (which use `>=` comparison)
- BUG-03 (multiplication): FIXED -- critical for multiplication verification
- BUG-04 (QFT addition): FIXED -- critical for addition verification
- BUG-05 (circuit reset): FIXED -- critical for batch test execution

## Open Questions

1. **Division/Modulo Result Extraction Position**
   - What we know: The `verify_circuit` fixture's `bitstring[:width]` does NOT extract the correct value for division and modulo. Empirically, for 3-bit `a // d`, the quotient appears at bitstring[5:8] in an 11-qubit circuit.
   - What's unclear: Whether the position is stable across different widths and divisors. The position depends on qubit allocation order (input, quotient, remainder, comparison ancillae), which may vary.
   - Recommendation: Build a calibration step: for each width, run a known-good case (e.g., `4 // 2 = 2`) and empirically determine the extraction position. Alternatively, test division via self-contained functions that handle extraction. **The planner must decide the approach.**

2. **Modular Arithmetic Result Extraction**
   - What we know: `qint_mod` operations also produce results NOT at `bitstring[:width]`. Tested `5+4 mod 7`: first 3 bits gave 6 (wrong), expected 2.
   - What's unclear: Same issue as division -- result register position depends on internal allocations.
   - Recommendation: Same calibration approach as division. Or test modular arithmetic via a different extraction method.

3. **Test Runtime for Division at 4-bit Exhaustive**
   - What we know: 4-bit division takes ~0.27s per test. Exhaustive at 4-bit with all (value, divisor) pairs where divisor in 1..15: 16*15=240 tests = ~65 seconds.
   - What's unclear: Whether Qiskit simulation scales linearly or super-linearly with circuit depth.
   - Recommendation: Start with exhaustive at 1-3 bits, sampled at 4 bits. Adjust if runtime is excessive.

4. **Whether `in_place=True` Parameter is Needed for Any Arithmetic Test**
   - What we know: The `verify_circuit` fixture has an `in_place` parameter (added for NOT operations in Phase 28). Arithmetic tests use out-of-place operations (result = a + b), so `in_place=False` (default) should be correct.
   - What's unclear: Whether any arithmetic variant (e.g., `a += b`) needs `in_place=True`.
   - Recommendation: Use default `in_place=False` for all out-of-place tests. For in-place variants (`+=`, `-=`, `*=`), the result is stored in the same qint, so extraction should still work at `bitstring[:width]` if the qint's qubits are at the highest indices. **Needs empirical verification for in-place variants.**

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/quantum_language/qint_arithmetic.pxi` -- addition, subtraction, multiplication implementations
- Codebase inspection: `src/quantum_language/qint_division.pxi` -- division, modulo, divmod implementations
- Codebase inspection: `src/quantum_language/qint_mod.pyx` -- modular arithmetic (add, sub, mul with mod N)
- Codebase inspection: `tests/conftest.py` -- verify_circuit fixture implementation
- Codebase inspection: `tests/verify_helpers.py` -- input generation and failure formatting
- Codebase inspection: `tests/verify_init.py` -- established test pattern
- Codebase inspection: `tests/bugfix/test_bug*.py` -- bug fix verification tests (Phase 29)
- Phase 28 research: `.planning/phases/28-verification-framework-init/28-RESEARCH.md`
- Phase 29 verification: `.planning/phases/29-c-backend-bug-fixes/29-18-SUMMARY.md`
- Empirical testing: Ran verify_init.py (184/184 pass), bugfix tests (24/24 pass)
- Empirical testing: Tested result extraction for add, sub, mul, div, mod, and qint_mod operations

### Secondary (MEDIUM confidence)
- Phase 30 CONTEXT.md -- locked decisions for coverage strategy, operation variants, failure handling

### Tertiary (LOW confidence)
- Division result register position analysis -- based on 3-4 bit empirical testing only; may not generalize to all widths

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools already installed and verified working
- Architecture: HIGH -- framework proven in Phase 28, patterns established
- Pitfalls: HIGH -- verified empirically through actual test execution
- Division/modulo extraction: LOW -- known problem identified, solution approach uncertain

**Research date:** 2026-01-31
**Valid until:** 90 days (framework is stable; Qiskit API is mature)
