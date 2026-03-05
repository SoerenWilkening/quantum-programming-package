# Requirements: Quantum Assembly

**Defined:** 2026-03-05
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v7.0 Requirements

Requirements for multi-level compile infrastructure. Each maps to roadmap phases.

### Compilation API

- [ ] **CAPI-01**: User can set `@ql.compile(opt=1)` to generate standalone sequences with call graph DAG (default)
- [ ] **CAPI-02**: User can set `@ql.compile(opt=2)` to selectively merge overlapping-qubit sequences
- [ ] **CAPI-03**: User can set `@ql.compile(opt=3)` for full circuit expansion (current behavior, backward compatible)
- [ ] **CAPI-04**: Existing 106+ compile tests pass unchanged when opt=3 is used

### Call Graph

- [ ] **CGRAPH-01**: Call graph DAG built from sequence calls with qubit sets per node
- [ ] **CGRAPH-02**: Parallel sequences (disjoint qubit sets) identified as concurrent groups
- [ ] **CGRAPH-03**: Weighted qubit overlap edges between dependent sequences
- [ ] **CGRAPH-04**: Precise gate count, depth, qubit count, and T-count extractable per node from call graph
- [ ] **CGRAPH-05**: Aggregate totals (gates, depth, T-count) computed across full call graph without building circuit

### Visualization

- [ ] **VIS-01**: User can export call graph as DOT string via API (e.g., `ql.compile_graph()`)
- [ ] **VIS-02**: Compilation report showing per-node stats (gate count, depth, qubit set, parallel group)

### Sequence Merging

- [ ] **MERGE-01**: Overlapping-qubit sequences automatically identified as merge candidates
- [ ] **MERGE-02**: Merged sequences preserve correct per-qubit gate ordering
- [ ] **MERGE-03**: Cross-boundary optimization (e.g., QFT/IQFT cancellation between adjacent sequences)
- [ ] **MERGE-04**: Merged result verified equivalent to sequential execution via Qiskit simulation

## Future Requirements

### Sparse Circuit (v8.0)

- **SPARSE-01**: Auto dense→sparse transition for gate_index_of_layer_and_qubits above memory threshold
- **SPARSE-02**: Transparent to Cython layer — no changes to inject_remapped_gates or extract_gate_range
- **SPARSE-03**: Small circuits retain dense arrays with no performance regression

### Advanced Compilation

- **ADV-01**: Resource estimation for compiled functions
- **ADV-02**: Serialization of compiled functions to disk
- **ADV-03**: Compiled function composition

## Out of Scope

| Feature | Reason |
|---------|--------|
| Sparse circuit arrays | Deferred to v8.0 — independent C-level track, needs benchmarking |
| PIL-based graph visualization | DOT format sufficient — external Graphviz tools handle rendering |
| Automatic opt_flag selection | User controls compilation level explicitly |
| Modifying C backend for DAG | Call graph is Python-level overlay on existing CompiledBlock objects |
| Changing Cython boundary | inject_remapped_gates and extract_gate_range remain unchanged |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAPI-01 | — | Pending |
| CAPI-02 | — | Pending |
| CAPI-03 | — | Pending |
| CAPI-04 | — | Pending |
| CGRAPH-01 | — | Pending |
| CGRAPH-02 | — | Pending |
| CGRAPH-03 | — | Pending |
| CGRAPH-04 | — | Pending |
| CGRAPH-05 | — | Pending |
| VIS-01 | — | Pending |
| VIS-02 | — | Pending |
| MERGE-01 | — | Pending |
| MERGE-02 | — | Pending |
| MERGE-03 | — | Pending |
| MERGE-04 | — | Pending |

**Coverage:**
- v7.0 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15 ⚠️

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after initial definition*
