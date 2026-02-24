# Feature Research: v5.0 Advanced Arithmetic & Compilation

**Domain:** Quantum programming framework -- modular Toffoli arithmetic, parametric compilation, depth/ancilla tradeoff, quantum counting
**Researched:** 2026-02-24
**Confidence:** MEDIUM-HIGH (well-established quantum computing algorithms, strong existing codebase to build on)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that users of a quantum programming framework with Toffoli arithmetic and Grover infrastructure would expect to find.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Modular addition mod N (Toffoli)** | Any Shor's implementation needs `(a + b) mod N` with reversible gates; existing `qint_mod` uses QFT-based add underneath which defeats fault-tolerant purpose | HIGH | Requires compare-subtract pattern: add, compare with N, conditionally subtract N, uncompute comparison. Current `_reduce_mod` is broken (BUG-MOD-REDUCE). New implementation must use Beauregard-style single conditional subtraction rather than iterative approach |
| **Modular subtraction mod N (Toffoli)** | Inverse of modular addition; needed for uncomputation and modular multiplication | MEDIUM | Derived from modular addition via adjoint: sub mod N = add mod N with negated operand, or run mod-add in reverse. Standard pattern: add N, then subtract, then conditionally add N based on overflow |
| **Controlled modular addition** | Modular exponentiation requires controlled modular multiply, which decomposes into controlled modular adds | HIGH | Convert final comparison CX to CCX (Toffoli) to make it controlled. Adds one control qubit to every gate in the mod-add circuit. Existing `_derive_controlled_gates` in compile.py handles this pattern |
| **Quantum counting (`ql.count_solutions`)** | Natural companion to `ql.grover()` and `ql.amplitude_estimate()`; users who search want to know how many solutions exist | LOW | M = N * sin^2(theta) where theta is estimated via IQAE. Reuses existing IQAE infrastructure almost entirely |
| **Depth/ancilla tradeoff awareness** | Users with Toffoli arithmetic expect to choose between CDKM (O(n) depth, 1 ancilla) and BK CLA (O(log n) depth, O(n) ancilla) based on their constraints | MEDIUM | Already have both adders; need selection API and auto-selection heuristic |

### Differentiators (Competitive Advantage)

Features that set the framework apart from Qiskit, Cirq, or other quantum programming tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Parametric compilation** | Compile `f(x, classical_val)` once as a template, then substitute different classical values without re-capturing. No other framework at this level offers this for circuit-building DSLs | HIGH | Current cache key includes `tuple(classical_args)` -- different classical values cause full re-capture. Parametric mode would capture gate structure with symbolic classical slots, then instantiate per-value. Key insight: CQ operations already vary only in which X gates fire based on classical bits |
| **Automatic depth/ancilla tradeoff** | User says `ql.option('optimize_for', 'depth')` or `'qubits'` and framework auto-selects RCA vs CLA for every addition. No manual per-operation configuration needed | MEDIUM | Heuristic: use CLA when width >= threshold AND ancilla budget allows. Could also expose `ql.option('adder', 'cdkm'|'bk_cla'|'auto')` for explicit control |
| **Modular multiplication mod N (Toffoli)** | End-to-end Shor's requires `(a * b) mod N`; implementing this with pure Toffoli gates (no QFT rotations) enables full fault-tolerant Shor's pipeline | HIGH | Decompose into repeated controlled modular additions via shift-and-add, same pattern as existing Toffoli schoolbook multiplication but with mod-reduce after each partial product. Requires working mod-add first |
| **Natural-syntax quantum counting** | `M = ql.count_solutions(lambda x: x > 5, width=3)` returns integer estimate. Consistent API with existing `ql.grover()` and `ql.amplitude_estimate()` | LOW | Thin wrapper: call IQAE, compute M = round(N * estimate). Same oracle/predicate infrastructure |
| **Compile-time adder budget analysis** | Report estimated depth and ancilla cost before running, letting user make informed tradeoff decisions | LOW | Extend `ql.circuit_stats()` with per-operation breakdown. Useful for resource estimation |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems in this context.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full Shor's algorithm end-to-end API** | Users want `ql.factor(N)` | Requires QPE wrapper, modular exponentiation, classical post-processing (continued fractions), and scales to thousands of qubits that cannot be simulated. Would be untestable on current 17-qubit simulator limit | Provide modular arithmetic building blocks; users compose Shor's themselves. Document the composition pattern |
| **Automatic Clifford+T decomposition in mod-add** | Users want minimal T-count for fault-tolerant mod-add | Applying CCX decomposition inside the mod-add circuit explodes gate count by 15x per Toffoli, making circuits unwieldy and slow to generate. The decomposition is already available via `ql.option('toffoli_decompose', True)` as a separate pass | Keep decomposition as post-processing step, not baked into mod-add generation |
| **QFT-based modular arithmetic (Beauregard coset)** | Beauregard's original uses QFT-basis addition which has lower qubit count (2n+3) | Mixes QFT rotations into fault-tolerant pipeline, defeating the purpose of Toffoli backend. Rotation synthesis adds enormous overhead. Current QFT division is broken (BUG-QFT-DIV) | Focus on purely Toffoli-based modular arithmetic (Haner-Roetteler-Svore style) |
| **Dynamic parametric recompilation** | Users want to change parameters mid-circuit | Violates compile-then-execute model. Parameters must be classical and known at circuit generation time | Parametric compilation with `assign_parameters()` before circuit export, not during |
| **Optimal adder selection per individual operation** | Users want different adder for each `+` in the same circuit | Per-operation dispatch adds complexity with minimal benefit; in practice all additions in a circuit face the same depth/qubit constraint | Global adder selection via `ql.option()`, not per-operation |

## Feature Dependencies

```
Bug fixes (BUG-DIV-02, BUG-MOD-REDUCE)
    |
    v
Modular Addition mod N (Toffoli)
    |
    +----> Modular Subtraction mod N (Toffoli)
    |          |
    |          v
    +----> Controlled Modular Addition
    |          |
    |          v
    +----> Modular Multiplication mod N (Toffoli)

Existing IQAE (amplitude_estimate)
    |
    v
Quantum Counting (count_solutions)

Existing @ql.compile cache system
    |
    v
Parametric Compilation (symbolic classical slots)

Existing CDKM + BK CLA adders
    |
    v
Automatic Depth/Ancilla Tradeoff (adder selection)
```

### Dependency Notes

- **Modular Addition requires bug fixes first:** BUG-MOD-REDUCE is in `_reduce_mod` which is the core of modular reduction. The current iterative compare-subtract loop is both broken and inefficient. Must redesign to single-pass Beauregard-style conditional subtraction before building modular Toffoli arithmetic on top.
- **Modular Multiplication requires Modular Addition:** The schoolbook multiply-mod-N decomposes into `n` controlled modular additions with shift. Cannot build without working mod-add.
- **Controlled Modular Addition requires Modular Addition:** Adds one control qubit to every gate in the mod-add circuit. Must have correct mod-add first.
- **Quantum Counting is independent:** Only depends on existing IQAE infrastructure which is already working and tested.
- **Parametric Compilation is independent:** Extends existing `@ql.compile` cache system. No dependency on arithmetic features.
- **Depth/Ancilla Tradeoff is independent:** Both adders already exist. Just needs selection logic and API.

## MVP Definition

### Phase 1: Independent Features (No Arithmetic Dependencies)

Features that can be built immediately without waiting for bug fixes.

- [ ] **Quantum Counting (`ql.count_solutions`)** -- Thin wrapper over existing IQAE. M = N * sin^2(theta). Consistent API with grover/amplitude_estimate. LOW effort, HIGH value.
- [ ] **Automatic Depth/Ancilla Tradeoff** -- Add `ql.option('adder', 'auto'|'cdkm'|'bk_cla')` with auto-selection heuristic. Both adders exist. MEDIUM effort, MEDIUM value.
- [ ] **Parametric Compilation (basic)** -- Extend `@ql.compile` to recognize classical int arguments and generate template sequences with substitution slots. HIGH effort, HIGH value for repeated classical-value circuits.

### Phase 2: Bug Fix Prerequisites

Must fix before modular Toffoli arithmetic.

- [ ] **Fix BUG-DIV-02** -- MSB comparison leak in division. Uncomputation architecture redesign for orphan temporaries.
- [ ] **Fix BUG-QFT-DIV** -- QFT division/modulo failures. Depends on BUG-DIV-02.
- [ ] **Fix BUG-MOD-REDUCE** -- Redesign `_reduce_mod` from iterative compare-subtract to single-pass Beauregard-style conditional subtraction.

### Phase 3: Modular Toffoli Arithmetic

Build once bug fixes are solid.

- [ ] **Modular Addition mod N (Toffoli)** -- Core building block. Compare with N, conditionally subtract N.
- [ ] **Modular Subtraction mod N (Toffoli)** -- Adjoint of modular addition.
- [ ] **Controlled Modular Addition** -- Add control qubit to mod-add circuit.
- [ ] **Modular Multiplication mod N (Toffoli)** -- Schoolbook shift-and-add with mod-reduce.

### Future Consideration (v6+)

- [ ] **Modular Exponentiation** -- Repeated squaring with controlled modular multiply. Requires working mod-mul first. Deferred because circuit sizes exceed simulator capacity.
- [ ] **Resource Estimation for Modular Circuits** -- T-count, depth, qubit estimates for Shor's at various bit widths. Useful for publications but not needed for framework functionality.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Dependencies |
|---------|------------|---------------------|----------|--------------|
| Quantum Counting | HIGH | LOW | P1 | None (IQAE exists) |
| Depth/Ancilla Tradeoff | MEDIUM | MEDIUM | P1 | None (both adders exist) |
| Parametric Compilation | HIGH | HIGH | P1 | None (extends @ql.compile) |
| Fix BUG-MOD-REDUCE | HIGH | HIGH | P1 | None |
| Fix BUG-DIV-02 | HIGH | HIGH | P1 | None |
| Fix BUG-QFT-DIV | MEDIUM | MEDIUM | P2 | BUG-DIV-02 |
| Modular Add mod N (Toffoli) | HIGH | HIGH | P2 | BUG-MOD-REDUCE fix |
| Modular Sub mod N (Toffoli) | MEDIUM | LOW | P2 | Mod Add |
| Controlled Mod Add | HIGH | MEDIUM | P2 | Mod Add |
| Modular Mul mod N (Toffoli) | HIGH | HIGH | P2 | Controlled Mod Add |

**Priority key:**
- P1: Build immediately (no blockers, or is itself a blocker)
- P2: Build after prerequisites are complete
- P3: Nice to have, future consideration

## Detailed Feature Specifications

### 1. Modular Toffoli Arithmetic

**Algorithm: Modular Addition `(a + b) mod N` using Toffoli gates**

The standard Beauregard-style modular addition uses this pattern:
1. **Add:** Compute `a + b` using CDKM or BK CLA adder
2. **Compare:** Check if `(a + b) >= N` by subtracting N and checking overflow/sign bit
3. **Conditional subtract:** If overflow, subtract N to reduce result
4. **Uncompute comparison:** Restore comparison ancilla to |0>

The critical insight is that the comparison ancilla must be fully uncomputed. The existing `_reduce_mod` fails because it creates orphan comparison qbools that corrupt the circuit state (BUG-MOD-REDUCE).

**Correct single-pass implementation:**
```
|a> |b> |0_ancilla>
  --> add(a, b)              --> |a> |a+b> |0>
  --> sub(N, result)         --> |a> |a+b-N> |0>  (may underflow)
  --> copy MSB to ancilla    --> |a> |a+b-N> |msb>
  --> if ancilla: add(N)     --> |a> |correct> |msb>
  --> uncompute ancilla      --> |a> |(a+b) mod N> |0>
```

The ancilla uncomputation step is the tricky part. It requires:
- Add b back to the result (giving a+b or a+b-N+N=a+b)
- Check if result >= N (which tells us whether we subtracted or not)
- Copy this comparison to a fresh ancilla
- Subtract b again

This produces a clean ancilla and the correct `(a+b) mod N` in the result register.

**Qubit cost:** Input qubits + 1 ancilla (for overflow flag) + adder ancilla (1 for CDKM, O(n) for CLA)
**Gate cost:** O(n) Toffoli gates (3 additions + comparison)
**Depth:** O(n) with CDKM, O(n log n) with CLA (paradoxically, CLA helps less here because additions are sequential)

**Controlled modular addition:** Replace final comparison CNOT with Toffoli (add one more control to each gate). This is already supported by `_derive_controlled_gates` in compile.py and the C-level cQQ/cCQ infrastructure.

**Modular multiplication `(a * c) mod N` (c classical):**
Schoolbook method -- for each bit i of classical c:
1. If bit i is 1: controlled add `(a << i) mod N` to accumulator
2. Reduce accumulator mod N after each partial product

This mirrors the existing Toffoli schoolbook multiplication pattern in `ToffoliMultiplication.c` but with mod-reduce interleaved.

**Integration with existing `qint_mod` class:**
The existing `qint_mod` in `qint_mod.pyx` already has the right API (`__add__`, `__sub__`, `__mul__` operators). The fix is to replace the `_reduce_mod` implementation with the Beauregard-style circuit, and route through Toffoli add/sub when `ql.option('fault_tolerant')` is true.

**Confidence: HIGH** -- These are well-established algorithms from Beauregard (2003) and Haner-Roetteler-Svore (2017).

### 2. Parametric Compilation

**What it does:** Compile a quantum function once for a given qubit width, then replay with different classical parameter values without re-capturing the gate sequence.

**Current behavior (problem):**
```python
@ql.compile
def add_const(x, c):
    x += c
    return x

add_const(qint(0, width=4), 3)   # Capture for c=3
add_const(qint(0, width=4), 7)   # Re-capture for c=7 (different cache key!)
add_const(qint(0, width=4), 11)  # Re-capture for c=11 (again!)
```

Each classical value causes a full re-capture because the cache key includes `tuple(classical_args)` at line 608 of compile.py.

**Desired behavior:**
```python
@ql.compile(parametric=True)
def add_const(x, c):
    x += c
    return x

add_const(qint(0, width=4), 3)   # Capture template with c as parameter
add_const(qint(0, width=4), 7)   # Instantiate template for c=7 (fast!)
add_const(qint(0, width=4), 11)  # Instantiate template for c=11 (fast!)
```

**Implementation approach:**

The key insight is that CQ (classical-quantum) operations already work by emitting different gate patterns based on classical bit values. For `x += c`, the gates that change between different `c` values are only the X gates that initialize the temporary classical register and the CQ-specific gate simplifications.

Two viable strategies:

**Strategy A -- Gate template with classical slots (recommended):**
During capture, mark gates that depend on classical arguments with a "slot" annotation. On replay, fill slots based on the new classical value. This requires tracking which gates are classical-value-dependent during capture.

What changes in the cached gate list between different classical values:
1. X gates that initialize temporary registers with the classical value
2. Gate elision in CQ-inline paths (gates skipped when classical bit is 0)
3. Rotation angles in QFT-based CQ operations (angle depends on classical bits)

For Toffoli backend (CQ operations): only X gates change. The CCX/CX structure is identical.
For QFT backend (CQ operations): rotation angles change based on classical value.

**Strategy B -- Width-only cache key (simpler fallback):**
Change cache key from `(classical_args, widths)` to just `(widths)` when `parametric=True`. Re-execute the function body on each call but skip gates already captured. Simpler but still requires function re-execution.

**Recommended: Strategy A** because it avoids re-execution entirely.

**API design:**
```python
@ql.compile(parametric=True)
def add_const(x, c):
    x += c
    return x

# Or with explicit parameter annotation:
@ql.compile(parametric=['c'])
def add_const(x, c):
    x += c
    return x
```

The `parametric=True` form auto-detects classical arguments (non-qint, non-qarray). The `parametric=['c']` form explicitly names which arguments are parametric.

**Complexity: HIGH** -- Requires careful analysis of which gates are classical-value-dependent during capture, and a template instantiation mechanism. The gate dicts in CompiledBlock must support conditional inclusion and value substitution.

**Confidence: MEDIUM** -- Novel feature for this framework. Qiskit has `Parameter` objects but they work differently (symbolic angles, not classical integer parameters to arithmetic operations). No direct precedent for this exact pattern in any quantum framework.

### 3. Automatic Depth/Ancilla Tradeoff

**What it does:** Automatically select between CDKM ripple-carry adder and Brent-Kung CLA adder based on user-specified optimization target.

**Current state:**
- CDKM: O(n) depth, 1 ancilla, ~6n Toffoli gates. Default adder.
- BK CLA: O(log n) depth, O(n) ancilla, ~4n Toffoli gates. Available but must be explicitly selected.
- Selection: `ql.option('cla_adder', 'bk')` vs default CDKM. Binary, manual.

**Proposed API:**
```python
ql.option('adder', 'auto')      # Auto-select based on optimize_for
ql.option('adder', 'cdkm')      # Force CDKM (qubit-efficient circuits)
ql.option('adder', 'bk_cla')    # Force BK CLA (depth-efficient circuits)

ql.option('optimize_for', 'depth')    # Prefer CLA when possible
ql.option('optimize_for', 'qubits')   # Prefer CDKM always
ql.option('optimize_for', 'balanced') # Auto-select based on width threshold
```

**Auto-selection heuristic:**
- Width <= 4: Always use CDKM (CLA overhead not worth it for small widths, log(4)=2 vs 4 is marginal)
- Width 5-8: Use CDKM unless `optimize_for='depth'`
- Width >= 9: Use BK CLA (O(log n) depth savings become significant: log(16)=4 vs 16)
- If total circuit qubit count approaching 17-qubit simulator limit: Fall back to CDKM to save ancillas

**Known limitation to document:** BK CLA subtraction currently falls back to CDKM RCA because carry-copy ancilla cannot be uncomputed in reverse. This means depth savings only apply to addition, not subtraction. This must be clearly documented.

**Implementation plan:**
1. Add `'adder'` and `'optimize_for'` options to `ql.option()` registry
2. Modify dispatch logic in `_core.pyx` or `qint_arithmetic.pxi` that calls C-level add/sub
3. C-level dispatch already exists between CDKM and CLA -- just need Python-level plumbing
4. Add width-based heuristic for `'auto'` mode

**Complexity: MEDIUM** -- Both adders exist and are tested. Main work is dispatch logic and API design.

**Confidence: HIGH** -- Straightforward engineering on top of existing infrastructure.

### 4. Quantum Counting (`ql.count_solutions`)

**What it does:** Estimate the number of solutions M for a given oracle/predicate over a search space of size N.

**Algorithm (Brassard-Hoyer-Mosca-Tapp 1998):**
1. Use IQAE to estimate `a = sin^2(theta)` where theta encodes the fraction of solutions
2. Compute `M = round(N * a)` where `N = 2^n` is the search space size
3. Derive confidence interval: `M_lower = floor(N * ci_lower)`, `M_upper = ceil(N * ci_upper)`

**Proposed API:**
```python
# Basic usage
result = ql.count_solutions(lambda x: x > 5, width=3)
print(result.count)           # Estimated M (integer)
print(result.estimate)        # Raw amplitude estimate (float)
print(result.count_interval)  # (M_lower, M_upper) confidence interval
print(result.search_space)    # N = 2^width

# With precision control
result = ql.count_solutions(
    lambda x: x > 5,
    width=3,
    epsilon=0.01,              # Precision of amplitude estimate
    confidence_level=0.95,     # Confidence level
)

# Multi-register
result = ql.count_solutions(
    lambda x, y: x + y == 10,
    widths=[4, 4],
)
```

**Return type:** `CountingResult` class with:
- `.count` -- Integer estimate of M (rounded)
- `.estimate` -- Raw IQAE amplitude (float, the sin^2(theta) value)
- `.count_interval` -- `(lower, upper)` integer bounds from CI
- `.search_space` -- N (total search space size)
- `.num_oracle_calls` -- Total oracle calls used

**Implementation:** Nearly trivial wrapper around existing `amplitude_estimate()`:
```python
class CountingResult:
    def __init__(self, count, estimate, search_space, count_interval, num_oracle_calls):
        self.count = count
        self.estimate = estimate
        self.search_space = search_space
        self.count_interval = count_interval
        self.num_oracle_calls = num_oracle_calls

def count_solutions(oracle, *registers, width=None, widths=None,
                    epsilon=0.01, confidence_level=0.95, max_iterations=None):
    ae_result = amplitude_estimate(
        oracle, *registers, width=width, widths=widths,
        epsilon=epsilon, confidence_level=confidence_level,
        max_iterations=max_iterations
    )
    # Compute search space size
    if registers:
        N = 1
        for r in registers:
            N *= 2 ** r.width
    elif widths:
        N = 1
        for w in widths:
            N *= 2 ** w
    else:
        N = 2 ** width

    count = round(N * ae_result.estimate)
    ci = ae_result.confidence_interval
    ci_lower = max(0, int(N * ci[0]))
    ci_upper = min(N, int(math.ceil(N * ci[1])))
    return CountingResult(count, ae_result.estimate, N,
                          (ci_lower, ci_upper), ae_result.num_oracle_calls)
```

**Complexity: LOW** -- Reuses all existing IQAE infrastructure. Approximately 50-80 lines of new code.

**Confidence: HIGH** -- Well-established algorithm (Brassard-Hoyer-Mosca-Tapp 1998). Direct application of existing amplitude estimation.

## Competitor Feature Analysis

| Feature | Qiskit | Cirq | Classiq | Our Approach |
|---------|--------|------|---------|--------------|
| Modular arithmetic | Manual circuit construction; no high-level API. `PhaseAdder` and modular adder available as library circuits but require manual wiring | Not built-in; users build from primitives | Declarative model generates mod-arith automatically from high-level spec | Operator overloading: `qint_mod(5, N=17) + qint_mod(3, N=17)` auto-generates Toffoli mod-add circuit |
| Parametric circuits | `Parameter` objects for rotation angles; `assign_parameters()` for binding values. Works at gate level, not arithmetic level | `sympy.Symbol` parameters; `resolve_parameters()` | Built-in parametric model in synthesis engine | `@ql.compile(parametric=True)` -- parameters are classical integers to arithmetic operations, not just rotation angles. Unique approach |
| Depth/ancilla tradeoff | Manual circuit selection; `transpile()` can optimize for depth but not at adder-algorithm level | Manual circuit selection; no adder-level dispatch | Automatic via synthesis engine constraints (`max_width`, `max_depth`) | `ql.option('adder', 'auto')` with width-based heuristic. Simpler than Classiq but more accessible |
| Quantum counting | `IterativeAmplitudeEstimation` + manual M computation from estimate. No single `count_solutions` API | Not built-in | Built-in counting model in algorithm library | `ql.count_solutions(predicate, width=n)` -- returns integer M directly with confidence interval. Simplest API |

**Key differentiator:** Our framework operates at the arithmetic level (integers, operators, modular arithmetic) while competitors operate at the gate level (circuits, parameters, manual construction). Parametric compilation of integer arithmetic operations is unique to this framework.

## Sources

### Modular Arithmetic Circuits
- [Beauregard, "Circuit for Shor's algorithm using 2n+3 qubits" (2003)](https://www.semanticscholar.org/paper/Circuit-for-Shor's-algorithm-using-2n+3-qubits-Beauregard/9f61ff5e3f480e85d380b57a1048bf0426574323) -- HIGH confidence
- [Haner, Roetteler, Svore, "Factoring using 2n+2 qubits with Toffoli based modular multiplication" (2017)](https://arxiv.org/abs/1611.07995) -- HIGH confidence
- [Comprehensive Study of Quantum Arithmetic Circuits (2024)](https://arxiv.org/html/2406.03867v1) -- HIGH confidence

### Adder Algorithms
- [Cuccaro et al., "A new quantum ripple-carry addition circuit" (CDKM, 2004)](https://arxiv.org/pdf/quant-ph/0410184) -- HIGH confidence
- [Draper et al., "A logarithmic-depth quantum carry-lookahead adder" (2006)](https://www.semanticscholar.org/paper/A-logarithmic-depth-quantum-carry-lookahead-adder-Draper-Kutin/b96e881f8d525bf8b8e62804ae40f2debb53d5cc) -- HIGH confidence
- [Quantum adders: structural link between ripple-carry and carry-lookahead (2025)](https://arxiv.org/abs/2510.00840) -- MEDIUM confidence (preprint)

### Quantum Counting
- [Brassard, Hoyer, Mosca, Tapp, "Quantum Counting" (1998)](https://arxiv.org/abs/quant-ph/9805082) -- HIGH confidence
- [Grinko, Gacon, Zoufal, Woerner, "Iterative Quantum Amplitude Estimation" (2021)](https://www.nature.com/articles/s41534-021-00379-1) -- HIGH confidence
- [Classiq quantum counting implementation](https://docs.classiq.io/latest/explore/algorithms/amplitude_estimation/quantum_counting/quantum_counting/) -- MEDIUM confidence

### Parametric Compilation
- [van de Wetering et al., "Optimal compilation of parametrised quantum circuits" (2025)](https://arxiv.org/abs/2401.12877) -- MEDIUM confidence (different problem scope)
- [Qiskit Parameter documentation](https://docs.quantum.ibm.com/api/qiskit/qiskit.circuit.Parameter) -- HIGH confidence
- [Qiskit parameterized circuit compilation (2022)](https://arxiv.org/abs/2206.07885) -- MEDIUM confidence

---
*Feature research for: Quantum Assembly v5.0 Advanced Arithmetic & Compilation*
*Researched: 2026-02-24*
