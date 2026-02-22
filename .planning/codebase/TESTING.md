# Testing Patterns

**Analysis Date:** 2026-02-22

## Test Framework

**Runner (Python):**
- pytest 7.0+
- Config: `pytest.ini` (root)
- Default test path: `tests/python/`
- Default flags: `-v --tb=short --strict-markers`

**Runner (C):**
- Custom Makefile in `tests/c/Makefile`
- Compiled with `gcc -Wall -Wextra -g`
- Assertion: C standard `assert()` from `<assert.h>`
- No CTest or external framework

**Assertion Library (Python):**
- pytest native assertions (`assert actual == expected`)
- `pytest.approx` for floating-point comparisons
- `pytest.raises` for exception assertions
- `pytest.warns` for warning assertions

**Run Commands:**
```bash
pytest tests/python/ -v                    # All Python tests
pytest tests/python/ -v -m "not slow"     # Skip slow tests
pytest tests/python/ -v -m integration    # Integration only
pytest tests/python/test_grover.py -v     # Single file
```

```bash
# C tests (from tests/c/)
make test_allocator_block && ./test_allocator_block
make test_reverse_circuit && ./test_reverse_circuit
make test_hot_path_add && ./test_hot_path_add
make test_hot_path_mul && ./test_hot_path_mul
make test_allocator_block_debug && ./test_allocator_block_debug   # With DEBUG flag
```

## Test File Organization

**Python test location:**
- Primary: `tests/python/` — all pytest-run tests (694 test functions across 30+ files)
- Legacy root-level: `tests/test_*.py` — older verification tests run directly, not via pytest

**Naming:**
- `test_<feature>.py` — feature-level tests (e.g., `test_grover.py`, `test_oracle.py`, `test_diffusion.py`)
- `test_phase<N>_<feature>.py` — phase-gated tests tied to development milestones (e.g., `test_phase15_initialization.py`, `test_phase7_arithmetic.py`)

**Structure:**
```
tests/
├── conftest.py              # verify_circuit fixture (Qiskit simulation pipeline)
├── verify_helpers.py        # Shared: generate_exhaustive_pairs, generate_sampled_pairs
├── python/
│   ├── conftest.py          # clean_circuit, sample_qints fixtures; normalize_circuit_output()
│   ├── test_grover.py
│   ├── test_amplitude_estimation.py
│   ├── test_cross_backend.py
│   ├── test_phase15_initialization.py
│   └── test_*.py            # 30+ test files
└── c/
    ├── Makefile
    ├── test_allocator_block.c
    ├── test_reverse_circuit.c
    ├── test_hot_path_add.c
    ├── test_hot_path_mul.c
    ├── test_hot_path_xor.c
    └── test_comparison.c
```

## Test Structure

**Python suite organization (class-based):**
```python
class TestGroverIterations:
    """Unit tests for _grover_iterations and _resolve_widths. No Qiskit needed."""

    def test_iteration_count_n8_m1(self):
        """N=8, M=1 -> k=1 (floor(pi/4 * sqrt(8) - 0.5) = floor(1.72) = 1)."""
        assert _grover_iterations(8, 1) == 1


class TestGroverEndToEnd:
    """Integration tests verifying ql.grover() finds correct solutions via Qiskit."""

    def test_grover_single_solution_3bit(self):
        """Oracle marks x=5 in 3-bit space. Expect value=5 with high probability."""
        ...
```

**Pattern:** Each test file contains 2–5 classes. Classes group by:
- Unit vs. integration (e.g., `TestGroverIterations` vs. `TestGroverEndToEnd`)
- Feature area (e.g., `TestBasicInitialization`, `TestAutoWidthMode`, `TestBoundaryConditions`)
- Requirements coverage (e.g., `TestRequirementsCoverage` mapping to spec IDs like `INIT-01`)

**Parametrized tests:**
```python
@pytest.mark.parametrize(
    "value,expected_width",
    [
        (1, 1),
        (5, 3),
        (8, 4),
        (255, 8),
    ],
)
def test_auto_width_parametrized(self, value, expected_width):
    a = ql.qint(value)
    assert a.width == expected_width, f"qint({value}) should have width {expected_width}, got {a.width}"
```

**C test structure:**
```c
static void test_block_reuse_after_free(void) {
    printf("test_block_reuse_after_free... ");
    fflush(stdout);

    qubit_allocator_t *alloc = allocator_create(64);
    assert(alloc != NULL);

    qubit_t s1 = allocator_alloc(alloc, 4, false);
    int rc = allocator_free(alloc, s1, 4);
    assert(rc == 0);

    qubit_t s2 = allocator_alloc(alloc, 4, false);
    assert(s2 == s1 && "Freed block of 4 should be reused");

    allocator_destroy(alloc);
    printf("PASS\n");
}

int main(void) {
    printf("=== block allocator unit tests ===\n\n");
    test_block_reuse_after_free();
    // ... more tests ...
    printf("\n=== ALL N TESTS PASSED ===\n");
    return 0;
}
```

## Mocking

**Framework:** None — no `unittest.mock`, `pytest-mock`, or similar.

**Patterns:** No mocking is used. Tests exercise real Cython/C backends directly.

**What to Mock:** Nothing is currently mocked. All code paths are tested against the actual implementation.

**What NOT to Mock:** The C backend, Qiskit simulation, and qubit allocator are never mocked — they are the primary subjects of testing.

## Fixtures and Factories

**`tests/python/conftest.py` fixtures:**

```python
@pytest.fixture
def clean_circuit():
    """Provides a fresh circuit for each test."""
    circ = ql.circuit()
    yield circ
    # Cleanup via Python GC

@pytest.fixture
def sample_qints():
    """Provides sample quantum integers."""
    return {
        "small": ql.qint(value=5, bits=4),
        "medium": ql.qint(value=100, bits=8),
        "large": ql.qint(value=5000, bits=16),
    }
```

**`tests/conftest.py` fixtures (Qiskit pipeline):**

```python
@pytest.fixture
def verify_circuit():
    """Full verification pipeline: build circuit -> export QASM -> Qiskit simulate -> extract result."""

    def _verify(circuit_builder, width, in_place=False):
        gc.collect()      # Prevent stale qint destructors from firing on new circuit
        ql.circuit()      # Reset circuit state

        result = circuit_builder()
        if isinstance(result, tuple):
            expected, _keepalive = result   # keepalive prevents premature GC of qint refs
        else:
            expected = result

        qasm_str = ql.to_openqasm()
        _keepalive = None

        circuit = qiskit.qasm3.loads(qasm_str)
        if not circuit.cregs:
            circuit.measure_all()

        simulator = AerSimulator(method="statevector", max_parallel_threads=4)
        job = simulator.run(circuit, shots=1)
        counts = job.result().get_counts()
        bitstring = list(counts.keys())[0]
        result_bits = bitstring[:width] if not in_place else bitstring
        actual = int(result_bits, 2)

        return (actual, expected)

    return _verify
```

**`tests/verify_helpers.py` (shared input generation):**

```python
def generate_exhaustive_pairs(width):
    """All (a, b) pairs for width <= 4 (exhaustive)."""
    return list(itertools.product(range(2**width), repeat=2))

def generate_sampled_pairs(width, sample_size=50):
    """Edge cases + seeded random pairs for width >= 5."""
    max_val = (2**width) - 1
    edge_values = [0, 1, max_val, max_val - 1]
    edge_pairs = set(itertools.product(edge_values, repeat=2))
    random.seed(42)  # Deterministic seed for reproducibility
    random_pairs = {(random.randint(0, max_val), random.randint(0, max_val)) for _ in range(sample_size)}
    return sorted(edge_pairs | random_pairs)
```

**Location of fixtures:**
- `tests/python/conftest.py` — `clean_circuit`, `sample_qints`, `normalize_circuit_output()`
- `tests/conftest.py` — `verify_circuit` (full Qiskit simulation pipeline), `clean_circuit`
- `tests/verify_helpers.py` — `generate_exhaustive_pairs`, `generate_sampled_pairs`, `format_failure_message`

## Coverage

**Requirements:** None enforced (no `--cov` or coverage threshold configured)

**View Coverage:**
```bash
# Not configured; would require: pip install pytest-cov
pytest tests/python/ --cov=src/quantum_language --cov-report=html
```

**Observed coverage strategy:** Exhaustive input coverage for small widths (1–4 bits), sampled for larger widths (5–8+ bits). Cross-backend equivalence tests (`test_cross_backend.py`) cover all arithmetic operation variants systematically.

## Test Types

**Unit Tests (no Qiskit required):**
- Pure Python/math logic: `TestGroverIterations`, `TestIQAEHelpers`, `TestAmplitudeEstimationResult`
- API contract tests: `TestCircuitAPI`, `TestQintAPI`, `TestQboolAPI` in `test_api_coverage.py`
- C allocator tests: `tests/c/test_allocator_block.c`
- Scope: individual functions or classes, no simulation

**Integration Tests (Qiskit simulation required):**
- End-to-end circuit verification: `TestGroverEndToEnd`, `TestAmplitudeEstimationEndToEnd`
- Cross-backend equivalence: `TestCrossBackendAddition`, `TestCrossBackendMultiplication`, etc. in `test_cross_backend.py`
- Marked with `@pytest.mark.integration` in some files
- Use `AerSimulator(method="statevector", max_parallel_threads=4)` — max 4 threads enforced
- Never exceed 17 qubits (project constraint from project memory)

**E2E Tests:**
- `verify_circuit` fixture provides a full pipeline from Python API through C backend to Qiskit simulation and result extraction
- Used in `test_phase7_arithmetic.py`, `test_phase13_equality.py`, `test_phase15_initialization.py`, etc.

## Common Patterns

**Async Testing:**
Not applicable — all code is synchronous.

**Probabilistic test assertions:**
Grover and amplitude estimation results are probabilistic. Tests use statistical bounds with explicit reasoning:
```python
# Run 20 times, expect at least 7/20 hits
found_count = 0
for _ in range(20):
    value, iters = ql.grover(mark_five, width=3)
    if value == 5:
        found_count += 1
assert found_count >= 7, f"Expected >=7/20 hits, got {found_count}"
```

**Error testing:**
```python
def test_invalid_width_below_1(self):
    with pytest.raises(ValueError, match="Width must be 1-64"):
        ql.qint(5, width=0)

def test_overflow_emits_warning(self):
    with pytest.warns(UserWarning, match="Value.*exceeds"):
        a = ql.qint(1000, width=8)

def test_max_iterations_cap(self):
    with pytest.warns(UserWarning, match="max_iterations"):
        result = ql.amplitude_estimate(lambda x: x == 3, width=3, epsilon=0.001, max_iterations=10)
```

**Known failure documentation (xfail):**
```python
@pytest.mark.parametrize(
    "width",
    [
        pytest.param(
            2,
            marks=pytest.mark.xfail(
                reason="BUG-CQQ-QFT: QFT controlled QQ addition incorrect at width 2+ (CCP rotation angle errors)",
                strict=False,
            ),
        ),
    ],
)
def test_cqq_add(self, width):
    ...
```

**Slow test marking:**
```python
pytest.param(7, marks=pytest.mark.slow)   # Deselect with: -m "not slow"
pytest.param(8, marks=pytest.mark.slow)
```

**GC coordination for quantum state tests:**
```python
# Always call gc.collect() before ql.circuit() to prevent stale destructors
# from injecting uncomputation gates into the new circuit
gc.collect()
ql.circuit()
```

**keepalive pattern (prevent premature uncomputation):**
```python
def build():
    a = ql.qint(5, width=4)
    b = ql.qint(3, width=4)
    c = a + b
    return 8, [a, b, c]   # Return (expected, keepalive_refs)

actual, expected = verify_circuit(build, width=4)
```

**Failure collection (no early exit on first failure):**
Cross-backend tests collect all failures before asserting, producing detailed diagnostics:
```python
failures = []
for a, b in pairs:
    toffoli_result, qft_result = _compare_backends(build_fn, width)
    if toffoli_result != qft_result:
        failures.append(f"w={width} a={a} b={b}: toffoli={toffoli_result}, qft={qft_result}")

assert not failures, f"{len(failures)} cross-backend mismatches:\n" + "\n".join(failures[:20])
```

**Trivial-pass guard:**
```python
# Guard against all-zero results masking a broken test
assert saw_nonzero, f"All cQQ mul results were 0 at width {width} -- test may be trivially passing"
```

---

*Testing analysis: 2026-02-22*
