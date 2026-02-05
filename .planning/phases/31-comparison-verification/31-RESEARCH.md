# Phase 31: Comparison Verification - Research

**Researched:** 2026-01-31
**Domain:** Exhaustive verification of all six comparison operators (==, !=, <, >, <=, >=) across CQ and QQ variants through the full pipeline (Python -> C circuit -> OpenQASM 3.0 -> Qiskit simulate -> result check)
**Confidence:** HIGH

## Summary

Phase 31 verifies the correctness of all six comparison operators across both qint-vs-int (CQ) and qint-vs-qint (QQ) variants. The Phase 28 verification framework (`verify_circuit` fixture, `verify_helpers`) is already proven working. Phase 29 plan 16 fixed all three root causes of BUG-02 (MSB index error, GC gate reversal, unsigned overflow), and the six BUG-02 regression tests all pass.

All comparison operators return a `qbool` (1-bit qint). The result is the last allocated qubit in the circuit, so `verify_circuit(circuit_builder, width=1)` correctly extracts the boolean result at `bitstring[:1]`. This is empirically verified by the 6 existing BUG-02 tests. No custom extraction logic is needed for the boolean result -- the standard `verify_circuit` fixture works as-is with `width=1`.

Operand preservation verification (checking that input qints are not corrupted after comparison) requires a different approach. The `verify_circuit` fixture only extracts the last-allocated register. To verify operand preservation, a custom pipeline helper is needed that examines the full bitstring at the positions of the input operand registers. However, the comparison implementations use subtract-add-back patterns that are mathematically guaranteed to restore operands. Empirical verification through the full pipeline adds confidence but requires custom extraction.

**Primary recommendation:** Use `verify_circuit(circuit_builder, width=1)` for all comparison boolean result tests (the proven BUG-02 pattern). For operand preservation, build a separate custom helper that extracts input register bits from the full bitstring. The BUG-02 regression suite should be a separate test class/section with sub-cases per root cause.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x+ | Test framework with parametrization | Already in use; Phase 28/30 framework built on it |
| Qiskit | 2.3.0 | OpenQASM import and circuit simulation | Already installed; `qiskit.qasm3.loads()` for QASM import |
| qiskit-aer | 0.17+ | Statevector simulator backend | Already in use; `AerSimulator(method='statevector')` for deterministic results |
| quantum_language | 0.1.0 | The project's quantum programming API | All comparison operators under test |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| itertools | stdlib | Exhaustive pair generation | `itertools.product(range(2**width), repeat=2)` for all input pairs |
| random | stdlib | Deterministic sampling | `random.seed(42)` for reproducible representative tests at larger widths |
| verify_helpers | project | Input generation and failure formatting | `generate_exhaustive_pairs()`, `generate_sampled_pairs()`, `format_failure_message()` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| verify_circuit with width=1 | Custom pipeline helper | verify_circuit works perfectly for boolean results; no need for custom extraction |
| Separate operand preservation tests | Combined boolean+preservation per test | Separate tests are cleaner; combined tests need custom pipeline helper |

## Architecture Patterns

### Recommended Project Structure

```
tests/
  conftest.py               # Existing verify_circuit fixture (Phase 28)
  verify_helpers.py          # Existing input generators and formatting (Phase 28)
  verify_init.py             # Existing init tests (Phase 28)
  test_add.py ... test_mod.py  # Existing arithmetic verification (Phase 30)
  test_compare.py            # NEW: All 6 comparison operators, CQ and QQ, exhaustive+sampled
  test_compare_preservation.py  # NEW: Operand preservation tests (optional, see Open Questions)
  bugfix/
    test_bug02_comparison.py # Existing BUG-02 regression (6 tests) -- keep as-is
```

Note: CONTEXT.md says the test file organization is Claude's discretion. A single `test_compare.py` file is recommended over six separate files (one per operator) because:
1. All operators share the same test structure and data generation
2. A single file with clear sections reduces duplication
3. The Phase 30 pattern uses one file per operation category (test_add.py, test_sub.py, etc.)

### Pattern 1: Comparison Boolean Result Test (using verify_circuit)

**What:** Parametrized tests for each comparison operator, using `verify_circuit(circuit_builder, width=1)` to extract the 1-bit boolean result.

**When to use:** For all comparison result verification tests.

**Example:**
```python
# Source: Adapted from tests/bugfix/test_bug02_comparison.py (proven pattern)
import warnings
import pytest
from verify_helpers import format_failure_message, generate_exhaustive_pairs, generate_sampled_pairs
import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")

OPS = {
    'eq': lambda a, b: int(a == b),
    'ne': lambda a, b: int(a != b),
    'lt': lambda a, b: int(a < b),
    'gt': lambda a, b: int(a > b),
    'le': lambda a, b: int(a <= b),
    'ge': lambda a, b: int(a >= b),
}

QL_OPS = {
    'eq': lambda qa, qb: qa == qb,
    'ne': lambda qa, qb: qa != qb,
    'lt': lambda qa, qb: qa < qb,
    'gt': lambda qa, qb: qa > qb,
    'le': lambda qa, qb: qa <= qb,
    'ge': lambda qa, qb: qa >= qb,
}

def _exhaustive_qq_cases():
    """Generate (width, a, b, op_name) for all operators at widths 1-4."""
    cases = []
    for width in [1, 2, 3, 4]:
        for a, b in generate_exhaustive_pairs(width):
            for op_name in OPS:
                cases.append((width, a, b, op_name))
    return cases

EXHAUSTIVE_QQ = _exhaustive_qq_cases()

@pytest.mark.parametrize("width,a,b,op_name", EXHAUSTIVE_QQ)
def test_qq_cmp_exhaustive(verify_circuit, width, a, b, op_name):
    """QQ comparison: qint(a) op qint(b) at widths 1-4 bits."""
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = op(qa, qb)
        return OPS[op_name](a, b)

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(
        f"qq_{op_name}", [a, b], width, exp, actual
    )
```

**Design choice -- all 6 operators per (a,b) pair vs separate:** Testing all 6 operators per (a,b) pair in one parametrized test (with `op_name` as a parameter) is the most efficient approach. Each test case is still independently reported by pytest. Total test count: `(4+16+64+256) * 6 = 2040` for exhaustive QQ at widths 1-4.

### Pattern 2: CQ Comparison Tests

**What:** Tests for classical-quantum comparisons (qint op int).

**When to use:** For CQ comparison variants.

**Example:**
```python
@pytest.mark.parametrize("width,a,b,op_name", EXHAUSTIVE_CQ)
def test_cq_cmp_exhaustive(verify_circuit, width, a, b, op_name):
    """CQ comparison: qint(a) op int(b) at widths 1-4 bits."""
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op):
        qa = ql.qint(a, width=w)
        _result = op(qa, b)  # b is plain int (CQ path)
        return OPS[op_name](a, b)

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(
        f"cq_{op_name}", [a, b], width, exp, actual
    )
```

### Pattern 3: BUG-02 Regression Suite

**What:** Dedicated regression tests for the three BUG-02 root causes.

**When to use:** In a separate section of the test file or as a dedicated class.

**Example:**
```python
class TestBug02Regression:
    """BUG-02 regression: three root causes fixed in Phase 29-16."""

    def test_msb_index_fix(self, verify_circuit):
        """Root cause 1: MSB at index 63 (not 64-width) in right-aligned storage."""
        def circuit_builder():
            x = ql.qint(3, width=4)
            y = ql.qint(5, width=4)
            _result = x < y  # Uses MSB check
            return 1
        actual, expected = verify_circuit(circuit_builder, width=1)
        assert actual == expected

    def test_gc_gate_reversal_fix(self, verify_circuit):
        """Root cause 2: comparison results must not have layer tracking."""
        def circuit_builder():
            x = ql.qint(5, width=4)
            y = ql.qint(5, width=4)
            _result = x <= y  # Was affected by GC reversal
            return 1
        actual, expected = verify_circuit(circuit_builder, width=1)
        assert actual == expected

    def test_unsigned_overflow_fix(self, verify_circuit):
        """Root cause 3: (n+1)-bit widened comparison for full unsigned range."""
        def circuit_builder():
            x = ql.qint(0, width=4)
            y = ql.qint(15, width=4)
            _result = x <= y  # 0 <= 15, was broken by n-bit overflow
            return 1
        actual, expected = verify_circuit(circuit_builder, width=1)
        assert actual == expected
```

### Pattern 4: Sampled Tests at Larger Widths (5-8 bits)

**What:** Boundary pairs + random sampled pairs for representative coverage.

**Example:**
```python
def _sampled_cases():
    """Generate (width, a, b, op_name) for widths 5-8 with boundary + random pairs."""
    cases = []
    for width in [5, 6, 7, 8]:
        max_val = (1 << width) - 1
        boundary_pairs = [(0, 0), (0, max_val), (max_val, 0), (max_val, max_val)]
        sampled = generate_sampled_pairs(width, sample_size=10)
        all_pairs = sorted(set(sampled) | set(boundary_pairs))
        for a, b in all_pairs:
            for op_name in OPS:
                cases.append((width, a, b, op_name))
    return cases
```

### Pattern 5: Operand Preservation Test (Custom Pipeline)

**What:** Custom helper that runs comparison through the pipeline and checks that input operand bits are preserved in the final bitstring.

**When to use:** For VCMP requirement that inputs are not corrupted.

**Example:**
```python
import qiskit.qasm3
from qiskit_aer import AerSimulator

def _verify_preservation(width, a, b, op_name):
    """Run QQ comparison and verify both operands are preserved.

    Qubit layout for QQ comparison (most operators):
      - qint a: width qubits (allocated first, at highest bitstring positions)
      - qint b: width qubits (allocated second)
      - qbool result: 1 qubit (allocated last, at bitstring[:1])
      - For __gt__: additional (width+1)-bit temporaries from widened comparison

    Returns (a_preserved, b_preserved, bool_result).
    """
    ql.circuit()
    qa = ql.qint(a, width=width)
    qb = ql.qint(b, width=width)
    ql_op = QL_OPS[op_name]
    _result = ql_op(qa, qb)
    qasm_str = ql.to_openqasm()

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    n = len(bitstring)
    # a is allocated first -> highest qubit indices -> last `width` chars of bitstring
    a_bits = bitstring[n - width : n]
    a_val = int(a_bits, 2)
    # b is allocated second -> next `width` chars
    b_bits = bitstring[n - 2 * width : n - width]
    b_val = int(b_bits, 2)
    # Result qbool is at bitstring[:1] (last allocated, highest index)
    bool_result = int(bitstring[0], 2)

    return a_val, b_val, bool_result
```

**IMPORTANT caveat:** The qubit layout for `__gt__` QQ path allocates additional (n+1)-bit widened temporaries (`temp_other`, `temp_self`). For `__le__` and `__ge__` (which delegate to `__gt__` and `__lt__` respectively), the circuit may have additional qubits. The operand preservation extraction positions need empirical calibration per operator.

**Recommended approach for operand preservation:**
1. Run a calibration case (known a, b values) for each operator to empirically determine bitstring positions
2. Verify extraction positions match expectations
3. Use those positions for the remaining tests

### Anti-Patterns to Avoid

- **Using width > 1 for comparison result extraction:** All comparisons return qbool (1 bit). Always use `verify_circuit(circuit_builder, width=1)`.
- **Assuming identical qubit layout across all operators:** `__gt__` allocates extra temporaries. `__eq__` QQ path uses subtract-add-back + CQ_equal(0). Different operators have different circuit sizes.
- **Testing CQ `__gt__` separately from QQ `__gt__`:** CQ `__gt__` internally creates a temp qint and delegates to QQ `__gt__`. The CQ test exercises the QQ path too, but with the overhead of a temp qint allocation.
- **Not binding closure variables with defaults:** `def circuit_builder(a=a, b=b, w=width):` is required; without default binding, Python closures capture by reference and all tests use the last iteration's values.
- **Forgetting `_result = ...` in circuit_builder:** The comparison result must be assigned to a variable to prevent Python from GC-ing it during circuit_builder execution. The `_result` variable keeps the qbool alive.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exhaustive pair generation | Manual nested loops | `generate_exhaustive_pairs(width)` from verify_helpers.py | Already implemented and proven in Phase 28/30 |
| Sampled pair generation | Custom sampling | `generate_sampled_pairs(width, sample_size=10)` from verify_helpers.py | Deterministic seed=42, boundary values included |
| Failure messages | Ad-hoc f-strings | `format_failure_message()` from verify_helpers.py | Consistent format across all verification phases |
| Circuit simulation pipeline | Custom per-test | verify_circuit fixture from conftest.py | Standardized build-export-simulate-extract for boolean results |
| Expected comparison results | Manual expected value tables | Python native operators (`int(a == b)`, `int(a < b)`, etc.) | The oracle is Python itself -- zero chance of transcription errors |

**Key insight:** Comparison verification is simpler than arithmetic verification because:
1. The result is always 1 bit (qbool), so `verify_circuit` with `width=1` works for all operators
2. Python's native comparison operators serve as the oracle -- no manual expected value computation
3. No custom extraction needed for the boolean result (unlike division/modulo in Phase 30)

## Common Pitfalls

### Pitfall 1: Test Count Explosion with 6 Operators

**What goes wrong:** Testing all 6 operators for all pairs at all widths creates a very large test suite.

**Why it happens:** 6 operators x 2 variants (CQ, QQ) x (4+16+64+256 pairs at widths 1-4) = 4080 exhaustive tests. With sampled tests at 5-8 bits, total could exceed 5000.

**How to avoid:**
- This is the intended coverage per CONTEXT.md decisions
- Expected test counts:
  - Exhaustive QQ: 340 pairs x 6 ops = 2040 tests
  - Exhaustive CQ: 340 pairs x 6 ops = 2040 tests
  - Sampled QQ (5-8 bits): ~30 pairs/width x 4 widths x 6 ops = ~720 tests
  - Sampled CQ (5-8 bits): ~720 tests
  - BUG-02 regression: ~3-6 tests
  - Operand preservation: ~30-50 tests (representative subset)
  - **Total: ~5500+ tests**
- Each test takes ~0.1-0.3s; total runtime ~10-25 minutes
- Use `pytest -x` for early failure detection during development

**Warning signs:** Test suite takes >30 minutes to run.

### Pitfall 2: __gt__ QQ Path Has Extra Qubit Allocations

**What goes wrong:** Operand preservation tests assume a simple `2*width + 1` qubit layout, but `__gt__` QQ path allocates `2*(width+1)` extra qubits for widened temporaries.

**Why it happens:** The BUG-02 fix for unsigned overflow uses (n+1)-bit widened subtraction. This allocates `temp_other = qint(0, width=comp_width)` and `temp_self = qint(0, width=comp_width)` where `comp_width = max(self.bits, other.bits) + 1`. These temporaries add `2*(width+1)` qubits to the circuit.

**How to avoid:**
- For boolean result tests: Not an issue. `verify_circuit(circuit_builder, width=1)` always works because the qbool is the last allocated qubit.
- For operand preservation: Use empirical calibration per operator (run known case, verify bitstring layout).
- Operators with extra allocations: `__gt__` (QQ path), `__le__` (delegates to `__gt__`), `__ne__` (delegates to `__eq__`), `__ge__` (delegates to `__lt__`)

**Warning signs:** Operand preservation tests fail with seemingly random values for `__gt__` and `__le__` while `__lt__` and `__eq__` work.

### Pitfall 3: CQ __gt__ and CQ __le__ Create Temporary qints

**What goes wrong:** The CQ path for `__gt__` creates a `temp = qint(other, width=self.bits)` and delegates to the QQ path. CQ `__le__` delegates to `~(self > other)` which also creates this temp. This means the CQ path has additional qubit allocations compared to a simple CQ circuit.

**Why it happens:** The Phase 29-16 fix for circular dependency changed CQ `__gt__` to create a temp qint instead of delegating to `__le__`.

**How to avoid:**
- For boolean results: Not an issue (verify_circuit with width=1 works).
- For operand preservation: the extra temporary shifts bitstring positions. Calibrate per operator.
- The CQ `__eq__` and CQ `__lt__` paths do NOT create temporary qints (they use direct C functions or in-place subtract-add-back), so they have simpler qubit layouts.

**Warning signs:** CQ `__gt__` operand preservation tests fail while CQ `__lt__` passes.

### Pitfall 4: __ne__ and __le__ and __ge__ Are Delegation-Only Operators

**What goes wrong:** Tests for `__ne__`, `__le__`, and `__ge__` are effectively re-testing their delegate operators.

**Why it happens:**
- `__ne__` = `~(self == other)` -- exercises `__eq__` + NOT
- `__le__` = `~(self > other)` -- exercises `__gt__` + NOT
- `__ge__` = `~(self < other)` -- exercises `__lt__` + NOT

**How to avoid:** Still test all 6 operators for completeness (they could break independently if delegation changes), but be aware that failures in `__ne__` likely trace back to `__eq__`, etc.

**Warning signs:** `__ne__` fails exactly where `__eq__` gives the inverted wrong answer.

### Pitfall 5: UserWarning Noise for Values >= 2^(width-1)

**What goes wrong:** `ql.qint(value, width=w)` emits `UserWarning: Value X exceeds N-bit range` for values >= 2^(w-1).

**Why it happens:** qint internally uses two's complement while verification treats values as unsigned.

**How to avoid:** Add `warnings.filterwarnings("ignore", message="Value .* exceeds")` at module level. This is the established Phase 30 pattern.

### Pitfall 6: Self-Comparison Optimization Bypass

**What goes wrong:** `a == a`, `a < a`, `a > a`, `a <= a`, `a >= a` all have self-comparison optimizations that return classical qbool without generating any circuit.

**Why it happens:** When `self is other`, the comparison returns a constant qbool (True/False) without any quantum gates. This means no circuit is generated, and `ql.to_openqasm()` may produce an empty or minimal circuit.

**How to avoid:** Always use two separate qint objects: `qa = ql.qint(a, width=w); qb = ql.qint(b, width=w)`. Never do `qa < qa`.

**Warning signs:** Tests with `a == b` where `a` and `b` have the same value fail because `to_openqasm()` produces no circuit (when using the same object).

## Code Examples

### Complete Test File Structure (Recommended)

```python
"""Verification tests for qint comparison operations.

Tests all 6 comparison operators (==, !=, <, >, <=, >=) for both QQ and CQ
variants through the full pipeline: Python API -> C backend -> OpenQASM -> Qiskit simulation.

Coverage:
- Exhaustive: All input pairs x all operators for widths 1-4 bits (QQ and CQ)
- Sampled: Boundary + random pairs x all operators for widths 5-8 bits
- BUG-02 regression: Three root causes (MSB index, GC reversal, unsigned overflow)

Result extraction: All comparisons return qbool (1-bit), extracted via verify_circuit(width=1).
"""

import warnings
import pytest
from verify_helpers import format_failure_message, generate_exhaustive_pairs, generate_sampled_pairs
import quantum_language as ql

warnings.filterwarnings("ignore", message="Value .* exceeds")

# --- Oracle: Python native comparison operators ---
OPS = {
    'eq': lambda a, b: int(a == b),
    'ne': lambda a, b: int(a != b),
    'lt': lambda a, b: int(a < b),
    'gt': lambda a, b: int(a > b),
    'le': lambda a, b: int(a <= b),
    'ge': lambda a, b: int(a >= b),
}

QL_OPS = {
    'eq': lambda qa, qb: qa == qb,
    'ne': lambda qa, qb: qa != qb,
    'lt': lambda qa, qb: qa < qb,
    'gt': lambda qa, qb: qa > qb,
    'le': lambda qa, qb: qa <= qb,
    'ge': lambda qa, qb: qa >= qb,
}

QL_OPS_CQ = {
    'eq': lambda qa, b: qa == b,
    'ne': lambda qa, b: qa != b,
    'lt': lambda qa, b: qa < b,
    'gt': lambda qa, b: qa > b,
    'le': lambda qa, b: qa <= b,
    'ge': lambda qa, b: qa >= b,
}
```

### Exhaustive QQ Comparison Test

```python
# Source: Adapted from tests/test_add.py pattern + tests/bugfix/test_bug02_comparison.py
def _exhaustive_qq_cases():
    cases = []
    for width in [1, 2, 3, 4]:
        for a, b in generate_exhaustive_pairs(width):
            for op_name in OPS:
                cases.append((width, a, b, op_name))
    return cases

EXHAUSTIVE_QQ = _exhaustive_qq_cases()

@pytest.mark.parametrize("width,a,b,op_name", EXHAUSTIVE_QQ)
def test_qq_cmp_exhaustive(verify_circuit, width, a, b, op_name):
    expected = OPS[op_name](a, b)
    ql_op = QL_OPS[op_name]

    def circuit_builder(a=a, b=b, w=width, op=ql_op, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = op(qa, qb)
        return exp

    actual, exp = verify_circuit(circuit_builder, width=1)
    assert actual == exp, format_failure_message(f"qq_{op_name}", [a, b], width, exp, actual)
```

### Operand Preservation Custom Helper

```python
# Source: Adapted from tests/test_div.py custom pipeline pattern
import qiskit.qasm3
from qiskit_aer import AerSimulator

def _run_qq_comparison(width, a, b, op_name):
    """Run QQ comparison and return (bool_result, full_bitstring, total_qubits)."""
    ql.circuit()
    qa = ql.qint(a, width=width)
    qb = ql.qint(b, width=width)
    ql_op = QL_OPS[op_name]
    _result = ql_op(qa, qb)
    qasm_str = ql.to_openqasm()

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    # Boolean result is at bitstring[:1] (last allocated qubit)
    bool_result = int(bitstring[0], 2)
    return bool_result, bitstring, len(bitstring)


def _extract_operands(bitstring, width):
    """Extract operand values from bitstring.

    For simple comparisons (eq, lt with CQ_equal_width):
      Total qubits = 2*width + 1 (a, b, result_qbool)
      a at bitstring[n-width:n], b at bitstring[n-2*width:n-width]

    For gt (widened comparison):
      Additional 2*(width+1) qubits for temporaries
      a and b positions shift accordingly

    Returns (a_val, b_val) -- may need calibration per operator.
    """
    n = len(bitstring)
    a_bits = bitstring[n - width : n]
    b_bits = bitstring[n - 2 * width : n - width]
    return int(a_bits, 2), int(b_bits, 2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MSB index was `self[64 - self.bits]` | MSB index is `self[63]` (right-aligned) | Phase 29-16 | All comparisons now check correct bit |
| Layer tracking on comparison results | No layer tracking (no GC gate reversal) | Phase 29-16 | Results persist correctly in circuit |
| n-bit subtraction for GT | (n+1)-bit widened subtraction | Phase 29-16 | Full unsigned range comparison works |
| __le__ used OR(is_negative, is_zero) | __le__ delegates to ~(self > other) | Phase 29-16 | Simpler, correctness follows from __gt__ |
| __gt__ CQ used ~(self <= other) | __gt__ CQ creates temp qint, uses QQ path | Phase 29-16 | Eliminates circular dependency |

**Comparison operator delegation chain (current):**
- `__eq__` QQ: subtract-add-back + `CQ_equal_width(0)` (C function)
- `__eq__` CQ: `CQ_equal_width(bits, value)` (C function)
- `__ne__` all: `~(self == other)`
- `__lt__` QQ: subtract-add-back + MSB[63] check
- `__lt__` CQ: subtract-add-back + MSB[63] check
- `__gt__` QQ: (n+1)-bit widened temps, subtract, MSB[63] check
- `__gt__` CQ: creates temp qint, delegates to QQ `__gt__`
- `__le__` all: `~(self > other)`
- `__ge__` all: `~(self < other)`

**No signed comparison paths exist** in the codebase. All comparisons are unsigned.

## Open Questions

1. **Operand Preservation Verification Complexity**
   - What we know: The `verify_circuit` fixture extracts only the last-allocated register (width=1 for qbool). Extracting input operand values requires custom pipeline helpers with operator-specific bitstring position knowledge.
   - What's unclear: Whether the bitstring positions for `a` and `b` are stable across all operators. `__gt__` allocates extra temporaries that shift positions. `__ne__` delegates to `__eq__` + NOT, which may or may not allocate additional qubits.
   - Recommendation: Build a calibration test per operator at a known width (e.g., 3-bit, a=3, b=5) to empirically determine operand positions. If positions are complex/unstable, consider limiting operand preservation tests to a representative subset rather than exhaustive coverage. **The planner should decide the scope.**

2. **Test Runtime with 5500+ Tests**
   - What we know: Phase 30 arithmetic tests (2460 tests) run successfully. Each comparison test takes ~0.1-0.3s.
   - What's unclear: Exact runtime for the full comparison suite. `__gt__` and `__le__` generate larger circuits (widened temporaries) and may be slower.
   - Recommendation: Start with exhaustive at 1-4 bits for all operators. If runtime is excessive (>30 min), reduce sampled test count at 5-8 bits.

3. **Whether to Keep Existing bugfix/test_bug02_comparison.py**
   - What we know: 6 existing BUG-02 regression tests in `tests/bugfix/test_bug02_comparison.py` all pass.
   - What's unclear: Whether to keep these as-is and add NEW regression tests in test_compare.py, or consolidate.
   - Recommendation: Keep existing BUG-02 tests as-is (they serve as regression). Add NEW BUG-02 regression sub-cases in test_compare.py covering the three specific root causes. This provides both backward compatibility and explicit root-cause coverage.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/quantum_language/qint.pyx` lines 1572-1992 -- all 6 comparison operator implementations (current, post-BUG-02 fix)
- Codebase inspection: `c_backend/include/comparison_ops.h` -- C-level comparison function signatures (CQ_equal_width, QQ_equal, QQ_less_than, CQ_less_than)
- Codebase inspection: `src/quantum_language/qbool.pyx` -- qbool is 1-bit qint (width=1)
- Codebase inspection: `tests/conftest.py` -- verify_circuit fixture (width=1 extracts bitstring[:1])
- Codebase inspection: `tests/verify_helpers.py` -- exhaustive/sampled pair generation
- Codebase inspection: `tests/bugfix/test_bug02_comparison.py` -- proven pattern: verify_circuit(builder, width=1)
- Codebase inspection: `tests/test_add.py` -- Phase 30 test file structure and patterns
- Codebase inspection: `tests/test_div.py` -- custom pipeline helper and xfail patterns
- Phase 29-16 summary: `.planning/phases/29-c-backend-bug-fixes/29-16-SUMMARY.md` -- three BUG-02 root causes and fixes
- Phase 30 research: `.planning/phases/30-arithmetic-verification/30-RESEARCH.md` -- framework patterns
- Project state: `.planning/STATE.md` -- BUG-02 fully fixed, all bugs documented

### Secondary (MEDIUM confidence)
- Phase 31 CONTEXT.md -- locked decisions for coverage strategy, variant requirements, xfail handling

### Tertiary (LOW confidence)
- Operand preservation bitstring position analysis -- based on code reading, not empirical testing. Positions may vary by operator and width.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools already installed and verified working in Phase 30
- Architecture: HIGH -- framework proven in Phase 28/30; comparison result extraction (width=1) verified by BUG-02 tests
- Pitfalls: HIGH -- identified from code inspection of all 6 operator implementations and their delegation chains
- Operand preservation: MEDIUM -- approach identified but extraction positions not empirically verified

**Research date:** 2026-01-31
**Valid until:** 90 days (framework is stable; comparison implementations are fixed)
