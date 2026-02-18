# Phase 32: Bitwise Verification - Research

**Researched:** 2026-02-01
**Domain:** Quantum bitwise operation verification (AND, OR, XOR, NOT) through full pipeline
**Confidence:** HIGH

## Summary

Phase 32 verifies that all four bitwise operations (AND, OR, XOR, NOT) produce correct results through the full pipeline: Python quantum_language API -> C backend circuit generation -> OpenQASM 3.0 export -> Qiskit simulation -> result extraction. This follows the same verification pattern established in Phases 30-31 (arithmetic and comparison verification).

The codebase already has all infrastructure needed: the `verify_circuit` fixture in `tests/conftest.py`, helper functions in `tests/verify_helpers.py`, and well-established test file patterns in `tests/test_add.py` (simplest binary op) and `tests/test_compare.py` (parametrized with operator dictionaries). The bitwise operations are fully implemented in both the C backend (`LogicOperations.c`) and the Python layer (`qint_bitwise.pxi`).

**Primary recommendation:** Create two test files following established patterns: `tests/test_bitwise.py` for correctness verification (exhaustive+sampled, QQ+CQ, same-width and mixed-width) and `tests/test_bitwise_preservation.py` for operand preservation with per-operator calibration.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | (installed) | Test framework and parametrization | Used by all existing verification tests |
| qiskit-aer | (installed) | AerSimulator for deterministic statevector simulation | Established pipeline backend |
| qiskit.qasm3 | (installed) | OpenQASM 3.0 loading | Pipeline component |
| quantum_language | (local) | Python API for qint bitwise operations | The system under test |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| verify_helpers | (local) | `generate_exhaustive_pairs`, `generate_sampled_pairs`, `format_failure_message` | All parametrized test data generation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom pipeline for preservation | verify_circuit fixture | verify_circuit only extracts result register; preservation needs full bitstring access |

**Installation:** No new packages needed. All dependencies are already installed.

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── conftest.py                    # verify_circuit fixture (Phase 28, EXISTS)
├── verify_helpers.py              # Pair generation + formatting (Phase 28, EXISTS)
├── test_bitwise.py                # NEW: Correctness verification (VBIT-01)
└── test_bitwise_preservation.py   # NEW: Operand preservation + mixed-width (VBIT-02)
```

### Pattern 1: Oracle-Based Parametrized Testing (from test_compare.py)
**What:** Define Python oracle functions for each operation, parametrize over (width, a, b, op_name), compare oracle result against pipeline result.
**When to use:** Verifying correctness of all four bitwise operations across all input pairs.
**Source:** `tests/test_compare.py` lines 45-75

```python
# Python native bitwise oracles
OPS = {
    "and": lambda a, b, w: a & b,
    "or":  lambda a, b, w: a | b,
    "xor": lambda a, b, w: a ^ b,
    "not": lambda a, w: ((1 << w) - 1) ^ a,  # width-masked complement
}

# Quantum-quantum operator callables
QL_OPS_QQ = {
    "and": lambda qa, qb: qa & qb,
    "or":  lambda qa, qb: qa | qb,
    "xor": lambda qa, qb: qa ^ qb,
}

# Classical-quantum operator callables
QL_OPS_CQ = {
    "and": lambda qa, b: qa & b,
    "or":  lambda qa, b: qa | b,
    "xor": lambda qa, b: qa ^ b,
}
```

### Pattern 2: verify_circuit Fixture for Result Extraction (from test_add.py)
**What:** Use the existing `verify_circuit(circuit_builder, width)` fixture that runs the full pipeline and returns `(actual, expected)`.
**When to use:** All correctness tests for binary ops (AND, OR, XOR) and NOT.
**Source:** `tests/conftest.py` lines 19-108

**Critical notes from codebase analysis:**
- For binary ops (AND, OR, XOR): result register width = `max(width_a, width_b)`. Use `verify_circuit(builder, width=result_width)`.
- For NOT: operation is **in-place** (`~a` returns `a` mutated). Use `verify_circuit(builder, width=w, in_place=True)` -- BUT review needed: the `in_place=True` path uses full bitstring, which may need calibration. Alternative: just use standard extraction since the NOT result is on the same qubits as the input.
- Always bind closure variables with default arguments: `def circuit_builder(a=a, b=b, w=width):`
- Always assign result to `_result` variable to keep qint alive in scope.

### Pattern 3: Empirical Calibration for Operand Preservation (from test_compare_preservation.py)
**What:** Run a known-answer test to determine where operand values sit in the measurement bitstring, then verify operands are unchanged after the operation.
**When to use:** Operand preservation tests for binary ops.
**Source:** `tests/test_compare_preservation.py` lines 88-163

```python
def _calibrate_extraction(width, a, b, op_name, variant='qq'):
    """Empirically determine operand extraction positions."""
    # Run pipeline, get full bitstring
    # Search for known values a,b in bitstring windows
    # Return extraction positions or None
```

### Pattern 4: NOT as In-Place Operation
**What:** `~a` applies X gates to all qubits of `a` in-place and returns `a` (same object reference). The result is read from the same qubits as the input.
**When to use:** NOT verification requires understanding that no new result register is allocated.
**Source:** `qint_bitwise.pxi` lines 448-494

**Key insight:** Unlike AND/OR/XOR which allocate a result register (ancilla qubits), NOT modifies the input in-place. This means:
1. The result sits at the same bitstring position as the input
2. No ancilla cleanup check is needed for standalone NOT
3. For verify_circuit: use `in_place=True` flag or extract from known input position

### Pattern 5: Mixed-Width Operand Handling
**What:** When operands have different widths, the result width is `max(width_a, width_b)`. The narrower operand is zero-extended (its higher bits are |0>).
**When to use:** Mixed-width verification (VBIT-02).
**Source:** `qint_bitwise.pxi` lines 56-60 (width determination), `bitwise_ops.h` line 11 ("support variable-width quantum integers")

**Qubit layout for mixed-width AND/OR:**
- `[0, result_bits-1]` = result register (ancilla)
- `[result_bits, result_bits + self.bits - 1]` = operand A (self)
- `[2*result_bits, 2*result_bits + other.bits - 1]` = operand B (other)
- If `self.bits < result_bits`, the upper bits of self's slot are |0> (zero-extension)

**Mixed-width XOR:** Two-step process:
1. Copy self to result via Q_xor (result = 0 XOR self = self)
2. XOR other into result (result = self XOR other)

### Anti-Patterns to Avoid
- **Hardcoded bitstring positions:** Different operations have different qubit layouts (AND/OR use 3*width qubits, XOR uses copy+XOR pattern, NOT is in-place). Always use empirical calibration for preservation.
- **Testing self-operation (`a & a`):** Self-references may trigger optimization or use same qubits for both operands. Always use distinct qint objects.
- **Forgetting closure binding:** Always use `def circuit_builder(a=a, b=b, w=width):` to avoid late-binding closures in parametrized tests.
- **Using width > result_width for verify_circuit:** Binary ops return `max(width_a, width_b)` bits. NOT returns same width as input.
- **Assuming CQ XOR exists at C level:** There is no `CQ_xor` function. The Python layer implements CQ XOR by applying individual X gates via `Q_not(1)` for each set bit. This means CQ XOR is slower and uses a different gate pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test pair generation | Custom loops | `generate_exhaustive_pairs(width)`, `generate_sampled_pairs(width, sample_size)` | Handles edge cases, dedup, deterministic seeding |
| Failure messages | Inline f-strings | `format_failure_message(op_name, operands, width, expected, actual)` | Consistent format across all verification tests |
| Pipeline execution | Manual qiskit setup | `verify_circuit` fixture | Encapsulates circuit reset, QASM export, simulation, result extraction |
| Operand position detection | Hardcoded offsets | Calibration function (empirical search) | Positions vary by operation due to different qubit counts |

**Key insight:** The verification infrastructure is mature. Phase 32 should reuse everything from Phases 28-31 and only create new test files.

## Common Pitfalls

### Pitfall 1: NOT In-Place vs Out-of-Place Confusion
**What goes wrong:** Treating NOT like binary ops and expecting a separate result register.
**Why it happens:** AND, OR, XOR all allocate new result qubits. NOT does not -- it flips bits in-place.
**How to avoid:** For NOT tests, the "result" is the same register as the input. Use `in_place=True` in verify_circuit, or understand that the input register now holds the inverted value.
**Warning signs:** NOT tests returning 0 when expecting complement -- likely extracting from wrong bitstring position.

### Pitfall 2: Mixed-Width Zero Extension
**What goes wrong:** Expecting mixed-width AND to produce `a & b` where both are at their original widths.
**Why it happens:** The narrower operand is zero-extended to the wider width before the operation. For example, 3-bit `0b101` & 4-bit `0b1111` = 4-bit `0b0101 & 0b1111 = 0b0101`.
**How to avoid:** Oracle function must zero-extend: `(a & ((1 << wider_width) - 1)) & (b & ((1 << wider_width) - 1))` -- but since a and b are already unsigned and within their width, it's simply `a & b` masked to the result width.
**Warning signs:** Results differ at higher bit positions for mixed-width operations.

### Pitfall 3: CQ XOR Gate Pattern Difference
**What goes wrong:** Assuming CQ XOR uses the same circuit structure as QQ XOR.
**Why it happens:** No `CQ_xor` exists at C level. Python applies individual X gates per set bit.
**How to avoid:** This is transparent to testing -- the oracle `a ^ b` is the same regardless. But it may affect performance (more gates for CQ XOR). Keep in mind if circuits get large.
**Warning signs:** CQ XOR tests running significantly slower than QQ XOR.

### Pitfall 4: Ancilla Qubit Verification Complexity
**What goes wrong:** Trying to verify ancilla qubits return to |0> after operations.
**Why it happens:** The context decision says "verify ancilla qubits return to |0>". However, for out-of-place binary ops (AND, OR, XOR), the result IS the ancilla -- it holds the answer, not |0>. Ancilla cleanup applies to intermediate scratch qubits used inside operations.
**How to avoid:** For AND: uses Toffoli gates directly, no intermediate ancillae. For OR: uses CNOT+CNOT+Toffoli, no cleanup needed. Ancilla check is relevant mainly when uncomputation (Phase 33) is enabled. For Phase 32, focus on result correctness and operand preservation.
**Warning signs:** Trying to assert |0> on result register qubits (they should hold the answer, not |0>).

### Pitfall 5: Width 5-6 Circuit Size
**What goes wrong:** Tests at widths 5-6 may use significantly more qubits and time.
**Why it happens:** AND requires 3*width qubits (result + A + B), OR requires 3*width qubits. At width 6, that's 18 qubits per QQ operation (manageable). But total circuit size grows with multiple operations in scope.
**How to avoid:** Use sampled pairs (not exhaustive) at widths 5-6. Context decision already limits to sampling. Monitor execution time -- target under 5 minutes total.
**Warning signs:** Individual tests taking > 5 seconds; total suite exceeding 5 minutes.

## Code Examples

### Example 1: QQ AND Correctness Test (following test_add.py pattern)
```python
@pytest.mark.parametrize("width,a,b", EXHAUSTIVE_QQ)
def test_qq_and_exhaustive(verify_circuit, width, a, b):
    expected = a & b

    def circuit_builder(a=a, b=b, w=width, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        _result = qa & qb
        return exp

    actual, exp = verify_circuit(circuit_builder, width=w)
    assert actual == exp, format_failure_message("qq_and", [a, b], width, exp, actual)
```

### Example 2: NOT Test (in-place operation)
```python
def test_qq_not(verify_circuit, width, a):
    mask = (1 << width) - 1
    expected = mask ^ a  # bitwise complement within width

    def circuit_builder(a=a, w=width, exp=expected):
        qa = ql.qint(a, width=w)
        ~qa  # in-place NOT
        return exp

    actual, exp = verify_circuit(circuit_builder, width=w, in_place=True)
    assert actual == exp, format_failure_message("not", [a], width, exp, actual)
```

### Example 3: Mixed-Width Test
```python
def test_qq_and_mixed_width(verify_circuit, width_a, width_b, a, b):
    result_width = max(width_a, width_b)
    expected = a & b  # both already unsigned, result naturally fits

    def circuit_builder(a=a, b=b, wa=width_a, wb=width_b, exp=expected):
        qa = ql.qint(a, width=wa)
        qb = ql.qint(b, width=wb)
        _result = qa & qb
        return exp

    actual, exp = verify_circuit(circuit_builder, width=result_width)
    assert actual == exp
```

### Example 4: Composed NOT-AND Test
```python
def test_not_and(verify_circuit, width, a, b):
    mask = (1 << width) - 1
    expected = (mask ^ a) & b  # NOT(a) AND b

    def circuit_builder(a=a, b=b, w=width, exp=expected):
        qa = ql.qint(a, width=w)
        qb = ql.qint(b, width=w)
        ~qa  # in-place NOT
        _result = qa & qb
        return exp

    actual, exp = verify_circuit(circuit_builder, width=w)
    assert actual == exp
```

### Example 5: Operand Preservation (following test_compare_preservation.py pattern)
```python
def _run_bitwise_pipeline(width, a, b, op_name, variant='qq'):
    ql.circuit()
    qa = ql.qint(a, width=width)
    if variant == 'qq':
        qb = ql.qint(b, width=width)
        _result = QL_OPS_QQ[op_name](qa, qb)
    else:
        _result = QL_OPS_CQ[op_name](qa, b)

    qasm_str = ql.to_openqasm()
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    sim = AerSimulator(method="statevector")
    job = sim.run(circuit, shots=1)
    counts = job.result().get_counts()
    bitstring = list(counts.keys())[0]
    return bitstring, len(bitstring)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 6 unit tests (type/width checks only) | Phase 32 full-pipeline verification | Phase 28+ | Actually verifies computed values, not just API shape |
| Hardcoded bitstring positions | Empirical calibration | Phase 31-02 | Handles varying qubit layouts per operation |

**Deprecated/outdated:**
- `tests/python/test_phase6_bitwise.py`: These are unit tests that only check types and widths, not computed values. Phase 32 supersedes with full pipeline verification.

## Open Questions

1. **NOT in_place flag behavior with verify_circuit**
   - What we know: The `in_place=True` flag in verify_circuit uses the full bitstring (`result_bits = bitstring`). This means `int(result_bits, 2)` converts the ENTIRE bitstring to an integer, not just the NOT result.
   - What's unclear: Whether `in_place=True` correctly extracts just the NOT result, or whether calibration is needed for NOT too.
   - Recommendation: Test NOT with a simple known case first (e.g., NOT of 0 at width 2 = 3). If `in_place=True` doesn't work correctly, use calibration-based extraction like the preservation tests. Alternatively, since NOT is in-place and the input register is the first allocated, try standard extraction (`width` parameter only, `in_place=False`) -- the result register IS the input register.

2. **CQ XOR classical value width handling**
   - What we know: CQ XOR applies X gates per set bit. The classical value's effective width is `bit_length()`.
   - What's unclear: If the classical value has more bits than the quantum register, are the extra bits silently ignored?
   - Recommendation: Test CQ XOR where classical value exceeds qint width (e.g., `qint(0, width=2) ^ 15`). The Python layer uses `result_bits = max(self.bits, classical_width)`, so the result register expands.

3. **Ancilla verification scope**
   - What we know: Context says "verify ancilla qubits return to |0>". But AND/OR/XOR are out-of-place -- the "ancilla" IS the result register.
   - What's unclear: Whether there are additional intermediate ancillae inside Q_and, Q_or, Q_xor that need cleanup.
   - Recommendation: From reading the C code, Q_and uses only Toffoli gates (no scratch qubits), Q_or uses CNOT+CNOT+Toffoli (no scratch). CQ_and and CQ_or also have no scratch qubits. Ancilla cleanup is NOT needed for bitwise ops. Document this finding but skip ancilla verification tests.

## Sources

### Primary (HIGH confidence)
- `tests/conftest.py` - verify_circuit fixture implementation (read directly)
- `tests/verify_helpers.py` - pair generation and formatting helpers (read directly)
- `tests/test_add.py` - simplest binary op verification pattern (read directly)
- `tests/test_compare.py` - operator dictionary parametrized pattern (read directly)
- `tests/test_compare_preservation.py` - calibration-based operand preservation (read directly)
- `c_backend/include/bitwise_ops.h` - C API and qubit layouts (read directly)
- `c_backend/src/LogicOperations.c` - Q_and, Q_or, Q_xor, Q_not, CQ_and, CQ_or implementations (read directly)
- `src/quantum_language/qint_bitwise.pxi` - Python layer for all bitwise ops (read directly)
- `.planning/phases/31-comparison-verification/31-01-PLAN.md` - Phase 31 plan structure (read directly)
- `.planning/phases/31-comparison-verification/31-02-SUMMARY.md` - Preservation test outcomes (read directly)

### Secondary (MEDIUM confidence)
- Phase 6 unit tests (`tests/python/test_phase6_bitwise.py`) - existing unit test patterns (read directly)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all tools and patterns are established from Phases 28-31, read directly from codebase
- Architecture: HIGH - follows exact same patterns as test_compare.py and test_compare_preservation.py
- Pitfalls: HIGH - identified from direct code reading (NOT in-place behavior, no CQ_xor, qubit layouts)

**Key implementation details for planner:**

1. **Qubit counts per operation (determines simulation feasibility):**
   - NOT: `width` qubits (in-place)
   - XOR QQ: `2*width` qubits (target + source, out-of-place via copy)
   - XOR CQ: `2*width` qubits (result + quantum operand, plus individual X gates)
   - AND QQ: `3*width` qubits (result + A + B)
   - AND CQ: `2*width` qubits (result + quantum operand)
   - OR QQ: `3*width` qubits (result + A + B)
   - OR CQ: `2*width` qubits (result + quantum operand)
   - At width 6: max 18 qubits (QQ AND/OR) -- well within simulation limits

2. **Test count estimates:**
   - Exhaustive widths 1-4: 2+4+8+16=30 values per width, pairs = 4+16+64+256=340 pairs
   - For 3 binary ops (AND, OR, XOR) x 2 variants (QQ, CQ) = 6 test sets x 340 = 2040 tests
   - NOT exhaustive widths 1-4: 2+4+8+16=30 values = 30 tests
   - Sampled widths 5-6: ~30 pairs per width x 2 widths x 6 variants = ~360 tests
   - Mixed-width: 5 adjacent pairs x ~20 pairs each x 3 ops x 2 variants = ~600 tests
   - NOT compositions (NOT-AND, NOT-OR, NOT-XOR): subset of exhaustive pairs = ~200 tests
   - Preservation: ~4 ops x 2 variants x 8 pairs = ~64 tests
   - **Total estimate: ~3300 tests**

3. **Suggested plan structure:**
   - Plan 32-01: Correctness verification (`test_bitwise.py`) -- same-width exhaustive/sampled for AND/OR/XOR/NOT, both QQ and CQ
   - Plan 32-02: Mixed-width and preservation (`test_bitwise_preservation.py`) -- mixed-width tests, NOT composition tests, operand preservation with calibration

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (stable domain, no external dependencies changing)
