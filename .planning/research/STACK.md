# Stack Research: v5.0 Advanced Arithmetic & Compilation

**Domain:** Quantum programming framework -- modular Toffoli arithmetic, parametric compilation, automatic depth/ancilla tradeoff, quantum counting
**Researched:** 2026-02-24
**Confidence:** HIGH (all four features build on existing verified infrastructure with well-understood algorithms)

## Executive Summary

The v5.0 milestone requires **zero new external dependencies**. All four features -- modular Toffoli arithmetic, parametric compilation, automatic depth/ancilla tradeoff, and quantum counting -- are algorithmic compositions of existing C backend primitives and Python infrastructure. The only stack action needed is declaring the already-used scipy dependency in `pyproject.toml`.

## Recommended Stack

### Core Technologies (Unchanged)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | >=3.11 | Frontend, algorithm logic | **Existing** -- no change |
| Cython | >=3.0.11,<4.0 | C/Python bindings | **Existing** -- no change |
| C (gcc/clang, C11) | System | Backend gate/circuit engine | **Existing** -- no change |
| NumPy | >=1.24 | Array ops, angle math | **Existing** -- no change |
| Pillow | >=9.0 | Circuit visualization | **Existing** -- no change |
| Qiskit | >=1.0 | Verification (optional) | **Existing** -- no change |
| qiskit-aer | >=0.13 | Simulation backend (optional) | **Existing** -- no change |

### Critical Fix: Undeclared scipy Dependency

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| SciPy | >=1.10 | `beta.ppf` for Clopper-Pearson CI in IQAE | **Used but undeclared** -- add to pyproject.toml |

`amplitude_estimation.py` line 29 imports `from scipy.stats import beta` but scipy is absent from `pyproject.toml` `[project].dependencies`. Quantum counting (`ql.count_solutions`) will reuse the IQAE infrastructure, making this dependency critical. SciPy >=1.10 because it introduced improved `beta.ppf` numerical stability via the Boost Math C++ backend. Current stable is v1.17.0.

### Supporting Libraries (Unchanged)

| Library | Version | Purpose | When Used |
|---------|---------|---------|-----------|
| pytest | >=7.0 | Test runner | Dev dependency, existing |
| pytest-cov | >=6.0 | Coverage | Dev dependency, existing |
| ruff | >=0.1.0 | Linting | Dev dependency, existing |

### Development Tools (Unchanged)

| Tool | Purpose | Notes |
|------|---------|-------|
| Cython >=3.0.11 | Extension compilation | `CYTHON_USE_SYS_MONITORING=0` still needed on Python 3.13 for coverage |
| gcc/clang | C backend compilation | `-Os` release, `-O3` debug |
| pre-commit | Code quality hooks | Existing |

## Feature-Specific Stack Analysis

### 1. Modular Toffoli Arithmetic (FTE-02)

**Existing building blocks (verified, tested):**

| C Function | Location | Purpose |
|------------|----------|---------|
| `toffoli_QQ_add(bits)` | `ToffoliAdditionCDKM.c` | a += b via CDKM RCA |
| `toffoli_CQ_add(bits, value)` | `ToffoliAdditionCDKM.c` | a += classical_value |
| `toffoli_cQQ_add(bits)` | `ToffoliAdditionCDKM.c` | Controlled a += b |
| `toffoli_cCQ_add(bits, value)` | `ToffoliAdditionCDKM.c` | Controlled a += classical_value |
| `toffoli_mul_cq(...)` | `ToffoliMultiplication.c` | ret = a * classical_value |
| `toffoli_cmul_cq(...)` | `ToffoliMultiplication.c` | Controlled ret = a * classical_value |
| `IntegerComparison` | `IntegerComparison.c` | a >= b, a < b, etc. |

**Existing Python layer:**

| Component | Location | Purpose |
|-----------|----------|---------|
| `qint_mod` class | `qint_mod.pyx` | Modular arithmetic with classical modulus N |
| `_reduce_mod()` | `qint_mod.pyx:107` | Comparison + conditional subtraction loop |
| `_wrap_result()` | `qint_mod.pyx:133` | Wrap plain qint as qint_mod |

**What needs to be built (no new deps):**

The modular arithmetic hierarchy for Shor's algorithm is:

```
Layer 1: modular_add(a, b, N)          = add(a,b); if result >= N: subtract N
Layer 2: controlled_modular_add(a,b,N,ctrl) = controlled version of Layer 1
Layer 3: modular_mul(a, c, N)          = loop of controlled_modular_add (shift-and-add)
Layer 4: controlled_modular_mul(a,c,N,ctrl) = controlled version of Layer 3
Layer 5: modular_exp(a, x, N)          = repeated controlled_modular_mul (square-and-multiply)
```

Each layer composes exclusively from existing C functions. Following Haner-Roetteler-Svore (2017): purely Toffoli-based, O(n^3 log n) total gates, 2n+2 qubits. The existing `_reduce_mod` pattern is correct in structure (compare + conditional subtract); the BUG-MOD-REDUCE is an implementation issue, not an architectural one.

**Implementation location:** New C file `ToffoliModular.c` for optimized modular add/sub, or pure Python composition at `qint_mod.pyx` level using existing hot paths.

**Stack impact:** Zero new dependencies.

### 2. Parametric Compilation (PAR-01, PAR-02)

**Existing infrastructure:**

| Component | Location | How It Works |
|-----------|----------|-------------|
| `CompiledFunc.__call__` | `compile.py:594` | Classify args -> cache lookup -> capture or replay |
| `_classify_args` | `compile.py` | Splits args into quantum (qint/qarray) and classical (int) |
| Cache key structure | `compile.py:608` | `(tuple(classical_args), tuple(widths), control_count, qubit_saving)` |
| Gate list storage | `compile.py` | List of dicts with `type`, `target`, `angle`, `controls`, etc. |

**The problem parametric compilation solves:**

Currently, `f(x, 5)` and `f(x, 7)` produce two separate cache entries because the classical value `5` vs `7` is part of the cache key. For modular arithmetic where the modulus N is a classical parameter but the circuit structure is identical (only CQ gate X-patterns differ), this means N separate compilations.

**Implementation approach (pure Python, no new deps):**

1. Add `parametric` kwarg to `@ql.compile`: `@ql.compile(parametric=['modulus'])`
2. During capture, detect CQ operations and store classical value as a symbolic reference: `{'type': _X, 'target': 3, 'param_ref': 'modulus', 'bit_index': 2}`
3. Cache key excludes parametric args: `(tuple(non_parametric_classical), tuple(widths), control_count, qubit_saving)`
4. During replay, substitute concrete values: iterate gate list, resolve `param_ref` to concrete int, emit/skip X gates per bit

**What NOT to use:**

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SymPy | 20+ transitive deps, designed for continuous symbolic algebra; our params are discrete integers | Simple dict lookup / lambda closures for X-gate bit selection |
| Qiskit Parameter/ParameterVector | For variational circuits with continuous rotation angles; our CQ operations use integer bit patterns | Custom param_ref in gate dict |
| Abstract Syntax Tree (AST) analysis | Fragile, version-dependent Python internals | Gate-level capture already works |

**Stack impact:** Zero new dependencies. Refactoring of `compile.py` only.

### 3. Automatic Depth/Ancilla Tradeoff (OPT-01)

**Existing infrastructure:**

| Component | Location | Current Behavior |
|-----------|----------|-----------------|
| `CLA_THRESHOLD` | `hot_path_add_toffoli.c:24` | Hardcoded `= 2` (use CLA for width >= 2) |
| `circuit_s.cla_override` | `_core.pxd:145` | 0 = auto CLA, 1 = force RCA |
| `ql.option('cla', bool)` | `_core.pyx:229` | Python API for CLA toggle |
| `toffoli_dispatch_qq` | `hot_path_add_toffoli.c` | Try CLA first, fallback to RCA |
| `toffoli_dispatch_cq` | `hot_path_add_toffoli.c` | Try CLA first, fallback to RCA |
| `bk_cla_ancilla_count(bits)` | `ToffoliAdditionCLA.c` | Ancilla cost for BK CLA |

**Known tradeoff metrics:**

| Adder | Depth | Ancilla | Toffoli Count | Best For |
|-------|-------|---------|---------------|----------|
| CDKM RCA | O(n) (2n-1 layers) | 1 | 2n-1 Toffoli | Ancilla-constrained circuits |
| BK CLA | O(log n) | 2*(n-1) + tree_merges | ~4n Toffoli | Depth-constrained circuits |

**What needs to change (C-level, no new deps):**

1. Add `adder_strategy` field to `circuit_s` struct: enum `{ADDER_AUTO, ADDER_PREFER_DEPTH, ADDER_PREFER_ANCILLA}`
2. Replace static `CLA_THRESHOLD` with dynamic decision in `toffoli_dispatch_qq`/`toffoli_dispatch_cq`:
   - `ADDER_PREFER_DEPTH`: always try CLA first (current behavior)
   - `ADDER_PREFER_ANCILLA`: always use RCA (current `cla_override=1` behavior)
   - `ADDER_AUTO`: use CLA when width >= 4 AND depth reduction > 2x AND ancilla budget available
3. Add `ql.option('adder_strategy', 'auto'|'depth'|'ancilla')` Python API

**Stack impact:** C struct change + option handler. Zero new dependencies.

### 4. Quantum Counting (GADV-01)

**Existing infrastructure:**

| Component | Location | Purpose |
|-----------|----------|---------|
| `amplitude_estimate()` | `amplitude_estimation.py:482` | Full IQAE implementation |
| `_iqae_loop` | `amplitude_estimation.py:390` | Core IQAE algorithm |
| `_build_and_simulate` | `amplitude_estimation.py:337` | Build circuit + simulate multi-shot |
| `_count_good_states` | `amplitude_estimation.py:188` | Count satisfying outcomes |
| `_clopper_pearson_confint` | `amplitude_estimation.py:219` | Confidence intervals (uses scipy.stats.beta) |
| `AmplitudeEstimationResult` | `amplitude_estimation.py:52` | Result wrapper with float-like behavior |
| Oracle synthesis | `oracle.py`, `grover.py` | Lambda -> GroverOracle conversion |

**What needs to be built:**

`ql.count_solutions` is a thin wrapper:

```python
def count_solutions(oracle, *, width=None, widths=None, epsilon=1.0,
                    confidence_level=0.95, **kwargs):
    """Estimate M = number of solutions satisfying oracle.

    Uses IQAE: M = N * a, where a = sin^2(theta) is the amplitude estimate
    and N = 2^(sum of register widths) is the search space size.
    """
    # Compute search space size
    N = 2 ** sum(register_widths)

    # Scale epsilon for counting precision: epsilon_a = epsilon / N
    epsilon_a = epsilon / N

    result = amplitude_estimate(oracle, width=width, widths=widths,
                                 epsilon=epsilon_a,
                                 confidence_level=confidence_level, **kwargs)
    M = N * float(result)
    ci = (N * result.confidence_interval[0], N * result.confidence_interval[1])
    return QuantumCountingResult(M, N, result.num_oracle_calls, ci)
```

The math: Brassard-Hoyer-Mosca-Tapp (1998) showed quantum counting = amplitude estimation where `M = N * sin^2(theta)`. Since IQAE already estimates `a = sin^2(theta)`, the conversion is `M = N * a`.

**Stack impact:** New `counting.py` (~100-150 lines). Reuses all IQAE + oracle infrastructure. Zero new dependencies.

## Installation

```bash
# Fix: Add scipy to declared dependencies in pyproject.toml
# Change:
#   dependencies = ["numpy>=1.24", "Pillow>=9.0"]
# To:
#   dependencies = ["numpy>=1.24", "Pillow>=9.0", "scipy>=1.10"]

# Build (unchanged):
pip install -e ".[dev,verification]"
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Haner-Roetteler-Svore modular approach (Toffoli-only) | Beauregard QFT-based modular addition | If QFT mode were the default. But `fault_tolerant` is default and Toffoli-only is required for error correction readiness |
| Python closure parametric substitution | SymPy symbolic compilation | If parametric params were continuous rotation angles needing differentiation (variational algorithms). Our params are discrete integers |
| IQAE-based quantum counting | QPE-based quantum counting | If exact eigenvalue estimation were needed (requires QFT circuit, counting register qubits, not implemented). IQAE is already implemented, fewer qubits, no QFT |
| Dynamic CLA/RCA dispatch with cost model | Static `CLA_THRESHOLD = 2` | Never -- static threshold ignores circuit context (ancilla pressure, depth budget) |
| Conditional subtraction mod reduce | Barrett/Montgomery reduction | If moduli exceeded 64 bits or if reduce_mod were called in tight inner loops. Conditional subtraction is simpler, correct for width 1-64, and composes from existing primitives |
| Composition from existing C functions | New dedicated modular arithmetic C module | Start with composition; only create dedicated C functions if profiling shows performance bottleneck in inner loop of modular multiplication |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SymPy | Massive dependency tree (~20 transitive packages), designed for continuous symbolic math. Our parametric values are integers controlling X-gate bit patterns | Python closures / dict substitution in captured gate lists |
| Qiskit Parameter/ParameterVector | Designed for variational algorithms (QAOA, VQE) with continuous rotation parameters. Incompatible with our capture-replay model | Custom `param_ref` field in gate dict for integer CQ parameters |
| QPE for quantum counting | Requires QFT circuit construction (not implemented), counting register qubits (extra overhead), more complex than IQAE | `ql.amplitude_estimate()` with `M = N * a` conversion |
| Gidney 2025 CQ adder (constant workspace) | Uses "venting" (X-basis measurement + classical feedforward) which the framework does not support. Would require mid-circuit measurement infrastructure | Standard temp-register CQ approach (`toffoli_CQ_add`) already implemented and verified |
| External modular arithmetic libraries | Unnecessary dependency for something trivially composable from existing Toffoli add/sub/mul/compare | Layer-by-layer composition from existing C primitives |
| New Cython modules | v5.0 features are either C-level (modular arith, tradeoff) or pure Python (parametric, counting) | C functions for performance-critical paths, pure Python for algorithm orchestration |

## Stack Patterns by Feature

**For modular Toffoli arithmetic:**
- Implement modular add/sub as C functions in new `ToffoliModular.c` (or extend `ToffoliAdditionHelpers.c`)
- Pattern: `plain_add(a, b)` -> `compare(result, N)` -> `controlled_subtract(result, N, cmp_flag)` -> `uncompute(cmp_flag)`
- Expose via Cython `cdef extern` in `_core.pxd`
- Rewrite `qint_mod._reduce_mod` to call new C-level modular operations directly
- Fix BUG-MOD-REDUCE by using Beauregard-style ancilla for overflow detection instead of comparison-based approach

**For parametric compilation:**
- Modify `CompiledFunc._classify_args` to detect parametric-marked args
- Change cache key: parametric args excluded (wildcard) -> single cache entry for all classical values
- Store gate list with `param_ref` metadata on CQ gates instead of resolved bit patterns
- On replay: evaluate param_ref -> concrete int -> emit/skip X gates per bit position
- Backwards compatible: default behavior unchanged unless `parametric=` specified

**For automatic depth/ancilla tradeoff:**
- Add `adder_strategy` enum to `circuit_s` struct in `qubit_allocator.h`
- Modify `toffoli_dispatch_qq`/`toffoli_dispatch_cq` decision tree in `hot_path_add_toffoli.c`
- Expose via `ql.option('adder_strategy', 'auto')` in `_core.pyx`
- Auto mode: prefer CLA at width >= 4, fall back to RCA if ancilla count exceeds threshold

**For quantum counting:**
- New `counting.py` in `src/quantum_language/`
- `QuantumCountingResult` class wrapping count estimate + IQAE metadata
- `count_solutions()` function: resolve widths, compute N, call `amplitude_estimate`, convert `a -> M = N * a`
- Register in `__init__.py` as `ql.count_solutions`

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| scipy>=1.10 | Python >=3.9, NumPy >=1.22 | Already implicitly required; v1.17.0 (stable) supports Python 3.13 |
| Cython >=3.0.11,<4.0 | Python 3.11-3.13 | No new .pyx modules needed for v5.0 |
| qiskit>=1.0 | Python >=3.8 | Verification only, no change |
| qiskit-aer>=0.13 | qiskit>=1.0 | Verification only, no change |

**Python 3.13 compatibility confirmed:** SciPy 1.17.0 supports Python 3.13. The `CYTHON_USE_SYS_MONITORING=0` workaround in `setup.py` remains necessary for Cython 3.2.x coverage builds on Python 3.13+.

## Confidence Assessment

| Area | Confidence | Source | Notes |
|------|------------|--------|-------|
| No new deps needed | HIGH | Codebase analysis | All four features compose from existing primitives |
| scipy undeclared | HIGH | `grep` of source + pyproject.toml | `amplitude_estimation.py:29` imports scipy, not in dependencies |
| Modular arith hierarchy | HIGH | Haner-Roetteler-Svore (2017), Beauregard (2003) | Well-established building block composition |
| Parametric compilation approach | MEDIUM | Architectural analysis | Novel for this codebase; needs careful cache key design |
| CLA/RCA tradeoff metrics | HIGH | Draper-Kutin-Rains-Svore (2006), CDKM (2004) | Standard complexity results |
| IQAE-based counting | HIGH | BHMT (1998), Classiq implementation reference | M = N * a is standard conversion |

## Sources

### Primary (HIGH confidence)
- [Haner, Roetteler, Svore (2017) - Factoring using 2n+2 qubits with Toffoli based modular multiplication](https://arxiv.org/abs/1611.07995) -- Toffoli-only modular mult hierarchy, O(n^3 log n) gates, 2n+2 qubits
- [Beauregard (2003) - Circuit for Shor's algorithm using 2n+3 qubits](https://arxiv.org/abs/quant-ph/0205095) -- QFT-based modular addition hierarchy (reference, not used for Toffoli path)
- [Brassard, Hoyer, Mosca, Tapp (1998) - Quantum Counting](https://arxiv.org/abs/quant-ph/9805082) -- quantum counting = amplitude estimation + M = N * a
- [Grinko, Gacon, Zoufal, Woerner (2021) - Iterative Quantum Amplitude Estimation](https://www.nature.com/articles/s41534-021-00379-1) -- IQAE already implemented in framework
- [SciPy v1.17.0 docs - scipy.stats.beta](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.beta.html) -- beta.ppf for Clopper-Pearson CI, Boost Math backend

### Secondary (MEDIUM confidence)
- [Classiq - Quantum Counting Using IQAE](https://docs.classiq.io/latest/explore/algorithms/amplitude_estimation/quantum_counting/quantum_counting/) -- Reference implementation of IQAE-based counting
- [Gidney (2025) - Classical-Quantum Adder with Constant Workspace](https://arxiv.org/abs/2507.23079) -- State-of-art CQ adder (not used: requires venting/mid-circuit measurement)
- [Draper, Kutin, Rains, Svore (2006) - Logarithmic-depth quantum carry-lookahead adder](https://www.researchgate.net/publication/2193063_A_logarithmic-depth_quantum_carry-lookahead_adder) -- CLA depth/ancilla tradeoffs

### Codebase Analysis (HIGH confidence)
- `c_backend/include/toffoli_arithmetic_ops.h` -- Full Toffoli add/mul function signatures
- `c_backend/src/hot_path_add_toffoli.c` -- CLA/RCA dispatch, CLA_THRESHOLD=2
- `src/quantum_language/compile.py:594-625` -- Cache key structure, classify_args
- `src/quantum_language/amplitude_estimation.py` -- Full IQAE implementation with scipy dependency
- `src/quantum_language/qint_mod.pyx` -- Existing modular arithmetic with _reduce_mod

---
*Stack research for: Quantum Assembly v5.0 -- modular Toffoli arithmetic, parametric compilation, automatic depth/ancilla tradeoff, quantum counting*
*Researched: 2026-02-24*
*Conclusion: One fix (declare scipy>=1.10 in pyproject.toml). Zero new external dependencies. All features compose from existing infrastructure.*
