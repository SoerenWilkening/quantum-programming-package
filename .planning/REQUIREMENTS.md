# Requirements: Quantum Assembly v8.0

**Defined:** 2026-03-08
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v8.0 Requirements

Requirements for the Quantum Chess Walk Rewrite milestone. The chess walk serves as a demonstration of the framework's expressiveness — all predicates and logic use standard `quantum_language` constructs (`with qbool:`, operator overloading, `@ql.compile`, `ql.array`).

### Quantum Predicates

- [x] **PRED-01**: Quantum piece-exists predicate checks whether a specific piece type occupies a source square in superposition using `with` conditional and qarray element access
- [x] **PRED-02**: Quantum no-friendly-capture predicate rejects moves where target square is occupied by same-color piece, using `with` conditional on board qarray elements
- [x] **PRED-03**: Quantum check detection predicate verifies king is not in check after a move using pre-computed attack tables (knight L-shapes + king adjacency) evaluated via `with` conditionals on board qarray
- [ ] **PRED-04**: Combined move legality predicate composes piece-exists, no-friendly-capture, and check detection using standard `with qbool:` conditional nesting and boolean operators
- [x] **PRED-05**: All predicates use `@ql.compile(inverse=True)` for automatic ancilla uncomputation and compiled replay

### Walk Infrastructure

- [x] **WALK-01**: All-moves enumeration table precomputes every geometrically possible (piece_type, src, dst) triple for knights (8 per square) and kings (8 per square)
- [ ] **WALK-02**: Rewritten evaluate_children calls quantum legality predicate per move candidate instead of trivial always-valid check
- [x] **WALK-03**: Diffusion operator redesigned with arithmetic counting circuit (sum validity bits into count register) replacing O(2^d_max) itertools.combinations enumeration
- [ ] **WALK-04**: Rewritten chess_walk.py integrates quantum predicates, all-moves enumeration, and redesigned diffusion into end-to-end walk step U = R_B * R_A
- [ ] **WALK-05**: Demo serves as showcase of the framework — all quantum logic expressed via standard ql constructs (with, operators, @ql.compile), no raw gate emission for application logic

### Compile Infrastructure

- [x] **COMP-01**: compile.py qubit_set construction uses numpy operations (np.unique/np.concatenate) replacing Python set.update() loops
- [x] **COMP-02**: call_graph.py DAGNode overlap computation uses numpy arrays (np.intersect1d) alongside frozenset for backward compatibility
- [x] **COMP-03**: Profiling baseline established measuring compile performance before/after numpy migration on real workloads

## Future Requirements

Deferred to future milestones.

### Extended Piece Types

- **PIECE-01**: Sliding piece move generation (bishops, rooks, queens) with ray-tracing circuits
- **PIECE-02**: Special move rules (castling, en passant, pawn promotion)

### Walk Enhancements

- **WADV-01**: Compiled predicate caching for amortized cost across walk iterations
- **WADV-02**: Quantum walk public API (ql.quantum_walk / ql.detect_solution)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Sliding pieces (B/R/Q) | Ray-tracing circuits are significantly more complex; knights + kings sufficient for demo |
| Full chess rules | Castling, en passant, promotion are scope explosion; not needed for walk demo |
| Google Quantum Chess approach | Measurement-based, incompatible with Montanaro reversible walk operators |
| python-chess integration | Classical library, cannot evaluate superposition states |
| Raw gate emission for predicates | Defeats purpose of framework demo — must use with/operators/@ql.compile |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRED-01 | Phase 114 | Complete |
| PRED-02 | Phase 114 | Complete |
| PRED-03 | Phase 115 | Complete |
| PRED-04 | Phase 115 | Pending |
| PRED-05 | Phase 114 | Complete |
| WALK-01 | Phase 113 | Complete |
| WALK-02 | Phase 116 | Pending |
| WALK-03 | Phase 113 | Complete |
| WALK-04 | Phase 116 | Pending |
| WALK-05 | Phase 116 | Pending |
| COMP-01 | Phase 112 | Complete |
| COMP-02 | Phase 112 | Complete |
| COMP-03 | Phase 112 | Complete |

**Coverage:**
- v8.0 requirements: 13 total
- Mapped to phases: 13/13
- Unmapped: 0

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-08 after roadmap creation*
