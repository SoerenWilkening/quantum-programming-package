# Project Research Summary

**Project:** Quantum Assembly v7.0 -- Multi-Level Compile Infrastructure
**Domain:** Quantum circuit compilation (call graph DAG, sequence merging, sparse circuit arrays)
**Researched:** 2026-03-05
**Confidence:** HIGH

## Executive Summary

The v7.0 milestone adds multi-level compilation to the existing `@ql.compile` decorator, introducing three capabilities: a call graph DAG that captures program structure without full circuit expansion (opt_flag=1), selective sequence merging that eliminates redundant QFT/IQFT pairs across compiled function boundaries (opt_flag=2), and sparse circuit arrays for large circuits (independent track). The recommended approach is LLVM-style optimization levels -- opt_flag=1 is cheap structural analysis, opt_flag=2 is selective inlining with gate cancellation, and opt_flag=3 is the existing full-expansion behavior relabeled. No major quantum framework (Qiskit, TKET, Cirq, PennyLane) exposes multi-level compilation as a user-facing feature, making this a genuine differentiator.

The stack situation is unusually favorable: zero new core dependencies are needed. rustworkx (already installed, Rust-native DAG library used by Qiskit itself) provides all graph primitives. scipy.sparse (already installed) handles large gate arrays. NumPy bitmasks give O(1) qubit overlap detection. The only new optional dependency is pydot for DOT image rendering. All new code is pure Python in compile.py, with no changes to the C backend or Cython bridge for the DAG and merge features. Sparse circuit arrays are the one exception -- they require C-level modifications to replace the dense `gate_index_of_layer_and_qubits` array with a hash map, but this is an independent track that can ship separately.

The primary risk is silent quantum correctness bugs. Unlike classical compilation, a missed qubit dependency or reordered gate sequence produces a valid-looking circuit that computes the wrong quantum state with no runtime error. The top three pitfalls are: (1) treating control qubits as read-only in dependency analysis (classical intuition that is wrong for quantum -- phase kickback makes all qubit interactions bidirectional), (2) merge operations violating per-qubit gate ordering, and (3) ancilla lifecycle corruption when forward-inverse pairs are split during DAG restructuring. All three are preventable with explicit invariant checks and statevector verification tests against Qiskit simulation.

## Key Findings

### Recommended Stack

Zero new core dependencies. Everything needed is already installed. See `.planning/research/STACK.md` for full analysis.

**Core technologies:**
- **rustworkx 0.17.1** (installed): Call graph DAG via `PyDAG`, topological sort, parallelism detection via `topological_generations()`, cycle prevention -- 10-100x faster than NetworkX, same library Qiskit uses internally
- **scipy.sparse** (installed): `dok_array` for incremental gate capture, `csr_array` for fast row-sliced replay -- used only for Python-level virtual gate lists exceeding 50K gates
- **NumPy uint64 bitmasks** (installed): O(1) qubit overlap detection for merge decisions -- scalar path for <64 virtual qubits (common case), ndarray path for wider circuits
- **pydot >=3.0.0** (NEW, optional): DOT image rendering via `rustworkx.visualization.graphviz_draw()` -- pure Python, lazy-imported, not a hard runtime dependency

**What NOT to add:** NetworkX (slower, redundant with rustworkx), pygraphviz (requires C compiler/SWIG), pandas (massive overhead for gate storage), any new Cython bindings (Python-level is sufficient for DAG traversal).

### Expected Features

See `.planning/research/FEATURES.md` for full analysis including competitor comparison and dependency tree.

**Must have (v7.0 launch -- P1):**
- opt_flag parameter on `@ql.compile` -- the API surface for selecting compilation level
- opt_flag=1: Call graph DAG with qubit overlap edges -- the core new abstraction
- opt_flag=3: Full expansion (current behavior, relabeled) -- backward compatibility
- Call graph node metadata (function name, gate count, qubit set, depth) -- makes DAG actionable
- DOT-format call graph export -- makes DAG visible
- Qubit overlap analysis -- foundation for both merging and parallelism detection

**Should have (v7.x -- P2):**
- opt_flag=2: Selective sequence merging -- the killer feature (QFT/IQFT cancellation across function boundaries)
- Merge cost estimation ("merging f+g saves 847 gates") -- transparency for merge decisions
- Parallelism detection from call graph -- free information from overlap analysis
- Compilation report with per-level stats -- extends existing debug mode

**Defer (v8+ -- P3):**
- Sparse circuit arrays at C level -- independent track, needs careful benchmarking of hash map vs. array indexing crossover
- Cross-function merge chains (A+B+C in one pass) -- needs real-world merge patterns to validate

**Anti-features to avoid:** Automatic opt_flag selection (hides tradeoffs), cross-function global optimization (combinatorial explosion), lazy/deferred circuit construction (changes execution model), custom user-defined merge strategies (backward-compat burden).

### Architecture Approach

The architecture follows a "capture-then-analyze" pattern that preserves the existing stateless C backend. Gates flow through the normal `add_gate()` path during capture, are extracted into `CompiledBlock` objects (already existing), and then registered in a Python-level `CallGraphDAG`. For opt_flag=1, the DAG is informational alongside the fully-expanded circuit. For opt_flag=2, the DAG drives merge decisions, after which a fresh circuit is built from merged blocks via the existing `inject_remapped_gates()` path. See `.planning/research/ARCHITECTURE.md` for full component inventory and data flows.

**Major components:**
1. **CallGraphDAG** (new, Python) -- rustworkx `PyDAG` wrapper with `SequenceNode` entries, qubit overlap edges, topological sort, and DOT export
2. **MergeHeuristic** (new, Python) -- decision logic for which sequence pairs to merge based on qubit overlap ratio and estimated gate reduction
3. **opt_flag routing** (modified, Python) -- `CompiledFunc.__call__()` branches on opt_flag to build DAG (1), merge and rebuild (2), or expand directly (3, existing)
4. **sparse_layer_t** (new, C, deferred) -- open-addressing hash map replacing dense `gate_index_of_layer_and_qubits` for large circuits

**Key architectural decisions:**
- opt_flag=1 does NOT suppress gates from entering the circuit -- it builds the DAG alongside normal expansion (avoids modifying C backend)
- Sparse arrays are Python-level only for v7.0; C-level sparse is deferred to v8+
- Per-gate Cython boundary crossing stays as-is (no batch injection needed for v7.0)
- Merge operates on `CompiledBlock` virtual gate lists, not on the physical circuit

### Critical Pitfalls

See `.planning/research/PITFALLS-COMPILE-INFRASTRUCTURE.md` for all 7 pitfalls with recovery strategies. Top five:

1. **Incomplete qubit dependency tracking** -- Control qubits are NOT read-only in quantum circuits (phase kickback). All qubits in target+controls must be treated as full dependencies. Two functions sharing ANY qubit must be sequentially ordered. Test with superposition inputs, not just computational basis states.

2. **Merge violates gate ordering** -- Interleaving gates from two sequences that share qubits can reorder operations on the same qubit. Must build per-qubit dependency chains and perform topological merge. Post-merge validation: extract per-qubit gate subsequence and compare to original ordering.

3. **Ancilla lifecycle corruption** -- Forward-inverse pairs (`inverse=True` functions) must be treated as atomic scheduling units in the DAG. Never split them. Ancilla qubits must not appear in other nodes between forward and inverse calls.

4. **Parametric topology breaks after merge** -- Merging changes gate ordering, which changes topology signatures. Parametric comparison must happen BEFORE merge on individual blocks, not after.

5. **Breaking 118 existing compile tests** -- New features must be opt-in. Default `@ql.compile` (no new flags) must produce identical gate sequences to v6.1. Never batch-update test expectations.

## Implications for Roadmap

Based on combined research, the v7.0 milestone naturally splits into 5 phases with clear dependency ordering. Sparse circuit arrays (originally in scope) should be deferred to v8+ -- they require C-level changes that are independent of and riskier than the Python-level compilation features.

### Phase 1: opt_flag API + Call Graph DAG Foundation
**Rationale:** Everything depends on this. The opt_flag parameter is the API surface. The call graph DAG is the core data structure. Qubit overlap analysis is needed by both DAG ordering and later merge decisions.
**Delivers:** `@ql.compile(opt_flag=1)` producing a `CallGraphDAG` with nodes (wrapping existing `CompiledBlock`), qubit overlap edges, and topological ordering. opt_flag=3 relabeled as current behavior.
**Addresses:** opt_flag parameter, opt_flag=1 call graph DAG, opt_flag=3 backward compat, qubit overlap analysis, call graph node metadata (all P1 features)
**Avoids:** Pitfall 1 (qubit dependency tracking -- design qubit sets correctly from day one), Pitfall 3 (ancilla atomicity -- encode forward-inverse pairing in DAG design), Pitfall 5 (cache key -- include opt_flag in cache key from start), Pitfall 7 (controlled variants -- define propagation strategy)
**Stack:** rustworkx PyDAG, NumPy bitmasks

### Phase 2: DOT Visualization + Compilation Report
**Rationale:** Once the DAG exists, making it visible is low-cost and high-value. DOT export is trivial string generation. Compilation report extends existing debug mode. Having visualization available before implementing merging makes merge debugging dramatically easier.
**Delivers:** `call_graph.to_dot()` producing valid DOT strings with node labels (function name, gate count, qubit set) and edge labels (shared qubit count). Compilation stats at each opt_flag level. Parallelism detection with color-coding of independent nodes.
**Addresses:** DOT-format export, parallelism detection, compilation report (P1/P2 features)
**Avoids:** Pitfall checklist item "DOT missing edge labels" -- include qubit dependency labels from the start
**Stack:** Pure Python string generation (no pydot needed for DOT text)

### Phase 3: Selective Sequence Merging (opt_flag=2)
**Rationale:** Depends on Phase 1 (DAG with qubit overlaps). This is the highest-complexity, highest-value feature. QFT/IQFT cancellation across function boundaries is the killer differentiator that no other quantum framework offers.
**Delivers:** `@ql.compile(opt_flag=2)` that identifies overlapping-qubit sequence pairs, merges their gate lists, runs existing `_optimize_gate_list()` on the junction, and rebuilds the circuit from merged blocks.
**Addresses:** opt_flag=2 selective merging, merge cost estimation (P2 features)
**Avoids:** Pitfall 2 (gate ordering -- per-qubit dependency chains with topological merge), Pitfall 3 (ancilla corruption -- skip merge for functions with ancilla tracking), Pitfall 4 (parametric topology -- compare topology before merge, not after)
**Stack:** Existing `_optimize_gate_list()`, `_remap_gates()`, `inject_remapped_gates()` -- all reused

### Phase 4: Merge Validation + End-to-End Testing
**Rationale:** After merge implementation, rigorous correctness validation is essential. Quantum compilation bugs are silent -- wrong circuits produce valid-looking but incorrect results. This phase is about proving correctness via Qiskit simulation.
**Delivers:** Statevector comparison tests (merged vs. sequential execution), per-qubit ordering assertions, parametric replay tests at each opt_flag level, full 118-test regression suite passing.
**Addresses:** Pitfall 6 (existing test regression), all "Looks Done But Isn't" checklist items from pitfalls research
**Avoids:** Shipping silently incorrect merge behavior

### Phase 5: Sparse Circuit Arrays (Deferred -- v8+ Candidate)
**Rationale:** Independent of the opt_flag system. Requires C-level modifications (hash map in `circuit_t`, 6 access sites in optimizer.c). High risk of performance regression for small circuits. Should only be pursued when real-world workloads demonstrate memory pressure from the dense `gate_index_of_layer_and_qubits` array.
**Delivers:** Auto-transition from dense to sparse index storage when memory exceeds threshold. Same circuit output, reduced memory for large circuits (2000+ qubits).
**Addresses:** Sparse circuit arrays (P3 feature)
**Avoids:** Anti-pattern of sparse-by-default (hash lookups are 3-5x slower than array indexing for small circuits)
**Stack:** C-level open-addressing hash map with linear probing

### Phase Ordering Rationale

- Phases 1-2-3-4 form a strict dependency chain: opt_flag API before DAG, DAG before visualization, DAG with overlaps before merging, merging before validation.
- Phase 5 is independent: sparse arrays touch only the C backend and can ship in any order relative to Python-level features. Deferring it reduces v7.0 scope and risk.
- Phase 2 (DOT) comes before Phase 3 (merge) deliberately: having visualization available makes merge debugging dramatically easier. Build the debuggability tooling before the complex feature.
- Phase 4 (validation) is a separate phase, not an afterthought: quantum correctness bugs are silent, so a dedicated validation phase with Qiskit simulation ensures merged circuits compute the right quantum states.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Selective Merging):** HIGH complexity. Merge heuristic thresholds (overlap ratio, minimum benefit) need tuning against real QFT arithmetic workloads. The interaction between merging and parametric compilation is subtle. Recommend `/gsd:research-phase` before implementation.
- **Phase 5 (Sparse Arrays):** C-level hash map design, dense-to-sparse transition strategy, and performance crossover benchmarking all need investigation. Recommend `/gsd:research-phase` if this phase is pulled into v7.0.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Call Graph DAG):** Well-documented. rustworkx API is straightforward. Existing `CompiledBlock` provides all needed data. Direct mapping from code analysis to implementation.
- **Phase 2 (DOT Visualization):** Trivial string generation. DOT format is well-specified. No unknowns.
- **Phase 4 (Validation):** Standard testing patterns. Qiskit statevector comparison is established practice in this codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core libraries already installed and verified. Zero new dependencies for core features. Versions confirmed via pip list. |
| Features | HIGH | Classical compiler analogies (LLVM -O levels) well-established. Competitor analysis confirms no existing framework offers user-facing multi-level compilation. Feature dependencies are clear. |
| Architecture | HIGH | Based on direct source analysis of compile.py (1700+ lines), _core.pyx (1011 lines), optimizer.c (217 lines). Integration points precisely identified with line numbers. |
| Pitfalls | HIGH | Based on direct codebase analysis plus quantum physics fundamentals (phase kickback). 118 existing tests provide concrete regression baseline. |

**Overall confidence:** HIGH

### Gaps to Address

- **Merge heuristic thresholds:** The optimal qubit overlap ratio and minimum gate reduction thresholds for merge decisions are not known. Need empirical tuning against real QFT arithmetic circuits (quantum walk adders, Grover's oracle arithmetic). Address during Phase 3 planning.
- **opt_flag=2 circuit rebuild cost:** Merging requires building the circuit twice (capture + rebuild). For large circuits, this doubles construction time. Need to measure whether the gate reduction from merging justifies the rebuild cost. Address with benchmarks during Phase 3 implementation.
- **Controlled variant propagation through call graph:** The exact mechanism for deriving controlled variants of call graph nodes (recursive propagation vs. flatten-then-control) needs design work. Address during Phase 1 detailed design.
- **Sparse array performance crossover:** At what circuit size does hash map lookup become cheaper than dense array allocation? Needs benchmarking on target hardware. Address if Phase 5 is scheduled.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `compile.py`, `_core.pyx`, `circuit.h`, `optimizer.c`, `types.h`, `circuit_allocations.c`
- Verified library versions: rustworkx 0.17.1, scipy 1.17.1, numpy 2.4.2 (via pip list)
- rustworkx DAG API documentation and tutorials
- scipy.sparse array API documentation
- Existing test suite: 118 tests in `test_compile.py`
- Project documentation: `.planning/PROJECT.md` (v7.0 milestone goals, key decisions)

### Secondary (MEDIUM confidence)
- Qiskit DAGCircuit representation (DeepWiki) -- internal IR patterns
- TKET compilation and box hierarchy -- subroutine handling patterns
- MLIR quantum circuit transformations (arXiv:2112.10677) -- multi-level IR concepts
- LLVM optimization levels -- analogy for opt_flag semantics
- Quantum arithmetic with QFT (arXiv:1411.5949) -- Draper adder QFT/IQFT structure

### Tertiary (LOW confidence)
- Sparse tensor simulation (arXiv:2602.04011) -- sparse representation patterns, needs validation for circuit index storage specifically
- Merge heuristic thresholds -- no empirical data yet, needs tuning during implementation

---
*Research completed: 2026-03-05*
*Ready for roadmap: yes*
