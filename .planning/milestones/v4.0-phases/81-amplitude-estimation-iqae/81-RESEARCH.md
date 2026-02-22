# Phase 81: Amplitude Estimation (IQAE) - Research

**Researched:** 2026-02-22
**Domain:** Iterative Quantum Amplitude Estimation (QFT-free)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**API surface:**
- Top-level export: `ql.amplitude_estimate(oracle, *registers, **kwargs)` -- matches `ql.grover()` signature pattern
- Accepts same oracle types as grover(): @grover_oracle decorated functions AND lambda predicates
- Register passing mirrors grover() with `*registers` (not single register)
- Supports `width`/`widths` params like grover() for multi-register consistency
- Lives in its own module: `src/quantum_language/amplitude_estimation.py`
- Epsilon, confidence_level, max_iterations are keyword-only arguments

**Precision & confidence:**
- Default confidence level: 0.95 (95%)
- Default epsilon: Claude's discretion (pick sensible IQAE default from literature)
- Optional `max_iterations` parameter to cap oracle calls
- When max_iterations is hit before reaching precision: return best estimate + emit warning
- Warn (but allow) unreasonable precision requests that would require impractical iterations
- Shots per round determined by algorithm internally, no user-facing shots param
- Follow standard IQAE paper algorithm for everything not explicitly decided above

**Result format:**
- Returns a result object (class, not dict) with `.estimate` (float) and `.num_oracle_calls` (int)
- Result object behaves float-like: supports arithmetic, `float(result)` works (implement `__float__`, numeric dunder methods)
- Default Python repr (no custom pretty-printing)

**Integration with Grover:**
- Reuses existing oracle format -- same @grover_oracle functions and lambda predicates
- Reuses grover() internal iteration machinery (oracle + diffusion) -- no reimplementation
- Auto-synthesizes oracles from lambda predicates, same as grover()
- Supports adaptive mode (unknown M) using Phase 80's exponential backoff infrastructure
- grover() and amplitude_estimate() remain separate functions -- no cross-linking return values
- Tests are standalone IQAE tests -- not cross-validated against grover() results

### Claude's Discretion
- Default epsilon value
- Internal IQAE algorithm details (round scheduling, confidence interval narrowing)
- Warning message text for unreasonable precision / iteration cap
- Internal helper functions and code organization within the module

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AMP-01 | `ql.amplitude_estimate(oracle, register)` returns estimated probability | IQAE main loop returns midpoint of final confidence interval as `.estimate` on result object; reuses `_run_grover_attempt` pattern from grover.py with multi-shot simulation |
| AMP-02 | Uses Iterative QAE (IQAE) variant -- no QFT circuit required | Grinko et al. (2021) IQAE uses only Grover operator powers Q^k, no QFT; circuit is identical to Grover iteration circuit already in codebase |
| AMP-03 | User can specify precision (epsilon) and confidence level | Algorithm takes epsilon (target half-width) and alpha=1-confidence_level; stopping condition is theta interval width <= epsilon/pi |
</phase_requirements>

## Summary

IQAE (Iterative Quantum Amplitude Estimation) estimates the success probability `a` of a quantum oracle by iteratively running Grover circuits with increasing powers `k` and narrowing a confidence interval for the amplitude. The algorithm is due to Grinko, Gacon, Zoufal & Woerner (arXiv:1912.05559, published npj Quantum Information 2021). It achieves O(1/epsilon) oracle calls (up to log factors) with no QFT circuit, using only the same Grover iterate (oracle + diffusion) that Phase 79 already implements.

The implementation is straightforward because the project already has all quantum building blocks: `_run_grover_attempt` builds a fresh circuit with `k` Grover iterations and simulates it, `_predicate_to_oracle` converts lambdas to oracles, and the `GroverOracle` class handles caching and replay. IQAE adds a classical outer loop that: (1) picks the next Grover power `k` via `FindNextK`, (2) runs the circuit with multi-shot measurement (not single-shot like `grover()`), (3) computes a confidence interval from measurement statistics, (4) maps the confidence interval through arccos to refine theta bounds, and (5) repeats until the interval is narrow enough.

The main new complexity is the multi-shot simulation (IQAE needs many shots per round, not just 1) and the classical statistics (Clopper-Pearson confidence intervals via `scipy.stats.beta`). Both are well-understood and have reference implementations in Qiskit.

**Primary recommendation:** Implement IQAE as a pure-Python module `amplitude_estimation.py` with a `_simulate_multi_shot` helper (extending the existing `_simulate_single_shot` pattern), the IQAE main loop, `FindNextK`, confidence interval helpers, and the `AmplitudeEstimationResult` float-like result class. Reuse `_run_grover_attempt`'s circuit-building logic but return QASM for external multi-shot simulation instead of single-shot.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| numpy | 2.4.2 | Math operations (arccos, sin, log, sqrt, pi) | Already used throughout project |
| scipy | 1.17.0 | `scipy.stats.beta.ppf` for Clopper-Pearson confidence intervals | Standard statistical library, already installed |
| qiskit / qiskit_aer | (existing) | Circuit simulation with configurable shots | Already used by `_simulate_single_shot` in grover.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| warnings | stdlib | Emit warnings for max_iterations cap, unreasonable epsilon | Always (user-facing warnings) |
| math | stdlib | Basic math (pi, sqrt, log, ceil, floor) | Can substitute for numpy for simple ops |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Clopper-Pearson (beta) CI | Chernoff-Hoeffding CI | Chernoff is simpler (no scipy needed) but requires more shots for same confidence; Clopper-Pearson is tighter and is the default in Qiskit's IQAE |
| Custom IQAE implementation | Qiskit's `IterativeAmplitudeEstimation` directly | This project has its own circuit infrastructure (C backend + Cython); cannot use Qiskit's algorithm class directly, must implement the classical logic using project's simulation |

## Architecture Patterns

### Recommended Module Structure
```
src/quantum_language/
    amplitude_estimation.py    # NEW: IQAE algorithm + result class
    __init__.py                # UPDATE: add amplitude_estimate export
    grover.py                  # REUSE: _run_grover_attempt pattern, helpers
    oracle.py                  # REUSE: _predicate_to_oracle, GroverOracle
    diffusion.py               # REUSE: diffusion operator (unchanged)
```

### Pattern 1: Circuit Build + Multi-Shot Simulate (adapting `_run_grover_attempt`)
**What:** Build a fresh circuit with `k` Grover iterations, export to QASM, simulate with N shots, return counts dict.
**When to use:** Every IQAE round needs multi-shot measurement of the same circuit.
**Example:**
```python
# Source: Adapted from grover.py _run_grover_attempt + _simulate_single_shot
def _build_grover_circuit(oracle, register_widths, k):
    """Build circuit with k Grover iterations, return QASM string."""
    from .qint import qint as qint_type
    circuit()
    option("fault_tolerant", True)
    registers = [qint_type(0, width=w) for w in register_widths]
    for reg in registers:
        reg.branch(0.5)
    for _ in range(k):
        oracle(*registers)
        _apply_hadamard_layer(registers)
        diffusion(*registers)
        _apply_hadamard_layer(registers)
    return to_openqasm(), registers

def _simulate_multi_shot(qasm_str, shots):
    """Run N-shot simulation, return (one_counts, total_shots)."""
    import qiskit.qasm3
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    circuit_qk = qiskit.qasm3.loads(qasm_str)
    if not circuit_qk.cregs:
        circuit_qk.measure_all()
    sim = AerSimulator(max_parallel_threads=4)
    result = sim.run(transpile(circuit_qk, sim), shots=shots).result()
    counts = result.get_counts()
    return counts
```

### Pattern 2: IQAE Main Loop (theta interval refinement)
**What:** Iteratively select Grover power k, measure, compute confidence interval, refine theta bounds.
**When to use:** Core algorithm loop in `amplitude_estimate()`.
**Example:**
```python
# Source: Grinko et al. (2021) Algorithm 1, verified against Qiskit iae.py
def _iqae_loop(oracle, register_widths, epsilon, alpha, max_iterations):
    theta_interval = [0.0, 0.25]  # initial: theta/2pi in [0, 1/4]
    powers = [0]
    upper_half_circle = True
    num_oracle_queries = 0
    max_rounds = int(np.log(2 * np.pi / 8 / epsilon) / np.log(2)) + 1

    while theta_interval[1] - theta_interval[0] > epsilon / np.pi:
        k, upper_half_circle = _find_next_k(
            powers[-1], upper_half_circle, theta_interval
        )
        powers.append(k)

        # Build circuit and simulate
        qasm = _build_grover_circuit(oracle, register_widths, k)
        shots = _compute_shots(max_rounds, alpha)
        counts = _simulate_multi_shot(qasm, shots)
        one_counts, prob = _count_good_states(counts, register_widths)

        num_oracle_queries += shots * k

        # Check max_iterations cap
        if max_iterations and num_oracle_queries > max_iterations:
            warnings.warn("max_iterations reached before target precision")
            break

        # Confidence interval update
        a_min, a_max = _clopper_pearson_confint(
            one_counts, shots, alpha / max_rounds
        )
        # Map to theta space and refine
        theta_interval = _update_theta_interval(
            theta_interval, a_min, a_max, k, upper_half_circle
        )

    # Final estimate
    a_l = np.sin(2 * np.pi * theta_interval[0]) ** 2
    a_u = np.sin(2 * np.pi * theta_interval[1]) ** 2
    return (a_l + a_u) / 2, num_oracle_queries
```

### Pattern 3: Float-Like Result Object
**What:** Result class that behaves like a float for arithmetic but carries metadata.
**When to use:** Return value of `amplitude_estimate()`.
**Example:**
```python
class AmplitudeEstimationResult:
    """Result of amplitude estimation with float-like behavior."""

    def __init__(self, estimate, num_oracle_calls, confidence_interval=None):
        self._estimate = float(estimate)
        self._num_oracle_calls = int(num_oracle_calls)
        self._confidence_interval = confidence_interval

    @property
    def estimate(self):
        return self._estimate

    @property
    def num_oracle_calls(self):
        return self._num_oracle_calls

    def __float__(self):
        return self._estimate

    def __add__(self, other):
        return self._estimate + float(other)

    def __radd__(self, other):
        return float(other) + self._estimate

    def __mul__(self, other):
        return self._estimate * float(other)

    def __rmul__(self, other):
        return float(other) * self._estimate

    # ... __sub__, __rsub__, __truediv__, __rtruediv__, __neg__,
    #     __abs__, __eq__, __lt__, __le__, __gt__, __ge__,
    #     __int__, __round__, __bool__

    def __repr__(self):
        return (f"AmplitudeEstimationResult(estimate={self._estimate}, "
                f"num_oracle_calls={self._num_oracle_calls})")
```

### Anti-Patterns to Avoid
- **Re-implementing oracle/diffusion logic:** The oracle call and H-diffusion-H Grover iterate already exist in `_run_grover_attempt`. Do not rewrite. Refactor to share the circuit-building portion.
- **Using single-shot simulation for IQAE:** IQAE requires many shots per round for statistical confidence. The existing `_simulate_single_shot` returns a single bitstring; IQAE needs counts.
- **Hardcoding shots:** The IQAE paper computes required shots from alpha, max_rounds, and the confidence interval method. Let the algorithm determine this.
- **Using QFT circuits:** IQAE explicitly avoids QFT. The circuit is just Q^k A|0> where Q is the standard Grover operator.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Clopper-Pearson confidence intervals | Manual beta distribution inverse CDF | `scipy.stats.beta.ppf(q, a, b)` | Edge cases at counts=0 and counts=shots need special handling; scipy handles NaN gracefully |
| Grover operator circuit (Q^k) | New circuit construction | Reuse `_run_grover_attempt` pattern from grover.py | Already handles circuit init, register allocation, H-sandwich, oracle caching |
| Oracle synthesis from lambda | New lambda-to-oracle converter | `_predicate_to_oracle` from oracle.py | Already handles tracing, caching, closure values |
| Qiskit simulation | Custom statevector math | `AerSimulator` with `shots=N` via `_simulate_multi_shot` | Consistent with project's simulation infrastructure |

**Key insight:** The IQAE implementation is ~80% classical statistics + loop control and ~20% quantum circuit construction. The quantum part is already built (Phases 78-80). The classical part has a well-tested reference implementation in Qiskit's `iae.py` to follow.

## Common Pitfalls

### Pitfall 1: "Good State" Measurement Interpretation
**What goes wrong:** IQAE measures the probability of a "good state" (oracle-marked state). In Grover search, the oracle marks states via phase flip. When measuring, we need to identify which bitstrings correspond to "good" states.
**Why it happens:** In standard QAE (textbook), the oracle uses an ancilla qubit whose measurement directly indicates good/bad. In this project's oracle pattern, the phase flip is implicit -- there's no ancilla measurement bit that says "this is a marked state."
**How to avoid:** After applying Q^k A|0>, the amplitude of marked states is `sin^2((2k+1) * theta_a)` where `theta_a = arcsin(sqrt(a))`. The measurement probability of each basis state already encodes this. For IQAE, we need to know which states are "good." Two approaches: (A) Use an explicit ancilla qubit that the oracle flips, then measure that ancilla; or (B) Use the classical predicate to classify measured bitstrings. Approach (B) is simpler and matches the project's existing patterns -- run multi-shot simulation, parse each bitstring, count how many satisfy the predicate.
**Warning signs:** If estimated amplitude is always 0 or 1, the good-state counting logic is wrong.

### Pitfall 2: Theta Interval Mapping with Scaling Factor
**What goes wrong:** When scaling the theta interval by K = 4k+2, the interval wraps around 2pi. The algorithm must track which half-circle (upper [0,pi] or lower [pi,2pi]) the scaled interval falls in, because arccos is only invertible on [0,pi].
**Why it happens:** The relationship a = sin^2(theta) = (1 - cos(2*theta))/2 has the same value at theta and -theta. Scaling by K amplifies this ambiguity.
**How to avoid:** Follow the Qiskit reference implementation exactly for `_find_next_k` and the theta interval update. The `upper_half_circle` boolean tracks which half the interval is in. Use `int(scaling * theta_l)` and `int(scaling * theta_u)` for the integer part when unscaling.
**Warning signs:** Confidence interval doesn't narrow across iterations, or estimate diverges.

### Pitfall 3: 17-Qubit Simulator Limit
**What goes wrong:** IQAE circuits with large search registers plus comparison ancilla qubits exceed the 17-qubit Aer simulator limit, causing simulation failure or extreme slowness.
**Why it happens:** Even a 3-bit search register with inequality comparisons allocates ancilla qubits for the comparison logic. Multi-shot simulation with many shots amplifies the cost.
**How to avoid:** Test with small register widths (2-3 bits). Use `max_parallel_threads=4` always. Warn users when total qubit count approaches 17. Keep default test cases under 14 search qubits (leaves room for ancilla).
**Warning signs:** Tests hanging, memory errors, or Qiskit transpile failures.

### Pitfall 4: Circuit Freshness Between Rounds
**What goes wrong:** The project's circuit state is global. Each IQAE round needs a fresh circuit with a different power k. If you don't call `circuit()` to reset, gates from previous rounds accumulate.
**Why it happens:** The C backend maintains a single global circuit. `_run_grover_attempt` already calls `circuit()` to reset.
**How to avoid:** Each IQAE round must start with a fresh `circuit()` call, same as `_run_grover_attempt` does. Factor out circuit building so each round builds its own.
**Warning signs:** QASM string grows unboundedly across iterations, circuit has thousands of gates after 3 rounds.

### Pitfall 5: Shots per Round vs Oracle Calls Accounting
**What goes wrong:** `max_iterations` is meant to cap total oracle calls, not simulation shots. Each shot at power k costs k oracle calls. Total oracle cost for a round = shots * k.
**Why it happens:** Confusing "iterations" (IQAE rounds) with "oracle calls" (shots * power per round).
**How to avoid:** Track `num_oracle_queries += shots * k` per round. The `max_iterations` parameter caps `num_oracle_queries`, not the number of IQAE rounds.
**Warning signs:** max_iterations doesn't actually limit computation time.

## Code Examples

### Good State Counting from Multi-Shot Measurement
```python
# Approach: Run circuit, measure all qubits, use classical predicate
# to classify each bitstring as good/bad
def _count_good_states(counts, register_widths, predicate):
    """Count measurement outcomes that satisfy the predicate.

    Parameters
    ----------
    counts : dict
        Qiskit measurement counts {bitstring: count}.
    register_widths : list[int]
        Width of each search register.
    predicate : callable
        Classical predicate function.

    Returns
    -------
    (int, int)
        (good_counts, total_shots)
    """
    good_counts = 0
    total_shots = 0
    for bitstring, count in counts.items():
        total_shots += count
        values = _parse_bitstring(bitstring, register_widths)
        if _verify_classically(predicate, values):
            good_counts += count
    return good_counts, total_shots
```

### Clopper-Pearson Confidence Interval
```python
# Source: Qiskit iae.py _clopper_pearson_confint, verified against scipy docs
from scipy.stats import beta

def _clopper_pearson_confint(counts, shots, alpha):
    """Compute Clopper-Pearson confidence interval.

    Parameters
    ----------
    counts : int
        Number of "good" outcomes.
    shots : int
        Total number of measurements.
    alpha : float
        Significance level (CI is 1-alpha).

    Returns
    -------
    (float, float)
        Lower and upper bounds for the true probability.
    """
    lower, upper = 0.0, 1.0
    if counts != 0:
        lower = beta.ppf(alpha / 2, counts, shots - counts + 1)
    if counts != shots:
        upper = beta.ppf(1 - alpha / 2, counts + 1, shots - counts)
    return lower, upper
```

### FindNextK Implementation
```python
# Source: Qiskit iae.py _find_next_k, following Grinko et al. Algorithm 2
def _find_next_k(k, upper_half_circle, theta_interval, min_ratio=2.0):
    """Find largest k_next such that scaled interval stays in one half-circle.

    Parameters
    ----------
    k : int
        Current Grover power.
    upper_half_circle : bool
        Whether current interval is in upper half.
    theta_interval : tuple[float, float]
        Current (theta_l, theta_u) normalized to [0, 1].
    min_ratio : float
        Minimum ratio K_next / K_current for convergence.

    Returns
    -------
    (int, bool)
        (next_power, upper_half_circle)
    """
    theta_l, theta_u = theta_interval
    old_scaling = 4 * k + 2

    # Maximum scaling bounded by interval width
    max_scaling = int(1 / (2 * (theta_u - theta_l)))
    scaling = max_scaling - (max_scaling - 2) % 4  # enforce form 4k+2

    while scaling >= min_ratio * old_scaling:
        theta_min = scaling * theta_l - int(scaling * theta_l)
        theta_max = scaling * theta_u - int(scaling * theta_u)

        if theta_min <= theta_max <= 0.5 and theta_min <= 0.5:
            return int((scaling - 2) / 4), True
        elif theta_max >= 0.5 and theta_max >= theta_min >= 0.5:
            return int((scaling - 2) / 4), False

        scaling -= 4

    return k, upper_half_circle
```

### Theta Interval Update
```python
# Source: Qiskit iae.py estimate() main loop, Grinko et al. Section III
def _update_theta_interval(theta_interval, a_min, a_max, k, upper_half_circle):
    """Refine theta interval from measured amplitude bounds.

    Maps measured probability bounds [a_min, a_max] through arccos
    to theta space, accounts for scaling factor K = 4k+2, and
    intersects with previous interval.
    """
    scaling = 4 * k + 2

    if upper_half_circle:
        theta_min_i = np.arccos(1 - 2 * a_min) / 2 / np.pi
        theta_max_i = np.arccos(1 - 2 * a_max) / 2 / np.pi
    else:
        theta_min_i = 1 - np.arccos(1 - 2 * a_max) / 2 / np.pi
        theta_max_i = 1 - np.arccos(1 - 2 * a_min) / 2 / np.pi

    # Unscale: combine with previous interval bounds
    theta_u = (int(scaling * theta_interval[1]) + theta_max_i) / scaling
    theta_l = (int(scaling * theta_interval[0]) + theta_min_i) / scaling

    return [theta_l, theta_u]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QPE-based QAE (Brassard 2000) | IQAE (Grinko 2021) | 2019-2021 | No QFT needed, fewer qubits, same asymptotic scaling |
| Suzuki MLQAE (2020) | IQAE preferred for simplicity | 2021 | IQAE has simpler implementation, no MLE optimization step |
| Chernoff confidence intervals | Clopper-Pearson (beta) default | Qiskit adoption | Tighter intervals, fewer shots needed |

**Deprecated/outdated:**
- QPE-based amplitude estimation: Replaced by QFT-free variants (IQAE, MLQAE) for practical implementations
- Qiskit Aqua `IterativeAmplitudeEstimation`: Moved to `qiskit-algorithms` community package; algorithm logic is the same

## Algorithm Parameter Recommendations

### Default Epsilon: 0.01
**Rationale:** This is the most common default in IQAE literature and implementations. For a 3-bit search space (N=8), M=1 solution has true probability a=1/8=0.125. Epsilon=0.01 means the estimate will be in [0.115, 0.135] which is meaningful. Epsilon=0.1 would be too coarse for small spaces. Epsilon=0.001 would require impractical oracle calls for simulator testing.

**Confidence:** MEDIUM -- based on Qiskit examples and Qrisp defaults (both use eps=0.01 in demos). This is Claude's discretion per CONTEXT.md.

### Shots Per Round
**Formula (from paper):** `N_shots = ceil(32 / (1 - 2*sin(pi/14))^2 * ln(2 * max_rounds / alpha))`
**Simplified:** For alpha=0.05, max_rounds~10, this gives N_shots ~ 100-200.
**Recommendation:** Compute from the formula. The Qiskit implementation uses a fixed shot count per circuit execution (configurable via sampler), typically 100-1000. For our simulator-limited setup, 100 shots per round is reasonable.

### Max Rounds
**Formula:** `T = int(log(min_ratio * pi / 8 / epsilon) / log(min_ratio)) + 1`
**For defaults (epsilon=0.01, min_ratio=2):** T ~ 8-10 rounds.

## Implementation Plan Sketch

The implementation naturally splits into two plans:

**Plan 1: Core IQAE Algorithm + Result Class**
- `AmplitudeEstimationResult` class with float-like behavior
- `_simulate_multi_shot` helper (extending existing simulation pattern)
- `_find_next_k` (FindNextK algorithm)
- `_clopper_pearson_confint` (confidence interval computation)
- `_count_good_states` (bitstring classification using predicate)
- `_iqae_loop` (main algorithm loop)
- `amplitude_estimate()` public API function
- Export from `__init__.py`

**Plan 2: Tests**
- Unit tests for helpers (_find_next_k, _clopper_pearson_confint, result arithmetic)
- Integration tests with known oracles (exact probability verification)
- Lambda predicate tests
- max_iterations cap test
- Epsilon/confidence_level parameter tests

## Open Questions

1. **Good state identification for decorated oracles (not predicates)**
   - What we know: Lambda predicates can use `_verify_classically` to classify measured bitstrings. This is the approach for Pitfall 1.
   - What's unclear: For `@grover_oracle` decorated functions (not lambdas), there's no classical predicate to verify against. How do we count "good" states?
   - Recommendation: For decorated oracles, require the user to also pass a `predicate` keyword argument for classical verification. Alternatively, use the oracle's structure: if the oracle marks state |x> with a phase flip, then after Q^k A|0>, all states have amplitudes that depend on a. The total measurement probability in the computational basis is always 1 -- we need to know WHICH states are "good." The simplest approach: for lambdas, use the predicate. For decorated oracles, require `predicate=` kwarg or `target_states=` kwarg. This is a design decision for the planner.

2. **Oracle call accounting with cached oracles**
   - What we know: `GroverOracle` caches gate sequences after first call and replays. Replay is cheaper than first call but still counts as an oracle call algorithmically.
   - What's unclear: Does the IQAE max_iterations count include the shots within each round?
   - Recommendation: Count `num_oracle_queries += shots * k` per round (each shot at power k uses k oracle calls). This matches the standard IQAE query complexity accounting.

## Sources

### Primary (HIGH confidence)
- Qiskit `qiskit-algorithms` source code: `iae.py` -- Complete reference implementation of IQAE algorithm with FindNextK, Clopper-Pearson, Chernoff, theta interval updates. Verified by reading full source from GitHub.
- Project codebase: `grover.py`, `oracle.py`, `diffusion.py` -- Existing Grover infrastructure (circuit building, oracle caching, predicate synthesis, multi-shot simulation pattern)

### Secondary (MEDIUM confidence)
- Grinko, D., Gacon, J., Zoufal, C., & Woerner, S. (2021). "Iterative Quantum Amplitude Estimation." npj Quantum Information 7, 52. arXiv:1912.05559. -- Original IQAE paper with Algorithm 1, Algorithm 2 (FindNextK), Theorem 1 (query complexity)
- Qiskit `IterativeAmplitudeEstimation` API docs: https://qiskit-community.github.io/qiskit-algorithms/stubs/qiskit_algorithms.IterativeAmplitudeEstimation.html -- Parameter descriptions and defaults (epsilon_target, alpha, confint_method, min_ratio)

### Tertiary (LOW confidence)
- Qrisp IQAE documentation (https://qrisp.eu/reference/Primitives/IQAE.html) -- Alternative implementation reference, limited detail available
- Default epsilon=0.01 recommendation -- based on common usage patterns in demos, not formally standardized

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- numpy, scipy, qiskit_aer all already in project; no new dependencies
- Architecture: HIGH -- module structure follows established grover.py/oracle.py pattern; algorithm is well-specified in paper and Qiskit reference
- Pitfalls: HIGH -- identified from both theoretical understanding (theta mapping ambiguity) and practical project constraints (17-qubit limit, global circuit state)
- Algorithm details: HIGH -- Full Qiskit source code retrieved and analyzed for FindNextK, confidence intervals, theta update, stopping condition

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable algorithm, no expected changes)
