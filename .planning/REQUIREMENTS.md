# Requirements: Quantum Assembly

**Defined:** 2026-03-05
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v7.0 Requirements

Requirements for multi-level compile infrastructure. Each maps to roadmap phases.

### Compilation API

- [x] **CAPI-01**: User can set `@ql.compile(opt=1)` to generate standalone sequences with call graph DAG (default)
- [x] **CAPI-02**: User can set `@ql.compile(opt=2)` to selectively merge overlapping-qubit sequences
- [x] **CAPI-03**: User can set `@ql.compile(opt=3)` for full circuit expansion (current behavior, backward compatible)
- [x] **CAPI-04**: Existing 106+ compile tests pass unchanged when opt=3 is used

### Call Graph

- [x] **CGRAPH-01**: Call graph DAG built from sequence calls with qubit sets per node
- [x] **CGRAPH-02**: Parallel sequences (disjoint qubit sets) identified as concurrent groups
- [x] **CGRAPH-03**: Weighted qubit overlap edges between dependent sequences
- [x] **CGRAPH-04**: Precise gate count, depth, qubit count, and T-count extractable per node from call graph
- [x] **CGRAPH-05**: Aggregate totals (gates, depth, T-count) computed across full call graph without building circuit

### Visualization

- [x] **VIS-01**: User can export call graph as DOT string via API (e.g., `ql.compile_graph()`)
- [x] **VIS-02**: Compilation report showing per-node stats (gate count, depth, qubit set, parallel group)

### Sequence Merging

- [x] **MERGE-01**: Overlapping-qubit sequences automatically identified as merge candidates
- [x] **MERGE-02**: Merged sequences preserve correct per-qubit gate ordering
- [x] **MERGE-03**: Cross-boundary optimization (e.g., QFT/IQFT cancellation between adjacent sequences)
- [ ] **MERGE-04**: Merged result verified equivalent to sequential execution via Qiskit simulation

## Future Requirements

### Sparse Circuit (v8.0)

- **SPARSE-01**: Auto dense->sparse transition for gate_index_of_layer_and_qubits above memory threshold
- **SPARSE-02**: Transparent to Cython layer -- no changes to inject_remapped_gates or extract_gate_range
- **SPARSE-03**: Small circuits retain dense arrays with no performance regression

### Advanced Compilation

- **ADV-01**: Resource estimation for compiled functions
- **ADV-02**: Serialization of compiled functions to disk
- **ADV-03**: Compiled function composition

## Out of Scope

| Feature | Reason |
|---------|--------|
| Sparse circuit arrays | Deferred to v8.0 -- independent C-level track, needs benchmarking |
| PIL-based graph visualization | DOT format sufficient -- external Graphviz tools handle rendering |
| Automatic opt_flag selection | User controls compilation level explicitly |
| Modifying C backend for DAG | Call graph is Python-level overlay on existing CompiledBlock objects |
| Changing Cython boundary | inject_remapped_gates and extract_gate_range remain unchanged |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CAPI-01 | Phase 107 | Complete |
| CAPI-02 | Phase 109 | Complete |
| CAPI-03 | Phase 107 | Complete |
| CAPI-04 | Phase 107 | Complete |
| CGRAPH-01 | Phase 107 | Complete |
| CGRAPH-02 | Phase 107 | Complete |
| CGRAPH-03 | Phase 107 | Complete |
| CGRAPH-04 | Phase 108 | Complete |
| CGRAPH-05 | Phase 108 | Complete |
| VIS-01 | Phase 108 | Complete |
| VIS-02 | Phase 108 | Complete |
| MERGE-01 | Phase 109 | Complete |
| MERGE-02 | Phase 109 | Complete |
| MERGE-03 | Phase 109 | Complete |
| MERGE-04 | Phase 110 | Pending |

**Coverage:**
- v7.0 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-03-05*
*Last updated: 2026-03-05 after roadmap creation (15/15 mapped)*
