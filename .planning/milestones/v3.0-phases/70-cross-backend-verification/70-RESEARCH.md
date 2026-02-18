# Phase 70: Cross-Backend Verification - Research

**Researched:** 2026-02-15
**Domain:** Cross-backend equivalence testing (Toffoli vs QFT arithmetic)
**Confidence:** HIGH

## Summary

Phase 70 is a pure verification phase -- no new features, no C code changes, no Python logic changes. The goal is to create a regression test suite that runs every arithmetic operation with both backends (Toffoli and QFT) and asserts they produce identical computational results. This proves that the Toffoli backend is a drop-in replacement for QFT arithmetic.

The key technical challenge is **result extraction asymmetry**: QFT circuits have no ancilla above the result register (result is at highest qubit indices), while Toffoli circuits allocate ancilla qubits above the result register (1 carry qubit for addition, more for multiplication and division). The existing codebase already solves this via two patterns: (1) the `verify_circuit` fixture extracts from highest qubits (works for QFT), and (2) Toffoli tests use `_simulate_and_extract(qasm_str, num_qubits, result_start, result_width)` with explicit physical qubit indices. For cross-backend tests, each backend must have its own result extraction, or both must use the `allocated_start` property from the Python qint object, which provides backend-independent physical qubit positions.

The second challenge is **simulation feasibility**. Both backends must be simulated to compare results, doubling the simulation cost per test case. QFT addition uses 2N qubits (in-place) or 3N qubits (out-of-place), while Toffoli addition uses 2N+1 (in-place) or 3N+1 (out-of-place). For multiplication, Toffoli uses even more ancilla. Division uses O(7N-10N) qubits with Toffoli. At larger widths, Toffoli circuits also contain MCX gates that require transpilation for MPS simulation. The width ranges in the success criteria (add: 1-8, mul: 1-6, div: 2-6) are chosen to balance coverage with simulation time, but may need to use sampled rather than exhaustive testing at the upper end.

**Primary recommendation:** Create a single test file `tests/python/test_cross_backend.py` that, for each operation/variant/width, builds the circuit twice (once with `fault_tolerant=True`, once with `fault_tolerant=False`), simulates each independently using the appropriate extraction method, and asserts the results match. Use `allocated_start` from the result qint for backend-independent result extraction. Known-failing cases (BUG-DIV-02, BUG-MOD-REDUCE) should be excluded or xfailed in both backends. Mark controlled multiplication with the BUG-COND-MUL-01 scope workaround as needed.

## Standard Stack

### Core (Existing -- No New Dependencies)

| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| `quantum_language` (ql) | `src/quantum_language/` | Python API for circuit building | All operations flow through this |
| `ql.option('fault_tolerant', bool)` | `_core.pyx:164` | Backend switching | Toggles ARITH_TOFFOLI vs ARITH_QFT in C backend |
| `ql.circuit()` | `_core.pyx` | Circuit reset | Clean state between test runs |
| `ql.to_openqasm()` | `_core.pyx` | Circuit export | Pipeline to Qiskit simulation |
| `qiskit.qasm3.loads()` | Qiskit | QASM parsing | Load exported circuits |
| `AerSimulator` | qiskit-aer | Simulation | statevector and matrix_product_state methods |
| `pytest` | Python testing | Test framework | Parametrized tests, xfail markers |
| `verify_helpers.py` | `tests/verify_helpers.py` | Test utilities | `format_failure_message`, `generate_*_pairs` |

### Files to Create

| File | Purpose | Estimated Lines |
|------|---------|-----------------|
| `tests/python/test_cross_backend.py` | Cross-backend equivalence tests | ~500-700 |

### Files NOT Changed

| File | Why No Change |
|------|---------------|
| Any C backend file | Pure verification -- no implementation changes |
| Any `.pyx`/`.pxi` file | Pure verification -- no implementation changes |
| `conftest.py` | Existing fixtures not suitable; cross-backend tests use own helpers |
| Existing test files | Independent test suites; cross-backend is additive |

## Architecture Patterns

### Recommended Test Structure

```
tests/python/test_cross_backend.py
    _run_with_backend(backend, circuit_builder, width) -> int
        - Sets fault_tolerant = (backend == "toffoli")
        - Builds circuit
        - Exports QASM
        - Simulates
        - Extracts result using allocated_start
        - Returns integer result

    _compare_backends(circuit_builder_fn, width, ...) -> None
        - Calls _run_with_backend for each backend
        - Asserts results match

    TestCrossBackendAddition
        test_qq_add_cross_backend  [widths 1-8]
        test_cq_add_cross_backend  [widths 1-8]
        test_cqq_add_cross_backend [widths 1-8]
        test_ccq_add_cross_backend [widths 1-8]

    TestCrossBackendSubtraction
        test_qq_sub_cross_backend  [widths 1-8]
        test_cq_sub_cross_backend  [widths 1-8]

    TestCrossBackendMultiplication
        test_qq_mul_cross_backend  [widths 1-6]
        test_cq_mul_cross_backend  [widths 1-6]
        test_cqq_mul_cross_backend [widths 1-6]
        test_ccq_mul_cross_backend [widths 1-6]

    TestCrossBackendDivision
        test_div_classical_cross_backend [widths 2-6]
        test_mod_classical_cross_backend [widths 2-6]
        test_div_quantum_cross_backend   [widths 2-6]
        test_mod_quantum_cross_backend   [widths 2-6]
```

### Pattern 1: Backend-Independent Result Extraction via allocated_start

**What:** Use the `allocated_start` property from the result qint to determine physical qubit positions, regardless of backend.

**When to use:** Every cross-backend test.

**Example:**
```python
def _run_with_backend(backend, circuit_builder_fn, width):
    """Run a circuit with a specific backend and return the result integer."""
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", backend == "toffoli")

    result_qint, expected, keepalive = circuit_builder_fn()

    # Get result position from the qint object itself (backend-independent)
    result_start = result_qint.allocated_start

    qasm_str = ql.to_openqasm()
    keepalive = None  # Release references after export

    num_qubits = _get_num_qubits(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width)
    return actual
```

**Why this works:** `allocated_start` is set by the qubit allocator when qubits are allocated. For QFT addition (out-of-place), the result register is the last allocated, so it starts after a+b. For Toffoli addition, the result also starts after a+b -- the ancilla is at an even higher index. The `allocated_start` property correctly captures this difference without any backend-specific logic.

### Pattern 2: Controlled Operations with Scope Workaround

**What:** For controlled multiplication tests (`with ctrl: c = a * b`), apply the BUG-COND-MUL-01 workaround (temporarily set scope_depth=0).

**When to use:** All cQQ/cCQ multiplication cross-backend tests.

**Example:**
```python
def circuit_builder():
    qa = ql.qint(a, width=w)
    qb = ql.qint(b, width=w)
    ctrl = ql.qint(1, width=1)
    with ctrl:
        saved = current_scope_depth.get()
        current_scope_depth.set(0)
        qc = qa * qb
        current_scope_depth.set(saved)
    return qc, (a * b) % (1 << w), [qa, qb, ctrl, qc]
```

### Pattern 3: Exhaustive vs Sampled Testing by Width

**What:** Use exhaustive testing for small widths (where all input pairs fit), sampled for larger.

**When to use:** All cross-backend tests.

| Operation | Exhaustive Range | Sampled Range | Rationale |
|-----------|-----------------|---------------|-----------|
| Addition (QQ/CQ) | widths 1-4 | widths 5-8 | 2^8 = 256 pairs at w=4, but 2^16 at w=8 |
| Subtraction (QQ/CQ) | widths 1-4 | widths 5-8 | Same as addition |
| Controlled Add (cQQ/cCQ) | widths 1-4 | widths 5-8 | Same, but test both ctrl=0 and ctrl=1 |
| Multiplication (QQ/CQ) | widths 1-3 | widths 4-6 | 2^6 = 64 at w=3, but 2^12 at w=6 |
| Controlled Mul (cQQ/cCQ) | widths 1-3 | widths 4-6 | Expensive: MCX + MPS transpilation |
| Division (classical) | widths 2-3 | widths 4-6 | O(7N) qubits, MPS needed at w>=3 |
| Modulo (classical) | widths 2-3 | widths 4-6 | Same qubit cost as division |
| Division (quantum) | width 2 | widths 3-6 | 37 qubits at w=2, 82 at w=3 |
| Modulo (quantum) | width 2 | widths 3-6 | Same as quantum division |

### Pattern 4: Simulation Method Selection

**What:** Choose Qiskit simulator method based on circuit characteristics.

| Circuit Type | Method | Rationale |
|-------------|--------|-----------|
| QFT circuits (any width) | `statevector` | No MCX gates, exact |
| Toffoli addition (width <= 8) | `statevector` | Small enough, no MCX for uncontrolled |
| Toffoli controlled add | `statevector` or `matrix_product_state` | MCX gates need transpilation for MPS |
| Toffoli multiplication | `statevector` (small) or `matrix_product_state` (large) | MCX in controlled mul loop |
| Toffoli division | `matrix_product_state` | Many qubits (7N-10N), MCX from comparison ops |

**Note:** The existing Toffoli division tests use MPS with basis-gate transpilation (`transpile(circuit, basis_gates=["cx", "u1", "u2", "u3", "x", "h", "ccx", "id"], optimization_level=0)`). Cross-backend tests should use the same approach for Toffoli circuits that contain MCX gates.

### Anti-Patterns to Avoid

- **Anti-pattern: Comparing QASM strings between backends.** The gate sequences are intentionally different (CCX/CX/X vs H/P/CP). Only compare computed integer results.
- **Anti-pattern: Sharing qubit extraction code between backends.** QFT result is at highest qubit indices; Toffoli result may have ancilla above it. Use `allocated_start` to avoid backend-specific extraction logic.
- **Anti-pattern: Testing known-buggy cases as cross-backend mismatches.** BUG-DIV-02 and BUG-MOD-REDUCE affect both backends (or one more than the other). These should be excluded from cross-backend comparison or xfailed.
- **Anti-pattern: Using `verify_circuit` fixture for Toffoli.** The fixture extracts from highest qubits, which is wrong for Toffoli. Use `_simulate_and_extract` with explicit positions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Qubit position extraction | Manual position calculation per backend | `allocated_start` property on qint | Backend-independent, already maintained by allocator |
| Test data generation | Custom pair generators | `generate_exhaustive_pairs`, `generate_sampled_pairs` from `verify_helpers.py` | Already deterministic, edge-case-aware |
| Simulation pipeline | New simulator setup | Copy/adapt `_simulate_and_extract` from existing Toffoli tests | MPS + transpilation pattern already debugged |
| Known-bug exclusion | Custom skip logic | `pytest.mark.xfail` with `strict=True` | Standard pattern used across test suite |

**Key insight:** The simulation and extraction infrastructure already exists in the codebase across multiple test files. The cross-backend tests should reuse these patterns (particularly the `_simulate_and_extract` helper and `_get_num_qubits` utility), not reinvent them.

## Common Pitfalls

### Pitfall 1: Result Extraction Position Mismatch

**What goes wrong:** Cross-backend comparison reports a mismatch, but both backends actually compute the correct result -- it's extracted from the wrong qubit positions.

**Why it happens:** QFT and Toffoli allocate different numbers of qubits. QFT out-of-place addition uses 3N qubits (a, b, result), while Toffoli uses 3N+1 (a, b, result, carry ancilla). If the test assumes a fixed qubit layout, results are extracted from the wrong physical qubits.

**How to avoid:** Always use `result_qint.allocated_start` for the result register start position. Never hardcode qubit positions based on width alone.

**Warning signs:** All cross-backend tests fail at width >= 2 for Toffoli, but pass for QFT. Or results differ by powers of 2 (bit shift from wrong position).

### Pitfall 2: Stale Circuit State Between Backend Runs

**What goes wrong:** The second backend run produces wrong results because the circuit was not fully reset.

**Why it happens:** `ql.circuit()` resets the circuit, but leftover qint Python objects from the first run may inject uncomputation gates into the new circuit during garbage collection.

**How to avoid:** Call `gc.collect()` before `ql.circuit()`. Keep qint references alive until after `ql.to_openqasm()`, then explicitly set them to `None`.

**Warning signs:** Non-deterministic test failures. Tests pass when run individually but fail in batch.

### Pitfall 3: Scope Workaround for Controlled Multiplication

**What goes wrong:** Controlled multiplication returns 0 for all inputs in both backends, making the cross-backend comparison trivially pass with a wrong answer.

**Why it happens:** BUG-COND-MUL-01 -- scope cleanup reverses out-of-place multiplication results created inside `with ctrl:` blocks.

**How to avoid:** Apply the `current_scope_depth.set(0)` workaround for ALL controlled multiplication tests, in both QFT and Toffoli backends.

**Warning signs:** All controlled multiplication tests "pass" (both backends return 0).

### Pitfall 4: Division Known-Bug Asymmetry

**What goes wrong:** Cross-backend comparison fails because BUG-DIV-02 affects Toffoli and QFT differently.

**Why it happens:** The KNOWN_DIV_MSB_LEAK set in `test_div.py` (QFT mode, since Toffoli is default and these tests don't set fault_tolerant=False) differs from KNOWN_TOFFOLI_DIV_FAILURES in `test_toffoli_division.py`. The failure patterns are not identical between backends because the comparison operator implementation differs slightly.

**How to avoid:** Build a union of known failures from both backends. Any (width, a, b) triple in either backend's failure set should be xfailed in cross-backend tests. Alternatively, only test widths/ranges where both backends are known to be correct.

**Warning signs:** Cross-backend division tests fail for specific edge cases that pass in one backend but fail in the other.

**Details on known failures:**

QFT-mode known failures (from `test_div.py`):
```python
KNOWN_DIV_MSB_LEAK = {
    (3, 4, 1), (3, 5, 1), (3, 6, 1), (3, 7, 1),
    (4, 13, 1), (4, 14, 1), (4, 14, 2), (4, 15, 1), (4, 15, 2),
}
```

Toffoli-mode known failures (from `test_toffoli_division.py`):
```python
KNOWN_TOFFOLI_DIV_FAILURES = {
    (3, 0, 1), (3, 2, 1), (3, 4, 1), (3, 6, 1),
    (4, 0, 1), (4, 0, 2), (4, 1, 1), (4, 1, 2),
    (4, 3, 1), (4, 7, 3), (4, 13, 1), (4, 14, 1),
    (4, 15, 1), (4, 15, 2),
}
```

Union of failures at width 3: `{(3, 0, 1), (3, 2, 1), (3, 4, 1), (3, 5, 1), (3, 6, 1), (3, 7, 1)}`
Union of failures at width 4 is even larger. For cross-backend tests, widths 2 and possibly 3 are the safest for division.

**IMPORTANT CORRECTION:** `test_div.py` does NOT set `fault_tolerant=False`, so since Phase 67-03, it is actually running with Toffoli backend. The "QFT mode" label is misleading -- those failures are Toffoli failures observed through the default mode. To get true QFT-mode division failures, the tests would need to be re-run with explicit `ql.option("fault_tolerant", False)`. This means the cross-backend comparison for division at width 3+ will reveal NEW information about QFT-mode division failures.

### Pitfall 5: Simulation Time for Toffoli at Large Widths

**What goes wrong:** Test suite takes too long (>10 minutes), making it impractical as a regression suite.

**Why it happens:** Toffoli circuits have more qubits (ancilla), more gates (CCX decomposition), and may need MPS transpilation. At width 8 for addition, Toffoli uses ~25 qubits -- still manageable with statevector. But multiplication at width 6 uses ~19 qubits (Toffoli: a=6, b=6, result=6, ancilla) + loop iterations. Division at width 6 uses 42-60 qubits.

**How to avoid:** Use sampled pairs at wider widths. Set a per-test timeout. Consider parametrizing with `@pytest.mark.slow` for widths > 4 to allow quick runs.

**Warning signs:** Tests hang or timeout. CI fails due to time limits.

### Pitfall 6: Modulo Cross-Backend Comparison

**What goes wrong:** BUG-MOD-REDUCE causes widespread modulo failures in both backends, making cross-backend comparison meaningless for modulo.

**Why it happens:** `_reduce_mod` result corruption is a shared algorithm bug (Python-level in `qint_division.pxi`), not a backend-specific bug. Both backends call the same Python division algorithm, so both produce the same wrong answer.

**How to avoid:** For modulo, the cross-backend test may "pass" even though both backends are wrong (they agree on the wrong answer). Document this. Consider only testing modulo at width 2 where some cases are known to work, and xfail the rest.

**Warning signs:** Modulo cross-backend tests pass 100% but individual backend tests show widespread xfails.

## Code Examples

### Backend Switching and Result Extraction

```python
import gc
import warnings
import pytest
import qiskit.qasm3
from qiskit import transpile
from qiskit_aer import AerSimulator
from verify_helpers import format_failure_message, generate_exhaustive_pairs, generate_sampled_pairs
import quantum_language as ql
from quantum_language._core import current_scope_depth

warnings.filterwarnings("ignore", message="Value .* exceeds")


def _get_num_qubits(qasm_str):
    """Extract qubit count from OpenQASM string."""
    for line in qasm_str.split("\n"):
        line = line.strip()
        if line.startswith("qubit["):
            return int(line.split("[")[1].split("]")[0])
    raise Exception(f"Could not find qubit count in QASM:\n{qasm_str[:200]}")


def _simulate_and_extract(qasm_str, num_qubits, result_start, result_width, use_mps=False):
    """Simulate QASM and extract integer from result register.

    Args:
        qasm_str: OpenQASM 3.0 string
        num_qubits: Total qubits
        result_start: Physical qubit index of result LSB
        result_width: Number of result qubits
        use_mps: If True, transpile and use MPS (for MCX-containing circuits)
    """
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()

    if use_mps:
        basis_gates = ["cx", "u1", "u2", "u3", "x", "h", "ccx", "id"]
        circuit = transpile(circuit, basis_gates=basis_gates, optimization_level=0)
        simulator = AerSimulator(method="matrix_product_state")
    else:
        simulator = AerSimulator(method="statevector")

    job = simulator.run(circuit, shots=1)
    result = job.result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]

    msb_pos = num_qubits - result_start - result_width
    lsb_pos = num_qubits - 1 - result_start
    result_bits = bitstring[msb_pos:lsb_pos + 1]
    return int(result_bits, 2)


def _run_backend(backend, build_fn, width, use_mps=False):
    """Run circuit with given backend, return integer result.

    Args:
        backend: "toffoli" or "qft"
        build_fn: Callable returning (result_qint, expected_value, keepalive_list)
        width: Result register width
        use_mps: Whether to use MPS simulator
    """
    gc.collect()
    ql.circuit()
    ql.option("fault_tolerant", backend == "toffoli")

    result_qint, expected, keepalive = build_fn()
    result_start = result_qint.allocated_start

    qasm_str = ql.to_openqasm()
    keepalive = None

    num_qubits = _get_num_qubits(qasm_str)
    actual = _simulate_and_extract(qasm_str, num_qubits, result_start, width, use_mps=use_mps)
    return actual
```

### Cross-Backend Addition Test

```python
class TestCrossBackendAddition:
    @pytest.mark.parametrize("width", [1, 2, 3, 4, 5, 6, 7, 8])
    def test_qq_add_cross_backend(self, width):
        """QQ addition produces same results in both backends."""
        if width <= 4:
            pairs = generate_exhaustive_pairs(width)
        else:
            pairs = generate_sampled_pairs(width, sample_size=20)

        failures = []
        for a, b in pairs:
            def build_fn(a=a, b=b, w=width):
                qa = ql.qint(a, width=w)
                qb = ql.qint(b, width=w)
                qc = qa + qb
                return qc, (a + b) % (1 << w), [qa, qb, qc]

            toffoli_result = _run_backend("toffoli", build_fn, width)
            qft_result = _run_backend("qft", build_fn, width)

            if toffoli_result != qft_result:
                failures.append(
                    f"MISMATCH: qq_add({a},{b}) w={width}: "
                    f"toffoli={toffoli_result}, qft={qft_result}"
                )

        assert not failures, f"{len(failures)} mismatches:\n" + "\n".join(failures[:10])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate test suites per backend | Cross-backend equivalence suite (Phase 70) | Phase 70 | Proves backends are interchangeable |
| test_div.py runs with default (unknowingly Toffoli) | Explicit backend selection in each test | Phase 67-03 | Some QFT-mode test results are actually untested since Toffoli became default |
| verify_circuit extracts from highest qubits | allocated_start for backend-independent extraction | Phase 69 | Works for any backend, any operation |

**Deprecated/outdated:**
- `verify_circuit` fixture in `tests/conftest.py` only works for QFT result extraction. Not suitable for Toffoli or cross-backend tests.
- `test_sub.py` and `test_div.py` do not set `fault_tolerant=False`, so they test Toffoli mode (not QFT) since Phase 67-03, despite not being labeled as Toffoli-specific tests.

## Open Questions

1. **QFT-mode division failures are unknown**
   - What we know: `test_div.py` runs with default (Toffoli since Phase 67-03), so its KNOWN_DIV_MSB_LEAK set documents Toffoli failures, not QFT failures. `test_toffoli_division.py` also runs Toffoli explicitly.
   - What's unclear: What are the actual QFT-mode division failures? They may differ from Toffoli failures.
   - Recommendation: Run division tests with explicit `ql.option("fault_tolerant", False)` first to discover QFT failure set, then build the cross-backend comparison against that baseline. Alternatively, only test division at widths 2-3 where failures are minimal.

2. **Controlled multiplication scope workaround in QFT mode**
   - What we know: BUG-COND-MUL-01 (scope auto-uncomputation) affects Toffoli controlled multiplication. The workaround is `current_scope_depth.set(0)`.
   - What's unclear: Does QFT-mode controlled multiplication also need this workaround? The existing `test_mul.py` does not test controlled multiplication in QFT mode.
   - Recommendation: Apply the workaround for both backends in cross-backend tests. If QFT controlled mul doesn't need it, it's harmless (scope_depth=0 just prevents scope registration).

3. **Target directory: tests/ vs tests/python/**
   - What we know: Success criterion 4 says "integrated into `pytest tests/python/ -v`". The `pytest.ini` sets `testpaths = tests/python`. Existing verification tests (test_add.py, test_toffoli_*.py) are in `tests/` and run with explicit paths.
   - What's unclear: Should cross-backend tests go in `tests/python/` (runs with default pytest) or `tests/` (requires explicit path)?
   - Recommendation: Place in `tests/python/` to satisfy success criterion 4 ("integrated into pytest tests/python/ -v"). The conftest.py in tests/python/ provides `clean_circuit` fixture. Import `verify_helpers` from parent tests/ directory or duplicate the needed helpers.

4. **Simulation time budget**
   - What we know: Phase 69 verification (126 tests) ran in ~47 seconds. Addition verification (340 exhaustive + sampled) runs in ~60 seconds. Each cross-backend test case runs TWO simulations.
   - What's unclear: Total time for cross-backend suite at specified widths.
   - Recommendation: Estimate: Addition 1-8 (exhaustive 1-4, sampled 5-8) x 4 variants x 2 backends = ~2000 simulations. At ~0.1s each = ~200s. Multiplication 1-6 x 4 variants = ~1000 simulations = ~100s. Division 2-6 = ~500 simulations = ~50-100s (MPS slower). Total: ~400-500s (7-8 min). Acceptable for regression but should mark wider widths as `@pytest.mark.slow`.

## Sources

### Primary (HIGH confidence)
- Codebase analysis of `tests/test_toffoli_addition.py` (1006 lines, all patterns for Toffoli testing)
- Codebase analysis of `tests/test_toffoli_multiplication.py` (750 lines, controlled mul patterns)
- Codebase analysis of `tests/test_toffoli_division.py` (642 lines, MPS + transpile pattern, known-bug sets)
- Codebase analysis of `tests/test_add.py`, `test_mul.py` (QFT-mode explicit opt-in pattern)
- Codebase analysis of `tests/test_div.py`, `test_mod.py` (division pipeline, known failures)
- Codebase analysis of `tests/conftest.py` (verify_circuit fixture limitations)
- Codebase analysis of `tests/verify_helpers.py` (generate_exhaustive_pairs, generate_sampled_pairs)
- Codebase analysis of `src/quantum_language/_core.pyx:164-218` (option switching mechanism)
- Phase 69 verification report (69-VERIFICATION.md) -- current test counts and known bugs
- Phase 69 research (69-RESEARCH.md) -- qubit count formulas
- Project STATE.md -- accumulated decisions and blockers

### Secondary (MEDIUM confidence)
- Qubit count estimates based on CDKM adder analysis (2N+1 for CQ, 3N+1 for QQ with Toffoli)
- Simulation time estimates based on Phase 69 run times (~47s for 126 tests)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components already exist in codebase, just need composition
- Architecture: HIGH -- pattern of running both backends and comparing is straightforward; allocated_start pattern proven in Phase 69
- Pitfalls: HIGH -- all pitfalls are documented in existing test files or STATE.md; bug sets are explicitly enumerated

**Research date:** 2026-02-15
**Valid until:** Indefinite (internal codebase analysis, no external dependencies)
