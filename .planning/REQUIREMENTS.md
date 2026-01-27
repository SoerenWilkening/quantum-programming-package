# Requirements: Quantum Assembly v1.1

**Defined:** 2026-01-27
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.1 Requirements

Requirements for QPU State Removal & Comparison Refactoring milestone.

### Global State Removal

- [x] **GLOB-01**: Remove QPU_state global dependency from C backend
- [x] **GLOB-02**: Implement `CQ_equal_width` to take classical value and width as parameters (replaces removed CQ_equal)
- [x] **GLOB-03**: Implement `cCQ_equal_width` to take classical value and width as parameters (replaces removed cCQ_equal)
- [x] **GLOB-04**: Remove `CC_equal` (purely classical, not needed) - *Completed in Phase 11-01*

### Comparison Refactoring

- [x] **COMP-01**: Implement qint == int using `CQ_equal_width` in Python bindings
- [x] **COMP-02**: Implement qint == qint as `(qint - qint) == 0`
- [ ] **COMP-03**: Refactor <= to use in-place subtraction/addition (no temp qint)
- [ ] **COMP-04**: Refactor >= to use in-place subtraction/addition (no temp qint)

### Initialization

- [ ] **INIT-01**: Initialize qint with classical value by setting qubits to |1> via Q_not based on binary representation

## Future Requirements

Deferred to later milestones.

- **SHIFT-01**: Bit shift operations (<<, >>)
- **QASM-01**: OpenQASM 3.0 export
- **OPT-01**: Advanced circuit optimization passes

## Out of Scope

Explicitly excluded from this milestone.

| Feature | Reason |
|---------|--------|
| New arithmetic operations | v1.1 focuses on cleanup, not new features |
| OpenQASM 3.0 | Deferred to later milestone |
| Python API changes | Internal refactoring only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GLOB-01 | Phase 11 | Complete |
| GLOB-02 | Phase 12 | Complete |
| GLOB-03 | Phase 12 | Complete |
| GLOB-04 | Phase 11 | Complete (CC_equal removed in 11-01) |
| COMP-01 | Phase 13 | Complete |
| COMP-02 | Phase 13 | Complete |
| COMP-03 | Phase 14 | Pending |
| COMP-04 | Phase 14 | Pending |
| INIT-01 | Phase 15 | Pending |

**Coverage:**
- v1.1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

**Note:** GLOB-02 and GLOB-03 updated to reflect actual work needed (implement new functions, not refactor removed ones). The original CQ_equal/cCQ_equal functions were removed in Phase 11-04 as part of QPU_state cleanup.

---
*Requirements defined: 2026-01-27*
*Last updated: 2026-01-27 — Phase 13 complete (COMP-01, COMP-02 satisfied)*
