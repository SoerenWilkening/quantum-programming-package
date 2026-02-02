# Requirements: Quantum Assembly v1.8

**Defined:** 2026-02-02
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.8 Requirements

Requirements for v1.8 release. Each maps to roadmap phases.

### Quantum Copy

- [ ] **COPY-01**: qint supports CNOT-based quantum state copy (allocate new qubits, CNOT each bit from source to target)
- [ ] **COPY-02**: qarray binary ops (`+`, `-`, `*`, etc.) produce new arrays with quantum-copied elements instead of classical-value-initialized elements
- [ ] **COPY-03**: qint binary ops (`qint + int`, `qint + qint`) use quantum copy for the source operand before applying the operation

### Array Mutability

- [ ] **AMUT-01**: `qarray[i] += x` modifies the element's existing qubits in-place (where `x` is int, qint, or qbool)
- [ ] **AMUT-02**: `qarray[i] -= x`, `qarray[i] *= x`, and other augmented assignments work in-place
- [ ] **AMUT-03**: Multi-dimensional indexing works for in-place ops (`qarray[i, j] += x`)

### Uncomputation Fix

- [ ] **UNCOMP-01**: Investigate and identify the uncomputation regression
- [ ] **UNCOMP-02**: Fix automatic uncomputation so expressions uncompute correctly on scope exit

## Future Requirements

**Deferred from v1.7 (carry forward):**
- BUG-MOD-REDUCE: _reduce_mod result corruption — needs different circuit structure
- BUG-COND-MUL-01: Controlled multiplication corruption — not yet investigated
- BUG-DIV-02: MSB comparison leak in division

## Out of Scope

| Feature | Reason |
|---------|--------|
| Deep copy (full entanglement cloning) | Violates no-cloning theorem — CNOT copy creates correlated state, not independent clone |
| qarray element deletion/insertion | Array structure is fixed at creation; only element values change |
| Uncomputation of array elements | Complex interaction with mutability; defer to future |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COPY-01 | TBD | Pending |
| COPY-02 | TBD | Pending |
| COPY-03 | TBD | Pending |
| AMUT-01 | TBD | Pending |
| AMUT-02 | TBD | Pending |
| AMUT-03 | TBD | Pending |
| UNCOMP-01 | TBD | Pending |
| UNCOMP-02 | TBD | Pending |

**Coverage:**
- v1.8 requirements: 8 total
- Mapped to phases: 0
- Unmapped: 8 (pending roadmap)

---
*Requirements defined: 2026-02-02*
*Last updated: 2026-02-02 after initial definition*
