# Requirements: Quantum Assembly

**Defined:** 2026-02-26
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v6.0 Requirements

Requirements for quantum walk primitives (Montanaro 2015 backtracking speedup). Each maps to roadmap phases.

### Tree Encoding

- [x] **TREE-01**: QuantumBacktrackingTree class with one-hot height register (max_depth+1 qubits) and QuantumArray branch registers (one entry per depth level)
- [x] **TREE-02**: Resource estimator that computes exact qubit count for given tree parameters and fails fast before circuit construction
- [x] **TREE-03**: Node initialization (root state preparation with correct height qubit)

### Predicate Interface

- [x] **PRED-01**: Accept/reject predicate interface — user provides callable returning two qbools (is_accept, is_reject) for a given tree state
- [x] **PRED-02**: Predicate mutual exclusion validation (accept and reject cannot both be true)
- [x] **PRED-03**: Predicate uncomputation managed below LIFO scope tracking (raw allocation or @ql.compile inverse pattern)

### Local Diffusion

- [ ] **DIFF-01**: D_x local diffusion operator for uniform branching with correct amplitude angle phi = 2*arctan(sqrt(d))
- [ ] **DIFF-02**: Root node diffusion with separate phi_root formula (different amplitude weighting per Montanaro section 2)
- [ ] **DIFF-03**: Statevector tests verifying |psi_x> amplitudes match 1/sqrt(d(x)+1) tolerance
- [ ] **DIFF-04**: Variable branching support — count valid children per node via predicate evaluation, controlled Ry rotation based on child count d(x)

### Walk Operators

- [ ] **WALK-01**: R_A operator applying local diffusions at even-depth nodes via height-parity control
- [ ] **WALK-02**: R_B operator applying local diffusions at odd-depth nodes (plus root reflection) via height-parity control
- [ ] **WALK-03**: Walk step U = R_B * R_A composed as single operation
- [ ] **WALK-04**: Walk step wrapped in @ql.compile for caching and controlled variant derivation
- [ ] **WALK-05**: Qubit disjointness test confirming R_A and R_B have zero qubit-index overlap

### Detection

- [ ] **DET-01**: Iterative power-method detection algorithm (apply walk step powers, measure, threshold probability > 3/8)
- [ ] **DET-02**: Demo on small SAT instance (binary tree depth 2-3, within 17-qubit budget)
- [ ] **DET-03**: Qiskit statevector verification confirming detection probability on known-solution and no-solution instances

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Public API

- **API-01**: `ql.quantum_walk()` / `ql.detect_solution()` public API with WalkResult type
- **API-02**: `__init__.py` exports for quantum walk module

### Solution Finding

- **FIND-01**: Solution finding via hybrid classical-quantum Algorithm 2 (recursive subtree detection)
- **FIND-02**: Solution extraction returning actual variable assignments

### Advanced Walk

- **ADV-WALK-01**: Subspace optimization (halves circuit depth by allowing reject on non-algorithmic states)
- **ADV-WALK-02**: General graph quantum walks (non-tree structures)
- **ADV-WALK-03**: QPE-based detection with formal precision guarantees
- **ADV-WALK-04**: CSP-to-predicate compiler (auto CNF to accept/reject)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Continuous-time quantum walk (CTQW) | Incompatible mathematical framework requiring Hamiltonian simulation |
| IQAE reuse for detection | IQAE convergence assumes Grover operator structure; walk eigenvalue analysis is different |
| QPE with arbitrary precision | Each precision qubit costs one register qubit under the 17-qubit ceiling |
| Fault-tolerant walk operators (Clifford+T) | Need correct operators before optimizing them |
| General graph walks | Fundamentally different framework; separate future module |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TREE-01 | Phase 97 | Complete |
| TREE-02 | Phase 97 | Complete |
| TREE-03 | Phase 97 | Complete |
| PRED-01 | Phase 97 | Complete |
| PRED-02 | Phase 97 | Complete |
| PRED-03 | Phase 97 | Complete |
| DIFF-01 | Phase 98 | Pending |
| DIFF-02 | Phase 98 | Pending |
| DIFF-03 | Phase 98 | Pending |
| DIFF-04 | Phase 100 | Pending |
| WALK-01 | Phase 99 | Pending |
| WALK-02 | Phase 99 | Pending |
| WALK-03 | Phase 99 | Pending |
| WALK-04 | Phase 99 | Pending |
| WALK-05 | Phase 99 | Pending |
| DET-01 | Phase 101 | Pending |
| DET-02 | Phase 101 | Pending |
| DET-03 | Phase 101 | Pending |

**Coverage:**
- v6.0 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-02-26*
*Last updated: 2026-03-02 -- Phase 97 complete (TREE-01, TREE-02, TREE-03, PRED-01, PRED-02, PRED-03)*
