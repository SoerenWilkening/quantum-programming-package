# Project Research Summary

**Project:** Quantum Assembly v5.0 — Advanced Arithmetic & Compilation
**Domain:** Quantum programming framework — modular Toffoli arithmetic, parametric compilation, automatic depth/ancilla tradeoff, quantum counting
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

The v5.0 milestone adds four significant capabilities to an existing, well-structured quantum programming framework: modular Toffoli arithmetic (for Shor's algorithm building blocks), parametric compilation (compile-once-replay-many for circuits with varying classical parameters), automatic depth/ancilla tradeoff (intelligent CLA vs RCA adder selection), and quantum counting (estimating solution cardinality via IQAE). All four features compose from existing verified infrastructure — no new external dependencies are required beyond declaring the already-used `scipy>=1.10` in `pyproject.toml`. The framework's three-layer architecture (Python frontend -> Cython bindings -> C backend) is the right foundation for all of these, and the implementation patterns are clearly defined by peer-reviewed literature.

The recommended build order is dependency-driven: quantum counting first (independent, simplest, immediate user value), then bug fixes (BUG-DIV-02 and BUG-MOD-REDUCE must be resolved before modular arithmetic), then the modular Toffoli arithmetic chain (modular add -> modular sub -> controlled modular add -> modular multiply), then the depth/ancilla tradeoff system (enhances all arithmetic and must know the full set of mode flags before parametric compilation), and finally parametric compilation (the most complex, benefits from stable arithmetic as its primary use case). This ordering surfaces bugs early and avoids building on a broken foundation.

The primary risks are three interacting failure modes: (1) the existing BUG-DIV-02 MSB comparison leak will reproduce identically in Beauregard modular addition if not fixed first — both share the same orphan-temporary pattern from Python-level comparison operators; (2) parametric compilation cannot be applied uniformly to Toffoli CQ operations because their gate topology depends on classical bit values, not just angles, requiring per-value fallback for Toffoli CQ; and (3) the quantum counting diffusion operator uses a sign convention correct for Grover search but wrong for QPE-based counting, requiring either a formula correction or a switch to IQAE-based counting. All three risks are well-understood with clear mitigations — they are sequencing risks, not fundamental algorithmic problems.

## Key Findings

### Recommended Stack

The v5.0 stack is identical to v4.x. All features compose from existing Python, Cython, and C primitives. The only required action is adding `scipy>=1.10` to `pyproject.toml` — `amplitude_estimation.py` already imports `scipy.stats.beta` for Clopper-Pearson confidence intervals, but it is absent from declared dependencies. This matters immediately for quantum counting, which reuses the IQAE infrastructure directly.

**Core technologies:**
- Python >=3.11: Frontend, algorithm logic — unchanged; all new features are pure Python wrappers or `compile.py` extensions
- Cython >=3.0.11,<4.0: C/Python bindings — new `cdef extern` declarations needed for modular arithmetic C functions; no new .pyx modules required
- C (gcc/clang, C11): Backend gate/circuit engine — one new file (`ToffoliModularArithmetic.c`) implementing the Beauregard modular adder sequence by composing existing Toffoli adder calls
- SciPy >=1.10: Clopper-Pearson CI in IQAE (used but undeclared) — declare in `pyproject.toml` immediately; v1.17.0 stable, supports Python 3.13

**What NOT to add:**
- SymPy: 20+ transitive deps; parametric values are discrete integers, not continuous symbolic expressions needing differentiation
- Qiskit Parameter/ParameterVector: Designed for variational rotation angles; incompatible with capture-replay model for integer arithmetic parameters
- QPE for quantum counting: Requires extra qubit register that would exceed the 17-qubit simulation limit; IQAE is already implemented and fits within constraints

### Expected Features

The feature landscape divides cleanly into two parallel tracks. An independent track (quantum counting, parametric compilation, depth/ancilla tradeoff) can begin immediately. A dependent track (the modular arithmetic hierarchy) requires bug fixes first.

**Must have (table stakes):**
- Modular addition mod N (Toffoli) — fault-tolerant Shor's needs `(a+b) mod N` with reversible gates; current `_reduce_mod` is broken (BUG-MOD-REDUCE)
- Modular subtraction mod N (Toffoli) — inverse of modular addition; needed for uncomputation in modular multiply
- Controlled modular addition — modular exponentiation decomposes into controlled modular adds; adds one control to every gate in the mod-add circuit
- Quantum counting (`ql.count_solutions`) — natural companion to `ql.grover()` and `ql.amplitude_estimate()`; table stakes for any search framework
- Configurable depth/ancilla tradeoff — users with Toffoli arithmetic expect to choose CDKM vs BK CLA; both adders already exist

**Should have (competitive):**
- Parametric compilation `@ql.compile(parametric=True)` — compile-once-replay-many for circuits with varying classical parameters; unique in any circuit-building DSL framework at this level
- Modular multiplication mod N (Toffoli) — end-to-end Shor's requires `(a*c) mod N`; enables a complete fault-tolerant arithmetic pipeline
- Automatic adder selection via `ql.option('tradeoff', 'auto'|'min_depth'|'min_qubits')` — policy abstraction hiding CLA/RCA implementation details from users

**Defer (v6+):**
- Modular exponentiation — circuit sizes exceed simulator capacity; requires working mod-mul; provide building blocks with documented composition pattern
- Full Shor's algorithm end-to-end API (`ql.factor(N)`) — untestable on 17-qubit simulator; QPE wrapper and classical post-processing (continued fractions) are out of scope
- QFT-based modular arithmetic — defeats the fault-tolerant purpose; BUG-QFT-DIV also makes the QFT path unreliable

### Architecture Approach

The existing three-layer architecture handles all four features cleanly without structural changes. Modular Toffoli arithmetic belongs at the C level — Python-level composition via `_reduce_mod` creates orphan qubits and circuit corruption (this is not an optimization, it is a correctness requirement). Quantum counting is a thin Python wrapper (`counting.py`) over `amplitude_estimate()` with M = N * sin^2(theta) conversion. The depth/ancilla tradeoff is a `tradeoff_policy_t` enum added to `circuit_t` and plumbed through `hot_path_add_toffoli.c`. Parametric compilation extends `compile.py`'s cache and replay with `DeferredCQOp` nodes for value-topology-dependent operations.

**Major components:**
1. `ToffoliModularArithmetic.c` (NEW) — Beauregard modular add/sub/mul implemented as atomic C functions; calls existing `toffoli_QQ_add`, `toffoli_CQ_add`, `toffoli_cCQ_add` in a 5-step sequence; includes `toffoli_modular_ops.h`
2. `compile.py` (MODIFIED) — adds `parametric=True` option; `DeferredCQOp` and `ParametricPlaceholder` node types for deferred classical substitution; cache key extended to include `arithmetic_mode` and `cla_override` (pre-existing bug fix)
3. `counting.py` (NEW) — `count_solutions()` function and `CountResult` class; wraps `amplitude_estimate()` with N-scaling, integer rounding, and corrected sign formula
4. `hot_path_add_toffoli.c` + `circuit.h` (MODIFIED) — `tradeoff_policy_t` enum (`TRADEOFF_AUTO`, `TRADEOFF_MIN_DEPTH`, `TRADEOFF_MIN_QUBITS`) added to `circuit_t`; policy-based CLA/RCA dispatch replaces hardcoded `CLA_THRESHOLD = 2`
5. `qint_mod.pyx` + `qint_mod.pxd` (MODIFIED) — `_reduce_mod` replaced by Cython `cdef extern` calls into new C-level modular operations

### Critical Pitfalls

1. **BUG-DIV-02 MSB comparison leak reproduces in modular arithmetic** — The same orphan-temporary pattern that causes BUG-DIV-02 appears in any Beauregard modular adder implemented at the Python level. Fix BUG-DIV-02 first. Implement the Beauregard sequence at the C level where ancilla is managed explicitly via `allocator_alloc`/`allocator_free`, never escaping to the Python-level uncomputation system. Warning signs: modular add works for single calls but produces wrong results when chained; `circuit_stats()['current_in_use']` grows with each call.

2. **Quantum counting sign ambiguity produces wrong M** — The existing diffusion operator uses W~ = -W (X-MCZ-X pattern), shifting QPE eigenvalues by pi/2. Standard formula `M = N * sin^2(pi * j / 2^t)` with this operator gives wrong counts (Chung & Nepomechie 2023 show errors near factor of 2). Use IQAE-based counting (recommended), which sidesteps QPE entirely and stays within the 17-qubit limit. If QPE is used, apply corrected formula `M = N * sin^2(pi * (j/2^t - 1/2))`.

3. **Parametric compilation cannot uniformly handle Toffoli CQ operations** — Toffoli CQ operations generate structurally different circuits per classical value because the Phase 73 optimizer eliminates gates at zero-bit positions. Circuit topology changes with the value, not just gate angles. Parametric compilation must detect Toffoli mode and fall back to per-value caching for CQ operations, or use the unoptimized (fixed-topology) CQ path. Document this limitation clearly.

4. **Compile cache key is missing arithmetic_mode and cla_override** — A pre-existing bug: the compile cache key does not include circuit-level mode flags added in v3.0 and v4.0. Replaying a Toffoli-compiled function in QFT mode returns the wrong gate sequence with wrong qubit layout assumptions. Fix this before adding any new mode flags for the tradeoff feature.

5. **BK CLA subtraction falls back to RCA, breaking modular operation symmetry** — Beauregard modular adder requires addition and subtraction with the same circuit structure (subtraction = inverse of addition). If automatic tradeoff selects CLA for the forward pass, the reverse pass uses RCA due to the known BK CLA subtraction limitation. Force RCA inside all modular arithmetic primitives until a dedicated CLA subtractor is implemented.

## Implications for Roadmap

Based on combined research, suggested phase structure (5 phases):

### Phase 1: Scipy Declaration + Quantum Counting

**Rationale:** Zero dependencies on other v5.0 features. Declaring the scipy dependency is a one-line `pyproject.toml` change that must happen before quantum counting can be properly installed. Quantum counting itself is a thin wrapper (~80 lines) over existing, verified IQAE infrastructure and delivers immediate user value. This phase can ship independently and proves the counting API before the more complex arithmetic phases.

**Delivers:** `scipy>=1.10` declared in `pyproject.toml`; `ql.count_solutions(oracle, width=n)` returning integer M with confidence interval; `CountResult` class with `.count`, `.estimate`, `.count_interval`, `.search_space`, `.num_oracle_calls`; corrected sign formula applied; tests against known-M oracles for M=1,2,3

**Addresses:** GADV-01 (quantum counting); undeclared scipy dependency

**Avoids:** Pitfall 5 (sign ambiguity) — use IQAE-based counting with corrected formula rather than QPE-based counting; Pitfall 8 (QPE qubit overhead) — IQAE stays within 17-qubit simulation limit without additional QPE ancilla register

### Phase 2: Bug Fixes (BUG-DIV-02 + BUG-MOD-REDUCE)

**Rationale:** Modular Toffoli arithmetic cannot be built correctly until the MSB comparison leak (BUG-DIV-02) and modular reduction corruption (BUG-MOD-REDUCE) are resolved. Both bugs share the same root cause: Python-level comparison operators creating orphan qubits that corrupt circuit state. Fixing them together in one phase avoids compounding the same architectural mistake in two separate places. This phase is purely remediation — it does not add user-facing features but is a hard prerequisite for Phase 3.

**Delivers:** Clean MSB comparison and uncomputation in division (BUG-DIV-02 fix); `_reduce_mod` replaced or disabled in favor of C-level implementation forthcoming in Phase 3 (BUG-MOD-REDUCE); BUG-QFT-DIV addressed to the extent it depends on BUG-DIV-02; regression tests verifying ancilla cleanliness after modular operations (`circuit_stats()['current_in_use']` stable)

**Addresses:** BUG-DIV-02, BUG-MOD-REDUCE, BUG-QFT-DIV (partial)

**Avoids:** Pitfall 1 (BUG-DIV-02 compounds modular arithmetic) — resolved before Phase 3 begins; Pitfall 2 (garbage qubits from iterative modular reduction) — iterative `_reduce_mod` loop removed

### Phase 3: Modular Toffoli Arithmetic

**Rationale:** Builds directly on the bug fixes from Phase 2. Implementation order within this phase is strict: modular add -> modular sub -> controlled modular add -> modular multiply. Each step depends on the previous. The Beauregard modular adder is implemented at the C level as an atomic function composing existing Toffoli adders — not as Python-level operator stacking. This is the core deliverable of v5.0.

**Delivers:** `ToffoliModularArithmetic.c` with Beauregard modular add/sub implemented atomically; `toffoli_modular_ops.h` API; controlled modular addition (adds single control qubit to Beauregard sequence); modular multiplication via schoolbook shift-and-add with mod-reduce interleaved; `qint_mod` operators (`+`, `-`, `*`) routed through C-level modular ops; exhaustive verification for widths 2-4 with statevector simulator, widths 5-8 with MPS simulator

**Addresses:** FTE-02 (modular Toffoli arithmetic); `qint_mod` operator correctness in fault-tolerant mode

**Avoids:** Pitfall 4 (CLA subtraction in modular ops) — force RCA for all internal additions/subtractions; Pitfall 9 (layer-based uncomputation for composite operations) — use `@ql.compile`-based uncomputation for modular operations, which operates on captured gate lists rather than layer indices; Pitfall 10 (CCCX ancilla explosion for controlled variants) — pre-allocate single AND-ancilla and verify reuse via `allocator_get_stats()`; Pitfall 14 (simulation qubit limit) — use MPS for widths >= 5

### Phase 4: Automatic Depth/Ancilla Tradeoff

**Rationale:** Enhances all Toffoli operations, including the new modular arithmetic from Phase 3. Most meaningful after modular arithmetic is stable because that is where CLA/RCA tradeoff has the greatest performance impact (O(n) modular additions per multiply). Must be done before Phase 5 because it adds a new mode flag (`tradeoff_policy`) that must be in the parametric compilation cache key. The tradeoff explicitly excludes CLA from inside modular primitives due to the CLA subtraction fallback limitation.

**Delivers:** `tradeoff_policy_t` enum in `circuit_t`; `ql.option('tradeoff', 'auto'|'min_depth'|'min_qubits')` Python API; policy-based dispatch in `hot_path_add_toffoli.c` replacing hardcoded `CLA_THRESHOLD = 2`; width-threshold auto-selection heuristic (CLA at width >= 4, RCA otherwise); documentation of CLA subtraction limitation and exclusion from modular primitives; `allocator_available()` query function added to `qubit_allocator.c`

**Addresses:** OPT-01 (automatic depth/ancilla tradeoff)

**Avoids:** Pitfall 4 (CLA inside modular ops) — tradeoff policy explicitly excluded within `ToffoliModularArithmetic.c` primitives; Pitfall 7 (no qubit budget mechanism) — width-threshold approach is sufficient for v5.0; document `qubit_budget` option as future enhancement; Pitfall 13 (threshold vs hardcoded sequences) — verify correct cache array (`precompiled_toffoli_QQ_add[]` vs `precompiled_toffoli_QQ_add_bk[]`) is accessed per policy decision

### Phase 5: Parametric Compilation

**Rationale:** The most complex v5.0 feature. Benefits from modular arithmetic being stable (it is the primary use case — Shor's modular exponentiation calls the modular multiplier with many different classical values, making the compile-once benefit most visible here). The cache key fix (adding `arithmetic_mode`, `cla_override`, and now `tradeoff_policy`) is done as part of this phase since parametric compilation touches the same cache infrastructure. Toffoli CQ operations fall back to per-value caching with clear documentation.

**Delivers:** `@ql.compile(parametric=True)` and `@ql.compile(parametric=['arg_name'])` API; `DeferredCQOp` and `ParametricPlaceholder` node types in `compile.py`; extended cache key including `arithmetic_mode`, `cla_override`, `tradeoff_policy`; parametric replay for QFT CQ operations (angle substitution); documented per-value fallback for Toffoli CQ operations; oracle decorator (`@ql.grover_oracle`) forced to per-value caching for all classical parameters regardless of parametric setting; regression tests for cache-miss on mode change

**Addresses:** PAR-01, PAR-02 (parametric compilation); pre-existing compile cache key correctness bug

**Avoids:** Pitfall 3 (cache key missing mode flags) — fixed as part of this phase before any other changes; Pitfall 6 (Toffoli CQ topology is value-dependent) — detected via arithmetic mode and handled with per-value fallback, documented explicitly; Pitfall 11 (oracle parametric caching corrupting search) — oracle decorator forces per-value caching for structural parameters

### Phase Ordering Rationale

- **Quantum counting first** because it is fully independent, delivers immediate user value, and keeps Phase 1 small and shippable. It also validates the IQAE-to-count conversion pipeline before the more complex arithmetic phases begin.
- **Bug fixes before modular arithmetic** because the MSB comparison leak reproduces identically in the Beauregard sequence if not resolved first. Building modular arithmetic on a broken comparison/uncomputation foundation creates hard-to-diagnose compound failures.
- **Modular arithmetic before tradeoff** because the tradeoff is most meaningful in the context of modular operations (where O(n) additions per multiply make CLA/RCA choice impactful), and because implementing modular arithmetic with forced RCA first then making the adder configurable is simpler than building both simultaneously.
- **Tradeoff before parametric compilation** because the tradeoff adds a new circuit mode flag (`tradeoff_policy`) that must be in the compile cache key. Doing this before Phase 5 lets the cache key fix absorb all new mode flags in one pass.
- **Parametric compilation last** because it touches the most shared infrastructure (compile.py cache, replay, gate list internals) and benefits from knowing the full set of mode flags and from modular arithmetic being stable (its primary use case).

### Research Flags

Phases likely needing `/gsd:research-phase` during planning:

- **Phase 3 (Modular Toffoli Arithmetic):** The Beauregard ancilla reset step (steps 5-7 of the modular add sequence) requires careful qubit layout specification — specifically how a single ancilla is shared across all five sub-operations and how the controlled variants extend this layout. The interaction between `allocator_alloc`/`allocator_free` and the controlled Toffoli adder calls needs verification before C implementation begins. HIGH risk.
- **Phase 5 (Parametric Compilation):** Novel feature with no direct precedent in other quantum frameworks. The `DeferredCQOp` replay mechanism — specifically how it interacts with qubit remapping during `_replay` and the boundary conditions for when to fall back to per-value caching — needs detailed design before any code is written. MEDIUM-HIGH risk.

Phases with standard patterns (skip additional research):

- **Phase 1 (Quantum Counting):** Well-established algorithm (BHMT 1998); direct wrapper over verified IQAE. Sign convention issue is documented and correctable with a one-line formula change.
- **Phase 2 (Bug Fixes):** Root causes are understood and confirmed via codebase inspection. The fix is architectural (move comparison to C level), not algorithmic. Both bugs share the same root cause, simplifying analysis.
- **Phase 4 (Depth/Ancilla Tradeoff):** Both adders already exist and are tested. The policy abstraction is standard engineering. Width-threshold heuristic is a minimal change to the existing dispatch logic.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies confirmed by codebase analysis; scipy undeclared dependency verified by direct source inspection of `amplitude_estimation.py:29` vs `pyproject.toml` |
| Features | HIGH | Well-established quantum algorithms from peer-reviewed literature; feature dependency graph is fully traceable in existing codebase |
| Architecture | HIGH | Codebase-verified integration points; Beauregard/Haner-Roetteler-Svore patterns confirmed in literature; component boundaries clear |
| Pitfalls | HIGH | Critical pitfalls identified from codebase inspection of known bugs (BUG-DIV-02, BUG-MOD-REDUCE) and literature (Chung & Nepomechie 2023 for sign convention); Toffoli CQ topology pitfall confirmed by Phase 73 code inspection |

**Overall confidence:** HIGH

### Gaps to Address

- **Parametric compilation Toffoli CQ boundary mechanism:** Research identifies that Toffoli CQ operations have value-dependent topology, but the exact mechanism for detecting which gates are value-dependent during capture (vs which are static structure) is not fully specified. This needs explicit design work during Phase 5 planning before any code is written.
- **Qubit budget for automatic tradeoff:** The auto-selection heuristic uses width thresholds rather than true qubit budget awareness. A `qubit_budget` option would make selection more accurate for nested operations (e.g., modular multiply with multiple concurrent additions). Track as future enhancement; width-threshold is sufficient for v5.0.
- **Modular multiply verification via MPS simulator:** At widths >= 5, modular multiplication exceeds the 17-qubit statevector simulation limit. Before Phase 3 begins, confirm the `matrix_product_state` simulator path is functional by running a smoke test of an existing large-qubit circuit via MPS.
- **BUG-QFT-DIV scope in Phase 2:** Research indicates BUG-QFT-DIV depends on BUG-DIV-02, but it may also have independent bugs beyond cascading effects. Phase 2 should scope BUG-QFT-DIV explicitly — either fix fully in Phase 2 or defer with documented remaining failure modes.
- **AND-ancilla reuse for controlled modular operations:** Controlled modular multiply turns every CCX into CCCX, which decomposes into CCX + AND-ancilla. The claim is that a single AND-ancilla can be reused across all CCCX decompositions (returned to |0> after each use). This needs verification against the existing `allocator_alloc()` count=1 reuse path before Phase 3 implementation.

## Sources

### Primary (HIGH confidence)
- Haner, Roetteler, Svore (2017) "Factoring using 2n+2 qubits with Toffoli based modular multiplication" [arXiv:1611.07995](https://arxiv.org/abs/1611.07995) — Toffoli-only modular multiplication hierarchy, O(n^3 log n) gates, 2n+2 qubits
- Beauregard (2003) "Circuit for Shor's algorithm using 2n+3 qubits" [arXiv:quant-ph/0205095](https://arxiv.org/abs/quant-ph/0205095) — Beauregard modular adder: add, subtract N, check MSB, conditionally add N back, reset ancilla
- Brassard, Hoyer, Mosca, Tapp (1998) "Quantum Counting" [arXiv:quant-ph/9805082](https://arxiv.org/abs/quant-ph/9805082) — M = N * sin^2(theta) conversion; counting via amplitude estimation
- Grinko, Gacon, Zoufal, Woerner (2021) "Iterative Quantum Amplitude Estimation" [Nature npj QI](https://www.nature.com/articles/s41534-021-00379-1) — IQAE already implemented in `amplitude_estimation.py`
- Cuccaro, Draper, Kutin, Moulton (2004) "A new quantum ripple-carry addition circuit" (CDKM) [arXiv:quant-ph/0410184](https://arxiv.org/abs/quant-ph/0410184) — CDKM adder: O(n) depth, 1 ancilla
- Draper, Kutin, Rains, Svore (2006) "A logarithmic-depth quantum carry-lookahead adder" [arXiv:quant-ph/0406142](https://arxiv.org/abs/quant-ph/0406142) — BK CLA adder: O(log n) depth, O(n) ancilla; subtraction fallback documented

### Secondary (MEDIUM confidence)
- Chung & Nepomechie (2023) "Quantum counting, and a relevant sign" [arXiv:2310.07428](https://arxiv.org/abs/2310.07428) — diffusion operator sign convention in quantum counting; quantified error near factor of 2
- Classiq quantum counting documentation [classiq.io](https://docs.classiq.io/latest/explore/algorithms/amplitude_estimation/quantum_counting/quantum_counting/) — IQAE-based counting reference implementation
- Comprehensive Study of Quantum Arithmetic Circuits (2024) [arXiv:2406.03867](https://arxiv.org/html/2406.03867v1) — depth-count tradeoffs, RCA vs CLA comparison across circuit families
- Optimal compilation of parametrised quantum circuits (2024) [arXiv:2401.12877](https://arxiv.org/abs/2401.12877) — parametric compilation scope, constraints, and limitations for quantum circuits
- SciPy v1.17.0 documentation [scipy.org](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.beta.html) — `beta.ppf` Clopper-Pearson CI with Boost Math backend; Python 3.13 compatible

### Codebase Analysis (HIGH confidence)
- `src/quantum_language/amplitude_estimation.py:29` — `from scipy.stats import beta` import confirming undeclared dependency
- `src/quantum_language/qint_mod.pyx:107-131` — broken `_reduce_mod` iterative loop (BUG-MOD-REDUCE root cause)
- `src/quantum_language/compile.py:594-625` — cache key structure, `_classify_args`, missing mode flags
- `c_backend/src/hot_path_add_toffoli.c` — CLA/RCA dispatch, hardcoded `CLA_THRESHOLD = 2`, existing two-cache dispatch arrays
- `c_backend/src/ToffoliAdditionCDKM.c`, `ToffoliAdditionCLA.c`, `ToffoliMultiplication.c` — existing Toffoli primitives used by new modular arithmetic
- `c_backend/include/circuit.h` — `circuit_t` struct, `cla_override`, `qubit_saving`, `arithmetic_mode` fields
- `c_backend/include/toffoli_arithmetic_ops.h` — full Toffoli add/mul function signatures
- Previous pitfall research: `.planning/research/PITFALLS-TOFFOLI-ARITHMETIC.md`, `.planning/research/PITFALLS-COMPILE-DECORATOR.md`, `.planning/research/PITFALLS_GROVER.md`
- Known bugs: BUG-DIV-02 (MSB comparison leak in division), BUG-QFT-DIV (QFT division failures), BUG-MOD-REDUCE (`_reduce_mod` corruption)

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
