# Pitfalls Research: Multi-Level Compilation Infrastructure (v7.0)

**Domain:** Adding call graph DAG, sequence merging, and sparse circuit support to existing quantum circuit compilation framework
**Researched:** 2026-03-05
**Confidence:** HIGH (based on direct codebase analysis of compile.py, circuit_allocations.c, _core.pyx, types.h, and 118 existing compile tests)

## Executive Summary

The v7.0 multi-level compilation restructuring introduces three interlocking subsystems (call graph DAG, selective sequence merging, sparse circuit arrays) into a framework where `@ql.compile` already has 118 tests, 6 consumers (Grover's, quantum walk, chess demo, quantum counting, amplitude estimation, oracle decorator), and tight coupling between Python-level gate lists, Cython boundary functions (`inject_remapped_gates`, `extract_gate_range`), and a C backend built on 2D jagged arrays (`gate_t **sequence[layer][gate]`). The fundamental risk is that each new subsystem can silently break quantum semantics -- unlike classical compilation, a missed qubit dependency produces a valid-looking circuit that computes the wrong quantum state, with no runtime error. The pitfalls below are ordered by severity: the first five are "silent corruption" risks, the remaining are performance or integration regressions.

---

## Critical Pitfalls

Issues that produce silently incorrect circuits or cause data loss.

### Pitfall 1: Incomplete Qubit Dependency Tracking in Call Graph DAG

**What goes wrong:** The call graph DAG must track which qubits each compiled function reads and writes to determine parallelism and ordering. In quantum circuits, *every* qubit touched by a gate is both read and written (unitary operations are reversible transformations of the full state). If the dependency tracker treats control qubits as "read-only" (a natural classical intuition), it will conclude that two functions sharing only control qubits can execute in parallel. They cannot -- the control qubit's phase is affected by controlled operations (phase kickback), so reordering produces a different quantum state.

**Why it happens:** Classical compiler intuition distinguishes reads from writes. Quantum gates have no such distinction: a CNOT modifies both the control and target qubit's quantum state. The existing `_build_virtual_mapping` in compile.py correctly treats all qubits in `[gate["target"]] + gate["controls"]` uniformly (line ~491), but a new call graph layer might introduce a read/write distinction for "optimization."

**How to avoid:**
1. Every qubit in a gate's target AND controls list is a dependency. Period. No read/write distinction.
2. Two call graph nodes sharing ANY qubit must be sequentially ordered.
3. Unit test: Create two compiled functions that share only a control qubit. Verify the call graph enforces ordering. Verify the output state matches sequential execution.

**Warning signs:** Call graph shows two nodes as parallelizable when they share control qubits. Tests pass for computational basis states but fail for superposition inputs (phase kickback only manifests in superposition).

**Phase to address:** Phase 1 (call graph DAG design). This is the foundational invariant.

---

### Pitfall 2: Sequence Merging Violates Gate Ordering Semantics

**What goes wrong:** When merging two compiled sequences that operate on overlapping qubits, the merge must preserve the relative order of every gate pair that shares a qubit. A merge heuristic that interleaves gates from sequence A and B based on "earliest available layer" can reorder gates on the same qubit. In quantum circuits, gate order on the same qubit is NEVER commutative (except for trivially commuting pairs like two Z rotations). Reordering `H(q0); X(q0)` to `X(q0); H(q0)` produces a completely different unitary.

**Why it happens:** The existing circuit builder in C (`add_gate` in gate.c) uses layer scheduling to pack gates into the earliest available layer, which naturally preserves per-qubit ordering because gates are added sequentially. But a merge operation that takes two pre-built gate lists and interleaves them can violate this if it does not maintain topological sort order per qubit.

**How to avoid:**
1. Treat each qubit's gate sequence as a total order (chain). Merging two sequences is a topological merge of multiple chains -- standard DAG scheduling.
2. Build a per-qubit dependency graph before merging. Each gate depends on the previous gate on any of its qubits (target or control).
3. Validate merged sequences: for every qubit, extract its gate subsequence and verify it matches the concatenation of the original subsequences.
4. Never merge across compiled function boundaries that have ancilla tracking -- the ancilla lifecycle (allocate, use, uncompute, deallocate) must remain contiguous.

**Warning signs:** Merged circuits have correct gate counts but wrong simulation results. Optimizer reports "improved depth" but Qiskit verification fails.

**Phase to address:** Phase 2 (selective merge implementation). Gate ordering validation should be a mandatory post-merge check.

---

### Pitfall 3: Ancilla Lifecycle Corruption During Merge or DAG Reordering

**What goes wrong:** Compiled functions with `inverse=True` track ancilla allocations via `AncillaRecord` (forward call registry). The ancilla lifecycle is: allocate -> use -> uncompute (via inverse) -> deallocate. If sequence merging interleaves gates from two functions that share an ancilla pool, or if DAG reordering moves the inverse call away from its forward call, ancillas may be in use when they are expected to be in |0> state, or deallocated while still entangled.

**Why it happens:** The existing `_partition_ancillas` in compile.py (line ~430) splits ancillas into "return" vs "temp" based on `return_qubit_range`. This partitioning is valid only when the forward and inverse calls are paired. Multi-level compilation that restructures call ordering can break this pairing. The `_forward_calls` deque in `CompiledFunc` assumes LIFO ordering -- the chess demo relies on this for oracle replay with correct inverse order (key decision: "Oracle replay for board state derivation").

**How to avoid:**
1. Treat forward-inverse pairs as atomic units in the call graph. Never split them.
2. If a compiled function has ancillas (`_has_ancillas` flag), its call graph node must include both the forward and inverse calls as a single scheduling unit.
3. Ancilla qubits must not appear in the dependency graph of any other node between the forward and inverse calls.
4. Test: Compile a function with ancillas, call forward, interleave other operations, call inverse. Verify ancillas return to |0> via statevector check.

**Warning signs:** `f.inverse(x)` produces "No forward call to invert" errors after DAG restructuring. Ancilla qubits show non-zero amplitude in statevector after inverse.

**Phase to address:** Phase 1 (call graph design must encode forward-inverse atomicity).

---

### Pitfall 4: Parametric Compilation Topology Breaks After Merge

**What goes wrong:** Parametric compilation (`@ql.compile(parametric=True)`) uses `_extract_topology` to verify that different classical values produce the same circuit structure (same gate types, same qubit connectivity, different angles only). After sequence merging, the merged topology may differ from the unmerged topology because the merge changes layer assignments. If the parametric cache uses pre-merge topology as the key but replays post-merge gates, or vice versa, topology mismatches cause spurious re-captures or incorrect angle substitution.

**Why it happens:** The topology signature in `_extract_topology` (line ~78) includes `(gate_type, target, controls_tuple, num_controls)` per gate. Merging does not change these per-gate, but it changes gate ordering. If topology comparison is order-sensitive (it is -- it's a tuple of tuples), then merging changes the topology even when the logical circuit is equivalent.

**How to avoid:**
1. Decide early: does parametric topology comparison happen before or after merging? Pick one and be consistent.
2. Recommendation: topology comparison should happen BEFORE merge (on individual compiled blocks), and merged sequences should be derived from already-topology-validated blocks.
3. Never cache a merged sequence under a parametric key derived from unmerged topology.
4. Test: Create a parametric function, call with value A (triggers capture + merge), call with value B (should parametric replay). Verify gates match value B's angles.

**Warning signs:** Parametric cache hit rate drops to 0% after enabling merge. Or worse: parametric replay produces wrong angles because the merge reordered gates.

**Phase to address:** Phase 2 (merge must be topology-aware if parametric compilation is enabled).

---

### Pitfall 5: Cache Key Explosion from opt_flag Levels

**What goes wrong:** Adding three-level `opt_flag` compilation (call graph only / selective merge / full expansion) multiplies the cache key space. The existing cache key includes `(widths, mode_flags)` via `_get_mode_flags()` which returns `(arithmetic_mode, cla_override, tradeoff_policy)`. Adding `opt_flag` means each function is potentially cached at 3 different compilation levels. If a function is first called at opt_flag=0 (call graph only), cached, then called at opt_flag=2 (full expansion) in a different context, the stale call-graph-only entry may be returned instead of the fully expanded one.

**Why it happens:** The existing `_cache` dict in `CompiledFunc` keys on argument signatures. If opt_flag is not included in the key, different optimization levels collide. But if opt_flag IS included, the cache fragments -- a function compiled at level 0 is recompiled at level 2 even though level 2 is a superset.

**How to avoid:**
1. Include opt_flag in the cache key, but implement a promotion path: level 0 cache entry can be promoted to level 2 by applying merge/expansion on top of the cached call graph.
2. Never silently return a lower-level cache entry when a higher level is requested.
3. Clear cache on opt_flag change (similar to how `_get_mode_flags` handles arithmetic mode changes).
4. Test: Call function at opt_flag=0, then at opt_flag=2. Verify the second call produces a different (more optimized) gate sequence.

**Warning signs:** Circuit depth does not decrease when increasing opt_flag. Or: increasing opt_flag produces different results (correctness bug from stale cache).

**Phase to address:** Phase 1 (cache key design must account for opt_flag from the start).

---

### Pitfall 6: Breaking the 118 Existing Compile Tests via Behavioral Changes

**What goes wrong:** The existing 118 tests in `test_compile.py` test specific gate counts, optimization ratios, cache hit/miss patterns, ancilla tracking behavior, and controlled variant derivation. Any change to compilation infrastructure risks breaking these tests in ways that look like test failures but are actually behavioral regressions. For example, if sequence merging changes the optimization ratio, a test asserting "12 gates reduced to 8" now gets "12 gates reduced to 7" -- the test fails, but the new behavior is arguably better. The temptation is to "update the test," but the old assertion may have been catching a specific invariant.

**Why it happens:** The tests are characterization tests -- they assert specific numerical outcomes, not just "circuit is correct." This is by design (v2.0 key decision: "Comprehensive test suite (62 tests) covering all compilation scenarios," expanded to 118 by v2.1). Changing compilation semantics changes these numbers.

**How to avoid:**
1. Run the full existing test suite BEFORE any compilation changes as a baseline. Record all pass/fail/skip/xfail counts.
2. New compilation features (call graph, merge, sparse) should be OPT-IN. Default behavior (`@ql.compile` with no new flags) must produce identical gate sequences to v6.1.
3. If a test breaks under new behavior, verify the new behavior is correct via Qiskit simulation before updating the test expectation.
4. Never batch-update test expectations. Each changed expectation needs individual justification.
5. The 14-15 pre-existing xfail tests (noted in known limitations) must not increase.

**Warning signs:** More than 5 tests break simultaneously after a single change. Test failures in ancilla tracking or controlled variants (these are the most fragile).

**Phase to address:** Every phase. Run the full test suite as a gate for every PR. Phase 1 should establish the "behavioral compatibility" principle.

---

### Pitfall 7: Controlled Variant Derivation Breaks with Multi-Level Compilation

**What goes wrong:** The existing `_derive_controlled_gates` adds one control qubit to every gate in a compiled block. This works because the compiled block is a flat gate list. With multi-level compilation, a "compiled function" might be represented as a call graph node (not expanded to gates). Deriving the controlled variant of a call graph node requires either: (a) expanding it first, then adding controls (losing the call graph structure), or (b) propagating the control qubit through the call graph recursively. Option (b) is correct but complex -- every sub-node must support controlled derivation, and the control qubit must be added to the dependency set of every node.

**Why it happens:** The chess demo uses `@ql.compile(inverse=True)` with controlled variants extensively (factory pattern for move oracles). Grover's oracle uses it via `@ql.grover_oracle` which validates compute-phase-uncompute ordering. Both consumers expect controlled derivation to work transparently.

**How to avoid:**
1. Multi-level compilation must support lazy controlled derivation: when a controlled variant is requested, either derive it at the current compilation level (if the level supports it) or force expansion to flat gates first.
2. The call graph DAG must propagate control qubits through its dependency edges, not just annotate the top-level node.
3. Test: Compile a multi-level function (call graph with sub-calls), derive controlled variant, verify gate-level equivalence with the flat controlled variant.

**Warning signs:** `with qbool:` blocks containing compiled functions produce "controlled variant not available" errors. Grover's oracle validation fails on compiled functions that previously worked.

**Phase to address:** Phase 1 (call graph design must define controlled variant propagation).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Flatten call graph to gate list for every operation | Avoids complex graph algorithms | Defeats the purpose of multi-level compilation -- O(N) expansion on every call | Only during prototyping/Phase 1 as proof-of-concept |
| Skip sparse arrays and always use dense | Simpler C code | Memory regression for large circuits (200+ qubits, 10K+ layers) | For circuits under 64 qubits / 1K layers |
| Copy-paste gate list for controlled variants | Fast to implement | 2x memory per controlled function, stale if original is updated | Never -- use lazy derivation with back-pointer |
| Store merge results in Python dicts | Avoids C changes | Per-gate Python dict overhead (existing: ~320 bytes/gate in Python) scales poorly | For prototype only; merge results should feed into inject_remapped_gates for C-level storage |
| Global opt_flag instead of per-function | Simpler API | Cannot mix compilation levels in the same circuit (e.g., inner function at level 0, outer at level 2) | Never -- per-function is essential for composability |

## Integration Gotchas

Common mistakes when connecting new subsystems to existing infrastructure.

| Integration Point | Common Mistake | Correct Approach |
|-------------------|----------------|------------------|
| inject_remapped_gates (Cython->C boundary) | Calling once per gate in merged sequence (N boundary crossings = N*overhead) | Batch injection: build the full remapped gate array in Cython, pass to a single C function that appends all gates |
| extract_gate_range (C->Python boundary) | Extracting gates from a range that includes merged+unmerged regions | Track merge boundaries explicitly; extract_gate_range should know about merged vs. original layers |
| _get_mode_flags cache key | Forgetting to include opt_flag alongside arithmetic_mode, cla_override, tradeoff_policy | Add opt_flag to the tuple returned by _get_mode_flags() |
| _clear_all_caches (circuit reset hook) | New call graph structures not cleared on ql.circuit() reset | Register call graph and merge caches in the clear hook registry |
| CompiledBlock.__slots__ | Adding new fields to CompiledBlock without updating __slots__ | Add fields AND update all constructors -- __slots__ classes raise AttributeError on uninitialized fields |
| Ancilla tracking with forward call registry | Multi-level merge moves gates between forward calls, breaking LIFO inverse ordering | Merge must preserve forward-inverse pairing as atomic units |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Python-level call graph traversal for every compiled call | Latency increases linearly with graph size | Cache the traversal result; only re-traverse when graph changes | >50 nodes in call graph |
| Dense 2D array for sparse circuits (current: gate_t **sequence[layer][gate]) | Memory proportional to max_layer * max_gates_per_layer even when most entries are empty | Sparse representation: CSR or hash-map-of-layer for circuits with >90% empty layers | >10K layers with <10% occupancy |
| Python dict gate representation in merge logic | 320+ bytes per gate dict; merge creates copies | Use numpy structured arrays or C-level gate buffers for merge operations | >100K gates in merge |
| Rebuilding qubit dependency set on every merge query | O(G) scan per query where G = total gates | Pre-compute and cache per-qubit gate indices during capture | Merge queries on circuits with >50K gates |
| Eager expansion of call graph at every compilation level change | Re-expanding a 10K-gate function for each opt_flag change | Promote cache entries: level 0 -> level 1 -> level 2 incrementally | Functions with >5K gates called at multiple opt levels |
| Layer reallocation in C during bulk merge injection | allocate_more_layer called repeatedly in 128-block increments | Pre-calculate total layers needed from merge result; allocate once | Merging sequences totaling >1K layers |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Call graph DAG:** Often missing control qubit phase kickback in dependency analysis -- verify with superposition inputs, not just computational basis
- [ ] **Sequence merging:** Often missing per-qubit order preservation check -- verify by extracting per-qubit gate subsequence from merged result and comparing to original
- [ ] **Sparse arrays:** Often missing compatibility with circuit_optimizer.c -- verify that optimization passes (OPT_PASS_MERGE, OPT_PASS_CANCEL_INVERSE) work on sparse representation
- [ ] **opt_flag levels:** Often missing interaction with parametric compilation -- verify parametric replay works at each opt_flag level
- [ ] **DOT visualization:** Often missing edge labels for qubit dependencies -- without labels, the graph shows structure but not WHY nodes are ordered
- [ ] **Controlled variants on call graph nodes:** Often missing recursive propagation -- verify controlled variant of a function that calls another compiled function
- [ ] **Cache invalidation:** Often missing ql.circuit() reset for call graph structures -- verify that creating a new circuit clears all multi-level caches
- [ ] **Inverse derivation on merged sequences:** Often missing angle negation consistency after merge reordering -- verify adjoint of merged sequence equals merge of adjoint sequences
- [ ] **Sparse array free_circuit:** Often missing large_control cleanup for gates stored in sparse structure -- verify valgrind shows no leaks

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Incorrect qubit dependency tracking | MEDIUM | Add dependency validation pass that simulates both sequential and DAG-scheduled execution; diff statevectors |
| Merge violates gate ordering | HIGH | Revert to flat gate list (disable merge); fix merge algorithm; add per-qubit ordering assertion |
| Ancilla lifecycle corruption | HIGH | Disable merge for functions with ancillas; fix atomic forward-inverse pairing; re-verify all ancilla tests |
| Parametric topology mismatch after merge | MEDIUM | Pin parametric comparison to pre-merge topology; add topology equivalence check post-merge |
| Cache key collision across opt_flags | LOW | Add opt_flag to cache key tuple; clear all caches; re-run test suite |
| Existing test regression | MEDIUM | Bisect to identify breaking change; verify new behavior with Qiskit; update test expectation with justification |
| Controlled variant fails on call graph | MEDIUM | Fall back to flatten-then-control; add controlled variant support to call graph nodes incrementally |
| Sparse array memory corruption | HIGH | Revert to dense arrays; run valgrind; fix sparse allocation/deallocation; add C-level assertions |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1: Incomplete qubit dependency tracking | Phase 1 (call graph DAG design) | Unit test: two functions sharing only control qubit must be sequentially ordered; statevector comparison with superposition inputs |
| P2: Sequence merge ordering violation | Phase 2 (selective merge) | Post-merge validation: extract per-qubit gate subsequence, compare to original ordering; Qiskit statevector diff |
| P3: Ancilla lifecycle corruption | Phase 1 (call graph design) | Forward-inverse pair atomicity test; statevector check that ancillas return to zero |
| P4: Parametric topology after merge | Phase 2 (merge + parametric interaction) | Parametric cache hit test at each opt_flag level; angle substitution correctness test |
| P5: Cache key explosion | Phase 1 (cache key design) | Test: call function at opt_flag 0, 1, 2 in sequence; verify distinct cache entries and correct gate sequences |
| P6: Existing test regression | Every phase (continuous) | Full 118-test suite as CI gate; no net increase in xfail count; individual justification for any changed expectation |
| P7: Controlled variants on call graph | Phase 1 (call graph design) | Test: controlled variant of multi-level compiled function; gate-level equivalence with flat controlled variant |
| Sparse array C memory safety | Phase 3 (sparse arrays) | valgrind clean run; free_circuit covers sparse paths; allocator stress test at 200+ qubits |
| Cython boundary batch injection | Phase 2 (merge implementation) | Benchmark: merged injection must not exceed 2x single-sequence injection time; no per-gate boundary crossing |
| Dense/sparse transition | Phase 3 (sparse arrays) | Regression test: dense circuit results unchanged when sparse threshold not met; sparse circuits produce identical QASM output |

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Call graph DAG | Treating control qubits as read-only (classical intuition) | All qubits in target+controls are dependencies; no read/write distinction |
| Call graph DAG | Forward-inverse pairs split across graph nodes | Encode forward-inverse as atomic scheduling unit |
| Selective merge | Interleaving gates that share qubits without topological sort | Build per-qubit dependency chains; merge = topological sort of chains |
| Selective merge | Breaking ancilla contiguity | Skip merge for functions with ancilla tracking enabled |
| Sparse arrays | Small circuit regression (sparse overhead > dense for <64 qubits) | Auto-detect: use sparse only when qubit_count * layer_count > threshold |
| Sparse arrays | Incompatibility with circuit_optimizer.c passes | Implement sparse-to-dense conversion for optimizer, or sparse-aware optimizer |
| opt_flag levels | Global flag prevents mixing levels in same circuit | Per-function opt_flag via `@ql.compile(opt_flag=N)` |
| DOT visualization | Graph too large to render for complex call graphs | Hierarchical DOT with cluster subgraphs; limit to N levels of depth |

## Sources

- Direct codebase analysis: `src/quantum_language/compile.py` (1700+ lines, capture-replay architecture)
- Direct codebase analysis: `c_backend/src/circuit_allocations.c` (2D jagged array: `gate_t **sequence[layer][gate]`)
- Direct codebase analysis: `c_backend/include/circuit.h` (circuit_t structure with QUBIT_BLOCK=128, LAYER_BLOCK=128)
- Direct codebase analysis: `src/quantum_language/_core.pyx` (inject_remapped_gates, extract_gate_range -- Cython/C boundary)
- Direct codebase analysis: `tests/test_compile.py` (118 tests covering all compilation scenarios)
- Project documentation: `.planning/PROJECT.md` (v7.0 milestone goals, key decisions, known limitations)
- Prior research: `.planning/research/PITFALLS-COMPILE-DECORATOR.md` (v2.0 pitfalls, still relevant for backward compatibility)
- Quantum computing fundamentals: phase kickback on control qubits makes all qubit interactions bidirectional (HIGH confidence -- textbook physics)

---
*Pitfalls research for: Multi-level compilation infrastructure (v7.0)*
*Researched: 2026-03-05*
