# Pitfalls Research: Grover's Algorithm, Oracle Compilation, and Amplitude Estimation

**Domain:** Adding Grover's search, oracle compilation, and amplitude estimation to an existing quantum framework
**Researched:** 2026-02-19
**Confidence:** HIGH (verified from quantum computing literature, framework source code inspection, and established quantum programming patterns)

## Executive Summary

Adding Grover's algorithm and amplitude amplification to the Quantum Assembly framework involves pitfalls in three categories: (1) Oracle design and compilation challenges specific to the existing `@ql.compile` and automatic uncomputation infrastructure, (2) Iteration count and diffusion operator mistakes that cause the algorithm to fail silently (wrong answer with high probability), and (3) Amplitude estimation integration requiring controlled oracle access and inverse operations that must interoperate with the existing dependency tracking system. The most dangerous pitfalls are those that produce syntactically correct circuits but semantically wrong quantum algorithms -- circuits that run without error but return random results.

---

## Critical Pitfalls

Mistakes that cause completely wrong results, require architecture rewrites, or break existing functionality.

### Pitfall 1: Phase Oracle vs Bit-Flip Oracle Confusion

**What goes wrong:**
Users build a bit-flip oracle (flips an ancilla qubit when condition is met) but Grover's algorithm requires a phase oracle (multiplies the amplitude of marked states by -1). The algorithm runs, but amplification fails to occur. Results are uniformly random, not amplified.

**Why it happens:**
Classical thinking: "mark the solution by setting a flag bit." The `@ql.compile` decorator captures exactly what the function does, which may be bit-flip semantics. Without explicit phase conversion, the captured oracle is incorrect for Grover's.

**How to avoid:**
1. Provide explicit oracle type parameter: `@ql.grover_oracle(oracle_type='phase')` or `@ql.grover_oracle(oracle_type='bitflip')`
2. If bitflip oracle provided, automatically wrap with phase kickback transformation:
   - Sandwich ancilla qubit with X-H-(...oracle...)-H-X
   - Or initialize ancilla in |-> state (X then H) and apply XOR oracle
3. Document clearly: "Grover requires phase oracles. If your function sets a flag qubit, use `oracle_type='bitflip'` for automatic conversion."
4. Detect common patterns: If the oracle only targets a single "result" qubit and applies X gates controlled on search qubits, it's likely a bitflip oracle.

**Warning signs:**
- Oracle function takes an extra `result` qubit parameter
- Oracle function contains `if condition: result ^= 1` patterns
- Grover returns uniformly distributed results instead of amplified solutions

**Phase to address:**
Phase 1 (Oracle Infrastructure) -- core oracle decorator must handle both types from the start.

**Confidence:** HIGH -- verified from [Qiskit tutorials](https://qiskit-community.github.io/qiskit-algorithms/tutorials/06_grover.html) and quantum computing literature. The phase kickback technique is standard.

---

### Pitfall 2: Uncomputation Destroys Phase Information in Oracles

**What goes wrong:**
The existing automatic uncomputation (`_auto_uncompute` in compile.py, qubit_saving_mode) uncomputes ancilla qubits used during oracle evaluation. However, the oracle's purpose is to create a phase mark on the search register. If intermediate computations that contribute to the phase mark are uncomputed too early (before phase kickback occurs), the phase information is lost.

**Why it happens:**
The current compile decorator tracks ancilla allocations and can eagerly uncompute them in `qubit_saving_mode`. For arithmetic operations this is correct. For oracles, the phase must be kicked back to the search register BEFORE uncomputation occurs.

**Consequences:**
- Oracle appears to work (gates run, qubits are used/freed)
- No phase mark is applied to marked states
- Grover iterations do nothing (uniform superposition throughout)
- Silently wrong results with no error

**How to avoid:**
1. Oracle compilation must preserve phase before uncomputation:
   ```python
   # Correct oracle structure:
   # 1. Compute condition into ancilla
   # 2. Apply phase gate (Z or controlled-Z) based on ancilla
   # 3. THEN uncompute ancilla
   ```
2. Add explicit `phase_point` marker: `ql.mark_phase(condition_qubit)` that applies Z gate before any uncomputation
3. Oracle decorator should delay uncomputation until after phase application:
   ```python
   @ql.grover_oracle
   def my_oracle(x):
       condition = (x == 42)  # Creates temp qubits
       ql.mark_phase(condition)  # Apply phase BEFORE uncomputation
       # Framework auto-uncomputes condition after mark_phase
   ```
4. In qubit_saving_mode, detect oracle context and defer uncomputation to end of oracle scope

**Warning signs:**
- Oracle function uses comparisons/arithmetic but never applies Z/phase gates
- Oracle returns a qbool but no controlled-Z is visible in the circuit
- `@ql.compile` with `qubit_saving_mode=True` inside oracle code

**Phase to address:**
Phase 1 (Oracle Infrastructure) -- must be architected before any oracle features work correctly.

**Confidence:** HIGH -- verified from [Qrisp uncomputation docs](https://qrisp.eu/reference/Core/Uncomputation.html) and the project's compile.py code showing auto_uncompute logic.

---

### Pitfall 3: Iteration Count Calculation Error (Over/Under Iteration)

**What goes wrong:**
The optimal number of Grover iterations is `floor(pi/4 * sqrt(N/M) - 1/2)` where N is search space size and M is number of solutions. Too few iterations: solution not amplified enough. Too many iterations: probability oscillates past the peak and decreases. Both failure modes give wrong answers with high probability.

**Why it happens:**
- Using `sqrt(N)` instead of `sqrt(N/M)` when multiple solutions exist
- Off-by-one errors in iteration count formula
- Not accounting for the initial superposition state (first iteration is different)
- Assuming "more iterations = better" (classical optimization intuition)

**Consequences:**
- Algorithm returns non-solutions with high probability
- Users blame oracle correctness when the real issue is iteration count
- Debugging is difficult because circuit runs fine

**How to avoid:**
1. Provide automatic iteration count calculation:
   ```python
   def grover_iterations(n_qubits: int, n_solutions: int = 1) -> int:
       N = 2 ** n_qubits
       return max(1, int(np.floor(np.pi/4 * np.sqrt(N / n_solutions) - 0.5)))
   ```
2. For unknown number of solutions, implement quantum counting first
3. Warn users when they specify iteration count manually: "Manual iteration count provided. Optimal for N={N}, M=1 is {optimal}."
4. Document the probability-vs-iterations curve and why it oscillates
5. Test with known-solution oracles and verify peak probability at calculated iteration count

**Warning signs:**
- User passes `iterations=100` for a 4-qubit search (optimal is ~3)
- Success probability is suspiciously close to 1/N (no amplification occurred)
- Success probability varies wildly with small changes to iteration count

**Phase to address:**
Phase 2 (Grover's Core Algorithm) -- iteration API must include calculation helpers.

**Confidence:** HIGH -- verified from [Microsoft Azure Quantum documentation](https://learn.microsoft.com/en-us/azure/quantum/concepts-grovers) and [Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm).

---

### Pitfall 4: Diffusion Operator Applied to Wrong Qubit Subset

**What goes wrong:**
The Grover diffusion operator must reflect about the uniform superposition state on the search register qubits. If it's applied to ancilla qubits, oracle qubits, or a subset of search qubits, the algorithm breaks.

**Why it happens:**
- Oracle may entangle search qubits with ancillas; developer applies diffusion to all qubits
- Variable-width qints make it unclear which qubits are "the search register"
- Multiple qints passed to oracle; diffusion applied to only one

**Consequences:**
- Diffusion on wrong qubits destroys superposition
- Algorithm may still "run" but probabilities don't amplify
- Hard to debug because circuit structure looks reasonable

**How to avoid:**
1. Grover API must explicitly track search register qubits:
   ```python
   result = ql.grover(search_space=x, oracle=my_oracle, iterations=k)
   # search_space defines which qubits get diffusion
   ```
2. Diffusion operator takes explicit qubit list, not "all qubits in circuit"
3. Document: "Ancilla and output qubits do NOT receive diffusion"
4. Validate: assert len(diffusion_qubits) == n_search_qubits before applying

**Warning signs:**
- Diffusion operator in circuit spans more qubits than search space
- Oracle returns qbool/qint that is included in diffusion
- Circuit depth increases unexpectedly (diffusion on too many qubits)

**Phase to address:**
Phase 2 (Grover's Core Algorithm) -- diffusion operator implementation.

**Confidence:** HIGH -- standard quantum algorithm requirement.

---

### Pitfall 5: Amplitude Estimation Requires Oracle Inverse Access

**What goes wrong:**
Amplitude estimation (and amplitude amplification) requires the ability to apply both the state preparation unitary U and its inverse U^dagger. The existing `@ql.compile` decorator supports `.adjoint` for inverse access, but the oracle must also be invertible. If the oracle contains measurements, non-unitary operations, or is not efficiently invertible, amplitude estimation cannot work.

**Why it happens:**
Research published in July 2025 by Tang and Wright formally proves that amplitude amplification and estimation require inverse access -- there's no workaround. Classical functions compiled into oracles may not have efficient inverses if they depend on irreversible operations.

**Consequences:**
- Amplitude estimation fails at runtime when U^dagger is needed
- Or, naive inverse computation causes exponential blowup in circuit size
- Algorithm cannot achieve quadratic speedup without inverse access

**How to avoid:**
1. Oracle decorator must verify invertibility at compile time:
   - Check no measurement gates in oracle body
   - Confirm all operations are unitary
2. The existing compile.py `_adjoint_gate` function handles most gates (P, R have angle negation). Extend to handle oracle-specific patterns.
3. For controlled-U^dagger in amplitude estimation, use the existing `block.control_virtual_idx` mechanism with adjoint gates.
4. Document: "Oracles for amplitude estimation must be pure (no measurements, no classical side effects)"
5. Error clearly: "Oracle contains measurement gate at position X. Amplitude estimation requires invertible oracles."

**Warning signs:**
- Oracle function calls `measure()` or `sample()`
- Oracle accesses external state that changes between calls
- `oracle.adjoint()` raises an error about non-reversible gates

**Phase to address:**
Phase 3 (Amplitude Estimation) -- prerequisite check before algorithm runs.

**Confidence:** HIGH -- verified from [Tang & Wright 2025](https://arxiv.org/abs/2507.23787): "Amplitude amplification and estimation require inverses."

---

### Pitfall 6: Garbage Qubits Cause Destructive Interference

**What goes wrong:**
If an oracle produces "garbage" qubits (intermediate results that are not uncomputed), these garbage qubits become entangled with the search register. When the diffusion operator is applied, the garbage causes destructive interference that destroys the amplification.

**Why it happens:**
The oracle computes correctly, but temporary values are left behind instead of being uncomputed. The existing `@ql.compile` with `qubit_saving_mode=False` (lazy mode) intentionally leaves ancillas allocated for later reuse. In Grover context, this is wrong -- oracle must be "clean" (all ancillas returned to |0>).

**Consequences:**
- Search register becomes entangled with garbage
- Looking at search register alone shows maximally mixed state
- Amplification fails silently

**How to avoid:**
1. Oracles MUST run with forced uncomputation:
   ```python
   @ql.grover_oracle  # Implicitly enables qubit_saving_mode for oracle body
   def my_oracle(x):
       temp = x * 2  # temp qubits allocated
       result = (temp == 84)
       return result  # temp MUST be uncomputed before return
   ```
2. Oracle decorator should validate: after oracle execution, only phase changes remain (no new entangled qubits)
3. Use the existing `_partition_ancillas` logic from compile.py to identify temp vs return qubits, ensure all temp qubits are uncomputed
4. Add circuit validation: check that oracle's qubit allocation delta is zero (except for designated output qubit)

**Warning signs:**
- Oracle allocates qubits that are never freed
- `circuit_stats()['current_in_use']` increases after oracle call
- Search results show uniform distribution instead of amplified peaks

**Phase to address:**
Phase 1 (Oracle Infrastructure) -- oracle must enforce clean uncomputation.

**Confidence:** HIGH -- fundamental requirement for Grover's algorithm. Garbage qubits destroy quantum interference.

---

## Moderate Pitfalls

Mistakes that cause performance issues, unexpected behavior, or technical debt.

### Pitfall 7: Controlled Oracle for Amplitude Estimation Has Wrong Control Semantics

**What goes wrong:**
Amplitude estimation requires controlled applications of the Grover operator (oracle + diffusion). The existing compile.py `_derive_controlled_gates` adds a control qubit to every gate. However, for oracles, the control should only activate the phase flip, not the entire computation.

**Why it happens:**
The generic controlled-gate derivation treats all gates equally. For oracles: compute condition (always runs), apply phase flip (controlled), uncompute (always runs). If the entire oracle is naively controlled, the control qubit must be |1> just to evaluate the condition -- wrong semantics.

**Consequences:**
- Controlled oracle doesn't produce intended behavior
- Amplitude estimation phases are incorrect
- Results are wrong even though circuit looks correct

**How to avoid:**
1. Oracle structure must separate phases:
   ```python
   # Inside oracle:
   condition = compute_condition(x)  # NOT controlled
   ql.controlled_phase(condition)     # Controlled by QPE ancilla
   uncompute_condition()              # NOT controlled
   ```
2. When deriving controlled oracle, only control the phase application, not compute/uncompute
3. Document the three-phase oracle structure clearly
4. Consider explicit marking: `with ql.controlled():` only wraps the phase part

**Warning signs:**
- Controlled oracle circuit depth is 3x normal oracle depth
- QPE/amplitude estimation gives obviously wrong phases
- Controlled oracle uses vastly more gates than expected

**Phase to address:**
Phase 3 (Amplitude Estimation) -- when implementing controlled-Grover.

**Confidence:** MEDIUM -- specific to this framework's control derivation approach.

---

### Pitfall 8: QFT vs Toffoli Mode Interaction with Oracles

**What goes wrong:**
The framework has two arithmetic modes: QFT-based (rotations) and Toffoli-based (fault-tolerant). Oracles using arithmetic may produce different circuits depending on mode. If mode changes between oracle compilation and execution, cached gates are invalid.

**Why it happens:**
The compile.py cache key includes `qubit_saving` mode but not `arithmetic_mode`. Oracle compiled in QFT mode is replayed in Toffoli mode -- gates don't match hardware expectations.

**Consequences:**
- Oracle produces different results depending on when it was compiled
- Hard to reproduce bugs (depends on cache state)
- Toffoli mode circuits may be much larger than expected

**How to avoid:**
1. Add `arithmetic_mode` to compile cache key:
   ```python
   # In CompiledFunc.__call__:
   arithmetic_mode = ql.option('fault_tolerant')
   cache_key = (tuple(classical_args), tuple(widths), control_count, qubit_saving, arithmetic_mode)
   ```
2. Or, clear oracle caches when arithmetic mode changes
3. Document: "Changing `ql.option('fault_tolerant')` invalidates compiled oracle caches"
4. Consider separate oracle caches per mode

**Warning signs:**
- Same oracle produces different gate counts on different runs
- Oracle works in simulator but fails on fault-tolerant backend
- `circuit.gate_counts` shows unexpected gate types (rotations vs Toffolis)

**Phase to address:**
Phase 1 (Oracle Infrastructure) -- cache key must include all mode flags.

**Confidence:** HIGH -- verified from project source code: compile.py uses `qubit_saving` in cache key but not `arithmetic_mode`.

---

### Pitfall 9: Multiple Solutions Unknown Leads to Wrong Iteration Count

**What goes wrong:**
The optimal iteration formula depends on M (number of solutions). If M is unknown and assumed to be 1 when it's actually larger, too many iterations are performed and probability overshoots.

**Why it happens:**
Users often don't know M upfront. The naive approach: "assume M=1 and run Grover." If M is actually 10, optimal iterations are ~3x fewer than calculated for M=1.

**Consequences:**
- Algorithm finds solutions but not reliably
- Success probability varies between runs in ways that seem random
- When M is large (>N/4), Grover may actually reduce success probability

**How to avoid:**
1. Implement quantum counting as prerequisite for Grover when M is unknown:
   ```python
   if num_solutions is None:
       M_estimate = ql.quantum_count(search_space, oracle)
       iterations = grover_iterations(n_qubits, M_estimate)
   ```
2. Use adaptive Grover: start with few iterations, measure, repeat with more if no solution found
3. Warn when user doesn't specify M: "Number of solutions unspecified. Using M=1; results may be suboptimal if multiple solutions exist."
4. For M > N/4, skip Grover entirely (classical is better)

**Warning signs:**
- Grover finds solutions sometimes but not others
- Success probability is lower than expected sqrt(M/N) scaling
- Adding more iterations makes success rate worse

**Phase to address:**
Phase 4 (Quantum Counting) -- prerequisite for robust Grover.

**Confidence:** HIGH -- fundamental property of Grover's algorithm.

---

### Pitfall 10: Oracle Captures External State at Compile Time

**What goes wrong:**
The `@ql.compile` decorator captures gate sequences on first call. If the oracle's behavior depends on external Python variables (classical parameters), the captured sequence reflects values at compile time, not call time.

**Why it happens:**
Python closures capture variables by reference, but the compiled gate sequence uses their VALUES at capture time. If a classical parameter changes between compile and replay, the replay uses stale values.

**Consequences:**
- Oracle marks different states than intended
- Bugs depend on call order (first call "locks in" behavior)
- Extremely confusing debugging experience

**How to avoid:**
1. Oracle classical parameters must be part of cache key (already handled by `_classify_args` for function arguments)
2. Warn if oracle closure references mutable external state
3. Document: "All classical values affecting oracle behavior must be passed as function parameters, not captured from outer scope"
4. Consider static analysis: detect closures over non-constant values
5. Test with varied classical parameters to ensure replay correctness

**Warning signs:**
- Oracle behaves correctly on first call, incorrectly on subsequent calls
- Changing a global variable doesn't change oracle behavior
- `oracle.clear_cache()` "fixes" the bug

**Phase to address:**
Phase 1 (Oracle Infrastructure) -- parameter handling in oracle decorator.

**Confidence:** HIGH -- inherent to the compile decorator's caching mechanism.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without architecture changes.

### Pitfall 11: Grover on Small N is Slower Than Classical

**What goes wrong:**
For small search spaces (N < 100), the overhead of setting up Grover (superposition, oracle, diffusion) exceeds the benefit. Users run Grover on 3-qubit problems and wonder why it's not faster.

**How to avoid:**
- Warn when N is small: "Grover on N=8 has overhead exceeding benefit. Consider classical search."
- Document break-even point (~N > 1000 for typical overhead)
- Provide timing comparison utility

**Phase:** Documentation phase.

---

### Pitfall 12: Forgetting Initial Hadamard on Search Register

**What goes wrong:**
Grover requires starting in uniform superposition |s> = H^n|0>^n. If the user forgets to apply Hadamards before Grover iterations, the search starts in |0...0>, which is either the solution (trivial) or not amplified correctly.

**How to avoid:**
- Grover API automatically applies initial Hadamards
- Document: "ql.grover() includes initial superposition; do not apply H gates before calling"
- Validate: warn if search register already has gates applied before Grover call

**Phase:** Phase 2 (Grover's Core Algorithm).

---

### Pitfall 13: Amplitude Estimation Precision vs Circuit Depth Tradeoff

**What goes wrong:**
Standard QPE-based amplitude estimation requires m ancilla qubits for m bits of precision, with circuit depth 2^m controlled-oracle applications. Users request high precision without understanding the exponential cost.

**How to avoid:**
- Implement iterative amplitude estimation (IQAE) as default -- logarithmic depth
- Provide complexity estimates: "Precision ε requires O(1/ε) oracle calls"
- Warn if requested precision implies circuit depth exceeding hardware limits

**Phase:** Phase 3 (Amplitude Estimation).

---

### Pitfall 14: Oracle Output Qubit Measured Instead of Search Register

**What goes wrong:**
Users measure the oracle's output qubit (the phase-marked ancilla) instead of the search register. The output qubit is always in |-> after phase kickback -- measuring it gives random results.

**How to avoid:**
- Document clearly which qubits to measure
- Grover API returns the search register, not the oracle ancilla
- Consider hiding oracle ancilla from user entirely

**Phase:** Phase 2 (Grover's Core Algorithm) -- API design.

---

### Pitfall 15: Existing Dependency Tracking Conflicts with Oracle Scoping

**What goes wrong:**
The framework's dependency tracking (`_start_layer`, `_end_layer`, `dependency_parents` in qint.pyx) is designed for arithmetic operations. Oracle scoping has different semantics -- the entire oracle is atomic from dependency perspective, not individual operations within it.

**How to avoid:**
- Mark oracle entry/exit in dependency system
- All qubits touched by oracle share same scope epoch
- Uncomputation scope respects oracle boundaries

**Phase:** Phase 1 (Oracle Infrastructure) -- before implementing oracle decorator.

**Confidence:** MEDIUM -- interaction with existing system needs careful design.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded iteration count | Quick prototype | Fails on different problem sizes | Demo code only, never production |
| Skipping oracle uncomputation | Simpler oracle code | Garbage qubits break algorithm | Never -- fundamentally incorrect |
| Manual diffusion implementation | Works for one width | Must rewrite for each width | Prototyping only |
| Ignoring multiple solutions | Simpler API | Suboptimal for M > 1 | When M is known to be 1 |
| QPE-based amplitude estimation | Standard textbook approach | Exponential depth | When precision needs are small |

---

## Integration Gotchas

Common mistakes when integrating with existing Quantum Assembly features.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `@ql.compile` decorator | Assuming compile handles oracle semantics | Create separate `@ql.grover_oracle` that extends compile with oracle-specific behavior |
| `with` statement (conditionals) | Using conditionals inside oracle | Oracle phase is global; use explicit phase marking |
| Automatic uncomputation | Letting qubit_saving uncompute mid-oracle | Force uncomputation timing within oracle decorator |
| Variable-width qint | Diffusion on variable width | Validate all qints in search register have same width |
| Toffoli mode | Assuming oracle is mode-agnostic | Include arithmetic_mode in oracle cache key |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Naive oracle synthesis | Circuit works | Use reversible logic synthesis | > 10 variables in oracle |
| Full QPE for amplitude est | Results correct | Use iterative methods | > 5 qubits precision |
| Non-optimal diffusion | Algorithm works | Use optimized multi-controlled-Z | > 8 qubits search space |
| Oracle recompilation | Fast enough | Cache oracle per argument signature | > 100 oracle calls |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Oracle:** Often missing uncomputation -- verify ancilla count is zero after oracle
- [ ] **Grover loop:** Often missing final measurement -- verify search register is measured
- [ ] **Iteration count:** Often hardcoded -- verify formula accounts for solution count
- [ ] **Diffusion:** Often wrong qubit set -- verify only search qubits get diffusion
- [ ] **Phase oracle:** Often bit-flip instead -- verify Z gates or phase kickback present
- [ ] **Amplitude estimation:** Often missing inverse access -- verify oracle.adjoint works
- [ ] **Controlled oracle:** Often controls entire oracle -- verify only phase part is controlled

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong oracle type (bit vs phase) | LOW | Add phase kickback wrapper, no algorithm changes |
| Garbage qubits in oracle | MEDIUM | Refactor oracle to uncompute temps; may need new oracle structure |
| Wrong iteration count | LOW | Recalculate with correct formula; rerun |
| Diffusion on wrong qubits | LOW | Identify search register; fix qubit list |
| Oracle caches wrong mode | LOW | Clear cache (`oracle.clear_cache()`); may need mode in key |
| No inverse access | HIGH | Rewrite oracle to be invertible; may require different approach |
| External state capture | MEDIUM | Move variables to parameters; clear cache |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Phase vs bit-flip oracle | Phase 1: Oracle Infrastructure | Test both oracle types produce correct amplification |
| Uncomputation destroys phase | Phase 1: Oracle Infrastructure | Verify phase marks survive uncomputation |
| Iteration count error | Phase 2: Grover Core | Test known-solution oracles at various N |
| Diffusion wrong qubits | Phase 2: Grover Core | Assert diffusion qubit count == search width |
| No inverse access | Phase 3: Amplitude Estimation | Test oracle.adjoint() succeeds |
| Garbage qubits | Phase 1: Oracle Infrastructure | Assert oracle ancilla delta == 0 |
| Controlled oracle semantics | Phase 3: Amplitude Estimation | QPE produces correct phase estimates |
| QFT/Toffoli mode interaction | Phase 1: Oracle Infrastructure | Run oracle in both modes, compare results |
| Multiple solutions unknown | Phase 4: Quantum Counting | Counting produces correct M estimate |
| External state capture | Phase 1: Oracle Infrastructure | Test oracle with varied external state |

---

## Sources

- [Grover's Algorithm -- IBM Quantum Learning](https://learning.quantum.ibm.com/course/fundamentals-of-quantum-algorithms/grovers-algorithm)
- [Grover's Algorithm and Amplitude Amplification -- Qiskit](https://qiskit-community.github.io/qiskit-algorithms/tutorials/06_grover.html)
- [Qrisp Uncomputation Documentation](https://qrisp.eu/reference/Core/Uncomputation.html)
- [Amplitude amplification and estimation require inverses -- Tang & Wright 2025](https://arxiv.org/abs/2507.23787)
- [Theory of Grover Search Algorithm -- Microsoft Azure Quantum](https://learn.microsoft.com/en-us/azure/quantum/concepts-grovers)
- [Grover's Algorithm -- Wikipedia](https://en.wikipedia.org/wiki/Grover's_algorithm)
- [Unqomp: Synthesizing Uncomputation in Quantum Circuits -- PLDI 2021](https://dl.acm.org/doi/10.1145/3453483.3454040)
- [VQO: Verified Compilation of Quantum Oracles](https://github.com/inqwire/vqo)
- [Quantum Circuit Synthesis for Grover's Algorithm Oracle -- MDPI 2024](https://www.mdpi.com/1999-4893/17/9/382)
- [Phase Kickback -- Wikipedia](https://en.wikipedia.org/wiki/Phase_kickback)
- [Iterative Quantum Phase Estimation -- Qiskit](https://qiskit.org/documentation/stable/0.28/tutorials/algorithms/09_IQPE.html)
- Project source: `src/quantum_language/compile.py` (oracle caching, adjoint derivation)
- Project source: `src/quantum_language/_core.pyx` (circuit state, controlled context)
- Project source: `src/quantum_language/qint.pyx` (dependency tracking, width handling)

---
*Pitfalls research for: Grover's Algorithm, Oracle Compilation, Amplitude Estimation*
*Researched: 2026-02-19*
