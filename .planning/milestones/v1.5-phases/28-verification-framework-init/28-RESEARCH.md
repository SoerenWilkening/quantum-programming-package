# Phase 28: Verification Framework & Init - Research

**Researched:** 2026-01-30
**Domain:** Python testing framework for quantum circuit verification with OpenQASM export and Qiskit simulation
**Confidence:** HIGH

## Summary

Phase 28 requires building a reusable, parameterized test framework for quantum circuit verification. The framework must support the full pipeline: Python quantum_language API → C backend circuit → OpenQASM 3.0 export → Qiskit simulation → result verification. This phase establishes the foundation for exhaustive verification across all operations (Phases 30-33) and must accommodate both exhaustive testing (1-4 bits) and sampled testing (5+ bits).

The codebase already has:
- An existing v1.4 verification script (`scripts/verify_circuit.py`) with working patterns for OpenQASM export, Qiskit simulation, and result checking
- Pytest infrastructure with fixtures (`tests/python/conftest.py`)
- Working `ql.to_openqasm()` export functionality
- Qiskit 2.3.0 installed with AerSimulator statevector simulation

The standard approach is to build on pytest with parameterized tests, organize verification files by operation category (`verify_init.py`, `verify_arithmetic.py`, etc.), and use fixtures for reusable test generation logic.

**Primary recommendation:** Refactor `scripts/verify_circuit.py` into a pytest-based framework with shared test generation fixtures, separate verification files per operation category, and parameterization via `@pytest.mark.parametrize` for exhaustive/sampled input generation.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 8.x+ | Test framework and runner | Industry standard for Python testing in 2026; supports parameterization, fixtures, and clear test organization |
| Qiskit | 2.3.0 | Quantum circuit simulation | Already installed; provides `qiskit.qasm3.loads()` for OpenQASM import and `AerSimulator` for statevector simulation |
| qiskit-aer | Latest (0.17+) | High-performance quantum simulator backend | Required for AerSimulator; provides deterministic statevector simulation |
| qiskit-qasm3-import | Latest | OpenQASM 3.0 parser | Dependency for loading OpenQASM 3.0 circuits into Qiskit |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.24+ | Numerical operations | Already a dependency; useful for sampling strategies and result comparisons |
| itertools | stdlib | Combinatorial generation | Standard library; use for exhaustive input pair generation (e.g., `itertools.product`) |
| random | stdlib | Sampling | Standard library; use with fixed seed for deterministic representative sampling at larger widths |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest | unittest | Pytest provides simpler syntax, better parameterization, and fixture scoping; unittest requires more boilerplate |
| pytest | Standalone scripts | Standalone scripts lack test discovery, fixture reuse, and parameterization; pytest provides all this with minimal overhead |
| AerSimulator | BasicAer | AerSimulator is faster and supports more backend methods; BasicAer is deprecated in recent Qiskit versions |

**Installation:**
```bash
# Core testing dependencies (likely already installed)
pip install pytest qiskit>=2.0 qiskit-aer qiskit-qasm3-import

# Already satisfied by project pyproject.toml
pip install numpy>=1.24
```

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── verify_init.py              # Classical initialization verification (Phase 28)
├── verify_arithmetic.py        # Arithmetic operations (Phase 30)
├── verify_comparison.py        # Comparison operators (Phase 31)
├── verify_bitwise.py          # Bitwise operations (Phase 32)
├── verify_advanced.py         # Uncomputation, conditionals, arrays (Phase 33)
├── conftest.py                # Shared fixtures for test generation and simulation
└── python/                    # Existing pytest unit tests
    ├── test_phase*.py
    └── conftest.py
```

### Pattern 1: Parameterized Test Generation with Fixtures

**What:** Use pytest fixtures to generate test parameters, supporting both exhaustive and sampled strategies.

**When to use:** For operations requiring verification across multiple bit widths and input combinations.

**Example:**
```python
# conftest.py
import pytest
import itertools
import random

@pytest.fixture
def exhaustive_inputs(request):
    """Generate all input pairs for given bit width (1-4 bits)."""
    width = request.param
    max_val = (1 << width) - 1  # 2^width - 1
    return list(itertools.product(range(max_val + 1), repeat=2))

@pytest.fixture
def sampled_inputs(request):
    """Generate representative sample of inputs for larger widths (5+ bits)."""
    width = request.param
    max_val = (1 << width) - 1

    # Edge cases: 0, 1, max, max-1
    edge_cases = [0, 1, max_val, max_val - 1]

    # Random sampling with fixed seed for determinism
    random.seed(42)
    sample_size = min(50, max_val)  # Cap at 50 pairs
    random_pairs = [(random.randint(0, max_val), random.randint(0, max_val))
                    for _ in range(sample_size)]

    # Combine edge cases with random pairs
    edge_pairs = list(itertools.product(edge_cases, repeat=2))
    return list(set(edge_pairs + random_pairs))
```

### Pattern 2: Reusable Test Function via Fixture

**What:** Centralize the build-export-simulate-verify pipeline in a fixture that all verification tests can use.

**When to use:** For every verification test to eliminate code duplication.

**Example:**
```python
# conftest.py
import pytest
import quantum_language as ql
import qiskit.qasm3
from qiskit_aer import AerSimulator

@pytest.fixture
def verify_circuit():
    """Fixture that builds, exports, simulates, and verifies a quantum circuit.

    Returns a callable that takes:
        - circuit_builder: function that builds circuit and returns expected result
        - width: bit width of result register

    Returns (actual, expected) tuple for assertion.
    """
    def _verify(circuit_builder, width):
        # Build circuit and get expected value
        ql.circuit()  # Reset circuit
        expected = circuit_builder()

        # Export to OpenQASM
        qasm_str = ql.to_openqasm()

        # Load into Qiskit
        circuit = qiskit.qasm3.loads(qasm_str)

        # Add measurements if not present
        if not circuit.cregs:
            circuit.measure_all()

        # Simulate with statevector (deterministic)
        simulator = AerSimulator(method='statevector')
        job = simulator.run(circuit, shots=1)
        result = job.result()
        counts = result.get_counts()

        # Extract result (MSB-first bitstring, first `width` chars)
        bitstring = list(counts.keys())[0]
        result_bits = bitstring[:width]
        actual = int(result_bits, 2)

        return actual, expected

    return _verify
```

### Pattern 3: Separate Verification Files Per Category

**What:** Organize tests by operation category with one file per category (init, arithmetic, comparison, etc.).

**When to use:** Following the phase context decision for organization.

**Example:**
```python
# verify_init.py
import pytest
import quantum_language as ql

@pytest.mark.parametrize("width", [1, 2, 3, 4])  # Exhaustive widths
@pytest.mark.parametrize("value", range(16))      # All values up to 4-bit max
def test_init_exhaustive_small_widths(verify_circuit, width, value):
    """Verify classical qint initialization for 1-4 bit widths (exhaustive)."""
    max_val = (1 << width) - 1

    if value > max_val:
        pytest.skip(f"Value {value} exceeds {width}-bit max {max_val}")

    def build():
        a = ql.qint(value, width=width)
        return value

    actual, expected = verify_circuit(build, width)
    assert actual == expected, (
        f"FAIL: init({value}) {width}-bit: expected={expected}, got={actual}"
    )

@pytest.mark.parametrize("width", [5, 6, 7, 8])  # Sampled widths
def test_init_sampled_larger_widths(verify_circuit, sampled_inputs, width):
    """Verify classical qint initialization for 5-8 bit widths (sampled)."""
    # Use sampled_inputs fixture with proper parametrization
    # Implementation depends on sampling strategy from conftest.py
    pass
```

### Anti-Patterns to Avoid

- **Subprocess-based test isolation (from verify_circuit.py):** The existing script runs each test in a subprocess for memory isolation, but this adds significant overhead. Pytest's `ql.circuit()` reset is sufficient.
- **Hardcoded test cases:** Don't enumerate all test cases manually. Use `@pytest.mark.parametrize` to generate them.
- **Silent passing tests:** The context specifies "silent summary on all-pass" but pytest naturally provides summary output. Keep pytest's default behavior for consistency.
- **Custom test discovery:** Don't write custom test collection logic. Use pytest's built-in discovery (test_*.py or *_test.py files).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Test parameterization | Manual loops or test case generation | `@pytest.mark.parametrize` | Pytest provides built-in support with clear test IDs, filtering, and reporting |
| Exhaustive combinations | Nested loops | `itertools.product` | Standard library; efficient and readable |
| Test fixture management | Global variables or manual setup/teardown | Pytest fixtures with proper scoping | Fixtures provide explicit dependencies, automatic cleanup, and reusability |
| Sampling with determinism | Custom random logic | `random.seed()` with stdlib random | Simple, deterministic, and well-understood |
| Test result reporting | Custom formatters | Pytest's default output with optional plugins | Pytest output is already clear; custom formatting adds complexity |
| Circuit simulation | Custom quantum simulator | Qiskit AerSimulator with statevector method | Production-grade, deterministic, and widely used |

**Key insight:** Python's testing ecosystem has mature, well-tested solutions for parameterization, fixture management, and combinatorial test generation. The existing v1.4 script already demonstrates the correct pipeline; the refactor should focus on leveraging pytest's features rather than reimplementing them.

## Common Pitfalls

### Pitfall 1: Non-deterministic Test Results

**What goes wrong:** Quantum simulations with shot noise or floating-point precision issues cause flaky tests.

**Why it happens:** Using shot-based simulation instead of statevector, or comparing floating-point values without tolerance.

**How to avoid:**
- Use `AerSimulator(method='statevector')` with `shots=1` for deterministic results
- Always extract integer measurement results from bitstrings (no floating-point comparison needed)
- Set a fixed seed with `seed_simulator` parameter if needed (though statevector with 1 shot is already deterministic)

**Warning signs:** Tests pass locally but fail in CI, or tests pass/fail randomly on repeated runs.

### Pitfall 2: Bitstring Endianness Confusion

**What goes wrong:** Qiskit uses MSB-first bitstring ordering (leftmost character = highest qubit index), but circuit allocation may use LSB-first or vary by operation.

**Why it happens:** Different conventions for qubit indexing and bitstring representation.

**How to avoid:**
- Always document which end of the bitstring corresponds to which qubit
- The existing verify_circuit.py uses `bitstring[:width]` to extract the first (highest) qubits
- For NOT operation (in-place), use entire bitstring; for binary operations, use first `width` chars
- Add comments explaining the expected layout: "Result register at highest qubit indices"

**Warning signs:** Tests fail with off-by-one errors, or bit-reversed results.

### Pitfall 3: Test Explosion with Exhaustive Parameterization

**What goes wrong:** Exhaustive testing at 4-bit width generates 65,536 test cases (256×256 input pairs), which takes too long to run.

**Why it happens:** Using `@pytest.mark.parametrize` naively without considering test count.

**How to avoid:**
- Calculate test count before running: `(2^width)^operands` for exhaustive testing
- Use sampling for widths where exhaustive testing exceeds reasonable time (>10,000 tests)
- For Phase 28 init tests: exhaustive is fine (256 tests for 1-4 bits combined)
- For arithmetic: consider exhaustive only up to 3 bits for multiplication (64 tests), sampled for 4+ bits

**Warning signs:** Test suite takes >5 minutes to run, or CI times out.

### Pitfall 4: OpenQASM Export Without Measurements

**What goes wrong:** Circuits exported to OpenQASM without measurement instructions cause Qiskit simulation to fail or produce no counts.

**Why it happens:** `ql.to_openqasm()` may not automatically add measurements.

**How to avoid:**
- Always check if circuit has measurements: `if not circuit.cregs: circuit.measure_all()`
- This pattern is already used in verify_circuit.py and should be preserved
- Alternatively, ensure `ql.to_openqasm()` always exports measurements (but this is an API change outside phase scope)

**Warning signs:** Empty counts dictionary, or Qiskit raises errors about missing measurements.

### Pitfall 5: C Backend State Leakage Between Tests

**What goes wrong:** Tests fail when run together but pass individually, or test order affects results.

**Why it happens:** The C backend maintains global state (circuit, qubit allocations) that isn't properly reset between tests.

**Why it happens:** The existing `ql.circuit()` call may not fully reset all global state in the C backend.

**How to avoid:**
- Call `ql.circuit()` at the start of each test (already standard pattern)
- Use pytest's fixture scoping to ensure clean state: `@pytest.fixture(scope="function")`
- If issues persist, investigate whether C backend needs explicit cleanup (e.g., freeing memory)

**Warning signs:** Tests pass individually (`pytest test_file.py::test_name`) but fail in suite, or different results when test order changes.

## Code Examples

Verified patterns from official sources and existing codebase:

### Exhaustive Input Generation for Small Widths
```python
# Source: Python itertools documentation + Phase 28 context
import itertools

def generate_exhaustive_inputs(width):
    """Generate all (a, b) pairs for given bit width.

    For width=2: [(0,0), (0,1), (0,2), (0,3), (1,0), ..., (3,3)]
    Total pairs: (2^width)^2
    """
    max_val = (1 << width) - 1  # 2^width - 1
    return list(itertools.product(range(max_val + 1), repeat=2))

# Usage in test
@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_addition_exhaustive(verify_circuit, width):
    for a, b in generate_exhaustive_inputs(width):
        def build():
            qa = ql.qint(a, width=width)
            qb = ql.qint(b, width=width)
            result = qa + qb
            return (a + b) % (1 << width)  # Wrap overflow

        actual, expected = verify_circuit(build, width)
        assert actual == expected
```

### Sampling Strategy for Larger Widths
```python
# Source: Phase 28 context + Python random module
import random

def generate_sampled_inputs(width, sample_size=50):
    """Generate representative sample of (a, b) pairs.

    Includes:
    - Edge cases: 0, 1, max, max-1
    - Random pairs: up to sample_size additional pairs
    """
    max_val = (1 << width) - 1

    # Edge cases
    edge_values = [0, 1, max_val, max_val - 1]
    edge_pairs = list(itertools.product(edge_values, repeat=2))

    # Random pairs with fixed seed
    random.seed(42)
    random_pairs = [
        (random.randint(0, max_val), random.randint(0, max_val))
        for _ in range(sample_size)
    ]

    # Combine and deduplicate
    all_pairs = edge_pairs + random_pairs
    return list(set(all_pairs))  # Remove duplicates
```

### Full Verification Pipeline in Fixture
```python
# Source: Adapted from scripts/verify_circuit.py (v1.4 verification script)
import pytest
import quantum_language as ql
import qiskit.qasm3
from qiskit_aer import AerSimulator

@pytest.fixture
def verify_circuit():
    """Reusable circuit verification fixture.

    Usage:
        def test_something(verify_circuit):
            def build():
                a = ql.qint(5, width=4)
                return 5

            actual, expected = verify_circuit(build, width=4)
            assert actual == expected
    """
    def _verify(circuit_builder, width):
        # Step 1: Build circuit
        ql.circuit()  # Reset to clean state
        expected = circuit_builder()

        # Step 2: Export to OpenQASM
        qasm_str = ql.to_openqasm()

        # Step 3: Load into Qiskit
        circuit = qiskit.qasm3.loads(qasm_str)

        # Step 4: Add measurements if needed
        if not circuit.cregs:
            circuit.measure_all()

        # Step 5: Simulate with statevector (deterministic)
        simulator = AerSimulator(method='statevector')
        job = simulator.run(circuit, shots=1)
        result = job.result()
        counts = result.get_counts()

        # Step 6: Extract result (MSB-first, first width chars)
        bitstring = list(counts.keys())[0]
        result_bits = bitstring[:width]
        actual = int(result_bits, 2)

        return actual, expected

    return _verify
```

### Compact Failure Message
```python
# Source: Phase 28 context requirement VFWK-03
# "Compact one-liner on failure: `FAIL: add(3,5) 4-bit: expected=8, got=6`"

def test_operation(verify_circuit, width, a, b):
    def build():
        qa = ql.qint(a, width=width)
        qb = ql.qint(b, width=width)
        result = qa + qb
        return (a + b) % (1 << width)

    actual, expected = verify_circuit(build, width)
    assert actual == expected, (
        f"FAIL: add({a},{b}) {width}-bit: expected={expected}, got={actual}"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Subprocess-based test isolation | Pytest with fixture-based state reset | Phase 28 (2026-01-30) | Faster test execution, simpler code, leverages pytest ecosystem |
| Hardcoded test cases in classes | Parameterized test generation with itertools | Phase 28 | Exhaustive coverage without manual enumeration, easier to extend |
| Custom test runners | Pytest with built-in discovery and reporting | Phase 28 | Standard tooling, better IDE integration, community plugins |
| BasicAer StatevectorSimulator | AerSimulator with statevector method | Qiskit 1.0+ (2024) | Better performance, unified simulator interface |
| OpenQASM 2.0 | OpenQASM 3.0 | Qiskit 1.0+ (2024) | Richer feature set, better hardware compatibility |

**Deprecated/outdated:**
- `qiskit.providers.basicaer.StatevectorSimulator`: Deprecated in Qiskit 1.0; use `qiskit_aer.AerSimulator(method='statevector')` instead
- Subprocess-based test execution for memory isolation: Unnecessary with proper `ql.circuit()` reset
- Manual test case enumeration: Replaced by pytest parameterization

## Open Questions

1. **Sampling Count for 5+ Bit Widths**
   - What we know: Context specifies "representative samples" with edge cases plus random pairs
   - What's unclear: Exact number of random pairs per width (50? 100? Adaptive?)
   - Recommendation: Start with 50 random pairs + edge cases; adjust if tests run too long. Document the choice for future phases to follow.

2. **Result Register Extraction for Different Operations**
   - What we know: NOT is in-place (use full bitstring), binary operations have separate result register (use first `width` chars)
   - What's unclear: Are there other operation types with different layouts? What about comparisons (1-bit result)?
   - Recommendation: Extract result width as a parameter to `verify_circuit()` fixture; handle comparisons (width=1) and multi-bit operations uniformly.

3. **Handling of Two's Complement vs Unsigned**
   - What we know: qint uses two's complement internally, but verification may need unsigned interpretation
   - What's unclear: Should negative values be tested? How to interpret signed vs unsigned results?
   - Recommendation: Phase 28 (init) only tests classical values, which are unsigned. For arithmetic phases, document whether operations are signed or unsigned and interpret accordingly.

## Sources

### Primary (HIGH confidence)
- Qiskit AerSimulator Documentation: [Qiskit Aer 0.17.1 AerSimulator](https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html)
- Pytest Parametrization: [How to parametrize fixtures and test functions](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- Qiskit QASM3 Documentation: [qasm3 (latest version) | IBM Quantum Documentation](https://docs.quantum.ibm.com/api/qiskit/qasm3)
- Existing v1.4 verification script: `/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/scripts/verify_circuit.py`
- Phase 28 Context: `/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/.planning/phases/28-verification-framework-init/28-CONTEXT.md`
- Roadmap v1.5: `/Users/sorenwilkening/Desktop/UNI/Promotion/Projects/Quantum Programming Language/Quantum_Assembly/.planning/ROADMAP.md`

### Secondary (MEDIUM confidence)
- Pytest Advanced Patterns: [Advanced Pytest Patterns: Harnessing the Power of Parametrization and Factory Methods | Fiddler AI Blog](https://www.fiddler.ai/blog/advanced-pytest-patterns-harnessing-the-power-of-parametrization-and-factory-methods)
- Python Testing Frameworks 2026: [Top Python Testing Frameworks in 2026 | TestGrid](https://testgrid.io/blog/python-testing-framework/)
- Qiskit Aer GitHub: [GitHub - Qiskit/qiskit-aer](https://github.com/Qiskit/qiskit-aer)

### Tertiary (LOW confidence)
- Parameterized library: [parameterized · PyPI](https://pypi.org/project/parameterized/) - Alternative to pytest.mark.parametrize; not needed for this project

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Qiskit 2.3.0 already installed, pytest is industry standard, existing verify_circuit.py proves viability
- Architecture: HIGH - Patterns based on existing codebase, phase context decisions, and pytest best practices
- Pitfalls: HIGH - Identified from verify_circuit.py implementation and known quantum circuit testing challenges

**Research date:** 2026-01-30
**Valid until:** 90 days (testing frameworks are stable; Qiskit API is mature as of 2.x release)

## Notes for Planner

1. **Build on Existing Code:** The v1.4 verification script (`scripts/verify_circuit.py`) is well-structured and working. Refactor it into pytest-based fixtures rather than rewriting from scratch.

2. **Pytest is the Right Choice:** Context left "test runner approach" to Claude's discretion. Pytest is the clear standard in 2026, already used in the codebase (`tests/python/`), and provides all needed features (parameterization, fixtures, clear output).

3. **File Organization is Fixed:** Context specifies separate files per category (`verify_init.py`, etc.) in `tests/` directory. This is non-negotiable per phase context.

4. **Exhaustive vs Sampled Strategy is Clear:** 1-4 bits exhaustive, 5+ bits sampled with edge cases. The exact sampling count (50 random pairs suggested) can be tuned during implementation.

5. **Output Format Specified:** Phase context requires "compact one-liner on failure" and "one line per category on success". This maps well to pytest's default output with custom assertion messages.

6. **No Fail-Fast by Default:** Context specifies "default continue-all; fail-fast flag available". Pytest provides `--maxfail=1` flag for this.

7. **Dependencies Already Satisfied:** Qiskit 2.3.0, numpy, pytest all already installed. No additional dependencies needed.
