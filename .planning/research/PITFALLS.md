# Pitfalls Research: v5.0 Advanced Arithmetic & Compilation

**Domain:** Adding modular Toffoli arithmetic, parametric compilation, automatic depth/ancilla tradeoff, and quantum counting to an existing quantum programming framework
**Researched:** 2026-02-24
**Confidence:** HIGH for codebase-specific pitfalls (source inspected + existing bug context), MEDIUM for algorithmic pitfalls (literature-verified)

## Executive Summary

The v5.0 milestone combines four distinct feature tracks -- modular Toffoli arithmetic, parametric compilation, automatic depth/ancilla tradeoff, and quantum counting -- on top of an existing framework with three known deferred bugs (BUG-DIV-02, BUG-QFT-DIV, BUG-MOD-REDUCE) and two known architectural limitations (layer-based uncomputation unreliable under optimizer parallelization, BK CLA subtraction falling back to RCA). The primary danger is that these features interact through shared subsystems (the circuit optimizer, the uncomputation mechanism, the `@ql.compile` cache, and the qubit allocator) in ways that compound existing bugs rather than merely adding new ones. The pitfalls below are ordered by severity: the first six are critical (cause silent wrong results or require rewrites), the next five are moderate (cause specific failure modes or performance issues), and the remainder are minor but require awareness.

---

## Critical Pitfalls

### Pitfall 1: Beauregard Modular Addition Requires Comparison-on-Dirty-Ancilla -- Interacts with BUG-DIV-02

**What goes wrong:**
Beauregard's modular addition circuit (the standard for Shor's algorithm) works by: (1) add a+b, (2) subtract N, (3) check MSB to see if result went negative, (4) conditionally add N back, (5) reset the MSB flag qubit. Step 5 requires subtracting `a` from the register, checking the MSB, flipping the flag, and adding `a` back. This "reset the auxiliary" step is structurally identical to the pattern that causes BUG-DIV-02 (MSB comparison leak in division -- orphan temporaries not uncomputed). The existing `_reduce_mod` in `qint_mod.pyx` (line 107-131) uses `cmp = value >= self._modulus` followed by `with cmp: value -= self._modulus`, which creates a comparison qbool that becomes an orphan temporary after the `with` block exits.

**Why it happens:**
The existing modular reduction uses the high-level comparison operators which allocate comparison result qubits. These qubits are tracked by the layer-based uncomputation system, but when the optimizer parallelizes gates, the layer ranges become unreliable (known limitation from PROJECT.md). Beauregard's algorithm makes this worse because the auxiliary reset step requires a comparison, a conditional operation, AND correct uncomputation of the comparison result -- all three of which must succeed for the ancilla to be clean for the next iteration.

**How to avoid:**
1. Fix BUG-DIV-02 FIRST, before implementing Beauregard modular arithmetic. The same orphan-temporary pattern will appear in modular addition.
2. Implement Beauregard's modular addition at the C level as a single atomic operation, not composed from Python-level `>=` and `with` blocks. This avoids the layer-tracking problems entirely because the C-level sequence handles all ancilla internally.
3. The Beauregard circuit needs exactly one ancilla qubit (the MSB flag). Allocate it explicitly at the start and manage it through the entire sequence, never letting it escape to the Python-level uncomputation system.
4. Test the complete modular add-subtract-compare-reset cycle exhaustively for widths 2-8 with all input pairs before composing into modular multiplication.

**Warning signs:**
- Modular addition works for single calls but produces wrong results when chained (e.g., `x += a mod N; x += b mod N` gives wrong result for the second addition)
- The MSB flag qubit is not in |0> after the operation (measure it in debug mode)
- `circuit_stats()['current_in_use']` grows with each modular operation call

**Phase to address:**
Bug fix phase (BUG-DIV-02) must precede modular Toffoli arithmetic implementation. Attempting to build modular arithmetic on the broken comparison/uncomputation foundation will compound bugs.

---

### Pitfall 2: Modular Reduction Iterative Subtraction Creates O(N) Garbage Qubits

**What goes wrong:**
The current `_reduce_mod` implementation (line 107-131 of `qint_mod.pyx`) uses a Python-level loop: `for _ in range(iterations): cmp = value >= self._modulus; with cmp: value -= self._modulus`. Each iteration creates a comparison qbool (`cmp`). In the current system, these comparison results persist without auto-uncompute (see Key Decision: "Comparison results persist without auto-uncompute"). This means each modular reduction creates `iterations` orphan qubits. For an n-bit modulus, `iterations = O(log(2^n / N))`, but for modular multiplication the reduction is called after each partial product addition, creating `O(n * log(2^n / N))` total orphan qubits across a single modular multiply.

**Why it happens:**
BUG-MOD-REDUCE was deferred specifically because the existing `_reduce_mod` has result corruption issues. The root cause is that the iterative conditional-subtraction pattern does not properly track which comparison qubits need uncomputation and in what order. Beauregard's algorithm solves this differently -- it uses a single ancilla qubit reset within the modular adder itself, rather than relying on external iterative reduction.

**How to avoid:**
1. Replace the iterative `_reduce_mod` with Beauregard-style in-circuit modular reduction. This is NOT an optimization -- it is a correctness requirement. The iterative approach fundamentally cannot work correctly in a quantum circuit because each comparison creates entanglement that must be undone.
2. Implement modular addition as a single C-level primitive: `toffoli_mod_add(bits, modulus, a_qubits, b_qubits, ancilla)`. The primitive internally handles: add, subtract N, check MSB, conditional add-back, reset ancilla.
3. Do NOT compose modular operations from Python-level arithmetic operators. The Python-level composition creates intermediate qint/qbool objects whose lifetime management conflicts with the quantum requirement that all ancilla be returned to |0>.

**Warning signs:**
- Qubit count for modular multiplication is orders of magnitude higher than expected
- Modular multiplication works for 2-bit but fails for 3+ bit moduli
- Qiskit verification shows non-zero probability on ancilla qubits after modular operations

**Phase to address:**
BUG-MOD-REDUCE fix phase. This must be redesigned as a C-level primitive, not patched at the Python level.

---

### Pitfall 3: Parametric Compilation Cache Key Must Include Arithmetic Mode AND CLA Override

**What goes wrong:**
The `@ql.compile` decorator (compile.py) caches gate sequences keyed by `(classical_args, widths, control_count, qubit_saving)`. The v3.0 Toffoli arithmetic added `arithmetic_mode` (QFT vs Toffoli) and `cla_override` (auto CLA vs force RCA) as circuit-level options. The cache key does NOT include either of these. If a user compiles a function in Toffoli mode, switches to QFT mode, and replays the cached function, the Toffoli gate sequence is replayed into a QFT-mode context. The gates themselves will be emitted correctly (they are just X/CX/CCX/P gates), but the qubit layout assumptions are wrong: Toffoli sequences expect ancilla qubits that the QFT layout does not provide.

More subtly: when the automatic depth/ancilla tradeoff feature is added (OPT-01), the adder selection (RCA vs CLA) may change per-call based on width and available qubit budget. If the compile cache stores a sequence that used RCA (width=4, below CLA threshold), and the function is later called with width=8 (above CLA threshold), the cache hit returns the wrong sequence.

**Why it happens:**
The compile.py cache was designed in v2.0 before the Toffoli backend existed. The v3.0 and v4.0 milestones did not update the cache key despite adding new circuit-level mode flags. The existing pitfall from PITFALLS-COMPILE-DECORATOR.md (Pitfall 8: QFT vs Toffoli mode) flagged this, but it was not fixed in v4.0 or v4.1.

**How to avoid:**
1. Extend the compile cache key immediately: `cache_key = (classical_args, widths, control_count, qubit_saving, arithmetic_mode, cla_override)`. This is a one-line change in `CompiledFunc.__call__` in compile.py.
2. When adding automatic depth/ancilla tradeoff, the adder selection decision must be captured in the cache key or forced to be deterministic for a given cache key. If the tradeoff is dynamic (based on runtime qubit budget), then compiled functions CANNOT use automatic tradeoff -- they must use the mode that was active during capture.
3. Add a regression test: compile a function in Toffoli mode, switch to QFT mode, call again, verify it recompiles (cache miss) and produces correct results.

**Warning signs:**
- Compiled function gate count changes when arithmetic mode changes (should trigger recompilation)
- Circuit contains Toffoli gates when QFT mode is active, or vice versa
- Segfault when replaying compiled function after mode change (qubit layout mismatch)

**Phase to address:**
Parametric compilation phase (PAR-01/PAR-02). Fix cache key BEFORE adding new mode flags.

---

### Pitfall 4: BK CLA Subtraction Fallback Breaks Modular Arithmetic Bidirectionality

**What goes wrong:**
Beauregard's modular addition requires both addition AND subtraction with the same circuit structure (subtraction = inverse of addition). The BK CLA adder currently falls back to RCA for subtraction because the carry-copy ancilla cannot be uncomputed in reverse (known limitation from PROJECT.md). This means: if automatic depth/ancilla tradeoff selects CLA for a modular addition, the addition uses CLA (O(log n) depth) but the internal subtraction falls back to RCA (O(n) depth). The modular addition circuit is now asymmetric -- the forward and reverse paths use different adder implementations with different qubit layouts and different ancilla counts. This breaks the Beauregard pattern where addition and subtraction are exact inverses.

**Why it happens:**
The BK CLA compute-copy-uncompute pattern leaves carry-copy ancilla dirty (documented in tests/python/test_cla_bk_algorithm.py lines 7-12). Running the sequence in reverse (for subtraction) would require the carry-copy ancilla to start in the correct dirty state, which is impossible without computing it first -- creating a circular dependency.

**How to avoid:**
1. For modular arithmetic, force RCA mode for all internal additions and subtractions. Do NOT allow automatic CLA selection within modular primitives. This ensures forward/reverse symmetry.
2. OR: Implement a CLA subtractor that does not rely on inverting the CLA adder. The Draper-Kutin CLA paper (quant-ph/0406142) describes a direct subtraction circuit, but it requires different ancilla management.
3. The automatic depth/ancilla tradeoff feature (OPT-01) must be aware of this constraint: when selecting an adder for use inside a modular arithmetic primitive, only RCA is safe unless a dedicated CLA subtractor is implemented.
4. Document this constraint clearly in the API: `ql.option('cla', True)` may not apply to modular arithmetic internally.

**Warning signs:**
- Modular addition gate count is asymmetric (forward path cheaper than reverse)
- Modular addition works but modular subtraction fails
- Automatic tradeoff selects CLA for modular operations but results are wrong

**Phase to address:**
Automatic depth/ancilla tradeoff phase (OPT-01). The tradeoff logic must exclude CLA from modular primitives unless a direct CLA subtractor exists.

---

### Pitfall 5: Quantum Counting Sign Ambiguity Produces Wrong Solution Count

**What goes wrong:**
Quantum counting applies QPE to the Grover operator G = WV (diffusion * oracle). The eigenvalues of G are e^(+/-2i*theta) where sin^2(theta) = M/N. However, the standard implementation of the diffusion operator W = 2|s><s| - I has a global phase. The existing diffusion operator in `diffusion.py` implements W~ = -W (X-MCZ-X pattern), which is equivalent to -2|s><s| + I. This global phase is irrelevant for Grover search (measurement probabilities unchanged) but shifts the QPE eigenvalues from e^(+/-2i*theta) to -e^(+/-2i*theta) = e^(+/-2i*(theta +/- pi/2)). Using the standard formula M = N * sin^2(pi * j / 2^t) with the shifted eigenvalue produces the wrong solution count.

As shown by Chung and Nepomechie (arXiv:2310.07428), using the wrong sign convention in quantum counting can yield m approximately 5 instead of the correct m approximately 3 for a specific example -- an error by almost a factor of 2.

**Why it happens:**
The existing `diffusion()` function was designed for Grover search where the sign does not matter. Quantum counting reuses this diffusion operator but applies QPE, where the sign matters critically.

**How to avoid:**
1. When implementing `ql.count_solutions`, use the corrected formula: `M = N * sin^2(pi * (j/2^t - 1/2))` if using the W~ = -W diffusion operator, NOT the standard `M = N * sin^2(pi * j / 2^t)`.
2. OR: Modify the diffusion operator for quantum counting to include the correct global phase (add an extra global phase gate after the X-MCZ-X pattern).
3. Add a parameter to `diffusion()`: `sign_convention='grover'` (default, omits phase) vs `sign_convention='counting'` (includes correct phase for QPE).
4. Test with known solution counts: oracle that marks exactly k solutions out of N, verify `count_solutions` returns k.

**Warning signs:**
- `count_solutions` returns approximately correct but consistently off by a factor related to pi/2
- Solution count is wrong by a symmetric amount (e.g., returns N-M instead of M)
- QPE phase outputs cluster around unexpected values

**Phase to address:**
Quantum counting phase (GADV-01). Must be addressed in the core counting algorithm design, not as a post-hoc fix.

---

### Pitfall 6: Parametric Compilation Cannot Parameterize Toffoli CQ Sequences

**What goes wrong:**
Parametric compilation (PAR-01/PAR-02) aims to "compile once for all classical values." For QFT-based CQ operations, this is conceptually possible: `CQ_add(bits=8, value=V)` produces a sequence where the classical value `V` only affects rotation angles (gate values), not circuit topology. The topology (which qubits connect to which) is identical for all values of V at the same width. So a parametric version could store the topology once and patch rotation angles per-value.

But for Toffoli-based CQ operations, this is NOT possible. `toffoli_CQ_add(bits=8, value=V)` generates a structurally different circuit for each value of V. The inline CQ generators (Phase 73) exploit known classical bit values to eliminate gates at zero-bit positions -- a value with 3 set bits produces fewer Toffoli gates than a value with 7 set bits. The circuit TOPOLOGY changes per value, not just gate parameters.

**Why it happens:**
The Toffoli CQ optimization (Phase 73) specifically designed the CQ path to be value-dependent for T-count reduction. This is correct for performance but fundamentally incompatible with parametric compilation's goal of compile-once-replay-many.

**How to avoid:**
1. Parametric compilation for Toffoli CQ must be explicitly scoped out or handled differently: either (a) use the non-optimized path (X-init temp, run QQ adder, X-cleanup) which has fixed topology per width, or (b) cache per-value as the current `@ql.compile` does (not truly parametric, but correct).
2. Document clearly: "Parametric compilation parameterizes over QFT rotation angles. Toffoli CQ operations are value-dependent and require per-value compilation."
3. If implementing parametric compilation, detect Toffoli mode and either fall back to per-value caching or use the unoptimized CQ path for parametric functions.
4. The compile cache key already includes classical args, so per-value caching is the existing behavior. The new feature should NOT change this for Toffoli mode.

**Warning signs:**
- Parametric compiled function produces wrong results in Toffoli mode when classical argument changes
- T-count is unexpectedly high (using unoptimized CQ path when optimized was expected)
- Parametric compiled function works in QFT mode but fails in Toffoli mode

**Phase to address:**
Parametric compilation phase (PAR-01/PAR-02). Must design the parametric boundary carefully per backend.

---

## Moderate Pitfalls

### Pitfall 7: Automatic Depth/Ancilla Tradeoff Requires Qubit Budget Information Not Currently Available

**What goes wrong:**
The automatic tradeoff (OPT-01) should select RCA (1 ancilla, O(n) depth) vs CLA (O(n) ancilla, O(log n) depth) based on the circuit's qubit budget. But the framework has no concept of a qubit budget. The `qubit_allocator.c` allocates qubits up to `ALLOCATOR_MAX_QUBITS` (8192) without any feedback about how many qubits are "affordable." The decision to use CLA vs RCA currently depends solely on width (`cla_override == 0 && result_bits >= CLA_THRESHOLD` in hot_path_add_toffoli.c line 112), not on available qubit headroom.

**Why it happens:**
The current architecture has no mechanism for the adder selection logic to query "how many ancilla qubits can I afford?" The allocator tracks `peak_allocated` and `current_in_use` but does not expose a "remaining budget" concept. Without this, the tradeoff cannot be truly automatic -- it can only be threshold-based (use CLA for width >= T, RCA otherwise).

**How to avoid:**
1. Start with the simple width-threshold approach (already implemented as `CLA_THRESHOLD`). This is sufficient for v5.0. Rename the feature from "automatic depth/ancilla tradeoff" to "configurable depth/ancilla tradeoff" if no qubit budget mechanism is added.
2. If a true automatic selection is desired, add a `qubit_budget` option: `ql.option('qubit_budget', 1000)`. The adder selection checks `current_in_use + cla_ancilla_count <= qubit_budget` before selecting CLA.
3. For modular arithmetic, the qubit budget is critical: a modular multiplication with CLA adders needs O(n^2) ancilla across all partial products vs O(n) with RCA. The tradeoff must consider the total operation, not just individual additions.

**Warning signs:**
- CLA selected for large widths causes `ALLOCATOR_MAX_QUBITS` exceeded error
- Automatic selection makes different choices for the same width in different contexts
- Performance is worse with automatic selection than with manual RCA (CLA ancilla overhead exceeds depth benefit)

**Phase to address:**
Automatic depth/ancilla tradeoff phase (OPT-01).

---

### Pitfall 8: Quantum Counting QPE Precision vs Qubit Count for Practical Circuits

**What goes wrong:**
Quantum counting uses QPE with `t` ancilla qubits to estimate the eigenvalue of the Grover operator. The precision of the solution count estimate scales as O(2^t). For a search space of N = 2^n, the counting ancilla register needs t = O(n) qubits to distinguish M solutions from M+1 solutions. This means quantum counting on an 8-qubit search space needs approximately 8 additional ancilla qubits for QPE, plus the search register (8 qubits), plus oracle ancilla. Total qubit count for even modest problems exceeds 20, approaching the Qiskit simulation limit of 17 qubits (from project memory constraints).

**Why it happens:**
The QPE-based quantum counting has inherent qubit overhead. The IQAE-based approach (already implemented in `amplitude_estimation.py`) avoids this by using iterative measurements instead of a QPE register, but IQAE estimates amplitude (probability), not solution count directly. Converting amplitude to count requires M = N * sin^2(theta), which introduces rounding errors for integer M.

**How to avoid:**
1. Implement `ql.count_solutions` using the IQAE infrastructure (already built) rather than QPE-based quantum counting. IQAE estimates sin^2(theta) = M/N with epsilon precision using O(1/epsilon) oracle calls and NO additional QPE ancilla qubits. Then M = round(N * estimate).
2. For exact counting (when M must be an integer), use the IQAE estimate to narrow the range, then run a few Grover searches at nearby iteration counts to verify.
3. Document the qubit limit: "Quantum counting with QPE requires n_search + t_precision + n_oracle_ancilla qubits. For Qiskit simulation, total must be <= 17."
4. The project's simulation constraint (max 17 qubits) means QPE-based counting can only be tested for search spaces of 4-5 qubits. IQAE-based counting can handle larger spaces because it does not add QPE ancilla.

**Warning signs:**
- QPE-based counting exceeds simulation qubit limit for any non-trivial problem
- IQAE-based counting gives M = 2.7 for a problem that should have exactly 3 solutions
- Counting results are consistently off by +/- 1 due to rounding

**Phase to address:**
Quantum counting phase (GADV-01).

---

### Pitfall 9: Layer-Based Uncomputation Breaks When Modular Operations Span Many Layers

**What goes wrong:**
A modular multiplication `x *= a mod N` expands to O(n) modular additions, each of which expands to O(1) plain additions, subtractions, comparisons, and conditional operations. The total gate count for an 8-bit modular multiply is in the thousands. The existing `_start_layer` / `_end_layer` tracking records the layer range for uncomputation. But the known limitation -- "Layer-based uncomputation tracking unreliable when optimizer parallelizes gates" -- means the layer range may not bracket the correct gates after optimization. For modular arithmetic with thousands of gates across hundreds of layers, the optimizer has maximum freedom to reorder, making the layer range almost certainly wrong.

**Why it happens:**
The optimizer's `minimum_layer()` function schedules gates at the earliest possible layer where all operand qubits are available. For Toffoli circuits with many ancilla qubits (which have no prior occupancy), gates can be scheduled much earlier than expected. A comparison gate from modular operation B might be scheduled into a layer that is within the layer range of modular operation A.

**How to avoid:**
1. For v5.0, do NOT rely on layer-based uncomputation for modular operations. Instead, implement modular operations as `@ql.compile`-wrapped functions where the compile decorator handles uncomputation via its own gate-list tracking (not layer indices).
2. The compile decorator's `_partition_ancillas` and `_auto_uncompute` mechanism operates on the captured gate list (Python-level), not on layer indices, making it immune to optimizer reordering.
3. Long-term: transition from layer-based to instruction-counter-based uncomputation tracking (noted as future work in PROJECT.md).
4. Short-term: disable the optimizer for modular arithmetic sequences (emit all gates with sequential layer_floor advancement).

**Warning signs:**
- Modular operations work without optimizer but fail after optimization
- `reverse_circuit_range` on a modular operation reverses wrong gates
- Uncomputation of modular result corrupts other registers

**Phase to address:**
This is a cross-cutting concern that affects all phases. Modular arithmetic phase should use compile-decorator-based uncomputation from the start.

---

### Pitfall 10: Controlled Modular Multiplication for Shor's Requires Controlled-Controlled Operations

**What goes wrong:**
Shor's algorithm requires controlled modular exponentiation: for each qubit in the QPE register, apply a controlled modular multiplication. The modular multiplication internally uses conditional subtraction (controlled by comparison results). This creates controlled-controlled operations (the QPE control AND the comparison control). With Toffoli gates, this means some internal gates become CCCX (3-control X), which exceeds `MAXCONTROLS=2` and requires the `large_control` path or AND-ancilla decomposition. Each CCCX decomposes into 2 CCX + 1 ancilla, doubling the ancilla count for controlled modular arithmetic.

**Why it happens:**
The Toffoli adder uses CCX as its fundamental gate. Adding an external control (for QPE) turns every CCX into CCCX. The existing MCX decomposition handles this (Phase 74: AND-ancilla pattern), but the ancilla count doubles. For controlled modular multiplication with n partial products each containing O(n) adder gates, the total AND-ancilla count is O(n^2).

**How to avoid:**
1. Pre-allocate a single AND-ancilla qubit for the entire controlled modular multiplication and reuse it across all CCCX decompositions. The AND-ancilla pattern (compute, use, uncompute) returns the ancilla to |0> after each use, so a single ancilla suffices.
2. Verify that the `allocator_alloc()` count=1 reuse path (line 94 of qubit_allocator.c) correctly recycles the AND-ancilla. Currently, count=1 reuse works, so this should be fine.
3. Track the AND-ancilla count in circuit stats to verify it stays at 1 (not growing linearly).

**Warning signs:**
- Controlled modular multiply uses 2x or more ancilla than uncontrolled
- `allocator_get_stats()` shows many more ancilla allocations than expected
- Qubit count exceeds simulation limit for even small widths

**Phase to address:**
Modular Toffoli arithmetic phase (FTE-02), specifically when implementing controlled modular multiplication for Shor's.

---

### Pitfall 11: Parametric Compilation Interaction with Oracle Caching

**What goes wrong:**
The existing `@ql.compile` and `@ql.grover_oracle` decorators both cache gate sequences. Parametric compilation (PAR-01/PAR-02) adds a new caching layer where classical parameters can vary without recompilation. If a Grover oracle uses arithmetic operations with classical parameters (e.g., `lambda x: x * a + b == target` where `a`, `b`, `target` are classical), the oracle's compiled form depends on these classical values. Parametric compilation might cache the oracle's gate sequence once and try to parameterize over `a`, `b`, `target`. But changing `a` changes the circuit topology (especially in Toffoli mode, per Pitfall 6), not just gate angles.

**Why it happens:**
The oracle decorator delegates to `@ql.compile` for gate capture. Parametric compilation wraps `@ql.compile`. If parametric compilation is applied to an oracle without understanding which classical parameters are structural (change topology) vs parametric (change angles only), the cached oracle becomes invalid.

**How to avoid:**
1. Oracles must NEVER use parametric compilation for structural parameters. The `@ql.grover_oracle` decorator should force per-value caching for all classical arguments, regardless of whether parametric compilation is enabled globally.
2. Parametric compilation should be opt-in per function, not global: `@ql.compile(parametric=['theta'])` explicitly names which parameters are angle-only.
3. Document: "Parametric compilation only applies to parameters that affect gate angles, not circuit structure. For oracles with classical integer parameters, use standard per-value caching."

**Warning signs:**
- Oracle returns wrong results after classical parameter changes
- Oracle cache hit when cache miss was expected (classical param changed)
- Grover search finds wrong solutions after changing search target

**Phase to address:**
Parametric compilation phase (PAR-01/PAR-02).

---

## Minor Pitfalls

### Pitfall 12: Quantum Counting Requires Controlled Grover Operator -- Not Just Controlled Oracle

**What goes wrong:**
QPE-based quantum counting needs controlled-G^(2^k) where G = WV (diffusion * oracle). Implementers often provide controlled-V (controlled oracle) but forget that the diffusion W must also be controlled. A controlled diffusion operator requires a multi-controlled-Z on (n+1) qubits (n search qubits + 1 control), which is more expensive than the standard n-qubit MCZ.

**How to avoid:**
- Implement `controlled_grover_operator(oracle, search_qubits, control_qubit)` as a single function that applies both controlled-oracle and controlled-diffusion.
- If using IQAE-based counting (recommended per Pitfall 8), this is handled by the iterative protocol which already supports controlled Grover iterations.

**Phase to address:** Quantum counting phase (GADV-01).

---

### Pitfall 13: Automatic Tradeoff Width Threshold Interacts with Hardcoded Sequences

**What goes wrong:**
Toffoli arithmetic has hardcoded sequences for widths 1-8 (CDKM and BK CLA, ~120 C files). If the automatic tradeoff selects a different adder than the hardcoded sequence assumes, the wrong sequence is dispatched. Currently, `CLA_THRESHOLD` controls which adder is used, and hardcoded sequences are generated for both CDKM and BK CLA. But if the threshold changes dynamically (based on qubit budget), the mapping from width to hardcoded sequence becomes ambiguous.

**How to avoid:**
- Hardcoded sequences should be keyed by (width, adder_type), not just width. The existing separate caches (`precompiled_toffoli_QQ_add[]` for CDKM, `precompiled_toffoli_QQ_add_bk[]` for BK) already do this. The dispatch logic just needs to respect the tradeoff decision.
- Verify: when tradeoff changes the adder selection at runtime, the correct cache array is accessed.

**Phase to address:** Automatic depth/ancilla tradeoff phase (OPT-01).

---

### Pitfall 14: Modular Toffoli Multiplication Qubit Count May Exceed Simulation Limit

**What goes wrong:**
An n-bit modular multiplication requires: n data qubits (x), n data qubits (result), 1 ancilla (Beauregard flag), plus adder ancilla per partial product. For CDKM RCA: 1 carry ancilla reusable = n+n+1+1 = 2n+2 qubits. But the comparison operations within modular reduction add more: each `>=` comparison creates a comparison result qubit. For n=8: minimum 18 qubits, more likely 25-30 with comparison temporaries. This approaches the simulation limit (17 qubits max for Qiskit).

**How to avoid:**
- Test modular Toffoli arithmetic at widths 2-4 initially (well within 17-qubit limit)
- Use `matrix_product_state` simulator for wider tests (already used for division tests at 44+ qubits)
- Track qubit count during implementation and set expectations: modular multiplication at width 8+ requires MPS simulator, not statevector

**Phase to address:** Modular Toffoli arithmetic phase (FTE-02) -- testing strategy.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Python-level modular reduction (current `_reduce_mod`) | Works for QFT mode | Creates O(n) orphan qubits per reduction; BUG-MOD-REDUCE | Never for Toffoli mode; replace with C-level Beauregard |
| Width-only threshold for RCA/CLA selection | Simple to implement | Ignores qubit budget; fails for nested operations | Acceptable for v5.0 as starting point |
| Per-value caching for Toffoli CQ in parametric mode | Correct results | No compile-once benefit for Toffoli CQ | Acceptable if documented; true parametric only for QFT |
| Using existing diffusion operator for quantum counting | Reuses code | Wrong sign convention yields wrong M estimate | Never -- must fix sign or use corrected formula |
| Layer-based uncomputation for modular operations | Consistent with existing system | Unreliable under optimizer; known limitation | Never for large composite operations; use compile decorator |

## Integration Gotchas

Common mistakes when integrating these features with existing subsystems.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Modular arithmetic + optimizer | Assuming optimizer preserves modular operation boundaries | Disable optimizer for modular sequences or use compile decorator |
| Parametric compilation + Toffoli mode | Assuming classical params only affect gate angles | Toffoli CQ topology depends on classical value; per-value cache required |
| Quantum counting + existing diffusion | Assuming diffusion sign is irrelevant | Use corrected formula M = N*sin^2(pi*(j/2^t - 1/2)) for W~ = -W |
| Automatic tradeoff + modular arithmetic | Allowing CLA inside modular primitives | Force RCA inside modular operations (CLA subtraction broken) |
| Compile cache + new mode flags | Keeping old cache key | Add arithmetic_mode and cla_override to compile cache key |
| BUG-DIV-02 fix + modular arithmetic | Fixing bugs independently | Modular arithmetic depends on the same MSB comparison pattern; fix together |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Python-level modular reduction loop | Correct for 2-bit | O(n) orphan qubits per call | Width >= 4 |
| CLA adder inside modular multiply | Faster single addition | O(n^2) ancilla across all partial products | Width >= 6 |
| QPE-based quantum counting | Works for small N | Requires n+t qubits (exceeds 17) | Search space >= 5 qubits |
| Controlled modular multiply without AND-ancilla reuse | Correct results | O(n^2) AND-ancilla qubits | Width >= 4 |
| Parametric compile with Toffoli CQ | Cache hit appears to work | Wrong circuit topology | When classical value changes bit pattern |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Modular addition:** Often missing the auxiliary reset step (step 5 of Beauregard) -- verify ancilla returns to |0> after each call
- [ ] **Modular multiplication:** Often missing the controlled variant for Shor's -- verify controlled modular multiply works with external QPE control
- [ ] **Parametric compilation:** Often missing Toffoli CQ handling -- verify classical value changes trigger recompilation in Toffoli mode
- [ ] **Compile cache key:** Often missing new mode flags -- verify cache miss when arithmetic_mode or cla_override changes
- [ ] **Quantum counting:** Often using wrong sign formula -- verify count matches known-solution oracle for M=1,2,3
- [ ] **Automatic tradeoff:** Often allowing CLA inside modular ops -- verify modular arithmetic forces RCA internally
- [ ] **BUG-DIV-02 fix:** Often fixing division only -- verify the same MSB comparison pattern works for modular reduction
- [ ] **Quantum counting IQAE:** Often returning float -- verify integer rounding produces correct M for exact solution counts

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Modular add orphan qubits (Pitfall 2) | HIGH | Rewrite as C-level Beauregard primitive; cannot be patched at Python level |
| Compile cache mode mismatch (Pitfall 3) | LOW | Add mode flags to cache key; one-line change |
| CLA inside modular ops (Pitfall 4) | MEDIUM | Add mode flag to force RCA inside modular primitives |
| Quantum counting sign error (Pitfall 5) | LOW | Switch to corrected formula; one-line change in counting |
| Toffoli CQ parametric failure (Pitfall 6) | MEDIUM | Fall back to per-value caching for Toffoli CQ; document limitation |
| Layer-based uncomputation failure (Pitfall 9) | HIGH | Migrate to compile-decorator-based uncomputation; architectural change |
| BUG-DIV-02 compounds modular (Pitfall 1) | HIGH | Must fix BUG-DIV-02 first; blocks modular arithmetic |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Pitfall 1: BUG-DIV-02 compounds modular | Bug fix phase (BUG-DIV-02) | MSB comparison qubits properly uncomputed; no orphan temporaries |
| Pitfall 2: Modular reduction garbage qubits | Bug fix phase (BUG-MOD-REDUCE) | `circuit_stats()['current_in_use']` stable after modular operations |
| Pitfall 3: Compile cache missing mode flags | Parametric compilation (PAR-01) | Cache miss on mode change; regression test |
| Pitfall 4: CLA subtraction in modular ops | Depth/ancilla tradeoff (OPT-01) | Modular arithmetic forces RCA; assertion in code |
| Pitfall 5: Quantum counting sign | Quantum counting (GADV-01) | `count_solutions` returns exact M for known-solution oracles |
| Pitfall 6: Toffoli CQ parametric | Parametric compilation (PAR-01) | Toffoli CQ triggers recompilation on value change |
| Pitfall 7: No qubit budget | Depth/ancilla tradeoff (OPT-01) | Width-threshold works; document limitation |
| Pitfall 8: Counting qubit overhead | Quantum counting (GADV-01) | Use IQAE-based counting; test within 17-qubit limit |
| Pitfall 9: Layer uncomputation failure | Modular arithmetic (FTE-02) | Use compile decorator for modular ops; avoid layer-based uncomputation |
| Pitfall 10: Controlled modular CCCX | Modular arithmetic (FTE-02) | AND-ancilla reuse verified; qubit count matches expectation |
| Pitfall 11: Oracle parametric caching | Parametric compilation (PAR-01) | Oracles force per-value caching for structural params |
| Pitfall 12: Controlled diffusion for counting | Quantum counting (GADV-01) | Controlled Grover operator includes both oracle and diffusion |
| Pitfall 13: Threshold vs hardcoded sequences | Depth/ancilla tradeoff (OPT-01) | Correct cache array accessed per tradeoff decision |
| Pitfall 14: Modular qubit count | Modular arithmetic (FTE-02) | Width 2-4 with statevector; width 5+ with MPS simulator |

## Sources

- Codebase inspection: `src/quantum_language/qint_mod.pyx`, `src/quantum_language/compile.py`, `src/quantum_language/qint_division.pxi`, `c_backend/src/ToffoliAdditionCDKM.c`, `c_backend/src/ToffoliAdditionCLA.c`, `c_backend/src/hot_path_add_toffoli.c`, `c_backend/include/circuit.h`, `c_backend/include/toffoli_arithmetic_ops.h`
- [Chung & Nepomechie, "Quantum counting, and a relevant sign" (arXiv:2310.07428)](https://arxiv.org/abs/2310.07428) -- sign ambiguity in quantum counting
- [Beauregard, "Circuit for Shor's algorithm using 2n+3 qubits" (arXiv:quant-ph/0205095)](https://arxiv.org/abs/quant-ph/0205095) -- modular arithmetic circuit design
- [A Comprehensive Study of Quantum Arithmetic Circuits (arXiv:2406.03867)](https://arxiv.org/html/2406.03867v1) -- depth-count tradeoffs, RCA vs CLA comparison
- [Draper-Kutin-Rains-Svore CLA Adder (arXiv:quant-ph/0406142)](https://arxiv.org/abs/quant-ph/0406142) -- CLA ancilla requirements
- [Optimal compilation of parametrised quantum circuits (arXiv:2401.12877)](https://arxiv.org/abs/2401.12877) -- parametric compilation constraints
- [Quantum counting algorithm -- Wikipedia](https://en.wikipedia.org/wiki/Quantum_counting_algorithm) -- QPE-based counting overview
- [Classiq: Quantum Counting Using IQAE](https://docs.classiq.io/latest/explore/algorithms/amplitude_estimation/quantum_counting/quantum_counting/) -- IQAE-based counting approach
- Previous research: `.planning/research/PITFALLS-TOFFOLI-ARITHMETIC.md`, `.planning/research/PITFALLS-COMPILE-DECORATOR.md`, `.planning/research/PITFALLS_GROVER.md`
- Known bugs: BUG-DIV-02 (MSB comparison leak), BUG-QFT-DIV (QFT division failures), BUG-MOD-REDUCE (_reduce_mod corruption)

---
*Pitfalls research for: v5.0 Advanced Arithmetic & Compilation (modular Toffoli arithmetic, parametric compilation, depth/ancilla tradeoff, quantum counting)*
*Researched: 2026-02-24*
