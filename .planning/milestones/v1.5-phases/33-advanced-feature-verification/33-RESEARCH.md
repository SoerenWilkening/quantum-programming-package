# Phase 33: Advanced Feature Verification - Research

**Researched:** 2026-02-01
**Domain:** Verification of automatic uncomputation, quantum conditionals, and array operations through the full pipeline
**Confidence:** HIGH

## Summary

Phase 33 verifies three advanced language features through the full pipeline (Python quantum_language API -> C backend circuit -> OpenQASM 3.0 -> Qiskit simulation -> result check): automatic uncomputation (ancilla qubits return to |0>), quantum conditionals (`with qbool:` gating operations on condition qubit), and `ql.array` operations (reductions and element-wise). This is a verification-only phase -- all features are already implemented in phases 18-20 (uncomputation), phase 19 (context manager / conditionals), and phases 22-24 (arrays).

The codebase has a well-established verification infrastructure: the `verify_circuit` fixture in `tests/conftest.py`, helper functions in `tests/verify_helpers.py`, and proven test patterns across `test_add.py` (simple binary ops), `test_compare.py` (xfail patterns), `test_compare_preservation.py` (full-bitstring extraction), and `test_bitwise_mixed.py` (keepalive pattern). Uncomputation verification requires a new approach: measuring ALL qubits in the circuit and checking that non-result qubits are in |0> state -- similar to the preservation test pattern but checking for zero instead of value preservation.

**Primary recommendation:** Create three test files: `tests/test_uncomputation.py` (VADV-01), `tests/test_conditionals.py` (VADV-02), and `tests/test_array_verify.py` (VADV-03), each using the established pipeline but with adaptations for full-bitstring analysis and conditional behavior verification. Use `xfail(reason="BUG-XX", strict=False)` consistently for known bugs.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | (installed) | Test framework and parametrization | Used by all existing verification tests |
| qiskit-aer | (installed) | AerSimulator for deterministic statevector simulation | Established pipeline backend |
| qiskit.qasm3 | (installed) | OpenQASM 3.0 loading | Pipeline component |
| quantum_language | (local) | Python API for qint, qbool, qarray, context manager | The system under test |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| verify_helpers | (local) | `generate_exhaustive_pairs`, `format_failure_message` | Parametrized test data generation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom full-bitstring pipeline | verify_circuit fixture | verify_circuit only extracts first `width` bits; uncomputation needs ALL bits checked |
| Statevector inspection | AerSimulator shots=1 | Statevector gives amplitudes directly but bitstring approach is consistent with rest of suite |

**Installation:** No new packages needed. All dependencies are already installed.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py                    # verify_circuit fixture (EXISTS)
├── verify_helpers.py              # Pair generation + formatting (EXISTS)
├── test_uncomputation.py          # NEW: VADV-01 - ancilla qubits return to |0>
├── test_conditionals.py           # NEW: VADV-02 - quantum conditional gating
└── test_array_verify.py           # NEW: VADV-03 - array reductions + element-wise
```

### Pattern 1: Full-Bitstring Pipeline (for Uncomputation Verification)
**What:** Run the full pipeline but instead of extracting just the result register, inspect ALL qubits. Non-result qubits must be |0> (ancilla cleanup). Result qubits must contain the correct value.
**When to use:** VADV-01 uncomputation tests
**Source:** Adapted from `tests/test_compare_preservation.py` lines 54-80

```python
import gc
import qiskit.qasm3
from qiskit_aer import AerSimulator
import quantum_language as ql

def run_full_pipeline(circuit_builder):
    """Run circuit and return full bitstring for analysis."""
    gc.collect()
    ql.circuit()

    result = circuit_builder()
    if isinstance(result, tuple):
        expected, _keepalive = result
    else:
        expected = result
        _keepalive = None

    qasm_str = ql.to_openqasm()
    _keepalive = None  # Safe to release

    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]

    return bitstring, expected

def check_ancilla_cleanup(bitstring, result_width):
    """Check that all non-result qubits are |0>."""
    # Result register is at bitstring[:result_width] (highest qubit indices)
    result_bits = bitstring[:result_width]
    ancilla_bits = bitstring[result_width:]

    # All ancilla bits should be '0'
    actual_result = int(result_bits, 2)
    ancilla_clean = all(b == '0' for b in ancilla_bits)

    return actual_result, ancilla_clean, ancilla_bits
```

### Pattern 2: Conditional Branch Testing (for Quantum Conditionals)
**What:** Build circuit with `with qbool:` block, run pipeline for both condition=True and condition=False, verify operation happened or was skipped respectively.
**When to use:** VADV-02 conditional tests
**Source:** Context manager implementation in `qint.pyx` lines 569-657

```python
def test_conditional_true(verify_circuit):
    """When condition is True, operation inside with-block should execute."""
    def build():
        a = ql.qint(5, width=3)
        flag = (a > 2)  # True for a=5
        result = ql.qint(0, width=3)
        with flag:
            result += 1  # Should execute since flag is True
        return (1, [a, flag, result])  # Expected: 1

    actual, expected = verify_circuit(build, width=3)
    assert actual == expected

def test_conditional_false(verify_circuit):
    """When condition is False, operation inside with-block should be skipped."""
    def build():
        a = ql.qint(1, width=3)
        flag = (a > 2)  # False for a=1
        result = ql.qint(0, width=3)
        with flag:
            result += 1  # Should NOT execute since flag is False
        return (0, [a, flag, result])  # Expected: 0

    actual, expected = verify_circuit(build, width=3)
    assert actual == expected
```

### Pattern 3: Array Verification (for Reductions + Element-wise)
**What:** Create small arrays, perform operations, verify result through pipeline. Sum uses addition (verified in phase 30). AND/OR use bitwise (verified in phase 32). Element-wise addition/subtraction verified by computing expected values classically.
**When to use:** VADV-03 array tests

```python
def test_array_sum_2elem(verify_circuit):
    """Sum of 2-element array [a, b] should equal a + b."""
    def build(a=1, b=2, w=3):
        arr = ql.array([a, b], width=w)
        _result = arr.sum()
        return ((a + b) % (1 << w), [arr])

    actual, expected = verify_circuit(build, width=3)
    assert actual == expected

def test_array_add_scalar(verify_circuit):
    """Element-wise addition: [a, b] + c should give [a+c, b+c]."""
    def build():
        arr = ql.array([1, 2], width=3)
        result = arr + 1
        # Last element allocated is result[-1], extracted from bitstring
        return (3, [arr, result])  # 2+1 = 3 (last element)

    actual, expected = verify_circuit(build, width=3)
    assert actual == expected
```

### Anti-Patterns to Avoid
- **Large bit widths in uncomputation tests:** Uncomputation circuits grow fast. CONTEXT.md locks widths to 2-3 bits. Do not exceed this.
- **Relying on verify_circuit for ancilla checking:** The existing fixture only extracts `bitstring[:width]`. Uncomputation needs custom full-bitstring analysis.
- **Forgetting keepalive references:** Circuit builders must return `(expected, [qint_refs])` to prevent GC from firing destructors before `to_openqasm()`. This was discovered in phase 32 and is critical.
- **Testing nested conditionals:** CONTEXT.md explicitly excludes nested/chained conditionals. Only test simple gating.
- **Using default width (8) for arrays:** CONTEXT.md specifies 2-3 bit elements. Use `width=` parameter explicitly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Simulation pipeline | Custom simulation code | `verify_circuit` fixture (for result-only) or `_run_comparison_pipeline` pattern (for full bitstring) | Established, tested, handles edge cases |
| Test parametrization | Manual loops | pytest `@pytest.mark.parametrize` | Consistent with all existing tests |
| Known-bug handling | Custom skip logic | `pytest.mark.xfail(reason="BUG-XX", strict=False)` | Phase context mandates non-strict xfail with bug reason |
| Pair generation | Manual value lists | `verify_helpers.generate_exhaustive_pairs(width)` | Already handles edge cases |

**Key insight:** The verification infrastructure from phases 28-32 is complete and battle-tested. Phase 33 needs only minor adaptations (full-bitstring extraction for uncomputation, conditional branch testing) rather than new infrastructure.

## Common Pitfalls

### Pitfall 1: GC-Induced Circuit Corruption
**What goes wrong:** Python's garbage collector runs qint destructors before `to_openqasm()` is called, adding uncomputation gates to the circuit and corrupting it.
**Why it happens:** Uncomputation is implemented via `__del__` on qint objects. If a qint goes out of scope in the circuit_builder function, GC may run before the QASM export.
**How to avoid:** Always return keepalive references: `return (expected, [qa, qb, result, ...])`. The conftest.py fixture handles this pattern (lines 84-89).
**Warning signs:** Tests pass sometimes but fail other times; bitstring has unexpected 1s in ancilla positions.

### Pitfall 2: Array Element Width Mismatch
**What goes wrong:** `ql.array([1, 2, 3])` creates elements with default width (INTEGERSIZE=8), creating very large circuits for simulation.
**Why it happens:** The array constructor infers width from values, floored at INTEGERSIZE (8 bits). With 3 elements at 8 bits each, the circuit has 24+ qubits before any operations.
**How to avoid:** Always specify `width=` parameter: `ql.array([1, 2, 3], width=3)`. CONTEXT.md specifies 2-3 bit elements.
**Warning signs:** Simulation timeouts, memory errors, or tests taking >30 seconds.

### Pitfall 3: Conditional Operations Requiring Controlled Variants
**What goes wrong:** Not all operations have controlled (`c`) variants implemented. The `with qbool:` block sets a control context that requires controlled gates.
**Why it happens:** Looking at the source code, addition has controlled variants (`cCQ_add`, `cQQ_add`), but bitwise AND/OR/XOR raise `NotImplementedError("Controlled ... not yet supported")`.
**How to avoid:** Only test conditionals with arithmetic operations (add, subtract) inside the with-block. Do NOT test conditional bitwise operations -- they will crash.
**Warning signs:** `NotImplementedError` exceptions from `__and__`, `__or__`, `__xor__` inside controlled context.

### Pitfall 4: Comparison Bugs Affecting Conditionals
**What goes wrong:** BUG-CMP-01 (equality inversion) and BUG-CMP-02 (ordering errors for MSB-spanning values) cause wrong condition evaluation.
**Why it happens:** Conditionals use comparison operators as condition sources. If the comparison returns wrong results, the conditional gates wrong operations.
**How to avoid:** Use `xfail` markers referencing the relevant comparison bug when using comparisons that are known to fail. Choose comparison operands carefully to avoid BUG-CMP-02 failure pairs (values where MSBs differ).
**Warning signs:** Conditional tests fail with inverted behavior (operation runs when it shouldn't, or vice versa).

### Pitfall 5: Array Sum Width Overflow
**What goes wrong:** Summing array elements may overflow if result width is not sufficient.
**Why it happens:** `arr.sum()` uses `a + b` which creates result with `max(a.width, b.width)`. For 2-bit elements [3, 3], sum=6 needs 3 bits but elements are 2-bit.
**How to avoid:** Either use values small enough to not overflow, or account for overflow with `% (1 << width)` in the expected value calculation.
**Warning signs:** Expected 6 but got 2 (overflow wrapping).

### Pitfall 6: Qubit Saving Mode Interaction
**What goes wrong:** Uncomputation behavior differs between EAGER mode (`qubit_saving=True`) and LAZY mode (default, `qubit_saving=False`).
**Why it happens:** In EAGER mode, intermediates are uncomputed immediately on GC. In LAZY mode, they persist until scope exit. Tests may see different circuit structures.
**How to avoid:** Test uncomputation with `ql.option('qubit_saving', True)` to ensure EAGER mode triggers uncomputation within the test. Reset afterwards with `ql.option('qubit_saving', False)`.
**Warning signs:** Ancilla qubits not cleaned up in LAZY mode because GC hasn't triggered yet.

## Code Examples

### Example 1: Uncomputation Verification (Arithmetic)
```python
def test_uncomp_add(width=2):
    """Verify uncomputation: after a + b with uncomputation, ancilla qubits are |0>."""
    gc.collect()
    ql.circuit()
    ql.option('qubit_saving', True)  # EAGER mode for immediate uncomputation

    a = ql.qint(1, width=width)
    b = ql.qint(2, width=width)
    result = a + b  # Creates intermediate -> should be uncomputed

    # Keep result alive, let intermediates be GC'd
    expected = (1 + 2) % (1 << width)

    qasm_str = ql.to_openqasm()
    ql.option('qubit_saving', False)  # Reset

    # Parse and simulate
    circuit = qiskit.qasm3.loads(qasm_str)
    circuit.measure_all()
    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    bitstring = list(job.result().get_counts().keys())[0]

    # Result at bitstring[:width], ancilla at bitstring[width:]
    actual = int(bitstring[:width], 2)
    ancilla = bitstring[width:]

    assert actual == expected
    assert all(b == '0' for b in ancilla), f"Ancilla not clean: {ancilla}"
```

### Example 2: Conditional Gating Verification
```python
def test_conditional_add_true(verify_circuit):
    """Conditional addition executes when condition is True."""
    def build():
        a = ql.qint(3, width=3)  # 3 > 1 is True
        cond = (a > 1)
        result = ql.qint(0, width=3)
        with cond:
            result += 2  # Should execute
        # Note: cond comparison may be affected by BUG-CMP-01/02
        return (2, [a, cond, result])

    actual, expected = verify_circuit(build, width=3)
    assert actual == expected
```

### Example 3: Array Reduction Verification
```python
def test_array_and_reduce(verify_circuit):
    """AND reduction of [a, b] should equal a & b."""
    def build():
        arr = ql.array([3, 1], width=2)
        _result = arr.all()  # 3 & 1 = 1 (bitwise AND)
        return (3 & 1, [arr])

    actual, expected = verify_circuit(build, width=2)
    assert actual == expected
```

### Example 4: Compound Boolean with Uncomputation
```python
def test_compound_bool_uncomp():
    """Compound boolean expression: (a == 2) & (b < 3) with uncomputation."""
    gc.collect()
    ql.circuit()
    ql.option('qubit_saving', True)

    a = ql.qint(2, width=2)
    b = ql.qint(1, width=2)
    # Compound: both sub-expressions generate ancillae
    cond = (a == 2) & (b < 3)  # True & True = True

    # Note: BUG-CMP-01 inverts eq, so this will likely fail
    # Mark with xfail(reason="BUG-CMP-01") if eq is involved

    qasm_str = ql.to_openqasm()
    ql.option('qubit_saving', False)
    # ... simulate and check
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual bitstring inspection | verify_circuit fixture | Phase 28 | Standardized pipeline for all verification |
| Skip tests for known bugs | xfail with bug reason | Phase 31 | Tests run, failures documented, CI not blocked |
| Default 8-bit elements | Explicit width parameter | Phase 30+ | Circuit size manageable for simulation |
| No keepalive pattern | Return (expected, refs) tuple | Phase 32 | Prevents GC-induced circuit corruption |

**Deprecated/outdated:**
- Using `pytest.skip()` for known bugs: replaced by `xfail(reason="BUG-XX", strict=False)`

## Open Questions

1. **Uncomputation timing with verify_circuit fixture**
   - What we know: The fixture calls `gc.collect()` at the start, then `circuit_builder()`, then `to_openqasm()`. Uncomputation gates fire on `__del__`.
   - What's unclear: In EAGER mode, when exactly do intermediates get uncomputed? Before or after `to_openqasm()`? The keepalive pattern prevents premature uncomputation of the result, but intermediates (from `a + b` creating a copy of `a`) may or may not be cleaned up before export.
   - Recommendation: Run a quick calibration test per operation type (similar to `test_compare_preservation.py`) to empirically determine what the bitstring looks like with uncomputation enabled. If ancilla bits are non-zero, the uncomputation is not firing before export, and tests should document this.

2. **Array element allocation order**
   - What we know: `ql.array([1, 2, 3], width=3)` creates 3 qint objects. The verify_circuit fixture extracts `bitstring[:width]` which is the last-allocated register.
   - What's unclear: For array sum/reduction, the result is a new qint created during reduction. Which register ends up at the highest qubit index (leftmost in bitstring)?
   - Recommendation: Use calibration (known values) to empirically determine extraction positions, following the `test_compare_preservation.py` pattern.

3. **Controlled multiplication inside conditionals**
   - What we know: `cCQ_mul` and `cQQ_mul` exist in the C backend (unlike bitwise ops which lack controlled variants).
   - What's unclear: Whether controlled multiplication actually works correctly -- it hasn't been tested through the pipeline.
   - Recommendation: Include a conditional multiplication test, xfail if it crashes. CONTEXT.md says "gate arithmetic operations inside conditionals" which includes multiply.

## Sources

### Primary (HIGH confidence)
- `tests/conftest.py` - verify_circuit fixture implementation, keepalive pattern
- `tests/verify_helpers.py` - Test data generation utilities
- `tests/test_compare.py` - xfail pattern with BUG-CMP-01/02 markers
- `tests/test_compare_preservation.py` - Full-bitstring extraction and calibration pattern
- `tests/test_bitwise_mixed.py` - Keepalive pattern, CQ mixed-width xfail
- `src/quantum_language/qint.pyx` - Context manager (`__enter__`/`__exit__`), uncomputation (`__del__`, `_do_uncompute`), comparison operators, arithmetic
- `src/quantum_language/qarray.pyx` - Array reductions (`all`, `any`, `sum`, `parity`), element-wise operations
- `src/quantum_language/qbool.pyx` - qbool is 1-bit qint, used as conditional control
- `src/quantum_language/_core.pyx` - `option('qubit_saving', ...)` for EAGER/LAZY mode

### Secondary (MEDIUM confidence)
- `.planning/phases/33-advanced-feature-verification/33-CONTEXT.md` - User decisions constraining scope
- `.planning/phases/32-bitwise-verification/32-RESEARCH.md` - Prior phase research patterns

### Tertiary (LOW confidence)
- None needed -- all research derived from codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Same stack as phases 30-32, all components verified working
- Architecture: HIGH - Patterns directly observed in existing test files
- Pitfalls: HIGH - Discovered by reading source code (controlled op limitations, GC behavior, width defaults)

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable -- no external dependencies changing)

## Appendix: Key Source Code References

### Controlled Operation Availability
From `qint.pyx`, the following operations have controlled variants (usable inside `with qbool:`):
- **Addition:** `cCQ_add`, `cQQ_add` -- AVAILABLE
- **Subtraction:** Uses `addition_inplace(other, invert=True)` with controlled add -- AVAILABLE
- **Multiplication:** `cCQ_mul`, `cQQ_mul` -- AVAILABLE (untested)
- **NOT:** `cQ_not` -- AVAILABLE
- **AND:** `NotImplementedError("Controlled ... AND not yet supported")` -- NOT AVAILABLE
- **OR:** `NotImplementedError("Controlled ... OR not yet supported")` -- NOT AVAILABLE
- **XOR:** `NotImplementedError("Controlled ... XOR not yet supported")` -- NOT AVAILABLE

This means conditional tests MUST use arithmetic (add, subtract) or NOT inside `with` blocks. Bitwise AND/OR/XOR will crash.

### Known Bug Impact Matrix for Phase 33
| Bug | Affects | Impact on Phase 33 |
|-----|---------|-------------------|
| BUG-CMP-01 | eq/ne return inverted | Conditionals using `==` or `!=` as condition will gate incorrectly |
| BUG-CMP-02 | lt/gt/le/ge wrong for MSB-spanning values | Conditionals using ordering comparisons with values where MSBs differ |
| BUG-06 | `_reduce_mod` result corruption | May affect array reductions if they use modular operations internally |
| BUG-07 | Subtraction extraction instability | May affect conditional tests that use subtraction inside `with` block |

### Array Constructor Bug (BUG-ARRAY-INIT) -- CONFIRMED EMPIRICALLY

From `qarray.pyx` lines 296-305, the array constructor for integer data:
```python
q = qint(self._width)    # BUG: passes self._width as VALUE, not width
q.value = value           # Just sets Python attribute, no quantum gates!
```

`qint(self._width)` calls `qint.__init__(value=self._width, width=None)`. The first positional arg is `value`, so `qint(3)` creates a 2-bit qint initialized to value 3 in the quantum circuit. Then `q.value = value` overwrites the Python `.value` attribute without changing the quantum state.

**Empirical confirmation:**
- `ql.array([1, 2], width=3)` produces QASM with only 4 qubits (2 elements x 2-bit auto-width from value=3), all X'd. Expected: 6 qubits (2 x 3-bit), selective X gates.
- Manual `qint(1, width=3)` + `qint(2, width=3)` produces correct QASM: 6 qubits, X on q[0] and q[4].

**Impact on Phase 33:** Array verification tests (VADV-03) CANNOT use `ql.array(values, width=w)` with non-zero values and expect correct quantum initialization. Tests must either:
1. Construct arrays manually from individual `qint(value, width=w)` objects and wrap in qarray
2. Document this as BUG-ARRAY-INIT and xfail all array tests that depend on value initialization
3. Use `ql.array(values)` without explicit width (auto-width from values, but elements still get wrong init)

The correct fix would be `q = qint(value, width=self._width)` but that is a code change outside phase 33 scope. The planner must account for this.
