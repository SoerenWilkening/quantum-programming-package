# Requirements: Quantum Assembly v1.5

**Defined:** 2026-01-30
**Core Value:** Write quantum algorithms in natural programming style that compiles to efficient, memory-optimized quantum circuits.

## v1.5 Requirements

### Bug Fixes

- [x] **BUG-01**: Fix subtraction underflow (3-7 returns 7 instead of wrapping to correct unsigned result)
- [x] **BUG-02**: Fix less-or-equal comparison (5<=5 returns 0 instead of 1)
- [x] **BUG-03**: Fix multiplication segfaults at certain widths
- [x] **BUG-04**: Fix QFT addition bug with both nonzero operands

### Verification Framework

- [x] **VFWK-01**: Reusable test framework: build circuit -> export OpenQASM -> Qiskit simulate -> verify outcome
- [x] **VFWK-02**: Parameterized test generation (exhaustive for small widths, representative for larger)
- [x] **VFWK-03**: Clear failure diagnostics (expected vs actual, operation, operand values, bit widths)

### Verification — Initialization

- [x] **VINIT-01**: Verify classical qint initialization produces correct values across all bit widths

### Verification — Arithmetic

- [x] **VARITH-01**: Verify addition (exhaustive 1-4 bits, representative larger)
- [x] **VARITH-02**: Verify subtraction (exhaustive 1-4 bits, representative larger)
- [x] **VARITH-03**: Verify multiplication (exhaustive 1-3 bits, representative larger)
- [x] **VARITH-04**: Verify division and modulo operations
- [x] **VARITH-05**: Verify modular arithmetic (add/sub/mul mod N)

### Verification — Comparison

- [ ] **VCMP-01**: Verify all 6 comparison operators (==, !=, <, >, <=, >=)
- [ ] **VCMP-02**: Verify qint vs int and qint vs qint comparison variants
- [ ] **VCMP-03**: Verify comparison edge cases (equal values, boundaries, zero)

### Verification — Bitwise

- [ ] **VBIT-01**: Verify AND, OR, XOR, NOT operations
- [ ] **VBIT-02**: Verify bitwise operations with variable-width operands

### Verification — Advanced

- [ ] **VADV-01**: Verify automatic uncomputation (ancilla qubits return to |0>)
- [ ] **VADV-02**: Verify quantum conditionals (`with` blocks)
- [ ] **VADV-03**: Verify ql.array operations (reductions, element-wise)

## Future Requirements

- Statistical verification for superposition-based algorithms
- Noise model simulation testing
- Hardware execution verification
- Performance regression benchmarks

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hardware execution testing | OpenQASM export covers this path |
| Noise model simulation | Not relevant for correctness verification |
| GUI test runner | CLI/pytest sufficient |
| Nested conditional verification | Requires quantum-quantum AND (not yet implemented) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 29 | Complete |
| BUG-02 | Phase 29 | Complete |
| BUG-03 | Phase 29 | Complete |
| BUG-04 | Phase 29 | Complete |
| VFWK-01 | Phase 28 | Complete |
| VFWK-02 | Phase 28 | Complete |
| VFWK-03 | Phase 28 | Complete |
| VINIT-01 | Phase 28 | Complete |
| VARITH-01 | Phase 30 | Complete |
| VARITH-02 | Phase 30 | Complete |
| VARITH-03 | Phase 30 | Complete |
| VARITH-04 | Phase 30 | Complete |
| VARITH-05 | Phase 30 | Complete |
| VCMP-01 | Phase 31 | Pending |
| VCMP-02 | Phase 31 | Pending |
| VCMP-03 | Phase 31 | Pending |
| VBIT-01 | Phase 32 | Pending |
| VBIT-02 | Phase 32 | Pending |
| VADV-01 | Phase 33 | Pending |
| VADV-02 | Phase 33 | Pending |
| VADV-03 | Phase 33 | Pending |

**Coverage:**
- v1.5 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-31 after Phase 30 completion*
