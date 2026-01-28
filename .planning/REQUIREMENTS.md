# Requirements: Quantum Assembly

**Defined:** 2026-01-28
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.2 Requirements

Requirements for automatic uncomputation milestone. Each maps to roadmap phases.

### Dependency Tracking

- [x] **TRACK-01**: Track parent→child dependencies when qbool operations create intermediate results
- [x] **TRACK-02**: Track dependencies from qint comparison results (>, <, ==, etc.)
- [x] **TRACK-03**: Single ownership model prevents circular reference memory leaks
- [x] **TRACK-04**: Layer-aware dependency tracking respects existing circuit structure

### Uncomputation Core

- [x] **UNCOMP-01**: Generate reverse gates (adjoints) for all supported gate types
- [x] **UNCOMP-02**: Cascade uncomputation through dependency graph when final qbool is uncomputed
- [x] **UNCOMP-03**: Reverse order (LIFO) cleanup ensures correct uncomputation sequence
- [x] **UNCOMP-04**: Gate-type-specific inversion handles multi-controlled gates and phase gates correctly

### Scope Integration

- [x] **SCOPE-01**: Uncompute temporaries automatically when `with` block exits
- [x] **SCOPE-02**: Uncompute when qbool is destroyed or goes out of scope
- [ ] **SCOPE-03**: Explicit `.keep()` method allows opt-out of automatic uncomputation
- [x] **SCOPE-04**: Scope-aware tracking handles nested `with` statements correctly

### Uncomputation Modes

- [ ] **MODE-01**: Default lazy mode keeps intermediates until final qbool is uncomputed
- [ ] **MODE-02**: Qubit-saving eager mode (`ql.option("qubit_saving")`) uncomputes intermediates immediately
- [ ] **MODE-03**: Per-circuit mode switching allows different strategies in same program

### User Control

- [ ] **CTRL-01**: Clear error messages when uncomputation fails or is invalid
- [ ] **CTRL-02**: Explicit `uncompute()` method available for manual control

## Future Requirements

Deferred to later milestones. Tracked but not in current roadmap.

### Debug & Visualization

- **DEBUG-01**: Debug mode showing what would be uncomputed before execution
- **DEBUG-02**: Statistics tracking showing qubits saved via uncomputation
- **DEBUG-03**: OpenQASM comment markers for uncomputation blocks in output

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Automatic qubit cloning | Violates no-cloning theorem — physically impossible |
| Measurement-based uncomputation | Not reversible — contradicts clean uncomputation goal |
| Global uncomputation at circuit end | Too late for qubit reuse benefits |
| Implicit uncomputation without tracking | Unsafe — could uncompute values still in use |
| Recompute-on-demand | Complex feature with unclear benefits (Qrisp implements, value questionable) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRACK-01 | Phase 16 | Complete |
| TRACK-02 | Phase 16 | Complete |
| TRACK-03 | Phase 16 | Complete |
| TRACK-04 | Phase 16 | Complete |
| UNCOMP-01 | Phase 17 | Complete |
| UNCOMP-04 | Phase 17 | Complete |
| UNCOMP-02 | Phase 18 | Complete |
| UNCOMP-03 | Phase 18 | Complete |
| SCOPE-02 | Phase 18 | Complete |
| SCOPE-01 | Phase 19 | Complete |
| SCOPE-04 | Phase 19 | Complete |
| MODE-01 | Phase 20 | Pending |
| MODE-02 | Phase 20 | Pending |
| MODE-03 | Phase 20 | Pending |
| CTRL-01 | Phase 20 | Pending |
| CTRL-02 | Phase 20 | Pending |
| SCOPE-03 | Phase 20 | Pending |

**Coverage:**
- v1.2 requirements: 17 total
- Mapped to phases: 17/17
- Unmapped: 0

**Phase distribution:**
- Phase 16 (Dependency Tracking): 4 requirements
- Phase 17 (Reverse Gate Generation): 2 requirements
- Phase 18 (Basic Uncomputation): 3 requirements
- Phase 19 (Context Manager Integration): 2 requirements
- Phase 20 (Modes and Control): 6 requirements

---
*Requirements defined: 2026-01-28*
*Last updated: 2026-01-28 after roadmap creation (100% coverage achieved)*
