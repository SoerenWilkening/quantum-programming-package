# Phase 110: Merge Verification & Regression - Research

**Researched:** 2026-03-06
**Domain:** Qiskit statevector simulation, pytest parametrization, quantum circuit equivalence testing
**Confidence:** HIGH

## Summary

Phase 110 proves that merged circuits (opt=2) produce correct results by comparing statevectors against opt=3 (full expansion), and verifies the full compile/merge test suite passes at all optimization levels. The project already has mature simulation infrastructure (sim_backend.py, verify_helpers.py, conftest.py fixtures) and established patterns from cross-backend testing (Phase 70).

The core technical approach is straightforward: compile the same operation at opt=2 and opt=3, export both to OpenQASM, load into Qiskit, extract statevectors via `Statevector.from_instruction()`, and compare with `np.allclose(atol=1e-10)`. Verified experimentally that this works -- opt=2 and opt=3 produce identical statevectors for addition at width=3.

**Primary recommendation:** Use `qiskit.quantum_info.Statevector.from_instruction()` for statevector extraction (no AerSimulator needed for equivalence tests), and `pytest.mark.parametrize` at the test level for opt-level regression across test_compile.py and test_merge.py.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Verify add, mul, and grover oracle workloads (matches success criteria exactly)
- Exhaustive testing at small widths (1-4) for add and mul, all input pairs within 17-qubit budget
- Grover oracle uses lambda predicate (e.g., `x == target`) to test full compile+merge pipeline
- Compare opt=2 output against opt=3 (full expansion) -- proves merge doesn't change behavior
- No need to compute expected results independently since opt=3 is already verified
- Use statevector simulation for exact equivalence (no shot-based noise)
- Compare full state vectors (all qubit amplitudes, not just output qubits) to catch any corruption including ancilla state
- Ignore global phase differences -- normalize by aligning phase of first non-zero amplitude
- Tolerance: np.allclose with atol=1e-10
- Parametrize all compile tests (test_compile.py, test_merge.py) with pytest fixture to run at opt=1, opt=2, opt=3
- All ~106 existing compile tests run at each opt level (~320 test runs total)
- Pre-existing 14-15 xfail tests remain xfail at all opt levels -- no new failures = pass
- Non-compile tests (arithmetic, comparison, etc.) not parametrized -- they don't use @ql.compile so opt level is irrelevant
- Explicit tests for parametric+opt interaction:
  - parametric=True + opt=1: should work with DAG
  - parametric=True + opt=3: should work, backward compat
  - parametric=True + opt=2: should raise ValueError
- Parametric verification confirms output correctness only -- topology may legitimately differ between opt levels

### Claude's Discretion
- How to implement the opt-level pytest fixture (conftest parametrize vs per-test decorator)
- Statevector extraction approach (Qiskit Statevector class vs AerSimulator statevector method)
- How to structure the equivalence test file (single file vs split by workload)
- Which specific grover oracle predicate and search space size to use within 17-qubit budget

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MERGE-04 | Merged result verified equivalent to sequential execution via Qiskit simulation | Statevector comparison pattern verified; qubit budgets computed; pytest parametrization approach researched |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| qiskit | installed | QASM loading, circuit representation | Already used throughout project |
| qiskit.quantum_info.Statevector | (part of qiskit) | Statevector extraction from circuits | Direct API, no simulator overhead |
| numpy | installed | Statevector comparison (allclose) | Already used, standard for numerical comparison |
| pytest | installed | Test framework, parametrize | Already used throughout project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit_aer | installed | NOT needed for statevector equivalence | Only for shot-based simulation (not this phase) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Statevector.from_instruction() | AerSimulator(method="statevector") + save_statevector | AerSimulator adds unnecessary overhead; Statevector class is direct and cleaner |

## Architecture Patterns

### Recommended Project Structure
```
tests/
├── test_compile.py          # Existing 118 tests -- add opt_level parametrize
├── python/
│   ├── test_merge.py        # Existing 29 tests -- add opt_level parametrize
│   └── test_merge_equiv.py  # NEW: statevector equivalence tests
└── verify_helpers.py        # Existing -- reuse generate_exhaustive_pairs
```

### Pattern 1: Statevector Equivalence Comparison
**What:** Compile same operation at opt=2 and opt=3, compare full statevectors
**When to use:** All equivalence tests (add, mul, grover oracle)
**Example:**
```python
import numpy as np
import qiskit.qasm3
from qiskit.quantum_info import Statevector

def compare_opt_levels(build_circuit_fn, *args):
    """Compare statevectors between opt=2 and opt=3.

    Returns True if circuits are equivalent (up to global phase).
    """
    import quantum_language as ql

    for opt in [2, 3]:
        ql.circuit()
        ql.option('fault_tolerant', True)

        @ql.compile(opt=opt)
        def fn(*a):
            return build_circuit_fn(*a)

        # ... build circuit with args ...
        qasm = ql.to_openqasm()
        circ = qiskit.qasm3.loads(qasm)
        sv = Statevector.from_instruction(circ)
        # store sv for comparison

    # Phase-normalize and compare
    return _statevectors_equivalent(sv2, sv3, atol=1e-10)


def _statevectors_equivalent(sv1, sv2, atol=1e-10):
    """Compare two statevectors up to global phase."""
    d1, d2 = sv1.data, sv2.data
    # Find first non-zero amplitude in sv1
    nz = np.flatnonzero(np.abs(d1) > atol)
    if len(nz) == 0:
        # Both should be zero
        return np.allclose(d2, 0, atol=atol)
    idx = nz[0]
    # Align global phase
    phase = d2[idx] / d1[idx]
    return np.allclose(d1 * phase, d2, atol=atol)
```

### Pattern 2: Opt-Level Pytest Parametrization
**What:** Run existing compile/merge tests at all opt levels via conftest fixture
**When to use:** test_compile.py and test_merge.py regression
**Recommendation:** Use `conftest.py` autouse fixture with `pytest.mark.parametrize` indirect approach, OR add a session-scoped fixture that wraps `ql.compile`. The cleanest approach is a **module-level parametrize marker** or a **conftest fixture that monkeypatches the default opt level**.

**Key challenge:** test_compile.py tests use `@ql.compile` directly in test bodies. The opt level must be injected somehow. Options:
1. **Monkeypatch approach:** Fixture monkeypatches `CompiledFunc.__init__` to override opt default
2. **Env var approach:** Set env var, CompiledFunc reads it as override
3. **Per-test parametrize:** Mark each test class/function -- verbose but explicit

**Recommendation:** Monkeypatch in conftest.py fixture. Create an `opt_level` fixture that parametrizes over [1, 2, 3] and monkeypatches `ql.compile` to pass the opt kwarg. Tests that explicitly set opt (e.g., `opt=2`) should NOT be overridden.

**Important caveat:** Some tests explicitly test opt=1, opt=2, or opt=3 behavior. Those should be excluded from parametrization or handled gracefully (e.g., skip when fixture opt doesn't match test's explicit opt).

### Pattern 3: Parametric + Opt Interaction Tests
**What:** Verify parametric=True works correctly with each opt level
**When to use:** Dedicated parametric interaction tests
```python
def test_parametric_opt1_works():
    ql.circuit()
    ql.option('fault_tolerant', True)

    @ql.compile(parametric=True, opt=1)
    def add_val(x, val):
        x += val
        return x

    for val in [1, 3, 5, 7]:
        ql.circuit()
        a = ql.qint(0, width=4)
        result = add_val(a, val)
        # Verify via simulation
        qasm = ql.to_openqasm()
        # ... simulate and check result == val ...

def test_parametric_opt2_raises():
    with pytest.raises(ValueError, match="parametric.*opt=2"):
        @ql.compile(parametric=True, opt=2)
        def f(x, val):
            x += val
            return x
```

### Anti-Patterns to Avoid
- **Shot-based comparison for equivalence:** Never use measurement counts to compare circuits -- statevectors give exact equivalence
- **Hardcoding expected values:** Compare opt=2 vs opt=3, not opt=2 vs hand-computed values (opt=3 is already verified)
- **Forgetting `ql.circuit()` reset:** Every test must call `ql.circuit()` before building a new circuit
- **Exceeding 17-qubit budget:** Always check qubit count before simulation

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Statevector extraction | Custom AerSimulator statevector save | `Statevector.from_instruction()` | Direct, no simulator overhead, returns numpy array |
| Input pair generation | Manual loops over ranges | `verify_helpers.generate_exhaustive_pairs()` | Already tested, handles edge cases |
| QASM loading | String parsing | `qiskit.qasm3.loads()` | Standard, handles all gate types |
| Phase normalization | Ad-hoc phase comparison | Dedicated `_statevectors_equivalent()` helper | Global phase is a real issue that needs systematic handling |

## Common Pitfalls

### Pitfall 1: Global Phase Differences
**What goes wrong:** Two physically equivalent circuits produce statevectors that differ by a global phase factor e^(i*theta). `np.allclose` returns False.
**Why it happens:** Different compilation paths can introduce different global phases (e.g., extra Z rotations that cancel physically but shift the global phase).
**How to avoid:** Normalize by aligning the phase of the first non-zero amplitude before comparison.
**Warning signs:** Tests fail with very small but non-zero differences that are constant across all amplitudes.

### Pitfall 2: 17-Qubit Budget Violations
**What goes wrong:** Tests allocate too many qubits, simulation fails or takes excessive memory.
**Why it happens:** Compiled operations with ancillas can use more qubits than expected.
**How to avoid:** Pre-computed qubit budgets (see below). Never exceed 17 qubits.
**Qubit counts verified experimentally:**
- add width=1: 3q, width=2: 7q, width=3: 10q, width=4: 13q
- mul width=1: 3q, width=2: 8q, width=3: 11q, width=4: 14q, width=5: 17q (MAX)
- grover oracle (x==target) width=3: 5q, width=4: 7q
- Safe budget: add up to width=4 (13q), mul up to width=4 (14q), mul width=5 (17q = limit)

### Pitfall 3: Test Pollution from GC
**What goes wrong:** Qint destructors from previous test inject uncomputation gates into new circuit.
**Why it happens:** Python GC is non-deterministic; qint objects from test N may be collected during test N+1.
**How to avoid:** Call `gc.collect()` before `ql.circuit()` reset, or use `ql.circuit()` as first line of each test. The existing `conftest.py` `verify_circuit` fixture already handles this.

### Pitfall 4: Parametrize Interaction with Explicit Opt Tests
**What goes wrong:** A test that explicitly tests `opt=2` behavior gets parametrized to also run at opt=1 and opt=3, causing false failures.
**Why it happens:** Blanket parametrization doesn't account for opt-specific tests.
**How to avoid:** Tests that explicitly set opt level should be marked to skip parametrization, OR the fixture should detect explicit opt and not override.

### Pitfall 5: Pre-existing Test Failures
**What goes wrong:** 15 pre-existing failures in test_compile.py (mostly qarray-related) cause confusion about whether new opt levels introduced regressions.
**Why it happens:** These failures exist at all opt levels (they're not merge-related).
**How to avoid:** Document the 15 known failures. Success criterion is "no NEW failures" -- same 15 tests fail at opt=1, opt=2, and opt=3. Consider marking them with `pytest.mark.xfail` if not already done.

## Code Examples

### Statevector Extraction from QASM
```python
# Source: verified experimentally on this project
import qiskit.qasm3
from qiskit.quantum_info import Statevector

qasm_str = ql.to_openqasm()
circuit = qiskit.qasm3.loads(qasm_str)
sv = Statevector.from_instruction(circuit)
# sv.data is numpy array of complex amplitudes, shape (2^n,)
```

### Phase-Aware Statevector Comparison
```python
import numpy as np

def statevectors_equivalent(sv1_data, sv2_data, atol=1e-10):
    """Compare two statevector numpy arrays up to global phase."""
    # Find first non-zero amplitude
    nz = np.flatnonzero(np.abs(sv1_data) > atol)
    if len(nz) == 0:
        return np.allclose(sv2_data, 0, atol=atol)
    idx = nz[0]
    if np.abs(sv2_data[idx]) < atol:
        return False  # One is zero where other isn't
    # Compute phase factor
    phase = sv2_data[idx] / sv1_data[idx]
    return np.allclose(sv1_data * phase, sv2_data, atol=atol)
```

### Exhaustive Equivalence Test Pattern
```python
from verify_helpers import generate_exhaustive_pairs

@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_add_opt2_equiv_opt3(width):
    """Merged add circuit matches full-expansion add at all input pairs."""
    for a_val, b_val in generate_exhaustive_pairs(width):
        sv2 = _get_statevector(a_val, b_val, width, opt=2)
        sv3 = _get_statevector(a_val, b_val, width, opt=3)
        assert statevectors_equivalent(sv2.data, sv3.data), \
            f"add({a_val}, {b_val}) width={width}: opt=2 != opt=3"
```

### Opt-Level Conftest Fixture (Recommended Approach)
```python
# In tests/conftest.py or tests/test_compile_conftest.py
import pytest

@pytest.fixture(params=[1, 2, 3], ids=["opt1", "opt2", "opt3"])
def opt_level(request, monkeypatch):
    """Parametrize tests across optimization levels."""
    level = request.param
    original_init = CompiledFunc.__init__

    def patched_init(self, func, **kwargs):
        if 'opt' not in kwargs:
            kwargs['opt'] = level
        original_init(self, func, **kwargs)

    monkeypatch.setattr(CompiledFunc, '__init__', patched_init)
    return level
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AerSimulator for statevectors | Statevector.from_instruction() | qiskit 0.24+ | Cleaner API, no simulator overhead |
| Custom QASM parsing | qiskit.qasm3.loads() | qiskit 0.36+ | Standard OpenQASM 3.0 support |

## Open Questions

1. **Monkeypatch vs explicit parametrize for opt-level regression**
   - What we know: test_compile.py has 118 tests, most use `@ql.compile` without explicit opt. 15 pre-existing failures exist.
   - What's unclear: Whether monkeypatching CompiledFunc.__init__ is clean enough, or if explicit parametrize decorators on each test class are safer.
   - Recommendation: Start with monkeypatch approach -- it's less invasive and doesn't require modifying 118 test functions. Fall back to explicit parametrize if monkeypatch causes issues.

2. **Grover oracle search space size**
   - What we know: Grover oracle (x==target, width=3) uses 5 qubits. Width=4 uses 7 qubits. Well within budget.
   - What's unclear: Whether to test with full ql.grover() pipeline or just the oracle circuit.
   - Recommendation: Test with compiled oracle function at opt=2 vs opt=3 (not full ql.grover() which includes simulation). Width=3 or 4 is safe. Use target=5 as predicate.

3. **How to handle parametric+opt=2 ValueError in parametrized tests**
   - What we know: parametric=True + opt=2 raises ValueError by design (Phase 109 decision).
   - What's unclear: Whether parametrize fixture should skip parametric tests when opt=2, or test them separately.
   - Recommendation: Test parametric+opt interaction in dedicated test functions, not via the parametrize fixture. The fixture should only apply to non-parametric tests.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed) |
| Config file | pytest.ini or pyproject.toml (project-level) |
| Quick run command | `pytest tests/python/test_merge_equiv.py -x -q` |
| Full suite command | `pytest tests/test_compile.py tests/python/test_merge.py tests/python/test_merge_equiv.py -q --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MERGE-04a | opt=2 add equiv to opt=3 | integration | `pytest tests/python/test_merge_equiv.py::test_add_equiv -x` | Wave 0 |
| MERGE-04b | opt=2 mul equiv to opt=3 | integration | `pytest tests/python/test_merge_equiv.py::test_mul_equiv -x` | Wave 0 |
| MERGE-04c | opt=2 grover oracle equiv to opt=3 | integration | `pytest tests/python/test_merge_equiv.py::test_grover_equiv -x` | Wave 0 |
| MERGE-04d | test_compile.py passes at opt=1,2,3 | regression | `pytest tests/test_compile.py -q --tb=short` | Exists (needs parametrize) |
| MERGE-04e | test_merge.py passes at opt=1,2,3 | regression | `pytest tests/python/test_merge.py -q --tb=short` | Exists (needs parametrize) |
| MERGE-04f | parametric+opt interaction correct | unit | `pytest tests/python/test_merge_equiv.py::TestParametricOptInteraction -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/python/test_merge_equiv.py -x -q`
- **Per wave merge:** `pytest tests/test_compile.py tests/python/test_merge.py tests/python/test_merge_equiv.py -q --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/python/test_merge_equiv.py` -- new file for statevector equivalence tests (MERGE-04a,b,c,f)
- [ ] Opt-level parametrization in conftest or test files (MERGE-04d,e)
- [ ] xfail markers for 15 pre-existing test_compile.py failures (if not already present)

## Sources

### Primary (HIGH confidence)
- Project codebase: tests/test_compile.py (118 tests, 15 pre-existing failures), tests/python/test_merge.py (29 tests)
- Project codebase: src/quantum_language/sim_backend.py (simulation patterns)
- Project codebase: tests/conftest.py (verify_circuit fixture pattern)
- Project codebase: tests/verify_helpers.py (exhaustive/sampled pair generation)
- Experimental verification: Statevector.from_instruction() works with project QASM output, opt=2 == opt=3 for add width=3

### Secondary (MEDIUM confidence)
- Qiskit Statevector API: from_instruction() returns Statevector with .data numpy array

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, experimentally verified
- Architecture: HIGH - patterns follow existing project conventions (cross-backend testing)
- Pitfalls: HIGH - qubit budgets experimentally verified, GC issue documented in existing code
- Parametrize approach: MEDIUM - monkeypatch approach untested, may need adjustment

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable domain, project-specific)
