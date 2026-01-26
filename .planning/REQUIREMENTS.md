# Requirements: Quantum Assembly

**Defined:** 2026-01-25
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundation

- [x] **FOUND-01**: Functions that modify circuit state accept explicit circuit_t* context (sequence-returning functions remain stateless)
- [x] **FOUND-02**: Memory ownership documented at every allocation point
- [x] **FOUND-03**: All sizeof() usage corrected (use sizeof(type) not sizeof(pointer))
- [x] **FOUND-04**: All structure fields initialized before use
- [x] **FOUND-05**: NULL checks after all malloc/calloc operations
- [x] **FOUND-06**: Qubit allocator centralizes qubit lifecycle management
- [x] **FOUND-07**: qint/qbool borrow qubits from circuit with tracked ownership
- [x] **FOUND-08**: Ancilla qubit allocation is trackable without significant performance overhead

### Testing Infrastructure

- [x] **TEST-01**: Characterization test suite captures current behavior before refactoring
- [ ] **TEST-02**: C backend unit tests cover core functions
- [ ] **TEST-03**: Python API unit tests cover qint/qbool operations
- [x] **TEST-04**: Valgrind/ASan memory testing integrated into development workflow
- [x] **TEST-05**: Pre-commit hooks enforce code quality (Ruff, linting)

### Variable-Width Integers

- [ ] **VINT-01**: QInt constructor accepts width parameter for arbitrary bit sizes
- [ ] **VINT-02**: Dynamic allocation based on width parameter
- [ ] **VINT-03**: Width validation in arithmetic operations
- [ ] **VINT-04**: Mixed-width integer operations handled correctly

### Arithmetic Operations

- [ ] **ARTH-01**: Addition works for variable-width integers
- [ ] **ARTH-02**: Subtraction works for variable-width integers
- [ ] **ARTH-03**: Multiplication works for any integer size (not just fixed)
- [ ] **ARTH-04**: Comparisons (>, <, ==, >=, <=) work for variable-width integers
- [ ] **ARTH-05**: Division operation implemented
- [ ] **ARTH-06**: Modulo operation implemented
- [ ] **ARTH-07**: Modular arithmetic (add/sub/mul mod N) implemented

### Bit Operations

- [ ] **BITOP-01**: Bitwise AND on quantum integers
- [ ] **BITOP-02**: Bitwise OR on quantum integers
- [ ] **BITOP-03**: Bitwise XOR on quantum integers
- [ ] **BITOP-04**: Bitwise NOT on quantum integers
- [ ] **BITOP-05**: Python operator overloading for bitwise ops (&, |, ^, ~)

### Circuit Output

- [ ] **CIRC-01**: Text-based circuit visualization for debugging
- [ ] **CIRC-02**: Automatic gate merging optimization
- [ ] **CIRC-03**: Inverse gate cancellation
- [ ] **CIRC-04**: Circuit statistics (depth, gate count, qubit usage)

### Code Organization

- [x] **CODE-01**: QPU.c responsibilities separated into focused modules
- [x] **CODE-02**: Circuit builder module (create/destroy/add gates)
- [x] **CODE-03**: Circuit optimizer module (layer assignment, merging)
- [ ] **CODE-04**: Operations organized by category (arithmetic, comparison, logic)
- [x] **CODE-05**: Clear dependency graph between modules

### Documentation

- [ ] **DOCS-01**: Comprehensive docstrings (NumPy style)
- [ ] **DOCS-02**: Sphinx documentation with examples
- [ ] **DOCS-03**: API reference auto-generated from docstrings
- [ ] **DOCS-04**: Tutorial examples demonstrating features

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Bit Operations

- **BITOP-06**: Bit shifts (left/right logical)
- **BITOP-07**: Bit shifts (arithmetic)
- **BITOP-08**: Bit rotations (left/right)

### Output Formats

- **OUT-01**: OpenQASM 3.0 export (mid-circuit measurement, real-time conditionals)
- **OUT-02**: Multiple hardware backend support

### Advanced Features

- **ADV-01**: QFT-based arithmetic (more efficient than ripple-carry)
- **ADV-02**: Exponentiation operations
- **ADV-03**: Circuit templates library (QFT, Grover, phase estimation)
- **ADV-04**: Direct/immediate execution mode

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Direct execution mode | Future direction, keep circuit compilation approach for v1 |
| Hardware integration | OpenQASM export handles most cases |
| ML framework integration | Requires stable API first, complex integration |
| Real-time debugging | Complex infrastructure requirement |
| GUI interface | Programmatic API sufficient for v1 |
| Direct quantum state access | Violates no-cloning theorem |
| Automatic qubit cloning | Physically impossible |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 2 | Complete |
| FOUND-02 | Phase 2 | Complete |
| FOUND-03 | Phase 2 | Complete |
| FOUND-04 | Phase 2 | Complete |
| FOUND-05 | Phase 2 | Complete |
| FOUND-06 | Phase 3 | Complete |
| FOUND-07 | Phase 3 | Complete |
| FOUND-08 | Phase 3 | Complete |
| TEST-01 | Phase 1 | Complete |
| TEST-02 | Phase 10 | Pending |
| TEST-03 | Phase 10 | Pending |
| TEST-04 | Phase 1 | Complete |
| TEST-05 | Phase 1 | Complete |
| VINT-01 | Phase 5 | Pending |
| VINT-02 | Phase 5 | Pending |
| VINT-03 | Phase 5 | Pending |
| VINT-04 | Phase 5 | Pending |
| ARTH-01 | Phase 5 | Pending |
| ARTH-02 | Phase 5 | Pending |
| ARTH-03 | Phase 7 | Pending |
| ARTH-04 | Phase 7 | Pending |
| ARTH-05 | Phase 7 | Pending |
| ARTH-06 | Phase 7 | Pending |
| ARTH-07 | Phase 7 | Pending |
| BITOP-01 | Phase 6 | Pending |
| BITOP-02 | Phase 6 | Pending |
| BITOP-03 | Phase 6 | Pending |
| BITOP-04 | Phase 6 | Pending |
| BITOP-05 | Phase 6 | Pending |
| CIRC-01 | Phase 8 | Pending |
| CIRC-02 | Phase 8 | Pending |
| CIRC-03 | Phase 8 | Pending |
| CIRC-04 | Phase 8 | Pending |
| CODE-01 | Phase 4 | Complete |
| CODE-02 | Phase 4 | Complete |
| CODE-03 | Phase 4 | Complete |
| CODE-04 | Phase 9 | Pending |
| CODE-05 | Phase 4 | Complete |
| DOCS-01 | Phase 10 | Pending |
| DOCS-02 | Phase 10 | Pending |
| DOCS-03 | Phase 10 | Pending |
| DOCS-04 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0

---
*Requirements defined: 2026-01-25*
*Last updated: 2026-01-26 after Phase 4 completion*
