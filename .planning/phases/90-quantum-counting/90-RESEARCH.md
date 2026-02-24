# Phase 90: Quantum Counting - Research

**Researched:** 2026-02-24
**Domain:** Quantum counting / amplitude estimation wrapper
**Confidence:** HIGH

## Summary

Phase 90 adds `ql.count_solutions()` as a thin semantic layer over the existing IQAE implementation in `amplitude_estimation.py`. The core algorithm already exists and is well-tested (Phase 81). The work is primarily: (1) creating a `CountResult` class that converts amplitude estimates to integer solution counts, (2) wiring `count_solutions()` through the same oracle/register infrastructure, and (3) declaring the missing `scipy>=1.10` dependency in `pyproject.toml`.

The implementation is low-risk because it reuses proven IQAE internals -- no new quantum algorithm is needed. The `CountResult` class follows the same design pattern as `AmplitudeEstimationResult` (wrapper with arithmetic operators) but for integer counts instead of float probabilities.

**Primary recommendation:** Implement `count_solutions()` in a new `quantum_counting.py` module that imports from `amplitude_estimation.py`, create `CountResult` as an int-like wrapper class, and verify with known-M oracles at M=1, M=2, M=3 using existing test patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Mirror `amplitude_estimate()` signature: `count_solutions(oracle, *registers, width=, widths=, epsilon=, confidence_level=, max_iterations=, predicate=)`
- `epsilon` controls amplitude precision (pass through to IQAE directly), not a separate count precision parameter
- `max_iterations` exposed as oracle call cap, same as `amplitude_estimate()`
- Top-level `ql.count_solutions()` function exported from `__init__.py`
- CountResult is int-like: `int(result)` returns `.count`, arithmetic operators work, `result == 3` works
- `.count` = rounded integer (the discrete solution count)
- `.estimate` = raw float (unrounded `N * amplitude` for precise analysis)
- `.count_interval` = `(floor(N * a_low), ceil(N * a_high))` -- conservative integer bounds from amplitude confidence interval
- `.search_space` = `N` as integer (`2^width`), no separate `.width` property
- `.num_oracle_calls` = total oracle calls from IQAE
- `.count` uses `round(N * amplitude)` clamped to `[0, N]`
- Zero is a valid count -- `.count = 0` with no special case or sentinel
- Identical oracle support to `grover()` and `amplitude_estimate()`: `@grover_oracle` decorated, lambda predicates, explicit qint registers
- Decorated oracles require `predicate=` kwarg for classical verification (same as `amplitude_estimate()`)
- Same qubit-budget warnings when register width > 14 qubits

### Claude's Discretion
- Whether `count_solutions` lives in its own module (`quantum_counting.py`) or in `amplitude_estimation.py`
- Internal implementation details of the amplitude-to-count conversion
- Test structure and verification approach for M=1, M=2, M=3 known-M oracles
- `repr` format for CountResult
- scipy dependency declaration approach in pyproject.toml

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CNT-01 | User can call `ql.count_solutions(oracle, width=n)` to get integer solution count M | Wraps existing `amplitude_estimate()` and converts result; same oracle/register pattern |
| CNT-02 | CountResult includes `.count`, `.estimate`, `.count_interval`, `.search_space`, `.num_oracle_calls` | New class mirroring `AmplitudeEstimationResult` pattern with amplitude-to-count conversion |
| CNT-03 | Quantum counting verified against known-M oracles (M=1,2,3) | Test with lambda predicates: `x==5` (M=1), `x>5` (M=2), `x>4` (M=3) in 3-bit space |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| quantum_language (this project) | 0.1.0 | Quantum circuit framework | This IS the project |
| scipy | >=1.10 | Beta distribution for Clopper-Pearson CI | Already used by IQAE but undeclared in pyproject.toml |
| numpy | >=1.24 | Numerical operations | Already declared dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qiskit | >=1.0 | Circuit simulation backend | Verification/testing only |
| qiskit-aer | >=0.13 | Aer simulator | Verification/testing only |
| pytest | >=7.0 | Test framework | Running tests |

## Architecture Patterns

### Recommended Module Structure
```
src/quantum_language/
├── quantum_counting.py    # NEW: count_solutions() + CountResult
├── amplitude_estimation.py  # Existing: amplitude_estimate() + IQAE internals
├── __init__.py              # Add count_solutions to exports
└── ...
```

**Rationale for separate module:** `quantum_counting.py` keeps the counting-specific logic (CountResult, amplitude-to-count conversion) separate from the IQAE algorithm internals. This mirrors how `grover.py` is separate from `diffusion.py` -- each module has a clear responsibility.

### Pattern 1: Result Wrapper with Numeric Behavior
**What:** A result class that acts like a primitive type (int/float) while carrying metadata
**When to use:** When returning algorithm results that users want to use in expressions
**Example from codebase:**
```python
# From amplitude_estimation.py -- AmplitudeEstimationResult is float-like
class AmplitudeEstimationResult:
    def __float__(self):
        return self._estimate
    def __add__(self, other):
        return self._estimate + float(other)
    def __eq__(self, other):
        try:
            return self._estimate == float(other)
        except (TypeError, ValueError):
            return NotImplemented
```

CountResult follows the same pattern but is int-like instead of float-like:
```python
class CountResult:
    def __int__(self):
        return self._count
    def __add__(self, other):
        return self._count + int(other)
    def __eq__(self, other):
        try:
            return self._count == int(other)
        except (TypeError, ValueError):
            return NotImplemented
```

### Pattern 2: Thin Wrapper over Existing Algorithm
**What:** `count_solutions()` calls `amplitude_estimate()` or `_iqae_loop()` and wraps the result
**When to use:** When adding a new user-facing API that reuses existing algorithm internals
**Implementation approach:**
```python
def count_solutions(oracle, *registers, width=None, widths=None,
                    epsilon=0.01, confidence_level=0.95,
                    max_iterations=None, predicate=None):
    # Call amplitude_estimate() to get amplitude result
    ae_result = amplitude_estimate(oracle, *registers, width=width, widths=widths,
                                    epsilon=epsilon, confidence_level=confidence_level,
                                    max_iterations=max_iterations, predicate=predicate)

    # Compute search space size N
    N = 2 ** total_width  # from register widths

    # Convert amplitude to count
    return CountResult(ae_result, N)
```

### Anti-Patterns to Avoid
- **Reimplementing IQAE:** count_solutions should delegate to amplitude_estimate, not duplicate the algorithm
- **Breaking int-like contract:** CountResult must work in `result == 3` and `int(result)` -- don't return a plain dict
- **Ignoring edge cases:** M=0 (no solutions) and M=N (all solutions) must be handled correctly

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Amplitude estimation | Custom QPE circuit | Existing `_iqae_loop()` | Battle-tested, handles Grover power selection, Bonferroni correction |
| Confidence intervals | Manual CI calculation | Existing `_clopper_pearson_confint()` | Handles edge cases (0/N, N/N) |
| Oracle synthesis | Custom oracle builder | Existing `_predicate_to_oracle()` | Handles lambda, decorated, compiled oracle types |
| Register resolution | Custom width parsing | Existing `_resolve_widths()` | Handles width, widths, explicit register args |

**Key insight:** Everything needed is already implemented in amplitude_estimation.py and grover.py. This phase is a semantic wrapper, not a new algorithm.

## Common Pitfalls

### Pitfall 1: Amplitude-to-Count Rounding Errors
**What goes wrong:** Naive `round(N * amplitude)` can give M=1 when the true answer is M=0 (or vice versa) near boundaries
**Why it happens:** IQAE estimates amplitude with precision epsilon, and the sin^2 mapping amplifies uncertainty near 0 and 1
**How to avoid:** Clamp to [0, N] after rounding. Use count_interval (floor/ceil of CI bounds) to express uncertainty. The user decision locks `.count = round(N * amplitude)` clamped to [0, N], which is correct.
**Warning signs:** Tests passing with generous tolerance but failing at exact equality

### Pitfall 2: Integer Arithmetic Operator Mismatch
**What goes wrong:** `CountResult.__eq__` using `int(other)` fails when `other` is a float like `3.0`
**Why it happens:** Python's `int()` truncates, so `int(3.7) == 3` but the user meant `3.7`
**How to avoid:** In `__eq__`, try `int(other)` but handle floats too. If `other` is a float and not an integer value, return False. Match `AmplitudeEstimationResult` pattern where comparison coerces consistently.
**Warning signs:** `result == 3` works but `result == 3.0` doesn't

### Pitfall 3: Forgetting to Export from __init__.py
**What goes wrong:** `ql.count_solutions()` raises AttributeError because it's not exported
**Why it happens:** New module created but `__init__.py` not updated
**How to avoid:** Add both `from .quantum_counting import count_solutions` and update `__all__`
**Warning signs:** `import quantum_language as ql; ql.count_solutions` fails

### Pitfall 4: Register Width Computation for Multi-Register Oracles
**What goes wrong:** `N = 2^width` is wrong when widths=[4, 4] -- N should be `2^(4+4) = 256`
**Why it happens:** Using single `width` parameter instead of `sum(register_widths)`
**How to avoid:** Compute `N = product of 2^w for w in register_widths` matching grover.py pattern
**Warning signs:** Multi-register count_solutions returns wrong counts

## Code Examples

### CountResult Class (recommended implementation)
```python
import math

class CountResult:
    """Result of quantum counting with int-like behavior."""

    def __init__(self, amplitude_result, search_space):
        N = search_space
        a = amplitude_result.estimate
        ci = amplitude_result.confidence_interval

        self._count = max(0, min(N, round(N * a)))
        self._estimate = N * a
        self._search_space = N
        self._num_oracle_calls = amplitude_result.num_oracle_calls

        if ci is not None:
            self._count_interval = (
                max(0, math.floor(N * ci[0])),
                min(N, math.ceil(N * ci[1]))
            )
        else:
            self._count_interval = (self._count, self._count)

    @property
    def count(self):
        return self._count

    @property
    def estimate(self):
        return self._estimate

    @property
    def count_interval(self):
        return self._count_interval

    @property
    def search_space(self):
        return self._search_space

    @property
    def num_oracle_calls(self):
        return self._num_oracle_calls

    def __int__(self):
        return self._count

    def __eq__(self, other):
        try:
            return self._count == int(other)
        except (TypeError, ValueError):
            return NotImplemented

    def __repr__(self):
        return f"CountResult(count={self._count}, search_space={self._search_space})"
```

### count_solutions() Function (recommended implementation)
```python
def count_solutions(oracle, *registers, width=None, widths=None,
                    epsilon=0.01, confidence_level=0.95,
                    max_iterations=None, predicate=None):
    from .amplitude_estimation import amplitude_estimate

    # Delegate to amplitude_estimate
    ae_result = amplitude_estimate(
        oracle, *registers, width=width, widths=widths,
        epsilon=epsilon, confidence_level=confidence_level,
        max_iterations=max_iterations, predicate=predicate
    )

    # Compute N from register widths
    if registers:
        register_widths = [r.width for r in registers]
    else:
        # Re-resolve widths (same logic as amplitude_estimate)
        ...  # Use _resolve_widths helper

    N = 1
    for w in register_widths:
        N *= 2 ** w

    return CountResult(ae_result, N)
```

### Test Pattern for Known-M Oracles
```python
def test_count_single_solution():
    """M=1: lambda x: x == 5 in 3-bit space. Expected count = 1."""
    result = ql.count_solutions(lambda x: x == 5, width=3, epsilon=0.05)
    assert result.count == 1
    assert result.search_space == 8
    assert result.num_oracle_calls > 0
    assert result.count_interval[0] <= 1 <= result.count_interval[1]
```

## Open Questions

1. **Should CountResult.__eq__ coerce floats?**
   - What we know: User decision says `result == 3` should work
   - What's unclear: Should `result == 3.0` also work?
   - Recommendation: Accept both -- `int(other)` handles `3.0` correctly via Python's int() which truncates, but better to check `other == int(other)` first

2. **Should count_solutions accept the same *registers positional args?**
   - What we know: User decision says "mirror amplitude_estimate() signature" including *registers
   - What's unclear: Need to resolve register widths to compute N even after passing registers through
   - Recommendation: Yes, accept *registers. Extract widths from registers before passing through. This matches the locked API decision.

## Sources

### Primary (HIGH confidence)
- Codebase: `src/quantum_language/amplitude_estimation.py` -- existing IQAE implementation
- Codebase: `src/quantum_language/__init__.py` -- current exports
- Codebase: `tests/python/test_amplitude_estimation.py` -- test patterns
- Codebase: `pyproject.toml` -- missing scipy dependency confirmed

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions -- locked API design from user discussion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all dependencies are already in the codebase
- Architecture: HIGH -- mirrors existing AmplitudeEstimationResult pattern exactly
- Pitfalls: HIGH -- identified from codebase analysis, no external uncertainty

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (stable -- internal codebase patterns)
