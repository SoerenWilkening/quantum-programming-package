# Testing Patterns

**Analysis Date:** 2026-02-22

## Test Framework

**Runner:**
- pytest >= 7.0
- Config: `pytest.ini` at project root

**Assertion Library:**
- pytest built-ins (`assert`, `pytest.raises`, `pytest.warns`, `pytest.approx`)
- No external assertion library

**Run Commands:**
```bash
pytest tests/python/ -v              # Run all primary tests (verbose, short tracebacks)
pytest tests/python/ -v -m "not slow"  # Skip slow tests
pytest tests/python/ -v -m slow     # Run only slow tests
pytest tests/python/ -v -m integration  # Run only integration tests
pytest tests/ -v                     # Run all tests (includes legacy tests/ root files)
```

## Test File Organization

**Primary test location:**
- `tests/python/` — canonical test suite (configured as `testpaths` in `pytest.ini`)
- Each file covers a feature area or phase milestone (e.g., `test_grover.py`, `test_amplitude_estimation.py`, `test_phase15_initialization.py`)

**Legacy test location:**
- `tests/` root — older verification tests, not in `testpaths`; used for exhaustive simulation-backed verification (files like `test_add.py`, `test_mul.py`, `test_div.py`)

**Naming:**
- Files: `test_<feature_or_phase_name>.py`
- Classes: `Test<FeatureName>` (e.g., `TestGroverIterations`, `TestAmplitudeEstimationEndToEnd`)
- Functions: `test_<what_is_tested>` with detailed description (e.g., `test_grover_single_solution_3bit`, `test_init01_x_gates_applied`)

**Structure within files:**
```
tests/python/
├── conftest.py              # Shared fixtures (clean_circuit, sample_qints, normalize_circuit_output)
├── test_grover.py           # Unit tests + E2E integration tests for Grover's algorithm
├── test_amplitude_estimation.py  # Unit tests + E2E integration tests for IQAE
├── test_phase15_initialization.py  # Tests by requirement group (INIT-01, etc.)
├── test_qint_operations.py  # Characterization tests, golden masters
└── test_cross_backend.py    # Cross-backend equivalence tests
tests/
├── conftest.py              # verify_circuit fixture (full simulation pipeline)
├── verify_helpers.py        # Shared helpers: generate_exhaustive_pairs, generate_sampled_pairs
└── test_add.py, test_mul.py, ...  # Legacy exhaustive verification tests
```

## Test Structure

**Suite Organization:**
- Files typically grouped into two or three `Test*` classes:
  1. Unit tests (no Qiskit needed) — fast, test helper functions and internal logic
  2. Integration tests (with Qiskit simulation) — slower, verify quantum circuit behavior
  3. Optional: edge case or requirements-coverage class

```python
# --- Group 1: Unit Tests (no Qiskit) ---
class TestGroverIterations:
    """Unit tests for _grover_iterations and _resolve_widths. No Qiskit needed."""

    def test_iteration_count_n8_m1(self):
        """N=8, M=1 -> k=1 (floor(pi/4 * sqrt(8) - 0.5) = floor(1.72) = 1)."""
        assert _grover_iterations(8, 1) == 1

# --- Group 2: End-to-End Integration Tests ---
class TestGroverEndToEnd:
    """Integration tests verifying ql.grover() finds correct solutions via Qiskit."""

    def test_grover_single_solution_2bit(self):
        """Oracle marks x=3 in 2-bit space. N=4, M=1 -> k=1, P=1.0 (exact)."""
        ...
        value, iters = ql.grover(mark_three, width=2)
        assert value == 3, f"Expected 3, got {value}"
```

**Patterns:**
- Module-level docstring states which requirements (e.g., `GROV-01`, `INIT-01`) the file covers
- Section dividers `# --- Group N: Description ---` or `# === Section Name ===` separate logical groups
- Each test has a one-line docstring stating what it verifies and expected values
- Assertion messages always include `f"Expected {expected}, got {actual}"` format

## Mocking

**Framework:** No mocking framework used (no `unittest.mock`, no `pytest-mock`)

**Patterns:**
- No mock objects; tests use real quantum circuits and real Qiskit simulation
- Isolation achieved by calling `ql.circuit()` to reset global circuit state before each test
- Garbage collection forced with `gc.collect()` before circuit reset to prevent ancilla corruption from stale qint destructors

**What to Mock:**
- Nothing currently mocked; all quantum behavior is tested against real simulation

**What NOT to Mock:**
- The C backend, Cython layer, or Qiskit simulator — these are the primary objects under test

## Fixtures and Factories

**Shared fixtures in `tests/python/conftest.py`:**

```python
@pytest.fixture
def clean_circuit():
    """Provides a fresh circuit for each test."""
    circ = ql.circuit()
    yield circ
    # Cleanup via Python GC

@pytest.fixture
def sample_qints():
    """Provides sample quantum integers for testing."""
    return {
        "small": ql.qint(value=5, bits=4),
        "medium": ql.qint(value=100, bits=8),
        "large": ql.qint(value=5000, bits=16),
    }
```

**Full verification pipeline fixture in `tests/conftest.py`:**

```python
@pytest.fixture
def verify_circuit():
    """Returns callable _verify(circuit_builder, width, in_place=False).

    Pipeline: ql.circuit() reset -> circuit_builder() -> ql.to_openqasm()
    -> qiskit.qasm3.loads() -> AerSimulator(statevector, shots=1)
    -> extract bitstring -> int -> return (actual, expected)
    """
    def _verify(circuit_builder, width, in_place=False):
        gc.collect()  # Force GC before circuit reset
        ql.circuit()
        result = circuit_builder()
        if isinstance(result, tuple):
            expected, _keepalive = result
        else:
            expected = result
        qasm_str = ql.to_openqasm()
        _keepalive = None
        # ... Qiskit simulation ...
        return (actual, expected)
    return _verify
```

**Test data generation (in `tests/verify_helpers.py`):**

```python
generate_exhaustive_pairs(width)  # All (a, b) pairs for width <= 4
generate_sampled_pairs(width, sample_size=50)  # Edge cases + random (seed=42) for width >= 5
generate_exhaustive_values(width)  # All single values for width <= 4
generate_sampled_values(width, sample_size=50)  # Edge cases + random for width >= 5
```

**Location:**
- Shared fixtures: `tests/python/conftest.py` and `tests/conftest.py`
- Data helpers: `tests/verify_helpers.py`

## Coverage

**Requirements:** No coverage target enforced (no `pytest-cov` or `.coveragerc` detected)

**Coverage approach:** Explicit requirement-tracing — test classes and functions reference requirement IDs (e.g., `GROV-01`, `INIT-01`, `ARTH-03`) in their docstrings and a `TestRequirementsCoverage` class verifies each requirement has a named test.

**View Coverage:**
```bash
# Not configured; would run as:
pytest tests/python/ --cov=src/quantum_language --cov-report=html
```

## Test Types

**Unit Tests:**
- Scope: individual helper functions and internal algorithm logic (`_grover_iterations`, `_resolve_widths`, `_clopper_pearson_confint`, `_find_next_k`, `AmplitudeEstimationResult`)
- No Qiskit required; fast execution
- Located in `Test*` classes labeled "no Qiskit needed"

**Integration Tests (Qiskit simulation):**
- Scope: end-to-end quantum circuit behavior via `ql.grover()`, `ql.amplitude_estimate()`, oracle decorator validation
- Use `AerSimulator(method="statevector", max_parallel_threads=4)` — **always** `max_parallel_threads=4` per project constraint
- Qubit limit: **never exceed 17 qubits** in any simulation (project hard constraint from memory)
- Marked `@pytest.mark.integration` or grouped into `TestGroverEndToEnd` / `TestAmplitudeEstimationEndToEnd` classes

**Characterization Tests (golden masters):**
- Scope: regression detection — captures current behavior, not specific gate sequences
- Found in `test_qint_operations.py` and `test_circuit_generation.py`
- These tests verify operations complete without error and return correct types, not specific output values

**Cross-Backend Equivalence Tests:**
- `tests/python/test_cross_backend.py` (1441 lines)
- Uses `ql.option('fault_tolerant', True)` for Toffoli backend and `False` for QFT backend
- Exhaustive for widths 1-4, sampled for widths 5+
- Documents known failures in `KNOWN_DIV_FAILURES` dict to avoid false failures

**Legacy Verification Tests:**
- `tests/` root files (`test_add.py`, `test_mul.py`, etc.) — not in `testpaths`
- Use `verify_circuit` fixture for full pipeline verification

## Common Patterns

**Simulator Invocation (always use this exact form):**
```python
from qiskit_aer import AerSimulator
simulator = AerSimulator(method="statevector", max_parallel_threads=4)
job = simulator.run(circuit, shots=1)
result = job.result()
counts = result.get_counts()
```

**Circuit Reset Pattern:**
```python
import gc
gc.collect()   # Force GC before reset to prevent stale qint destructor interference
ql.circuit()   # Reset global circuit state
```

**Qiskit Simulation Helper (from tests/python/test_oracle.py):**
```python
SHOTS = 8192

def _simulate_qasm(qasm_str: str) -> dict:
    """Run QASM through Qiskit Aer and return counts dict."""
    circuit = qiskit.qasm3.loads(qasm_str)
    if not circuit.cregs:
        circuit.measure_all()
    simulator = AerSimulator(max_parallel_threads=4)
    transpiled = transpile(circuit, simulator)
    result = simulator.run(transpiled, shots=SHOTS).result()
    return result.get_counts()
```

**Async / Probabilistic Testing:**
```python
# Statistical threshold: run 20 times, expect at least 7 hits (35% threshold)
found_count = 0
for _ in range(20):
    value, iters = ql.grover(mark_five, width=3)
    if value == 5:
        found_count += 1
assert found_count >= 7, f"Expected >=7/20 hits, got {found_count}"
```

**Error Testing:**
```python
with pytest.raises(ValueError, match="width or widths required"):
    _resolve_widths(["x"], None, None)

with pytest.warns(UserWarning, match="max_iterations"):
    result = ql.amplitude_estimate(lambda x: x == 3, width=3, epsilon=0.001, max_iterations=10)
```

**Parametrized Tests:**
```python
@pytest.mark.parametrize("bits", [2, 4, 8, 16])
def test_qint_creation_various_widths(bits):
    a = ql.qint(value=0, bits=bits)
    assert a is not None

@pytest.mark.parametrize(
    "value,expected_width",
    [(1, 1), (5, 3), (8, 4), (255, 8), (256, 9)],
)
def test_auto_width_parametrized(self, value, expected_width):
    a = ql.qint(value)
    assert a.width == expected_width, f"qint({value}) should have width {expected_width}, got {a.width}"
```

**float Approximate Comparisons (for IQAE):**
```python
# pytest.approx for arithmetic results
assert result + 0.5 == pytest.approx(0.625)

# Manual tolerance for probabilistic estimates
assert abs(result.estimate - 0.125) < 0.15, f"Expected ~0.125, got {result.estimate}"
```

## pytest Marks

Defined in `pytest.ini`:
- `@pytest.mark.slow` — marks tests that take a long time; deselect with `-m "not slow"`
- `@pytest.mark.integration` — marks tests requiring Qiskit simulation
- `@pytest.mark.parametrize(...)` — parametrized test variants (used heavily)
- `@pytest.mark.skip(reason=...)` — known skips (e.g., unimplemented features)
- `@pytest.mark.xfail(reason=..., strict=False)` — expected failures for known bugs

---

*Testing analysis: 2026-02-22*
