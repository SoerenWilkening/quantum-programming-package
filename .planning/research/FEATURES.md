# Feature Research

**Domain:** Multi-level quantum circuit compilation infrastructure
**Researched:** 2026-03-05
**Confidence:** HIGH (classical compiler analogies well-established; quantum-specific patterns verified via Qiskit/TKET/MLIR literature)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any multi-level compilation system must have. Without these, the opt_flag system feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| opt_flag=1: Call graph DAG (no placement) | Core promise of multi-level compilation. Users need to see program structure without paying full expansion cost. LLVM -O0 analogy. | MEDIUM | Captures individual instruction sequences per `@ql.compile` call, builds DAG with edges for qubit overlap and call ordering. Must integrate with existing `CompiledBlock` capture. |
| opt_flag=3: Full expansion (current behavior) | Backward compatibility. Existing users already depend on this. Breaking it is a non-starter. | LOW | Already implemented as current default. Relabel as opt_flag=3 and ensure all existing tests pass unchanged. |
| Qubit overlap analysis in call graph | Without knowing which sequences share qubits, the DAG is just a call tree -- useless for optimization decisions. This is what makes it a *dependency* graph, not just a *call* graph. | MEDIUM | For each pair of sequences, compute intersection of qubit sets. Store as edge weight. O(n^2) in number of sequences but n is typically small (tens, not thousands). |
| Call graph node metadata | Each node needs: function name, gate count, qubit set, depth, ancilla count. Without metadata, the graph is not actionable. | LOW | Already available from `CompiledBlock` attributes (gates, total_virtual_qubits, param_qubit_ranges, internal_qubit_count). Just expose them. |
| opt_flag parameter on @ql.compile | Users need a clean API to select compilation level. Must be keyword argument with sensible default (1 = call graph only). | LOW | Add `opt_flag=1` parameter to `@ql.compile` decorator and `CompiledFunc.__init__`. Route to different code paths in `__call__`. |
| DOT-format call graph export | DOT is the universal standard for graph visualization. Graphviz renders it. Every CI/CD pipeline can consume it. Without DOT output, the call graph is invisible. | LOW | Pure Python string generation. Nodes = compiled function calls, edges = qubit dependencies. Use `graphviz` package for rendering or raw DOT string for zero-dependency mode. |

### Differentiators (Competitive Advantage)

Features that set this apart from existing quantum frameworks. Qiskit, Cirq, TKET, and PennyLane do not offer user-facing multi-level compilation with selective merging.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| opt_flag=2: Selective sequence merging | The killer feature. No quantum framework offers user-accessible selective inlining with domain-specific optimization (QFT/IQFT cancellation). LLVM does function inlining at -O2; this is the quantum equivalent. Merging `a += b; a += c` eliminates redundant QFT/IQFT pairs, which is a massive gate count reduction for QFT arithmetic. | HIGH | Must identify mergeable sequence pairs (heavy qubit overlap), inline their gate lists, then run `_optimize_gate_list` on the combined sequence. The QFT/IQFT cancellation already works via inverse pair cancellation in the existing optimizer -- the challenge is deciding *which* sequences to merge and handling multi-sequence chains. |
| Parallelism detection from call graph | DAG reveals which sequences can execute simultaneously (no shared qubits = independent). This is free information from the call graph that no other framework surfaces at the user level. | LOW | Sequences with zero qubit overlap are independent. Color-code in DOT output. Report parallelism factor (max independent set size). |
| Sparse circuit arrays (memory-adaptive) | Current circuit storage is dense: `gate_t **sequence[layer][gates_per_layer]` and `gate_index_of_layer_and_qubits[layer][qubit]` allocate for every layer x qubit combination. For 1000+ qubit circuits with 300K layers, this is GB of mostly-zero memory. Sparse storage makes large programs feasible. | HIGH | Requires C-level changes to `circuit_t`. Replace dense `gate_index_of_layer_and_qubits` with hash map or skip list. Must not regress performance for small circuits (< 200 qubits). Auto opt-in via memory monitoring (e.g., when projected allocation exceeds threshold). |
| Merge cost estimation | Before merging, estimate gate reduction from QFT/IQFT cancellation. Users see "merging f+g saves 847 gates (23%)" in debug output. Informed decision-making. | MEDIUM | Simulate merge by concatenating gate lists and running `_optimize_gate_list` in dry-run mode. Compare before/after gate counts. |
| Compilation report with per-level stats | At each opt level, report: total gates, total depth, total qubits, number of sequences, merge opportunities found, parallelism factor. Builds on existing debug mode. | LOW | Extend existing `CompiledFunc` debug reporting. Add structured dict output alongside print. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automatic opt_flag selection | "Just pick the best level for me" | Optimal level depends on user intent (debugging vs. deployment vs. resource estimation). Auto-selection hides important tradeoffs and makes behavior unpredictable. | Default to opt_flag=1 (cheapest). Document when to use each level. Print suggestion in debug mode: "opt_flag=2 would save ~N gates". |
| Cross-function optimization (global opt) | "Merge all functions across the entire program" | Combinatorial explosion. N functions = O(2^N) merge candidates. Destroys function boundaries, making debugging impossible. Classical compilers learned this lesson (whole-program optimization is a separate, expensive mode). | Merge only adjacent calls on overlapping qubits. Preserve function boundaries. Let users explicitly compose functions if they want global optimization. |
| Lazy/deferred circuit construction | "Don't build the circuit until I ask for it" | Changes the fundamental execution model. Current architecture: operations immediately generate gates. Deferred construction requires a completely different tracing/IR approach (like JAX's jit). Massive architectural change. | opt_flag=1 already defers *placement* while still capturing sequences. This gives 80% of the benefit without changing the execution model. |
| Incremental/partial recompilation | "Only recompile the parts I changed" | Requires dependency tracking between Python source changes and compiled sequences. Extremely complex for a framework that uses runtime tracing (not AST analysis). Classical compilers have build systems; quantum frameworks don't. | Cache invalidation on `ql.circuit()` already works. Per-function cache keys already include mode flags. This is sufficient for interactive use. |
| Custom merge strategies (user-defined) | "Let me write my own merge rules" | Exposes internal gate representation. Creates backward-compatibility burden. Users will write fragile merge logic that breaks on gate format changes. | Provide merge heuristics that cover 95% of cases (QFT/IQFT cancellation, adjacent gate merging). Expose merge cost estimation for visibility. |

## Feature Dependencies

```
opt_flag parameter (API)
    |
    +-- opt_flag=1: Call graph DAG
    |       |
    |       +-- Qubit overlap analysis
    |       |       |
    |       |       +-- Parallelism detection
    |       |
    |       +-- Call graph node metadata
    |       |       |
    |       |       +-- DOT-format export
    |       |       |
    |       |       +-- Compilation report
    |       |
    |       +-- opt_flag=2: Selective merging
    |               |
    |               +-- requires: Qubit overlap analysis
    |               |
    |               +-- Merge cost estimation
    |
    +-- opt_flag=3: Full expansion (existing, no new deps)

Sparse circuit arrays (independent track)
    +-- Memory monitoring (trigger mechanism)
    +-- C-level hash map for gate_index_of_layer_and_qubits
    +-- Python-level auto opt-in logic
```

### Dependency Notes

- **opt_flag=2 requires opt_flag=1:** Cannot merge sequences without first building the call graph and computing qubit overlaps. The merge decision depends on DAG structure.
- **DOT export requires node metadata:** Graph visualization needs function names, gate counts, qubit sets to produce useful output.
- **Parallelism detection requires qubit overlap analysis:** Independence = zero overlap. Same computation, different interpretation.
- **Sparse arrays are independent:** Can be implemented and shipped separately from the opt_flag system. No interaction with call graph features.
- **Merge cost estimation enhances opt_flag=2:** Not strictly required for merging, but makes merge decisions transparent and debuggable.
- **opt_flag=3 conflicts with nothing:** It is the existing behavior, simply relabeled. All other features compose with it.

## MVP Definition

### Launch With (v7.0 Core)

Minimum viable multi-level compilation. Validates the concept and provides immediate value.

- [ ] opt_flag parameter on @ql.compile (API surface) -- enables the feature
- [ ] opt_flag=1: Call graph DAG with qubit overlap edges -- the core abstraction
- [ ] opt_flag=3: Full expansion (current behavior, relabeled) -- backward compatibility
- [ ] Call graph node metadata (function name, gate count, qubit set, depth) -- makes DAG useful
- [ ] DOT-format export -- makes DAG visible
- [ ] Qubit overlap analysis -- foundation for merging and parallelism

### Add After Validation (v7.x)

Features to add once the call graph DAG is working and users can see their program structure.

- [ ] opt_flag=2: Selective sequence merging -- add when call graph proves useful and merge heuristics are validated
- [ ] Merge cost estimation -- add alongside opt_flag=2 for transparency
- [ ] Parallelism detection -- low-cost addition once overlap analysis exists
- [ ] Compilation report with per-level stats -- extend debug mode

### Future Consideration (v8+)

Features to defer until multi-level compilation is proven.

- [ ] Sparse circuit arrays -- independent track, driven by memory pressure in real workloads. Needs C-level changes with careful performance testing.
- [ ] Cross-function merge chains (A+B+C merged in one pass) -- needs real-world merge patterns to validate heuristics

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| opt_flag parameter | HIGH | LOW | P1 |
| opt_flag=1 call graph DAG | HIGH | MEDIUM | P1 |
| opt_flag=3 full expansion | HIGH (backward compat) | LOW | P1 |
| Qubit overlap analysis | HIGH | MEDIUM | P1 |
| Call graph node metadata | HIGH | LOW | P1 |
| DOT-format export | MEDIUM | LOW | P1 |
| opt_flag=2 selective merging | HIGH | HIGH | P2 |
| Merge cost estimation | MEDIUM | MEDIUM | P2 |
| Parallelism detection | MEDIUM | LOW | P2 |
| Compilation report | MEDIUM | LOW | P2 |
| Sparse circuit arrays | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v7.0 launch (call graph + visualization)
- P2: Should have, add in v7.x (merging + analysis)
- P3: Nice to have, needs separate investigation (sparse storage)

## Competitor Feature Analysis

| Feature | Qiskit | TKET (pytket) | Cirq | This Project |
|---------|--------|---------------|------|--------------|
| DAG representation | DAGCircuit (internal to transpiler, not user-facing as compilation levels) | CompilationUnit with box hierarchy (subroutines are opaque boxes) | Moment-based (no explicit DAG) | User-facing call graph DAG with qubit overlap, opt_flag selects level |
| Optimization levels | 0-3 (transpiler passes, not compilation levels) | SequencePass chains (user-defined) | Optimizers (separate from circuit construction) | opt_flag=1/2/3 maps to call-graph/merge/expand |
| Selective inlining | Unrolling passes (all-or-nothing per gate type) | Box decomposition (explicit, not selective) | No equivalent | Selective merging based on qubit overlap heuristic |
| QFT/IQFT cancellation | Not at subroutine level | Not at subroutine level | Not at subroutine level | Existing `_optimize_gate_list` handles inverse pair cancellation; opt_flag=2 enables cross-sequence cancellation |
| Visualization | DAG drawing (matplotlib, internal) | Circuit rendering (not call graph) | SVG circuit diagrams | DOT-format call graph with qubit overlap edges |
| Sparse storage | Rust-based circuit (internal optimization) | Implicit via box hierarchy | No special sparse mode | Explicit sparse circuit arrays with auto opt-in |

**Key competitive insight:** No major quantum framework exposes multi-level compilation as a user-facing feature. They all have internal IRs (Qiskit's DAGCircuit, TKET's boxes), but users cannot choose "give me just the call graph" or "merge only these sequences." This project's opt_flag approach is genuinely novel in the quantum tooling space.

**Classical compiler analogy (LLVM):** LLVM's -O0/-O1/-O2/-O3 is the closest analogy. -O0 = no optimization (opt_flag=1, just structure). -O2 = inlining + aggressive passes (opt_flag=2, selective merging). -O3 = full optimization (opt_flag=3, full expansion). The key difference: classical compilers inline for performance; quantum compilers merge for gate cancellation. The optimization target is different (gate count/depth vs. instruction throughput) but the architecture is the same.

## Detailed Feature Specifications

### opt_flag=1: Call Graph DAG

**What it produces:** A Python object (e.g., `CallGraph`) containing:
- Nodes: one per `@ql.compile` function invocation, storing the `CompiledBlock` (gate list, qubit mapping, metadata)
- Edges: directed edges for temporal ordering, weighted by qubit overlap count
- No gates placed into the shared circuit

**How it integrates with existing code:**
- During `CompiledFunc.__call__`, instead of calling `inject_remapped_gates`, store the `CompiledBlock` and qubit mapping in the `CallGraph`
- The `CompiledBlock` capture path stays identical (same `extract_gate_range`, same `_build_virtual_mapping`, same `_optimize_gate_list`)
- Call graph is attached to the circuit or returned from a new `ql.call_graph()` API

**Depends on existing infrastructure:**
- `CompiledBlock` (stores gate sequences) -- already exists
- `_build_virtual_mapping` (virtualizes qubit indices) -- already exists
- `extract_gate_range` (captures gates from circuit) -- already exists
- Cache key with mode flags (`_get_mode_flags`) -- already exists

### opt_flag=2: Selective Sequence Merging

**What it produces:** Multiple smaller optimized circuits (or a single circuit with merged sequences where beneficial).

**Merge heuristic:** For adjacent calls f(a) and g(a) where a is the same qint:
1. Compute qubit overlap between f's gate set and g's gate set
2. If overlap exceeds threshold (e.g., > 50% of total qubits), merge candidate
3. Concatenate gate lists, run `_optimize_gate_list` on combined list
4. If gate reduction exceeds minimum threshold (e.g., > 10%), accept merge

**QFT/IQFT cancellation specifics:** When QFT addition is used (`a += b; a += c`), the sequence is:
1. QFT(a), phase rotations for b, IQFT(a), QFT(a), phase rotations for c, IQFT(a)
2. The adjacent IQFT(a)-QFT(a) pair cancels (they are inverses)
3. Merged: QFT(a), phase rotations for b, phase rotations for c, IQFT(a)
4. Existing `_optimize_gate_list` already handles this via `_gates_cancel` for adjacent inverse pairs

**This already works** at the gate level within a single `CompiledBlock`. The new capability is cross-block merging: detecting that two separate compiled function calls can be merged.

### Sparse Circuit Arrays

**Problem:** The C-level `circuit_t` uses dense arrays:
- `gate_index_of_layer_and_qubits[layer][qubit]` -- O(layers * qubits) memory
- `occupied_layers_of_qubit[qubit][index]` -- grows with circuit depth per qubit
- For a 1000-qubit, 100K-layer circuit: 100M entries in gate_index alone

**Approach:** Replace `gate_index_of_layer_and_qubits` with a hash map keyed by `(layer, qubit)`. Only store entries where a gate exists. For typical quantum circuits, occupancy is < 5% (most qubits are idle at most layers).

**Auto opt-in trigger:** Monitor `allocated_layer * allocated_qubits * sizeof(int)` during `allocate_more_layer`/`allocate_more_qubits`. If projected allocation exceeds threshold (e.g., 100MB), switch to sparse representation.

**Risk:** Hash map lookup is slower than array indexing for small circuits. Must benchmark crossover point carefully. Consider: keep dense representation for < 500 qubits, auto-switch to sparse above that.

## Sources

- [Qiskit DAGCircuit representation](https://deepwiki.com/Qiskit/qiskit/3.3-dag-circuit-representation) -- DAG as internal IR, optimization levels 0-3
- [TKET compilation and box hierarchy](https://docs.quantinuum.com/tket/user-guide/manual/manual_compiler.html) -- CompilationUnit, subroutine boxes, optimization passes
- [MLIR quantum circuit transformations](https://arxiv.org/abs/2112.10677) -- Multi-level IR for quantum compilation, pattern rewrite passes
- [QIRO: SSA-based quantum IR](https://dl.acm.org/doi/10.1145/3491247) -- Exposes data dependencies for optimization
- [Quantum arithmetic with QFT](https://arxiv.org/pdf/1411.5949) -- Draper adder, QFT/IQFT structure that enables cancellation
- [LLVM optimization levels](https://llvm.org/doxygen/classllvm_1_1OptimizationLevel.html) -- O0-O3 analogy for compilation levels
- [Graphviz DOT language](https://graphviz.readthedocs.io/en/stable/manual.html) -- Standard graph visualization format
- [Sparse tensor simulation for quantum circuits](https://arxiv.org/html/2602.04011v1) -- Sparse representations reduce memory for large circuits
- [Quantum circuit optimization survey](https://www.mdpi.com/2624-960X/7/1/2) -- Current trends in circuit optimization

---
*Feature research for: Multi-level quantum circuit compilation infrastructure*
*Researched: 2026-03-05*
